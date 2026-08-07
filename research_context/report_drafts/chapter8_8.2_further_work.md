## 8.2 Further Work

Several extensions follow directly from the evaluation evidence and known constraints. For Module 1, further work should continue to treat reporting dynamics as a first-class forecasting challenge rather than as an afterthought. Quantile or probabilistic Stage 2 outputs, fuller rolling one-step evaluation across all districts, and stronger nowcasting guards around catch-up weeks would help separate operational usefulness from flat multi-step holdout skill without conflating the two estimands. Extending climate representation beyond point-per-district Open-Meteo samples—where data quality allows—may also reduce residual structure that remains after compensation.

For Module 2, the sparse holdout positive class under the current harmonic label remains a central constraint. Future work could explore richer but still temporally honest label definitions, threshold policies that are periodically re-calibrated under prevalence shift, and carefully gated use of Module 1 forecasts in operational forward scoring without promoting architectures that harm calibration. External validation on later epidemic seasons, once available, would strengthen claims that currently rest on a single untouched holdout block with limited outbreak counts.

For Module 3, the priority is not to restate Stage 2 as a case-fit optimiser after a verified null aggregate-fit result. More promising directions include finer spatial grains where reliable case and covariate data exist, richer environmental layers than point climate and static elevation, and evaluation criteria aligned to spatial decision needs—such as hotspot stability, rank agreement with observed burden, or local residual diagnostics—rather than national MAE alone. Any move to DS-division or MOH-area analysis would require a new data contract and must not silently revive unsupported CHIRPS/WorldPop production claims.

At the framework level, further work should deepen the research-versus-operational evidence separation already implemented in the dashboard. Prospective paper-trading of alerts, stakeholder-in-the-loop review protocols, and versioned refresh audits would help convert the prototype into a stronger decision-support research platform. Collaboration with public-health partners would also clarify which complementary views—magnitude, calibrated risk, or spatial concentration—are most actionable in practice. These directions remain research and validation tasks; they do not imply that the present system is ready for unsupervised operational deployment.

**Approx. word count:** 480 words

**Notes for Team:**
- Realistic next steps only; no deployment overclaim
- Transition: Chapter 9 Challenges and Limitations
