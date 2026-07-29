"""Module 1 (forecasting) preprocessing layer.

Reads the shared, module-agnostic base tables from `data/processed/shared/`
and applies Module 1's own SARIMA-specific temporal adjustments (Decision
013 - these are NOT shared-layer transformations because Module 2 and
Module 3 may make different choices):

1. Merge epi-week 53 into week 52 for the confirmed 53-week years (Decision
   007) so every district-year has a fixed 52-week seasonal period.
2. Impute the remaining genuine missing weeks via seasonal-naive fill and
   flag them with `is_imputed` (Decision 011).
3. Merge in climate data on (District, Year, Week).
4. Merge in population and compute `cases_per_100k` as a reporting-only
   column (Decision 006) - not a modeling target.

Writes `data/processed/module1/weekly_modeling_table.csv`: one row per
District + Year + Week, 52 weeks/year for every interior (fully-covered)
year, no duplicate keys, `is_imputed` flag present, all climate columns
present, population + `cases_per_100k` present.
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
    MODULE1_PROCESSED_DIR,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    SHARED_CLIMATE_WEEKLY_PATH,
    SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH,
    SHARED_EPI_WEEK_CALENDAR_PATH,
    SHARED_POPULATION_ANNUAL_PATH,
)
from src.preprocessing.reporting_anomalies import flag_reporting_anomalies  # noqa: E402

logger = logging.getLogger(__name__)

# Decision 007 (Module-1-scoped): confirmed 53-epi-week years.
WEEK_53_MERGE_YEARS = [2009, 2016, 2019, 2021]
CANONICAL_WEEKS_PER_YEAR = 52

# Same weekly-mode convention used for weather_code in shared.py - there is
# no upstream rule for collapsing a categorical code across a merged pair of
# weeks, so the more frequent of the two is kept.
CLIMATE_MODE_COLUMN = "weather_code (wmo code)"
CLIMATE_SOURCE_COLUMN = "climate_data_source"
CATEGORICAL_CLIMATE_COLUMNS = {CLIMATE_MODE_COLUMN, CLIMATE_SOURCE_COLUMN}


# ---------------------------------------------------------------------------
# Loading shared inputs
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
# Step 1: merge week 53 into week 52 (Decision 007)
# ---------------------------------------------------------------------------

def merge_week_53_into_52(
    df: pd.DataFrame,
    agg_map: dict,
    group_cols: tuple[str, ...] = ("District", "Year"),
) -> pd.DataFrame:
    """Collapse weeks 52 and 53 of the confirmed 53-week years into a single
    week-52 row per (District, Year), using `agg_map` to say how each value
    column should be combined (e.g. sum for cases, mean for climate).

    Any other column not in `agg_map` or `group_cols` is kept via "first"
    (relying on `df` being pre-sorted so week 52's own row - not week 53's -
    is the one that wins, e.g. for date columns).
    """
    df = df.sort_values(list(group_cols) + ["Week"]).reset_index(drop=True)

    affected_mask = df["Year"].isin(WEEK_53_MERGE_YEARS) & df["Week"].isin([52, 53])
    unaffected = df[~affected_mask]
    affected = df[affected_mask].copy()
    affected["Week"] = 52

    agg_spec = dict(agg_map)
    other_cols = [
        c for c in affected.columns
        if c not in agg_spec and c not in group_cols and c != "Week"
    ]
    for c in other_cols:
        agg_spec[c] = "first"

    collapsed = affected.groupby(list(group_cols) + ["Week"], as_index=False).agg(agg_spec)

    result = pd.concat([unaffected, collapsed], ignore_index=True, sort=False)
    return result.sort_values(list(group_cols) + ["Week"]).reset_index(drop=True)


def _weekly_mode(series: pd.Series):
    mode = series.mode()
    return mode.sort_values().iloc[0] if not mode.empty else pd.NA


def merge_week_53_cases(epi: pd.DataFrame) -> pd.DataFrame:
    return merge_week_53_into_52(epi, agg_map={"Number_of_Cases": "sum"})


def merge_week_53_climate(climate: pd.DataFrame) -> pd.DataFrame:
    value_cols = [c for c in climate.columns if c not in ("District", "Year", "Week")]
    agg_map = {c: "mean" for c in value_cols if c not in CATEGORICAL_CLIMATE_COLUMNS}
    for col in CATEGORICAL_CLIMATE_COLUMNS:
        if col in value_cols:
            agg_map[col] = _weekly_mode
    return merge_week_53_into_52(climate, agg_map=agg_map)


# ---------------------------------------------------------------------------
# Step 2: seasonal-naive imputation of remaining genuine gaps (Decision 011)
# ---------------------------------------------------------------------------

def find_missing_weeks(epi: pd.DataFrame) -> pd.DataFrame:
    """Find genuine (District, Year, Week) gaps within *interior* years only.

    The dataset's first and last years are partial by construction (case
    data starts 2006-12-23 mid-year; the most recent year is still ongoing at
    scrape time) - that is a natural boundary condition, not a "genuine gap",
    so those two years are excluded from the completeness check rather than
    having dozens of fabricated weeks forced into them.
    """
    min_year, max_year = epi["Year"].min(), epi["Year"].max()
    interior = epi[(epi["Year"] > min_year) & (epi["Year"] < max_year)]

    expected_weeks = set(range(1, CANONICAL_WEEKS_PER_YEAR + 1))
    missing_rows = []
    for district in DISTRICTS:
        district_df = interior[interior["District"] == district]
        for year, group in district_df.groupby("Year"):
            present_weeks = set(group["Week"])
            for week in sorted(expected_weeks - present_weeks):
                missing_rows.append({"District": district, "Year": int(year), "Week": week})

    return pd.DataFrame(missing_rows, columns=["District", "Year", "Week"])


def impute_missing_weeks(epi: pd.DataFrame, missing: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    """Fill genuine gaps via seasonal-naive imputation: same district, same
    epi-week, mean `Number_of_Cases` across all other available years. Adds
    the `is_imputed` boolean flag (True for filled rows, False otherwise).
    """
    epi = epi.copy()
    epi["is_imputed"] = False

    if missing.empty:
        logger.info("No genuine gaps found to impute.")
        return epi

    seasonal_means = (
        epi.groupby(["District", "Week"])["Number_of_Cases"].mean().rename("seasonal_mean_cases")
    )

    filled = missing.merge(seasonal_means.reset_index(), on=["District", "Week"], how="left")

    unresolved = filled["seasonal_mean_cases"].isna()
    if unresolved.any():
        logger.warning(
            "%d missing (District, Week) combos have no seasonal-naive "
            "reference value in any other year; Number_of_Cases left as NaN "
            "for those rows.",
            int(unresolved.sum()),
        )

    filled["Number_of_Cases"] = filled["seasonal_mean_cases"].round()
    filled["is_imputed"] = True
    filled = filled.drop(columns="seasonal_mean_cases")

    filled = filled.merge(calendar, on=["Year", "Week"], how="left")

    n_missing_dates = filled["Week_Start_Date"].isna().sum()
    if n_missing_dates:
        bad_weeks = sorted(set(map(tuple, filled.loc[filled["Week_Start_Date"].isna(), ["Year", "Week"]].to_numpy())))
        logger.warning(
            "%d imputed rows have no calendar date (their (Year, Week) - e.g. "
            "%s - has no available date slot, typically because the "
            "preceding year's own week-53 already consumes the days a "
            "sequential 'week 1' would otherwise occupy). Number_of_Cases is "
            "still imputed via seasonal-naive fill; Week_Start_Date/"
            "Week_End_Date are left as NaN rather than fabricated. See "
            "module_1_forecasting/MODULE_CONTEXT.md for this known case.",
            int(n_missing_dates), bad_weeks,
        )

    result = pd.concat(
        [epi, filled[["District", "Year", "Week", "Week_Start_Date", "Week_End_Date", "Number_of_Cases", "is_imputed"]]],
        ignore_index=True,
        sort=False,
    )

    logger.info(
        "Imputed %d genuine gap rows via seasonal-naive fill (same "
        "district/week, mean across other years).",
        len(filled),
    )

    return result.sort_values(["District", "Year", "Week"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Steps 3-4: merge climate + population, compute cases_per_100k
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


def merge_population(epi: pd.DataFrame, population: pd.DataFrame) -> pd.DataFrame:
    merged = epi.merge(population, on=["District", "Year"], how="left")
    merged["cases_per_100k"] = (
        merged["Number_of_Cases"] / merged["Estimated_Population"] * 100_000
    )

    n_missing_pop = merged["Estimated_Population"].isna().sum()
    if n_missing_pop:
        logger.warning(
            "%d rows have no matching population estimate for their "
            "(District, Year) - population_annual.csv covers 2006-2026.",
            int(n_missing_pop),
        )
    return merged


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_weekly_modeling_table(df: pd.DataFrame) -> None:
    dup_keys = df.duplicated(subset=["District", "Year", "Week"]).sum()
    if dup_keys:
        raise ValueError(f"{dup_keys} duplicate (District, Year, Week) rows found.")

    n_districts = df["District"].nunique()
    if n_districts != len(DISTRICTS):
        raise ValueError(f"Expected {len(DISTRICTS)} districts, found {n_districts}.")

    min_year, max_year = df["Year"].min(), df["Year"].max()
    interior = df[(df["Year"] > min_year) & (df["Year"] < max_year)]
    counts = interior.groupby(["District", "Year"]).size()
    bad_counts = counts[counts != CANONICAL_WEEKS_PER_YEAR]
    if not bad_counts.empty:
        raise ValueError(
            f"{len(bad_counts)} (District, Year) interior groups do not have "
            f"exactly {CANONICAL_WEEKS_PER_YEAR} weeks after week-53 merge + "
            f"imputation:\n{bad_counts}"
        )

    if "is_imputed" not in df.columns:
        raise ValueError("is_imputed column missing.")
    if "is_reporting_anomaly" not in df.columns:
        raise ValueError("is_reporting_anomaly column missing.")

    logger.info(
        "Validation passed: %d rows, %d districts, interior years %d-%d each "
        "have exactly %d weeks, %d rows flagged is_imputed, %d rows flagged "
        "is_reporting_anomaly.",
        len(df), n_districts, min_year + 1, max_year - 1,
        CANONICAL_WEEKS_PER_YEAR, int(df["is_imputed"].sum()),
        int(df["is_reporting_anomaly"].sum()),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_module1_preprocessing() -> pd.DataFrame:
    MODULE1_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    epi, climate, population, calendar = load_shared_tables()

    epi = merge_week_53_cases(epi)
    climate = merge_week_53_climate(climate)

    missing = find_missing_weeks(epi)
    epi = impute_missing_weeks(epi, missing, calendar)
    epi = flag_reporting_anomalies(epi)

    table = merge_climate(epi, climate)
    table = merge_population(table, population)

    table = table.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    validate_weekly_modeling_table(table)

    table.to_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, index=False)
    logger.info(
        "Module 1 preprocessing complete: %d rows written to %s.",
        len(table), MODULE1_WEEKLY_MODELING_TABLE_PATH,
    )
    return table


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_module1_preprocessing()
