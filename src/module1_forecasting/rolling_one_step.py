"""Module 1 - Rolling one-step-ahead operational evaluation.

Distinct from `baseline_sarima.forecast_holdout()` (fits SARIMA once on all
pre-holdout data and forecasts the entire 104-week holdout block in one
multi-step call) and from walk-forward validation folds (fixed fold
structure for model selection).

This script answers: "if we refit SARIMA each week on all data strictly
before week t and forecast only t, then apply the frozen Stage 2 XGBoost
checkpoint, how accurate are we?" — the evaluation mode closest to a
real weekly production deployment.

Uses the same district configs, XGBoost final model, and feature layout as
`compensation_model.py` / `forecast_future.py`. Case-derived features
respect `is_imputed` and `is_reporting_anomaly` masking via
`feature_engineering.build_fold_agnostic_features`.

`compute_dm_results_rolling()` additionally runs a Diebold-Mariano test
per district on this series (Phase 1 of the Module 1 remediation plan) -
`combine.py`'s own DM test only reaches significance for 5/25 districts at
its strict holdout-only scope (n=104/district); `--scope all` here produces
a much larger per-district out-of-sample sample. This is reporting only -
no model or feature is ever selected from it.
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings
from collections import deque
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import xgboost as xgb
from statsmodels.tsa.statespace.sarimax import SARIMAX

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_ROLLING_ONE_STEP_DM_PATH,
    MODULE1_ROLLING_ONE_STEP_METRICS_PATH,
    MODULE1_ROLLING_ONE_STEP_PATH,
    MODULE1_SARIMA_CONFIG_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.baseline_sarima import _has_explosive_ar_root, fit_and_forecast  # noqa: E402
from src.module1_forecasting.compensation_model import FEATURE_COLUMNS  # noqa: E402
from src.module1_forecasting.evaluate import dm_test, smape  # noqa: E402
from src.module1_forecasting.residual_transform import (  # noqa: E402
    combine_stage2_forecast,
    compute_stage2_target,
    validate_residual_mode,
)
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    HUMIDITY_COLUMN,
    RAINFALL_COLUMN,
    TEMPERATURE_COLUMN,
    build_fold_agnostic_features,
    compute_fold_climate_anomalies,
)
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_MIN_TRAIN_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    get_holdout_series,
)

logger = logging.getLogger(__name__)

CLIMATE_RAW_COLUMNS = [RAINFALL_COLUMN, TEMPERATURE_COLUMN, HUMIDITY_COLUMN]
DM_MAX_LAG = 12  # matches combine.py's DM_MAX_LAG for the holdout-block DM test
FOLD_AGNOSTIC_NUMERIC = [c for c in FEATURE_COLUMNS if c not in (
    "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly",
    "sarima_prediction", "residual_lag_1", "residual_lag_2", "District",
)]


def _load_selected_configs() -> dict[str, dict]:
    cfg = pd.read_csv(MODULE1_SARIMA_CONFIG_PATH)
    configs: dict[str, dict] = {}
    for _, row in cfg.iterrows():
        configs[row["District"]] = {
            "order": (int(row["order_p"]), int(row["order_d"]), int(row["order_q"])),
            "seasonal_order": (
                int(row["seasonal_P"]), int(row["seasonal_D"]),
                int(row["seasonal_Q"]), int(row["seasonal_m"]),
            ),
            "use_log1p": bool(row["use_log1p"]),
        }
    return configs


def _week_key(year: int, week: int) -> tuple[int, int]:
    return int(year), int(week)


def _low_freq_refit_step(
    train_series: pd.Series,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    use_log1p: bool,
    context: str,
    *,
    fitted_state,
    state_len: int,
    weeks_since_refit: int,
    refit_interval_weeks: int,
):
    """M1-014: one rolling step under a less-frequent refit cadence.

    Refits fresh (cold `.fit()`, same cost as the default weekly path) only
    every `refit_interval_weeks`; in between, extends the existing fitted
    state with the single newly-available observation via
    `SARIMAXResults.append(refit=False)` - a cheap Kalman-filter state
    update, NOT a re-optimization (confirmed via the statsmodels docstring
    before implementing this) - then forecasts 1 step from the updated
    state. Targets the hypothesis that refitting every single week (M1-011/
    Decision 035) may be *more* frequent than the true underlying process
    needs, without giving up entirely on incorporating new data (which pure
    buy-and-hold would do).

    Returns `(forecast, new_fitted_state, new_state_len, new_weeks_since_refit)`.
    On any failure, returns `(nan, None, 0, refit_interval_weeks)` - `None`
    state and `weeks_since_refit == refit_interval_weeks` force a fresh cold
    refit on the next call rather than propagating a broken state forward.
    """
    values = train_series.to_numpy(dtype=float)
    fit_values = np.log1p(values) if use_log1p else values
    need_refit = fitted_state is None or weeks_since_refit >= refit_interval_weeks

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if need_refit:
                model = SARIMAX(
                    fit_values, order=order, seasonal_order=seasonal_order,
                    enforce_stationarity=False, enforce_invertibility=False,
                )
                fitted = model.fit(disp=False)
                new_state_len = len(fit_values)
                new_weeks_since_refit = 0
            else:
                new_obs = fit_values[state_len:]
                fitted = fitted_state.append(new_obs, refit=False)
                new_state_len = len(fit_values)
                new_weeks_since_refit = weeks_since_refit + 1

            if _has_explosive_ar_root(fitted):
                logger.warning(
                    "Low-freq-refit SARIMAX for %s (order=%s, seasonal_order=%s, "
                    "use_log1p=%s, need_refit=%s) is non-stationary/explosive; "
                    "forcing a fresh cold refit next call.",
                    context, order, seasonal_order, use_log1p, need_refit,
                )
                return np.nan, None, 0, refit_interval_weeks
            forecast = float(fitted.forecast(steps=1)[0])
    except Exception:
        logger.warning(
            "Low-freq-refit SARIMAX fit/append/forecast failed for %s "
            "(order=%s, seasonal_order=%s, use_log1p=%s, need_refit=%s); "
            "forcing a fresh cold refit next call.",
            context, order, seasonal_order, use_log1p, need_refit, exc_info=True,
        )
        return np.nan, None, 0, refit_interval_weeks

    if use_log1p:
        forecast = float(np.expm1(forecast))
    forecast = max(forecast, 0.0)
    return forecast, fitted, new_state_len, new_weeks_since_refit


def _vintage_ensemble_step(
    train_series: pd.Series,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    use_log1p: bool,
    context: str,
    *,
    vintage_deque: "deque[tuple[int, object]]",
    ensemble_window: int,
):
    """M1-015: fresh weekly refit (identical cost/behavior to the default
    cold path - no slowdown), but the final SARIMA prediction for week t is
    the average, in transformed space, of this week's own 1-step forecast
    AND the forecasts that the last `ensemble_window - 1` weeks' OWN
    independently-fitted models make for the SAME target week (extended
    forward via cheap `.forecast(steps=h)` calls, not refit). Targets the
    hypothesis (M1-011) that each week's fresh MLE optimum is itself noisy;
    averaging several independent vintages' opinions about the same target
    week is a standard forecast-combination approach to reducing that noise,
    distinct from - and not ruled out by - M1-013's rejected warm-start
    approach (which tried to change what a single fit converges to, not
    combine several).

    Mutates `vintage_deque` in place (appends this week's fit, evicts the
    oldest once over `ensemble_window`). Returns the ensembled forecast.
    """
    values = train_series.to_numpy(dtype=float)
    fit_values = np.log1p(values) if use_log1p else values
    target_train_len = len(fit_values)  # this model's steps=1 forecast covers index target_train_len

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = SARIMAX(
                fit_values, order=order, seasonal_order=seasonal_order,
                enforce_stationarity=False, enforce_invertibility=False,
            )
            fitted = model.fit(disp=False)
            if _has_explosive_ar_root(fitted):
                logger.warning(
                    "Vintage-ensemble SARIMAX for %s (order=%s, seasonal_order=%s, "
                    "use_log1p=%s) is non-stationary/explosive; dropping this "
                    "vintage from the ensemble.",
                    context, order, seasonal_order, use_log1p,
                )
                vintage_deque.append((target_train_len, None))
                if len(vintage_deque) > ensemble_window:
                    vintage_deque.popleft()
                return np.nan
            this_week_forecast = float(fitted.forecast(steps=1)[0])
    except Exception:
        logger.warning(
            "Vintage-ensemble SARIMAX fit/forecast failed for %s (order=%s, "
            "seasonal_order=%s, use_log1p=%s); dropping this vintage.",
            context, order, seasonal_order, use_log1p, exc_info=True,
        )
        vintage_deque.append((target_train_len, None))
        if len(vintage_deque) > ensemble_window:
            vintage_deque.popleft()
        return np.nan

    forecasts_transformed = [this_week_forecast]
    for older_train_len, older_fitted in vintage_deque:
        if older_fitted is None:
            continue
        horizon = target_train_len - older_train_len + 1
        if horizon <= 0:
            continue
        try:
            forecasts_transformed.append(float(older_fitted.forecast(steps=horizon)[-1]))
        except Exception:
            logger.warning(
                "Vintage-ensemble older-fit forecast failed for %s (horizon=%d); "
                "excluding that vintage from this week's average.",
                context, horizon, exc_info=True,
            )

    vintage_deque.append((target_train_len, fitted))
    if len(vintage_deque) > ensemble_window:
        vintage_deque.popleft()

    forecast = float(np.mean(forecasts_transformed))
    if use_log1p:
        forecast = float(np.expm1(forecast))
    forecast = max(forecast, 0.0)
    return forecast


def rolling_one_step_district(
    district: str,
    weekly_df: pd.DataFrame,
    sarima_config: dict,
    xgb_model: xgb.XGBRegressor,
    *,
    min_train_weeks: int,
    target_keys: set[tuple[int, int]] | None,
    residual_mode: str = M1_STAGE2_RESIDUAL_MODE,
    sarima_prediction_overrides: dict[tuple[int, int], float] | None = None,
    model_resolver: "Callable[[int, int], xgb.XGBRegressor] | None" = None,
    warm_start: bool = False,
    refit_interval_weeks: int | None = None,
    ensemble_window: int | None = None,
) -> pd.DataFrame:
    """
    `sarima_prediction_overrides` (Open Question #17 diagnostic,
    `scripts/diagnose_rolling_dm_gap.py`): when a `(Year, Week)` key is
    present, skip the expensive `fit_and_forecast()` SARIMAX refit and reuse
    the given value instead - lets a diagnostic reuse an already-completed
    rolling run's `sarima_prediction` column verbatim while only varying
    which Stage 2 model scores the (otherwise identical) feature row. Safe
    because `residual_lag_1/2` are built from ACTUAL residuals
    (`compute_stage2_target(actual, sarima_pred)`), not from any model's
    prediction, so feature rows are already model-independent - only
    `predicted_residual`/`final_prediction` change.

    `model_resolver(year, week) -> xgb.XGBRegressor`, if given, picks which
    Stage 2 model scores that row's feature vector, instead of the single
    `xgb_model` passed in (which remains the default for any week the
    resolver doesn't override).

    `warm_start` (M1-013, root-causing Open Question #17/Decision 035's
    finding that weekly SARIMA refits are only weakly correlated with the
    walk-forward fold refits of the same weeks): when True, each week's
    `fit_and_forecast()` call is seeded with the PREVIOUS week's converged
    `SARIMAX` parameters via `start_params` (valid since `order`/
    `seasonal_order` - and therefore the parameter vector's shape - are
    fixed for this district's entire loop; only the training window grows
    by one row each week). The hypothesis: this reduces week-to-week
    optimizer-local-optimum jumping relative to a cold `.fit()` every time.
    Falls back to a cold start (`start_params=None`) for the first scored
    week and after any failed fit (no params to carry forward).

    `refit_interval_weeks` (M1-014, `_low_freq_refit_step`) and
    `ensemble_window` (M1-015, `_vintage_ensemble_step`) are mutually
    exclusive with each other and with `warm_start` - at most one of the
    three should be set per call. Both default to `None` (unchanged weekly-
    cold-refit behavior).
    """
    dist_df = (
        weekly_df.loc[weekly_df["District"] == district]
        .sort_values(["Year", "Week"])
        .reset_index(drop=True)
    )
    if len(dist_df) <= min_train_weeks:
        return pd.DataFrame()

    work_cols = ["District", "Year", "Week", "Number_of_Cases", "is_imputed", "is_reporting_anomaly"] + CLIMATE_RAW_COLUMNS
    work_cols = [c for c in work_cols if c in dist_df.columns]

    residual_history: dict[tuple[int, int], float] = {}
    rows: list[dict] = []
    last_params: np.ndarray | None = None
    low_freq_fitted = None
    low_freq_state_len = 0
    weeks_since_refit = 0
    vintage_deque: deque = deque()

    for i in range(min_train_weeks, len(dist_df)):
        row = dist_df.iloc[i]
        year, week = int(row["Year"]), int(row["Week"])
        key = _week_key(year, week)
        if target_keys is not None and key not in target_keys:
            continue

        override = sarima_prediction_overrides.get(key) if sarima_prediction_overrides else None
        if override is not None:
            sarima_pred = float(override)
        else:
            train_df = dist_df.iloc[:i]
            train_series = pd.Series(
                train_df["Number_of_Cases"].to_numpy(dtype=float),
                index=pd.MultiIndex.from_frame(train_df[["Year", "Week"]]),
            )
            if refit_interval_weeks is not None:
                sarima_pred, low_freq_fitted, low_freq_state_len, weeks_since_refit = _low_freq_refit_step(
                    train_series,
                    sarima_config["order"], sarima_config["seasonal_order"], sarima_config["use_log1p"],
                    context=f"{district} rolling low-freq-refit {year} Wk{week}",
                    fitted_state=low_freq_fitted, state_len=low_freq_state_len,
                    weeks_since_refit=weeks_since_refit, refit_interval_weeks=refit_interval_weeks,
                )
            elif ensemble_window is not None:
                sarima_pred = _vintage_ensemble_step(
                    train_series,
                    sarima_config["order"], sarima_config["seasonal_order"], sarima_config["use_log1p"],
                    context=f"{district} rolling vintage-ensemble {year} Wk{week}",
                    vintage_deque=vintage_deque, ensemble_window=ensemble_window,
                )
            elif warm_start:
                forecast_arr, fitted_params = fit_and_forecast(
                    train_series,
                    n_periods=1,
                    order=sarima_config["order"],
                    seasonal_order=sarima_config["seasonal_order"],
                    use_log1p=sarima_config["use_log1p"],
                    context=f"{district} rolling 1-step {year} Wk{week}",
                    start_params=last_params,
                    return_params=True,
                )
                sarima_pred = float(forecast_arr[0])
                last_params = fitted_params if fitted_params is not None else last_params
            else:
                sarima_pred = float(
                    fit_and_forecast(
                        train_series,
                        n_periods=1,
                        order=sarima_config["order"],
                        seasonal_order=sarima_config["seasonal_order"],
                        use_log1p=sarima_config["use_log1p"],
                        context=f"{district} rolling 1-step {year} Wk{week}",
                    )[0]
                )

        # Features for week t use history through t (current-week cases nulled).
        hist_df = dist_df.iloc[: i + 1][work_cols].copy()
        hist_df.loc[hist_df.index[-1], "Number_of_Cases"] = np.nan
        feats = build_fold_agnostic_features(hist_df)
        row_feats = feats.iloc[-1]

        train_mask = pd.Series(False, index=hist_df.index)
        train_mask.iloc[:-1] = True
        anomalies = compute_fold_climate_anomalies(hist_df, train_mask)
        anomaly_row = anomalies.iloc[-1]

        prev1 = _week_key(int(dist_df.iloc[i - 1]["Year"]), int(dist_df.iloc[i - 1]["Week"])) if i >= 1 else None
        prev2 = _week_key(int(dist_df.iloc[i - 2]["Year"]), int(dist_df.iloc[i - 2]["Week"])) if i >= 2 else None

        feature_row = {col: row_feats[col] for col in FOLD_AGNOSTIC_NUMERIC if col in row_feats.index}
        feature_row["rainfall_anomaly"] = float(anomaly_row["rainfall_anomaly"])
        feature_row["temperature_anomaly"] = float(anomaly_row["temperature_anomaly"])
        feature_row["humidity_anomaly"] = float(anomaly_row["humidity_anomaly"])
        feature_row["sarima_prediction"] = sarima_pred
        feature_row["residual_lag_1"] = residual_history.get(prev1, np.nan) if prev1 else np.nan
        feature_row["residual_lag_2"] = residual_history.get(prev2, np.nan) if prev2 else np.nan
        feature_row["District"] = district

        X = pd.DataFrame([feature_row])[FEATURE_COLUMNS]
        X["District"] = pd.Categorical(X["District"], categories=DISTRICTS)
        active_model = model_resolver(year, week) if model_resolver is not None else xgb_model
        predicted_residual = float(active_model.predict(X)[0])
        final_prediction = float(
            combine_stage2_forecast(sarima_pred, predicted_residual, mode=residual_mode)
        )

        actual = float(row["Number_of_Cases"])
        if not np.isnan(sarima_pred) and not bool(row.get("is_reporting_anomaly", False)):
            residual_history[key] = float(
                compute_stage2_target(actual, sarima_pred, mode=residual_mode)
            )

        numeric_feats = pd.Series(feature_row)[FOLD_AGNOSTIC_NUMERIC + [
            "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly",
            "sarima_prediction", "residual_lag_1", "residual_lag_2",
        ]]
        completeness = float(numeric_feats.notna().mean())

        rows.append({
            "District": district,
            "Year": year,
            "Week": week,
            "Week_Start_Date": row.get("Week_Start_Date"),
            "Number_of_Cases": actual,
            "is_imputed": bool(row.get("is_imputed", False)),
            "is_reporting_anomaly": bool(row.get("is_reporting_anomaly", False)),
            "sarima_prediction": sarima_pred,
            "predicted_residual": predicted_residual,
            "final_prediction": round(final_prediction, 1),
            "feature_completeness_pct": round(100 * completeness, 1),
            "evaluation_mode": "rolling_one_step",
        })

    return pd.DataFrame(rows)


def _holdout_target_keys(weekly_df: pd.DataFrame, district: str) -> set[tuple[int, int]]:
    series = pd.Series(
        weekly_df.loc[weekly_df["District"] == district, "Number_of_Cases"].to_numpy(),
        index=pd.MultiIndex.from_frame(
            weekly_df.loc[weekly_df["District"] == district, ["Year", "Week"]]
        ),
    )
    holdout = get_holdout_series(
        series,
        holdout_years=DEFAULT_HOLDOUT_YEARS,
        weeks_per_year=DEFAULT_WEEKS_PER_YEAR,
    )
    return {_week_key(int(y), int(w)) for y, w in holdout.index}


def summarize_metrics(result: pd.DataFrame) -> pd.DataFrame:
    """Period summaries for thesis reporting (Colombo/Gampaha focus periods)."""
    if result.empty:
        return pd.DataFrame()

    scored = result[~result["is_imputed"]].copy()
    periods = [
        ("holdout_all", lambda s: pd.Series(True, index=s.index)),
        ("2026_wk22_23", lambda s: (s["Year"] == 2026) & s["Week"].isin([22, 23])),
        ("2026_wk22_25", lambda s: (s["Year"] == 2026) & s["Week"].between(22, 25)),
        ("2026_wk25_only", lambda s: (s["Year"] == 2026) & (s["Week"] == 25)),
    ]
    summary_rows = []
    for district in sorted(scored["District"].unique()):
        dist = scored[scored["District"] == district]
        for period_name, mask_fn in periods:
            sub = dist[mask_fn(dist)]
            if sub.empty:
                continue
            summary_rows.append({
                "District": district,
                "period": period_name,
                "smape_pct": round(smape(sub["Number_of_Cases"], sub["final_prediction"]), 1),
                "n_weeks": len(sub),
                "evaluation_mode": "rolling_one_step",
            })
    return pd.DataFrame(summary_rows)


def compute_dm_results_rolling(result: pd.DataFrame, *, scope: str) -> pd.DataFrame:
    """Diebold-Mariano test (Stage-1-only vs Stage-1+Stage-2), per district,
    on the rolling one-step series.

    `combine.py`'s own DM test only reaches `p < 0.05` for 5/25 districts at
    its strict holdout-only scope (n=104/district) - this is a genuinely
    larger out-of-sample sample per district (every rolling-scored week, not
    just the 104-week holdout block), giving the test more statistical
    power. Masking mirrors `combine.py` exactly (`is_imputed` only -
    `is_reporting_anomaly` rows are NOT excluded, matching the existing
    convention there). This is pure evidence-gathering: no model or feature
    is ever selected from this result, so it carries no leakage risk.
    """
    scored = result.loc[~result["is_imputed"]].copy()
    rows: list[dict] = []
    for district in sorted(scored["District"].unique()):
        dist = scored.loc[scored["District"] == district]
        e1 = (dist["Number_of_Cases"] - dist["sarima_prediction"]).to_numpy(dtype=float)
        e2 = (dist["Number_of_Cases"] - dist["final_prediction"]).to_numpy(dtype=float)
        dm = dm_test(e1, e2, max_lag=DM_MAX_LAG, loss="squared")
        rows.append({"District": district, "scope": scope, **dm})
    return pd.DataFrame(rows)


def run_rolling_one_step(
    districts: list[str] | None = None,
    *,
    scope: str = "holdout",
    min_train_years: int = DEFAULT_MIN_TRAIN_YEARS,
    residual_mode: str | None = None,
    warm_start: bool = False,
    output_path: Path | None = None,
    metrics_path: Path | None = None,
    dm_path: Path | None = None,
) -> pd.DataFrame:
    mode = validate_residual_mode(residual_mode or M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    weekly_df = pd.read_csv(
        MODULE1_WEEKLY_MODELING_TABLE_PATH,
        parse_dates=["Week_Start_Date", "Week_End_Date"],
    )
    sarima_configs = _load_selected_configs()
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(paths["xgboost_final_model"]))

    districts = districts or DISTRICTS
    min_train_weeks = min_train_years * DEFAULT_WEEKS_PER_YEAR

    frames = []
    for district in districts:
        target_keys = _holdout_target_keys(weekly_df, district) if scope == "holdout" else None
        logger.info("Rolling 1-step scoring %s (%d target weeks)...", district, len(target_keys or []))
        frames.append(
            rolling_one_step_district(
                district,
                weekly_df,
                sarima_configs[district],
                xgb_model,
                min_train_weeks=min_train_weeks,
                target_keys=target_keys,
                residual_mode=mode,
                warm_start=warm_start,
            )
        )

    result = pd.concat(frames, ignore_index=True)
    out_path = output_path or MODULE1_ROLLING_ONE_STEP_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)

    metrics = summarize_metrics(result)
    met_path = metrics_path or MODULE1_ROLLING_ONE_STEP_METRICS_PATH
    met_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(met_path, index=False)

    dm_results = compute_dm_results_rolling(result, scope=scope)
    dm_out_path = dm_path or MODULE1_ROLLING_ONE_STEP_DM_PATH
    dm_out_path.parent.mkdir(parents=True, exist_ok=True)
    dm_results.to_csv(dm_out_path, index=False)

    logger.info(
        "Wrote %d rolling 1-step rows to %s, %d summary rows to %s, and %d DM-test rows to %s.",
        len(result), out_path, len(metrics), met_path, len(dm_results), dm_out_path,
    )
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 1 rolling one-step-ahead evaluation.")
    parser.add_argument(
        "--districts", nargs="+", default=None,
        help=f"Districts to score (default: all {len(DISTRICTS)}).",
    )
    parser.add_argument(
        "--scope", choices=["holdout", "all"], default="holdout",
        help="holdout = last 2 years per district only; all = every week after min train window.",
    )
    parser.add_argument(
        "--residual-mode",
        choices=["additive", "log"],
        default=None,
        help="Stage 2 target transform (must match trained XGBoost model).",
    )
    parser.add_argument(
        "--warm-start", action="store_true",
        help="Seed each week's SARIMAX fit with the previous week's converged params (M1-013).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_rolling_one_step(
        districts=args.districts, scope=args.scope, residual_mode=args.residual_mode,
        warm_start=args.warm_start,
    )
