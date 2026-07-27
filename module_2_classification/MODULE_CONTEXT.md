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
- Baseline classifier probability (Stage 2 input — added once Stage 1 exists)
- Probability residual lags (Stage 2 input — added once Stage 1 exists)

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
4. **Open, informed by an empirical audit before finalizing.** How should
   class imbalance be handled? Current plan: `class_weight="balanced"` /
   `scale_pos_weight` at the model level (Logistic Regression / Random Forest /
   XGBoost), **not SMOTE** — synthetic oversampling before/across a temporal
   walk-forward split risks fabricating points that blur the fold boundary and
   distort genuinely rare-event-in-time structure. `scripts/data_audit_module2.py`
   will quantify the actual imbalance per district across candidate `k` values
   before this is treated as final.
5. Should probability calibration be included? Planned for Stage 2
   (`compensation_model.py`) — isotonic/Platt recalibration as a baseline,
   benchmarked against an XGBoost-based probability-error compensation model.
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
3. **Label definition** (`src/module2_classification/label_definition.py`):
   fold-aware epidemic-threshold labeling — the historical mean/SD for any
   `(District, Week)` only ever uses strictly-prior years, never the full
   series (Decision 019's leakage guard, distinct from Module 1's
   feature-only anomaly guard).
4. **Feature engineering** (`src/module2_classification/feature_engineering.py`):
   case lags/rolling trend, seasonal/monsoon indicators, fold-aware climate
   anomalies (reusing Module 1's proven leakage-safe pattern).
5. **Stage 1** (`src/module2_classification/baseline_classifier.py`):
   Logistic Regression / Random Forest / XGBoost benchmark, pooled model with
   `District` as a categorical feature (validated empirically, not assumed),
   class-weighting for imbalance, PR-AUC/F1 as primary metrics.
6. **Stage 2** (`src/module2_classification/compensation_model.py`):
   probability/classification-error compensation using climate-anomaly and
   contextual features.
7. **Evaluation + orchestration** (`evaluate.py`, `main.py`), mirroring
   Module 1's idempotent `main.py` pattern.

## Documentation Rule

Update this file when Module 2 labels, models, features, or evaluation method changes.
