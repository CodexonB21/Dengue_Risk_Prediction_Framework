"""Module 3 (hybrid spatial hotspot detection) preprocessing layer.

Reads the shared, module-agnostic base tables from `data/processed/shared/`
(read-only; see `module_3_spatial/MODULE_CONTEXT.md`'s scope rule) and joins
them into a single district-week table. Unlike Module 1/2, this layer does
NOT reimplement any aggregation already done in `shared.py`: climate is
already weekly per district, population is already an annual per-district
series - Module 3 only joins and adds its own spatial covariate (elevation),
which the shared layer never carries forward (it lives only in the raw
Open-Meteo CSV preambles, stripped out during `shared.py`'s daily-to-weekly
aggregation).

No week-53 handling or missing-week imputation happens here (Module-1/2-scoped
decisions, not inherited - Module 3's KDE/Moran's I baseline and RF residual
model do not require a gap-free series the way SARIMA or lag features do).

Writes `data/processed/module3/master_table.csv`: one row per
District + Year + Week, with case counts, climate, population, and
elevation. District boundary geometry (GADM Level-1 shapefile,
`data/raw/spatial/gadm41_LKA_1.*`) is intentionally NOT loaded here - it has
no (District, Year, Week) grain and belongs to the Stage 1 KDE/Moran's I step
(`kde_baseline.py`), not this tabular join.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE3_MASTER_TABLE_PATH,
    MODULE3_PROCESSED_DIR,
    RAW_WEATHER_DIR,
    SHARED_CLIMATE_WEEKLY_PATH,
    SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH,
    SHARED_EPI_WEEK_CALENDAR_PATH,
    SHARED_POPULATION_ANNUAL_PATH,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Loading shared inputs (read-only; owned by src/preprocessing/shared.py)
# ---------------------------------------------------------------------------

def load_shared_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    epi = pd.read_csv(
        SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH,
        parse_dates=["Week_Start_Date", "Week_End_Date"],
    )
    climate = pd.read_csv(SHARED_CLIMATE_WEEKLY_PATH)
    population = pd.read_csv(SHARED_POPULATION_ANNUAL_PATH)
    calendar = pd.read_csv(
        SHARED_EPI_WEEK_CALENDAR_PATH,
        parse_dates=["Week_Start_Date", "Week_End_Date"],
    )
    return epi, climate, population, calendar


# ---------------------------------------------------------------------------
# Elevation - the one raw source shared.py does not carry into its weekly
# output (it lives only in each Open-Meteo file's 3-line metadata preamble).
# ---------------------------------------------------------------------------

def district_from_weather_filename(path: Path) -> str:
    """Mirror shared.py's convention: 'open-meteo-6.92N79.91E4m Colombo.csv'
    -> 'Colombo'."""
    stem = path.stem
    parts = stem.split(" ", 1)
    return parts[1].strip() if len(parts) > 1 else stem.strip()


def extract_elevation(weather_dir: Path = RAW_WEATHER_DIR) -> pd.DataFrame:
    """Read the `elevation` value out of each per-district Open-Meteo CSV's
    metadata preamble (row 2, column 3 - see the `latitude,longitude,
    elevation,...` header on row 1). Static per district, no Year/Week grain.
    """
    files = sorted(weather_dir.glob("*.csv"))
    if len(files) != len(DISTRICTS):
        raise ValueError(f"Expected {len(DISTRICTS)} weather files, found {len(files)}")

    records = []
    for f in files:
        district = district_from_weather_filename(f)
        if district not in DISTRICTS:
            raise ValueError(f"Weather file '{f.name}' parsed to unexpected district '{district}'")

        with open(f, "r", encoding="utf-8-sig") as fh:
            header_line = fh.readline()
            value_line = fh.readline()

        header_cols = [c.strip() for c in header_line.split(",")]
        value_cols = [c.strip() for c in value_line.split(",")]
        try:
            elevation_idx = header_cols.index("elevation")
        except ValueError as exc:
            raise ValueError(f"No 'elevation' column in {f.name}'s metadata preamble") from exc

        elevation_m = float(value_cols[elevation_idx])
        records.append({"District": district, "elevation_m": elevation_m})

    result = pd.DataFrame(records).sort_values("District").reset_index(drop=True)

    n_districts = result["District"].nunique()
    if n_districts != len(DISTRICTS):
        raise ValueError(f"Expected {len(DISTRICTS)} districts of elevation, got {n_districts}")

    return result


# ---------------------------------------------------------------------------
# Joins
# ---------------------------------------------------------------------------

def merge_climate(epi: pd.DataFrame, climate: pd.DataFrame) -> pd.DataFrame:
    merged = epi.merge(climate, on=["District", "Year", "Week"], how="left")

    climate_cols = [c for c in climate.columns if c not in ("District", "Year", "Week")]
    n_missing_climate = merged[climate_cols[0]].isna().sum()
    if n_missing_climate:
        logger.warning(
            "%d rows have no matching climate data for their (District, "
            "Year, Week) - expected only for years before climate coverage "
            "begins (2007) or after it ends.",
            int(n_missing_climate),
        )
    return merged


def merge_population(df: pd.DataFrame, population: pd.DataFrame) -> pd.DataFrame:
    merged = df.merge(population, on=["District", "Year"], how="left")

    n_missing_pop = merged["Estimated_Population"].isna().sum()
    if n_missing_pop:
        logger.warning(
            "%d rows have no matching population estimate for their "
            "(District, Year) - population_annual.csv covers 2006-2026.",
            int(n_missing_pop),
        )
    return merged


def merge_elevation(df: pd.DataFrame, elevation: pd.DataFrame) -> pd.DataFrame:
    merged = df.merge(elevation, on="District", how="left")

    n_missing_elev = merged["elevation_m"].isna().sum()
    if n_missing_elev:
        raise ValueError(
            f"{n_missing_elev} rows have no matching elevation value - "
            "elevation is static per district and should never be missing "
            "once every district's weather file has been read."
        )
    return merged


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_master_table(df: pd.DataFrame) -> None:
    dup_keys = df.duplicated(subset=["District", "Year", "Week"]).sum()
    if dup_keys:
        raise ValueError(f"{dup_keys} duplicate (District, Year, Week) rows found.")

    n_districts = df["District"].nunique()
    if n_districts != len(DISTRICTS):
        raise ValueError(f"Expected {len(DISTRICTS)} districts, found {n_districts}.")

    logger.info(
        "Validation passed: %d rows, %d districts, %d-%d.",
        len(df), n_districts, df["Year"].min(), df["Year"].max(),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_module3_preprocessing() -> pd.DataFrame:
    MODULE3_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    epi, climate, population, _calendar = load_shared_tables()
    elevation = extract_elevation()

    table = merge_climate(epi, climate)
    table = merge_population(table, population)
    table = merge_elevation(table, elevation)

    table = table.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    validate_master_table(table)

    table.to_csv(MODULE3_MASTER_TABLE_PATH, index=False)
    logger.info(
        "Module 3 preprocessing complete: %d rows written to %s.",
        len(table), MODULE3_MASTER_TABLE_PATH,
    )
    return table


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_module3_preprocessing()
