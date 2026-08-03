## 7.5 Module 3: Spatial Hotspot Evaluation

### 7.5.1 Experimental setup

Module 3 evaluates a district-week spatial residual-compensation pipeline. Stage 1 constructs a case-weighted Gaussian KDE baseline over district centroids and validates spatial clustering with Global Moran’s I under queen contiguity. Stage 2 predicts spatial residuals with a Random Forest regressor and updates risk iteratively under shrinkage. Validation uses five-fold spatial K-means cross-validation on district centroids so that whole districts remain held out together. Unlike Modules 1 and 2, Module 3 does not reserve a temporal two-year holdout; the research question is geographic redistribution and residual structure, not multi-week-ahead temporal forecast skill. Aggregate fit comparisons therefore describe how well Risk surfaces recover observed case intensity across the modelled district-week corpus, not holdout forecast accuracy in the Module 1 sense.

### 7.5.2 Stage 1 KDE baseline and Moran’s I validation

Aggregated Global Moran’s I on the KDE baseline is I ≈ 0.702 with permutation p-value 0.001, indicating significant spatial clustering at the district level. Selected weekly checks confirm that clustering is strong in peak and low-burden illustrative weeks, but not universal across the calendar.

**Table 7.5: Global Moran’s I validation of the Stage 1 KDE baseline**

| Check | Year / Week | Moran’s I | p_sim | Significant |
|---|---|---|---|---|
| Aggregated (primary) | — | 0.702 | 0.001 | Yes |
| Peak / SW monsoon | 2017 / 29 | 0.728 | 0.001 | Yes |
| Low burden | 2007 / 13 | 0.735 | 0.001 | Yes |
| NE monsoon | 2021 / 1 | 0.031 | 0.279 | No |

The NE-monsoon week’s non-significance is retained deliberately. It shows that the aggregated I ≈ 0.70 headline must not be read as proof that every week exhibits the same clustering strength. Stage 1 therefore establishes a generally clustered spatial baseline with documented temporal nuance, which is an appropriate foundation for residual adjustment rather than a claim of invariant spatial structure.

### 7.5.3 Stage 2 RF residual adjustment and α-update convergence

Stage 2 defines residual intensity as actual case intensity minus current Risk, beginning from the mass-conserving rescaled KDE baseline. Out-of-fold residual prediction under spatial CV achieved mean MAE 33.12 ± 23.57 and RMSE 54.79 ± 29.63 across five folds. The iterative update uses

```text
Risk_t = Risk_(t-1) + α · predicted_residual_t
```

with α = 0.05. A literal unshrunk update (α = 1.0) diverged under honest out-of-fold residual prediction. Under α = 0.05 the loop converged at iteration 1 (max_delta ≈ 9.63 below epsilon ≈ 12.98), with residual Moran’s I remaining non-significant. Feature importance of the final Random Forest is dominated by population density (≈ 0.407) and estimated population (≈ 0.178), followed by temperature and rainfall lag/anomaly terms. This pattern supports an interpretation of Stage 2 as district-level burden correction informed by demography and climate, rather than as a pure spatial declustering engine.

### 7.5.4 Stage 1 vs Stage 2 aggregate fit

Comparison of the rescaled Stage 1 baseline against the converged Stage 2 Risk surface yields a verified null-to-negative aggregate-fit result.

**Table 7.6: Stage 1 versus Stage 2 aggregate fit to actual district-week cases**

| Stage | Correlation | MAE | RMSE |
|---|---|---|---|
| Stage 1 alone (Risk_0, rescaled KDE) | 0.8243 | 20.19 | 47.30 |
| Stage 2 final (Risk, post iterative loop) | 0.8205 | 20.54 | 47.72 |
| Change (Stage 2 − Stage 1) | −0.0037 | +0.35 | +0.41 |

Stage 2 at α = 0.05 does not improve aggregate correlation, MAE, or RMSE relative to the rescaled KDE baseline. The implemented correction therefore cannot be defended as a national case-fit optimiser. Its evaluated contribution is stable residual adjustment under spatial validation, covariate-informed explanation of burden deviations, and methodological honesty in reporting a null aggregate-fit outcome rather than selecting a flattering secondary metric after the fact.

### 7.5.5 Interpretation and limits

Module 3 Stage 1 succeeds as a clustered spatial baseline with an important weekly caveat. Stage 2 succeeds as a constrained residual-adjustment procedure that converges under shrinkage and yields interpretable demographic/climate drivers, but it does not improve aggregate case-fit. IDW rendering used for maps is visualisation only and does not alter either stage’s estimates. District-level analysis cannot resolve sub-district hotspots, and Open-Meteo climate/elevation remain point-per-district inputs. These limits belong in the evaluation narrative because they bound what the Risk surface can claim as early-warning spatial support.

Figure 7.5 shows the continuous hybrid risk surface for the Stage 1 peak week (2017 Week 29), obtained by IDW interpolation of the twenty-five district Risk scores onto a land-clipped grid. The map concentrates elevated risk in the south-western coastal corridor, notably around Colombo, Gampaha, and Kalutara, while much of the north and east remains comparatively low. The figure should be read as a visualisation of the converged district Risk surface for a high-burden week, not as evidence that Stage 2 improved aggregate case-fit relative to Stage 1.

[Insert Figure 7.5 here]
*(PNG: `research_context/report_drafts/diagrams/figure_7_5_module3_risk_surface.png`; source: `outputs/figures/module3/risk_surface_peak_week.png`)*

**Figure 7.5: Module 3 continuous hybrid risk surface for peak week 2017 Week 29 (IDW visualisation of district Risk scores)**

**Approx. word count:** 850 words

**Notes for Team:**
- Standalone: `research_context/report_drafts/chapter7_7.5_module3.md`
- Figure 7.5 = peak-week IDW surface (2017 Wk29); optional companion weeks already exist (`risk_surface_2007_wk13.png`, `risk_surface_2021_wk01.png`)
- Keep M3-005 null aggregate-fit claim explicit — do not reframe Stage 2 as case-fit improvement
- α = 0.05 and IDW viz-only remain mandatory wording
- Transition: next topics are **7.6 Comparative**, **7.7 Discussion**, **7.8 Summary**
