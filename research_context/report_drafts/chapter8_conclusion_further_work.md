# Chapter 8 — Conclusion and Further Work

**Status:** Paste-ready draft (accepted structure 2026-07-30)  
**Aligned with:** Chapters 4–7; module experiment logs; soft decision-support framing

---

## 8.1 Conclusion

This research developed and evaluated a Residual Compensation Modeling Framework for dengue risk prediction at the district–week level in Sri Lanka. The central idea was that a well-chosen Stage 1 baseline can capture a primary structure of dengue burden—temporal seasonality and autocorrelation for cases, ranking structure for outbreak risk, or spatial concentration for hotspots—while a second stage can compensate for residual error that the baseline cannot explain. The framework was implemented as three complementary modules and integrated into a Streamlit early-warning dashboard that presents research and operational evidence as distinct tiers rather than as interchangeable claims.

Module 1 addressed weekly case forecasting. A climate-free per-district SARIMA Stage 1 provided the baseline, and a pooled XGBoost Stage 2 predicted additive residuals from lagged epidemiological, climate, seasonal, and reporting-delay features. Under expanding-window walk-forward evaluation and an untouched two-year holdout, residual compensation improved median holdout MASE for most districts relative to SARIMA alone, with Kilinochchi and Mannar retained as honest exceptions and with Diebold–Mariano significance treated as partial rather than universal. The production stack refinement associated with reporting-delay features further stabilised the operating point without replacing the Stage 1 versus Stage 1+2 comparison as the primary compensation claim.

Module 2 addressed rare-event outbreak-risk classification. After harmonic epidemic labelling, a pooled Random Forest Stage 1 provided discrimination under PR-AUC, while isotonic Stage 2 improved calibration under Brier Skill Score and supported absolute-threshold alerts and ordered risk tiers. Rejected ablations showed that Module 2’s Stage 2 problem is probability calibration rather than a forced copy of Module 1’s additive residual regressor. Cross-module experiment M2-009 further showed that thresholding Module 1 case forecasts is not a substitute for Module 2 alerts: forecasting magnitude and detecting relative seasonal exceedance remain empirically separable tasks.

Module 3 addressed spatial hotspot detection. A case-weighted KDE Stage 1 produced a clustered district risk baseline, validated by Global Moran’s I with documented weekly nuance, including a non-significant NE-monsoon check. Stage 2 applied Random Forest residual adjustment under an iterative update with shrinkage α = 0.05. The stage converged stably and yielded demographically interpretable feature importance, but it did not improve aggregate case-fit relative to the rescaled Stage 1 baseline. That null-to-negative result was retained deliberately as an honesty constraint on what spatial residual compensation can claim in this setting.

Across the three modules, the main contribution is methodological and architectural rather than a claim of a single best predictor. The project demonstrates that residual compensation can be specialised to different dengue risk questions—case magnitude, calibrated outbreak state, and spatial concentration—while preserving leakage-aware evaluation and soft decision-support language. The dashboard contribution is similarly bounded: it integrates module outputs for analytical review and demonstration, but it does not retrain models, overwrite holdout evidence, or constitute an operational public-health command system. In that sense, the work closes the modelling-to-interpretation gap partially and honestly, leaving clinical certification, guaranteed outbreak prevention, and nationwide real-time deployment outside the scope of what was completed.

**Approx. word count:** 700 words
*(Standalone: `research_context/report_drafts/chapter8_8.1_conclusion.md`)*

---

## 8.2 Further Work

Several extensions follow directly from the evaluation evidence and known constraints. For Module 1, further work should continue to treat reporting dynamics as a first-class forecasting challenge rather than as an afterthought. Quantile or probabilistic Stage 2 outputs, fuller rolling one-step evaluation across all districts, and stronger nowcasting guards around catch-up weeks would help separate operational usefulness from flat multi-step holdout skill without conflating the two estimands. Extending climate representation beyond point-per-district Open-Meteo samples—where data quality allows—may also reduce residual structure that remains after compensation.

For Module 2, the sparse holdout positive class under the current harmonic label remains a central constraint. Future work could explore richer but still temporally honest label definitions, threshold policies that are periodically re-calibrated under prevalence shift, and carefully gated use of Module 1 forecasts in operational forward scoring without promoting architectures that harm calibration. External validation on later epidemic seasons, once available, would strengthen claims that currently rest on a single untouched holdout block with limited outbreak counts.

For Module 3, the priority is not to restate Stage 2 as a case-fit optimiser after a verified null aggregate-fit result. More promising directions include finer spatial grains where reliable case and covariate data exist, richer environmental layers than point climate and static elevation, and evaluation criteria aligned to spatial decision needs—such as hotspot stability, rank agreement with observed burden, or local residual diagnostics—rather than national MAE alone. Any move to DS-division or MOH-area analysis would require a new data contract and must not silently revive unsupported CHIRPS/WorldPop production claims.

At the framework level, further work should deepen the research-versus-operational evidence separation already implemented in the dashboard. Prospective paper-trading of alerts, stakeholder-in-the-loop review protocols, and versioned refresh audits would help convert the prototype into a stronger decision-support research platform. Collaboration with public-health partners would also clarify which complementary views—magnitude, calibrated risk, or spatial concentration—are most actionable in practice. These directions remain research and validation tasks; they do not imply that the present system is ready for unsupervised operational deployment.

**Approx. word count:** 480 words
*(Standalone: `research_context/report_drafts/chapter8_8.2_further_work.md`)*

---

## Word-Count Summary

| Section | Approx. words |
|---|---|
| 8.1 Conclusion | 700 |
| 8.2 Further Work | 480 |
| **Chapter 8 total** | **~1,180** |

**Notes for Team:**
- Title in Word may use “Conclusion and Further Work” (or department variant “Further Works” if required)
- Do not invent deployment readiness or clinical impact
- Keep Module 3 null aggregate-fit honesty in the conclusion
- Transition: Chapter 9 Challenges and Limitations
