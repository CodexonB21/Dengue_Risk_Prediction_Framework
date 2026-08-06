"""M1-012: STL + ARIMA pilot on non-seasonal districts.

Deliberately narrow pilot (3 districts, NOT a full 25-district rollout) -
see `research_context/RESEARCH_DECISIONS.md`/`EXPERIMENT_LOG.md` for the
reasoning. Compares `stl_arima.validate_stl_candidate()` (raw + log1p, same
walk-forward folds) against each district's ALREADY-SELECTED SARIMA
candidate on validation MASE. If STL+ARIMA wins for a district, the holdout
block is checked ONCE, for that district only, purely to confirm - never to
pick between candidates (Decision 009 unchanged).

Does NOT modify any production Stage 1 config, model file, or metrics CSV -
purely a research/reporting script.
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
from statsmodels.tsa.seasonal import STL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE1_FIGURES_DIR,
    MODULE1_METRICS_DIR,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_SARIMA_METRICS_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
)
from src.module1_forecasting.baseline_sarima import (  # noqa: E402
    fit_and_forecast,
    get_district_imputed_flags,
)
from src.module1_forecasting.evaluate import compute_all_metrics  # noqa: E402
from src.module1_forecasting.stl_arima import (  # noqa: E402
    WEEKS_PER_YEAR,
    fit_and_forecast_stl,
    select_stl_order,
    validate_stl_candidate,
)
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_MIN_TRAIN_YEARS,
    get_district_series,
    get_holdout_series,
)

logger = logging.getLogger(__name__)

PILOT_DISTRICTS = ("Colombo", "Gampaha", "Kurunegala")
RESULTS_PATH = MODULE1_METRICS_DIR / "stl_arima_pilot_results.csv"
DECOMPOSITION_PLOT_DISTRICT = "Colombo"
DECOMPOSITION_PLOT_PATH = MODULE1_FIGURES_DIR / "stl_decomposition_pilot_Colombo.png"


def plot_decomposition_sanity_check(series: pd.Series, district: str, output_path: Path) -> None:
    """Visual sanity check (per the plan's 'pilot before trusting the
    numbers' caution) - plot observed/trend/seasonal/resid before treating
    any walk-forward MASE number from this module as meaningful."""
    result = STL(series.to_numpy(dtype=float), period=WEEKS_PER_YEAR).fit()
    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(result.observed); axes[0].set_ylabel("Observed")
    axes[1].plot(result.trend); axes[1].set_ylabel("Trend")
    axes[2].plot(result.seasonal); axes[2].set_ylabel("Seasonal")
    axes[3].plot(result.resid); axes[3].set_ylabel("Resid")
    axes[3].set_xlabel("Week index")
    fig.suptitle(f"{district}: STL decomposition (period=52) sanity check")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved STL decomposition sanity-check plot to %s.", output_path)


def _existing_sarima_baseline(district: str, configs_df: pd.DataFrame) -> dict:
    row = configs_df.loc[configs_df["District"] == district].iloc[0]
    use_log1p = bool(row["use_log1p"])
    validation_mase = float(row["log1p_aggregate_mase"] if use_log1p else row["raw_aggregate_mase"])
    return {
        "order": (int(row["order_p"]), int(row["order_d"]), int(row["order_q"])),
        "seasonal_order": (int(row["seasonal_P"]), int(row["seasonal_D"]), int(row["seasonal_Q"]), int(row["seasonal_m"])),
        "use_log1p": use_log1p,
        "validation_mase": validation_mase,
    }


def _existing_sarima_holdout_mase(district: str, sarima_metrics_df: pd.DataFrame) -> float:
    row = sarima_metrics_df.loc[
        (sarima_metrics_df["District"] == district) & (sarima_metrics_df["fold_id"] == "holdout")
    ]
    return float(row["mase"].iloc[0]) if not row.empty else float("nan")


def run_pilot(districts: tuple[str, ...] = PILOT_DISTRICTS) -> pd.DataFrame:
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    configs_df = pd.read_csv(MODULE1_SARIMA_CONFIG_PATH)
    sarima_metrics_df = pd.read_csv(MODULE1_SARIMA_METRICS_PATH)

    rows = []
    for district in districts:
        series = get_district_series(weekly_df, district, value_col="Number_of_Cases")
        imputed = get_district_imputed_flags(weekly_df, district)
        baseline = _existing_sarima_baseline(district, configs_df)
        baseline_holdout_mase = _existing_sarima_holdout_mase(district, sarima_metrics_df)

        stl_candidates = {}
        for use_log1p in (False, True):
            order, fallback_used = select_stl_order(series, use_log1p)
            result = validate_stl_candidate(series, imputed, district, order, use_log1p)
            stl_candidates[use_log1p] = {**result, "fallback_used": fallback_used}
            logger.info(
                "%s STL+ARIMA (%s): order=%s validation MASE=%.3f",
                district, "log1p" if use_log1p else "raw", order, result["aggregate_mase"],
            )

        best_transform = min(stl_candidates, key=lambda k: (
            stl_candidates[k]["aggregate_mase"] if not np.isnan(stl_candidates[k]["aggregate_mase"]) else float("inf")
        ))
        best_stl = stl_candidates[best_transform]
        stl_wins = best_stl["aggregate_mase"] < baseline["validation_mase"]

        row = {
            "District": district,
            "existing_sarima_order": baseline["order"],
            "existing_sarima_seasonal_order": baseline["seasonal_order"],
            "existing_sarima_transform": "log1p" if baseline["use_log1p"] else "raw",
            "existing_sarima_validation_mase": baseline["validation_mase"],
            "existing_sarima_holdout_mase": baseline_holdout_mase,
            "stl_arima_order": best_stl["order"],
            "stl_arima_transform": "log1p" if best_transform else "raw",
            "stl_arima_validation_mase": best_stl["aggregate_mase"],
            "stl_wins_on_validation": bool(stl_wins),
        }

        if stl_wins:
            holdout = get_holdout_series(series, holdout_years=DEFAULT_HOLDOUT_YEARS, weeks_per_year=WEEKS_PER_YEAR)
            pre_holdout = series.iloc[: len(series) - len(holdout)]
            imputed_holdout = imputed.loc[holdout.index]
            imputed_pre_holdout = imputed.loc[pre_holdout.index]
            holdout_pred = fit_and_forecast_stl(
                pre_holdout, n_periods=len(holdout), order=best_stl["order"], use_log1p=bool(best_transform),
                context=f"{district} STL+ARIMA holdout confirmation",
            )
            holdout_metrics = compute_all_metrics(
                y_true=holdout.to_numpy(), y_pred=holdout_pred, y_train=pre_holdout.to_numpy(),
                m=WEEKS_PER_YEAR, mask=~imputed_holdout.to_numpy(), train_mask=~imputed_pre_holdout.to_numpy(),
            )
            row["stl_arima_holdout_mase"] = holdout_metrics["mase"]
            row["stl_confirmed_on_holdout"] = bool(holdout_metrics["mase"] <= baseline_holdout_mase)
            logger.info(
                "%s: STL+ARIMA WON validation (%.3f vs %.3f) - holdout check: %.3f vs existing %.3f (%s)",
                district, best_stl["aggregate_mase"], baseline["validation_mase"],
                holdout_metrics["mase"], baseline_holdout_mase,
                "CONFIRMED" if row["stl_confirmed_on_holdout"] else "NOT confirmed",
            )
        else:
            row["stl_arima_holdout_mase"] = float("nan")
            row["stl_confirmed_on_holdout"] = False
            logger.info(
                "%s: STL+ARIMA did not beat existing SARIMA on validation (%.3f vs %.3f) - no holdout check performed.",
                district, best_stl["aggregate_mase"], baseline["validation_mase"],
            )
        rows.append(row)

    result_df = pd.DataFrame(rows)
    MODULE1_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(RESULTS_PATH, index=False)
    logger.info("Wrote pilot results to %s.", RESULTS_PATH)
    return result_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    plot_decomposition_sanity_check(
        get_district_series(weekly_df, DECOMPOSITION_PLOT_DISTRICT), DECOMPOSITION_PLOT_DISTRICT, DECOMPOSITION_PLOT_PATH,
    )
    run_pilot()
