# Module 2 Context: Hybrid Outbreak Risk Classification

## Owner
Nethma L.H.K.

## Purpose
Classify dengue outbreak risk using a two-stage residual/error compensation approach.

---

## Current Architecture

```text
Stage 1: Baseline outbreak classifier
Stage 2: Probability / classification error compensation model
```

Exact models may change after benchmarking.

---

## Data Pipeline Note (2026-07-26, decisions finalized 2026-07-28 — Decision 020)

Module 2 consumes `data/processed/shared/` (Kalmunai merged into Ampara, master epi-week calendar, full 13-column climate aggregation, interpolated population) — the same base tables Module 1 uses. Module 2 does **not** automatically inherit Module 1's downstream choices (Decision 013): its own choices, reviewed and finalized 2026-07-28 (Decision 020), are:

- **Week 53 (2009, 2016, 2019, 2021) is kept as its own week, NOT merged into week 52** — the opposite of Module 1's Decision 007. Merging would sum two real weeks' case counts before the epidemic threshold is computed, risking a spurious label and contaminating week 52's cross-year `historical_mean`/`SD` for every year, not just the merged ones. Kept unmerged, week 53 will almost always have an undefined label (only 4 total occurrences, short of the 3-strictly-prior-years rule) — honest, not a defect.
- **Missing weeks are still seasonal-naive-imputed** (`is_imputed` flag, same method as Module 1's Decision 011) — required for `.shift()`-based lag feature alignment, not because Module 2's own model needs a gap-free series the way SARIMA does. `is_imputed` rows are masked to `NaN` consistently across every case-derived feature that could see them (`cases_lag_*`, rolling stats, `case_anomaly_lag_*`, and the label) — not just the label as originally implemented.
- **`weather_code` exclusion reconfirmed** (same reasoning as Module 1's Decision 008).

See `research_context/PIPELINE_ARCHITECTURE_PLAN.md` for the full layered pipeline design and `research_context/RESEARCH_DECISIONS.md` Decision 020 for the full review.

---

## Possible Stage 1 Models

- Random Forest
- XGBoost
- Logistic Regression baseline
- Gradient Boosting

**RESOLVED (2026-07-28, Decision 021).** All three of Random Forest, XGBoost,
and Logistic Regression were benchmarked; **XGBoost selected** as the
official Stage 1 model by median validation PR-AUC. See "Stage 1
Implementation Status" below.

---

## Possible Stage 2 Models

- XGBoost
- Random Forest
- Calibration model
- Residual/probability correction model

---

## Target Direction

The module predicts outbreak risk, not exact case count.

Possible outputs:

- Binary outbreak/non-outbreak label
- Multi-class risk level: low / medium / high
- Outbreak probability

---

## Current Feature Direction

**Finalized 2026-07-28** (dedicated feature-engineering review — see
`research_context/FEATURE_ENGINEERING_SPEC.md`'s Module 2 section for full
detail and `src/module2_classification/feature_engineering.py` for the
implementation):

- Case lags (1-4), rolling mean/std (4w), rate of change, and
  `momentum_vs_rolling_mean` (added after review to reduce zero-inflation
  noise in a bare rate-of-change). `is_imputed` rows are masked to `NaN`
  before any of these are derived (Decision 020, fixed a consistency gap
  found during the preprocessing review)
- Lagged climate: rainfall (2-8w), temperature (1-4w), humidity (1-4w) — new
  addition after review; the original feature direction only had anomalies,
  which miss dengue's ~2-8-week transmission delay
- Current-week raw climate (rainfall/temperature/humidity) — Module 2's own
  deliberate choice, unlike Module 1's Stage-1 climate-free rule (Decision 001
  is Module-1-scoped)
- Fold-aware climate anomalies (reused unchanged from Module 1)
- Seasonal week encoding (`sin_week`/`cos_week`), monsoon indicators
- Case-level seasonal anomaly lags (`case_anomaly_lag_1/2`) — new addition
  after review, conceptually similar to Module 1's `residual_lag`; safe to
  compute globally (see spec's leakage-guard architecture note)
- `District` (categorical, pooled-model support)
- **Now available (2026-07-28, Decision 021)**: baseline classifier
  probability — `data/processed/module2/baseline_classifier_predictions.csv`'s
  `predicted_probability` column (official model = XGBoost) — Stage 2's
  primary input once Stage 2 is built.
- Probability residual lags (Stage 2 input — still to be added once Stage 2 exists)

**Explicitly excluded from the model feature matrix** (leakage/metadata
guard found during this review, fixed before any Stage 1 code was written):
`Number_of_Cases`, `cases_per_100k` (both leak the label - see spec),
raw `Year`, and reporting/metadata columns. Stage 1/2 code must build its
feature matrix from `feature_engineering.FOLD_AGNOSTIC_FEATURE_COLUMNS`
(an explicit enumerated list), never from "all columns minus an exclude
list."

---

## Current Open Questions

1. **RESOLVED (2026-07-28, Decision 019).** How should outbreak labels be
   defined? Epidemic-threshold method:
   `outbreak = 1 if Number_of_Cases > historical_mean(District, Week) + k *
   historical_SD(District, Week)`, computed from strictly-prior years only
   (fold-aware, no leakage) — a WHO/CDC-style statistical threshold rather
   than an arbitrary fixed count.
2. **RESOLVED (2026-07-28, Decision 019).** Should labels be district-specific
   and week-specific? Yes — the threshold is computed per `(District, Week)`,
   directly addressing the known cross-district incidence heterogeneity
   (`DATA_DICTIONARY.md` zero-inflation findings).
3. **RESOLVED (2026-07-28, Decision 019).** Which threshold definition is most
   defensible? The epidemic-threshold (mean + k*SD) method over a single fixed
   count — see Decision 019's Reason section.
4. **RESOLVED (2026-07-28, Decision 021).** How should class imbalance be
   handled? Implemented and validated: `class_weight="balanced"` (Logistic
   Regression, Random Forest) / per-fold `scale_pos_weight` (XGBoost) — not
   SMOTE. See "Stage 1 Implementation Status" below for the full benchmark
   result.
5. **Elevated from "planned" to a load-bearing prerequisite (2026-07-28,
   Stage 1 calibration diagnostic).** Should probability calibration be
   included? Yes, necessarily — Stage 1's official model has a *negative*
   Brier skill score in 8/14 folds+holdout (worse-than-climatology
   calibration despite strong PR-AUC discrimination). Planned for Stage 2
   (`compensation_model.py`) — isotonic/Platt recalibration as a baseline,
   benchmarked against an XGBoost-based probability-error compensation
   model. See "Discrimination-vs-Calibration Diagnostic" below.
6. **Deferred, not abandoned (2026-07-28, Decision 019).** How will Module 1
   forecasts feed into Module 2? Module 2's Stage 1 is being built
   independently of Module 1 for now (own case-count/climate features only).
   Revisit as a candidate Stage 2 feature once Module 2's own baseline exists
   and can be evaluated with vs. without it.
7. **RESOLVED (2026-07-28).** What is the right value of `k`? `k=2`,
   confirmed via `scripts/data_audit_module2.py` against the real shared data
   (25,348 rows): no district produced a degenerate (outside [2%, 40%])
   outbreak rate at `k ∈ {1.5, 2.0, 2.5}`; pooled outbreak rate at `k=2` is
   18.4% (range 12.6%-25.2% across districts), and per-district ordering is
   nearly identical across all three candidates, so the choice is not highly
   sensitive. 15.7% of rows have an undefined label (< 3 strictly-prior years
   of history), concentrated in each district's earliest years — expected and
   excluded from training/scoring rather than defaulted. Full numbers:
   `outputs/metrics/module2/label_balance_audit.csv`.
8. **New (2026-07-28), flagged by the class-balance audit itself.** An
   18-25%-of-weeks outbreak rate is considerably higher than typical WHO/CDC
   epidemic-alert rates (often single-digit %) — the single-week
   `mean + k*SD` threshold likely flags much of each district's normal
   seasonal (monsoon) peak, not only genuinely anomalous spikes above that
   seasonal pattern. Candidate follow-ups, not yet implemented: (a) require
   the threshold to be exceeded for >= 2 consecutive weeks before labeling an
   outbreak (closer to how WHO epidemic alerts are operationalized), or (b)
   deseasonalize/detrend before computing the anomaly (analogous to how
   Module 1's climate anomalies already subtract a seasonal norm). `k=2` is
   accepted as Module 2's kickoff starting point, not a final validated label
   definition — this open question should be revisited once Stage 1 exists
   and can be evaluated with vs. without a consecutive-week refinement.
9. **RESOLVED (2026-07-28, Decision 020).** Module 2's own week-53/missing-week/
   `weather_code` policies (flagged as kickoff defaults, not fully deliberated,
   in the original Decision 019 implementation) were reviewed before Stage 1
   modeling began: week 53 is now kept unmerged (reverses the kickoff default —
   see Data Pipeline Note above), `is_imputed` masking was made consistent
   across all case-derived features (a real bug fix, not just a design
   choice), and `weather_code` exclusion was reconfirmed unchanged.

---

## Evaluation Metrics

- Accuracy
- Precision
- Recall / Sensitivity
- Specificity
- F1-score
- ROC-AUC
- PR-AUC
- Confusion matrix
- Calibration plots

---

## Implementation Plan (2026-07-28, kickoff)

Full technical detail lives in `research_context/PIPELINE_ARCHITECTURE_PLAN.md`
("Module 2 Layer" section). Summary, mirroring Module 1's sequencing:

1. **Empirical class-balance audit** (`scripts/data_audit_module2.py`):
   compute the epidemic-threshold label distribution per district across
   candidate `k` values before locking in `k=2`.
2. **Module 2 preprocessing** (`src/preprocessing/module2_preprocessing.py`):
   reads `data/processed/shared/*.csv`, applies Module 2's own (independently
   decided, per Decision 013) missing-week/`weather_code`/week-53 policies,
   writes `data/processed/module2/weekly_modeling_table.csv`.
3. **Label definition** (`src/module2_classification/labels.py` — note: the
   actual filename is `labels.py`, not `label_definition.py` as earlier
   drafts of this plan named it):
   fold-aware epidemic-threshold labeling — the historical mean/SD for any
   `(District, Week)` only ever uses strictly-prior years, never the full
   series (Decision 019's leakage guard, distinct from Module 1's
   feature-only anomaly guard).
4. **Feature engineering** (`src/module2_classification/feature_engineering.py`):
   case lags/rolling trend, seasonal/monsoon indicators, fold-aware climate
   anomalies (reusing Module 1's proven leakage-safe pattern).
5. **COMPLETE (2026-07-28, Decision 021)** — **Stage 1**
   (`src/module2_classification/baseline_classifier.py`):
   Logistic Regression / Random Forest / XGBoost benchmark, pooled model with
   `District` as a categorical feature (validated empirically, not assumed),
   class-weighting for imbalance, PR-AUC as the primary metric. See "Stage 1
   Implementation Status" below for full results.
6. **Stage 2** (`src/module2_classification/compensation_model.py`):
   probability/classification-error compensation using climate-anomaly and
   contextual features. Not yet started.
7. **Evaluation + orchestration** (`evaluate.py`, `main.py`) — **evaluate.py
   and main.py's Stage 1 wiring are COMPLETE**; `main.py` mirrors Module 1's
   idempotent `PIPELINE_STAGES` pattern exactly. Stage 2's wiring remains.

---

## Stage 1 Implementation Status (2026-07-28, Decision 021)

Implemented and run end to end: `src/module2_classification/evaluate.py`,
`src/module2_classification/baseline_classifier.py`,
`src/module2_classification/main.py`. Full narrative in
`module_2_classification/EXPERIMENT_LOG.md` entry M2-001; full decision
record in `research_context/RESEARCH_DECISIONS.md` Decision 021.

**Fold design**: `MODULE2_MIN_TRAIN_YEARS = 4` (new, Module-2-specific;
Module 1's `DEFAULT_MIN_TRAIN_YEARS = 3` left fold 1 with zero trainable
rows for every district) → **13 walk-forward folds** (vs. Module 1's 14),
plus the same `DEFAULT_HOLDOUT_YEARS = 2` final holdout block.

**Pooled vs. per-district (XGBoost arbiter)**: pooled median PR-AUC across
13 folds = **0.500**, per-district median PR-AUC = **0.287** (mean 0.433) —
pooled clearly wins, confirming the architecture choice empirically rather
than by analogy with Module 1 Stage 2. Full table:
`outputs/metrics/module2/pooled_vs_per_district_comparison.csv`.

**3-model benchmark** (median PR-AUC / ROC-AUC / F1 across 13 validation
folds, fixed 0.5 cutoff for F1):

| Model | PR-AUC | ROC-AUC | F1 | Brier |
|---|---|---|---|---|
| Logistic Regression | 0.437 | 0.799 | 0.397 | 0.141 |
| Random Forest | 0.462 | 0.815 | 0.454 | 0.133 |
| **XGBoost (selected)** | **0.500** | 0.816 | 0.437 | 0.117 |

**Held-out final block** (never touched during fold-based selection):
XGBoost PR-AUC = 0.538, ROC-AUC = 0.898, F1 = 0.491 (prevalence 7.2%,
lower than the validation folds' 14.4% pooled prevalence — later years
skew toward fewer high-relative-threshold outbreak weeks in the label's
own construction).

**Top feature importance** (official XGBoost model, gain): `case_anomaly_lag_1`
(312.9) ≫ `case_anomaly_lag_2` (155.6) > `rolling_mean_cases_4w` (44.1) >
`monsoon_indicator_SW` (35.3) > `cos_week` (31.5) > `District` (30.7). The
dominance of `case_anomaly_lag_1` is expected, not a leakage red flag — it
is conceptually near-identical to the label one week prior (documented in
`FEATURE_ENGINEERING_SPEC.md`'s Group M2-5 leakage note).

**Artifacts**: `data/processed/module2/baseline_classifier_predictions.csv`
(58,500 rows), `outputs/metrics/module2/baseline_classifier_metrics.csv`,
`outputs/metrics/module2/pooled_vs_per_district_comparison.csv`,
`outputs/metrics/module2/baseline_classifier_feature_importance.csv`,
`models/module2/baseline_classifier/{fold_1..13,holdout,
final_production_model}.json`.

**Not yet addressed** (flagged, not silently skipped): Open Question #5
(probability calibration) and #8 (single-week vs. consecutive-week outbreak
trigger) both remain open — Stage 1 was built against the label and
threshold-free probability output as-is; calibration is explicitly deferred
to Stage 2.

### Discrimination-vs-Calibration Diagnostic (2026-07-28)

"Success" for Stage 1 has two independent dimensions — **discrimination**
(can it rank outbreak-risk weeks correctly?) and **calibration** (are the
probability *values* themselves trustworthy?) — and they turned out to tell
different stories. Computed via `scripts/stage1_calibration_diagnostic.py`
(read-only, derives from the existing metrics CSV; full table:
`outputs/metrics/module2/baseline_classifier_calibration_diagnostic.csv`),
for the official XGBoost model:

- **Discrimination — strong.** PR-AUC beats the correct no-skill reference
  (`prevalence` itself, not 0) in **every one of the 13 validation folds
  and the holdout**, median uplift **3.65x** (range 1.2x–13.2x). A naive
  accuracy reading would be misleading, though: accuracy is actually
  *below* a majority-class ("always predict no outbreak") baseline in
  **8/13 validation folds** — expected, and exactly why PR-AUC (not
  accuracy) is the primary metric (Decision 021), but worth flagging
  explicitly against a casual reading of the metrics CSV.
- **Calibration — poor, by design, not yet fixed.** Brier skill score
  (skill relative to always predicting the fold's own base rate) is
  **negative in 8 of 14 folds+holdout** (median **-0.11**, as low as
  -0.93). The model's raw predicted probabilities are, in most folds, LESS
  accurate than a trivial base-rate forecast — despite strong PR-AUC in
  those same folds. This is a known effect of `scale_pos_weight`-based
  imbalance correction (improves ranking under a reweighted loss, distorts
  the output probability scale) and is the concrete evidence that Stage
  2's planned probability recalibration (Open Question #5) is a load-bearing
  prerequisite, not optional polish, before `predicted_probability` can be
  treated as a real risk estimate.
- **Independent sanity check on the label itself**: the two most
  extreme-prevalence folds map onto real, verifiable epidemiological
  events — fold 7 (prevalence 78.9%) covers **2016–2017**, Sri Lanka's
  worst recorded dengue epidemic year; fold 11 (prevalence 2.5%) covers
  **2020–2021**, plausibly consistent with COVID-era mobility suppression.
  Not label-construction noise.

Full narrative: `module_2_classification/EXPERIMENT_LOG.md` M2-001 addendum.

## Documentation Rule

Update this file when Module 2 labels, models, features, or evaluation method changes.
