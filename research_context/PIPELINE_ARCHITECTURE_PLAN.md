# Pipeline Architecture Plan

## Status
Living technical build plan. This is the concrete, implementation-level companion to
`research_context/CURRENT_ARCHITECTURE.md`. Update this file whenever the pipeline's
stages, scripts, or file layout change. Research-level rationale and decisions belong
in `research_context/RESEARCH_DECISIONS.md`; this file is about *how it is built*.

**Implementation status (2026-07-27):** the Stage 0 fix, the Shared Layer,
and the Module 1 Layer described below are now implemented and have been run
against the real data - see `module_1_forecasting/MODULE_CONTEXT.md`
"Implementation Status" section for exact row counts, deviations from this
plan, and new open questions discovered while building it (most notably a
newly-found systematic date-mislabeling issue affecting 30 epi-weeks,
distinct from the 5 collisions fixed 2026-07-26). Module 1's Stage 1/2
modeling scripts (`baseline_sarima.py` onward) remain unimplemented pending
resolution of the open SARIMA/log-transform questions.

## Last Updated
2026-07-27

---

# Guiding Principle

**A transformation belongs in the shared layer only if every module would make the
same choice for the same reason.** If a transformation exists to satisfy one model's
assumptions (e.g. SARIMA's fixed seasonal period), it belongs in that module's own
preprocessing step, not upstream where it would silently bias the other modules.

This principle was adopted after review found that week-53 merging and missing-week
imputation had been designed around Module 1's SARIMA requirements but were at risk of
being applied at a shared layer, which would have quietly discarded real data for
Module 2 and Module 3. See `RESEARCH_DECISIONS.md` Decision 013.

---

# Pipeline Stages

```text
data/raw/                                  (raw source files)
        |
        v
src/preprocessing/shared.py                (module-agnostic cleaning)
        |
        v
data/processed/shared/                     (shared clean base tables)
        |
   +----+----+----+
   |         |         |
   v         v         v
module1_preprocessing.py   module2_preprocessing.py   module3_preprocessing.py
   |                          |                            |
   v                          v                            v
data/processed/module1/   data/processed/module2/    data/processed/module3/
   |                          |                            |
   v                          v                            v
Stage 1 baseline           Stage 1 baseline            Stage 1 baseline
(SARIMA per district)      (classifier, TBD)           (KDE / Moran's I, TBD)
   |                          |                            |
   v                          v                            v
feature_engineering.py    feature_engineering.py      feature_engineering.py
(Module 1)                (Module 2, TBD)              (Module 3, TBD)
   |                          |                            |
   v                          v                            v
data/features/module1/    data/features/module2/      data/features/module3/
   |                          |                            |
   v                          v                            v
Stage 2 compensation       Stage 2 compensation        Stage 2 compensation
(XGBoost on residuals)     model (TBD)                  model (TBD)
```

Only Module 1's path is detailed below (it's the only module with an accepted design
ready to implement). Module 2 and Module 3 sections are placeholders to be filled in
when those modules are actively built — they must not be skipped, just deferred.

---

# Stage 0: Prerequisite fix (before any pipeline code is written)

`src/config.py` currently has placeholder values that contradict already-decided
facts:

```python
DISTRICTS = ["District A", "District B", "District C"]
MONSOON_WEEKS = [1, 2, 3, 4]
```

Before writing any preprocessing code, replace these with:
- The real 25-district list (post Kalmunai-merge; see Decision 012).
- The correct monsoon week definitions from `FEATURE_ENGINEERING_SPEC.md`:
  `monsoon_indicator_SW` = weeks 20-38, `monsoon_indicator_NE` = weeks 44-52 or 1-8.

`OUTBREAK_THRESHOLD = 50` is a Module 2 concern and should stay a placeholder until
Module 2's label definition is actually decided (see open questions in
`module_2_classification/MODULE_CONTEXT.md`) — do not treat it as settled.

---

# Shared Layer: `src/preprocessing/shared.py`

Reads from `data/raw/`, writes to `data/processed/shared/`. Contains only
transformations every module would make the same way.

## Inputs
- `data/raw/epidemiological/dengue_cases_corected.csv` (already manually corrected —
  zero duplicate weeks, zero negative values, confirmed 2026-07-26)
- `data/raw/weather/*.csv` (25 per-district files, flat, no subfolders; the
  formerly separate `Humidity/` subfolder was confirmed redundant and has been
  deleted)
- `data/raw/population/population_by_district.csv` (2001/2012/2024 census, placed
  2026-07-27; wide format, one row per district, columns
  `District, Population_2001, Population_2012, Population_2024`). Note: the source
  district name `Moneragala` was corrected to `Monaragala` in this file to match the
  canonical spelling used everywhere else.

## Steps

1. **Load and merge Kalmunai into Ampara** (Decision 012).
   - Sum `Number_of_Cases` per `(Year, Week)` across Kalmunai and Ampara.
   - If both are genuinely missing that week, the merged result is still missing
     (do not fabricate a value here — that is a module-specific decision).
   - Output: exactly 25 districts.

2. **Build the master epi-week calendar.**
   - For each `(Year, Week)`, take the **mode** (most common) `Week_Start_Date` /
     `Week_End_Date` pair across all 25 districts. Districts should share one
     national MoH calendar, so the majority value is the trustworthy one.
   - Log any row whose own date fields disagree with the mode for that
     `(Year, Week)` — these are the residual per-row date wobbles found during the
     2026-07-26 audit (present even after the 5 major collisions were fixed; they
     don't affect the `(District, Year, Week)` key, only individual date columns).
   - Output: `data/processed/shared/epi_week_calendar.csv` with columns
     `Year, Week, Week_Start_Date, Week_End_Date`.

3. **Aggregate daily climate to epi-weeks using the master calendar** (not each
   row's own possibly-wobbly dates).
   - Per `FEATURE_ENGINEERING_SPEC.md` Section 4 rules: rainfall/precipitation =
     weekly sum; temperature/humidity = weekly mean of the daily means/max/min.
   - Keep **all** 13 columns from the raw weather CSVs, including
     `weather_code` — do not drop it here. Column exclusion is a module-specific
     feature-selection choice (see Decision 008's Module 1 scope below), not a
     shared-layer decision.
   - Output: `data/processed/shared/climate_weekly.csv` with columns
     `District, Year, Week, <13 aggregated climate columns>`.

4. **Interpolate population to an annual series** (Decision 006, finalized).
   - Melt the wide source file to long format: `District, Year, Population` with
     `Year` in `{2001, 2012, 2024}`.
   - Linear interpolation between 2001↔2012 and 2012↔2024, per district, for every
     year needed (2006-2026 to cover the full case/climate range).
   - For 2025-2026 (after the last census point), extrapolate forward using that
     district's own 2012→2024 linear slope.
   - Tag `Source_Type`: `"census"` for 2001/2012/2024 exactly, `"interpolated"` for
     years strictly between two census points, `"extrapolated"` for 2025-2026.
   - Known limitation to carry forward, not silently smooth over: `Kilinochchi`,
     `Mullaitivu`, `Mannar` have a non-monotonic 2001→2012→2024 trend (war-era
     displacement/recovery) — see `DATA_DICTIONARY.md` Section 3. Linear
     interpolation is still used (no better data exists), but downstream
     `cases_per_100k` for these 3 districts in 2007-2012 should be flagged as
     lower-confidence wherever it's reported.
   - Output: `data/processed/shared/population_annual.csv` with columns
     `District, Year, Estimated_Population, Source_Type`.

5. **Write the cleaned, non-imputed, non-week-53-merged case table.**
   - This is Kalmunai-merged, 25-district, but otherwise a faithful reflection of
     the corrected raw file — real gaps stay as absent rows, 53-week years are
     left as 53 rows. No fabrication happens at this layer.
   - Output: `data/processed/shared/epidemiological_weekly.csv` with columns
     `District, Year, Week, Week_Start_Date, Week_End_Date, Number_of_Cases`.

## Explicitly NOT done in this layer
- No week-53 merging.
- No missing-week imputation / `is_imputed` flagging.
- No `weather_code` exclusion.
- No lag/rolling/anomaly feature engineering.

---

# Module 1 Layer

## `src/preprocessing/module1_preprocessing.py`

Reads `data/processed/shared/*.csv`, writes to `data/processed/module1/`.

1. **Merge week 53 into week 52** for 2009, 2016, 2019, 2021 (Decision 007,
   Module-1-scoped). Sum cases, average climate columns.
2. **Impute the remaining genuine gaps** (Decision 011, Module-1-scoped):
   - Confirmed true gaps (2026-07-26 audit, excluding the moot week-53 cases):
     4 weeks missing for all 25 districts (`2015 Wk30`, `2020 Wk1`, `2021 Wk42`,
     `2022 Wk43`), plus Kalmunai-specific gaps now folded into the Ampara merge,
     plus Ampara's own `2014 Wk39` gap.
   - Fill using seasonal-naive: same district, same `Week` number, mean across all
     other available years.
   - Add `is_imputed` boolean column (`True` for filled rows, `False` otherwise).
3. **Merge in climate data** (`climate_weekly.csv`) on `(District, Year, Week)`.
4. **Merge in population** (`population_annual.csv`) on `(District, Year)`, compute
   `cases_per_100k` as a reporting-layer column (Decision 006) — not a modeling
   target.
5. Output: `data/processed/module1/weekly_modeling_table.csv` — one row per
   `District + Year + Week`, exactly 52 weeks/year, no duplicate keys, `is_imputed`
   flag present, all 13 climate columns present, population + incidence columns
   present.

## `src/module1_forecasting/validation.py` (implemented 2026-07-27)

Implements Decisions 009/010 as reusable, testable functions:
- `generate_walk_forward_folds(district_series, holdout_years=2, step="year")` →
  yields `(train_index, val_index)` pairs using expanding windows, per district.
- A hard rule enforced here, not left to convention: any function that fits SARIMA
  for a fold must only see data up to that fold's cutoff. This module should make
  it structurally awkward to violate that (e.g. by only exposing a
  `fit_window(series, up_to_date)` helper rather than the full series).

## `src/module1_forecasting/feature_engineering.py` (implemented 2026-07-27)

Reads `data/processed/module1/weekly_modeling_table.csv`, builds Stage 2 features
per `FEATURE_ENGINEERING_SPEC.md`, writes to `data/features/module1/`.

- **Fold-agnostic features** (safe to compute once, globally): `cases_lag_1..4`,
  `rolling_mean_cases_4w`, `rolling_std_cases_4w`, `rate_of_change`, climate lags
  (rainfall lag 2-8, temperature/humidity lag 1-4), `sin_week`, `cos_week`,
  `monsoon_indicator_SW`, `monsoon_indicator_NE`. These are pure shifts/windows of
  already-observed data and don't leak future information regardless of split.
- **Fold-aware features** (must be recomputed per walk-forward fold, using only
  that fold's training window): `rainfall_anomaly`, `temperature_anomaly`,
  `humidity_anomaly` — each defined as `current_week_value -
  long_term_mean_for_same_district_and_week`, per `FEATURE_ENGINEERING_SPEC.md`.
  Computing this once globally would leak future climate norms into early
  training folds.
- `sarima_prediction` and `residual_lag_1/2` are produced by the Stage 1 model
  inside each fold, not by this script directly — this script should accept them
  as an input column once Stage 1 has run, not compute them itself.
- `weather_code` is excluded here (Decision 008, Module-1-scoped) — it remains
  present in `data/processed/module1/` and is only dropped at this final
  feature-selection step, not upstream.
- Rows where `is_imputed == True` should be excluded from serving as a **Stage 2
  training target**, but may still be used to compute lag features for
  *subsequent* real weeks (i.e., don't delete the row, just don't score against it
  or use it as a residual target).

## Existing stub files — role clarification

| File | Role |
|---|---|
| `src/preprocessing/module1_preprocessing.py` | Module-1-specific temporal adjustments (week-53 merge, imputation) — see above |
| `src/module1_forecasting/baseline_sarima.py` | Stage 1: fit SARIMA per district per walk-forward fold |
| `src/module1_forecasting/compensation_model.py` | Stage 2: fit XGBoost on out-of-sample residuals |
| `src/module1_forecasting/combine.py` | `final_prediction = sarima_prediction + predicted_residual` |
| `src/module1_forecasting/evaluate.py` | RMSE/MAE/sMAPE/MASE, filtering out `is_imputed == True` rows first |
| `src/module1_forecasting/main.py` | Orchestrates the full Module 1 pipeline end to end |

---

# Module 2 Layer (placeholder — expand when Module 2 development starts)

- Reads from `data/processed/shared/` — the same Kalmunai-merged, calendar-aligned
  base tables Module 1 uses.
- Does **not** inherit Module 1's week-53 merge or imputation. Module 2 must decide
  its own missing-week policy (e.g., drop vs. impute) once its label definition is
  settled — see open questions in `module_2_classification/MODULE_CONTEXT.md`.
- Does **not** inherit Module 1's `weather_code` exclusion by default — re-evaluate
  independently.
- Writes to `data/processed/module2/` and `data/features/module2/`.

# Module 3 Layer (placeholder — expand when Module 3 development starts)

- Reads from `data/processed/shared/`.
- Likely aggregates to a coarser temporal resolution than weekly (TBD) — a handful
  of missing weeks may simply wash out in aggregation rather than needing explicit
  imputation.
- Needs spatial boundary data (district polygons) — not yet placed in
  `data/raw/spatial/` (currently empty except `.gitkeep`).
- Writes to `data/processed/module3/` and `data/features/module3/`.

---

# Open Items

1. ~~Population census file needs to be placed in `data/raw/`.~~ **Resolved
   2026-07-27** — placed at `data/raw/population/population_by_district.csv`;
   shared Step 4 is now unblocked.
2. ~~`src/config.py` needs the Stage 0 fix described above.~~ **Resolved
   2026-07-27.**
3. ~~Confirm the master-calendar mode-based construction (shared Step 2)
   doesn't produce ties or ambiguous cases before relying on it — spot-check
   after building.~~ **Done 2026-07-27.** Only 2 genuine per-row
   mode-disagreements exist in the whole dataset (see
   `data/processed/shared/epi_week_calendar_disagreements.csv`) — ties are
   not the real risk here. The spot-check instead surfaced a **different,
   more significant issue**: see item 4.
4. **NEW (2026-07-27), Open, needs team review:** 30 `(Year, Week)` labels
   (2008-2024) have a date stamp that is self-consistent across almost all
   districts (so it doesn't trigger the per-row disagreement check) but is
   chronologically inconsistent with neighbouring weeks — most likely a
   page-level MoH scrape error for that specific week, not a per-row
   transcription slip like the 5 collisions fixed 2026-07-26. This breaks
   the calendar-based day-to-week join for climate aggregation on 15 of
   those weeks (375 of 25,350 rows in `weekly_modeling_table.csv` have no
   matching climate for this reason; a further 125 rows have no climate for
   the separate, expected 2006/2026 boundary reason). Full list in
   `data/processed/shared/epi_week_calendar_chronology_issues.csv`.
   `shared.py` does NOT attempt to auto-correct these (only genuinely
   *absent* week labels are auto-inferred, via `fill_isolated_calendar_gaps`,
   and only when unambiguous — see `module_1_forecasting/MODULE_CONTEXT.md`
   open question #10 for full detail). Needs the same joint human-review
   process used for the earlier 5 collisions before it can be corrected at
   the source (`data/raw/epidemiological/dengue_cases_corected.csv`).
5. **NEW (2026-07-27), Open, needs team decision:** `2020 Wk1` (one of the 4
   confirmed nationwide case-data gaps) cannot be assigned a calendar date at
   all — 2019 is a confirmed 53-week year whose Wk53 already runs through
   2020-01-03, and 2020's Wk2 starts 2020-01-04, leaving no free day-range to
   place a "Week 1" in. `Number_of_Cases` is still seasonal-naive imputed and
   flagged `is_imputed` for this week, but its dates are left `NaN` rather
   than fabricated. Does a real "epi-week 1 of 2020" exist in the true MoH
   calendar, or is this a structural artifact of the 53-week year before it?
6. **Open, unresolved research decision, not addressed by this session's
   implementation:** Module 1 Open Question #5 (`rain_sum` vs
   `precipitation_sum`) — `feature_engineering.py`'s `rainfall_lag_*`
   features currently default to `rain_sum (mm)` as a flagged placeholder.
