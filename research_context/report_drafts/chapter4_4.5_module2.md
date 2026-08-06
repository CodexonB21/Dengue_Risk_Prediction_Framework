# Chapter 4 — Section 4.5 Module 2: Hybrid Outbreak Risk Classification

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 4.4 Module 1: Hybrid Time-Series Case Forecasting  
**Next topic:** 4.6 Module 3: Hybrid Spatial Hotspot Detection

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

**Figure 4.3 content to draw (required):**

```text
Weekly district cases + climate/seasonal features
        ↓
Epidemic-threshold labelling
   outbreak = 1 if cases > historical_mean + k × historical_SD
        ↓
Stage 1: Pooled Random Forest
   → initial outbreak probability
        ↓
Stage 2: Isotonic calibration
   → calibrated probability
        ↓
Decision-support outputs
   alert_flag + risk_tier (low / medium / high)
```

Optional side note on the figure: “Climate included in Stage 1; Stage 2 = calibration, not environmental residual regression.”

Do **not** show SMOTE as the production imbalance method, elevation/population as core Module 2 inputs, or Stage 2 as climate residual ML in the Module 1 sense.

**Approx. word count:** 580 words

**Notes for Team:**
- Inputs/outputs stated in prose (4.5.1–4.5.2 and 4.5.4); full feature list belongs in Chapters 5–6; cross-module IPO comparison in Table 4.2 (Section 4.8).
- Cite Figure 4.3 in the body (done in 4.5.3) and place it immediately after that paragraph in Word.
- Align any existing Module 2 draw.io with Random Forest → isotonic (not XGBoost → climate residual).
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md` (Figure 4.3).
