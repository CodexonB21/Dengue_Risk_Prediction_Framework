"""Shared, module-agnostic preprocessing layer.

Reads raw source files from `data/raw/` and writes the shared clean base
tables in `data/processed/shared/` that Module 1, 2, and 3 all build on.

Per Decision 013 (`research_context/RESEARCH_DECISIONS.md`), this file
contains ONLY transformations every module would make the same way for the
same reason:

1. Merge Kalmunai's case counts into Ampara (Decision 012).
2. Build the master MoH epi-week calendar (mode date-pair per (Year, Week)).
3. Aggregate daily climate to epi-weeks using that master calendar, keeping
   every raw climate measurement column.
4. Interpolate/extrapolate census population to an annual series
   (Decision 006).
5. Write a cleaned, non-imputed, non-week-53-merged case table.

Explicitly NOT done here (Module-1-scoped, see `module1_preprocessing.py`):
week-53 merging (Decision 007), missing-week imputation/`is_imputed`
flagging (Decision 011), and `weather_code` exclusion (Decision 008).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    RAW_EPI_PATH,
    RAW_POPULATION_PATH,
    RAW_WEATHER_DIR,
    SHARED_CLIMATE_WEEKLY_PATH,
    SHARED_DIR,
    SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH,
    SHARED_EPI_WEEK_CALENDAR_PATH,
    SHARED_POPULATION_ANNUAL_PATH,
)

logger = logging.getLogger(__name__)

KALMUNAI_SOURCE_NAME = "Kalmunai"
KALMUNAI_MERGE_TARGET = "Ampara"

# Weekly aggregation rules (DATA_DICTIONARY.md Section 5). `weather_code` is
# categorical (WMO code); there is no upstream-specified rule for collapsing
# it to a weekly value, so the weekly-mode (most frequent daily code that
# week) is used as a reasonable representative value. This is a shared-layer
# implementation choice, not a research decision - flagged in the doc update
# for this session.
CLIMATE_SUM_COLUMNS = ["rain_sum (mm)", "precipitation_sum (mm)"]
CLIMATE_MEAN_COLUMNS = [
    "relative_humidity_2m_mean (%)",
    "relative_humidity_2m_max (%)",
    "relative_humidity_2m_min (%)",
    "temperature_2m_max (°C)",
    "temperature_2m_min (°C)",
    "apparent_temperature_mean (°C)",
    "apparent_temperature_max (°C)",
    "apparent_temperature_min (°C)",
    "temperature_2m_mean (°C)",
]
CLIMATE_MODE_COLUMN = "weather_code (wmo code)"

POPULATION_CENSUS_YEARS = (2001, 2012, 2024)
POPULATION_OUTPUT_YEARS = range(2006, 2027)  # 2006-2026 inclusive


# ---------------------------------------------------------------------------
# Step 1 + inputs: load raw epidemiological data, merge Kalmunai -> Ampara
# ---------------------------------------------------------------------------

def load_raw_epidemiological(path: Path = RAW_EPI_PATH) -> pd.DataFrame:
    """Load the corrected raw case file with dates parsed as datetimes."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Week_Start_Date"] = pd.to_datetime(df["Week_Start_Date"], format="mixed", dayfirst=False)
    df["Week_End_Date"] = pd.to_datetime(df["Week_End_Date"], format="mixed", dayfirst=False)
    return df


def merge_kalmunai_into_ampara(epi_raw: pd.DataFrame) -> pd.DataFrame:
    """Sum `Number_of_Cases` per (District, Year, Week), folding Kalmunai into
    Ampara (Decision 012).

    A week missing for one of the pair but present for the other yields the
    present value (groupby.sum only sums rows that actually exist - nothing
    is fabricated). A week missing for BOTH stays absent from the result.

    Returns a 25-district (District, Year, Week, Number_of_Cases) table.
    """
    remapped = epi_raw.copy()
    remapped["District"] = remapped["District"].replace(
        KALMUNAI_SOURCE_NAME, KALMUNAI_MERGE_TARGET
    )

    merged_cases = (
        remapped.groupby(["District", "Year", "Week"], as_index=False)["Number_of_Cases"]
        .sum()
    )

    n_districts = merged_cases["District"].nunique()
    if n_districts != len(DISTRICTS):
        raise ValueError(
            f"Expected {len(DISTRICTS)} districts after Kalmunai merge, "
            f"got {n_districts}: {sorted(merged_cases['District'].unique())}"
        )
    unexpected = set(merged_cases["District"].unique()) - set(DISTRICTS)
    if unexpected:
        raise ValueError(f"Unexpected district names after merge: {sorted(unexpected)}")

    return merged_cases


# ---------------------------------------------------------------------------
# Step 2: master epi-week calendar
# ---------------------------------------------------------------------------

def build_epi_week_calendar(epi_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the master (Year, Week) -> (Week_Start_Date, Week_End_Date)
    calendar and a diagnostic table of rows that disagree with it.

    The mode is computed across ALL raw district rows for each (Year, Week)
    label, including Kalmunai's own row (before it is folded into Ampara).
    This is equivalent to computing it "across all 25 districts" post-merge:
    since the mode is per (Year, Week) regardless of which district
    contributed the row, having Kalmunai as an extra corroborating (or
    dissenting) vote for a handful of weeks does not change the interpretation
    - it just means a small number of (Year, Week) labels get up to 26 votes
    instead of exactly 25. This is called out explicitly because the plan
    text says "across all 25 districts"; see the implementation note recorded
    in `module_1_forecasting/MODULE_CONTEXT.md` for this session.

    Returns:
        (calendar, disagreements) - `calendar` has one row per (Year, Week);
        `disagreements` lists every raw row whose own date pair did not match
        the chosen mode for its (Year, Week), for the mandatory spot-check.
    """
    pairs = epi_raw[["District", "Year", "Week", "Week_Start_Date", "Week_End_Date"]]

    calendar_rows = []
    disagreement_rows = []

    for (year, week), group in pairs.groupby(["Year", "Week"]):
        counts = (
            group.groupby(["Week_Start_Date", "Week_End_Date"])
            .size()
            .sort_values(ascending=False)
        )
        top_count = counts.iloc[0]
        tied = counts[counts == top_count]

        if len(tied) > 1:
            # Deterministic tie-break: earliest date pair. Logged so a human
            # can spot-check every tie before trusting the calendar.
            chosen = sorted(tied.index.tolist())[0]
            logger.warning(
                "Calendar tie for Year=%s Week=%s: %d date-pairs tied at %d "
                "votes each; picked earliest %s as tie-break.",
                year, week, len(tied), top_count, chosen,
            )
        else:
            chosen = counts.index[0]

        start, end = chosen
        calendar_rows.append(
            {"Year": year, "Week": week, "Week_Start_Date": start, "Week_End_Date": end}
        )

        mismatched = group[
            (group["Week_Start_Date"] != start) | (group["Week_End_Date"] != end)
        ]
        for _, row in mismatched.iterrows():
            disagreement_rows.append(
                {
                    "District": row["District"],
                    "Year": year,
                    "Week": week,
                    "row_Week_Start_Date": row["Week_Start_Date"],
                    "row_Week_End_Date": row["Week_End_Date"],
                    "calendar_Week_Start_Date": start,
                    "calendar_Week_End_Date": end,
                }
            )

    calendar = (
        pd.DataFrame(calendar_rows).sort_values(["Year", "Week"]).reset_index(drop=True)
    )
    disagreements = pd.DataFrame(disagreement_rows)

    if not disagreements.empty:
        logger.warning(
            "%d raw epi rows disagree with the master calendar for their "
            "(Year, Week) label - see epi_week_calendar_disagreements.csv.",
            len(disagreements),
        )

    return calendar, disagreements


def find_calendar_chronology_issues(calendar: pd.DataFrame) -> pd.DataFrame:
    """Flag any (Year, Week) whose date range overlaps with (or precedes) its
    immediate predecessor once the whole calendar is sorted by date.

    The majority-vote calendar (above) resolves disagreements BETWEEN
    districts for the same (Year, Week) label, but cannot detect a (Year,
    Week) label where ALL or nearly all raw rows agree on a date that is
    nonetheless wrong relative to neighbouring weeks - a systematic per-week
    scrape error (e.g. the whole source page for that week was mis-dated),
    not a per-row wobble. This is a genuinely different failure mode from the
    ones the 2026-07-26 audit fixed (which were per-row duplicate-key
    collisions); it was discovered while spot-checking this step, as
    instructed, and is recorded as a new open item rather than silently
    patched here - see `module_1_forecasting/MODULE_CONTEXT.md`.
    """
    ordered = calendar.sort_values("Week_Start_Date").reset_index(drop=True)
    prev_end = ordered["Week_End_Date"].shift(1)
    prev_year = ordered["Year"].shift(1)
    prev_week = ordered["Week"].shift(1)
    bad = ordered["Week_Start_Date"] <= prev_end

    issues = ordered[bad].copy()
    if not issues.empty:
        issues["previous_Year"] = prev_year[bad]
        issues["previous_Week"] = prev_week[bad]
        issues["previous_Week_End_Date"] = prev_end[bad]
        logger.warning(
            "%d calendar weeks overlap with (or precede) their chronological "
            "predecessor - likely systematic per-week date-scrape errors "
            "affecting all districts equally (so they don't surface as "
            "per-row disagreements). See "
            "epi_week_calendar_chronology_issues.csv.",
            len(issues),
        )
    return issues


def _infer_gap_label(cur_year: int, cur_week: int, next_year: int, next_week: int):
    """Return the (Year, Week) label that fits exactly between two
    chronologically-adjacent calendar rows, or None if it can't be
    determined unambiguously (e.g. spans a 52/53-week year boundary in an
    unexpected way)."""
    if next_year == cur_year and next_week == cur_week + 2:
        return cur_year, cur_week + 1
    if next_year == cur_year + 1 and next_week == 2 and cur_week >= 52:
        return next_year, 1
    return None


def fill_isolated_calendar_gaps(calendar: pd.DataFrame) -> pd.DataFrame:
    """Infer any single-week (Year, Week) gap that is completely absent from
    the raw-vote calendar (i.e. NO district has any raw row for that week at
    all - a nationwide source outage, e.g. Decision 011's confirmed
    `2015 Wk30`, `2020 Wk1`, `2021 Wk42`, `2022 Wk43`) by sequential
    extrapolation, but ONLY when it fits a clean, unambiguous single 7-day
    slot between two known neighbouring weeks (their dates are exactly 8
    days apart).

    This is a different failure mode from `build_epi_week_calendar`'s
    tie-break logic: that handles weeks that DO have raw votes (just
    possibly disagreeing ones); this handles weeks with ZERO raw votes.
    Ambiguous or multi-week gaps are left alone and logged, not guessed at.

    Critically, an 8-day gap in the DATE-sorted view can also be produced by
    a week whose label already exists elsewhere in the calendar but with a
    wrong (chronology-issue) date - that case must NOT be filled here (it
    would create a duplicate (Year, Week) calendar row); it is already
    covered by `find_calendar_chronology_issues`. Only genuinely absent
    labels (checked against the full existing label set) are inferred.

    This was added after spot-checking the calendar (as instructed) revealed
    the 4 confirmed nationwide gap weeks would otherwise have no date at all
    downstream - see the implementation note recorded in
    `module_1_forecasting/MODULE_CONTEXT.md`.
    """
    existing_labels = set(zip(calendar["Year"], calendar["Week"]))
    ordered = calendar.sort_values("Week_Start_Date").reset_index(drop=True)
    inferred_rows = []

    for i in range(len(ordered) - 1):
        cur = ordered.iloc[i]
        nxt = ordered.iloc[i + 1]
        gap_days = (nxt["Week_Start_Date"] - cur["Week_End_Date"]).days

        if gap_days == 8:
            label = _infer_gap_label(cur["Year"], cur["Week"], nxt["Year"], nxt["Week"])
            if label is None:
                logger.warning(
                    "8-day calendar gap between %s Wk%s and %s Wk%s could "
                    "not be assigned an unambiguous (Year, Week) label - "
                    "left unfilled.",
                    cur["Year"], cur["Week"], nxt["Year"], nxt["Week"],
                )
                continue
            gap_year, gap_week = label
            if (gap_year, gap_week) in existing_labels:
                # The label already exists elsewhere in the calendar with a
                # wrong date (a chronology issue, not a genuine absence) -
                # inserting a second row for it would create a duplicate key.
                logger.warning(
                    "8-day date gap between %s Wk%s and %s Wk%s looks like a "
                    "missing Year=%s Week=%s, but that label already exists "
                    "elsewhere in the calendar with a different (likely "
                    "wrong) date - not inserting a duplicate; see "
                    "epi_week_calendar_chronology_issues.csv instead.",
                    cur["Year"], cur["Week"], nxt["Year"], nxt["Week"],
                    gap_year, gap_week,
                )
                continue
            gap_start = cur["Week_End_Date"] + pd.Timedelta(days=1)
            gap_end = gap_start + pd.Timedelta(days=6)
            inferred_rows.append(
                {"Year": gap_year, "Week": gap_week, "Week_Start_Date": gap_start, "Week_End_Date": gap_end}
            )
            logger.warning(
                "Inferred calendar entry for Year=%s Week=%s (%s to %s) - no "
                "raw source row exists for ANY district this week "
                "(nationwide scrape gap); dates sequentially extrapolated "
                "from neighbouring weeks, not sourced from raw data.",
                gap_year, gap_week, gap_start.date(), gap_end.date(),
            )
        elif gap_days > 8:
            logger.warning(
                "Calendar gap of %d days (> 1 week) between %s Wk%s and %s "
                "Wk%s - not auto-filled (ambiguous how many weeks are "
                "missing).",
                gap_days, cur["Year"], cur["Week"], nxt["Year"], nxt["Week"],
            )

    if not inferred_rows:
        return calendar

    result = pd.concat([calendar, pd.DataFrame(inferred_rows)], ignore_index=True)
    return result.sort_values(["Year", "Week"]).reset_index(drop=True)


def _build_day_to_week_lookup(calendar: pd.DataFrame) -> pd.DataFrame:
    """Expand the calendar's weekly date ranges into a day -> (Year, Week)
    lookup table, used to assign daily climate records to epi-weeks."""
    frames = []
    for row in calendar.itertuples(index=False):
        days = pd.date_range(row.Week_Start_Date, row.Week_End_Date, freq="D")
        frames.append(pd.DataFrame({"time": days, "Year": row.Year, "Week": row.Week}))
    lookup = pd.concat(frames, ignore_index=True)

    n_dupes = lookup["time"].duplicated().sum()
    if n_dupes:
        logger.warning(
            "%d calendar days map to more than one epi-week (overlapping "
            "week ranges) - keeping the first mapping for each day.",
            int(n_dupes),
        )
        lookup = lookup.drop_duplicates(subset="time", keep="first")

    return lookup


# ---------------------------------------------------------------------------
# Step 3: aggregate daily climate to epi-weeks
# ---------------------------------------------------------------------------

def district_from_weather_filename(path: Path) -> str:
    """Extract the district name from an Open-Meteo export filename, e.g.
    'open-meteo-6.92N79.91E4m Colombo.csv' -> 'Colombo'. Mirrors
    `scripts/data_audit_module1.py`'s convention for consistency."""
    stem = path.stem
    parts = stem.split(" ", 1)
    return parts[1].strip() if len(parts) > 1 else stem.strip()


def load_weather_file(path: Path) -> pd.DataFrame:
    """Load one per-district Open-Meteo CSV, skipping its metadata preamble
    (lat/lon/elevation/timezone rows) to find the real header row."""
    with open(path, "r", encoding="utf-8-sig") as fh:
        preamble = [fh.readline() for _ in range(6)]
    header_idx = next(
        (i for i, line in enumerate(preamble) if line.lower().startswith("time,")), None
    )
    if header_idx is None:
        raise ValueError(f"Could not find a 'time,...' header row in {path}")

    df = pd.read_csv(path, skiprows=header_idx, encoding="utf-8-sig")
    # Dates are inconsistently formatted across files (24/25 use ISO
    # YYYY-MM-DD, one - Colombo - uses M/D/Y); parse per-element rather than
    # assuming a single format.
    df["time"] = pd.to_datetime(df["time"], format="mixed", dayfirst=False)
    return df


def aggregate_climate_weekly(
    calendar: pd.DataFrame, weather_dir: Path = RAW_WEATHER_DIR
) -> pd.DataFrame:
    """Aggregate daily per-district climate to epi-weeks using the master
    calendar (not each row's own date). All 12 non-`time` raw climate
    measurement columns are retained (the 13th raw column, `time`, is by
    definition replaced by `Year`/`Week` once aggregated to weekly - nothing
    is dropped, see the doc note recorded for this session).
    """
    lookup = _build_day_to_week_lookup(calendar)
    files = sorted(weather_dir.glob("*.csv"))

    if len(files) != len(DISTRICTS):
        raise ValueError(f"Expected {len(DISTRICTS)} weather files, found {len(files)}")

    weekly_frames = []
    for f in files:
        district = district_from_weather_filename(f)
        if district not in DISTRICTS:
            raise ValueError(f"Weather file '{f.name}' parsed to unexpected district '{district}'")

        daily = load_weather_file(f)
        daily = daily.merge(lookup, on="time", how="inner")

        agg_spec = {col: "sum" for col in CLIMATE_SUM_COLUMNS}
        agg_spec.update({col: "mean" for col in CLIMATE_MEAN_COLUMNS})
        weekly = daily.groupby(["Year", "Week"], as_index=False).agg(agg_spec)

        weekly_mode = (
            daily.groupby(["Year", "Week"])[CLIMATE_MODE_COLUMN]
            .agg(lambda s: s.mode().sort_values().iloc[0] if not s.mode().empty else np.nan)
            .reset_index()
        )
        weekly = weekly.merge(weekly_mode, on=["Year", "Week"], how="left")

        weekly.insert(0, "District", district)
        weekly_frames.append(weekly)

    climate_weekly = pd.concat(weekly_frames, ignore_index=True)
    return climate_weekly.sort_values(["District", "Year", "Week"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 4: population interpolation
# ---------------------------------------------------------------------------

def interpolate_population(path: Path = RAW_POPULATION_PATH) -> pd.DataFrame:
    """Melt the wide census file to long format and linearly
    interpolate/extrapolate to an annual series (Decision 006, finalized).

    - 2001<=year<=2012: interpolate between the 2001 and 2012 census points.
    - 2012<=year<=2024: interpolate between the 2012 and 2024 census points.
    - 2025-2026: extrapolate forward using the district's own 2012->2024
      linear slope.
    - Output covers 2006-2026 (the case/climate data's coverage window).

    Known limitation (DATA_DICTIONARY.md Section 3): Kilinochchi, Mullaitivu,
    and Mannar have a non-monotonic 2001->2012->2024 trend (sharp decline
    then recovery, consistent with civil-war-era displacement in the Vanni
    region ending 2009). Linear interpolation cannot recover the true
    2007-2012 population path for these 3 districts - this is a real,
    structural data limitation (no better annual estimate exists), not
    something silently smoothed over here. Because population is a
    reporting-layer-only denominator (Decision 006), it never touches the
    Stage 1 SARIMA target, but any `cases_per_100k` figure for these 3
    districts in 2007-2012 should be treated as lower-confidence.
    """
    wide = pd.read_csv(path)

    long = wide.melt(
        id_vars="District",
        value_vars=[f"Population_{y}" for y in POPULATION_CENSUS_YEARS],
        var_name="census_year_col",
        value_name="Population",
    )
    long["Year"] = long["census_year_col"].str.extract(r"(\d{4})").astype(int)
    long = long.drop(columns="census_year_col")

    file_districts = set(long["District"])
    if file_districts != set(DISTRICTS):
        raise ValueError(
            "Population file districts do not match the 25-district DISTRICTS "
            f"list. Missing: {set(DISTRICTS) - file_districts}, "
            f"Unexpected: {file_districts - set(DISTRICTS)}"
        )

    records = []
    for district, group in long.groupby("District"):
        census = group.set_index("Year")["Population"].to_dict()
        pop_2001, pop_2012, pop_2024 = (
            census[POPULATION_CENSUS_YEARS[0]],
            census[POPULATION_CENSUS_YEARS[1]],
            census[POPULATION_CENSUS_YEARS[2]],
        )
        slope_2012_2024 = (pop_2024 - pop_2012) / (POPULATION_CENSUS_YEARS[2] - POPULATION_CENSUS_YEARS[1])

        for year in POPULATION_OUTPUT_YEARS:
            if year in POPULATION_CENSUS_YEARS:
                pop = census[year]
                source_type = "census"
            elif year < POPULATION_CENSUS_YEARS[1]:
                pop = pop_2001 + (pop_2012 - pop_2001) * (year - POPULATION_CENSUS_YEARS[0]) / (
                    POPULATION_CENSUS_YEARS[1] - POPULATION_CENSUS_YEARS[0]
                )
                source_type = "interpolated"
            elif year <= POPULATION_CENSUS_YEARS[2]:
                pop = pop_2012 + (pop_2024 - pop_2012) * (year - POPULATION_CENSUS_YEARS[1]) / (
                    POPULATION_CENSUS_YEARS[2] - POPULATION_CENSUS_YEARS[1]
                )
                source_type = "interpolated"
            else:
                pop = pop_2024 + slope_2012_2024 * (year - POPULATION_CENSUS_YEARS[2])
                source_type = "extrapolated"

            records.append(
                {
                    "District": district,
                    "Year": year,
                    "Estimated_Population": pop,
                    "Source_Type": source_type,
                }
            )

    result = pd.DataFrame(records)
    result["Estimated_Population"] = result["Estimated_Population"].round().astype(int)
    return result.sort_values(["District", "Year"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 5: cleaned, non-imputed, non-week-53-merged case table
# ---------------------------------------------------------------------------

def build_epidemiological_weekly(
    merged_cases: pd.DataFrame, calendar: pd.DataFrame
) -> pd.DataFrame:
    """Attach the master calendar's canonical dates to the Kalmunai-merged
    case table. Real gaps stay as absent rows; 53-week years stay as 53 rows.
    No week-53 merging or imputation happens here (Module-1-scoped, see
    `module1_preprocessing.py`).
    """
    result = merged_cases.merge(calendar, on=["Year", "Week"], how="left")

    n_missing_calendar = result["Week_Start_Date"].isna().sum()
    if n_missing_calendar:
        logger.warning(
            "%d case rows have no matching calendar entry for their "
            "(Year, Week) label.",
            int(n_missing_calendar),
        )

    return result[
        ["District", "Year", "Week", "Week_Start_Date", "Week_End_Date", "Number_of_Cases"]
    ].sort_values(["District", "Year", "Week"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_shared_preprocessing() -> None:
    SHARED_DIR.mkdir(parents=True, exist_ok=True)

    epi_raw = load_raw_epidemiological()
    calendar, disagreements = build_epi_week_calendar(epi_raw)
    calendar = fill_isolated_calendar_gaps(calendar)
    chronology_issues = find_calendar_chronology_issues(calendar)
    merged_cases = merge_kalmunai_into_ampara(epi_raw)
    epidemiological_weekly = build_epidemiological_weekly(merged_cases, calendar)
    climate_weekly = aggregate_climate_weekly(calendar)
    population_annual = interpolate_population()

    calendar.to_csv(SHARED_EPI_WEEK_CALENDAR_PATH, index=False)
    climate_weekly.to_csv(SHARED_CLIMATE_WEEKLY_PATH, index=False)
    population_annual.to_csv(SHARED_POPULATION_ANNUAL_PATH, index=False)
    epidemiological_weekly.to_csv(SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH, index=False)

    if not disagreements.empty:
        disagreements.to_csv(SHARED_DIR / "epi_week_calendar_disagreements.csv", index=False)
    if not chronology_issues.empty:
        chronology_issues.to_csv(
            SHARED_DIR / "epi_week_calendar_chronology_issues.csv", index=False
        )

    logger.info(
        "Shared preprocessing complete: %d calendar weeks, %d climate rows, "
        "%d population rows, %d epi rows written to %s.",
        len(calendar), len(climate_weekly), len(population_annual),
        len(epidemiological_weekly), SHARED_DIR,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_shared_preprocessing()
