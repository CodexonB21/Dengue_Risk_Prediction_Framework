# Chapter 4 — Our Approach (Expanded Draft)

**Source of truth:** `CURRENT_ARCHITECTURE.md`, module `MODULE_CONTEXT.md` files, `RESEARCH_DECISIONS.md`, Decisions 001/013/022/025/027  
**Status:** Full conceptual draft for Word paste  
**Last updated:** 2026-07-30  
**Companion:** Section 4.1 is in `chapter4_4.1_introduction.md` (keep as-is).  
**Supersedes:** interim nested 4.2.1/4.2.2 bullet IPO text and `chapter4_4.2.1_4.2.2.md` numbering.

---

## 4.2 Overview of the Proposed Framework

The proposed Residual Compensation Modeling Framework treats dengue risk as a multidimensional decision-support problem rather than a single forecasting task. At the district-week scale used by Sri Lanka’s official epidemiological reporting, public health interpretation requires three complementary views of the same epidemic process. The first is quantitative magnitude: how many dengue cases are expected in the coming weeks. The second is probabilistic outbreak risk: whether current conditions are consistent with an elevated epidemic state rather than routine seasonal variation. The third is geographic concentration: which districts form spatially coherent high-burden areas that may warrant prioritisation. The framework therefore comprises three analytical modules—Hybrid Time-Series Case Forecasting, Hybrid Outbreak Risk Classification, and Hybrid Spatial Hotspot Detection—each responsible for one of these dimensions.

The spatial and temporal resolution of the framework is deliberately aligned with available surveillance data. Modelling is performed for Sri Lanka’s 25 administrative districts on an epidemiological-week calendar. Historical weekly dengue incidence is combined with district-level meteorological information such as rainfall, temperature, and humidity, together with temporal descriptors derived from the epidemiological calendar. The approach does not claim sub-district or household-level prediction. Instead, it aims to extract more useful early-warning signal from district-week incidence and climate information than is typically obtained from a single baseline model or a one-dimensional risk product.

Figure 4.1 presents the high-level organisation of the proposed framework. Epidemiological and climate inputs pass through shared preprocessing and then into the three modules. Each module applies a two-stage residual compensation design appropriate to its task and produces a distinct risk product: compensated case forecasts, calibrated outbreak-risk indicators, and spatial hotspot interpretations. These outputs are then brought together in an early-warning decision-support dashboard for joint visualisation and interpretation.

All three modules share a residual compensation philosophy, but they are developed and validated as modular pipelines. Shared preprocessing produces common epidemiological and climate base tables, while module-specific preprocessing and feature engineering preserve modelling choices that should not be forced onto every task. This architecture allows each module to be improved independently and then presented jointly through the dashboard. In the main research and training design, Modules 1 and 2 are complementary peers rather than a hard dependency chain. An operational forward pathway may use Module 1 case forecasts to populate lag features for Module 2 when true future case counts are unavailable; that pathway is treated as an operational evidence tier and is not the primary evaluation story for either module. The detailed meaning of residual compensation in each module is explained in the following section.

**[Insert Figure 4.1 here]**

**Figure 4.1:** High-level residual compensation framework for dengue risk prediction.

**Figure content to draw:** inputs → shared preprocessing → Modules 1/2/3 (magnitude / outbreak risk / hotspot) → early-warning dashboard; optional dashed M1→M2 “operational forward only”.

**Approx. word count:** 420 words

---

## 4.3 Residual Compensation Strategy

The central methodological idea of the framework is that useful predictive structure often remains in the errors of a carefully chosen baseline model. Rather than replacing the baseline with a single opaque learner, the framework separates pattern capture from error correction. Stage 1 establishes an interpretable baseline that is appropriate to the task. Stage 2 then learns systematic residual or calibration structure that the baseline leaves behind. In general form:

```text
baseline output + compensation = improved final output
```

The meaning of compensation is task-specific. In Module 1, the residual is defined on the case-count scale:

```text
residual = actual_cases - sarima_prediction
final_prediction = sarima_prediction + predicted_residual
```

Stage 2 therefore predicts the signed forecast error and adds it back to the SARIMA forecast. Climate and related contextual features enter primarily at this compensation stage, so that Stage 1 remains a climate-free temporal baseline and Stage 2 focuses on structured deviations associated with lagged climate, anomalies, and short-term epidemiological dynamics.

In Module 2, a literal residual of the form `label − predicted_probability` is statistically poorly behaved for a binary outcome. Compensation is therefore implemented as probability calibration. Stage 1 produces an initial outbreak probability, and Stage 2 adjusts that probability so that predicted risk better matches observed outbreak frequency. The official Stage 2 method is isotonic regression, selected after comparison with alternative calibration and correction architectures. The compensated probability then supports alert flags and graded risk tiers.

In Module 3, the baseline is a spatial risk surface rather than a univariate forecast. Compensation adjusts that surface using environmental and demographic context so that hotspot interpretation is not driven by case geography alone. The residual compensation strategy therefore provides a common research language across modules while allowing each module to use a mathematically appropriate form of error correction.

This two-stage design improves interpretability relative to a single black-box model because the contribution of the baseline and the contribution of the compensator can be examined separately. It also makes failure modes easier to diagnose: if Stage 2 does not improve a district or period, the residual may be close to random for that setting, which is itself an informative research outcome. Table 4.1 summarises how the shared compensation principle is instantiated differently across the three modules.

**[Insert Table 4.1 here]**

**Table 4.1:** Module-wise meaning of residual compensation in the proposed framework.

| Module | Baseline output | Compensation target / method | Final output |
|---|---|---|---|
| Module 1: Hybrid Time-Series Case Forecasting | SARIMA weekly case forecast | Predicted case residual using XGBoost | Compensated weekly case forecast |
| Module 2: Hybrid Outbreak Risk Classification | Outbreak probability from Random Forest | Probability calibration using isotonic regression | Calibrated probability, alert flag, and risk tier |
| Module 3: Hybrid Spatial Hotspot Detection | Spatial risk surface from KDE and Moran’s I | Spatial residual adjustment using environmental and demographic context | Adjusted hotspot / spatial risk map |

As shown in Table 4.1, residual compensation is a shared design principle rather than a single identical algorithm repeated three times. Module 1 corrects continuous forecast error on the case-count scale, Module 2 recalibrates probabilistic risk scores, and Module 3 adjusts a spatial baseline surface. The subsequent sections describe each module’s conceptual approach in turn.

**Approx. word count:** 430 words

---

## 4.4 Module 1: Hybrid Time-Series Case Forecasting

### 4.4.1 Purpose and scope

Module 1 estimates short-horizon weekly dengue case counts for each of Sri Lanka’s 25 administrative districts. Its purpose is to quantify expected case magnitude so that early-warning interpretation is grounded in a concrete forecast of burden rather than only in qualitative risk language. Within the overall residual compensation framework, Module 1 answers the magnitude question identified in Section 4.2: how many cases are expected in the coming weeks at the district-week scale used by official surveillance.

The modelling unit is the district-week observation, consistent with Weekly Epidemiological Report reporting. The module does not attempt sub-district or fine-scale spatial forecasting, does not classify outbreak labels, and does not produce hotspot surfaces; those responsibilities belong to Modules 2 and 3. Historical weekly dengue case counts form the primary Stage 1 input, while district-level meteorological covariates such as rainfall, temperature, and humidity are reserved mainly for Stage 2 residual learning.

### 4.4.2 Stage 1 baseline (SARIMA)

Stage 1 fits a Seasonal Autoregressive Integrated Moving Average (SARIMA) model independently for each district using historical weekly case counts only. Climate covariates are deliberately excluded from Stage 1. This design choice keeps the baseline focused on trend, autocorrelation, and seasonal temporal structure, and leaves climate-driven and other nonlinear deviations in the residual for Stage 2 to model. In other words, Stage 1 is intentionally a climate-free temporal baseline rather than a climate-aware SARIMAX specification.

Where appropriate, a `log1p` transform of case counts may be selected on a per-district basis to stabilise variance, with predictions inverse-transformed back to the raw case-count scale before residual construction and evaluation. Fitting separate district models recognises that dengue dynamics differ across districts and that a single pooled national baseline would obscure district-specific temporal behaviour that later residual learning needs to correct.

### 4.4.3 Stage 2 residual compensation (XGBoost)

After Stage 1 produces forecasts that can be compared with observed cases, residuals are extracted as:

```text
residual = actual_cases - sarima_prediction
```

Stage 2 then trains an XGBoost regression model to predict these residuals. The compensation feature set includes lagged case counts, rolling case statistics, rate-of-change indicators, lagged rainfall/precipitation features, lagged temperature and humidity features, climate anomaly indicators, seasonal cyclic encodings, monsoon indicators, the SARIMA prediction itself, and lagged residual features. Reporting-delay and related nowcasting indicators may also be used where they improve residual learning without violating temporal leakage constraints.

The Stage 2 model is intended to correct structured baseline error, not to replace the SARIMA forecast. Climate information therefore enters the Module 1 pipeline primarily as an explanation of residual behaviour rather than as a direct Stage 1 covariate. The final Module 1 forecast is obtained by adding the predicted residual to the baseline prediction:

```text
final_prediction = sarima_prediction + predicted_residual
```

Figure 4.2 summarises this two-stage workflow from the SARIMA baseline through residual extraction and XGBoost compensation to the final compensated case forecast.

**[Insert Figure 4.2 here]**

**Figure 4.2:** Two-stage residual compensation workflow for Module 1 (SARIMA baseline → residual extraction → XGBoost compensation → final case forecast).

### 4.4.4 Expected outputs and users

The primary output of Module 1 is a district-week forecast of expected dengue cases. These forecasts support early-warning interpretation and situational awareness for district-level public health analysts and planners who need quantitative estimates of case burden. The module is positioned as a research decision-support component rather than as a clinically certified or fully operational deployment system. Forecast quality is assessed under walk-forward and holdout protocols in the evaluation chapter; those numeric results are not repeated here. Compensated case forecasts may also inform complementary outbreak-risk interpretation in Module 2, especially in operational forward settings where true future case counts are not yet available.

**Approx. word count:** 560 words

---

## 4.5 Module 2: Hybrid Outbreak Risk Classification

### 4.5.1 Purpose and label concept

Module 2 addresses a complementary question to Module 1. Rather than forecasting the exact number of dengue cases, it estimates whether a district-week observation corresponds to an elevated outbreak-risk state and produces an interpretable risk score for early warning. Within the overall framework, Module 2 answers the probabilistic-risk dimension identified in Section 4.2: whether current conditions are consistent with an unusual epidemic elevation rather than routine seasonal variation.

The module operates at the same district-week resolution as Module 1 and uses the shared epidemiological and climate base tables, while applying Module 2–specific labelling, preprocessing, and modelling choices. Outbreak labels are constructed using a district-aware epidemic threshold based on historical case behaviour:

```text
outbreak = 1 if cases > historical_mean + k × historical_SD
```

Historical mean and dispersion are estimated from strictly prior years within each training window, so that label construction does not leak future information into model fitting. In the accepted design, the historical seasonal baseline is estimated using a harmonic regression approach that stabilises district-week expectations relative to a noisier exact-week sample mean. This adaptive definition accounts for cross-district differences in baseline incidence: a case count that is routine in a high-burden district may represent an unusual surge in a low-burden district.

### 4.5.2 Stage 1 baseline classifier

Stage 1 uses a pooled Random Forest classifier, selected after benchmarking against Logistic Regression and XGBoost under a walk-forward validation scheme. The Stage 1 inputs combine historical weekly dengue case counts with climate and seasonal information. At a conceptual level, the feature groups include epidemiological history descriptors such as case lags, rolling statistics, rate-of-change indicators, and case-anomaly lags, together with rainfall/precipitation, temperature, humidity, climate anomaly indicators, and seasonal encodings. District identity is also used to support pooled learning across districts. The detailed Stage 1 feature dictionary is reserved for the design and implementation chapters.

Unlike Module 1 Stage 1, Module 2 Stage 1 intentionally includes climate information because its task is direct outbreak-risk discrimination rather than isolation of a pure temporal residual. Class imbalance is handled through class reweighting rather than synthetic oversampling as the production strategy. Elevation and population-density layers are not treated as core Module 2 Stage 1 inputs; those covariates belong primarily to Module 3.

### 4.5.3 Stage 2 probability compensation

The meaning of residual compensation in Module 2 differs from Module 1. A literal residual of the form `label − predicted_probability` is statistically poorly behaved for a binary outcome, so Stage 2 is implemented as probability calibration rather than residual regression on the label scale. Stage 1 first produces an initial outbreak probability. Stage 2 then adjusts that probability so that predicted risk better matches observed outbreak frequency.

After benchmarking isotonic regression, Platt scaling, and a stacked contextual correction model, isotonic regression was selected as the official Stage 2 method. From the calibrated probability, the module derives two decision-support outputs using fixed absolute thresholds selected for early-warning utility: a binary alert flag and a three-level risk tier (`low`, `medium`, or `high`). Exact threshold values and discrimination/calibration metrics are reported in the evaluation chapter rather than here.

Figure 4.3 summarises this workflow from epidemic-threshold labelling through baseline probability estimation and isotonic calibration to the final alert and risk-tier outputs.

**[Insert Figure 4.3 here]**

**Figure 4.3:** Two-stage Module 2 workflow (epidemic-threshold labelling → Random Forest baseline probability → isotonic calibration → alert flag and risk tier).

### 4.5.4 Expected outputs and users

The primary outputs of Module 2 are a calibrated outbreak probability, a binary alert flag, and a graded risk tier. These outputs are intended for district-level health analysts and decision-makers who need probabilistic outbreak-risk communication to complement Module 1’s quantitative case forecasts. They should be interpreted as model-based risk indicators under the defined label and evaluation protocol, not as clinical diagnoses or guaranteed outbreak forecasts.

In the main research and training design, Module 2 does not require Module 1 forecasts as an input. An optional operational forward pathway may later use Module 1 case forecasts to populate lag features when true future case counts are unavailable; that pathway is treated as a separate operational evidence tier and is not the primary training architecture described in this section.

**Approx. word count:** 580 words

---

## 4.6 Module 3: Hybrid Spatial Hotspot Detection

### 4.6.1 Purpose and scope

Module 3 focuses on the geographic concentration of dengue risk. While Modules 1 and 2 summarise expected case magnitude and outbreak probability for each district-week, they do not by themselves describe how burden is organised across neighbouring districts. Module 3 therefore answers the geographic-concentration dimension identified in Section 4.2: which districts form spatially coherent high-burden areas that may warrant prioritisation.

The accepted spatial unit is the administrative district (GADM Level-1), consistent with the epidemiological surveillance grain used throughout the framework. The module uses district-level case intensity together with district boundaries and centroids; it does not claim fine-scale targeting below the district level, nor does it depend on point-level geocoded household case locations. In addition to case geography, Module 3 incorporates environmental and demographic context such as rainfall, temperature, elevation, and population to support spatial residual adjustment.

### 4.6.2 Stage 1 spatial baseline (KDE and Moran’s I)

Stage 1 produces a spatial baseline risk surface using Kernel Density Estimation (KDE) informed by district-level case intensity and district-centroid geography. The KDE baseline redistributes weekly case burden across districts according to spatial proximity structure, providing an initial estimate of where risk appears concentrated. Moran’s I is then used to assess whether the resulting pattern reflects statistically meaningful spatial clustering rather than random geographic dispersion.

In this sense, Stage 1 answers two related questions: where burden appears spatially concentrated, and whether that concentration is coherent enough to justify a spatial modelling treatment. Local indicators such as LISA may be considered as extensions, but the core Stage 1 approach is KDE plus global spatial autocorrelation assessment. Detailed numeric Moran’s I results are reported in the evaluation chapter rather than here.

### 4.6.3 Stage 2 spatial residual adjustment

Stage 2 applies residual compensation in the spatial domain. After the baseline risk surface is established, systematic differences between observed case intensity and the baseline spatial estimate are treated as spatial residuals. These residuals are then adjusted using environmental and demographic context, including rainfall, temperature, elevation, and population. The accepted compensation design uses a tree-based spatial residual adjustment model, refined through an iterative loop that checks whether successive adjustments materially change the risk surface and whether residual spatial structure remains.

Conceptually, Stage 2 corrects baseline hotspot estimates that are incompletely explained by case geography alone. Environmental and demographic information therefore enter Module 3 primarily as compensators of spatial residual structure, allowing the final risk interpretation to reflect both geographic clustering and contextual modifiers. This is analogous in spirit to Modules 1 and 2, but the compensation target is a spatial risk surface rather than a univariate case residual or a calibrated probability.

Figure 4.4 summarises this two-stage spatial workflow from the KDE and Moran’s I baseline through environmental and demographic residual adjustment to the final hotspot interpretation.

**[Insert Figure 4.4 here]**

**Figure 4.4:** Two-stage Module 3 workflow (KDE + Moran’s I baseline → environmental/demographic residual adjustment → hotspot / risk surface).

### 4.6.4 Expected outputs and users

The intended outputs of Module 3 are district-level hotspot interpretations and adjusted spatial risk surfaces that complement Module 1’s case forecasts and Module 2’s outbreak probabilities. These outputs are useful for vector-control planning discussions and geographic prioritisation within a research decision-support framing. They should be interpreted as model-based spatial risk indicators, not as guaranteed outbreak maps or operationally certified targeting instructions.

This section establishes the conceptual approach only. Detailed spatial pipeline design, preprocessing choices, residual-surface construction, and quantitative spatial evaluation are developed further in the analysis, implementation, and evaluation chapters. The detailed spatial feature dictionary is likewise reserved for those later chapters.

**Approx. word count:** 520 words

---

## 4.7 System Integration and Early Warning Dashboard

The three modules are valuable individually, but their practical usefulness increases when their outputs can be interpreted together. Module 1 answers how large the expected case burden is, Module 2 answers how elevated the outbreak-risk state appears, and Module 3 answers where burden is spatially concentrated. Without an integration layer, these products remain separate analytical artifacts. The framework therefore includes an early-warning decision-support dashboard that presents the complementary module outputs in one interface for joint visualisation and interpretation.

The accepted dashboard implementation is a Streamlit application that consumes versioned module outputs such as compensated case forecasts, calibrated outbreak probabilities, alert flags, risk tiers, and spatial hotspot layers. It is designed as a read-only visualisation and interpretation layer rather than as a separate model-training system or a custom web-service stack. Where predicted case counts are elevated or calibrated outbreak risk crosses selected alert thresholds, the dashboard can surface visual alerts and summary indicators. The interface supports inspection of time-series forecasts, risk trajectories, and map-based hotspot views. It does not claim intervention scenario simulation, guaranteed outbreak prevention, or a fully operational public-health command-centre deployment.

An important integration principle is the separation of evidence tiers. Holdout-validated research outputs remain the primary basis for claiming model quality in the evaluation chapter. Operational forward outputs—such as multi-week-ahead case forecasts and forward risk scores that may use Module 1 predictions and forecast climate when true future case counts are unavailable—are presented as a distinct operational tier. This prevents research metrics and forward operational products from being conflated. In the main research design, Modules 1 and 2 remain complementary peers; the Module 1 → Module 2 linkage for forward scoring is an operational convenience, not the core training architecture.

Figure 4.5 illustrates how the three module outputs feed the early-warning dashboard. As shown in the figure, epidemiological and climate-derived analytical products are not collapsed into a single score. Instead, magnitude, probabilistic risk, and spatial concentration remain visible as related but distinct decision-support views. In this way, the dashboard closes part of the modelling-to-decision gap by making multidimensional dengue risk outputs inspectable together, while remaining honest about the difference between validated backtesting and operational forward use.

**[Insert Figure 4.5 here — optional but recommended]**

**Figure 4.5:** Integration of forecasting, risk classification, and hotspot outputs into the early-warning dashboard.

**Approx. word count:** 390 words

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

---

## 4.9 Summary

This chapter presented the overall approach of the Residual Compensation Modeling Framework for Dengue Risk Prediction. The framework organises dengue risk intelligence into three complementary district-week modules covering case magnitude, outbreak probability, and spatial concentration. Each module follows a two-stage baseline-then-compensation design, but the meaning of compensation is adapted to the task: residual case-count correction in Module 1, probability calibration in Module 2, and spatial residual adjustment in Module 3. The modules are developed modularly and integrated through an early-warning decision-support dashboard that presents forecasts, risk alerts, and hotspot views together while distinguishing validated research outputs from operational forward products. The next chapter develops the analysis and design of this approach in greater architectural detail, including data flow, pipeline structure, and module-level design decisions.

**Approx. word count:** 140 words

---

## Chapter totals and paste checklist

| Section | Approx. words |
|---|---|
| 4.1 (separate file) | ~240 |
| 4.2 | ~360 |
| 4.3 | ~420 |
| 4.4 | ~480 |
| 4.5 | ~520 |
| 4.6 | ~430 |
| 4.7 | ~320 |
| 4.8 | ~220 |
| 4.9 | ~140 |
| **Total (4.1–4.9)** | **~3,130** |

**Paste checklist for Word**
- [ ] Keep corrected 4.1 from `chapter4_4.1_introduction.md`
- [ ] Replace interim 4.2–4.3 content with sections above
- [ ] Remove internal Notes / this checklist before final submission
- [ ] Insert Figures 4.1–4.5 and Tables 4.1–4.2
- [ ] Do not carry interim claims: fine-scale, SARIMAX, RF-or-XGBoost undecided, Module 2 climate residual Stage 2, scenario simulation, Command Centre stack

**Notes for Team**
- 4.4 is slightly under the 500-word floor (~480); acceptable for approach depth; expand in Chapter 5/6 if needed.
- 4.7 is slightly under 350 (~320); kept lean to avoid duplicating Chapter 5 integration design.
- Exact alert thresholds, MASE/PR-AUC, Moran’s I numeric headlines belong mainly in Chapter 7 (Moran’s I I=0.70 may be cited later when reporting Module 3 results).
