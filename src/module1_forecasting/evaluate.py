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

`dm_test` and `ljung_box_diagnostics` were added for Module 1 Stage 2
(`compensation_model.py`/`combine.py`) - both are generic (no Stage-1- or
Stage-2-specific assumptions) so they're reusable wherever two forecasts or
a residual series need comparing/diagnosing.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm
from statsmodels.stats.diagnostic import acorr_ljungbox


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


def dm_test(
    e1,
    e2,
    max_lag: int = 12,
    loss: str = "squared",
) -> dict[str, float]:
    """Diebold-Mariano test for equal predictive accuracy between two
    aligned forecast-error series `e1` (e.g. Stage-1-only) and `e2` (e.g.
    Stage-1+Stage-2 combined), added for Module 1 Stage 2's evaluation
    framework (`combine.py`).

    Tests H0: E[g(e1) - g(e2)] = 0 (equal expected loss) against a two-sided
    alternative, where `g` is the squared-error or absolute-error loss.
    `mean_loss_diff` is `mean(g(e1) - g(e2))`, so `mean_loss_diff > 0` (and a
    small p-value) means `e2` has LOWER average loss than `e1` - i.e. Stage 2
    helped. (Corrected 2026-07-27: an earlier version of this docstring had
    the sign backwards - verified against the actual `d = g1 - g2` computation
    below and cross-checked empirically against `combine.py`'s known-improved
    districts, e.g. `Colombo`/`Kandy`, which all correctly show `mean_loss_diff
    > 0` at significant p-values.)

    The long-run variance of the loss differential is estimated with a
    Newey-West/Bartlett-kernel HAC estimator using `max_lag` lags, then a
    Harvey-Leybourne-Newbold (1997) small-sample correction is applied to
    the resulting statistic. `max_lag` defaults to 12 (roughly a quarter's
    worth of weekly observations) rather than the classic DM `h-1` rule
    (which assumes literal h-step-ahead iterated forecasts) - this project's
    per-row forecasts are not iterated, but Stage 1's Ljung-Box diagnostics
    (`module_1_forecasting/EXPERIMENT_LOG.md` M1-001) show real residual
    autocorrelation at longer lags, so a purely lag-0 variance estimate
    would understate the loss differential's true variance and inflate
    apparent significance. This is a practical, documented choice, not a
    rigorously optimal bandwidth.

    Returns a dict with `dm_stat`, `p_value`, `mean_loss_diff`, `n_obs`. NaN
    fields (with `n_obs` reflecting the usable sample size) are returned if
    fewer than 10 paired, non-NaN observations remain after masking.
    """
    e1 = np.asarray(e1, dtype=float)
    e2 = np.asarray(e2, dtype=float)
    keep = ~np.isnan(e1) & ~np.isnan(e2)
    e1, e2 = e1[keep], e2[keep]
    n = e1.size

    if n < 10:
        return {"dm_stat": float("nan"), "p_value": float("nan"), "mean_loss_diff": float("nan"), "n_obs": int(n)}

    if loss == "squared":
        g1, g2 = e1**2, e2**2
    elif loss == "absolute":
        g1, g2 = np.abs(e1), np.abs(e2)
    else:
        raise ValueError(f"Unknown loss '{loss}' - expected 'squared' or 'absolute'.")

    d = g1 - g2
    d_bar = float(np.mean(d))

    effective_max_lag = min(max_lag, n - 1)
    gamma0 = float(np.var(d, ddof=0))
    long_run_var = gamma0
    for lag in range(1, effective_max_lag + 1):
        gamma_lag = float(np.mean((d[lag:] - d_bar) * (d[:-lag] - d_bar)))
        long_run_var += 2 * gamma_lag
    long_run_var = max(long_run_var, 1e-12)  # guard against a nonpositive HAC estimate

    dm_stat = d_bar / np.sqrt(long_run_var / n)

    # Small-sample correction (Harvey, Leybourne & Newbold 1997), using the
    # HAC truncation lag in place of the classic h-step-ahead horizon.
    h = effective_max_lag + 1
    correction = np.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 0.0))
    dm_stat_corrected = float(dm_stat * correction)

    p_value = float(2 * (1 - norm.cdf(abs(dm_stat_corrected))))

    return {
        "dm_stat": dm_stat_corrected,
        "p_value": p_value,
        "mean_loss_diff": d_bar,
        "n_obs": int(n),
    }


def ljung_box_diagnostics(residuals, lags: tuple[int, ...] = (26, 52)) -> dict[str, float]:
    """Ljung-Box test for residual autocorrelation at the given lags. Generic
    version of `baseline_sarima.py`'s `run_ljung_box_diagnostics` (left
    untouched there to avoid touching already-validated Stage 1 code),
    reused by Stage 2 (`combine.py`) to sanity-check the FINAL combined
    residuals (`actual - final_prediction`) - i.e. confirm Stage 2 actually
    removed structure rather than just moving it.

    NaNs are dropped internally (unlike the Stage-1-specific version, which
    assumed pre-filtered input) so callers can pass a raw residual series
    directly.
    """
    residuals = np.asarray(residuals, dtype=float)
    residuals = residuals[~np.isnan(residuals)]

    usable_lags = [lag for lag in lags if residuals.size > lag]
    out: dict[str, float] = {}
    if not usable_lags:
        for lag in lags:
            out[f"ljung_box_stat_lag{lag}"] = float("nan")
            out[f"ljung_box_pvalue_lag{lag}"] = float("nan")
        return out

    result = acorr_ljungbox(residuals, lags=usable_lags, return_df=True)
    for lag in lags:
        if lag in result.index:
            out[f"ljung_box_stat_lag{lag}"] = float(result.loc[lag, "lb_stat"])
            out[f"ljung_box_pvalue_lag{lag}"] = float(result.loc[lag, "lb_pvalue"])
        else:
            out[f"ljung_box_stat_lag{lag}"] = float("nan")
            out[f"ljung_box_pvalue_lag{lag}"] = float("nan")
    return out
