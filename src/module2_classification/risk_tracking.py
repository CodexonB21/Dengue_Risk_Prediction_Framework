"""Prospective (not backtested) accuracy tracking for Module 2's forward
risk scoring.

Every other Module 2 evidence source - walk-forward validation, the 2-year
holdout, live scoring of already-observed recent weeks - scores against data
that is already in the dataset, just held back from training/selection.
`forecast_future_risk.run_forward_risk()`'s genuinely future rows
(`prediction_type == "forward_week"`) are different: they predict a week
with NO ground truth yet, so none of that machinery can validate them
directly. This is the same gap Module 1's nowcast had before Decision
041/M1-017's `nowcast_tracking.py`, and this module closes it the same way -
by waiting:

1. `append_to_risk_log()` - every `run_forward_risk()` call appends its
   genuinely-forward rows to a permanent, append-only log
   (`data/processed/module2/risk_prediction_log.csv`). Nothing is ever
   overwritten; repeat predictions for the same target week (e.g. if forward
   scoring is re-run after a climate refresh) are all kept, each stamped
   with when it was made. The already-resolved `observed_week` row
   (horizon_step=0) is deliberately excluded - it already has ground truth
   at logging time, so it is not a prospective prediction and would dilute
   this log's purpose.
2. `reconcile_risk_log()` - recomputes the actual epidemic-threshold label
   (same `labels.compute_epidemic_threshold_labels()` used everywhere else in
   Module 2) from the current `weekly_modeling_table.csv`, and joins it
   against the log. Only rows whose target week has since received real
   case data AND has a defined label are included in the output
   (`outputs/metrics/module2/risk_prospective_accuracy.csv`) - this table
   grows over real calendar time as weeks actually pass and is the first
   genuinely prospective accuracy evidence for Module 2's production stack
   (or any future Stage 1/Stage 2 change).

Run standalone (`python -m src.module2_classification.risk_tracking`) to
reconcile without generating new forward predictions, or call
`reconcile_risk_log()` from `refresh_dashboard_data.py` after each refresh.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE2_RISK_LOG_PATH,
    MODULE2_RISK_PROSPECTIVE_ACCURACY_PATH,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
)
from src.module2_classification.labels import compute_epidemic_threshold_labels  # noqa: E402

logger = logging.getLogger(__name__)

LOG_COLUMNS = [
    "District", "Year", "Week", "Week_Start_Date", "horizon_step", "prediction_type",
    "predicted_probability", "calibrated_probability", "alert_flag", "risk_tier",
    "feature_completeness_pct", "cases_source", "climate_source", "uses_module1_cases",
    "evidence_tier", "logged_at_utc",
]


def append_to_risk_log(
    forward_df: pd.DataFrame,
    *,
    logged_at: str | None = None,
    log_path: Path = MODULE2_RISK_LOG_PATH,
) -> pd.DataFrame:
    """Append this run's genuinely-forward risk rows to the permanent log.

    Only `prediction_type == "forward_week"` rows are logged - the
    `observed_week` row (horizon_step=0) already has ground truth when
    scored, so it is not a prospective prediction. Every call appends, even
    a repeat prediction for a target week already logged, so the log is a
    complete history of what was predicted and when, not just the latest
    guess.
    """
    logged_at = logged_at or datetime.now(timezone.utc).isoformat()
    entry = forward_df.loc[forward_df["prediction_type"] == "forward_week"].copy()
    entry["logged_at_utc"] = logged_at
    entry = entry[[c for c in LOG_COLUMNS if c in entry.columns]]

    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        existing = pd.read_csv(log_path)
        combined = pd.concat([existing, entry], ignore_index=True)
    else:
        combined = entry
    combined.to_csv(log_path, index=False)
    logger.info(
        "Appended %d forward-week rows to risk prediction log (%s, now %d rows total).",
        len(entry), log_path, len(combined),
    )
    return combined


def reconcile_risk_log(
    *,
    log_path: Path = MODULE2_RISK_LOG_PATH,
    weekly_table_path: Path = MODULE2_WEEKLY_MODELING_TABLE_PATH,
    output_path: Path = MODULE2_RISK_PROSPECTIVE_ACCURACY_PATH,
) -> pd.DataFrame:
    """Join the prediction log against real outcomes, wherever real data for
    a logged target week has since appeared. Strictly additive over time - a
    row that can't be resolved yet (either the week hasn't passed, or it has
    but doesn't yet have enough prior-year history for a defined label) is
    simply absent from the output, never fabricated or estimated.
    """
    if not log_path.exists():
        logger.warning("No risk prediction log found at %s yet - nothing to reconcile.", log_path)
        return pd.DataFrame()

    log = pd.read_csv(log_path)
    weekly_df = pd.read_csv(weekly_table_path, parse_dates=["Week_Start_Date", "Week_End_Date"])
    labeled = compute_epidemic_threshold_labels(weekly_df)
    actuals = labeled[
        ["District", "Year", "Week", "Number_of_Cases", "is_imputed", "is_reporting_anomaly", "label"]
    ].rename(columns={"label": "actual_label"})

    merged = log.merge(actuals, on=["District", "Year", "Week"], how="left")
    resolved = merged.loc[merged["Number_of_Cases"].notna() & merged["actual_label"].notna()].copy()

    resolved["alert_correct"] = (resolved["alert_flag"].astype(bool)) == (resolved["actual_label"] == 1.0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.to_csv(output_path, index=False)
    n_pending = len(log) - len(resolved)
    logger.info(
        "Reconciled %d/%d logged forward predictions against real outcomes "
        "(%d still pending resolution) -> %s.",
        len(resolved), len(log), n_pending, output_path,
    )
    return resolved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    reconcile_risk_log()
