# Chapter 1 — Section 1.4 Proposed Solution

> **Numbering note:** In `REPORT_STRUCTURE.md`, Proposed Solution is listed as 1.6 and Research Gap as 1.4. This draft follows the interim/user numbering (**1.4 Proposed Solution**). Renumber later if the supervisor prefers the structure-file order.

## 1.4 Proposed Solution

The proposed solution is a residual compensation modeling framework for dengue risk prediction. To keep the research scope clear and justifiable, the framework is organised into three complementary analytical modules. Each module follows the same two-stage philosophy: a baseline model first captures the dominant structure of the problem, and a second-stage compensation model then corrects systematic residual or calibration errors that remain after the baseline stage. The modules operate at the district-week level across Sri Lanka’s administrative districts and are designed to support early-warning interpretation rather than clinical diagnosis or guaranteed outbreak prediction.

**Module 1: Hybrid Time-Series Case Forecasting.**  
The first module estimates short-horizon weekly dengue case counts. Stage 1 fits a SARIMA baseline separately for each district using historical weekly case counts only; climate covariates are deliberately excluded from this stage so that the baseline concentrates on trend, autocorrelation, and seasonal temporal structure [5]. Stage 2 then trains an XGBoost residual compensation model to learn structured prediction errors using lagged epidemiological features, lagged climate variables (rainfall/precipitation, temperature, and humidity), climate anomaly indicators, seasonal encodings, and related contextual signals. The residual and final forecast are defined as:

```text
residual = actual_cases - sarima_prediction
final_prediction = sarima_prediction + predicted_residual
```

In this way, Module 1 produces a quantitative estimate of expected case magnitude that improves on the baseline when residual structure is learnable.

**Module 2: Hybrid Outbreak Risk Classification.**  
The second module addresses a complementary question: whether a district-week observation corresponds to an elevated outbreak-risk state. Rather than predicting exact case counts, Stage 1 uses a pooled Random Forest classifier, selected after benchmarking against Logistic Regression and XGBoost, to estimate an initial outbreak probability from lagged case features, short-term trend descriptors, climate features, and seasonal indicators. Outbreak labels are defined using a district- and week-aware epidemic threshold based on historical incidence, so that “outbreak” reflects unusual elevation relative to a district’s own seasonal baseline rather than a single global case cutoff. Stage 2 then applies isotonic regression as a probability-compensation step, selected after comparison with Platt scaling and a stacked correction model, so that predicted probabilities are better calibrated to observed outbreak frequency. From the calibrated probability, the module derives early-warning outputs in the form of a binary alert flag and a graded risk tier (low, medium, or high), consistent with the need for interpretable outbreak-oriented risk communication [7].

**Module 3: Hybrid Spatial Hotspot Detection.**  
The third module focuses on the geographic concentration of dengue risk. Stage 1 constructs a spatial baseline risk surface using Kernel Density Estimation (KDE), with Moran’s I used to assess whether the resulting pattern reflects statistically meaningful spatial clustering rather than random geographic dispersion. Stage 2 then applies a spatial residual adjustment model that incorporates environmental and demographic context, such as rainfall, elevation, temperature, and population density, to correct baseline spatial risk estimates that temporal models alone cannot explain. The intended output is a district-level hotspot interpretation that complements Module 1’s case forecasts and Module 2’s outbreak probabilities, following principles established in spatial epidemiology and related geospatial risk-mapping research [8].

The outputs of the three modules are brought together in a centralised early-warning dashboard for joint visualisation and interpretation. Predicted case burden, outbreak-risk indicators, and spatial hotspot information can therefore be examined as complementary views of the same district-week dengue situation. Where predicted case counts are elevated or calibrated outbreak risk crosses the selected alert thresholds, the dashboard presents visual alerts and summary indicators intended to convert model outputs into decision-support information for public health preparedness. The contribution of the proposed solution is therefore not a single model in isolation, but an integrated residual compensation framework that links forecasting, classification, and spatial analysis under a common error-correction design.

**Approx. word count:** 560 words

**Notes for Team:**
- Word count is slightly above the 250–500 standard-subsection target because this section must introduce all three modules; trim later if supervisor prefers a shorter Chapter 1 overview and more detail in Chapter 4.
- Corrected SARIMAX → SARIMA (climate only in Module 1 Stage 2).
- Locked Module 1 Stage 2 to XGBoost; Module 2 Stage 1 to Random Forest; Module 2 Stage 2 to isotonic calibration (not climate residual ML).
- Module 2 Stage 1 includes climate (unlike Module 1 Stage 1).
- Softened automatic “actionable authority deployment” claims to decision-support / early-warning language.
- Module 3 described as designed/intended architecture; Stage 1 KDE+Moran’s I is implemented, Stage 2 residual adjustment is the accepted design — avoid claiming full operational completion if still evolving.
- Citations [5], [7], [8] retained from interim text — verify they still match the intended sources.
- Consider adding a figure placeholder: Figure 1.X overall residual compensation framework (optional in Chapter 1; often better in Chapter 4/5).
