# Chapter 5 — Section 5.4.3 Module 3 Design

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 5.4.2 Module 2 design (+ Figure 5.4)  
**Next topic:** 5.5 Integration and Output Design (+ Figure 5.6)

---

### 5.4.3 Module 3: Hybrid Spatial Hotspot Detection

The design of Module 3 addresses geographic concentration of dengue risk at the same district-week grain used by Modules 1 and 2. While the forecasting and classification modules summarise magnitude and outbreak probability for each district-week, they do not by themselves describe how burden is organised across neighbouring districts. Module 3 therefore constructs a spatial baseline risk surface and then adjusts residual spatial structure using environmental and demographic context. The module does not attempt DS-division or point-level geocoded targeting; analysis is constrained to the 25 GADM Level-1 districts so that spatial outputs remain comparable with the temporal modules.

Four design objectives guide the module. First, Stage 1 must produce an interpretable spatial baseline from district-level case intensity and geography. Second, that baseline must be checked for coherent spatial clustering rather than treated as random geographic noise. Third, Stage 2 must compensate systematic differences between observed intensity and the baseline using climate, elevation, and population covariates. Fourth, residual adjustment must be refined through a controlled iterative update so that the final hotspot surface is a compensated spatial risk estimate rather than a one-shot residual overlay.

Figure 5.5 summarises the Module 3 component flow from shared and spatial inputs through the KDE baseline, residual compensation, iterative refinement, and hotspot output.

**[Insert Figure 5.5 here]**

**Figure 5.5:** High-level architecture of Module 3 — Hybrid Spatial Hotspot Detection (KDE + Moran’s I baseline → Random Forest residual compensation → iterative risk update).

**Shared and spatial input layer.** Module 3 reuses the shared epidemiological weekly table and weekly climate aggregates aligned to the Ministry of Health epidemiological calendar. In addition, it joins district-level elevation, interpolated population (and derived population density), and GADM Level-1 district boundaries/centroids. Module 3 does not inherit Module 1’s week-53 merge or Module 2’s labelling pipeline; those choices remain module-specific under Decision 013. A Module 3 master table assembles the joined district-week records used by both stages.

**Stage 1 — KDE spatial baseline with Moran’s I checkpoint.** Stage 1 uses Kernel Density Estimation over district centroids, weighted by weekly case counts, with a Gaussian kernel and a bandwidth derived from the spatial spread of the district geography. The resulting `KDE_baseline` provides a spatially smoothed risk surface that redistributes weekly burden according to proximity among case-heavy neighbours. Global Moran’s I under queen contiguity is then used as a design checkpoint to assess whether the baseline pattern exhibits statistically meaningful spatial clustering. Local indicators such as LISA remain optional extensions; the core Stage 1 design is KDE plus global spatial autocorrelation assessment.

An important design distinction is that `KDE_baseline` is used in two consistent forms. The raw density surface is appropriate for Moran’s I, which is scale-invariant and validates relative clustering. For residual compensation, the same spatial shape is mass-conserved (rescaled) within each week so that the baseline is numerically comparable with observed case intensity. This preserves the geographic redistribution pattern while making the residual

```text
Residual = Actual_case_intensity − Current_Risk
```

a meaningful Stage 2 target rather than an almost exact copy of the case series.

**Stage 2 — Random Forest residual compensation with iterative refinement.** Stage 2 trains a Random Forest regressor to predict the spatial residual from lagged rainfall and temperature features, climate anomalies, monsoon indicators, elevation, population density, and a multivariate Mahalanobis anomaly score. Unlike Modules 1 and 2, compensation is wrapped in an iterative refinement loop. At each iteration the risk surface is updated as

```text
Risk_t = Risk_(t-1) + α · predicted_residual_t
```

with a shrinkage factor `α = 0.05`. The loop continues until successive risk changes fall below a tolerance and residual Moran’s I is no longer statistically significant, subject to a small iteration cap as a practical safeguard. Shrinkage is part of the accepted design because an unshrunk full-step update was found to diverge during implementation; the present section records that design choice, while quantitative convergence and fit results are reserved for Chapter 7.

**Output and intended users.** The primary analytical output is the converged hybrid spatial risk surface (district-week hotspot / risk map), exportable with district geometry for dashboard visualisation. A continuous IDW surface may be rendered for display, but IDW is treated as a visualisation aid rather than an additional modelling stage. Evaluation design emphasises Moran’s I for spatial structure and spatial cross-validation error metrics for residual-model performance. Intended users are analysts who need geographic concentration of dengue burden to complement Module 1’s magnitude forecasts and Module 2’s calibrated outbreak probabilities. As with the other modules, Module 3 is positioned as a research decision-support component rather than a fine-scale operational targeting system.

**Approx. word count:** 610 words

**Notes for Team:**
- Do not claim Stage 2 improves aggregate case-fit; verified results show null/negative aggregate fit change (M3-005). Stage 2’s documented value is mainly explanatory (population/climate importance) plus the iterative residual-compensation design.
- Report Moran’s I nuance in Chapter 7: aggregated I ≈ 0.70 (significant), but NE-monsoon representative week not significant.
- Figure assets: `research_context/report_drafts/diagrams/figure_5_5_module3_architecture.drawio` (+ `.png`).
- Keep numeric MAE/RMSE/feature-importance values for Chapter 7.
