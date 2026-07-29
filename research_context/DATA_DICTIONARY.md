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
2007-01-01 through daily refresh (Open-Meteo Archive + Forecast APIs via
`scripts/fetch_open_meteo_weather.py`). As of 2026-07-29 refresh: observed daily
through yesterday, forecast daily ~16 days ahead. Weekly aggregation via master
epi-week calendar in `shared.py`.

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
| climate_data_source | `observed` or `forecast` (daily level; optional — defaults to `observed` if absent) | Propagated to weekly via majority vote in `climate_weekly.csv` |

## Operational outputs (Decision 027)

| File | Description |
|---|---|
| `data/processed/module1/future_forecast.csv` | M1 forward case forecast (8 weeks), `feature_completeness_pct` |
| `data/processed/module2/live_risk_predictions.csv` | M2 recent-week risk (default last 8 weeks) |
| `data/processed/module2/future_risk_predictions.csv` | M2 forward operational risk; columns include `horizon_step`, `cases_source`, `climate_source`, `uses_module1_cases`, `evidence_tier=operational` |
| `data/raw/weather/climate_fetch_manifest.csv` | Per-district fetch log from Open-Meteo refresh |

---

# 3. Population / Census Dataset

## Source File (placed 2026-07-27)
`data/raw/population/population_by_district.csv` — wide format, one row per district:

```text
District,Population_2001,Population_2012,Population_2024
Kandy,1279028,1375382,1461895
...
```

## Granularity
Per district, per census year only. Sri Lanka runs a national census roughly once per
decade, so only three data points exist per district — this is a real, structural data
limitation, not a collection gap that more scraping could fix.

## Columns
Population count per district for census years: **2001, 2012, 2024**.

## Coverage Check (2026-07-27)
25 rows, exact 1:1 match against the 25-district modeling list in `src/config.py`
(post Kalmunai→Ampara merge, Decision 012). `Kalmunai` correctly has **no separate
row**: it is a divisional secretariat within Ampara District administratively, so its
population is already counted inside Ampara's census total — no adjustment needed.

## District Name Correction (2026-07-27)
The source used `Moneragala`; corrected to `Monaragala` in the saved file to match the
canonical spelling used everywhere else in the pipeline (the epidemiological dataset
had the same typo, fixed during the 2026-07-26 audit — see Data Quality Notes).

## Role
Not a Stage 1 modeling input. Used to compute cases-per-100,000 as a **reporting/evaluation-layer** metric for cross-district comparability (see Decision 006). The Stage 1 SARIMA target remains raw `Number_of_Cases`.

## Interpolation / Extrapolation Policy (finalized 2026-07-27, see Decision 006)
- **2001–2012 and 2012–2024:** linear interpolation between the two bracketing census
  points, per district. `Source_Type = "interpolated"` for non-census years,
  `"census"` for 2001/2012/2024 exactly.
- **2025–2026:** falls after the last census point. Extrapolate using the same linear
  slope computed from 2012→2024 for that district, extended forward.
  `Source_Type = "extrapolated"`. Treat any incidence figure in this range with
  reduced confidence and say so explicitly if used in the write-up.

## Known Limitation: War-Affected Districts (flagged 2026-07-27)

`Kilinochchi`, `Mullaitivu`, and `Mannar` show a **non-monotonic** 2001→2012→2024
trend that plain linear interpolation cannot represent correctly:

| District | 2001 | 2012 | 2024 | 2001→2012 | 2012→2024 |
|---|---|---|---|---|---|
| Kilinochchi | 127,263 | 113,510 | 136,710 | −10.8% | +20.4% |
| Mullaitivu | 121,667 | 92,238 | 122,619 | −24.2% | +32.9% |
| Mannar | 151,577 | 99,570 | 123,756 | −34.3% | +24.3% |

This pattern is consistent with the final phase of the Sri Lankan civil war
(concentrated in these Vanni-region districts, ending May 2009) causing severe
displacement between the 2001 and 2012 censuses, followed by resettlement/recovery
after 2012. The true population path almost certainly dropped sharply during
2007–2009 (exactly when our case/climate data begins) and did not decline smoothly
from 2001 to 2012 as linear interpolation assumes. Because population here is a
**reporting-layer denominator only** (Decision 006) — it does not touch the SARIMA
target or Stage 2 features — this does not corrupt the actual modeling pipeline, but
any `cases_per_100k` figures reported for these three districts in 2007–2012 should
be presented with an explicit caveat, not treated as precise incidence rates. No
better annual estimate is available, so this is documented as an accepted limitation
rather than something to silently interpolate over.

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

Each row also carries an `is_imputed` flag (see Decision 011) marking whether `Number_of_Cases` for that row was imputed due to a missing source week, and an `is_reporting_anomaly` flag (Decision 028) marking suspected delayed-reporting catch-up weeks (sharp drop ≥75% after ≥100 prior-week cases, followed by ≥2.5× rebound). The latter is used only to mask case-derived features — raw counts are retained for labels and metrics.

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
| Population census file not yet placed | **Resolved (2026-07-27)** | Placed at `data/raw/population/population_by_district.csv` (2001/2012/2024). District name typo `Moneragala` corrected to `Monaragala` on ingestion |
| Kilinochchi/Mullaitivu/Mannar population non-monotonic across census years (war-related displacement) | **Documented limitation (2026-07-27)** | Linear interpolation cannot represent the true 2007-2012 wartime population path for these 3 districts; `cases_per_100k` for that period/districts should be reported with a caveat. Reporting-layer only, does not affect modeling target |
| Systematic per-week date mislabeling — 30 `(Year, Week)` labels (2008-2024) had a date stamp agreed on by almost all districts (invisible to per-row/duplicate-key checks) but chronologically wrong relative to neighbouring weeks — page-level MoH scrape errors, distinct from the 5 row-level collisions fixed 2026-07-26 | **Resolved (2026-07-27)** — user manually corrected 28 of 30 in `dengue_cases_corected.csv` against the original MoH source pages; the assistant found and corrected 2 more the user's pass had missed (`2009 Wk24`, `2023 Wk40` — both a month-field-one-behind error, e.g. `5/6/2009` should have been `6/6/2009`) | `epi_week_calendar_chronology_issues.csv` and `epi_week_calendar_disagreements.csv` are now empty after re-running `shared.py` (0 rows each). All 375 previously-missing climate rows attributable to this issue are now populated; only the expected 150-row 2006/2020-Wk1/2026 boundary gap remains (see next row). Two accepted exceptions remain **by design, not oversight** — see next two rows |
| 2009 Wk17 (8 days) and 2009 Wk22 (6 days) — the raw source has a genuine 1-day surplus/deficit in these two multi-week stretches that no single-row date edit can remove without either fabricating a day or opening a new gap with a neighbour | **Accepted limitation (2026-07-27)** | Verified: shortening Wk17 to 7 days (moving its end date one day earlier) creates a *new* 2-day gap with Wk18 that didn't exist before, because Wk18's own start date is untouched and independently correct — the extra day is real and has nowhere else to go. Symmetrically, Wk22's 6-day span (from the user's earlier Wk21/22 boundary fix) is the mirror case. Both are left as irregular-length weeks rather than silently shifting the shortage/surplus onto a neighbour that was already correct. Case counts for these weeks are unaffected; only week-length is atypical |
| 3 new date-entry errors surfaced by a full-calendar day-count scan (not caught by the original overlap-only chronology check, since a *gap* with no overlap doesn't trip that check) — `2010 Wk9` (end date before start date), `2011 Wk48` (start date 3 days late, leaving a 4-day week), `2013 Wk39`/`Wk40` (1-day boundary shift, mirroring the `2009 Wk21/22` pattern) | **Resolved (2026-07-27)** | Corrected directly in `dengue_cases_corected.csv` for all 26 (25 districts + Kalmunai) rows per affected week: `2010 Wk9` start `3/27/2010→2/27/2010`; `2011 Wk48` start `11/29/2011→11/26/2011`; `2013 Wk39` end `9/28/2013→9/27/2013` and `2013 Wk40` start `9/29/2013→9/28/2013`. All now connect cleanly (7 days, 1-day gap to each neighbour) |
| 2 per-row "disagrees with the national mode" cases (Ampara only) — `2013 Wk51` (Ampara alone recorded a 14-day span) and `2023 Wk14` (Ampara alone recorded dates one week later than the national consensus) | **Resolved (2026-07-27)** | Corrected Ampara's row only (other 24/25 districts were already correct and untouched): `2013 Wk51` end `12/27/2013→12/20/2013`; `2023 Wk14` start/end `4/8–4/14/2023→4/1–4/7/2023`. `epi_week_calendar_disagreements.csv` is now empty |
| Genuine 3-day gap at the live edge of the dataset: `2025 Wk52` ends `12/26/2025`, `2026 Wk1` starts `12/29/2025` (confirmed present in raw source for at least Colombo) | **Open (low priority, discovered 2026-07-27)** | Not corrected — this sits at the current live-scrape boundary of the dataset (raw case data extends to 2026 Wk25 as of this writing) and may simply reflect how the source reports the most recent year-end; needs a source-page check rather than an assumed fix. Low modeling impact either way given its position at the very edge of the series |
| Diagnostic files (`epi_week_calendar_chronology_issues.csv`, `epi_week_calendar_disagreements.csv`) previously were only written when non-empty, so a clean re-run after fixing the underlying issue left a stale file on disk from the prior run | **Resolved (2026-07-27)** | `src/preprocessing/shared.py`'s `run_shared_preprocessing()` now always (re)writes both diagnostic files, including writing an empty file when there are zero issues, so the file on disk always reflects the most recent run |
| The 4 confirmed nationwide case-data gaps (`2015 Wk30`, `2020 Wk1`, `2021 Wk42`, `2022 Wk43`) have zero raw rows for ANY district — confirmed (2026-07-27) they are absent from the master epi-week calendar too, not just the case data | **Partially resolved (2026-07-27)** | `shared.py`'s `fill_isolated_calendar_gaps` sequentially infers a date only when exactly one week's worth of days fits unambiguously between two known neighbours — recovered dates for 3 of the 4. `2020 Wk1` remains dateless: 2019's confirmed week-53 already runs through 2020-01-03, leaving no gap for a "week 1" — open team decision on whether this week truly exists in the MoH calendar. See `PIPELINE_ARCHITECTURE_PLAN.md` Open Item 5 |
| Weather CSV `time` column uses inconsistent date formats across files | **Resolved (2026-07-27), worth normalizing at source** | 24 of 25 files use ISO `YYYY-MM-DD`; the Colombo file alone uses `M/D/Y`. `src/preprocessing/shared.py` parses with `pd.to_datetime(..., format="mixed")`, which works but is fragile if more format variants are ever introduced |
