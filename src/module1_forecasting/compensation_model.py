"""Module 1 Stage 2 - XGBoost residual compensation model.

Implements the design approved by the user before this file was written (see
`module_1_forecasting/MODULE_CONTEXT.md` "Stage 2 Implementation Status" for
the permanent record):

1. **Pooled model, not per-district** (revisits Decision 002 for Stage 2
   specifically): one XGBoost model per walk-forward fold, trained on all 25
   districts' residuals together with `District` as a categorical feature -
   not 25 separate per-district models. Per-district training data is too
   thin under this walk-forward scheme (fold 2 would have as few as ~52 rows
   for one district); pooling gives ~1,300+ rows even in early folds. Per-
   district MASE is still used for evaluation (`combine.py`), so pooling
   doesn't hide district-level failure.
2. **residual_lag_1/2**: built by reindexing each district's out-of-sample
   residual onto the FULL weekly calendar (not just the sparse validation +
   holdout rows) before taking `shift(1)/shift(2)` - see
   `build_residual_lags()` for why this matters (a genuine ~26-week gap
   exists between the last walk-forward fold and the holdout block for every
   district, discovered while implementing this file).
3. **Walk-forward scheme**: reuses Stage 1's exact 14 folds (via
   `fold_id`/`split` already in `sarima_stage1_predictions.csv`). Fold *k*'s
   training set is the pooled, non-imputed validation-split residuals from
   folds `1..k-1`. Fold 1 has no prior residual data at all and is a
   documented no-op (`predicted_residual = 0`, `stage2_trained = False`).
   Hyperparameters are fixed (not tuned per fold); early stopping uses the
   single most recent prior fold as an internal validation slice wherever
   enough history exists.
4. **Rainfall column**: `feature_engineering.py`'s `RAINFALL_COLUMN` now
   points at `precipitation_sum (mm)` (Decision 008, resolved) - this module
   simply consumes whatever `rainfall_lag_*` columns that produces.

Fold-aware climate anomalies (Feature Group 3) are computed once per
validation/holdout row here, using that row's OWN originating fold's SARIMA
training window (exactly the same training window Stage 1 used to produce
that row's residual) - see `build_fold_scoped_anomalies()`. This value is
then fixed for that row regardless of which later Stage 2 fold consumes it
as a training example, which is safe: reusing a genuinely-already-known,
correctly-scoped value as a training input for a later model is not leakage.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE1_SARIMA_PREDICTIONS_PATH,
    MODULE1_STAGE2_FEATURE_TABLE_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH,
    MODULE1_XGBOOST_FINAL_MODEL_PATH,
    MODULE1_XGBOOST_METRICS_PATH,
    MODULE1_XGBOOST_MODELS_DIR,
    MODULE1_XGBOOST_PREDICTIONS_PATH,
)
from src.module1_forecasting.evaluate import mae, rmse, smape  # noqa: E402
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    compute_fold_climate_anomalies,
)
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_MIN_TRAIN_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    generate_walk_forward_folds,
    get_district_series,
    get_holdout_series,
)

logger = logging.getLogger(__name__)

TARGET_COL = "residual"
IMPUTED_COL = "is_imputed"

WEEKS_PER_YEAR = DEFAULT_WEEKS_PER_YEAR
HOLDOUT_YEARS = DEFAULT_HOLDOUT_YEARS
MIN_TRAIN_YEARS = DEFAULT_MIN_TRAIN_YEARS
N_FOLDS = 14

# Feature Groups 1, 2, 4 (fold-agnostic - already computed globally by
# feature_engineering.py).
FOLD_AGNOSTIC_FEATURE_COLUMNS = [
    "cases_lag_1", "cases_lag_2", "cases_lag_3", "cases_lag_4",
    "rolling_mean_cases_4w", "rolling_std_cases_4w", "rate_of_change",
    "rainfall_lag_2", "rainfall_lag_3", "rainfall_lag_4", "rainfall_lag_5",
    "rainfall_lag_6", "rainfall_lag_7", "rainfall_lag_8",
    "temperature_lag_1", "temperature_lag_2", "temperature_lag_3", "temperature_lag_4",
    "humidity_lag_1", "humidity_lag_2", "humidity_lag_3", "humidity_lag_4",
    "sin_week", "cos_week", "monsoon_indicator_SW", "monsoon_indicator_NE",
]

# Feature Group 3 (fold-aware anomalies), Group 5 (SARIMA prediction +
# residual lags), plus District - a deliberate, documented extension of the
# spec to support the pooled-model decision (see FEATURE_ENGINEERING_SPEC.md).
FOLD_AWARE_FEATURE_COLUMNS = [
    "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly",
    "sarima_prediction", "residual_lag_1", "residual_lag_2",
]
CATEGORICAL_FEATURE_COLUMNS = ["District"]

FEATURE_COLUMNS = FOLD_AGNOSTIC_FEATURE_COLUMNS + FOLD_AWARE_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS

# Fixed, conservative, regularized hyperparameters (not tuned per fold -
# XGBoost fits in seconds so an exhaustive per-fold grid search isn't the
# bottleneck Stage 1's auto_arima search was, but the small-data regime here
# still calls for deliberately shallow/regularized trees rather than an
# expensive search).
#
# objective="reg:absoluteerror" (MAE), not the more common squared error, is
# a deliberate robustness choice discovered necessary during implementation:
# Stage 1's SARIMA diverged for at least one district/fold (Vavuniya,
# 2010 weeks 42-51 - forecasts reached ~30 million against an actual mean of
# ~6 cases/week; see EXPERIMENT_LOG.md M1-002), producing a residual on the
# order of -30,000,000. Because Stage 2 pools ALL districts into one
# squared-error-loss model, that single extreme value dominated the loss
# globally and corrupted predicted residuals for every OTHER district too
# (e.g. Colombo's predicted residuals, which should be O(100), blew up to
# O(1,000,000)). MAE's gradient is bounded (+-1 regardless of error
# magnitude), so one extreme outlier in the pooled training set can no
# longer dominate the fit - this is a general robustness property of the
# pooled-model architecture, not a one-off patch for this single outlier.
XGB_BASE_PARAMS = dict(
    objective="reg:absoluteerror",
    max_depth=3,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    min_child_weight=5,
    tree_method="hist",
    enable_categorical=True,
    random_state=42,
)
XGB_EVAL_METRIC = "mae"
MAX_ESTIMATORS = 500
EARLY_STOPPING_ROUNDS = 30
FIXED_N_ESTIMATORS_NO_EARLY_STOP = 100
# Fold 2 trains on fold 1 alone - too little history to further carve out an
# internal early-stopping validation slice, so it uses a fixed tree count
# instead. Folds >= 3 have >= 2 prior folds and use the most recent prior
# fold as that slice.
MIN_FOLD_FOR_EARLY_STOPPING = 3


# ---------------------------------------------------------------------------
# Fold boundary reconstruction (must exactly match Stage 1's folds)
# ---------------------------------------------------------------------------

def compute_fold_boundaries(
    weekly_df: pd.DataFrame, districts: list[str] = DISTRICTS
) -> tuple[dict[int, set], dict[int, set], set, set]:
    """Reconstruct Stage 1's exact per-district fold + holdout boundaries by
    re-running `validation.py`'s (unchanged) fold generator with the same
    defaults `baseline_sarima.py` used. This is deterministic, so it
    reproduces the identical folds without needing to touch Stage 1's code.

    Returns `(fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys)`
    where each `fold_*_keys` value is a `set[(District, Year, Week)]`.
    """
    fold_train_keys: dict[int, set] = {i: set() for i in range(1, N_FOLDS + 1)}
    fold_val_keys: dict[int, set] = {i: set() for i in range(1, N_FOLDS + 1)}
    pre_holdout_keys: set = set()
    holdout_keys: set = set()

    for district in districts:
        series = get_district_series(weekly_df, district, value_col="Number_of_Cases")

        for fold_id, (train_index, val_index) in enumerate(
            generate_walk_forward_folds(
                series,
                holdout_years=HOLDOUT_YEARS,
                min_train_years=MIN_TRAIN_YEARS,
                weeks_per_year=WEEKS_PER_YEAR,
            ),
            start=1,
        ):
            fold_train_keys[fold_id].update((district, int(y), int(w)) for y, w in train_index)
            fold_val_keys[fold_id].update((district, int(y), int(w)) for y, w in val_index)

        holdout = get_holdout_series(series, holdout_years=HOLDOUT_YEARS, weeks_per_year=WEEKS_PER_YEAR)
        pre_holdout = series.iloc[: len(series) - len(holdout)]
        pre_holdout_keys.update((district, int(y), int(w)) for y, w in pre_holdout.index)
        holdout_keys.update((district, int(y), int(w)) for y, w in holdout.index)

    n_folds_found = sum(1 for k in fold_train_keys if fold_train_keys[k])
    if n_folds_found != N_FOLDS:
        raise ValueError(
            f"Expected {N_FOLDS} walk-forward folds, reconstructed {n_folds_found} - "
            "fold boundaries no longer match Stage 1's assumptions."
        )

    return fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys


# ---------------------------------------------------------------------------
# Fold-scoped climate anomalies (Feature Group 3)
# ---------------------------------------------------------------------------

def build_fold_scoped_anomalies(
    feature_df: pd.DataFrame,
    fold_train_keys: dict[int, set],
    fold_val_keys: dict[int, set],
    pre_holdout_keys: set,
    holdout_keys: set,
) -> pd.DataFrame:
    """Compute rainfall/temperature/humidity anomalies for every validation +
    holdout row, using EACH ROW'S OWN originating fold's training window
    (identical to the window Stage 1 used to produce that row's residual).

    Returns one row per (District, Year, Week) validation/holdout row with
    columns `rainfall_anomaly`, `temperature_anomaly`, `humidity_anomaly`.
    """
    df = feature_df.copy()
    keys = list(zip(df["District"], df["Year"].astype(int), df["Week"].astype(int)))
    df["_key"] = keys

    anomaly_frames: list[pd.DataFrame] = []

    for fold_id in range(1, N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_id])
        if not train_mask.any():
            logger.warning("Fold %d has no training rows for anomaly computation - skipping.", fold_id)
            continue
        anomalies = compute_fold_climate_anomalies(df, train_mask)
        val_mask = df["_key"].isin(fold_val_keys[fold_id])
        sub = anomalies.loc[val_mask].copy()
        sub["District"] = df.loc[val_mask, "District"].to_numpy()
        sub["Year"] = df.loc[val_mask, "Year"].to_numpy()
        sub["Week"] = df.loc[val_mask, "Week"].to_numpy()
        anomaly_frames.append(sub)

    train_mask = df["_key"].isin(pre_holdout_keys)
    anomalies = compute_fold_climate_anomalies(df, train_mask)
    val_mask = df["_key"].isin(holdout_keys)
    sub = anomalies.loc[val_mask].copy()
    sub["District"] = df.loc[val_mask, "District"].to_numpy()
    sub["Year"] = df.loc[val_mask, "Year"].to_numpy()
    sub["Week"] = df.loc[val_mask, "Week"].to_numpy()
    anomaly_frames.append(sub)

    combined = pd.concat(anomaly_frames, ignore_index=True)
    return combined[["District", "Year", "Week", "rainfall_anomaly", "temperature_anomaly", "humidity_anomaly"]]


# ---------------------------------------------------------------------------
# Residual lags (Feature Group 5) - leakage-safe, gap-aware construction
# ---------------------------------------------------------------------------

def build_residual_lags(weekly_df: pd.DataFrame, predictions_df: pd.DataFrame) -> pd.DataFrame:
    """Leakage-safe `residual_lag_1/2`: reindex each district's out-of-sample
    residual onto the FULL weekly calendar (not just the sparse validation +
    holdout rows) before taking `shift(1)/shift(2)`.

    This matters because of a real, previously undocumented structural gap:
    Stage 1's 14 walk-forward folds only cover weeks
    [initial 3-year window .. fold 14's validation end] - the ~26 weeks
    between fold 14's validation end and the holdout block's start (per
    district) are used as SARIMA training data for the holdout fit but were
    NEVER scored out-of-sample, so they have no residual value. A naive
    `shift(1)` computed only over the concatenated validation+holdout rows
    (ignoring this gap) would incorrectly treat fold 14's last residual as
    "1 week ago" for the holdout block's first row - actually ~26 weeks
    stale. Reindexing onto the full calendar first makes `shift` correctly
    produce NaN across this gap (and at each district's series start, before
    Stage 1's initial training window ends) rather than silently pulling in
    a stale value. NaNs are left as-is for XGBoost's native missing-value
    handling - not fabricated.
    """
    calendar = weekly_df[["District", "Year", "Week"]].copy()
    residuals = predictions_df[["District", "Year", "Week", "residual"]]
    merged = calendar.merge(residuals, on=["District", "Year", "Week"], how="left")
    merged = merged.sort_values(["District", "Year", "Week"]).reset_index(drop=True)

    grouped = merged.groupby("District")["residual"]
    merged["residual_lag_1"] = grouped.shift(1)
    merged["residual_lag_2"] = grouped.shift(2)

    return merged[["District", "Year", "Week", "residual_lag_1", "residual_lag_2"]]


# ---------------------------------------------------------------------------
# Assemble the full Stage 2 working table
# ---------------------------------------------------------------------------

def assemble_stage2_table() -> pd.DataFrame:
    weekly_df = pd.read_csv(
        MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    feature_df = pd.read_csv(
        MODULE1_STAGE2_FEATURE_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    predictions_df = pd.read_csv(MODULE1_SARIMA_PREDICTIONS_PATH)

    # fold_id is a mixed int/"holdout" string column on disk - read back as
    # object/string dtype by pandas. Keep the original for output fidelity,
    # add a numeric helper column (NaN for "holdout") for internal fold logic.
    predictions_df["fold_id_numeric"] = pd.to_numeric(predictions_df["fold_id"], errors="coerce")

    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(weekly_df)
    anomalies = build_fold_scoped_anomalies(feature_df, fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys)
    residual_lags = build_residual_lags(weekly_df, predictions_df)

    feature_subset = feature_df[["District", "Year", "Week"] + FOLD_AGNOSTIC_FEATURE_COLUMNS]

    stage2 = predictions_df.merge(feature_subset, on=["District", "Year", "Week"], how="left")
    stage2 = stage2.merge(anomalies, on=["District", "Year", "Week"], how="left")
    stage2 = stage2.merge(residual_lags, on=["District", "Year", "Week"], how="left")

    n_missing_features = stage2[FEATURE_COLUMNS[:-1]].isna().all(axis=1).sum()
    if n_missing_features:
        logger.warning("%d rows have entirely missing features after merge - check join keys.", n_missing_features)

    return stage2


# ---------------------------------------------------------------------------
# XGBoost fit/predict helpers
# ---------------------------------------------------------------------------

def _prepare_xy(df_subset: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    X = df_subset[FEATURE_COLUMNS].copy()
    X["District"] = pd.Categorical(X["District"], categories=DISTRICTS)
    y = df_subset[TARGET_COL].to_numpy(dtype=float)
    return X, y


def _trainable_mask(stage2_df: pd.DataFrame) -> pd.Series:
    """Rows usable as XGBoost training/early-stopping-validation targets:
    not `is_imputed`, AND have a non-NaN `residual` (target). The latter
    guards against Stage 1's explosive-AR-root fix (`baseline_sarima.py`,
    `_has_explosive_ar_root`) - a fold whose SARIMA fit is now correctly
    flagged as failed produces `NaN` residuals for that fold, which XGBoost
    cannot accept as a training target. Previously (pre-fix) this wasn't
    needed because failed fits were rare/absent from the folds that fed
    Stage 2; it is not merely defensive now that some folds (e.g. Vavuniya
    2010, Mannar 2022) are expected to legitimately produce NaN residuals.
    """
    return (~stage2_df[IMPUTED_COL]) & (~stage2_df[TARGET_COL].isna())


def _fit_with_early_stopping(X_fit, y_fit, X_val, y_val) -> int:
    """Probe fit with early stopping to find a sensible tree count; returns
    `best_iteration + 1` (or MAX_ESTIMATORS if early stopping never
    triggered)."""
    probe = xgb.XGBRegressor(
        **XGB_BASE_PARAMS,
        n_estimators=MAX_ESTIMATORS,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        eval_metric=XGB_EVAL_METRIC,
    )
    probe.fit(X_fit, y_fit, eval_set=[(X_val, y_val)], verbose=False)
    best_iteration = getattr(probe, "best_iteration", None)
    return int(best_iteration) + 1 if best_iteration is not None else MAX_ESTIMATORS


def train_and_predict_fold(stage2_df: pd.DataFrame, fold_num: int) -> tuple[np.ndarray, bool, "xgb.XGBRegressor | None"]:
    """Train pooled XGBoost on folds `1..fold_num-1` (non-imputed rows only)
    and predict fold `fold_num`'s rows. Fold 1 is a documented no-op.
    """
    target_mask = stage2_df["fold_id_numeric"] == fold_num
    target_rows = stage2_df.loc[target_mask]
    X_target, _ = _prepare_xy(target_rows)

    if fold_num == 1:
        return np.zeros(len(target_rows)), False, None

    trainable = _trainable_mask(stage2_df)
    if fold_num < MIN_FOLD_FOR_EARLY_STOPPING:
        # fold_num == 2: only fold 1 available, too little to carve out a
        # further internal early-stopping slice.
        train_mask = (stage2_df["fold_id_numeric"] == 1) & trainable
        X_train, y_train = _prepare_xy(stage2_df.loc[train_mask])
        model = xgb.XGBRegressor(**XGB_BASE_PARAMS, n_estimators=FIXED_N_ESTIMATORS_NO_EARLY_STOP)
        model.fit(X_train, y_train)
    else:
        val_fold = fold_num - 1
        fit_mask = stage2_df["fold_id_numeric"].between(1, val_fold - 1) & trainable
        val_mask = (stage2_df["fold_id_numeric"] == val_fold) & trainable
        X_fit, y_fit = _prepare_xy(stage2_df.loc[fit_mask])
        X_val, y_val = _prepare_xy(stage2_df.loc[val_mask])
        best_n = _fit_with_early_stopping(X_fit, y_fit, X_val, y_val)

        train_mask = stage2_df["fold_id_numeric"].between(1, fold_num - 1) & trainable
        X_train, y_train = _prepare_xy(stage2_df.loc[train_mask])
        model = xgb.XGBRegressor(**XGB_BASE_PARAMS, n_estimators=best_n)
        model.fit(X_train, y_train)

    predicted = model.predict(X_target)
    return predicted, True, model


def train_and_predict_holdout(stage2_df: pd.DataFrame) -> tuple[np.ndarray, "xgb.XGBRegressor"]:
    """Train pooled XGBoost on all 14 folds' non-imputed residuals and
    predict the holdout block, carving out fold 14 as the early-stopping
    validation slice."""
    target_mask = stage2_df["split"] == "holdout"
    target_rows = stage2_df.loc[target_mask]
    X_target, _ = _prepare_xy(target_rows)

    trainable = _trainable_mask(stage2_df)
    fit_mask = stage2_df["fold_id_numeric"].between(1, N_FOLDS - 1) & trainable
    val_mask = (stage2_df["fold_id_numeric"] == N_FOLDS) & trainable
    X_fit, y_fit = _prepare_xy(stage2_df.loc[fit_mask])
    X_val, y_val = _prepare_xy(stage2_df.loc[val_mask])
    best_n = _fit_with_early_stopping(X_fit, y_fit, X_val, y_val)

    train_mask = stage2_df["fold_id_numeric"].between(1, N_FOLDS) & trainable
    X_train, y_train = _prepare_xy(stage2_df.loc[train_mask])
    model = xgb.XGBRegressor(**XGB_BASE_PARAMS, n_estimators=best_n)
    model.fit(X_train, y_train)

    predicted = model.predict(X_target)
    return predicted, model


def train_final_production_model(stage2_df: pd.DataFrame) -> "xgb.XGBRegressor":
    """Train one final model on ALL available out-of-sample residuals (14
    folds + holdout, non-imputed) for potential future live forecasting use.
    Not used for any reported metric - holdout has already served its
    reporting purpose in `train_and_predict_holdout`. Carves out the holdout
    block as the early-stopping validation slice, then refits on everything.
    """
    trainable = _trainable_mask(stage2_df)
    all_mask = (
        stage2_df["fold_id_numeric"].between(1, N_FOLDS) | (stage2_df["split"] == "holdout")
    ) & trainable

    fit_mask = stage2_df["fold_id_numeric"].between(1, N_FOLDS) & trainable
    val_mask = (stage2_df["split"] == "holdout") & trainable
    X_fit, y_fit = _prepare_xy(stage2_df.loc[fit_mask])
    X_val, y_val = _prepare_xy(stage2_df.loc[val_mask])
    best_n = _fit_with_early_stopping(X_fit, y_fit, X_val, y_val)

    X_all, y_all = _prepare_xy(stage2_df.loc[all_mask])
    model = xgb.XGBRegressor(**XGB_BASE_PARAMS, n_estimators=best_n)
    model.fit(X_all, y_all)
    return model


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

OUTPUT_COLUMNS = [
    "District", "Year", "Week", "split", "fold_id",
    "Number_of_Cases", "is_imputed", "sarima_prediction", "residual",
]


def _build_output_rows(df_subset: pd.DataFrame, predicted_residual: np.ndarray, stage2_trained: bool) -> pd.DataFrame:
    out = df_subset[OUTPUT_COLUMNS].copy()
    out["predicted_residual"] = predicted_residual
    out["stage2_trained"] = stage2_trained
    return out


def _stage2_own_metrics(predictions_df: pd.DataFrame) -> pd.DataFrame:
    """Per-district, per-fold (+ per-district aggregate) RMSE/MAE/sMAPE of
    `predicted_residual` vs the actual SARIMA residual - a diagnostic on how
    well Stage 2 predicts the error itself. MASE is intentionally NOT
    computed here (its seasonal-naive scale assumes a single ordered
    per-district time series, which doesn't have a clean meaning for a
    pooled residual-of-a-residual prediction task) - the primary,
    decision-relevant evaluation (Stage-1-only vs Stage-1+Stage-2 accuracy
    against actual case counts, including MASE) lives in `combine.py`.
    """
    rows = []
    for district, district_df in predictions_df.groupby("District"):
        fold_maes = []
        for fold_id, fold_df in district_df.groupby("fold_id"):
            mask = ~fold_df["is_imputed"].to_numpy()
            row = {
                "District": district,
                "fold_id": fold_id,
                "stage2_trained": bool(fold_df["stage2_trained"].iloc[0]),
                "rmse": rmse(fold_df["residual"], fold_df["predicted_residual"], mask=mask),
                "mae": mae(fold_df["residual"], fold_df["predicted_residual"], mask=mask),
                "smape": smape(fold_df["residual"], fold_df["predicted_residual"], mask=mask),
                "n_obs_scored": int(mask.sum()),
                "n_obs_total": int(len(fold_df)),
            }
            rows.append(row)
            if fold_id != "holdout" and not np.isnan(row["mae"]):
                fold_maes.append(row["mae"])

        rows.append(
            {
                "District": district,
                "fold_id": "validation_aggregate",
                "stage2_trained": True,
                "rmse": float("nan"),
                "mae": float(np.median(fold_maes)) if fold_maes else float("nan"),
                "smape": float("nan"),
                "n_obs_scored": int((~district_df.loc[district_df["split"] == "validation", "is_imputed"]).sum()),
                "n_obs_total": int((district_df["split"] == "validation").sum()),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_stage2_pipeline() -> pd.DataFrame:
    logger.info("Assembling Stage 2 feature table (residuals + features + fold-scoped anomalies + residual lags)...")
    stage2_df = assemble_stage2_table()

    MODULE1_XGBOOST_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MODULE1_XGBOOST_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

    output_frames: list[pd.DataFrame] = []

    fold1_rows = stage2_df.loc[stage2_df["fold_id_numeric"] == 1]
    output_frames.append(_build_output_rows(fold1_rows, np.zeros(len(fold1_rows)), stage2_trained=False))
    logger.info("Fold 1: no-op (no prior residual data) - %d rows, predicted_residual=0.", len(fold1_rows))

    for fold_num in range(2, N_FOLDS + 1):
        predicted, trained, model = train_and_predict_fold(stage2_df, fold_num)
        target_rows = stage2_df.loc[stage2_df["fold_id_numeric"] == fold_num]
        output_frames.append(_build_output_rows(target_rows, predicted, trained))
        if model is not None:
            model.save_model(str(MODULE1_XGBOOST_MODELS_DIR / f"fold_{fold_num}.json"))
        logger.info("Fold %d: trained on folds 1-%d, predicted %d rows.", fold_num, fold_num - 1, len(target_rows))

    predicted_holdout, holdout_model = train_and_predict_holdout(stage2_df)
    holdout_rows = stage2_df.loc[stage2_df["split"] == "holdout"]
    output_frames.append(_build_output_rows(holdout_rows, predicted_holdout, stage2_trained=True))
    holdout_model.save_model(str(MODULE1_XGBOOST_MODELS_DIR / "holdout.json"))
    logger.info("Holdout: trained on all %d folds, predicted %d rows.", N_FOLDS, len(holdout_rows))

    predictions_df = pd.concat(output_frames, ignore_index=True)
    predictions_df.to_csv(MODULE1_XGBOOST_PREDICTIONS_PATH, index=False)
    logger.info("Wrote %d Stage 2 prediction rows to %s.", len(predictions_df), MODULE1_XGBOOST_PREDICTIONS_PATH)

    logger.info("Training final production model on all available out-of-sample residuals...")
    final_model = train_final_production_model(stage2_df)
    final_model.save_model(str(MODULE1_XGBOOST_FINAL_MODEL_PATH))

    importance = final_model.get_booster().get_score(importance_type="gain")
    importance_df = (
        pd.DataFrame({"feature": list(importance.keys()), "gain": list(importance.values())})
        .sort_values("gain", ascending=False)
        .reset_index(drop=True)
    )
    # Features never split on are absent from get_score() - report them
    # explicitly at zero rather than silently omitting them.
    missing = set(FEATURE_COLUMNS) - set(importance_df["feature"])
    if missing:
        importance_df = pd.concat(
            [importance_df, pd.DataFrame({"feature": sorted(missing), "gain": 0.0})], ignore_index=True
        )
    importance_df.to_csv(MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH, index=False)

    metrics_df = _stage2_own_metrics(predictions_df)
    metrics_df.to_csv(MODULE1_XGBOOST_METRICS_PATH, index=False)

    logger.info(
        "Stage 2 complete: predictions -> %s | final model -> %s | feature importance -> %s | metrics -> %s",
        MODULE1_XGBOOST_PREDICTIONS_PATH,
        MODULE1_XGBOOST_FINAL_MODEL_PATH,
        MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH,
        MODULE1_XGBOOST_METRICS_PATH,
    )
    return predictions_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_stage2_pipeline()
