# Chapter 5 — Section 5.5 Integration and Output Design

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 5.4.3 Module 3 design (+ Figure 5.5)  
**Next topic:** 5.6 Summary

---

## 5.5 Integration and Output Design

Integration design concerns how the three module outputs are consumed together without collapsing their distinct meanings. Module 1 contributes compensated district-week case forecasts, Module 2 contributes calibrated outbreak probabilities with alert flags and risk tiers, and Module 3 contributes adjusted spatial hotspot surfaces. Each product answers a different decision-support question: how large the expected burden is, how elevated the outbreak-risk state appears, and where burden is geographically concentrated. Without a dedicated output layer, these products would remain separate analytical artifacts. The early-warning dashboard is therefore designed as the presentation layer that makes magnitude, probabilistic risk, and spatial concentration jointly inspectable.

Figure 5.6 summarises this integration design. As illustrated, the three module outputs feed one decision-support interface while retaining their distinct semantics, so that interpretation can use case magnitude, calibrated risk, and hotspot geography together without forcing them into a single undifferentiated score.

**[Insert Figure 5.6 here]**

**Figure 5.6:** Integration of module outputs into the early-warning dashboard (Streamlit decision-support views with research vs operational evidence tiers).

**Dashboard as a read-only consumer.** The accepted output design uses a Streamlit application that reads versioned analytical artifacts rather than retraining models at interaction time. Forecast charts, risk trajectories, alert indicators, district drill-downs, and map overlays are views over module outputs, not a fourth modelling stage. This keeps a clean boundary between research pipelines and visualisation: pipelines produce and version outputs; the dashboard consumes and displays them. Where predicted case counts are elevated or calibrated outbreak risk crosses selected alert thresholds, the interface can surface visual alerts and summary indicators. Exact threshold values belong with evaluation results in Chapter 7 rather than in the architectural claim of the dashboard itself.

**What the interface deliberately does not claim.** The design does not include intervention scenario simulation, guaranteed outbreak prevention, or a separate Flask/React command-centre stack. Nor does it fuse Modules 1–3 into one opaque “final dengue score.” Preserving separate views is intentional: a high forecast in Module 1, a high calibrated probability in Module 2, and a concentrated hotspot in Module 3 may co-occur, but they remain different quantities with different validation logics. Collapsing them would hide uncertainty and encourage over-interpretation.

**Research versus operational evidence tiers.** A further integration design rule is the separation of evidence tiers. Holdout-validated research outputs remain the basis for claiming model quality in the evaluation chapter and are presented as the research-evidence view of the dashboard. Operational forward products—such as multi-week-ahead case forecasts and forward risk scores that may use Module 1 predictions (and refreshed climate) when true future case counts are unavailable—are labelled as an operational prototype tier. This prevents research metrics and forward operational products from being conflated during demonstration or viva discussion. In the main research architecture, Modules 1 and 2 remain complementary peers sharing cleaned base tables; Module 1 → Module 2 lag substitution for forward scoring is an operational convenience rather than a hard training dependency.

**Intended users and design implication.** The intended users are district-level public health analysts and research reviewers who need to inspect complementary dengue risk signals in one place. The integration layer therefore closes part of the modelling-to-decision gap by making multidimensional outputs jointly readable, while remaining honest about the difference between validated backtesting and operational forward use. Implementation details of pages, refresh scripts, and artifact paths are presented in Chapter 6; the present section establishes the integration and output design only.

**Approx. word count:** 520 words

**Notes for Team:**
- Figure assets: `research_context/report_drafts/diagrams/figure_5_6_integration_dashboard.drawio` (+ `.png`).
- Do not claim Command Centre / scenario simulation.
- Keep numeric thresholds and metric tables for Chapter 7.
- Align wording with Chapter 4.7 (same principles; Chapter 5 is the design-depth version).
