## 9.3 Module-Specific Modelling Limitations

Module 1’s Stage 1 SARIMA baseline is intentionally climate-free and cases-only. That design clarifies residual compensation, but it also means Stage 1 alone is often a weak forecaster, particularly in sparse or volatile districts. Stage 2 reduces error magnitude for most districts without fully whitening residuals, as indicated by persistent Ljung–Box significance in many series. Flat multi-step holdout evaluation and rolling one-step operational analogues answer related but different questions; conflating them would overstate either research skill or near-term operational usefulness. Extreme catch-up spikes remain difficult even after reporting-delay features.

Module 2 faces rare-event imbalance by construction. Under the current harmonic label, holdout prevalence is only about 1.5%, so precision, recall, and calibration estimates on the final block are statistically fragile. Strong Stage 1 discrimination does not imply well-calibrated raw probabilities; Stage 2 isotonic correction improves BSS but can trade a small amount of ranking performance. Absolute alert thresholds selected on validation folds may drift if prevalence or reporting behaviour changes. Rejected alternatives such as SMOTENC and Module 1–symmetric residual stacking show that not every intuitively attractive imbalance or residual idea survives holdout scrutiny.

Module 3 is limited by both grain and objective. With only twenty-five districts, spatial degrees of freedom are small, and spatial K-means cross-validation—while appropriate—cannot substitute for a temporal holdout of the Module 1/2 type. The KDE baseline depends on centroid geometry and a fixed bandwidth rule; continuous IDW maps are visualisation only and must not be mistaken for sub-district resolution. Most importantly, Stage 2 residual adjustment at α = 0.05 did not improve aggregate case-fit. Treating Module 3 as a national intensity optimiser would therefore misrepresent the verified experimental outcome.

**Approx. word count:** 450 words
*(Standalone: `research_context/report_drafts/chapter9_9.3_modelling.md`)*

---
