## 7.4 Module 2: Outbreak Classification Evaluation

### 7.4.1 Experimental setup and outbreak labelling

Module 2 uses fold-aware epidemic-threshold labels under the harmonic seasonal estimator with `k = 3.0` (Decision 025). Evaluation uses 13 walk-forward folds with a four-year minimum training depth, plus a two-year holdout block of 2,600 district-weeks. Under the current label, holdout outbreak prevalence is approximately 1.5% (about 40 positive rows), so holdout metrics carry higher sampling variance than under earlier, superseded label definitions and are not directly comparable to pre–Decision-025 numbers. Stage 2 fold `k` trains only on official Stage 1 out-of-sample probabilities from earlier folds.

### 7.4.2 Stage 1 discrimination

After label re-estimation, Stage 1 model selection favoured Random Forest over Logistic Regression and XGBoost by median validation PR-AUC.

**Table 7.3: Stage 1 model comparison under the current harmonic label**

| Model | Median validation PR-AUC (13 folds) |
|---|---|
| Logistic Regression | 0.358 |
| XGBoost (tuned params) | 0.373 |
| Random Forest (selected) | 0.377 |

On the untouched holdout block, Random Forest achieved PR-AUC = 0.429, ROC-AUC = 0.885, and Brier score = 0.027. Pooled modelling continued to outperform per-district modelling on the pre-registered median PR-AUC comparison. Case-anomaly lags dominate feature importance, consistent with a label that encodes recent seasonal exceedance. This is documented as an expected near-label signal rather than an accidental leakage of current-week cases. The modest validation PR-AUC gaps among tree models are less important than the consistent finding that Stage 1 can rank rare outbreak weeks far above chance under a prevalence-sensitive metric.

### 7.4.3 Stage 2 calibration compensation

Stage 1 raw probabilities are poorly calibrated relative to base-rate forecasts, motivating Stage 2. Under the current label and official Stage 1 model, three Stage 2 architectures were re-benchmarked. Isotonic regression remains the official Stage 2 method by median validation BSS.

**Table 7.4: Stage 2 architecture comparison, alert utility, and risk-tier rates**

| Architecture | Median validation BSS | Holdout BSS (check) |
|---|---|---|
| Stage 1 raw | −0.584 | — |
| Stacked XGBoost | −0.108 | — |
| Platt scaling | 0.2116 | 0.2344 |
| Isotonic (selected) | 0.2146 | 0.2315 |

| Alert rule (holdout) | Recall | Precision | F2 | Accuracy |
|---|---|---|---|---|
| Naive cutoff 0.5 | 45.0% | — | 0.459 | 98.5% |
| F2-optimal τ = 0.14 | 60.0% | 33.8% | 0.519 | 97.6% |

| Risk tier | Validation outbreak rate (folds 2–13) | Holdout outbreak rate |
|---|---|---|
| Low | 1.3% | 0.6% |
| Medium | 26.2% | 13.3% |
| High | 71.1% | 48.8% |

Isotonic mildly reduces holdout PR-AUC relative to Stage 1 raw in some write-ups; production confirmation lists isotonic holdout PR-AUC 0.412. BSS remains the Stage 2 selection metric; discrimination is primarily a Stage 1 responsibility. As shown in Figure 7.4, Stage 1 raw probabilities lie systematically off the perfect-calibration diagonal, whereas isotonic Stage 2 moves predicted probabilities closer to observed outbreak rates on the Stage 2–trained validation folds. The holdout panel is noisier because only about forty positive labels are available, so it is interpreted as a secondary check rather than as a finely resolved calibration curve. The large negative BSS of Stage 1 raw probabilities remains the clearest justification for treating Module 2 Stage 2 as calibration compensation rather than as a second ranking model.

### 7.4.4 Alert thresholds and risk tiers

Validation-selected absolute thresholds under the current label are an alert threshold τ = 0.14 (F2-oriented) and a high-confidence boundary of 0.35 (F0.5-oriented). At τ = 0.14, holdout recall rises from 45.0% under a naive 0.5 cutoff to 60.0%, with precision 33.8% and F2 = 0.519. High accuracy under the naive cutoff largely reflects low prevalence and should not be over-interpreted as outbreak-detection skill. Observed outbreak rates by risk tier remain ordered on both validation and holdout splits, indicating that the calibrated probability bands retain monotonic risk separation even under sparse holdout positives.

### 7.4.5 Rejected ablations

Several alternatives were tested and not adopted for production. SMOTENC oversampling (M2-006) failed to improve holdout PR-AUC despite validation gains. Logit-space residual correction (M2-007A) did not beat isotonic. A climate-free Stage 1 with climate-stacked Stage 2 intended to mimic Module 1’s residual pattern (M2-008) was rejected because stacked BSS remained weaker than the production calibrator. Module 1 forecast features in a tree Stage 2 (M2-007D) showed some ranking signal but were not promoted over isotonic. These negatives are academically useful: they show that Module 2’s accepted Stage 2 form is probability calibration, not a forced copy of Module 1’s additive residual regressor.

[Insert Figure 7.4 here]
*(PNG: `research_context/report_drafts/diagrams/figure_7_4_module2_reliability.png`)*

**Figure 7.4: Module 2 reliability diagrams comparing Stage 1 raw probabilities with isotonic Stage 2 calibration (validation and holdout)**

**Approx. word count:** 950 words

**Notes for Team:**
- Standalone: `research_context/report_drafts/chapter7_7.4_module2.md`
- Figure 7.4 regenerated from `stage2_compensated_predictions.csv` with **isotonic** (do not paste older `reliability_diagram_*.png` labelled Platt)
- Thresholds: τ = 0.14 / high = 0.35 only (post–Decision 025)
- Holdout reliability panel is sparse (~40 positives) — interpret cautiously in viva
- Transition: next topic is **7.5 Module 3** (+ Tables 7.5–7.6, Figure 7.5)
