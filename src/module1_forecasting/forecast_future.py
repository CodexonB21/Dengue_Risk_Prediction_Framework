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
(`outputs/figures/module1/future_forecast_{Colombo,Gampaha}.png`).
"""

from __future__ import annotations

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
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_FIGURES_DIR,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_SARIMA_PREDICTIONS_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.baseline_sarima import fit_and_forecast  # noqa: E402
from src.module1_forecasting.compensation_model import FEATURE_COLUMNS  # noqa: E402
from src.module1_forecasting.residual_transform import combine_stage2_forecast, validate_residual_mode  # noqa: E402
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    HUMIDITY_COLUMN,
    RAINFALL_COLUMN,
    TEMPERATURE_COLUMN,
    WEEKS_PER_YEAR,
    build_fold_agnostic_features,
)

logger = logging.getLogger(__name__)

# 8 weeks ~ 2 months beyond the last available week. Deliberately not longer:
# residual_lag_1/2 - the two most predictive Stage 2 features by a wide
# margin (see xgboost_feature_importance.csv) - are already fully
# recursive/self-fed by week 3 of the horizon, so confidence keeps degrading
# with every additional week; going further wouldn't add a meaningfully
# different story, just a longer tail of low-confidence numbers.
FORECAST_HORIZON_WEEKS = 8
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

    work_cols = ["District", "Year", "Week", "Number_of_Cases"] + CLIMATE_RAW_COLUMNS
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
        })

    return pd.DataFrame(rows)


def run_future_forecast(
    districts: list[str] = DISTRICTS,
    horizon: int = FORECAST_HORIZON_WEEKS,
    *,
    residual_mode: str | None = None,
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
                residual_mode=mode,
            )
        )

    result = pd.concat(frames, ignore_index=True)
    MODULE1_FUTURE_FORECAST_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(MODULE1_FUTURE_FORECAST_PATH, index=False)
    logger.info("Wrote %d forward-forecast rows to %s.", len(result), MODULE1_FUTURE_FORECAST_PATH)

    plot_future_forecast(weekly_df, result)
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_future_forecast()
