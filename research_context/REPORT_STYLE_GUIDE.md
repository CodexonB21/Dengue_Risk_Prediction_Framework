# Team Codexon FYP Report Style Guide

## Purpose

This file defines the writing, formatting, terminology, structural, and length rules for the final report of:

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

# Paragraph vs Bullet Point Usage

This is one of the most important structural rules in this guide. A final year report is a piece of continuous academic writing, not a slide deck, README, or meeting summary. Reviewers and supervisors expect connected reasoning, not fragmented lists.

## Default: paragraph form

Use paragraphs for anything that requires explanation, justification, comparison, interpretation, or argument, including:

- background and motivation
- literature discussion and synthesis
- why a technology or tool was chosen
- how a module works conceptually
- design rationale and trade-offs
- how implementation decisions were made
- interpretation of evaluation results
- discussion of limitations and their implications
- conclusions and future work reasoning

Example of the wrong approach:

```text
Python was chosen because:
- It is easy to use
- It has many libraries
- It supports machine learning
- It is popular in research
```

Example of the right approach:

```text
Python was selected as the primary programming language for this project because it provided a mature ecosystem of libraries for statistical time-series modelling, machine learning, and geospatial analysis within a single environment. Its widespread adoption in dengue and epidemiological forecasting research also made it easier to align the implementation with established methods reported in the literature, while its readability supported collaborative development across the three project modules.
```

## When bullet points or numbered lists are acceptable

Use a bulleted or numbered list only when the content is a genuine enumeration, such as:

- a list of research objectives
- a list of module names
- a list of dataset columns or features
- a list of tools/libraries in a summary table
- an ordered sequence of processing steps where the order itself is meaningful (e.g., a pipeline: load data, clean data, engineer features, train model, evaluate)
- short evaluation metric names before they are discussed in prose

Every list must:

1. Be introduced by a full sentence that sets up what the list represents.
2. Be followed, where relevant, by a paragraph that explains, interprets, or elaborates on the listed items. A list should rarely be left to stand alone as the entire explanation.

## Quantity limits

- At most one list per section/subsection, unless the subsection is explicitly structured around multiple distinct enumerations (e.g., a subsection describing inputs, processes, and outputs separately).
- Do not use nested bullet lists more than one level deep in report body text.
- Avoid single-word or very short bullet fragments (e.g., "- Scalable", "- Fast", "- Accurate"). If a point is worth including, it is worth a full sentence.

## Target balance

As a working target, at least 70-80% of the words in the Literature Review, Approach, Analysis and Design, Implementation, and Evaluation chapters should be in paragraph form, with the remainder in tables, lists, and figure captions. The Introduction, Technologies, Conclusion, and Challenges chapters may have a similar or slightly higher paragraph share, since they are largely narrative and reflective in nature.

## Converting notes into report prose

Project notes, markdown logs, experiment logs, and chat-style bullet points are useful as source material, but must be rewritten into connected academic prose before being placed into the report. Do not copy bullet-style working notes directly into report chapters.

---

# Word Count and Section Length Guidance

Report content must be substantive. A subsection that is only one or two sentences long generally has not been developed to the depth expected of a final year report chapter, unless it is intentionally a short transitional note.

## Default targets

| Report Element | Target Length |
|---|---|
| Abstract | 250-400 words |
| Chapter Introduction section (e.g., X.1) | 120-250 words |
| Standard subsection | 250-500 words |
| Major analytical subsection (literature discussion, module design, evaluation discussion) | 400-800 words |
| Chapter Summary section | 100-200 words |
| Full chapter | 1,500-3,500 words, depending on chapter importance |

## Chapter-level guidance

- Literature Review, Analysis and Design, Implementation, and Evaluation are usually the longest chapters, since they require the most explanation, justification, and interpretation.
- Introduction, Technologies Adapted, Conclusion and Future Work, and Challenges and Limitations are typically shorter, but should still be fully developed rather than skeletal.
- Front matter (abstract, dedication, acknowledgement) has its own conventions and should not be padded artificially; the guideline in the department's formatting instructions should be followed for these.

## Rules for managing length

- Do not pad a section with repeated phrasing, restated points, or filler transitions purely to reach a word count. If there is genuinely not enough material yet (e.g., results are pending), keep the section honest and mark missing parts with a placeholder rather than inflating the word count.
- If the user requests a specific word count or page limit, that instruction overrides the defaults in this guide.
- If a quick or partial draft is requested, clearly label it as a shortened draft, and note that it can be expanded to meet full report-length expectations later.
- When a chapter or section is completed, note the approximate word count so progress can be tracked against overall report length expectations (check current department/supervisor expectations for the exact figure required for the full report body).

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
2. Main content sections, written primarily in paragraph form
3. Summary

The chapter introduction should briefly explain, in prose:

- what the previous chapter covered
- what this chapter covers
- why the chapter is important

The chapter summary should briefly explain, in prose:

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

Every figure/table must be mentioned in the body text, and every figure/table should be followed by a short paragraph interpreting its content rather than left to speak for itself.

Example:

```text
Figure 5.1 shows the high-level architecture of the proposed dengue risk prediction framework. As illustrated, epidemiological and climate data flow through a shared preprocessing layer before being routed to the three independent modules described in the following sections.
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

The literature review should not be a list of summaries only, and should not be a series of bullet points per paper.

For each group of related work, write connected paragraphs that explain:

1. What previous researchers did.
2. What methods they used.
3. What limitations remain.
4. How those limitations relate to this project.
5. How this project addresses or differs from them.

Use comparison tables to summarize multiple papers side by side, but always follow the table with a discussion paragraph rather than leaving the table to stand alone.

---

# Technology Chapter Style

Do not describe tools generically or as a bare list.

Bad:

```text
Python is a popular programming language used for many applications.
```

Bad (bullet list of reasons):

```text
Python was chosen because:
- Easy syntax
- Many libraries
- Popular
```

Better (paragraph form, tied to the project):

```text
Python was used as the primary programming language because the project required data preprocessing, statistical forecasting, machine learning model development, and visualization within a single flexible environment. Its extensive ecosystem, including libraries for time-series analysis, gradient-boosted classification, and geospatial visualization, allowed all three modules to be developed using a consistent toolset.
```

Each technology should be linked to the project through prose, not just named.

---

# Implementation Chapter Style

The implementation chapter should explain, mostly in paragraph form:

- dataset preparation
- preprocessing
- feature engineering
- model implementation
- training setup
- experiment workflow
- output generation

Short ordered lists are acceptable for describing a strict processing sequence (e.g., the exact preprocessing pipeline steps), but each step should still be explained rather than left as a bare label.

Avoid placing too many screenshots in the main body.

Use appendices for:

- long code snippets
- extended screenshots
- detailed logs
- full hyperparameter grids

---

# Evaluation Chapter Style

Evaluation must be evidence-based and written in prose, not as a bare list of numbers.

Do not say:

```text
The model performed well.
```

Do not present bare bullet metrics with no discussion:

```text
- RMSE: 4.2
- MAE: 3.1
```

Instead, write:

```text
The model achieved an RMSE of 4.2 and an MAE of 3.1 on the held-out test period, indicating that, on average, the forecast deviated from the actual weekly case count by approximately four cases. This represented an improvement over the SARIMA-only baseline, suggesting that the residual compensation step captured additional variation not accounted for by the statistical model alone.
```

If results are not finalized, use:

```text
[To be updated after final experiment results]
```

---

# Challenges and Limitations Style

Limitations should be honest, academic, and written as connected reasoning rather than a bare checklist.

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

Avoid making the project look weak. Explain limitations as realistic research boundaries, with brief reasoning about their cause and potential impact.

---

# Consistency Checklist

Before finalizing any chapter, check:

- Are module names consistent?
- Are equations consistent?
- Are dataset names consistent?
- Are figure/table captions numbered correctly?
- Are all figures/tables cited in text and followed by an interpreting paragraph?
- Are all claims supported?
- Are placeholders clearly marked?
- Does the chapter match current implementation?
- Does the writing avoid overclaiming?
- Does the section connect back to dengue risk prediction?
- Is the section mostly paragraph-form, with bullets used only where genuinely appropriate?
- Does the section fall within the expected word count range for its type?

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

The final report should read as one coherent document, not as separate pieces written by different team members, and not as a set of bullet-point notes.

Maintain:

- consistent terminology
- consistent formatting
- consistent module descriptions
- consistent tense
- consistent citation style
- consistent figure/table numbering
- consistent explanation depth
- a predominantly paragraph-based narrative style
- section lengths that meet the word count guidance above
