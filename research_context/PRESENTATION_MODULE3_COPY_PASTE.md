# Module 3 — Copy-Paste Slide Content
## Hybrid Spatial Hotspot Detection

**Owner:** Karunarathna R.M.D.R.R. (214099D)  
**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Deck size:** 7 slides (presentation-safe)

**How to use:** Copy each **ON-SLIDE** block into your slide body. Paste figures from the paths listed. Speaker notes are optional.

---

## SLIDE 1 — Module Introduction

**Title (paste as slide title):**
```
Module 3 — Hybrid Spatial Hotspot Detection
Karunarathna R.M.D.R.R. | 214099D
```

**ON-SLIDE:**
```
What is Module 3?
• Hybrid spatial hotspot pipeline that maps where dengue burden
  concentrates across 25 districts using KDE + RF residual compensation

Research gap
• Temporal modules (M1, M2) do not show geographic concentration
• Raw case counts ignore neighbour influence and spatial clustering
• Hotspot maps based on geography alone miss demographic and
  environmental drivers of burden redistribution

Novelty
• Extends residual compensation to the spatial domain — KDE baseline
  validated with Moran's I, then demographic/climate Stage 2 correction
• Same two-stage philosophy as M1/M2 but compensation target is a
  spatial risk surface, not a forecast or probability score
• Completes the framework's third axis: magnitude, outbreak state, location
```

**INSERT:** None

**SPEAKER NOTES:**
Module 3 is the spatial layer — "where is burden concentrated?" Lead later slides with the peak-week map. IDW is visualisation only; do not claim sub-district precision.

---

## SLIDE 2 — Two-Stage Design

**Title:**
```
Spatial Residual Compensation Design
```

**ON-SLIDE:**
```
Stage 1 — Spatial baseline
• Case-weighted Gaussian KDE over district centroids
• Global Moran's I validates genuine spatial clustering
• Output: KDE_baseline risk surface

Stage 2 — Residual compensation
• Residual = (actual case intensity − current Risk) / (current Risk + 1) — a RELATIVE measure
• Random Forest predicts the relative spatial residual
• Full-magnitude iterative update (α = 1):
    Risk_t = Risk_(t−1) + α · predicted_residual_t · (Risk_(t−1)+1)

Validation
• 5-fold spatial K-means cross-validation on district centroids
• Whole districts held out together (spatial CV)

Visualisation
• IDW interpolation for continuous risk maps (display layer only)
```

**INSERT FIGURE:**
- **Figure 6.4** — Module 3 implementation pipeline  
- File: `research_context/report_drafts/diagrams/figure_6_4_module3_implementation.png`  
- Place: right half of slide (or full-width below text)

**FIGURE CAPTION (optional):**
```
Figure 6.4: Module 3 implementation pipeline —
spatial data → KDE baseline → RF compensation → risk surface
```

**SPEAKER NOTES:**
Module 3 uses spatial cross-validation, not the temporal holdout of Modules 1 and 2 — because the research question is geographic redistribution of burden, not multi-week-ahead forecasting. IDW is for map rendering only; it does not change Stage 1 or Stage 2 estimates.

---

## SLIDE 3 — Spatial Data Stack

**Title:**
```
Spatial Data Stack (District Level)
```

**ON-SLIDE:**
```
Spatial unit
• GADM Level-1 — 25 Sri Lankan districts
• District centroids and queen-contiguity neighbours from GADM geometry

Integrated master table (district-week)
• Weekly dengue cases (epi-week aligned)
• Weekly climate — rainfall, temperature, humidity (Open-Meteo)
• Census population (interpolated) → population density
• Elevation (Open-Meteo district headers)
• District boundaries for mapping and spatial statistics

Stage 2 role of covariates
• Population density and environmental features support
  demographic and climate-driven residual adjustment
```

**INSERT TABLE (paste into slide):**

| Layer | Source | Role |
|---|---|---|
| Cases | MoH WER | KDE weights / residual target |
| Climate | Open-Meteo (weekly) | Stage 2 covariates |
| Population | Census 2001 / 2012 / 2024 | Burden context |
| Elevation | Open-Meteo | Environmental covariate |
| Boundaries | GADM v4.1 Level-1 | Maps and Moran's I weights |

**SPEAKER NOTES:**
All three modules share the same epidemiological and climate foundation. Module 3 adds spatial geometry, population layers, and district-level mapping outputs on top of that shared stack.

---

## SLIDE 4 — Stage 1: KDE + Moran's I

**Title:**
```
Stage 1 — Spatial Baseline Validated
```

**ON-SLIDE:**
```
Kernel Density Estimation (KDE)
• Case-count-weighted Gaussian KDE over district centroids
• Silverman bandwidth fixed from district geography
• Captures neighbour-influenced spatial concentration of burden

Moran's I validation (queen contiguity, 999 permutations)
• Aggregated Global Moran's I = 0.702, p = 0.001
• Statistically significant spatial clustering confirmed

Selected weekly checks
• Peak week 2017 / Week 29:  I = 0.728  (significant)
• Low-burden week 2007 / Week 13:  I = 0.735  (significant)

Conclusion
• KDE baseline reflects genuine spatial clustering —
  appropriate foundation for residual adjustment
```

**INSERT TABLE — Table 7.5 (presentation version, paste into slide):**

| Check | Year / Week | Moran's I | Significant |
|---|---|---|:---:|
| Aggregated (primary) | All weeks | 0.702 | Yes |
| Peak / SW monsoon | 2017 / 29 | 0.728 | Yes |
| Low burden | 2007 / 13 | 0.735 | Yes |

**SPEAKER NOTES:**
Moran's I confirms the KDE surface is not arbitrary noise — dengue burden clusters spatially at district level. Peak week 2017 Wk29 aligns with Sri Lanka's worst recorded dengue epidemic, which strengthens the ecological validity of the baseline.

---

## SLIDE 5 — Stage 2: Residual Model & Drivers

**Title:**
```
Stage 2 — Relative-Residual Correction Driven by Case Persistence
```

**ON-SLIDE:**
```
Residual model
• Target: (observed case intensity − current Risk) / (current Risk + 1) — a RELATIVE measure
• Random Forest regressor under 5-fold spatial cross-validation
• Residual features: own-district recent case history (primary),
  population, climate lags, anomalies, elevation (secondary)

Iterative risk update
• Full-magnitude update (α = 1) — stable once own-district history was added
• Converged Risk surface: corr(Risk, Cases) ≈ 0.96 —
  a genuine improvement over Stage 1 alone (≈0.82) and a naive
  "no model" baseline (≈0.95)

Dominant correction drivers
• Own-district relative-residual lag (1 week back) — leading feature (~67% importance)
• Own-district relative-residual lag (2 weeks back) — second (~14% importance)
• Population density and climate terms — supporting (each <2%)

Interpretation
• Stage 2's real mechanism is short-term epidemic persistence,
  with demographic/environmental context playing a secondary role
```

**INSERT FIGURE:**
- **Feature importance chart**  
- File: `outputs/figures/module3/feature_importance.png` (regenerated 2026-08-08)  
- Place: right half or full-width below text

**INSERT TABLE (paste into slide):**

| Rank | Feature | Importance |
|:---:|---|---|
| 1 | relative_residual_lag_1 | ≈ 0.67 |
| 2 | relative_residual_lag_2 | ≈ 0.14 |
| 3 | population_density | supporting (<2%) |
| 4 | climate lag / anomaly terms | supporting (each <2%) |

**FIGURE CAPTION (optional):**
```
Stage 2 Random Forest feature importance —
own-district case persistence leads spatial residual correction
```

**SPEAKER NOTES:**
A district's own recent case history dominating feature importance makes epidemiological sense — dengue burden carries genuine week-to-week persistence. This was found only after an earlier version trained on climate/demographics alone was tested and produced no improvement.

---

## SLIDE 6 — Hybrid Risk Surface Map

**Title:**
```
Hybrid Hotspot Map — Peak Burden Week (2017 Week 29)
```

**ON-SLIDE:**
```
Visualisation
• Continuous hybrid risk surface for 2017 Week 29
• National dengue outbreak peak — SW monsoon period
• IDW interpolation of 25 district Risk scores onto land-clipped grid

Geographic pattern
• Elevated risk in the south-western coastal corridor
• Highest concentration: Colombo, Gampaha, Kalutara
• Northern and eastern districts comparatively lower

Framework value
• Supports geographic prioritisation alongside
  Module 1 case forecasts and Module 2 outbreak alerts
• Strong association with observed burden (corr ≈ 0.96) —
  genuinely better than Stage 1 alone AND a naive "no model" check
```

**INSERT FIGURE (required — make this the hero slide):**
- **Figure 7.5** — Hybrid risk surface, peak week  
- File: `research_context/report_drafts/diagrams/figure_7_5_module3_risk_surface.png`  
- Alternative source: `outputs/figures/module3/risk_surface_peak_week.png`  
- Place: full slide (large, readable)

**FIGURE CAPTION:**
```
Figure 7.5: Hybrid spatial risk surface — 2017 Week 29
(IDW visualisation of district Risk scores)
```

**SPEAKER NOTES:**
This is the strongest visual asset for Module 3. The SW corridor pattern matches known epidemic geography from the 2017 outbreak. Frame the map as situational awareness for where to focus attention — not as proof of sub-district precision.

---

## SLIDE 7 — Summary & Framework Role

**Title:**
```
Module 3 — Key Outcomes
```

**ON-SLIDE:**
```
Delivered
• District-level spatial hotspot pipeline with validated KDE baseline
• Random Forest residual compensation with stable iterative update
• Continuous hybrid risk maps integrated in Streamlit dashboard

Demonstrated
• Significant spatial clustering (Moran's I ≈ 0.70)
• A relative-residual correction, driven mainly by case persistence, that
  genuinely improves case-fit and hotspot ranking over Stage 1 AND a naive
  "no model" baseline (bootstrap-confirmed, not just an aggregate table)
• Peak-week map aligns with known high-burden geography

Framework role — three complementary modules
• Module 1: How many cases next?        (magnitude)
• Module 2: Is this an outbreak-risk week?  (alert layer)
• Module 3: Where is burden concentrated?    (spatial layer)
```

**INSERT TABLE (paste into slide):**

| Module | Question answered | Output |
|---|---|---|
| 1 | How many cases? | Weekly case forecast |
| 2 | Outbreak risk? | Calibrated alert + tiers |
| 3 | Where concentrated? | Hybrid risk surface / map |

**INSERT (optional):**
- Small thumbnail of Figure 7.5, OR
- Three-column framework diagram (Magnitude | Outbreak | Spatial)

**SPEAKER NOTES:**
Close by tying all three modules together. The dashboard shows them side by side — magnitude, outbreak state, and spatial concentration — as complementary decision-support views, not a single merged score.

---

# Quick reference — files to insert

| Slide | Asset | Path |
|:---:|---|---|
| 2 | Figure 6.4 | `research_context/report_drafts/diagrams/figure_6_4_module3_implementation.png` |
| 5 | Feature importance | `outputs/figures/module3/feature_importance.png` |
| 6 | Figure 7.5 | `research_context/report_drafts/diagrams/figure_7_5_module3_risk_surface.png` |

---

# Slide footer (optional, all slides)

```
Team Codexon | A Residual Compensation Modeling Framework for Dengue Risk Prediction
Module 3 — Hybrid Spatial Hotspot Detection | 214099D
```

---

**Approx. on-slide word count:** ~640 words across 7 slides  
**Status:** Copy-paste ready (presentation-safe, 2026-07-31; UPDATED 2026-08-08 after M3-015 promotion — Stage 2 now genuinely improves case-fit, see `PRESENTATION_MODULE3_SLIDES.md` for full context)
