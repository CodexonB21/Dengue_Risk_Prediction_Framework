"""Module 1 Stage 1 - STL + ARIMA pilot candidate (M1-012).

Targets the finding that 18/25 districts' selected SARIMA has no seasonal
component at all (`seasonal_order=(0,0,0,52)`, Open Question #12) despite
`m=52` - both OCSB and Canova-Hansen seasonal-differencing tests
independently agreed `D=0`, and forcing `D=1` was previously benchmarked as
computationally infeasible at scale (~7 min/fit). This module instead
decomposes the series with STL (which does not require a seasonal-
differencing search at all) and fits a plain, cheap non-seasonal ARIMA on
the deseasonalized series.

Uses `statsmodels.tsa.forecasting.stl.STLForecast`, confirmed (2026-08-04,
plan verification) to handle seasonal + trend extrapolation internally - no
hand-rolled extrapolation logic is needed, unlike the original (more
speculative) version of this plan.

Mirrors `baseline_sarima.py`'s interface (`select_order` / `fit_and_forecast`
/ `validate_candidate`) exactly, so it can reuse `validation.py`'s unchanged
walk-forward fold generator with no changes to the harness - this is a pilot
on a small set of districts, NOT wired into `main.py`'s validated pipeline
and NOT swapping any district's production Stage 1 config (see
`scripts/pilot_stl_arima.py`).
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pmdarima as pm
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.forecasting.stl import STLForecast

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.module1_forecasting.evaluate import compute_all_metrics  # noqa: E402
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_MIN_TRAIN_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    fit_window,
    generate_walk_forward_folds,
)

logger = logging.getLogger(__name__)

WEEKS_PER_YEAR = DEFAULT_WEEKS_PER_YEAR
HOLDOUT_YEARS = DEFAULT_HOLDOUT_YEARS
MIN_TRAIN_YEARS = DEFAULT_MIN_TRAIN_YEARS

# Same constrained bounds as baseline_sarima.AUTO_ARIMA_KWARGS, just
# non-seasonal - STL already extracts the seasonal cycle, so the ARIMA
# fit on the deseasonalized series never needs a seasonal search at all,
# which is what makes this cheap enough to run at scale (unlike forcing
# D=1 directly on the raw series, previously benchmarked as infeasible).
AUTO_ARIMA_KWARGS = dict(
    seasonal=False,
    max_p=2,
    max_q=2,
    information_criterion="aic",
    suppress_warnings=True,
    error_action="ignore",
)
FALLBACK_ORDER = (1, 1, 1)

# STL requires at least two full periods of history to fit at all.
MIN_STL_OBSERVATIONS = 2 * WEEKS_PER_YEAR


def select_stl_order(series: pd.Series, use_log1p: bool) -> tuple[tuple[int, int, int], bool]:
    """Non-seasonal `auto_arima` on the raw/log1p series (NOT the STL
    remainder - `STLForecast` handles deseasonalizing internally per fit).
    One call per district per transform, mirroring
    `baseline_sarima.select_order()`'s cost profile exactly."""
    values = series.to_numpy(dtype=float)
    if use_log1p:
        values = np.log1p(values)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = pm.auto_arima(values, **AUTO_ARIMA_KWARGS)
        return model.order, False
    except Exception:
        logger.warning(
            "STL+ARIMA order search failed entirely (use_log1p=%s); falling back to order=%s.",
            use_log1p, FALLBACK_ORDER, exc_info=True,
        )
        return FALLBACK_ORDER, True


def fit_and_forecast_stl(
    train_series: pd.Series,
    n_periods: int,
    order: tuple[int, int, int],
    use_log1p: bool,
    period: int = WEEKS_PER_YEAR,
    context: str = "",
) -> np.ndarray:
    """Fit `STLForecast(values, ARIMA, model_kwargs={"order": order},
    period=period)` and forecast `n_periods` steps ahead, mirroring
    `baseline_sarima.fit_and_forecast()`'s never-raises / 0-floor-clip /
    inverse-transform conventions exactly, so it drops into the same
    walk-forward harness unchanged.
    """
    values = train_series.to_numpy(dtype=float)
    fit_values = np.log1p(values) if use_log1p else values

    if len(fit_values) < MIN_STL_OBSERVATIONS:
        logger.warning(
            "STL+ARIMA fit for %s skipped: only %d observations, need >= %d "
            "(2 full periods) for STL to decompose at all.",
            context, len(fit_values), MIN_STL_OBSERVATIONS,
        )
        return np.full(n_periods, np.nan)

    # A constant trend term ("c") is only valid when d == 0 - with
    # differencing, a constant would be eliminated by the differencing
    # operation itself and statsmodels raises ValueError. No trend term is
    # passed when d > 0 (differencing already absorbs the trend).
    model_kwargs = {"order": order}
    if order[1] == 0:
        model_kwargs["trend"] = "c"

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stlf = STLForecast(fit_values, ARIMA, model_kwargs=model_kwargs, period=period)
            fitted = stlf.fit()
            forecast = fitted.forecast(n_periods)
    except Exception:
        logger.warning(
            "STL+ARIMA fit/forecast failed for %s (order=%s, use_log1p=%s); returning NaNs.",
            context, order, use_log1p, exc_info=True,
        )
        return np.full(n_periods, np.nan)

    forecast = np.asarray(forecast, dtype=float)
    if use_log1p:
        forecast = np.expm1(forecast)
    forecast = np.clip(forecast, a_min=0.0, a_max=None)
    return forecast


def validate_stl_candidate(
    series: pd.Series,
    imputed: pd.Series,
    district: str,
    order: tuple[int, int, int],
    use_log1p: bool,
) -> dict:
    """Walk-forward validate the STL+ARIMA candidate - identical structure
    to `baseline_sarima.validate_candidate()`, calling `fit_and_forecast_stl`
    per fold instead of `fit_and_forecast`."""
    fold_records: list[dict] = []
    fold_metrics: list[dict] = []
    fold_mase_values: list[float] = []

    for fold_id, (train_index, val_index) in enumerate(
        generate_walk_forward_folds(
            series, holdout_years=HOLDOUT_YEARS, min_train_years=MIN_TRAIN_YEARS, weeks_per_year=WEEKS_PER_YEAR,
        ),
        start=1,
    ):
        train_series = fit_window(series, train_index[-1])
        actual = series.loc[val_index]
        imputed_val = imputed.loc[val_index]
        imputed_train = imputed.loc[train_series.index]

        predictions = fit_and_forecast_stl(
            train_series, n_periods=len(val_index), order=order, use_log1p=use_log1p,
            context=f"{district} fold {fold_id} (STL+ARIMA, {'log1p' if use_log1p else 'raw'})",
        )

        for (year, week), y_true, y_pred, is_imp in zip(
            val_index, actual.to_numpy(), predictions, imputed_val.to_numpy()
        ):
            residual = float(y_true - y_pred) if not np.isnan(y_pred) else float("nan")
            fold_records.append({
                "District": district, "Year": int(year), "Week": int(week),
                "split": "validation", "fold_id": fold_id,
                "Number_of_Cases": float(y_true), "is_imputed": bool(is_imp),
                "stl_arima_prediction": float(y_pred) if not np.isnan(y_pred) else float("nan"),
                "residual": residual,
            })

        metrics = compute_all_metrics(
            y_true=actual.to_numpy(), y_pred=predictions, y_train=train_series.to_numpy(),
            m=WEEKS_PER_YEAR, mask=~imputed_val.to_numpy(), train_mask=~imputed_train.to_numpy(),
        )
        fold_metrics.append({"District": district, "split": "validation", "fold_id": fold_id, **metrics})
        if not np.isnan(metrics["mase"]):
            fold_mase_values.append(metrics["mase"])

    aggregate_mase = float(np.median(fold_mase_values)) if fold_mase_values else float("nan")
    return {
        "order": order,
        "fold_records": fold_records,
        "fold_metrics": fold_metrics,
        "aggregate_mase": aggregate_mase,
    }
