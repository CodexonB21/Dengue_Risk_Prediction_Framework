"""Poster supplement for Module 2 (2026-08-08): alert utility + risk-tier
separation, holdout split, current production architecture (tuned Random
Forest -> Platt scaling, Decision 047/M2-013).

These two claims have no existing figure anywhere in the repo -- only the
calibration story (reliability diagram) was previously illustrated. Numbers
verified against:
  - outputs/metrics/module2/risk_threshold_holdout_comparison.csv
    (naive_0.5 vs f2_optimal_alert rows)
  - research_context/report_drafts/chapter7_7.4_module2_v2.md, Section 7.4.4
    (risk-tier holdout rates + small-n caveat: medium n=49, high n=24)

Usage: python generate_poster_module2_supplement.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent

NAVY = "#1E3A8A"
STEEL = "#2563EB"
STEEL_FILL = "#DBEAFE"
GREY = "#6B7280"
INK = "#111827"


def plot_alert_utility(ax):
    rules = ["Naive 0.5 cutoff", "Calibrated τ = 0.10"]
    recall = [0.375, 0.625]
    f2 = [0.4076, 0.5365]

    x = np.arange(len(rules))
    w = 0.32
    b1 = ax.bar(x - w / 2, recall, w, label="Recall", color=GREY)
    b2 = ax.bar(x + w / 2, f2, w, label="F2 score", color=STEEL)

    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.015, f"{h:.1%}" if h < 1 else f"{h:.2f}",
                     ha="center", va="bottom", fontsize=9.5, color=INK)

    ax.set_xticks(x)
    ax.set_xticklabels(rules, fontsize=10.5)
    ax.set_ylim(0, 0.78)
    ax.set_ylabel("Holdout score")
    ax.set_title("Alert utility (holdout, n=2,600)", loc="left", fontsize=11, fontweight="semibold")
    ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def plot_risk_tiers(ax):
    tiers = ["Low\n(n=2,527)", "Medium\n(n=49)", "High\n(n=24)"]
    rates = [0.006, 0.204, 0.625]
    colors = ["#93C5FD", "#3B82F6", NAVY]

    bars = ax.bar(tiers, rates, color=colors, width=0.55)
    for bar, r in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, r + 0.02, f"{r:.1%}",
                 ha="center", va="bottom", fontsize=10.5, fontweight="bold", color=INK)

    ax.set_ylim(0, 0.78)
    ax.set_ylabel("Observed outbreak rate")
    ax.set_title("Risk-tier separation (holdout)", loc="left", fontsize=11, fontweight="semibold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.text(0.5, -0.24, "Medium/high tiers have small holdout counts -- read exact % with sampling caution",
            transform=ax.transAxes, ha="center", fontsize=8, color=GREY, style="italic")


def main() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    plot_alert_utility(axes[0])
    plot_risk_tiers(axes[1])
    fig.suptitle("Module 2 -- Alert Utility and Risk-Tier Separation (Platt-scaled, current production stack)",
                 fontsize=12, y=1.03)
    fig.tight_layout()
    out = OUT / "poster_figure_module2_alert_tiers.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Wrote", out)
    return out


if __name__ == "__main__":
    main()
