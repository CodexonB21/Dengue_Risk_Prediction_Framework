# Chapter 5 — Section 5.3 Data Architecture and Pipeline Design

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 5.2 High-Level System Architecture  
**Next topic:** 5.4.1 Module 1 design (+ Figure 5.3)

---

## 5.3 Data Architecture and Pipeline Design

The data architecture distinguishes between shared base tables and module-specific modelling tables. Shared epidemiological weekly data provide district-week case counts and calendar fields. Shared climate weekly data provide aggregated meteorological covariates aligned to the same calendar. Population series support incidence-oriented reporting and Module 3 demographic context. These shared tables are intentionally conservative: they preserve information that later modules may need and avoid imposing one module’s modelling assumptions on the others.

Figure 5.2 shows the resulting data flow. Raw epidemiological, climate, and spatial sources are cleaned into shared tables. Each module then branches into its own preprocessing and feature-engineering path before Stage 1 and Stage 2 modelling. This design prevents silent leakage of SARIMA-specific calendar repairs into classification labelling, and it keeps spatial covariates from being forced into Module 1 Stage 1.

Table 5.1 summarises the principal shared versus module-specific decisions. Week-53 merging, seasonal-naive imputation policy details, and default exclusion of categorical weather codes are Module 1–scoped where they exist to satisfy SARIMA’s fixed seasonal period or Stage 2 feature choices. Module 2 retains week 53 as its own row because merging would distort epidemic-threshold labels and contaminate week-52 historical statistics. Module 3 builds on shared epi-week alignment but adds spatial master-table construction with elevation and population for hotspot modelling.

Feature engineering is designed at group level rather than as an exhaustive dictionary in this chapter. Across modules, the main groups are short-term epidemiological history features, lagged climate and climate-anomaly features, seasonal and monsoon indicators, and module-specific residual or probability-related features. The architecture also encodes leakage guards as design rules: climate anomalies and outbreak labels are computed from strictly prior information within each training window; Module 1 Stage 2 trains on out-of-sample SARIMA residuals rather than in-sample fitted residuals; and imputed or otherwise untrusted case weeks are excluded from evaluation targets or masked before lag construction where required.

As shown in Table 5.1, shared preprocessing is reserved for decisions that are common by necessity. Modelling-specific calendar and feature choices remain inside each module’s pipeline so that residual compensation is evaluated on a design that does not silently bias the other modules. Exact feature dictionaries and implementation scripts are presented in Chapter 6.

**[Insert Figure 5.2 here]**

**Figure 5.2:** Data flow from raw sources through shared and module-specific layers.

**Figure 5.2 content to draw (required):**

```text
Raw sources
  - epidemiological weekly cases (WER)
  - daily Open-Meteo climate
  - spatial: GADM boundaries, population, elevation
        ↓
Shared preprocessing (Decision 013)
  → epidemiological_weekly
  → climate_weekly
  → population series
        ↓
        ┌─────────────────┬─────────────────┬─────────────────┐
        ↓                 ↓                 ↓
 Module 1 prep      Module 2 prep      Module 3 prep
 (week-53 merge,    (week-53 keep,     (spatial master
  impute+flag)       mask imputed)      table)
        ↓                 ↓                 ↓
 Feature groups     Feature groups     Spatial features
 (case/climate      (case/climate      (KDE inputs +
  lags, anomalies,   lags, anomalies,   env/demographic
  residual lags)     case anomalies)    covariates)
        ↓                 ↓                 ↓
 Stage 1 / Stage 2  Stage 1 / Stage 2  Stage 1 / Stage 2
 modelling          modelling          modelling
```

Do **not** show all preprocessing as a single shared block, or put Module 1 week-53 merge upstream of Module 2/3.

**[Insert Table 5.1 here]**

**Table 5.1:** Shared versus module-specific preprocessing decisions in the proposed design.

| Decision area | Shared layer | Module 1 | Module 2 | Module 3 |
|---|---|---|---|---|
| District set / Kalmunai→Ampara merge | Yes | Consumes shared | Consumes shared | Consumes shared |
| Epi-week calendar alignment | Yes | Consumes shared | Consumes shared | Consumes shared |
| Week-53 handling | Leave unmerged | Merge into week 52 for SARIMA (`m=52`) | Keep week 53 | Uses shared calendar; no SARIMA merge requirement |
| Missing-week policy | Gaps may remain as absent rows | Seasonal-naive impute + `is_imputed` | Module-specific impute/mask for case-derived features | Module-specific spatial table construction |
| Climate source aggregation | Canonical weekly climate retained | Stage 2 climate/anomaly features; `weather_code` excluded by default | Climate in Stage 1 features; `weather_code` excluded by default | Climate + elevation/population for spatial residual adjustment |
| Population | Interpolated/extrapolated series available | Reporting-layer use | Not a core Stage 1/2 input | Demographic spatial covariate |

**Approx. word count:** 490 words

**Notes for Team:**
- Cite Figure 5.2 and Table 5.1 in the body (done) and place them after the relevant paragraphs in Word.
- Full feature lists belong in Chapter 6, not here.
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md` (Figure 5.2, Table 5.1).
