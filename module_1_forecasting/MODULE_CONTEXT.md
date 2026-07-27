# Module 1 Context: Hybrid Time-Series Case Forecasting

## Owner
Bandara H.R.B.G.M.

## Purpose
Predict weekly dengue case counts using a two-stage residual compensation model.

---

## Current Architecture

```text
Stage 1: SARIMA baseline forecasting model
Stage 2: XGBoost residual compensation model
```

---

## Stage 1

### Model
SARIMA

### Input
Weekly dengue case count series per district.

### Excluded
Climate variables are excluded from Stage 1.

### Reason
Stage 1 should model normal temporal structure only. Climate-driven deviations should remain in residuals for Stage 2.

---

## Stage 2

### Model
XGBoost regressor, subject to benchmarking.

### Target

```text
residual = actual_cases - sarima_prediction
```

### Feature Groups

- Case lags: `cases_lag_1` to `cases_lag_4`
- Rolling case features: 4-week rolling mean and standard deviation
- Rate of change
- Rainfall lags: 2 to 8 weeks
- Temperature lags: 1 to 4 weeks
- Humidity lags: 1 to 4 weeks
- Climate anomalies
- Seasonal cyclic features
- Monsoon indicators
- SARIMA prediction
- Residual lags

---

## Current Open Questions

1. Which SARIMA orders perform best per district?
2. Should STL + SARIMA be tested as an alternative baseline?
3. Are residuals autocorrelated enough to justify residual_lag features?
4. Which rainfall lag window gives best performance?
5. Should `rain_sum` or `precipitation_sum` be preferred?
6. How much improvement is required to claim compensation benefit?
7. **Zero-inflation risk (new, 2026-07-26):** Most weeks report zero cases across many districts. Need to compute per-district zero-week % and assess whether SARIMA remains an appropriate Stage 1 baseline for very sparse districts, or whether a simpler baseline (e.g., week-of-year historical mean, monthly aggregation) is more defensible there. This is a potential refinement to Decision 002 ("one SARIMA per district"), not yet resolved.
8. Log transform for SARIMA should use `log1p`, not plain `log`, given zero-valued weeks — both transformed and untransformed SARIMA should be compared empirically.

---

## Resolved Data Questions (2026-07-26)

- Data range confirmed: 2007–2026 per district (weekly case + daily climate), sufficient for SARIMA m=52 seasonality.
- Epi-week definition confirmed: Sri Lanka MoH epidemiological week standard (scraped directly from source), not ISO calendar week.
- District names confirmed consistent across case and climate datasets — no merge-key risk.
- Population data available: census years 2001, 2012, 2024 — see Decision 006 for interpolation/reporting-layer policy. **Placed 2026-07-27** at `data/raw/population/population_by_district.csv` (`Moneragala` corrected to `Monaragala` on ingestion). Note: `Kilinochchi`/`Mullaitivu`/`Mannar` show a non-monotonic, war-era population trend across the 3 census points — documented limitation, see `DATA_DICTIONARY.md` Section 3.
- Climate data confirmed single-point-per-district (Open-Meteo constraint) — documented as a limitation in `DATA_DICTIONARY.md`.
- See `RESEARCH_DECISIONS.md` Decisions 006–012 for the resulting policy decisions (population normalization, week-53 merge, `weather_code` exclusion, walk-forward validation, no-leakage rule, missing-week imputation, Kalmunai merge).

## Raw Data Audit Findings (2026-07-26, post-cleanup)

A full audit (`scripts/data_audit_module1.py`) was run against the actual placed raw files and, after a joint iterative cleanup with the team, confirmed:

- **26 → 25 modeling districts**: `Kalmunai` (real 19-year series, no weather station) merged into `Ampara` per Decision 012. Two district-name typos (`Moneragala`, `Puttlam`) were also found and corrected to `Monaragala`/`Puttalam`.
- **Zero duplicate `(District, Year, Week)` rows** after resolving 5 week-boundary collisions (2010, 2012/2013, 2014, 2022/2023) — see `RESEARCH_DECISIONS.md` and `CHANGELOG.md` for details.
- **Remaining real (non-error) missing weeks**: `Ampara`, `Kilinochchi`, `Mullaitivu` (1 week each), plus 3 weeks from the merged `Kalmunai` series. These go through the Decision 011 imputation policy.
- **Confirmed 53-week years**: 2009, 2016, 2019, 2021.
- **Climate source**: use `data/raw/weather/*.csv` (25 per-district files, flat, no subfolders). Each file has all 13 columns including humidity. The formerly separate `Humidity/` subfolder was confirmed fully redundant and has been deleted; `Weather (Except Humidity)/` was flattened into `data/raw/weather/` directly.
- **Corrected zero-inflation understanding**: pooled 13.7%, but concentrated in `Mullaitivu` (52.8%), `Kilinochchi` (47.7%), `Mannar` (40.4%), `Ampara` (32.9%), `Vavuniya` (32.3%). High-incidence districts (`Colombo`, `Kandy`, `Gampaha`, `Kegalle`, `Kurunegala`) have near-zero zero-weeks. The SARIMA-appropriateness question below applies mainly to the five sparse districts, not universally.

---

## Evaluation Metrics

- RMSE
- MAE
- sMAPE (preferred over MAPE due to frequent zero-case weeks)
- MASE (scale-free, more robust than sMAPE under zero-inflation)
- Residual variance reduction
- Diebold-Mariano test, if applicable

---

## Implementation Plan (2026-07-26)

Full technical detail lives in `research_context/PIPELINE_ARCHITECTURE_PLAN.md`. Summary:

1. **Prerequisite:** fix `src/config.py` placeholders (real 25-district list, correct monsoon weeks: SW = weeks 20-38, NE = weeks 44-52/1-8).
2. **Shared layer** (`src/preprocessing/shared.py`, module-agnostic, feeds Module 2/3 too): Kalmunai→Ampara merge, master epi-week calendar, climate aggregation (all 13 columns retained), population interpolation. Writes to `data/processed/shared/`.
3. **Module 1 preprocessing** (`src/preprocessing/module1_preprocessing.py`): week-53 merge (Decision 007), missing-week imputation with `is_imputed` flag (Decision 011), merge in climate + population, compute `cases_per_100k`. Writes to `data/processed/module1/weekly_modeling_table.csv`.
4. **Validation harness** (`src/module1_forecasting/validation.py`, new file): walk-forward fold generator enforcing the no-leakage rule (Decision 010).
5. **Feature engineering** (`src/module1_forecasting/feature_engineering.py`, new file): builds Stage 2 features per `FEATURE_ENGINEERING_SPEC.md`, distinguishing fold-agnostic features (lags, rolling stats — safe to compute globally) from fold-aware features (climate anomalies — must be recomputed per walk-forward fold to avoid leakage). Excludes `weather_code` here (Decision 008). Writes to `data/features/module1/`.
6. **Stage 1/2 modeling**: `baseline_sarima.py` → `compensation_model.py` → `combine.py` → `evaluate.py` (excludes `is_imputed == True` rows from scoring), orchestrated by `main.py`.

## Validation Strategy (Proposed, Decision 009/010)

- Final ~2 years (104 weeks) per district held out untouched until final reporting.
- Expanding-window walk-forward validation (annual folds) on remaining history for SARIMA order selection and XGBoost hyperparameter tuning.
- Stage 2 must always train on out-of-sample SARIMA residuals (refit per fold) — never in-sample fitted residuals, to avoid inflating apparent compensation benefit.
- Report per-district metrics plus a median-across-districts aggregate (avoids high-incidence districts like Colombo/Gampaha dominating the aggregate).

---

## Implementation Status (2026-07-27 - Preprocessing Pipeline Built)

The shared preprocessing layer and the full Module 1 preprocessing/feature
pipeline (up to, but not including, the Stage 1/2 models themselves) are now
implemented and have been run end to end against the real data:

- `src/config.py` - real 25-district `DISTRICTS` list, `MONSOON_WEEKS_SW`
  (weeks 20-38), `MONSOON_WEEKS_NE` (weeks 44-52, 1-8), and all pipeline
  paths (raw/shared/module1 processed + feature paths).
- `src/preprocessing/shared.py` - Kalmunai->Ampara merge, master epi-week
  calendar, climate weekly aggregation (all climate columns retained), and
  population interpolation/extrapolation. Outputs written to
  `data/processed/shared/`: `epi_week_calendar.csv` (1,017 rows),
  `climate_weekly.csv` (25,300 rows x 15 cols — up from 24,950 prior to the
  2026-07-27 raw date corrections below), `population_annual.csv`
  (525 rows), `epidemiological_weekly.csv` (25,348 rows).
- `src/preprocessing/module1_preprocessing.py` - week-53 merge (2009, 2016,
  2019, 2021), seasonal-naive imputation of the 4 confirmed nationwide gap
  weeks (100 rows flagged `is_imputed`), climate + population merge,
  `cases_per_100k`. Output: `data/processed/module1/weekly_modeling_table.csv`
  (25,350 rows; every interior year 2007-2025 has exactly 52 weeks/district;
  zero duplicate `(District, Year, Week)` keys).
- `src/module1_forecasting/validation.py` (new) - `generate_walk_forward_folds`,
  `fit_window`, `get_holdout_series`, `iter_walk_forward_windows`,
  `generate_walk_forward_folds_by_district`. Tested against Colombo's real
  series: 14 expanding-window annual folds, 104-week holdout, zero overlap
  between any fold and the holdout block.
- `src/module1_forecasting/feature_engineering.py` (new) - fold-agnostic
  features (case lags/rolling stats/rate of change, climate lags, cyclic
  week + monsoon indicators) written to
  `data/features/module1/stage2_feature_table.csv` (25,350 rows x 47 cols,
  `weather_code` excluded). Fold-aware climate anomalies are exposed as
  `compute_fold_climate_anomalies(df, train_mask)` - deliberately NOT written
  to a global file, since a global computation would leak future climate
  norms into early walk-forward folds. Verified against a manual
  hand-calculation for one district/fold.

Out of scope this session (per plan): `baseline_sarima.py`,
`compensation_model.py`, `combine.py`, `evaluate.py`, `main.py`.

### Deviations From the Plan / Implementation Choices Made

1. **Weekly aggregation rule for `weather_code`** (both in
   `shared.py`'s daily->weekly step and `module1_preprocessing.py`'s
   week-53 merge): the plan says "keep all columns" / "average climate
   columns" but never specifies a rule for a *categorical* code. Implemented
   as the weekly/pair **mode** (most frequent value, ties broken by the
   smaller code). This is an implementation choice, not a research decision -
   flag for review if `weather_code` is ever promoted out of "excluded"
   status (Decision 008).
2. **`rainfall_lag_*` feature source**: Open Question #5 below ("`rain_sum`
   vs `precipitation_sum`") is still unresolved. `feature_engineering.py`
   defaults to `rain_sum (mm)` as a **provisional placeholder**, clearly
   flagged in code (`RAINFALL_COLUMN`) - not a resolution of the open
   question.
3. **`rate_of_change` formula**: not specified in
   `FEATURE_ENGINEERING_SPEC.md`. Implemented as the absolute difference
   `cases_lag_1 - cases_lag_2` rather than a percent change, specifically to
   avoid divide-by-zero blowups given this module's well-documented
   zero-inflation. Worth an ablation later.
4. **Rolling case stats use `shift(1)` before `rolling(4)`**: i.e.
   `rolling_mean_cases_4w`/`rolling_std_cases_4w` for week *t* summarize
   weeks *t-1..t-4*, never week *t* itself. Not explicit in the spec, but
   required to avoid the feature leaking its own target.
5. **Interior-year completeness check excludes the two boundary years**
   (2006, 2026): "exactly 52 weeks/district/year" is enforced for 2007-2025
   only. 2006 (starts 12/23) and 2026 (data ends mid-year) are naturally
   partial by construction, not genuine gaps - forcing them to 52 rows would
   have meant fabricating dozens of weeks that were never scraped because
   they hadn't happened yet / the series hadn't started.
6. **Calendar gap-filling added to `shared.py`** (`fill_isolated_calendar_gaps`,
   not in the original plan text): see open question #10 below - this was
   necessary to give the 4 confirmed nationwide-gap weeks a usable date at
   all downstream.

### New Open Questions / Data Quality Findings (discovered 2026-07-27 while implementing)

9. **Confirmed via re-run**: the 4 documented nationwide case-data gaps
   (`2015 Wk30`, `2020 Wk1`, `2021 Wk42`, `2022 Wk43`) have **zero raw rows
   for any district** - they don't even exist in the master epi-week
   calendar (which is built from raw rows), not just the case data. Handled
   by (a) a new `fill_isolated_calendar_gaps` step in `shared.py` that
   sequentially infers a clean date range when exactly one week's worth of
   days (8-day gap) fits unambiguously between two known neighbours, and
   (b) `module1_preprocessing.py`'s existing seasonal-naive imputation for
   the case counts. 3 of the 4 (`2015 Wk30`, `2021 Wk42`, `2022 Wk43`) got
   an inferred date this way. **`2020 Wk1` could not be dated**: 2019 is a
   confirmed 53-week year whose Wk53 already runs through 2020-01-03, and
   2020's own Wk2 starts 2020-01-04 - there is no day-range gap left to
   place a "Week 1" in at all. `Number_of_Cases` for these 25 rows is still
   seasonal-naive imputed and flagged `is_imputed`, but their
   `Week_Start_Date`/`Week_End_Date` are left as `NaN` rather than
   fabricated. **Needs team discussion**: does a real "epi-week 1 of 2020"
   exist in the true MoH calendar at all, or is this a structural artifact
   of 2019 running long?
10. **RESOLVED (2026-07-27).** Systematic per-week date mislabeling,
    distinct from the 5 collisions fixed 2026-07-26. Building the master
    calendar and sorting it chronologically originally surfaced **30
    `(Year, Week)` labels** (2008-2024) whose date stamp was self-consistent
    across (almost) all districts — invisible to the per-row disagreement
    check — but chronologically wrong relative to neighbouring weeks (a
    page-level MoH scrape error per affected week). The user manually
    corrected 28 of the 30 against the original MoH source pages. Verifying
    that pass surfaced two further layers of issues, all now fixed directly
    in `dengue_cases_corected.csv`:
    - **2 of the 30 were missed** — `2009 Wk24` and `2023 Wk40` both had the
      same "month field one behind" error as the other 28 (e.g. `2009 Wk24`
      showed `5/6/2009–5/12/2009`, day-of-month exactly right, but should
      have been `6/6/2009–6/12/2009`), just not caught during manual review.
    - **A full-calendar day-count scan** (checking every week for exactly 7
      days and a 1-day gap to its neighbour, not just the overlap-only check
      that found the original 30) found 3 more previously-undetected
      date-entry errors that don't manifest as overlaps: `2010 Wk9` (end
      date was literally before its start date — `3/27/2010–3/5/2010`; fixed
      to `2/27/2010–3/5/2010`), `2011 Wk48` (start date 3 days late, leaving
      a 4-day week; fixed `11/29/2011→11/26/2011`), and `2013 Wk39`/`Wk40`
      (a 1-day boundary misplacement mirroring the `2009 Wk21/22` pattern;
      fixed `9/28/2013→9/27/2013` and `9/29/2013→9/28/2013` respectively).
    - The 2 outstanding per-row disagreements (`Ampara 2013 Wk51`, `Ampara
      2023 Wk14`) were also corrected — Ampara's own row now matches the
      national mode for both weeks.
    - **Two weeks are accepted as irregular by design, not left broken by
      oversight**: `2009 Wk17` (8 days) and `2009 Wk22` (6 days) each sit in
      a stretch of the raw data with a genuine 1-day surplus/deficit that
      cannot be fixed by editing one date without opening a *new* gap with
      an already-correct neighbour (verified concretely for `Wk17`: shortening
      it creates a fresh 2-day gap with `Wk18`, which was untouched and
      correct). Case counts for both weeks are unaffected.
    - **One low-priority item remains open**: a genuine 3-day gap between
      `2025 Wk52` (ends `12/26/2025`) and `2026 Wk1` (starts `12/29/2025`),
      confirmed present in the raw source. This sits at the live-scrape edge
      of the dataset (raw data currently extends to `2026 Wk25`) and needs a
      source-page check rather than an assumed fix.
    - After re-running the full pipeline, `epi_week_calendar_chronology_issues.csv`
      and `epi_week_calendar_disagreements.csv` are both empty, and all 375
      climate rows previously blocked by this issue in
      `weekly_modeling_table.csv` are now populated (confirmed: the only
      remaining 150 "no matching climate" rows are the expected boundary
      cases — 2006 Wk52 before climate coverage begins, 2020 Wk1's dateless
      rows per #9, and 2026 Wk22-25 after current climate coverage ends).
    - **Bonus fix**: also found `shared.py` only wrote the two diagnostic
      CSVs above when non-empty, so a clean re-run left a stale issues file
      from a prior run on disk. `run_shared_preprocessing()` now always
      (re)writes both files.
11. **Weather CSV dates are inconsistently formatted**: 24 of 25 per-district
    files use ISO `YYYY-MM-DD`; the Colombo file alone uses `M/D/Y`. Parsed
    with `pd.to_datetime(..., format="mixed")` in `shared.py` - works, but
    is a fragile pattern worth normalizing at the source if the raw files
    are ever regenerated.

## Documentation Rule

Update this file when Module 1 architecture, features, decisions, or evaluation method changes.
