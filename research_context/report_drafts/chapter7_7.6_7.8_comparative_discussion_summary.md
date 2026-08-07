## 7.6 Cross-Module Comparative Analysis

Experiment M2-009 tested whether Module 2 is unnecessary given Module 1 case forecasts, by comparing Module 2 alerts with thresholding Module 1’s `final_prediction` on the same holdout block and outbreak label. The comparison uses the production Module 2 stack at τ = 0.14 against fair and naive Module 1 thresholding rules, with an oracle upper bound included only as a reference.

**Table 7.7: Holdout alert comparison of Module 2 versus Module 1 thresholding rules (M2-009)**

| Rule (holdout, 40 outbreaks / 2,600 rows) | PR-AUC | Recall | Precision | F2 |
|---|---|---|---|---|
| Module 2 production (τ = 0.14) | 0.412 | 0.600 | 0.338 | 0.519 |
| Module 1 forecast > epidemic threshold | 0.063 | 0.225 | 0.563 | 0.256 |
| Module 1 excess score (pred − threshold) | 0.280 | 0.225 | 0.563 | 0.256 |
| Module 1 forecast > 100 (naive) | 0.063 | 0.500 | 0.073 | 0.231 |
| Oracle: actual > threshold | 0.302 | 1.000 | 1.000 | 1.000 |

Module 2 captured 15 true outbreaks missed by the fair Module 1–threshold rule; the reverse set was empty. Forecasting case magnitude and detecting relative epidemic exceedance are therefore empirically separable tasks under this protocol. Module 1 remains the quantification layer; Module 2 remains the outbreak-alert layer. The large PR-AUC gap between Module 2 (0.412) and the fair Module 1 threshold rule (0.063) is the headline comparative result: good case forecasts do not automatically yield good outbreak alerts when the decision target is seasonal exceedance rather than absolute case count.

Module 3 adds a third complementary axis: spatial concentration and demographically informed residual burden. Because Module 3 is not scored on the same temporal holdout outbreak label, it is not entered into the M2-009 alert table. Instead, the comparative claim is architectural and decision-support oriented. Magnitude (Module 1), calibrated outbreak state (Module 2), and spatial hotspot structure (Module 3) answer different questions and should remain visible as related but distinct products rather than being collapsed into a single undifferentiated score. The early-warning dashboard’s research-versus-operational separation follows from the same principle: joint visualisation is useful, but evaluation authority stays with each module’s validated protocol.

**Approx. word count:** 430 words

---

## 7.7 Discussion of Results

Across the framework, residual compensation is a shared methodological theme with module-specific meanings. In Module 1, compensation is an additive correction to SARIMA case forecasts using climate-aware and reporting-state features; the evidence supports material MASE reduction for most districts without claiming universal Diebold–Mariano significance or fully whitened residuals. In Module 2, compensation is isotonic recalibration of poorly calibrated Stage 1 probabilities; the evidence supports improved BSS and more useful absolute-threshold alerts, while rejected ablations show that forcing a Module 1–style residual regressor is not the right Stage 2 form for classification. In Module 3, compensation is a shrunk iterative adjustment of a KDE risk surface; the evidence supports stable convergence and interpretable drivers, while the aggregate case-fit comparison honestly fails to improve on Stage 1.

Taken together, the results support a multidimensional residual-compensation framework rather than a single winning model. Module 1 improves magnitude estimation relative to its baseline. Module 2 improves outbreak-alert usability relative to raw probabilities and relative to naive thresholding of Module 1 forecasts. Module 3 provides spatial hotspot structure and explanatory residual adjustment without overstating case-fit gains. Soft decision-support interpretation follows naturally: the framework can inform situational awareness, but it does not claim clinical diagnosis, guaranteed outbreak prevention, or operational command-centre readiness.

Several limitations should remain explicit in any defence of these results. District-level aggregation cannot capture sub-district heterogeneity, and Open-Meteo climate inputs remain point samples per district rather than spatial averages. Module 2 holdout positives are sparse under the current label, so alert and calibration metrics on the final block carry sampling variance. Some districts remain difficult for forecasting, and Module 3 validation is spatial rather than temporal. Operational live and forward dashboard outputs are useful for demonstration but remain a weaker evidence tier than the research metrics reported in this chapter.

**Approx. word count:** 410 words

---

## 7.8 Summary

This chapter evaluated all three modules of the Residual Compensation Modeling Framework under protocols matched to each research question. Module 1’s residual compensation improved case-forecast MASE for most districts relative to SARIMA alone, with honest holdout exceptions and partial statistical significance. Module 2’s Random Forest Stage 1 and isotonic Stage 2 provided outbreak-alert performance that cannot be recovered by simply thresholding Module 1 forecasts. Module 3’s KDE baseline exhibited significant spatial clustering with documented weekly nuance, while Stage 2 residual adjustment converged under α = 0.05 without improving aggregate case-fit. Cross-module comparison supports retaining magnitude, calibrated outbreak risk, and spatial hotspot views as complementary decision-support products. Chapter 8 summarises the completed research contributions and outlines realistic future work.

**Approx. word count:** 155 words

**Notes for Team:**
- Standalone: `research_context/report_drafts/chapter7_7.6_7.8_comparative_discussion_summary.md`
- Table 7.7 added for M2-009 (update REPORT_DIAGRAM_PLAN if needed)
- Chapter 7 topic-by-topic set (7.1–7.8) is now complete
- Remaining figure gap: Figure 7.1 evaluation-protocol schematic
- Transition: Chapter 8 Conclusion and Future Work
