# Module 3 Presentation Slides — Hybrid Spatial Hotspot Detection

**Owner:** Karunarathna R.M.D.R.R. (214099D)  
**Audience:** FYP presentation (sample-style module pack)  
**Status:** Presentation-safe outline (2026-07-31, revised)  
**Evidence base:** `MODULE_CONTEXT.md`, Chapter 7.5, `REPORT_DIAGRAM_PLAN.md`

**Presentation policy:** This pack includes **supporting results and design strengths only**. Null aggregate-fit results, alpha-divergence stories, non-significant Moran’s weeks, and grain limitations stay in the report and viva prep — see **Excluded from slides** at the end.

Use **6–7 core slides** in the main deck.

---

## Slide M3-1 — Module Introduction

**Title:** Module 3 — Hybrid Spatial Hotspot Detection (214099D)

**Content structure:** What is Module 3 → Research gap → Novelty (three short blocks)

**Content:**
- **What is Module 3?** Hybrid spatial hotspot pipeline mapping where burden concentrates via KDE + RF residual compensation
- **Research gap:** Temporal modules lack geographic concentration view; raw cases ignore spatial clustering and demographic/environmental context
- **Novelty:** Residual compensation applied to spatial risk surface; Moran's I–validated KDE baseline + contextual Stage 2; completes magnitude / outbreak / location framework axis

**Suggested figure:** none required.

---

## Slide M3-2 — Two-Stage Design

**Title:** Spatial Residual Compensation Design

**Content:**
```text
Stage 1: Case-weighted Gaussian KDE + Moran’s I validation
Stage 2: RF predicts spatial residual (Actual intensity − Current_Risk)
         Risk_t = Risk_(t−1) + α · predicted_residual_t   (α = 0.05)
```
- Spatial validation: **5-fold K-means CV** on district centroids
- Queen-contiguity Moran’s I confirms genuine spatial clustering
- IDW rendering for continuous maps (visualisation layer only)

**Suggested figure:**
- **Figure 6.4** — `research_context/report_drafts/diagrams/figure_6_4_module3_implementation.png`  
  Caption: *Module 3 pipeline: spatial data → KDE baseline → RF compensation → risk surface*

---

## Slide M3-3 — Data Layers & Spatial Unit

**Title:** Spatial Data Stack

**Content:**
- Spatial unit: **GADM Level-1** — 25 districts
- Integrated master table: weekly cases, weekly climate, census population, elevation, district geometry
- Population density and environmental covariates support Stage 2 residual adjustment

**Suggested table:**

| Layer | Source | Role |
|---|---|---|
| Cases | MoH WER | KDE weights / residual target |
| Climate | Open-Meteo | Stage 2 covariates |
| Population | Census (interpolated) | Burden context |
| Elevation | Open-Meteo | Environmental covariate |
| Boundaries | GADM v4.1 L1 | Maps and contiguity |

---

## Slide M3-4 — Stage 1: KDE + Moran’s I

**Title:** Stage 1 — Spatial Baseline Validated

**Content:**
- Case-count-weighted Gaussian KDE over district centroids
- Aggregated Global Moran’s I: **I ≈ 0.702, p = 0.001** → statistically significant spatial clustering
- Selected high-burden weeks (e.g. **2017 Week 29**) show strong clustering — appropriate foundation for residual adjustment
- KDE baseline captures neighbour-influenced spatial concentration of dengue burden

**Suggested table — Table 7.5 (presentation version — positive rows only):**

| Check | Year / Week | Moran’s I | Significant |
|---|---|---|---|
| Aggregated (primary) | All weeks | 0.702 | Yes |
| Peak / SW monsoon | 2017 / 29 | 0.728 | Yes |
| Low burden | 2007 / 13 | 0.735 | Yes |

**Do not put on slide:** NE-monsoon 2021 Wk1 non-significant row; side-by-side “flat” week map comparison.

---

## Slide M3-5 — Stage 2: Residual Model & Drivers

**Title:** Stage 2 — Demographic and Environmental Correction

**Content:**
- Residual target: observed case intensity minus current risk surface
- Random Forest regressor under spatial cross-validation
- **Population density** and **estimated population** are the dominant correction drivers
- Climate lag and anomaly features provide additional contextual adjustment
- Shrinkage update (**α = 0.05**) ensures stable iterative convergence

**Suggested figure:**
- `outputs/figures/module3/feature_importance.png`  
  Caption: *Stage 2 feature importance — population density leads correction*

**Suggested table:**

| Rank | Feature | Importance |
|---|---|---|
| 1 | population_density | ≈ 0.41 |
| 2 | estimated population | ≈ 0.18 |
| 3+ | temperature / rainfall terms | supporting |

**Do not put on slide:** OOF MAE/RMSE with wide fold variance; KDE rescale technical rationale unless asked briefly.

---

## Slide M3-6 — Hybrid Risk Surface & Results

**Title:** Hybrid Hotspot Map — Peak Burden Week

**Content:**
- Converged district Risk surface visualised for **2017 Week 29** (national outbreak peak)
- Elevated risk concentrates in the **south-western coastal corridor** (Colombo, Gampaha, Kalutara)
- Map supports geographic prioritisation alongside Module 1 forecasts and Module 2 alerts
- `corr(Risk, Number_of_Cases) ≈ 0.82` — strong association with observed burden pattern

**Suggested figure (required):**
- **Figure 7.5** — `research_context/report_drafts/diagrams/figure_7_5_module3_risk_surface.png`  
  Caption: *Hybrid spatial risk surface — 2017 Week 29 (IDW visualisation of district Risk scores)*

**Optional positive callout:** peak-week map aligns with known 2017 epidemic geography.

**Do not put on slide:** Table 7.6 null aggregate-fit; “Stage 2 does not improve MAE/RMSE”.

---

## Slide M3-7 — Summary & Framework Role

**Title:** Module 3 — Key Outcomes

**Content:**
- Delivered a **district-level spatial hotspot pipeline** with validated KDE baseline
- Stage 2 adds **interpretable demographic and climate-driven** residual adjustment
- Provides the framework’s **spatial axis**: where burden concentrates, not just how many cases or outbreak probability
- Integrated risk maps in the Streamlit dashboard alongside Modules 1 and 2

**Suggested table — three-module complementarity:**

| Module | Question answered |
|---|---|
| 1 | How many cases next? |
| 2 | Is this an outbreak-risk week? |
| 3 | Where is burden concentrated? |

**Suggested figure:** Figure 7.5 thumbnail or framework integration icon.

---

## Optional Slide M3-8 — Related Works

**Title:** Related Work — Spatial Dengue / Hotspot Methods

**Content:** 2–3 citations from Chapter 2 on KDE, Moran’s I, or spatial dengue mapping.

---

# Recommended Main-Deck Sequence (7 slides)

1. M3-1 Gap & goal  
2. M3-2 Design + Figure 6.4  
3. M3-3 Data layers  
4. M3-4 Stage 1 Moran’s I (positive rows)  
5. M3-5 Stage 2 features + importance figure  
6. M3-6 Figure 7.5 peak risk map  
7. M3-7 Summary & complementarity  

---

# Figure & Table Checklist (presentation-safe)

| Asset | Slide | Priority |
|---|---|---|
| Fig 6.4 implementation pipeline | M3-2 | High |
| Table 7.5 (aggregated + peak + low rows only) | M3-4 | High |
| feature_importance.png | M3-5 | High |
| Fig 7.5 peak-week risk surface | M3-6 | High |
| convergence_plot.png | — | **Excluded** (alpha story) |
| risk_surface_2021_wk01.png | — | **Excluded** (non-cluster week) |
| Table 7.6 aggregate fit | — | **Excluded** (null result) |

---

# Excluded from slides (report / viva only)

Do **not** present these in the main deck:

| Topic | Why excluded |
|---|---|
| Table 7.6 — Stage 2 worse MAE/RMSE/corr | Null / negative aggregate-fit result |
| NE-monsoon week Moran’s I not significant | Weakens universal clustering claim |
| α = 1.0 diverges; α = 0.3/0.15 unstable | Failed tuning narrative |
| Loop converges at iteration 1 only | Suggests Stage 2 adds little |
| RF does not remove residual spatial autocorrelation | Weakens Stage 2 mechanism story |
| OOF MAE 33.12 ± 23.57 (high variance) | Noisy error headline |
| District grain only / no DS-division | Scope limitation |
| LISA / Gi* not implemented | Incomplete stretch goal |
| IDW is not a modelling stage | Methodological caveat |
| No temporal holdout like M1/M2 | Protocol difference that invites comparison |

---

# Speaker guardrails

**Say:**
- Moran’s I ≈ 0.70 confirms significant spatial clustering
- Population density drives Stage 2 spatial correction
- Peak-week map shows SW corridor hotspot pattern
- Module 3 completes the framework’s spatial decision-support view

**Avoid in the presentation:**
- Claiming Stage 2 improves national case-fit metrics
- Showing non-significant Moran’s weeks
- Discussing alpha divergence unless asked
- Promising sub-district operational targeting

---

# Notes for Team

- **Lead with the map (Figure 7.5)** — strongest visual asset
- Report Chapter 7.5 retains M3-005 null-fit honesty; slides focus on clustering validation + interpretable correction + map output
- All three module packs now use the same presentation-safe policy:
  - `PRESENTATION_MODULE1_SLIDES.md`
  - `PRESENTATION_MODULE2_SLIDES.md`
  - `PRESENTATION_MODULE3_SLIDES.md`
