"""Module 2 (outbreak classification) preprocessing layer.

Reads the shared, module-agnostic base tables from `data/processed/shared/`
and applies Module 2's OWN temporal-adjustment decisions (Decision 013 - these
are independently decided, not inherited from Module 1, even where they
happen to match):

1. Epi-week 53 (2009, 2016, 2019, 2021) is kept as its OWN week, NOT merged
   into week 52 (deliberately diverges from Module 1's Decision 007, revised
   2026-07-28 after a dedicated preprocessing review - see
   `research_context/RESEARCH_DECISIONS.md` Decision 013's addendum). Module 1
   merges because SARIMA requires a fixed 52-week seasonal period; Module 2
   has no such requirement, and merging would SUM two real weeks' case counts
   into one bucket before the epidemic threshold is computed - risking a
   spurious "outbreak" label from the merge arithmetic itself, and
   contaminating week 52's cross-year historical_mean/SD (used by
   `label_definition.py`) for every other year, not just the four merged
   ones. Consequence: week 53 only occurs 4 times total, so it will almost
   always fail the 3-strictly-prior-years rule and get an undefined label -
   an honest reflection of insufficient history, not a defect.
2. Impute the remaining genuine missing weeks via seasonal-naive fill and flag
   them with `is_imputed` (same method as Module 1's Decision 011). This is
   still required even though Module 2 has no SARIMA-style algorithmic need
   for a gap-free series: Stage 1's lag/rolling features (`feature_engineering
   .py`) use `.shift()` per district, which silently misaligns if a calendar
   week is simply absent (the "next" row would be wrongly treated as "1 week
   ago"). Unlike Module 1, imputed rows here must be excluded not just from
   evaluation but from ever serving as an outbreak LABEL target, AND must be
   masked out of every case-derived feature that could see them (lags,
   rolling stats, anomaly lags) - a fabricated case count is not a real
   observation and must not silently bias either the label or a neighboring
   week's feature - enforced downstream in `src/module2_classification/
   labels.py` and `feature_engineering.py`, not here.
3. Merge in climate data on (District, Year, Week). `weather_code` is kept at
   this layer (same convention as Module 1) - its exclusion is a
   feature-selection choice made in `feature_engineering.py`, not here.
4. Merge in population and compute `cases_per_100k` as a reporting-only
   column (Decision 006) - not a modeling target.

Writes `data/processed/module2/weekly_modeling_table.csv`: one row per
District + Year + Week, 52 weeks/year for every interior (fully-covered) year
(53 for the four confirmed 53-week years), no duplicate keys, `is_imputed`
flag present, all climate columns present, population + `cases_per_100k`
present.
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
    MODULE2_PROCESSED_DIR,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
    SHARED_CLIMATE_WEEKLY_PATH,
    SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH,
    SHARED_EPI_WEEK_CALENDAR_PATH,
    SHARED_POPULATION_ANNUAL_PATH,
)

logger = logging.getLogger(__name__)

# Years with a genuine epi-week 53 - kept as its own week, NOT merged into
# week 52 (module docstring point 1). Still needed here to compute the
# correct "expected weeks" count per year for gap-detection/validation.
WEEK_53_YEARS = [2009, 2016, 2019, 2021]
DEFAULT_WEEKS_PER_YEAR = 52


def expected_weeks_for_year(year: int) -> set[int]:
    n_weeks = 53 if year in WEEK_53_YEARS else DEFAULT_WEEKS_PER_YEAR
    return set(range(1, n_weeks + 1))


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
# Step 1: seasonal-naive imputation of remaining genuine gaps
# ---------------------------------------------------------------------------
#
# NOTE: unlike Module 1, there is no week-53-merge step here (module docstring
# point 1) - week 53 rows pass through from the shared tables unchanged.

def find_missing_weeks(epi: pd.DataFrame) -> pd.DataFrame:
    """Find genuine (District, Year, Week) gaps within *interior* years only.

    The dataset's first and last years are partial by construction (case data
    starts mid-year 2006; the most recent year is still ongoing at scrape
    time) - excluded from the completeness check, same rationale as Module 1.
    Expected week count per year is 53 for `WEEK_53_YEARS`, 52 otherwise
    (`expected_weeks_for_year`).
    """
    min_year, max_year = epi["Year"].min(), epi["Year"].max()
    interior = epi[(epi["Year"] > min_year) & (epi["Year"] < max_year)]

    missing_rows = []
    for district in DISTRICTS:
        district_df = interior[interior["District"] == district]
        for year, group in district_df.groupby("Year"):
            present_weeks = set(group["Week"])
            expected_weeks = expected_weeks_for_year(int(year))
            for week in sorted(expected_weeks - present_weeks):
                missing_rows.append({"District": district, "Year": int(year), "Week": week})

    return pd.DataFrame(missing_rows, columns=["District", "Year", "Week"])


def impute_missing_weeks(epi: pd.DataFrame, missing: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    """Fill genuine gaps via seasonal-naive imputation: same district, same
    epi-week, mean `Number_of_Cases` across all other available years. Adds
    the `is_imputed` boolean flag (True for filled rows, False otherwise).

    Rows flagged `is_imputed=True` must never be used as an outbreak LABEL
    target downstream (a fabricated case count cannot honestly trigger or
    suppress an "outbreak" label) - enforced in `label_definition.py`, not
    here; this function only produces the flag.
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
            "%d imputed rows have no calendar date (see Module 1's "
            "documented '2020 Wk1' case in module_1_forecasting/MODULE_CONTEXT.md "
            "for why this can happen). Number_of_Cases is still imputed via "
            "seasonal-naive fill; Week_Start_Date/Week_End_Date are left as "
            "NaN rather than fabricated. Affected: %s",
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
    expected_counts = counts.index.get_level_values("Year").map(
        lambda y: 53 if y in WEEK_53_YEARS else DEFAULT_WEEKS_PER_YEAR
    )
    bad_counts = counts[counts.to_numpy() != expected_counts.to_numpy()]
    if not bad_counts.empty:
        raise ValueError(
            f"{len(bad_counts)} (District, Year) interior groups do not have "
            f"their expected week count (52, or 53 for {WEEK_53_YEARS}) after "
            f"imputation:\n{bad_counts}"
        )

    if "is_imputed" not in df.columns:
        raise ValueError("is_imputed column missing.")

    logger.info(
        "Validation passed: %d rows, %d districts, interior years %d-%d each "
        "have their expected week count (52, or 53 for %s), %d rows flagged "
        "is_imputed.",
        len(df), n_districts, min_year + 1, max_year - 1,
        WEEK_53_YEARS, int(df["is_imputed"].sum()),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_module2_preprocessing() -> pd.DataFrame:
    MODULE2_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    epi, climate, population, calendar = load_shared_tables()

    missing = find_missing_weeks(epi)
    epi = impute_missing_weeks(epi, missing, calendar)

    table = merge_climate(epi, climate)
    table = merge_population(table, population)

    table = table.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    validate_weekly_modeling_table(table)

    table.to_csv(MODULE2_WEEKLY_MODELING_TABLE_PATH, index=False)
    logger.info(
        "Module 2 preprocessing complete: %d rows written to %s.",
        len(table), MODULE2_WEEKLY_MODELING_TABLE_PATH,
    )
    return table


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_module2_preprocessing()
