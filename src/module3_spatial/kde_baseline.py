"""Stage 1 - KDE spatial baseline + Global Moran's I validation.

Computes a case-count-weighted Gaussian KDE surface over the 25 district
centroids (GADM Level-1) and validates that it reflects genuine spatial
clustering via Global Moran's I with queen contiguity weights (see
`module_3_spatial/MODULE_CONTEXT.md`, Stage 1).

Design note on bandwidth: the Silverman bandwidth (covariance) is derived
ONCE from the district centroids' own spatial spread (an unweighted,
unchanging point pattern - the geography), not re-derived per week from that
week's case counts. Per-week variation is carried entirely by the KDE
weights (`Number_of_Cases`), not by a week-varying kernel shape - otherwise
the smoothing scale itself would shrink/grow with epidemic intensity, which
would confound "how far risk spreads spatially" with "how many cases
occurred", and would break down entirely on the many all-zero-case weeks
(a data-driven bandwidth needs at least a handful of non-zero, non-collinear
weighted points to avoid a singular covariance matrix).

Because the kernel is a fixed 25x25 matrix, computing the weighted density
for every week is one matrix multiply (case-count matrix @ kernel matrix)
rather than refitting a KDE per week - this also makes all-zero-case weeks
trivially correct (0 cases in -> 0 KDE_baseline out, no special-casing
needed).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from esda.moran import Moran
from libpysal.weights import Queen
from scipy.stats import gaussian_kde, multivariate_normal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    GADM_LEVEL1_SHAPEFILE_PATH,
    MODULE3_BASELINE_RISK_PATH,
    MODULE3_FEATURES_DIR,
    MODULE3_MASTER_TABLE_PATH,
    MODULE3_METRICS_DIR,
    MODULE3_MORANS_I_METRICS_PATH,
    MONSOON_WEEKS_NE,
    MONSOON_WEEKS_SW,
)

logger = logging.getLogger(__name__)

# Sri Lanka's longitude range (~79.5-81.9 deg E) sits entirely inside UTM
# zone 44N (78-84 deg E); reprojecting out of GADM's native EPSG:4326
# (lat/lon degrees) is required before computing centroids or any
# Euclidean-distance-based Gaussian kernel - degrees are not a physically
# uniform distance unit.
METRIC_CRS = "EPSG:32644"

# GADM's own spelling for this district ("Moneragala") differs from the
# spelling already standardised across the rest of the pipeline
# ("Monaragala" - see DISTRICTS in src/config.py and the Kalmunai/Moneragala
# merge note in module_3_spatial/MODULE_CONTEXT.md's Data Pipeline Note).
GADM_NAME_FIXES = {"Moneragala": "Monaragala"}

MORAN_PERMUTATIONS = 999
MORAN_SIGNIFICANCE_LEVEL = 0.05
# esda.Moran's permutation test draws from numpy's global RNG and has no
# seed parameter of its own (verified: Moran.__init__ signature has no
# `seed`/`random_state` argument) - without seeding that RNG here, `p_sim`
# drifts slightly between runs (observed: NE-monsoon check moved from
# p_sim=0.2850 to 0.2860 across two unseeded runs on identical data). The I
# statistic itself is a closed-form calculation and is NOT affected by this -
# only p_sim is. Seeding makes the whole script's output byte-for-byte
# reproducible, which the persisted metrics CSV below depends on.
MORAN_RANDOM_SEED = 13


# ---------------------------------------------------------------------------
# Step 1: master table (post climate-coverage drop)
# ---------------------------------------------------------------------------

def load_master_table(path: Path = MODULE3_MASTER_TABLE_PATH) -> pd.DataFrame:
    """Load master_table.csv and drop the 125 rows outside Open-Meteo's
    climate coverage window (2006 Wk52 and the final weeks of 2026 - the
    same rows `module3_preprocessing.py::merge_climate` already flags with a
    warning). KDE itself only needs District/Year/Week/Number_of_Cases, but
    dropping these rows keeps this stage's (District, Year, Week) row set
    aligned with the rest of Module 3's pipeline rather than silently
    including weeks the rest of the pipeline treats as incomplete.
    """
    df = pd.read_csv(path)
    before = len(df)
    df = df.dropna(subset=["rain_sum (mm)"]).reset_index(drop=True)
    dropped = before - len(df)
    logger.info(
        "Loaded master_table.csv: %d rows (dropped %d rows outside climate coverage).",
        len(df), dropped,
    )
    return df


# ---------------------------------------------------------------------------
# Step 2: GADM district boundaries -> centroids (metric CRS)
# ---------------------------------------------------------------------------

def load_district_boundaries(path: Path = GADM_LEVEL1_SHAPEFILE_PATH) -> gpd.GeoDataFrame:
    """Load GADM Level-1 polygons, fix the Moneragala/Monaragala spelling,
    reproject to a metric CRS, and reindex to the canonical DISTRICTS order
    so every downstream matrix (kernel, pivoted case counts, Queen weights)
    lines up on the same row/column order.
    """
    gdf = gpd.read_file(path)
    gdf["District"] = gdf["NAME_1"].replace(GADM_NAME_FIXES)

    shapefile_districts = set(gdf["District"])
    unexpected = shapefile_districts - set(DISTRICTS)
    missing = set(DISTRICTS) - shapefile_districts
    if unexpected or missing:
        raise ValueError(
            f"GADM district names do not match DISTRICTS. "
            f"Unexpected: {sorted(unexpected)}, Missing: {sorted(missing)}"
        )

    gdf = gdf.to_crs(METRIC_CRS)
    gdf = gdf.set_index("District").loc[DISTRICTS].reset_index()
    return gdf[["District", "geometry"]]


def district_centroid_coords(boundaries: gpd.GeoDataFrame) -> np.ndarray:
    """(25, 2) array of (x, y) centroid coordinates in metres, same row
    order as `boundaries` (i.e. DISTRICTS order)."""
    centroids = boundaries.geometry.centroid
    return np.column_stack([centroids.x.to_numpy(), centroids.y.to_numpy()])


# ---------------------------------------------------------------------------
# Step 3: weighted Gaussian KDE, Silverman bandwidth
# ---------------------------------------------------------------------------

def silverman_covariance(coords: np.ndarray) -> np.ndarray:
    """Silverman-rule covariance matrix for the Gaussian kernel shape,
    computed via scipy's own `gaussian_kde(bw_method="silverman")` on the
    unweighted district centroids (see module docstring for why this is
    computed once from the geography, not per week)."""
    kde = gaussian_kde(coords.T, bw_method="silverman")
    return kde.covariance


def build_kernel_matrix(coords: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    """(25, 25) matrix where kernel[i, j] is the Silverman-bandwidth Gaussian
    density, centered on district i, evaluated at district j's centroid.
    Symmetric since all districts share one covariance matrix."""
    n = len(coords)
    kernel = np.empty((n, n))
    for i in range(n):
        kernel[i] = multivariate_normal(mean=coords[i], cov=covariance).pdf(coords)
    return kernel


def compute_kde_baseline(
    master: pd.DataFrame, coords: np.ndarray, kernel: np.ndarray
) -> pd.DataFrame:
    """Weight = Number_of_Cases per district-week. `KDE_baseline` for
    (district j, week t) = sum over all districts i of
    cases[t, i] * kernel[i, j] - a case-count-weighted sum of Gaussian
    kernels centered on every district, evaluated at district j.
    """
    pivot = master.pivot(index=["Year", "Week"], columns="District", values="Number_of_Cases")
    pivot = pivot[DISTRICTS]  # column order must match kernel's row/col order

    # A handful of (District, Year, Week) combos are genuinely absent from
    # master_table.csv (real historical gaps, never imputed - see
    # module3_preprocessing.py/shared.py). The pivot fills those cells with
    # NaN; left as-is, NaN in a matrix multiply would poison every OTHER
    # district's KDE_baseline for that week too, not just the missing one.
    # Treating an unknown case count as a 0 *weight* here only affects which
    # districts contribute to the smoothed surface that week - it does not
    # fabricate an output row, since the final merge back onto `master` only
    # keeps rows that actually exist.
    n_missing_cells = int(pivot.isna().to_numpy().sum())
    if n_missing_cells:
        logger.warning(
            "%d (District, Year, Week) cells are absent from master_table.csv "
            "(real gaps, not zeros); treated as 0 weight for KDE purposes only.",
            n_missing_cells,
        )
    pivot = pivot.fillna(0)

    kde_matrix = pivot.to_numpy() @ kernel
    kde_wide = pd.DataFrame(kde_matrix, index=pivot.index, columns=pivot.columns)

    kde_long = (
        kde_wide.reset_index()
        .melt(id_vars=["Year", "Week"], var_name="District", value_name="KDE_baseline")
    )

    result = master[["District", "Year", "Week", "Number_of_Cases"]].merge(
        kde_long, on=["District", "Year", "Week"], how="left"
    )

    if result["KDE_baseline"].isna().any():
        raise ValueError("KDE_baseline has unmatched rows after the pivot/melt round-trip.")

    return result


# ---------------------------------------------------------------------------
# Step 4: Global Moran's I validation (queen contiguity)
# ---------------------------------------------------------------------------

def build_queen_weights(boundaries: gpd.GeoDataFrame) -> Queen:
    w = Queen.from_dataframe(boundaries.set_index("District"), use_index=True)
    w.transform = "r"
    return w


def compute_global_moransI(w: Queen, kde_baseline: pd.DataFrame) -> Moran:
    """Aggregated Global Moran's I on the mean KDE_baseline per district
    (averaged across all weeks) - validates that the *typical* baseline risk
    surface shows genuine spatial clustering under queen contiguity, rather
    than computing a separate Moran's I for each of the ~1,000 weeks (both
    are valid per MODULE_CONTEXT.md; aggregated is the PRIMARY Stage 1
    checkpoint - the single validation number the report leads with).
    """
    mean_kde = kde_baseline.groupby("District")["KDE_baseline"].mean().reindex(w.id_order)
    if mean_kde.isna().any():
        raise ValueError("mean_kde has districts missing after reindexing to the weights' id_order.")

    return Moran(mean_kde.to_numpy(), w, permutations=MORAN_PERMUTATIONS)


def select_representative_weeks(kde_baseline: pd.DataFrame) -> dict[str, tuple[int, int]]:
    """Pick a peak week, a low week, and one representative week from each
    monsoon season for a SECONDARY, non-aggregated Moran's I check - not a
    replacement for the aggregated validation above, but evidence the
    clustering result is stable over time rather than an artifact of
    averaging across ~1,000 weeks (useful if asked "is this stable across
    time" at review).

    Weeks where every district has 0 cases (or, degenerately, identical
    KDE_baseline values) are excluded from every pick: Moran's I divides by
    the input's variance, which is exactly 0 for a constant vector.
    """
    weekly = kde_baseline.groupby(["Year", "Week"]).agg(
        total_cases=("Number_of_Cases", "sum"),
        kde_variance=("KDE_baseline", "var"),
    )
    non_degenerate = weekly[(weekly["total_cases"] > 0) & (weekly["kde_variance"] > 0)]

    sw = non_degenerate[non_degenerate.index.get_level_values("Week").isin(MONSOON_WEEKS_SW)]
    ne = non_degenerate[non_degenerate.index.get_level_values("Week").isin(MONSOON_WEEKS_NE)]

    return {
        "peak": non_degenerate["total_cases"].idxmax(),
        "low": non_degenerate["total_cases"].idxmin(),
        "sw_monsoon": sw["total_cases"].idxmax(),
        "ne_monsoon": ne["total_cases"].idxmax(),
    }


def compute_moransI_for_week(w: Queen, kde_baseline: pd.DataFrame, year: int, week: int) -> Moran:
    week_kde = (
        kde_baseline[(kde_baseline["Year"] == year) & (kde_baseline["Week"] == week)]
        .set_index("District")["KDE_baseline"]
        .reindex(w.id_order)
    )
    if week_kde.isna().any():
        raise ValueError(f"Missing districts for Year={year} Week={week} after reindexing.")
    return Moran(week_kde.to_numpy(), w, permutations=MORAN_PERMUTATIONS)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_kde_baseline() -> pd.DataFrame:
    MODULE3_FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    # Seeded once, up front, so both the aggregated and every per-week Moran's
    # I permutation test below are byte-for-byte reproducible across runs
    # (see MORAN_RANDOM_SEED's comment for the drift this fixes).
    np.random.seed(MORAN_RANDOM_SEED)

    master = load_master_table()
    boundaries = load_district_boundaries()
    coords = district_centroid_coords(boundaries)

    covariance = silverman_covariance(coords)
    kernel = build_kernel_matrix(coords, covariance)
    kde_baseline = compute_kde_baseline(master, coords, kernel)

    w = build_queen_weights(boundaries)
    moran = compute_global_moransI(w, kde_baseline)

    kde_baseline = kde_baseline.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    kde_baseline.to_csv(MODULE3_BASELINE_RISK_PATH, index=False)

    significant = moran.p_sim < MORAN_SIGNIFICANCE_LEVEL
    print(
        f"Global Moran's I (queen contiguity, mean KDE_baseline per district, "
        f"{MORAN_PERMUTATIONS} permutations):\n"
        f"  I statistic = {moran.I:.4f}\n"
        f"  p-value (permutation-based, p_sim) = {moran.p_sim:.4f}\n"
        f"  Clustering statistically significant at alpha={MORAN_SIGNIFICANCE_LEVEL}: "
        f"{'YES' if significant else 'NO'}"
    )

    metrics_rows = [
        {
            "check": "aggregated",
            "Year": None,
            "Week": None,
            "I": moran.I,
            "p_sim": moran.p_sim,
            "significant": significant,
        }
    ]

    # Secondary, non-aggregated stability check (see select_representative_weeks
    # docstring) - logged separately from the primary aggregated result above,
    # and captured in the same metrics CSV so it's reproducible on disk too.
    representative_weeks = select_representative_weeks(kde_baseline)
    for label, (year, week) in representative_weeks.items():
        week_moran = compute_moransI_for_week(w, kde_baseline, year, week)
        week_significant = week_moran.p_sim < MORAN_SIGNIFICANCE_LEVEL
        logger.info(
            "Secondary check [%s week, Year=%d Week=%d]: I=%.4f, p_sim=%.4f, "
            "significant=%s",
            label, year, week, week_moran.I, week_moran.p_sim, week_significant,
        )
        metrics_rows.append(
            {
                "check": label,
                "Year": year,
                "Week": week,
                "I": week_moran.I,
                "p_sim": week_moran.p_sim,
                "significant": week_significant,
            }
        )

    pd.DataFrame(metrics_rows).to_csv(MODULE3_MORANS_I_METRICS_PATH, index=False)

    logger.info(
        "KDE baseline complete: %d rows written to %s. Moran's I=%.4f, p_sim=%.4f. "
        "Full Moran's I validation (aggregated + representative weeks) written to %s.",
        len(kde_baseline), MODULE3_BASELINE_RISK_PATH, moran.I, moran.p_sim,
        MODULE3_MORANS_I_METRICS_PATH,
    )
    return kde_baseline


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_kde_baseline()
