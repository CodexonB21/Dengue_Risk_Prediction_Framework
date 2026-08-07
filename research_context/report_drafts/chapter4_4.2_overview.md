# Chapter 4 — Section 4.2 Overview of the Proposed Framework

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 4.1 Introduction  
**Next topic:** 4.3 Residual Compensation Strategy

---

## 4.2 Overview of the Proposed Framework

The proposed Residual Compensation Modeling Framework treats dengue risk as a multidimensional decision-support problem rather than a single forecasting task. At the district-week scale used by Sri Lanka’s official epidemiological reporting, public health interpretation requires three complementary views of the same epidemic process. The first is quantitative magnitude: how many dengue cases are expected in the coming weeks. The second is probabilistic outbreak risk: whether current conditions are consistent with an elevated epidemic state rather than routine seasonal variation. The third is geographic concentration: which districts form spatially coherent high-burden areas that may warrant prioritisation. The framework therefore comprises three analytical modules—Hybrid Time-Series Case Forecasting, Hybrid Outbreak Risk Classification, and Hybrid Spatial Hotspot Detection—each responsible for one of these dimensions.

The spatial and temporal resolution of the framework is deliberately aligned with available surveillance data. Modelling is performed for Sri Lanka’s 25 administrative districts on an epidemiological-week calendar. Historical weekly dengue incidence is combined with district-level meteorological information such as rainfall, temperature, and humidity, together with temporal descriptors derived from the epidemiological calendar. The approach does not claim sub-district or household-level prediction. Instead, it aims to extract more useful early-warning signal from district-week incidence and climate information than is typically obtained from a single baseline model or a one-dimensional risk product.

Figure 4.1 presents the high-level organisation of the proposed framework. Epidemiological and climate inputs pass through shared preprocessing and then into the three modules. Each module applies a two-stage residual compensation design appropriate to its task and produces a distinct risk product: compensated case forecasts, calibrated outbreak-risk indicators, and spatial hotspot interpretations. These outputs are then brought together in an early-warning decision-support dashboard for joint visualisation and interpretation.

All three modules share a residual compensation philosophy, but they are developed and validated as modular pipelines. Shared preprocessing produces common epidemiological and climate base tables, while module-specific preprocessing and feature engineering preserve modelling choices that should not be forced onto every task. This architecture allows each module to be improved independently and then presented jointly through the dashboard. In the main research and training design, Modules 1 and 2 are complementary peers rather than a hard dependency chain. An operational forward pathway may use Module 1 case forecasts to populate lag features for Module 2 when true future case counts are unavailable; that pathway is treated as an operational evidence tier and is not the primary evaluation story for either module. The detailed meaning of residual compensation in each module is explained in the following section.

**[Insert Figure 4.1 here]**

**Figure 4.1:** High-level residual compensation framework for dengue risk prediction.

**Figure content to draw (required):**
- Left: inputs — weekly district dengue cases; district climate (rainfall, temperature, humidity); temporal/seasonal descriptors; spatial boundaries/population for Module 3
- Middle top: shared preprocessing
- Middle: three parallel modules
  - Module 1: Hybrid Time-Series Case Forecasting → case magnitude
  - Module 2: Hybrid Outbreak Risk Classification → outbreak probability / alert
  - Module 3: Hybrid Spatial Hotspot Detection → hotspot / risk surface
- Right: early-warning decision-support dashboard combining the three outputs
- Optional dashed arrow: Module 1 → Module 2 labelled “operational forward scoring only”

Do **not** show: fine-scale/MOH-unit forecasting, SARIMAX in Stage 1, React/Flask “Command Centre”, or scenario simulation.

**Approx. word count:** 420 words

**Notes for Team:**
- Cite Figure 4.1 in the body (done above) and place the figure immediately after that paragraph in Word.
- Diagram tools: draw.io / PowerPoint / similar; export PNG for Word.
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md`.
