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

Possible sections include:

- 4.1 Introduction
- 4.2 Overview of the Proposed Framework
- 4.3 Module 1: Hybrid Time-Series Case Forecasting
- 4.4 Module 2: Hybrid Outbreak Risk Classification
- 4.5 Module 3: Hybrid Spatial Hotspot Detection
- 4.6 Residual Compensation Strategy
- 4.7 Integration Between Modules
- 4.8 Inputs, Processes, and Outputs
- 4.9 Summary

## Notes

This chapter should explain what the project does, why the modules exist, and how the modules are connected, mostly in paragraph form.

It should not go too deeply into code-level details.

Each module subsection (4.3-4.5) should read as a short narrative, not a bulleted feature list. A single inputs/processes/outputs table (4.8) is acceptable as a summary, but it should be preceded and/or followed by prose explaining the table.

## Target Length

Chapter target: 2,000-3,000 words. Each module subsection (4.3-4.5): 400-800 words.

---

# Chapter 5 - Analysis and Design

## Purpose

Present the system/research design, architecture, module interactions, data flow, and pipeline design.

## Adaptive Subtopics

Possible sections include:

- 5.1 Introduction
- 5.2 High-Level Architecture of the Proposed Framework
- 5.3 Data Architecture
- 5.4 Pipeline Architecture
- 5.5 Module 1 Design: Forecasting Pipeline
- 5.6 Module 2 Design: Classification Pipeline
- 5.7 Module 3 Design: Spatial Hotspot Pipeline
- 5.8 Integration Design
- 5.9 Output Design
- 5.10 Summary

## Required Figures

Possible figures include:

- Figure 5.X: High-level architecture of the proposed dengue risk prediction framework
- Figure 5.X: Data flow of the proposed framework
- Figure 5.X: Module interaction diagram
- Figure 5.X: Residual compensation workflow

## Notes

At least one top-level architecture diagram should be included.

Every diagram should be cited in the body text and followed by a paragraph interpreting it, not left to stand alone (see Figure and Table Style in `REPORT_STYLE_GUIDE.md`).

The architecture must match `CURRENT_ARCHITECTURE.md`.

## Target Length

Chapter target: 2,500-3,500 words. Each module design subsection (5.5-5.7): 400-800 words.

---

# Chapter 6 - Implementation

## Purpose

Explain how the proposed design was implemented.

## Adaptive Subtopics

Possible sections include:

- 6.1 Introduction
- 6.2 Dataset Preparation
- 6.3 Data Preprocessing
- 6.4 Feature Engineering
- 6.5 Implementation of Module 1: Forecasting
- 6.6 Implementation of Module 2: Outbreak Risk Classification
- 6.7 Implementation of Module 3: Spatial Hotspot Detection
- 6.8 Model Training and Experiment Setup
- 6.9 Output Generation and Visualization
- 6.10 Summary

## Notes

This chapter should be consistent with the design chapter, and written mostly in narrative form describing what was done and why, rather than as a bare sequence of bullet points.

Short ordered lists are acceptable for describing a strict processing sequence (e.g., exact preprocessing steps), but each step should still be explained rather than left as a bare label.

Avoid placing too many raw code screenshots in the main body.

Detailed code, extended screenshots, or additional outputs can be moved to appendices.

## Target Length

Chapter target: 2,500-3,500 words. Each module implementation subsection (6.5-6.7): 400-800 words.

---

# Chapter 7 - Evaluation and Results

## Purpose

Present the evaluation design, experimental results, model performance, comparisons, and interpretation.

## Adaptive Subtopics

Possible sections include:

- 7.1 Introduction
- 7.2 Evaluation Strategy
- 7.3 Module 1: Forecasting Evaluation
- 7.4 Module 2: Outbreak Classification Evaluation
- 7.5 Module 3: Spatial Hotspot Evaluation
- 7.6 Comparative Analysis
- 7.7 Discussion of Results
- 7.8 Summary

## Possible Metrics

For forecasting: MAE, RMSE, MAPE, sMAPE, residual error analysis.

For classification: accuracy, precision, recall, F1-score, ROC-AUC, confusion matrix, calibration metrics, if used.

For spatial hotspot detection: visual hotspot validation, spatial clustering quality, Moran's I, if used, LISA analysis, if used, comparison with observed dengue concentration patterns.

## Notes

Do not invent result values. Use actual experiment logs.

Every metric or number reported must be followed by a paragraph interpreting what it means, not left as a bare figure or bullet (see Evaluation Chapter Style in `REPORT_STYLE_GUIDE.md`).

If final results are not yet available, use placeholders.

## Target Length

Chapter target: 2,500-3,500 words. Each module evaluation subsection (7.3-7.5): 400-800 words.

---

# Chapter 8 - Conclusion and Future Work

## Purpose

Summarize the completed research, explain the main contributions, and describe realistic future improvements.

## Adaptive Subtopics

Possible sections include:

- 8.1 Conclusion
- 8.2 Research Contributions
- 8.3 Future Work
- 8.4 Summary, if required

## Notes

Avoid claiming full real-world deployment unless it was actually completed.

Conclusion should be aligned with actual evaluation results, written in reflective prose rather than a bullet-point recap.

## Target Length

Chapter target: 1,000-1,500 words. Each subsection: 250-500 words.

---

# Chapter 9 - Challenges and Limitations

## Purpose

Discuss limitations and challenges honestly and academically.

## Adaptive Subtopics

Possible sections include:

- 9.1 Introduction
- 9.2 Data-Related Challenges
- 9.3 Time-Series Modeling Limitations
- 9.4 Classification Limitations
- 9.5 Spatial Analysis Limitations
- 9.6 Integration Challenges
- 9.7 Generalization Limitations
- 9.8 Ethical and Public Health Considerations
- 9.9 Summary

## Possible Issues to Discuss

Limited data availability, missing values, inconsistent data formats, underreporting of dengue cases, weather data alignment issues, temporal leakage risk, spatial leakage risk, model generalization limits, district-level aggregation limitations, difficulty validating predicted hotspots, lack of real-time deployment.

## Notes

Each limitation should be explained as connected reasoning (cause, effect, and possible mitigation), not a bare list of one-line issues. A short list may be used to name the categories of limitation, but each named item must then be discussed in a paragraph.

## Target Length

Chapter target: 1,200-2,000 words. Each subsection (9.2-9.8): 200-400 words.

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
