# Chapter 6 — Section 6.2.4 Dataset Summary

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 6.2.3 Spatial and Demographic Datasets  
**Next topic:** 6.3 Shared Preprocessing and Pipeline Architecture (+ Figure 6.1)  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

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

**Notes for Team:**
- Do not reintroduce NASA POWER, CHIRPS, WorldPop, or GADM Level-2 rows into Table 6.3.
- Population density is derived in Module 3, not a separate raw WorldPop dataset.
- Next: **6.3 Shared Preprocessing (+ Figure 6.1)**.
