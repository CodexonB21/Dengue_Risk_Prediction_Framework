"""Module 1 Stage 2 - Diebold-Mariano test significance figure.

Renders `outputs/metrics/module1/diebold_mariano_results.csv` (written by
`combine.run_combine_pipeline()`, Decision 016) as a two-panel dot plot: one
panel per DM scope (`validation_and_holdout`, `holdout_only`), districts
sorted by p-value, with a dashed line at the p=0.05 significance threshold.
Districts where Stage 2 is directionally *worse* (`mean_loss_diff <= 0`) are
marked with a distinct marker, matching the red-diamond convention already
used for Kilinochchi/Mannar in Figure 7.3.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE1_DM_TEST_PATH, MODULE1_DM_TEST_PLOT_PATH  # noqa: E402

logger = logging.getLogger(__name__)

SCOPES = [
    ("validation_and_holdout", "Validation + holdout (pooled, larger sample)"),
    ("holdout_only", "Holdout only (n=104/district, stricter)"),
]
SIGNIFICANCE_THRESHOLD = 0.05


def plot_dm_significance(
    input_path: Path = MODULE1_DM_TEST_PATH,
    output_path: Path = MODULE1_DM_TEST_PLOT_PATH,
) -> None:
    df = pd.read_csv(input_path)

    # Districts ordered by the validation_and_holdout p-value so both panels
    # use the same y-axis order for direct left-vs-right comparison.
    order = (
        df[df["scope"] == "validation_and_holdout"]
        .sort_values("p_value")["District"]
        .tolist()
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 0.32 * len(order) + 1.5), sharey=True)

    for ax, (scope, title) in zip(axes, SCOPES):
        sub = df[df["scope"] == scope].set_index("District").loc[order]
        significant = sub["p_value"] < SIGNIFICANCE_THRESHOLD
        worsened = sub["mean_loss_diff"] <= 0

        colors = significant.map({True: "#2E7D32", False: "#9E9E9E"})
        markers_sig = ~worsened
        ax.scatter(
            sub.loc[markers_sig, "p_value"], sub.index[markers_sig],
            c=colors[markers_sig], s=45, zorder=3, label=None,
        )
        ax.scatter(
            sub.loc[worsened, "p_value"], sub.index[worsened],
            c=colors[worsened], marker="D", s=45, zorder=3, edgecolors="#C62828", linewidths=1.2,
        )
        ax.axvline(SIGNIFICANCE_THRESHOLD, color="#C62828", linestyle="--", linewidth=1, zorder=1)
        ax.set_xscale("log")
        ax.set_xlabel("p-value (log scale)")
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", alpha=0.2)

    n_sig = {scope: int((df[df["scope"] == scope]["p_value"] < SIGNIFICANCE_THRESHOLD).sum()) for scope, _ in SCOPES}
    fig.suptitle(
        "Diebold-Mariano test: Stage 1 vs Stage 1+2 (Decision 016) - "
        f"{n_sig['validation_and_holdout']}/25 significant (pooled), "
        f"{n_sig['holdout_only']}/25 significant (holdout only)",
        fontsize=11,
    )

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#2E7D32", markersize=8, label="Significant (p<0.05), Stage 2 better"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#9E9E9E", markersize=8, label="Not significant, Stage 2 better"),
        plt.Line2D([0], [0], marker="D", color="w", markerfacecolor="#9E9E9E", markeredgecolor="#C62828", markersize=8, label="Not significant, Stage 2 directionally worse"),
    ]
    fig.legend(handles=legend_handles, loc="lower center", ncol=1, fontsize=8, bbox_to_anchor=(0.5, -0.06))

    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved Diebold-Mariano significance plot -> %s", output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    plot_dm_significance()
