# Team Codexon FYP Chapter Status Tracker

## Project Title

**A Residual Compensation Modeling Framework for Dengue Risk Prediction**

## Purpose

This file tracks the progress, status, missing items, diagrams, tables, citations, and review notes for each chapter of the final report.

Update this file whenever a chapter or section is drafted, revised, reviewed, or finalized.

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

# Overall Report Status

| Area | Status | Notes |
|---|---|---|
| Front Matter | Not Started | Title page, declaration, dedication, acknowledgement, abstract pending |
| Chapter 1 | Not Started | Introduction and project motivation pending |
| Chapter 2 | Not Started | Literature review and research gap pending |
| Chapter 3 | Not Started | Technology/tools explanation pending |
| Chapter 4 | Not Started | Proposed framework explanation pending |
| Chapter 5 | Not Started | Architecture/design diagrams pending |
| Chapter 6 | Not Started | Implementation details pending |
| Chapter 7 | Not Started | Evaluation results pending |
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

Status: Not Started

## Possible Sections

- 1.1 Introduction
- 1.2 Background and Motivation
- 1.3 Problem Statement / Problem in Brief
- 1.4 Research Gap
- 1.5 Aim and Objectives
- 1.6 Proposed Solution
- 1.7 Research Scope
- 1.8 Summary

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

- [ ] Literature citations for dengue burden
- [ ] Finalized aim
- [ ] Finalized objectives
- [ ] Scope boundaries

## Notes

None yet.

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

Status: Not Started

## Possible Sections

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

## Required Content

- Python usage
- Jupyter Notebook / Cursor IDE usage
- Pandas and NumPy for preprocessing
- Statsmodels / pmdarima for SARIMA, if used
- Scikit-learn / XGBoost / LightGBM for ML, if used
- GeoPandas / Folium / GIS tools, if used
- GitHub and documentation workflow

## Required Figures/Tables

- Optional: Technology stack table

## Missing Items

- [ ] Confirm final library list
- [ ] Confirm final tools used by all modules
- [ ] Add citations if required

## Notes

Avoid generic tool descriptions. Every tool must be connected to project usage.

---

# Chapter 4 - Proposed Research Framework / Our Approach

## Current Status

Status: Not Started

## Possible Sections

- 4.1 Introduction
- 4.2 Overview of the Proposed Framework
- 4.3 Module 1: Hybrid Time-Series Case Forecasting
- 4.4 Module 2: Hybrid Outbreak Risk Classification
- 4.5 Module 3: Hybrid Spatial Hotspot Detection
- 4.6 Residual Compensation Strategy
- 4.7 Integration Between Modules
- 4.8 Inputs, Processes, and Outputs
- 4.9 Summary

## Required Content

- Explain the overall framework
- Explain each module conceptually
- Explain residual compensation
- Explain how modules integrate
- Explain expected inputs and outputs

## Required Figures/Tables

- [ ] Figure: Overall proposed research framework
- [ ] Optional Table: Inputs/processes/outputs by module
- [ ] Optional Figure: Residual compensation concept

## Missing Items

- [ ] Confirm current architecture
- [ ] Confirm module integration flow
- [ ] Confirm final input/output design

## Notes

This chapter should not go too deeply into implementation code.

---

# Chapter 5 - Analysis and Design

## Current Status

Status: Not Started

## Possible Sections

- 5.1 Introduction
- 5.2 High-Level Architecture
- 5.3 Data Architecture
- 5.4 Pipeline Architecture
- 5.5 Module 1 Design
- 5.6 Module 2 Design
- 5.7 Module 3 Design
- 5.8 Integration Design
- 5.9 Output Design
- 5.10 Summary

## Required Content

- Top-level architecture
- Data flow
- Pipeline design
- Module interactions
- Design of each module
- Output/report/map generation design

## Required Figures/Tables

- [ ] Figure: High-level architecture
- [ ] Figure: Data flow diagram
- [ ] Figure: Module interaction diagram
- [ ] Figure: Forecasting pipeline
- [ ] Figure: Classification pipeline
- [ ] Figure: Spatial hotspot pipeline

## Missing Items

- [ ] Final architecture diagram
- [ ] Final pipeline diagram
- [ ] Confirm current file paths and pipeline stages
- [ ] Confirm outputs generated by each module

## Notes

Architecture must match `CURRENT_ARCHITECTURE.md`.

---

# Chapter 6 - Implementation

## Current Status

Status: Not Started

## Possible Sections

- 6.1 Introduction
- 6.2 Dataset Preparation
- 6.3 Data Preprocessing
- 6.4 Feature Engineering
- 6.5 Forecasting Module Implementation
- 6.6 Outbreak Classification Module Implementation
- 6.7 Spatial Hotspot Detection Implementation
- 6.8 Model Training and Experiment Setup
- 6.9 Output Generation
- 6.10 Summary

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
- [ ] Preprocessing workflow figure
- [ ] Feature engineering summary table
- [ ] Model training workflow figure
- [ ] Output examples

## Missing Items

- [ ] Confirm final dataset columns
- [ ] Confirm preprocessing steps
- [ ] Confirm feature list
- [ ] Confirm model algorithms
- [ ] Confirm final implementation screenshots, if needed

## Notes

Avoid excessive code screenshots in the main chapter.

---

# Chapter 7 - Evaluation and Results

## Current Status

Status: Not Started

## Possible Sections

- 7.1 Introduction
- 7.2 Evaluation Strategy
- 7.3 Forecasting Evaluation
- 7.4 Outbreak Classification Evaluation
- 7.5 Spatial Hotspot Evaluation
- 7.6 Comparative Analysis
- 7.7 Discussion
- 7.8 Summary

## Required Content

- Train/test split explanation
- Evaluation metrics
- Forecasting results
- Classification results
- Spatial hotspot results
- Comparison with baseline methods
- Interpretation of findings

## Required Figures/Tables

- [ ] Forecast result plots
- [ ] Actual vs predicted plots
- [ ] Residual error plots
- [ ] Classification report table
- [ ] Confusion matrix
- [ ] ROC/PR curve, if used
- [ ] Hotspot map
- [ ] Model comparison table

## Missing Items

- [ ] Final Module 1 results
- [ ] Final Module 2 results
- [ ] Final Module 3 results
- [ ] Final comparison table
- [ ] Evaluation discussion

## Notes

Do not invent performance values. Use actual experiment logs only.

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

## YYYY-MM-DD

- Initial `CHAPTER_STATUS.md` created.
- Status tracker prepared for adaptive final report writing.
