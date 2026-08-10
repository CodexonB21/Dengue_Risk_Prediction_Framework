# Chapter 5 — Section 5.2 High-Level System Architecture

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 5.1 Introduction  
**Next topic:** 5.3 Data Architecture and Pipeline Design (+ Figure 5.2, Table 5.1)

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

**Figure 5.1 content to draw (required):**

```text
Data acquisition
  - weekly district dengue cases
  - Open-Meteo climate (rainfall, temperature, humidity)
  - spatial: boundaries/centroids, elevation, population
        ↓
Shared preprocessing (module-agnostic only)
  - 25-district consolidation
  - epi-week calendar alignment
        ↓
        ┌──────────────────┬──────────────────┬──────────────────┐
        ↓                  ↓                  ↓
 Module 1            Module 2            Module 3
 specific prep       specific prep       specific prep
 + feature groups    + feature groups    + spatial features
        ↓                  ↓                  ↓
 Stage 1 SARIMA      Stage 1 RF (tuned)  Stage 1 KDE + Moran’s I
        ↓                  ↓                  ↓
 Stage 2 XGBoost     Stage 2 Platt       Stage 2 RF relative
 residual (+climate) scaling             residual (α=1)
        ↓                  ↓                  ↓
 case forecast       alert / risk tier   hotspot surface
        └──────────────────┴──────────────────┘
                          ↓
              Evaluation design (walk-forward + holdout)
                          ↓
         Streamlit early-warning dashboard (read-only)
```

Dashed arrows (both required, not optional — both are real, implemented cross-module
dependencies, operational-tier only, never used for training/evaluation):
- Module 1 → Module 2 labelled "operational forward scoring only (Decision 027)" — M1's
  forward case forecast feeds Module 2's forward risk-scoring features.
- Module 1 → Module 3 labelled "operational forward only (Decision 031)" — M1's forward
  case forecast is the case-count proxy for Module 3's forward hotspot forecast.

Also note explicitly on the Module 1 Stage 2 box that climate lag/anomaly features enter
there, not at Stage 1 — Stage 1 (SARIMA) stays climate-free per Decision 001.

Do **not** show: one undifferentiated preprocessing block, fine-scale geocoded cases, SARIMAX in Module 1 Stage 1, Module 2 Stage 2 as climate residual ML, or a Command Centre / scenario-simulation UI.

**Approx. word count:** 550 words

**Notes for Team:**
- Cite Figure 5.1 in the body (done) and place it after the architecture paragraphs in Word.
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md` (Figure 5.1).
- Full Decision 013 table belongs in Section 5.3 (Table 5.1), not here.
