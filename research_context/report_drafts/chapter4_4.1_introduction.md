# Chapter 4 — Section 4.1 Introduction

**Source of truth:** `CURRENT_ARCHITECTURE.md`, Chapter 4 module drafts, Decisions 001/022/025  
**Status:** Draft for Word paste  
**Last updated:** 2026-07-30

---

## 4.1 Introduction

This chapter presents the overall approach adopted by Team Codexon for the Residual Compensation Modeling Framework for Dengue Risk Prediction. The proposed framework addresses key limitations of single-stage dengue prediction systems by combining three complementary analytical modules: hybrid time-series case forecasting, hybrid outbreak risk classification, and hybrid spatial hotspot detection. The modules are designed to provide related but distinct district-week views of dengue risk and are integrated into an early-warning decision-support dashboard for joint visualisation and interpretation.

Across the framework, each module follows a two-stage sequential design. In the first stage, a baseline model captures the dominant structure of the prediction task, such as temporal dependence in case counts, an initial outbreak probability, or a spatial risk surface. In the second stage, a compensation model learns and corrects systematic residual or calibration errors that remain after the baseline stage. The precise meaning of compensation differs by module: Module 1 corrects case-forecast residuals using lagged epidemiological and climate features; Module 2 recalibrates outbreak probabilities to improve risk-score reliability; and Module 3 adjusts spatial baseline risk using environmental and demographic context. By separating baseline pattern learning from error correction, the approach aims to improve the usefulness of dengue risk predictions relative to baseline-only models, while remaining interpretable as a residual compensation framework rather than a single black-box predictor.

The remainder of this chapter describes the conceptual design of the proposed framework and the role of each module before the detailed analysis, implementation, and evaluation chapters.

**Approx. word count:** 240 words

**Notes for Team:**
- Softened “overcome major weakness” / guaranteed accuracy claims.
- Softened “comprehensive early warning system for proactive public health decision making” → decision-support dashboard language.
- Important correction: Stage 2 does **not** use environmental/climate correction in the same way for every module; Module 2 Stage 2 is probability calibration.
- Official module names used.
- Ends with a short transition into the rest of Chapter 4.
