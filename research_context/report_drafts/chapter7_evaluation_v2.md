# Chapter 7 — Evaluation and Results

**Source of truth:** `module_1_forecasting/EXPERIMENT_LOG.md`, `module_2_classification/EXPERIMENT_LOG.md`, `module_3_spatial/EXPERIMENT_LOG.md`, module contexts, `RESEARCH_DECISIONS.md`, `outputs/metrics/`
**Scope:** Full three-module evaluation (7.1–7.8)
**Status:** Paste-ready draft (accepted structure 2026-07-30; Module 2 sections refreshed 2026-08-06 after Decision 047/M2-013)
**Last updated:** 2026-08-06

**Evidence rule:** Only documented experiment metrics are used. Operational/live/forward dashboard outputs are **not** mixed into holdout skill claims.

**Figures:** Planned as Figures 7.1–7.5 (PNG export from `outputs/` / draw.io pending).
**Tables:** Tables 7.1–7.6 embedded below.

---

## 7.1 Introduction

This chapter presents the evaluation design and empirical results for the Residual Compensation Modeling Framework. The purpose is to assess whether residual or error compensation improves upon each module's Stage 1 baseline under protocols that respect temporal and spatial leakage constraints, and whether the three modules provide complementary decision-support signals rather than redundant ones.

Module 1 is evaluated as a weekly district-level case-forecasting problem. Module 2 is evaluated as a rare-event outbreak-risk classification and calibration problem. Module 3 is evaluated as a district-level spatial hotspot detection and residual-adjustment problem. Across all three modules, Stage 1 establishes a baseline representation of dengue burden, risk, or spatial concentration, while Stage 2 compensates for structured residual error left by that baseline.

A distinction is maintained throughout between research evidence—walk-forward and untouched holdout metrics for Modules 1 and 2, and spatial cross-validation diagnostics for Module 3—and operational outputs such as live or forward dashboard scores, which must not be cited as additional validation evidence. Numerical claims in this chapter are taken from the experiment logs and metric artefacts; operational prototype behaviour remains a weaker evidence tier reserved for demonstration rather than thesis performance claims.

**Approx. word count:** 200 words

---

## 7.2 Evaluation Strategy

### 7.2.1 Common principles

Modules 1 and 2 share a temporally honest evaluation design. Expanding-window walk-forward folds advance by year so that each validation slice uses only earlier training history. A final untouched holdout block of the most recent two years (104 weeks) is reserved for one-shot final scoring and is not used for Stage 1 order selection, Stage 2 architecture choice, or threshold tuning. Random train/test splits are avoided to prevent temporal leakage. Imputed or otherwise untrusted rows are excluded from evaluation targets according to each module's preprocessing rules.

Module 3 answers a spatial rather than temporal research question and therefore uses a different validation axis. Districts are partitioned by spatial K-means clustering on centroids so that whole districts remain together within folds. This prevents the residual model from learning held-out-district behaviour through near-neighbour leakage that would occur under random district-week row splits. The absence of a Module 1/2-style temporal holdout for Module 3 is intentional and must be stated when interpreting spatial results.

Across the framework, research artefacts (validated prediction tables, metrics, and figures) are kept separate from operational refresh products consumed by the Streamlit dashboard. Regenerating live or forward scores must not silently overwrite frozen research evidence.

### 7.2.2 Module 1 metrics and protocol

Primary forecasting metrics include MAE, RMSE, sMAPE, and MASE scaled to a seasonal-naive benchmark with seasonal period `m = 52`. Stage 1 (SARIMA only) is compared with Stage 1 + Stage 2 (SARIMA plus XGBoost residual compensation). Additional diagnostics include Diebold–Mariano tests of Stage 1 versus Stage 1+2 loss differentials, residual variance reduction, and Ljung–Box checks on post-compensation residuals. MASE below 1 indicates improvement relative to the seasonal-naive benchmark. The primary compensation claim uses the regenerated pipeline after Stage 1 stationarity safeguards; production-stack refinements are reported separately so that feature-set updates are not confused with the residual-compensation effect itself.

### 7.2.3 Module 2 metrics and protocol

Because outbreak weeks are rare, PR-AUC is the primary Stage 1 discrimination metric; accuracy alone is not treated as decisive. Stage 2 is selected primarily by Brier Skill Score (BSS), which measures calibration relative to a base-rate forecast. Alert utility is summarised using recall, precision, and F2 at a fixed absolute probability threshold selected on validation folds only. Risk-tier quality is checked by observed outbreak rates within low, medium, and high bands defined by absolute calibrated-probability boundaries. Under the current harmonic epidemic label, holdout prevalence is low, so holdout metrics are interpreted with sampling-variance caution and are not compared directly to superseded pre–label-change numbers.

### 7.2.4 Module 3 metrics and protocol

Stage 1 spatial validity is assessed using Global Moran's I with queen-contiguity weights on the KDE baseline surface, reported both as an aggregated district summary and as selected weekly checks. Stage 2 residual prediction quality is assessed by out-of-fold MAE and RMSE under five-fold spatial K-means cross-validation. Convergence of the iterative risk update is checked by a dual criterion on maximum risk-value change and residual Moran's I significance, under the adopted full-magnitude update factor α = 1. Aggregate case-fit of the rescaled Stage 1 baseline, a naive persistence baseline, and the converged Stage 2 Risk surface is compared using correlation, MAE, and RMSE against actual district-week cases, alongside a rank-based hotspot lens (Spearman correlation, precision at top-k). This comparison is reported honestly regardless of outcome — an earlier design iteration is retained in the narrative precisely because it did not improve fit, before the final formulation was found to.

### 7.2.5 Scope boundaries

Operational forward forecasts and live risk scores are not treated as holdout-equivalent evidence. Cross-study "best model" claims are avoided; results are interpreted relative to each module's own baselines and ablations. Module 3 spatial metrics are not reframed as temporal forecasting skill. Alert and risk-tier thresholds reported for Module 2 are those selected under the current label and Stage 1 hyperparameters (τ = 0.10; high-confidence boundary 0.50, post–Decision 047) and must not be mixed with superseded thresholds from earlier label definitions or the pre-tuning production stack. Figure 7.1 summarises the evaluation protocol and evidence-tier separation.

[Insert Figure 7.1 here]

**Figure 7.1: Evaluation protocol schematic showing walk-forward folds and holdout for Modules 1 and 2, spatial cross-validation for Module 3, and separation of research versus operational evidence**

**Approx. word count:** 565 words

---

## 7.3 Module 1: Forecasting Evaluation

### 7.3.1 Experimental setup

Module 1 Stage 1 fits per-district SARIMA models on weekly case counts only. Stage 2 predicts the SARIMA residual with a pooled XGBoost regressor using case-lag, climate-lag and anomaly, seasonal, residual-lag, and—under the current production path—reporting-delay features. Evaluation uses 14 expanding-window walk-forward folds plus a 104-week holdout block per district. The core residual-compensation comparison reported below corresponds to the regenerated pipeline after Stage 1 stationarity safeguards (Decision 017 / experiment M1-003). The current production stack additionally includes reporting-delay features promoted under Decision 030 / M1-006B. Imputed rows are excluded from scoring.

### 7.3.2 Stage 1 vs Stage 1+2 residual compensation

Across all 25 districts, Stage 1+2 improved validation-aggregate MASE for 25/25 districts relative to Stage 1 only. On the untouched holdout block, 23/25 districts improved. The two holdout exceptions were Kilinochchi and Mannar; neither showed a statistically significant worsening under the Diebold–Mariano test. These exceptions are retained in the narrative rather than omitted, because the research claim is directional and material improvement for most districts, not universal perfection.

**Table 7.1: Headline Stage 1 versus Stage 1+2 MASE improvement (Decision 017 / M1-003)**

| Scope | Median MASE improvement (Stage 1 → Stage 1+2) | Districts improved |
|---|---|---|
| Validation aggregate | 43.5% | 25/25 |
| Holdout | 32.7% | 23/25 |

Median absolute holdout MASE moved from approximately 0.622 (Stage 1) to approximately 0.375 (Stage 1+2) in the Decision 017 regenerated comparison. Selected district examples from the same comparison include strong holdout gains for Colombo (0.65 → 0.32), Gampaha (0.74 → 0.35), and Batticaloa (0.59 → 0.25), alongside limited or negative holdout movement for Kilinochchi and Mannar. The median percentage reductions indicate that residual compensation recovers a substantial fraction of error left by the climate-free SARIMA baseline, while the absolute MASE values show that the compensated forecasts also move below the seasonal-naive scale for the typical district.

A full per-district Stage 1 versus Stage 1+2 MASE table may be placed in an appendix if the main chapter needs to remain compact; the source artefact is `outputs/metrics/module1/combined_vs_baseline_metrics.csv`, with narrative confirmation in `module_1_forecasting/MODULE_CONTEXT.md`.

### 7.3.3 Statistical significance

At the pooled validation-and-holdout Diebold–Mariano scope, 14/25 districts showed Stage 2 significantly better than Stage 1 (`p < 0.05`). At the stricter holdout-only scope, 5/25 districts reached significance. No district showed a statistically significant worsening at either scope. This pattern is interpreted honestly: residual compensation is directionally beneficial and often material, but universal statistical significance is not claimed at the per-district holdout sample size of 104 weeks. Diebold–Mariano therefore supports selective confidence rather than a blanket significance claim. The corresponding district-level test results are recorded in `outputs/metrics/module1/diebold_mariano_results.csv`.

### 7.3.4 Production stack refinement (M1-006B)

After promotion of reporting-delay / nowcasting-state features (M1-006B; Decision 030), the default production path achieved a further modest holdout refinement on top of the residual-compensation architecture.

**Table 7.2: Production stack holdout refinement after M1-006B**

| Metric (holdout) | Pre-promotion | Post-promotion (current) |
|---|---|---|
| Median MASE | 0.386 | 0.374 |
| Median sMAPE | 35.0% | 34.2% |
| Districts improved (MASE vs prior stack) | — | 22/25 |

These figures refine the production feature set; they do not replace the Stage 1 versus Stage 1+2 comparison as the primary evidence that compensation itself helps. The production median holdout MASE of 0.374 is therefore best read as the current operating point of an already-validated residual-compensation pipeline.

### 7.3.5 Interpretation and limits

Residual compensation substantially reduces average forecast error relative to SARIMA alone for most districts. Remaining structure in residuals—Ljung–Box still significant for many districts—indicates that Stage 2 reduces error magnitude without fully whitening residuals. Extreme catch-up weeks associated with suspected reporting dynamics remain difficult. Rolling one-step evaluation can improve near-term outbreak-week error relative to a flat multi-step holdout block, but flat holdout MASE remains the primary validated backtest evidence and must not be conflated with operational rolling analogues. Forward forecast files without ground truth are excluded from the skill claims above and must not be used as Figure 7.2 evidence.

As shown in Figure 7.2, selected district trajectories illustrate how Stage 1+2 tracks observed case intensity more closely than Stage 1 alone during the holdout window. Figure 7.3 summarises the district-level holdout MASE comparison that underlies Table 7.1, including the Kilinochchi and Mannar exceptions.

[Insert Figure 7.2 here]
*(PNG: `research_context/report_drafts/diagrams/figure_7_2_module1_holdout_forecasts.png`)*

**Figure 7.2: Example actual versus Stage 1 versus Stage 1+2 weekly case forecasts for selected districts (e.g. Colombo and Gampaha holdout windows)**

[Insert Figure 7.3 here]
*(PNG: `research_context/report_drafts/diagrams/figure_7_3_module1_holdout_mase.png`)*

**Figure 7.3: District-level holdout MASE comparison of Stage 1 versus Stage 1+2**

**Approx. word count:** 920 words

---

## 7.4 Module 2: Outbreak Classification Evaluation

### 7.4.1 Experimental setup and outbreak labelling

Module 2 uses fold-aware epidemic-threshold labels under the harmonic seasonal estimator with `k = 3.0` (Decision 025). Evaluation uses 13 walk-forward folds with a four-year minimum training depth, plus a two-year holdout block of 2,600 district-weeks. Under the current label, holdout outbreak prevalence is approximately 1.5% (about 40 positive rows), so holdout metrics carry higher sampling variance than under earlier, superseded label definitions and are not directly comparable to pre–Decision-025 numbers. Stage 2 fold `k` trains only on official Stage 1 out-of-sample probabilities from earlier folds.

### 7.4.2 Stage 1 discrimination

Model-type selection (Random Forest over Logistic Regression and XGBoost, Decision 025) was made first, by median validation PR-AUC across the same 13 folds this section reports throughout.

**Table 7.3: Stage 1 model comparison under the current harmonic label**

| Model | Median validation PR-AUC (13 folds) |
|---|---|
| Logistic Regression | 0.355 |
| XGBoost (tuned params) | 0.382 |
| Random Forest (selected model type) | 0.390 |

Random Forest was subsequently given its own hyperparameter search (Decision 047/M2-013) — a step Decision 025's label re-estimation had not included, since only XGBoost had previously been tuned (Decision 023), for an architecture no longer selected. A 50-trial Optuna search (`class_weight="balanced"` held fixed) found `n_estimators=472, max_depth=16, min_samples_leaf=11, min_samples_split=18, max_features="sqrt"`, raising median validation PR-AUC to **0.395** and, on the untouched holdout block, improving PR-AUC from 0.413 to **0.423**, ROC-AUC from 0.883 to **0.905**, and Brier score from 0.028 to **0.018**. Two related levers tested in the same experiment — `class_weight="balanced_subsample"` and an untuned Gradient Boosting benchmark (listed as a candidate model in earlier project documentation but never previously run) — both underperformed the tuned Random Forest and were not adopted. Pooled modelling continued to outperform per-district modelling on the pre-registered median PR-AUC comparison. Case-anomaly lags dominate feature importance, consistent with a label that encodes recent seasonal exceedance, documented as an expected near-label signal rather than an accidental leakage of current-week cases. The modest PR-AUC gaps among tree models remain less important than the consistent finding that Stage 1 ranks rare outbreak weeks far above chance under a prevalence-sensitive metric.

### 7.4.3 Stage 2 calibration compensation

Stage 1 raw probabilities remain poorly calibrated relative to base-rate forecasts (holdout Brier Skill Score −0.19), motivating Stage 2. Tuning Stage 1's Random Forest changed its probability distribution enough to flip Stage 2's architecture selection.

**Table 7.4: Stage 2 architecture comparison (post-tuning), validation and holdout**

| Architecture | Median validation BSS | Validation PR-AUC | Holdout BSS | Holdout PR-AUC |
|---|---:|---:|---:|---:|
| Stage 1 raw | −0.334 | 0.426 | −0.189 | 0.423 |
| Stacked XGBoost | −0.040 | 0.345 | −0.025 | 0.466 |
| Logit-residual | −0.014 | 0.368 | 0.001 | 0.320 |
| Isotonic | 0.220 | 0.390 | 0.259 | 0.419 |
| **Platt (selected)** | **0.227** | **0.426** | **0.267** | **0.423** |

Platt scaling now beats isotonic regression on median validation Brier Skill Score (0.227 vs. 0.220) and is selected per the same pre-registered rule that previously favoured isotonic — the flip is driven entirely by Stage 1's changed probability distribution after tuning, the same upstream-tuning mechanism that flipped Stage 2 the other way after Decision 023's earlier XGBoost tuning, not a Stage 2 code change. Because Platt scaling is a strictly monotonic transform of Stage 1's probability, holdout PR-AUC and ROC-AUC are identical to Stage 1 raw's own figures (0.423/0.905) — only the calibration (Brier/BSS), not the ranking, changes. Stacked XGBoost reaches the highest holdout PR-AUC (0.466) but a negative BSS on both splits, consistent with earlier findings that its own imbalance weighting reintroduces a probability-scale distortion; it remains unselected because BSS, not PR-AUC, is Stage 2's primary metric. As shown in Figure 7.4, Stage 1 raw probabilities lie systematically off the perfect-calibration diagonal, whereas the now-official Platt-scaled Stage 2 probabilities sit closer to observed outbreak rates on both the validation and holdout panels.

### 7.4.4 Alert thresholds and risk tiers

Validation-selected absolute thresholds, re-selected fresh from the new calibrated-probability distribution, are an alert threshold τ = 0.10 (F2-oriented) and a high-confidence boundary of 0.50 (F0.5-oriented) — both higher than the pre-tuning values (0.14/0.35) would suggest on their own, since threshold selection uses the same validation folds. At τ = 0.10, holdout recall is 62.5%, versus 37.5% under a naive 0.5 cutoff, with precision 34.2% and F2 = 0.536 — a modest but real improvement over the pre-tuning production figures (60.0% recall, 33.8% precision, F2 = 0.519). Observed outbreak rates by risk tier remain ordered and, on holdout, separate more cleanly than before: low 0.6%, medium 20.4%, high 62.5% (previously 0.6%/13.3%/48.8%), though the medium (n = 49) and high (n = 24) holdout groups remain small and their exact percentages should be read with the same sampling-variance caution as before.

### 7.4.5 Rejected ablations

Several alternatives were tested and not adopted for production. SMOTENC oversampling (M2-006) failed to improve holdout PR-AUC despite validation gains. Logit-space residual correction (M2-007A) did not beat Platt/isotonic. A climate-free Stage 1 with climate-stacked Stage 2 (M2-008) was rejected because stacked BSS remained weaker than the production calibrator. Module 1 forecast features in a tree Stage 2 (M2-007D) showed some ranking signal but were not promoted. Following the Random Forest tuning above, three further ablations were tested and also rejected: an ensemble of Stage 1's three benchmarked models, which won on validation but regressed on the untouched holdout block (M2-010); a district-specific, variance-adaptive relabeling rule, which genuinely narrowed cross-district prevalence variation but did not resolve the specific under-flagged case that motivated it (M2-011); and a lagged spatial risk feature drawn from Module 3's hybrid risk map, corrected for an earlier same-week leakage concern but still not beating the current feature set on validation (M2-014). These negatives, alongside the one genuine improvement above, illustrate that Module 2's Stage 2 form is probability calibration refined by careful, individually tested hyperparameter and feature choices, not an assumption that any plausible extension will help.

[Insert Figure 7.4 here]
*(PNG: `outputs/figures/module2/reliability_diagram_{validation,holdout}.png`, regenerated under the current production pipeline — now shows Platt, not isotonic)*

**Figure 7.4: Module 2 reliability diagrams comparing Stage 1 raw probabilities with Platt-scaled Stage 2 calibration (validation and holdout)**

**Approx. word count:** 900 words

---

## 7.5 Module 3: Spatial Hotspot Evaluation

### 7.5.1 Experimental setup

Module 3 evaluates a district-week spatial residual-compensation pipeline. Stage 1 constructs a case-weighted Gaussian KDE baseline over district centroids and validates spatial clustering with Global Moran's I under queen contiguity. Stage 2 predicts spatial residuals with a Random Forest regressor and updates risk iteratively under shrinkage. Validation uses five-fold spatial K-means cross-validation on district centroids so that whole districts remain held out together. Unlike Modules 1 and 2, Module 3 does not reserve a temporal two-year holdout; the research question is geographic redistribution and residual structure, not multi-week-ahead temporal forecast skill. Aggregate fit comparisons therefore describe how well Risk surfaces recover observed case intensity across the modelled district-week corpus, not holdout forecast accuracy in the Module 1 sense.

### 7.5.2 Stage 1 KDE baseline and Moran's I validation

Aggregated Global Moran's I on the KDE baseline is I ≈ 0.702 with permutation p-value 0.001, indicating significant spatial clustering at the district level. Selected weekly checks confirm that clustering is strong in peak and low-burden illustrative weeks, but not universal across the calendar.

**Table 7.5: Global Moran's I validation of the Stage 1 KDE baseline**

| Check | Year / Week | Moran's I | p_sim | Significant |
|---|---|---|---|---|
| Aggregated (primary) | — | 0.702 | 0.001 | Yes |
| Peak / SW monsoon | 2017 / 29 | 0.728 | 0.001 | Yes |
| Low burden | 2007 / 13 | 0.735 | 0.001 | Yes |
| NE monsoon | 2021 / 1 | 0.031 | 0.279 | No |

The NE-monsoon week's non-significance is retained deliberately. It shows that the aggregated I ≈ 0.70 headline must not be read as proof that every week exhibits the same clustering strength. Stage 1 therefore establishes a generally clustered spatial baseline with documented temporal nuance, which is an appropriate foundation for residual adjustment rather than a claim of invariant spatial structure.

### 7.5.3 Stage 2 RF residual adjustment and evolution to the final formulation

Stage 2's design went through two verified refinements before reaching its final, promoted form, and both are reported here because they materially change what the model's accuracy can be attributed to. An initial version trained the Random Forest on climate and demographic covariates alone (lagged rainfall and temperature, climate anomalies, monsoon indicators, elevation, population density, and a Mahalanobis anomaly score) and produced no genuine improvement over Stage 1 once benchmarked honestly. Diagnosing this null result found that none of those covariates gave the model information about a district's own recent case trajectory; adding own-district lags of the residual (one to four weeks back) resolved this and became the dominant features by a wide margin, confirming genuine short-term epidemic persistence at district level.

A second refinement addressed the scale of the residual target itself. A direct diagnostic of the raw (absolute) residual found it strongly heteroscedastic — error magnitude scales with the predicted baseline magnitude (correlation ≈ 0.78 between the baseline and the absolute residual's magnitude) — so a model trained on the absolute residual lets the handful of largest outbreak weeks dominate the learning signal at the expense of ordinary weeks. The final Stage 2 model instead predicts a relative residual, the absolute residual divided by the current baseline risk, with an exact reconstruction back to an absolute Risk value:

```text
Risk_t = Risk_(t-1) + α · predicted_relative_residual_t · (Risk_(t-1) + 1)
```

with α = 1 (the full-magnitude update). An earlier absolute-scale formulation required shrinkage (α = 0.05) because an unshrunk update on that scale diverged under honest out-of-fold prediction; the relative-scale reformulation, combined with the own-district lag features, removed this instability. The loop converges at iteration 1 under the dual numeric/spatial criterion, with residual Moran's I remaining non-significant. Feature importance of the final Random Forest is dominated by the district's own relative-residual lags (lag 1 ≈ 0.67, lag 2 ≈ 0.14, roughly 81 per cent combined), with the earlier absolute-residual lags, population density, and climate terms each contributing under two per cent. This pattern confirms that Stage 2's real, defensible mechanism is short-term epidemic persistence, not primarily an environmental or demographic correction — a genuine reframing from the module's original design intent, stated plainly rather than left implicit.

### 7.5.4 Stage 1 vs Stage 2 aggregate fit, and comparison against a naive persistence baseline

Because the own-district lag features account for the large majority of feature importance, the natural follow-up question is whether the Random Forest's out-of-fold prediction actually beats the trivial arithmetic of carrying a district's own last residual forward with no model at all. Both comparisons are reported together, since the naive-persistence check materially changes how the headline aggregate-fit improvement should be read.

**Table 7.6: Stage 1, naive persistence, and Stage 2 final — fit to actual district-week cases**

| Model | Correlation | MAE | RMSE |
|---|---|---|---|
| Stage 1 alone (Risk_0, rescaled KDE) | 0.8241 | 20.54 | 48.20 |
| Naive persistence (no model) | 0.9493 | 9.44 | 26.63 |
| Stage 2 final (Risk, post iterative loop) | 0.9592 | 8.03 | 24.02 |

Stage 2's final formulation improves on Stage 1 alone by roughly 61 per cent on MAE, and — unlike an earlier absolute-residual iteration of the same architecture, which lost to naive persistence on MAE — also improves on the naive-persistence baseline on every reported metric. This was confirmed through a week-level paired bootstrap (2,000 resamples) rather than trusted from the aggregate table alone, since an aggregate improvement can mask a result that is not robust week to week; the bootstrapped confidence intervals for Stage 2's advantage over both Stage 1 and naive persistence exclude zero. A rank-based companion evaluation — Spearman correlation and precision at the top 3 and top 5 highest-risk districts each week, matching Module 3's hotspot-detection purpose more directly than raw case-count error — shows the same ordering (Stage 2 final: Spearman ≈ 0.89, precision@5 ≈ 0.82; naive persistence: ≈ 0.85 and ≈ 0.78; Stage 1 alone: ≈ 0.71 and ≈ 0.60).

Two limitations are reported alongside this result rather than omitted. First, the RMSE improvement over naive persistence, while present in every spatial fold, is proportionally larger in the highest case-volume fold (containing Colombo and Gampaha) than in the others. Second, at the one representative week already identified in Stage 1 as lacking significant spatial clustering (an NE-monsoon week where the hotspot shifts away from the western districts), Stage 2's ranking accuracy is noticeably weaker than either baseline — a plausible sign that the model leans on dynamics specific to the dominant south-western clustering pattern that do not fully transfer to that structurally different regime.

### 7.5.5 Interpretation and limits

Module 3 Stage 1 succeeds as a clustered spatial baseline with an important weekly caveat. Stage 2, in its final form, succeeds as a genuine residual-compensation procedure: it converges cleanly, improves aggregate case-fit and hotspot-ranking accuracy over both Stage 1 alone and a naive persistence baseline, and its dominant learned mechanism (short-term own-district persistence) is interpretable and consistent with known epidemic dynamics. This required two rounds of honest diagnosis and correction — an initial covariate-only design that was null, and an absolute-residual design that lost to a trivial baseline — reported here as evidence of a rigorous evaluation process, not smoothed over. IDW rendering used for maps is visualisation only and does not alter either stage's estimates. District-level analysis cannot resolve sub-district hotspots, Open-Meteo climate/elevation remain point-per-district inputs, and the model's weaker performance at the structurally atypical NE-monsoon week remains an open limitation. These limits belong in the evaluation narrative because they bound what the Risk surface can claim as early-warning spatial support.

Figure 7.5 shows the continuous hybrid risk surface for the Stage 1 peak week (2017 Week 29), obtained by IDW interpolation of the twenty-five district Risk scores onto a land-clipped grid. The map concentrates elevated risk in the south-western coastal corridor, notably around Colombo, Gampaha, and Kalutara, while much of the north and east remains comparatively low. The figure should be read as a visualisation of the converged district Risk surface for a high-burden week, not as evidence that Stage 2 improved aggregate case-fit relative to Stage 1.

[Insert Figure 7.5 here]
*(PNG: `research_context/report_drafts/diagrams/figure_7_5_module3_risk_surface.png`; source: `outputs/figures/module3/risk_surface_peak_week.png`)*

**Figure 7.5: Module 3 continuous hybrid risk surface for peak week 2017 Week 29 (IDW visualisation of district Risk scores)**

**Approx. word count:** 850 words

---

## 7.6 Cross-Module Comparative Analysis

Experiment M2-009 tested whether Module 2 is unnecessary given Module 1 case forecasts, by comparing Module 2 alerts with thresholding Module 1's `final_prediction` on the same holdout block and outbreak label. The comparison uses the current production Module 2 stack (Platt-calibrated, τ = 0.10, post–Decision 047) against fair and naive Module 1 thresholding rules, with an oracle upper bound included only as a reference.

**Table 7.7: Holdout alert comparison of Module 2 versus Module 1 thresholding rules (M2-009, re-run post–Decision 047)**

| Rule (holdout, 40 outbreaks / 2,600 rows) | PR-AUC | Recall | Precision | F2 |
|---|---|---|---|---|
| Module 2 production (Platt, τ ≈ 0.10) | 0.423 | 0.625 | 0.342 | 0.536 |
| Module 1 forecast > epidemic threshold | 0.063 | 0.225 | 0.563 | 0.256 |
| Module 1 excess score (pred − threshold) | 0.280 | 0.225 | 0.563 | 0.256 |
| Module 1 forecast > 100 (naive) | 0.063 | 0.500 | 0.073 | 0.231 |
| Oracle: actual > threshold | 0.302 | 1.000 | 1.000 | 1.000 |

Module 2 captured 16 true outbreaks missed by the fair Module 1–threshold rule (previously 15, before the Random Forest tuning); the reverse set remains empty. Forecasting case magnitude and detecting relative epidemic exceedance are therefore still empirically separable tasks under this protocol, and the tuning that improved Module 2's own holdout numbers strengthened this comparison slightly rather than changing its conclusion. Module 1 remains the quantification layer; Module 2 remains the outbreak-alert layer. The large PR-AUC gap between Module 2 (0.423) and the fair Module 1 threshold rule (0.063) is still the headline comparative result: good case forecasts do not automatically yield good outbreak alerts when the decision target is seasonal exceedance rather than absolute case count.

Module 3 adds a third complementary axis: spatial concentration and demographically informed residual burden. Because Module 3 is not scored on the same temporal holdout outbreak label, it is not entered into the M2-009 alert table. Instead, the comparative claim is architectural and decision-support oriented. Magnitude (Module 1), calibrated outbreak state (Module 2), and spatial hotspot structure (Module 3) answer different questions and should remain visible as related but distinct products rather than being collapsed into a single undifferentiated score. The early-warning dashboard's research-versus-operational separation follows from the same principle: joint visualisation is useful, but evaluation authority stays with each module's validated protocol. A leakage-safe, lagged version of a fourth possible signal — feeding Module 3's spatial risk score into Module 2 as a Stage 1 feature — was tested after this comparison (M2-014) and did not improve Module 2's own discrimination, reinforcing that the three modules' current separation of concerns is not simply an unexploited opportunity for feature-sharing.

**Approx. word count:** 460 words

---

## 7.7 Discussion of Results

Across the framework, residual compensation is a shared methodological theme with module-specific meanings. In Module 1, compensation is an additive correction to SARIMA case forecasts using climate-aware and reporting-state features; the evidence supports material MASE reduction for most districts without claiming universal Diebold–Mariano significance or fully whitened residuals. In Module 2, compensation is now Platt-scaled recalibration of poorly calibrated Stage 1 probabilities (previously isotonic, before Stage 1's own hyperparameter tuning changed its output distribution); the evidence supports improved BSS and more useful absolute-threshold alerts, while rejected ablations — an ensemble of Stage 1 models, a district-adaptive relabeling rule, and a lagged spatial feature from Module 3 — show that several further plausible extensions did not survive the same holdout discipline that validated the tuning improvement that was adopted. In Module 3, compensation is a shrunk iterative adjustment of a KDE risk surface; the evidence supports stable convergence and interpretable drivers, while the aggregate case-fit comparison honestly fails to improve on Stage 1.

Taken together, the results support a multidimensional residual-compensation framework rather than a single winning model. Module 1 improves magnitude estimation relative to its baseline. Module 2 improves outbreak-alert usability relative to raw probabilities and relative to naive thresholding of Module 1 forecasts, and its own components (model family, hyperparameters, calibration method, decision thresholds) were each individually tested rather than assumed, with negative results reported alongside the one hyperparameter-tuning improvement that was adopted. Module 3 provides spatial hotspot structure and explanatory residual adjustment without overstating case-fit gains. Soft decision-support interpretation follows naturally: the framework can inform situational awareness, but it does not claim clinical diagnosis, guaranteed outbreak prevention, or operational command-centre readiness.

Several limitations should remain explicit in any defence of these results. District-level aggregation cannot capture sub-district heterogeneity, and Open-Meteo climate inputs remain point samples per district rather than spatial averages. Module 2 holdout positives are sparse under the current label, so alert and calibration metrics on the final block carry sampling variance — a limitation unchanged by the Random Forest tuning, since the holdout block itself did not grow. Some districts remain difficult for forecasting, and Module 3 validation is spatial rather than temporal. Operational live and forward dashboard outputs are useful for demonstration but remain a weaker evidence tier than the research metrics reported in this chapter.

**Approx. word count:** 420 words

---

## 7.8 Summary

This chapter evaluated all three modules of the Residual Compensation Modeling Framework under protocols matched to each research question. Module 1's residual compensation improved case-forecast MASE for most districts relative to SARIMA alone, with honest holdout exceptions and partial statistical significance. Module 2's tuned Random Forest Stage 1 and Platt-scaled Stage 2 provided outbreak-alert performance that cannot be recovered by simply thresholding Module 1 forecasts, and a subsequent round of hyperparameter tuning produced a further, holdout-confirmed improvement in both discrimination and calibration, alongside three additional ablations (ensembling, adaptive relabeling, a spatial feature from Module 3) that were tested and honestly not adopted. Module 3's KDE baseline exhibited significant spatial clustering with documented weekly nuance, and its final Stage 2 formulation — a relative-residual Random Forest driven mainly by own-district case persistence, converged under a full-magnitude (α = 1) update — genuinely improved aggregate case-fit and hotspot-ranking accuracy over both Stage 1 and a naive persistence baseline, after two earlier design iterations were honestly tested and found insufficient. Cross-module comparison supports retaining magnitude, calibrated outbreak risk, and spatial hotspot views as complementary decision-support products. Chapter 8 summarises the completed research contributions and outlines realistic future work.

**Approx. word count:** 165 words

---

## Word-Count Summary

| Section | Approx. words |
|---|---|
| 7.1 Introduction | 200 |
| 7.2 Evaluation Strategy | 565 |
| 7.3 Module 1 | 920 |
| 7.4 Module 2 | 900 |
| 7.5 Module 3 | 1050 |
| 7.6 Comparative | 460 |
| 7.7 Discussion | 420 |
| 7.8 Summary | 165 |
| **Chapter 7 total (body)** | **~4,480** |

---

## Notes for Team

- Primary paste file: this document (`chapter7_evaluation_v2.md`) — supersedes `chapter7_evaluation.md` (v1 retained unchanged, not deleted, per team instruction)
- Legacy M1/M2-only draft: `chapter7_m1_m2_evaluation.md` (superseded numbering; keep for reference only)
- Export Figures 7.2–7.5 from `outputs/figures/` / Module 3 map artefacts; draw Figure 7.1 protocol schematic
- Do not cite live/forward dashboard CSVs as holdout skill
- Module 3 honesty: no Stage 2 aggregate-fit improvement claim
- Module 2 thresholds: τ = 0.10 / high = 0.50 (post–Decision 047/M2-013) — superseding the v1 file's τ = 0.14 / 0.35
- Module 2 Stage 2 architecture: **Platt scaling** (post–Decision 047), superseding v1's isotonic
- Optional appendix: full per-district Module 1 MASE table from `combined_vs_baseline_metrics.csv`
