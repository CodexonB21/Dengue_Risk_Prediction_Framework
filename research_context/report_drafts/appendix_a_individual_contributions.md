# APPENDIX A — Individuals’ Contribution to the Project

**Team:** Codexon  
**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Status:** Paste-ready draft (first-person, expanded contributions; 2026-07-30)

**Module leadership**

| Index No. | Name | Primary module |
|---|---|---|
| 214029P | Bandara H.R.B.G.M. | Module 1 — Hybrid Time-Series Case Forecasting |
| 214140X | Nethma L.H.K. | Module 2 — Hybrid Outbreak Risk Classification |
| 214099D | Karunarathna R.M.D.R.R. | Module 3 — Hybrid Spatial Hotspot Detection |

Shared project work (epidemiological scraping, climate refresh, shared Decision 013 preprocessing, dashboard integration, and report drafting) was divided across the three members as summarised under each contribution below.

---

## 214029P — Bandara H.R.B.G.M.

I led Module 1: Hybrid Time-Series Case Forecasting, the quantitative case-magnitude component of the Residual Compensation Modeling Framework for Dengue Risk Prediction. My responsibility was to design, implement, and evaluate a two-stage hybrid forecasting pipeline that predicts weekly dengue case counts at district level. In Stage 1, I fitted per-district SARIMA models on weekly case counts only, without climate covariates, so that the baseline captured linear temporal structure cleanly. In Stage 2, I trained a pooled XGBoost residual model to predict additive SARIMA residuals using lagged epidemiological features, climate lags and anomalies, seasonal indicators, residual-lag features, and reporting-delay features. I implemented the final forecast as `final_prediction = sarima_prediction + predicted_residual`, which is the Module 1 form of residual compensation.

Within Module 1, I completed the end-to-end forecasting path from cleaned district–week inputs to validated outputs. I prepared Module 1–specific preprocessing, including seasonal-naive imputation where required, week-53 merge handling for SARIMA compatibility, and exclusion of imputed rows from scoring. I ran Stage 1 order and transform selection with stationarity safeguards, refit SARIMA models under expanding-window walk-forward folds, and reserved an untouched two-year holdout block for final evaluation. I engineered Stage 2 features, trained the residual model only on out-of-sample Stage 1 residuals to avoid leakage, and compared Stage 1 against Stage 1+2 using MAE, RMSE, sMAPE, MASE, Diebold–Mariano tests, residual-variance reduction, and Ljung–Box diagnostics. I also completed production-stack refinement after reporting-delay experiments and generated the forecasting evaluation artefacts used in Chapter 7, including holdout actual-versus-forecast plots and district-level MASE comparison figures.

As my equal share of cross-cutting project work, I led acquisition and maintenance of the MoH Weekly Epidemiological Report (WER) dengue case scrape and the shared district–week case table used by all three modules. I owned forecasting-side epidemiological calendar construction and Module 1 week-53 merge behaviour under Decision 013, and I contributed shared epidemiological cleaning utilities such as district-name standardisation. I drafted the Module 1 sections of the analysis, design, implementation, and evaluation chapters, and I integrated Module 1 research and forward-forecast artefacts into the Streamlit early-warning dashboard so that case forecasts could be inspected without overwriting frozen holdout evidence. Through this combined module and shared-data role, I delivered the framework’s primary weekly case-forecasting capability and the epidemiological data foundation required by the rest of the team.

**Approx. word count:** 420 words  
*(Standalone: `appendix_a_214029P_bandara.md`)*

---

## 214140X — Nethma L.H.K.

I led Module 2: Hybrid Outbreak Risk Classification, which converts dengue risk prediction into calibrated outbreak-probability intelligence and ordered risk tiers for early-warning decision support. My responsibility was to design, implement, and evaluate a two-stage residual-compensation classification pipeline. In Stage 1, I built models that estimate the probability of an outbreak week under a fold-aware harmonic epidemic threshold label (`k = 3.0`). After comparative experiments, I selected a pooled Random Forest classifier as the official Stage 1 model using PR-AUC as the primary discrimination metric. In Stage 2, I treated residual compensation as probability calibration rather than additive residual regression, and I selected isotonic regression as the official Stage 2 method using Brier Skill Score. I then defined fixed absolute thresholds to produce alerts and low/medium/high risk tiers from the calibrated probabilities.

Within Module 2, I completed the full classification workflow from labelling to evaluated alert outputs. I constructed fold-aware outbreak labels, engineered classification features including lagged case anomalies, climate lags and anomalies, and seasonal indicators, and enforced leakage-safe training so that Stage 2 used only out-of-sample Stage 1 probabilities. I compared Stage 1 candidates, benchmarked Stage 2 architectures including isotonic, Platt, and stacked alternatives, and documented rejected ablations such as SMOTENC oversampling and Module 1–symmetric residual stacking when they failed holdout scrutiny. I calibrated alert and high-confidence thresholds on validation folds, evaluated recall, precision, F2, and risk-tier separation on holdout data, and completed the Module 1 versus Module 2 complementarity study (M2-009), which showed that thresholding Module 1 case forecasts is not a substitute for Module 2 alerts. I also prepared the reliability diagrams and classification evaluation tables used in Chapter 7.

As my equal share of cross-cutting project work, I led Open-Meteo climate data acquisition, archive and forecast refresh, and weekly climate aggregation onto the shared epidemiological-week calendar. I established modelling conventions for physically consistent precipitation fields and co-owned the shared climate–epidemiology joins and lag/anomaly feature conventions reused by Modules 1 and 2. I contributed Decision 013 shared cleaning for climate readiness, drafted the Module 2 sections of the analysis, design, implementation, and evaluation chapters, and implemented dashboard support for calibrated risk trajectories, alert indicators, risk-tier summaries, and research-versus-operational evidence labelling for classification outputs. Through this combined module and shared-climate role, I delivered the framework’s outbreak-risk classification capability and the climate data foundation required across the project.

**Approx. word count:** 430 words  
*(Standalone: `appendix_a_214140X_nethma.md`)*

---

## 214099D — Karunarathna R.M.D.R.R.

I led Module 3: Hybrid Spatial Hotspot Detection, which identifies district-level geographic concentration of dengue burden for local situational awareness and soft decision-support discussion. My responsibility was to design, implement, and evaluate a two-stage spatial residual-compensation pipeline. In Stage 1, I constructed a case-weighted Gaussian kernel density estimation (KDE) baseline over district centroids and validated spatial clustering with Global Moran’s I under queen-contiguity weights, reporting both the aggregated clustering result and selected weekly checks, including weeks where clustering was not significant. In Stage 2, I modelled a relative spatial residual (the raw residual divided by current risk, after diagnosing that the raw residual was strongly heteroscedastic) with a Random Forest regressor dominated by each district's own recent case history, and updated district risk iteratively under a full-magnitude update (`Risk_t = Risk_(t-1) + α · predicted_relative_residual_t · (Risk_(t-1)+1)`, with `α = 1`) so that the correction remained stable under spatial cross-validation — an earlier absolute-residual formulation had required shrinkage (`α = 0.05`) before this reformulation. For visualisation only, I rendered continuous risk surfaces with inverse-distance weighting and did not treat IDW as an additional modelling stage.

Within Module 3, I completed the full spatial workflow from master-table construction to evaluated risk surfaces. I joined epidemiological, weekly climate, population, elevation, and GADM Level-1 geometry into a district–week spatial master table, derived population density from estimated population and land area, and dropped incomplete environmental joins before Stage 1. I implemented KDE baseline generation, Moran’s I validation, residual feature engineering with demographic and environmental covariates, five-fold spatial K-means cross-validation on district centroids, iterative convergence control, and the honest Stage 1 versus Stage 2 aggregate-fit comparison that showed no national case-fit improvement after Stage 2. I generated the hybrid risk-surface figures used in Chapter 7 and kept the production stack at district (GADM Level-1) resolution with census-derived population and Open-Meteo elevation, without introducing a CHIRPS/WorldPop raster production path.

As my equal share of cross-cutting project work, I led spatial and demographic data preparation for the whole framework. I prepared GADM Level-1 boundaries, census population interpolation and extrapolation, district land-area and population-density derivation, elevation joins, and the shared population tables used across modules. I contributed Decision 013 shared preprocessing for geometry-consistent district naming, drafted the Module 3 sections of the analysis, design, implementation, and evaluation chapters, and integrated spatial risk maps into the Streamlit early-warning dashboard so that hotspot outputs could be inspected alongside forecasting and classification views. Through this combined module and shared spatial-demographic role, I delivered the framework’s hotspot-detection capability and the geographic and population data foundation required by the team.

**Approx. word count:** 440 words  
*(Standalone: `appendix_a_214099D_karunarathna.md`)*

---

## Shared Workload Summary

| Shared work area | Primary owner | Supporting owners |
|---|---|---|
| WER epidemiological scrape and case tables | Bandara (214029P) | Nethma, Karunarathna |
| Open-Meteo climate refresh and weekly climate tables | Nethma (214140X) | Bandara, Karunarathna |
| Spatial/demographic layers (GADM, census, elevation) | Karunarathna (214099D) | Bandara, Nethma |
| Decision 013 shared cleaning / calendar alignment | All three (module-specific forks owned by each lead) | — |
| Streamlit dashboard integration | All three (each owns own module views) | — |
| Report drafting by module sections | Each module lead for own chapters/sections | Peer review across team |

---

**Notes for Team:**
- Written in first person (“I”) for Appendix A individual statements
- Each statement covers: module lead role, Stage 1/2 method, detailed module tasks, shared cross-cutting ownership, report/dashboard contribution
- Soft decision-support language retained
