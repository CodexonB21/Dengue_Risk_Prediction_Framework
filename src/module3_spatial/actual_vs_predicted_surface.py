"""Ad-hoc visualization: actual case-count surface vs. predicted Hybrid Risk
surface, side by side, for one week. Not part of the official Stage 1/Stage 2
pipeline and not referenced by `MODULE_CONTEXT.md` - a one-off comparison
figure reusing `risk_surface.py`'s already-validated kNN-IDW interpolation
(k=4, power=4) unchanged, applied to two different value columns
(`Number_of_Cases` vs. `Risk`) on the SAME grid/district coordinates so the
two panels are directly comparable.

Both panels share one color scale (vmin=0, vmax = the max of either surface)
- required for an honest visual comparison; two independently-scaled panels
would let a low-case week LOOK as "hot" as a high-case week, which is exactly
the kind of implied-second-scale distortion a side-by-side comparison must
avoid.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DISTRICTS, MODULE3_FIGURES_DIR, MODULE3_HYBRID_RISK_MAP_PATH  # noqa: E402
from src.module3_spatial.kde_baseline import (  # noqa: E402
    district_centroid_coords,
    load_district_boundaries,
    select_representative_weeks,
)
from src.module3_spatial.risk_surface import (  # noqa: E402
    DEFAULT_RESOLUTION_M,
    build_evaluation_grid,
    evaluate_risk_surface,
)

logger = logging.getLogger(__name__)

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_MUTED = "#898781"
BASELINE = "#c3c2b7"
LABELED_DISTRICTS = ("Colombo", "Gampaha", "Kalutara")


def _panel(ax, xx, yy, mask, values_col, vmax, boundaries, title):
    grid = np.full(xx.shape, np.nan)
    grid[mask] = values_col
    mesh = ax.pcolormesh(xx, yy, grid, cmap="YlOrRd", shading="auto", vmin=0, vmax=vmax)
    boundaries.boundary.plot(ax=ax, color=BASELINE, linewidth=0.6)
    for _, row in boundaries.iterrows():
        if row["District"] in LABELED_DISTRICTS:
            c = row.geometry.centroid
            ax.annotate(
                row["District"], (c.x, c.y), color=INK_PRIMARY, fontsize=9, fontweight="bold",
                ha="center", path_effects=[pe.withStroke(linewidth=2.5, foreground=SURFACE)],
            )
    ax.set_axis_off()
    ax.set_aspect("equal")
    ax.set_title(title, color=INK_PRIMARY, fontsize=12)
    return mesh


def run_actual_vs_predicted(year: int | None = None, week: int | None = None) -> Path:
    MODULE3_FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    hybrid_risk = pd.read_csv(MODULE3_HYBRID_RISK_MAP_PATH)
    if year is None or week is None:
        from src.config import MODULE3_BASELINE_RISK_PATH
        kde_baseline = pd.read_csv(MODULE3_BASELINE_RISK_PATH)
        year, week = select_representative_weeks(kde_baseline)["peak"]

    week_df = hybrid_risk[(hybrid_risk["Year"] == year) & (hybrid_risk["Week"] == week)].set_index("District")
    week_df = week_df.reindex(DISTRICTS)
    if week_df.isna().any().any():
        raise ValueError(f"Missing districts for Year={year} Week={week} after reindexing.")

    boundaries = load_district_boundaries()
    district_coords = district_centroid_coords(boundaries)
    xx, yy, mask, grid_coords = build_evaluation_grid(boundaries, DEFAULT_RESOLUTION_M)

    actual_values = week_df["Number_of_Cases"].to_numpy(dtype=float)
    predicted_values = week_df["Risk"].to_numpy(dtype=float)

    actual_surface = evaluate_risk_surface(grid_coords, district_coords, actual_values)
    predicted_surface = evaluate_risk_surface(grid_coords, district_coords, predicted_values)

    vmax = max(actual_surface.max(), predicted_surface.max())

    fig, axes = plt.subplots(1, 2, figsize=(13, 8), facecolor=SURFACE)
    _panel(axes[0], xx, yy, mask, actual_surface, vmax, boundaries, "Actual (Number_of_Cases)")
    mesh = _panel(axes[1], xx, yy, mask, predicted_surface, vmax, boundaries, "Predicted (Hybrid Risk)")

    cbar = fig.colorbar(mesh, ax=axes, shrink=0.7, location="bottom", pad=0.02)
    cbar.set_label("Case intensity / Hybrid Risk (shared scale)", color=INK_PRIMARY)
    cbar.ax.xaxis.set_tick_params(color=INK_MUTED, labelcolor=INK_MUTED)

    fig.suptitle(f"Module 3 - Actual vs. Predicted, {year} Week {week}", color=INK_PRIMARY, fontsize=14)

    out_path = MODULE3_FIGURES_DIR / f"actual_vs_predicted_{year}_wk{week:02d}.png"
    fig.savefig(out_path, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    logger.info("Actual vs. predicted surface saved to %s.", out_path)

    diff = week_df["Risk"] - week_df["Number_of_Cases"]
    logger.info(
        "Per-district actual vs. predicted (Year=%d Week=%d):\n%s",
        year, week,
        pd.DataFrame({
            "Number_of_Cases": week_df["Number_of_Cases"],
            "Risk": week_df["Risk"].round(2),
            "diff": diff.round(2),
        }).sort_values("Number_of_Cases", ascending=False).to_string(),
    )

    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Actual vs. predicted heatmap for one week.")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--week", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_actual_vs_predicted(args.year, args.week)
