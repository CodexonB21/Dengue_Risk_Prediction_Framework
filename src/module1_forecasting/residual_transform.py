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
    weight: np.ndarray | float = 1.0,
) -> np.ndarray | float:
    """Assemble final case-count forecast from Stage 1 + Stage 2.

    `weight` scales Stage 2's correction before it is added back
    (`final = sarima + weight * predicted_residual`, or the analogous scaling
    in log space). Defaults to `1.0` (full-strength correction, unchanged
    production behavior). Introduced for the Phase 3 per-district shrinkage
    ablation (`shrinkage.py`) targeting districts where Stage 2 empirically
    hurts holdout MASE - `weight` may be a scalar or an array broadcastable
    against `sarima_pred`/`predicted_residual` (e.g. a per-row weight looked
    up by District).
    """
    validate_residual_mode(mode)
    sarima_arr = np.asarray(sarima_pred, dtype=float)
    pred_arr = np.asarray(predicted_residual, dtype=float)
    weight_arr = np.asarray(weight, dtype=float)
    if mode == "additive":
        return np.maximum(sarima_arr + weight_arr * pred_arr, 0.0)
    log_level = np.log1p(np.maximum(sarima_arr, 0.0)) + weight_arr * pred_arr
    return np.maximum(np.expm1(log_level), 0.0)
