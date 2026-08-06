# Chapter 4 — Section 4.6 Module 3: Hybrid Spatial Hotspot Detection

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 4.5 Module 2: Hybrid Outbreak Risk Classification  
**Next topic:** 4.7 System Integration and Early Warning Dashboard

---

## 4.6 Module 3: Hybrid Spatial Hotspot Detection

### 4.6.1 Purpose and scope

Module 3 focuses on the geographic concentration of dengue risk. While Modules 1 and 2 summarise expected case magnitude and outbreak probability for each district-week, they do not by themselves describe how burden is organised across neighbouring districts. Module 3 therefore answers the geographic-concentration dimension identified in Section 4.2: which districts form spatially coherent high-burden areas that may warrant prioritisation.

The accepted spatial unit is the administrative district (GADM Level-1), consistent with the epidemiological surveillance grain used throughout the framework. The module uses district-level case intensity together with district boundaries and centroids; it does not claim fine-scale targeting below the district level, nor does it depend on point-level geocoded household case locations. In addition to case geography, Module 3 incorporates environmental and demographic context such as rainfall, temperature, elevation, and population to support spatial residual adjustment.

### 4.6.2 Stage 1 spatial baseline (KDE and Moran’s I)

Stage 1 produces a spatial baseline risk surface using Kernel Density Estimation (KDE) informed by district-level case intensity and district-centroid geography. The KDE baseline redistributes weekly case burden across districts according to spatial proximity structure, providing an initial estimate of where risk appears concentrated. Moran’s I is then used to assess whether the resulting pattern reflects statistically meaningful spatial clustering rather than random geographic dispersion.

In this sense, Stage 1 answers two related questions: where burden appears spatially concentrated, and whether that concentration is coherent enough to justify a spatial modelling treatment. Local indicators such as LISA may be considered as extensions, but the core Stage 1 approach is KDE plus global spatial autocorrelation assessment. Detailed numeric Moran’s I results are reported in the evaluation chapter rather than here.

### 4.6.3 Stage 2 spatial residual adjustment

Stage 2 applies residual compensation in the spatial domain. After the baseline risk surface is established, systematic differences between observed case intensity and the baseline spatial estimate are treated as spatial residuals. These residuals are then adjusted using environmental and demographic context, including rainfall, temperature, elevation, and population. The accepted compensation design uses a tree-based spatial residual adjustment model, refined through an iterative loop that checks whether successive adjustments materially change the risk surface and whether residual spatial structure remains.

Conceptually, Stage 2 corrects baseline hotspot estimates that are incompletely explained by case geography alone. Environmental and demographic information therefore enter Module 3 primarily as compensators of spatial residual structure, allowing the final risk interpretation to reflect both geographic clustering and contextual modifiers. This is analogous in spirit to Modules 1 and 2, but the compensation target is a spatial risk surface rather than a univariate case residual or a calibrated probability.

Figure 4.4 summarises this two-stage spatial workflow from the KDE and Moran’s I baseline through environmental and demographic residual adjustment to the final hotspot interpretation.

**[Insert Figure 4.4 here]**

**Figure 4.4:** Two-stage Module 3 workflow (KDE + Moran’s I baseline → environmental/demographic residual adjustment → hotspot / risk surface).

### 4.6.4 Expected outputs and users

The intended outputs of Module 3 are district-level hotspot interpretations and adjusted spatial risk surfaces that complement Module 1’s case forecasts and Module 2’s outbreak probabilities. These outputs are useful for vector-control planning discussions and geographic prioritisation within a research decision-support framing. They should be interpreted as model-based spatial risk indicators, not as guaranteed outbreak maps or operationally certified targeting instructions.

This section establishes the conceptual approach only. Detailed spatial pipeline design, preprocessing choices, residual-surface construction, and quantitative spatial evaluation are developed further in the analysis, implementation, and evaluation chapters. The detailed spatial feature dictionary is likewise reserved for those later chapters.

**Figure 4.4 content to draw (required):**

```text
District-level weekly cases
+ district boundaries / centroids
+ rainfall, temperature, elevation, population
        ↓
Stage 1: KDE spatial baseline
   (+ Moran’s I clustering check)
        ↓
Spatial residual extraction
   observed intensity vs baseline risk
        ↓
Stage 2: Environmental / demographic
         residual adjustment
   (tree-based compensator + iterative refinement)
        ↓
Adjusted hotspot / spatial risk surface
```

Do **not** show point-level geocoded case pins as the main data unit, DS-division (GADM Level-2) targeting, or Module 3 as only a static heatmap with no residual stage.

**Approx. word count:** 520 words

**Notes for Team:**
- Inputs/outputs stated in prose (4.6.1 and 4.6.4); full spatial feature/raster detail belongs in Chapters 5–6; cross-module IPO comparison in Table 4.2 (Section 4.8).
- Cite Figure 4.4 in the body (done in 4.6.3) and place it immediately after that paragraph in Word.
- Keep Chapter 4 conceptual; do not paste Moran’s I = 0.70 here unless the team wants a light forward reference to Chapter 7.
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md` (Figure 4.4).
