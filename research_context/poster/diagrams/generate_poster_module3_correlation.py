"""Poster supplement for Module 3 (2026-08-08): headline corr(Risk, Cases)
comparison across Stage 1 alone, naive persistence, and Stage 2 final.

No existing figure visualizes this specific comparison -- it previously only
appeared as a table in presentation decks. Numbers verified against
outputs/metrics/module3/results_summary.txt (M3-015, post relative-residual
reformulation) and persistence_baseline_comparison.csv.

Usage: python generate_poster_module3_correlation.py
"""
from pathlib import Path

import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent

RUST = "#D97706"
RUST_DARK = "#78350F"
GREY = "#6B7280"
INK = "#111827"


def main() -> Path:
    labels = ["Stage 1 alone\n(KDE baseline)", "Naive persistence\n(no model)", "Stage 1 + Stage 2\n(hybrid, current)"]
    corr = [0.8241, 0.9493, 0.9592]
    colors = [GREY, "#FBBF24", RUST_DARK]

    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    bars = ax.bar(labels, corr, color=colors, width=0.55)
    for bar, c in zip(bars, corr):
        ax.text(bar.get_x() + bar.get_width() / 2, c + 0.012, f"{c:.3f}",
                 ha="center", va="bottom", fontsize=12, fontweight="bold", color=INK)

    ax.set_ylim(0, 1.05)
    ax.set_ylabel("corr(Risk, Cases)")
    ax.set_title("Module 3 -- Case-Fit Comparison (spatial CV)", loc="left", fontsize=12.5, fontweight="semibold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.text(0.5, -0.16,
            "Bootstrap-confirmed win over both baselines (M3-015) -- not just an aggregate-table artifact",
            transform=ax.transAxes, ha="center", fontsize=8.5, color=GREY, style="italic")
    fig.tight_layout()

    out = OUT / "poster_figure_module3_correlation.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Wrote", out)
    return out


if __name__ == "__main__":
    main()
