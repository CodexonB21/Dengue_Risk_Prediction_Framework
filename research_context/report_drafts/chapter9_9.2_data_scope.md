## 9.2 Data and Scope Limitations

The epidemiological foundation of the project is district-level Weekly Epidemiological Report case counts. Aggregation at this grain smooths local transmission heterogeneity and prevents direct identification of neighbourhood or MOH-area hotspots. Underreporting, delayed reporting, and catch-up revisions can distort both recent case lags and outbreak labels, especially around suspected reporting-lag weeks. Although Module 1 introduced reporting-delay features and Module 2 uses fold-aware threshold labels, residual reporting noise remains a structural data limitation rather than a fully solved modelling problem.

Climate inputs were obtained from Open-Meteo as point samples associated with each district rather than as spatially averaged fields. This choice kept the production stack tractable and internally consistent, but it means that weather covariates do not represent intra-district climatic variation. Elevation likewise enters Module 3 as a static district header value. Population covariates rely on census points with interpolation and limited extrapolation; they approximate demography over a long study window but cannot capture short-term mobility or fine-scale exposure. Week-53 handling, Kalmunai-to-Ampara remapping, and shared calendar construction improved factual consistency under Decision 013, yet they also illustrate that epidemiological and climate series required non-trivial alignment before modelling could begin.

Scope was deliberately district-level and Sri Lanka–specific. The framework therefore cannot claim immediate transfer to other countries, to finer administrative units, or to syndromic streams beyond the WER case definition used here. Any expansion of scope would require a new data contract, not only a model re-fit.

**Approx. word count:** 380 words
*(Standalone: `research_context/report_drafts/chapter9_9.2_data_scope.md`)*

---
