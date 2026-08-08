# Chapter 5 — Analysis and Design (Expanded Draft)

**Source of truth:** `CURRENT_ARCHITECTURE.md`, `PIPELINE_ARCHITECTURE_PLAN.md`, Decision 013, Chapter 4 drafts, module contexts  
**Status:** Full design draft for Word paste  
**Last updated:** 2026-07-30  
**Supersedes:** interim figure-only 5.3.x placeholders; renumbers Module 1/2 design from former 5.3.1/5.3.2 → 5.4.1/5.4.2

**Chapter boundary**

| Chapter | Role |
|---|---|
| Chapter 4 | Conceptual what/why |
| **Chapter 5** | Structural design: layers, data flow, stage boundaries, leakage guards, feature groups |
| Chapter 6 | Implementation and exact feature dictionaries |
| Chapter 7 | Metrics and results |

---

## 5.1 Introduction

This chapter presents the analysis and design of the Residual Compensation Modeling Framework for Dengue Risk Prediction. Whereas Chapter 4 introduced the conceptual approach and the meaning of residual compensation across the three modules, the present chapter focuses on structural design: how data move through the system, where shared and module-specific processing boundaries are drawn, how each module’s stages are organised, and how outputs are integrated for early-warning interpretation.

The design goal is not to replace epidemiological judgement with a single opaque predictor, but to organise forecasting, outbreak-risk classification, and spatial hotspot detection as complementary pipelines that correct systematic baseline errors in a controlled way. Traditional one-stage dengue models often absorb temporal structure, climate effects, and risk interpretation into a single step, which can make residual behaviour difficult to diagnose and can encourage leakage-prone preprocessing choices. The proposed design therefore separates baseline modelling from compensation, and separates module-agnostic data cleaning from modelling-specific transformations.

The remainder of the chapter proceeds from the high-level system architecture to data and pipeline design, then to the individual module architectures, and finally to integration and output design. Implementation details and numerical evaluation results are reserved for the subsequent chapters.

**Approx. word count:** 220 words

---

## 5.2 High-Level System Architecture

The high-level architecture of the proposed framework is organised as a modular, pipeline-based system that transforms epidemiological, meteorological, and spatial inputs into complementary dengue risk products. The design is district-week in scope and supports three parallel analytical modules under a common residual compensation philosophy. Figure 5.1 presents the top-level organisation of this architecture.

At the front of the system is the **data acquisition** layer. Historical weekly dengue case counts provide the epidemiological backbone of the framework. District-level meteorological variables such as rainfall, temperature, and humidity represent environmental conditions relevant to transmission. Spatial and contextual inputs—including district boundaries, centroids, elevation, and population—support hotspot analysis in Module 3. These sources are aligned to the same administrative and temporal grain rather than to fine-scale household geolocation.

The acquired data then enter a **shared preprocessing** layer that performs only module-agnostic cleaning and alignment. Shared operations include corrections that every module would make for the same reason, such as consolidating reporting entities into the official 25-district set and constructing a common epidemiological-week calendar. Transformations that exist only to satisfy one baseline model’s assumptions are deliberately excluded from this shared layer.

After shared cleaning, each module applies **module-specific preprocessing and feature engineering**. This separation is a core architectural decision: Module 1 may impose a fixed 52-week calendar for SARIMA, Module 2 may retain week 53 to protect epidemic-threshold labelling, and Module 3 may assemble a spatial master table with elevation and population covariates. Feature construction is likewise module-specific and is designed at the level of feature groups—case lags, climate lags and anomalies, seasonal encodings, residual lags, and related descriptors—while exact feature dictionaries are left to the implementation chapter.

The **hybrid modelling** layer contains the three residual compensation modules. Module 1 combines a climate-free SARIMA baseline with XGBoost residual correction to estimate weekly case magnitude. Module 2 combines a pooled Random Forest baseline probability with isotonic calibration to support outbreak-risk alerts and tiers. Module 3 combines a KDE and Moran’s I spatial baseline with environmental and demographic residual adjustment to produce hotspot interpretations. The modules are designed as complementary peers that share cleaned base tables rather than as a forced sequential dependency chain.

An **evaluation design** layer is part of the architecture even though detailed metrics belong later. Each module is designed around temporally valid walk-forward validation and an untouched holdout block so that residual compensation is assessed under realistic forecasting conditions. Finally, the **output visualisation** layer presents module products through a Streamlit early-warning dashboard. The dashboard is a read-only consumer of versioned forecasts, calibrated risk indicators, and spatial surfaces; it is not a separate training engine and does not claim scenario-simulation command-centre functionality.

As illustrated in Figure 5.1, the architecture therefore proceeds from shared data preparation to module-specific residual compensation and then to integrated decision-support visualisation. The detailed shared versus module-specific preprocessing rules are elaborated in the next section.

**[Insert Figure 5.1 here]**

**Figure 5.1:** Top-level architecture of the proposed residual compensation framework.

**Figure 5.1 content to draw:** data acquisition → shared preprocessing → three module-specific branches (preprocess/features → Stage 1 → Stage 2) → evaluation design → Streamlit dashboard. Show shared vs module-specific split explicitly. Optional dashed M1→M2 “operational forward only.”

**Approx. word count:** 550 words

---

## 5.3 Data Architecture and Pipeline Design

The data architecture distinguishes between shared base tables and module-specific modelling tables. Shared epidemiological weekly data provide district-week case counts and calendar fields. Shared climate weekly data provide aggregated meteorological covariates aligned to the same calendar. Population series support incidence-oriented reporting and Module 3 demographic context. These shared tables are intentionally conservative: they preserve information that later modules may need and avoid imposing one module’s modelling assumptions on the others.

Figure 5.2 shows the resulting data flow. Raw epidemiological, climate, and spatial sources are cleaned into shared tables. Each module then branches into its own preprocessing and feature-engineering path before Stage 1 and Stage 2 modelling. This design prevents silent leakage of SARIMA-specific calendar repairs into classification labelling, and it keeps spatial covariates from being forced into Module 1 Stage 1.

Table 5.1 summarises the principal shared versus module-specific decisions. Week-53 merging, seasonal-naive imputation policy details, and default exclusion of categorical weather codes are Module 1–scoped where they exist to satisfy SARIMA’s fixed seasonal period or Stage 2 feature choices. Module 2 retains week 53 as its own row because merging would distort epidemic-threshold labels and contaminate week-52 historical statistics. Module 3 builds on shared epi-week alignment but adds spatial master-table construction with elevation and population for hotspot modelling.

Feature engineering is designed at group level rather than as an exhaustive dictionary in this chapter. Across modules, the main groups are short-term epidemiological history features, lagged climate and climate-anomaly features, seasonal and monsoon indicators, and module-specific residual or probability-related features. The architecture also encodes leakage guards as design rules: climate anomalies and outbreak labels are computed from strictly prior information within each training window; Module 1 Stage 2 trains on out-of-sample SARIMA residuals rather than in-sample fitted residuals; and imputed or otherwise untrusted case weeks are excluded from evaluation targets or masked before lag construction where required.

**[Insert Figure 5.2 here]**

**Figure 5.2:** Data flow from raw sources through shared and module-specific layers.

**Figure 5.2 content to draw:** raw sources → shared tables → three module-specific prep/feature branches → Stage 1/2 modelling. Do not put week-53 merge in the shared layer.

**[Insert Table 5.1 here]**

**Table 5.1:** Shared versus module-specific preprocessing decisions in the proposed design.

| Decision area | Shared layer | Module 1 | Module 2 | Module 3 |
|---|---|---|---|---|
| District set / Kalmunai→Ampara merge | Yes | Consumes shared | Consumes shared | Consumes shared |
| Epi-week calendar alignment | Yes | Consumes shared | Consumes shared | Consumes shared |
| Week-53 handling | Leave unmerged | Merge into week 52 for SARIMA (`m=52`) | Keep week 53 | Uses shared calendar; no SARIMA merge requirement |
| Missing-week policy | Gaps may remain as absent rows | Seasonal-naive impute + `is_imputed` | Module-specific impute/mask for case-derived features | Module-specific spatial table construction |
| Climate source aggregation | Canonical weekly climate retained | Stage 2 climate/anomaly features; `weather_code` excluded by default | Climate in Stage 1 features; `weather_code` excluded by default | Climate + elevation/population for spatial residual adjustment |
| Population | Interpolated/extrapolated series available | Reporting-layer use | Not a core Stage 1/2 input | Demographic spatial covariate |

As shown in Table 5.1, shared preprocessing is reserved for decisions that are common by necessity. Modelling-specific calendar and feature choices remain inside each module’s pipeline so that residual compensation is evaluated on a design that does not silently bias the other modules. Exact feature dictionaries and implementation scripts are presented in Chapter 6.

**Approx. word count:** 490 words

---

## 5.4 High-Level Architecture of Individual Modules

### 5.4.1 Module 1: Hybrid Time-Series Case Forecasting

The design of Module 1 is organised as a district-level weekly forecasting pipeline with a strict separation between a climate-free temporal baseline and a climate-aware residual compensator. The module estimates expected dengue case magnitude for all 25 administrative districts of Sri Lanka. It does not classify outbreak labels and does not produce spatial hotspot surfaces; those responsibilities belong to Modules 2 and 3. Its role in the overall framework is to provide a quantitative estimate of incidence over short forecasting horizons so that subsequent risk interpretation and alerting can be grounded in a forecast of case burden.

Four design objectives guide the module. First, Stage 1 must capture the regular temporal structure of weekly district case series using an interpretable statistical baseline. Second, climate-driven and nonlinear deviations must remain in the residual, which requires deliberately excluding climate covariates from Stage 1. Third, Stage 2 must learn and correct structured residual error using lagged epidemiological and climate features. Fourth, evaluation must follow temporally valid walk-forward and holdout protocols so that no future information leaks into model selection or residual training.

Figure 5.3 summarises the Module 1 component flow from shared inputs through preprocessing, baseline forecasting, residual extraction, compensation, and final forecast generation.

**[Insert Figure 5.3 here]**

**Figure 5.3:** High-level architecture of Module 1 — Hybrid Time-Series Case Forecasting (SARIMA baseline → residual extraction → XGBoost compensation → final case forecast).

Shared cleaning supplies the 25-district epidemiological and climate tables, but does not apply SARIMA-specific calendar constraints (Decision 013). Module-specific preprocessing merges week 53 into week 52 so that every district-year has exactly 52 rows (`m = 52`), and imputes scrape-gap weeks with a seasonal-naive method while flagging them with `is_imputed` for exclusion from evaluation targets and Stage 2 prediction targets.

Stage 1 fits a per-district SARIMA model on weekly case counts only (Decision 001). Optional `log1p` transformation is a per-district modelling choice, with inverse transformation before residual construction. Orders are selected once per district on the pre-holdout history and then held fixed during walk-forward refitting. The residual interface is:

```text
residual = actual_cases - sarima_prediction
```

Only out-of-sample SARIMA residuals are used for Stage 2 training. Stage 2 uses a pooled XGBoost residual regressor over residual-relevant feature groups: short-term case dynamics, lagged precipitation/temperature/humidity, fold-aware climate anomalies, seasonal/monsoon indicators, the SARIMA prediction, residual lags, and reporting-delay indicators where relevant. Climate anomalies are recomputed within each walk-forward training window so that future climate norms cannot leak into earlier folds. The compensated forecast is:

```text
final_prediction = sarima_prediction + predicted_residual
```

Validation is designed as expanding-window walk-forward validation by year, plus a final untouched multi-year holdout block. As illustrated in Figure 5.3, climate enters only at Stage 2, and residual compensation remains an additive correction of baseline error rather than a replacement forecasting model. The module is positioned as a research decision-support component for district-level public health analysts rather than a clinically certified deployment system.

**Approx. word count:** 580 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter5_5.4.1_module1.md`)*

---

### 5.4.2 Module 2: Hybrid Outbreak Risk Classification

The design of Module 2 complements Module 1 by estimating outbreak risk rather than case magnitude. It operates at the same district-week resolution across all 25 administrative districts and reuses the shared epidemiological and climate base tables, but applies Module 2–specific labelling, preprocessing, and a different interpretation of residual compensation. Whereas Module 1 corrects an additive case-count residual, Module 2 compensates systematic miscalibration in predicted outbreak probability. The module does not forecast weekly case totals and does not produce spatial hotspot surfaces; those responsibilities remain with Modules 1 and 3.

Four design objectives guide the module. First, outbreak labels must be defined in a district- and week-aware manner without leaking future history into the threshold. Second, Stage 1 must produce a usable baseline outbreak probability from epidemiological and climate context. Third, Stage 2 must compensate systematic probability error through a calibrated mapping rather than a literal residual regression on a binary outcome. Fourth, calibrated probabilities must be convertible into interpretable early-warning outputs under temporally valid walk-forward and holdout evaluation.

Figure 5.4 summarises the Module 2 component flow from shared inputs through preprocessing, labelling, baseline classification, probability compensation, and decision outputs.

**[Insert Figure 5.4 here]**

**Figure 5.4:** High-level architecture of Module 2 — Hybrid Outbreak Risk Classification (Random Forest baseline → isotonic probability compensation → alert / risk-tier outputs).

Shared cleaning supplies the 25-district epidemiological and climate tables but does not impose Module 1’s SARIMA calendar constraints (Decision 013). Module 2 keeps week 53 unmerged because merging would alter epidemic-threshold labelling and contaminate week-52 historical statistics. Imputed scrape-gap weeks are flagged with `is_imputed` and masked before derivation of case-based features. Outbreak status is defined by a fold-aware epidemic threshold using historical mean and dispersion estimated from strictly prior years; the production design uses a harmonic seasonal estimator and a tuned multiplier `k`. Undefined labels are excluded from training and scoring.

Stage 1 is a pooled binary classifier with district as a categorical feature. The accepted Stage 1 model is Random Forest, selected after comparison with Logistic Regression and XGBoost under walk-forward validation on the current label definition (Decision 025). Unlike Module 1 Stage 1, Module 2 Stage 1 includes climate features because the task is direct risk discrimination. Class imbalance is handled by class reweighting rather than synthetic oversampling (Decision 026).

Stage 2 receives the Stage 1 predicted probability and applies isotonic regression as the official probability-compensation layer after benchmarking against Platt scaling and a stacked contextual correction model:

```text
calibrated_probability = g(predicted_probability)
```

Secondary decision-support outputs are then derived using fixed absolute probability thresholds: a binary `alert_flag` and a three-level `risk_tier`. Module 2 uses walk-forward validation with a module-specific minimum training-history setting, followed by an untouched holdout block. Discrimination and calibration are both first-class design concerns.

Table 5.2 summarises the design contrast with Module 1.

**[Insert Table 5.2 here]**

**Table 5.2:** Design contrast between Module 1 and Module 2 residual-compensation architectures.

| Design aspect | Module 1 | Module 2 |
|---|---|---|
| Prediction target | Weekly case count | Outbreak risk (binary label → probability) |
| Stage 1 model | Per-district SARIMA | Pooled Random Forest classifier |
| Climate in Stage 1 | Excluded | Included |
| Week-53 policy | Merge into week 52 | Keep unmerged |
| Stage 2 target | Case residual | Probability calibration |
| Stage 2 model | XGBoost regressor | Isotonic regression |
| Final decision output | `final_prediction` (cases) | `calibrated_probability`, `alert_flag`, `risk_tier` |

As shown in Table 5.2, Modules 1 and 2 share a residual-compensation philosophy while differing in stage semantics, climate placement, and calendar handling. This deliberate divergence is part of the framework design: each module’s second stage corrects the error type that remains after its own baseline.

**Approx. word count:** 620 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter5_5.4.2_module2.md`)*

---

### 5.4.3 Module 3: Hybrid Spatial Hotspot Detection

The design of Module 3 addresses geographic concentration of dengue risk at the same district-week grain used by Modules 1 and 2. While the forecasting and classification modules summarise magnitude and outbreak probability for each district-week, they do not by themselves describe how burden is organised across neighbouring districts. Module 3 therefore constructs a spatial baseline risk surface and then adjusts residual spatial structure using environmental and demographic context. The module does not attempt DS-division or point-level geocoded targeting; analysis is constrained to the 25 GADM Level-1 districts so that spatial outputs remain comparable with the temporal modules.

Four design objectives guide the module. First, Stage 1 must produce an interpretable spatial baseline from district-level case intensity and geography. Second, that baseline must be checked for coherent spatial clustering rather than treated as random geographic noise. Third, Stage 2 must compensate systematic differences between observed intensity and the baseline using climate, elevation, and population covariates. Fourth, residual adjustment must be refined through a controlled iterative update so that the final hotspot surface is a compensated spatial risk estimate rather than a one-shot residual overlay.

Figure 5.5 summarises the Module 3 component flow from shared and spatial inputs through the KDE baseline, residual compensation, iterative refinement, and hotspot output.

**[Insert Figure 5.5 here]**

**Figure 5.5:** High-level architecture of Module 3 — Hybrid Spatial Hotspot Detection (KDE + Moran’s I baseline → Random Forest residual compensation → iterative risk update).

Module 3 reuses shared epidemiological and climate tables and joins elevation, interpolated population (and derived population density), and GADM Level-1 boundaries/centroids. It does not inherit Module 1’s week-53 merge or Module 2’s labelling pipeline (Decision 013). Stage 1 uses Kernel Density Estimation over district centroids, weighted by weekly case counts, to produce `KDE_baseline`. Global Moran’s I under queen contiguity is the spatial-clustering checkpoint. The raw density surface is used for scale-invariant Moran’s I; a mass-conserved (rescaled) form of the same spatial shape is used for residual compensation so that

```text
Residual = Actual_case_intensity − Current_Risk
```

is a meaningful Stage 2 target.

Stage 2 trains a Random Forest regressor primarily on own-district lags of the residual, together with lagged climate features, anomalies, monsoon indicators, elevation, population density, and a Mahalanobis anomaly score as secondary context. The residual target is expressed on a relative scale — divided by the current baseline risk — after a diagnostic found the raw (absolute) residual strongly heteroscedastic. Compensation is wrapped in an iterative refinement loop:

```text
Risk_t = Risk_(t-1) + α · predicted_relative_residual_t · (Risk_(t-1) + 1)
```

with the full-magnitude factor `α = 1`. An earlier absolute-scale formulation required shrinkage (`α = 0.05`) because an unshrunk update on that scale diverged; the relative-scale reformulation removed this instability. The loop stops when successive risk changes fall below a tolerance and residual Moran’s I is no longer significant, subject to a small iteration cap. The primary output is the converged hybrid spatial risk surface; continuous IDW rendering is visualisation only, not an additional modelling stage. Quantitative Moran’s I, spatial CV, and Stage 1 vs Stage 2 fit results are reserved for Chapter 7.

**Approx. word count:** 670 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter5_5.4.3_module3.md`)*

---

## 5.5 Integration and Output Design

Integration design concerns how the three module outputs are consumed together without collapsing their distinct meanings. Module 1 contributes compensated district-week case forecasts, Module 2 contributes calibrated outbreak probabilities with alert flags and risk tiers, and Module 3 contributes adjusted spatial hotspot surfaces. Each product answers a different decision-support question: how large the expected burden is, how elevated the outbreak-risk state appears, and where burden is geographically concentrated. Without a dedicated output layer, these products would remain separate analytical artifacts. The early-warning dashboard is therefore designed as the presentation layer that makes magnitude, probabilistic risk, and spatial concentration jointly inspectable.

Figure 5.6 summarises this integration design. As illustrated, the three module outputs feed one decision-support interface while retaining their distinct semantics, so that interpretation can use case magnitude, calibrated risk, and hotspot geography together without forcing them into a single undifferentiated score.

**[Insert Figure 5.6 here]**

**Figure 5.6:** Integration of module outputs into the early-warning dashboard (Streamlit decision-support views with research vs operational evidence tiers).

The accepted output design uses a Streamlit application that reads versioned analytical artifacts rather than retraining models at interaction time. Forecast charts, risk trajectories, alert indicators, district drill-downs, and map overlays are views over module outputs, not a fourth modelling stage. This keeps a clean boundary between research pipelines and visualisation. Where predicted case counts are elevated or calibrated outbreak risk crosses selected alert thresholds, the interface can surface visual alerts and summary indicators. The design does not include intervention scenario simulation or a separate Flask/React command-centre stack, and it does not fuse Modules 1–3 into one opaque “final dengue score.”

A further integration design rule is the separation of evidence tiers. Holdout-validated research outputs remain the basis for claiming model quality in the evaluation chapter. Operational forward products—such as multi-week-ahead forecasts and forward risk scores that may use Module 1 predictions when true future cases are unavailable—are labelled as an operational prototype tier. In the main research architecture, Modules 1 and 2 remain complementary peers sharing cleaned base tables; Module 1 → Module 2 lag substitution is an operational forward convenience rather than a hard training dependency. Intended users are district-level public health analysts and research reviewers who need complementary dengue risk signals in one place. Implementation details of pages, refresh scripts, and artifact paths are presented in Chapter 6.

**Approx. word count:** 520 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter5_5.5_integration.md`)*

---

## 5.6 Summary

This chapter presented the analysis and design of the Residual Compensation Modeling Framework as a modular, pipeline-based architecture for district-level dengue risk prediction in Sri Lanka. The design separates shared, module-agnostic cleaning from module-specific calendar handling and feature construction, then applies two-stage residual compensation within three complementary modules. Module 1 uses a climate-free SARIMA baseline with XGBoost case-residual compensation for weekly case forecasting. Module 2 uses a Random Forest outbreak classifier with isotonic probability calibration for early-warning risk scores. Module 3 uses a KDE spatial baseline, validated by Moran’s I, with Random Forest residual compensation refined through an iterative risk update. Although the modules differ in baseline models, climate placement, and compensation semantics, they share a common district-week scope and leakage-aware walk-forward validation design. Integrated outputs are presented through a Streamlit early-warning dashboard that preserves the distinct meanings of case magnitude, calibrated outbreak risk, and spatial concentration, while separating research-evidence views from operational prototype products. The next chapter describes how this design was implemented in the project pipelines, datasets, and software components.

**Approx. word count:** 175 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter5_5.6_summary.md`)*

---

## Chapter totals and paste checklist

| Section | Approx. words |
|---|---|
| 5.1 | ~220 |
| 5.2 | ~520 |
| 5.3 | ~480 |
| 5.4.1 | ~580 |
| 5.4.2 | ~620 |
| 5.4.3 | ~610 |
| 5.5 | ~520 |
| 5.6 | ~175 |
| **Total** | **~3,505** |

**Notes for Team**
- Figures 5.3–5.6 created as four-column diagrams under `report_drafts/diagrams/`.
- Strip internal notes before final submission.
- Do not claim Module 3 Stage 2 improves aggregate case-fit (null/negative M3-005).
- Do not claim Command Centre / scenario simulation for the dashboard.
