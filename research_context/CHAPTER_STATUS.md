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
| Chapter 6 - Implementation | 2,500-3,500 |
| Chapter 7 - Evaluation and Results | 2,500-3,500 |
| Chapter 8 - Conclusion and Future Work | 1,000-1,500 |
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
| Chapter 6 | Drafting | 6.2.1/6.2.2/6.3.1/6.3.2 draft ready; Module 3 implementation now complete in code — Ch.6 M3 subsection still to draft |
| Chapter 7 | Drafting | M1/M2 evaluation draft ready; Module 3 results available (`outputs/metrics/module3/`) — Ch.7 M3 subsection still to draft |
| Chapter 8 | Not Started | Conclusion and future work pending |
| Chapter 9 | Not Started | Challenges and limitations pending |
| References | Not Started | Citation list pending |
| Appendices | Not Started | Individual contributions and supporting materials pending |

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

- [x] Planned: Figure 5.1 top-level architecture
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

Status: Drafting

## Possible Sections

- 6.1 Introduction — still outdated in interim (NASA POWER / all-module summary); edit later
- 6.2 Dataset Preparation / Datasets Incorporated
  - 6.2.1 Epidemiological Dataset — **Draft ready**
  - 6.2.2 Meteorological Dataset (Open-Meteo) — **Draft ready**
  - 6.2.3 Spatial/Environmental Datasets — deferred (Module 3)
  - 6.2.4 Dataset Summary — edit later (needs M3 or M1/M2-only summary)
- 6.3 Implementation of Modules
  - 6.3.1 Module 1 Forecasting — **Draft ready** (preprocessing + Stage 1/2)
  - 6.3.2 Module 2 Classification — **Draft ready** (preprocessing + Stage 1/2)
  - 6.3.3 Module 3 Spatial — deferred
- 6.4 Summary — edit later

## Required Content

- Data loading and cleaning
- Handling missing values
- Temporal alignment
- Feature engineering
- SARIMA baseline implementation
- Residual model implementation
- Classification model implementation
- Spatial model/map implementation
- Training and testing setup

## Required Figures/Tables

- [ ] Screenshot/table of dataset structure
- [x] Draft table text: epidemiological columns / Open-Meteo aggregation
- [x] Draft figure text: Module 1 and Module 2 implementation pipelines
- [ ] Feature engineering summary table (final numbers)
- [ ] Model training workflow figure
- [ ] Output examples

## Missing Items

- [x] Confirm meteorological source = Open-Meteo for M1/M2 draft
- [x] Confirm Module 1/2 preprocessing divergences (week 53, climate in Stage 1, isotonic Stage 2)
- [ ] Confirm final screenshots, if needed
- [ ] Paste Word update of interim sections 6.2.1 / 6.2.2 / 6.3.1 / 6.3.2

## Notes

Avoid excessive code screenshots in the main chapter.

Draft location: `research_context/report_drafts/chapter6_6.2_6.3_m1_m2.md`

Key corrections vs interim draft:
- NASA POWER → Open-Meteo
- Seasonal-naive imputation + `is_imputed` (not linear/forward fill as production story)
- Walk-forward + 2-year holdout (not only a simple calendar split narrative)
- Module 1 week-53 merge vs Module 2 week-53 keep
- Module 2 harmonic epidemic threshold (`k=3.0`) + isotonic Stage 2
- Training/model stages added (interim stopped at preprocessing)

---

# Chapter 7 - Evaluation and Results

## Current Status

Status: Drafting

## Possible Sections

- 7.1 Introduction — **Draft ready** (reframed from interim progress narrative)
- 7.2 Evaluation Strategy — **Draft ready**
- 7.3 Module 1 Forecasting Evaluation — **Draft ready**
- 7.4 Module 2 Outbreak Classification Evaluation — **Draft ready**
- 7.5 Comparative Analysis (M2-009) — **Draft ready**
- 7.6 Discussion of Module 1/2 Results — **Draft ready**
- 7.7 Summary — **Draft ready**
- Module 3 evaluation — deferred placeholder

## Required Content

- Train/test split explanation
- Evaluation metrics
- Forecasting results
- Classification results
- Spatial hotspot results
- Comparison with baseline methods
- Interpretation of findings

## Required Figures/Tables

- [x] Draft tables for M1 Stage 1 vs Stage 1+2 / production stack
- [x] Draft tables for M2 Stage 1/2 / alerts / M2-009
- [ ] Forecast result plots (from `outputs/figures/module1/`)
- [ ] Reliability diagrams (from `outputs/figures/module2/`)
- [ ] Confusion / threshold figures if used
- [ ] Hotspot map — deferred

## Missing Items

- [x] Module 1 results sourced from experiment logs / MODULE_CONTEXT
- [x] Module 2 results sourced from M2-005 / production confirmation / M2-009
- [ ] Paste Word figures from outputs/
- [ ] Module 3 results

## Notes

Do not invent performance values. Use actual experiment logs only.

Draft location: `research_context/report_drafts/chapter7_m1_m2_evaluation.md`

Interim Chapter 7 “Discussion / Current Progress” should be fully replaced.

Consistency fix applied 2026-07-29: Module 2 Stage 1 official model = **Random Forest** (post M2-005); Chapters 4–6 drafts and Module 2 draw.io label updated accordingly.

---

# Chapter 8 - Conclusion and Future Work

## Current Status

Status: Not Started

## Possible Sections

- 8.1 Conclusion
- 8.2 Research Contributions
- 8.3 Future Work

## Required Content

- Summary of completed work
- Main project contributions
- Summary of module outcomes
- Reasonable future improvements

## Missing Items

- [ ] Final results summary
- [ ] Confirm contributions
- [ ] Confirm future work points

## Notes

Write this after Chapter 7 is stable.

---

# Chapter 9 - Challenges and Limitations

## Current Status

Status: Not Started

## Possible Sections

- 9.1 Introduction
- 9.2 Data-Related Challenges
- 9.3 Time-Series Modeling Limitations
- 9.4 Classification Limitations
- 9.5 Spatial Analysis Limitations
- 9.6 Integration Challenges
- 9.7 Generalization Limitations
- 9.8 Ethical and Public Health Considerations
- 9.9 Summary

## Required Content

- Data limitations
- Missing/incomplete records
- Weather alignment issues
- Temporal leakage risks
- Spatial validation limits
- Model generalization issues
- Deployment limitations

## Missing Items

- [ ] Confirm known project limitations
- [ ] Confirm limitations observed during experiments
- [ ] Add realistic future mitigation suggestions

## Notes

Limitations should be honest but professionally written.

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

Status: Not Started

## Required Appendices

- Appendix A: Individual Contribution to the Project

## Possible Additional Appendices

- Appendix B: Dataset Details
- Appendix C: Feature Dictionary
- Appendix D: Additional Experiment Results
- Appendix E: Hyperparameter Settings
- Appendix F: Code Listings
- Appendix G: Additional Diagrams
- Appendix H: Research Publication Details, if applicable

## Missing Items

- [ ] Individual contribution drafts
- [ ] Supporting screenshots
- [ ] Additional results
- [ ] Extended code or configuration details

---

# Change Log for Report Work

Use this section to record major report-related changes.

## 2026-07-30

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
- Drafted Chapter 7 Module 1/2 evaluation in `research_context/report_drafts/chapter7_m1_m2_evaluation.md` (replaces interim progress narrative).
- Consistency fix: Module 2 Stage 1 official model updated to **Random Forest** in Chapters 4–6 drafts and Module 2 draw.io (aligned to M2-005).
- Module 3 subsections intentionally deferred.

## YYYY-MM-DD

- Initial `CHAPTER_STATUS.md` created.
- Status tracker prepared for adaptive final report writing.
