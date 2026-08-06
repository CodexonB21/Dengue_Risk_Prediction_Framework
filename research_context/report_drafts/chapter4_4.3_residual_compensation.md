# Chapter 4 — Section 4.3 Residual Compensation Strategy

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 4.2 Overview of the Proposed Framework  
**Next topic:** 4.4 Module 1: Hybrid Time-Series Case Forecasting

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

**Notes for Team:**
- No new diagram is required in 4.3; Table 4.1 is the main visual element.
- Optional later cross-reference: Figure 4.2 (Module 1 workflow) can reuse the Module 1 equations introduced here.
- Do not invent a Module 2 “environmental residual regression” story; Stage 2 is calibration.
- Exact thresholds, BSS/PR-AUC, and MASE results belong in Chapter 7, not here.
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md` (Table 4.1).
