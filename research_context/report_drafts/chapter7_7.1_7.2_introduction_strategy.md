## 7.1 Introduction

This chapter presents the evaluation design and empirical results for the Residual Compensation Modeling Framework. The purpose is to assess whether residual or error compensation improves upon each module’s Stage 1 baseline under protocols that respect temporal and spatial leakage constraints, and whether the three modules provide complementary decision-support signals rather than redundant ones.

Module 1 is evaluated as a weekly district-level case-forecasting problem. Module 2 is evaluated as a rare-event outbreak-risk classification and calibration problem. Module 3 is evaluated as a district-level spatial hotspot detection and residual-adjustment problem. Across all three modules, Stage 1 establishes a baseline representation of dengue burden, risk, or spatial concentration, while Stage 2 compensates for structured residual error left by that baseline.

A distinction is maintained throughout between research evidence—walk-forward and untouched holdout metrics for Modules 1 and 2, and spatial cross-validation diagnostics for Module 3—and operational outputs such as live or forward dashboard scores, which must not be cited as additional validation evidence. Numerical claims in this chapter are taken from the experiment logs and metric artefacts; operational prototype behaviour remains a weaker evidence tier reserved for demonstration rather than thesis performance claims.

**Approx. word count:** 200 words

---

## 7.2 Evaluation Strategy

### 7.2.1 Common principles

Modules 1 and 2 share a temporally honest evaluation design. Expanding-window walk-forward folds advance by year so that each validation slice uses only earlier training history. A final untouched holdout block of the most recent two years (104 weeks) is reserved for one-shot final scoring and is not used for Stage 1 order selection, Stage 2 architecture choice, or threshold tuning. Random train/test splits are avoided to prevent temporal leakage. Imputed or otherwise untrusted rows are excluded from evaluation targets according to each module’s preprocessing rules.

Module 3 answers a spatial rather than temporal research question and therefore uses a different validation axis. Districts are partitioned by spatial K-means clustering on centroids so that whole districts remain together within folds. This prevents the residual model from learning held-out-district behaviour through near-neighbour leakage that would occur under random district-week row splits. The absence of a Module 1/2-style temporal holdout for Module 3 is intentional and must be stated when interpreting spatial results.

Across the framework, research artefacts (validated prediction tables, metrics, and figures) are kept separate from operational refresh products consumed by the Streamlit dashboard. Regenerating live or forward scores must not silently overwrite frozen research evidence.

### 7.2.2 Module 1 metrics and protocol

Primary forecasting metrics include MAE, RMSE, sMAPE, and MASE scaled to a seasonal-naive benchmark with seasonal period `m = 52`. Stage 1 (SARIMA only) is compared with Stage 1 + Stage 2 (SARIMA plus XGBoost residual compensation). Additional diagnostics include Diebold–Mariano tests of Stage 1 versus Stage 1+2 loss differentials, residual variance reduction, and Ljung–Box checks on post-compensation residuals. MASE below 1 indicates improvement relative to the seasonal-naive benchmark. The primary compensation claim uses the regenerated pipeline after Stage 1 stationarity safeguards; production-stack refinements are reported separately so that feature-set updates are not confused with the residual-compensation effect itself.

### 7.2.3 Module 2 metrics and protocol

Because outbreak weeks are rare, PR-AUC is the primary Stage 1 discrimination metric; accuracy alone is not treated as decisive. Stage 2 is selected primarily by Brier Skill Score (BSS), which measures calibration relative to a base-rate forecast. Alert utility is summarised using recall, precision, and F2 at a fixed absolute probability threshold selected on validation folds only. Risk-tier quality is checked by observed outbreak rates within low, medium, and high bands defined by absolute calibrated-probability boundaries. Under the current harmonic epidemic label, holdout prevalence is low, so holdout metrics are interpreted with sampling-variance caution and are not compared directly to superseded pre–label-change numbers.

### 7.2.4 Module 3 metrics and protocol

Stage 1 spatial validity is assessed using Global Moran’s I with queen-contiguity weights on the KDE baseline surface, reported both as an aggregated district summary and as selected weekly checks. Stage 2 residual prediction quality is assessed by out-of-fold MAE and RMSE under five-fold spatial K-means cross-validation. Convergence of the iterative risk update is checked by a dual criterion on maximum risk-value change and residual Moran’s I significance, under the adopted shrinkage factor α = 0.05. Aggregate case-fit of the rescaled Stage 1 baseline versus the converged Stage 2 Risk surface is compared using correlation, MAE, and RMSE against actual district-week cases. This last comparison is reported honestly even when Stage 2 does not improve fit.

### 7.2.5 Scope boundaries

Operational forward forecasts and live risk scores are not treated as holdout-equivalent evidence. Cross-study “best model” claims are avoided; results are interpreted relative to each module’s own baselines and ablations. Module 3 spatial metrics are not reframed as temporal forecasting skill. Alert and risk-tier thresholds reported for Module 2 are those selected under the current label (τ = 0.14; high-confidence boundary 0.35) and must not be mixed with superseded thresholds from earlier label definitions. Figure 7.1 summarises the evaluation protocol and evidence-tier separation.

[Insert Figure 7.1 here]

**Figure 7.1: Evaluation protocol schematic showing walk-forward folds and holdout for Modules 1 and 2, spatial cross-validation for Module 3, and separation of research versus operational evidence**

**Approx. word count:** 560 words

**Notes for Team:**
- Standalone file: `research_context/report_drafts/chapter7_7.1_7.2_introduction_strategy.md`
- Combined chapter: `research_context/report_drafts/chapter7_evaluation.md`
- Figure 7.1 draw.io/PNG still pending — protocol schematic only (no fabricated metrics)
- No result tables in 7.2; metrics definitions only
- Transition: next topic is **7.3 Module 1** (+ Tables 7.1–7.2, Figures 7.2–7.3)
