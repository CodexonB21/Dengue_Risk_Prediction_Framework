"""Evaluate M2-007A logit-residual Stage 2 vs isotonic baseline (holdout)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE2_METRICS_DIR, MODULE2_STAGE2_PREDICTIONS_PATH  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402

logger = logging.getLogger(__name__)

BASELINE_HOLDOUT_PR_AUC = 0.412
ALERT_THRESHOLD = 0.14


def _holdout_metrics(df: pd.DataFrame, architecture: str) -> dict:
    rows = df[(df["architecture"] == architecture) & (df["split"] == "holdout")]
    y_true = rows["label"].to_numpy(dtype=float)
    y_prob = rows["calibrated_probability"].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    pred_label = (y_prob >= 0.5).astype(float)
    alert_flags = y_prob >= ALERT_THRESHOLD
    return {
        "architecture": architecture,
        "pr_auc": evaluate.pr_auc(y_true, y_prob, mask=mask),
        "roc_auc": evaluate.roc_auc(y_true, y_prob, mask=mask),
        "brier_score": evaluate.brier_score(y_true, y_prob, mask=mask),
        "brier_skill_score": evaluate.brier_skill_score(y_true, y_prob, mask=mask),
        "precision_at_0.5": evaluate.precision(y_true, pred_label, mask=mask),
        "recall_at_0.5": evaluate.recall(y_true, pred_label, mask=mask),
        "f2_at_0.5": evaluate.fbeta_score(y_true, pred_label, beta=2.0, mask=mask),
        "alert_precision_at_0.14": evaluate.precision(y_true, alert_flags.astype(float), mask=mask),
        "alert_recall_at_0.14": evaluate.recall(y_true, alert_flags.astype(float), mask=mask),
        "n_obs_scored": int(mask.sum()),
    }


def run_m2_007a_evaluation(predictions_path: Path | None = None) -> pd.DataFrame:
    pred_path = predictions_path or MODULE2_STAGE2_PREDICTIONS_PATH
    preds = pd.read_csv(pred_path)

    if "logit_residual" not in preds["architecture"].unique():
        raise ValueError(
            f"No logit_residual rows in {pred_path} - rerun Stage 2 compensation first."
        )

    rows = []
    for arch in ("isotonic", "logit_residual", "stage1_raw"):
        if arch in preds["architecture"].unique():
            rows.append(_holdout_metrics(preds, arch))

    comparison = pd.DataFrame(rows)
    logit_row = comparison[comparison["architecture"] == "logit_residual"].iloc[0]
    iso_row = comparison[comparison["architecture"] == "isotonic"].iloc[0]

    accept = (
        logit_row["pr_auc"] > BASELINE_HOLDOUT_PR_AUC
        or (
            logit_row["alert_recall_at_0.14"] >= 0.65
            and logit_row["alert_precision_at_0.14"] >= 0.30
        )
    )

    summary = pd.DataFrame([{
        "variant": "m2_007_a_logit_residual",
        "holdout_pr_auc_isotonic": iso_row["pr_auc"],
        "holdout_pr_auc_logit_residual": logit_row["pr_auc"],
        "pr_auc_delta": logit_row["pr_auc"] - iso_row["pr_auc"],
        "holdout_bss_isotonic": iso_row["brier_skill_score"],
        "holdout_bss_logit_residual": logit_row["brier_skill_score"],
        "alert_recall_at_0.14_isotonic": iso_row["alert_recall_at_0.14"],
        "alert_recall_at_0.14_logit": logit_row["alert_recall_at_0.14"],
        "alert_precision_at_0.14_isotonic": iso_row["alert_precision_at_0.14"],
        "alert_precision_at_0.14_logit": logit_row["alert_precision_at_0.14"],
        "accept_criterion": accept,
    }])

    out_dir = MODULE2_METRICS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = out_dir / "m2_007_a_vs_baseline.csv"
    summary_path = out_dir / "m2_007_a_summary.csv"
    comparison.to_csv(comparison_path, index=False)
    summary.to_csv(summary_path, index=False)

    # Variant predictions artifact (holdout + validation, logit_residual only)
    variant_preds = preds[preds["architecture"] == "logit_residual"].copy()
    variant_path = PROJECT_ROOT / "data/processed/module2/stage2_compensated_predictions_m2_007_a.csv"
    variant_preds.to_csv(variant_path, index=False)

    print("=== M2-007A logit-residual vs isotonic (holdout) ===")
    print(comparison.to_string(index=False))
    print(f"\nSummary accept={accept}")
    print(f"Wrote comparison -> {comparison_path}")
    print(f"Wrote variant predictions -> {variant_path}")
    return comparison


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_m2_007a_evaluation()
