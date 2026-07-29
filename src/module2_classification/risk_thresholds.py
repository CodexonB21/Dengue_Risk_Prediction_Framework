"""Module 2 Stage 2 follow-up - alert threshold + low/medium/high risk tiers.

Completes Decision 022's deferred item: calibrated `predicted_probability`
was made the primary Stage 2 output, with fixed-threshold risk tiers
explicitly postponed "until Stage 2's real calibrated-probability
distribution can be inspected." That distribution now exists
(`compensation_model.py`, Platt scaling selected) - this module picks the
actual threshold values (Decision 024):

1. **Alert threshold** (binary "should this trigger an outbreak alert?"
   cutoff): argmax **F2** score (recall weighted 2x over precision) - the
   natural choice for a public-health early-warning system, where missing a
   real outbreak is costlier than an extra false alarm. Replaces the fixed,
   explicitly-untuned 0.5 cutoff used only as a diagnostic throughout
   Stage 1/2's own benchmarking.
2. **High-confidence tier boundary**: argmax **F0.5** score (precision
   weighted 2x over recall) - the natural choice for a "high confidence"
   label, where a false positive at the top tier is more costly to the
   system's credibility than at the alert tier. One consistent F-beta
   framework at two operating points, not two unrelated ad hoc rules.
3. **Fixed absolute thresholds, not quantiles** (Decision 022's own
   reasoning, reaffirmed): quantile cutoffs would force a constant fraction
   of "high risk" weeks regardless of true epidemic conditions - meaningless
   once probabilities are genuinely calibrated.
4. **Selected on validation folds 2-13 only, never the holdout.** The
   official architecture's rows in folds 2-13 are the selection population;
   fold 1's uncalibrated no-op passthrough (`architecture="none"`) is
   automatically excluded (it never has the official architecture's rows),
   and holdout is deliberately excluded so it can serve as the one honest,
   untouched check of whether the new threshold actually helps (mirrors
   every other holdout-gated decision in this project: Decisions 009, 021, 023).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH,
    MODULE2_RISK_THRESHOLD_SCAN_PATH,
    MODULE2_RISK_TIER_PREDICTIONS_PATH,
    MODULE2_STAGE2_PREDICTIONS_PATH,
)
from src.module2_classification import evaluate  # noqa: E402

logger = logging.getLogger(__name__)

TARGET_COL = "label"
CALIBRATED_PROB_COL = "calibrated_probability"
NAIVE_THRESHOLD = 0.5  # Stage 1/2's existing untuned diagnostic cutoff - kept only as a before/after comparison point.


def _official_architecture(predictions_df: pd.DataFrame) -> str:
    selected = predictions_df.loc[predictions_df["is_selected_architecture"], "architecture"]
    if selected.empty:
        raise ValueError("predictions_df has no 'is_selected_architecture' rows - has Stage 2 been run?")
    return str(selected.iloc[0])


def selection_population(predictions_df: pd.DataFrame, official_architecture: str) -> pd.DataFrame:
    """Rows eligible for threshold SELECTION: the official architecture's
    predictions on the validation split only. Fold 1's no-op passthrough
    always uses `architecture="none"`, never the official architecture, so
    it is automatically excluded here - no separate fold_id check needed.
    The holdout split is explicitly excluded too, reserved for the honest
    final check."""
    return predictions_df[
        (predictions_df["architecture"] == official_architecture) & (predictions_df["split"] == "validation")
    ]


def scan_alert_thresholds(population: pd.DataFrame) -> pd.DataFrame:
    y_true = population[TARGET_COL].to_numpy(dtype=float)
    y_prob = population[CALIBRATED_PROB_COL].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    return evaluate.threshold_scan(y_true, y_prob, mask=mask)


def select_thresholds(scan_df: pd.DataFrame) -> tuple[float, float]:
    """`alert_threshold` = argmax F2 (recall-weighted); `high_threshold` =
    argmax F0.5 (precision-weighted). Precision generally rises with
    threshold, so `high_threshold >= alert_threshold` should hold naturally
    in practice - if it doesn't (the two objectives are scanned
    independently), clip `high_threshold` up to `alert_threshold` rather than
    silently producing an incoherent tier ordering."""
    alert_threshold = float(scan_df.loc[scan_df["f2"].idxmax(), "threshold"])
    high_threshold_raw = float(scan_df.loc[scan_df["f0_5"].idxmax(), "threshold"])
    high_threshold = max(high_threshold_raw, alert_threshold)
    if high_threshold != high_threshold_raw:
        logger.warning(
            "F0.5-optimal threshold (%.3f) fell below the F2-optimal alert threshold (%.3f) - "
            "clipped up to %.3f so 'high' stays strictly above 'medium'.",
            high_threshold_raw, alert_threshold, high_threshold,
        )
    return alert_threshold, high_threshold


def assign_risk_tier(calibrated_probability: np.ndarray, alert_threshold: float, high_threshold: float) -> np.ndarray:
    proba = np.asarray(calibrated_probability, dtype=float)
    tier = np.full(proba.shape, "low", dtype=object)
    tier[proba >= alert_threshold] = "medium"
    tier[proba >= high_threshold] = "high"
    tier[np.isnan(proba)] = None
    return tier


def run_holdout_threshold_evaluation(
    predictions_df: pd.DataFrame, official_architecture: str, alert_threshold: float,
) -> pd.DataFrame:
    """Apply BOTH the new F2-optimal alert threshold and the naive 0.5
    cutoff to the untouched holdout block - the honest "did switching
    thresholds actually help" evidence, since the threshold itself was
    selected purely from validation folds 2-13."""
    holdout_rows = predictions_df[
        (predictions_df["architecture"] == official_architecture) & (predictions_df["split"] == "holdout")
    ]
    y_true = holdout_rows[TARGET_COL].to_numpy(dtype=float)
    y_prob = holdout_rows[CALIBRATED_PROB_COL].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)

    rows = []
    for name, threshold in (("naive_0.5", NAIVE_THRESHOLD), ("f2_optimal_alert", alert_threshold)):
        pred_label = (y_prob >= threshold).astype(float)
        rows.append(
            {
                "threshold_name": name,
                "threshold": threshold,
                "precision": evaluate.precision(y_true, pred_label, mask=mask),
                "recall": evaluate.recall(y_true, pred_label, mask=mask),
                "f1": evaluate.f1(y_true, pred_label, mask=mask),
                "f2": evaluate.fbeta_score(y_true, pred_label, beta=2.0, mask=mask),
                "accuracy": evaluate.accuracy(y_true, pred_label, mask=mask),
                "n_obs_scored": int(mask.sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_tier_rates(df_with_tiers: pd.DataFrame) -> pd.DataFrame:
    """For each risk tier, report `n` and the empirical observed outbreak
    rate - the actual evidence that "high" really does mean higher risk than
    "medium" than "low" (not just an assumption from the threshold values)."""
    rows = []
    valid = df_with_tiers.dropna(subset=[TARGET_COL])
    for tier in ("low", "medium", "high"):
        tier_rows = valid[valid["risk_tier"] == tier]
        rows.append(
            {
                "risk_tier": tier,
                "n": len(tier_rows),
                "observed_outbreak_rate": float(tier_rows[TARGET_COL].mean()) if len(tier_rows) else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def run_risk_threshold_pipeline() -> pd.DataFrame:
    logger.info("Loading Stage 2 calibrated predictions from %s...", MODULE2_STAGE2_PREDICTIONS_PATH)
    predictions_df = pd.read_csv(MODULE2_STAGE2_PREDICTIONS_PATH)
    official_architecture = _official_architecture(predictions_df)
    logger.info("Official Stage 2 architecture: %s", official_architecture)

    population = selection_population(predictions_df, official_architecture)
    logger.info(
        "Selecting thresholds on %d validation-fold rows (folds %s, official architecture only, holdout excluded)...",
        len(population), sorted(population["fold_id"].unique().tolist()),
    )

    scan_df = scan_alert_thresholds(population)
    alert_threshold, high_threshold = select_thresholds(scan_df)
    logger.info(
        "Selected alert_threshold=%.3f (F2-optimal, recall-weighted), high_confidence_threshold=%.3f (F0.5-optimal, precision-weighted).",
        alert_threshold, high_threshold,
    )

    MODULE2_RISK_THRESHOLD_SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    scan_df.to_csv(MODULE2_RISK_THRESHOLD_SCAN_PATH, index=False)

    holdout_comparison_df = run_holdout_threshold_evaluation(predictions_df, official_architecture, alert_threshold)
    holdout_comparison_df.to_csv(MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH, index=False)
    logger.info("Holdout threshold comparison (naive 0.5 vs. F2-optimal alert threshold):\n%s", holdout_comparison_df.to_string(index=False))

    output_df = predictions_df.copy()
    calibrated = output_df[CALIBRATED_PROB_COL].to_numpy(dtype=float)
    output_df["alert_flag"] = calibrated >= alert_threshold
    output_df["risk_tier"] = assign_risk_tier(calibrated, alert_threshold, high_threshold)

    tier_summary_validation = summarize_tier_rates(
        output_df[(output_df["architecture"] == official_architecture) & (output_df["split"] == "validation")]
    )
    tier_summary_holdout = summarize_tier_rates(
        output_df[(output_df["architecture"] == official_architecture) & (output_df["split"] == "holdout")]
    )
    logger.info("Tier summary (validation folds 2-13):\n%s", tier_summary_validation.to_string(index=False))
    logger.info("Tier summary (holdout):\n%s", tier_summary_holdout.to_string(index=False))

    MODULE2_RISK_TIER_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(MODULE2_RISK_TIER_PREDICTIONS_PATH, index=False)
    logger.info(
        "Stage 2 risk-threshold pipeline complete: alert_threshold=%.3f, high_confidence_threshold=%.3f | "
        "predictions -> %s | scan -> %s | holdout comparison -> %s",
        alert_threshold, high_threshold, MODULE2_RISK_TIER_PREDICTIONS_PATH,
        MODULE2_RISK_THRESHOLD_SCAN_PATH, MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH,
    )
    return output_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_risk_threshold_pipeline()
