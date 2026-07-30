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

Chapter: Chapter 4 - Our Approach
Status: Planned (caption/text ready in expanded Chapter 4 draft)

Purpose:

Show the three-module structure of the proposed framework:

1. Hybrid Time-Series Case Forecasting
2. Hybrid Outbreak Risk Classification
3. Hybrid Spatial Hotspot Detection

plus the early-warning dashboard integration layer.

Notes:

- Should show how epidemiological, climate, temporal, and spatial data enter the framework.
- Should show outputs such as case forecasts, outbreak risk levels, and hotspot maps.
- Must match `CURRENT_ARCHITECTURE.md`.
- Caption: Figure 4.1: High-level residual compensation framework for dengue risk prediction.

---

## Figure 4.2: Module 1 Residual Compensation Workflow

Chapter: Chapter 4 - Our Approach
Status: Planned (caption/text ready)

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
XGBoost residual prediction (climate + epi features)
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
- Do not include climate variables in SARIMA stage.
- Caption: Figure 4.2: Two-stage residual compensation workflow for Module 1.

---

## Figure 4.3: Module 2 Outbreak Risk Classification Workflow

Chapter: Chapter 4 - Our Approach
Status: Planned (caption/text ready)

Purpose:

Show epidemic-threshold labelling → Random Forest baseline probability → isotonic calibration → alert flag and risk tier.

Caption: Figure 4.3: Two-stage Module 2 workflow for outbreak risk classification.

---

## Figure 4.4: Module 3 Spatial Hotspot Workflow

Chapter: Chapter 4 - Our Approach
Status: Planned (caption/text ready)

Purpose:

Show KDE + Moran’s I baseline → spatial residual adjustment using environmental/demographic context → hotspot / risk surface.

Caption: Figure 4.4: Two-stage Module 3 workflow for spatial hotspot detection.

---

## Figure 4.5: Integration of Module Outputs into the Early-Warning Dashboard

Chapter: Chapter 4 - Our Approach
Status: Planned (optional)

Purpose:

Show how Module 1/2/3 outputs feed a Streamlit decision-support dashboard (no scenario-simulation claim).

Caption: Figure 4.5: Integration of forecasting, risk classification, and hotspot outputs into the early-warning dashboard.

---

## Table 4.1: Module-wise Meaning of Residual Compensation

Chapter: Chapter 4 - Our Approach
Status: Planned (draft text ready)

Purpose: Contrast case residual correction, probability calibration, and spatial residual adjustment.

---

## Table 4.2: Inputs, Processes, and Outputs by Module

Chapter: Chapter 4 - Our Approach
Status: Planned (draft text ready)

Purpose: Compact IPO summary for Modules 1–3.

---

## Figure 5.1: Top-Level Architecture of the Proposed Framework

Chapter: Chapter 5 - Analysis and Design
Status: Planned (caption/text ready in expanded Chapter 5 draft)

Purpose:

Show the main architecture layers with **shared vs module-specific** split (Decision 013):

- Data acquisition
- Shared preprocessing
- Module-specific preprocessing / feature engineering
- Three hybrid modelling modules
- Evaluation design
- Streamlit early-warning dashboard

Caption: Figure 5.1: Top-level architecture of the proposed residual compensation framework.

Notes:

- Must show shared vs module-specific preprocessing, not one undifferentiated preprocessing block.
- Modules are largely parallel peers; optional dashed M1→M2 for operational forward only.

---

## Figure 5.2: Data Flow Through Shared and Module-Specific Layers

Chapter: Chapter 5 - Analysis and Design
Status: Planned (caption/text ready)

Purpose:

Show raw epi/climate/spatial sources → shared tables → module-specific preprocessing → feature groups → module outputs.

Caption: Figure 5.2: Data flow from raw sources through shared and module-specific layers.

---

## Table 5.1: Shared vs Module-Specific Preprocessing Decisions

Chapter: Chapter 5 - Analysis and Design
Status: Planned (draft text ready)

Purpose: Contrast Decision 013 choices (e.g. week-53 merge Module 1 only; Module 2 keeps week 53).

---

## Figure 5.3: Module 1 High-Level Architecture

Chapter: Chapter 5 - Analysis and Design
Status: **Created (2026-07-30)** — editable draw.io + PNG ready for Word

Purpose:

Show Module 1 design flow in the same four-column layout as the interim figure (Inputs | Stage 1 | Stage 2 | Output), corrected to the current architecture.

Caption:

```text
Figure 5.3: High-level architecture of Module 1 — Hybrid Time-Series Case Forecasting (SARIMA baseline → residual extraction → XGBoost compensation → final case forecast)
```

Source / file:

- **Primary (new 4-column layout):** `research_context/report_drafts/diagrams/figure_5_3_module1_architecture.drawio`
- **PNG export:** `research_context/report_drafts/diagrams/figure_5_3_module1_architecture.png`
- Legacy vertical flow: `figure_5_4_module1_architecture.drawio` (superseded layout; keep for reference)
- Referenced from: `research_context/report_drafts/chapter5_5.4.1_module1.md`

Corrections vs interim Figure (old):

| Old interim figure | Current Figure 5.3 |
|---|---|
| RF / XGBoost residual learner | **XGBoost only** |
| Meteorology Dept / NASA | **Open-Meteo climate API** |
| MAPE, R² | **RMSE, MAE, sMAPE, MASE** |
| No preprocessing shown | draw.io includes Module 1 preprocessing (week-53 merge; seasonal-naive; `is_imputed`) |
| Climate path ambiguous | Explicit: cases → SARIMA; climate/engineered → XGBoost only |

Notes:

- Climate must enter only at Stage 2.
- Residual equations: `Actual − Ŷ_SARIMA` and `Ŷ_SARIMA + Δ̂`.
- Dashed arrow: base prediction used as a Stage 2 feature.
- Open draw.io in diagrams.net to tweak labels before final Word export if needed.

---

## Figure 5.4: Module 2 High-Level Architecture

Chapter: Chapter 5 - Analysis and Design
Status: **Created (2026-07-30)** — editable draw.io + PNG ready for Word

Purpose:

Show Module 2 design flow in the same four-column layout as Figure 5.3 (Inputs | Stage 1 | Stage 2 | Output), corrected to the current architecture.

Caption:

```text
Figure 5.4: High-level architecture of Module 2 — Hybrid Outbreak Risk Classification (Random Forest baseline → isotonic probability compensation → alert / risk-tier outputs)
```

Source / file:

- **Primary (new 4-column layout):** `research_context/report_drafts/diagrams/figure_5_4_module2_architecture.drawio`
- **PNG export:** `research_context/report_drafts/diagrams/figure_5_4_module2_architecture.png`
- Legacy vertical flow: `figure_5_5_module2_architecture.drawio` (superseded layout; keep for reference)
- Referenced from: `research_context/report_drafts/chapter5_5.4.2_module2.md`

Key design facts on the figure:

- Stage 1 official model = **Random Forest** (Decision 025)
- Stage 2 = **isotonic regression** (probability calibration, not case-residual ML)
- Climate included in Stage 1
- Week 53 kept unmerged
- Evaluation: PR-AUC, ROC-AUC, Brier, BSS

Notes:

- Show labelling as an explicit box before / with Stage 1.
- Do not put numeric alert/tier thresholds on the figure (report those in Chapter 7).
- Open draw.io in diagrams.net to tweak labels before final Word export if needed.

---

## Table 5.2: Module 1 vs Module 2 Design Contrast

Chapter: Chapter 5 - Analysis and Design
Status: Planned (draft text ready)

---

## Figure 5.5: Module 3 High-Level Architecture

Chapter: Chapter 5 - Analysis and Design
Status: **Created (2026-07-30)** — editable draw.io + PNG ready for Word

Purpose:

Show Module 3 design flow in the same four-column layout as Figures 5.3/5.4 (Inputs | Stage 1 | Stage 2 | Output).

Caption:

```text
Figure 5.5: High-level architecture of Module 3 — Hybrid Spatial Hotspot Detection (KDE + Moran’s I baseline → Random Forest residual compensation → iterative risk update)
```

Source / file:

- **Primary:** `research_context/report_drafts/diagrams/figure_5_5_module3_architecture.drawio`
- **PNG export:** `research_context/report_drafts/diagrams/figure_5_5_module3_architecture.png`
- Referenced from: `research_context/report_drafts/chapter5_5.4.3_module3.md`

Key design facts on the figure:

- Stage 1 = **KDE + Moran’s I** (district centroids; queen contiguity)
- Stage 2 = **Random Forest** residual learner + iterative loop `Risk_t = Risk_(t-1) + α · Δ̂` with **α = 0.05**
- IDW continuous surface = **visualization only**, not a modelling stage
- Scope = GADM Level-1 (25 districts), not DS-division

Notes:

- Keep numeric Moran’s I / MAE / RMSE for Chapter 7.
- Do not claim Stage 2 improves aggregate case-fit on the figure.

---

## Figure 5.6: Integration and Output Design (Early-Warning Dashboard)

Chapter: Chapter 5 - Analysis and Design
Status: **Created (2026-07-30)** — editable draw.io + PNG ready for Word

Purpose:

Show Module 1/2/3 outputs feeding Streamlit dashboard; research vs operational evidence tiers; dashboard views.

Caption:

```text
Figure 5.6: Integration of module outputs into the early-warning dashboard (Streamlit decision-support views with research vs operational evidence tiers)
```

Source / file:

- **Primary:** `research_context/report_drafts/diagrams/figure_5_6_integration_dashboard.drawio`
- **PNG export:** `research_context/report_drafts/diagrams/figure_5_6_integration_dashboard.png`
- Referenced from: `research_context/report_drafts/chapter5_5.5_integration.md`

Key design facts on the figure:

- Streamlit = read-only consumer (not a fourth modelling stage)
- Magnitude / probability / geography kept distinct (no fused final score)
- Research evidence vs operational prototype tiers
- M1→M2 lag substitution: operational forward only
- No scenario simulation / Command Centre stack

Notes:

- Align with Chapter 4.7 principles; Chapter 5 is the design-depth version.

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
