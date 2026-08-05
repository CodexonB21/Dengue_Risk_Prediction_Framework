"""M1-018: retroactive check of the production nowcast - single-fit vs.
vintage-ensembled (mean/median/trimmed_mean) - against already-known
recent weeks.

The prediction log (`nowcast_tracking.py`, Decision 041/M1-017) only starts
accumulating genuinely prospective evidence from 2026-08-05 forward - there
is no "last week's nowcast" to look back at yet. This script answers a
different, immediately-answerable question instead: for several of the
MOST RECENT weeks that already have a known real outcome, what would
`forecast_district()` - the exact production function, not a re-
implementation - have predicted under (a) the old single fit, (b) the
vintage ensemble averaged with a plain mean (Decision 040/M1-016's
production default), (c) median, and (d) trimmed mean (M1-018) - if it had
been run right before each of those weeks?

Method: for each target week, truncate `weekly_modeling_table.csv` to end
the week before the target (so `forecast_district` believes "today" is
right before that week - identical to how it would have actually been
called then). `_collect_vintage_forecasts()` is called ONCE per
(district, week) - the expensive part - then all three aggregation rules
are computed from that SAME set of vintage fits via
`_aggregate_vintage_forecasts()` (cheap), each fed into
`forecast_district()` via `precomputed_sarima_forecast` to get a directly
comparable `final_prediction` without re-fitting per rule. All four
variants use the identical frozen Stage 2 model and feature pipeline - only
the Stage 1 SARIMA input differs.

This is a legitimate, direct verification of the deployed code on genuinely
real outcomes - a stronger check than M1-015's separate rolling-evaluator
implementation, though it covers far fewer weeks (recent weeks only, not
the full history) so should be read as a spot-check, not a replacement for
that broader evidence.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_METRICS_DIR,
    MODULE1_NOWCAST_ENSEMBLE_WINDOW,
    MODULE1_SARIMA_PREDICTIONS_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.forecast_future import (  # noqa: E402
    AGGREGATION_METHODS,
    _aggregate_vintage_forecasts,
    _collect_vintage_forecasts,
    _compute_climate_norms,
    _load_selected_configs,
    fit_and_forecast,
    forecast_district,
)
from src.module1_forecasting.residual_transform import validate_residual_mode  # noqa: E402

logger = logging.getLogger(__name__)

N_RECENT_WEEKS = 24
OUTPUT_PATH = MODULE1_METRICS_DIR / "nowcast_ensemble_recent_weeks_backtest.csv"


def run_backtest(
    districts: list[str] = DISTRICTS,
    n_recent_weeks: int = N_RECENT_WEEKS,
    ensemble_window: int = MODULE1_NOWCAST_ENSEMBLE_WINDOW,
) -> pd.DataFrame:
    mode = validate_residual_mode(M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    predictions_df = pd.read_csv(MODULE1_SARIMA_PREDICTIONS_PATH)
    sarima_configs = _load_selected_configs()
    climate_norms = _compute_climate_norms(weekly_df)

    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(paths["xgboost_final_model"]))

    rows: list[dict] = []
    for district in districts:
        dist_df = weekly_df.loc[weekly_df["District"] == district].sort_values(["Year", "Week"]).reset_index(drop=True)
        n = len(dist_df)
        cfg = sarima_configs[district]
        target_indices = range(max(n - n_recent_weeks, 0), n)

        for target_idx in target_indices:
            target_row = dist_df.iloc[target_idx]
            actual = float(target_row["Number_of_Cases"])
            if pd.isna(actual):
                continue
            year, week = int(target_row["Year"]), int(target_row["Week"])

            truncated_weekly_df = pd.concat([
                weekly_df.loc[weekly_df["District"] != district],
                dist_df.iloc[:target_idx],
            ], ignore_index=True)
            full_series = pd.Series(
                dist_df["Number_of_Cases"].iloc[:target_idx].to_numpy(dtype=float),
                index=pd.MultiIndex.from_frame(dist_df[["Year", "Week"]].iloc[:target_idx]),
            )

            # Single fit (Decision 018's original nowcast behavior).
            single_forecast = fit_and_forecast(
                full_series, n_periods=1, order=cfg["order"], seasonal_order=cfg["seasonal_order"],
                use_log1p=cfg["use_log1p"], context=f"{district} backtest single {year}Wk{week}",
            )
            single = forecast_district(
                district, truncated_weekly_df, predictions_df, sarima_configs, xgb_model, climate_norms,
                horizon=1, residual_mode=mode, precomputed_sarima_forecast=single_forecast, precomputed_n_vintages=1,
            ).iloc[0]

            # Vintage fits collected ONCE, reused across all aggregation rules.
            vintages = _collect_vintage_forecasts(
                full_series, cfg["order"], cfg["seasonal_order"], cfg["use_log1p"], ensemble_window,
                context=f"{district} backtest ensemble {year}Wk{week}",
            )

            row = {
                "District": district, "Year": year, "Week": week, "actual": actual,
                "is_reporting_anomaly": bool(target_row.get("is_reporting_anomaly", False)),
                "n_sarima_vintages": len(vintages),
                "single_sarima": single["sarima_prediction"], "single_final": single["final_prediction"],
                "single_abs_error": abs(actual - single["final_prediction"]),
            }
            for agg in AGGREGATION_METHODS:
                agg_forecast = _aggregate_vintage_forecasts(vintages, cfg["use_log1p"], agg)
                agg_result = forecast_district(
                    district, truncated_weekly_df, predictions_df, sarima_configs, xgb_model, climate_norms,
                    horizon=1, residual_mode=mode,
                    precomputed_sarima_forecast=np.array([agg_forecast]), precomputed_n_vintages=len(vintages),
                ).iloc[0]
                row[f"{agg}_sarima"] = agg_result["sarima_prediction"]
                row[f"{agg}_final"] = agg_result["final_prediction"]
                row[f"{agg}_abs_error"] = abs(actual - agg_result["final_prediction"])
            rows.append(row)
        logger.info("Done %s (%d target weeks).", district, len(target_indices))

    result = pd.DataFrame(rows)
    MODULE1_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    logger.info("=" * 70)
    logger.info("Retroactive check on %d (district, week) pairs (single-fit baseline):", len(result))
    logger.info("  single-fit:   median=%.2f mean=%.2f", result["single_abs_error"].median(), result["single_abs_error"].mean())
    for agg in AGGREGATION_METHODS:
        col = f"{agg}_abs_error"
        n_better = int((result[col] < result["single_abs_error"]).sum())
        n_worse = int((result[col] > result["single_abs_error"]).sum())
        logger.info(
            "  %-13s median=%.2f mean=%.2f | better=%d worse=%d tied=%d (vs single-fit)",
            agg + ":", result[col].median(), result[col].mean(), n_better, n_worse,
            len(result) - n_better - n_worse,
        )
    logger.info("Wrote %d rows to %s.", len(result), OUTPUT_PATH)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_backtest()
