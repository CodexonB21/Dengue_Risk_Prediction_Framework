# Changelog

This file records important project changes.

Use it to track why the architecture, features, models, or decisions changed over time.

---

## Entry Format

```markdown
## YYYY-MM-DD - Short Change Title

### Module
Module name or All modules

### Change
What changed?

### Reason
Why was the change made?

### Impact
What files/code/models are affected?

### Status
Accepted / Rejected / Experimental / Superseded
```

---

## 2026-07-26 - Living Cursor Context System Added

### Module
All modules

### Change
Introduced living project documentation and Cursor rules so the agent can read and update project context as the research evolves.

### Reason
The project architecture, decisions, features, and approaches may change over time. Static rules can become outdated.

### Impact
Added/updated:

- `.cursor/rules/codexon_fyp.mdc`
- `research_context/PROJECT_CONTEXT.md`
- `research_context/CURRENT_ARCHITECTURE.md`
- `research_context/RESEARCH_DECISIONS.md`
- `research_context/CHANGELOG.md`
- module-specific context files

### Status
Accepted

---

## 2026-07-26 - Module 1 Data Realities Confirmed and New Decisions Proposed

### Module
Module 1 (with cross-module implication for Module 3 via population data)

### Change
User confirmed actual data characteristics for Module 1: full 2007–2026 weekly/daily coverage, Sri Lanka MoH epi-week standard (scraped), consistent district names, census population data (2001/2012/2024), single-point-per-district climate data (Open-Meteo constraint), and heavy zero-inflation in weekly case counts. Based on these facts, six new decisions were proposed (006–011): population used as a reporting-layer normalization only (not a Stage 1 target change), week-53 merged into week-52 for seasonal consistency, `weather_code` excluded from the feature set, walk-forward validation with a held-out final test block, a no-leakage rule for Stage 2 residual training, and a seasonal-naive imputation + flagging policy for missing weeks.

### Reason
Confirming real data characteristics resolved several previously open questions in `DATA_DICTIONARY.md` and `module_1_forecasting/MODULE_CONTEXT.md`, and surfaced new risks (zero-inflation, 53-week years, residual leakage) that needed explicit, documented handling before implementation begins.

### Impact
Updated:

- `research_context/DATA_DICTIONARY.md` (epi-week definition, spatial resolution caveat, population/census section, data quality notes)
- `research_context/RESEARCH_DECISIONS.md` (Decisions 006–011, all status Proposed pending final sign-off)
- `research_context/FEATURE_ENGINEERING_SPEC.md` (`weather_code` exclusion, week-53 merge note, feature change log)
- `module_1_forecasting/MODULE_CONTEXT.md` (resolved data questions, new zero-inflation open question, validation strategy, updated evaluation metrics)

### Status
Proposed (decisions 006–011 pending final user sign-off before implementation)

---

## 2026-07-26 - Raw Module 1 Data Audited and Cleaned

### Module
Module 1

### Change
Ran a full read-only audit (`scripts/data_audit_module1.py`, newly added) against the actual raw files placed in `data/raw/epidemiological/` and `data/raw/weather/`. Found and worked with the user through a joint iterative fix of five `(District, Year, Week)` collisions in the case data (2010 week 34/35 mislabeling, a 2012/2013 year-boundary mislabel, a 2014 week 2/3 double-track ambiguity, and a 2022/2023 year-boundary mislabel with a corrupted date). Also found and fixed two single-row district-name typos (`Moneragala`, `Puttlam`). Confirmed `Kalmunai` has a real 19-year case history but no matching weather station, and decided (Decision 012) to merge it into `Ampara`. Confirmed the `Humidity/` weather subfolder is fully redundant with `Weather (Except Humidity)/` (byte-identical humidity values) and should be dropped as a source. Corrected the earlier zero-inflation characterization: it is concentrated in 5 Northern/Eastern districts, not universal. Confirmed the earlier "encoding corruption" concern was a chat-display artifact, not a real file issue.

### Reason
The raw case data had genuine week-numbering integrity issues that would have silently corrupted any merge with climate data (row fan-out) and any SARIMA seasonal fitting (broken 7-day cadence) if left unresolved.

### Impact
- `data/raw/epidemiological/dengue_cases_corected.csv` — corrected in place by the user, verified by re-running the audit script until 0 duplicate rows remained.
- `research_context/DATA_DICTIONARY.md` — epi-week definition, climate source-folder guidance, and Data Quality Notes table updated with verified facts.
- `research_context/RESEARCH_DECISIONS.md` — added Decision 012 (Kalmunai → Ampara merge, Accepted); confirmed scope note added to Decision 011.
- `module_1_forecasting/MODULE_CONTEXT.md` — to be updated with final confirmed district list and data status.
- Added `scripts/data_audit_module1.py` as a reusable, read-only diagnostic — safe to re-run after any future edits to the raw case file.

### Status
Accepted (data-cleaning outcomes); Decision 012 Accepted; Decisions 006-011 remain Proposed pending pipeline implementation

---

## 2026-07-26 - Layered Pipeline Architecture Adopted; Detailed Build Plan Created

### Module
All modules

### Change
Corrected a design flaw: several transformations (week-53 merge, missing-week imputation, `weather_code` exclusion) had been implicitly treated as general-purpose data cleaning, when they actually exist to satisfy Module 1's SARIMA-specific assumptions. Adopted a layered pipeline (Decision 013): a shared, module-agnostic preprocessing stage (`data/processed/shared/`) feeding into separate module-specific preprocessing and feature-engineering stages (`data/processed/moduleN/`, `data/features/moduleN/`). Also corrected the missing-week count under Decision 011 using a more rigorous method (true label-gap detection instead of row-count comparison): the real picture is 4 weeks missing nationwide across all districts, plus a few district-specific gaps, totaling 104 rows (not the smaller, less accurate estimate previously recorded). Created a detailed technical build plan covering the shared layer and the full Module 1 pipeline, ready to implement.

### Reason
Applying Module-1-specific transformations at a shared layer would have silently discarded real data and imposed unproven feature-selection choices on Module 2 and Module 3 before their own designs are finalized.

### Impact
- Added `docs/PIPELINE_ARCHITECTURE_PLAN.md` (new, detailed technical build plan).
- `research_context/CURRENT_ARCHITECTURE.md` — added the layered pipeline diagram and guiding principle.
- `research_context/RESEARCH_DECISIONS.md` — added Decision 013; re-scoped Decisions 007, 008, 011 to Module 1 only; corrected Decision 011's confirmed missing-week count.
- `research_context/FEATURE_ENGINEERING_SPEC.md` — added fold-aware computation requirement for climate anomaly features.
- `module_1_forecasting/MODULE_CONTEXT.md` — added an Implementation Plan section.
- `module_2_classification/MODULE_CONTEXT.md`, `module_3_spatial/MODULE_CONTEXT.md` — added data pipeline consumption notes clarifying they do not inherit Module 1's modeling-specific choices.

### Status
Accepted

---

## 2026-07-26 - Module-Level Documentation Structure Added

### Module
All modules

### Change
Created separate module folders with their own `MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md` files.

### Reason
Three team members work on separate modules. Each module needs its own source of truth.

### Impact
Added:

- `module_1_forecasting/MODULE_CONTEXT.md`
- `module_1_forecasting/EXPERIMENT_LOG.md`
- `module_2_classification/MODULE_CONTEXT.md`
- `module_2_classification/EXPERIMENT_LOG.md`
- `module_3_spatial/MODULE_CONTEXT.md`
- `module_3_spatial/EXPERIMENT_LOG.md`

### Status
Accepted

---

## 2026-07-27 - Raw Weather Folder Flattened; Build Plan Relocated

### Module
All modules (Module 1 most directly affected)

### Change
The user moved the 25 canonical per-district weather CSVs out of the nested
`data/raw/weather/Weather (Except Humidity)/` subfolder directly into
`data/raw/weather/`, and deleted the now-redundant `data/raw/weather/Humidity/`
subfolder entirely (both subfolders no longer exist). Separately,
`PIPELINE_ARCHITECTURE_PLAN.md` was relocated from `docs/` to
`research_context/` (the `docs/` folder no longer exists). Updated all path
references accordingly: `DATA_DICTIONARY.md`, `module_1_forecasting/MODULE_CONTEXT.md`,
`PIPELINE_ARCHITECTURE_PLAN.md` itself (weather path), and `scripts/data_audit_module1.py`
(simplified to a single `WEATHER_DIR` with no Humidity-comparison logic); and all
`docs/PIPELINE_ARCHITECTURE_PLAN.md` cross-references in `CURRENT_ARCHITECTURE.md`,
`RESEARCH_DECISIONS.md`, `FEATURE_ENGINEERING_SPEC.md`, and all three
`MODULE_CONTEXT.md` files were repointed to `research_context/PIPELINE_ARCHITECTURE_PLAN.md`.

### Reason
Keep living documentation and scripts in sync with the actual raw-data folder
layout and file locations on disk, so pipeline code written against these paths
doesn't break.

### Impact
Weather ingestion in the upcoming `src/preprocessing/shared.py` should read
`data/raw/weather/*.csv` directly (no subfolder). All references to
`docs/PIPELINE_ARCHITECTURE_PLAN.md` should be read as
`research_context/PIPELINE_ARCHITECTURE_PLAN.md`.

### Status
Accepted
