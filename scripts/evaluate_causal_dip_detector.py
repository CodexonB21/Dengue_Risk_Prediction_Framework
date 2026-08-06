"""M1-019 (Step 2 of the reporting-catch-up-spike scoping plan): how good is
a REAL-TIME-USABLE (causal) reporting-dip detector, compared against the
existing retrospective `is_reporting_anomaly` label as ground truth?

`reporting_anomalies.flag_reporting_anomalies()` needs the rebound week's
own value to confirm a dip was a reporting delay - unusable for a genuine
forward forecast. `flag_reporting_dip_causal()` drops that confirmation,
using only the drop itself. This script measures the resulting precision/
recall tradeoff directly: for every week the causal detector flags, was it
also confirmed by the retrospective detector (a true positive - a genuine,
subsequently-rebounding reporting delay) or not (a false positive - most
likely a genuine decline, or a drop that didn't rebound sharply enough to
confirm)?

This number alone answers whether building an adjustment on top of the
causal flag (Option A in the scoping plan) is worth attempting, or whether
only the low-risk uncertainty-flagging path (Option B) makes sense.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE1_METRICS_DIR, MODULE1_WEEKLY_MODELING_TABLE_PATH  # noqa: E402
from src.preprocessing.reporting_anomalies import flag_reporting_dip_causal  # noqa: E402

logger = logging.getLogger(__name__)

OUTPUT_PATH = MODULE1_METRICS_DIR / "causal_dip_detector_precision_recall.csv"


def evaluate() -> pd.DataFrame:
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH)
    flagged = flag_reporting_dip_causal(weekly_df)

    causal = flagged["is_reporting_dip_causal"].astype(bool)
    retrospective = flagged["is_reporting_anomaly"].astype(bool)

    tp = int((causal & retrospective).sum())
    fp = int((causal & ~retrospective).sum())
    fn = int((~causal & retrospective).sum())
    n_causal_flagged = int(causal.sum())
    n_retrospective_flagged = int(retrospective.sum())

    precision = tp / n_causal_flagged if n_causal_flagged else float("nan")
    recall = tp / n_retrospective_flagged if n_retrospective_flagged else float("nan")

    overall = pd.DataFrame([{
        "n_causal_flagged": n_causal_flagged,
        "n_retrospective_flagged": n_retrospective_flagged,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }])

    per_district = (
        flagged.assign(tp=causal & retrospective, fp=causal & ~retrospective)
        .groupby("District")
        .agg(n_causal_flagged=("is_reporting_dip_causal", "sum"), tp=("tp", "sum"), fp=("fp", "sum"))
        .reset_index()
    )
    per_district["precision"] = (per_district["tp"] / per_district["n_causal_flagged"]).round(4)

    MODULE1_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    overall.to_csv(OUTPUT_PATH, index=False)
    per_district.to_csv(OUTPUT_PATH.with_name("causal_dip_detector_precision_recall_by_district.csv"), index=False)

    logger.info("=" * 70)
    logger.info(
        "Causal dip detector: %d flagged (vs. %d retrospectively confirmed) - "
        "precision=%.1f%%, recall=%.1f%%.",
        n_causal_flagged, n_retrospective_flagged, 100 * precision, 100 * recall,
    )
    logger.info("TP=%d FP=%d FN=%d.", tp, fp, fn)
    logger.info("Wrote %s and per-district breakdown.", OUTPUT_PATH)
    return overall


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    evaluate()
