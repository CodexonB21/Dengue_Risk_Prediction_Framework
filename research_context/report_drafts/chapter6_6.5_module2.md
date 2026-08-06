# Chapter 6 — Section 6.5 Module 2 Implementation (+ Figure 6.3)

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 6.4 Module 1 (+ Figure 6.2)  
**Next topic:** 6.6 Implementation of Module 3 (+ Figure 6.4)  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

## 6.5 Implementation of Module 2: Hybrid Outbreak Risk Classification

Module 2 was implemented on the same shared epidemiological and climate base tables as Module 1, but with Module 2–specific preprocessing, fold-aware epidemic-threshold labelling, Stage 1 Random Forest classification, and Stage 2 isotonic probability calibration. The module predicts outbreak risk rather than exact case counts. Graded early-warning communication is obtained from calibrated probabilities through fixed absolute thresholds (`alert_flag` and `risk_tier`), not by treating a separate multi-class label as the primary modelling target.

Figure 6.3 summarises the Module 2 implementation path from preprocessing and labelling through calibrated alerts.

**[Insert Figure 6.3 here]**

**Figure 6.3:** Implementation pipeline of Module 2 — Hybrid Outbreak Risk Classification (Module 2 preprocessing → epidemic-threshold labels → Random Forest → isotonic calibration → alert / risk tier).

### 6.5.1 Module 2 Preprocessing and Label Construction

Module 2 begins from the same shared tables as Module 1 but applies Decision 020’s independent temporal policy. Week 53 is retained as its own district-week row rather than merged into week 52, because merging would sum two real weeks before threshold comparison and would contaminate week-52 historical statistics across all years. Missing weeks are still seasonal-naive imputed for lag alignment, but every imputed row is masked to missing before case-derived features and labels are computed, preventing fabricated seasonal-naive values from flowing into neighbouring weeks’ lags or rolling statistics. Weekly climate is joined from the shared table; `weather_code` is excluded from model features by default. Leakage-prone columns such as contemporaneous `Number_of_Cases` and `cases_per_100k` are excluded from the model feature matrix.

Outbreak labels follow a binary epidemic-threshold definition:

```text
outbreak = 1 if Number_of_Cases > historical_mean + k × historical_SD
```

Historical mean and standard deviation are estimated from a per-district harmonic seasonal curve fitted only on strictly prior years, with `k = 3.0` after re-audit for that estimator (Decision 025). Rows lacking sufficient prior history receive undefined labels and are excluded from training and scoring rather than defaulted to non-outbreak. Synthetic oversampling methods such as SMOTE were audited and rejected for production (Decision 026), so class imbalance is handled through model weights rather than fabricated minority samples that could interpolate implausible lag combinations across a temporal split.

### 6.5.2 Stage 1: Pooled Random Forest Classifier

Stage 1 benchmarks candidate classifiers under walk-forward evaluation and, after label re-estimation, selects a pooled Random Forest with `District` encoded as a categorical feature (Decision 025). Unlike Module 1 Stage 1, Module 2 Stage 1 includes climate: lagged precipitation, temperature, and humidity; current-week climate; and fold-aware climate anomalies recomputed from each fold’s training window. Case-trend features, seasonal encodings, monsoon indicators, and lagged case-seasonal anomalies complete the feature matrix. Class-weight balancing is applied for Random Forest, and a Module 2–specific minimum training depth (`MIN_TRAIN_YEARS`) is used because the label’s own prior-history requirement would otherwise leave the first fold without trainable defined labels. Median imputation and District encoding for models that cannot handle missing values natively are fitted on each fold’s training rows only. Raw `Year` and current-week case count / incidence are excluded to prevent trivial label leakage or exploitation of the walk-forward split structure.

### 6.5.3 Stage 2: Isotonic Calibration and Risk Tiers

Stage 2 does not regress a literal `label − predicted_probability` residual, which is statistically ill-posed for a binary target. Instead, well-posed calibration architectures were benchmarked—isotonic regression, Platt scaling, and stacked contextual correction—and isotonic regression on the Stage 1 predicted probability was selected as the official compensation stage. In functional terms, Stage 2 learns a monotone mapping

```text
calibrated_probability = g(predicted_probability)
```

where `g` is the fitted isotonic calibrator trained only on prior out-of-sample Stage 1 probabilities. From the calibrated probability, the pipeline derives a binary `alert_flag` and a nested `risk_tier` (`low` / `medium` / `high`) using fixed absolute probability thresholds selected on validation folds only. Exact threshold values and their holdout operating characteristics are reported in Chapter 7. Quantile-based tiers were rejected because they would force a constant fraction of high-risk weeks irrespective of epidemic conditions once probabilities are calibrated. Reliability diagrams and threshold-scan tables are persisted so that alert behaviour remains auditable without re-fitting.

### 6.5.4 Training Protocol and Artefacts

Module 2 uses expanding-window walk-forward folds plus a final two-year holdout, with fold generation adapted to the higher minimum training depth required by label history. Stage 2 fold `k` trains only on official Stage 1 out-of-sample probabilities from earlier folds, with fold 1 treated as a documented passthrough when no prior out-of-sample probabilities yet exist. Pipeline artefacts include the Module 2 weekly modelling table, Stage 1 feature table, baseline classifier predictions and models, Stage 2 compensated predictions and calibrators, risk-tier prediction tables, threshold-scan metrics, reliability diagrams, and separate live and forward operational scoring outputs tagged as operational evidence.

Training and holdout evaluation remain independent of Module 1 forecasts; Module 1 case forecasts are used only in operational forward-risk feature assembly beyond the last observed case week. Live scoring recomputes features for recent weeks through frozen Stage 1 and Stage 2 artefacts without rewriting the validated prediction tables. As illustrated in Figure 6.3, validated research scoring is separated from operational live/forward scoring scripts that consume frozen production models without altering holdout evidence. Classification performance metrics themselves are deferred to Chapter 7.

**Approx. word count:** 900 words

**Suggested Figure:**
Figure 6.3: Module 2 implementation pipeline.  
Asset: `research_context/report_drafts/diagrams/figure_6_3_module2_implementation.png` (adapted from Figure 5.4; Word caption = 6.3).

**Notes for Team:**
- Stage 1 = Random Forest (Decision 025), not the pre-Decision-025 XGBoost selection.
- Stage 2 = isotonic calibration, not climate-anomaly residual ML.
- No SMOTE in production; climate is included in Stage 1.
- Keep numeric alert/tier thresholds for Chapter 7.
- Next: **6.6 Module 3 (+ Figure 6.4)**.
