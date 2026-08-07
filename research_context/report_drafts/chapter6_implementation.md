# Chapter 6 – Implementation

**Status:** Full paste-ready draft (hybrid structure 6.1–6.8)  
**Last updated:** 2026-07-30  
**Sources:** `DATA_DICTIONARY.md`, `PIPELINE_ARCHITECTURE_PLAN.md`, `FEATURE_ENGINEERING_SPEC.md`, `RESEARCH_DECISIONS.md`, Module 1/2/3 contexts  
**Supersedes:** interim NASA POWER / CHIRPS draft; earlier stub `chapter6_6.2_6.3_m1_m2.md` (renumbered into 6.4–6.5)

**Figures:** `research_context/report_drafts/diagrams/figure_6_1_shared_pipeline.png` … `figure_6_5_dashboard_outputs.png`

---

## 6.1 Introduction

This chapter describes how the Residual Compensation Modeling Framework for dengue risk prediction was implemented in practice. Whereas Chapter 5 established the structural design of shared and module-specific pipelines, the present chapter documents the concrete datasets, preprocessing decisions, modelling stages, and output artefacts that realise that design. The aim is to show what was built, how it was organised in code and data products, and why selected implementation choices were required for temporally and spatially valid residual compensation.

Three data families underpin the implementation. Weekly district-level dengue case counts were obtained from the Weekly Epidemiological Reports published by the Epidemiology Unit of the Ministry of Health, Sri Lanka, and aligned to the Ministry’s official epidemiological-week calendar rather than ISO weeks. Meteorological covariates were obtained from Open-Meteo as daily district-point series and aggregated to the same epi-week calendar. Spatial and demographic context for hotspot modelling was drawn from GADM Level-1 district polygons, census population series, and elevation values recorded in the Open-Meteo station headers. In accordance with Decision 013, transformations that every module would apply for the same reason were placed in a shared preprocessing layer, while modelling assumptions that serve only one baseline—for example, SARIMA’s fixed fifty-two-week seasonal period—were confined to module-specific stages.

The implemented system comprises three residual-compensation pipelines—Hybrid Time-Series Case Forecasting, Hybrid Outbreak Risk Classification, and Hybrid Spatial Hotspot Detection—together with a Streamlit early-warning dashboard that consumes their curated outputs. The remainder of the chapter presents the incorporated datasets, the shared pipeline architecture, the Stage 1 and Stage 2 implementation of each module, and the dashboard as a read-only decision-support interface. Numerical evaluation results are reserved for Chapter 7. The dashboard is presented as a soft decision-support prototype for analytical early-warning review; it is not claimed as an operational public-health command system or as a certified clinical decision tool.

**Approx. word count:** 250 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.1_introduction.md`)*

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
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.2.1_epidemiological.md`)*

### 6.2.2 Meteorological Dataset: Open-Meteo District Climate Series

Meteorological covariates were obtained from Open-Meteo as daily weather series for a representative point in each of the twenty-five modelling districts. This climate source replaced the earlier NASA POWER-based interim description and is the production weather input for Modules 1, 2, and 3. Daily records were temporally aligned to the Ministry of Health epidemiological-week calendar and aggregated to weekly resolution so that climate features share a common temporal key with dengue case counts.

An important spatial caveat applies throughout the project. Open-Meteo values are point samples at a single coordinate per district, not district-wide spatial averages. Larger districts may therefore have reduced spatial representativeness relative to smaller ones. This is a data-source constraint rather than a silent processing assumption, and it is stated explicitly as a modelling limitation for later discussion in the challenges chapter.

Historical daily coverage begins on 1 January 2007. The series is maintained through Open-Meteo Archive and Forecast refresh scripts, so observed daily weather can be extended with short-range forecast days where required for operational dashboard refresh. Weekly aggregation uses the shared master epidemiological-week calendar constructed from the MoH scrape, rather than deriving week boundaries independently from each district’s climate file. Aggregation followed physically motivated rules: temperature and relative-humidity fields were reduced by weekly means of the relevant daily statistics, while precipitation and rainfall were reduced by weekly sums.

Among rainfall-related fields, `precipitation_sum` was preferred over `rain_sum` as the primary precipitation signal for Modules 1 and 2. Open-Meteo defines precipitation as the sum of rain, showers, and snowfall liquid equivalent. Because Sri Lanka’s monsoon rainfall is strongly shower-driven, excluding showers would risk understating water input relevant to mosquito breeding habitat. The categorical `weather_code` field was retained in the shared weekly climate table for audit completeness but was excluded from model feature matrices by default (Decision 008), because continuous temperature, humidity, and precipitation variables already capture the physically relevant signal with less encoding complexity.

Climate enters each module at a different stage, reflecting Decision 001 and the residual-compensation philosophy. Module 1 keeps Stage 1 climate-free so that SARIMA residuals can preserve unexplained climate-linked structure for Stage 2 compensation. Module 2 includes lagged climate, current-week climate, and fold-aware climate anomalies in Stage 1 features because outbreak classification has no equivalent purity constraint and because current-week weather is observable before confirmed case counts. Module 3 consumes the same district-level weekly Open-Meteo climate table for spatial residual adjustment and does not use CHIRPS raster rainfall as a production covariate. Table 6.2 summarises the principal weekly aggregation choices.

**Table 6.2: Open-Meteo variables and weekly aggregation rules**

| Variable | Weekly aggregation | Modelling status |
|---|---|---|
| `temperature_2m_mean` / `max` / `min` | Weekly mean of daily values | Used (temperature features and anomalies) |
| `relative_humidity_2m_mean` (/ `max` / `min`) | Weekly mean of daily values | Used (humidity features and anomalies) |
| `precipitation_sum` | Weekly sum | Preferred primary precipitation signal |
| `rain_sum` | Weekly sum | Available; not the preferred primary rainfall column for Modules 1–2 |
| `weather_code` | Retained in shared weekly table | Excluded from model feature matrices by default |

As shown in Table 6.2, retention of a variable in the shared climate table does not imply that it is used as a modelling feature. Feature exclusion remains a module-level decision under Decision 013, while the shared layer preserves a complete weekly climate artefact for audit and reuse.

**Approx. word count:** 380 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.2.2_meteorological.md`)*

### 6.2.3 Spatial and Demographic Datasets for Module 3

Module 3 required explicit spatial geometry and demographic context in addition to the shared epidemiological and climate tables. Unlike Modules 1 and 2, which operate on tabular district-week series alone, Hybrid Spatial Hotspot Detection needs district polygons, centroids, contiguity relationships, and population exposure measures so that a spatial baseline and residual correction can be constructed. These layers were assembled at the same twenty-five-district resolution used by the temporal modules, preserving cross-module comparability.

District boundary polygons were obtained from the Global Administrative Areas (GADM) database, version 4.1, at administrative Level-1. Level-1 corresponds to Sri Lanka’s twenty-five districts and was used to derive district centroids for kernel density estimation, to construct queen-contiguity spatial weights for Moran’s I, and to compute district land area for population-density derivation. GADM Level-2 boundaries, which represent divisional secretariat divisions, were deliberately not used. The analytical target of the framework remains district-level risk support rather than DS-division hotspot targeting, and fine-scale geocoded case locations are not publicly available in the MoH weekly reports.

Population denominators were taken from national census counts for 2001, 2012, and 2024. An annual `Estimated_Population` series was produced for each district by linear interpolation between consecutive census points and by linear extrapolation beyond 2024 using each district’s own 2012–2024 slope. Population density was then derived as `Estimated_Population` divided by district land area from the reprojected GADM polygons, rather than by importing an external gridded population product. A documented limitation applies to districts whose census totals are non-monotonic across 2001–2012 because of wartime displacement; linear interpolation cannot recover the true wartime population path in those districts, and incidence-style reporting for that period should carry a caveat. Elevation (`elevation_m`) was extracted from Open-Meteo weather-file headers as a static district covariate.

Climate for Module 3 uses the same district-level weekly Open-Meteo series described in Section 6.2.2, joined into the Module 3 master table on district and epidemiological week. This keeps spatial residual adjustment on a temporally consistent grain with Modules 1 and 2. Equally important is what was rejected for production. Earlier interim wording had contemplated CHIRPS rainfall rasters, WorldPop population grids, and SRTM elevation grids with DS-division targeting. The implemented Module 3 stack does not depend on those products. District weekly Open-Meteo climate, census-based population, Open-Meteo elevation headers, and GADM Level-1 geometry constitute the production spatial–demographic context. This choice preserves alignment with Modules 1 and 2, reduces multi-source raster alignment risk, and keeps the spatial module honest about operating at district rather than fine-scale resolution.

**Approx. word count:** 360 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.2.3_spatial_demographic.md`)*

### 6.2.4 Dataset Summary

Table 6.3 consolidates the datasets incorporated by the implemented Residual Compensation Modeling Framework. It emphasises source provenance, temporal coverage, spatial coverage, and file format so that later evaluation claims can be traced to clearly scoped inputs rather than to an ambiguous multi-source stack. The summary also makes the production climate and spatial choices explicit: Open-Meteo is used throughout, and Module 3 operates at GADM Level-1 district resolution without a CHIRPS/WorldPop raster pipeline.

**Table 6.3: Summary of datasets incorporated in the framework**

| Module(s) | Dataset | Source | Temporal Coverage | Spatial Coverage | Format |
|---|---|---|---|---|---|
| 1, 2, 3 | Weekly dengue cases | MoH WER (`epid.gov.lk`) | ~2006-12-23 to 2026-06-21 | 25 districts (Kalmunai→Ampara) | CSV |
| 1, 2, 3 | Daily / weekly climate | Open-Meteo | Daily from 2007-01-01; weekly via epi-week calendar | One point per district | CSV |
| 3 | District boundaries | GADM v4.1 Level-1 | Static geometry | 25 districts | Shapefile / GeoJSON |
| 1, 2, 3 | Census population | National census 2001 / 2012 / 2024 | Annual interpolated / extrapolated series | 25 districts | CSV |
| 3 | Elevation | Open-Meteo weather-file headers | Static | 25 districts | Extracted scalar per district |

As shown in Table 6.3, epidemiological cases and Open-Meteo climate form the shared backbone of all three modules, while GADM Level-1 geometry and Open-Meteo elevation are Module 3–specific spatial inputs. Census population is shared as an annual series and is further converted to population density within Module 3 using district land area. This consolidated view closes the dataset section and prepares for the shared preprocessing and module-specific pipeline architecture described next.

**Approx. word count:** 160 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.2.4_dataset_summary.md`)*

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
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.3_shared_preprocessing.md`)*

---

## 6.4 Implementation of Module 1: Hybrid Time-Series Case Forecasting

Module 1 was implemented as a layered district-week forecasting pipeline: Module 1–specific temporal adjustments on the shared base tables, Stage 1 SARIMA baseline forecasting, Stage 2 feature construction, and pooled XGBoost residual compensation. The implementation follows the accepted residual-compensation principle:

```text
residual = actual_cases − sarima_prediction
final_prediction = sarima_prediction + predicted_residual
```

Figure 6.2 summarises this implementation flow from preprocessing through final forecast combination.

**[Insert Figure 6.2 here]**

**Figure 6.2:** Implementation pipeline of Module 1 — Hybrid Time-Series Case Forecasting (Module 1 preprocessing → SARIMA → residual features → XGBoost → final forecast).

### 6.4.1 Module 1 Preprocessing

Module 1 preprocessing begins from the shared epidemiological and climate tables and applies only those temporal adjustments required by SARIMA and by Stage 2 feature construction. In years containing fifty-three MoH epidemiological weeks (2009, 2016, 2019, and 2021), week 53 was merged into week 52 by summing cases and averaging climate columns. This yields a regular fifty-two-week seasonal period compatible with `sin_week` / `cos_week` encodings and with SARIMA’s fixed seasonal period. Remaining genuine missing weeks were filled by a seasonal-naive rule that replaces an absent district-week with the mean of the same district and week number across other available years. Every filled row was flagged with `is_imputed = True` so that imputed magnitudes could later be excluded from residual targets and from primary accuracy metrics while still contributing lag context for subsequent real weeks.

Climate was then joined on `(District, Year, Week)`, and population was joined annually to support reporting-layer incidence where required. The categorical `weather_code` column remained present in the processed Module 1 table but was excluded at feature selection, consistent with Decision 008. Suspected reporting-anomaly weeks were additionally flagged so that case-derived lag features could mask untrusted values without deleting the underlying reported counts. The resulting weekly modelling table therefore contains a complete district-week panel suitable for Stage 1 fitting and Stage 2 feature derivation without silently treating missing weeks as zero cases.

### 6.4.2 Stage 1: Per-District SARIMA Baseline

Stage 1 fits one SARIMA model per district using weekly `Number_of_Cases` only. Climate covariates are deliberately excluded so that residual compensation remains meaningful and so that Stage 1 does not absorb the climate signal that Stage 2 is intended to learn (Decision 001). Candidate orders and an optional `log1p` transform were explored with constrained `auto_arima` search on pre-holdout history; thereafter, each walk-forward fold refitted a fixed-order model on that fold’s own training window only. Selected configurations were held fixed across folds and the holdout block. Predictions were inverse-transformed to the raw case-count scale before residual construction, and forecasts were clipped at zero to avoid nonsensical negative case counts. Explosive or non-stationary autoregressive roots were guarded against during fitting so that divergent fold forecasts would be recorded as missing rather than allowed to contaminate later residual training. Stage 1 therefore produces out-of-sample `sarima_prediction` values for every validation and holdout district-week that can serve as honest residual targets under Decision 010.

### 6.4.3 Stage 2: XGBoost Residual Compensation

Stage 2 predicts the SARIMA residual rather than re-predicting the raw case count from scratch. Feature groups comprise lagged and rolling case-trend features (lags 1–4, 4-week rolling mean/standard deviation, rate of change); lagged precipitation (`precipitation_sum`, lags 2–8), temperature, and humidity; fold-aware climate anomalies recomputed from each fold’s training window only; seasonal encodings (`sin_week`, `cos_week`) and southwest/northeast monsoon indicators; residual lags constructed by full-calendar reindexing before shifting; reporting-delay state features where adopted; and the SARIMA prediction itself. District is included as a categorical feature because Stage 2 is implemented as a single pooled XGBoost model rather than twenty-five independent district models, giving early folds enough training mass while still allowing district-specific error behaviour.

Training uses the robust objective `reg:absoluteerror` so that rare extreme Stage 1 residuals cannot dominate a pooled squared-error loss and silently corrupt compensation for every other district. Rows flagged as imputed are excluded from residual targets, climate anomalies are never computed from future norms relative to a fold’s cutoff, and residual lags are never allowed to jump across the structural gap between the final validation fold and the holdout block.

### 6.4.4 Training Protocol and Artefacts

Module 1 training follows Decision 009: expanding-window annual walk-forward folds on the pre-holdout history, with the final approximately two years reserved as an untouched holdout block (104 weeks per district under the Module 1 calendar). Within each fold, Stage 1 is refitted on data available up to the fold cutoff, Stage 2 is trained only on prior out-of-sample residuals, and the final forecast is formed by adding the predicted residual to the SARIMA prediction, with non-negative clipping applied to the combined prediction. Metrics are computed after excluding imputed evaluation rows; quantitative accuracy is reserved for Chapter 7.

The pipeline was implemented as an idempotent sequence of scripts rather than as an interactive notebook workflow. Principal artefacts include the Module 1 weekly modelling table, Stage 1 prediction and selected-configuration files, the Stage 2 feature table, fold-wise and final XGBoost model files, combined prediction tables, and metrics and figures under the Module 1 outputs directory. A separate forward-forecast script generates recursive multi-step operational forecasts beyond the last observed case week, and a rolling one-step evaluator provides an operational-deployment analogue; both are kept distinct from the holdout-validated evidence path so that research claims and prototype forward outputs are never conflated. As illustrated in Figure 6.2, Stage 1 remains case-only, while climate and anomaly structure enter only through Stage 2 residual learning.

**Approx. word count:** 880 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.4_module1.md`)*

---

## 6.5 Implementation of Module 2: Hybrid Outbreak Risk Classification

Module 2 was implemented on the same shared epidemiological and climate base tables as Module 1, but with Module 2–specific preprocessing, fold-aware epidemic-threshold labelling, Stage 1 Random Forest classification, and Stage 2 isotonic probability calibration. The module predicts outbreak risk rather than exact case counts. Graded early-warning communication is obtained from calibrated probabilities through fixed absolute thresholds (`alert_flag` and `risk_tier`), not by treating a separate multi-class label as the primary modelling target.

Figure 6.3 summarises the Module 2 implementation path from preprocessing and labelling through calibrated alerts.

**[Insert Figure 6.3 here]**

**Figure 6.3:** Implementation pipeline of Module 2 — Hybrid Outbreak Risk Classification (Module 2 preprocessing → epidemic-threshold labels → Random Forest → isotonic calibration → alert / risk tier).

### 6.5.1 Module 2 Preprocessing and Label Construction

Module 2 begins from the same shared tables as Module 1 but applies Decision 020’s independent temporal policy. Week 53 is retained as its own district-week row rather than merged into week 52, because merging would sum two real weeks before threshold comparison and would contaminate week-52 historical statistics across all years. Missing weeks are still seasonal-naive imputed for lag alignment, but every imputed row is masked to missing before case-derived features and labels are computed, preventing fabricated seasonal-naive values from flowing into neighbouring weeks’ lags or rolling statistics. Weekly climate is joined from the shared table; `weather_code` is excluded from model features by default. Leakage-prone columns such as contemporaneous `Number_of_Cases` and `cases_per_100k` are excluded from the model feature matrix.

Outbreak labels follow a binary epidemic-threshold definition:

```text
outbreak = 1 if Number_of_Cases > historical_mean + k × historical_SD
```

Historical mean and standard deviation are estimated from a per-district harmonic seasonal curve fitted only on strictly prior years, with `k = 3.0` after re-audit for that estimator (Decision 025). Rows lacking sufficient prior history receive undefined labels and are excluded from training and scoring rather than defaulted to non-outbreak. Synthetic oversampling methods such as SMOTE were audited and rejected for production (Decision 026), so class imbalance is handled through model weights rather than fabricated minority samples that could interpolate implausible lag combinations across a temporal split.

### 6.5.2 Stage 1: Pooled Random Forest Classifier

Stage 1 benchmarks candidate classifiers under walk-forward evaluation and, after label re-estimation, selects a pooled Random Forest with `District` encoded as a categorical feature (Decision 025). Unlike Module 1 Stage 1, Module 2 Stage 1 includes climate: lagged precipitation, temperature, and humidity; current-week climate; and fold-aware climate anomalies recomputed from each fold’s training window. Case-trend features, seasonal encodings, monsoon indicators, and lagged case-seasonal anomalies complete the feature matrix. Class-weight balancing is applied for Random Forest, and a Module 2–specific minimum training depth (`MIN_TRAIN_YEARS`) is used because the label’s own prior-history requirement would otherwise leave the first fold without trainable defined labels. Median imputation and District encoding for models that cannot handle missing values natively are fitted on each fold’s training rows only. Raw `Year` and current-week case count / incidence are excluded to prevent trivial label leakage or exploitation of the walk-forward split structure.

### 6.5.3 Stage 2: Isotonic Calibration and Risk Tiers

Stage 2 does not regress a literal `label − predicted_probability` residual, which is statistically ill-posed for a binary target. Instead, well-posed calibration architectures were benchmarked—isotonic regression, Platt scaling, and stacked contextual correction—and isotonic regression on the Stage 1 predicted probability was selected as the official compensation stage. In functional terms, Stage 2 learns a monotone mapping

```text
calibrated_probability = g(predicted_probability)
```

where `g` is the fitted isotonic calibrator trained only on prior out-of-sample Stage 1 probabilities. From the calibrated probability, the pipeline derives a binary `alert_flag` and a nested `risk_tier` (`low` / `medium` / `high`) using fixed absolute probability thresholds selected on validation folds only. Exact threshold values and their holdout operating characteristics are reported in Chapter 7. Quantile-based tiers were rejected because they would force a constant fraction of high-risk weeks irrespective of epidemic conditions once probabilities are calibrated. Reliability diagrams and threshold-scan tables are persisted so that alert behaviour remains auditable without re-fitting.

### 6.5.4 Training Protocol and Artefacts

Module 2 uses expanding-window walk-forward folds plus a final two-year holdout, with fold generation adapted to the higher minimum training depth required by label history. Stage 2 fold `k` trains only on official Stage 1 out-of-sample probabilities from earlier folds, with fold 1 treated as a documented passthrough when no prior out-of-sample probabilities yet exist. Pipeline artefacts include the Module 2 weekly modelling table, Stage 1 feature table, baseline classifier predictions and models, Stage 2 compensated predictions and calibrators, risk-tier prediction tables, threshold-scan metrics, reliability diagrams, and separate live and forward operational scoring outputs tagged as operational evidence.

Training and holdout evaluation remain independent of Module 1 forecasts; Module 1 case forecasts are used only in operational forward-risk feature assembly beyond the last observed case week. Live scoring recomputes features for recent weeks through frozen Stage 1 and Stage 2 artefacts without rewriting the validated prediction tables. As illustrated in Figure 6.3, validated research scoring is separated from operational live/forward scoring scripts that consume frozen production models without altering holdout evidence. Classification performance metrics themselves are deferred to Chapter 7.

**Approx. word count:** 900 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.5_module2.md`)*

---

## 6.6 Implementation of Module 3: Hybrid Spatial Hotspot Detection

### 6.6.1 Master Table Construction

Module 3 preprocessing joins the shared epidemiological, weekly climate, and annual population tables with GADM Level-1 geometry and Open-Meteo elevation into a spatial master table. Each row remains a district-week unit, preserving temporal compatibility with Modules 1 and 2 while adding the spatial attributes required for kernel density estimation, contiguity weights, and environmental residual adjustment. Population density is derived from Estimated_Population and district land area rather than imported from an external gridded population product. Elevation enters as a static district covariate extracted from Open-Meteo response headers. Rows outside climate coverage are dropped before Stage 1 density estimation so that later residual features are not built on incomplete environmental joins.

This construction deliberately keeps Module 3 at district level. No DS-division, MOH-area, or raster population stack is introduced in the production path. The master table therefore provides a single district-week analytical grain for both the spatial baseline and the residual compensation stage, and it remains consistent with the spatial and demographic sources described in Section 6.2.3.

### 6.6.2 Stage 1: KDE Baseline and Moran’s I Validation

Stage 1 constructs a case-weighted kernel density surface over district centroids using a Gaussian kernel and Silverman’s bandwidth rule. Bandwidth is derived once from the spatial spread of the centroids so that smoothing scale remains a property of geography rather than of week-to-week epidemic intensity. Global Moran’s I with queen-contiguity weights then validates whether the resulting surface exhibits genuine spatial clustering rather than spatial randomness. Local indicators and Getis-Ord statistics remain optional extensions and are not required for the production Stage 1 path.

The same KDE_baseline quantity is used in two deliberate forms. In raw form it is a normalised density surface suitable for scale-invariant Moran’s I validation. For Stage 2 residual modelling it is rescaled in a mass-conserving way within each week so that district baseline risk sums to that week’s national case total. Rescaling preserves the spatial redistribution shape encoded by the kernel while making the baseline magnitude comparable to actual case intensity. This dual use is an implementation necessity, not a contradiction: clustering validation does not require absolute case-scale magnitudes, whereas residual subtraction does.

### 6.6.3 Stage 2: Random Forest Residual Adjustment and Iterative Update

Stage 2 defines the spatial residual as

```text
Residual = Actual_case_intensity − Current_Risk
```

where Current_Risk begins as the rescaled KDE baseline and is updated across iterations. A Random Forest regressor predicts residuals from rainfall and temperature lags, climate anomalies, monsoon indicators, elevation, population density, and a Mahalanobis anomaly score over selected environmental and demographic variables. Validation uses spatial K-means cross-validation on district centroids so that whole districts remain together within folds, matching the spatial rather than temporal research question of Module 3.

The iterative update applies shrinkage:

```text
Risk_t = Risk_(t-1) + α · predicted_residual_t
```

with α = 0.05. The unshrunk update was found to diverge under honest out-of-fold residual prediction because static district covariates make held-out-district extrapolation imperfect; adding full-magnitude prediction error back into Risk compounds iteration over iteration. The shrinkage term stabilises convergence under a dual check on risk-value change and residual Moran’s I significance, with a small iteration cap as a safeguard. Retraining within the loop uses the same spatial folds so that predicted residuals remain out of fold for held-out districts rather than memorising in-sample targets.

### 6.6.4 Converged Risk Map and Visualisation

The converged Risk surface is exported as the hybrid risk map for dashboard and report visualisation. Continuous map rendering interpolates the twenty-five district Risk scores onto a land-clipped grid using k-nearest-neighbour inverse-distance weighting with k = 4 and power = 4. IDW is a visualisation-layer technique only; it is not an additional modelling stage and does not alter Stage 1 or Stage 2 estimates. Choropleth maps and generic heatmap blur were judged insufficient to communicate neighbourhood blending already implied by the KDE geometry, whereas IDW with a limited neighbour set and steeper distance decay better preserves local hotspot contrast without colouring ocean cells.

Importantly, Stage 2 is not claimed to improve aggregate case-fit relative to the rescaled Stage 1 baseline. The implemented correction prioritises stable spatial residual adjustment and covariate-informed explanation of burden deviations; any aggregate fit comparison belongs in Chapter 7 and must be reported honestly rather than reframed around a more flattering secondary metric. Figure 6.4 summarises the Module 3 implementation stack.

[Insert Figure 6.4 here]

**Figure 6.4: Module 3 implementation workflow from master-table construction through KDE/Moran’s I, Random Forest residual adjustment, iterative α-update, and IDW visualisation**

Figure 6.4 should be interpreted as a district-level spatial residual-compensation pipeline grounded in Open-Meteo and GADM Level-1 inputs, not as a CHIRPS/WorldPop/DS-division production system.

**Approx. word count:** 920 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.6_module3.md`)*

---

## 6.7 Output Generation and Early-Warning Dashboard

Validated module outputs are persisted as CSV prediction tables, metrics, figures, and model artefacts under the module-specific processed, features, models, and outputs directories. On top of these research artefacts, an early-warning dashboard was implemented in Streamlit as a read-only consumer of curated files. The dashboard does not retrain models, rewrite holdout predictions, or act as a write-back control interface. Its purpose is to present forecasting, outbreak-risk, and spatial-risk outputs in a form suitable for analytical review, viva demonstration, and soft decision-support discussion.

The interface deliberately separates research and operational evidence tiers. The research tier surfaces holdout-validated and walk-forward artefacts that may be cited alongside Chapter 7 evaluation claims, including Stage 1 versus Stage 1-plus-Stage 2 comparisons where available. The operational tier presents live recent-week scoring and forward prototype outputs—Module 1 future case forecasts, Module 2 live and forward risk predictions, and Module 3 hybrid risk views—explicitly tagged so that they cannot be mistaken for holdout accuracy. Typical views include district selection, recent calibrated risk trajectories, forward case and risk horizons with completeness diagnostics, alert or tier summaries, and spatial risk map rendering. Module 1 answers expected case magnitude, Module 2 answers elevated outbreak-risk state, and Module 3 answers spatial concentration; the dashboard keeps these complementary products visible rather than collapsing them into a single undifferentiated score. No Command Centre, scenario-simulation control room, or automated intervention dispatch layer is implemented or claimed.

Operational refresh is orchestrated at a high level by `scripts/refresh_dashboard_data.py`. The script coordinates Open-Meteo weather refresh, shared and module preprocessing updates where required, Module 1 forward forecasting, and Module 2 live/forward risk scoring before the Streamlit application reads the resulting CSV products. This keeps data-currency concerns outside the validated training loop and preserves the distinction between research evidence and operational prototype behaviour. Because the dashboard is read-only, regenerating operational files cannot silently overwrite the frozen research metrics used for thesis evaluation. Figure 6.5 illustrates the dashboard’s relationship to the three module pipelines.

[Insert Figure 6.5 here]

**Figure 6.5: Streamlit early-warning dashboard as a read-only consumer of research and operational module outputs**

Figure 6.5 reinforces the soft decision-support framing introduced in Section 6.1: the dashboard integrates module outputs for inspection, but evaluation authority remains with the holdout-validated artefacts documented in Chapter 7.

**Approx. word count:** 430 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.7_dashboard.md`)*

---

## 6.8 Summary

This chapter documented the implementation of the Residual Compensation Modeling Framework, from dataset incorporation through shared preprocessing, three module pipelines, and a Streamlit early-warning dashboard. Epidemiological WER cases, Open-Meteo climate, GADM Level-1 geometry, census population, and Open-Meteo elevation formed the production data stack. Decision 013 separated shared factual cleaning from module-specific modelling assumptions, allowing Module 1 to merge week 53 for SARIMA, Module 2 to retain week 53 for threshold integrity, and Module 3 to build a spatial master table without inheriting SARIMA constraints. Module 1 was implemented as per-district SARIMA followed by pooled XGBoost residual compensation; Module 2 as pooled Random Forest classification followed by isotonic calibration and fixed-threshold alerts; and Module 3 as case-weighted KDE with Moran’s I validation, followed by Random Forest residual adjustment under an iterative α = 0.05 update, with IDW used only for visualisation. The dashboard consumes these outputs as a soft decision-support prototype with explicit research versus operational evidence tiers. Chapter 7 evaluates the quantitative performance of these implemented pipelines using the holdout-validated metrics and spatial diagnostics reserved for that purpose.

**Approx. word count:** 175 words
*(Standalone paste-ready file: `research_context/report_drafts/chapter6_6.8_summary.md`)*

---

## Word-Count Summary

| Section | Approx. words |
|---|---|
| 6.1 Introduction | 185 |
| 6.2 Lead-in | 78 |
| 6.2.1 Epidemiological | 325 |
| 6.2.2 Meteorological (Open-Meteo) | 330 |
| 6.2.3 Spatial/demographic | 295 |
| 6.2.4 Dataset summary | 85 |
| 6.3 Shared preprocessing | 405 |
| 6.4 Module 1 (6.4.1–6.4.4) | 850 |
| 6.5 Module 2 (6.5.1–6.5.4) | 855 |
| 6.6 Module 3 (6.6.1–6.6.4) | 920 |
| 6.7 Dashboard | 430 |
| 6.8 Summary | 175 |
| **Chapter 6 total (body)** | **~4,873** |

---

## Notes for Team

- NASA POWER wording from interim drafts must not re-enter this chapter; production climate is Open-Meteo only.
- CHIRPS / WorldPop / SRTM-grid / GADM Level-2 / DS-division production claims are explicitly rejected for Module 3; keep GADM L1 + census population + Open-Meteo elevation/climate.
- Module 2 alert_threshold and high_confidence_threshold numeric values belong in Chapter 7, not in the Implementation body.
- Module 3 honesty requirement: do not claim Stage 2 improves aggregate case-fit; IDW is visualisation only; α = 0.05 is a stability choice.
- Insert/export Figures 6.1–6.5 before Word paste; captions are ready above.
- No invented RMSE/MAE/PR-AUC/BSS/MASE numbers were included in this chapter.
