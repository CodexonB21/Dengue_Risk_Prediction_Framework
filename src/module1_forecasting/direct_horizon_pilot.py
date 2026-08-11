"""M1-023/M1-024 pilot - direct h=2/3/4 Stage 2 models vs. the CURRENT
recursive approach's output at the same horizons, both evaluated at
genuinely dense, weekly-spaced historical origins.

## Why this exists

M1-022/Decision 053 found the recursive multi-week forecast (`forecast_future.py`)
carries a systematic downward bias once Stage 2's lag features become fully
recursive (fed on the model's own prior predictions rather than real data,
from horizon_step=2 onward). The textbook fix is a DIRECT strategy: train a
separate Stage 2 model per horizon step, each predicting straight from
features known at the forecast origin, never from a recursively-generated
guess. M1-023 piloted this at horizon=2 only and found a holdout-confirmed
improvement. This version generalizes to horizons 2, 3, AND 4 together in
one pass (M1-024) - reusing the SAME SARIMA fit per origin (asked for
`n_periods=MAX_HORIZON` once, not refit per horizon) and chaining the
recursive comparison through each step exactly as `forecast_future.py`
itself does for a genuinely multi-step recursive forecast.

## Two leakage risks found while designing the h=2 pilot (unchanged here,
## still avoided the same way):

1. `sarima_prediction` (an existing Stage 2 feature) is normally the SARIMA
   forecast FOR that exact row's week - reusing it unmodified for an h>1
   target would silently use a shorter-horizon number to predict a
   longer-horizon target. Fixed by asking ONE SARIMAX fit for
   `n_periods=MAX_HORIZON` and using the (h-1)-th step specifically as that
   horizon's `sarima_prediction`.
2. `rainfall_anomaly`/`temperature_anomaly`/`humidity_anomaly` are
   contemporaneous with the row's own week (real, same-week weather - safe
   for the EXISTING h=1 design, since weather reporting outpaces case
   reporting). This script deliberately does NOT give any direct-h model a
   forward (target-week) climate anomaly at all - every direct-h model
   reuses the SAME origin week's own anomaly the h=1 model already uses.
   This is a conservative simplification (documented, not hidden): the
   direct models get no forward climate signal at all, while the RECURSIVE
   comparison below effectively does get each target week's real climate
   (via its own recursive feature reconstruction) - a genuine asymmetry in
   the recursive approach's favor, left in place rather than papered over.

## Method, per district, per historical origin week W:

1. Fit SARIMA once on data through W-1, ask for `n_periods=MAX_HORIZON`:
   step[0] = h1 forecast (FOR week W), step[1] = h2 (FOR W+1), step[2] = h3
   (FOR W+2), step[3] = h4 (FOR W+3).
2. Build W's feature row exactly as `rolling_one_step.py` does (same
   `build_fold_agnostic_features`/`compute_fold_climate_anomalies` calls) -
   this SAME base row is reused, unchanged, for every direct-h model; only
   `sarima_prediction` differs per horizon.
3. Direct-h training row (h=2,3,4): W's base feature row, `sarima_prediction`
   = that horizon's SARIMA value, target = `actual(W+h-1) - sarima_h`.
4. Recursive comparison, CHAINED exactly as `forecast_future.py` recurses:
   - h1: apply the CURRENT production model to W's real feature row ->
     `predicted_residual_h1`, `final_prediction_h1` (reproduces
     `rolling_one_step.py`'s own h1 output).
   - h2: insert `final_prediction_h1` as a synthetic `Number_of_Cases` at
     W+1 (real climate, since this is a historical backtest - the date has
     already happened), rebuild features, `residual_lag_1 =
     predicted_residual_h1` (the model's own prior guess, not a real lag -
     matches `forecast_future.py`'s own convention), apply the model again.
   - h3/h4: repeat, each step inserting the PREVIOUS step's
     `final_prediction_h*` as that week's synthetic case count, with
     `residual_lag_1`/`residual_lag_2` set to the two most recent steps'
     `predicted_residual_h*` values (real lags run out entirely by h3).
5. `residual_lag_1/2` for every DIRECT model (any horizon) come from a
   clean, weekly (not annual-fold) rolling h1 residual history - `actual(W)
   - sarima_h1_forecast_made_from_W-1` - never from the recursive chain
   above, and never from the annual-fold `sarima_stage1_predictions.csv`
   (see M1-023's discussion for why that fold-annual design mixes
   forecast horizons within a fold and isn't the right basis here).

Run standalone: `python -m src.module1_forecasting.direct_horizon_pilot`
(add `--districts` to pilot a subset first, `--scope holdout` for a quick
sanity check before the full `--scope all` run, `--max-horizon` to change
how many steps ahead are computed - default 4).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_DIRECT_HORIZON_PILOT_PATH,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.baseline_sarima import _has_explosive_ar_root, fit_and_forecast  # noqa: E402
from src.module1_forecasting.compensation_model import FEATURE_COLUMNS  # noqa: E402
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    HUMIDITY_COLUMN,
    RAINFALL_COLUMN,
    TEMPERATURE_COLUMN,
    build_fold_agnostic_features,
    compute_fold_climate_anomalies,
)
from src.module1_forecasting.residual_transform import (  # noqa: E402
    combine_stage2_forecast,
    compute_stage2_target,
    validate_residual_mode,
)
from src.module1_forecasting.rolling_one_step import _load_selected_configs  # noqa: E402
from src.module1_forecasting.validation import DEFAULT_MIN_TRAIN_YEARS, DEFAULT_WEEKS_PER_YEAR  # noqa: E402

logger = logging.getLogger(__name__)

MAX_HORIZON_DEFAULT = 4
CLIMATE_RAW_COLUMNS = [RAINFALL_COLUMN, TEMPERATURE_COLUMN, HUMIDITY_COLUMN]
FOLD_AGNOSTIC_NUMERIC = [c for c in FEATURE_COLUMNS if c not in (
    "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly",
    "sarima_prediction", "residual_lag_1", "residual_lag_2", "District",
)]


def _week_key(year: int, week: int) -> tuple[int, int]:
    return int(year), int(week)


def _origin_feature_row(hist_df_through_w: pd.DataFrame) -> dict:
    """W's own feature row (base_feature_row, no `sarima_prediction`/
    `residual_lag_*` yet) - identical construction to `rolling_one_step.py`.
    `hist_df_through_w` must already have W's OWN `Number_of_Cases` set to
    NaN (the target being featured)."""
    feats = build_fold_agnostic_features(hist_df_through_w)
    row_feats = feats.iloc[-1]

    train_mask = pd.Series(False, index=hist_df_through_w.index)
    train_mask.iloc[:-1] = True
    anomalies = compute_fold_climate_anomalies(hist_df_through_w, train_mask)
    anomaly_row = anomalies.iloc[-1]

    base = {col: row_feats[col] for col in FOLD_AGNOSTIC_NUMERIC if col in row_feats.index}
    base["rainfall_anomaly"] = float(anomaly_row["rainfall_anomaly"])
    base["temperature_anomaly"] = float(anomaly_row["temperature_anomaly"])
    base["humidity_anomaly"] = float(anomaly_row["humidity_anomaly"])
    return base


def rolling_direct_and_recursive_district(
    district: str,
    weekly_df: pd.DataFrame,
    sarima_config: dict,
    xgb_model_production: xgb.XGBRegressor,
    *,
    min_train_weeks: int,
    target_keys: set[tuple[int, int]] | None,
    residual_mode: str = M1_STAGE2_RESIDUAL_MODE,
    max_horizon: int = MAX_HORIZON_DEFAULT,
) -> pd.DataFrame:
    """One row per scoreable historical origin week W, with columns for
    EVERY horizon 2..max_horizon (h=1 is the unchanged production design,
    used only as the recursion's first step, not re-evaluated here)."""
    dist_df = (
        weekly_df.loc[weekly_df["District"] == district]
        .sort_values(["Year", "Week"])
        .reset_index(drop=True)
    )
    if len(dist_df) <= min_train_weeks + max_horizon:
        return pd.DataFrame()

    work_cols = ["District", "Year", "Week", "Number_of_Cases", "is_imputed", "is_reporting_anomaly"] + CLIMATE_RAW_COLUMNS
    work_cols = [c for c in work_cols if c in dist_df.columns]

    residual_history: dict[tuple[int, int], float] = {}
    rows: list[dict] = []

    for i in range(min_train_weeks, len(dist_df) - max_horizon + 1):
        row = dist_df.iloc[i]
        year, week = int(row["Year"]), int(row["Week"])
        key = _week_key(year, week)

        train_df = dist_df.iloc[:i]
        train_series = pd.Series(
            train_df["Number_of_Cases"].to_numpy(dtype=float),
            index=pd.MultiIndex.from_frame(train_df[["Year", "Week"]]),
        )
        forecast_arr = fit_and_forecast(
            train_series,
            n_periods=max_horizon,
            order=sarima_config["order"],
            seasonal_order=sarima_config["seasonal_order"],
            use_log1p=sarima_config["use_log1p"],
            context=f"{district} direct-horizon pilot origin {year} Wk{week}",
        )
        sarima_steps = [float(v) for v in forecast_arr]  # index s -> horizon s+1

        hist_df = dist_df.iloc[: i + 1][work_cols].copy()
        real_case_at_w = float(hist_df["Number_of_Cases"].iloc[-1])
        hist_df.loc[hist_df.index[-1], "Number_of_Cases"] = np.nan
        base_feature_row = _origin_feature_row(hist_df)
        base_feature_row["District"] = district

        prev1 = _week_key(int(dist_df.iloc[i - 1]["Year"]), int(dist_df.iloc[i - 1]["Week"])) if i >= 1 else None
        prev2 = _week_key(int(dist_df.iloc[i - 2]["Year"]), int(dist_df.iloc[i - 2]["Week"])) if i >= 2 else None
        residual_lag_1 = residual_history.get(prev1, np.nan) if prev1 else np.nan
        residual_lag_2 = residual_history.get(prev2, np.nan) if prev2 else np.nan

        # --- h1: production model on W's real feature row (recursion's seed step) ---
        feature_row_h1 = {**base_feature_row, "sarima_prediction": sarima_steps[0],
                           "residual_lag_1": residual_lag_1, "residual_lag_2": residual_lag_2}
        X1 = pd.DataFrame([feature_row_h1])[FEATURE_COLUMNS]
        X1["District"] = pd.Categorical(X1["District"], categories=DISTRICTS)
        predicted_residual_prev = float(xgb_model_production.predict(X1)[0])
        final_prediction_prev = float(combine_stage2_forecast(sarima_steps[0], predicted_residual_prev, mode=residual_mode))

        # extended_df carries the recursion forward one synthetic row at a time.
        extended_df = dist_df.iloc[: i + 1][work_cols].copy()
        extended_df.loc[extended_df.index[-1], "Number_of_Cases"] = real_case_at_w
        residual_lag_1_recursive, residual_lag_2_recursive = residual_lag_1, residual_lag_2

        include = target_keys is None or key in target_keys
        entry = {
            "District": district, "origin_Year": year, "origin_Week": week,
            **{f"feat__{k}": v for k, v in base_feature_row.items() if k != "District"},
            "feat__residual_lag_1": residual_lag_1, "feat__residual_lag_2": residual_lag_2,
        }

        for s in range(1, max_horizon):  # s=1 -> horizon 2, s=2 -> horizon 3, s=3 -> horizon 4
            horizon = s + 1
            target_idx = i + s
            if target_idx >= len(dist_df):
                break
            target_row = dist_df.iloc[target_idx]
            t_year, t_week = int(target_row["Year"]), int(target_row["Week"])
            sarima_h = sarima_steps[s]

            # --- recursive comparison: insert PREVIOUS step's prediction as this step's synthetic history ---
            synthetic_row = {c: np.nan for c in work_cols}
            synthetic_row.update({
                "District": district, "Year": t_year, "Week": t_week,
                "Number_of_Cases": final_prediction_prev, "is_imputed": False, "is_reporting_anomaly": False,
            })
            for c in CLIMATE_RAW_COLUMNS:
                if c in dist_df.columns:
                    synthetic_row[c] = target_row[c]
            extended_df = pd.concat([extended_df, pd.DataFrame([synthetic_row])], ignore_index=True)

            feats_r = build_fold_agnostic_features(extended_df)
            row_feats_r = feats_r.iloc[-1]
            train_mask_r = pd.Series(False, index=extended_df.index)
            train_mask_r.iloc[:-1] = True
            anomalies_r = compute_fold_climate_anomalies(extended_df, train_mask_r)
            anomaly_row_r = anomalies_r.iloc[-1]

            recursive_feature_row = {col: row_feats_r[col] for col in FOLD_AGNOSTIC_NUMERIC if col in row_feats_r.index}
            recursive_feature_row["rainfall_anomaly"] = float(anomaly_row_r["rainfall_anomaly"])
            recursive_feature_row["temperature_anomaly"] = float(anomaly_row_r["temperature_anomaly"])
            recursive_feature_row["humidity_anomaly"] = float(anomaly_row_r["humidity_anomaly"])
            recursive_feature_row["sarima_prediction"] = sarima_h
            recursive_feature_row["residual_lag_1"] = residual_lag_1_recursive if s == 1 else predicted_residual_prev
            recursive_feature_row["residual_lag_2"] = residual_lag_2_recursive if s == 1 else residual_lag_1_recursive
            recursive_feature_row["District"] = district

            Xr = pd.DataFrame([recursive_feature_row])[FEATURE_COLUMNS]
            Xr["District"] = pd.Categorical(Xr["District"], categories=DISTRICTS)
            predicted_residual_h = float(xgb_model_production.predict(Xr)[0])
            final_prediction_h = float(combine_stage2_forecast(sarima_h, predicted_residual_h, mode=residual_mode))

            # roll the recursion's own bookkeeping forward for the NEXT step
            residual_lag_2_recursive = residual_lag_1_recursive if s == 1 else predicted_residual_prev
            residual_lag_1_recursive = predicted_residual_prev
            predicted_residual_prev, final_prediction_prev = predicted_residual_h, final_prediction_h

            # --- direct-h target (only recorded if this origin is in scope) ---
            actual_h = float(target_row["Number_of_Cases"])
            target_h_direct = float(compute_stage2_target(actual_h, sarima_h, mode=residual_mode))

            if include:
                entry[f"sarima_h{horizon}"] = sarima_h
                entry[f"actual_h{horizon}"] = actual_h
                entry[f"target_Year_h{horizon}"] = t_year
                entry[f"target_Week_h{horizon}"] = t_week
                entry[f"is_imputed_h{horizon}"] = bool(target_row.get("is_imputed", False))
                entry[f"stage2_target_h{horizon}"] = target_h_direct
                entry[f"final_prediction_recursive_h{horizon}"] = round(final_prediction_h, 1)

        if include:
            rows.append(entry)

        if not np.isnan(sarima_steps[0]) and not bool(row.get("is_reporting_anomaly", False)):
            residual_history[key] = float(compute_stage2_target(real_case_at_w, sarima_steps[0], mode=residual_mode))

    return pd.DataFrame(rows)


def run_direct_horizon_pilot(
    districts: list[str] | None = None,
    *,
    scope: str = "all",
    min_train_years: int = DEFAULT_MIN_TRAIN_YEARS,
    residual_mode: str | None = None,
    max_horizon: int = MAX_HORIZON_DEFAULT,
    output_path: Path | None = None,
) -> pd.DataFrame:
    mode = validate_residual_mode(residual_mode or M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    sarima_configs = _load_selected_configs()
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(paths["xgboost_final_model"]))

    districts = districts or DISTRICTS
    min_train_weeks = min_train_years * DEFAULT_WEEKS_PER_YEAR

    from src.module1_forecasting.rolling_one_step import _holdout_target_keys  # noqa: E402

    frames = []
    for district in districts:
        target_keys = _holdout_target_keys(weekly_df, district) if scope == "holdout" else None
        logger.info("Direct-horizon pilot scoring %s (scope=%s, max_horizon=%d)...", district, scope, max_horizon)
        frames.append(
            rolling_direct_and_recursive_district(
                district, weekly_df, sarima_configs[district], xgb_model,
                min_train_weeks=min_train_weeks, target_keys=target_keys, residual_mode=mode,
                max_horizon=max_horizon,
            )
        )

    result = pd.concat(frames, ignore_index=True)
    out_path = output_path or MODULE1_DIRECT_HORIZON_PILOT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    logger.info("Wrote %d direct-horizon-pilot rows to %s.", len(result), out_path)
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M1-023/M1-024 direct multi-horizon Stage 2 pilot.")
    parser.add_argument("--districts", nargs="+", default=None, help="Districts to score (default: all).")
    parser.add_argument(
        "--scope", choices=["holdout", "all"], default="all",
        help="holdout = last 2 years per district only (fast sanity check); all = full history.",
    )
    parser.add_argument("--max-horizon", type=int, default=MAX_HORIZON_DEFAULT, help="Furthest horizon to compute (default 4).")
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_direct_horizon_pilot(districts=args.districts, scope=args.scope, max_horizon=args.max_horizon)
