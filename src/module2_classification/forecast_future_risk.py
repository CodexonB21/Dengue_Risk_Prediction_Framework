"""Module 2 - Forward operational risk scoring (M1-fed case lags).

Standalone script (NOT wired into ``main.py``) that scores recent observed
weeks and true forward epi-weeks beyond the last case-count week. For
multi-week-ahead rows, Module 1 ``final_prediction`` values populate case-derived
lag features when real case counts are unavailable (user-approved operational
integration — distinct from holdout-validated walk-forward evaluation).

Prerequisites::

    python -m src.module1_forecasting.forecast_future
    python -m src.module2_classification.forecast_future_risk

Output: ``data/processed/module2/future_risk_predictions.csv``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    FORECAST_HORIZON_WEEKS,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
    RAW_WEATHER_DIR,
    SHARED_CLIMATE_WEEKLY_PATH,
    SHARED_EPI_WEEK_CALENDAR_PATH,
)
from src.preprocessing.shared import (  # noqa: E402
    CLIMATE_MEAN_COLUMNS,
    CLIMATE_MODE_COLUMN,
    CLIMATE_SOURCE_COLUMN,
    CLIMATE_SUM_COLUMNS,
    district_from_weather_filename,
    load_weather_file,
)
from src.module2_classification.feature_engineering import (  # noqa: E402
    RAINFALL_COLUMN,
    TEMPERATURE_COLUMN,
    HUMIDITY_COLUMN,
    build_fold_agnostic_features,
    compute_case_anomaly_lags,
)
from src.module2_classification.scoring_utils import (  # noqa: E402
    apply_risk_tiers,
    load_production_thresholds,
    load_stage1_model,
    load_stage2_model,
    official_stage1_model,
    official_stage2_architecture,
    score_feature_rows,
)
from src.module2_classification.baseline_classifier import attach_fold_anomalies  # noqa: E402

logger = logging.getLogger(__name__)

WEEKS_PER_YEAR = 52
CLIMATE_COLS = [RAINFALL_COLUMN, TEMPERATURE_COLUMN, HUMIDITY_COLUMN]

OUTPUT_COLUMNS = [
    "District", "Year", "Week", "Week_Start_Date", "horizon_step", "prediction_type",
    "Number_of_Cases", "cases_source", "climate_source", "predicted_probability",
    "calibrated_probability", "alert_flag", "risk_tier", "feature_completeness_pct",
    "uses_module1_cases", "evidence_tier",
]


def _next_week(year: int, week: int) -> tuple[int, int]:
    if week >= WEEKS_PER_YEAR:
        return year + 1, 1
    return year, week + 1


def _load_m1_forecasts() -> pd.DataFrame:
    if not MODULE1_FUTURE_FORECAST_PATH.exists():
        raise FileNotFoundError(
            f"{MODULE1_FUTURE_FORECAST_PATH} not found - run "
            "`python -m src.module1_forecasting.forecast_future` first."
        )
    return pd.read_csv(MODULE1_FUTURE_FORECAST_PATH)


def _aggregate_daily_climate_for_range(
    daily: pd.DataFrame,
    week_start: pd.Timestamp,
    week_end: pd.Timestamp,
) -> dict:
    """Aggregate raw daily Open-Meteo rows into one epi-week (forward weeks)."""
    mask = (daily["time"] >= week_start) & (daily["time"] <= week_end)
    subset = daily.loc[mask]
    if subset.empty:
        return {}
    row: dict = {}
    for col in CLIMATE_SUM_COLUMNS:
        if col in subset.columns:
            row[col] = subset[col].sum()
    for col in CLIMATE_MEAN_COLUMNS:
        if col in subset.columns:
            row[col] = subset[col].mean()
    if CLIMATE_MODE_COLUMN in subset.columns:
        mode = subset[CLIMATE_MODE_COLUMN].mode()
        row[CLIMATE_MODE_COLUMN] = mode.iloc[0] if not mode.empty else np.nan
    if CLIMATE_SOURCE_COLUMN in subset.columns:
        filled = subset[CLIMATE_SOURCE_COLUMN].fillna("observed")
        counts = filled.value_counts()
        if len(counts) > 1 and counts.get("forecast", 0) > 0 and counts.get("observed", 0) > 0:
            row[CLIMATE_SOURCE_COLUMN] = "mixed"
        else:
            row[CLIMATE_SOURCE_COLUMN] = counts.idxmax()
    else:
        row[CLIMATE_SOURCE_COLUMN] = "observed"
    return row


def _load_district_daily_weather() -> dict[str, pd.DataFrame]:
    """Cache daily weather per district for forward-week aggregation."""
    cache: dict[str, pd.DataFrame] = {}
    for path in sorted(RAW_WEATHER_DIR.glob("open-meteo-*.csv")):
        district = district_from_weather_filename(path)
        if district in DISTRICTS:
            cache[district] = load_weather_file(path)
    return cache


def _extend_with_forward_weeks(
    modeling_df: pd.DataFrame,
    calendar: pd.DataFrame,
    climate_weekly: pd.DataFrame,
    horizon: int,
    daily_weather: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Append synthetic future epi-week rows (climate only, cases NaN)."""
    extra_rows: list[dict] = []
    for district in DISTRICTS:
        dist = modeling_df.loc[modeling_df["District"] == district].sort_values(["Year", "Week"])
        if dist.empty:
            continue
        year, week = int(dist["Year"].iloc[-1]), int(dist["Week"].iloc[-1])
        last_start = pd.Timestamp(dist["Week_Start_Date"].iloc[-1])
        last_end = pd.Timestamp(dist["Week_End_Date"].iloc[-1])
        for step in range(horizon):
            year, week = _next_week(year, week)
            cal_row = calendar.loc[(calendar["Year"] == year) & (calendar["Week"] == week)]
            if not cal_row.empty:
                week_start = pd.Timestamp(cal_row["Week_Start_Date"].iloc[0])
                week_end = pd.Timestamp(cal_row["Week_End_Date"].iloc[0])
            else:
                week_start = last_start + pd.Timedelta(days=7 * (step + 1))
                week_end = last_end + pd.Timedelta(days=7 * (step + 1))

            climate_row = climate_weekly.loc[
                (climate_weekly["District"] == district)
                & (climate_weekly["Year"] == year)
                & (climate_weekly["Week"] == week)
            ]
            row: dict = {
                "District": district,
                "Year": year,
                "Week": week,
                "Week_Start_Date": week_start,
                "Week_End_Date": week_end,
                "Number_of_Cases": np.nan,
                "is_imputed": False,
                "cases_per_100k": np.nan,
                "Estimated_Population": np.nan,
                "Source_Type": np.nan,
            }
            if not climate_row.empty:
                for col in CLIMATE_COLS:
                    row[col] = climate_row.iloc[0].get(col, np.nan)
                src = climate_row.iloc[0].get("climate_data_source", "observed")
                row["climate_data_source"] = src if pd.notna(src) else "observed"
            else:
                daily = (daily_weather or {}).get(district)
                if daily is not None:
                    agg = _aggregate_daily_climate_for_range(daily, week_start, week_end)
                    for col in CLIMATE_COLS:
                        row[col] = agg.get(col, np.nan)
                    row["climate_data_source"] = agg.get(CLIMATE_SOURCE_COLUMN, "missing")
                else:
                    for col in CLIMATE_COLS:
                        row[col] = np.nan
                    row["climate_data_source"] = "missing"
            extra_rows.append(row)

    if not extra_rows:
        return modeling_df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    extended = pd.concat([modeling_df, pd.DataFrame(extra_rows)], ignore_index=True)
    return extended.sort_values(["District", "Year", "Week"]).reset_index(drop=True)


def _cases_for_lags(extended_df: pd.DataFrame, m1_forecasts: pd.DataFrame) -> pd.Series:
    """Case series used ONLY for lag/anomaly feature construction."""
    m1 = m1_forecasts[["District", "Year", "Week", "final_prediction"]].rename(
        columns={"final_prediction": "m1_cases"}
    )
    merged = extended_df.merge(m1, on=["District", "Year", "Week"], how="left")
    cases = merged["Number_of_Cases"].copy()
    mask = cases.isna() & merged["m1_cases"].notna()
    cases.loc[mask] = merged.loc[mask, "m1_cases"]
    return cases


def _build_features_with_case_proxy(extended_df: pd.DataFrame, cases_for_lags: pd.Series) -> pd.DataFrame:
    work = extended_df.copy()
    work["_cases_for_lags"] = cases_for_lags.values
    work["Number_of_Cases_original"] = work["Number_of_Cases"]
    work["Number_of_Cases"] = work["_cases_for_lags"]

    fold_agnostic = build_fold_agnostic_features(work)
    case_anomaly = compute_case_anomaly_lags(work)
    features = fold_agnostic.merge(case_anomaly, on=["District", "Year", "Week"], how="left")
    features["Number_of_Cases"] = work["Number_of_Cases_original"].values
    return features.drop(columns=["_cases_for_lags"], errors="ignore")


def _attach_anomalies(features: pd.DataFrame) -> pd.DataFrame:
    train_mask = pd.Series(True, index=features.index)
    return attach_fold_anomalies(features, train_mask)


def _climate_source_label(row: pd.Series) -> str:
    src = row.get("climate_data_source")
    if pd.isna(src) or src in ("", "missing"):
        return "missing"
    src = str(src)
    if src == "forecast":
        return "forecast"
    if src == "observed":
        return "observed"
    return "mixed"


def _cases_source_label(row: pd.Series) -> tuple[str, bool]:
    """Label case provenance for output rows (not lag-chain internals)."""
    if pd.notna(row["Number_of_Cases"]):
        return "actual", False
    horizon = int(row["horizon_step"])
    if row.get("prediction_type") == "forward_week" and horizon >= 2:
        # M1 final_prediction feeds the synthetic lag chain from t+2 onward.
        return "module1_forecast", True
    # t+1: real historical lags only; current-week cases intentionally NaN.
    return "na", False


def run_forward_risk(horizon: int = FORECAST_HORIZON_WEEKS) -> pd.DataFrame:
    modeling_df = pd.read_csv(
        MODULE2_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    calendar = pd.read_csv(SHARED_EPI_WEEK_CALENDAR_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    climate_weekly = pd.read_csv(SHARED_CLIMATE_WEEKLY_PATH)
    m1_forecasts = _load_m1_forecasts()
    daily_weather = _load_district_daily_weather()

    extended = _extend_with_forward_weeks(
        modeling_df, calendar, climate_weekly, horizon, daily_weather=daily_weather,
    )
    cases_for_lags = _cases_for_lags(extended, m1_forecasts)
    features = _build_features_with_case_proxy(extended, cases_for_lags)
    features = _attach_anomalies(features)

    # Identify scoring targets: latest observed week (horizon 0) + forward weeks.
    targets: list[pd.DataFrame] = []
    for district in DISTRICTS:
        dist = extended.loc[extended["District"] == district].sort_values(["Year", "Week"])
        if dist.empty:
            continue
        last_real_idx = dist.index[dist["Number_of_Cases"].notna()].max()
        last_real = dist.loc[[last_real_idx]]
        last_real = last_real.assign(horizon_step=0, prediction_type="observed_week")
        targets.append(last_real)

        forward = dist.loc[dist["Number_of_Cases"].isna()].head(horizon)
        forward = forward.assign(
            horizon_step=range(1, len(forward) + 1),
            prediction_type="forward_week",
        )
        targets.append(forward)

    target_meta = pd.concat(targets, ignore_index=True)
    meta_output_cols = [
        "District", "Year", "Week", "Week_Start_Date", "horizon_step", "prediction_type",
        "Number_of_Cases",
    ]
    target_meta_out = target_meta[meta_output_cols]
    feature_subset = features.merge(
        target_meta[["District", "Year", "Week", "horizon_step", "prediction_type"]],
        on=["District", "Year", "Week"],
    )

    stage1_name = official_stage1_model()
    stage2_arch = official_stage2_architecture()
    stage1_model = load_stage1_model(stage1_name)
    stage2_model = load_stage2_model(stage2_arch)

    scored = score_feature_rows(feature_subset, stage1_model, stage1_name, stage2_model, stage2_arch)
    alert_threshold, high_threshold = load_production_thresholds()
    scored = apply_risk_tiers(scored, alert_threshold, high_threshold)

    result = target_meta_out.merge(
        scored[
            ["District", "Year", "Week", "predicted_probability", "calibrated_probability",
             "alert_flag", "risk_tier", "feature_completeness_pct"]
        ],
        on=["District", "Year", "Week"],
    )
    result = result.merge(
        extended[["District", "Year", "Week", "climate_data_source"]],
        on=["District", "Year", "Week"],
        how="left",
    )
    cases_info = result.apply(_cases_source_label, axis=1, result_type="expand")
    result["cases_source"] = cases_info[0]
    result["uses_module1_cases"] = cases_info[1]
    result["climate_source"] = result.apply(_climate_source_label, axis=1)
    result["evidence_tier"] = "operational"

    out = result[OUTPUT_COLUMNS].sort_values(["District", "horizon_step"]).reset_index(drop=True)

    MODULE2_FUTURE_RISK_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(MODULE2_FUTURE_RISK_PREDICTIONS_PATH, index=False)
    logger.info(
        "Forward risk scoring complete: %d rows (%d districts) -> %s",
        len(out), out["District"].nunique(), MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
    )
    return out


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score Module 2 forward operational outbreak risk.")
    parser.add_argument(
        "--horizon", type=int, default=FORECAST_HORIZON_WEEKS,
        help=f"Forward epi-weeks to score beyond last case week (default: {FORECAST_HORIZON_WEEKS}).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_forward_risk(horizon=args.horizon)
