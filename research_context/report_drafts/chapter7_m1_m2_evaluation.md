# Chapter 7 Draft — Module 1 and Module 2 Evaluation

**Source of truth:** `module_1_forecasting/EXPERIMENT_LOG.md`, `module_2_classification/EXPERIMENT_LOG.md`, module contexts, `RESEARCH_DECISIONS.md`  
**Scope:** Evaluation strategy + Module 1/2 results only (Module 3 deferred)  
**Status:** Draft for Word paste (replaces interim Chapter 7 “Discussion / Current Progress”)  
**Last updated:** 2026-07-29

**Evidence rule:** Only documented experiment metrics are used. Operational/live/forward dashboard outputs are **not** mixed into holdout skill claims.

**Important consistency note for earlier drafts:**  
After Decision 025 / M2-005, Module 2 Stage 1’s official model is **Random Forest** (not XGBoost). Chapters 4.2.2 / 5.3.2 / 6.3.2 drafts written earlier still say XGBoost and should be corrected when pasting.

---

## 7.1 Introduction

This chapter presents the evaluation design and empirical results for the forecasting and outbreak-classification components of the Residual Compensation Modeling Framework. The purpose is to assess whether residual/error compensation improves upon the corresponding baseline models under temporally valid protocols, and whether Module 1 and Module 2 provide complementary decision-support signals.

Module 1 is evaluated as a weekly case-forecasting problem. Module 2 is evaluated as a rare-event outbreak-risk classification and calibration problem. Module 3 spatial hotspot evaluation is deferred until that module’s implementation is complete.

A distinction is maintained throughout between:

- **research evidence** — walk-forward and untouched holdout metrics from the experiment logs; and
- **operational outputs** — live or forward dashboard scores, which must not be cited as additional validation evidence.

---

## 7.2 Evaluation Strategy

### 7.2.1 Common principles

Both modules use expanding-window walk-forward evaluation by year and reserve a final untouched holdout block of the most recent two years. Random train/test splits are avoided to prevent temporal leakage. Imputed or otherwise untrusted rows are excluded from evaluation targets according to each module’s preprocessing rules.

### 7.2.2 Module 1 metrics

Primary forecasting metrics include MAE, RMSE, sMAPE, and MASE (seasonal-naive scale, `m = 52`). Stage 1 (SARIMA only) is compared with Stage 1 + Stage 2 (SARIMA + XGBoost residual compensation). Additional diagnostics include:

- Diebold–Mariano (DM) tests of Stage 1 versus Stage 1+2 loss differentials
- residual variance reduction
- Ljung–Box checks on post-compensation residuals

MASE below 1 indicates improvement relative to a seasonal-naive benchmark.

### 7.2.3 Module 2 metrics

Because outbreak weeks are rare, **PR-AUC** is the primary Stage 1 discrimination metric; accuracy alone is not treated as decisive. Stage 2 is selected primarily by **Brier Skill Score (BSS)**, which measures calibration relative to a base-rate forecast. Alert utility is summarised using recall, precision, and F2 at a fixed absolute probability threshold selected on validation folds only. Risk-tier quality is checked by observed outbreak rates within `low` / `medium` / `high` bands.

### 7.2.4 What is not claimed here

- Operational forward forecasts and live risk scores are not treated as holdout-equivalent evidence.
- Module 3 spatial metrics are omitted pending completion.
- Cross-study “best model” claims are avoided; results are interpreted relative to each module’s own baselines and ablations.

**Suggested Figure:**  
Figure 7.X: Evaluation protocol schematic (walk-forward folds + holdout; research vs operational evidence tiers).

---

## 7.3 Module 1: Forecasting Evaluation

### 7.3.1 Experimental setup

Module 1 Stage 1 fits per-district SARIMA models on weekly case counts only. Stage 2 predicts the SARIMA residual with a pooled XGBoost regressor using case-lag, climate-lag/anomaly, seasonal, and residual-lag features. Evaluation uses 14 walk-forward folds plus a 104-week holdout block per district. The core residual-compensation comparison reported below corresponds to the regenerated pipeline after Stage 1 stationarity safeguards (Decision 017 / experiment M1-003). The current production stack additionally includes reporting-delay features promoted under Decision 030 / M1-006B.

### 7.3.2 Residual compensation benefit (Stage 1 vs Stage 1+2)

Across all 25 districts, Stage 1+2 improved validation-aggregate MASE for **25/25** districts relative to Stage 1 only. On the untouched holdout block, **23/25** districts improved. The two holdout exceptions were Kilinochchi and Mannar; neither showed a statistically significant worsening under the DM test.

Headline median improvements across districts:

| Scope | Median MASE improvement (Stage 1 → Stage 1+2) | Districts improved |
|---|---|---|
| Validation aggregate | **43.5%** | 25/25 |
| Holdout | **32.7%** | 23/25 |

Median absolute holdout MASE moved from approximately **0.622** (Stage 1) to approximately **0.375** (Stage 1+2) in the Decision 017 regenerated comparison. Selected district examples from the same table include strong holdout gains for Colombo (0.65 → 0.32), Gampaha (0.74 → 0.35), and Batticaloa (0.59 → 0.25), alongside limited or negative holdout movement for Kilinochchi and Mannar.

**Suggested Table:**  
Table 7.X: Per-district Stage 1 vs Stage 1+2 MASE (validation and holdout) — paste from `MODULE_CONTEXT.md` Stage 2 results table / `combined_vs_baseline_metrics.csv`.

### 7.3.3 Statistical significance

At the pooled `validation_and_holdout` DM scope, **14/25** districts showed Stage 2 significantly better than Stage 1 (`p < 0.05`). At the stricter `holdout_only` scope, **5/25** districts reached significance. No district showed a statistically significant worsening at either scope. This pattern is interpreted honestly: residual compensation is directionally beneficial and often material, but universal statistical significance is not claimed at the per-district holdout sample size (`n = 104` weeks).

### 7.3.4 Current production stack (M1-006B)

After promotion of reporting-delay / nowcasting-state features (M1-006B; Decision 030), the default production path achieved:

| Metric (holdout) | Pre-promotion | Post-promotion (current) |
|---|---|---|
| Median MASE | 0.386 | **0.374** |
| Median sMAPE | 35.0% | **34.2%** |
| Districts improved (MASE vs prior stack) | — | **22/25** |

These figures refine the production feature set on top of the residual-compensation architecture; they do not replace the Stage 1 vs Stage 1+2 comparison as the primary evidence that compensation itself helps.

### 7.3.5 Interpretation and limits

Residual compensation substantially reduces average forecast error relative to SARIMA alone for most districts. Remaining structure in residuals (Ljung–Box still significant for many districts) indicates that Stage 2 reduces error magnitude without fully whitening residuals. Extreme catch-up weeks associated with suspected reporting dynamics remain difficult; rolling one-step evaluation can improve near-term outbreak-week error relative to a flat multi-step holdout block, but flat holdout MASE remains the primary validated backtest evidence.

**Suggested Figures:**  
Figure 7.X: Example actual vs Stage 1 vs Stage 1+2 forecasts (e.g. Colombo / Gampaha).  
Figure 7.X: District-level holdout MASE comparison (Stage 1 vs Stage 1+2).

**Notes for Team:**
- Prefer citing M1-003 / Decision 017 for the compensation claim; cite M1-006B only as production refinement.
- Do not quote forward-forecast CSVs as holdout skill.
- Full per-district table should be included or placed in an appendix if too large for the main chapter.

---

## 7.4 Module 2: Outbreak Classification Evaluation

### 7.4.1 Experimental setup

Module 2 uses fold-aware epidemic-threshold labels under the harmonic seasonal estimator (`k = 3.0`; Decision 025). Evaluation uses 13 walk-forward folds (`MODULE2_MIN_TRAIN_YEARS = 4`) plus a two-year holdout block (2,600 district-weeks). Under the current label, holdout outbreak prevalence is approximately **1.5%** (about 40 positive rows), so holdout metrics carry higher sampling variance than under earlier, superseded label definitions and are not directly comparable to pre-Decision-025 numbers.

### 7.4.2 Stage 1 discrimination

After label re-estimation, Stage 1 model selection favoured **Random Forest** over Logistic Regression and XGBoost by median validation PR-AUC:

| Model | Median validation PR-AUC (13 folds) |
|---|---|
| Logistic Regression | 0.358 |
| XGBoost (tuned params) | 0.373 |
| **Random Forest (selected)** | **0.377** |

On the untouched holdout block, Random Forest achieved **PR-AUC = 0.429**, **ROC-AUC = 0.885**, and Brier score = 0.027. Pooled modelling continued to outperform per-district modelling on the pre-registered median PR-AUC comparison.

Case-anomaly lags dominate feature importance, consistent with a label that encodes recent seasonal exceedance. This is documented as an expected near-label signal rather than an accidental leakage of current-week cases.

### 7.4.3 Stage 2 calibration compensation

Stage 1 raw probabilities are poorly calibrated relative to base-rate forecasts (negative BSS in many folds historically), motivating Stage 2. Under the current label and official Stage 1 model, three Stage 2 architectures were re-benchmarked. **Isotonic regression** remains the official Stage 2 method by median validation BSS:

| Architecture | Median validation BSS | Holdout BSS (check) |
|---|---|---|
| Stage 1 raw | −0.584 | — |
| Stacked XGBoost | −0.108 | — |
| Platt scaling | 0.2116 | 0.2344 |
| **Isotonic (selected)** | **0.2146** | 0.2315 |

Isotonic mildly reduces holdout PR-AUC relative to Stage 1 raw (approximately 0.390 vs 0.410 in the M2-005 write-up; production confirmation lists isotonic holdout PR-AUC **0.412**). BSS remains the Stage 2 selection metric; discrimination is primarily a Stage 1 responsibility.

Reliability diagrams show Stage 1 overconfidence corrected toward the diagonal after isotonic calibration.

### 7.4.4 Alert threshold and risk tiers

Validation-selected absolute thresholds under the current label are:

- alert threshold **τ = 0.14** (F2-oriented)
- high-confidence boundary **0.35** (F0.5-oriented)

Holdout alert performance at τ = 0.14:

| Rule | Recall | Precision | F2 | Accuracy |
|---|---|---|---|---|
| Naive cutoff 0.5 | 45.0% | — | 0.459 | 98.5% |
| **F2-optimal τ = 0.14** | **60.0%** | **33.8%** | **0.519** | 97.6% |

Observed outbreak rates by risk tier remain ordered:

| Split | Low | Medium | High |
|---|---|---|---|
| Validation (folds 2–13) | 1.3% | 26.2% | 71.1% |
| Holdout | 0.6% | 13.3% | 48.8% |

High accuracy under the naive cutoff largely reflects low prevalence and should not be over-interpreted as outbreak-detection skill.

### 7.4.5 Negative / rejected ablations (summary)

Several alternatives were tested and **not** adopted for production:

| Experiment | Claim tested | Outcome |
|---|---|---|
| M2-006 | SMOTE-family oversampling improves Stage 1 | Rejected (holdout PR-AUC wash/regression) |
| M2-007A | Logit-space residual correction beats isotonic | Rejected |
| M2-008 | Climate-free Stage 1 + climate stacked Stage 2 (Module 1–symmetric) | Rejected (stacked BSS negative; does not beat production) |
| M2-007D | Module 1 forecast features in tree Stage 2 | Ranking signal present; official Stage 2 kept as isotonic |

These negatives are academically useful: they show that Module 2’s accepted Stage 2 form is probability calibration, not a forced copy of Module 1’s additive residual regressor.

**Suggested Figures:**  
Figure 7.X: Reliability diagrams (Stage 1 raw vs isotonic; validation/holdout).  
Figure 7.X: PR curves or threshold-scan summary for alert selection.

**Suggested Table:**  
Table 7.X: Stage 1 model comparison and Stage 2 architecture comparison (current label).

---

## 7.5 Comparative Analysis: Are Modules 1 and 2 Redundant?

Experiment **M2-009** tested whether Module 2 is unnecessary given Module 1 case forecasts, by comparing Module 2 alerts with thresholding Module 1’s `final_prediction` on the same holdout block and outbreak label.

| Rule (holdout, 40 outbreaks / 2,600 rows) | PR-AUC | Recall | Precision | F2 |
|---|---|---|---|---|
| **Module 2 production (τ = 0.14)** | **0.412** | **0.600** | 0.338 | **0.519** |
| Module 1 forecast > epidemic threshold | 0.063 | 0.225 | 0.563 | 0.256 |
| Module 1 excess score (pred − threshold) | 0.280 | 0.225 | 0.563 | 0.256 |
| Module 1 forecast > 100 (naive) | 0.063 | 0.500 | 0.073 | 0.231 |
| Oracle: actual > threshold | 0.302 | 1.000 | 1.000 | 1.000 |

Module 2 captured **15** true outbreaks missed by the fair Module 1–threshold rule; the reverse set was empty. Forecasting case magnitude and detecting relative epidemic exceedance are therefore empirically separable tasks under this protocol. Module 1 remains the quantification layer; Module 2 remains the outbreak-alert layer.

**Suggested Figure:**  
Figure 7.X: Side-by-side alert comparison (M2 vs M1-threshold) on holdout.

---

## 7.6 Discussion of Module 1/2 Results

The Module 1 results support the residual-compensation hypothesis for weekly case forecasting: a climate-aware second stage reduces error left by a climate-free SARIMA baseline for most districts, with honest exceptions and incomplete residual whitening. The Module 2 results support a related but distinct claim: baseline outbreak ranking can be strong while raw probabilities remain poorly calibrated, so Stage 2 compensation is best realised as isotonic recalibration rather than an additive residual regressor. Cross-module comparison further justifies retaining both modules.

Key limitations that should be stated in the report:

1. District-level aggregation cannot capture sub-district heterogeneity.
2. Climate inputs are point samples per district (Open-Meteo), not spatial averages.
3. Module 2 holdout positives are sparse under the current label (~1.5% prevalence).
4. Some districts remain difficult for forecasting (e.g. sparse or volatile series).
5. Operational live/forward outputs are useful for demonstration but are a weaker evidence tier than holdout evaluation.
6. Module 3 evaluation is not yet available.

**Notes for Team:**
- Replace the entire interim Chapter 7 progress narrative with this evaluation structure.
- When citing numbers orally in viva, prefer one “headline card” per module:
  - M1: 23/25 holdout districts improved; median ~33% MASE reduction from compensation; production median holdout MASE 0.374
  - M2: RF Stage 1 holdout PR-AUC 0.429; isotonic Stage 2; alert recall 0.60 @ τ=0.14; M2-009 beats M1-threshold alerting
- Update Chapters 4–6 Module 2 Stage 1 model name to Random Forest before final Word freeze.
- Leave a Module 3 subsection placeholder only.

---

## 7.7 Summary

This chapter evaluated Modules 1 and 2 under walk-forward and holdout protocols. Module 1’s residual compensation improved case-forecast MASE for most districts relative to SARIMA alone. Module 2’s calibrated classifier provided outbreak-alert performance that cannot be recovered by simply thresholding Module 1 forecasts. Together, the results support a multidimensional residual-compensation framework in which forecasting magnitude and classifying outbreak risk remain complementary tasks. Spatial hotspot evaluation will be reported once Module 3 is complete.

---

## Optional subsection stub (do not invent results)

### 7.X Module 3: Spatial Hotspot Evaluation

```text
[Module 3 — to be updated after Stage 1/2 completion and experiment logging]
```

---

## Paste checklist for Word

- [ ] Retitle interim Chapter 7 from “Discussion” to “Evaluation and Results” (or department-required equivalent)
- [ ] Insert tables/figures from `outputs/metrics/` and `outputs/figures/` rather than typing fragile decimals by hand where possible
- [ ] Fix Module 2 Stage 1 = Random Forest in Chapters 4–6 drafts
- [ ] Keep research vs operational evidence language consistent with the dashboard guide
- [ ] Strip Notes for Team before submission
