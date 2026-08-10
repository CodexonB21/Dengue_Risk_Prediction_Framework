"""Prospective (not backtested) accuracy tracking for Module 3's forward
hotspot forecast.

Every other Module 3 evidence source - Moran's I validation, the iterative
loop's convergence, the spatial K-means CV comparison against Stage 1 alone
and against naive persistence - scores against district-weeks that are
already in the dataset (Decision 052's forward forecast has no temporal
holdout at all; see `RESEARCH_DECISIONS.md` and `MODULE_CONTEXT.md`'s
"Open Questions" section for why spatial K-means CV was used instead).
`forecast_future.run_forecast_future()`'s output is different: it predicts a
genuinely future week with NO ground truth yet, for a district-week whose
case count Module 3 has not observed. This is the same gap Module 1's
nowcast (Decision 041/M1-017) and Module 2's forward risk (Decision
048/M2-015) already had, and this module closes it the same way - by
waiting:

1. `append_to_hotspot_log()` - every `run_forecast_future()` call appends
   its forecast row(s) to a permanent, append-only log
   (`data/processed/module3/hotspot_prediction_log.csv`). Nothing is ever
   overwritten; repeat forecasts for the same target week (e.g. after a
   climate/case refresh) are all kept, each stamped with when they were
   made.
2. `reconcile_hotspot_log()` - once a logged target week's real case count
   has been reported (i.e. `baseline_risk.csv`/`master_table.csv` has a row
   for that District/Year/Week), recomputes what Stage 1's KDE baseline
   WOULD have been using the REAL total case count for that week (the same
   `compensation_model.rescale_kde_baseline()` mass-conservation every other
   Module 3 evidence source already uses), then reapplies the
   ALREADY-LOGGED `predicted_relative_residual` unchanged - Stage 2's own
   RF model only ever consumes backward-looking lag/climate/static features
   and never this week's own case count, so its prediction does not need to
   be, and should not be, recomputed. The only thing that changes between
   `Risk_forecast` and this reconciled `Risk_actual` is Stage 1's baseline,
   which isolates a genuinely useful number: how much of Module 3's
   forward-forecast error is inherited from Module 1's case-count forecast
   feeding it (`risk_0_abs_error`), versus anything else. Only rows whose
   target week has since received real case data are included in the
   output (`outputs/metrics/module3/hotspot_prospective_accuracy.csv`) -
   this table grows over real calendar time as weeks actually pass.

Run standalone (`python -m src.module3_spatial.hotspot_tracking`) to
reconcile without generating a new forecast, or call
`reconcile_hotspot_log()` from `refresh_dashboard_data.py` after each
refresh.
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
    MODULE3_BASELINE_RISK_PATH,
    MODULE3_HOTSPOT_LOG_PATH,
    MODULE3_HOTSPOT_PROSPECTIVE_ACCURACY_PATH,
    MODULE3_MASTER_TABLE_PATH,
)
from src.module3_spatial.compensation_model import rescale_kde_baseline  # noqa: E402
from src.module3_spatial.iterative_loop import SHRINKAGE_ALPHA  # noqa: E402

logger = logging.getLogger(__name__)

LOG_COLUMNS = [
    "District", "Year", "Week", "Week_Start_Date", "horizon_step",
    "Risk_0_forecast", "predicted_relative_residual", "Risk_forecast",
    "cases_forecast", "cases_source", "climate_source",
    "feature_completeness_pct", "evidence_tier", "logged_at_utc",
]


def append_to_hotspot_log(
    forecast_df: pd.DataFrame,
    *,
    logged_at: str | None = None,
    log_path: Path = MODULE3_HOTSPOT_LOG_PATH,
) -> pd.DataFrame:
    """Append this run's forecast row(s) to the permanent log.

    Unlike Module 2's forward risk log, every row `run_forecast_future()`
    produces is already a genuine forward prediction (there is no
    `observed_week`/horizon_0 pass-through row to exclude here) - so the
    whole frame is logged as-is.
    """
    logged_at = logged_at or datetime.now(timezone.utc).isoformat()
    entry = forecast_df.copy()
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
        "Appended %d rows to hotspot prediction log (%s, now %d rows total).",
        len(entry), log_path, len(combined),
    )
    return combined


def reconcile_hotspot_log(
    *,
    log_path: Path = MODULE3_HOTSPOT_LOG_PATH,
    master_table_path: Path = MODULE3_MASTER_TABLE_PATH,
    baseline_risk_path: Path = MODULE3_BASELINE_RISK_PATH,
    output_path: Path = MODULE3_HOTSPOT_PROSPECTIVE_ACCURACY_PATH,
) -> pd.DataFrame:
    """Join the prediction log against real outcomes, wherever real case
    data for a logged target week has since been reported. Strictly
    additive over time - a row that can't be resolved yet is simply absent
    from the output, never fabricated or estimated.
    """
    if not log_path.exists():
        logger.warning("No hotspot prediction log found at %s yet - nothing to reconcile.", log_path)
        return pd.DataFrame()

    log = pd.read_csv(log_path)

    master = pd.read_csv(master_table_path)[["District", "Year", "Week", "Number_of_Cases"]]
    baseline = pd.read_csv(baseline_risk_path)[["District", "Year", "Week", "KDE_baseline"]]
    # Mass-conservation is a per-week, ALL-district operation (the national
    # case total redistributed by the KDE weight profile) - rescale on the
    # full real-data table BEFORE narrowing to whichever District/Year/Week
    # combinations happen to be in the log, so a partially-logged week never
    # sees a wrong (partial-district) total.
    actuals = master.merge(baseline, on=["District", "Year", "Week"], how="inner")
    actuals = rescale_kde_baseline(actuals).rename(columns={"kde_baseline_rescaled": "Risk_0_actual"})
    actuals = actuals[["District", "Year", "Week", "Number_of_Cases", "Risk_0_actual"]]

    merged = log.merge(actuals, on=["District", "Year", "Week"], how="left")
    resolved = merged.loc[merged["Risk_0_actual"].notna()].copy()

    resolved["Risk_actual"] = np.clip(
        resolved["Risk_0_actual"]
        + SHRINKAGE_ALPHA * resolved["predicted_relative_residual"] * (resolved["Risk_0_actual"] + 1),
        0.0, None,
    )
    resolved["abs_error"] = (resolved["Risk_forecast"] - resolved["Risk_actual"]).abs()
    denom = resolved["Risk_forecast"].abs() + resolved["Risk_actual"].abs()
    resolved["smape_pct"] = np.where(denom > 0, 200 * resolved["abs_error"] / denom, 0.0)
    # Isolates how much of the forecast error is inherited from Module 1's
    # case-count forecast feeding Stage 1's KDE mass, since
    # `predicted_relative_residual` is identical in both columns by
    # construction (Stage 2 never sees this week's own case count).
    resolved["risk_0_abs_error"] = (resolved["Risk_0_forecast"] - resolved["Risk_0_actual"]).abs()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.to_csv(output_path, index=False)
    n_pending = len(log) - len(resolved)
    logger.info(
        "Reconciled %d/%d logged forecasts against real outcomes (%d still pending resolution) -> %s.",
        len(resolved), len(log), n_pending, output_path,
    )
    return resolved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    reconcile_hotspot_log()
