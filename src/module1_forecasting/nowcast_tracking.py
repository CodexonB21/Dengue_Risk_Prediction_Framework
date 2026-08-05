"""Prospective (not backtested) accuracy tracking for the production nowcast.

Every other Module 1 evidence source - walk-forward validation, the
104-week holdout, the rolling one-step evaluator (`rolling_one_step.py`) -
scores against data that is already in the dataset, just held back from
training/selection. `forecast_future.run_nowcast()` is different: it
predicts a genuinely future week with NO ground truth yet, so none of that
machinery can validate it directly (Decision 018).

This module closes that gap the only honest way possible - by waiting:

1. `append_to_nowcast_log()` - every `run_nowcast()` call appends its
   predictions to a permanent, append-only log
   (`data/processed/module1/nowcast_prediction_log.csv`). Nothing is ever
   overwritten; repeat predictions for the same target week (e.g. if the
   nowcast is re-run after a climate refresh) are all kept, each stamped
   with when it was made.
2. `reconcile_nowcast_log()` - joins the log against
   `weekly_modeling_table.csv`'s actual case counts. Only rows whose target
   week has since received real data are included in the output
   (`outputs/metrics/module1/nowcast_prospective_accuracy.csv`) - this table
   grows over real calendar time as weeks actually pass, and is the first
   genuinely prospective accuracy evidence for M1-016's vintage-ensembled
   nowcast (or any future nowcast change).

Run standalone (`python -m src.module1_forecasting.nowcast_tracking`) to
reconcile without generating a new nowcast, or call `reconcile_nowcast_log()`
from `refresh_dashboard_data.py` after each refresh.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE1_NOWCAST_ACCURACY_PATH,
    MODULE1_NOWCAST_LOG_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
)

logger = logging.getLogger(__name__)

LOG_COLUMNS = [
    "District", "Year", "Week", "sarima_prediction", "predicted_residual",
    "final_prediction", "feature_completeness_pct", "n_sarima_vintages",
    "evidence_tier", "logged_at_utc",
]


def append_to_nowcast_log(
    nowcast_df: pd.DataFrame,
    *,
    logged_at: str | None = None,
    log_path: Path = MODULE1_NOWCAST_LOG_PATH,
) -> pd.DataFrame:
    """Append this run's nowcast predictions to the permanent log.

    Every call appends - even a repeat prediction for a target week already
    logged - so the log is a complete history of what was predicted and
    when, not just the latest guess. `n_sarima_vintages` (from Decision
    040/M1-016) travels with each row unchanged, if present.
    """
    logged_at = logged_at or datetime.now(timezone.utc).isoformat()
    entry = nowcast_df.copy()
    entry["logged_at_utc"] = logged_at
    entry = entry[[c for c in LOG_COLUMNS if c in entry.columns]]

    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        existing = pd.read_csv(log_path)
        combined = pd.concat([existing, entry], ignore_index=True)
    else:
        combined = entry
    combined.to_csv(log_path, index=False)
    logger.info("Appended %d rows to nowcast prediction log (%s, now %d rows total).",
                len(entry), log_path, len(combined))
    return combined


def reconcile_nowcast_log(
    *,
    log_path: Path = MODULE1_NOWCAST_LOG_PATH,
    weekly_table_path: Path = MODULE1_WEEKLY_MODELING_TABLE_PATH,
    output_path: Path = MODULE1_NOWCAST_ACCURACY_PATH,
) -> pd.DataFrame:
    """Join the prediction log against real outcomes, wherever real data
    for a logged target week has since appeared. Strictly additive over
    time - a row that can't be resolved yet is simply absent from the
    output, never fabricated or estimated.
    """
    if not log_path.exists():
        logger.warning("No nowcast prediction log found at %s yet - nothing to reconcile.", log_path)
        return pd.DataFrame()

    log = pd.read_csv(log_path)
    weekly_df = pd.read_csv(weekly_table_path)
    actuals = weekly_df[["District", "Year", "Week", "Number_of_Cases", "is_imputed", "is_reporting_anomaly"]]

    merged = log.merge(actuals, on=["District", "Year", "Week"], how="left")
    resolved = merged.loc[merged["Number_of_Cases"].notna()].copy()

    resolved["abs_error"] = (resolved["Number_of_Cases"] - resolved["final_prediction"]).abs()
    denom = resolved["Number_of_Cases"].abs() + resolved["final_prediction"].abs()
    resolved["smape_pct"] = np.where(denom > 0, 200 * resolved["abs_error"] / denom, 0.0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.to_csv(output_path, index=False)
    n_pending = len(log) - len(resolved)
    logger.info(
        "Reconciled %d/%d logged predictions against real outcomes (%d still pending resolution) -> %s.",
        len(resolved), len(log), n_pending, output_path,
    )
    return resolved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    reconcile_nowcast_log()
