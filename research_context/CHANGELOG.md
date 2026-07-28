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

## 2026-07-28 - Module 2 Live/Production Risk Scoring Added; New Climate-Currency-Gap Finding

### Module
Module 2

### Change
Added `src/module2_classification/live_scoring.py` (new, standalone - not
wired into `main.py`'s idempotent `PIPELINE_STAGES`, same precedent as Module
1's `forecast_future.py`). Recomputes Stage 1's feature table fresh from the
current `weekly_modeling_table.csv`, attaches full-history climate anomalies,
scores the most recent N weeks per district (default 8) through the frozen
Stage 1 + Stage 2 final-production models (model/architecture type read
dynamically from each stage's metrics CSV `selected` column, never
hardcoded), and applies the persisted alert/high-confidence risk thresholds.
Outputs `data/processed/module2/live_risk_predictions.csv`.

While building/testing this script, discovered that Module 2 shares Module
1's Open Question #16 climate-currency gap: `weekly_modeling_table.csv`'s
case counts extend through 2026 Wk25 but every climate column stops 4 weeks
earlier (2026 Wk21) for all 25 districts, since both modules consume the same
shared climate pipeline. `feature_completeness_pct` drops from 100% to 60%
over the most recent 4 scored weeks as a result.

### Reason
Module 2's training/evaluation pipeline (Stage 1 -> Stage 2 -> risk
thresholds) only ever scores against data already inside the dataset
(walk-forward folds, the 2-year holdout). There was no way to produce a risk
classification for the dashboard's actual use case - "what does the model say
about the most recent real weeks, right now" - without manually rerunning the
entire walk-forward benchmark. Unlike Module 1, no SARIMA-style recursive
multi-step extrapolation is needed: every Stage 1 feature is a lag of a prior
week or that week's own already-reported climate, never that week's own case
count, so as long as the raw data already covers the target week, every
feature is a real observation.

### Impact
New: `src/module2_classification/live_scoring.py`,
`data/processed/module2/live_risk_predictions.csv`. Config: added
`MODULE2_LIVE_RISK_PREDICTIONS_PATH` to `src/config.py`. Documentation:
`module_2_classification/MODULE_CONTEXT.md` new "Live/Production Risk
Scoring" section and new Open Question #10 (climate-currency gap). No
production training/evaluation code changed.

### Status
Accepted. First real-world spot check (current data through 2026 Wk25)
correctly flags 9 districts `high` and 6 `medium`, including `Colombo` and
`Gampaha` - the same two districts already independently confirmed as a real,
ongoing 2026 outbreak in `module_1_forecasting/MODULE_CONTEXT.md`. The
climate-currency-gap finding remains open (shared fix with Module 1's Open
Question #16: rerun the shared climate preprocessing/Open-Meteo fetch).

---

## 2026-07-28 - Module 2 SMOTENC Oversampling Audited and Rejected; Decision 021 Reconfirmed (Decision 026, M2-006)

### Module
Module 2

### Change
Added `scripts/audit_smote_imbalance.py` (read-only diagnostic, added
`imbalanced-learn` to `requirements.txt`) and used it to benchmark leakage-safe
SMOTENC oversampling (fit strictly on each fold's own training rows, `District`
as a `categorical_features` column) against the current
`class_weight`/`scale_pos_weight`-only approach, across 4 variants x 2 models
(Random Forest, XGBoost), on the identical 13 walk-forward folds + holdout
used by production `baseline_classifier.py`.

### Reason
A user request to research accuracy-improvement techniques beyond this repo
surfaced SMOTE-family oversampling as a commonly cited lever for imbalanced
outbreak classification in the literature. Decision 021 had already rejected
SMOTE, but on a reasoning ("blurs the temporal fold boundary") that doesn't
precisely describe the real risk of oversampling this pipeline's lagged
features - the reasoning needed correcting, so the underlying conclusion was
re-tested empirically rather than assumed to still hold, per this project's
"critique assumptions, don't just agree" rule.

### Impact
No production code changed - `baseline_classifier.py` and all its outputs are
unchanged. Result: **rejected**. For Random Forest (official model), the best
SMOTENC variant shows a small validation-median PR-AUC gain (+0.0096) that
evaporates on holdout (effectively a wash) and costs holdout recall. Every
SMOTENC variant improved XGBoost's validation PR-AUC but worsened its holdout
PR-AUC - a validation-improves/holdout-regresses pattern the pre-registered
holdout check exists to catch. A consistent secondary finding (better raw
Brier/calibration under SMOTENC) is judged likely redundant with Stage 2's
existing isotonic recalibration. `research_context/RESEARCH_DECISIONS.md`
(new Decision 026), `module_2_classification/EXPERIMENT_LOG.md` (new entry
M2-006), `module_2_classification/MODULE_CONTEXT.md` (Open Question #4
addendum), `requirements.txt` (added `imbalanced-learn`). New artifacts:
`scripts/audit_smote_imbalance.py`, `outputs/metrics/module2/
smote_imbalance_audit.csv`.

### Status
Rejected

---

## 2026-07-28 - Module 2 Label Mean/SD Estimator Replaced With Harmonic Regression; k Re-Audited to 3.0 (Decision 025, M2-005)

### Module
Module 2

### Change
Added `scripts/audit_label_stabilization.py` (read-only diagnostic, mirrors
`scripts/data_audit_module2.py`'s original k-audit) and used it to compare 6
candidate `historical_mean`/`historical_sd` estimators for Decision 019's
outbreak-threshold label formula (`exact_week` control, `windowed` at
window=1/2/3, `harmonic` at 1/2 harmonics) x 3 `k` values each, plus an
explicit spot-check of Colombo District/2025/Week 15. **Adopted harmonic
regression (`compute_historical_stats_harmonic`, `n_harmonics=1`) with
`k=3.0`** as the new official estimator in
`src/module2_classification/labels.py`, replacing Decision 019's exact-per-
(District, Week) sample mean/SD (kept in the codebase, not deleted, marked
superseded). `src/module2_classification/feature_engineering.py`'s
`compute_case_anomaly_lags` switched to match (Group M2-5 reuses the same
estimator as the label by design). `src/config.py`: `EPIDEMIC_THRESHOLD_K`
`2.0` -> `3.0`; new `EPIDEMIC_THRESHOLD_N_HARMONICS = 1`. Reran the full
Module 2 pipeline end to end (`feature_engineering` through
`stage2_risk_thresholds`, `--force`).

**Important correction to the motivating evidence, surfaced before
implementing anything**: the task's flagship example (Colombo 2025 Wk15,
277 cases, cited as a label defect) was verified directly against the
running pipeline and found to be **already correctly labeled `1`
(outbreak)** under the OLD estimator (`threshold=256.4 < 277`). The actual
issue was a Stage 2 calibration near-miss (isotonic-calibrated probability
0.155, just under the pre-existing 0.170 alert threshold) - not a label
problem. The real, addressed problem is the separately-documented 18-25%
pooled "outbreak" prevalence (well above WHO/CDC's single-digit-percent
norm), which this change reduces to 8.57% while also reducing the
undefined-label rate (16.0% -> 10.7%). **Window-pooling was tested and
rejected**: it increases the SD estimate in high-variance districts,
raising (not lowering) their threshold. **Honest limitation, not hidden**:
the chosen `k=3.0` raises Colombo's own threshold enough that its 2025
Wk15 row's label actually FLIPS from `1` to `0` under the new estimator -
an expected consequence of one global `k` fixing an aggregate-prevalence
problem, flagged as an open follow-up (district-specific/variance-adaptive
`k`), not silently presented as a clean win.

Full pipeline rerun surfaced further downstream consequences of the label
change: **Stage 1's official model selection flipped from XGBoost to
Random Forest** (median validation PR-AUC 0.3766 vs. 0.3726), Stage 2's
architecture contest tightened considerably (isotonic 0.2146 vs. Platt
0.2116 median BSS, both markedly improved vs. Stage 1 raw), and risk
thresholds recalibrated lower (alert 0.170 -> 0.140, high-confidence 0.570
-> 0.350) to track the new, lower prevalence.

### Reason
Open Question #8 (flagged at Decision 019's kickoff, never acted on until
now) argued the single-week `mean + k*SD` threshold was too noisy from
small per-week sample sizes. An audit-first approach (rather than assuming
a fix direction) was required per the user's explicit instruction, and
that audit's first useful output was disproving the specific motivating
example rather than confirming it - a finding that had to be surfaced
honestly before proceeding, per this project's "critique assumptions"
mandate, rather than silently implementing a fix for a problem that (in
that specific case) didn't exist.

### Impact
New file `scripts/audit_label_stabilization.py`. New outputs:
`outputs/metrics/module2/{label_stabilization_audit,
label_stabilization_spot_check}.csv`. Modified
`src/module2_classification/labels.py` (new
`compute_historical_stats_harmonic`/`_harmonic_design`; old
`compute_historical_stats` kept, marked superseded),
`src/module2_classification/feature_engineering.py` (estimator switched for
`case_anomaly_lag_1/2`), `src/config.py` (`EPIDEMIC_THRESHOLD_K` and new
`EPIDEMIC_THRESHOLD_N_HARMONICS`). Regenerated
`data/features/module2/stage1_feature_table.csv`,
`data/processed/module2/{baseline_classifier_predictions,
stage2_compensated_predictions, stage2_risk_tier_predictions}.csv`, all
Stage 1/2/threshold metrics and figures, and both stages' model artifacts.
Updated `research_context/RESEARCH_DECISIONS.md` (new Decision 025),
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-005; M2-001
through M2-004 explicitly marked as measured against the superseded
label), `module_2_classification/MODULE_CONTEXT.md` (Open Question #8
resolved; Stage 1/Stage 2 Implementation Status refreshed),
`research_context/FEATURE_ENGINEERING_SPEC.md` (Label Definition and Group
M2-5 updated), `research_context/PIPELINE_ARCHITECTURE_PLAN.md`
(`labels.py` entry and status banner updated).

### Status
Accepted. M2-001 through M2-004's numeric results are superseded by
M2-005 (a different label = a different, non-comparable target); their
qualitative findings (pooled beats per-district, isotonic/Platt beat
stacked XGBoost for Stage 2, F-beta thresholds beat a naive 0.5 cutoff)
remain valid. A district-specific/variance-adaptive `k` is flagged as an
open follow-up, not implemented this round.

---

## 2026-07-28 - Module 2 Stage 2 Risk Thresholds Implemented and Run (Decision 024, M2-004)

### Module
Module 2

### Change
Implemented `src/module2_classification/risk_thresholds.py` per Decision
024's design and ran it end to end. Added `fbeta_score()` and
`threshold_scan()` to `src/module2_classification/evaluate.py`; added risk-
threshold path constants to `src/config.py`; wired `stage2_risk_thresholds`
into `src/module2_classification/main.py`'s `PIPELINE_STAGES` as the final
stage. Completes Decision 022's deferred risk-tier item.

Selected an **F2-optimal alert threshold (0.170)** and an **F0.5-optimal
high-confidence tier boundary (0.570)**, chosen purely from the official
Stage 2 architecture's validation-fold rows (folds 2-13), holdout reserved
for the final check. On the untouched holdout block, switching from the
naive 0.5 cutoff to 0.170 nearly doubles recall (39.9% -> 68.6%) at the
expected precision cost, improving F2 from 0.437 to 0.574. Risk-tier
empirical separation is strong and monotonic on both splits: observed
outbreak rate 2.6% (low) -> 22.0% (medium) -> 76.7% (high) on holdout.

### Reason
The naive 0.5 cutoff used throughout Stage 1/2 benchmarking was always
documented as an untuned diagnostic, not a real decision threshold. An
early-warning system should weight recall over precision (F2) for its
primary alert, and precision over recall (F0.5) for a "high confidence"
label - one consistent F-beta framework at two operating points, avoiding
an arbitrary rule and staying consistent with Decision 022's earlier
rejection of quantile-based cutoffs.

### Impact
New file `src/module2_classification/risk_thresholds.py`. New outputs:
`data/processed/module2/stage2_risk_tier_predictions.csv`,
`outputs/metrics/module2/{risk_threshold_scan,
risk_threshold_holdout_comparison}.csv`. Updated
`module_2_classification/MODULE_CONTEXT.md` ("Target Direction" fully
resolved, new "Risk Thresholds" subsection), `module_2_classification/
EXPERIMENT_LOG.md` (new entry M2-004), `research_context/
RESEARCH_DECISIONS.md` (new Decision 024), `research_context/
PIPELINE_ARCHITECTURE_PLAN.md` (new `risk_thresholds.py` entry).

### Status
Accepted. Module 2's "Target Direction" ambiguity (calibrated probability
vs. risk tier vs. binary alert) is now fully resolved with concrete,
holdout-evaluated artifacts for all three.

---

## 2026-07-28 - Module 2 Stage 1 XGBoost Hyperparameters Tuned via Optuna, Adopted; Stage 2 Rerun (Decision 023, M2-003)

### Module
Module 2

### Change
Added a standalone `scripts/tune_stage1_xgboost.py` (Optuna TPE search, 60
trials, 13-fold median PR-AUC objective, holdout-gated adopt/reject
verdict) and an optional `xgb_params` override parameter to
`baseline_classifier.fit_and_predict`. Ran the search; holdout PR-AUC
improved 0.5380 -> 0.5577 (+0.0198) and holdout ROC-AUC improved 0.8978 ->
0.9109 under the tuned hyperparameters versus Decision 021's hand-picked
defaults - **adopted**, `XGB_BASE_PARAMS` in `baseline_classifier.py`
updated permanently. Reran Stage 1 and Stage 2 end to end with `--force`.

XGBoost remained Stage 1's selected model and pooled remained the winning
architecture, as expected. Unexpectedly, **Stage 2's official architecture
flipped from Platt scaling to isotonic regression** (median Brier Skill
Score 0.166 vs. Platt's 0.145) purely as a consequence of Stage 1's
reshaped probability distribution - no Stage 2 code changed. Isotonic
mildly regresses PR-AUC vs. Stage 1 raw (flagged automatically by the
existing Decision 022 gating check, not blocked, since BSS is the primary
metric).

### Reason
Following M2-002's finding that Stage 2 recalibration cannot itself improve
discrimination (by construction, for monotonic methods), the team asked
whether Stage 1's own discrimination could be improved before considering a
larger Module 2 redesign. Hand-picked hyperparameters (Decision 021) were
never claimed optimal, only conservative; a holdout-gated Optuna search
(not gated on the same fold-median metric already used for model-type
selection, to avoid compounding a second round of the same mild selection
bias) is the correct way to test that.

### Impact
`src/module2_classification/baseline_classifier.py`'s `fit_and_predict` gained
an optional `xgb_params` parameter; `XGB_BASE_PARAMS` permanently updated.
New files: `scripts/tune_stage1_xgboost.py`,
`outputs/metrics/module2/{xgboost_tuning_trials,
xgboost_tuning_holdout_comparison}.csv`. Regenerated:
`data/processed/module2/{baseline_classifier_predictions,
stage2_compensated_predictions}.csv` and all dependent metrics/model
artifacts. Updated `module_2_classification/MODULE_CONTEXT.md` (Stage 1 and
Stage 2 Implementation Status sections), `module_2_classification/
EXPERIMENT_LOG.md` (new entry M2-003; M2-002 marked superseded),
`research_context/RESEARCH_DECISIONS.md` (new Decision 023; Decision 022's
status corrected), `research_context/PIPELINE_ARCHITECTURE_PLAN.md`
(tuned-params note).

### Status
Accepted. M2-002's specific numeric results (Platt selected, exact BSS/
PR-AUC values) are superseded by M2-003; M2-002's qualitative findings
(stacked XGBoost underperforms, pooled beats per-district) remain valid.

---

## 2026-07-28 - Module 2 Stage 2 Compensation Model Implemented and Run (M2-002)

### Module
Module 2

### Change
Implemented `src/module2_classification/compensation_model.py` per Decision
022's design and ran it end to end. Added `brier_skill_score()` and
`reliability_curve()` to `src/module2_classification/evaluate.py`; added
Stage 2 path constants to `src/config.py`; wired `stage2_compensation` into
`src/module2_classification/main.py`'s `PIPELINE_STAGES`.

**Platt scaling selected** as the official Stage 2 architecture: median
Brier Skill Score improved from -0.043 (Stage 1 raw) to +0.130 on the 12
trainable validation folds, and from -0.080 to +0.292 on the untouched
holdout block. PR-AUC/ROC-AUC are numerically *identical* to Stage 1 raw in
both splits, confirming Decision 022's "no discrimination regression" gate
holds exactly (Platt scaling is a strictly monotonic transform, so ranking
cannot change by construction). Isotonic regression also improved
calibration substantially but is not selected (lower median BSS than
Platt). Stacked XGBoost did not improve calibration (median BSS still
negative, -0.074) - a genuine negative result attributed to its own
per-fold `scale_pos_weight` likely reintroducing a similar probability-scale
distortion to Stage 1's. Pooled-vs-per-district was re-validated
empirically for Stage 2 (stacked-XGBoost arbiter) and again favors pooled,
mirroring Decision 021's Stage-1 finding. Reliability diagrams confirm Stage
1 was systematically overconfident (not underconfident) across most of the
probability range, and Platt scaling pulls both the validation and holdout
curves close to the diagonal.

### Reason
Stage 1's negative Brier skill score (M2-001) meant its raw probabilities
were not usable as real risk estimates despite strong discrimination.
Benchmarking three well-posed architectures (rather than assuming one)
produced clear, reproducible evidence for which correction actually works,
and the exact PR-AUC/ROC-AUC equality for the winning architecture is a
strong internal-consistency check that the implementation is correct.

### Impact
New outputs: `data/processed/module2/stage2_compensated_predictions.csv`,
`outputs/metrics/module2/{stage2_compensation_metrics,
stage2_pooled_vs_per_district_comparison}.csv`,
`outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
`models/module2/stage2_compensation/`. Updated
`module_2_classification/MODULE_CONTEXT.md` ("Stage 2 Implementation
Status" section, Open Question #5 resolved) and
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-002).

### Status
Accepted. The fixed-threshold risk-tier follow-up (deferred in Decision 022)
is now unblocked, since a real calibrated-probability distribution exists.

---

## 2026-07-28 - Module 2 Stage 2 Design Finalized (Decision 022)

### Module
Module 2

### Change
A dedicated planning session (no code written) finalized Module 2 Stage 2's
design before implementation began. Key outcome: a literal port of Module 1
Stage 2's `residual = actual - sarima_prediction` formula was examined and
rejected as statistically ill-posed for a binary label (`label -
predicted_probability` for a single Bernoulli observation is a
high-variance, low-information target, with no clean way to keep
`predicted_probability + predicted_residual` inside `[0, 1]`). Three
numerically well-posed architectures are benchmarked instead, selected by
median Brier Skill Score: isotonic regression (pooled, feature-free), Platt
scaling (pooled, feature-free, logistic regression on
`logit(predicted_probability)` - not raw `p`), and a stacked XGBoost model
on `[predicted_probability, contextual features, District,
probability_residual_lag_1/2]` -> `label`. An XGBoost `base_margin`-warm-
started variant was considered as the most literal translation of Module
1's residual metaphor that stays well-posed, but deferred as a future
ablation rather than built now (the stacked model already covers its
expected benefit and is more flexible).

Also decided: a Decision-010-style no-leakage rule (fold *k* trains only on
prior folds' out-of-sample Stage 1 probabilities, fold 1 is a no-op
passthrough, yielding 12 trainable folds vs. Stage 1's 13); pooled-vs-per-
district re-validated empirically via the stacked-XGBoost architecture as
arbiter, not assumed from Decision 021; calibrated probability as the
primary output with risk-tier labels as a secondary output using fixed (not
quantile) thresholds, values deferred until the real calibrated
distribution can be inspected; Module 1 forecast integration deferred again
as a concrete post-Stage-2 ablation (the two modules' fold boundaries are
misaligned - 14 folds/`MIN_TRAIN_YEARS=3` vs. 13 folds/`MIN_TRAIN_YEARS=4`
- so merging requires a dedicated leakage audit, not a simple merge); Open
Question #8 (consecutive-week trigger) stays deferred.

### Reason
Working through the design before writing code caught a real statistical
problem (the ill-posed residual target) that a direct copy of Module 1's
architecture would have produced. Benchmarking three architectures rather
than picking one a priori follows the same evidentiary standard already
used for Stage 1's model selection (Decision 021).

### Impact
No code changes yet - implementation follows in a subsequent session.
Updated `research_context/RESEARCH_DECISIONS.md` (new Decision 022),
`module_2_classification/MODULE_CONTEXT.md` (Open Questions #5/#6 updated,
Target Direction resolved, "Possible Stage 2 Models" resolved, new "Stage 2
Design Status" section), `research_context/FEATURE_ENGINEERING_SPEC.md`
(new Module 2 Stage 2 feature-group section), and this file.

### Status
Accepted (design); implementation and results pending.

---

## 2026-07-28 - Module 2 Stage 1 Baseline Classifier Implemented

### Module
Module 2

### Change
Implemented `src/module2_classification/evaluate.py` (classification
metrics: `accuracy`, `precision`, `recall`, `specificity`, `f1`, `roc_auc`,
`pr_auc`, `brier_score`, `prevalence`, `confusion_counts`, mirroring Module
1's masked-pure-function style), `src/module2_classification/
baseline_classifier.py` (the full Stage 1 pipeline), and
`src/module2_classification/main.py` (idempotent orchestration mirroring
`module1_forecasting/main.py`'s `PIPELINE_STAGES` pattern). Ran the full
pipeline end to end.

Stage 1 benchmarks Logistic Regression / Random Forest / XGBoost per
walk-forward fold, pooled across all 25 districts (`District` as a
categorical feature). A critical fold-1 fix was found and applied before
the benchmark could run at all: `validation.py`'s SARIMA-tuned
`DEFAULT_MIN_TRAIN_YEARS=3` left fold 1's entire training window with
**zero** rows that have a defined label - the label's own
3-strictly-prior-years requirement (Decision 019) overlaps exactly with
that window, for every district simultaneously. A new, Module-2-specific
`MODULE2_MIN_TRAIN_YEARS=4` (`src/config.py`) fixes this, yielding 13
walk-forward folds (vs. Module 1's 14). The pooled architecture choice was
validated **empirically**, not assumed by analogy with Module 1 Stage 2: a
dedicated XGBoost-only comparison found pooled median PR-AUC (0.500) far
exceeds per-district median PR-AUC (0.287) across the 13 folds. **XGBoost
selected** as the official Stage 1 model by median validation PR-AUC (vs.
Random Forest 0.462, Logistic Regression 0.437); its held-out final-block
PR-AUC is 0.538. A second correction was made mid-implementation: the
original premise that "tree-based models handle NaN natively" is only true
for XGBoost among the three benchmarked models - `sklearn`'s
`RandomForestClassifier` requires explicit imputation, added via a shared
`ColumnTransformer` (also used for Logistic Regression).

### Reason
Module 2's Stage 1 had no code yet, and its fold design needed to be
verified empirically (not assumed to mirror Module 1's) before any model
could be honestly benchmarked - the label's own strictly-prior-years
construction interacts with the walk-forward minimum-training-window
parameter in a way specific to a classification target, not a regression
target. The pooled-vs-per-district architecture question was likewise a
genuine design decision requiring its own evidence, not simply inherited
from Module 1 Stage 2's precedent (a different target type, and a
different, coincidental cause of early-fold data thinness).

### Impact
Added `src/module2_classification/evaluate.py`, `src/module2_classification/
baseline_classifier.py`, `src/module2_classification/main.py` (all
previously placeholders). Added `data/processed/module2/
baseline_classifier_predictions.csv` (58,500 rows), `outputs/metrics/
module2/{baseline_classifier_metrics, pooled_vs_per_district_comparison,
baseline_classifier_feature_importance}.csv`, `models/module2/
baseline_classifier/{fold_1..13, holdout, final_production_model}.json`.
Updated `src/config.py` (`MODULE2_MIN_TRAIN_YEARS` and 6 new output path
constants). Updated `research_context/RESEARCH_DECISIONS.md` (new Decision
021), `module_2_classification/MODULE_CONTEXT.md` (Open Question #4
resolved, new "Stage 1 Implementation Status" section), `module_2_
classification/EXPERIMENT_LOG.md` (new entry M2-001),
`research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer section
updated; `labels.py` filename correction), `research_context/
FEATURE_ENGINEERING_SPEC.md` (baseline classifier probability now
available for Stage 2).

### Status
Accepted.

---

## 2026-07-28 - Module 2 Kickoff: Outbreak Label Definition Decided

### Module
Module 2

### Change
Formalized Module 2's foundational research decision (Decision 019): the
outbreak classification target is a fold-aware **epidemic-threshold** label —
`outbreak = 1 if Number_of_Cases > historical_mean(District, Week) + k *
historical_SD(District, Week)`, with `historical_mean`/`historical_SD`
computed from strictly-prior years only (no label leakage), `k=2` as a
literature-standard default pending an empirical class-balance audit, and a
minimum 3-strictly-prior-years history requirement before a label is defined.
This retires `src/config.py`'s `OUTBREAK_THRESHOLD = 50` placeholder. Also
decided: Module 2's Stage 1 will be built independently of Module 1 (no
SARIMA/XGBoost forecast consumption yet) — deferred, not abandoned, per Open
Question #6.

Updated `module_2_classification/MODULE_CONTEXT.md` (Open Questions #1-3
resolved, #6 annotated deferred, new #7 for `k` calibration; new
"Implementation Plan" section), `research_context/FEATURE_ENGINEERING_SPEC.md`
(Module 2's label formula and feature categories made concrete, explicit note
that Module 1 integration is deferred), and
`research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer section
expanded from a placeholder into a concrete build plan covering
preprocessing, label definition, feature engineering, and both stages).

### Reason
Module 2 had no code yet, and its most fundamental open question (how an
"outbreak" is even defined) was blocking all downstream work. A single fixed
count threshold is not defensible across 25 districts with very different
baseline incidence (per the already-documented zero-inflation heterogeneity);
a per-district-week statistical threshold is both more defensible and
naturally resolves two other open questions (district-specificity, threshold
justification) at the same time.

### Impact
`research_context/RESEARCH_DECISIONS.md` (new Decision 019),
`module_2_classification/MODULE_CONTEXT.md`,
`research_context/FEATURE_ENGINEERING_SPEC.md`,
`research_context/PIPELINE_ARCHITECTURE_PLAN.md`. No code changes yet in this
entry — implementation (`scripts/data_audit_module2.py`,
`src/preprocessing/module2_preprocessing.py`,
`src/module2_classification/label_definition.py`, etc.) follows in subsequent
work and will be logged separately once run.

### Status
Accepted (label definition and Module 1 sequencing); `k=2` remains tunable
pending the empirical class-balance audit.

---

## 2026-07-28 - Module 2 Label Class-Balance Audit Run; k=2 Finalized

### Module
Module 2

### Change
Added `scripts/data_audit_module2.py` (new, read-only diagnostic mirroring
`scripts/data_audit_module1.py`'s style) and ran it against
`data/processed/shared/epidemiological_weekly.csv` (25,348 rows, 25
districts) for Decision 019's epidemic-threshold label at `k ∈ {1.5, 2.0,
2.5}`. No district produced a degenerate outbreak rate (outside a [2%, 40%]
sanity band) at any candidate. `k=2` is finalized: pooled outbreak rate 18.4%
(range 12.6%-25.2% across districts), 15.7% of rows undefined (< 3
strictly-prior years of history, concentrated in each district's earliest
years, correctly excluded rather than defaulted to 0). Full per-district,
per-`k` results written to `outputs/metrics/module2/label_balance_audit.csv`.

**Methodological finding, flagged rather than silently accepted**: an
18-25%-of-weeks outbreak rate is considerably higher than typical WHO/CDC
epidemic-alert rates (usually single-digit %), suggesting the single-week
`mean + k*SD` threshold is flagging much of each district's normal seasonal
(monsoon) peak rather than only genuinely anomalous spikes. Recorded as new
Module 2 Open Question #8 - candidate follow-ups (requiring >=2 consecutive
weeks above threshold, or deseasonalizing before computing the anomaly) are
noted but not implemented this session; `k=2` proceeds as the kickoff's
working default, not a final validated label definition.

### Reason
`k` needed empirical confirmation, not an assumed literature value, given
Module 1's already-documented cross-district zero-inflation heterogeneity
(e.g. `Mullaitivu` 52.8% zero-weeks vs `Colombo` 0.5%) which could plausibly
have produced degenerate per-district label rates at a naively chosen `k`.

### Impact
Added `scripts/data_audit_module2.py`,
`outputs/metrics/module2/label_balance_audit.csv`. Updated
`research_context/RESEARCH_DECISIONS.md` (Decision 019's `k` finalized with
evidence and the seasonal-peak caveat), `module_2_classification/MODULE_CONTEXT.md`
(Open Question #7 resolved, new Open Question #8).

### Status
Accepted (`k=2` as kickoff default); Open Question #8 (single-week vs
consecutive-week / deseasonalized trigger) left open for future refinement.

---

## 2026-07-28 - Module 2 Preprocessing, Label Definition, and Stage 1 Feature Engineering Implemented

### Module
Module 2

### Change
Implemented `src/preprocessing/module2_preprocessing.py` (own week-53/
missing-week/`weather_code` decisions per Decision 013, mirroring but not
inheriting Module 1's pattern; output: `data/processed/module2/
weekly_modeling_table.csv`, 25,350 rows, matching Module 1's row count since
the underlying policy choices happened to align), `src/module2_classification/
labels.py` (Decision 019's fold-aware epidemic-threshold label -
`compute_historical_stats`/`compute_epidemic_threshold_labels`; verified
18.35% pooled outbreak rate at `k=2`, consistent with the earlier audit's
18.41%), and `src/module2_classification/feature_engineering.py` (Stage 1
features).

Feature engineering was deliberately paused mid-implementation for a
dedicated review (prompted by the user, not yet fully finalized) before
Stage 1 modeling code was written on top of it. That review found and fixed
a real leakage risk (the first pass carried `Number_of_Cases`/`cases_per_100k`
- the exact quantity the label is thresholded on - forward as if they were
usable features) and added two new feature groups beyond the original
feature-direction bullet list: lagged climate (`rainfall_lag_2-8`,
`temperature_lag_1-4`, `humidity_lag_1-4`, capturing dengue's ~2-8-week
transmission delay, which anomaly-only features miss) and case-level
seasonal-anomaly lags (`case_anomaly_lag_1/2`, conceptually similar to Module
1's `residual_lag`). Also added `momentum_vs_rolling_mean` (reduces
zero-inflation noise vs. a bare `rate_of_change`) and current-week raw
climate features (a deliberate divergence from Module 1's Stage-1
climate-free rule, since Decision 001 is Module-1-scoped). Final feature
table: 25,350 rows x 53 columns (32 enumerated in
`FOLD_AGNOSTIC_FEATURE_COLUMNS`), written to `data/features/module2/
stage1_feature_table.csv`.

Also documented, as a subtle but important correctness point: the
case-anomaly lag's `historical_mean`/`historical_sd` (reused from `labels.py`)
use a per-ROW expanding, strictly-prior-calendar-year construction, which is
safe to compute ONCE globally - a different (and here, provably equivalent)
leakage-guard architecture than the climate anomaly's per-FOLD frozen
construction (reused unchanged from Module 1). The two must not be conflated.

### Reason
A classifier trained on `cases_per_100k` (or the raw case count itself) as a
feature would trivially "predict" its own label rather than learn genuine
epidemiological structure - this had to be fixed with an explicit, enumerated
feature-column list before any Stage 1 model could be honestly evaluated.
The two new feature groups were added because the original feature-direction
list (anomalies only, no lags; no case-level anomaly signal) would have left
out signal Module 1's own design already demonstrated as valuable
(`residual_lag_1/2` was Module 1's single most important Stage 2 feature).

### Impact
Added `src/preprocessing/module2_preprocessing.py`,
`src/module2_classification/labels.py`,
`src/module2_classification/feature_engineering.py` (rewritten once after
the review), `data/processed/module2/weekly_modeling_table.csv`,
`data/features/module2/stage1_feature_table.csv`. Updated `src/config.py`
(Module 2 path constants, `EPIDEMIC_THRESHOLD_K`/`_MIN_PRIOR_YEARS`),
`research_context/FEATURE_ENGINEERING_SPEC.md` (Module 2 feature groups
finalized in detail), `module_2_classification/MODULE_CONTEXT.md` (Current
Feature Direction section rewritten).

### Status
Accepted.

---

## 2026-07-28 - Module 2 Preprocessing Review: Week 53 Kept Unmerged; is_imputed Masking Made Consistent

### Module
Module 2

### Change
Before starting Stage 1 modeling, paused (prompted by the user) to review the
three Decision-013-independent preprocessing choices flagged as unreviewed
kickoff defaults in the prior entry (Decision 020,
`research_context/RESEARCH_DECISIONS.md`):

1. **Week 53 (2009, 2016, 2019, 2021) is no longer merged into week 52** —
   reverses the kickoff default. `src/preprocessing/module2_preprocessing.py`'s
   week-53 merge functions were removed entirely; `find_missing_weeks`/
   `validate_weekly_modeling_table` now expect 53 weeks for those four years,
   52 otherwise.
2. **`is_imputed` rows are now masked to `NaN` before deriving `cases_lag_1-4`,
   `rolling_mean_cases_4w`, `rolling_std_cases_4w`, `rate_of_change`, and
   `momentum_vs_rolling_mean`** in `src/module2_classification/
   feature_engineering.py` — previously only `case_anomaly_lag_1/2` had this
   masking, a real inconsistency found during the review, not just a design
   preference.
3. **`weather_code` exclusion reconfirmed unchanged** — no Module-2-specific
   reason found to revisit Module 1's original redundancy reasoning.
4. Added `MODULE2_MONSOON_WEEKS_NE` (`= MONSOON_WEEKS_NE + [53]`) since week
   53 (late December) is now exposed to the monsoon-indicator feature and
   falls inside the NE monsoon window; the shared `MONSOON_WEEKS_NE` constant
   assumes Module 1's merged 52-week structure and must not be mutated.

Both preprocessing outputs were regenerated: `data/processed/module2/
weekly_modeling_table.csv` (25,450 rows, up from 25,350; 102 rows flagged
`is_imputed`, up from ~100) and `data/features/module2/
stage1_feature_table.csv` (unchanged shape: 53 columns, 32 fold-agnostic
features). Verified post-fix that `cases_lag_1` for the week immediately
following an imputed week is now `NaN` rather than the previously-silent
fabricated value.

### Reason
Merging week 53 into week 52 sums two real weeks' case counts *before* the
epidemic threshold is computed — for Module 2 specifically (unlike Module 1,
which only needs total magnitude for SARIMA) this risks (a) spuriously
tripping the outbreak threshold from merge arithmetic alone, and (b)
contaminating week 52's cross-year `historical_mean`/`SD` (used by
`labels.py`) for every year, not just the four merged ones — a genuine
label-integrity concern, not just a simplification worth revisiting later.
The `is_imputed` masking gap was an inconsistency: the label and
`case_anomaly_lag_*` already excluded fabricated seasonal-naive values from
biasing a statistic, but plain case-trend features did not.

### Impact
Modified `src/preprocessing/module2_preprocessing.py` (week-53 merge
functions removed; `find_missing_weeks`/`validate_weekly_modeling_table`
updated for variable weeks-per-year), `src/module2_classification/
feature_engineering.py` (masking fix; `MODULE2_MONSOON_WEEKS_NE` added).
Regenerated `data/processed/module2/weekly_modeling_table.csv` and
`data/features/module2/stage1_feature_table.csv`. The `k=2` label-balance
audit (`outputs/metrics/module2/label_balance_audit.csv`) required no rerun —
`scripts/data_audit_module2.py` already read the unmerged shared table
directly. Updated `research_context/RESEARCH_DECISIONS.md` (Decision 020),
`research_context/PIPELINE_ARCHITECTURE_PLAN.md`, `module_2_classification/
MODULE_CONTEXT.md`, `research_context/FEATURE_ENGINEERING_SPEC.md`.

### Status
Accepted.

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
