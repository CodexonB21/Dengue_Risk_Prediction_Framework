# Research Decisions

This is a living decision log. Update it whenever the team accepts, rejects, or revises a research decision.

Each decision should include:

- Decision
- Reason
- Status
- Date
- Related module

---

## Decision 001: Keep Stage 1 of Module 1 Climate-Free

**Module:** Module 1 - Time-Series Forecasting  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Stage 1 uses SARIMA with weekly dengue case counts only. Climate variables are not included in Stage 1.

### Reason
The research objective is residual compensation. If climate variables are included in Stage 1, the baseline model may already absorb the climate signal, leaving weaker residuals for Stage 2.

### Implication
Climate variables should mainly enter Stage 2 as lagged climate, anomaly, and interaction features.

---

## Decision 002: Fit SARIMA Separately Per District

**Module:** Module 1 - Time-Series Forecasting  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Fit one SARIMA model per district instead of one pooled national model.

### Reason
Dengue behavior differs across districts. Pooling may hide or fabricate district-specific seasonality and residual behavior.

---

## Decision 003: Use Climate Anomalies for Residual Compensation

**Module:** Module 1 / Module 2  
**Status:** Accepted but may be refined  
**Date:** 2026-07-26

### Decision
Use climate anomaly variables such as rainfall anomaly, temperature anomaly, and humidity anomaly.

### Reason
Raw climate variables contain seasonal patterns that may overlap with seasonality already captured by baseline models. Anomalies are more aligned with residual correction because they represent unusual deviations from expected district-week conditions.

---

## Decision 004: Use Module-Specific Documentation

**Module:** All modules  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Each module should maintain its own `MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md`.

### Reason
The three team members work on separate modules. Module-specific documentation prevents one module's temporary changes from polluting another module's context.

---

## Decision 005: Let Cursor Maintain Living Documentation

**Module:** All modules  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Cursor should update documentation when major decisions, experiments, or architecture changes occur.

### Reason
The project is evolving. Static rules become outdated. The repository markdown files should act as project memory.

### Guardrail
Cursor should not silently overwrite major decisions. For major architecture changes, it should document the change in `CHANGELOG.md` and update the relevant module context.
