"""Module 1 Stage 1 - SARIMA baseline.

Implements Decision 002 (one SARIMA per district, `research_context/
RESEARCH_DECISIONS.md`), and validates Decisions 009/010 (walk-forward
validation with a held-out final block; every fold's residuals must come
from a genuinely out-of-sample refit) by reusing
`src/module1_forecasting/validation.py` unchanged.

Five design decisions were explicitly reviewed and approved by the user
before this file was written (see `module_1_forecasting/MODULE_CONTEXT.md`
"Stage 1 Implementation Notes" for the permanent record):

1. **Order search scope**: `pmdarima.auto_arima` is run ONCE per district
   per transform (raw counts, `log1p` counts) on the full pre-holdout
   history, not per walk-forward fold (already benchmarked at ~25-59s/call
   even with a constrained stepwise search - refitting per fold across 25
   districts x 14 folds x 2 transforms would be infeasible). This is an
   accepted, documented compromise: the fixed (order, seasonal_order) used
   for an early fold is technically informed by data the model wouldn't
   have seen yet at that fold's forecast origin. Decision 010 itself is
   NOT violated by this - every fold's actual *fitted parameters* and
   *residuals* still come from `SARIMAX.fit()` on that fold's own training
   window only, via `fit_and_forecast()` below.
2. **Non-negative forecasts**: case counts cannot be negative. Both
   candidates' forecasts are clipped to a 0 floor after inverse-transforming
   back to raw-count scale - not just the raw-count candidate. (`log1p`
   forecasts are usually already non-negative after `expm1`, but a SARIMA
   forecast can technically dip below `log1p(0) == 0` in transformed space,
   which `expm1` would turn negative - clipping both candidates uniformly
   closes this edge case rather than leaving it to chance.)
3. **SARIMAX robustness**: `enforce_stationarity=False,
   enforce_invertibility=False` on every fit, to avoid convergence failures
   across 25 districts x 14 folds x 2 candidates. Any fold/candidate whose
   fit still fails is caught, logged with full context, and recorded as
   `NaN` predictions rather than crashing the whole run.
4. **Selection metric**: MASE (seasonal-naive scale, m=52) is the single
   metric that decides (a) raw vs `log1p` per district and (b) the
   "winning" config recorded in `sarima_selected_configs.csv`. RMSE, MAE,
   and sMAPE are still computed and stored for every fold for transparency.
5. **Holdout**: the final 104-week block per district gets both a forecast
   AND computed metrics in this same run (fit once on all pre-holdout data
   using the winning config). These holdout numbers are written with
   `split="holdout"` and are a one-time report only - they must never be
   used to go back and revise a district's chosen order/transform, which
   would violate Decision 009's "untouched until final reporting" rule.

Genuine out-of-sample validation-fold residuals (`split="validation"`) are
exactly what Stage 2 (`compensation_model.py`) trains on per Decision 010 -
this script is the one and only place they are produced.

### Post-hoc fix: explosive/non-stationary AR root guard (2026-07-27)

Discovered while building and debugging Stage 2 (Open Question #14,
`module_1_forecasting/MODULE_CONTEXT.md`): `enforce_stationarity=False`
(decision 3 above) lets `SARIMAX.fit()` land on a non-stationary AR
polynomial (root(s) on or inside the unit circle) when a fold's training
window is short/choppy relative to the fixed order chosen from the full
pre-holdout history. Concretely, `Vavuniya`'s fold 1 (2010) fit an AR(1)
coefficient of 1.266 (>1, explosive), producing a forecast that grew
geometrically to ~30 million cases/week by the end of that fold's 52-week
horizon against an actual mean of ~6/week - silently, since a squared-error-
based fit doesn't flag this as a "failure". The same pathology was
independently confirmed for `Mannar`'s 2022 fold (seasonal AR coefficient
1.162, `(0,0,0)x(1,0,0,52)`) - a general failure mode of this design, not a
one-off. `_has_explosive_ar_root()` below checks the fitted model's combined
AR polynomial roots after every fit; if any root fails to lie strictly
outside the unit circle, the fit is treated exactly like any other failure
mode already handled by decision 3 (logged, recorded as `NaN` for that fold)
rather than silently returning an unbounded-growth forecast. This is a
narrow, targeted fix - it does not change order selection, transform
selection, or any other part of Stage 1's design.
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pmdarima as pm
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE1_FIGURES_DIR,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_SARIMA_METRICS_PATH,
    MODULE1_SARIMA_PREDICTIONS_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
)
from src.module1_forecasting.evaluate import compute_all_metrics  # noqa: E402
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_MIN_TRAIN_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    fit_window,
    generate_walk_forward_folds,
    get_district_series,
    get_holdout_series,
)

logger = logging.getLogger(__name__)

VALUE_COL = "Number_of_Cases"
IMPUTED_COL = "is_imputed"

WEEKS_PER_YEAR = DEFAULT_WEEKS_PER_YEAR
HOLDOUT_YEARS = DEFAULT_HOLDOUT_YEARS
MIN_TRAIN_YEARS = DEFAULT_MIN_TRAIN_YEARS

# Constrained stepwise search - already benchmarked at ~25-59s/call with
# these bounds (see module docstring, decision 1).
AUTO_ARIMA_KWARGS = dict(
    seasonal=True,
    m=WEEKS_PER_YEAR,
    stepwise=True,
    max_p=2,
    max_q=2,
    max_P=1,
    max_Q=1,
    information_criterion="aic",
    suppress_warnings=True,
    error_action="ignore",
)

# Used only if auto_arima fails outright for a district/transform.
FALLBACK_ORDER = (1, 1, 1)
FALLBACK_SEASONAL_ORDER = (0, 1, 1, WEEKS_PER_YEAR)

# A stationary AR polynomial's roots must lie strictly outside the unit
# circle; a small tolerance avoids flagging a root landing at ~1.0000001 due
# to floating-point noise as "stable" when it is really borderline-explosive.
AR_ROOT_STABILITY_TOLERANCE = 1.0 + 1e-6

# ACF plots are diagnostic spot-checks, not a full 25-district report -
# one high-volume (Colombo), one moderate (Kandy), two sparse/zero-inflated
# (Mullaitivu, Kilinochchi) per the task brief.
ACF_DIAGNOSTIC_DISTRICTS = ("Colombo", "Kandy", "Mullaitivu", "Kilinochchi")
LJUNG_BOX_LAGS = (26, 52)


# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------

def get_district_imputed_flags(df: pd.DataFrame, district: str) -> pd.Series:
    """Return the `is_imputed` flag series for one district, indexed
    identically to `get_district_series` (same sort, same source rows) so
    the two series can always be aligned via `.loc[same_index]`.
    """
    district_df = df[df["District"] == district].sort_values(["Year", "Week"])
    index = pd.MultiIndex.from_frame(district_df[["Year", "Week"]], names=["Year", "Week"])
    return pd.Series(district_df[IMPUTED_COL].to_numpy(), index=index, name=IMPUTED_COL)


# ---------------------------------------------------------------------------
# Order selection (one-time per district per transform)
# ---------------------------------------------------------------------------

def select_order(
    series: pd.Series, use_log1p: bool
) -> tuple[tuple[int, int, int], tuple[int, int, int, int], bool]:
    """Run `auto_arima` once on `series` (the full pre-holdout history for
    one district) and return `(order, seasonal_order, fallback_used)`.

    See module docstring, decision 1, for why this deliberately uses all
    pre-holdout history rather than a single fold's training window.
    """
    values = series.to_numpy(dtype=float)
    if use_log1p:
        values = np.log1p(values)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = pm.auto_arima(values, **AUTO_ARIMA_KWARGS)
        return model.order, model.seasonal_order, False
    except Exception:
        logger.warning(
            "auto_arima failed entirely (use_log1p=%s); falling back to "
            "order=%s seasonal_order=%s.",
            use_log1p,
            FALLBACK_ORDER,
            FALLBACK_SEASONAL_ORDER,
            exc_info=True,
        )
        return FALLBACK_ORDER, FALLBACK_SEASONAL_ORDER, True


# ---------------------------------------------------------------------------
# Cheap per-fold refit + forecast (fast: fixed order, statsmodels SARIMAX)
# ---------------------------------------------------------------------------

def _has_explosive_ar_root(fitted) -> bool:
    """Return True if the fitted (S)ARIMAX model's combined AR polynomial
    (regular and seasonal roots together - `SARIMAXResults.arroots` already
    combines both) has any root on or inside the unit circle, i.e. the
    optimizer (permitted by `enforce_stationarity=False`) landed on a
    non-stationary/explosive fit. Such a fit's forecast either grows
    geometrically without bound (regular AR instability) or oscillates with
    a growing envelope every `seasonal_order[3]` weeks (seasonal AR
    instability) - never a valid model for a bounded weekly case-count
    series. See the module docstring "Post-hoc fix" note for the concrete
    `Vavuniya`/`Mannar` cases that motivated this check.
    """
    roots = np.asarray(fitted.arroots)
    if roots.size == 0:
        return False
    return bool(np.any(np.abs(roots) <= AR_ROOT_STABILITY_TOLERANCE))


def fit_and_forecast(
    train_series: pd.Series,
    n_periods: int,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    use_log1p: bool,
    context: str = "",
    *,
    start_params: np.ndarray | None = None,
    return_params: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray | None]:
    """Fit a fixed-order SARIMAX on `train_series` and forecast `n_periods`
    steps ahead, returning predictions back on the RAW case-count scale.

    Never raises: any fit/forecast failure is logged with `context` and
    returns an all-`NaN` array so the caller can continue with other
    folds/districts rather than aborting the whole run (decision 3).

    `start_params`/`return_params` (added for the M1-013 warm-start ablation,
    `rolling_one_step.py`'s `warm_start` option) are optional and additive:
    with both left at their defaults, behavior and return type are byte-
    identical to before this change. `start_params`, if given, is passed to
    `SARIMAX.fit()` as the optimizer's starting point instead of its own
    default initialization - valid because `order`/`seasonal_order` (and
    therefore the parameter vector's length) are fixed for the life of a
    walk-forward/rolling loop; only `train_series` grows. `return_params=True`
    changes the return value to `(forecast, fitted_params_or_None)` so a
    caller can chain one fit's converged parameters into the next fit's
    `start_params` - `fitted_params` is `None` on any failure path (the
    caller should then cold-start the next fit rather than propagate a stale
    or nonexistent vector).
    """
    values = train_series.to_numpy(dtype=float)
    fit_values = np.log1p(values) if use_log1p else values

    def _done(forecast_array: np.ndarray, params: np.ndarray | None):
        return (forecast_array, params) if return_params else forecast_array

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = SARIMAX(
                fit_values,
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fitted = model.fit(disp=False, start_params=start_params)
            if _has_explosive_ar_root(fitted):
                logger.warning(
                    "SARIMAX fit for %s (order=%s, seasonal_order=%s, "
                    "use_log1p=%s) is non-stationary/explosive (an AR root "
                    "landed on or inside the unit circle) despite "
                    "enforce_stationarity=False having allowed it; treating "
                    "as a failed fit and returning NaNs for this fold "
                    "rather than an unbounded-growth forecast.",
                    context,
                    order,
                    seasonal_order,
                    use_log1p,
                )
                return _done(np.full(n_periods, np.nan), None)
            forecast = fitted.forecast(steps=n_periods)
            fitted_params = np.asarray(fitted.params, dtype=float)
    except Exception:
        logger.warning(
            "SARIMAX fit/forecast failed for %s (order=%s, seasonal_order=%s, "
            "use_log1p=%s); returning NaNs for this fold.",
            context,
            order,
            seasonal_order,
            use_log1p,
            exc_info=True,
        )
        return _done(np.full(n_periods, np.nan), None)

    forecast = np.asarray(forecast, dtype=float)
    if use_log1p:
        forecast = np.expm1(forecast)
    # Case counts cannot be negative for either candidate (decision 2) -
    # log1p forecasts are usually already non-negative after expm1, but a
    # transformed-space forecast can dip below log1p(0) == 0, so this floor
    # is applied unconditionally rather than only for the raw candidate.
    forecast = np.clip(forecast, a_min=0.0, a_max=None)
    return _done(forecast, fitted_params)


# ---------------------------------------------------------------------------
# Walk-forward validation of one (district, transform) candidate
# ---------------------------------------------------------------------------

def validate_candidate(
    series: pd.Series,
    imputed: pd.Series,
    district: str,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    use_log1p: bool,
) -> dict:
    """Walk every fold from `generate_walk_forward_folds` (validation.py,
    unchanged) for one candidate, refitting the fixed order/seasonal_order
    on each fold's own training window (Decision 010) and scoring against
    that fold's actual values with `is_imputed` rows masked out
    (Decision 011).

    Returns a dict with the candidate's `order`/`seasonal_order`, per-row
    `fold_records` (for the predictions CSV), per-fold `fold_metrics` (for
    the metrics CSV), and `aggregate_mase` (median MASE across folds - the
    single number decision 4 uses to pick raw vs log1p).
    """
    fold_records: list[dict] = []
    fold_metrics: list[dict] = []
    fold_mase_values: list[float] = []

    for fold_id, (train_index, val_index) in enumerate(
        generate_walk_forward_folds(
            series,
            holdout_years=HOLDOUT_YEARS,
            min_train_years=MIN_TRAIN_YEARS,
            weeks_per_year=WEEKS_PER_YEAR,
        ),
        start=1,
    ):
        train_series = fit_window(series, train_index[-1])
        actual = series.loc[val_index]
        imputed_val = imputed.loc[val_index]
        imputed_train = imputed.loc[train_series.index]

        predictions = fit_and_forecast(
            train_series,
            n_periods=len(val_index),
            order=order,
            seasonal_order=seasonal_order,
            use_log1p=use_log1p,
            context=f"{district} fold {fold_id} ({'log1p' if use_log1p else 'raw'})",
        )

        for (year, week), y_true, y_pred, is_imp in zip(
            val_index, actual.to_numpy(), predictions, imputed_val.to_numpy()
        ):
            residual = float(y_true - y_pred) if not np.isnan(y_pred) else float("nan")
            fold_records.append(
                {
                    "District": district,
                    "Year": int(year),
                    "Week": int(week),
                    "split": "validation",
                    "fold_id": fold_id,
                    "Number_of_Cases": float(y_true),
                    "is_imputed": bool(is_imp),
                    "sarima_prediction": float(y_pred) if not np.isnan(y_pred) else float("nan"),
                    "residual": residual,
                }
            )

        metrics = compute_all_metrics(
            y_true=actual.to_numpy(),
            y_pred=predictions,
            y_train=train_series.to_numpy(),
            m=WEEKS_PER_YEAR,
            mask=~imputed_val.to_numpy(),
            train_mask=~imputed_train.to_numpy(),
        )
        fold_metrics.append(
            {"District": district, "split": "validation", "fold_id": fold_id, **metrics}
        )
        if not np.isnan(metrics["mase"]):
            fold_mase_values.append(metrics["mase"])

    aggregate_mase = float(np.median(fold_mase_values)) if fold_mase_values else float("nan")

    return {
        "order": order,
        "seasonal_order": seasonal_order,
        "fold_records": fold_records,
        "fold_metrics": fold_metrics,
        "aggregate_mase": aggregate_mase,
    }


def select_winning_candidate(raw_mase: float, log1p_mase: float) -> str:
    """Pick 'raw' or 'log1p' by lower aggregate MASE (decision 4). Ties -
    including the degenerate case where both candidates failed entirely -
    are broken toward 'raw' for interpretability."""
    if np.isnan(raw_mase) and np.isnan(log1p_mase):
        return "raw"
    if np.isnan(raw_mase):
        return "log1p"
    if np.isnan(log1p_mase):
        return "raw"
    return "log1p" if log1p_mase < raw_mase else "raw"


# ---------------------------------------------------------------------------
# Final holdout forecast (Decision 009) - one-time, non-tuning report
# ---------------------------------------------------------------------------

def forecast_holdout(
    series: pd.Series,
    imputed: pd.Series,
    district: str,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    use_log1p: bool,
) -> dict:
    """Fit once on all pre-holdout data using the winning config and
    forecast the full held-out block (decision 5). These are one-time
    numbers for final reporting only - never used to revise the selected
    order/transform (that would defeat the purpose of a held-out block).
    """
    holdout = get_holdout_series(series, holdout_years=HOLDOUT_YEARS, weeks_per_year=WEEKS_PER_YEAR)
    pre_holdout = series.iloc[: len(series) - len(holdout)]
    imputed_holdout = imputed.loc[holdout.index]
    imputed_pre_holdout = imputed.loc[pre_holdout.index]

    predictions = fit_and_forecast(
        pre_holdout,
        n_periods=len(holdout),
        order=order,
        seasonal_order=seasonal_order,
        use_log1p=use_log1p,
        context=f"{district} holdout ({'log1p' if use_log1p else 'raw'})",
    )

    fold_records = []
    for (year, week), y_true, y_pred, is_imp in zip(
        holdout.index, holdout.to_numpy(), predictions, imputed_holdout.to_numpy()
    ):
        residual = float(y_true - y_pred) if not np.isnan(y_pred) else float("nan")
        fold_records.append(
            {
                "District": district,
                "Year": int(year),
                "Week": int(week),
                "split": "holdout",
                "fold_id": "holdout",
                "Number_of_Cases": float(y_true),
                "is_imputed": bool(is_imp),
                "sarima_prediction": float(y_pred) if not np.isnan(y_pred) else float("nan"),
                "residual": residual,
            }
        )

    metrics = compute_all_metrics(
        y_true=holdout.to_numpy(),
        y_pred=predictions,
        y_train=pre_holdout.to_numpy(),
        m=WEEKS_PER_YEAR,
        mask=~imputed_holdout.to_numpy(),
        train_mask=~imputed_pre_holdout.to_numpy(),
    )
    metric_row = {"District": district, "split": "holdout", "fold_id": "holdout", **metrics}

    return {"fold_records": fold_records, "metric_row": metric_row}


# ---------------------------------------------------------------------------
# Residual diagnostics (Ljung-Box + ACF) - evidence for Open Question #3
# ---------------------------------------------------------------------------

def pooled_validation_residuals(fold_records: list[dict]) -> np.ndarray:
    """Concatenate one district's out-of-sample validation residuals in
    chronological order (folds are non-overlapping and generated in
    ascending order, so simple list order already IS chronological order),
    excluding `is_imputed` rows (Decision 011) and any failed-fit `NaN`s.
    """
    residuals = [
        r["residual"]
        for r in fold_records
        if r["split"] == "validation" and not r["is_imputed"] and not np.isnan(r["residual"])
    ]
    return np.asarray(residuals, dtype=float)


def run_ljung_box_diagnostics(
    residuals: np.ndarray, lags: tuple[int, ...] = LJUNG_BOX_LAGS
) -> dict:
    """Ljung-Box test for residual autocorrelation at the given lags,
    answering Open Question #3 with evidence. This does NOT by itself
    trigger building `residual_lag_*` features - that remains Stage 2's
    decision per `research_context/PIPELINE_ARCHITECTURE_PLAN.md`.
    """
    usable_lags = [lag for lag in lags if residuals.size > lag]
    out: dict = {}
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


def plot_acf_diagnostics(
    residuals_by_district: dict[str, np.ndarray],
    districts: tuple[str, ...] = ACF_DIAGNOSTIC_DISTRICTS,
    output_dir: Path = MODULE1_FIGURES_DIR,
) -> None:
    """Save ACF plots for a representative subset only (one high-volume,
    one moderate, two sparse/zero-inflated districts) - not all 25, per the
    task brief.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    for district in districts:
        residuals = residuals_by_district.get(district)
        if residuals is None or residuals.size < 3:
            logger.warning("Not enough pooled residuals for an ACF plot: %s", district)
            continue

        fig, ax = plt.subplots(figsize=(10, 4))
        max_lags = min(60, residuals.size - 1)
        plot_acf(residuals, lags=max_lags, ax=ax, title=f"Out-of-sample SARIMA residual ACF - {district}")
        fig.tight_layout()
        safe_name = district.replace(" ", "_")
        fig.savefig(output_dir / f"acf_residuals_{safe_name}.png", dpi=150)
        plt.close(fig)
        logger.info("Saved ACF diagnostic plot for %s.", district)


# ---------------------------------------------------------------------------
# Aggregation helper
# ---------------------------------------------------------------------------

def _aggregate_validation_metrics(fold_metrics: list[dict]) -> dict:
    """Per-district aggregate row: median of each metric across folds
    (consistent with `aggregate_mase`'s selection logic), plus summed
    observation counts."""

    def _median(key: str) -> float:
        values = [r[key] for r in fold_metrics if not np.isnan(r[key])]
        return float(np.median(values)) if values else float("nan")

    return {
        "rmse": _median("rmse"),
        "mae": _median("mae"),
        "smape": _median("smape"),
        "mase": _median("mase"),
        "n_obs_scored": int(sum(r["n_obs_scored"] for r in fold_metrics)),
        "n_obs_total": int(sum(r["n_obs_total"] for r in fold_metrics)),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_stage1_pipeline(districts: list[str] = DISTRICTS) -> None:
    df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])

    all_prediction_rows: list[dict] = []
    all_metric_rows: list[dict] = []
    config_rows: list[dict] = []
    residuals_by_district: dict[str, np.ndarray] = {}

    for district in districts:
        logger.info("=== %s ===", district)
        series = get_district_series(df, district, value_col=VALUE_COL)
        imputed = get_district_imputed_flags(df, district)
        pre_holdout_series = series.iloc[: len(series) - HOLDOUT_YEARS * WEEKS_PER_YEAR]

        candidate_results = {}
        for use_log1p in (False, True):
            key = "log1p" if use_log1p else "raw"
            order, seasonal_order, fallback_used = select_order(pre_holdout_series, use_log1p)
            result = validate_candidate(series, imputed, district, order, seasonal_order, use_log1p)
            result["fallback_used"] = fallback_used
            candidate_results[key] = result
            logger.info(
                "%s | %-5s | order=%s seasonal_order=%s | aggregate_mase=%.4f | fallback_used=%s",
                district,
                key,
                order,
                seasonal_order,
                result["aggregate_mase"],
                fallback_used,
            )

        if np.isnan(candidate_results["raw"]["aggregate_mase"]) and np.isnan(
            candidate_results["log1p"]["aggregate_mase"]
        ):
            logger.warning(
                "%s: BOTH candidates failed to produce any valid validation "
                "fold - defaulting to 'raw' with fallback order. Investigate "
                "this district manually.",
                district,
            )

        winner_key = select_winning_candidate(
            candidate_results["raw"]["aggregate_mase"], candidate_results["log1p"]["aggregate_mase"]
        )
        winner = candidate_results[winner_key]
        use_log1p_winner = winner_key == "log1p"

        config_rows.append(
            {
                "District": district,
                "order_p": winner["order"][0],
                "order_d": winner["order"][1],
                "order_q": winner["order"][2],
                "seasonal_P": winner["seasonal_order"][0],
                "seasonal_D": winner["seasonal_order"][1],
                "seasonal_Q": winner["seasonal_order"][2],
                "seasonal_m": winner["seasonal_order"][3],
                "use_log1p": use_log1p_winner,
                "raw_aggregate_mase": candidate_results["raw"]["aggregate_mase"],
                "log1p_aggregate_mase": candidate_results["log1p"]["aggregate_mase"],
                "fallback_used": winner["fallback_used"],
            }
        )

        all_prediction_rows.extend(winner["fold_records"])
        all_metric_rows.extend(winner["fold_metrics"])

        aggregate_row = {"District": district, "split": "validation_aggregate", "fold_id": "aggregate"}
        aggregate_row.update(_aggregate_validation_metrics(winner["fold_metrics"]))

        district_residuals = pooled_validation_residuals(winner["fold_records"])
        residuals_by_district[district] = district_residuals
        aggregate_row.update(run_ljung_box_diagnostics(district_residuals))
        all_metric_rows.append(aggregate_row)

        holdout_result = forecast_holdout(
            series, imputed, district, winner["order"], winner["seasonal_order"], use_log1p_winner
        )
        all_prediction_rows.extend(holdout_result["fold_records"])
        all_metric_rows.append(holdout_result["metric_row"])

    predictions_df = pd.DataFrame(all_prediction_rows)
    metrics_df = pd.DataFrame(all_metric_rows)
    config_df = pd.DataFrame(config_rows)

    MODULE1_SARIMA_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODULE1_SARIMA_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODULE1_SARIMA_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

    predictions_df.to_csv(MODULE1_SARIMA_PREDICTIONS_PATH, index=False)
    config_df.to_csv(MODULE1_SARIMA_CONFIG_PATH, index=False)
    metrics_df.to_csv(MODULE1_SARIMA_METRICS_PATH, index=False)

    plot_acf_diagnostics(residuals_by_district)

    logger.info(
        "Stage 1 complete: %d prediction rows -> %s | %d config rows -> %s | "
        "%d metric rows -> %s",
        len(predictions_df),
        MODULE1_SARIMA_PREDICTIONS_PATH,
        len(config_df),
        MODULE1_SARIMA_CONFIG_PATH,
        len(metrics_df),
        MODULE1_SARIMA_METRICS_PATH,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_stage1_pipeline()
