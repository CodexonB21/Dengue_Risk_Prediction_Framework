# Chapter 9 — Challenges and Limitations

**Status:** Paste-ready draft (accepted structure 2026-07-30)  
**Aligned with:** Chapter 7 evaluation honesty; Decisions 013/018/025/027; module contexts

---

## 9.1 Introduction

No dengue risk prediction framework is free of constraints, and residual compensation does not remove them. This chapter records the principal challenges and limitations encountered in data preparation, modelling, evaluation, and decision-support integration for the Residual Compensation Modeling Framework. The purpose is not to diminish the completed work, but to bound the claims that can responsibly be made from it. Where possible, each limitation is stated with its cause, its effect on interpretation, and a realistic mitigation path that remains consistent with Chapter 8.

**Approx. word count:** 160 words
*(Standalone: `research_context/report_drafts/chapter9_9.1_introduction.md`)*

---

## 9.2 Data and Scope Limitations

The epidemiological foundation of the project is district-level Weekly Epidemiological Report case counts. Aggregation at this grain smooths local transmission heterogeneity and prevents direct identification of neighbourhood or MOH-area hotspots. Underreporting, delayed reporting, and catch-up revisions can distort both recent case lags and outbreak labels, especially around suspected reporting-lag weeks. Although Module 1 introduced reporting-delay features and Module 2 uses fold-aware threshold labels, residual reporting noise remains a structural data limitation rather than a fully solved modelling problem.

Climate inputs were obtained from Open-Meteo as point samples associated with each district rather than as spatially averaged fields. This choice kept the production stack tractable and internally consistent, but it means that weather covariates do not represent intra-district climatic variation. Elevation likewise enters Module 3 as a static district header value. Population covariates rely on census points with interpolation and limited extrapolation; they approximate demography over a long study window but cannot capture short-term mobility or fine-scale exposure. Week-53 handling, Kalmunai-to-Ampara remapping, and shared calendar construction improved factual consistency under Decision 013, yet they also illustrate that epidemiological and climate series required non-trivial alignment before modelling could begin.

Scope was deliberately district-level and Sri Lanka–specific. The framework therefore cannot claim immediate transfer to other countries, to finer administrative units, or to syndromic streams beyond the WER case definition used here. Any expansion of scope would require a new data contract, not only a model re-fit.

**Approx. word count:** 380 words
*(Standalone: `research_context/report_drafts/chapter9_9.2_data_scope.md`)*

---

## 9.3 Module-Specific Modelling Limitations

Module 1’s Stage 1 SARIMA baseline is intentionally climate-free and cases-only. That design clarifies residual compensation, but it also means Stage 1 alone is often a weak forecaster, particularly in sparse or volatile districts. Stage 2 reduces error magnitude for most districts without fully whitening residuals, as indicated by persistent Ljung–Box significance in many series. Flat multi-step holdout evaluation and rolling one-step operational analogues answer related but different questions; conflating them would overstate either research skill or near-term operational usefulness. Extreme catch-up spikes remain difficult even after reporting-delay features.

Module 2 faces rare-event imbalance by construction. Under the current harmonic label, holdout prevalence is only about 1.5%, so precision, recall, and calibration estimates on the final block are statistically fragile. Strong Stage 1 discrimination does not imply well-calibrated raw probabilities; Stage 2 isotonic correction improves BSS but can trade a small amount of ranking performance. Absolute alert thresholds selected on validation folds may drift if prevalence or reporting behaviour changes. Rejected alternatives such as SMOTENC and Module 1–symmetric residual stacking show that not every intuitively attractive imbalance or residual idea survives holdout scrutiny.

Module 3 is limited by both grain and objective. With only twenty-five districts, spatial degrees of freedom are small, and spatial K-means cross-validation—while appropriate—cannot substitute for a temporal holdout of the Module 1/2 type. The KDE baseline depends on centroid geometry and a fixed bandwidth rule; continuous IDW maps are visualisation only and must not be mistaken for sub-district resolution. Most importantly, Stage 2 residual adjustment at α = 0.05 did not improve aggregate case-fit. Treating Module 3 as a national intensity optimiser would therefore misrepresent the verified experimental outcome.

**Approx. word count:** 450 words
*(Standalone: `research_context/report_drafts/chapter9_9.3_modelling.md`)*

---

## 9.4 Evaluation, Integration, and Decision-Support Limitations

Evaluation design reduced temporal and spatial leakage, but it did not eliminate all inferential risk. Walk-forward folds and untouched holdouts protect against naive random splits, yet a single final holdout block still reflects one historical window. Module 2’s sparse positives amplify that issue. Module 3’s spatial CV answers a geographic question and should not be rhetorically converted into a temporal forecasting claim. Operational live and forward dashboard products are useful for demonstration, but under Decisions 018 and 027 they remain a weaker evidence tier than frozen research metrics.

Integration across modules is complementary by design and therefore incomplete as a single score. The dashboard presents magnitude, calibrated outbreak risk, and spatial concentration together, but it does not automatically reconcile conflicting signals or prescribe interventions. No Command Centre, scenario-simulation control room, or automated dispatch layer was implemented. Soft decision-support framing is thus a limitation as well as a safeguard: the system can inform situational awareness, yet it cannot replace epidemiological judgement, field investigation, or clinical care pathways.

Ethical and public-health considerations follow from the same boundary. Risk maps and alerts may influence attention and resource discussion; overstated certainty could therefore cause false reassurance or unnecessary alarm. Because the project is a research prototype rather than a certified surveillance system, outputs should be accompanied by uncertainty language, evidence-tier labels, and explicit non-diagnostic disclaimers whenever shown outside the thesis context.

**Approx. word count:** 400 words
*(Standalone: `research_context/report_drafts/chapter9_9.4_evaluation_integration.md`)*

---

## 9.5 Summary

The Residual Compensation Modeling Framework is constrained by district-level data grain, point climate representation, reporting dynamics, rare-event sparsity, incomplete residual whitening, Module 3’s null aggregate-fit result, and the separation between research validation and operational prototype outputs. These limitations do not invalidate the completed modules; they define the honest interpretive envelope around them. Chapter 8’s further-work directions respond to the same constraints. Taken together, Chapters 8 and 9 close the report by affirming what the framework achieved and by stating clearly what it does not yet claim.

**Approx. word count:** 140 words
*(Standalone: `research_context/report_drafts/chapter9_9.5_summary.md`)*

---

## Word-Count Summary

| Section | Approx. words |
|---|---|
| 9.1 Introduction | 160 |
| 9.2 Data and Scope | 380 |
| 9.3 Module-Specific Modelling | 450 |
| 9.4 Evaluation / Integration / Decision-Support | 400 |
| 9.5 Summary | 140 |
| **Chapter 9 total** | **~1,530** |

**Notes for Team:**
- Standalone file: `research_context/report_drafts/chapter9_challenges_limitations.md`
- Keep Chapter 9 diagnostic; keep Chapter 8 prospective
- Do not revive CHIRPS/WorldPop/NASA POWER production claims when discussing data limits
- Next typical report items: References, Appendices
