# Team Codexon FYP Report Diagram Plan

**Updated 2026-08-06:** All Module 2 references to "isotonic" as the official Stage 2
calibrator and to τ=0.14/high=0.35 thresholds were corrected to Platt scaling and
τ=0.10/high=0.50 after Decision 047/M2-013 (Random Forest hyperparameter tuning changed
Stage 1's probability distribution enough to flip Stage 2's architecture selection).
Figure 7.4's generator script was also fixed to label the calibrated curve dynamically
from the data rather than a hardcoded name, so this cannot silently go stale again.

**Updated 2026-08-07 (poster-prep audit):** the 2026-08-06 correction above updated this
plan's *text* but the actual Figure 5.1/5.4 diagram files were never regenerated — both
still rendered "Isotonic Regression" until now. Fixed and regenerated (Isotonic → Platt
scaling, "Random Forest" → "Random Forest (tuned)"): `figure_5_1_system_architecture.png`
(via `generate_figure_5_1_architecture.py`) and `figure_5_4_module2_architecture.png`/
`.drawio` (new companion generator `generate_figure_5_4_module2_architecture.py`, so the
PNG can be regenerated after any future drawio text edit instead of drifting again).
Figure 5.6 was also stale on an unrelated axis — it predated the 2026-08-07 dashboard
redesign (Decision — 4-page multipage app) and showed only two evidence tiers, missing
the Prospective Tracking tier added by Decisions 041/048. Corrected: dashboard views now
list the actual four pages (Overview / Research Evidence / Operational Monitoring /
Prospective Tracking) and evidence tiers now show three (Research Evidence / Operational
Prototype / Prospective Tracking). New companion generator:
`generate_figure_5_6_integration_dashboard.py`. Figures 5.3 (Module 1) and 5.5 (Module 3)
were checked against their current `MODULE_CONTEXT.md` files and found already accurate —
not touched.

**Updated 2026-08-08 (Figure 5.1 consistency pass):** a user-drafted alternative
high-level architecture sketch was reviewed against current docs and found to omit the
shared-vs-module-specific preprocessing split (Decision 013) and both cross-module
operational links, and to invent an undocumented "Data/Model Gateway" component. Rather
than adopt that structure, Figure 5.1's existing (already-correct) layered layout was
kept and extended: (1) the Module 1 Stage 2 box now notes "(+ climate lags/anomalies)"
so the diagram no longer implies XGBoost is climate-blind (Decision 001 only makes Stage
1/SARIMA climate-free); (2) a second dashed cross-module arrow, Module 1 → Module 3
"operational forward only (Decision 031)", was added alongside the existing Module 1 →
Module 2 arrow — Module 3's forward hotspot forecast was implemented after this figure's
original design and had never been reflected in it. Also fixed a real drift found while
doing this: `figure_5_1_system_architecture.drawio` (the hand-editable source) still said
"Stage 2: Isotonic calibration" and "RF residual (α=0.05)" even though
`generate_figure_5_1_architecture.py`/the PNG had already been corrected to Platt
scaling / α=1 on 2026-08-07/M3-015 — the drawio file was never brought in sync with the
generator at that time. All three now agree.

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

Show epidemic-threshold labelling → tuned Random Forest baseline probability → Platt-scaling calibration → alert flag and risk tier.

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
Status: Created

Purpose:

Show the main architecture layers with **shared vs module-specific** split (Decision 013):

- Data acquisition
- Shared preprocessing
- Module-specific preprocessing / feature engineering
- Three hybrid modelling modules
- Evaluation design
- Streamlit early-warning dashboard

Caption: Figure 5.1: Top-level architecture of the proposed residual compensation framework.

Files:

- PNG: `research_context/report_drafts/diagrams/figure_5_1_system_architecture.png`
- Alias: `research_context/report_drafts/diagrams/figure_high_level_system_architecture.png`
- Draw.io: `research_context/report_drafts/diagrams/figure_5_1_system_architecture.drawio`
- Generator: `generate_figure_5_1_architecture.py`

Notes:

- Must show shared vs module-specific preprocessing, not one undifferentiated preprocessing block.
- Modules are largely parallel peers; two dashed cross-module arrows required (both real,
  operational-tier only, never used for training/evaluation): M1→M2 "operational forward
  only (Decision 027)" and M1→M3 "operational forward only (Decision 031)".
- Correct models: M1 SARIMA→XGBoost (Stage 2 uses climate lags/anomalies — label this on
  the Stage 2 box, since Decision 001 only makes Stage 1/SARIMA climate-free, not Stage
  2); M2 tuned RF→Platt scaling (Decision 047 — was isotonic before Stage 1 tuning); M3
  KDE/Moran→RF relative residual, α=1 (UPDATED 2026-08-08, M3-015 — was α=0.05).
- **Verified current (2026-08-08)**: PNG regenerated from `generate_figure_5_1_architecture.py`
  — Module 2 column reads "Random Forest (tuned)" → "Platt scaling"; Module 3 column reads
  "RF relative residual (α=1)"; Module 1 Stage 2 box reads "XGBoost residual (+ climate
  lags/anomalies)"; both M1→M2 and M1→M3 dashed operational arrows present.
  `figure_5_1_system_architecture.drawio` brought back in sync with the generator/PNG in
  the same pass (it had drifted — see the 2026-08-08 dated note above).

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
Figure 5.4: High-level architecture of Module 2 — Hybrid Outbreak Risk Classification (tuned Random Forest baseline → Platt-scaling probability compensation → alert / risk-tier outputs)
```

Source / file:

- **Primary (new 4-column layout):** `research_context/report_drafts/diagrams/figure_5_4_module2_architecture.drawio`
- **PNG export:** `research_context/report_drafts/diagrams/figure_5_4_module2_architecture.png` — regenerate via the new
  companion `generate_figure_5_4_module2_architecture.py` after any further drawio text edit.
- Legacy vertical flow: `figure_5_5_module2_architecture.drawio` (superseded layout; still says "isotonic" — kept for
  reference only, not corrected, since it predates the 4-column layout and is not the figure actually used)
- Referenced from: `research_context/report_drafts/chapter5_5.4.2_module2.md`
- **Corrected 2026-08-07**: was still rendering "Isotonic Regression" despite this plan's 2026-08-06 text update —
  drawio + PNG now both say "Platt Scaling" / "Random Forest (tuned)".

Key design facts on the figure:

- Stage 1 official model = **Random Forest** (Decision 025), tuned (Decision 047)
- Stage 2 = **Platt scaling** (probability calibration, not case-residual ML) — flipped from isotonic after Decision 047's Stage 1 tuning
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
Status: **STALE PNG (2026-08-08, M3-015)** — `.drawio` source text corrected (relative-residual formula, α = 1, own-district lags noted as primary), but the `.png` export was NOT regenerated (no draw.io CLI available in this environment — same constraint already documented for Figures 5.4/5.6). Re-export the PNG from the corrected `.drawio` in the draw.io app before final submission.

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
- Stage 2 = **Random Forest** relative-residual learner (own-district lags primary; climate/demographic secondary) + iterative loop `Risk_t = Risk_(t-1) + α · Δ̂ · (Risk_(t-1)+1)` with **α = 1**
- IDW continuous surface = **visualization only**, not a modelling stage
- Scope = GADM Level-1 (25 districts), not DS-division

Notes:

- Keep numeric Moran’s I / MAE / RMSE for Chapter 7.
- UPDATED 2026-08-08 (M3-015): Stage 2, in its final form, DOES improve aggregate case-fit — the figure/caption must not carry the old "does not improve" wording.

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
- **PNG export:** `research_context/report_drafts/diagrams/figure_5_6_integration_dashboard.png` — regenerate via the
  new companion `generate_figure_5_6_integration_dashboard.py` after any further drawio text edit.
- Referenced from: `research_context/report_drafts/chapter5_5.5_integration.md`
- **Corrected 2026-08-07**: predated the 2026-08-07 dashboard redesign (4-page multipage app) and the Prospective
  Tracking evidence tier (Decisions 041/048). Dashboard Views column now lists the actual four pages (Overview /
  Research Evidence / Operational Monitoring / Prospective Tracking); Evidence Tiers column now shows three tiers
  (added Prospective Tracking alongside Research Evidence / Operational Prototype).

Key design facts on the figure:

- Streamlit = read-only consumer (not a fourth modelling stage)
- Magnitude / probability / geography kept distinct (no fused final score)
- Research evidence vs operational prototype tiers
- M1→M2 lag substitution: operational forward only
- No scenario simulation / Command Centre stack

Notes:

- Align with Chapter 4.7 principles; Chapter 5 is the design-depth version.

---

## Figure 6.1: Shared vs Module-Specific Pipeline

Chapter: Chapter 6 - Implementation
Status: **Created (2026-07-30)** — draw.io + PNG ready

Purpose:

Show layered pipeline: raw sources → shared cleaning → module-specific forks → Stage 1/2 → outputs/dashboard.

Caption:

```text
Figure 6.1: Shared preprocessing and module-specific pipeline architecture
```

Source / file:

- `research_context/report_drafts/diagrams/figure_6_1_shared_pipeline.drawio` (+ `.png`)

---

## Figure 6.2: Module 1 Implementation Pipeline

Chapter: Chapter 6 - Implementation
Status: **Created (2026-07-30)** — PNG adapted from Figure 5.3 (`figure_6_2_module1_implementation.png`)

Purpose:

Show Module 1 implementation: preprocessing → SARIMA → residual → XGBoost → final forecast.

Caption:

```text
Figure 6.2: Implementation pipeline of Module 1 — Hybrid Time-Series Case Forecasting
```

---

## Figure 6.3: Module 2 Implementation Pipeline

Chapter: Chapter 6 - Implementation
Status: **Created (2026-07-30)** — PNG adapted from Figure 5.4 (`figure_6_3_module2_implementation.png`)

Purpose:

Show Module 2 implementation: preprocessing → labels → tuned Random Forest → Platt scaling → alert/risk tier.

Caption:

```text
Figure 6.3: Implementation pipeline of Module 2 — Hybrid Outbreak Risk Classification
```

---

## Figure 6.4: Module 3 Implementation Pipeline

Chapter: Chapter 6 - Implementation
Status: **STALE (2026-08-08, M3-015)** — adapted from Figure 5.5, so it inherits that figure's stale `α = 0.05`/absolute-residual labelling (`figure_6_4_module3_implementation.png`). Re-adapt from the corrected Figure 5.5 `.drawio` once that is re-exported.

Purpose:

Show Module 3 implementation: master table → KDE + Moran’s I → RF residual + iterative loop → risk map / IDW viz.

Caption:

```text
Figure 6.4: Implementation pipeline of Module 3 — Hybrid Spatial Hotspot Detection
```

---

## Figure 6.5: Dashboard Output Integration

Chapter: Chapter 6 - Implementation
Status: **Created (2026-07-30)** — PNG adapted from Figure 5.6 (`figure_6_5_dashboard_outputs.png`)

Purpose:

Show versioned module artefacts feeding Streamlit research vs operational views.

Caption:

```text
Figure 6.5: Implementation of module output integration in the early-warning dashboard
```

---

## Figure 6.X (legacy): Feature Engineering Pipeline

Chapter: Chapter 6 - Implementation
Status: Superseded by module-specific Figures 6.2–6.4

Purpose (historical):

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

## Figure 7.1: Evaluation Protocol Schematic

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Show walk-forward folds + untouched holdout for Modules 1/2, research vs operational evidence tiers, and Module 3 spatial K-means CV as a distinct validation axis.

Notes:

- Do not invent metrics on the figure.
- Emphasize that Module 3 does not use the temporal holdout protocol.

---

## Figure 7.2: Module 1 Actual vs Stage 1 vs Stage 1+2 Forecasts

Chapter: Chapter 7 - Evaluation and Results
Status: Created

Purpose:

Show forecasting performance of Module 1 for selected districts (Colombo / Gampaha) on the untouched holdout window.

File:

- `research_context/report_drafts/diagrams/figure_7_2_module1_holdout_forecasts.png`
- Generator: `research_context/report_drafts/diagrams/generate_figure_7_2_7_3.py`

Notes:

- Source: `data/processed/module1/final_combined_predictions.csv` (holdout, non-imputed).
- Do not use `future_forecast_*.png` (operational, no ground truth).
- **Updated 2026-08-07**: the chart now merges in `is_reporting_anomaly` (from
  `weekly_modeling_table.csv`) and annotates the week immediately after any flagged week
  (e.g. Colombo/Gampaha 2026 Wk25, and Colombo's earlier 2026 Wk14 event) with an "X" marker
  + "flagged reporting-delay catch-up spike (§7.3)" callout. Reason: the 2026 Wk25 spike
  (Colombo 1,138 / Gampaha 1,294 actual vs. both forecast lines staying flat) is a dramatic,
  unexplained-looking miss at first glance without this — annotating it turns a scary-looking
  outlier into a demonstrated, already-investigated limitation (Decision 026/028/043) instead
  of something to hide. Generator: `generate_figure_7_2_7_3.py` (data-driven, not hardcoded to
  this one week — will also catch any future flagged week in the holdout window).

---

## Figure 7.3: Module 1 Holdout MASE Comparison (Stage 1 vs Stage 1+2)

Chapter: Chapter 7 - Evaluation and Results
Status: Created

Purpose:

Compare district-level holdout MASE before and after residual compensation.

File:

- `research_context/report_drafts/diagrams/figure_7_3_module1_holdout_mase.png`
- Generator: `research_context/report_drafts/diagrams/generate_figure_7_2_7_3.py`

Notes:

- Source: `outputs/metrics/module1/combined_vs_baseline_metrics.csv` (`fold_id=holdout`).
- Kilinochchi / Mannar shown as non-improved (red diamonds).
- Median Stage 1 MASE ≈ 0.622; median Stage 1+2 MASE ≈ 0.374 (matches Table 7.1 narrative).

---

## Figure 7.4: Module 2 Reliability / Calibration Diagram

Chapter: Chapter 7 - Evaluation and Results
Status: Created

Purpose:

Show Stage 1 raw vs Platt-scaled Stage 2 calibration (reliability diagrams) on validation and holdout.

File:

- `research_context/report_drafts/diagrams/figure_7_4_module2_reliability.png`
- Generator: `research_context/report_drafts/diagrams/generate_figure_7_4.py` (labels the calibrated curve dynamically from the data's `architecture` column, so it cannot silently go stale like this did after Decision 047)

Notes:

- **2026-08-06 update:** regenerated after Decision 047/M2-013 (Random Forest tuning flipped the official Stage 2 architecture from isotonic to Platt). Source: `data/processed/module2/stage2_compensated_predictions.csv` (`architecture=platt`, selected).
- The old note here previously said "do not paste `reliability_diagram_*.png` labelled Platt" — that guidance is now backwards; Platt is the current official architecture. If in doubt, regenerate via the script above rather than trusting either PNG's filename/date.
- Holdout panel is sparse (~40 positives); secondary check only.

---

## Figure 7.5: Module 3 Hybrid Risk / Hotspot Map

Chapter: Chapter 7 - Evaluation and Results
Status: Created

Purpose:

Show Module 3 converged Risk surface for the Stage 1 peak week (2017 Week 29) via IDW visualisation.

File:

- `research_context/report_drafts/diagrams/figure_7_5_module3_risk_surface.png`
- Source artefact: `outputs/figures/module3/risk_surface_peak_week.png`

Notes:

- IDW is visualisation-only (k=4, power=4); not a modelling stage.
- Do not present this map as evidence that Stage 2 improved aggregate case-fit (M3-005 null/negative).
- Optional companion weeks: `risk_surface_2007_wk13.png`, `risk_surface_2021_wk01.png`.

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

## Table 7.1: Module 1 Stage 1 vs Stage 1+2 Headline MASE

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Compare SARIMA baseline vs residual-compensated forecasts (validation aggregate and holdout).

Suggested columns:

- Scope
- Median MASE improvement
- Districts improved
- Notes

Source: Decision 017 / M1-003; `combined_vs_baseline_metrics.csv`

---

## Table 7.2: Module 1 Production Stack Refinement (M1-006B)

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Show holdout MASE/sMAPE before and after reporting-delay feature promotion.

Suggested columns:

- Metric (holdout)
- Pre-promotion
- Post-promotion (current)

Source: Decision 030 / M1-006B

---

## Table 7.3: Module 2 Stage 1 Discrimination

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Compare Stage 1 classifiers under the current harmonic label (k=3.0).

Suggested columns:

- Model
- Median validation PR-AUC
- Holdout PR-AUC / ROC-AUC (for selected model)

Source: Decision 025 / M2-005; official Stage 1 = Random Forest

---

## Table 7.4: Module 2 Stage 2 Calibration, Alerts, and Risk Tiers

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Summarise Platt-scaling BSS selection (was isotonic pre–Decision 047), alert performance at τ=0.10 (was 0.14), and observed outbreak rates by risk tier.

Suggested columns / panels:

- Stage 2 architecture vs median validation BSS
- Alert rule vs recall / precision / F2
- Risk tier vs observed outbreak rate (validation / holdout)

Source: Decision 025 / M2-005; production confirmation

---

## Table 7.5: Module 3 Moran’s I Validation

Chapter: Chapter 7 - Evaluation and Results
Status: Planned

Purpose:

Report aggregated Global Moran’s I and selected weekly checks (including NE-monsoon non-significance).

Suggested columns:

- Check
- Year / Week
- Moran’s I
- p_sim
- Significant

Source: `outputs/metrics/module3/morans_i_validation.csv`; M3-001

---

## Table 7.6: Module 3 Stage 1, Naive Persistence, and Stage 2 Aggregate Fit

Chapter: Chapter 7 - Evaluation and Results
Status: **UPDATED 2026-08-08 (M3-015)** — supersedes the original M3-005 null/negative framing. Comparison of the rescaled KDE baseline, a naive persistence baseline (no model), and the final promoted Stage 2 Risk surface against actual cases. The final Stage 2 model now genuinely improves on both other rows, confirmed via a week-level bootstrap (`outputs/metrics/module3/relative_residual_bootstrap_ci.csv`), not just this aggregate table — cite the bootstrap CIs alongside this table, not the table alone, per the M3-013 lesson that an aggregate table can overstate a result that doesn't survive week-level scrutiny.

Suggested columns:

- Model (Stage 1 alone / Naive persistence / Stage 2 final)
- Correlation
- MAE
- RMSE

Source: `outputs/metrics/module3/stage1_vs_stage2_comparison.csv`, `persistence_baseline_comparison.csv`; M3-010/M3-015

---

## Table 7.7: Module 2 vs Module 1 Threshold Alert Comparison (M2-009)

Chapter: Chapter 7 - Evaluation and Results
Status: Drafted in prose

Purpose:

Show that Module 2 outbreak alerts are not redundant with thresholding Module 1 case forecasts.

Suggested columns:

- Rule
- PR-AUC
- Recall
- Precision
- F2

Source: M2-009 / `outputs/metrics/module2/m2_009_*.csv`

---

# Update Rule

Update this file whenever:

- a new figure/table is planned
- a figure/table is created
- a diagram changes due to architecture updates
- experiment results introduce new plots
- supervisor asks for additional visual material
