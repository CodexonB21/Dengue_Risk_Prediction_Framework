# Project Context

## Project Title
A Residual Compensation Modeling Framework for Dengue Risk Prediction

## Team
Team Codexon

## Research Goal
Develop a residual compensation modeling framework that improves dengue risk prediction by correcting the systematic errors left by baseline models.

The framework contains three complementary modules:

1. **Module 1: Hybrid Time-Series Case Forecasting**
2. **Module 2: Hybrid Outbreak Risk Classification**
3. **Module 3: Hybrid Spatial Hotspot Detection**

Each module may evolve independently, but all modules follow the same research philosophy:

```text
Baseline model output + residual / error compensation = improved final output
```

---

## Living Documentation Rule

This repository uses living markdown documentation.

That means the files in `research_context/` and each module folder must be updated whenever:

- Architecture changes
- Modeling approach changes
- Feature engineering changes
- New experiments are completed
- A decision is accepted or rejected
- A supervisor/evaluator question is answered
- Implementation differs from documentation

The Cursor agent must not treat older documentation as permanently correct. It must read the latest files before giving project-specific advice.

---

## Core Research Hypothesis

Baseline dengue prediction models often leave residual errors that are not purely random. These residuals may contain useful information related to:

- Climate anomalies
- Monsoon-related nonlinear effects
- Environmental shifts
- District-specific epidemiological behavior
- Spatial and demographic context
- Intervention effects, if data becomes available

If these errors can be learned and corrected, the final prediction can become more accurate and more useful for public health decision-making.

---

## Current High-Level Architecture

Always check `CURRENT_ARCHITECTURE.md` for the latest accepted architecture.

At the current planning stage, the framework is expected to follow this structure:

```text
Module 1: SARIMA baseline -> XGBoost residual compensation
Module 2: Baseline classifier -> probability/error compensation model
Module 3: KDE/Moran's I baseline -> spatial residual adjustment model
```

This may change as experiments progress.

---

## Data Currently Available

### Weekly Dengue Case Dataset

Columns currently available:

- District
- Number_of_Cases
- Week_Start_Date
- Month
- Year
- Week
- Week_End_Date

### Daily Meteorological Dataset Per District

Columns currently available:

- time
- relative_humidity_2m_mean (%)
- relative_humidity_2m_max (%)
- relative_humidity_2m_min (%)
- temperature_2m_max (°C)
- temperature_2m_min (°C)
- apparent_temperature_mean (°C)
- apparent_temperature_max (°C)
- apparent_temperature_min (°C)
- temperature_2m_mean (°C)
- rain_sum (mm)
- precipitation_sum (mm)
- weather_code (wmo code)

---

## Repository Memory Principle

The repository documentation is the project memory.

Before answering research-specific questions, the agent should inspect:

1. `research_context/PROJECT_CONTEXT.md`
2. `research_context/CURRENT_ARCHITECTURE.md`
3. `research_context/RESEARCH_DECISIONS.md`
4. `research_context/CHANGELOG.md`
5. Relevant module-specific `MODULE_CONTEXT.md`
6. Relevant module-specific `EXPERIMENT_LOG.md`

---

## Documentation Update Principle

After any major task, the agent should check whether documentation needs to be updated.

Examples:

| Change | File to Update |
|---|---|
| Overall architecture changed | `CURRENT_ARCHITECTURE.md`, `CHANGELOG.md` |
| Module architecture changed | relevant `MODULE_CONTEXT.md`, `CHANGELOG.md` |
| Experiment completed | relevant `EXPERIMENT_LOG.md` |
| Feature added/removed | `FEATURE_ENGINEERING_SPEC.md`, module context |
| Research decision made | `RESEARCH_DECISIONS.md`, `CHANGELOG.md` |
| Defense answer improved | `QUESTIONS_FOR_DEFENSE.md` |
