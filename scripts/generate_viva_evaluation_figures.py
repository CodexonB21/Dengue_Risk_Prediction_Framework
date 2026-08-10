"""Generate viva-support evaluation figures for Module 2, from data that
already exists on disk (no retraining, no pipeline changes).

Produces, in outputs/figures/module2/:
  - roc_pr_curves_holdout.png   : ROC curve and PR curve side by side (holdout),
                                   with the production alert threshold (tau=0.10)
                                   marked on both.
  - confusion_matrix_holdout.png: confusion matrix at tau=0.10 (holdout).
  - harmonic_curve_examples.png : fitted seasonal (harmonic regression) curve
                                   vs. real case counts for two districts, with
                                   the mean + k*SD threshold line and labeled
                                   outbreak weeks highlighted.

Read-only with respect to the modeling pipeline: only reads
stage2_risk_tier_predictions.csv and weekly_modeling_table.csv, both already
produced by the existing pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    auc,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from src.config import (  # noqa: E402
    EPIDEMIC_THRESHOLD_K,
    MODULE2_FIGURES_DIR,
    MODULE2_RISK_TIER_PREDICTIONS_PATH,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
)
from src.module2_classification.labels import compute_epidemic_threshold_labels  # noqa: E402

ALERT_THRESHOLD = 0.10  # Production alert_flag threshold (F2-optimal, Decision 047).


def _load_holdout_predictions() -> pd.DataFrame:
    df = pd.read_csv(MODULE2_RISK_TIER_PREDICTIONS_PATH)
    holdout = df[(df["split"] == "holdout") & (df["is_selected_architecture"])].copy()
    holdout = holdout.dropna(subset=["label"])
    if holdout.empty:
        raise ValueError("No defined-label holdout rows found - check stage2_risk_tier_predictions.csv.")
    return holdout


def plot_roc_pr_curves(holdout: pd.DataFrame, output_dir: Path) -> None:
    y_true = holdout["label"].to_numpy(dtype=int)
    y_prob = holdout["calibrated_probability"].to_numpy(dtype=float)

    fpr, tpr, roc_thresh = roc_curve(y_true, y_prob)
    roc_auc = roc_auc_score(y_true, y_prob)

    precision, recall, pr_thresh = precision_recall_curve(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)
    prevalence = y_true.mean()

    # Locate the point on each curve closest to the production alert threshold.
    roc_idx = int(np.argmin(np.abs(roc_thresh - ALERT_THRESHOLD)))
    pr_idx = int(np.argmin(np.abs(pr_thresh - ALERT_THRESHOLD))) if len(pr_thresh) else 0

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    ax = axes[0]
    ax.plot(fpr, tpr, color="#1f77b4", lw=2, label=f"Module 2 (ROC-AUC = {roc_auc:.3f})")
    ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Random guessing (AUC = 0.5)")
    ax.scatter(fpr[roc_idx], tpr[roc_idx], color="red", zorder=5, label=f"tau = {ALERT_THRESHOLD:.2f}")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("Recall (True Positive Rate)")
    ax.set_title("ROC Curve (holdout)")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)

    ax = axes[1]
    ax.plot(recall, precision, color="#d62728", lw=2, label=f"Module 2 (PR-AUC = {pr_auc:.3f})")
    ax.axhline(prevalence, color="gray", lw=1, linestyle="--", label=f"No-skill baseline (prevalence = {prevalence:.3f})")
    if len(pr_thresh):
        ax.scatter(recall[pr_idx], precision[pr_idx], color="red", zorder=5, label=f"tau = {ALERT_THRESHOLD:.2f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("PR Curve (holdout)")
    ax.legend(loc="upper right", fontsize=9)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)

    fig.suptitle("Module 2 Stage 2: ROC vs. PR Curve, Holdout Block", fontsize=13)
    fig.tight_layout()
    out_path = output_dir / "roc_pr_curves_holdout.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path} (ROC-AUC={roc_auc:.4f}, PR-AUC={pr_auc:.4f}, prevalence={prevalence:.4f})")


def plot_confusion_matrix(holdout: pd.DataFrame, output_dir: Path) -> None:
    y_true = holdout["label"].to_numpy(dtype=int)
    y_pred = (holdout["calibrated_probability"].to_numpy(dtype=float) >= ALERT_THRESHOLD).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = ax.imshow(cm, cmap="Blues")
    labels = ["No Outbreak (0)", "Outbreak (1)"]
    ax.set_xticks([0, 1], labels=["Predicted: " + l for l in labels])
    ax.set_yticks([0, 1], labels=["Actual: " + l for l in labels])
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")

    names = [["TN", "FP"], ["FN", "TP"]]
    for i in range(2):
        for j in range(2):
            color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, f"{names[i][j]}\n{cm[i, j]}", ha="center", va="center", color=color, fontsize=13)

    ax.set_title(f"Confusion Matrix at tau = {ALERT_THRESHOLD:.2f} (holdout)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out_path = output_dir / "confusion_matrix_holdout.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path} (TN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}, TP={cm[1,1]})")


def plot_harmonic_curve_examples(output_dir: Path, districts: list[str]) -> None:
    df = pd.read_csv(
        MODULE2_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    labeled = compute_epidemic_threshold_labels(df)

    fig, axes = plt.subplots(len(districts), 1, figsize=(12, 5 * len(districts)), squeeze=False)
    for ax, district in zip(axes[:, 0], districts):
        sub = labeled[labeled["District"] == district].sort_values(["Year", "Week"]).reset_index(drop=True)
        sub = sub[sub["Year"] >= sub["Year"].max() - 4].reset_index(drop=True)  # last 5 years, for readability
        x = np.arange(len(sub))
        cases = sub["Number_of_Cases"].to_numpy(dtype=float)
        curve = sub["historical_mean"].to_numpy(dtype=float)
        threshold = sub["threshold"].to_numpy(dtype=float)
        is_outbreak = sub["label"].to_numpy() == 1.0

        ax.plot(x, cases, color="#1f77b4", lw=1.2, label="Actual weekly cases")
        ax.plot(x, curve, color="#2ca02c", lw=1.5, label="Harmonic seasonal curve (historical_mean)")
        ax.plot(x, threshold, color="#d62728", lw=1.2, linestyle="--",
                label=f"Threshold = mean + {EPIDEMIC_THRESHOLD_K}×SD")
        ax.scatter(x[is_outbreak], cases[is_outbreak], color="red", zorder=5, s=25, label="Labeled outbreak (label=1)")

        year_ticks = sub.groupby("Year").apply(lambda g: g.index[0]).to_numpy()
        year_labels = sorted(sub["Year"].unique())
        ax.set_xticks(year_ticks)
        ax.set_xticklabels(year_labels)
        ax.set_ylabel("Weekly case count")
        ax.set_title(f"{district}: real cases vs. harmonic curve and outbreak threshold (last 5 years)")
        ax.legend(loc="upper left", fontsize=8)

    fig.tight_layout()
    out_path = output_dir / "harmonic_curve_examples.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path} (districts: {', '.join(districts)})")


def main() -> None:
    MODULE2_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    holdout = _load_holdout_predictions()
    plot_roc_pr_curves(holdout, MODULE2_FIGURES_DIR)
    plot_confusion_matrix(holdout, MODULE2_FIGURES_DIR)
    plot_harmonic_curve_examples(MODULE2_FIGURES_DIR, districts=["Colombo", "Nuwara Eliya"])


if __name__ == "__main__":
    main()
