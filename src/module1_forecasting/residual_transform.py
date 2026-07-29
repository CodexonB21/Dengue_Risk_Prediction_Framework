"""Stage 2 residual target transforms (M1-006A log-scale ablation).

Additive (production baseline, Decision 010):
```text
target = actual - sarima_prediction
final  = sarima_prediction + predicted_residual
```

Log-scale / multiplicative (M1-006A):
```text
target = log1p(actual) - log1p(sarima_prediction)
final  = expm1(log1p(sarima_prediction) + predicted_r_log)
```
"""

from __future__ import annotations

import numpy as np

RESIDUAL_MODES = ("additive", "log")


def validate_residual_mode(mode: str) -> str:
    if mode not in RESIDUAL_MODES:
        raise ValueError(f"Unknown residual mode {mode!r}; expected one of {RESIDUAL_MODES}")
    return mode


def compute_stage2_target(
    actual: np.ndarray | float,
    sarima_pred: np.ndarray | float,
    mode: str = "additive",
) -> np.ndarray | float:
    """Training/scoring target for Stage 2 XGBoost."""
    validate_residual_mode(mode)
    actual_arr = np.asarray(actual, dtype=float)
    sarima_arr = np.asarray(sarima_pred, dtype=float)
    if mode == "additive":
        return actual_arr - sarima_arr
    return np.log1p(np.maximum(actual_arr, 0.0)) - np.log1p(np.maximum(sarima_arr, 0.0))


def combine_stage2_forecast(
    sarima_pred: np.ndarray | float,
    predicted_residual: np.ndarray | float,
    mode: str = "additive",
) -> np.ndarray | float:
    """Assemble final case-count forecast from Stage 1 + Stage 2."""
    validate_residual_mode(mode)
    sarima_arr = np.asarray(sarima_pred, dtype=float)
    pred_arr = np.asarray(predicted_residual, dtype=float)
    if mode == "additive":
        return np.maximum(sarima_arr + pred_arr, 0.0)
    log_level = np.log1p(np.maximum(sarima_arr, 0.0)) + pred_arr
    return np.maximum(np.expm1(log_level), 0.0)
