## 6.6 Implementation of Module 3: Hybrid Spatial Hotspot Detection

### 6.6.1 Master Table Construction

Module 3 preprocessing joins the shared epidemiological, weekly climate, and annual population tables with GADM Level-1 geometry and Open-Meteo elevation into a spatial master table. Each row remains a district-week unit, preserving temporal compatibility with Modules 1 and 2 while adding the spatial attributes required for kernel density estimation, contiguity weights, and environmental residual adjustment. Population density is derived from Estimated_Population and district land area rather than imported from an external gridded population product. Elevation enters as a static district covariate extracted from Open-Meteo response headers. Rows outside climate coverage are dropped before Stage 1 density estimation so that later residual features are not built on incomplete environmental joins.

This construction deliberately keeps Module 3 at district level. No DS-division, MOH-area, or raster population stack is introduced in the production path. The master table therefore provides a single district-week analytical grain for both the spatial baseline and the residual compensation stage, and it remains consistent with the spatial and demographic sources described in Section 6.2.3.

### 6.6.2 Stage 1: KDE Baseline and Moran’s I Validation

Stage 1 constructs a case-weighted kernel density surface over district centroids using a Gaussian kernel and Silverman’s bandwidth rule. Bandwidth is derived once from the spatial spread of the centroids so that smoothing scale remains a property of geography rather than of week-to-week epidemic intensity. Global Moran’s I with queen-contiguity weights then validates whether the resulting surface exhibits genuine spatial clustering rather than spatial randomness. Local indicators and Getis-Ord statistics remain optional extensions and are not required for the production Stage 1 path.

The same KDE_baseline quantity is used in two deliberate forms. In raw form it is a normalised density surface suitable for scale-invariant Moran’s I validation. For Stage 2 residual modelling it is rescaled in a mass-conserving way within each week so that district baseline risk sums to that week’s national case total. Rescaling preserves the spatial redistribution shape encoded by the kernel while making the baseline magnitude comparable to actual case intensity. This dual use is an implementation necessity, not a contradiction: clustering validation does not require absolute case-scale magnitudes, whereas residual subtraction does.

### 6.6.3 Stage 2: Random Forest Residual Adjustment and Iterative Update

Stage 2 defines the spatial residual as

```text
Residual = Actual_case_intensity − Current_Risk
```

where Current_Risk begins as the rescaled KDE baseline and is updated across iterations. An initial implementation trained a Random Forest regressor to predict this residual from rainfall and temperature lags, climate anomalies, monsoon indicators, elevation, population density, and a Mahalanobis anomaly score over selected environmental and demographic variables, but produced no genuine improvement in fit once benchmarked honestly. Diagnosing this null result showed that none of those covariates gave the model any information about a district's own recent case trajectory — every feature was either static per district or described only current-week climate. Own-district lags of the residual (one to four weeks back) were added to close this gap and immediately became the dominant features by a wide margin, confirming that dengue burden carries genuine short-term persistence at district level that the original feature set could not represent.

A second refinement addressed the SCALE of the residual target. A direct diagnostic of the raw (absolute) residual found it strongly heteroscedastic — error magnitude scales with the predicted baseline magnitude — so a model trained on the absolute residual lets the largest outbreak weeks dominate the learning signal at the expense of ordinary weeks. Stage 2 therefore predicts a relative residual, the absolute residual divided by the current baseline risk, with an exact (not approximate) reconstruction back to an absolute Risk value. Validation throughout uses spatial K-means cross-validation on district centroids so that whole districts remain together within folds, matching the spatial rather than temporal research question of Module 3.

The iterative update is

```text
Risk_t = Risk_(t-1) + α · predicted_relative_residual_t · (Risk_(t-1) + 1)
```

with α = 1, the full-magnitude update. An earlier absolute-scale formulation required shrinkage (α = 0.05) because an unshrunk full-step update on that scale diverged under honest out-of-fold residual prediction: static district covariates alone made held-out-district extrapolation imperfect, so adding full-magnitude prediction error back into Risk compounded iteration over iteration. Once own-district relative-residual lags gave the model a genuine dynamic anchor even for a held-out district, this instability resolved and the full-magnitude update became the best-performing choice. The loop is still checked against a dual criterion on risk-value change and residual Moran's I significance each run, with a small iteration cap as a safeguard, and retraining within the loop uses the same spatial folds so that predicted residuals remain out of fold for held-out districts rather than memorising in-sample targets.

### 6.6.4 Converged Risk Map and Visualisation

The converged Risk surface is exported as the hybrid risk map for dashboard and report visualisation. Continuous map rendering interpolates the twenty-five district Risk scores onto a land-clipped grid using k-nearest-neighbour inverse-distance weighting with k = 4 and power = 4. IDW is a visualisation-layer technique only; it is not an additional modelling stage and does not alter Stage 1 or Stage 2 estimates. Choropleth maps and generic heatmap blur were judged insufficient to communicate neighbourhood blending already implied by the KDE geometry, whereas IDW with a limited neighbour set and steeper distance decay better preserves local hotspot contrast without colouring ocean cells.

In its final promoted form, Stage 2 does improve aggregate case-fit relative to the rescaled Stage 1 baseline, and — unlike an earlier absolute-residual iteration — also improves on a naive persistence baseline (simply carrying a district's own last recorded residual forward with no model at all), confirmed through a week-level bootstrap rather than an aggregate table alone. This should not be overstated: the improvement is not uniform across every spatial fold or week, and the model is noticeably weaker at the one representative week already identified in Stage 1 as lacking significant spatial clustering. Any aggregate fit comparison and its caveats belong in Chapter 7 and must be reported honestly rather than reframed around a more flattering secondary metric. Figure 6.4 summarises the Module 3 implementation stack.

[Insert Figure 6.4 here]

**Figure 6.4: Module 3 implementation workflow from master-table construction through KDE/Moran’s I, Random Forest residual adjustment, iterative α-update, and IDW visualisation**

Figure 6.4 should be interpreted as a district-level spatial residual-compensation pipeline grounded in Open-Meteo and GADM Level-1 inputs, not as a CHIRPS/WorldPop/DS-division production system.

**Approx. word count:** 1080 words

**Notes for Team:**
- PNG: `research_context/report_drafts/diagrams/figure_6_4_module3_implementation.png`
- Draw.io: `research_context/report_drafts/diagrams/figure_6_4_module3_implementation.drawio`
- UPDATED 2026-08-08 (M3-015): official formula is now `α = 1` with the relative-residual reconstruction shown above, not `α = 0.05` on the absolute residual — regenerate the figure/diagram accordingly. Keep IDW (k=4, power=4) explicit.
- Stage 2 now DOES improve aggregate case-fit (over Stage 1 and over naive persistence) — do not keep the old "does not improve" wording; defer exact metrics and honest caveats (fold heterogeneity, NE-monsoon weakness) to Chapter 7.
- Do not revive CHIRPS / WorldPop / SRTM / DS-division claims
- Transition: next section is 6.7 Output Generation and Early-Warning Dashboard
