# Chapter 6 — Section 6.2 Lead-in + 6.2.1 Epidemiological Dataset

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 6.1 Introduction  
**Next topic:** 6.2.2 Meteorological Dataset (Open-Meteo)  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

## 6.2 Datasets Incorporated

The Residual Compensation Modeling Framework was implemented using three complementary data families: epidemiological case reports, meteorological observations, and spatial–demographic layers required by Module 3. Each source was selected for district-level coverage, temporal compatibility with the Ministry of Health epidemiological-week calendar, and reproducibility under a Python-based research pipeline. The subsections below describe the provenance, structure, coverage, and module roles of these datasets before summarising them in a consolidated comparison table.

### 6.2.1 Epidemiological Dataset: Weekly Dengue Case Counts

Weekly dengue case counts were obtained from the Epidemiology Unit of the Ministry of Health, Sri Lanka, as published in the Weekly Epidemiological Reports (WER) available through `epid.gov.lk`. The series provides district-level surveillance counts and forms the primary epidemiological input for all three analytical modules. Weeks follow the Ministry’s official epidemiological-week definition rather than a plain ISO calendar week. Because MoH week boundaries are not identical to ISO weeks, a master epidemiological-week calendar was constructed from the same scrape and used as the single temporal spine for aligning climate and other covariates.

After audit and correction of source inconsistencies—including duplicate `(District, Year, Week)` collisions and date-boundary errors—the usable coverage spans approximately 23 December 2006 to 21 June 2026, corresponding to roughly 19.5 years of district-week observations. This horizon is long enough to support expanding-window walk-forward modelling while still leaving a multi-year holdout block for final reporting. Confirmed fifty-three-week years in the MoH calendar are 2009, 2016, 2019, and 2021; module-specific handling of week 53 is described later under shared versus module-specific preprocessing.

The modelling table retains the core fields listed in Table 6.1. These columns jointly identify the administrative unit, the reported case burden, and the MoH week boundaries used for climate alignment. Kalmunai appears in the raw reporting series but has no matching Open-Meteo weather station and is administratively associated with Ampara District. Shared preprocessing therefore merges Kalmunai into Ampara by summing cases for shared epidemiological weeks. After this merge, the framework models exactly the twenty-five official districts.

**Table 6.1: Epidemiological dataset columns used in the framework**

| Column | Description | Role in the framework |
|---|---|---|
| District | Administrative district name | Spatial key and per-district segmentation |
| Number_of_Cases | Weekly reported dengue cases | Module 1 target; Module 2 label input; Module 3 KDE weight |
| Week_Start_Date | Start date of the MoH epi-week | Temporal ordering and calendar construction |
| Week_End_Date | End date of the MoH epi-week | Temporal ordering and calendar construction |
| Year | Calendar year of the epi-week | Temporal splits, expanding history, reporting |
| Week | MoH epidemiological week number | Seasonality, lag alignment, label thresholds |
| Month | Calendar month | Contextual checking and reporting |

As shown in Table 6.1, the epidemiological table is not merely a case series: its date fields define the national temporal spine against which climate and spatial covariates are joined.

Two distributional properties of the case series shaped later modelling choices. First, the data are strongly zero-inflated in several Northern and Eastern districts, while high-incidence urban districts report zeros far less often. This heterogeneity affects transform choice, the suitability of percentage-error metrics, and the interpretation of sparse-series forecasts. Second, national dengue burden exhibits bimodal monsoon-linked seasonality associated with the South-West and North-East monsoon windows. Case burden is typically higher in densely populated western and related high-incidence districts such as Colombo, Gampaha, Kalutara, and Kandy. These patterns motivated cyclic week encodings and monsoon indicators in the residual and classification feature sets.

Across modules, `Number_of_Cases` plays distinct but consistent roles. In Module 1 it is the sole Stage 1 SARIMA target and the basis of Stage 2 residuals. In Module 2 it enters fold-aware epidemic-threshold label construction and case-derived lag features. In Module 3 it supplies the case weights for kernel density estimation over district centroids, so that hotspot intensity reflects reported burden rather than unweighted geography alone. Exact cleaned row counts after shared preprocessing are confirmed from the shared epidemiological weekly artefact before final submission if required by examiners.

**Approx. word count:** 420 words (lead-in ~70 + 6.2.1 ~350)

**Notes for Team:**
- Do not claim sub-district case locations; data are district aggregates.
- Week-53 merge policy is Module 1–specific; do not state it as universal here.
- Next: **6.2.2 Meteorological Dataset (Open-Meteo)**.
