# Team Codexon FYP Chapter Status Tracker

## Project Title

**A Residual Compensation Modeling Framework for Dengue Risk Prediction**

## Purpose

This file tracks the progress, status, word counts, missing items, diagrams, tables, citations, and review notes for each chapter of the final report.

Update this file whenever a chapter or section is drafted, revised, reviewed, or finalized. Record the approximate word count of each drafted section against the targets defined in `research_context/REPORT_STYLE_GUIDE.md`.

---

# Status Legend

| Status | Meaning |
|---|---|
| Not Started | No content drafted yet |
| Outline Ready | Chapter structure prepared |
| Drafting | Content is being written |
| Draft Complete | Full initial draft completed |
| Needs Evidence | Missing results, citations, diagrams, or references |
| Needs Review | Requires team/supervisor review |
| Revised | Updated after review |
| Finalized | Ready for final formatting/submission |

---

# Word Count Targets

Approximate target lengths per chapter (full targets and per-subsection guidance are in `research_context/REPORT_STYLE_GUIDE.md`):

| Chapter | Target Word Count |
|---|---|
| Chapter 1 - Introduction | 1,500-2,500 |
| Chapter 2 - Literature Review | 2,500-3,500 |
| Chapter 3 - Technologies and Tools Used | 1,200-2,000 |
| Chapter 4 - Proposed Research Framework | 2,000-3,000 |
| Chapter 5 - Analysis and Design | 2,500-3,500 |
| Chapter 6 - Implementation | 3,000-4,000 |
| Chapter 7 - Evaluation and Results | 3,200-4,500 |
| Chapter 8 - Conclusion and Further Work | 1,000-1,500 |
| Chapter 9 - Challenges and Limitations | 1,200-2,000 |

---

# Overall Report Status

---

# Overall Report Status

| Area | Status | Notes |
|---|---|---|
| Front Matter | Not Started | Title page, declaration, dedication, acknowledgement, abstract pending |
| Chapter 1 | Drafting | 1.1, 1.3, 1.4, 1.5.2, 1.5 Summary drafts ready; Aim and remaining sections pending |
| Chapter 2 | Not Started | Literature review and research gap pending |
| Chapter 3 | Drafting | 3.2 + 3.3 Summary drafts ready (`report_drafts/chapter3_3.2_technology_adapted.md`, `chapter3_3.3_summary.md`) |
| Chapter 4 | Drafting | Expanded Ch.4 structure accepted; full draft in `report_drafts/chapter4_our_approach.md`; Module 3 conceptual approach included |
| Chapter 5 | Drafting | Expanded Ch.5 structure accepted; full draft in `report_drafts/chapter5_analysis_and_design.md`; Module 3 design included |
| Chapter 6 | Draft Complete | Full paste-ready draft in `report_drafts/chapter6_implementation.md` (~4,840 words) |
| Chapter 7 | Drafting | Accepted full 7.1–7.8 structure (incl. Module 3); combined draft in `report_drafts/chapter7_evaluation.md` |
| Chapter 8 | Drafting | Accepted 8.1–8.2; draft in `report_drafts/chapter8_conclusion_further_work.md` |
| Chapter 9 | Drafting | Accepted 9.1–9.5; draft in `report_drafts/chapter9_challenges_limitations.md` |
| References | Not Started | Citation list pending |
| Appendices | Drafting | Appendix A individual contributions draft ready |

---

# Front Matter

## Required Items

- Cover Page
- Title Page
- Declaration / Certification Page
- Dedication
- Acknowledgement
- Abstract
- Table of Contents
- List of Figures
- List of Tables
- List of Abbreviations, if required

## Current Status

Status: Not Started

## Notes

- Abstract should be written after implementation and evaluation chapters are stable.
- Table of contents should be generated after final pagination.
- List of figures and tables should be updated after all diagrams/tables are finalized.

---

# Chapter 1 - Introduction

## Current Status

Status: Drafting

## Possible Sections

- 1.1 Introduction — **Draft ready** (~245 words)
- 1.2 Background and Motivation
- 1.3 Problem Statement / Problem in Brief — **Draft ready** (~420 words)
- 1.4 Proposed Solution — **Draft ready** (~560 words; interim numbering; `REPORT_STRUCTURE.md` lists this as 1.6)
- 1.5 Aim and Objectives
  - 1.5.1 Aim — pending
  - 1.5.2 Objectives — **Draft ready**
- 1.5 Summary — **Draft ready** (~195 words; interim numbering; typically final Ch.1 subsection)
- 1.6 Research Scope / Research Gap — confirm final order with supervisor
- (Adaptive: Research Gap may be inserted as a separate subsection if required)

## Required Content

- Dengue problem background
- Motivation for prediction and early warning
- Importance of forecasting, classification, and hotspot detection
- Aim and objectives
- Proposed framework overview
- Report structure

## Required Figures/Tables

- Optional: Overview of the problem context
- Optional: Summary of proposed modules

## Missing Items

- [x] 1.1 Introduction draft aligned to current architecture (district-level; residual compensation; three modules)
- [x] 1.3 Problem in Brief draft (reframed away from fine-scale; residual compensation + multidimensional risk)
- [x] 1.4 Proposed Solution draft (SARIMA→XGBoost; RF→isotonic; KDE/Moran’s I spatial design)
- [x] 1.5.2 Objectives draft (Module 2 calibration wording corrected)
- [x] 1.5 Summary draft
- [ ] 1.5.1 Aim draft
- [ ] Literature citations for dengue burden (beyond Uduwanage et al. [1] / Uelmen Jr. et al. [4])
- [ ] Finalized aim
- [ ] Finalized objectives — draft ready; confirm with Aim and supervisor
- [ ] Scope boundaries
- [ ] Confirm Chapter 1 subsection order (Proposed Solution vs Research Gap numbering)
- [ ] Paste Word update of sections 1.1 / 1.3 / 1.4 / 1.5.2 / 1.5 Summary

## Notes

Draft locations:
- `research_context/report_drafts/chapter1_1.1_introduction.md`
- `research_context/report_drafts/chapter1_1.3_problem_in_brief.md`
- `research_context/report_drafts/chapter1_1.4_proposed_solution.md`
- `research_context/report_drafts/chapter1_1.5.2_objectives.md`
- `research_context/report_drafts/chapter1_1.5_summary.md`

Key corrections vs interim Chapter 1 text:
- Dengue-focused; residual compensation framing; district-level (not fine-scale)
- Softened Command Center / scenario-simulation claims → early-warning decision-support dashboard
- Module 1 Stage 1 = SARIMA only (not SARIMAX); Stage 2 = XGBoost
- Module 2 Stage 1 = Random Forest with climate included; Stage 2 = isotonic calibration
- Module 3 = KDE + Moran’s I baseline + spatial residual adjustment (design-level in Ch.1)
- Objectives / Summary: Module 2 no longer claims environmental-anomaly residual correction for all modules alike

---

# Chapter 2 - Literature Review

## Current Status

Status: Not Started

## Possible Sections

- 2.1 Introduction
- 2.2 Dengue as a Public Health Problem
- 2.3 Epidemiological and Climate Factors
- 2.4 Time-Series Forecasting for Dengue
- 2.5 Machine Learning for Dengue Prediction
- 2.6 Hybrid Forecasting and Residual Correction
- 2.7 Outbreak Risk Classification
- 2.8 Spatial Hotspot Detection
- 2.9 Comparison of Existing Approaches
- 2.10 Research Gap
- 2.11 Summary

## Required Content

- Review of dengue forecasting studies
- Review of ML-based dengue prediction
- Review of hybrid/residual modeling approaches
- Review of spatial hotspot mapping approaches
- Clear research gap

## Required Figures/Tables

- [ ] Table comparing related work
- [ ] Optional taxonomy diagram of related methods

## Missing Items

- [ ] Final literature sources
- [ ] Comparison criteria
- [ ] Research gap wording
- [ ] Citations for climate and dengue relationship
- [ ] Citations for spatial hotspot methods

## Notes

This chapter must be strongly citation-supported.

---

# Chapter 3 - Technologies and Tools Used

## Current Status

Status: Drafting

## Possible Sections

- 3.1 Introduction — pending
- 3.2 Technology Adapted — **Draft ready** (~920 words)
  - 3.2.1 Programming Languages
  - 3.2.2 Development Environments and Tools
  - 3.2.3 Libraries and Frameworks
  - 3.2.4 Version Control and Collaboration
- 3.3 Summary — **Draft ready** (~160 words)
- 3.3–3.10 alternative split in `REPORT_STRUCTURE.md` — optional later redistribution

## Required Content

- Python usage
- Jupyter Notebook / Cursor IDE usage
- Pandas and NumPy for preprocessing
- Statsmodels / pmdarima for SARIMA
- Scikit-learn / XGBoost for ML and calibration
- GeoPandas / Folium / libpysal / esda for spatial/dashboard mapping
- Streamlit / Plotly dashboard stack
- GitHub and documentation workflow

## Required Figures/Tables

- [x] Draft Table 3.1: technology summary
- Optional: Technology stack diagram

## Missing Items

- [x] Confirm final library list against `requirements.txt` / implementation
- [x] 3.3 Summary draft
- [ ] Confirm whether VS Code should be named alongside Cursor for any teammate workflow
- [ ] Paste Word update of sections 3.2 / 3.3
- [ ] Chapter 3 introduction
- [ ] Add citations if department requires tool/library citations

## Notes

Avoid generic tool descriptions. Every tool must be connected to project usage.

Draft location: `research_context/report_drafts/chapter3_3.2_technology_adapted.md`

Key corrections vs interim 3.2:
- Removed Flask/Django, React, LightGBM, Colab-as-core, SARIMAX/STL-as-production
- Dashboard = Streamlit (+ Plotly / Folium), not command-center web stack
- imbalanced-learn = SMOTE audit only; production uses class weights
- Official models stated accurately (SARIMA→XGBoost; RF→isotonic)

---

# Chapter 4 - Proposed Research Framework / Our Approach

## Current Status

Status: Drafting

## Possible Sections

- 4.1 Introduction — **Draft ready** (`report_drafts/chapter4_4.1_introduction.md`)
- 4.2 Overview of the Proposed Framework — in expanded draft
- 4.3 Residual Compensation Strategy — in expanded draft
- 4.4 Module 1 (4.4.1–4.4.4) — in expanded draft
- 4.5 Module 2 (4.5.1–4.5.4) — in expanded draft
- 4.6 Module 3 (4.6.1–4.6.4) — conceptual approach in expanded draft
- 4.7 System Integration and Early Warning Dashboard — in expanded draft
- 4.8 Inputs, Processes, and Outputs Summary — in expanded draft
- 4.9 Summary — in expanded draft

## Required Content

- Explain the overall framework
- Explain each module conceptually
- Explain residual compensation
- Explain how modules integrate
- Explain expected inputs and outputs

## Required Figures/Tables

- [x] Planned: Figure 4.1 overall framework
- [x] Planned: Figure 4.2 Module 1 workflow
- [x] Planned: Figure 4.3 Module 2 workflow
- [x] Planned: Figure 4.4 Module 3 workflow
- [x] Planned: Figure 4.5 dashboard integration (optional)
- [x] Planned: Table 4.1 compensation meanings
- [x] Planned: Table 4.2 IPO summary

## Missing Items

- [x] Expanded Chapter 4 structure accepted (2026-07-30)
- [x] Full conceptual draft for sections 4.2–4.9
- [ ] Draw/export Figures 4.1–4.5 for Word
- [ ] Paste Word update of expanded Chapter 4

## Notes

This chapter should not go too deeply into implementation code.

Primary draft location: `research_context/report_drafts/chapter4_our_approach.md`  
Earlier M1/M2 stub: `research_context/report_drafts/chapter4_4.2.1_4.2.2.md` (superseded by expanded numbering)

Key corrections vs interim Chapter 4:
- District-level (not fine-scale)
- Module 1 Stage 1 = SARIMA only (not SARIMAX); climate in Stage 2
- Module 1 Stage 2 = XGBoost residual regression
- Module 2 Stage 1 = Random Forest with climate included
- Module 2 Stage 2 = isotonic probability calibration (official)
- Avoid SMOTE as production imbalance method
- Dashboard = Streamlit decision-support (no scenario simulation / Command Centre stack)

---

# Chapter 5 - Analysis and Design

## Current Status

Status: Drafting

## Possible Sections

- 5.1 Introduction — in expanded draft
- 5.2 High-Level System Architecture — in expanded draft
- 5.3 Data Architecture and Pipeline Design — in expanded draft
- 5.4 High-Level Architecture of Individual Modules
  - 5.4.1 Module 1 — **standalone draft ready** (~580 words; + Figure 5.3)
  - 5.4.2 Module 2 — **standalone draft ready** (~620 words; + Figure 5.4 + Table 5.2)
  - 5.4.3 Module 3 — **standalone draft ready** (~610 words; + Figure 5.5)
- 5.5 Integration and Output Design — **standalone draft ready** (~520 words; + Figure 5.6)
- 5.6 Summary — **standalone draft ready** (~175 words)

## Required Content

- Top-level architecture
- Data flow
- Pipeline design (shared vs module-specific)
- Module interactions
- Design of each module
- Output/report/map generation design

## Required Figures/Tables

- [x] Planned: Figure 5.1 top-level architecture — **created** (`figure_5_1_system_architecture.png` / `.drawio`)
- [x] Planned: Figure 5.2 data flow
- [x] Planned: Figure 5.3 Module 1 — **draw.io + PNG created** (`figure_5_3_module1_architecture.*`)
- [x] Planned: Figure 5.4 Module 2 — **draw.io + PNG created** (`figure_5_4_module2_architecture.*`)
- [x] Planned: Figure 5.5 Module 3 — **draw.io + PNG created** (`figure_5_5_module3_architecture.*`)
- [x] Planned: Figure 5.6 dashboard integration — **draw.io + PNG created** (`figure_5_6_integration_dashboard.*`)
- [x] Planned: Table 5.1 shared vs module-specific
- [x] Planned: Table 5.2 Module 1 vs Module 2 contrast — **in 5.4.2 draft**

## Missing Items

- [x] Expanded Chapter 5 structure accepted (2026-07-30)
- [x] Full conceptual/design draft for sections 5.1–5.6
- [x] Standalone paste-ready drafts for 5.4.1–5.6 + Figures 5.3–5.6
- [ ] Export/redraw Figures 5.1–5.2 for Word (if not already exported)
- [ ] Paste Word update of expanded Chapter 5

## Notes

Architecture must match `CURRENT_ARCHITECTURE.md` and module contexts (Module 2 Stage 2 = isotonic calibration; Module 3 complete with KDE + RF iterative loop).

Primary draft: `research_context/report_drafts/chapter5_analysis_and_design.md`  
Standalone 5.4.1: `research_context/report_drafts/chapter5_5.4.1_module1.md`  
Standalone 5.4.2: `research_context/report_drafts/chapter5_5.4.2_module2.md`  
Standalone 5.4.3: `research_context/report_drafts/chapter5_5.4.3_module3.md`  
Standalone 5.5: `research_context/report_drafts/chapter5_5.5_integration.md`  
Standalone 5.6: `research_context/report_drafts/chapter5_5.6_summary.md`  
Earlier M1/M2 stub: `research_context/report_drafts/chapter5_5.3.1_5.3.2.md` (superseded numbering 5.3.x → 5.4.x)

---

# Chapter 6 - Implementation

## Current Status

Status: **Draft ready** (full hybrid 6.1–6.8, 2026-07-30)

## Possible Sections

- 6.1 Introduction — **draft ready**
- 6.2 Datasets Incorporated (6.2.1–6.2.4) — **draft ready**
- 6.3 Shared Preprocessing and Pipeline Architecture (+ Figure 6.1) — **draft ready**
- 6.4 Implementation of Module 1 (+ Figure 6.2) — **draft ready**
- 6.5 Implementation of Module 2 (+ Figure 6.3) — **draft ready**
- 6.6 Implementation of Module 3 (+ Figure 6.4) — **draft ready**
- 6.7 Output Generation and Early-Warning Dashboard (+ Figure 6.5) — **standalone draft ready** (`chapter6_6.7_dashboard.md`)
- 6.8 Summary — **standalone draft ready** (`chapter6_6.8_summary.md`)
- Chapter 6 topic-by-topic paste-ready set: **complete** (6.1–6.8)

## Required Content

- Data loading and cleaning (Open-Meteo; MoH WER; GADM L1; census population)
- Shared vs module-specific preprocessing (Decision 013)
- Module 1/2/3 Stage 1 and Stage 2 implementation
- Training / walk-forward / spatial CV setup
- Dashboard as read-only consumer (research vs operational tiers)

## Required Figures/Tables

- [x] Table 6.1 epidemiological columns — in draft
- [x] Table 6.2 Open-Meteo aggregation — in draft
- [x] Table 6.3 dataset summary — in draft
- [x] Figures 6.1–6.5 — PNGs in `report_drafts/diagrams/`

## Missing Items

- [x] Hybrid Chapter 6 structure accepted
- [x] Full paste-ready Chapter 6 draft (6.1–6.8)
- [ ] Full Word paste of expanded Chapter 6
- [ ] Final figure export polish for Figures 6.1–6.5 if needed

## Notes

Avoid excessive code screenshots in the main chapter.

Primary draft: `research_context/report_drafts/chapter6_implementation.md` (~4,840 words)  
Earlier M1/M2 stub: `research_context/report_drafts/chapter6_6.2_6.3_m1_m2.md` (superseded numbering 6.3.x → 6.4/6.5)

| Section | Status | Approx. words |
|---|---|---|
| 6.1 Introduction | Draft Complete | 250 |
| 6.2 Datasets (incl. 6.2.1–6.2.4) | Draft Complete | ~1,200 (6.2.1 standalone polished) |
| 6.3 Shared preprocessing | Draft Complete | 430 |
| 6.4 Module 1 | Draft Complete | 880 |
| 6.5 Module 2 | Draft Complete | 900 |
| 6.6 Module 3 | Draft Complete | 920 |
| 6.7 Dashboard | Draft Complete | 430 |
| 6.8 Summary | Draft Complete | 175 |

Key corrections vs interim draft:
- NASA POWER → Open-Meteo
- No CHIRPS/WorldPop/GADM-L2 production stack for Module 3
- Seasonal-naive imputation + `is_imputed`
- Walk-forward + 2-year holdout (M1/M2); spatial CV (M3)
- Module 1 week-53 merge vs Module 2 week-53 keep
- Module 2: Random Forest + isotonic; no SMOTE
- Module 3: KDE + Moran’s I + RF iterative loop (α=0.05); IDW viz-only
- Soft decision-support dashboard (no Command Centre)

---

# Chapter 7 - Evaluation and Results

## Current Status

Status: **Drafting** (accepted full three-module structure, 2026-07-30)

## Accepted Sections

- 7.1 Introduction
- 7.2 Evaluation Strategy (7.2.1–7.2.5)
- 7.3 Module 1: Forecasting Evaluation (7.3.1–7.3.5)
- 7.4 Module 2: Outbreak Classification Evaluation (7.4.1–7.4.5)
- 7.5 Module 3: Spatial Hotspot Evaluation (7.5.1–7.5.5)
- 7.6 Cross-Module Comparative Analysis
- 7.7 Discussion of Results
- 7.8 Summary

## Section Draft Status

| Section | Status | Approx. words |
|---|---|---|
| 7.1 Introduction | Draft Complete | ~200 |
| 7.2 Evaluation Strategy | Draft Complete | ~560 |
| 7.3 Module 1 | Draft Complete | ~920 |
| 7.4 Module 2 | Draft Complete | ~950 |
| 7.5 Module 3 | Draft Complete | ~850 |
| 7.6 Comparative | Draft Complete | ~430 |
| 7.7 Discussion | Draft Complete | ~410 |
| 7.8 Summary | Draft Complete | ~155 |
| **Chapter 7 total** | **Draft ready** | **~4,475** |

## Required Content

- Train/test / walk-forward / holdout explanation (M1/M2)
- Spatial CV explanation (M3)
- Evaluation metrics per module
- Forecasting results (Stage 1 vs Stage 1+2; production stack)
- Classification results (RF; isotonic; alerts/tiers)
- Spatial hotspot results (Moran’s I; α=0.05; honest null aggregate fit)
- Cross-module complementarity (M2-009)
- Interpretation of findings

## Required Figures/Tables

- Chapter 7 topic-by-topic paste-ready set: **complete** (7.1–7.8)
- [x] Tables 7.1–7.2 drafted in chapter prose (M1)
- [x] Tables 7.3–7.4 drafted in chapter prose (M2)
- [x] Tables 7.5–7.6 drafted in chapter prose (M3)
- [x] Table 7.7 drafted in chapter prose (M2-009)
- [ ] Figure 7.1 Evaluation protocol schematic (draw.io pending)
- [x] Figure 7.2 Forecast plots — **created** (`figure_7_2_module1_holdout_forecasts.png`)
- [x] Figure 7.3 Holdout MASE comparison — **created** (`figure_7_3_module1_holdout_mase.png`)
- [x] Figure 7.4 Reliability diagrams — **created** (`figure_7_4_module2_reliability.png`; isotonic, not Platt)
- [x] Figure 7.5 Hotspot / Risk map — **created** (`figure_7_5_module3_risk_surface.png`; 2017 Wk29 peak)

## Missing Items

- [ ] Paste Word figures from `outputs/`
- [ ] Figure 7.1 draw.io export
- [ ] Optional full per-district M1 MASE appendix table

## Notes

Do not invent performance values. Use actual experiment logs only.

Primary draft: `research_context/report_drafts/chapter7_evaluation.md`  
Legacy M1/M2-only draft retained for reference: `chapter7_m1_m2_evaluation.md` (superseded numbering).

Honesty: Module 3 Stage 2 does **not** improve aggregate case-fit (M3-005); operational live/forward outputs are not holdout evidence; Module 2 Stage 1 = Random Forest; thresholds τ=0.14 / high=0.35.

---

# Chapter 8 - Conclusion and Further Work

## Current Status

Status: **Draft ready** (accepted structure 2026-07-30)

## Accepted Sections

- 8.1 Conclusion
- 8.2 Further Work

## Section Draft Status

| Section | Status | Approx. words |
|---|---|---|
| 8.1 Conclusion | Draft Complete | ~700 |
| 8.2 Further Work | Draft Complete | ~480 |
| **Chapter 8 total** | **Draft ready** | **~1,180** |

## Required Content

- Summary of completed work
- Main project contributions (inside 8.1)
- Summary of module outcomes
- Reasonable future improvements (8.2)

## Notes

Primary draft: `research_context/report_drafts/chapter8_conclusion_further_work.md`

Avoid deployment overclaim; align with Chapter 7 evaluation honesty (incl. Module 3 null aggregate fit).

---

# Chapter 9 - Challenges and Limitations

## Current Status

Status: **Draft ready** (accepted structure 2026-07-30)

## Accepted Sections

- 9.1 Introduction
- 9.2 Data and Scope Limitations
- 9.3 Module-Specific Modelling Limitations
- 9.4 Evaluation, Integration, and Decision-Support Limitations
- 9.5 Summary

## Section Draft Status

| Section | Status | Approx. words |
|---|---|---|
| 9.1 Introduction | Draft Complete | ~160 |
| 9.2 Data and Scope | Draft Complete | ~380 |
| 9.3 Module-Specific Modelling | Draft Complete | ~450 |
| 9.4 Evaluation / Integration / Decision-Support | Draft Complete | ~400 |
| 9.5 Summary | Draft Complete | ~140 |
| **Chapter 9 total** | **Draft ready** | **~1,530** |

## Required Content

- Data limitations
- Missing/incomplete records / reporting dynamics
- Weather alignment / point-climate limits
- Temporal and spatial leakage risks
- Module-specific modelling limits
- Deployment / soft decision-support limits

## Notes

Primary draft: `research_context/report_drafts/chapter9_challenges_limitations.md`

Limitations should be honest but professionally written; do not merely repeat Chapter 8 future-work bullets.

---

# References

## Current Status

Status: Not Started

## Required Content

- Dengue epidemiology sources
- Forecasting sources
- Machine learning sources
- Residual modeling sources
- Spatial hotspot/GIS sources
- Dataset/source references
- Tool/library references, if required

## Missing Items

- [ ] Final reference list
- [ ] Check all in-text citations
- [ ] Ensure every reference is cited

---

# Appendices

## Current Status

Status: **Drafting** (Appendix A ready 2026-07-30)

## Required Appendices

- Appendix A: Individual Contribution to the Project — **draft ready** (`report_drafts/appendix_a_individual_contributions.md`)

## Possible Additional Appendices

- Appendix B: Dataset Details
- Appendix C: Feature Dictionary
- Appendix D: Additional Experiment Results
- Appendix E: Hyperparameter Settings
- Appendix F: Code Listings
- Appendix G: Additional Diagrams
- Appendix H: Research Publication Details, if applicable

## Missing Items

- [x] Individual contribution drafts (Appendix A)
- [ ] Supporting screenshots
- [ ] Additional results
- [ ] Extended code or configuration details

---

# Presentation Slides

| Pack | Status | File |
|---|---|---|
| Module 1 slide outline | Outline Ready | `research_context/PRESENTATION_MODULE1_SLIDES.md` |
| Module 1 copy-paste deck | Copy-paste Ready | `research_context/PRESENTATION_MODULE1_COPY_PASTE.md` |
| Module 2 slide outline | Outline Ready | `research_context/PRESENTATION_MODULE2_SLIDES.md` |
| Module 2 copy-paste deck | Copy-paste Ready | `research_context/PRESENTATION_MODULE2_COPY_PASTE.md` |
| Module 3 slide outline | Outline Ready | `research_context/PRESENTATION_MODULE3_SLIDES.md` |
| Module 3 copy-paste deck | Copy-paste Ready | `research_context/PRESENTATION_MODULE3_COPY_PASTE.md` |
| 15-min presentation scripts | Script Ready | `research_context/PRESENTATION_SCRIPTS_15MIN.md` |
| Intro slides (per-slide scripts) | Script Ready | `research_context/PRESENTATION_SCRIPTS_INTRO_SLIDES.md` |
| Printable script — Bandara (214029P) | Script Ready | `research_context/PRESENTATION_SCRIPT_214029P_bandara.md` |
| Printable script — Nethma (214140X) | Script Ready | `research_context/PRESENTATION_SCRIPT_214140X_nethma.md` |
| Printable script — Karunarathna (214099D) | Script Ready | `research_context/PRESENTATION_SCRIPT_214099D_karunarathna.md` |
| Closing scripts (challenges / conclusion / further work) | Script Ready | `research_context/PRESENTATION_SCRIPTS_CLOSING.md` |

Module 1: Figs 6.2/7.2/7.3; Tables 7.1 (headline). Presentation-safe (2026-07-31): negatives/caveats excluded — see each pack’s *Excluded from slides* section.  
Module 2: Figs 6.3/7.4; Tables 7.3–7.4/7.7 (trimmed). RF → isotonic; τ = 0.14.  
Module 3: Figs 6.4/7.5; Table 7.5 (positive rows); feature_importance. Table 7.6 and null-fit excluded from slides.

---

# Change Log for Report Work

Use this section to record major report-related changes.

## 2026-07-31

- Created **Module 1 presentation slide outline** in `research_context/PRESENTATION_MODULE1_SLIDES.md` (gap → design → data → Stage 1/2 → results → limits; figure/table checklist tied to Figs 6.2/7.2/7.3 and Tables 7.1/7.2).
- Created **Module 2 presentation slide outline** in `research_context/PRESENTATION_MODULE2_SLIDES.md` (calibration-as-compensation narrative; Figs 6.3/7.4; Tables 7.3/7.4/7.7; Decision 025 RF + τ = 0.14 numbers).
- Created **Module 3 presentation slide outline** in `research_context/PRESENTATION_MODULE3_SLIDES.md` (KDE/Moran → RF α=0.05; Figs 6.4/7.5; Tables 7.5–7.6; null aggregate-fit guardrails).
- **Revised all three module presentation outlines** to presentation-safe versions: excluded negative results, failed ablations, null-fit tables, partial significance, and questionable caveats from slide content; added *Excluded from slides (report/viva only)* sections to each pack.

## 2026-07-30

- Rewrote **Appendix A — Individuals’ Contribution** in `report_drafts/appendix_a_individual_contributions.md`: completed-project past tense; Module 1/2/3 ownership retained; shared WER scrape / Open-Meteo / spatial-demographic / dashboard / report work split across Bandara, Nethma, and Karunarathna; corrected Open-Meteo / RF+isotonic / α=0.05 facts.
- Drafted complete paste-ready **Chapter 6 Implementation** (`report_drafts/chapter6_implementation.md`, ~4,840 words): Open-Meteo/WER/GADM-L1 stack; Decision 013; M1 SARIMA→XGBoost; M2 RF→isotonic; M3 KDE/Moran→RF α=0.05 + IDW viz-only; Streamlit research/operational tiers; no NASA POWER/CHIRPS/WorldPop production claims.
- Drafted corrected Chapter 1 section **1.1 Introduction** in `research_context/report_drafts/chapter1_1.1_introduction.md` (district-level; residual compensation; early-warning dashboard wording).
- Drafted corrected Chapter 1 section **1.3 Problem in Brief** in `research_context/report_drafts/chapter1_1.3_problem_in_brief.md` (removed fine-scale contradiction; added residual-error and multidimensional risk framing).
- Drafted corrected Chapter 1 section **1.4 Proposed Solution** in `research_context/report_drafts/chapter1_1.4_proposed_solution.md` (aligned Module 1/2 official models; Module 3 design-level; dashboard wording).
- Drafted corrected Chapter 1 section **1.5.2 Objectives** in `research_context/report_drafts/chapter1_1.5.2_objectives.md` (Module 2 = probability calibration, not environmental residual ML).
- Drafted corrected Chapter 1 **Summary** in `research_context/report_drafts/chapter1_1.5_summary.md` (district-level; module-specific compensation meanings; early-warning dashboard).
- Drafted corrected Chapter 3 section **3.2 Technology Adapted** in `research_context/report_drafts/chapter3_3.2_technology_adapted.md` (aligned to `requirements.txt` / Streamlit stack; removed Flask/React/LightGBM/Colab-core claims).
- Drafted corrected Chapter 3 section **3.3 Summary** in `research_context/report_drafts/chapter3_3.3_summary.md`.
- Drafted corrected Chapter 4 section **4.1 Introduction** in `research_context/report_drafts/chapter4_4.1_introduction.md` (module-specific compensation meanings; decision-support wording).
- Accepted expanded Chapter 4 structure (4.1–4.9); updated `REPORT_STRUCTURE.md` and `REPORT_DIAGRAM_PLAN.md`; full draft in `report_drafts/chapter4_our_approach.md`.
- Accepted expanded Chapter 5 structure (5.1–5.6); full draft in `report_drafts/chapter5_analysis_and_design.md`; Module 1/2 figure captions renumbered to 5.3/5.4.

## 2026-07-29

- Started Chapter 4 drafting from interim report `16_Codexon interim_V2.docx`.
- Drafted corrected sections **4.2.1** (Module 1) and **4.2.2** (Module 2) in `research_context/report_drafts/chapter4_4.2.1_4.2.2.md`.
- Drafted corrected Chapter 6 sections **6.2.1**, **6.2.2**, **6.3.1**, **6.3.2** in `research_context/report_drafts/chapter6_6.2_6.3_m1_m2.md` (Open-Meteo; M1/M2 pipelines; Module 3 deferred).
- Drafted corrected Chapter 5 sections **5.3.1** and **5.3.2** in `research_context/report_drafts/chapter5_5.3.1_5.3.2.md`; planned Figures 5.4/5.5 in `REPORT_DIAGRAM_PLAN.md`.
- Drafted Chapters **8** and **9**: `report_drafts/chapter8_conclusion_further_work.md` (~1,180 words; 8.1–8.2) and `report_drafts/chapter9_challenges_limitations.md` (~1,530 words; 9.1–9.5).
- Accepted full Chapter 7 Evaluation structure (7.1–7.8 incl. Module 3) and drafted `research_context/report_drafts/chapter7_evaluation.md` (~4,210 words); legacy M1/M2-only draft retained as `chapter7_m1_m2_evaluation.md`.
- Drafted Chapter 7 Module 1/2 evaluation in `research_context/report_drafts/chapter7_m1_m2_evaluation.md` (replaces interim progress narrative; superseded numbering).
- Consistency fix: Module 2 Stage 1 official model updated to **Random Forest** in Chapters 4–6 drafts and Module 2 draw.io (aligned to M2-005).
- Module 3 subsections intentionally deferred.

## YYYY-MM-DD

- Initial `CHAPTER_STATUS.md` created.
- Status tracker prepared for adaptive final report writing.
