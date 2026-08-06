# Chapter 6 — Section 6.3 Shared Preprocessing (+ Figure 6.1)

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 6.2.4 Dataset Summary  
**Next topic:** 6.4 Implementation of Module 1 (+ Figure 6.2)  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

## 6.3 Shared Preprocessing and Pipeline Architecture

Shared preprocessing implements Decision 013: only transformations that every module would make for the same reason are applied upstream of the modelling forks. This principle was adopted after review found that SARIMA-specific choices—most notably week-53 merging and gap filling—had risked being treated as general-purpose cleaning. Applying those choices in a shared layer would have silently discarded real week-53 observations for Modules 2 and 3 and would have forced unproven temporal assumptions onto modules that do not need a continuous SARIMA calendar. The shared layer therefore creates a common factual base, while modelling assumptions that serve only one baseline remain local to that module.

The shared pipeline loads the audited epidemiological CSV from the Ministry of Health scrape and the flat Open-Meteo weather files for all twenty-five districts. It merges Kalmunai into Ampara by summing `Number_of_Cases` for shared `(Year, Week)` keys, constructs a master MoH epi-week calendar by taking the modal `Week_Start_Date` and `Week_End_Date` across districts for each `(Year, Week)`, and aggregates daily climate onto that calendar while retaining the full set of weekly climate columns. Census population is melted from the wide 2001/2012/2024 source and converted into an annual `Estimated_Population` series by linear interpolation between census years and linear extrapolation beyond 2024. Critically, the cleaned case table is written without week-53 merging and without fabricating missing weeks, so genuine gaps remain absent rows rather than zeros. Shared outputs are stored under `data/processed/shared/`, principally `epidemiological_weekly.csv`, `epi_week_calendar.csv`, `climate_weekly.csv`, and `population_annual.csv`.

Figure 6.1 summarises this shared-to-module architecture.

**[Insert Figure 6.1 here]**

**Figure 6.1:** Shared preprocessing layer and module-specific pipeline forks under Decision 013.

Module-specific preprocessing then diverges deliberately. Module 1 merges week 53 into week 52 to satisfy SARIMA’s fixed seasonal period, applies seasonal-naive imputation with an `is_imputed` flag, and joins climate and population into a regular fifty-two-week modelling table. Module 2 keeps week 53 as its own row so that epidemic-threshold labels and week-52 historical statistics are not contaminated by merge arithmetic; it still imputes missing weeks for lag alignment, but masks imputed case values before deriving case-based features and labels. Module 3 joins the shared tables with GADM Level-1 geometry, elevation, and derived population density into a spatial master table, without inheriting Module 1’s week-53 merge or Module 2’s label-oriented masking rules.

Across the repository, artefacts follow a consistent progression from processed tables to engineered features, fitted models, and evaluation or dashboard outputs. Raw inputs remain under `data/raw/`. Shared and module-specific cleaned tables are written to `data/processed/`. Feature matrices are written to `data/features/`. Fitted Stage 1 and Stage 2 artefacts are stored under `models/`. Metrics and figures are written to `outputs/`. This layout keeps research evidence reproducible, separates validated holdout artefacts from operational refresh products, and makes it possible to regenerate any stage without silently rewriting another module’s evidence base. As illustrated in Figure 6.1, shared cleaning is intentionally conservative: it standardises epidemiology, climate, and population once, then allows each residual-compensation module to apply only the additional transformations its own Stage 1 and Stage 2 designs require.

**Approx. word count:** 430 words

**Suggested Figure:**
Figure 6.1: Shared preprocessing and module-specific pipeline forks.  
Assets: `research_context/report_drafts/diagrams/figure_6_1_shared_pipeline.drawio` (+ `.png`).

**Notes for Team:**
- Do not claim week-53 merge or seasonal-naive imputation as universal shared steps.
- Script names may be mentioned later in module subsections (`shared.py`, `module1_preprocessing.py`, etc.).
- Next: **6.4 Module 1 Implementation (+ Figure 6.2)**.
