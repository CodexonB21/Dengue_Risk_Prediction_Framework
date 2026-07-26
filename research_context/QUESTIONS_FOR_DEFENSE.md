# Questions for Defense

This file contains prepared explanations for supervisor, evaluator, and viva-style questions.

Update this file whenever a new important question is asked or a better explanation is developed.

---

## Why do we use two stages?

We use two stages to separate baseline pattern learning from error correction.

Stage 1 captures the expected structure using a baseline model. Stage 2 learns what the baseline missed by modeling the residual or error.

This makes the framework more interpretable than a black-box single-stage model.

---

## What happens to the compensation output?

The compensation model predicts the baseline model's error.

For Module 1:

```text
Final Forecast = SARIMA Forecast + Predicted Residual
```

The compensation stage does not replace the baseline. It corrects it.

---

## What if the residuals are random?

If residuals are random, compensation may not improve the result.

That is still a valid finding because it means the baseline model has already captured most learnable structure for that district or period.

This should be checked using residual diagnostics such as ACF plots, Ljung-Box tests, and performance comparison.

---

## Why are module-specific documents needed?

The project has three separate modules handled by different team members.

Module-specific documents prevent confusion and allow each module to evolve independently while still following the overall residual compensation framework.

---

## How do we avoid outdated Cursor rules?

The Cursor rule file should not contain detailed static research facts. Instead, it should instruct Cursor to read the latest markdown files and update them when decisions change.

The latest documentation should be treated as the source of truth, not the conversation history.
