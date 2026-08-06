# Chapter 4 — Sections 4.8 and 4.9

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 4.7 System Integration and Early Warning Dashboard  
**Next chapter:** Chapter 5 — Analysis and Design

---

## 4.8 Inputs, Processes, and Outputs Summary

The preceding sections described each module of the Residual Compensation Modeling Framework in narrative form. Table 4.2 summarises the corresponding inputs, processes, and outputs so that the overall approach can be compared at a glance. The table is a condensation of the conceptual design presented in Sections 4.4 to 4.7; it is not a substitute for those module discussions, and it does not replace the detailed feature dictionaries reserved for the design and implementation chapters.

**[Insert Table 4.2 here]**

**Table 4.2:** Inputs, processes, and outputs of the three modules in the proposed framework.

| Module | Main inputs | Core process | Main outputs |
|---|---|---|---|
| Module 1: Hybrid Time-Series Case Forecasting | Weekly district dengue case counts; lagged climate and temporal/seasonal features for Stage 2 | Climate-free SARIMA baseline → XGBoost residual compensation | Compensated weekly case forecast (`final_prediction`) |
| Module 2: Hybrid Outbreak Risk Classification | Weekly district case counts; climate and seasonal features; epidemic-threshold outbreak labels | Pooled Random Forest probability → isotonic calibration → alert/tier rules | Calibrated outbreak probability; alert flag; low/medium/high risk tier |
| Module 3: Hybrid Spatial Hotspot Detection | District case intensity; district boundaries/centroids; rainfall, temperature, elevation, population | KDE + Moran’s I spatial baseline → environmental/demographic residual adjustment | Adjusted hotspot / spatial risk surface |
| Integration layer | Module 1–3 outputs | Streamlit early-warning dashboard for joint visualisation and alerting | Forecast charts, risk alerts, hotspot maps (research and operational views) |

As shown in Table 4.2, the modules share epidemiological and climate information at a high level but apply different Stage 1 and Stage 2 processes because they answer different risk questions. Module 1 produces quantitative case magnitude, Module 2 produces calibrated outbreak-risk indicators, and Module 3 produces geographic hotspot interpretation. The early-warning dashboard then combines these outputs for joint inspection without collapsing them into a single undifferentiated score. Detailed preprocessing choices, exact feature lists, pipeline file structures, and evaluation metrics are developed in the subsequent analysis, implementation, and evaluation chapters.

**Approx. word count:** 250 words

**Notes for Team:**
- Table 4.2 is the main visual for 4.8; no additional figure is required.
- Keep feature detail at category level here; full dictionaries belong in Chapters 5–6.
- The Integration layer row is optional if the supervisor prefers a modules-only IPO table; recommended for completeness after Section 4.7.

---

## 4.9 Summary

This chapter presented the overall approach of the Residual Compensation Modeling Framework for Dengue Risk Prediction. The framework organises dengue risk intelligence into three complementary district-week modules covering case magnitude, outbreak probability, and spatial concentration. Each module follows a two-stage baseline-then-compensation design, but the meaning of compensation is adapted to the task: residual case-count correction in Module 1, probability calibration in Module 2, and spatial residual adjustment in Module 3. The modules are developed modularly and integrated through an early-warning decision-support dashboard that presents forecasts, risk alerts, and hotspot views together while distinguishing validated research outputs from operational forward products. The next chapter develops the analysis and design of this approach in greater architectural detail, including data flow, pipeline structure, and module-level design decisions.

**Approx. word count:** 140 words

**Notes for Team:**
- No figure or table required in 4.9.
- Transition sentence prepared for Chapter 5 Analysis and Design.
