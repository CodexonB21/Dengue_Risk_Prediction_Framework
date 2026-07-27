# Changelog

This file records important project changes.

Use it to track why the architecture, features, models, or decisions changed over time.

---

## Entry Format

```markdown
## YYYY-MM-DD - Short Change Title

### Module
Module name or All modules

### Change
What changed?

### Reason
Why was the change made?

### Impact
What files/code/models are affected?

### Status
Accepted / Rejected / Experimental / Superseded
```

---

## 2026-07-27 - Module 1 Stage 2 XGBoost Residual Compensation Implemented

### Module
Module 1

### Change
Implemented `src/module1_forecasting/compensation_model.py`, `combine.py`,
and `main.py` (all previously placeholders), added `dm_test()` and
`ljung_box_diagnostics()` to `evaluate.py`, and ran the full pipeline
end-to-end against all 25 districts. Stage 2 is a **pooled** XGBoost
regressor (all 25 districts trained together, `District` as a categorical
feature) - one model per Stage 1 walk-forward fold (reusing Stage 1's exact
14 folds via `fold_id`/`split`), trained on pooled non-imputed out-of-sample
residuals from prior folds only. `combine.py` computes
`final_prediction = sarima_prediction + predicted_residual` (Decision 010)
and reports Stage-1-only vs Stage-1+Stage-2 accuracy (RMSE/MAE/sMAPE/MASE),
a Diebold-Mariano test, residual variance reduction, and a final Ljung-Box
check. `main.py` orchestrates the full pipeline (shared preprocessing ->
module1 preprocessing -> feature engineering -> Stage 1 -> Stage 2 ->
combine) idempotently, skipping any stage whose output already exists unless
`--force` is passed.

Also: `feature_engineering.py`'s `RAINFALL_COLUMN` switched from the
provisional `rain_sum (mm)` to `precipitation_sum (mm)` (Open Question #5,
resolved - see Decision 008) and `stage2_feature_table.csv` regenerated
before Stage 2 was built; `requirements.txt` gained an explicit `scipy` pin;
`src/config.py` gained the Stage 2/combine path constants.

**Major mid-implementation finding and fix**: the first full run used the
standard `objective="reg:squarederror"` and produced a deeply suspicious
result - 23/25 districts got *worse* with Stage 2 than without (e.g.
Colombo's RMSE rose from 162.8 to 274.0). Root cause: Stage 1's SARIMA
diverged catastrophically for `Vavuniya` in one walk-forward fold (2010
weeks 42-51, forecasts reaching ~30 million cases/week against an actual
mean of ~6/week - a residual of roughly -30,000,000). Because Stage 2 pools
every district into one squared-error-loss model, this single extreme value
dominated training globally and corrupted predicted residuals for every
*other* district too. Switching to `objective="reg:absoluteerror"` (MAE -
bounded gradient, immune to any single outlier's magnitude) fixed this
immediately. This is now documented as a required robustness property of
the pooled-model architecture (Decision 014), not a one-off patch. Stage 1's
Vavuniya divergence itself was not fixed at the source this session (flagged
as a new open question instead - Stage 1 is a separate, already-accepted
stage).

**A second, previously-undocumented structural finding**: there is a real
~26-week gap per district between the last walk-forward fold's validation
window and the holdout block's start (used as SARIMA training data for the
holdout fit but never scored out-of-sample). `residual_lag_1/2` are
therefore built by reindexing each district's residual onto the full weekly
calendar before taking `shift(1)/shift(2)`, rather than naively shifting the
sparse validation+holdout rows directly - the latter would have silently
treated fold 14's last residual as "1 week ago" for the holdout block's
first row (Decision 015).

**Result**: 24/25 districts improve on both validation-aggregate and holdout
MASE (median 42.8%/28.7% across all 25 districts); `Kilinochchi` is the sole
exception. Diebold-Mariano reaches significance (`p < 0.05`) for 12/25
districts at the larger validation+holdout scope, 4/25 at the stricter
holdout-only scope. The 18 non-seasonal-SARIMA districts show a larger
median improvement (43.2%/37.2%) than the 7 seasonal-SARIMA districts
(28.5%/24.3%), resolving Open Question #12 in favor of the original
sequencing bet (no Stage 1 rework currently justified). 23/25 districts
still show significant residual autocorrelation post-Stage-2 (Ljung-Box lag
26), an honest limitation flagged for future work.

### Reason
Stage 2's purpose is to learn systematic, predictable structure in Stage 1's
out-of-sample forecast error using climate, seasonal, and lagged-residual
features that SARIMA (deliberately univariate, per Decision 001) cannot see.
The pooled architecture was chosen over per-district models because
per-district training data is too thin for a many-feature GBM in early
walk-forward folds; the robust-loss fix was required once that pooling was
found to also pool a single district's data-quality problem into every
other district's correction.

### Impact
`src/module1_forecasting/compensation_model.py`, `combine.py`, `main.py`
(implemented), `evaluate.py` (`dm_test`, `ljung_box_diagnostics` added),
`feature_engineering.py` (`RAINFALL_COLUMN` changed), `src/config.py` (new
path constants), `requirements.txt` (`scipy` added). New data artifacts:
`data/processed/module1/xgboost_stage2_predictions.csv`,
`data/processed/module1/final_combined_predictions.csv`,
`models/module1/xgboost_folds/`, `models/module1/xgboost_final_model.json`,
`outputs/metrics/module1/xgboost_feature_importance.csv`,
`outputs/metrics/module1/xgboost_stage2_metrics.csv`,
`outputs/metrics/module1/combined_vs_baseline_metrics.csv`,
`outputs/metrics/module1/diebold_mariano_results.csv`,
`outputs/figures/module1/acf_residuals_final_*.png`.

### Status
Accepted

---

## 2026-07-27 - Module 1 Stage 1 SARIMA Baseline Implemented

### Module
Module 1

### Change
Implemented `src/module1_forecasting/baseline_sarima.py` and
`src/module1_forecasting/evaluate.py` (both previously 1-line placeholders)
and ran the full pipeline against all 25 districts. For each district,
`pmdarima.auto_arima` proposes a candidate SARIMA order for raw counts and
for `log1p` counts (one-time, constrained stepwise search on the full
pre-holdout history); both candidates are then genuinely walk-forward
validated (14 expanding-window folds, fixed-order `SARIMAX` refit per fold
per Decision 010) and the lower-aggregate-MASE transform is kept per
district. The final 104-week holdout block is forecast and scored once with
the winning config. Five design decisions were reviewed and approved before
implementation: (1) order search uses full pre-holdout history rather than
per-fold search (infeasible at scale - already benchmarked); (2) forecasts
from both candidates are clipped to a 0 floor after inverse-transforming;
(3) `SARIMAX` fits relax `enforce_stationarity`/`enforce_invertibility` for
robustness; (4) MASE (seasonal-naive scale) is the single deciding metric
for transform/config selection, with all four metrics logged for
transparency; (5) the holdout block is scored now (not deferred), clearly
labeled as a one-time, non-tuning report.

Also added: `src/config.py` (`MODULE1_SARIMA_PREDICTIONS_PATH`,
`MODULE1_SARIMA_CONFIG_PATH`, `MODULE1_SARIMA_METRICS_PATH`, plus their
parent-directory constants); `requirements.txt` pins for `pmdarima==2.1.1`,
`xgboost==3.2.0`, `statsmodels==0.14.6` (all already installed, previously
unpinned).

**Significant finding**: the seasonal-differencing test (`auto_arima`'s
default OCSB test, cross-checked against Canova-Hansen — both agree)
selected `D=0` for all 25 districts, and the constrained stepwise search
added no seasonal MA term for any district either. **18 of 25** selected
configs ended up with `seasonal_order=(0,0,0,52)` — a plain, non-seasonal
ARIMA despite `m=52` being specified. Forcing `D=1` was tested directly and
found computationally infeasible at scale (a single `D=1, m=52` SARIMAX fit
took 7+ minutes vs. ~0.01s for the `D=0` fixed-order refits used everywhere
else in this pipeline). This is documented as the top open finding from
Stage 1 (`module_1_forecasting/MODULE_CONTEXT.md` Open Question #12), not
silently patched over: 12/25 districts have validation-fold MASE > 1 (worse
than a naive "repeat last year's same week" forecast), and Ljung-Box tests
show significant residual autocorrelation in 23/25 districts, consistent
with the annual cycle not being captured by these particular selected
models. Zero-inflation % was checked as a possible explanation and largely
ruled out as the dominant driver (`Vavuniya`, one of the sparsest districts,
is the single best performer; `Colombo`, essentially never sparse, still
underperforms).

### Reason
Stage 2 (residual compensation) cannot be built without genuine
out-of-sample Stage 1 residuals to train on (Decision 010) - this was the
last blocking step before Stage 2 work can begin. The open SARIMA
order/log-transform questions (`module_1_forecasting/MODULE_CONTEXT.md`
Open Questions #1, #8) needed a concrete, evidence-based per-district
resolution rather than a single global assumption, given the project's
already-documented zero-inflation heterogeneity.

### Impact
- Added: `data/processed/module1/sarima_stage1_predictions.csv` (20,800
  rows), `models/module1/sarima_selected_configs.csv` (25 rows),
  `outputs/metrics/module1/sarima_walk_forward_metrics.csv` (400 rows),
  `outputs/figures/module1/acf_residuals_{Colombo,Kandy,Mullaitivu,
  Kilinochchi}.png`.
- Updated: `src/module1_forecasting/baseline_sarima.py`,
  `src/module1_forecasting/evaluate.py`, `src/config.py`, `requirements.txt`.
- Updated: `module_1_forecasting/MODULE_CONTEXT.md` (Open Questions #1, #2,
  #3, #7, #8 resolved/updated; new Open Questions #12-13; new "Stage 1
  Implementation Status" section), `module_1_forecasting/EXPERIMENT_LOG.md`
  (first real entry, M1-001), `research_context/RESEARCH_DECISIONS.md`
  (Decisions 009/010 status Proposed -> Accepted, implementation notes
  added).
- Explicitly untouched this session (per plan): `compensation_model.py`,
  `combine.py`, `main.py`.

### Status
Accepted (Stage 1 pipeline code and outputs). The AIC/seasonal-structure
finding (Open Question #12) is flagged Open, pending a future ablation
(STL+SARIMA or a forecast-horizon-aware order criterion) - not yet
resolved, and worth raising with the thesis supervisor before treating
Stage 1's absolute performance numbers as final.

---

## 2026-07-26 - Living Cursor Context System Added

### Module
All modules

### Change
Introduced living project documentation and Cursor rules so the agent can read and update project context as the research evolves.

### Reason
The project architecture, decisions, features, and approaches may change over time. Static rules can become outdated.

### Impact
Added/updated:

- `.cursor/rules/codexon_fyp.mdc`
- `research_context/PROJECT_CONTEXT.md`
- `research_context/CURRENT_ARCHITECTURE.md`
- `research_context/RESEARCH_DECISIONS.md`
- `research_context/CHANGELOG.md`
- module-specific context files

### Status
Accepted

---

## 2026-07-26 - Module 1 Data Realities Confirmed and New Decisions Proposed

### Module
Module 1 (with cross-module implication for Module 3 via population data)

### Change
User confirmed actual data characteristics for Module 1: full 2007–2026 weekly/daily coverage, Sri Lanka MoH epi-week standard (scraped), consistent district names, census population data (2001/2012/2024), single-point-per-district climate data (Open-Meteo constraint), and heavy zero-inflation in weekly case counts. Based on these facts, six new decisions were proposed (006–011): population used as a reporting-layer normalization only (not a Stage 1 target change), week-53 merged into week-52 for seasonal consistency, `weather_code` excluded from the feature set, walk-forward validation with a held-out final test block, a no-leakage rule for Stage 2 residual training, and a seasonal-naive imputation + flagging policy for missing weeks.

### Reason
Confirming real data characteristics resolved several previously open questions in `DATA_DICTIONARY.md` and `module_1_forecasting/MODULE_CONTEXT.md`, and surfaced new risks (zero-inflation, 53-week years, residual leakage) that needed explicit, documented handling before implementation begins.

### Impact
Updated:

- `research_context/DATA_DICTIONARY.md` (epi-week definition, spatial resolution caveat, population/census section, data quality notes)
- `research_context/RESEARCH_DECISIONS.md` (Decisions 006–011, all status Proposed pending final sign-off)
- `research_context/FEATURE_ENGINEERING_SPEC.md` (`weather_code` exclusion, week-53 merge note, feature change log)
- `module_1_forecasting/MODULE_CONTEXT.md` (resolved data questions, new zero-inflation open question, validation strategy, updated evaluation metrics)

### Status
Proposed (decisions 006–011 pending final user sign-off before implementation)

---

## 2026-07-26 - Raw Module 1 Data Audited and Cleaned

### Module
Module 1

### Change
Ran a full read-only audit (`scripts/data_audit_module1.py`, newly added) against the actual raw files placed in `data/raw/epidemiological/` and `data/raw/weather/`. Found and worked with the user through a joint iterative fix of five `(District, Year, Week)` collisions in the case data (2010 week 34/35 mislabeling, a 2012/2013 year-boundary mislabel, a 2014 week 2/3 double-track ambiguity, and a 2022/2023 year-boundary mislabel with a corrupted date). Also found and fixed two single-row district-name typos (`Moneragala`, `Puttlam`). Confirmed `Kalmunai` has a real 19-year case history but no matching weather station, and decided (Decision 012) to merge it into `Ampara`. Confirmed the `Humidity/` weather subfolder is fully redundant with `Weather (Except Humidity)/` (byte-identical humidity values) and should be dropped as a source. Corrected the earlier zero-inflation characterization: it is concentrated in 5 Northern/Eastern districts, not universal. Confirmed the earlier "encoding corruption" concern was a chat-display artifact, not a real file issue.

### Reason
The raw case data had genuine week-numbering integrity issues that would have silently corrupted any merge with climate data (row fan-out) and any SARIMA seasonal fitting (broken 7-day cadence) if left unresolved.

### Impact
- `data/raw/epidemiological/dengue_cases_corected.csv` — corrected in place by the user, verified by re-running the audit script until 0 duplicate rows remained.
- `research_context/DATA_DICTIONARY.md` — epi-week definition, climate source-folder guidance, and Data Quality Notes table updated with verified facts.
- `research_context/RESEARCH_DECISIONS.md` — added Decision 012 (Kalmunai → Ampara merge, Accepted); confirmed scope note added to Decision 011.
- `module_1_forecasting/MODULE_CONTEXT.md` — to be updated with final confirmed district list and data status.
- Added `scripts/data_audit_module1.py` as a reusable, read-only diagnostic — safe to re-run after any future edits to the raw case file.

### Status
Accepted (data-cleaning outcomes); Decision 012 Accepted; Decisions 006-011 remain Proposed pending pipeline implementation

---

## 2026-07-26 - Layered Pipeline Architecture Adopted; Detailed Build Plan Created

### Module
All modules

### Change
Corrected a design flaw: several transformations (week-53 merge, missing-week imputation, `weather_code` exclusion) had been implicitly treated as general-purpose data cleaning, when they actually exist to satisfy Module 1's SARIMA-specific assumptions. Adopted a layered pipeline (Decision 013): a shared, module-agnostic preprocessing stage (`data/processed/shared/`) feeding into separate module-specific preprocessing and feature-engineering stages (`data/processed/moduleN/`, `data/features/moduleN/`). Also corrected the missing-week count under Decision 011 using a more rigorous method (true label-gap detection instead of row-count comparison): the real picture is 4 weeks missing nationwide across all districts, plus a few district-specific gaps, totaling 104 rows (not the smaller, less accurate estimate previously recorded). Created a detailed technical build plan covering the shared layer and the full Module 1 pipeline, ready to implement.

### Reason
Applying Module-1-specific transformations at a shared layer would have silently discarded real data and imposed unproven feature-selection choices on Module 2 and Module 3 before their own designs are finalized.

### Impact
- Added `docs/PIPELINE_ARCHITECTURE_PLAN.md` (new, detailed technical build plan).
- `research_context/CURRENT_ARCHITECTURE.md` — added the layered pipeline diagram and guiding principle.
- `research_context/RESEARCH_DECISIONS.md` — added Decision 013; re-scoped Decisions 007, 008, 011 to Module 1 only; corrected Decision 011's confirmed missing-week count.
- `research_context/FEATURE_ENGINEERING_SPEC.md` — added fold-aware computation requirement for climate anomaly features.
- `module_1_forecasting/MODULE_CONTEXT.md` — added an Implementation Plan section.
- `module_2_classification/MODULE_CONTEXT.md`, `module_3_spatial/MODULE_CONTEXT.md` — added data pipeline consumption notes clarifying they do not inherit Module 1's modeling-specific choices.

### Status
Accepted

---

## 2026-07-27 - Population Census Data Placed; Decision 006 Finalized

### Module
Module 1 (cross-module implication for Module 3)

### Change
Placed the population census file at `data/raw/population/population_by_district.csv`
(2001/2012/2024, 25 districts, wide format). Corrected the source's `Moneragala`
spelling to `Monaragala` on ingestion to match the rest of the pipeline. Confirmed
`Kalmunai` needs no separate population row (administratively part of Ampara).
Finalized Decision 006's interpolation method: linear between census points,
linear extrapolation using the 2012→2024 slope for 2025-2026. This was previously
the last blocker on Shared Layer Step 4 in `PIPELINE_ARCHITECTURE_PLAN.md`.

### Reason
The pipeline-implementation prompt drafted for the next session needed a real answer
for the population step rather than an open TODO.

### Impact
- Flagged a genuine methodological limitation while reviewing the data: `Kilinochchi`,
  `Mullaitivu`, and `Mannar` show a non-monotonic 2001→2012→2024 population trend
  (sharp decline then recovery), consistent with civil-war-era displacement in the
  Vanni region ending 2009 — right when the case/climate data begins. Linear
  interpolation can't recover the true 2007-2012 population path for these 3
  districts. Since population is a reporting-layer-only denominator (Decision 006),
  this doesn't touch the modeling target, but `cases_per_100k` for these districts in
  that period should be reported with an explicit caveat. Documented in
  `DATA_DICTIONARY.md` Section 3 and `RESEARCH_DECISIONS.md` Decision 006.
- `research_context/DATA_DICTIONARY.md` — new Population section content, source file
  location, coverage check, district-name correction, limitation table rows.
- `research_context/RESEARCH_DECISIONS.md` — Decision 006 status Proposed → Accepted.
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` — Shared Step 4 unblocked, exact
  melt/interpolate/extrapolate steps specified, Open Items list updated.
- `module_1_forecasting/MODULE_CONTEXT.md` — Resolved Data Questions updated.

### Status
Accepted

---

## 2026-07-27 - Shared Preprocessing Layer and Module 1 Pipeline Implemented

### Module
All modules (shared layer); Module 1 (preprocessing, validation, feature engineering)

### Change
Implemented and ran, end to end against the real data, everything specified
in `PIPELINE_ARCHITECTURE_PLAN.md`'s Stage 0 / Shared Layer / Module 1 Layer
sections: `src/config.py` (real 25-district list, `MONSOON_WEEKS_SW`/`_NE`),
`src/preprocessing/shared.py` (Kalmunai->Ampara merge, master epi-week
calendar, climate weekly aggregation, population interpolation),
`src/preprocessing/module1_preprocessing.py` (week-53 merge, seasonal-naive
imputation, climate + population merge, `cases_per_100k`), and two new
files, `src/module1_forecasting/validation.py` (walk-forward fold generator,
`fit_window`/`get_holdout_series` no-leakage helpers) and
`src/module1_forecasting/feature_engineering.py` (fold-agnostic Stage 2
features + a `compute_fold_climate_anomalies` function for the fold-aware
ones). `baseline_sarima.py`/`compensation_model.py`/`combine.py`/
`evaluate.py`/`main.py` remain out of scope (SARIMA order selection, log1p
vs raw, etc. are still open research questions).

While spot-checking the master epi-week calendar (explicitly required by the
build plan before trusting it downstream), found a **new, previously
undiscovered data-quality issue distinct from the 5 collisions fixed
2026-07-26**: 30 `(Year, Week)` labels across 2008-2024 have a date stamp
that essentially all districts agree on (so it never showed up as a
duplicate-key or per-row disagreement) but that is chronologically
inconsistent with neighbouring weeks - almost certainly a page-level MoH
scrape error for that specific week, not a per-row transcription slip. This
measurably breaks the day-to-week join for climate aggregation on 15 of
those weeks (375 of 25,350 rows in `weekly_modeling_table.csv` have no
matching climate because of this; a further 125 rows have no climate for
the separate, expected reason that climate coverage doesn't extend into the
2006/2026 boundary years). Also confirmed the 4 documented nationwide case-data
gaps (`2015 Wk30`, `2020 Wk1`, `2021 Wk42`, `2022 Wk43`) have zero raw rows
for any district at all - not even a calendar entry - and added a
conservative `fill_isolated_calendar_gaps` step to `shared.py` that
sequentially infers a date only when it fits an unambiguous single 7-day
slot; this recovered dates for 3 of the 4 (`2020 Wk1` could not be dated -
2019's confirmed week-53 already runs through 2020-01-03, leaving no gap for
a "week 1"). None of this was silently patched into "correct" values - it
is fully logged, written to diagnostic CSVs
(`epi_week_calendar_chronology_issues.csv`,
`epi_week_calendar_disagreements.csv`) in `data/processed/shared/`, and
flagged for the same joint human-review process used for the earlier 5
collisions.

### Reason
The build plan explicitly required spot-checking the calendar-construction
step for ties/ambiguous cases before trusting it downstream; doing so
surfaced a real, previously-unknown, and non-trivial data quality issue
(distinct in kind from the already-fixed collisions) that affects climate
feature completeness for ~2% of Module 1's weekly rows.

### Impact
- Added: `data/processed/shared/{epi_week_calendar.csv, climate_weekly.csv,
  population_annual.csv, epidemiological_weekly.csv,
  epi_week_calendar_disagreements.csv,
  epi_week_calendar_chronology_issues.csv}`.
- Added: `data/processed/module1/weekly_modeling_table.csv`.
- Added: `data/features/module1/stage2_feature_table.csv`.
- Updated: `src/config.py`, `src/preprocessing/shared.py`,
  `src/preprocessing/module1_preprocessing.py`.
- Added: `src/module1_forecasting/validation.py`,
  `src/module1_forecasting/feature_engineering.py`.
- Updated: `module_1_forecasting/MODULE_CONTEXT.md` (implementation status,
  deviations from plan, 3 new open questions #9-11),
  `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (status/last-updated,
  new open item for the chronology-issue discovery),
  `research_context/DATA_DICTIONARY.md` (new Data Quality Notes rows).

### Status
Accepted (pipeline code); the newly discovered 30-week date-mislabeling
issue is flagged Open, pending team review - not yet resolved.

---

## 2026-07-27 - Systematic Date-Mislabeling Issue Resolved in Raw Epidemiological Data

### Module
Module 1 (raw data feeds all downstream shared/Module 1 outputs)

### Change
Resolved the 30-week systematic date-mislabeling issue discovered while
implementing the shared preprocessing layer (previous entry). The user
manually corrected 28 of the 30 flagged `(Year, Week)` labels in
`dengue_cases_corected.csv` against the original MoH source pages,
reporting back a detailed row-by-row account of what was found and fixed
(mostly month-field-off-by-one errors and week-boundary overlaps). The
assistant then re-ran the pipeline and cross-checked every one of the 30
against the regenerated calendar, which found:

- **2 of the 30 the user's pass had missed** (`2009 Wk24`, `2023 Wk40`) —
  both had the same month-field error as the other 28, just not caught
  during manual review. Corrected by the assistant.
- **A full-calendar day-count scan** (checking *every* week in the dataset
  for exactly 7 days and a clean 1-day gap to its neighbour, not just the
  overlap-based check that found the original 30) surfaced 3 more
  previously-undetected date-entry errors that don't manifest as overlaps
  and so were invisible to both the original diagnostic and the user's
  manual review: `2010 Wk9` (end date literally before its start date),
  `2011 Wk48` (start date 3 days late, producing a 4-day week), and
  `2013 Wk39`/`Wk40` (a 1-day boundary misplacement). Corrected by the
  assistant.
- The 2 outstanding per-row disagreements from the original diagnostic
  (`Ampara 2013 Wk51`, `Ampara 2023 Wk14`) were also corrected.
- **2 weeks accepted as irregular by design**: `2009 Wk17` (8 days) and
  `2009 Wk22` (6 days) each sit in a stretch with a genuine 1-day
  surplus/deficit in the source that cannot be fixed by editing one date
  without opening a new gap with an already-correct neighbour — verified
  concretely rather than assumed (the assistant initially "fixed" `2009
  Wk17` by shortening it, found this created a brand-new 2-day gap with
  `Wk18`, and reverted the change).
- **1 low-priority item left open**: a genuine 3-day gap between `2025
  Wk52` and `2026 Wk1` at the live-scrape edge of the dataset.
- Also fixed a minor pipeline robustness bug found during verification:
  `shared.py` previously only wrote the two chronology/disagreement
  diagnostic CSVs when non-empty, so a clean re-run after fixing the
  underlying data left a stale issues file on disk from the previous run.
  `run_shared_preprocessing()` now always rewrites both files.

Re-ran the full pipeline (`shared.py` → `module1_preprocessing.py` →
`feature_engineering.py`) after every fix to confirm no regressions.
`epi_week_calendar_chronology_issues.csv` and
`epi_week_calendar_disagreements.csv` are now both empty. All 375 climate
rows previously blocked by this issue in `weekly_modeling_table.csv` are
now populated; the only remaining 150 "no matching climate" rows are the
expected boundary cases (2006 Wk52 before climate coverage begins, 2020
Wk1's dateless rows, 2026 Wk22-25 after current climate coverage ends).

### Reason
The 30-week issue was flagged as needing joint human review before
correcting the raw source, per the same process used for the 5 collisions
fixed 2026-07-26. Verifying the user's fixes against the regenerated
calendar (rather than trusting the fix count at face value) surfaced
additional real errors invisible to both the original overlap-only
diagnostic and manual source-page review, which would have silently
persisted into the modeling data otherwise.

### Impact
- `data/raw/epidemiological/dengue_cases_corected.csv` — corrected in place
  (28 rows by the user; 5 more date fixes + 2 disagreement fixes + 3 stale
  `Month`-column cosmetic fixes by the assistant; all changes verified via
  full pipeline re-run).
- `src/preprocessing/shared.py` — diagnostic CSVs now always rewritten
  (fixes staleness bug).
- Regenerated: all `data/processed/shared/*.csv`,
  `data/processed/module1/weekly_modeling_table.csv`,
  `data/features/module1/stage2_feature_table.csv`.
- `research_context/DATA_DICTIONARY.md` — Data Quality Notes rows updated
  from Open to Resolved, with exact before/after values for every fix and
  the two accepted-irregular-week exceptions documented.
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` — Open Item 4 marked
  resolved; Open Item 5 (`2020 Wk1` dateless week) remains open and
  unrelated to this fix.
- `module_1_forecasting/MODULE_CONTEXT.md` — Open Question #10 marked
  resolved with full detail; `climate_weekly.csv` row count updated
  (24,950 → 25,300).

### Status
Accepted. Open Item 5 (`2020 Wk1`) and the `2025 Wk52`/`2026 Wk1` 3-day
gap remain open, unrelated data-quality items requiring separate team
decisions.

---

## 2026-07-26 - Module-Level Documentation Structure Added

### Module
All modules

### Change
Created separate module folders with their own `MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md` files.

### Reason
Three team members work on separate modules. Each module needs its own source of truth.

### Impact
Added:

- `module_1_forecasting/MODULE_CONTEXT.md`
- `module_1_forecasting/EXPERIMENT_LOG.md`
- `module_2_classification/MODULE_CONTEXT.md`
- `module_2_classification/EXPERIMENT_LOG.md`
- `module_3_spatial/MODULE_CONTEXT.md`
- `module_3_spatial/EXPERIMENT_LOG.md`

### Status
Accepted

---

## 2026-07-27 - Raw Weather Folder Flattened; Build Plan Relocated

### Module
All modules (Module 1 most directly affected)

### Change
The user moved the 25 canonical per-district weather CSVs out of the nested
`data/raw/weather/Weather (Except Humidity)/` subfolder directly into
`data/raw/weather/`, and deleted the now-redundant `data/raw/weather/Humidity/`
subfolder entirely (both subfolders no longer exist). Separately,
`PIPELINE_ARCHITECTURE_PLAN.md` was relocated from `docs/` to
`research_context/` (the `docs/` folder no longer exists). Updated all path
references accordingly: `DATA_DICTIONARY.md`, `module_1_forecasting/MODULE_CONTEXT.md`,
`PIPELINE_ARCHITECTURE_PLAN.md` itself (weather path), and `scripts/data_audit_module1.py`
(simplified to a single `WEATHER_DIR` with no Humidity-comparison logic); and all
`docs/PIPELINE_ARCHITECTURE_PLAN.md` cross-references in `CURRENT_ARCHITECTURE.md`,
`RESEARCH_DECISIONS.md`, `FEATURE_ENGINEERING_SPEC.md`, and all three
`MODULE_CONTEXT.md` files were repointed to `research_context/PIPELINE_ARCHITECTURE_PLAN.md`.

### Reason
Keep living documentation and scripts in sync with the actual raw-data folder
layout and file locations on disk, so pipeline code written against these paths
doesn't break.

### Impact
Weather ingestion in the upcoming `src/preprocessing/shared.py` should read
`data/raw/weather/*.csv` directly (no subfolder). All references to
`docs/PIPELINE_ARCHITECTURE_PLAN.md` should be read as
`research_context/PIPELINE_ARCHITECTURE_PLAN.md`.

### Status
Accepted

---

## 2026-07-27 - Stage 1 Explosive-AR-Root Fix; Real-World Outbreak Sanity Check

### Module
Module 1

### Change
Fixed the `Vavuniya`/`Mannar` SARIMA divergence flagged as Open Question #14
during Stage 2 development: `baseline_sarima.fit_and_forecast()` now checks
every fitted SARIMAX model's combined AR polynomial roots and treats any fit
with a root on or inside the unit circle (non-stationary/explosive despite
`enforce_stationarity=False`) as a failed fit (`NaN` for that fold), instead
of returning an unbounded-growth forecast. Confirmed via a full 25-district
scan that this affects exactly two folds: `Vavuniya` fold 1 (2010, AR(1)
coefficient 1.266) and `Mannar` fold 13 (2022, seasonal AR coefficient
1.162). The full Stage 1 → Stage 2 → combine pipeline was regenerated
(`main.py --force --stages stage1_sarima stage2_xgboost combine`, ~62
minutes). `compensation_model.py` (`_trainable_mask()`) and `combine.py`
(`residual_variance_reduction()` switched to `np.nanvar`) were hardened to
correctly handle the newly-possible `NaN` residual rows. Also fixed a
sign-convention bug found while re-verifying results: `evaluate.dm_test`'s
docstring had `mean_loss_diff`'s interpretation backwards (the code was
already correct; only the prose was wrong).

Separately, while investigating whether the framework could predict the
real, ongoing 2026 Colombo/Gampaha dengue outbreak (the dataset already
extends to 2026 week 25, which includes the actual spike inside the
untouched holdout block), found that the shared climate data pipeline has
not been refreshed past 2026 week 21 - leaving every climate feature `NaN`
for weeks 22-25, exactly the weeks containing the outbreak spike.

### Reason
The Vavuniya/Mannar divergence was previously only mitigated at the Stage 2
level (Decision 014's MAE loss switch contained the symptom) but never
fixed at the source, and was explicitly flagged in Open Question #14 as
worth a targeted look. A user question about the framework's real-world
predictive accuracy on the current outbreak prompted revisiting this fix
before further real-world evaluation, and separately surfaced the climate
data currency gap as a distinct, actionable finding.

### Impact
- `data/processed/module1/sarima_stage1_predictions.csv`,
  `models/module1/sarima_selected_configs.csv`,
  `outputs/metrics/module1/sarima_walk_forward_metrics.csv`,
  `data/processed/module1/xgboost_stage2_predictions.csv`,
  `data/processed/module1/final_combined_predictions.csv`,
  `outputs/metrics/module1/combined_vs_baseline_metrics.csv`, and
  `outputs/metrics/module1/diebold_mariano_results.csv` all regenerated.
- Stage 2's headline result improved from 24/25 to **25/25 districts**
  improving on validation-aggregate MASE; median validation MASE
  improvement 43.5% (was ~42.8%), median holdout MASE improvement 32.7%
  (was ~28.7%). `Vavuniya` went from one of the most fragile districts to
  one of the best. Holdout win rate is 23/25 (`Kilinochchi`, `Mannar` show
  small, non-significant holdout regressions).
- `module_1_forecasting/MODULE_CONTEXT.md` (Open Question #14 resolved and
  fixed; Open Question #12's numbers refreshed; new Open Question #16 for
  the climate-data-lag/real-world-outbreak finding; "Stage 1/2
  Implementation Status" sections fully refreshed).
- `research_context/RESEARCH_DECISIONS.md` (new Decision 017; Decision 016
  annotated as superseded by it).
- `module_1_forecasting/EXPERIMENT_LOG.md` (new entry M1-003).
- The climate data pipeline currency gap (2026 weeks 22-25) is flagged but
  **not yet fixed** - re-running the shared climate preprocessing (Open-Meteo
  fetch) through the current date is a follow-up action item.

### Status
Accepted

---

## 2026-07-27 - Module 1 Forward Production Forecast Added

### Module
Module 1

### Change
Added `src/module1_forecasting/forecast_future.py` (new): generates a
genuine forward forecast for 8 weeks beyond the last available case-count
week (2026 weeks 26-33), for all 25 districts. Stage 1 is refit on each
district's entire available history and forecasts 8 steps ahead in one
deterministic call; Stage 2 applies the existing final production XGBoost
model recursively (real historical values feed the first 1-2 future weeks'
lag features, then the script's own prior-step predictions feed all later
weeks). A `feature_completeness_pct` diagnostic is reported per row to
quantify declining confidence with horizon. Outputs
`data/processed/module1/future_forecast.csv` and illustrative plots for
`Colombo`/`Gampaha`.

### Reason
Prompted by the user asking whether Module 1's testing was complete and
whether it can predict genuinely future case counts - a different question
from the already-answered "does the holdout MASE improve" (M1-002/M1-003).
No existing script in the pipeline could answer this: walk-forward
validation and the holdout block both score against data already present in
the dataset, not genuinely new weeks.

### Impact
- New file `data/processed/module1/future_forecast.csv` (200 rows) and new
  plots `outputs/figures/module1/future_forecast_{Colombo,Gampaha}.png`.
- `src/config.py`: added `MODULE1_FUTURE_FORECAST_PATH`.
- For the real-outbreak districts: `Colombo`'s forecast settles to a
  ~460-470/week plateau (from a pre-spike ~300-500/week baseline);
  `Gampaha`'s settles to a ~1,360-1,370/week plateau (from ~200-500/week) -
  both clearly elevated but not simply repeating the single week-25 spike
  value (1,138/1,294), consistent with the model discounting what may be a
  partly reporting-lag-driven outlier (a suspicious week-24 dip precedes the
  spike in both districts).
- `feature_completeness_pct` declines from 56.2% (horizon step 1) to 43.8%
  (steps 5-8) as `residual_lag_1/2` become fully recursive and climate lags
  run out of range - reported explicitly rather than hidden.
- Deliberately **not** wired into `main.py`'s orchestration and does **not**
  close Open Question #16's climate-data-currency gap or substitute for the
  still-not-built rolling 1-week-ahead re-evaluation - both remain open.
- `research_context/RESEARCH_DECISIONS.md` (new Decision 018).
- `module_1_forecasting/MODULE_CONTEXT.md` (new "Forward Production
  Forecast" section).
- `module_1_forecasting/EXPERIMENT_LOG.md` (new entry M1-004).

### Status
Accepted
