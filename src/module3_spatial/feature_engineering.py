"""Stage 2 - feature engineering + residual target (no model training here).

Merges the Stage 1 outputs (`master_table.csv`, `baseline_risk.csv`) and
builds the feature set `MODULE_CONTEXT.md`'s Stage 2 section specifies:
rainfall/temperature lags, climate anomalies, monsoon dummies, elevation +
population density, and a Mahalanobis multivariate anomaly score. Writes
`data/features/module3/stage2_feature_table.csv`.

Two column choices the spec leaves implicit are pinned down here:

- "Rainfall" / "temperature" each map to ONE canonical column -
  `rain_sum (mm)` and `temperature_2m_mean (°C)` - not every rainfall/temp
  column in master_table.csv. `precipitation_sum (mm)` is dropped as a
  rainfall candidate because it is identical to `rain_sum (mm)` in this
  dataset (Sri Lanka has no snow, so Open-Meteo's rain/precipitation totals
  never diverge).
- "Population density" is NOT actually a column in master_table.csv (only
  raw `Estimated_Population` is) - it is derived here from the same
  reprojected GADM Level-1 polygons `kde_baseline.py` already uses for
  centroids/Queen weights (`Estimated_Population / district land area`),
  rather than mislabeling the raw headcount as a density.

Lags are computed via `.shift()` on each district's own time-ordered rows,
not on calendar week arithmetic - the ~2 known genuinely-absent (District,
Year, Week) cells (see kde_baseline.py) mean a shifted value can, in that
rare case, be the previous AVAILABLE week rather than strictly N calendar
weeks prior. Module 3 does not impute (no such decision is recorded), so
this is an accepted, documented limitation, not an oversight.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_BASELINE_RISK_PATH,
    MODULE3_FEATURES_DIR,
    MODULE3_MAHALANOBIS_STATS_PATH,
    MODULE3_MASTER_TABLE_PATH,
    MODULE3_MODELS_DIR,
    MODULE3_STAGE2_FEATURE_TABLE_PATH,
    MONSOON_WEEKS_NE,
    MONSOON_WEEKS_SW,
)
from src.module3_spatial.kde_baseline import load_district_boundaries

logger = logging.getLogger(__name__)

# See module docstring for why these are the ONE canonical rainfall/
# temperature column, not every candidate in master_table.csv.
LAG_SOURCE_COLUMNS = {
    "rain_sum (mm)": "rainfall",
    "temperature_2m_mean (°C)": "temperature",
}
LAG_WEEKS = [2, 3, 4]

MAHALANOBIS_COLUMNS = [
    "rain_sum (mm)",
    "temperature_2m_mean (°C)",
    "elevation_m",
    "Estimated_Population",
]

OUTPUT_COLUMNS = (
    ["District", "Year", "Week", "Week_Start_Date"]
    + ["Number_of_Cases", "KDE_baseline", "Residual"]
    + list(LAG_SOURCE_COLUMNS.keys())
    + [f"{label}_lag_{lag}" for label in LAG_SOURCE_COLUMNS.values() for lag in LAG_WEEKS]
    + [f"{label}_anomaly" for label in LAG_SOURCE_COLUMNS.values()]
    + ["monsoon_indicator_SW", "monsoon_indicator_NE"]
    + ["elevation_m", "Estimated_Population", "population_density"]
    + ["mahalanobis_anomaly_score"]
)


# ---------------------------------------------------------------------------
# Step 1: load + merge Stage 1 outputs
# ---------------------------------------------------------------------------

def load_and_merge() -> pd.DataFrame:
    master = pd.read_csv(
        MODULE3_MASTER_TABLE_PATH,
        parse_dates=["Week_Start_Date", "Week_End_Date"],
    )
    baseline = pd.read_csv(MODULE3_BASELINE_RISK_PATH)[["District", "Year", "Week", "KDE_baseline"]]

    merged = master.merge(baseline, on=["District", "Year", "Week"], how="inner")

    if len(merged) != len(baseline):
        raise ValueError(
            f"Expected the merge to preserve all {len(baseline)} baseline_risk.csv "
            f"rows (its (District, Year, Week) keys are a strict subset of "
            f"master_table.csv's), got {len(merged)}."
        )
    return merged


# ---------------------------------------------------------------------------
# Step 2: residual target
# ---------------------------------------------------------------------------

def compute_residual(df: pd.DataFrame) -> pd.DataFrame:
    df["Residual"] = df["Number_of_Cases"] - df["KDE_baseline"]
    return df


# ---------------------------------------------------------------------------
# Step 3a: rainfall/temperature lags (2-4 weeks, per district)
# ---------------------------------------------------------------------------

def compute_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["District", "Week_Start_Date"]).reset_index(drop=True)
    grouped = df.groupby("District")
    for source_col, label in LAG_SOURCE_COLUMNS.items():
        for lag in LAG_WEEKS:
            df[f"{label}_lag_{lag}"] = grouped[source_col].shift(lag)
    return df


# ---------------------------------------------------------------------------
# Step 3b: climate anomaly (actual - historical per-calendar-week mean)
# ---------------------------------------------------------------------------

def compute_climate_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """actual - historical mean for that (District, calendar Week), computed
    across ALL years in the series (per MODULE_CONTEXT.md's Stage 2 spec) -
    not a strictly-prior-years expanding mean. Module 3's validation axis is
    spatial K-means CV (Open Questions #4/5), not a temporal walk-forward
    split, so a full-sample per-week historical mean does not leak across
    folds the way it would under Module 1/2's temporal CV.
    """
    for source_col, label in LAG_SOURCE_COLUMNS.items():
        historical_mean = df.groupby(["District", "Week"])[source_col].transform("mean")
        df[f"{label}_anomaly"] = df[source_col] - historical_mean
    return df


# ---------------------------------------------------------------------------
# Step 3c: monsoon season dummies
# ---------------------------------------------------------------------------

def compute_monsoon_dummies(df: pd.DataFrame) -> pd.DataFrame:
    df["monsoon_indicator_SW"] = df["Week"].isin(MONSOON_WEEKS_SW).astype(int)
    df["monsoon_indicator_NE"] = df["Week"].isin(MONSOON_WEEKS_NE).astype(int)
    return df


# ---------------------------------------------------------------------------
# Step 3d: population density (derived - see module docstring)
# ---------------------------------------------------------------------------

def compute_population_density(df: pd.DataFrame) -> pd.DataFrame:
    boundaries = load_district_boundaries()
    area_km2 = (boundaries.geometry.area / 1e6).rename("area_km2")
    area_df = pd.concat([boundaries["District"], area_km2], axis=1)

    result = df.merge(area_df, on="District", how="left")
    result["population_density"] = result["Estimated_Population"] / result["area_km2"]
    return result.drop(columns="area_km2")


# ---------------------------------------------------------------------------
# Step 3e: Mahalanobis multivariate anomaly score
# ---------------------------------------------------------------------------

def fit_mahalanobis_stats(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Fits the mean vector + covariance matrix of `MAHALANOBIS_COLUMNS` over
    `df` (the full historical training table). Split out from
    `apply_mahalanobis_scores` so the exact fitted stats can be persisted
    (`MODULE3_MAHALANOBIS_STATS_PATH`) and reused unchanged when scoring a
    forecast row (`forecast_future.py`) - recomputing mean/covariance over a
    historical-data-plus-one-new-row sample would shift the fitted
    distribution slightly and make the forecast row inconsistent with what
    the RF was actually trained against.
    """
    X = df[MAHALANOBIS_COLUMNS].to_numpy()
    mean = X.mean(axis=0)
    cov = np.cov(X, rowvar=False)
    return mean, cov


def apply_mahalanobis_scores(df: pd.DataFrame, mean: np.ndarray, cov: np.ndarray) -> pd.DataFrame:
    """Multivariate anomaly score across [rainfall, temperature, elevation,
    population] per district-week, relative to an already-fitted mean/
    covariance (not per-district) - captures how unusual a given
    district-week's COMBINATION of these 4 variables is, accounting for
    correlation between them (unlike a plain per-variable z-score sum).
    """
    inv_cov = np.linalg.inv(cov)
    X = df[MAHALANOBIS_COLUMNS].to_numpy()
    diff = X - mean
    d2 = np.einsum("ij,jk,ik->i", diff, inv_cov, diff)
    df["mahalanobis_anomaly_score"] = np.sqrt(d2)
    return df


def compute_mahalanobis_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Fits mean/covariance on `df` itself and applies them in one step -
    the historical training-table path. See `fit_mahalanobis_stats`/
    `apply_mahalanobis_scores` for the split used when a forecast row must
    reuse already-fitted stats instead of refitting.
    """
    mean, cov = fit_mahalanobis_stats(df)
    return apply_mahalanobis_scores(df, mean, cov)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_feature_table(df: pd.DataFrame) -> None:
    lag_cols = [c for c in df.columns if "_lag_" in c]
    non_lag_cols = [c for c in df.columns if c not in lag_cols]

    unexpected_nan = df[non_lag_cols].isna().sum()
    unexpected_nan = unexpected_nan[unexpected_nan > 0]
    if not unexpected_nan.empty:
        raise ValueError(f"Unexpected NaN outside lag columns:\n{unexpected_nan}")

    dup_keys = df.duplicated(subset=["District", "Year", "Week"]).sum()
    if dup_keys:
        raise ValueError(f"{dup_keys} duplicate (District, Year, Week) rows found.")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_feature_engineering() -> pd.DataFrame:
    MODULE3_FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    df = load_and_merge()
    df = compute_residual(df)
    df = compute_lag_features(df)
    df = compute_climate_anomaly(df)
    df = compute_monsoon_dummies(df)
    df = compute_population_density(df)

    mahalanobis_mean, mahalanobis_cov = fit_mahalanobis_stats(df)
    df = apply_mahalanobis_scores(df, mahalanobis_mean, mahalanobis_cov)
    MODULE3_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"mean": mahalanobis_mean, "cov": mahalanobis_cov, "columns": MAHALANOBIS_COLUMNS},
        MODULE3_MAHALANOBIS_STATS_PATH,
    )
    logger.info("Mahalanobis fit stats (mean/covariance) saved to %s.", MODULE3_MAHALANOBIS_STATS_PATH)

    df = df[OUTPUT_COLUMNS]
    validate_feature_table(df)

    df.to_csv(MODULE3_STAGE2_FEATURE_TABLE_PATH, index=False)

    lag_cols = [c for c in df.columns if "_lag_" in c]
    lag_nan_counts = df[lag_cols].isna().sum()
    logger.info(
        "Stage 2 feature table: %d rows, %d columns written to %s.",
        len(df), len(df.columns), MODULE3_STAGE2_FEATURE_TABLE_PATH,
    )
    logger.info(
        "NaN counts from lag features (series-start rows, KEPT not dropped):\n%s",
        lag_nan_counts.to_string(),
    )
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_feature_engineering()
