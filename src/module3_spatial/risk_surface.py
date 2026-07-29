"""Continuous risk-surface interpolation for Module 3 (visualization layer
only - see `MODULE_CONTEXT.md`'s "Visualization: Continuous Risk Surface"
section).

Interpolates the 25 already-computed district `Risk` scores
(`hybrid_risk_map.csv`) onto a fine spatial grid - so that a point between
two high-risk neighbouring districts (e.g. the Colombo/Gampaha border)
reads as genuinely hotter than a point between a high-risk and a low-risk
district (e.g. Colombo/Kalutara), instead of every district rendering as
one flat, solid-colored block.

Interpolation method (IMPORTANT - a Gaussian-kernel weighted average was
tried FIRST and rejected, in two forms, both verified numerically before
being abandoned):

1. A single, country-wide Gaussian bandwidth (Stage 1's own
   `kde_baseline.py::silverman_covariance`, tuned for a Moran's I
   clustering TEST over all 25 districts) diluted the local
   Colombo-vs-Kalutara contrast to near nothing: checked on 2017 Wk29 (the
   documented peak week - Colombo 1285 / Gampaha 1296 / Kalutara 1141, a
   genuine 12% gap between Gampaha and Kalutara), the Colombo-Gampaha vs.
   Colombo-Kalutara midpoints came out only 1.3% apart. Root cause: at
   Silverman's scale the kernel evaluated at that border also picks up
   meaningful contribution from Kandy, Kurunegala, and roughly half the
   country.
2. A PER-DISTRICT bandwidth (each district's own mean distance to its own
   Queen-contiguous neighbours) was tried next, reasoning that Sri Lanka's
   districts vary too much in size/spacing for one shared bandwidth to fit
   both the dense western cluster and the sparse north/east. Checked
   numerically: this did narrow the kernel, but introduced a WORSE, more
   subtle problem - different districts now have differently-shaped
   kernels (a big-bandwidth neighbour's flat kernel vs a small-bandwidth
   neighbour's peaked one), so a point equidistant between two districts is
   no longer weighted symmetrically between them. Checked on the same 2017
   Wk29 example, this actually REVERSED the expected order
   (Colombo-Gampaha 860.7 < Colombo-Kalutara 863.0) - confirmed unusable,
   not a borderline result.

`evaluate_risk_surface()` instead uses k-nearest-neighbour Inverse Distance
Weighting (IDW, Shepard's method): at any point, only the `k` PHYSICALLY
CLOSEST districts contribute at all (distant districts get exactly zero
weight, not a small-but-nonzero Gaussian tail), weighted by `1/distance^power`.
This directly matches the intended behaviour - a point exactly between two
districts is weighted symmetrically between just those two (plus a small,
bounded contribution from the 3rd/4th-nearest), regardless of how densely
or sparsely districts are packed elsewhere in the country. Verified this
produces the expected, defensible result (see `evaluate_risk_surface`'s
own docstring for the final sanity-check numbers).

This is a rendering-layer technique only: it does not feed back into the
RF/iterative loop, does not change any committed Stage 1/Stage 2 output
(Stage 1's own `silverman_covariance` and its I=0.70 result are untouched -
not used anywhere in this file), and is unrelated to Module 3's
already-rejected GWR-as-a-modeling-method decision (`MODULE_CONTEXT.md`,
"Rejected approach") - the interpolation here operates on a fixed set of
already-computed scores for display; it does not re-fit or re-weight
anything the RF predicts.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely import contains_xy

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE3_BASELINE_RISK_PATH,
    MODULE3_FIGURES_DIR,
    MODULE3_HYBRID_RISK_MAP_PATH,
    MODULE3_RISK_SURFACE_PLOT_PATH,
)
from src.module3_spatial.kde_baseline import (  # noqa: E402
    district_centroid_coords,
    load_district_boundaries,
    select_representative_weeks,
)

logger = logging.getLogger(__name__)

# Report-figure grid resolution (metres, metric CRS EPSG:32644) - fine
# enough for a smooth PNG contour without being slow for a one-off script
# run. The dashboard (dashboard/pages.py) uses a coarser resolution for the
# interactive Leaflet heatmap, since that's rendered as individual DOM
# points rather than a single raster image.
DEFAULT_RESOLUTION_M = 1000.0

LABELED_DISTRICTS = ("Colombo", "Gampaha", "Kalutara")  # the user's own worked example


# ---------------------------------------------------------------------------
# Step 1: evaluation grid, clipped to Sri Lanka's landmass
# ---------------------------------------------------------------------------

def build_evaluation_grid(
    boundaries: gpd.GeoDataFrame, resolution_m: float = DEFAULT_RESOLUTION_M
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(xx, yy) meshgrid (metric CRS) over the districts' combined bounding
    box, a boolean `mask` of the same shape marking cells that fall inside
    Sri Lanka's landmass, and `grid_coords` - the (N, 2) array of just the
    masked (on-land) points, ready for kernel evaluation. Keeps the surface
    from ever coloring the ocean/India.
    """
    landmass = boundaries.geometry.union_all()
    minx, miny, maxx, maxy = landmass.bounds

    x = np.arange(minx, maxx, resolution_m)
    y = np.arange(miny, maxy, resolution_m)
    xx, yy = np.meshgrid(x, y)

    mask = contains_xy(landmass, xx, yy)
    grid_coords = np.column_stack([xx[mask], yy[mask]])

    return xx, yy, mask, grid_coords


# ---------------------------------------------------------------------------
# Step 2: k-nearest-neighbour Inverse Distance Weighting (IDW / Shepard's
# method) - see module docstring for why a Gaussian-kernel weighted average
# (both a single global bandwidth AND a per-district bandwidth) was tried
# first and rejected.
# ---------------------------------------------------------------------------

DEFAULT_K_NEAREST = 4
# Swept k in {2..5} x power in {2,3,4,6} against the Colombo-Gampaha vs.
# Colombo-Kalutara sanity check (2017 Wk29): power=2's 4.9% gap grows
# toward a ~6.4% ceiling (the plain 2-district average - what you get in
# the limit as only the single nearest district matters) as power
# increases, with diminishing returns past ~4. power=4 keeps k=4 (avoiding
# k=2/3's more blocky, sharply-faceted look) while sitting close to that
# ceiling (6.1%) and steepens the falloff away from each district's own
# centroid, which is what actually narrows the hot zone's visual footprint
# (less bleed into Kegalle/Ratnapura beyond the immediate cluster).
DEFAULT_IDW_POWER = 4.0


def evaluate_risk_surface(
    grid_coords: np.ndarray,
    district_coords: np.ndarray,
    district_values: np.ndarray,
    k: int = DEFAULT_K_NEAREST,
    power: float = DEFAULT_IDW_POWER,
) -> np.ndarray:
    """k-nearest-neighbour IDW: at every point in `grid_coords`, only the
    `k` PHYSICALLY CLOSEST districts contribute (every other district gets
    exactly zero weight - not a small-but-nonzero Gaussian tail), weighted
    by `1/distance^power`:
    `surface(x) = sum_{i in kNN(x)}(value_i / d(x,i)^power) / sum_{i in kNN(x)}(1 / d(x,i)^power)`.

    This stays in the same units as `district_values` - a grid point
    sitting on (or very near) district i's own centroid comes out
    approximately equal to value_i - and, critically, a point exactly
    between two districts is weighted SYMMETRICALLY between just those two
    (plus a small, bounded contribution from the 3rd/4th-nearest), which is
    what a Gaussian kernel with any single bandwidth failed to deliver:
    verified this produces the intended behaviour on 2017 Wk29 (Colombo
    1285 / Gampaha 1296 / Kalutara 1141) - the Colombo-Gampaha midpoint
    reads meaningfully higher than Colombo-Kalutara, not diluted or
    reversed like the Gaussian attempts (see `run_risk_surface`'s sanity
    check for the actual logged numbers).
    """
    k = min(k, district_coords.shape[0])
    # (n_grid, n_districts) pairwise distance matrix - one row per
    # evaluation point. Fine at the resolutions this module uses (tens of
    # thousands of grid points x 25 districts is a few million floats).
    diffs = grid_coords[:, None, :] - district_coords[None, :, :]
    dist = np.sqrt((diffs ** 2).sum(axis=2))

    nearest_idx = np.argsort(dist, axis=1)[:, :k]
    rows = np.arange(len(grid_coords))[:, None]
    nearest_dist = dist[rows, nearest_idx]
    nearest_values = district_values[nearest_idx]

    # Floors distance at 1m before the power - only matters for the
    # essentially-impossible case of a grid point landing exactly on a
    # district's own centroid (avoids a 0/0 division), negligible
    # everywhere else given every grid resolution this module uses is
    # >= 1000m.
    weights = 1.0 / np.maximum(nearest_dist, 1.0) ** power
    return (weights * nearest_values).sum(axis=1) / weights.sum(axis=1)


def risk_surface_for_week(
    hybrid_risk: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    grid_coords: np.ndarray,
    year: int,
    week: int,
) -> np.ndarray:
    """Pulls the 25 district `Risk` values for (year, week), reindexed to
    DISTRICTS order to match `district_centroid_coords`, and interpolates
    them onto `grid_coords`."""
    week_risk = (
        hybrid_risk[(hybrid_risk["Year"] == year) & (hybrid_risk["Week"] == week)]
        .set_index("District")["Risk"]
        .reindex(DISTRICTS)
    )
    if week_risk.isna().any():
        raise ValueError(f"Missing districts for Year={year} Week={week} after reindexing.")

    district_coords = district_centroid_coords(boundaries)
    return evaluate_risk_surface(grid_coords, district_coords, week_risk.to_numpy(dtype=float))


# ---------------------------------------------------------------------------
# Step 3: raster overlay for interactive (Leaflet/Folium) maps
# ---------------------------------------------------------------------------
#
# Feeding the interpolated grid to Leaflet's point-based `HeatMap` plugin
# (one DOM point per grid cell, fixed pixel radius/blur) looks fine at the
# zoom level the radius was tuned for, but breaks down at any other zoom:
# radius/blur are FIXED SCREEN PIXELS, while the real-world spacing between
# grid points covers a different pixel distance at every zoom level. Zoom
# in past that one correct level and the points stop overlapping - the
# continuous surface visibly degrades into separate uniform blobs, which
# is exactly backwards for a feature whose entire point is showing a
# CONTINUOUS surface. A raster image, by contrast, is geographically
# anchored (via `bounds`) and scales with the map at every zoom level like
# any other map tile - so it looks the same continuous gradient regardless
# of how far in the user zooms.


def risk_surface_rgba(
    xx: np.ndarray, yy: np.ndarray, mask: np.ndarray, surface_values: np.ndarray, cmap_name: str = "YlOrRd"
) -> np.ndarray:
    """(ny, nx, 4) uint8 RGBA array of the interpolated surface - transparent
    outside Sri Lanka's landmass (`mask`), opaque `YlOrRd` elsewhere, ready
    to hand to `folium.raster_layers.ImageOverlay`. Row 0 is the NORTH edge
    (image convention - top row first), the opposite of `xx`/`yy`'s own
    row-0-is-south ordering from `np.meshgrid`, so the array is flipped
    vertically before returning.
    """
    grid = np.full(xx.shape, np.nan)
    grid[mask] = surface_values

    vmax = np.nanmax(grid)
    normalized = np.clip(grid / vmax, 0.0, 1.0) if vmax > 0 else np.zeros_like(grid)

    cmap = plt.get_cmap(cmap_name)
    rgba = cmap(normalized)
    rgba[..., 3] = np.where(mask, 0.85, 0.0)  # opaque on land, fully transparent over ocean/India

    return np.flipud((rgba * 255).astype(np.uint8))


def grid_lonlat_bounds(xx: np.ndarray, yy: np.ndarray) -> list[list[float]]:
    """[[south, west], [north, east]] lon/lat bounding box for `xx`/`yy`'s
    metric-CRS (EPSG:32644) extent, for `folium.raster_layers.ImageOverlay`'s
    `bounds` parameter. Reprojects all 4 corners (not just 2 diagonal ones)
    and takes their bounding box - UTM-zone skew over Sri Lanka's extent is
    small enough that this axis-aligned approximation is visually exact at
    map-viewing scale.
    """
    corners = gpd.GeoSeries(
        gpd.points_from_xy(
            [xx.min(), xx.min(), xx.max(), xx.max()],
            [yy.min(), yy.max(), yy.min(), yy.max()],
        ),
        crs="EPSG:32644",
    ).to_crs("EPSG:4326")
    return [[corners.y.min(), corners.x.min()], [corners.y.max(), corners.x.max()]]


# ---------------------------------------------------------------------------
# Step 4: static report figure
# ---------------------------------------------------------------------------

# Chart chrome, matching evaluate.py's validated palette (dataviz skill,
# references/palette.md) so this figure reads as part of the same set.
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_MUTED = "#898781"
BASELINE = "#c3c2b7"


def plot_risk_surface(
    xx: np.ndarray,
    yy: np.ndarray,
    mask: np.ndarray,
    surface_values: np.ndarray,
    boundaries: gpd.GeoDataFrame,
    year: int,
    week: int,
    path: Path,
) -> None:
    """Renders the interpolated surface as a masked pcolormesh (landmass
    only, ocean/India left transparent), with district outlines and the
    user's own Colombo/Gampaha/Kalutara example labeled for direct
    reference."""
    grid = np.full(xx.shape, np.nan)
    grid[mask] = surface_values

    fig, ax = plt.subplots(figsize=(8, 9), facecolor=SURFACE)
    mesh = ax.pcolormesh(xx, yy, grid, cmap="YlOrRd", shading="auto")
    boundaries.boundary.plot(ax=ax, color=BASELINE, linewidth=0.6)

    for _, row in boundaries.iterrows():
        if row["District"] in LABELED_DISTRICTS:
            c = row.geometry.centroid
            ax.annotate(
                row["District"], (c.x, c.y), color=INK_PRIMARY, fontsize=9,
                fontweight="bold", ha="center",
                path_effects=[pe.withStroke(linewidth=2.5, foreground=SURFACE)],
            )

    ax.set_axis_off()
    ax.set_aspect("equal")
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.7)
    cbar.set_label("Interpolated Hybrid Risk", color=INK_PRIMARY)
    cbar.ax.yaxis.set_tick_params(color=INK_MUTED, labelcolor=INK_MUTED)
    ax.set_title(
        f"Module 3 - Continuous Hybrid Risk Surface\n{year} Week {week}",
        color=INK_PRIMARY, fontsize=13,
    )

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    logger.info("Risk surface plot saved to %s.", path)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_risk_surface(year: int | None = None, week: int | None = None) -> None:
    """Defaults to Stage 1's already-identified peak week (2017 Wk29 per
    MODULE_CONTEXT.md) when `year`/`week` aren't given, saving to the
    canonical `risk_surface_peak_week.png`. An explicit `year`/`week` (e.g.
    via `--year --week` on the CLI) instead saves to a week-specific
    filename, so testing other weeks never overwrites the canonical figure.
    """
    MODULE3_FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    boundaries = load_district_boundaries()
    district_coords = district_centroid_coords(boundaries)

    xx, yy, mask, grid_coords = build_evaluation_grid(boundaries, DEFAULT_RESOLUTION_M)
    logger.info("Evaluation grid: %d on-land points at %.0fm resolution.", len(grid_coords), DEFAULT_RESOLUTION_M)

    hybrid_risk = pd.read_csv(MODULE3_HYBRID_RISK_MAP_PATH)

    if year is None or week is None:
        kde_baseline = pd.read_csv(MODULE3_BASELINE_RISK_PATH)
        year, week = select_representative_weeks(kde_baseline)["peak"]
        out_path = MODULE3_RISK_SURFACE_PLOT_PATH
    else:
        available = hybrid_risk[(hybrid_risk["Year"] == year) & (hybrid_risk["Week"] == week)]
        if available.empty:
            raise ValueError(
                f"No hybrid_risk_map.csv rows for Year={year} Week={week} - available range is "
                f"{hybrid_risk['Year'].min()}-{hybrid_risk['Year'].max()} "
                f"(latest: {hybrid_risk['Year'].max()} Wk{hybrid_risk.loc[hybrid_risk['Year'] == hybrid_risk['Year'].max(), 'Week'].max()})."
            )
        out_path = MODULE3_FIGURES_DIR / f"risk_surface_{year}_wk{week:02d}.png"

    surface_values = risk_surface_for_week(hybrid_risk, boundaries, grid_coords, year, week)

    plot_risk_surface(xx, yy, mask, surface_values, boundaries, year, week, out_path)

    # Direct sanity check against the user's own Colombo/Gampaha/Kalutara
    # framing: the Colombo-Gampaha midpoint (two high-case neighbours)
    # should read hotter than the Colombo-Kalutara midpoint.
    by_district = boundaries["District"].tolist()
    colombo_xy = district_coords[by_district.index("Colombo")]
    gampaha_xy = district_coords[by_district.index("Gampaha")]
    kalutara_xy = district_coords[by_district.index("Kalutara")]

    cg_mid = np.array([(colombo_xy + gampaha_xy) / 2])
    ck_mid = np.array([(colombo_xy + kalutara_xy) / 2])

    week_risk = (
        hybrid_risk[(hybrid_risk["Year"] == year) & (hybrid_risk["Week"] == week)]
        .set_index("District")["Risk"].reindex(DISTRICTS).to_numpy(dtype=float)
    )
    cg_value = evaluate_risk_surface(cg_mid, district_coords, week_risk)[0]
    ck_value = evaluate_risk_surface(ck_mid, district_coords, week_risk)[0]

    logger.info(
        "Sanity check [%d Wk%d]: Colombo-Gampaha midpoint = %.3f, "
        "Colombo-Kalutara midpoint = %.3f (expect the former higher, since "
        "Colombo and Gampaha are both high-case neighbours).",
        year, week, cg_value, ck_value,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Render the continuous risk surface for one week (default: Stage 1's peak week)."
    )
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--week", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_risk_surface(args.year, args.week)
