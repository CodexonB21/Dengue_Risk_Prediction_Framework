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
