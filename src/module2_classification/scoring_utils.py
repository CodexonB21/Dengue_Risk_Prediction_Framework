"""Shared helpers for Module 2 live and forward operational scoring."""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from src.config import (
    DISTRICTS,
    MODULE2_BASELINE_FINAL_MODEL_PATH,
    MODULE2_BASELINE_METRICS_PATH,
    MODULE2_RISK_THRESHOLD_SCAN_PATH,
    MODULE2_STAGE2_FINAL_MODEL_PATH,
    MODULE2_STAGE2_METRICS_PATH,
)
from src.module2_classification.baseline_classifier import (
    CATEGORICAL_FEATURE_COLUMNS,
    NUMERIC_FEATURE_COLUMNS,
    attach_fold_anomalies,
)
from src.module2_classification.compensation_model import (  # noqa: E402
    LOGIT_EPS,
    LOGIT_RESIDUAL_ALL_COLUMNS,
    _logit,
    _prepare_tree_stage2_xy,
    _sigmoid,
)
from src.module2_classification.feature_engineering import build_module2_feature_table
from src.module2_classification.risk_thresholds import assign_risk_tier, select_thresholds


def official_stage1_model() -> str:
    metrics = pd.read_csv(MODULE2_BASELINE_METRICS_PATH)
    selected = metrics.loc[metrics["selected"], "model"].unique()
    if len(selected) != 1:
        raise ValueError(f"Expected exactly one selected Stage 1 model, found {selected!r}.")
    return str(selected[0])


def official_stage2_architecture() -> str:
    metrics = pd.read_csv(MODULE2_STAGE2_METRICS_PATH)
    selected = metrics.loc[metrics["selected"], "architecture"].unique()
    if len(selected) != 1:
        raise ValueError(f"Expected exactly one selected Stage 2 architecture, found {selected!r}.")
    return str(selected[0])


def load_stage1_model(model_name: str):
    path = MODULE2_BASELINE_FINAL_MODEL_PATH.with_suffix(".json" if model_name == "xgboost" else ".joblib")
    if model_name == "xgboost":
        model = xgb.XGBClassifier()
        model.load_model(str(path))
        return model
    return joblib.load(path)


def load_stage2_model(architecture: str):
    path = MODULE2_STAGE2_FINAL_MODEL_PATH.with_suffix(
        ".json" if architecture in ("stacked_xgboost", "logit_residual") else ".joblib"
    )
    if architecture == "stacked_xgboost":
        model = xgb.XGBClassifier()
        model.load_model(str(path))
        return model
    if architecture == "logit_residual":
        model = xgb.XGBRegressor()
        model.load_model(str(path))
        return model
    return joblib.load(path)


def load_production_thresholds() -> tuple[float, float]:
    if not MODULE2_RISK_THRESHOLD_SCAN_PATH.exists():
        raise FileNotFoundError(
            f"{MODULE2_RISK_THRESHOLD_SCAN_PATH} not found - run Module 2 training pipeline first."
        )
    scan_df = pd.read_csv(MODULE2_RISK_THRESHOLD_SCAN_PATH)
    return select_thresholds(scan_df)


def build_scoring_feature_table() -> pd.DataFrame:
    features = build_module2_feature_table()
    train_mask = pd.Series(True, index=features.index)
    return attach_fold_anomalies(features, train_mask)


def prepare_stage1_X(target_df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    cols = NUMERIC_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS
    X = target_df[cols].copy()
    if model_name == "xgboost":
        X["District"] = pd.Categorical(X["District"], categories=DISTRICTS)
    return X


def score_feature_rows(
    target_df: pd.DataFrame,
    stage1_model,
    stage1_model_name: str,
    stage2_model,
    stage2_architecture: str,
) -> pd.DataFrame:
    X1 = prepare_stage1_X(target_df, stage1_model_name)
    predicted_probability = stage1_model.predict_proba(X1)[:, 1]

    if stage2_architecture == "stacked_xgboost":
        raise NotImplementedError(
            "Live/forward scoring for 'stacked_xgboost' is not implemented "
            "(isotonic/Platt are the only architectures ever selected)."
        )

    if stage2_architecture == "logit_residual":
        stage2_df = target_df.copy()
        stage2_df["predicted_probability"] = predicted_probability
        _, X2 = _prepare_tree_stage2_xy(stage2_df, stage2_df, LOGIT_RESIDUAL_ALL_COLUMNS)
        g_pred = stage2_model.predict(X2)
        calibrated_probability = np.clip(
            _sigmoid(_logit(predicted_probability, eps=LOGIT_EPS) + g_pred),
            0.0,
            1.0,
        )
    else:
        calibrated_probability = stage2_model.predict(predicted_probability)

    out = target_df.copy()
    out["predicted_probability"] = predicted_probability
    out["calibrated_probability"] = np.clip(calibrated_probability, 0.0, 1.0)
    out["feature_completeness_pct"] = (
        target_df[NUMERIC_FEATURE_COLUMNS].notna().mean(axis=1) * 100
    ).round(1)
    return out


def apply_risk_tiers(
    scored: pd.DataFrame,
    alert_threshold: float,
    high_threshold: float,
    *,
    tau_ramp: float | None = None,
    rho: float | None = None,
) -> pd.DataFrame:
    calibrated = scored["calibrated_probability"].to_numpy(dtype=float)
    scored = scored.copy()
    if tau_ramp is not None and rho is not None and {"cases_lag_1", "cases_lag_2"}.issubset(scored.columns):
        from src.module2_classification.alert_rules import apply_ramp_alert_rule

        scored["alert_flag"] = apply_ramp_alert_rule(
            calibrated,
            scored["cases_lag_1"].to_numpy(dtype=float),
            scored["cases_lag_2"].to_numpy(dtype=float),
            tau=alert_threshold,
            tau_ramp=tau_ramp,
            rho=rho,
        )
    else:
        scored["alert_flag"] = calibrated >= alert_threshold
    scored["risk_tier"] = assign_risk_tier(calibrated, alert_threshold, high_threshold)
    return scored
