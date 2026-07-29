# Team Codexon FYP Report Style Guide

## Purpose

This file defines the writing, formatting, terminology, and consistency rules for the final report of:

**A Residual Compensation Modeling Framework for Dengue Risk Prediction**

The goal is to maintain a consistent academic writing style across all chapters and contributors.

---

# General Writing Style

Use a formal final-year research report style.

The writing should be:

- clear
- academic
- precise
- concise
- technically accurate
- evidence-based
- easy to understand

Avoid:

- casual wording
- overly emotional language
- exaggerated claims
- unsupported statements
- unnecessary repetition
- overly complex sentences

---

# Tone

Use an objective academic tone.

Preferred:

```text
This research proposes a hybrid framework for dengue risk prediction by combining time-series forecasting, outbreak risk classification, and spatial hotspot detection.
```

Avoid:

```text
Our system is extremely powerful and can accurately predict dengue outbreaks.
```

---

# Tense Usage

Use past tense for completed work:

```text
The dataset was preprocessed to handle missing values and inconsistent date formats.
```

Use present tense for system/framework descriptions:

```text
The proposed framework consists of three modules.
```

Use future tense only for planned future work:

```text
Future work will focus on integrating real-time weather data.
```

---

# Preferred Terminology

Use these terms consistently:

- proposed framework
- dengue risk prediction
- weekly dengue case forecasting
- outbreak risk classification
- spatial hotspot detection
- residual compensation
- SARIMA baseline
- machine learning residual model
- predicted residual
- final forecast
- epidemiological data
- climate/weather features
- lag features
- temporal features
- spatial features
- district-level analysis
- risk score
- hotspot map
- decision-support system

---

# Terms to Avoid or Use Carefully

Avoid saying:

- guaranteed prediction
- perfect accuracy
- clinical diagnosis
- real-time deployment, unless implemented
- public health certified system
- fully automated disease control
- best model, unless supported by comparison
- highly accurate, unless supported by metrics

Use safer alternatives:

| Risky Wording | Better Academic Wording |
|---|---|
| The system predicts outbreaks accurately | The system supports outbreak risk prediction based on available data |
| The model gives correct dengue forecasts | The model produces dengue case forecasts that are evaluated using forecasting metrics |
| This is the best approach | This approach was selected based on its suitability for the project scope |
| The system can be used by health authorities | The system can support future public health decision-making after further validation |
| The model proves dengue outbreaks | The model identifies patterns associated with increased dengue risk |

---

# Module Naming Rules

Use these full names when introducing modules:

## Module 1

**Hybrid Time-Series Case Forecasting Module**

After introduction, acceptable shortened forms:

- forecasting module
- Module 1

## Module 2

**Hybrid Outbreak Risk Classification Module**

After introduction, acceptable shortened forms:

- classification module
- outbreak classification module
- Module 2

## Module 3

**Hybrid Spatial Hotspot Detection Module**

After introduction, acceptable shortened forms:

- spatial module
- hotspot detection module
- Module 3

---

# Project Description Template

Use this wording as a base when introducing the project:

```text
This research proposes a residual compensation-based dengue risk prediction framework that integrates weekly case forecasting, outbreak risk classification, and spatial hotspot detection. The framework is designed to support early warning and analytical decision-making by combining epidemiological data, weather-related features, temporal patterns, and spatial indicators.
```

Modify only if the architecture changes.

---

# Residual Compensation Explanation Template

Use this explanation when describing the core idea:

```text
The forecasting module uses a statistical time-series model as the baseline forecasting component. The residual error is calculated as the difference between the actual dengue case count and the baseline prediction. A machine learning model is then trained to learn patterns in these residuals using additional explanatory features. The final prediction is obtained by adding the predicted residual to the baseline forecast.
```

Use equations when appropriate:

```text
residual = actual_cases - baseline_prediction
final_prediction = baseline_prediction + predicted_residual
```

Where the baseline model is SARIMA unless the latest documentation states otherwise.

---

# Chapter Writing Rules

Each chapter should normally contain:

1. Introduction
2. Main content sections
3. Summary

The chapter introduction should briefly explain:

- what the previous chapter covered
- what this chapter covers
- why the chapter is important

The chapter summary should briefly explain:

- the key points covered in the chapter
- how the chapter connects to the next chapter

---

# Figure and Table Style

Use this format for figure captions:

```text
Figure X.X: Description of the figure
```

Example:

```text
Figure 5.1: High-level architecture of the proposed dengue risk prediction framework
```

Use this format for table captions:

```text
Table X.X: Description of the table
```

Example:

```text
Table 2.1: Comparison of existing dengue forecasting approaches
```

Every figure/table must be mentioned in the body text.

Example:

```text
Figure 5.1 shows the high-level architecture of the proposed dengue risk prediction framework.
```

---

# Citation Style

Use numbered citations in square brackets unless supervisor instructions say otherwise.

Example:

```text
Dengue transmission is influenced by rainfall, temperature, humidity, and mosquito breeding conditions [1].
```

Do not add fake citations.

Use `[Citation required]` if a citation is needed but not yet available.

---

# Literature Review Style

The literature review should not be a list of summaries only.

For each group of related work, explain:

1. What previous researchers did
2. What methods they used
3. What limitations remain
4. How those limitations relate to this project
5. How this project addresses or differs from them

Use comparison tables where helpful.

---

# Technology Chapter Style

Do not describe tools generically.

Bad:

```text
Python is a popular programming language used for many applications.
```

Better:

```text
Python was used as the primary programming language because the project required data preprocessing, statistical forecasting, machine learning model development, and visualization within a single flexible environment.
```

Each technology should be linked to the project.

---

# Implementation Chapter Style

The implementation chapter should explain:

- dataset preparation
- preprocessing
- feature engineering
- model implementation
- training setup
- experiment workflow
- output generation

Avoid placing too many screenshots in the main body.

Use appendices for:

- long code snippets
- extended screenshots
- detailed logs
- full hyperparameter grids

---

# Evaluation Chapter Style

Evaluation must be evidence-based.

Do not say:

```text
The model performed well.
```

Say:

```text
The model achieved an RMSE of [value] and MAE of [value], indicating the average forecasting error across the test period.
```

If results are not finalized, use:

```text
[To be updated after final experiment results]
```

---

# Challenges and Limitations Style

Limitations should be honest and academic.

Possible limitation areas:

- dataset completeness
- temporal generalization
- spatial resolution
- weather data alignment
- underreporting of dengue cases
- outbreak threshold definition
- model interpretability
- evaluation constraints
- deployment limitations

Avoid making the project look weak. Explain limitations as realistic research boundaries.

---

# Consistency Checklist

Before finalizing any chapter, check:

- Are module names consistent?
- Are equations consistent?
- Are dataset names consistent?
- Are figure/table captions numbered correctly?
- Are all figures/tables cited in text?
- Are all claims supported?
- Are placeholders clearly marked?
- Does the chapter match current implementation?
- Does the writing avoid overclaiming?
- Does the section connect back to dengue risk prediction?

---

# Common Placeholders

Use these placeholders when needed:

```text
[Citation required]
```

```text
[To be updated after final experiment results]
```

```text
[Confirm with supervisor]
```

```text
[Insert Figure X.X here]
```

```text
[Insert Table X.X here]
```

```text
[Dataset details to be confirmed]
```

---

# Final Report Quality Target

The final report should read as one coherent document, not as separate pieces written by different team members.

Maintain:

- consistent terminology
- consistent formatting
- consistent module descriptions
- consistent tense
- consistent citation style
- consistent figure/table numbering
- consistent explanation depth
