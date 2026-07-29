"""Evaluate M2-007D M1-fed Stage 2 features vs isotonic baseline."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE2_METRICS_DIR, MODULE2_STAGE2_PREDICTIONS_PATH, module2_stage2_paths  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402

BASELINE_ISOTONIC_PR_AUC = 0.412
ALERT_THRESHOLD = 0.14


def _holdout_row(df: pd.DataFrame, architecture: str) -> dict:
    rows = df[(df["architecture"] == architecture) & (df["split"] == "holdout")]
    y_true = rows["label"].to_numpy(dtype=float)
    y_prob = rows["calibrated_probability"].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    alert = y_prob >= ALERT_THRESHOLD
    return {
        "architecture": architecture,
        "pr_auc": evaluate.pr_auc(y_true, y_prob, mask=mask),
        "roc_auc": evaluate.roc_auc(y_true, y_prob, mask=mask),
        "brier_skill_score": evaluate.brier_skill_score(y_true, y_prob, mask=mask),
        "alert_recall_at_0.14": evaluate.recall(y_true, alert.astype(float), mask=mask),
        "alert_precision_at_0.14": evaluate.precision(y_true, alert.astype(float), mask=mask),
        "n_obs_scored": int(mask.sum()),
    }


def _slice_pr_auc(df: pd.DataFrame, architecture: str, year: int, week_min: int, week_max: int) -> float:
    rows = df[
        (df["architecture"] == architecture)
        & (df["split"] == "holdout")
        & (df["Year"] == year)
        & (df["Week"].between(week_min, week_max))
    ]
    y_true = rows["label"].to_numpy(dtype=float)
    y_prob = rows["calibrated_probability"].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    return evaluate.pr_auc(y_true, y_prob, mask=mask)


def run_m2_007d_evaluation(
    variant_predictions_path: Path | None = None,
    baseline_predictions_path: Path | None = None,
) -> pd.DataFrame:
    baseline_path = baseline_predictions_path or MODULE2_STAGE2_PREDICTIONS_PATH
    variant_path = variant_predictions_path or module2_stage2_paths("m2_007_d")["predictions"]

    baseline = pd.read_csv(baseline_path)
    variant = pd.read_csv(variant_path)

    rows = [_holdout_row(baseline, "isotonic")]
    for arch in ("stacked_xgboost", "logit_residual"):
        if arch in variant["architecture"].unique():
            rows.append(_holdout_row(variant, arch))

    comparison = pd.DataFrame(rows)

    iso_row = comparison[comparison["architecture"] == "isotonic"].iloc[0]
    best_tree = comparison[comparison["architecture"] != "isotonic"]
    best_arch = None
    best_pr = -1.0
    if not best_tree.empty:
        best_idx = best_tree["pr_auc"].idxmax()
        best_arch = str(best_tree.loc[best_idx, "architecture"])
        best_pr = float(best_tree.loc[best_idx, "pr_auc"])

    slice_iso = _slice_pr_auc(baseline, "isotonic", 2026, 20, 25)
    slice_best = float("nan")
    if best_arch:
        slice_best = _slice_pr_auc(variant, best_arch, 2026, 20, 25)

    accept = False
    if best_arch:
        best_row = best_tree.loc[best_tree["architecture"] == best_arch].iloc[0]
        accept = (
            best_row["pr_auc"] >= BASELINE_ISOTONIC_PR_AUC + 0.02
            or (
                best_row["alert_recall_at_0.14"] >= iso_row["alert_recall_at_0.14"] + 0.05
                and best_row["alert_precision_at_0.14"] >= 0.25
            )
        )

    summary = pd.DataFrame([{
        "variant": "m2_007_d",
        "baseline_isotonic_pr_auc": iso_row["pr_auc"],
        "best_tree_architecture": best_arch,
        "best_tree_pr_auc": best_pr,
        "pr_auc_delta_vs_isotonic": best_pr - iso_row["pr_auc"] if best_arch else np.nan,
        "baseline_alert_recall_at_0.14": iso_row["alert_recall_at_0.14"],
        "best_tree_alert_recall_at_0.14": best_row["alert_recall_at_0.14"] if best_arch else np.nan,
        "holdout_pr_auc_slice_2026_wk20_25_isotonic": slice_iso,
        "holdout_pr_auc_slice_2026_wk20_25_best_tree": slice_best,
        "accept_criterion": accept,
    }])

    out_dir = MODULE2_METRICS_DIR
    comparison_path = out_dir / "m2_007_d_vs_baseline.csv"
    summary_path = out_dir / "m2_007_d_summary.csv"
    comparison.to_csv(comparison_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("=== M2-007D M1-fed features vs isotonic baseline (holdout) ===")
    print(comparison.to_string(index=False))
    print(f"\nSummary accept={accept}")
    print(f"Wrote {comparison_path}")
    return comparison


if __name__ == "__main__":
    run_m2_007d_evaluation()
