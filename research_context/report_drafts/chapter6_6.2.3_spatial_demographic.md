# Chapter 6 — Section 6.2.3 Spatial and Demographic Datasets

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 6.2.2 Meteorological Dataset (Open-Meteo)  
**Next topic:** 6.2.4 Dataset Summary  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

### 6.2.3 Spatial and Demographic Datasets for Module 3

Module 3 required explicit spatial geometry and demographic context in addition to the shared epidemiological and climate tables. Unlike Modules 1 and 2, which operate on tabular district-week series alone, Hybrid Spatial Hotspot Detection needs district polygons, centroids, contiguity relationships, and population exposure measures so that a spatial baseline and residual correction can be constructed. These layers were assembled at the same twenty-five-district resolution used by the temporal modules, preserving cross-module comparability.

District boundary polygons were obtained from the Global Administrative Areas (GADM) database, version 4.1, at administrative Level-1. Level-1 corresponds to Sri Lanka’s twenty-five districts and was used to derive district centroids for kernel density estimation, to construct queen-contiguity spatial weights for Moran’s I, and to compute district land area for population-density derivation. GADM Level-2 boundaries, which represent divisional secretariat divisions, were deliberately not used. The analytical target of the framework remains district-level risk support rather than DS-division hotspot targeting, and fine-scale geocoded case locations are not publicly available in the MoH weekly reports.

Population denominators were taken from national census counts for 2001, 2012, and 2024. An annual `Estimated_Population` series was produced for each district by linear interpolation between consecutive census points and by linear extrapolation beyond 2024 using each district’s own 2012–2024 slope. Population density was then derived as `Estimated_Population` divided by district land area from the reprojected GADM polygons, rather than by importing an external gridded population product. A documented limitation applies to districts whose census totals are non-monotonic across 2001–2012 because of wartime displacement; linear interpolation cannot recover the true wartime population path in those districts, and incidence-style reporting for that period should carry a caveat. Elevation (`elevation_m`) was extracted from Open-Meteo weather-file headers as a static district covariate.

Climate for Module 3 uses the same district-level weekly Open-Meteo series described in Section 6.2.2, joined into the Module 3 master table on district and epidemiological week. This keeps spatial residual adjustment on a temporally consistent grain with Modules 1 and 2. Equally important is what was rejected for production. Earlier interim wording had contemplated CHIRPS rainfall rasters, WorldPop population grids, and SRTM elevation grids with DS-division targeting. The implemented Module 3 stack does not depend on those products. District weekly Open-Meteo climate, census-based population, Open-Meteo elevation headers, and GADM Level-1 geometry constitute the production spatial–demographic context. This choice preserves alignment with Modules 1 and 2, reduces multi-source raster alignment risk, and keeps the spatial module honest about operating at district rather than fine-scale resolution.

**Approx. word count:** 360 words

**Notes for Team:**
- Explicitly reject CHIRPS / WorldPop / SRTM-grid / GADM-L2 production claims.
- Population density is derived, not imported from WorldPop.
- Next: **6.2.4 Dataset Summary** (+ Table 6.3).
