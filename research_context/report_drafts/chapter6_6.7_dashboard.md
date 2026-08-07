## 6.7 Output Generation and Early-Warning Dashboard

Validated module outputs are persisted as CSV prediction tables, metrics, figures, and model artefacts under the module-specific processed, features, models, and outputs directories. On top of these research artefacts, an early-warning dashboard was implemented in Streamlit as a read-only consumer of curated files. The dashboard does not retrain models, rewrite holdout predictions, or act as a write-back control interface. Its purpose is to present forecasting, outbreak-risk, and spatial-risk outputs in a form suitable for analytical review, viva demonstration, and soft decision-support discussion.

The interface deliberately separates research and operational evidence tiers. The research tier surfaces holdout-validated and walk-forward artefacts that may be cited alongside Chapter 7 evaluation claims, including Stage 1 versus Stage 1-plus-Stage 2 comparisons where available. The operational tier presents live recent-week scoring and forward prototype outputs—Module 1 future case forecasts, Module 2 live and forward risk predictions, and Module 3 hybrid risk views—explicitly tagged so that they cannot be mistaken for holdout accuracy. Typical views include district selection, recent calibrated risk trajectories, forward case and risk horizons with completeness diagnostics, alert or tier summaries, and spatial risk map rendering. Module 1 answers expected case magnitude, Module 2 answers elevated outbreak-risk state, and Module 3 answers spatial concentration; the dashboard keeps these complementary products visible rather than collapsing them into a single undifferentiated score. No Command Centre, scenario-simulation control room, or automated intervention dispatch layer is implemented or claimed.

Operational refresh is orchestrated at a high level by `scripts/refresh_dashboard_data.py`. The script coordinates Open-Meteo weather refresh, shared and module preprocessing updates where required, Module 1 forward forecasting, and Module 2 live/forward risk scoring before the Streamlit application reads the resulting CSV products. This keeps data-currency concerns outside the validated training loop and preserves the distinction between research evidence and operational prototype behaviour. Because the dashboard is read-only, regenerating operational files cannot silently overwrite the frozen research metrics used for thesis evaluation. Figure 6.5 illustrates the dashboard’s relationship to the three module pipelines.

[Insert Figure 6.5 here]

**Figure 6.5: Streamlit early-warning dashboard as a read-only consumer of research and operational module outputs**

Figure 6.5 reinforces the soft decision-support framing introduced in Section 6.1: the dashboard integrates module outputs for inspection, but evaluation authority remains with the holdout-validated artefacts documented in Chapter 7.

**Approx. word count:** 430 words

**Notes for Team:**
- PNG: `research_context/report_drafts/diagrams/figure_6_5_dashboard_outputs.png`
- Keep research vs operational evidence tiers explicit
- Soft decision-support only; no Command Centre / scenario-simulation claims
- Transition: next section is 6.8 Summary
