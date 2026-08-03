# Chapter 6 — Section 6.1 Introduction

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous chapter:** Chapter 5 — Analysis and Design  
**Next topic:** 6.2 Datasets Incorporated  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

## 6.1 Introduction

This chapter describes how the Residual Compensation Modeling Framework for dengue risk prediction was implemented in practice. Whereas Chapter 5 established the structural design of shared and module-specific pipelines, the present chapter documents the concrete datasets, preprocessing decisions, modelling stages, and output artefacts that realise that design. The aim is to show what was built, how it was organised in code and data products, and why selected implementation choices were required for temporally and spatially valid residual compensation.

Three data families underpin the implementation. Weekly district-level dengue case counts were obtained from the Weekly Epidemiological Reports published by the Epidemiology Unit of the Ministry of Health, Sri Lanka, and aligned to the Ministry’s official epidemiological-week calendar rather than ISO weeks. Meteorological covariates were obtained from Open-Meteo as daily district-point series and aggregated to the same epi-week calendar. Spatial and demographic context for hotspot modelling was drawn from GADM Level-1 district polygons, census population series, and elevation values recorded in the Open-Meteo station headers. In accordance with Decision 013, transformations that every module would apply for the same reason were placed in a shared preprocessing layer, while modelling assumptions that serve only one baseline—for example, SARIMA’s fixed fifty-two-week seasonal period—were confined to module-specific stages.

The implemented system comprises three residual-compensation pipelines—Hybrid Time-Series Case Forecasting, Hybrid Outbreak Risk Classification, and Hybrid Spatial Hotspot Detection—together with a Streamlit early-warning dashboard that consumes their curated outputs. The remainder of the chapter presents the incorporated datasets, the shared pipeline architecture, the Stage 1 and Stage 2 implementation of each module, and the dashboard as a read-only decision-support interface. Numerical evaluation results are reserved for Chapter 7. The dashboard is presented as a soft decision-support prototype for analytical early-warning review; it is not claimed as an operational public-health command system or as a certified clinical decision tool.

**Approx. word count:** 250 words

**Visuals for this section:** none required.

**Notes for Team:**
- Do not paste NASA POWER / CHIRPS / WorldPop wording from the interim draft.
- Next topic: **6.2 Datasets Incorporated** (starting with 6.2.1 epidemiological).
