"""Module 1 - Forward production forecast beyond the last available data.

Fundamentally different from everything else in `module1_forecasting/`:
`baseline_sarima.py`/`compensation_model.py`/`combine.py` all score against
data that IS already in the dataset but was held out from model
selection/training (walk-forward validation folds, the 104-week holdout
block). This script instead asks "what does the trained pipeline predict for
weeks that don't exist in the dataset at all yet?" - there is no ground
truth to check these numbers against, so they must not be treated as
equivalent evidence to the holdout MASE/DM-test results in
`combine.py`/`EXPERIMENT_LOG.md`.

Method, per district:

1. **Stage 1**: refit the district's already-SELECTED (order, seasonal_order,
   use_log1p) config (`sarima_selected_configs.csv`) on the ENTIRE available
   history (through the last case-count week in the dataset) - not a
   pre-holdout window - then forecast `FORECAST_HORIZON_WEEKS` steps beyond
   it in one shot (`fit_and_forecast`, unchanged). This is a single,
   deterministic multi-step SARIMA forecast; it does not depend on Stage 2's
   step-by-step process below.
2. **Stage 2**: features are assembled recursively, one future week at a
   time, using the ALREADY-TRAINED final production XGBoost model
   (`xgboost_final_model.json`, trained on all 14 folds + holdout - the
   maximal-data checkpoint, per `compensation_model.train_final_production_
   model`). "Recursively" means: for the first 1-2 future weeks, case-count
   lags and `residual_lag_1/2` are built from REAL historical values; for
   every week after that, this script's own prior-step `final_prediction`/
   `predicted_residual` are fed back in as if they were the real outcome -
   the standard approach for multi-step-ahead forecasting when true future
   values aren't available yet. Errors can compound with horizon; this is
   flagged per-row via `feature_completeness_pct`, not hidden.
3. **Climate features degrade to `NaN` immediately**: climate data
   (`weekly_modeling_table.csv`) is not currently available past the last
   case-count week either (see `module_1_forecasting/MODULE_CONTEXT.md`
   Open Question #16) - every climate-derived feature (raw anomaly, and any
   lag that reaches back past the climate cutoff) is `NaN` for every future
   week here. XGBoost's native missing-value handling copes numerically, but
   this is a real, honest degradation in the model's information, not a
   modeling failure - `feature_completeness_pct` quantifies it per row.

Outputs `data/processed/module1/future_forecast.csv` (all districts x
`FORECAST_HORIZON_WEEKS` weeks) and two illustrative plots
(`outputs/figures/module1/future_forecast_{Colombo,Gampaha}.png`). Every
output row carries an `evidence_tier` column (`"operational_nowcast"` for
`horizon_step == 1`, `"operational_forecast"` for later steps), mirroring
Module 2's `forecast_future_risk.py` provenance-tagging convention - this
must never be cited alongside the validated walk-forward/holdout MASE/DM
results in `combine.py`/`EXPERIMENT_LOG.md` as if it were the same kind of
evidence.

`run_nowcast()` is a thin `horizon=1` wrapper around `run_future_forecast()`
that produces the genuine "predict next week using all data up to the
current week" production output (`data/processed/module1/
nowcast_next_week.csv`). It is not an approximation: at `horizon_step == 1`
there is zero recursion anywhere in `forecast_district()` below - every
lag/rolling/anomaly feature is built from real historical values, never a
self-fed prior-step prediction - so calling `run_future_forecast(horizon=1)`
*is* the honest single-step nowcast, not a shortcut. Written to its own path
so it can never silently overwrite (or be overwritten by) the 8-week
artifact above.

**Vintage-ensembled Stage 1 for the nowcast (Decision 039/M1-015, promoted
2026-08-05 by Decision 040/M1-016).** `run_nowcast()`'s Stage 1 prediction
is no longer a single SARIMA fit - it is the average, in transformed space,
of `MODULE1_NOWCAST_ENSEMBLE_WINDOW` (default 4) independent fits, each on
`full_series` trimmed back by one additional week, each extended forward to
the SAME next-week target (`_ensembled_next_week_sarima()`). This was
validated via a full 25-district rolling one-step evaluation (Decision
039): districts with Stage 2 helping in that deployment-faithful evaluation
rose from 10/25 (single-fit) to 24/25 (ensembled), with rolling sMAPE
improving for 22/25 districts. Every vintage is fit on data strictly before
the target week - no leakage. This does NOT change Stage 2 or the additive
combination formula, and does NOT affect `run_future_forecast()`'s default
8-week recursive path (`ensemble_window` defaults to `None` there, i.e.
unchanged single-fit behavior) - only `run_nowcast()`'s horizon=1 step
uses ensembling by default. `n_sarima_vintages` is reported per row for
transparency (1 when ensembling isn't used or a vintage's fit failed and
was dropped).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    FORECAST_HORIZON_WEEKS,
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_FIGURES_DIR,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE1_NOWCAST_ENSEMBLE_WINDOW,
    MODULE1_NOWCAST_PATH,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_SARIMA_PREDICTIONS_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.baseline_sarima import fit_and_forecast  # noqa: E402
from src.module1_forecasting.compensation_model import FEATURE_COLUMNS  # noqa: E402
from src.module1_forecasting.nowcast_tracking import append_to_nowcast_log  # noqa: E402
from src.module1_forecasting.residual_transform import combine_stage2_forecast, validate_residual_mode  # noqa: E402
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    HUMIDITY_COLUMN,
    RAINFALL_COLUMN,
    REPORTING_DELAY_FEATURE_COLUMNS,
    TEMPERATURE_COLUMN,
    WEEKS_PER_YEAR,
    build_fold_agnostic_features,
)
from src.preprocessing.reporting_anomalies import REPORTING_DELAY_FEATURE_COLUMNS  # noqa: E402

logger = logging.getLogger(__name__)

# UPDATED 2026-08-10 (Decision 053): now imported from src.config, not
# locally defined - this file used to hardcode its own separate
# `FORECAST_HORIZON_WEEKS = 8` (never actually read from config.py's own
# same-named/same-value constant), exactly the "same value defined twice,
# silently able to drift" pattern already flagged as a past incident
# elsewhere in this project (Decision 047/DASHBOARD_GUIDE.md). Shortened
# from 8 to 4 weeks: `residual_lag_1/2` - the two most predictive Stage 2
# features by a wide margin (see xgboost_feature_importance.csv) - are
# already fully recursive/self-fed from horizon_step=2 onward, and a direct
# check of `future_forecast.csv` confirmed this isn't just "less confident"
# but a systematic downward bias (24/25 districts declined 8-week-out vs.
# week 1, four collapsed to exactly 0, while Stage 1/SARIMA's own baseline
# stayed essentially flat over the same span - see Decision 053). Cropping
# to 4 weeks doesn't fix the recursive bias itself (it's already partly
# visible by week 3-4), it reduces exposure to its worst effects while
# keeping a still-actionable lead time.
PLOT_DISTRICTS = ("Colombo", "Gampaha")
PLOT_HISTORY_WEEKS = 52

CLIMATE_RAW_COLUMNS = [RAINFALL_COLUMN, TEMPERATURE_COLUMN, HUMIDITY_COLUMN]
NON_DISTRICT_FEATURE_COLUMNS = [c for c in FEATURE_COLUMNS if c != "District"]


def _load_selected_configs() -> dict[str, dict]:
    cfg = pd.read_csv(MODULE1_SARIMA_CONFIG_PATH)
    configs: dict[str, dict] = {}
    for _, row in cfg.iterrows():
        configs[row["District"]] = {
            "order": (int(row["order_p"]), int(row["order_d"]), int(row["order_q"])),
            "seasonal_order": (
                int(row["seasonal_P"]), int(row["seasonal_D"]), int(row["seasonal_Q"]), int(row["seasonal_m"]),
            ),
            "use_log1p": bool(row["use_log1p"]),
        }
    return configs


def _compute_climate_norms(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """Long-term per-(District, Week) climate mean over ALL available
    history, used as the anomaly baseline (same formula as
    `feature_engineering.compute_fold_climate_anomalies`, but over the full
    dataset since there is no fold structure here)."""
    return weekly_df.groupby(["District", "Week"])[CLIMATE_RAW_COLUMNS].mean()


def _next_week(year: int, week: int) -> tuple[int, int]:
    if week >= WEEKS_PER_YEAR:
        return year + 1, 1
    return year, week + 1


# STL's own MIN_STL_OBSERVATIONS convention (2 full periods) - reused here
# as a sanity floor before trusting any SARIMA fit at all, not specific to STL.
MIN_ENSEMBLE_TRAIN_WEEKS = 2 * WEEKS_PER_YEAR


AGGREGATION_METHODS = ("mean", "median", "trimmed_mean")


def _collect_vintage_forecasts(
    full_series: pd.Series,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    use_log1p: bool,
    ensemble_window: int,
    context: str,
) -> list[float]:
    """Fit `ensemble_window` independent SARIMA models - each on
    `full_series` trimmed back by 0, 1, ..., ensemble_window-1 additional
    weeks, extended forward via `fit_and_forecast`'s own multi-step
    forecasting to reach the SAME next-week target - and return each
    vintage's forecast IN TRANSFORMED SPACE (log1p if `use_log1p`, else
    raw).

    This is the expensive part (SARIMA fitting), deliberately separated
    from `_aggregate_vintage_forecasts()`'s cheap combination logic so a
    caller comparing multiple aggregation rules (M1-018) - or the
    production ensemble itself - never needs to refit per rule.

    Mirrors `rolling_one_step._vintage_ensemble_step()`'s validated
    statistical approach (Decision 039/M1-015), adapted for a stateless
    one-off call: the rolling evaluator reused persisted fitted-model state
    across a long sequential loop, but a single nowcast invocation has no
    such history sitting around, so each vintage is refit fresh here - this
    costs `ensemble_window` SARIMA fits instead of 1, still cheap in
    absolute terms for a script that isn't run in a tight loop.
    """
    n = len(full_series)
    values_transformed: list[float] = []
    for k in range(ensemble_window):
        train_len = n - k
        if train_len < MIN_ENSEMBLE_TRAIN_WEEKS:
            continue
        trimmed = full_series.iloc[:train_len]
        horizon = k + 1  # steps needed to reach the same target as k=0's 1-step forecast
        forecast = fit_and_forecast(
            trimmed, n_periods=horizon, order=order, seasonal_order=seasonal_order,
            use_log1p=use_log1p, context=f"{context} (ensemble vintage k={k})",
        )
        target_val = float(forecast[-1])
        if np.isnan(target_val):
            continue
        values_transformed.append(np.log1p(target_val) if use_log1p else target_val)
    return values_transformed


def _aggregate_vintage_forecasts(
    values_transformed: list[float],
    use_log1p: bool,
    aggregation: str = "mean",
) -> float:
    """Combine transformed-space vintage forecasts (from
    `_collect_vintage_forecasts`) into a single raw-case-count-scale
    forecast (inverse-transformed + 0-floor clipped).

    `aggregation` (M1-018, targeting per-vintage noise - e.g. one fit
    landing oddly without technically tripping the explosive-AR-root
    guard):
    - `"mean"` (default, validated in Decision 039/M1-015): plain average.
    - `"median"`: robust to any single outlying vintage.
    - `"trimmed_mean"`: drops the single highest and lowest vintage before
      averaging the rest (falls back to plain mean with fewer than 4
      vintages, since there's nothing meaningful left to trim).
    """
    if not values_transformed:
        return float("nan")
    arr = np.asarray(values_transformed, dtype=float)
    if aggregation == "mean":
        agg = float(np.mean(arr))
    elif aggregation == "median":
        agg = float(np.median(arr))
    elif aggregation == "trimmed_mean":
        agg = float(np.mean(np.sort(arr)[1:-1])) if arr.size >= 4 else float(np.mean(arr))
    else:
        raise ValueError(f"Unknown aggregation {aggregation!r}; expected one of {AGGREGATION_METHODS}.")
    result = float(np.expm1(agg)) if use_log1p else agg
    return max(result, 0.0)


def _ensembled_next_week_sarima(
    full_series: pd.Series,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    use_log1p: bool,
    ensemble_window: int,
    context: str,
    *,
    aggregation: str = "mean",
) -> tuple[float, int]:
    """Thin wrapper: `_collect_vintage_forecasts()` then
    `_aggregate_vintage_forecasts()`. Returns `(ensembled_forecast,
    n_vintages_used)`; `n_vintages_used` may be less than `ensemble_window`
    if a trimmed window is too short or its fit fails. Returns `(nan, 0)`
    if every vintage fails.
    """
    values_transformed = _collect_vintage_forecasts(
        full_series, order, seasonal_order, use_log1p, ensemble_window, context,
    )
    result = _aggregate_vintage_forecasts(values_transformed, use_log1p, aggregation)
    return result, len(values_transformed)


def forecast_district(
    district: str,
    weekly_df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    sarima_configs: dict[str, dict],
    xgb_model: xgb.XGBRegressor,
    climate_norms: pd.DataFrame,
    horizon: int = FORECAST_HORIZON_WEEKS,
    *,
    residual_mode: str = M1_STAGE2_RESIDUAL_MODE,
    ensemble_window: int | None = None,
    aggregation: str = "mean",
    precomputed_sarima_forecast: np.ndarray | None = None,
    precomputed_n_vintages: int = 1,
) -> pd.DataFrame:
    dist_df = (
        weekly_df.loc[weekly_df["District"] == district]
        .sort_values(["Year", "Week"])
        .reset_index(drop=True)
    )
    last_year, last_week = int(dist_df["Year"].iloc[-1]), int(dist_df["Week"].iloc[-1])
    last_week_start = dist_df["Week_Start_Date"].iloc[-1]

    full_series = pd.Series(
        dist_df["Number_of_Cases"].to_numpy(dtype=float),
        index=pd.MultiIndex.from_frame(dist_df[["Year", "Week"]]),
    )
    cfg = sarima_configs[district]

    # `precomputed_sarima_forecast` (M1-018) lets a caller supply an
    # already-fitted/aggregated Stage 1 forecast directly, skipping ALL
    # fitting here - used by scripts/backtest_nowcast_ensemble.py to
    # compare several `aggregation` rules against the SAME underlying
    # vintage fits (from `_collect_vintage_forecasts`, called once) instead
    # of refitting per rule.
    step1_n_vintages = 1
    if precomputed_sarima_forecast is not None:
        sarima_forecast = precomputed_sarima_forecast
        step1_n_vintages = precomputed_n_vintages
    # Vintage-ensembled Stage 1 (Decision 039/M1-015, promoted by Decision
    # 040/M1-016) only applies to the genuine single-step nowcast
    # (horizon == 1, i.e. run_nowcast()) - the 8-week recursive path is
    # unaffected unless a caller explicitly opts in with horizon=1.
    elif ensemble_window is not None and horizon == 1:
        step1_forecast, step1_n_vintages = _ensembled_next_week_sarima(
            full_series, cfg["order"], cfg["seasonal_order"], cfg["use_log1p"], ensemble_window,
            context=f"{district} nowcast", aggregation=aggregation,
        )
        sarima_forecast = np.array([step1_forecast])
    else:
        sarima_forecast = fit_and_forecast(
            full_series,
            n_periods=horizon,
            order=cfg["order"],
            seasonal_order=cfg["seasonal_order"],
            use_log1p=cfg["use_log1p"],
            context=f"{district} future forecast (all-history refit)",
        )

    dist_resid = predictions_df.loc[predictions_df["District"] == district]
    residual_history: dict[tuple[int, int], float] = {
        (int(y), int(w)): float(r)
        for y, w, r in zip(dist_resid["Year"], dist_resid["Week"], dist_resid["residual"])
    }

    work_cols = ["District", "Year", "Week", "Number_of_Cases", "is_reporting_anomaly"] + CLIMATE_RAW_COLUMNS
    work_df = dist_df[work_cols].copy()
    all_weeks_order: list[tuple[int, int]] = list(zip(dist_df["Year"].astype(int), dist_df["Week"].astype(int)))

    year, week = last_year, last_week
    rows: list[dict] = []
    for step in range(horizon):
        year, week = _next_week(year, week)
        prev1 = all_weeks_order[-1]
        prev2 = all_weeks_order[-2]

        new_row = {
            "District": district, "Year": year, "Week": week, "Number_of_Cases": np.nan,
            "is_reporting_anomaly": False,
            RAINFALL_COLUMN: np.nan, TEMPERATURE_COLUMN: np.nan, HUMIDITY_COLUMN: np.nan,
        }
        work_df = pd.concat([work_df, pd.DataFrame([new_row])], ignore_index=True)
        feats = build_fold_agnostic_features(work_df)
        row_feats = feats.iloc[-1]

        norm = (
            climate_norms.loc[(district, week)]
            if (district, week) in climate_norms.index
            else pd.Series({c: np.nan for c in CLIMATE_RAW_COLUMNS})
        )
        rainfall_anomaly = row_feats[RAINFALL_COLUMN] - norm[RAINFALL_COLUMN]
        temperature_anomaly = row_feats[TEMPERATURE_COLUMN] - norm[TEMPERATURE_COLUMN]
        humidity_anomaly = row_feats[HUMIDITY_COLUMN] - norm[HUMIDITY_COLUMN]

        sarima_pred = float(sarima_forecast[step])
        residual_lag_1 = residual_history.get(prev1, np.nan)
        residual_lag_2 = residual_history.get(prev2, np.nan)

        feature_row = {col: row_feats[col] for col in [
            "cases_lag_1", "cases_lag_2", "cases_lag_3", "cases_lag_4",
            "rolling_mean_cases_4w", "rolling_std_cases_4w", "rate_of_change",
            "rainfall_lag_2", "rainfall_lag_3", "rainfall_lag_4", "rainfall_lag_5",
            "rainfall_lag_6", "rainfall_lag_7", "rainfall_lag_8",
            "temperature_lag_1", "temperature_lag_2", "temperature_lag_3", "temperature_lag_4",
            "humidity_lag_1", "humidity_lag_2", "humidity_lag_3", "humidity_lag_4",
            "sin_week", "cos_week", "monsoon_indicator_SW", "monsoon_indicator_NE",
            *REPORTING_DELAY_FEATURE_COLUMNS,
        ]}
        feature_row["rainfall_anomaly"] = rainfall_anomaly
        feature_row["temperature_anomaly"] = temperature_anomaly
        feature_row["humidity_anomaly"] = humidity_anomaly
        feature_row["sarima_prediction"] = sarima_pred
        feature_row["residual_lag_1"] = residual_lag_1
        feature_row["residual_lag_2"] = residual_lag_2
        feature_row["District"] = district

        X = pd.DataFrame([feature_row])[FEATURE_COLUMNS]
        X["District"] = pd.Categorical(X["District"], categories=DISTRICTS)
        predicted_residual = float(xgb_model.predict(X)[0])
        final_prediction = float(
            combine_stage2_forecast(sarima_pred, predicted_residual, mode=residual_mode)
        )

        completeness = float(pd.Series(feature_row)[NON_DISTRICT_FEATURE_COLUMNS].notna().mean())

        work_df.loc[work_df.index[-1], "Number_of_Cases"] = final_prediction
        residual_history[(year, week)] = predicted_residual
        all_weeks_order.append((year, week))

        rows.append({
            "District": district,
            "Year": year,
            "Week": week,
            "Week_Start_Date": last_week_start + pd.Timedelta(days=7 * (step + 1)),
            "horizon_step": step + 1,
            "sarima_prediction": sarima_pred,
            "predicted_residual": predicted_residual,
            "final_prediction": round(final_prediction, 1),
            "feature_completeness_pct": round(100 * completeness, 1),
            "residual_lag_1_is_recursive": step >= 1,
            "residual_lag_2_is_recursive": step >= 2,
            "n_sarima_vintages": step1_n_vintages if step == 0 else 1,
        })

    return pd.DataFrame(rows)


def run_future_forecast(
    districts: list[str] = DISTRICTS,
    horizon: int = FORECAST_HORIZON_WEEKS,
    *,
    residual_mode: str | None = None,
    output_path: Path | None = None,
    plot: bool = True,
    ensemble_window: int | None = None,
    aggregation: str = "mean",
) -> pd.DataFrame:
    mode = validate_residual_mode(residual_mode or M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    predictions_df = pd.read_csv(MODULE1_SARIMA_PREDICTIONS_PATH)
    sarima_configs = _load_selected_configs()
    climate_norms = _compute_climate_norms(weekly_df)

    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(paths["xgboost_final_model"]))

    frames = []
    for district in districts:
        logger.info("Forecasting %s forward %d weeks...", district, horizon)
        frames.append(
            forecast_district(
                district, weekly_df, predictions_df, sarima_configs, xgb_model, climate_norms, horizon,
                residual_mode=mode, ensemble_window=ensemble_window, aggregation=aggregation,
            )
        )

    result = pd.concat(frames, ignore_index=True)
    # Evidence-tier discipline (mirrors Module 2's forecast_future_risk.py):
    # horizon_step 1 uses only real historical lags (zero recursion) - the
    # honest single-step nowcast. Steps beyond 1 are self-fed and carry a
    # separate, lower-confidence tier. Neither tier is validated backtest
    # evidence; see the module docstring.
    result["evidence_tier"] = result["horizon_step"].apply(
        lambda step: "operational_nowcast" if step == 1 else "operational_forecast"
    )

    out_path = output_path or MODULE1_FUTURE_FORECAST_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    logger.info("Wrote %d forward-forecast rows to %s.", len(result), out_path)

    if plot:
        plot_future_forecast(weekly_df, result)
    return result


def run_nowcast(
    districts: list[str] = DISTRICTS,
    *,
    residual_mode: str | None = None,
    ensemble_window: int | None = MODULE1_NOWCAST_ENSEMBLE_WINDOW,
    aggregation: str = "mean",
    log_prediction: bool = True,
) -> pd.DataFrame:
    """Predict next week's case count using all data available up to now.

    Thin `horizon=1` wrapper around `run_future_forecast()` - see the module
    docstring for why this is a genuine, not approximate, single-step
    nowcast. Written to `MODULE1_NOWCAST_PATH`, distinct from the 8-week
    `future_forecast.csv`. Not wired into `main.py`'s validated pipeline
    (Decision 018) - re-run this (or `refresh_dashboard_data.py`, which calls
    it after refreshing climate) whenever new case/climate data lands.

    `ensemble_window` defaults to `MODULE1_NOWCAST_ENSEMBLE_WINDOW` (4) -
    the validated vintage-ensemble Stage 1 (Decision 039/M1-015, promoted by
    Decision 040/M1-016). Pass `None` to fall back to the original single-
    fit behavior. `aggregation` (M1-018) defaults to `"mean"` - the
    validated combination rule; `"median"`/`"trimmed_mean"` are available
    but not yet promoted (see `_aggregate_vintage_forecasts`).

    `log_prediction=True` (default, Decision 041/M1-017) appends this run's
    predictions to the permanent nowcast prediction log
    (`nowcast_tracking.append_to_nowcast_log()`) - the only source of
    genuinely prospective (not backtested) accuracy evidence for the
    nowcast, since every other Module 1 evaluation scores against data
    already in the dataset. Set `False` for one-off/exploratory calls that
    shouldn't pollute that permanent record (e.g. ad hoc testing).
    """
    result = run_future_forecast(
        districts,
        horizon=1,
        residual_mode=residual_mode,
        output_path=MODULE1_NOWCAST_PATH,
        plot=False,
        ensemble_window=ensemble_window,
        aggregation=aggregation,
    )
    if log_prediction:
        append_to_nowcast_log(result)
    return result


def plot_future_forecast(
    weekly_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    districts: tuple[str, ...] = PLOT_DISTRICTS,
    output_dir: Path = MODULE1_FIGURES_DIR,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for district in districts:
        hist = (
            weekly_df.loc[weekly_df["District"] == district]
            .sort_values(["Year", "Week"])
            .tail(PLOT_HISTORY_WEEKS)
        )
        fut = forecast_df.loc[forecast_df["District"] == district].sort_values("horizon_step")
        if hist.empty or fut.empty:
            continue

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(hist["Week_Start_Date"], hist["Number_of_Cases"], color="tab:blue", marker="o", markersize=3, label="Actual cases")
        ax.plot(fut["Week_Start_Date"], fut["final_prediction"], color="tab:red", marker="o", markersize=4, linestyle="--", label="Forward forecast (Stage 1 + Stage 2)")
        # Confidence degrades once residual_lag stops using real values (step >= 2).
        low_conf = fut.loc[fut["horizon_step"] >= 2]
        if not low_conf.empty:
            ax.axvspan(low_conf["Week_Start_Date"].iloc[0], low_conf["Week_Start_Date"].iloc[-1], color="tab:red", alpha=0.07, label="Recursive / lower-confidence weeks")
        ax.axvline(hist["Week_Start_Date"].iloc[-1], color="gray", linestyle=":", linewidth=1)
        ax.set_title(f"{district}: forward forecast beyond last available data")
        ax.set_xlabel("Week")
        ax.set_ylabel("Weekly dengue cases")
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        safe_name = district.replace(" ", "_")
        fig.savefig(output_dir / f"future_forecast_{safe_name}.png", dpi=150)
        plt.close(fig)
        logger.info("Saved forward-forecast plot for %s.", district)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 1 forward forecast / next-week nowcast.")
    parser.add_argument(
        "--nowcast", action="store_true",
        help="Run the single-step 'predict next week' nowcast (horizon=1, no plots) instead of "
             f"the default {FORECAST_HORIZON_WEEKS}-week forward forecast.",
    )
    parser.add_argument(
        "--horizon", type=int, default=FORECAST_HORIZON_WEEKS,
        help=f"Forward weeks to forecast (ignored if --nowcast is set). Default: {FORECAST_HORIZON_WEEKS}.",
    )
    parser.add_argument(
        "--ensemble-window", type=int, default=None,
        help="Override the nowcast's vintage-ensemble window (only used with --nowcast). "
             f"Default: {MODULE1_NOWCAST_ENSEMBLE_WINDOW}. Pass 0 to disable ensembling (single fit).",
    )
    parser.add_argument(
        "--no-log", action="store_true",
        help="Skip appending to the permanent nowcast prediction log (only used with --nowcast) - "
             "use for ad hoc/exploratory runs that shouldn't pollute the prospective-accuracy record.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    if args.nowcast:
        kwargs = {"log_prediction": not args.no_log}
        if args.ensemble_window is not None:
            kwargs["ensemble_window"] = args.ensemble_window or None
        run_nowcast(**kwargs)
    else:
        run_future_forecast(horizon=args.horizon)
