"""M1-023 pilot - direct h=2 Stage 2 model vs. the CURRENT recursive
approach's h=2 output, both evaluated at genuinely dense, weekly-spaced
historical origins.

## Why this exists

M1-022/Decision 053 found the recursive multi-week forecast (`forecast_future.py`)
carries a systematic downward bias once Stage 2's lag features become fully
recursive (fed on the model's own prior predictions rather than real data,
from horizon_step=2 onward). The textbook fix is a DIRECT strategy: train a
separate Stage 2 model per horizon step, each predicting straight from
features known at the forecast origin, never from a recursively-generated
guess. This script is the first, smallest piece of that: a horizon=2 pilot,
built to answer "does this actually help, and by how much" before committing
to horizons 3/4 too.

## Two leakage risks found while designing this (not obvious from the
## existing per-row feature table) - both avoided here, see inline comments:

1. `sarima_prediction` (an existing Stage 2 feature) is normally the SARIMA
   forecast FOR that exact row's week - reusing it unmodified for an h=2
   target would silently use a 1-step-ahead number to predict a 2-step-ahead
   target. Fixed by asking the SAME SARIMAX fit for `n_periods=2` and using
   the SECOND step specifically as this model's `sarima_prediction`.
2. `rainfall_anomaly`/`temperature_anomaly`/`humidity_anomaly` are
   contemporaneous with the row's own week (real, same-week weather - safe
   for the EXISTING h=1 design, since weather reporting outpaces case
   reporting). This script deliberately does NOT try to give the h=2 model a
   forward (target-week) climate anomaly at all - it reuses the SAME origin
   week's own anomaly the h=1 model already uses. This is a conservative
   simplification (documented, not hidden): the h=2 model gets no forward
   climate signal at all, while the RECURSIVE comparison below effectively
   does get the target week's real climate (via its own recursive feature
   reconstruction) - a genuine asymmetry in the recursive approach's favor,
   left in place rather than papered over, since resolving it would require
   deciding how to handle target-week climate that isn't itself validated
   here.

## Method, per district, per historical origin week W (the same "row being
## scored" convention `rolling_one_step.py` already uses - SARIMA fit on data
## strictly before W, feature row anchored at W using W's own real,
## same-week climate plus lags strictly before W):

1. Fit SARIMA once on data through W-1, ask for `n_periods=2`:
   step[0] = h1 forecast (FOR week W, unchanged from the existing design),
   step[1] = h2 forecast (FOR week W+1, new).
2. Build W's feature row exactly as `rolling_one_step.py` does (same
   `build_fold_agnostic_features`/`compute_fold_climate_anomalies` calls).
3. Direct h2 training row: W's feature row, with `sarima_prediction`
   REPLACED by the h2 SARIMA value, target = `actual(W+1) - sarima_h2`.
4. Recursive h2 comparison row: apply the CURRENT PRODUCTION XGBoost model to
   W's (h1) feature row to get `final_prediction_h1` (this exactly
   reproduces `rolling_one_step.py`'s own h1 output), insert it as a
   synthetic `Number_of_Cases` for W+1 (mirroring `forecast_future.py`'s own
   recursion), rebuild W+1's feature row from that extended series (now
   partially recursive, exactly as production does for horizon_step=2), and
   apply the SAME current production model again to get
   `final_prediction_h2_recursive`.
5. `residual_lag_1/2` for both h1 and h2 direct-model rows come from a clean,
   weekly (not annual-fold) rolling h1 residual history - `actual(W) -
   sarima_h1_forecast_made_from_W-1`, tracked incrementally as the loop
   advances - never from the annual-fold `sarima_stage1_predictions.csv`,
   whose `sarima_prediction` column mixes together forecast horizons from 1
   to 52 depending on a row's position within its fold (a separate,
   previously-undocumented property of the existing walk-forward design,
   found while investigating this - see `research_context/RESEARCH_DECISIONS.md`
   Decision 053's discussion for why that fold-annual design is itself a
   deliberate, already-defended choice, just not the right basis for a
   dense-origin direct-h2 model).

## Model comparison

Reuses the EXACT SAME walk-forward fold boundaries, hyperparameters
(`XGB_BASE_PARAMS`), and training/early-stopping recipe
(`train_and_predict_fold`/`train_and_predict_holdout`) `compensation_model.py`
already uses for the production h=1 model - a new direct-h2 model is trained
per fold on that fold's own direct-h2 training rows, then compared against
(a) SARIMA-h2-alone (no correction) and (b) the recursive comparison rows
from step 4 above, on the SAME held-out weeks.

Run standalone: `python -m src.module1_forecasting.direct_horizon_pilot`
(add `--districts` to pilot a subset first, `--scope holdout` to restrict to
the last 2 years for a quick sanity check before the full `--scope all` run).
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
    MODULE1_DIRECT_HORIZON_PILOT_COMPARISON_PATH,
    MODULE1_DIRECT_HORIZON_PILOT_PATH,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.baseline_sarima import _has_explosive_ar_root, fit_and_forecast  # noqa: E402
from src.module1_forecasting.compensation_model import (  # noqa: E402
    FEATURE_COLUMNS,
    IMPUTED_COL,
    N_FOLDS,
    TARGET_COL,
    XGB_BASE_PARAMS,
    _prepare_xy,
    _trainable_mask,
    compute_fold_boundaries,
    train_and_predict_fold,
    train_and_predict_holdout,
)
from src.module1_forecasting.evaluate import dm_test, mase, smape  # noqa: E402
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

CLIMATE_RAW_COLUMNS = [RAINFALL_COLUMN, TEMPERATURE_COLUMN, HUMIDITY_COLUMN]
FOLD_AGNOSTIC_NUMERIC = [c for c in FEATURE_COLUMNS if c not in (
    "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly",
    "sarima_prediction", "residual_lag_1", "residual_lag_2", "District",
)]


def _week_key(year: int, week: int) -> tuple[int, int]:
    return int(year), int(week)


def rolling_direct_and_recursive_district(
    district: str,
    weekly_df: pd.DataFrame,
    sarima_config: dict,
    xgb_model_production: xgb.XGBRegressor,
    *,
    min_train_weeks: int,
    target_keys: set[tuple[int, int]] | None,
    residual_mode: str = M1_STAGE2_RESIDUAL_MODE,
) -> pd.DataFrame:
    """One row per scoreable historical origin week W (target_keys, if given,
    restricts which W's are scored - matching `rolling_one_step.py`'s
    `--scope holdout` convention - but SARIMA is still fit on ALL weeks up to
    W regardless, and `residual_history` is still updated for every W so
    later scored rows see an uninterrupted lag history).
    """
    dist_df = (
        weekly_df.loc[weekly_df["District"] == district]
        .sort_values(["Year", "Week"])
        .reset_index(drop=True)
    )
    if len(dist_df) <= min_train_weeks + 1:
        return pd.DataFrame()

    work_cols = ["District", "Year", "Week", "Number_of_Cases", "is_imputed", "is_reporting_anomaly"] + CLIMATE_RAW_COLUMNS
    work_cols = [c for c in work_cols if c in dist_df.columns]

    residual_history: dict[tuple[int, int], float] = {}
    rows: list[dict] = []

    # Stop one week early so W+1 (the h2 target) always exists.
    for i in range(min_train_weeks, len(dist_df) - 1):
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
            n_periods=2,
            order=sarima_config["order"],
            seasonal_order=sarima_config["seasonal_order"],
            use_log1p=sarima_config["use_log1p"],
            context=f"{district} direct-horizon pilot origin {year} Wk{week}",
        )
        sarima_h1 = float(forecast_arr[0])
        sarima_h2 = float(forecast_arr[1])

        # --- W's own feature row (identical construction to rolling_one_step.py) ---
        hist_df = dist_df.iloc[: i + 1][work_cols].copy()
        real_case_at_w = float(hist_df["Number_of_Cases"].iloc[-1])
        hist_df.loc[hist_df.index[-1], "Number_of_Cases"] = np.nan
        feats = build_fold_agnostic_features(hist_df)
        row_feats = feats.iloc[-1]

        train_mask = pd.Series(False, index=hist_df.index)
        train_mask.iloc[:-1] = True
        anomalies = compute_fold_climate_anomalies(hist_df, train_mask)
        anomaly_row = anomalies.iloc[-1]

        prev1 = _week_key(int(dist_df.iloc[i - 1]["Year"]), int(dist_df.iloc[i - 1]["Week"])) if i >= 1 else None
        prev2 = _week_key(int(dist_df.iloc[i - 2]["Year"]), int(dist_df.iloc[i - 2]["Week"])) if i >= 2 else None

        base_feature_row = {col: row_feats[col] for col in FOLD_AGNOSTIC_NUMERIC if col in row_feats.index}
        base_feature_row["rainfall_anomaly"] = float(anomaly_row["rainfall_anomaly"])
        base_feature_row["temperature_anomaly"] = float(anomaly_row["temperature_anomaly"])
        base_feature_row["humidity_anomaly"] = float(anomaly_row["humidity_anomaly"])
        base_feature_row["District"] = district
        residual_lag_1 = residual_history.get(prev1, np.nan) if prev1 else np.nan
        residual_lag_2 = residual_history.get(prev2, np.nan) if prev2 else np.nan

        feature_row_h1 = {**base_feature_row, "sarima_prediction": sarima_h1,
                           "residual_lag_1": residual_lag_1, "residual_lag_2": residual_lag_2}
        feature_row_h2_direct = {**base_feature_row, "sarima_prediction": sarima_h2,
                                  "residual_lag_1": residual_lag_1, "residual_lag_2": residual_lag_2}

        # --- Recursive comparison: apply the CURRENT production model at h1,
        # then recurse one more step exactly as forecast_future.py does. ---
        X1 = pd.DataFrame([feature_row_h1])[FEATURE_COLUMNS]
        X1["District"] = pd.Categorical(X1["District"], categories=DISTRICTS)
        predicted_residual_h1 = float(xgb_model_production.predict(X1)[0])
        final_prediction_h1 = float(combine_stage2_forecast(sarima_h1, predicted_residual_h1, mode=residual_mode))

        w1_year, w1_week = int(dist_df.iloc[i + 1]["Year"]), int(dist_df.iloc[i + 1]["Week"])
        extended_df = dist_df.iloc[: i + 1][work_cols].copy()
        extended_df.loc[extended_df.index[-1], "Number_of_Cases"] = real_case_at_w
        synthetic_row = {c: np.nan for c in work_cols}
        synthetic_row.update({
            "District": district, "Year": w1_year, "Week": w1_week,
            "Number_of_Cases": final_prediction_h1, "is_imputed": False, "is_reporting_anomaly": False,
        })
        for c in CLIMATE_RAW_COLUMNS:
            if c in dist_df.columns:
                synthetic_row[c] = dist_df.iloc[i + 1][c]
        extended_df = pd.concat([extended_df, pd.DataFrame([synthetic_row])], ignore_index=True)

        feats2 = build_fold_agnostic_features(extended_df)
        row_feats2 = feats2.iloc[-1]
        train_mask2 = pd.Series(False, index=extended_df.index)
        train_mask2.iloc[:-1] = True
        anomalies2 = compute_fold_climate_anomalies(extended_df, train_mask2)
        anomaly_row2 = anomalies2.iloc[-1]

        recursive_feature_row = {col: row_feats2[col] for col in FOLD_AGNOSTIC_NUMERIC if col in row_feats2.index}
        recursive_feature_row["rainfall_anomaly"] = float(anomaly_row2["rainfall_anomaly"])
        recursive_feature_row["temperature_anomaly"] = float(anomaly_row2["temperature_anomaly"])
        recursive_feature_row["humidity_anomaly"] = float(anomaly_row2["humidity_anomaly"])
        recursive_feature_row["sarima_prediction"] = sarima_h2
        recursive_feature_row["residual_lag_1"] = predicted_residual_h1  # recursive: model's OWN prior prediction
        recursive_feature_row["residual_lag_2"] = residual_lag_1  # one real lag back, matches forecast_future.py
        recursive_feature_row["District"] = district

        X2r = pd.DataFrame([recursive_feature_row])[FEATURE_COLUMNS]
        X2r["District"] = pd.Categorical(X2r["District"], categories=DISTRICTS)
        predicted_residual_h2_recursive = float(xgb_model_production.predict(X2r)[0])
        final_prediction_h2_recursive = float(
            combine_stage2_forecast(sarima_h2, predicted_residual_h2_recursive, mode=residual_mode)
        )

        actual_w1 = float(dist_df.iloc[i + 1]["Number_of_Cases"])
        target_h2_direct = float(compute_stage2_target(actual_w1, sarima_h2, mode=residual_mode))

        include = target_keys is None or key in target_keys
        if include:
            entry = {
                "District": district,
                "origin_Year": year, "origin_Week": week,
                "target_Year": w1_year, "target_Week": w1_week,
                "is_imputed": bool(dist_df.iloc[i + 1].get("is_imputed", False)),
                "actual_target": actual_w1,
                "sarima_h1": sarima_h1, "sarima_h2": sarima_h2,
                "stage2_target": target_h2_direct,
                "final_prediction_recursive_h2": round(final_prediction_h2_recursive, 1),
                **{f"feat__{k}": v for k, v in feature_row_h2_direct.items() if k != "District"},
            }
            rows.append(entry)

        # --- Update the CLEAN weekly h1 residual history for future origins' lags ---
        if not np.isnan(sarima_h1) and not bool(row.get("is_reporting_anomaly", False)):
            residual_history[key] = float(compute_stage2_target(real_case_at_w, sarima_h1, mode=residual_mode))

    return pd.DataFrame(rows)


def run_direct_horizon_pilot(
    districts: list[str] | None = None,
    *,
    scope: str = "all",
    min_train_years: int = DEFAULT_MIN_TRAIN_YEARS,
    residual_mode: str | None = None,
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

    from src.module1_forecasting.rolling_one_step import _holdout_target_keys  # noqa: E402  (local import avoids a cycle at module load)

    frames = []
    for district in districts:
        target_keys = _holdout_target_keys(weekly_df, district) if scope == "holdout" else None
        logger.info("Direct-horizon pilot scoring %s (scope=%s)...", district, scope)
        frames.append(
            rolling_direct_and_recursive_district(
                district, weekly_df, sarima_configs[district], xgb_model,
                min_train_weeks=min_train_weeks, target_keys=target_keys, residual_mode=mode,
            )
        )

    result = pd.concat(frames, ignore_index=True)
    out_path = output_path or MODULE1_DIRECT_HORIZON_PILOT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    logger.info("Wrote %d direct-horizon-pilot rows to %s.", len(result), out_path)
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M1-023 direct h=2 Stage 2 pilot.")
    parser.add_argument("--districts", nargs="+", default=None, help="Districts to score (default: all).")
    parser.add_argument(
        "--scope", choices=["holdout", "all"], default="all",
        help="holdout = last 2 years per district only (fast sanity check); all = full history.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_direct_horizon_pilot(districts=args.districts, scope=args.scope)
