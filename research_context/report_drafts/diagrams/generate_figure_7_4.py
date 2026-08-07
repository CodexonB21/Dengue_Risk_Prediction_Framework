"""Generate Chapter 7 Figure 7.4: Module 2 reliability diagrams.

Labels the calibrated curve dynamically from `architecture` (the currently
`is_selected_architecture` row), rather than hardcoding "isotonic" - Decision
047/M2-013's Random Forest tuning flipped the official architecture to
Platt scaling, and this script previously named the wrong one."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_context" / "report_drafts" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

PRED = ROOT / "data/processed/module2/stage2_compensated_predictions.csv"
N_BINS = 10


def load_selected() -> pd.DataFrame:
    df = pd.read_csv(PRED)
    df = df[
        (df["is_selected_architecture"])
        & (~df["is_imputed"])
        & (df["label"].notna())
    ].copy()
    # Stage 2 trained rows only for calibrated curve on validation
    return df


def plot_panel(ax, y_true, p_raw, p_cal, title: str, architecture_label: str) -> None:
    ax.plot([0, 1], [0, 1], ls="--", color="#9ca3af", lw=1.2, label="Perfect calibration")
    if len(np.unique(y_true)) > 1 and len(y_true) >= N_BINS:
        frac_raw, mean_raw = calibration_curve(
            y_true, p_raw, n_bins=N_BINS, strategy="quantile"
        )
        frac_cal, mean_cal = calibration_curve(
            y_true, p_cal, n_bins=N_BINS, strategy="quantile"
        )
        ax.plot(
            mean_raw,
            frac_raw,
            marker="o",
            color="#4b5563",
            lw=1.4,
            ms=5,
            label="Stage 1 raw",
        )
        ax.plot(
            mean_cal,
            frac_cal,
            marker="o",
            color="#b45309",
            lw=1.5,
            ms=5,
            label=f"Stage 2 {architecture_label}",
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Mean observed outbreak rate")
    ax.set_title(title, loc="left", fontsize=11, fontweight="semibold")
    ax.grid(True, alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def main() -> Path:
    df = load_selected()
    # Validation: folds where Stage 2 was trained (exclude fold-1 passthrough)
    val = df[(df["split"] == "validation") & (df["stage2_trained"])]
    hold = df[df["split"] == "holdout"]
    architecture_label = str(df["architecture"].iloc[0]).capitalize() if len(df) else "Calibrated"

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8))
    plot_panel(
        axes[0],
        val["label"].to_numpy(),
        val["stage1_predicted_probability"].to_numpy(),
        val["calibrated_probability"].to_numpy(),
        "Validation (Stage 2–trained folds)",
        architecture_label,
    )
    plot_panel(
        axes[1],
        hold["label"].to_numpy(),
        hold["stage1_predicted_probability"].to_numpy(),
        hold["calibrated_probability"].to_numpy(),
        "Holdout",
        architecture_label,
    )
    axes[0].legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle(
        f"Module 2 reliability: Stage 1 raw vs {architecture_label} Stage 2",
        fontsize=12,
        y=1.02,
    )
    fig.tight_layout()
    out = OUT / "figure_7_4_module2_reliability.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print("validation rows", len(val), "positives", int(val["label"].sum()))
    print("holdout rows", len(hold), "positives", int(hold["label"].sum()))
    print("Wrote", out)
    return out


if __name__ == "__main__":
    main()
