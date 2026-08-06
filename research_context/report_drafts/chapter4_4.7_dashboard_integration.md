# Chapter 4 — Section 4.7 System Integration and Early Warning Dashboard

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 4.6 Module 3: Hybrid Spatial Hotspot Detection  
**Next topic:** 4.8 Inputs, Processes, and Outputs Summary

---

## 4.7 System Integration and Early Warning Dashboard

The three modules are valuable individually, but their practical usefulness increases when their outputs can be interpreted together. Module 1 answers how large the expected case burden is, Module 2 answers how elevated the outbreak-risk state appears, and Module 3 answers where burden is spatially concentrated. Without an integration layer, these products remain separate analytical artifacts. The framework therefore includes an early-warning decision-support dashboard that presents the complementary module outputs in one interface for joint visualisation and interpretation.

The accepted dashboard implementation is a Streamlit application that consumes versioned module outputs such as compensated case forecasts, calibrated outbreak probabilities, alert flags, risk tiers, and spatial hotspot layers. It is designed as a read-only visualisation and interpretation layer rather than as a separate model-training system or a custom web-service stack. Where predicted case counts are elevated or calibrated outbreak risk crosses selected alert thresholds, the dashboard can surface visual alerts and summary indicators. The interface supports inspection of time-series forecasts, risk trajectories, and map-based hotspot views. It does not claim intervention scenario simulation, guaranteed outbreak prevention, or a fully operational public-health command-centre deployment.

An important integration principle is the separation of evidence tiers. Holdout-validated research outputs remain the primary basis for claiming model quality in the evaluation chapter. Operational forward outputs—such as multi-week-ahead case forecasts and forward risk scores that may use Module 1 predictions and forecast climate when true future case counts are unavailable—are presented as a distinct operational tier. This prevents research metrics and forward operational products from being conflated. In the main research design, Modules 1 and 2 remain complementary peers; the Module 1 → Module 2 linkage for forward scoring is an operational convenience, not the core training architecture.

Figure 4.5 illustrates how the three module outputs feed the early-warning dashboard. As shown in the figure, epidemiological and climate-derived analytical products are not collapsed into a single score. Instead, magnitude, probabilistic risk, and spatial concentration remain visible as related but distinct decision-support views. In this way, the dashboard closes part of the modelling-to-decision gap by making multidimensional dengue risk outputs inspectable together, while remaining honest about the difference between validated backtesting and operational forward use.

**[Insert Figure 4.5 here — optional but recommended]**

**Figure 4.5:** Integration of forecasting, risk classification, and hotspot outputs into the early-warning dashboard.

**Figure 4.5 content to draw (recommended):**

```text
Module 1 outputs          Module 2 outputs           Module 3 outputs
(case forecasts)     (calibrated risk / alerts)   (hotspot / risk surface)
        \                     |                      /
         \                    |                     /
          \                   |                    /
           →  Early-warning decision-support dashboard (Streamlit)
                 - forecast charts
                 - risk tiers / alert indicators
                 - spatial maps
                 - research vs operational evidence labels
```

Optional annotation: dashed note “Module 1 → Module 2 lag features: operational forward scoring only.”

Do **not** show scenario simulation controls, React/Flask “Command Centre” architecture, or a single fused “final dengue score” that hides the three module meanings.

**Approx. word count:** 390 words

**Notes for Team:**
- Figure 4.5 is optional in the Chapter 4 plan but recommended for viva clarity.
- Exact alert thresholds and metric tables belong in Chapter 7.
- Dashboard implementation details (pages, refresh scripts, CSV paths) belong mainly in Chapters 5–6.
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md` (Figure 4.5).
