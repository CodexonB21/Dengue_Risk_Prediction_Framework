"""Module 1 Stage 1 evaluation metrics.

Implements RMSE, MAE, sMAPE, and MASE, all of which accept an optional
boolean `mask` (True = keep the row) so callers can exclude `is_imputed ==
True` rows from scoring, per Decision 011
(`research_context/RESEARCH_DECISIONS.md`): imputed weeks are used to fit
SARIMA (a complete, regularly-spaced series is the whole point of
imputation) but must never be scored against.

`mase` additionally accepts `train_mask` so the seasonal-naive scale
denominator (computed over the *training* window, not the evaluation
window) can apply the same `is_imputed` exclusion for consistency - the
scale is itself an evaluation-relevant quantity, not a fitting quantity.
"""

from __future__ import annotations

import numpy as np


def _apply_mask(*arrays: np.ndarray, mask: np.ndarray | None) -> list[np.ndarray]:
    """Coerce inputs to float ndarrays and apply a boolean keep-mask.

    Rows that are NaN in any of `arrays` are also dropped, since a missing
    prediction (e.g. a fold whose SARIMAX fit failed) must not silently
    count as a zero-error observation.
    """
    coerced = [np.asarray(a, dtype=float) for a in arrays]
    if mask is None:
        keep = np.ones_like(coerced[0], dtype=bool)
    else:
        keep = np.asarray(mask, dtype=bool)

    for arr in coerced:
        keep = keep & ~np.isnan(arr)

    return [arr[keep] for arr in coerced]


def rmse(y_true, y_pred, mask: np.ndarray | None = None) -> float:
    """Root Mean Squared Error, in raw case-count units."""
    yt, yp = _apply_mask(y_true, y_pred, mask=mask)
    if yt.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean((yt - yp) ** 2)))


def mae(y_true, y_pred, mask: np.ndarray | None = None) -> float:
    """Mean Absolute Error, in raw case-count units."""
    yt, yp = _apply_mask(y_true, y_pred, mask=mask)
    if yt.size == 0:
        return float("nan")
    return float(np.mean(np.abs(yt - yp)))


def smape(y_true, y_pred, mask: np.ndarray | None = None) -> float:
    """Symmetric Mean Absolute Percentage Error, as a percentage (0-200).

    Preferred over plain MAPE given this project's well-documented
    zero-inflation (DATA_DICTIONARY.md), where actual cases are frequently
    0 and MAPE's `|y_true|` denominator would blow up. sMAPE still has a
    0/0 case when both `y_true` and `y_pred` are exactly 0 (a perfectly
    correct "no cases" prediction) - that case contributes 0 error rather
    than NaN, since it is not an error at all.
    """
    yt, yp = _apply_mask(y_true, y_pred, mask=mask)
    if yt.size == 0:
        return float("nan")

    numerator = np.abs(yt - yp)
    denominator = np.abs(yt) + np.abs(yp)

    ratio = np.zeros_like(numerator)
    nonzero = denominator != 0
    ratio[nonzero] = numerator[nonzero] / denominator[nonzero]
    # denominator == 0 implies yt == yp == 0: a correct prediction, ratio stays 0.

    return float(np.mean(ratio) * 200.0)


def mase(
    y_true,
    y_pred,
    y_train,
    m: int = 52,
    mask: np.ndarray | None = None,
    train_mask: np.ndarray | None = None,
) -> float:
    """Mean Absolute Scaled Error (Hyndman & Koehler), seasonal-naive scale.

    Scale-free and, per `module_1_forecasting/MODULE_CONTEXT.md`'s existing
    ranking, the most robust of the four metrics under heavy zero-inflation
    (unlike sMAPE, it does not saturate at 0/200 when both sides are near
    zero). This is the primary metric used to select each district's SARIMA
    order/transform.

    The scale denominator is the mean absolute error of a seasonal-naive
    forecast (`y_train[t] - y_train[t-m]`) computed over the *training*
    window supplied via `y_train` - never the evaluation window, which
    would leak evaluation-period difficulty into the normalizer.

    `train_mask` lets callers exclude `is_imputed == True` training rows
    from the scale computation too (Decision 011 consistency): a row's
    naive-forecast error is only meaningful if both `y_train[t]` and
    `y_train[t-m]` are real, non-imputed observations.
    """
    yt, yp = _apply_mask(y_true, y_pred, mask=mask)
    if yt.size == 0:
        return float("nan")

    y_train = np.asarray(y_train, dtype=float)
    if y_train.size <= m:
        return float("nan")

    naive_errors = np.abs(y_train[m:] - y_train[:-m])
    if train_mask is not None:
        train_keep = np.asarray(train_mask, dtype=bool)
        # A naive error at position i (aligned to y_train[m:]) requires
        # BOTH y_train[i + m] and y_train[i] to be real observations.
        pair_keep = train_keep[m:] & train_keep[:-m]
        naive_errors = naive_errors[pair_keep]

    naive_errors = naive_errors[~np.isnan(naive_errors)]
    if naive_errors.size == 0:
        return float("nan")

    scale = np.mean(naive_errors)
    if scale == 0:
        return float("nan")

    return float(np.mean(np.abs(yt - yp)) / scale)


def compute_all_metrics(
    y_true,
    y_pred,
    y_train,
    m: int = 52,
    mask: np.ndarray | None = None,
    train_mask: np.ndarray | None = None,
) -> dict[str, float]:
    """Convenience wrapper computing all four metrics at once, plus simple
    observation counts (post-mask vs total), for logging/CSV output.
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    n_total = int(y_true_arr.size)
    if mask is None:
        n_scored = n_total
    else:
        keep = np.asarray(mask, dtype=bool) & ~np.isnan(y_true_arr) & ~np.isnan(
            np.asarray(y_pred, dtype=float)
        )
        n_scored = int(np.sum(keep))

    return {
        "rmse": rmse(y_true, y_pred, mask=mask),
        "mae": mae(y_true, y_pred, mask=mask),
        "smape": smape(y_true, y_pred, mask=mask),
        "mase": mase(y_true, y_pred, y_train, m=m, mask=mask, train_mask=train_mask),
        "n_obs_scored": n_scored,
        "n_obs_total": n_total,
    }
