# Team Codexon FYP Final Report Structure

## Project Title

**A Residual Compensation Modeling Framework for Dengue Risk Prediction**

## Purpose of This File

This file maintains the current working structure of the final report.

This structure is not fixed. It should evolve based on:

- Supervisor feedback
- University final report expectations
- The latest sample report format
- Actual project implementation
- Final experiment results
- Current research decisions
- Final defense requirements

The old final report guideline should be treated as a minimum academic formatting guide. The newer sample report should be treated as a modern structural reference. However, the final report must be customized for this dengue risk prediction project.

For writing style, prose-vs-bullet usage, and word count targets, see `research_context/REPORT_STYLE_GUIDE.md`. This file focuses on structure (chapters and subsections); that file focuses on how each subsection should be written.

---

# Report Structuring Principle

The report should follow a professional final year research report flow, but subsection names must be adjusted to match the actual project.

Do not blindly copy subsection names from any sample report.

Use the sample report for:

- general organization
- chapter-level flow
- front matter arrangement
- use of figures and captions
- module-wise explanation style
- implementation and evaluation presentation style

Do not copy the sample report's:

- project-specific headings
- healthcare/psychiatric module structure
- wording
- dataset descriptions
- model explanations
- results

---

# Current High-Level Report Structure

## Front Matter

Suggested order:

1. Cover Page
2. Title Page
3. Declaration / Certification Page
4. Dedication
5. Acknowledgement
6. Abstract
7. Table of Contents
8. List of Figures
9. List of Tables
10. List of Abbreviations, if required

Notes:

- The abstract should summarize the problem, approach, modules, implementation, and key outcomes in flowing prose, not bullet points (target: 250-400 words; see `REPORT_STYLE_GUIDE.md`).
- Avoid citations in the abstract unless the department specifically requires them.
- The table of contents, list of figures, and list of tables should be generated after pagination is finalized.

---

# Chapter 1 - Introduction

## Purpose

Introduce the dengue risk prediction problem, explain why the project is important, define the research aim and objectives, and summarize the proposed solution.

## Adaptive Subtopics

Possible sections include:

- 1.1 Introduction
- 1.2 Background and Motivation
- 1.3 Problem in Brief / Problem Statement
- 1.4 Research Gap
- 1.5 Aim and Objectives
- 1.6 Proposed Solution
- 1.7 Research Scope
- 1.8 Summary

## Notes

The exact subsection names may be changed based on supervisor preference.

This chapter should clearly explain, mostly in paragraph form, the following points:

- why dengue prediction is important
- why forecasting alone is not enough
- why outbreak risk classification is useful
- why spatial hotspot mapping is useful
- why a hybrid residual compensation framework is proposed

Only the Aim and Objectives subsection should use a numbered/bulleted list (for the objectives themselves); every other subsection should be written as connected prose per `REPORT_STYLE_GUIDE.md`.

## Target Length

Chapter target: 1,500-2,500 words. Standard subsections: 250-500 words each; the Introduction subsection (1.1): 120-250 words; Summary (1.8): 100-200 words.

---

# Chapter 2 - Literature Review

## Purpose

Review existing work related to dengue prediction, outbreak forecasting, machine learning models, residual modeling, and spatial hotspot detection.

## Adaptive Subtopics

Possible sections include:

- 2.1 Introduction
- 2.2 Dengue as a Public Health Problem
- 2.3 Epidemiological and Climate Factors in Dengue Transmission
- 2.4 Time-Series Forecasting for Dengue Cases
- 2.5 Machine Learning for Dengue Prediction
- 2.6 Hybrid Forecasting and Residual Correction Approaches
- 2.7 Outbreak Risk Classification Methods
- 2.8 Spatial Hotspot Detection and GIS-Based Disease Mapping
- 2.9 Comparison of Existing Approaches
- 2.10 Research Gap
- 2.11 Summary

## Suggested Tables

- Table 2.X: Comparison of dengue forecasting studies
- Table 2.X: Comparison of time-series, machine learning, and hybrid approaches
- Table 2.X: Summary of spatial hotspot detection methods

## Notes

This chapter must contain citations and should be written as connected discussion, not a bullet-point summary per paper. Each subsection should synthesize multiple sources into a coherent narrative, not list one paper per bullet.

Comparison tables (2.9) should always be followed by a discussion paragraph interpreting the comparison, not left to stand alone.

The research gap should lead naturally into the proposed three-module framework.

## Target Length

This is one of the longest chapters. Chapter target: 2,500-3,500 words. Major analytical subsections (2.4-2.9): 400-800 words each.

---

# Chapter 3 - Technologies and Tools Used

## Purpose

Explain the technologies, tools, libraries, and platforms used in the project, but only in relation to how they support the research.

## Adaptive Subtopics

Possible sections include:

- 3.1 Introduction
- 3.2 Programming Language
- 3.3 Development Environment
- 3.4 Data Processing Libraries
- 3.5 Time-Series Forecasting Libraries
- 3.6 Machine Learning Libraries
- 3.7 Spatial Analysis and Mapping Tools
- 3.8 Visualization Tools
- 3.9 Version Control and Documentation Tools
- 3.10 Summary

## Possible Technologies

- Python
- Jupyter Notebook
- Cursor IDE
- Pandas
- NumPy
- Scikit-learn
- Statsmodels
- pmdarima
- XGBoost
- LightGBM
- Matplotlib
- Seaborn
- GeoPandas
- Folium
- Git and GitHub

## Notes

Do not write a generic technology description or a bare bullet list of features.

For each technology, explain in paragraph form:

- why it was selected
- where it was used in the project
- how it supports dengue risk prediction

A summary table (Table 3.1) listing all tools is acceptable, but each technology should still be discussed in prose beforehand, per `REPORT_STYLE_GUIDE.md`.

## Target Length

Chapter target: 1,200-2,000 words. Each technology subsection: roughly 150-350 words depending on how central the tool is to the project.

---

# Chapter 4 - Proposed Research Framework / Our Approach

## Purpose

Describe the proposed solution conceptually before going into detailed design and implementation.

## Adaptive Subtopics

Current accepted structure (2026-07-30):

- 4.1 Introduction
- 4.2 Overview of the Proposed Framework
- 4.3 Residual Compensation Strategy
- 4.4 Module 1: Hybrid Time-Series Case Forecasting
  - 4.4.1 Purpose and scope
  - 4.4.2 Stage 1 baseline (SARIMA)
  - 4.4.3 Stage 2 residual compensation (XGBoost)
  - 4.4.4 Expected outputs and users
- 4.5 Module 2: Hybrid Outbreak Risk Classification
  - 4.5.1 Purpose and label concept
  - 4.5.2 Stage 1 baseline classifier
  - 4.5.3 Stage 2 probability compensation
  - 4.5.4 Expected outputs and users
- 4.6 Module 3: Hybrid Spatial Hotspot Detection
  - 4.6.1 Purpose and scope
  - 4.6.2 Stage 1 spatial baseline (KDE and Moran’s I)
  - 4.6.3 Stage 2 spatial residual adjustment
  - 4.6.4 Expected outputs and users
- 4.7 System Integration and Early Warning Dashboard
- 4.8 Inputs, Processes, and Outputs Summary
- 4.9 Summary

## Notes

This chapter should explain what the project does, why the modules exist, and how the modules are connected, mostly in paragraph form.

It should not go too deeply into code-level details, file paths, fold counts, or evaluation metric tables (those belong in Chapters 5–7).

Each module section should read as a narrative. A single inputs/processes/outputs table (4.8) is acceptable as a summary, but it should be preceded and/or followed by prose explaining the table.

Compensation meanings differ by module: Module 1 = case residual correction; Module 2 = probability calibration; Module 3 = spatial residual adjustment.

## Target Length

Chapter target: 2,500–3,200 words. Module sections (4.4–4.6): 400–700 words each.

---

# Chapter 5 - Analysis and Design

## Purpose

Present the system/research design, architecture, module interactions, data flow, and pipeline design.

## Adaptive Subtopics

Current accepted structure (2026-07-30):

- 5.1 Introduction
- 5.2 High-Level System Architecture
- 5.3 Data Architecture and Pipeline Design
- 5.4 High-Level Architecture of Individual Modules
  - 5.4.1 Module 1: Hybrid Time-Series Case Forecasting
  - 5.4.2 Module 2: Hybrid Outbreak Risk Classification
  - 5.4.3 Module 3: Hybrid Spatial Hotspot Detection
- 5.5 Integration and Output Design
- 5.6 Summary

## Required Figures / Tables

- Figure 5.1: Top-level architecture (shared vs module-specific split)
- Figure 5.2: Data flow through shared and module-specific layers
- Figure 5.3: Module 1 architecture
- Figure 5.4: Module 2 architecture
- Figure 5.5: Module 3 architecture
- Figure 5.6: Dashboard integration design
- Table 5.1: Shared vs module-specific preprocessing decisions
- Table 5.2: Module 1 vs Module 2 design contrast

## Notes

Chapter 5 is structural design (components, stage boundaries, leakage guards, feature groups). It must not repeat Chapter 4’s conceptual what/why at length, and must not dump Chapter 6 feature dictionaries or Chapter 7 metric tables.

Decision 013 is mandatory: shared preprocessing is module-agnostic only; SARIMA-specific transforms stay in Module 1.

Architecture must match `CURRENT_ARCHITECTURE.md`. Module 2 Stage 2 = isotonic calibration.

## Target Length

Chapter target: 2,800–3,500 words. Module design subsections (5.4.1–5.4.3): 400–700 words each.

---

# Chapter 6 - Implementation

## Purpose

Explain how the proposed design was implemented in datasets, pipelines, module stages, and dashboard outputs.

## Accepted Structure (hybrid, 2026-07-30)

- 6.1 Introduction
- 6.2 Datasets Incorporated
  - 6.2.1 Epidemiological dataset
  - 6.2.2 Meteorological dataset (Open-Meteo)
  - 6.2.3 Spatial / demographic datasets (Module 3)
  - 6.2.4 Dataset summary table
- 6.3 Shared Preprocessing and Pipeline Architecture
- 6.4 Implementation of Module 1
  - 6.4.1 Module-specific preprocessing
  - 6.4.2 Stage 1 SARIMA
  - 6.4.3 Stage 2 features + XGBoost residual compensation
  - 6.4.4 Training, validation artefacts, outputs
- 6.5 Implementation of Module 2
  - 6.5.1 Module-specific preprocessing + labelling
  - 6.5.2 Stage 1 Random Forest
  - 6.5.3 Stage 2 isotonic calibration + alert/risk tiers
  - 6.5.4 Training, validation artefacts, outputs
- 6.6 Implementation of Module 3
  - 6.6.1 Master table / spatial prep
  - 6.6.2 Stage 1 KDE + Moran’s I
  - 6.6.3 Stage 2 RF residual + iterative loop
  - 6.6.4 Risk-surface rendering (IDW viz-only) + outputs
- 6.7 Output Generation and Early-Warning Dashboard
- 6.8 Summary

## Notes

Must match Chapter 5 design and living module contexts. Climate source = Open-Meteo (not NASA POWER). Module 3 = district-level (GADM L1); no CHIRPS/WorldPop production raster stack. Module 2 Stage 2 = isotonic calibration.

Short ordered lists are acceptable for true processing sequences only. Avoid raw code dumps in the main body.

## Planned Figures/Tables

- Table 6.1 Epidemiological columns
- Table 6.2 Open-Meteo aggregation
- Table 6.3 Dataset summary
- Figure 6.1 Shared vs module-specific pipeline
- Figure 6.2 Module 1 implementation
- Figure 6.3 Module 2 implementation
- Figure 6.4 Module 3 implementation
- Figure 6.5 Dashboard outputs

## Target Length

Chapter target: 3,000–4,000 words. Each module implementation block (6.4–6.6): 700–1,000 words total.

---

# Chapter 7 - Evaluation and Results

## Purpose

Present the evaluation design, experimental results, model performance, comparisons, and interpretation.

## Accepted Structure (full three-module, 2026-07-30)

- 7.1 Introduction
- 7.2 Evaluation Strategy
  - 7.2.1 Common principles (walk-forward, holdout, leakage, evidence tiers)
  - 7.2.2 Module 1 metrics and protocol
  - 7.2.3 Module 2 metrics and protocol
  - 7.2.4 Module 3 metrics and protocol
  - 7.2.5 Scope boundaries (what is not claimed)
- 7.3 Module 1: Forecasting Evaluation
  - 7.3.1 Experimental setup
  - 7.3.2 Stage 1 vs Stage 1+2 residual compensation
  - 7.3.3 Statistical significance (Diebold–Mariano)
  - 7.3.4 Production stack refinement (M1-006B)
  - 7.3.5 Interpretation and limits
- 7.4 Module 2: Outbreak Classification Evaluation
  - 7.4.1 Experimental setup and outbreak labelling
  - 7.4.2 Stage 1 discrimination (Random Forest / PR-AUC)
  - 7.4.3 Stage 2 calibration compensation (isotonic / BSS)
  - 7.4.4 Alert thresholds and risk tiers
  - 7.4.5 Rejected ablations (brief, evidence-backed)
- 7.5 Module 3: Spatial Hotspot Evaluation
  - 7.5.1 Experimental setup (spatial CV; not temporal holdout)
  - 7.5.2 Stage 1 KDE baseline and Moran’s I validation
  - 7.5.3 Stage 2 RF residual adjustment and α-update convergence
  - 7.5.4 Stage 1 vs Stage 2 aggregate fit (honest null/negative)
  - 7.5.5 Interpretation and limits
- 7.6 Cross-Module Comparative Analysis
- 7.7 Discussion of Results
- 7.8 Summary

## Metrics (module-specific)

- Module 1: MAE, RMSE, sMAPE, MASE (m=52), Diebold–Mariano, residual variance / Ljung–Box
- Module 2: PR-AUC (primary Stage 1), ROC-AUC, Brier, BSS (primary Stage 2), alert recall/precision/F2, risk-tier rates
- Module 3: Moran’s I (aggregated + selected weeks), spatial CV residual MAE/RMSE, Stage 1 vs Stage 2 corr/MAE/RMSE, feature importance

## Notes

Do not invent result values. Use actual experiment logs / `outputs/metrics/`.

Every metric or number reported must be followed by a paragraph interpreting what it means (see Evaluation Chapter Style in `REPORT_STYLE_GUIDE.md`).

Research vs operational evidence tiers must remain separated (Decisions 018, 027). Module 3 uses spatial CV, not the Module 1/2 temporal holdout. Module 3 Stage 2 must not be claimed to improve aggregate case-fit (M3-005).

## Planned Figures/Tables

- Figure 7.1 Evaluation protocol schematic
- Figure 7.2 Module 1 actual vs Stage 1 vs Stage 1+2
- Figure 7.3 Module 1 holdout MASE comparison
- Figure 7.4 Module 2 reliability / calibration diagram
- Figure 7.5 Module 3 hybrid risk / hotspot map
- Table 7.1 Module 1 Stage 1 vs Stage 1+2 headline MASE
- Table 7.2 Module 1 production stack (M1-006B)
- Table 7.3 Module 2 Stage 1 discrimination
- Table 7.4 Module 2 Stage 2 / alerts / risk tiers
- Table 7.5 Module 3 Moran’s I
- Table 7.6 Module 3 Stage 1 vs Stage 2 aggregate fit
- Table 7.7 Module 2 vs Module 1 threshold alert comparison (M2-009)

## Target Length

Chapter target: 3,200–4,500 words. Each module evaluation block (7.3–7.5): 650–950 words.

---

# Chapter 8 - Conclusion and Further Work

## Purpose

Summarize the completed research, explain the main contributions, and describe realistic future improvements.

## Accepted Structure (2026-07-30)

- 8.1 Conclusion
- 8.2 Further Work

## Notes

Contributions are synthesised inside 8.1 rather than as a separate numbered section, matching the team’s preferred two-part chapter layout.

Avoid claiming full real-world deployment unless it was actually completed.

Conclusion should be aligned with actual evaluation results, written in reflective prose rather than a bullet-point recap.

Further work must be realistic and tied to known limitations (Module 3 null aggregate fit, reporting delay, finer spatial grain, operational validation).

## Target Length

Chapter target: 1,000–1,500 words. 8.1: 550–850 words. 8.2: 400–600 words.

---

# Chapter 9 - Challenges and Limitations

## Purpose

Discuss limitations and challenges honestly and academically.

## Accepted Structure (2026-07-30)

- 9.1 Introduction
- 9.2 Data and Scope Limitations
- 9.3 Module-Specific Modelling Limitations
- 9.4 Evaluation, Integration, and Decision-Support Limitations
- 9.5 Summary

## Notes

Each limitation should be explained as connected reasoning (cause, effect, and possible mitigation), not a bare list of one-line issues.

Do not duplicate Chapter 8’s future-work wishlist at length; Chapter 9 diagnoses constraints, while Chapter 8 proposes next steps.

Soft decision-support wording: no clinical diagnosis, guaranteed outbreak prevention, or command-centre deployment claims.

## Target Length

Chapter target: 1,200–2,000 words. Subsections 9.2–9.4: 300–450 words each.

---

# References

## Purpose

List all sources cited in the report.

## Notes

All references cited in the body must appear in the reference list.

All references in the reference list should be cited inside the report.

Use the citation style required by the department or supervisor (see Citation Style in `REPORT_STYLE_GUIDE.md`).

---

# Appendices

## Required Appendix

- Appendix A: Individual Contribution to the Project

## Possible Additional Appendices

- Appendix B: Dataset Details
- Appendix C: Feature Dictionary
- Appendix D: Additional Experimental Results
- Appendix E: Model Hyperparameters
- Appendix F: Screenshots or Code Listings
- Appendix G: Additional Diagrams
- Appendix H: Research Publication Details, if applicable

---

# Current Status

This structure is a working version.

Update this file whenever:

- supervisor gives new instructions
- chapter order changes
- new sections are added
- sections are removed
- project architecture changes
- final evaluation results affect report organization

For actual drafting progress, word counts achieved, and per-chapter missing items, see `research_context/CHAPTER_STATUS.md`. For diagram and table tracking, see `research_context/REPORT_DIAGRAM_PLAN.md`.
