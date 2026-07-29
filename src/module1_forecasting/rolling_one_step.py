"""Module 1 - Rolling one-step-ahead operational evaluation.

Distinct from `baseline_sarima.forecast_holdout()` (fits SARIMA once on all
pre-holdout data and forecasts the entire 104-week holdout block in one
multi-step call) and from walk-forward validation folds (fixed fold
structure for model selection).

This script answers: "if we refit SARIMA each week on all data strictly
before week t and forecast only t, then apply the frozen Stage 2 XGBoost
checkpoint, how accurate are we?" — the evaluation mode closest to a
real weekly production deployment.

Uses the same district configs, XGBoost final model, and feature layout as
`compensation_model.py` / `forecast_future.py`. Case-derived features
respect `is_imputed` and `is_reporting_anomaly` masking via
`feature_engineering.build_fold_agnostic_features`.
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
    MODULE1_ROLLING_ONE_STEP_METRICS_PATH,
    MODULE1_ROLLING_ONE_STEP_PATH,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.baseline_sarima import fit_and_forecast  # noqa: E402
from src.module1_forecasting.compensation_model import FEATURE_COLUMNS  # noqa: E402
from src.module1_forecasting.evaluate import smape  # noqa: E402
from src.module1_forecasting.residual_transform import (  # noqa: E402
    combine_stage2_forecast,
    compute_stage2_target,
    validate_residual_mode,
)
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    HUMIDITY_COLUMN,
    RAINFALL_COLUMN,
    TEMPERATURE_COLUMN,
    build_fold_agnostic_features,
    compute_fold_climate_anomalies,
)
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_MIN_TRAIN_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    get_holdout_series,
)

logger = logging.getLogger(__name__)

CLIMATE_RAW_COLUMNS = [RAINFALL_COLUMN, TEMPERATURE_COLUMN, HUMIDITY_COLUMN]
FOLD_AGNOSTIC_NUMERIC = [c for c in FEATURE_COLUMNS if c not in (
    "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly",
    "sarima_prediction", "residual_lag_1", "residual_lag_2", "District",
)]


def _load_selected_configs() -> dict[str, dict]:
    cfg = pd.read_csv(MODULE1_SARIMA_CONFIG_PATH)
    configs: dict[str, dict] = {}
    for _, row in cfg.iterrows():
        configs[row["District"]] = {
            "order": (int(row["order_p"]), int(row["order_d"]), int(row["order_q"])),
            "seasonal_order": (
                int(row["seasonal_P"]), int(row["seasonal_D"]),
                int(row["seasonal_Q"]), int(row["seasonal_m"]),
            ),
            "use_log1p": bool(row["use_log1p"]),
        }
    return configs


def _week_key(year: int, week: int) -> tuple[int, int]:
    return int(year), int(week)


def rolling_one_step_district(
    district: str,
    weekly_df: pd.DataFrame,
    sarima_config: dict,
    xgb_model: xgb.XGBRegressor,
    *,
    min_train_weeks: int,
    target_keys: set[tuple[int, int]] | None,
    residual_mode: str = M1_STAGE2_RESIDUAL_MODE,
) -> pd.DataFrame:
    dist_df = (
        weekly_df.loc[weekly_df["District"] == district]
        .sort_values(["Year", "Week"])
        .reset_index(drop=True)
    )
    if len(dist_df) <= min_train_weeks:
        return pd.DataFrame()

    work_cols = ["District", "Year", "Week", "Number_of_Cases", "is_imputed", "is_reporting_anomaly"] + CLIMATE_RAW_COLUMNS
    work_cols = [c for c in work_cols if c in dist_df.columns]

    residual_history: dict[tuple[int, int], float] = {}
    rows: list[dict] = []

    for i in range(min_train_weeks, len(dist_df)):
        row = dist_df.iloc[i]
        year, week = int(row["Year"]), int(row["Week"])
        key = _week_key(year, week)
        if target_keys is not None and key not in target_keys:
            continue

        train_df = dist_df.iloc[:i]
        train_series = pd.Series(
            train_df["Number_of_Cases"].to_numpy(dtype=float),
            index=pd.MultiIndex.from_frame(train_df[["Year", "Week"]]),
        )
        sarima_pred = float(
            fit_and_forecast(
                train_series,
                n_periods=1,
                order=sarima_config["order"],
                seasonal_order=sarima_config["seasonal_order"],
                use_log1p=sarima_config["use_log1p"],
                context=f"{district} rolling 1-step {year} Wk{week}",
            )[0]
        )

        # Features for week t use history through t (current-week cases nulled).
        hist_df = dist_df.iloc[: i + 1][work_cols].copy()
        hist_df.loc[hist_df.index[-1], "Number_of_Cases"] = np.nan
        feats = build_fold_agnostic_features(hist_df)
        row_feats = feats.iloc[-1]

        train_mask = pd.Series(False, index=hist_df.index)
        train_mask.iloc[:-1] = True
        anomalies = compute_fold_climate_anomalies(hist_df, train_mask)
        anomaly_row = anomalies.iloc[-1]

        prev1 = _week_key(int(dist_df.iloc[i - 1]["Year"]), int(dist_df.iloc[i - 1]["Week"])) if i >= 1 else None
        prev2 = _week_key(int(dist_df.iloc[i - 2]["Year"]), int(dist_df.iloc[i - 2]["Week"])) if i >= 2 else None

        feature_row = {col: row_feats[col] for col in FOLD_AGNOSTIC_NUMERIC if col in row_feats.index}
        feature_row["rainfall_anomaly"] = float(anomaly_row["rainfall_anomaly"])
        feature_row["temperature_anomaly"] = float(anomaly_row["temperature_anomaly"])
        feature_row["humidity_anomaly"] = float(anomaly_row["humidity_anomaly"])
        feature_row["sarima_prediction"] = sarima_pred
        feature_row["residual_lag_1"] = residual_history.get(prev1, np.nan) if prev1 else np.nan
        feature_row["residual_lag_2"] = residual_history.get(prev2, np.nan) if prev2 else np.nan
        feature_row["District"] = district

        X = pd.DataFrame([feature_row])[FEATURE_COLUMNS]
        X["District"] = pd.Categorical(X["District"], categories=DISTRICTS)
        predicted_residual = float(xgb_model.predict(X)[0])
        final_prediction = float(
            combine_stage2_forecast(sarima_pred, predicted_residual, mode=residual_mode)
        )

        actual = float(row["Number_of_Cases"])
        if not np.isnan(sarima_pred) and not bool(row.get("is_reporting_anomaly", False)):
            residual_history[key] = float(
                compute_stage2_target(actual, sarima_pred, mode=residual_mode)
            )

        numeric_feats = pd.Series(feature_row)[FOLD_AGNOSTIC_NUMERIC + [
            "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly",
            "sarima_prediction", "residual_lag_1", "residual_lag_2",
        ]]
        completeness = float(numeric_feats.notna().mean())

        rows.append({
            "District": district,
            "Year": year,
            "Week": week,
            "Week_Start_Date": row.get("Week_Start_Date"),
            "Number_of_Cases": actual,
            "is_imputed": bool(row.get("is_imputed", False)),
            "is_reporting_anomaly": bool(row.get("is_reporting_anomaly", False)),
            "sarima_prediction": sarima_pred,
            "predicted_residual": predicted_residual,
            "final_prediction": round(final_prediction, 1),
            "feature_completeness_pct": round(100 * completeness, 1),
            "evaluation_mode": "rolling_one_step",
        })

    return pd.DataFrame(rows)


def _holdout_target_keys(weekly_df: pd.DataFrame, district: str) -> set[tuple[int, int]]:
    series = pd.Series(
        weekly_df.loc[weekly_df["District"] == district, "Number_of_Cases"].to_numpy(),
        index=pd.MultiIndex.from_frame(
            weekly_df.loc[weekly_df["District"] == district, ["Year", "Week"]]
        ),
    )
    holdout = get_holdout_series(
        series,
        holdout_years=DEFAULT_HOLDOUT_YEARS,
        weeks_per_year=DEFAULT_WEEKS_PER_YEAR,
    )
    return {_week_key(int(y), int(w)) for y, w in holdout.index}


def summarize_metrics(result: pd.DataFrame) -> pd.DataFrame:
    """Period summaries for thesis reporting (Colombo/Gampaha focus periods)."""
    if result.empty:
        return pd.DataFrame()

    scored = result[~result["is_imputed"]].copy()
    periods = [
        ("holdout_all", lambda s: pd.Series(True, index=s.index)),
        ("2026_wk22_23", lambda s: (s["Year"] == 2026) & s["Week"].isin([22, 23])),
        ("2026_wk22_25", lambda s: (s["Year"] == 2026) & s["Week"].between(22, 25)),
        ("2026_wk25_only", lambda s: (s["Year"] == 2026) & (s["Week"] == 25)),
    ]
    summary_rows = []
    for district in sorted(scored["District"].unique()):
        dist = scored[scored["District"] == district]
        for period_name, mask_fn in periods:
            sub = dist[mask_fn(dist)]
            if sub.empty:
                continue
            summary_rows.append({
                "District": district,
                "period": period_name,
                "smape_pct": round(smape(sub["Number_of_Cases"], sub["final_prediction"]), 1),
                "n_weeks": len(sub),
                "evaluation_mode": "rolling_one_step",
            })
    return pd.DataFrame(summary_rows)


def run_rolling_one_step(
    districts: list[str] | None = None,
    *,
    scope: str = "holdout",
    min_train_years: int = DEFAULT_MIN_TRAIN_YEARS,
    residual_mode: str | None = None,
) -> pd.DataFrame:
    mode = validate_residual_mode(residual_mode or M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    weekly_df = pd.read_csv(
        MODULE1_WEEKLY_MODELING_TABLE_PATH,
        parse_dates=["Week_Start_Date", "Week_End_Date"],
    )
    sarima_configs = _load_selected_configs()
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(paths["xgboost_final_model"]))

    districts = districts or DISTRICTS
    min_train_weeks = min_train_years * DEFAULT_WEEKS_PER_YEAR

    frames = []
    for district in districts:
        target_keys = _holdout_target_keys(weekly_df, district) if scope == "holdout" else None
        logger.info("Rolling 1-step scoring %s (%d target weeks)...", district, len(target_keys or []))
        frames.append(
            rolling_one_step_district(
                district,
                weekly_df,
                sarima_configs[district],
                xgb_model,
                min_train_weeks=min_train_weeks,
                target_keys=target_keys,
                residual_mode=mode,
            )
        )

    result = pd.concat(frames, ignore_index=True)
    MODULE1_ROLLING_ONE_STEP_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(MODULE1_ROLLING_ONE_STEP_PATH, index=False)

    metrics = summarize_metrics(result)
    MODULE1_ROLLING_ONE_STEP_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(MODULE1_ROLLING_ONE_STEP_METRICS_PATH, index=False)

    logger.info(
        "Wrote %d rolling 1-step rows to %s and %d summary rows to %s.",
        len(result),
        MODULE1_ROLLING_ONE_STEP_PATH,
        len(metrics),
        MODULE1_ROLLING_ONE_STEP_METRICS_PATH,
    )
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 1 rolling one-step-ahead evaluation.")
    parser.add_argument(
        "--districts", nargs="+", default=None,
        help=f"Districts to score (default: all {len(DISTRICTS)}).",
    )
    parser.add_argument(
        "--scope", choices=["holdout", "all"], default="holdout",
        help="holdout = last 2 years per district only; all = every week after min train window.",
    )
    parser.add_argument(
        "--residual-mode",
        choices=["additive", "log"],
        default=None,
        help="Stage 2 target transform (must match trained XGBoost model).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_rolling_one_step(districts=args.districts, scope=args.scope, residual_mode=args.residual_mode)
