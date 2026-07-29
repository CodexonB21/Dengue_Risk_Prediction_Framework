"""M2-007C consecutive-week / ramp-sensitive alert rule (post-processing).

Extends the F2-optimal single-threshold alert with a ramp branch:

```text
alert_flag = (calibrated_probability >= tau) OR
             (calibrated_probability >= tau_ramp AND ramp_ratio >= rho)
```

where ``ramp_ratio = cases_lag_1 / max(cases_lag_2, 1)`` with Decision 028
masking (``is_imputed``, ``is_reporting_anomaly`` -> NaN lags -> ramp branch off).

Rule parameters ``tau_ramp`` and ``rho`` are grid-searched on validation folds
only; holdout is scored with the selected rule for an honest check.
"""

from __future__ import annotations

import itertools
import logging
from typing import Iterable

import numpy as np
import pandas as pd

from src.module2_classification import evaluate

logger = logging.getLogger(__name__)

TARGET_COL = "label"
CALIBRATED_PROB_COL = "calibrated_probability"


def compute_ramp_ratio(
    cases_lag_1: np.ndarray | pd.Series,
    cases_lag_2: np.ndarray | pd.Series,
) -> np.ndarray:
    """``cases_lag_1 / max(cases_lag_2, 1)``; NaN if either lag is missing."""
    lag1 = np.asarray(cases_lag_1, dtype=float)
    lag2 = np.asarray(cases_lag_2, dtype=float)
    ratio = lag1 / np.maximum(lag2, 1.0)
    invalid = np.isnan(lag1) | np.isnan(lag2)
    ratio[invalid] = np.nan
    return ratio


def apply_ramp_alert_rule(
    calibrated_probability: np.ndarray | pd.Series,
    cases_lag_1: np.ndarray | pd.Series,
    cases_lag_2: np.ndarray | pd.Series,
    *,
    tau: float,
    tau_ramp: float,
    rho: float,
) -> np.ndarray:
    """Binary alert flags under the M2-007C rule."""
    prob = np.asarray(calibrated_probability, dtype=float)
    ratio = compute_ramp_ratio(cases_lag_1, cases_lag_2)
    base_alert = prob >= tau
    ramp_alert = (prob >= tau_ramp) & (ratio >= rho)
    ramp_alert = np.where(np.isnan(ratio), False, ramp_alert)
    return base_alert | ramp_alert


def _metric_row(
    y_true: np.ndarray,
    alert_flags: np.ndarray,
    *,
    tau: float,
    tau_ramp: float | None,
    rho: float | None,
    rule_name: str,
    mask: np.ndarray | None = None,
) -> dict:
    yt, yp = evaluate._apply_mask(y_true, alert_flags.astype(float), mask=mask)
    pred = (yp >= 0.5).astype(float)
    return {
        "rule": rule_name,
        "tau": tau,
        "tau_ramp": tau_ramp,
        "rho": rho,
        "precision": evaluate.precision(yt, pred),
        "recall": evaluate.recall(yt, pred),
        "f1": evaluate.f1(yt, pred),
        "f2": evaluate.fbeta_score(yt, pred, beta=2.0),
        "n_alerts": int(pred.sum()),
        "n_obs_scored": int(len(yt)),
    }


def grid_search_ramp_rule(
    population: pd.DataFrame,
    *,
    tau: float,
    tau_ramp_grid: Iterable[float] | None = None,
    rho_grid: Iterable[float] | None = None,
) -> pd.DataFrame:
    """Grid-search ``(tau_ramp, rho)`` on validation rows; maximize F2."""
    tau_ramp_grid = list(tau_ramp_grid or np.arange(0.05, tau, 0.01))
    rho_grid = list(rho_grid or [1.2, 1.5, 2.0, 2.5, 3.0, 4.0])

    y_true = population[TARGET_COL].to_numpy(dtype=float)
    prob = population[CALIBRATED_PROB_COL].to_numpy(dtype=float)
    lag1 = population["cases_lag_1"].to_numpy(dtype=float)
    lag2 = population["cases_lag_2"].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)

    rows = []
    for tau_ramp, rho in itertools.product(tau_ramp_grid, rho_grid):
        if tau_ramp >= tau:
            continue
        flags = apply_ramp_alert_rule(prob, lag1, lag2, tau=tau, tau_ramp=tau_ramp, rho=rho)
        rows.append(_metric_row(y_true, flags, tau=tau, tau_ramp=tau_ramp, rho=rho, rule_name="ramp", mask=mask))

    return pd.DataFrame(rows)


def select_ramp_parameters(scan_df: pd.DataFrame) -> tuple[float, float]:
    if scan_df.empty:
        raise ValueError("Ramp rule grid search produced no candidates.")
    best = scan_df.loc[scan_df["f2"].idxmax()]
    return float(best["tau_ramp"]), float(best["rho"])


def attach_case_lags(predictions_df: pd.DataFrame, feature_table_path) -> pd.DataFrame:
    """Join masked ``cases_lag_1/2`` from the Stage 1 feature table."""
    lags = pd.read_csv(feature_table_path)[
        ["District", "Year", "Week", "cases_lag_1", "cases_lag_2", "is_imputed", "is_reporting_anomaly"]
    ]
    merged = predictions_df.merge(lags, on=["District", "Year", "Week"], how="left", suffixes=("", "_feat"))
    if "is_imputed_feat" in merged.columns:
        untrusted = merged["is_imputed"].astype(bool) | merged["is_imputed_feat"].astype(bool)
        if "is_reporting_anomaly" in merged.columns and "is_reporting_anomaly_feat" in merged.columns:
            untrusted = untrusted | merged["is_reporting_anomaly"].astype(bool) | merged["is_reporting_anomaly_feat"].astype(bool)
        merged.loc[untrusted, ["cases_lag_1", "cases_lag_2"]] = np.nan
    return merged
