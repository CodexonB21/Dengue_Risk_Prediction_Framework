# Chapter 6 — Section 6.2.2 Meteorological Dataset (Open-Meteo)

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 6.2.1 Epidemiological Dataset  
**Next topic:** 6.2.3 Spatial and Demographic Datasets (Module 3)  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

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

**Notes for Team:**
- Delete all NASA POWER / MERRA-2 / PRECTOTCORR wording from the interim draft.
- Do not describe CHIRPS as the Module 1/2/3 production climate source.
- Point-sample limitation should also appear in Challenges/Limitations later.
- Next: **6.2.3 Spatial and Demographic Datasets**.
