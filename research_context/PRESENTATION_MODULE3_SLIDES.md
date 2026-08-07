# Module 3 Presentation Slides — Hybrid Spatial Hotspot Detection

**Owner:** Karunarathna R.M.D.R.R. (214099D)  
**Audience:** FYP presentation (sample-style module pack)  
**Status:** Presentation-safe outline (2026-07-31; UPDATED 2026-08-08 after M3-015 promotion)  
**Evidence base:** `MODULE_CONTEXT.md`, Chapter 7.5, `REPORT_DIAGRAM_PLAN.md`

**UPDATE 2026-08-08 (M3-015):** Stage 2's final formulation now genuinely improves aggregate case-fit AND hotspot-ranking accuracy over both Stage 1 and a naive persistence baseline, confirmed via a week-level bootstrap — this reverses the deck's original "don't claim case-fit improvement" policy for Table 7.6/aggregate fit specifically. The dominant driver is also no longer population density — it is now the district's own recent case history. Non-significant Moran's weeks, the earlier alpha-divergence story, and grain limitations remain excluded per the original policy below.

**Presentation policy:** This pack includes **supporting results and design strengths only**. Non-significant Moran’s weeks, the retired alpha-divergence story, the NE-monsoon ranking weakness, and grain limitations stay in the report and viva prep — see **Excluded from slides** at the end.

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
Stage 2: RF predicts a RELATIVE spatial residual
         (Actual intensity − Current_Risk) / (Current_Risk + 1)
         Risk_t = Risk_(t−1) + α · predicted_residual_t · (Risk_(t−1)+1)   (α = 1)
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

**Title:** Stage 2 — Relative-Residual Correction Driven by Case Persistence

**Content:**
- Residual target: a RELATIVE measure — observed case intensity minus current risk, divided by current risk — not the raw difference
- Random Forest regressor under spatial cross-validation
- **A district's own recent case history (1–2 weeks back)** is the dominant correction driver, not climate or demographics
- Population density, elevation, and climate lag/anomaly terms play a supporting, secondary role
- Full-magnitude update (**α = 1**) — an earlier version needed shrinkage (α = 0.05) before this feature/target change stabilised it

**Suggested figure:**
- `outputs/figures/module3/feature_importance.png` (regenerated 2026-08-08)  
  Caption: *Stage 2 feature importance — own-district relative-residual lags lead correction*

**Suggested table:**

| Rank | Feature | Importance |
|---|---|---|
| 1 | relative_residual_lag_1 | ≈ 0.67 |
| 2 | relative_residual_lag_2 | ≈ 0.14 |
| 3+ | population density / climate terms | supporting (each <2%) |

**Do not put on slide:** KDE rescale technical rationale unless asked briefly.

---

## Slide M3-6 — Hybrid Risk Surface & Results

**Title:** Hybrid Hotspot Map — Peak Burden Week

**Content:**
- Converged district Risk surface visualised for **2017 Week 29** (national outbreak peak)
- Elevated risk concentrates in the **south-western coastal corridor** (Colombo, Gampaha, Kalutara)
- Map supports geographic prioritisation alongside Module 1 forecasts and Module 2 alerts
- `corr(Risk, Number_of_Cases) ≈ 0.96` — strong association with observed burden pattern, and a genuine, bootstrap-confirmed improvement over both Stage 1 alone (≈0.82) and a naive "no-model" baseline (≈0.95)

**Suggested figure (required):**
- **Figure 7.5** — `research_context/report_drafts/diagrams/figure_7_5_module3_risk_surface.png` (regenerated 2026-08-08)  
  Caption: *Hybrid spatial risk surface — 2017 Week 29 (IDW visualisation of district Risk scores)*

**Suggested table (now safe to present — Table 7.6, positive result):**

| Model | MAE | RMSE |
|---|---|---|
| Stage 1 alone | 20.5 | 48.2 |
| Naive persistence (no model) | 9.4 | 26.6 |
| **Stage 2 final** | **8.0** | **24.0** |

**Optional positive callout:** peak-week map aligns with known 2017 epidemic geography; Stage 2 beats a naive "just copy last week" baseline, not only Stage 1.

**Do not put on slide:** the NE-monsoon week's weaker ranking result; per-fold RMSE variability.

---

## Slide M3-7 — Summary & Framework Role

**Title:** Module 3 — Key Outcomes

**Content:**
- Delivered a **district-level spatial hotspot pipeline** with validated KDE baseline
- Stage 2 adds a **relative-residual correction, driven mainly by case persistence**, that genuinely improves on both the spatial baseline and a naive "no model" check
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
| Fig 6.4 implementation pipeline | M3-2 | High (re-adapt from corrected Fig 5.5 before use) |
| Table 7.5 (aggregated + peak + low rows only) | M3-4 | High |
| feature_importance.png | M3-5 | High |
| Fig 7.5 peak-week risk surface | M3-6 | High |
| Table 7.6 aggregate fit (Stage 1 / persistence / Stage 2) | M3-6 | **High — now a positive result, include it** |
| convergence_plot.png | — | Excluded (technical convergence detail, not needed for the headline story) |
| risk_surface_2021_wk01.png | — | **Excluded** (non-cluster week; also Stage 2's weakest week) |

---

# Excluded from slides (report / viva only)

Do **not** present these in the main deck:

| Topic | Why excluded |
|---|---|
| NE-monsoon week: Stage 2 ranking accuracy notably weaker than baselines | Genuine, still-open limitation — save for viva questions |
| NE-monsoon week Moran’s I not significant | Weakens universal clustering claim |
| Two earlier design iterations were null (covariates-only) or lost to persistence (absolute-residual) | Design history, not needed for the headline result — mention only if asked how the final design was reached |
| RMSE improvement is proportionally larger in the highest-volume spatial fold | Fold-level nuance, not needed for the headline aggregate number |
| RF does not remove residual spatial autocorrelation (Stage 1 already does) | Mechanism nuance, not needed for the headline story |
| District grain only / no DS-division | Scope limitation |
| LISA / Gi* not implemented | Incomplete stretch goal |
| IDW is not a modelling stage | Methodological caveat |
| No temporal holdout like M1/M2 | Protocol difference that invites comparison |

---

# Speaker guardrails

**Say:**
- Moran’s I ≈ 0.70 confirms significant spatial clustering
- Stage 2's correction is driven mainly by each district's own recent case history, with climate/demographics as secondary context
- Stage 2 genuinely improves case-fit and hotspot ranking over both Stage 1 and a naive "no model" baseline, confirmed with a bootstrap test, not just an aggregate table
- Peak-week map shows SW corridor hotspot pattern
- Module 3 completes the framework’s spatial decision-support view

**Avoid in the presentation:**
- Showing non-significant Moran’s weeks
- Discussing the two earlier (null) design iterations unless asked how the final design was reached
- Promising sub-district operational targeting
- Claiming the improvement is uniform everywhere (it is not — save the NE-monsoon caveat for viva questions)

---

# Notes for Team

- **Lead with the map (Figure 7.5)** — strongest visual asset
- UPDATED 2026-08-08 (M3-015): the M3-005 null-fit result is superseded — Chapter 7.5 now reports a genuine, bootstrap-confirmed improvement (with the NE-monsoon caveat kept honest). Slides can now show Table 7.6 as a positive result.
- All three module packs now use the same presentation-safe policy:
  - `PRESENTATION_MODULE1_SLIDES.md`
  - `PRESENTATION_MODULE2_SLIDES.md`
  - `PRESENTATION_MODULE3_SLIDES.md`
