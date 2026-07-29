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

**RESOLVED (2026-07-28, Decision 022 — implemented; results updated 2026-07-28 by
Decision 023/M2-003 after Stage 1 retuning).**
Three numerically well-posed architectures are benchmarked, selected by median Brier
Skill Score:
- **Isotonic regression** (pooled, feature-free) on `predicted_probability` → `label` —
  **current official architecture** (M2-003, median BSS 0.166; superseded Platt after
  Stage 1's hyperparameters were retuned).
- **Platt scaling** (pooled, feature-free): logistic regression on
  `logit(predicted_probability)` — official architecture pre-tuning (M2-002, median BSS
  0.145), still the runner-up post-tuning.
- **Stacked XGBoost**: classifier on `[predicted_probability, contextual features,
  District, probability_residual_lag_1/2]` → `label` — this is the resolved form of
  "Residual/probability correction model" below; a literal `label -
  predicted_probability` regression target was considered and rejected as ill-posed for
  a binary outcome (see Decision 022's Reason). Consistently underperforms both
  recalibration methods (M2-002, M2-003).
- Deferred (not rejected): an XGBoost variant with `base_margin =
  logit(predicted_probability)`, flagged as a future ablation.

---

## Target Direction

The module predicts outbreak risk, not exact case count.

**FULLY RESOLVED (2026-07-28, Decision 022 design + Decision 024 thresholds/M2-004).**
Calibrated `predicted_probability` (`calibrated_probability` column, isotonic-corrected
per M2-003) is the primary Stage 2 output. A binary `alert_flag` (threshold **0.170**,
F2-optimal) and a 3-level `risk_tier` (`low`/`medium`/`high`, high boundary **0.570**,
F0.5-optimal) — both **fixed absolute probability thresholds, not quantile cutoffs** —
are derived, first-class outputs in `data/processed/module2/stage2_risk_tier_predictions.csv`.
Empirical validation confirms real risk separation: observed outbreak rate is 2.6% (low)
→ 22.0% (medium) → 76.7% (high) on the untouched holdout block. See "Stage 2
Implementation Status" below and `EXPERIMENT_LOG.md` M2-004 for full results.

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
- Probability residual lags (Stage 2 stacked-XGBoost input, built fold-scoped in
  `compensation_model.py` — implemented, Decision 022/M2-002)

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
4. **RESOLVED (2026-07-28, Decision 021; RECONFIRMED 2026-07-28, Decision
   026/M2-006).** How should class imbalance be handled? Implemented and
   validated: `class_weight="balanced"` (Logistic Regression, Random Forest)
   / per-fold `scale_pos_weight` (XGBoost) — not SMOTE. See "Stage 1
   Implementation Status" below for the full benchmark result.
   **Re-audited 2026-07-28** (`scripts/audit_smote_imbalance.py`) after a
   literature review suggested SMOTE-family oversampling as a likely
   accuracy lever: leakage-safe SMOTENC (fit only on each fold's own
   training rows) was benchmarked against the current approach across 4
   variants x 2 models (Random Forest, XGBoost), on the SAME 13 folds +
   holdout as production. **Result: rejected.** The best SMOTENC variant for
   the official model (Random Forest) shows a small validation-median PR-AUC
   gain (+0.0096) that evaporates on holdout (effectively a wash) and costs
   holdout recall; every SMOTENC variant improved XGBoost's validation PR-AUC
   but WORSENED its holdout PR-AUC — a validation-improves/holdout-regresses
   pattern the pre-registered holdout check exists to catch. A consistent
   secondary finding (better raw Brier/calibration under SMOTENC) is judged
   likely redundant with Stage 2's existing isotonic recalibration, not
   pursued further. Full results: `outputs/metrics/module2/
   smote_imbalance_audit.csv`; narrative: `EXPERIMENT_LOG.md` M2-006;
   decision record: `RESEARCH_DECISIONS.md` Decision 026. No production code
   changed.
5. **RESOLVED (2026-07-28, Decision 022 + M2-002; numbers updated 2026-07-28
   by Decision 023/M2-003).** Should probability calibration be included?
   Yes — and it worked. Stage 2 (`compensation_model.py`) benchmarked
   isotonic regression, Platt scaling (on `logit(predicted_probability)`),
   and a stacked XGBoost model, selected by median Brier Skill Score across
   12 trainable walk-forward folds. **Platt scaling won initially** (M2-002,
   pre-Stage-1-retuning); after Stage 1's XGBoost hyperparameters were tuned
   (Decision 023), **isotonic regression became the new winner** on rerun
   (median BSS **0.166** vs. Platt's 0.145; holdout BSS 0.320 vs. 0.304) — a
   genuine architecture flip driven purely by Stage 1's changed probability
   distribution, not a Stage-2 code change. See "Stage 2 Implementation
   Status" below and `EXPERIMENT_LOG.md` M2-002 (superseded) / M2-003
   (current) for full results.
5b. **RESOLVED (2026-07-28, Decision 023).** Can Stage 1's discrimination be
   improved by hyperparameter tuning alone? Yes, modestly: Optuna search
   (60 trials, holdout-gated adoption) improved holdout PR-AUC **0.538 →
   0.558** (+0.0198) and ROC-AUC **0.898 → 0.911**. Adopted as the new
   `XGB_BASE_PARAMS`. See `EXPERIMENT_LOG.md` M2-003.
5c. **RESOLVED (2026-07-28, Decision 024).** What alert threshold and
   risk-tier boundaries should Stage 2's calibrated probability use?
   F2-optimal alert threshold = **0.170**, F0.5-optimal high-confidence
   boundary = **0.570** — nearly doubles holdout recall (39.9% → 68.6%) vs.
   the naive 0.5 cutoff, with strong empirical tier separation (2.6% / 22.0%
   / 76.7% observed outbreak rate for low/medium/high on holdout). See
   `EXPERIMENT_LOG.md` M2-004.
6. **Deferred again, with a concrete follow-up plan (2026-07-28, Decision
   022).** How will Module 1 forecasts feed into Module 2? Still deferred —
   Module 1 (14 folds, `MIN_TRAIN_YEARS=3`) and Module 2 Stage 1 (13 folds,
   `MIN_TRAIN_YEARS=4`) have misaligned fold boundaries, so merging Module
   1's `final_prediction` in as a Stage 2 feature requires a dedicated
   fold-alignment leakage audit, not a simple merge, and would create a live
   cross-module dependency. Planned as an **optional ablation** after Stage
   2's own-feature-set version is built and evaluated, not abandoned.
7. **SUPERSEDED (2026-07-28, Decision 025/M2-005).** What is the right value
   of `k`? Originally `k=2` (confirmed via `scripts/data_audit_module2.py`
   against the exact-per-week estimator: pooled outbreak rate 18.4%, range
   12.6%-25.2% across districts, no degenerate district). **Re-audited and
   changed to `k=3.0`** once the estimator itself changed (Decision 025) —
   see Open Question #8 below. `k=2.0`'s value is specific to the OLD
   exact-per-week estimator and is no longer the production value.
8. **RESOLVED (2026-07-28, Decision 025/M2-005).** The class-balance audit
   flagged an 18-25%-of-weeks outbreak rate as considerably higher than
   typical WHO/CDC epidemic-alert rates (often single-digit %) — the
   single-week `mean + k*SD` threshold was flagging much of each district's
   normal seasonal (monsoon) peak, not only genuinely anomalous spikes.
   **Audited 6 candidate `historical_mean`/`historical_sd` estimators**
   (`scripts/audit_label_stabilization.py`): the exact-week control, a
   circular week-window pooling variant (window=1/2/3), and a per-district
   harmonic-regression variant (1/2 harmonics) — each x 3 `k` values.
   **Adopted harmonic regression (`n_harmonics=1`) with `k=3.0`**: pooled
   outbreak rate 18.4% → **8.6%**, undefined-label rate improved too (16.0%
   → 10.7%) — a genuine win on both axes, not a trade-off. Window-pooling
   was tested and **rejected**: it increases the SD estimate in
   high-variance districts, raising thresholds rather than stabilizing them.
   **Important correction surfaced during this work**: the task's original
   motivating example (Colombo 2025 Wk15, 277 cases) was verified to
   already be correctly labeled `1` (outbreak) under the OLD estimator — the
   real issue there was a Stage 2 calibration near-miss (calibrated
   probability 0.155 vs. the then-alert-threshold 0.170), not a label
   defect. **Honest limitation, not hidden**: the chosen `k=3.0` actually
   flips that specific row's label to `0`, since harmonic regression's
   residual SD for high-variance Colombo (209.0) is much larger than the
   old estimator's (87.7) — an expected consequence of one global `k` fixing
   an aggregate-prevalence problem, not a full resolution for every
   individual district. A district-specific/variance-adaptive `k` is flagged
   as a candidate future refinement, not implemented this round. Full
   evidence: `outputs/metrics/module2/{label_stabilization_audit,
   label_stabilization_spot_check}.csv`; full narrative:
   `EXPERIMENT_LOG.md` M2-005; decision record: `RESEARCH_DECISIONS.md`
   Decision 025.
9. **RESOLVED (2026-07-28, Decision 020).** Module 2's own week-53/missing-week/
   `weather_code` policies (flagged as kickoff defaults, not fully deliberated,
   in the original Decision 019 implementation) were reviewed before Stage 1
   modeling began: week 53 is now kept unmerged (reverses the kickoff default —
   see Data Pipeline Note above), `is_imputed` masking was made consistent
   across all case-derived features (a real bug fix, not just a design
   choice), and `weather_code` exclusion was reconfirmed unchanged.
10. **Partially resolved (2026-07-29, Decision 027).** Climate-currency gap for
    **observed** weeks closed via `scripts/fetch_open_meteo_weather.py` +
    preprocessing rerun — live scoring `feature_completeness_pct` back to 100%
    on latest weeks. **Remaining limitation:** forward epi-weeks beyond the
    master calendar edge may lack forecast climate until calendar extension is
    added; daily forecast API horizon is ~16 days.

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
6. **COMPLETE (2026-07-28, Decision 022/024, M2-002/M2-003/M2-004)** — **Stage 2**
   (`src/module2_classification/compensation_model.py`): probability
   calibration (isotonic regression, official) + `src/module2_classification/
   risk_thresholds.py`: alert threshold/risk-tier assignment. See "Stage 2
   Implementation Status" above for full results.
7. **Evaluation + orchestration** (`evaluate.py`, `main.py`) — **COMPLETE**:
   `main.py`'s `PIPELINE_STAGES` runs `shared_preprocessing →
   module2_preprocessing → feature_engineering → stage1_baseline_classifier →
   stage2_compensation → stage2_risk_thresholds` end to end, idempotently,
   mirroring Module 1's pattern.

---

## Stage 1 Implementation Status (2026-07-28, Decision 021; hyperparameters tuned 2026-07-28, Decision 023/M2-003; label re-estimated 2026-07-28, Decision 025/M2-005 — model selection flipped to Random Forest)

Implemented and run end to end: `src/module2_classification/evaluate.py`,
`src/module2_classification/baseline_classifier.py`,
`src/module2_classification/main.py`. Full narrative in
`module_2_classification/EXPERIMENT_LOG.md` entries M2-001 (original,
superseded), M2-003 (post-tuning, superseded), and **M2-005 (current
production numbers, post-label-re-estimation)**; full decision records in
`research_context/RESEARCH_DECISIONS.md` Decisions 021, 023, and 025.

**Fold design**: `MODULE2_MIN_TRAIN_YEARS = 4` (new, Module-2-specific;
Module 1's `DEFAULT_MIN_TRAIN_YEARS = 3` left fold 1 with zero trainable
rows for every district) → **13 walk-forward folds** (vs. Module 1's 14),
plus the same `DEFAULT_HOLDOUT_YEARS = 2` final holdout block. Re-verified
unchanged after Decision 025's label re-estimation (fold 1: 2,573 pooled
trainable rows through fold 13: 18,073 rows — consistent with the original
fold-boundary verification).

**Hyperparameters unchanged since Decision 023** (`XGB_BASE_PARAMS`:
`max_depth=3, learning_rate=0.01237, n_estimators=217, subsample=0.6565,
colsample_bytree=0.5962, reg_lambda=1.0758, min_child_weight=10,
reg_alpha=4.1197, gamma=2.4930`) — Decision 025 changed the LABEL, not
XGBoost's tuning; not re-tuned this round (flagged as an optional
follow-up in Decision 025, not assumed unnecessary).

**Model selection FLIPPED to Random Forest (Decision 025/M2-005)** — a
consequence of the much lower, differently-shaped label prevalence under
the new estimator, not a code change to any model:

| Model | PR-AUC (median, 13 validation folds) |
|---|---|
| Logistic Regression | 0.358 |
| **Random Forest (selected)** | **0.377** |
| XGBoost (Decision 023's tuned params) | 0.373 |

**Pooled vs. per-district (XGBoost arbiter, reconfirmed under the new label)**:
pooled aggregate median PR-AUC = **0.373**, per-district median PR-AUC =
**0.343** (mean 0.421 — per-district's mean now exceeds pooled's for the
first time, though pooled still wins the pre-registered median comparison).
Full table: `outputs/metrics/module2/pooled_vs_per_district_comparison.csv`.

**Held-out final block** (2,600 rows; prevalence now only **1.5%**, ≈40
positive rows — down from M2-003's 7.2%/≈187 positives, since the new
label's undefined rows concentrate more heavily in early years and the
holdout block itself is 0% undefined): Random Forest PR-AUC = **0.429**,
ROC-AUC = **0.885**, Brier = 0.027, vs. XGBoost 0.424/0.896/0.032,
Logistic Regression 0.235/0.835/0.039. **Flagged limitation**: this ~5x
smaller holdout positive-class count means holdout metrics under the new
label carry noticeably more sampling variance than under the old label —
read accordingly.

**Top feature importance** (official Random Forest model, post-Decision-025):
`case_anomaly_lag_1` (0.352) and `case_anomaly_lag_2` (0.268) together
account for >60% of total importance, followed by `rolling_std_cases_4w`
(0.053), `cases_lag_1` (0.041), `rolling_mean_cases_4w` (0.037). Same
top-2 features as before the label change (expected, not a leakage red
flag — documented in `FEATURE_ENGINEERING_SPEC.md`'s Group M2-5 leakage
note); their relative dominance is now even larger than under the old
label.

**Artifacts**: `data/processed/module2/baseline_classifier_predictions.csv`,
`outputs/metrics/module2/baseline_classifier_metrics.csv`,
`outputs/metrics/module2/pooled_vs_per_district_comparison.csv`,
`outputs/metrics/module2/baseline_classifier_feature_importance.csv`,
`models/module2/baseline_classifier/{fold_1..13,holdout,
final_production_model}.joblib` (Random Forest, per Decision 025 - the `.json`
files of the same names still on disk are stale leftovers from the
pre-Decision-025 XGBoost-official run and are ignored by anything reading
`baseline_classifier_metrics.csv`'s `selected` column, e.g. `live_scoring.py`).
Tuning-specific artifacts (historical, not rerun this round):
`scripts/tune_stage1_xgboost.py`, `outputs/metrics/module2/
{xgboost_tuning_trials,xgboost_tuning_holdout_comparison}.csv`.

**Resolved since original write-up**: Open Question #5 (probability
calibration — Stage 2), #5b (hyperparameter tuning — Decision 023), and #8
(label estimator noise — Decision 025) are now all resolved.

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

---

## Stage 2 Implementation Status (2026-07-28, Decision 022 + M2-002; superseded numerically 2026-07-28 by Decision 023/M2-003; risk thresholds added by Decision 024/M2-004; label re-estimated 2026-07-28 by Decision 025/M2-005 — current production numbers below)

Full design record in `research_context/RESEARCH_DECISIONS.md` Decision 022;
original results in `module_2_classification/EXPERIMENT_LOG.md` M2-002
(superseded), M2-003 (superseded); **current production numbers in M2-005**
(post-label-re-estimation rerun).

- **Three architectures benchmarked**: isotonic regression, Platt scaling on
  `logit(predicted_probability)`, stacked XGBoost on `[predicted_probability,
  contextual features, District, probability_residual_lag_1/2]` → `label` —
  a literal `label - predicted_probability` residual regression was
  considered and rejected as statistically ill-posed for a binary target.
- **No-leakage rule** (Decision-010-style): Stage 2 fold *k* (`k = 2..13`)
  trains only on the official Stage 1 model's out-of-sample
  `predicted_probability`/`label` from folds `1..k-1`. Fold 1 is a
  documented no-op passthrough (verified: `calibrated_probability ==
  predicted_probability` exactly for all 1,300 fold-1 rows). 12 trainable
  folds (vs. Stage 1's 13).
- **Isotonic regression remains the official architecture** (median Brier
  Skill Score across 12 trainable folds): **isotonic 0.2146** vs. Platt
  0.2116 vs. stacked XGBoost -0.108 vs. Stage 1 raw -0.584 — both isotonic
  and Platt markedly improved vs. the pre-Decision-025 values (0.166/0.145),
  and the race between them is now much tighter. Holdout BSS: **Platt
  (0.2344) very slightly edges isotonic (0.2315)**, but isotonic remains
  selected per the pre-registered validation-fold selection rule (holdout is
  a check, not a tiebreaker).
- **Isotonic mildly regresses PR-AUC vs. Stage 1 raw** (0.3904 vs. 0.4095
  holdout, 0.390 vs. 0.393 validation median) — flagged automatically by the
  existing PR-AUC-regression check (Decision 022), not blocked: BSS remains
  the primary selection metric and the regression is modest.
- **Stacked XGBoost underperformed again** (median BSS = -0.108, still
  negative) — its own per-fold `scale_pos_weight` likely reintroduces a
  similar probability-scale distortion to Stage 1's. A consistent negative
  result across M2-002, M2-003, and M2-005.
- **Pooled vs. per-district re-validated empirically** (stacked-XGBoost
  arbiter, post-Decision-025): pooled aggregate BSS **-0.108** vs.
  per-district median **-0.463** (mean -0.720) — pooled wins decisively,
  consistent with every other pooled-vs-per-district check in this project.
- **Reliability diagrams** confirm Stage 1 is systematically *overconfident*
  (predicts higher outbreak risk than observed across most of the
  probability range, not underconfident) and isotonic regression pulls the
  curve close to the diagonal in both validation and holdout splits.
- **Output format fully resolved (Decision 024/M2-004)**: calibrated
  probability primary; `alert_flag`/`risk_tier` derived outputs — thresholds
  recalibrated under the new label, see the "Risk Thresholds" subsection
  below.
- **Module 1 integration** remains deferred as an optional post-Stage-2
  ablation (fold-boundary misalignment between the two modules).

### Risk Thresholds (2026-07-28, Decision 024/M2-004; recalibrated 2026-07-28, Decision 025/M2-005)

Completes the deferred item from Decision 022. `src/module2_classification/risk_thresholds.py`
is a permanent pipeline stage (`stage2_risk_thresholds` in `main.py`), selecting thresholds
purely from the official architecture's validation-fold rows (folds 2-13), holdout untouched
until the final check. **Recalibrated under Decision 025's new label** (lower thresholds,
tracking the new, lower overall prevalence — not directly comparable to M2-004's original
values below, which measured a different, since-superseded label):

- **Alert threshold = 0.140** (was 0.170 pre-Decision-025; argmax F2, recall-weighted —
  early-warning framing: missing a real outbreak costs more than a false alarm).
- **High-confidence tier boundary = 0.350** (was 0.570 pre-Decision-025; argmax F0.5,
  precision-weighted).
- **Holdout evidence** (post-Decision-025, 2,600 rows, prevalence now only 1.5%): naive 0.5
  cutoff gives recall 45.0%/F2 0.459/accuracy 98.5% (high accuracy reflects the much lower
  prevalence, not improved skill); the new F2-optimal 0.140 threshold gives recall
  **60.0%**/F2 **0.519**/accuracy 97.6%. **Not directly comparable** to the pre-Decision-025
  figures immediately below — a different, less noisy label target.
- **Tier separation remains strong and monotonic on both splits** — observed outbreak rate:

  | Split | Low | Medium | High |
  |---|---|---|---|
  | Validation (folds 2-13) | 1.3% | 26.2% | 71.1% |
  | Holdout | 0.6% | 13.3% | 48.8% |

- **Artifacts**: `data/processed/module2/stage2_risk_tier_predictions.csv` (adds
  `alert_flag`/`risk_tier` to every row of `stage2_compensated_predictions.csv`),
  `outputs/metrics/module2/{risk_threshold_scan,risk_threshold_holdout_comparison}.csv`.

**Historical (pre-Decision-025) values, superseded, kept for reference**: alert threshold
0.170, high-confidence boundary 0.570; holdout recall improved 39.9% → 68.6% (F2 0.437 →
0.574) switching from naive 0.5; tier separation 3.2%/27.3%/83.2% (validation) and
2.6%/22.0%/76.7% (holdout). See `EXPERIMENT_LOG.md` M2-004 for the full original write-up.

## Live/Production Risk Scoring (2026-07-28, new)

`src/module2_classification/live_scoring.py` (new) closes the gap between the
evaluation pipeline above (which only ever scores against data already inside
the dataset - walk-forward folds, the holdout block) and actual dashboard use:
"what risk tier does the fully-trained pipeline assign to the MOST RECENT
weeks right now." Standalone, NOT wired into `main.py`'s idempotent
`PIPELINE_STAGES` - same precedent as Module 1's `forecast_future.py`.

### Why no SARIMA-style recursive extrapolation is needed here

Every Stage 1 feature is either a lag of a PRIOR week's case count/climate or
that week's OWN already-reported climate - never that week's own case count
(Decision 019's leakage guard). As long as `weekly_modeling_table.csv` already
has real data through the target week, every feature is a real observation,
never a recursively-fed prior prediction - no horizon-decay story the way
Module 1's forward forecast has one.

### Method
1. Recompute Stage 1's feature table fresh from the CURRENT
   `weekly_modeling_table.csv` (not the possibly-stale persisted feature CSV).
2. Attach climate anomalies using the FULL available history as the training
   window - the same maximal-data construction
   `baseline_classifier.train_final_production_model` already uses.
3. Score the most recent `n_recent_weeks` (default 8) per district through
   the FROZEN Stage 1 + Stage 2 final-production models - model/architecture
   type read dynamically from `baseline_classifier_metrics.csv`/
   `stage2_compensation_metrics.csv`'s `selected` column, never hardcoded.
4. Apply the same alert/high-confidence thresholds `risk_thresholds.py`
   already selected, re-derived from the persisted `risk_threshold_scan.csv`.

### Honest limitations (flagged, not hidden)
- The final-production models are trained on ALL available data (including
  whatever portion of the scored weeks already fell inside the holdout/
  walk-forward folds) - correct for a live checkpoint, but means this
  script's numbers must NEVER be quoted as additional validation/holdout
  evidence; `EXPERIMENT_LOG.md`/`RESEARCH_DECISIONS.md`'s existing figures
  remain the only honest skill estimates. Each row is flagged
  `already_scored_in_pipeline`.
- **Climate refresh (2026-07-29, Decision 027):** observed-week gap closed;
  forward-week climate beyond master calendar / ~16-day Forecast API window
  remains a documented operational limitation — see Open Question #10 above.
- Live scoring for the `stacked_xgboost` Stage 2 architecture is not
  implemented (raises `NotImplementedError`) - isotonic/Platt are the only
  architectures that have ever won Stage 2 selection, so this was not built
  speculatively.

### First real-world spot check (2026-07-28, current data through 2026 Wk25)
Scoring the last 8 weeks x 25 districts (200 rows, 0 genuinely new since the
last full pipeline run - 2026 Wk25 already sits inside the holdout block)
correctly flags **9 districts `high` and 6 `medium` at Wk25**, including
`Colombo` (calibrated 0.500) and `Gampaha` (calibrated 0.567) - the two
districts already independently confirmed as a real, ongoing 2026 outbreak in
`module_1_forecasting/MODULE_CONTEXT.md` Open Question #16 - plus `Galle`,
`Hambantota`, `Kurunegala`, `Matara`, `Monaragala`, `Nuwara Eliya`, and
`Ratnapura`. Not a substitute for the honest holdout PR-AUC/recall figures
above (see limitations), but a reassuring qualitative sanity check that the
live-scoring path reproduces a real, known outbreak signal.

**Output**: `data/processed/module2/live_risk_predictions.csv`.

## Forward Operational Risk (2026-07-29, Decision 027)

`src/module2_classification/forecast_future_risk.py` scores horizon 0 (latest
observed week) plus 8 forward epi-weeks per district. Multi-week-ahead rows
(`horizon_step >= 2`) use Module 1 `final_prediction` for case-derived lag features
(`uses_module1_cases=True`; `cases_source=module1_forecast`). Horizon 1 uses real
historical lags only (`cases_source=na`). Forward epi-weeks beyond
`climate_weekly.csv` aggregate daily Open-Meteo rows (observed/forecast/mixed
`climate_source`). Output: `future_risk_predictions.csv` with
`evidence_tier=operational`. Shared helpers in `scoring_utils.py`.

Module 1 `future_forecast.csv` is now an **operational input** to Module 2 forward
risk (Decision 027) — not used in training/evaluation pipelines (Decision 019/022
deferral unchanged).

## Documentation Rule

Update this file when Module 2 labels, models, features, or evaluation method changes.
