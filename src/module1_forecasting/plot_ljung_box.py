"""Module 1 - Ljung-Box before/after figure (Stage 1 vs Stage 1+2).

Renders a dumbbell (paired-dot) plot, one line per district per lag (26 and
52 weeks), connecting the Stage-1-only Ljung-Box p-value to the Stage-1+2
p-value - answering Decision 016's "did Stage 2 actually remove residual
autocorrelation, or just move it?" across all 25 districts, not only the 4
spot-checked by the existing ACF plots.

Data sources:
- Stage 1: `outputs/metrics/module1/sarima_walk_forward_metrics.csv`,
  `split == "validation_aggregate"` rows (`baseline_sarima.py`'s
  `run_ljung_box_diagnostics`, on Stage 1's own out-of-sample residuals).
- Stage 1+2: `outputs/metrics/module1/combined_vs_baseline_metrics.csv`,
  `model == "stage1_plus_stage2"` and `fold_id == "validation_aggregate"`
  rows (`combine.py`'s final Ljung-Box check on `actual - final_prediction`).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE1_COMBINED_METRICS_PATH,
    MODULE1_LJUNG_BOX_PLOT_PATH,
    MODULE1_SARIMA_METRICS_PATH,
)

logger = logging.getLogger(__name__)

SIGNIFICANCE_THRESHOLD = 0.05
# p-values of exactly 0.0 (float underflow from an extremely small true
# p-value) can't be plotted on a log axis - floor them for display only, and
# say so in the caption/notes rather than silently truncating the axis.
DISPLAY_FLOOR = 1e-10
LAGS = [26, 52]


def _load_stage1(lag: int) -> pd.Series:
    df = pd.read_csv(MODULE1_SARIMA_METRICS_PATH)
    df = df[df["split"] == "validation_aggregate"]
    return df.set_index("District")[f"ljung_box_pvalue_lag{lag}"]


def _load_stage12(lag: int) -> pd.Series:
    df = pd.read_csv(MODULE1_COMBINED_METRICS_PATH)
    df = df[(df["model"] == "stage1_plus_stage2") & (df["fold_id"] == "validation_aggregate")]
    return df.set_index("District")[f"ljung_box_pvalue_lag{lag}"]


def plot_ljung_box_before_after(output_path: Path = MODULE1_LJUNG_BOX_PLOT_PATH) -> None:
    stage1_52 = _load_stage1(52)
    order = stage1_52.sort_values().index.tolist()

    fig, axes = plt.subplots(1, len(LAGS), figsize=(11, 0.32 * len(order) + 1.5), sharey=True)

    for ax, lag in zip(axes, LAGS):
        s1 = _load_stage1(lag).loc[order].clip(lower=DISPLAY_FLOOR)
        s12 = _load_stage12(lag).loc[order].clip(lower=DISPLAY_FLOOR)

        for i, district in enumerate(order):
            ax.plot([s1[district], s12[district]], [i, i], color="#BDBDBD", linewidth=1, zorder=1)
        ax.scatter(s1.to_numpy(), range(len(order)), color="#C62828", s=35, zorder=2, label="Stage 1 only")
        ax.scatter(s12.to_numpy(), range(len(order)), color="#2E7D32", s=35, zorder=2, label="Stage 1+2")

        ax.axvline(SIGNIFICANCE_THRESHOLD, color="black", linestyle="--", linewidth=1, zorder=0)
        ax.set_xscale("log")
        ax.set_xlim(DISPLAY_FLOOR / 2, 1.5)
        ax.set_xlabel(f"Ljung-Box p-value, lag {lag} (log scale)")
        n_s1_sig = int((s1 < SIGNIFICANCE_THRESHOLD).sum())
        n_s12_sig = int((s12 < SIGNIFICANCE_THRESHOLD).sum())
        ax.set_title(f"Lag {lag}: {n_s1_sig}/25 -> {n_s12_sig}/25 significant", fontsize=10)
        ax.grid(axis="y", alpha=0.2)

    axes[0].set_yticks(range(len(order)))
    axes[0].set_yticklabels(order)

    fig.suptitle(
        "Ljung-Box residual autocorrelation test: Stage 1 only vs Stage 1+2\n"
        "(p < 0.05 = significant leftover autocorrelation still present)",
        fontsize=11,
    )
    handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#C62828", markersize=8, label="Stage 1 only"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#2E7D32", markersize=8, label="Stage 1+2"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.03))

    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved Ljung-Box before/after plot -> %s", output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    plot_ljung_box_before_after()
