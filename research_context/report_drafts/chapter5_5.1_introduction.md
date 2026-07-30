# Chapter 5 — Section 5.1 Introduction

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous chapter:** Chapter 4 — Our Approach  
**Next topic:** 5.2 High-Level System Architecture (+ Figure 5.1)

---

## 5.1 Introduction

This chapter presents the analysis and design of the Residual Compensation Modeling Framework for Dengue Risk Prediction. Whereas Chapter 4 introduced the conceptual approach and the meaning of residual compensation across the three modules, the present chapter focuses on structural design: how data move through the system, where shared and module-specific processing boundaries are drawn, how each module’s stages are organised, and how outputs are integrated for early-warning interpretation.

The design goal is not to replace epidemiological judgement with a single opaque predictor, but to organise forecasting, outbreak-risk classification, and spatial hotspot detection as complementary pipelines that correct systematic baseline errors in a controlled way. Traditional one-stage dengue models often absorb temporal structure, climate effects, and risk interpretation into a single step, which can make residual behaviour difficult to diagnose and can encourage leakage-prone preprocessing choices. The proposed design therefore separates baseline modelling from compensation, and separates module-agnostic data cleaning from modelling-specific transformations.

The remainder of the chapter proceeds from the high-level system architecture to data and pipeline design, then to the individual module architectures, and finally to integration and output design. Implementation details and numerical evaluation results are reserved for the subsequent chapters.

**Approx. word count:** 220 words

**Visuals for this section:** none required.

**Chapter boundary (for team reference only — do not paste into Word):**

| Chapter | Role |
|---|---|
| Chapter 4 | Conceptual what/why |
| **Chapter 5** | Structural design: layers, data flow, stage boundaries, leakage guards, feature groups |
| Chapter 6 | Implementation and exact feature dictionaries |
| Chapter 7 | Metrics and results |
