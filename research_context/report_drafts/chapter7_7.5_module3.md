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

**Approx. word count:** 1050 words

**Notes for Team:**
- Standalone: `research_context/report_drafts/chapter7_7.5_module3.md`
- Figure 7.5 = peak-week IDW surface (2017 Wk29), regenerated 2026-08-08 from the promoted relative-residual model; optional companion weeks already exist (`risk_surface_2007_wk13.png`, `risk_surface_2021_wk01.png`) and should be regenerated too if cited
- UPDATED 2026-08-08 (M3-015): Stage 2 final DOES now improve aggregate fit and hotspot-ranking accuracy over both Stage 1 and naive persistence — the M3-005 null result and the subsequent M3-010 "loses to persistence" finding are both superseded and kept only as design-rationale context in 7.5.3, not as the final claim. Do not revert to the old "Stage 2 does not improve case-fit" wording anywhere in the report.
- `α = 1` with the relative-residual reconstruction formula is now the mandatory wording, not `α = 0.05`
- Source data for the tables/figures above: `outputs/metrics/module3/results_summary.txt`, `stage1_vs_stage2_comparison.csv`, `persistence_baseline_comparison.csv`, `hotspot_ranking_evaluation.csv`
- Transition: next topics are **7.6 Comparative**, **7.7 Discussion**, **7.8 Summary**
