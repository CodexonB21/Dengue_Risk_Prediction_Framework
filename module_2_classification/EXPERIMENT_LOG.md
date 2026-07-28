# Module 2 Experiment Log

Use this file to record all outbreak classification experiments.

---

## Experiment Template

```markdown
## Experiment ID: M2-000

### Date
YYYY-MM-DD

### Research Question
What are we testing?

### Label Definition
Binary / multi-class threshold details

### Data Period
Training and test periods

### Stage 1 Model
Model and parameters

### Stage 2 Model
Model and parameters

### Features Used
List feature groups

### Class Imbalance Handling
None / class weights / SMOTE / other

### Metrics
Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC

### Results
Record metric values and observations

### Interpretation
What does this mean?

### Decision
Keep / Reject / Modify / Repeat

### Documentation Updated
List updated files
```

---

## Experiment ID: M2-001

### Date
2026-07-28

### Research Question
Given Decision 019's fold-aware epidemic-threshold label, which of Logistic
Regression / Random Forest / XGBoost produces the best genuinely
out-of-sample walk-forward outbreak classifier, is a pooled (all-districts,
`District` as a feature) architecture actually better than training one
model per district, and how well does the selected baseline classifier
perform overall?

### Label Definition
Decision 019's epidemic-threshold label: `outbreak = 1 if Number_of_Cases >
historical_mean(District, Week) + 2 * historical_SD(District, Week)`,
`historical_mean`/`historical_SD` computed from strictly-prior years only.
Rows with an undefined label (< 3 strictly-prior years of history, or
`is_imputed == True`) are excluded from both training and scoring, never
defaulted to 0.

### Data Period
`data/features/module2/stage1_feature_table.csv` (25,450 rows, 2006-2026),
labeled via `labels.compute_epidemic_threshold_labels`. Per district: **13**
expanding-window annual walk-forward folds (new `MODULE2_MIN_TRAIN_YEARS =
4` minimum initial training window - see Decision 021 for why Module 1's
`DEFAULT_MIN_TRAIN_YEARS = 3` doesn't work here), drawn from all history
except the final 104 weeks (2 years), held out untouched and scored once at
the end (mirrors Module 1's Decision 009).

### Stage 1 Model
Three models benchmarked per fold, pooled across all 25 districts
(`District` as a categorical feature): Logistic Regression
(`class_weight="balanced", max_iter=2000`), Random Forest (`n_estimators=300,
max_depth=8, min_samples_leaf=5, class_weight="balanced"`), XGBoost
(`max_depth=4, learning_rate=0.05, n_estimators=300, subsample=0.8,
colsample_bytree=0.8, scale_pos_weight` computed per fold from that fold's
own training labels). Fixed hyperparameters across all folds (not tuned per
fold). Logistic Regression/Random Forest use a `ColumnTransformer`
(median-impute + one-hot `District`, fit on training rows only per fold);
XGBoost uses raw features with `District` as a native pandas categorical
and untouched NaNs (`enable_categorical=True`).

### Stage 2 Model
Not built this session (out of scope - `compensation_model.py` remains a
placeholder).

### Features Used
`FOLD_AGNOSTIC_FEATURE_COLUMNS` (32 features: case lags/rolling
stats/rate-of-change/momentum, lagged + current-week raw climate, seasonal
indicators, case-anomaly lags) + fold-aware climate anomalies
(`rainfall_anomaly`, `temperature_anomaly`, `humidity_anomaly`, recomputed
per fold from that fold's training rows) + `District` (categorical). See
`research_context/FEATURE_ENGINEERING_SPEC.md` Module 2 section for the
full enumerated list.

### Class Imbalance Handling
`class_weight="balanced"` (Logistic Regression, Random Forest);
`scale_pos_weight = n_neg / n_pos` computed from each fold's own training
labels (XGBoost). Not SMOTE.

### Metrics
PR-AUC (primary), ROC-AUC, accuracy, precision, recall, specificity, F1
(fixed 0.5 cutoff, explicitly an untuned diagnostic), Brier score,
prevalence - all computed only on rows with a defined label. Reported per
fold, median-aggregated across the 13 validation folds, and once on the
held-out final block.

### Results
- **Fold-1 fix confirmed**: with Module 1's `DEFAULT_MIN_TRAIN_YEARS = 3`,
  fold 1's entire training window had **zero** rows with a defined label,
  for every district - the label's own 3-strictly-prior-years requirement
  overlaps exactly with that window. `MODULE2_MIN_TRAIN_YEARS = 4` fixes
  this (fold 1: 1,275 pooled trainable rows) at the cost of one fewer fold
  (13 vs. Module 1's 14).
- **Pooled vs. per-district (XGBoost arbiter)**: pooled median PR-AUC across
  13 folds = **0.500**, per-district median PR-AUC = **0.287** (mean
  0.433). Pooled wins in 10/13 folds, most decisively in the earliest,
  thinnest folds (fold 1: 0.272 vs. 0.165; fold 11: 0.331 vs. 0.048). Full
  table: `outputs/metrics/module2/pooled_vs_per_district_comparison.csv`.
- **3-model benchmark** (median across 13 validation folds):

  | Model | PR-AUC | ROC-AUC | Accuracy | Precision | Recall | F1 | Brier |
  |---|---|---|---|---|---|---|---|
  | Logistic Regression | 0.437 | 0.799 | 0.839 | 0.287 | 0.634 | 0.397 | 0.141 |
  | Random Forest | 0.462 | 0.815 | 0.840 | 0.346 | 0.627 | 0.454 | 0.133 |
  | **XGBoost** | **0.500** | 0.816 | 0.849 | 0.332 | 0.567 | 0.437 | 0.117 |

- **XGBoost selected** as the official Stage 1 model (highest median
  PR-AUC and lowest Brier score, i.e. best-calibrated of the three).
- **Held-out final block** (2 years, never touched during fold-based
  selection): XGBoost PR-AUC = 0.538, ROC-AUC = 0.898, F1 = 0.491
  (prevalence 7.2%, notably lower than the validation folds' pooled 14.4%
  scored prevalence).
- **Feature importance** (official XGBoost, gain): `case_anomaly_lag_1`
  (312.9) dominates, followed by `case_anomaly_lag_2` (155.6),
  `rolling_mean_cases_4w` (44.1), `monsoon_indicator_SW` (35.3), `cos_week`
  (31.5), `District` (30.7).
- Full detail: `outputs/metrics/module2/baseline_classifier_metrics.csv`,
  `outputs/metrics/module2/baseline_classifier_feature_importance.csv`,
  `data/processed/module2/baseline_classifier_predictions.csv` (58,500 rows).

### Addendum (2026-07-28): Discrimination-vs-Calibration Diagnostic
Prompted by the question "how do we know Stage 1 is actually a success?" -
raw metrics from the table above are not self-interpreting without a
no-skill/climatology reference. Added `scripts/stage1_calibration_diagnostic.py`
(read-only, derives from the already-written metrics CSV, no rerun needed)
computing three comparisons not in the raw metrics file, for the official
XGBoost model:

1. **PR-AUC uplift ratio** (`pr_auc / prevalence` - the correct no-skill
   reference for PR-AUC is the fold's own prevalence, not 0): XGBoost beats
   this in **every fold and the holdout**, median uplift **3.65x**, up to
   13.2x in the sparsest fold (11). Confirms genuine discriminative skill,
   not an imbalance artifact.
2. **Accuracy uplift vs. majority-class baseline** (`accuracy - (1 -
   prevalence)`): **negative in 8/13 validation folds** (e.g. fold 6: 71.6%
   vs. 82.2% majority-baseline). Not a failure - it is exactly why PR-AUC,
   not accuracy, is the primary metric (Decision 021) - but flagged
   because a bare "accuracy = 0.85" reading of the metrics CSV would be
   misleading without this comparison.
3. **Brier skill score** (`1 - brier_score / (prevalence * (1 -
   prevalence))`, i.e. skill relative to always predicting the fold's own
   base rate): **negative in 8/14 folds+holdout** (as low as -0.93 in fold
   12), median **-0.11**. This means the model's raw predicted
   probabilities are, in most folds, LESS accurate than a trivial
   "always-predict-the-base-rate" forecast - despite the same model having
   strong PR-AUC discrimination in those same folds. This is a well-known
   decoupling: `scale_pos_weight`-based imbalance correction improves
   ranking under a reweighted loss but distorts the output probability
   scale (typically overconfident on the minority class), and is a
   standard reason models trained this way need explicit post-hoc
   recalibration. Full per-fold table:
   `outputs/metrics/module2/baseline_classifier_calibration_diagnostic.csv`.

Cross-checked the two most extreme-prevalence folds against real-world
epidemiology as an independent, non-circular sanity check on the label
itself: fold 7's validation window (prevalence 78.9%, a huge outlier) is
**2016-2017** - Sri Lanka's worst recorded dengue epidemic year
(~186,000 national cases); fold 11's (prevalence 2.5%, the sparsest fold)
is **2020-2021** - plausibly consistent with COVID-era mobility
restrictions suppressing transmission. Both are genuine, independently
verifiable epidemiological events, not label-construction noise.

### Interpretation
The pooled architecture is not just theoretically preferable (more training
data per fold) but empirically confirmed on this exact label and feature
set, particularly valuable in the sparse early folds where a per-district
model has too little history to be reliable. All three models are
directionally reasonable (PR-AUC well above the ~0.14-0.22 pooled
prevalence baseline in most folds), with XGBoost's edge being modest but
consistent. `case_anomaly_lag_1`'s dominance is expected, not a leakage red
flag - it is conceptually near-identical to the label one week prior
(documented in `FEATURE_ENGINEERING_SPEC.md`'s Group M2-5 leakage note),
analogous to how `residual_lag_1` dominated Module 1 Stage 2's feature
importance.

The calibration diagnostic revises one claim from the original write-up:
XGBoost's lower raw Brier score does **not** mean its probability output is
"the best-calibrated starting point" in any absolute sense - both its raw
Brier score AND the correct no-skill Brier reference scale down together
with prevalence, so a small raw Brier score across low-prevalence folds is
not itself evidence of good calibration. **Stage 1 succeeds at
discrimination (ranking outbreak-risk weeks correctly), not at calibration
(the probability values themselves are not trustworthy as-is)** - which
means Stage 2's planned probability recalibration (Open Question #5) is not
optional polish but a necessary, now-evidenced step before
`predicted_probability` can be used as a real risk estimate.

### Decision
**Keep** the pooled XGBoost model as Stage 1's official output - it will be
the artifact Stage 2 consumes (`predicted_probability` column), on the
basis of its discrimination, not its raw calibration. **Keep**
`MODULE2_MIN_TRAIN_YEARS = 4` as a permanent, documented Module-2-specific
override, not a temporary workaround. **Elevate** probability calibration
(Open Question #5) from "planned" to a load-bearing prerequisite for Stage
2, given the negative Brier skill score finding - it is no longer just a
nice-to-have refinement. **Defer** the consecutive-week outbreak trigger
refinement (Open Question #8) to future work - remains open, not silently
resolved by this experiment.

### Documentation Updated
- `module_2_classification/MODULE_CONTEXT.md` (Open Question #4 resolved;
  Possible Stage 1 Models section resolved; Current Feature Direction
  updated; Implementation Plan steps 3/5/7 updated; new "Stage 1
  Implementation Status" section, including the calibration diagnostic).
- `module_2_classification/EXPERIMENT_LOG.md` (this entry, incl. addendum).
- `research_context/RESEARCH_DECISIONS.md` (new Decision 021).
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer section
  updated, `baseline_classifier.py` marked implemented).
- `research_context/FEATURE_ENGINEERING_SPEC.md` (baseline classifier
  probability now available for Stage 2).
- `research_context/CHANGELOG.md` (new entry).
- Added `scripts/stage1_calibration_diagnostic.py` and
  `outputs/metrics/module2/baseline_classifier_calibration_diagnostic.csv`.

---

## Experiment ID: M2-002

### Date
2026-07-28

### Research Question
Given Stage 1's confirmed calibration failure (M2-001's negative median Brier
skill score), which of three well-posed correction architectures - pooled
isotonic regression, pooled Platt scaling, or a stacked XGBoost classifier -
best repairs Stage 1's `predicted_probability` under a Decision-010-style
no-leakage rule, without regressing Stage 1's discrimination (PR-AUC/ROC-AUC)?
Is pooled still better than per-district for Stage 2, and does a literal
residual-regression framing even make sense for a binary target?

### Label Definition
Unchanged from M2-001 (Decision 019's epidemic-threshold label). Stage 2
consumes Stage 1's already-computed `label` column directly - no relabeling.

### Data Period
Stage 1's official (XGBoost) out-of-sample `predicted_probability` +
`label`, all 13 walk-forward folds + holdout, from
`data/processed/module2/baseline_classifier_predictions.csv`. Stage 2 fold
*k* (`k` = 2..13) trains only on folds `1..k-1`'s pooled out-of-sample rows
(Decision 022's no-leakage rule) - fold 1 has no prior data and is a
documented no-op passthrough. This yields **12 trainable folds** (one fewer
than Stage 1's 13) plus the holdout block (trained on all 13 folds pooled).

### Stage 1 Model
Unchanged from M2-001 - the official pooled XGBoost classifier. Stage 2
treats its `predicted_probability` as a fixed input to be corrected, not
retrained.

### Stage 2 Model
Three architectures benchmarked (Decision 022 - a literal `label -
predicted_probability` residual regression was examined and rejected as
ill-posed for a binary target before any of these were built):
- **Isotonic regression** (pooled, feature-free): `IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)` on `predicted_probability` -> `label`.
- **Platt scaling** (pooled, feature-free): `LogisticRegression(max_iter=2000)` on `logit(predicted_probability)` (1 feature, the log-odds).
- **Stacked XGBoost**: same fixed hyperparameters as Stage 1
  (`max_depth=4, learning_rate=0.05, n_estimators=300, subsample=0.8,
  colsample_bytree=0.8`, per-fold `scale_pos_weight`), on
  `[predicted_probability, 32 contextual features, 3 fold-scoped climate
  anomalies, District, probability_residual_lag_1/2]` -> `label`.

### Features Used
Isotonic/Platt: `predicted_probability` only (feature-free by design).
Stacked XGBoost: Stage 1's full `FOLD_AGNOSTIC_FEATURE_COLUMNS` (32) +
fold-scoped `rainfall_anomaly`/`temperature_anomaly`/`humidity_anomaly` +
`District` + `predicted_probability` + `probability_residual_lag_1/2`
(built via the same full-calendar-reindex-then-shift construction as
Module 1's `residual_lag_1/2`, Decision 015).

### Class Imbalance Handling
`scale_pos_weight = n_neg / n_pos` per training fold (stacked XGBoost only,
same as Stage 1). Isotonic/Platt make no explicit imbalance correction -
their entire purpose is to correct exactly the kind of scale distortion
`scale_pos_weight` can introduce.

### Metrics
Brier Skill Score (primary selection metric, `1 - brier_score /
(prevalence * (1 - prevalence))`), PR-AUC, ROC-AUC, accuracy, precision,
recall, specificity, F1 (fixed 0.5 cutoff), Brier score, prevalence - median
across the 12 trainable validation folds, plus once on holdout.
`architecture="stage1_raw"` rows computed at every fold for direct
before/after comparison. Reliability diagrams (binned predicted-probability
vs. observed frequency) for Stage 1 raw vs. the selected architecture.

### Results
- **Fold-1 no-op passthrough confirmed correct**: 1,300 rows,
  `calibrated_probability == stage1_predicted_probability` exactly
  (max abs diff = 0.0), `stage2_trained = False`.
- **Architecture benchmark** (median across the 12 trainable validation folds):

  | Architecture | PR-AUC | ROC-AUC | Brier score | Brier Skill Score |
  |---|---|---|---|---|
  | Stage 1 raw (no correction) | 0.505 | 0.831 | 0.114 | **-0.043** |
  | Isotonic | 0.482 | 0.830 | 0.080 | 0.127 |
  | **Platt** | **0.505** | **0.831** | 0.080 | **0.130** |
  | Stacked XGBoost | 0.469 | 0.812 | 0.122 | -0.074 |

- **Platt scaling selected** as the official Stage 2 architecture (highest
  median Brier Skill Score). Its PR-AUC/ROC-AUC are **numerically identical**
  to Stage 1 raw (0.504920 vs. 0.504920; 0.830953 vs. 0.830953) - expected,
  not a coincidence: Platt scaling is a strictly monotonic transform of
  `predicted_probability`, so it cannot change ranking/AUC at all by
  construction. This is the cleanest possible confirmation that Decision
  022's "PR-AUC/ROC-AUC must not regress" gate is satisfied exactly, not just
  approximately. Isotonic regression, also monotonic, regressed PR-AUC very
  slightly (0.482 vs. 0.505) - a known isotonic-regression artifact from its
  step-function output creating ties that `average_precision_score` breaks
  differently than the raw continuous probabilities; still far above Stage
  1's original discrimination floor.
- **Stacked XGBoost underperformed on calibration** (median BSS = -0.074,
  still negative) despite being the most flexible architecture, and also
  regressed PR-AUC/ROC-AUC slightly vs. Stage 1 raw - flagged per Decision
  022's gating check, not blocked (it was not the winner regardless). Most
  likely cause: its own per-fold `scale_pos_weight` reintroduces a similar
  probability-scale distortion to Stage 1's, on top of an already-small
  12-fold training signal for a second imbalance-corrected model to learn
  from cleanly.
- **Platt beats Stage 1 raw's Brier Skill Score in 11 of 12 trainable folds**
  (fold 7 is the lone exception: raw BSS 0.349 vs. Platt BSS -0.125, likely
  driven by fold 7's own extreme prevalence outlier - 78.9%, the 2016-2017
  epidemic year identified in M2-001 - where a pooled logit-space correction
  fit on far-lower-prevalence prior folds generalizes worst).
- **Pooled vs. per-district re-validated for Stage 2** (stacked XGBoost
  arbiter, mirrors M2-001's Stage 1 finding): pooled aggregate BSS = -0.074
  vs. per-district median = -0.274 (mean -0.620) across 270 scored
  district-folds. Pooled wins decisively again - full table:
  `outputs/metrics/module2/stage2_pooled_vs_per_district_comparison.csv`.
- **Held-out final block** (2 years, never touched during fold-based
  architecture selection): Platt BSS = **0.292** (vs. Stage 1 raw's
  **-0.080**), PR-AUC/ROC-AUC again numerically identical to Stage 1 raw
  (0.538/0.898). Reliability diagrams
  (`outputs/figures/module2/reliability_diagram_{validation,holdout}.png`)
  visually confirm the raw curve sits well below the diagonal across most of
  the probability range (Stage 1 is **overconfident** - predicts higher
  outbreak risk than actually observed, not underconfident) and Platt pulls
  it close to the diagonal in both splits.
- **Final production Platt model**: `coef_ = 1.011`, `intercept_ = -1.118`
  (in logit space) - a slope near 1 (the raw probabilities' relative
  ordering/spread in logit space is roughly right) with a substantial
  negative intercept shift, consistent with the reliability-diagram finding
  that Stage 1 is systematically overconfident, not just noisy.
- Full detail: `outputs/metrics/module2/stage2_compensation_metrics.csv`,
  `data/processed/module2/stage2_compensated_predictions.csv` (55,900 rows:
  1,300 fold-1 passthrough + 3 x (15,600 fold 2-13 rows + 2,600 holdout rows)).

### Interpretation
Decision 022's core design bet is confirmed empirically: a simple, pooled,
feature-free recalibration (Platt scaling) fixes Stage 1's calibration
failure completely (median BSS -0.043 -> +0.130, holdout -0.080 -> +0.292)
while being PROVABLY unable to touch discrimination, which is exactly what
was needed - Stage 1's problem was never its ranking (PR-AUC was already
solid), it was the raw probability *scale*. The more flexible stacked
XGBoost architecture, hypothesized as a possible improvement over pure
recalibration by allowing feature-based down-weighting of a distorted
Stage-1 signal, did not deliver that benefit in practice and is not
selected - a useful negative result, not a wasted benchmark: it confirms the
"ill-posed residual regression" concern from Decision 022 wasn't the only
risk worth checking, imbalance-correction reintroduction on a second
XGBoost layer was a real, evidenced failure mode too, not merely a
theoretical one. Pooled-vs-per-district's result mirrors M2-001 exactly,
reinforcing that Module 2's data volume per district remains too thin for
independent per-district modeling anywhere in the pipeline.

### Decision
**Keep** Platt scaling as Stage 2's official architecture - it is the
artifact that turns Stage 1's `predicted_probability` into a genuinely
usable risk estimate. **Keep** the pooled architecture for Stage 2 (as for
Stage 1). **Do not build** the deferred `base_margin`-initialized XGBoost
ablation as a priority follow-up - the stacked-model failure mode observed
here (reintroduced scale distortion) would very likely also affect it,
since it shares the same per-fold `scale_pos_weight` mechanism; worth
revisiting only if a future scale-distortion-free imbalance handling
approach is adopted. **Proceed** to the deferred fixed-threshold risk-tier
follow-up now that a real calibrated-probability distribution exists to set
thresholds against. **Keep** the Module 1 forecast integration deferred as
an ablation (Decision 022, unchanged).

### Documentation Updated
- `module_2_classification/MODULE_CONTEXT.md` ("Stage 2 Design Status"
  section replaced with "Stage 2 Implementation Status" reporting these
  results; Open Question #5 marked resolved with results).
- `module_2_classification/EXPERIMENT_LOG.md` (this entry).
- `research_context/RESEARCH_DECISIONS.md` Decision 022 (design already
  recorded prior to this run; results are in this log entry per the
  decision's own "Implication" note).
- New artifacts: `src/module2_classification/compensation_model.py`,
  `data/processed/module2/stage2_compensated_predictions.csv`,
  `outputs/metrics/module2/{stage2_compensation_metrics,
  stage2_pooled_vs_per_district_comparison}.csv`,
  `outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
  `models/module2/stage2_compensation/`.

**Superseded numerically by M2-003 (2026-07-28)**: Stage 1's hyperparameters were
subsequently tuned (Decision 023), which changed Stage 1's `predicted_probability`
distribution enough that Stage 2's official architecture flipped from Platt scaling to
isotonic regression on rerun. This entry's narrative and negative results (stacked XGBoost
underperforming, per-district losing to pooled) remain valid as historical results against
the pre-tuning Stage 1 model; the specific numbers above (Platt selected, exact BSS/PR-AUC
values) are no longer the current production state. See M2-003 for the current numbers.

---

## Experiment ID: M2-003

### Date
2026-07-28

### Research Question
Following M2-002's finding that Stage 2 fixes calibration but, by construction (monotonic
recalibration), cannot improve discrimination, can Stage 1's own discrimination (PR-AUC) be
improved by tuning its XGBoost hyperparameters (fixed by hand since Decision 021), without
overfitting to the same validation folds used for model-type selection? If adopted, how does
retuned Stage 1 change Stage 2's own architecture benchmark?

### Label Definition
Unchanged from M2-001/M2-002.

### Data Period
Same 13 Stage-1 walk-forward folds + holdout as M2-001 (`MODULE2_MIN_TRAIN_YEARS=4`). The
Optuna search itself only ever touches the 13 validation folds; the holdout block is reserved
exclusively for the adopt/reject verdict (never used by the search).

### Stage 1 Model
XGBoost only (the model already selected in Decision 021 — hyperparameter tuning does not
revisit model-type selection). `scripts/tune_stage1_xgboost.py`: Optuna TPE sampler (seed=42,
60 trials), objective = median PR-AUC across the 13 validation folds, searching `max_depth
[3,8]`, `learning_rate [0.01,0.3]` (log), `n_estimators [100,600]`, `subsample [0.5,1.0]`,
`colsample_bytree [0.5,1.0]`, `reg_lambda [0.1,10]` (log), `min_child_weight [1,15]`,
`reg_alpha [0,5]`, `gamma [0,5]`. `scale_pos_weight` excluded from the search — always
recomputed per fold from that fold's own training labels (leakage-safety property, not a
tunable hyperparameter).

### Stage 2 Model
Unchanged architecture set from M2-002 (isotonic, Platt, stacked XGBoost) — rerun against
Stage 1's retuned `predicted_probability` output, not itself retuned.

### Features Used
Unchanged from M2-001/M2-002.

### Class Imbalance Handling
Unchanged (`scale_pos_weight` per fold, XGBoost only).

### Metrics
Optuna search objective: median PR-AUC across 13 validation folds. Adopt/reject verdict:
holdout-only PR-AUC, ROC-AUC, Brier score, Brier Skill Score (default vs. tuned params).
Post-adoption full rerun: same metrics as M2-001 (Stage 1) and M2-002 (Stage 2).

### Results
- **Optuna search**: 60 trials, best median validation-fold PR-AUC = **0.5319** (up from the
  hand-picked defaults' contribution to Decision 021's originally-reported 0.500 — not
  directly comparable as a "search result" since Decision 021's 0.500 was itself measured
  with the old fixed hyperparameters on the same folds; the honest comparison is the holdout
  numbers below). Best params: `max_depth=3, learning_rate=0.012373, n_estimators=217,
  subsample=0.656521, colsample_bytree=0.596229, reg_lambda=1.075784, min_child_weight=10,
  reg_alpha=4.119728, gamma=2.493017`. Full trial history:
  `outputs/metrics/module2/xgboost_tuning_trials.csv`.
- **Holdout adopt/reject comparison** (the honest evidence — holdout never touched by the
  search):

  | Variant | PR-AUC | ROC-AUC | Brier | BSS |
  |---|---|---|---|---|
  | Default (Decision 021 hand-picked) | 0.5380 | 0.8978 | 0.0725 | -0.0804 |
  | **Tuned (Optuna best trial)** | **0.5577** | **0.9109** | 0.0902 | -0.3453 |

  PR-AUC delta **+0.0198** (+3.7% relative), ROC-AUC delta **+0.0131**. Brier/BSS got worse
  under the tuned params — expected and not disqualifying: the search objective is PR-AUC
  only, Stage 1 was never selected or tuned for calibration (Decision 021), and Stage 2
  recalibrates whatever scale Stage 1 produces regardless (Decision 022). Full table:
  `outputs/metrics/module2/xgboost_tuning_holdout_comparison.csv`.
- **RECOMMENDATION: ADOPT** (script's own holdout-PR-AUC-delta > 0 gate). `XGB_BASE_PARAMS`
  updated in `baseline_classifier.py`.
- **Full Stage 1 + Stage 2 rerun with `--force`** after adoption:
  - Stage 1: XGBoost remains the selected model (median validation PR-AUC **0.532** vs.
    Random Forest 0.462, Logistic Regression 0.437). Pooled-vs-per-district reconfirmed:
    aggregate pooled PR-AUC **0.532** vs. per-district median **0.355** (mean 0.455), pooled
    wins 12/13 folds. Holdout: PR-AUC 0.5577, ROC-AUC 0.9109, accuracy 0.8908 (matches the
    tuning script's own holdout recompute exactly — cross-check passed). Top feature
    importance reshuffled slightly under the new hyperparameters but the same features
    dominate: `case_anomaly_lag_1` (905.0) ≫ `case_anomaly_lag_2` (502.2) >
    `rolling_std_cases_4w` (214.0) > `current_humidity` (156.8) > `cases_lag_2` (145.4).
  - Stage 2 architecture benchmark (median across 12 trainable validation folds):

    | Architecture | PR-AUC | ROC-AUC | BSS |
    |---|---|---|---|
    | Stage 1 raw | 0.534 | 0.840 | -0.189 |
    | **Isotonic (new winner)** | 0.512 | 0.842 | **0.166** |
    | Platt (M2-002's winner) | 0.534 | 0.840 | 0.145 |
    | Stacked XGBoost | 0.463 | 0.810 | -0.102 |

    **Isotonic regression is now the official Stage 2 architecture** — median BSS 0.166 vs.
    Platt's 0.145, a genuine flip driven entirely by the retuned Stage 1 output distribution
    (nothing about Stage 2 itself changed). Isotonic mildly regresses PR-AUC vs. Stage 1 raw
    (0.534 → 0.512 validation, 0.5577 → 0.5420 holdout) — flagged automatically by
    `compensation_model.py`'s existing PR-AUC-regression check (Decision 022), not blocked,
    since BSS remains the primary selection metric and isotonic's regression is modest.
    Platt, still strictly rank-preserving, keeps PR-AUC/ROC-AUC numerically identical to
    Stage 1 raw on holdout (0.5577/0.9109) but isotonic's holdout BSS (0.320) still slightly
    beats Platt's (0.304) — isotonic's non-parametric flexibility is now a genuine edge, not
    just a tie-breaking artifact, on this retuned probability distribution.
  - Pooled-vs-per-district reconfirmed for Stage 2 too: aggregate pooled BSS **-0.102** vs.
    per-district median **-0.295** (mean -0.625), pooled wins 9/12 folds.

### Interpretation
The holdout-gating discipline did its job: a naive read of the Optuna search's own objective
value would have looked like a big win, but the real, load-bearing evidence is the untouched
holdout improvement (+0.0198 PR-AUC, +0.0131 ROC-AUC) — modest but genuine, and large enough
to change which Stage 2 architecture wins. The Stage 2 architecture flip (Platt → isotonic)
is the most interesting emergent finding: it was not planned or searched for, it fell out
entirely from Stage 1's retuning shifting the shape of the raw probability distribution
isotonic regression's step function is fit against. This is a concrete illustration of why
Decision 022 designed Stage 2 as a *benchmark*, not a single fixed choice — the "right"
calibration method is not an intrinsic property of the problem, it depends on the specific
shape of whatever upstream model is feeding it, which is exactly the kind of coupling a
two-stage architecture needs to keep re-verifying rather than assuming stays fixed.

### Decision
**Adopt** the tuned `XGB_BASE_PARAMS`. **Rerun** Stage 1 and Stage 2 with `--force`,
now the permanent production state. **Accept** isotonic regression as Stage 2's new official
architecture (superseding M2-002's Platt scaling) — its mild PR-AUC regression is within
Decision 022's accepted flag-not-block tolerance and its BSS is genuinely higher. **Proceed**
to the deferred risk-threshold follow-up (M2-004) against this new, current Stage 2 output.

### Documentation Updated
- `research_context/RESEARCH_DECISIONS.md` (new Decision 023; Decision 022's Status/
  Implication corrected to point here).
- `module_2_classification/EXPERIMENT_LOG.md` (this entry; M2-002 marked superseded).
- `module_2_classification/MODULE_CONTEXT.md` (Stage 1/Stage 2 Implementation Status
  sections updated with the new numbers and architecture).
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (tuned-`XGB_BASE_PARAMS` note).
- `research_context/CHANGELOG.md` (new entry).
- New artifacts: `scripts/tune_stage1_xgboost.py`,
  `outputs/metrics/module2/{xgboost_tuning_trials,xgboost_tuning_holdout_comparison}.csv`.
  Regenerated: `data/processed/module2/{baseline_classifier_predictions,
  stage2_compensated_predictions}.csv`, `outputs/metrics/module2/{baseline_classifier_metrics,
  pooled_vs_per_district_comparison,baseline_classifier_feature_importance,
  stage2_compensation_metrics,stage2_pooled_vs_per_district_comparison}.csv`,
  `outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
  `models/module2/{baseline_classifier,stage2_compensation}/*`.

---

## Experiment ID: M2-004

### Date
2026-07-28

### Research Question
Now that Stage 2 produces a genuinely calibrated probability (M2-003: isotonic regression),
what alert threshold and low/medium/high risk-tier boundaries should be applied to it, and do
they actually outperform the naive, explicitly-untuned 0.5 cutoff used throughout Stage 1/2's
own benchmarking?

### Label Definition
Unchanged.

### Data Period
`data/processed/module2/stage2_compensated_predictions.csv` (post-M2-003 rerun). Threshold
SELECTION uses only the official architecture's (isotonic) rows on the validation split
(folds 2-13 — fold 1's `architecture="none"` passthrough is automatically excluded, never
matching the official architecture). The holdout split is excluded from selection and used
only for the final evaluation.

### Stage 1 Model
Unchanged from M2-003 (tuned XGBoost).

### Stage 2 Model
Unchanged from M2-003 (isotonic regression, the official architecture).

### Features Used
N/A — this stage operates purely on `calibrated_probability` and `label`, no new features.

### Class Imbalance Handling
N/A (threshold selection directly accounts for the precision/recall trade-off via F-beta,
not resampling).

### Metrics
`threshold_scan` (new in `evaluate.py`) over 99 cutoffs (0.01-0.99): precision, recall, F1,
**F2** (alert threshold selection), **F0.5** (high-confidence tier selection), accuracy.
Holdout comparison: naive 0.5 vs. selected alert threshold, same metric set.

### Results
- **Selected thresholds** (on 15,600 validation-fold rows, folds 2-13, isotonic only):
  **alert_threshold = 0.170** (F2-optimal), **high_confidence_threshold = 0.570**
  (F0.5-optimal, `>= alert_threshold` as required).
- **Holdout comparison** (2,600 rows, isotonic only — the honest "did this help" check):

  | Threshold | Value | Precision | Recall | F1 | F2 | Accuracy |
  |---|---|---|---|---|---|---|
  | Naive (untuned diagnostic) | 0.50 | 0.708 | 0.399 | 0.510 | 0.437 | 0.945 |
  | **F2-optimal alert** | **0.17** | 0.347 | **0.686** | 0.461 | **0.574** | 0.884 |

  Switching to the F2-optimal threshold nearly **doubles recall** (39.9% → 68.6%) at the
  expected precision cost (70.8% → 34.7%) and improves the F2 score itself (0.437 → 0.574) —
  exactly the trade-off an early-warning system should make: for public health surveillance,
  missing an outbreak is far costlier than an extra false alarm to investigate.
- **Risk-tier empirical separation** (observed outbreak rate per tier — the real evidence
  that "high" genuinely means higher risk, not just an assumption from the threshold values):

  | Split | Low (n) | Low rate | Medium (n) | Medium rate | High (n) | High rate |
  |---|---|---|---|---|---|---|
  | Validation (folds 2-13) | 9,592 | 3.2% | 4,061 | 27.3% | 1,795 | 83.2% |
  | Holdout | 2,228 | 2.6% | 286 | 22.0% | 86 | 76.7% |

  Strong, monotonic separation on BOTH splits, including the untouched holdout — the tiers
  are not an artifact of the selection population.

### Interpretation
The naive 0.5 cutoff was never claimed to be a real decision threshold (it was always
documented as an untuned diagnostic, Decision 021) — this result is the first time Module 2
has an actual, evidence-based operating point. The recall gain is large enough to matter
operationally: at 0.5, roughly 6 in 10 real outbreak weeks in the holdout would have gone
unflagged; at 0.17, that drops to about 3 in 10. The risk-tier rate separation (2.6% → 22.0%
→ 76.7% observed outbreak rate, holdout) is a genuinely strong result for a downstream
early-warning product — a "high" tier week is roughly 30x more likely to be a real outbreak
than a "low" tier week.

### Decision
**Adopt** `alert_threshold = 0.170` and `high_confidence_threshold = 0.570` as Module 2's
production risk-tier thresholds. **Wire** `risk_thresholds.py` into `main.py` as a permanent
pipeline stage (`stage2_risk_thresholds`), unlike M2-003's one-off tuning script. **Resolve**
Decision 022's deferred risk-tier item — Module 2's "Target Direction" ambiguity is now fully
resolved with a concrete, evaluated artifact.

### Documentation Updated
- `research_context/RESEARCH_DECISIONS.md` (new Decision 024).
- `module_2_classification/EXPERIMENT_LOG.md` (this entry).
- `module_2_classification/MODULE_CONTEXT.md` ("Target Direction" and Stage 2 Implementation
  Status updated; deferred risk-tier item resolved).
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (new `risk_thresholds.py` entry).
- `research_context/CHANGELOG.md` (new entry).
- New artifacts: `src/module2_classification/risk_thresholds.py`,
  `data/processed/module2/stage2_risk_tier_predictions.csv`,
  `outputs/metrics/module2/{risk_threshold_scan,risk_threshold_holdout_comparison}.csv`.

---

## Experiment ID: M2-005

### Date
2026-07-28

### Research Question
Open Question #8 (flagged at Decision 019's kickoff, never yet acted on) asked whether the
label's exact-per-(District, Week) `historical_mean`/`historical_sd` estimator was too noisy,
given the audited 18-25%-of-weeks pooled "outbreak" rate — well above WHO/CDC's typical
single-digit-percent epidemic-alert norm. Does pooling information across weeks (via a
week-window or a per-district harmonic seasonal curve) produce a materially less noisy
estimator, and does the specific motivating case (Colombo 2025 Wk15, 277 cases, believed to
be under-flagged) actually reflect a label defect at all?

### Label Definition
**Formula unchanged from Decision 019** (`outbreak = 1 if Number_of_Cases > historical_mean +
k * historical_sd`, strictly-prior-years only). **Estimator changed (Decision 025)**: the
`historical_mean`/`historical_sd` inputs now come from `compute_historical_stats_harmonic`
(1-harmonic per-district OLS regression on week-of-year, refit expanding per year on
strictly-prior real data) instead of Decision 019's exact-per-(District, Week) sample
mean/SD. `k` changed from `2.0` to `3.0` (re-audited for the new estimator, not carried
over). `EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS = 3` unchanged.

### Data Period
Same underlying source as M2-001 through M2-004 (`data/processed/module2/
weekly_modeling_table.csv`, 25,450 rows, 2006-2026) — only the label's estimator changed, not
the input data. `shared`/`module2_preprocessing` stages were not rerun (nothing about them
depends on `labels.py`); `feature_engineering` through `stage2_risk_thresholds` were rerun
with `--force`. Fold structure re-verified, not assumed: still **13** expanding-window annual
walk-forward folds for Stage 1 (`MODULE2_MIN_TRAIN_YEARS=4` unchanged; fold 1 trained on
2,573 pooled rows through fold 13 trained on 18,073 rows, each scoring 1,300 validation rows
— consistent counts with M2-001's original fold-boundary verification), 12 trainable Stage 2
folds (fold 1 no-op passthrough, unchanged from Decision 022).

### Stage 1 Model
Unchanged code/hyperparameters (Decision 023's tuned `XGB_BASE_PARAMS`) — only the label
input changed. Model TYPE selection was rerun, not assumed: Logistic Regression / Random
Forest / XGBoost re-benchmarked against the new label.

### Stage 2 Model
Unchanged code (isotonic / Platt / stacked XGBoost, Decision 022's design) — rerun against
Stage 1's new output under the new label.

### Features Used
Unchanged feature set. `case_anomaly_lag_1/2` (Group M2-5) values themselves changed, since
`feature_engineering.py`'s `compute_case_anomaly_lags` was switched to the same harmonic
estimator as the label (Decision 025), per its existing "reused directly from `labels.py`,
must stay consistent" design.

### Class Imbalance Handling
Unchanged (`class_weight="balanced"` / per-fold `scale_pos_weight`).

### Metrics
Same metric set as M2-001 (Stage 1: PR-AUC primary), M2-002/M2-003 (Stage 2: Brier Skill
Score primary), M2-004 (risk thresholds: F2/F0.5). New audit-specific metrics from
`scripts/audit_label_stabilization.py`: pooled/per-district outbreak prevalence,
undefined-label rate, and an explicit single-row spot-check (Colombo/2025/Week 15).

### Results

**Audit phase** (6 candidate estimators x 3 k values, `outputs/metrics/module2/
label_stabilization_audit.csv`; Colombo spot-check in `label_stabilization_spot_check.csv`):

| Candidate (param) | k | Pooled outbreak % | Undefined % |
|---|---|---|---|
| exact_week (control, Decision 019) | 2.0 | 18.41% | 16.02% |
| windowed (window=3) | 2.0 | 15.51% | 15.14% |
| windowed (window=3) | 2.5 | 12.62% | 15.14% |
| harmonic (n_harmonics=1) | 2.0 | 12.27% | 10.72% |
| harmonic (n_harmonics=1) | 2.5 | 10.03% | 10.72% |
| **harmonic (n_harmonics=1)** | **3.0 (chosen)** | **8.57%** | **10.72%** |
| harmonic (n_harmonics=2) | 3.0 | 8.53%* | 10.72%* |

*2-harmonic results nearly identical to 1-harmonic at every k tested — 1 harmonic kept for
parsimony, not because 2 failed. No district was flagged degenerate (outside [2%, 40%]) for
any candidate/k combination tested.

**Colombo 2025 Week 15 spot-check** (actual = 277 cases) — the motivating example, and the
audit's single most important finding:

| Estimator | historical_mean | historical_sd | threshold | Label |
|---|---|---|---|---|
| exact_week (Decision 019, k=2.0 — the PRE-Decision-025 production value) | 80.9 | 87.7 | 256.4 | **1 (outbreak)** |
| windowed (window=3, k=2.0) | 111.3 | 145.4 | 402.2 | 0 |
| **harmonic (n_harmonics=1, k=3.0 — chosen)** | 165.9 | 209.0 | 792.8 | **0** |

**The motivating claim was disproven, not confirmed**: under the OLD (Decision 019)
estimator, this row's label was already `1` (outbreak) — `277 > 256.4`. Cross-referencing
`stage2_risk_tier_predictions.csv` for this exact row (pre-Decision-025 state) found the
actual issue: Stage 1's raw probability was 0.455, but the official isotonic-calibrated
probability was 0.155, just under the then-current 0.170 alert threshold — tiered "low," no
alert fired, while the non-selected stacked-XGBoost architecture (calibrated probability
0.428) would have tiered it "medium." **This is a Stage 2 calibration/threshold near-miss,
not a label defect.** Adopting harmonic+k=3.0 (chosen for the separate, real aggregate-
prevalence problem) actually FLIPS this specific row's label to `0` — Colombo's harmonic-fit
residual SD (209.0) is much larger than its exact-week SD (87.7), since a single smooth
seasonal curve doesn't capture Colombo's true week-to-week variability well. This trade-off
is accepted (see Decision 025's Reason section for the full justification) but explicitly
NOT presented as fixing the flagship example — it doesn't.

**Window-pooling rejected**: increases `historical_sd` in high-variance districts (more
weeks pooled = more spread captured), raising thresholds rather than stabilizing them —
only modest prevalence reduction (18.4% → 15.5% at window=3, k=2.0) vs. harmonic's 12.3% at
the same k.

**Full pipeline rerun results** (post-adoption, `--force`):

- **Stage 1 model selection FLIPPED to Random Forest** (median validation PR-AUC, 3-model
  benchmark):

  | Model | PR-AUC | ROC-AUC | Precision | Recall | F1 |
  |---|---|---|---|---|---|
  | Logistic Regression | 0.358 | 0.877 | 0.252 | 0.643 | 0.356 |
  | **Random Forest** | **0.377** | 0.901 | 0.367 | 0.548 | 0.440 |
  | XGBoost (Decision 023's tuned params) | 0.373 | 0.914 | 0.283 | 0.723 | 0.406 |

  Holdout (2,600 rows, prevalence now only **1.5%** — ~40 positive rows, since undefined
  labels concentrate in early years and the holdout block itself is 0% undefined): Random
  Forest PR-AUC 0.429/ROC-AUC 0.885 vs. XGBoost 0.424/0.896, Logistic Regression 0.235/0.835.
  **Flagged limitation**: holdout positive-class sample size dropped roughly 5x vs. the old
  label (M2-001's holdout prevalence was 7.2% of 2,600 ≈ 187 positives; now ≈ 40) — holdout
  metrics under the new label carry noticeably more sampling variance and should be read with
  that caveat.
- **Pooled-vs-per-district reconfirmed**: Stage 1 aggregate pooled median PR-AUC 0.373 vs.
  per-district median 0.343 (n=159 district-folds scored) — pooled still wins on the primary
  (median) comparison, though per-district's MEAN (0.421) exceeds pooled's for the first time,
  a mean/median divergence worth noting but not disqualifying (median remains the
  pre-registered selection criterion, Decision 021).
- **Stage 2 architecture unchanged (isotonic)** but now a much closer race: median validation
  BSS isotonic 0.2146 vs. Platt 0.2116 (both up sharply from Decision 023's 0.166/0.145) vs.
  Stage 1 raw's -0.584. Holdout: Platt (0.2344) very slightly edges isotonic (0.2315), but
  isotonic remains selected per the pre-registered validation-fold rule, consistent with prior
  entries' "selection uses validation folds, holdout is a check not a tiebreaker" discipline.
  Stage 2 pooled-vs-per-district reconfirmed (pooled aggregate BSS -0.108 vs. per-district
  median -0.463, n=134 district-folds).
- **Risk thresholds recalibrated lower**, tracking the lower overall prevalence: alert
  threshold 0.170 → **0.140**, high-confidence boundary 0.570 → **0.350**. Holdout: naive 0.5
  gives recall 45.0%/F2 0.459/accuracy 98.5% (the high accuracy reflects the much lower
  prevalence, not improved skill); the new F2-optimal 0.140 threshold gives recall 60.0%/F2
  0.519/accuracy 97.6%. **Not directly comparable to M2-004's 68.6%-recall/0.574-F2 holdout
  figures** — a different, less noisy label target, not a regression.
- **Feature importance dominance unchanged**: `case_anomaly_lag_1` (0.352) and
  `case_anomaly_lag_2` (0.268) remain overwhelmingly the top two features under the new
  official model (Random Forest), together over 60% of total importance — consistent with
  Decision 019's leakage note (conceptually near-identical to the label one week prior), no
  new leakage concern from the estimator change.

### Interpretation
The audit's most valuable output was disconfirming its own motivating premise before any
code was written: the Colombo case was never actually a label bug, it was a Stage 2
calibration near-miss — a materially different, more actionable diagnosis (Stage 2's
threshold/calibration, not Stage 1's target definition, is where that specific class of
miss should be addressed, if at all — no action taken on it this round, flagged as context
for any future Stage 2 revisit). The genuinely real problem — an implausibly high aggregate
"outbreak" prevalence — IS meaningfully improved by harmonic regression (18.4% → 8.6%,
within reach of WHO/CDC's single-digit norm), and this improvement comes with a bonus (lower
undefined-label rate) rather than a trade-off on that axis. The real trade-off is elsewhere:
raising `k` to fix the aggregate rate necessarily also raises the bar for the highest-
variance individual districts (Colombo chief among them), which is why this same
configuration flips the flagship example's label the "wrong" way. This is reported as an
honest limitation of a single global `k`, not smoothed over. The downstream Stage 1 model
flip (XGBoost → Random Forest) and the much smaller holdout positive-class count are further
concrete illustrations that changing a label is not a parameter tweak — it changes what
"correct" means throughout the whole downstream pipeline, consistent with why this decision
required a full end-to-end rerun rather than a partial one.

### Decision
**Adopt** `compute_historical_stats_harmonic` (`n_harmonics=1`) with `k=3.0` as Module 2's
official label estimator (Decision 025). **Keep** the old exact-week estimator in the
codebase for audit/comparison, explicitly marked superseded. **Keep** Random Forest as
Stage 1's official model (new selection, on its own merits under the new label — not simply
because it happened to change). **Keep** isotonic regression as Stage 2's official
architecture (still wins the pre-registered validation-fold comparison, even though the
race with Platt tightened). **Flag, do not implement**, a district-specific or
variance-adaptive `k` as a candidate future refinement to recover sensitivity to genuine
spikes in high-variance districts like Colombo without reopening the aggregate-prevalence
problem this decision fixes.

### Documentation Updated
- `research_context/RESEARCH_DECISIONS.md` (new Decision 025).
- `module_2_classification/EXPERIMENT_LOG.md` (this entry). **M2-001 through M2-004's
  numeric results are superseded** — measured against Decision 019's original label, not the
  current one; their qualitative findings (pooled beats per-district, isotonic/Platt beat
  stacked XGBoost, F-beta thresholds beat naive 0.5) remain valid.
- `module_2_classification/MODULE_CONTEXT.md` (Open Question #8 resolved; Stage 1/Stage 2
  Implementation Status sections refreshed).
- `research_context/FEATURE_ENGINEERING_SPEC.md` (Label Definition section and Group M2-5
  updated to describe the harmonic estimator).
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (`labels.py` entry and status banner
  updated).
- `research_context/CHANGELOG.md` (new entry).
- New artifacts: `scripts/audit_label_stabilization.py`, `outputs/metrics/module2/
  {label_stabilization_audit,label_stabilization_spot_check}.csv`. Regenerated:
  `data/features/module2/stage1_feature_table.csv`, `data/processed/module2/
  {baseline_classifier_predictions,stage2_compensated_predictions,
  stage2_risk_tier_predictions}.csv`, all dependent `outputs/metrics/module2/*` files,
  `outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
  `models/module2/{baseline_classifier,stage2_compensation}/*`.

---

## Experiment ID: M2-006

### Date
2026-07-28

### Research Question
Prompted by a user request to research accuracy-improvement techniques beyond this repo:
literature repeatedly points to SMOTE-family oversampling as effective for imbalanced
outbreak/disease classification. Decision 021 already rejected SMOTE for Stage 1, but on a
reasoning ("blurs the temporal fold boundary") that doesn't precisely describe the real risk
of oversampling lagged features. Given the reasoning needed correcting, is the underlying
conclusion still right? Does leakage-safe SMOTENC (fit only on each fold's own training rows)
actually improve Stage 1 discrimination over the current `class_weight`/`scale_pos_weight`
approach?

### Label Definition
Unchanged - Decision 025's harmonic-regression estimator, `k=3.0`.

### Data Period
Identical 13 walk-forward folds + 2-year holdout as production (`MODULE2_MIN_TRAIN_YEARS=4`).

### Stage 1 Model
Random Forest (official) and XGBoost (runner-up), both benchmarked. Same fixed hyperparameters
as production (`RF_PARAMS`, `XGB_BASE_PARAMS`) - only the training-time
resampling/weighting changed between variants.

### Stage 2 Model
Not touched this round - this experiment is Stage-1-only.

### Features Used
Identical `NUMERIC_FEATURE_COLUMNS` + `District` as production. XGBoost rows in this audit are
median-imputed first (SMOTENC requires no missing values) - a deliberate, flagged departure
from production XGBoost's native-NaN handling, since it only affects this audit's
apples-to-apples-ness for XGBoost, not Random Forest.

### Class Imbalance Handling (the variable under test)
Four variants, both models: `baseline_class_weight` (control, current production),
`smotenc_full_no_weight` (SMOTENC to 1:1 balance, no class weighting),
`smotenc_half_no_weight` (SMOTENC to 50% balance, no class weighting),
`smotenc_half_plus_weight` (SMOTENC to 50% balance, class weighting still applied). SMOTENC
fit strictly on each fold's own training rows post-imputation, `District` passed as a
`categorical_features` column (nearest-neighbor majority vote for synthetic rows' district,
never an invented category).

### Metrics
PR-AUC (primary, Decision 021), ROC-AUC, precision, recall, F1, F2, Brier score - median
across 13 validation folds, plus a holdout check (pre-registered as a check, not a tiebreaker).

### Results
**Random Forest (official model)** - median validation PR-AUC: baseline 0.3766 vs. best SMOTE
variant (`smotenc_half_no_weight`) 0.3862 (+0.0096) - but that gain **evaporates on holdout**
(0.4292 → 0.4290, effectively a wash) and costs holdout recall (0.550 → 0.500). The other two
variants underperform baseline on PR-AUC in both validation AND holdout - clean losses.

**XGBoost** - every SMOTE variant improved median validation PR-AUC (0.383 → 0.397-0.401) but
WORSENED holdout PR-AUC (0.422 → 0.411-0.416) in all three variants - a systematic
validation-improves/holdout-regresses pattern, exactly what a pre-registered holdout check
exists to catch.

**Consistent secondary finding**: nearly every SMOTE variant meaningfully improved raw Brier
score (e.g. Random Forest holdout 0.0273 → 0.0187), i.e. better-calibrated raw probabilities -
but Stage 2 already recalibrates Stage 1's raw probabilities via isotonic regression
regardless of their starting calibration quality, so this benefit is likely mostly redundant
with a correction that already happens downstream.

Full per-fold/per-model/per-variant numbers: `outputs/metrics/module2/smote_imbalance_audit.csv`.

### Interpretation
The literature's general case for SMOTE is real, but this audit finds it does not transfer
cleanly to THIS pipeline's specific feature set: the top two features
(`case_anomaly_lag_1/2`) are lagged/autocorrelated case-anomaly z-scores, and SMOTE's linear
interpolation between two random minority-class rows' feature vectors likely synthesizes
lag/rolling-stat combinations that don't correspond to any real epidemiological trajectory -
consistent with the observed pattern of validation-fold gains that fail to survive the
untouched holdout block. Decision 021's original conclusion (don't use SMOTE) holds up, even
though its original stated reasoning (temporal fold-boundary blurring) was imprecise and has
been corrected here.

### Decision
**Reject** SMOTENC as a Stage 1 imbalance-handling addition (Decision 026). **Keep**
`class_weight="balanced"`/`scale_pos_weight` as the sole imbalance-handling mechanism -
Decision 021 reconfirmed on stronger empirical footing. No production code changed.

### Documentation Updated
- `research_context/RESEARCH_DECISIONS.md` (new Decision 026).
- `module_2_classification/MODULE_CONTEXT.md` (Open Question #4 addendum).
- `research_context/CHANGELOG.md` (new entry).
- New artifacts: `scripts/audit_smote_imbalance.py` (read-only, not wired into `main.py`),
  `outputs/metrics/module2/smote_imbalance_audit.csv`. `requirements.txt` gained
  `imbalanced-learn` (used only by this audit script).
