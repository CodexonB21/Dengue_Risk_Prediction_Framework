# Data Dictionary

This document describes the currently available datasets and expected transformations.

Update this file whenever new columns, new datasets, or changed preprocessing rules are introduced.

---

# 1. Epidemiological Dataset

## Granularity
Weekly district-level dengue case counts.

## Columns

| Column | Description | Current Role |
|---|---|---|
| District | Administrative district name | Used for district-wise segmentation |
| Number_of_Cases | Weekly reported dengue case count | Target for Module 1 Stage 1 |
| Week_Start_Date | Start date of epidemiological week | Time ordering and merging |
| Month | Calendar month | Context / optional checking |
| Year | Calendar year | Temporal split and trend reference |
| Week | Epidemiological week number | Seasonal encoding and seasonal period |
| Week_End_Date | End date of epidemiological week | Time ordering and merging |

## Example

```text
District,Number_of_Cases,Week_Start_Date,Month,Year,Week,Week_End_Date
Ampara,0,12/23/2006,12,2006,52,12/29/2006
```

## Epidemiological Week Definition

Weeks follow the **Sri Lanka Ministry of Health (MoH) epidemiological week standard**, scraped directly from the official MoH source. This is not a plain ISO calendar week.

- Full coverage: 2006-12-23 to 2026-06-21 (~19.5 years).
- Some weeks are missing from the source website (see Data Quality Notes below).
- Some years contain 53 epi-weeks instead of 52 (see Decision 007 in `RESEARCH_DECISIONS.md` for the merge rule adopted to keep SARIMA's seasonal period consistent). Confirmed 53-week years: **2009, 2016, 2019, 2021**.
- A master `(Year, Week) → (Week_Start_Date, Week_End_Date)` lookup table (sourced from the same MoH scrape) should be used as the single source of truth for aligning daily climate records to epi-weeks, rather than deriving week boundaries independently in each dataset.
- **Validated (2026-07-26):** `data/raw/epidemiological/dengue_cases_corected.csv` was manually audited and corrected. Five week-boundary collisions (duplicate `(District, Year, Week)` labels caused by scraping/entry errors spanning 2010, 2012/2013, 2014, and 2022/2023) were identified and fixed by the team. The file now has **zero duplicate `(District, Year, Week)` rows** and zero negative case values. See `scripts/data_audit_module1.py` for the reusable audit used to verify this (safe to re-run after any future edits to the raw file).

## Zero-Inflation Note

Most weeks across most districts report zero cases. This has direct modeling implications (log-transform failure, MAPE instability, possible SARIMA appropriateness limits for very sparse districts) — see `module_1_forecasting/MODULE_CONTEXT.md` open questions and `RESEARCH_DECISIONS.md` Decision 011.

---

# 2. Meteorological Dataset

## Granularity
Daily per district.

## Spatial Resolution Caveat

Climate data is sourced from Open-Meteo at a **single point per district** (not a district-wide spatial average). This is a known constraint of the data source, not a processing choice. Larger districts may have reduced spatial representativeness. This limitation should be stated explicitly in any write-up rather than left implicit.

## Data Coverage
2007-01-01 to 2026-05-22, per district, daily. Starts slightly after the earliest case data (case data begins 12/23/2006), leaving a small leading-edge gap — see Data Quality Notes. Verified: zero missing calendar days and zero duplicate dates within range (checked across sampled districts).

## Source Folder Structure (Validated 2026-07-26; path updated 2026-07-27)

All 25 per-district weather CSVs live **flat** in `data/raw/weather/` (e.g. `data/raw/weather/open-meteo-6.92N79.91E4m Colombo.csv`) — there are no subfolders.

This is the result of a cleanup: the raw source originally shipped as two subfolders, `Weather (Except Humidity)/` and `Humidity/`. The audit found that `Weather (Except Humidity)/` (despite its name) already contained the **full 13-column set** (humidity, temperature, apparent temperature, rain/precipitation, weather code) for all 25 official districts, and that `Humidity/` was byte-for-byte identical on its 4 overlapping columns (Colombo cross-check: 0 mismatched rows across 7,081 dates) — i.e. fully redundant. The user subsequently deleted `Humidity/` and flattened `Weather (Except Humidity)/` directly into `data/raw/weather/`. Any pipeline code should read weather CSVs directly from `data/raw/weather/*.csv`.

## Columns

| Column | Description | Planned Weekly Aggregation |
|---|---|---|
| time | Date | Map to epidemiological week |
| relative_humidity_2m_mean (%) | Daily mean relative humidity | Weekly mean |
| relative_humidity_2m_max (%) | Daily maximum relative humidity | Weekly mean of daily max |
| relative_humidity_2m_min (%) | Daily minimum relative humidity | Weekly mean of daily min |
| temperature_2m_max (°C) | Daily maximum temperature | Weekly mean of daily max |
| temperature_2m_min (°C) | Daily minimum temperature | Weekly mean of daily min |
| apparent_temperature_mean (°C) | Daily mean apparent temperature | Optional weekly mean |
| apparent_temperature_max (°C) | Daily max apparent temperature | Optional weekly mean |
| apparent_temperature_min (°C) | Daily min apparent temperature | Optional weekly mean |
| temperature_2m_mean (°C) | Daily mean temperature | Weekly mean |
| rain_sum (mm) | Daily rain sum | Weekly sum |
| precipitation_sum (mm) | Daily precipitation sum | Weekly sum |
| weather_code (wmo code) | Categorical weather code | Excluded from Module 1 features (see Decision 008) |

---

# 3. Population / Census Dataset

## Granularity
Per district, per census year only.

## Columns
Population count per district for census years: **2001, 2012, 2024**.

## Role
Not a Stage 1 modeling input. Used to compute cases-per-100,000 as a **reporting/evaluation-layer** metric for cross-district comparability (see Decision 006). The Stage 1 SARIMA target remains raw `Number_of_Cases`.

## Interpolation Policy
- 2001–2012 and 2012–2024: linear interpolation (or constant growth-rate model) between census points to estimate annual population per district.
- 2025–2026: falls after the last census point and requires extrapolation. Flag any incidence figures in this range as based on extrapolated population and treat with reduced confidence.

---

# 4. Transformation Pipeline

```text
Daily climate records
  ↓
Weekly aggregation per district
  ↓
Merge with weekly dengue case data
  ↓
Create temporal features and climate features
  ↓
Run baseline model
  ↓
Extract residual/error
  ↓
Train compensation model
```

---

# 5. Current Weekly Aggregation Rules

## Rainfall / Precipitation

```text
weekly_rainfall = sum(rain_sum)
weekly_precipitation = sum(precipitation_sum)
```

## Temperature

```text
weekly_temperature_mean = mean(temperature_2m_mean)
weekly_temperature_max_mean = mean(temperature_2m_max)
weekly_temperature_min_mean = mean(temperature_2m_min)
```

## Humidity

```text
weekly_humidity_mean = mean(relative_humidity_2m_mean)
weekly_humidity_max_mean = mean(relative_humidity_2m_max)
weekly_humidity_min_mean = mean(relative_humidity_2m_min)
```

---

# 6. Final Modeling Unit

One row should represent:

```text
District + Epidemiological Week + Year
```

Each row also carries an `is_imputed` flag (see Decision 011) marking whether `Number_of_Cases` for that row was imputed due to a missing source week.

---

# 7. Data Quality Notes

Record future data issues here.

| Issue | Status | Resolution |
|---|---|---|
| Date alignment between daily climate and epidemiological weeks | Resolved | Use master MoH epi-week lookup table `(Year, Week) → (Start, End)` as single source of truth for aggregation |
| Duplicate `(District, Year, Week)` rows from week-boundary collisions (2010, 2012/2013, 2014, 2022/2023) | **Resolved (2026-07-26)** | Manually corrected in `dengue_cases_corected.csv` after joint audit (relabeled/retimestamped 5 collision points across all districts). Verified via `scripts/data_audit_module1.py`: 0 duplicate rows remain |
| District name typos (`Moneragala`, `Puttlam` single-row variants) | **Resolved (2026-07-26)** | Corrected to `Monaragala`/`Puttalam` as part of the same data cleanup pass |
| `Kalmunai` has no matching weather station | **Resolved (policy set, 2026-07-26)** | Merge Kalmunai's case counts into Ampara (sum) and use Ampara's climate series for the combined series. See Decision 012 |
| `Humidity/` weather subfolder is redundant | **Resolved (2026-07-26); files cleaned up (2026-07-27)** | Confirmed byte-identical to the humidity columns in the other subfolder. User deleted `Humidity/` and flattened the canonical weather CSVs directly into `data/raw/weather/` (no subfolders remain) |
| Missing dengue weeks (gaps in source website scrape) | Resolved (policy set) — **confirmed remaining gaps: Ampara, Kilinochchi, Mullaitivu (1 week each), Kalmunai (3 weeks)** | Impute via seasonal-naive (same district, same epi-week average across years) and flag with `is_imputed`; excluded from evaluation metrics and Stage 2 targets. See Decision 011 |
| 53-week years | Resolved (policy set) — **confirmed years: 2009, 2016, 2019, 2021** | Merge week 53 into week 52 (sum cases, average climate) to keep SARIMA seasonal period fixed at m=52. See Decision 007 |
| Leading-edge gap: case data starts 12/23/2006, climate starts 1/1/2007 | Open (low priority) | Stage 1 unaffected (case-only); Stage 2 climate features effectively start once climate coverage begins |
| Column encoding corruption (e.g. `Â°C` mojibake) | **Resolved — not a real issue** | Verified via raw byte inspection: files are genuine UTF-8 (`Â°C` was a chat-copy-paste display artifact, not a file defect). No ingestion fix needed beyond reading as UTF-8 |
| Choice between rain_sum and precipitation_sum | Open | Compare definitions and consistency |
| District name consistency across case/climate datasets | Resolved | Verified matching for all 25 official districts; Kalmunai handled separately (see above) |
| Zero-inflation (most weeks report zero cases in many districts) | **Refined (2026-07-26)** — not universal | Pooled zero-week rate is 13.7%, concentrated in `Mullaitivu` (52.8%), `Kilinochchi` (47.7%), `Mannar` (40.4%), `Ampara` (32.9%), `Vavuniya` (32.3%); high-incidence districts (`Colombo` 0.5%, `Kandy` 1.4%) are near-zero. SARIMA-appropriateness question applies mainly to the sparse Northern/Eastern districts. See `module_1_forecasting/MODULE_CONTEXT.md` |
| Climate data spatial resolution (single point per district) | Documented limitation | Acknowledged as an Open-Meteo data source constraint; not fixable, must be stated in write-up |
