# Pipeline Architecture Plan

## Status
Living technical build plan. This is the concrete, implementation-level companion to
`research_context/CURRENT_ARCHITECTURE.md`. Update this file whenever the pipeline's
stages, scripts, or file layout change. Research-level rationale and decisions belong
in `research_context/RESEARCH_DECISIONS.md`; this file is about *how it is built*.

**Implementation status (2026-07-27):** the Stage 0 fix, the Shared Layer,
and the Module 1 Layer described below are now implemented and have been run
against the real data - see `module_1_forecasting/MODULE_CONTEXT.md`
"Implementation Status" section for exact row counts and deviations from this
plan. The systematic date-mislabeling issue affecting 30 epi-weeks (found
while spot-checking the calendar) plus a further 5 date-entry errors and 2
per-row disagreements found by a follow-up full-calendar day-count scan are
now all resolved at the source (`dengue_cases_corected.csv`) — see Open Item 4
below. Module 1's Stage 1/2 modeling scripts (`baseline_sarima.py` onward)
remain unimplemented pending resolution of the open SARIMA/log-transform
questions.

**Implementation status (2026-07-28):** Module 2's label definition is now
settled (Decision 019) and its "Module 2 Layer" section below has been
expanded from a placeholder into a concrete build plan. Preprocessing, label
definition, and Stage 1 feature engineering are implemented and have been
regenerated against the real data after a dedicated preprocessing review
(Decision 020 — week 53 kept unmerged, `is_imputed` masking made consistent).
**Module 2 Stage 1 (`baseline_classifier.py`) is now also implemented and
run end to end** (Decision 021 — new `MODULE2_MIN_TRAIN_YEARS=4`, 13
walk-forward folds, pooled architecture confirmed empirically, XGBoost
selected as the official model).

**Module 2 Stage 2 (`compensation_model.py`) is now also implemented and run
end to end** (Decision 022 — three well-posed architectures benchmarked by
Brier Skill Score, not a literal residual regression; Platt scaling
originally selected — see M2-002, since superseded).

**Implementation status (2026-07-28, Decision 023/024):** Module 2 Stage 1's
XGBoost hyperparameters were tuned via a holdout-gated Optuna search
(`scripts/tune_stage1_xgboost.py`) and adopted — `XGB_BASE_PARAMS` in
`baseline_classifier.py` updated permanently (holdout PR-AUC 0.538 → 0.558).
Stage 1 + Stage 2 were rerun with `--force`; **Stage 2's official
architecture flipped from Platt scaling to isotonic regression** (median BSS
0.166, holdout BSS 0.320) as a downstream consequence of Stage 1's changed
probability distribution — see M2-003. A new permanent pipeline stage,
`src/module2_classification/risk_thresholds.py`, was also added
(`stage2_risk_thresholds` in `main.py`), selecting an F2-optimal alert
threshold (0.170) and F0.5-optimal high-confidence tier boundary (0.570) —
completing Decision 022's deferred risk-tier item. See
`module_2_classification/MODULE_CONTEXT.md` "Stage 1/Stage 2 Implementation
Status" and `EXPERIMENT_LOG.md` M2-003/M2-004 for full results.

**Implementation status (2026-07-28, Decision 025/M2-005):** Module 2's
label `historical_mean`/`historical_sd` ESTIMATOR (`src/module2_classification
/labels.py`) was replaced — a per-district harmonic-regression seasonal
curve (`compute_historical_stats_harmonic`, `n_harmonics=1`) now supplies
these quantities instead of Decision 019's exact-per-(District, Week)
sample mean/SD (kept in the codebase, marked superseded, for audit/
comparison). `k` was re-audited `2.0` → `3.0` for the new estimator. The
threshold FORMULA and leakage guard are unchanged. `feature_engineering.py`
was updated to match (Group M2-5 reuses the same estimator as the label).

**Implementation status (2026-07-28, new):** a new standalone script,
`src/module2_classification/live_scoring.py`, was added on top of the
training/evaluation pipeline above (not wired into `main.py`'s
`PIPELINE_STAGES`, same precedent as Module 1's `forecast_future.py`). It
recomputes Stage 1 features fresh from the current
`weekly_modeling_table.csv` and scores the most recent N weeks per district
through the frozen Stage 1/2 final-production models + persisted risk
thresholds, for dashboard consumption without a full pipeline rerun. Surfaced
a new finding while building it: Module 2 shares Module 1's Open Question
#16 climate-currency gap (see `module_2_classification/MODULE_CONTEXT.md`
Open Question #10) — the shared climate pipeline is 4 weeks behind case-count
data as of this writing.
Pooled outbreak prevalence dropped 18.4% → 8.6%; undefined-label rate
improved 16.0% → 10.7%. **Important correction found during this work**:
the motivating example (Colombo 2025 Wk15) was already correctly labeled
under the OLD estimator — the real issue there was a Stage 2 calibration
near-miss, not a label defect; adopting the new estimator+k actually flips
that specific row's label (an accepted, documented trade-off of fixing the
aggregate-prevalence problem with one global `k`). Full pipeline (feature
engineering through risk thresholds) rerun with `--force`; Stage 1's
official model flipped to Random Forest, Stage 2 remains isotonic
regression (now a much closer contest with Platt), risk thresholds
recalibrated lower (alert 0.170 → 0.140, high-confidence 0.570 → 0.350).
See `module_2_classification/MODULE_CONTEXT.md` Open Question #8 and
"Stage 1/Stage 2 Implementation Status", `EXPERIMENT_LOG.md` M2-005, and
`RESEARCH_DECISIONS.md` Decision 025 for full results.

**Implementation status (2026-07-29, Decision 027):** operational early-warning layer
implemented — Open-Meteo climate refresh (`scripts/fetch_open_meteo_weather.py`),
refresh orchestrator (`scripts/refresh_dashboard_data.py`), Module 2 forward
operational risk (`src/module2_classification/forecast_future_risk.py`, M1-fed
case lags), shared scoring helpers (`scoring_utils.py`), and Streamlit dashboard
(`src/dashboard/app.py`). Climate-currency gap (Open Question #16/#10) closed for
observed weeks through 2026 Wk25; daily weather extends through forecast API
horizon (~16 days). Forward epi-week climate beyond the master calendar edge
remains a documented limitation.

## Last Updated
2026-07-29 (operational dashboard layer — Decision 027)

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
(SARIMA per district)      (classifier — DONE)         (KDE / Moran's I, TBD)
   |                          |                            |
   v                          v                            v
feature_engineering.py    feature_engineering.py      feature_engineering.py
(Module 1)                (Module 2 — DONE)             (Module 3, TBD)
   |                          |                            |
   v                          v                            v
data/features/module1/    data/features/module2/      data/features/module3/
   |                          |                            |
   v                          v                            v
Stage 2 compensation       Stage 2 compensation        Stage 2 compensation
(XGBoost on residuals)     model (isotonic — DONE)      model (TBD)
   |                          |
   v                          v
                           risk_thresholds.py
                           (alert flag + tiers — DONE)
```

Module 1 and Module 2's paths are both detailed below (both have implemented, run
pipelines). Module 3's section remains a placeholder to be filled in when that module
is actively built — it must not be skipped, just deferred.

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
| `src/module1_forecasting/rolling_one_step.py` | Rolling 1-step-ahead operational evaluation (Decision 029; standalone CLI, not a `main.py` stage) |

## `src/module1_forecasting/rolling_one_step.py` (new, standalone — Decision 029)

Answers: "if we refit SARIMA each week on all data strictly before week *t* and
forecast only *t*, then apply the frozen Stage 2 checkpoint, how accurate are we?"
— the evaluation mode closest to real weekly production deployment. Distinct from
`baseline_sarima.forecast_holdout()` (single SARIMA fit → 104-week multi-step block)
and from walk-forward fold scoring (fixed fold structure for model selection).

Per week *t* per district: refit SARIMA on pre-*t* history using stored order/config;
1-step forecast; build fold-agnostic features with `is_imputed` + `is_reporting_anomaly`
masking; compute fold-scoped climate anomalies from the train-only window ending at
*t*−1; score with frozen `xgboost_final_model.json`; clip `final_prediction` ≥ 0.

CLI: `python -m src.module1_forecasting.rolling_one_step [--districts ...] [--scope holdout|all]`

Outputs: `data/processed/module1/rolling_one_step_predictions.csv`,
`outputs/metrics/module1/rolling_one_step_metrics.csv`.

---

# Module 2 Layer (kickoff started 2026-07-28 — see Decision 019)

Label definition is now settled (Decision 019, fold-aware epidemic-threshold
method) — this section is no longer a placeholder for the preprocessing/label
steps below. Stage 1 (`baseline_classifier.py`) is implemented (Decision 021,
hyperparameters tuned by Decision 023); Stage 2 (`compensation_model.py`,
Decision 022) and the risk-threshold follow-up (`risk_thresholds.py`,
Decision 024) are both implemented and run end to end.

## `src/preprocessing/module2_preprocessing.py` (revised 2026-07-28 — Decision 020)

Reads `data/processed/shared/*.csv` — the same Kalmunai-merged, calendar-aligned
base tables Module 1 uses. Applies Module 2's **own** temporal-adjustment
decisions (Decision 013 — these are independent of, and may coincidentally
match, Module 1's choices, but must not be silently inherited). A dedicated
preprocessing review (Decision 020) finalized these before Stage 1 modeling
began, revising two of the three original kickoff defaults:

1. **Missing weeks**: reuse the same seasonal-naive imputation + `is_imputed`
   flag as Module 1 — still required even without SARIMA's algorithmic
   constraint, because Stage 1's `.shift()`-based lag features would otherwise
   silently misalign across a gap. Rows flagged `is_imputed` are excluded from
   serving as a **label target**, AND (Decision 020 fix) masked to `NaN`
   *consistently* before deriving any case-derived feature that could see them
   (`cases_lag_*`, rolling stats, `case_anomaly_lag_*`) — the first
   implementation pass only masked `case_anomaly_lag_*` and the label,
   letting a fabricated case count silently flow into plain lag/rolling
   features for neighboring real weeks.
2. **`weather_code`**: excluded by default (same reasoning as Decision 008 —
   redundant with continuous climate variables); reconfirmed unchanged during
   the Decision 020 review.
3. **Week 53** (**REVERSED**, Decision 020): kept as its own week, NOT merged
   into week 52. The original kickoff default merged it (matching Decision
   007's rule) "for implementation simplicity" — but unlike Module 1, where
   only total magnitude matters, merging here sums two real weeks' cases
   *before* the epidemic threshold is computed, which can (a) spuriously
   trip the outbreak threshold from merge arithmetic alone, and (b)
   contaminates week 52's cross-year `historical_mean`/`SD` (used by
   `labels.py`) for every year, not just the four merged ones.
   Kept unmerged, week 53 will almost always get an undefined label (only 4
   total occurrences, short of the 3-strictly-prior-years rule) — honest, not
   a defect. Requires a Module-2-local `MODULE2_MONSOON_WEEKS_NE` override
   (`= MONSOON_WEEKS_NE + [53]`, week 53 falls in late December/NE monsoon)
   since the shared constant assumes Module 1's merged 52-week structure;
   `sin_week`/`cos_week` need no special-casing (periodicity already makes
   week 53's value equal week 1's).
4. Merge in climate (`climate_weekly.csv`) and population
   (`population_annual.csv`) exactly as Module 1 does; compute `cases_per_100k`
   as a reporting-layer column (Decision 006).
5. Output: `data/processed/module2/weekly_modeling_table.csv` — 25,450 rows,
   52 weeks/year except 53 for `{2009, 2016, 2019, 2021}`, 102 rows flagged
   `is_imputed`.

## `src/module2_classification/labels.py`

(Note: named `labels.py`, not `label_definition.py` as earlier drafts of
this plan called it — corrected 2026-07-28.) Implements Decision 019's
fold-aware epidemic-threshold label:
`outbreak = 1 if Number_of_Cases > historical_mean + k * historical_SD`,
where the historical mean/SD for any row uses **only strictly-prior years**
— never the full series. Requires >= 3 strictly-prior years of history
before a label is defined (rows without enough history are excluded, not
defaulted to 0). This is a **label**-leakage guard, distinct in kind from
Module 1's feature-leakage guard (`compute_fold_climate_anomalies`) —
reuses `src/module1_forecasting/validation.py`'s
`generate_walk_forward_folds_by_district` directly (already module-agnostic)
rather than duplicating fold-generation logic.

**`historical_mean`/`historical_SD` estimator (updated 2026-07-28, Decision 025)**:
`compute_historical_stats_harmonic` (per-district harmonic-regression seasonal
curve, `n_harmonics=1`, refit expanding per year on strictly-prior real data)
is now the official estimator `compute_epidemic_threshold_labels` calls,
replacing the original exact-per-`(District, Week)` sample mean/SD
(`compute_historical_stats`, kept in the file, marked superseded, for
audit/comparison via `scripts/audit_label_stabilization.py`). `k` changed
`2.0` → `3.0` alongside this (re-audited for the new estimator's different
SD semantics, not carried over). Motivation: the exact-week estimator was
too noisy from small per-week samples (18-25% pooled outbreak prevalence);
harmonic regression pools an entire season per district-year, reducing
prevalence to 8.6% while also lowering the undefined-label rate. See
`RESEARCH_DECISIONS.md` Decision 025 for full audit results, including the
important finding that the motivating "Colombo under-flagged" example was
actually already correctly labeled under the old estimator (a Stage 2
calibration issue, not a label issue) and the honest trade-off that the new
`k=3.0` flips that specific row's label the other way.

## `src/module2_classification/feature_engineering.py` (implemented 2026-07-28)

Reads `data/processed/module2/weekly_modeling_table.csv`, builds Stage 1
features per `FEATURE_ENGINEERING_SPEC.md`'s Module 2 section (finalized
after a dedicated feature-engineering review, not just the original
placeholder bullet list): case lags/rolling trend/rate-of-change/momentum,
lagged climate (`rainfall_lag_2-8`/`temperature_lag_1-4`/`humidity_lag_1-4`,
added after review to capture dengue's transmission delay), current-week raw
climate, `sin_week`/`cos_week`/monsoon indicators, and case-level seasonal
anomaly lags (`case_anomaly_lag_1/2`, added after review) — all fold-agnostic,
enumerated in `FOLD_AGNOSTIC_FEATURE_COLUMNS`. Fold-aware climate anomalies
are reused unchanged from Module 1's `compute_fold_climate_anomalies`. Does
**not** include baseline-probability or probability-error-lag features yet —
those are added once Stage 1 exists, mirroring how Module 1 added
`sarima_prediction`/`residual_lag_1/2` only after Stage 1 was built.
`Number_of_Cases`/`cases_per_100k`/raw `Year` are present in the output table
(for merging/reporting) but explicitly excluded from the feature list — a
real leakage risk caught and fixed during the review (see
`research_context/CHANGELOG.md`'s 2026-07-28 entry). Regenerated again after
Decision 020 (week-53 unmerged, `is_imputed` masking consistency fix) —
53 columns, 32 fold-agnostic model features.

## `src/module2_classification/baseline_classifier.py` (Stage 1 — implemented 2026-07-28, Decision 021; hyperparameters tuned 2026-07-28, Decision 023; label re-estimated 2026-07-28, Decision 025 — official model now Random Forest)

Benchmarks Logistic Regression / Random Forest / XGBoost per walk-forward
fold, pooled across all 25 districts (`District` as a categorical feature).
Uses a new Module-2-specific `MODULE2_MIN_TRAIN_YEARS = 4` (`src/config.py`)
instead of `validation.py`'s SARIMA-tuned `DEFAULT_MIN_TRAIN_YEARS = 3` —
verified empirically that the SARIMA-tuned default leaves fold 1's entire
training window with zero rows that have a defined label, since the
label's own 3-strictly-prior-years requirement (Decision 019) exactly
overlaps that window for every district simultaneously. Yields 13
walk-forward folds (vs. Module 1's 14) plus the same 2-year final holdout.

Pooled-vs-per-district is validated **empirically**, via a dedicated
`run_pooled_vs_per_district_comparison()` using XGBoost alone as the
arbiter (no imputation/encoding confound) — result: pooled median PR-AUC
0.500 vs. per-district median 0.287 across the 13 folds, confirming the
pooled choice. Uses `class_weight="balanced"` (Logistic Regression, Random
Forest) / per-fold `scale_pos_weight` (XGBoost) for imbalance — explicitly
not SMOTE, since synthetic oversampling before/across a temporal split risks
fabricating points that blur the fold boundary. Logistic Regression/Random
Forest use an identical `ColumnTransformer` (median-impute + one-hot
`District`, fit on training rows only per fold) — corrects the original
premise that "tree-based models handle NaN natively" (only true for
XGBoost among these three; `RandomForestClassifier` requires imputation).
**XGBoost selected** as the official model by median validation PR-AUC.
**Hyperparameters tuned via Optuna (Decision 023, `scripts/
tune_stage1_xgboost.py`)**: 60-trial TPE search, objective = median PR-AUC
across the 13 validation folds, adopt/reject decided purely on the untouched
holdout block (never gated on the search's own objective, to avoid
compounding the mild selection bias already accepted for model-TYPE
selection). Adopted: holdout PR-AUC 0.538 → 0.558, ROC-AUC 0.898 → 0.911.
Current production `XGB_BASE_PARAMS`: `max_depth=3, learning_rate=0.01237,
n_estimators=217, subsample=0.6565, colsample_bytree=0.5962,
reg_lambda=1.0758, min_child_weight=10, reg_alpha=4.1197, gamma=2.4930`.
`fit_and_predict` gained an optional `xgb_params` override parameter (XGBoost
only; `scale_pos_weight` always recomputed per-fold regardless, never
overridable) so the tuning script can reuse the walk-forward loop unchanged.
Outputs: `data/processed/module2/baseline_classifier_predictions.csv`,
`outputs/metrics/module2/{baseline_classifier_metrics,
pooled_vs_per_district_comparison, baseline_classifier_feature_importance}.csv`,
`models/module2/baseline_classifier/`; tuning-specific:
`outputs/metrics/module2/{xgboost_tuning_trials,
xgboost_tuning_holdout_comparison}.csv` (not part of the production
pipeline — standalone research script only). **Model selection FLIPPED to
Random Forest after Decision 025's label re-estimation** (median validation
PR-AUC 0.377 vs. XGBoost's 0.373 under the new, much lower-prevalence
label) — `XGB_BASE_PARAMS` themselves were not re-tuned, only the label
changed underneath the existing 3-model benchmark. Full results:
`module_2_classification/MODULE_CONTEXT.md` "Stage 1 Implementation
Status", `module_2_classification/EXPERIMENT_LOG.md` M2-001 (original,
superseded)/M2-003 (post-tuning, superseded)/M2-005 (current, post-label-
re-estimation).

## `src/module2_classification/compensation_model.py` (Stage 2 — implemented 2026-07-28, Decision 022; rerun 2026-07-28 after Stage 1 retuning, Decision 023; rerun again 2026-07-28 after label re-estimation, Decision 025 — isotonic remains official)

Benchmarks three numerically well-posed architectures per walk-forward fold
(a literal `label - predicted_probability` residual regression was
considered and rejected as ill-posed for a binary target — see Decision
022's Reason): **isotonic regression** and **Platt scaling** (both pooled,
feature-free, applied directly to Stage 1's `predicted_probability`/
`logit(predicted_probability)`), and a **stacked XGBoost** model on
`[predicted_probability, contextual features, District,
probability_residual_lag_1/2]` → `label`. Selected by median **Brier Skill
Score** across 12 trainable folds (fold 1 is a no-op passthrough — no prior
out-of-sample Stage 1 probabilities exist yet), gated by a check that
PR-AUC/ROC-AUC don't regress vs. Stage 1's raw probability.

No-leakage rule (Decision-010-style, adapted): fold *k* (`k = 2..13`) trains
only on the official Stage 1 model's out-of-sample `predicted_probability`/
`label` from folds `1..k-1`, never fold *k* itself. Pooled-vs-per-district
is re-validated empirically (stacked-XGBoost arbiter), not assumed from
Decision 021. **Isotonic regression is the current official architecture**
(median BSS 0.166; originally Platt scaling won pre-Stage-1-retuning, see
M2-002 — the flip is a downstream consequence of Decision 023's Stage 1
retuning, not a Stage 2 code change). Outputs:
`data/processed/module2/stage2_compensated_predictions.csv`,
`outputs/metrics/module2/{stage2_compensation_metrics,
stage2_pooled_vs_per_district_comparison}.csv`,
`outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
`models/module2/stage2_compensation/`. Module 1 forecast integration remains
deliberately deferred (Decision 022); risk-tier thresholds are now
implemented separately — see `risk_thresholds.py` below.

## `src/module2_classification/risk_thresholds.py` (Stage 2 follow-up — implemented 2026-07-28, Decision 024; recalibrated 2026-07-28, Decision 025)

Permanent pipeline stage (`stage2_risk_thresholds` in `main.py`, unlike
Decision 023's one-off tuning script) completing Decision 022's deferred
risk-tier item. Reads `stage2_compensated_predictions.csv`; selects an
**F2-optimal alert threshold** (recall-weighted — early-warning framing) and
an **F0.5-optimal high-confidence tier boundary** (precision-weighted,
clipped to `>= alert_threshold`) purely from the official architecture's
validation-fold rows (folds 2-13 — fold 1's `architecture="none"`
passthrough never carries the official architecture's rows, so no separate
fold check is needed), holdout reserved for the final evaluation. New
`evaluate.py` functions: `fbeta_score(y_true, y_pred_label, beta, mask=None)`
(generalizes `f1`), `threshold_scan(y_true, y_prob, thresholds=..., mask=None)`
(99-cutoff scan, columns `precision/recall/f1/f2/f0_5/accuracy`).

**Current (post-Decision-025) selected values**: `alert_threshold = 0.140`,
`high_confidence_threshold = 0.350` — recalibrated lower after the label
re-estimation reduced overall prevalence. Holdout evidence: F2-optimal
0.140 gives recall 60.0%/F2 0.519 (vs. naive 0.5's recall 45.0%/F2 0.459).
Empirical tier separation (observed outbreak rate): 0.6%/13.3%/48.8%
(low/medium/high) on holdout, 1.3%/26.2%/71.1% on validation folds 2-13.
**Historical (pre-Decision-025) values, superseded**: `alert_threshold =
0.170`, `high_confidence_threshold = 0.570`; holdout recall 39.9% → 68.6%,
F2 0.437 → 0.574; tier separation 2.6%/22.0%/76.7% (holdout),
3.2%/27.3%/83.2% (validation) — not comparable to the current values since
the label itself changed. Outputs:
`data/processed/module2/stage2_risk_tier_predictions.csv` (adds
`alert_flag`/`risk_tier` to every row of `stage2_compensated_predictions.csv`,
all architectures/splits, for audit),
`outputs/metrics/module2/{risk_threshold_scan,
risk_threshold_holdout_comparison}.csv`.

## `src/module2_classification/live_scoring.py` (new, standalone — not a `main.py` stage)

Answers a question none of the stages above do: "what does the fully-trained
pipeline predict for the MOST RECENT weeks right now" — as opposed to
walk-forward validation/holdout, which only ever score against data already
in the dataset, held back from training/selection. Mirrors Module 1's
`forecast_future.py` in spirit but needs none of its recursive multi-step
machinery: every Stage 1 feature here is a lag of a prior week or that week's
own already-reported climate, never that week's own case count, so as long as
`weekly_modeling_table.csv` covers the target week, every feature is a real
observation.

Recomputes `feature_engineering.build_module2_feature_table()` fresh (not the
persisted `stage1_feature_table.csv`), attaches climate anomalies over the
FULL available history (`baseline_classifier.attach_fold_anomalies` with an
all-True mask — same construction `train_final_production_model` uses), takes
the most recent `n_recent_weeks` per district (default 8), and scores them
through the frozen Stage 1 + Stage 2 `final_production_model.*` files.
Stage 1 model type and Stage 2 architecture are read dynamically from
`baseline_classifier_metrics.csv`/`stage2_compensation_metrics.csv`'s
`selected` column (never hardcoded — survives future model-selection flips
like Decision 025's). Risk thresholds are re-derived from the persisted
`risk_threshold_scan.csv` via `risk_thresholds.select_thresholds` rather than
duplicated. Output: `data/processed/module2/live_risk_predictions.csv`
(adds `already_scored_in_pipeline`, flagging whether each row was already
part of an honest out-of-sample walk-forward fold/holdout, vs. genuinely new
since the last full pipeline run — the former must never be cited as
additional validation evidence, since the final-production models were
trained on it).

Surfaced a new finding while building/testing it: Module 2 shares Module 1's
Open Question #16 climate-currency gap (same upstream shared climate
pipeline) — **resolved for observed weeks 2026-07-29** via
`scripts/fetch_open_meteo_weather.py` + preprocessing rerun; see Decision 027.

## `src/module2_classification/forecast_future_risk.py` (new, standalone — Decision 027)

Scores **forward operational outbreak risk** beyond the last case-count week.
Uses frozen Stage 1 RF + Stage 2 isotonic + persisted thresholds (via
`scoring_utils.py`, same as `live_scoring.py`). For multi-week-ahead rows
(`horizon_step >= 2`), Module 1 `final_prediction` populates case-derived lag
features (`cases_source`, `uses_module1_cases` flagged). Output:
`data/processed/module2/future_risk_predictions.csv` with
`evidence_tier=operational`.

Prerequisites: refreshed climate (`fetch_open_meteo_weather.py` +
preprocessing), `forecast_future.py` output.

## Operational refresh + dashboard (Decision 027)

| Script | Role |
|---|---|
| `scripts/fetch_open_meteo_weather.py` | Archive gap-fill + Forecast API; tags daily `climate_data_source` |
| `scripts/refresh_dashboard_data.py` | Orchestrates weather → shared/M1/M2 preprocess → M1/M2 forward outputs |
| `src/dashboard/app.py` | Streamlit read-only dashboard |

## Independent of Module 1 for **training/evaluation** (Decision 019)

Module 2's Stage 1 does not consume Module 1's forecast output for **training or
holdout evaluation** — Decision 019/022 deferral stands. Module 1 forecasts ARE
used for **operational forward risk feature assembly only** (Decision 027,
`forecast_future_risk.py`).

Writes to `data/processed/module2/` and `data/features/module2/`.

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
4. ~~30 `(Year, Week)` labels (2008-2024) have a date stamp that is
   self-consistent across almost all districts (so it doesn't trigger the
   per-row disagreement check) but is chronologically inconsistent with
   neighbouring weeks.~~ **Resolved 2026-07-27.** The user manually corrected
   28 of the 30 against the original MoH source pages; the assistant found
   and fixed the remaining 2 (`2009 Wk24`, `2023 Wk40`) plus 3 further
   date-entry errors an expanded full-calendar day-count scan surfaced
   (`2010 Wk9`, `2011 Wk48`, `2013 Wk39`/`Wk40`) and the 2 outstanding
   per-row disagreements (`Ampara 2013 Wk51`, `Ampara 2023 Wk14`).
   `epi_week_calendar_chronology_issues.csv` and
   `epi_week_calendar_disagreements.csv` are now both empty after
   re-running the full pipeline; all 375 climate rows previously blocked by
   this issue are now populated. Two weeks (`2009 Wk17`, `2009 Wk22`) are
   kept as accepted irregular-length weeks (8 and 6 days respectively) — a
   genuine 1-day surplus/deficit in the source that can't be corrected by
   editing a single date without opening a new gap elsewhere. A separate,
   low-priority 3-day gap at the live edge of the dataset (`2025 Wk52` →
   `2026 Wk1`) remains open — see `DATA_DICTIONARY.md` Data Quality Notes
   for full detail on all of the above. Also fixed: `shared.py` previously
   only wrote the two diagnostic CSVs when non-empty, leaving stale files
   after a clean re-run — it now always rewrites them.
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
