# Team Codexon FYP Report Diagram Plan

## Purpose

This file tracks diagrams, figures, charts, and tables planned for the final report.

Every figure or table used in the final report should have:

- a purpose
- a target chapter
- a proposed caption
- a source or generation method
- a status
- notes about required updates

---

# Status Legend

| Status | Meaning |
|---|---|
| Planned | Figure/table identified but not created |
| Drafted | Initial version created |
| Needs Update | Requires correction based on latest architecture/results |
| Reviewed | Checked by team |
| Finalized | Ready for final report |

---

# Planned Figures

## Figure 4.1: Overview of the Proposed Dengue Risk Prediction Framework

Chapter: Chapter 4 - Proposed Research Framework
Status: Planned

Purpose:

Show the three-module structure of the proposed framework:

1. Hybrid Time-Series Case Forecasting
2. Hybrid Outbreak Risk Classification
3. Hybrid Spatial Hotspot Detection

Notes:

- Should show how epidemiological, climate, temporal, and spatial data enter the framework.
- Should show outputs such as case forecasts, outbreak risk levels, and hotspot maps.
- Must match `CURRENT_ARCHITECTURE.md`.

---

## Figure 4.2: Residual Compensation Workflow

Chapter: Chapter 4 - Proposed Research Framework
Status: Planned

Purpose:

Explain the residual compensation mechanism used in Module 1.

Suggested flow:

```text
Historical weekly dengue cases
        ↓
SARIMA baseline forecast
        ↓
Residual calculation
        ↓
Machine learning residual prediction
        ↓
Final compensated forecast
```

Core equations:

```text
residual = actual_cases - sarima_prediction
final_prediction = sarima_prediction + predicted_residual
```

Notes:

- Use this figure to explain the novelty and core forecasting logic.
- Do not include climate variables in SARIMA stage unless documentation changes.

---

## Figure 5.1: High-Level Architecture of the Proposed Framework

Chapter: Chapter 5 - Analysis and Design
Status: Planned

Purpose:

Show the main architecture/components of the full framework.

Possible components:

- Data sources
- Preprocessing layer
- Feature engineering layer
- Module 1 forecasting service/pipeline
- Module 2 classification service/pipeline
- Module 3 spatial hotspot pipeline
- Output layer

Notes:

- This should be the main architecture diagram.
- Must be cited in the body text.

---

## Figure 5.2: Data Flow Diagram

Chapter: Chapter 5 - Analysis and Design
Status: Planned

Purpose:

Show how raw data becomes model-ready features and outputs.

Possible flow:

```text
Raw dengue data + weather data + spatial data
        ↓
Cleaning and alignment
        ↓
Feature engineering
        ↓
Module-specific modeling
        ↓
Predictions / risk scores / maps
```

Notes:

- Should reflect actual file structure and pipeline stages if finalized.

---

## Figure 5.3: Module Interaction Diagram

Chapter: Chapter 5 - Analysis and Design
Status: Planned

Purpose:

Show how Module 1, Module 2, and Module 3 interact or remain independent.

Notes:

- If modules are independent, clearly show independent outputs.
- If Module 1 outputs feed Module 2 or Module 3, clearly show that dependency.
- Must reflect latest architecture documentation.
- For now, Module 1 and Module 2 can be shown as largely independent production pipelines sharing cleaned base tables; Module 1→Module 2 forecast feed is optional/evaluation-side, not a hard Stage 1 dependency.

---

## Figure 5.4: Module 1 High-Level Architecture

Chapter: Chapter 5 - Analysis and Design
Status: Drafted

Purpose:

Show Module 1 design flow: shared tables → Module 1 preprocessing → SARIMA → residual → Stage 2 features → XGBoost → final forecast.

Caption suggestion:

```text
Figure 5.4: High-level architecture of Module 1 — Hybrid Time-Series Case Forecasting
```

Source / file:

- `research_context/report_drafts/diagrams/figure_5_4_module1_architecture.drawio`
- Also page 1 of `figure_5_4_and_5_5_module1_module2.drawio`

Notes:

- Climate must enter only at Stage 2.
- Include residual and final-prediction equations on the figure or immediately beside it.
- Replaces interim report “Figure 3”.
- Open in [diagrams.net](https://app.diagrams.net/) or the Draw.io VS Code/Cursor extension, then export PNG/SVG for Word.

---

## Figure 5.5: Module 2 High-Level Architecture

Chapter: Chapter 5 - Analysis and Design
Status: Drafted

Purpose:

Show Module 2 design flow: shared tables → Module 2 preprocessing → epidemic-threshold labels → XGBoost probability → isotonic calibration → alert/risk tier.

Caption suggestion:

```text
Figure 5.5: High-level architecture of Module 2 — Hybrid Outbreak Risk Classification
```

Source / file:

- `research_context/report_drafts/diagrams/figure_5_5_module2_architecture.drawio`
- Also page 2 of `figure_5_4_and_5_5_module1_module2.drawio`

Notes:

- Stage 2 is probability calibration, not climate residual regression.
- Show labelling as an explicit box before Stage 1.
- Replaces interim report “Figure 4”.
- Open in diagrams.net, then export PNG/SVG for Word.

---

## Figure 6.1: Dataset Preparation Workflow

Chapter: Chapter 6 - Implementation
Status: Planned

Purpose:

Show the steps from data collection to cleaned dataset.

Possible steps:

```text
Raw epidemiological data
Raw weather data
Raw spatial data
        ↓
Cleaning
        ↓
Temporal alignment
        ↓
District alignment
        ↓
Final model-ready datasets
```

---

## Figure 6.2: Feature Engineering Pipeline

Chapter: Chapter 6 - Implementation
Status: Planned

Purpose:

Show creation of:

- lag features
- rolling features
- seasonal features
- climate features
- residual features
- spatial features

Notes:

- Must match `FEATURE_ENGINEERING_SPEC.md`.

---

## Figure 7.1: Actual vs Predicted Dengue Cases

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Show forecasting performance of Module 1.

Notes:

- Use actual experiment output.
- Do not fabricate values.

---

## Figure 7.2: Forecasting Error / Residual Plot

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Show residual behavior before and/or after compensation.

Notes:

- Useful for explaining whether residual compensation improved the baseline.

---

## Figure 7.3: Outbreak Risk Classification Confusion Matrix

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Show Module 2 classification performance.

Notes:

- Use actual final experiment result.
- Include class labels clearly.

---

## Figure 7.4: Spatial Hotspot Map

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Show Module 3 spatial hotspot output.

Notes:

- Ensure map is readable in grayscale if required by printing guidelines.
- Include legend and district names if possible.

---

# Planned Tables

## Table 2.1: Comparison of Existing Dengue Forecasting Approaches

Chapter: Chapter 2 - Literature Review
Status: Planned

Purpose:

Compare previous studies by:

- method
- input data
- prediction target
- strengths
- limitations
- relevance to this project

---

## Table 3.1: Technologies and Tools Used

Chapter: Chapter 3 - Technologies and Tools Used
Status: Planned

Purpose:

Summarize tools/libraries and their project usage.

Suggested columns:

- Technology/Tool
- Purpose in Project
- Related Module(s)

---

## Table 4.1: Inputs, Processes, and Outputs of Each Module

Chapter: Chapter 4 - Proposed Research Framework
Status: Planned

Purpose:

Summarize the three modules.

Suggested columns:

- Module
- Inputs
- Main Process
- Outputs

---

## Table 6.1: Feature Categories Used in the Framework

Chapter: Chapter 6 - Implementation
Status: Planned

Purpose:

Summarize feature engineering.

Suggested columns:

- Feature Category
- Example Features
- Used By Module
- Purpose

---

## Table 7.1: Forecasting Model Performance Comparison

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Compare baseline and hybrid forecasting results.

Suggested columns:

- Model
- MAE
- RMSE
- MAPE/sMAPE
- Notes

---

## Table 7.2: Classification Model Performance

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Summarize Module 2 classification results.

Suggested columns:

- Model
- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC

---

# Update Rule

Update this file whenever:

- a new figure/table is planned
- a figure/table is created
- a diagram changes due to architecture updates
- experiment results introduce new plots
- supervisor asks for additional visual material
