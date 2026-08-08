"""Stage 2 via a RELATIVE (not absolute) residual target - motivated by a
direct diagnostic of Stage 1's raw error (scratchpad check, results
committed here for reproducibility):

    corr(Risk_0, |Number_of_Cases - Risk_0|)                = 0.7795
    corr(log(Risk_0), log(|Number_of_Cases - Risk_0| + 1))  = 0.8106

Stage 1's error is strongly HETEROSCEDASTIC - error magnitude scales with
predicted magnitude. Every prior Module 3 compensation attempt
(`compensation_model.py`'s RF, `persistence_baseline.py`, `blended_
persistence_rf.py`, `isotonic_calibration.py`) modeled the ABSOLUTE residual
directly, which lets the handful of huge-magnitude outbreak weeks (Colombo/
Gampaha, 2017) dominate the target's scale and effectively drown out
whatever structure exists at ordinary case volumes.

This models the RELATIVE residual instead:

    relative_residual = (Number_of_Cases - kde_baseline_rescaled) /
                         (kde_baseline_rescaled + 1)

(the "+1" avoids division by zero at Risk_0=0, same convention as the
scratchpad diagnostic). Reconstructing the absolute prediction from a
relative-residual prediction is EXACT, not approximate, by construction:

    Risk_reconstructed = Risk_0 + predicted_relative_residual * (Risk_0 + 1)

A second diagnostic (also committed here) ruled OUT a spatial-spillover
angle before this was built: a Queen-contiguous neighbor's residual lagged
one week correlates -0.30 with a district's own current residual, but that
drops to a negligible partial correlation of 0.03 once the district's OWN
residual_lag_1 is accounted for - neighboring districts' errors add
essentially nothing beyond what a district's own recent error already says,
so no neighbor-lag feature is included here.

Two candidates, evaluated on the SAME final (reconstructed, absolute-scale)
corr/MAE/RMSE + rank metrics every prior Module 3 comparison has used, for a
fair like-for-like comparison against Stage 1 / naive persistence / the
official RF / the blend:

1. "Relative persistence" (no model): predicted_relative_residual =
   relative_residual_lag_1 (own-district, one week back) - the relative-scale
   analogue of `persistence_baseline.py`'s absolute-scale naive predictor.
2. "RF on relative residual": same RF_PARAMS/STAGE2_FEATURE_COLUMNS as the
   official model, same 5-fold spatial CV, only the TARGET changes (relative,
   not absolute) - isolates whether the heteroscedasticity fix itself is
   what matters, independent of any other change.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_METRICS_DIR,
    MODULE3_RELATIVE_RESIDUAL_BOOTSTRAP_PATH,
    MODULE3_RELATIVE_RESIDUAL_COMPARISON_PATH,
)
from src.module3_spatial.blended_persistence_rf import bootstrap_ci_diff, per_week_metric_table  # noqa: E402
from src.module3_spatial.compensation_model import RF_PARAMS, STAGE2_FEATURE_COLUMNS, build_spatial_folds, prepare_training_table  # noqa: E402
from src.module3_spatial.hotspot_ranking_evaluation import (  # noqa: E402
    MODEL_PERSISTENCE,
    MODEL_RF,
    MODEL_STAGE1,
    build_model_predictions,
    compute_weekly_rank_metrics,
)

logger = logging.getLogger(__name__)

MODEL_RELATIVE_PERSISTENCE = "Relative persistence (no model)"
MODEL_RELATIVE_RF = "RF on relative residual"
RELATIVE_LAG_WEEKS = [1, 2, 3, 4]
RELATIVE_LAG_COLUMNS = [f"relative_residual_lag_{lag}" for lag in RELATIVE_LAG_WEEKS]


def _fit_metrics(pred: np.ndarray, actual: np.ndarray) -> dict:
    return {
        "corr": float(np.corrcoef(pred, actual)[0, 1]),
        "mae": float(np.mean(np.abs(actual - pred))),
        "rmse": float(np.sqrt(np.mean((actual - pred) ** 2))),
    }


# ---------------------------------------------------------------------------
# Step 1: relative residual target + its own lag features
# ---------------------------------------------------------------------------

def add_relative_residual_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["District", "Week_Start_Date"]).reset_index(drop=True)
    df["relative_residual"] = (df["Number_of_Cases"] - df["kde_baseline_rescaled"]) / (df["kde_baseline_rescaled"] + 1)
    grouped = df.groupby("District")
    for lag, col in zip(RELATIVE_LAG_WEEKS, RELATIVE_LAG_COLUMNS):
        df[col] = grouped["relative_residual"].shift(lag)
    return df


# ---------------------------------------------------------------------------
# Step 2: out-of-fold RF on the relative target (same spatial CV machinery)
# ---------------------------------------------------------------------------

def out_of_fold_relative_rf(df: pd.DataFrame, folds_df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    fold_assignment = df[["District"]].merge(folds_df, on="District", how="left")["spatial_fold"]
    if fold_assignment.isna().any():
        raise ValueError("Some districts missing spatial_fold assignment.")
    fold_assignment = fold_assignment.to_numpy()

    X = df[feature_cols]
    target = df["relative_residual"].to_numpy(dtype=float)
    predicted = np.empty(len(df))

    for fold_id in np.unique(fold_assignment):
        test_mask = fold_assignment == fold_id
        train_mask = ~test_mask
        model = RandomForestRegressor(**RF_PARAMS)
        model.fit(X.loc[train_mask], target[train_mask])
        predicted[test_mask] = model.predict(X.loc[test_mask])

    return predicted


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_relative_residual_compensation() -> tuple[pd.DataFrame, pd.DataFrame]:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    df = prepare_training_table()
    df = add_relative_residual_features(df)
    df = df.dropna(subset=RELATIVE_LAG_COLUMNS).reset_index(drop=True)
    logger.info("Training table after relative-lag NaN drop: %d rows.", len(df))

    folds_df = build_spatial_folds()

    risk_0 = df["kde_baseline_rescaled"].to_numpy(dtype=float)
    actual = df["Number_of_Cases"].to_numpy(dtype=float)

    # Candidate 1: relative persistence (no model)
    pred_rel_persistence = df["relative_residual_lag_1"].to_numpy(dtype=float)
    risk_relative_persistence = np.clip(risk_0 + pred_rel_persistence * (risk_0 + 1), 0.0, None)

    # Candidate 2: RF on the relative target
    feature_cols = STAGE2_FEATURE_COLUMNS + RELATIVE_LAG_COLUMNS
    pred_rel_rf = out_of_fold_relative_rf(df, folds_df, feature_cols=feature_cols)
    risk_relative_rf = np.clip(risk_0 + pred_rel_rf * (risk_0 + 1), 0.0, None)

    predictions = build_model_predictions()
    df_out = df[["District", "Year", "Week"]].copy()
    df_out[MODEL_RELATIVE_PERSISTENCE] = risk_relative_persistence
    df_out[MODEL_RELATIVE_RF] = risk_relative_rf

    predictions = predictions.merge(df_out, on=["District", "Year", "Week"], how="inner")
    if len(predictions) != len(df_out):
        raise ValueError(
            f"Expected the merge to preserve all {len(df_out)} rows, got {len(predictions)}."
        )

    actual_full = predictions["Number_of_Cases"].to_numpy(dtype=float)
    model_cols = [MODEL_STAGE1, MODEL_PERSISTENCE, MODEL_RF, MODEL_RELATIVE_PERSISTENCE, MODEL_RELATIVE_RF]

    comparison = pd.DataFrame([
        {"model": m, **_fit_metrics(predictions[m].to_numpy(dtype=float), actual_full)}
        for m in model_cols
    ])

    rank_metrics = compute_weekly_rank_metrics(predictions, model_cols)
    rank_agg = rank_metrics.groupby("model")[["spearman_rho", "precision_at_3", "precision_at_5"]].mean()
    comparison = comparison.merge(rank_agg, on="model", how="left")
    comparison.to_csv(MODULE3_RELATIVE_RESIDUAL_COMPARISON_PATH, index=False)

    logger.info(
        "Relative-residual candidates vs. established benchmarks:\n%s",
        comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"),
    )

    # Stress test: paired week-level bootstrap vs. naive persistence and the
    # official RF, same discipline as blended_persistence_rf.py /
    # isotonic_calibration.py.
    mae_weekly = per_week_metric_table(predictions, [MODEL_PERSISTENCE, MODEL_RF, MODEL_RELATIVE_PERSISTENCE, MODEL_RELATIVE_RF], metric="mae")
    p5_weekly = rank_metrics.pivot(index=["Year", "Week"], columns="model", values="precision_at_5").reset_index()
    rho_weekly = rank_metrics.pivot(index=["Year", "Week"], columns="model", values="spearman_rho").reset_index()

    comparisons = [
        ("MAE", mae_weekly, MODEL_RELATIVE_RF, MODEL_PERSISTENCE),
        ("MAE", mae_weekly, MODEL_RELATIVE_RF, MODEL_RF),
        ("MAE", mae_weekly, MODEL_RELATIVE_PERSISTENCE, MODEL_PERSISTENCE),
        ("precision_at_5", p5_weekly, MODEL_RELATIVE_RF, MODEL_PERSISTENCE),
        ("precision_at_5", p5_weekly, MODEL_RELATIVE_RF, MODEL_RF),
        ("spearman_rho", rho_weekly, MODEL_RELATIVE_RF, MODEL_PERSISTENCE),
        ("spearman_rho", rho_weekly, MODEL_RELATIVE_RF, MODEL_RF),
    ]
    bootstrap_rows = []
    for metric_name, table, model_a, model_b in comparisons:
        ci = bootstrap_ci_diff(table, model_a, model_b)
        lower_better = metric_name == "MAE"
        a_vals, b_vals = table[model_a].to_numpy(dtype=float), table[model_b].to_numpy(dtype=float)
        win_rate = float(np.mean(a_vals < b_vals) if lower_better else np.mean(a_vals > b_vals))
        bootstrap_rows.append({
            "metric": metric_name, "comparison": f"{model_a} vs. {model_b}",
            "point_diff (a - b)": ci["point_diff"], "ci_low": ci["ci_low"], "ci_high": ci["ci_high"],
            "pct_weeks_a_better": round(100 * win_rate, 1),
        })
    bootstrap_df = pd.DataFrame(bootstrap_rows)
    bootstrap_df.to_csv(MODULE3_RELATIVE_RESIDUAL_BOOTSTRAP_PATH, index=False)
    logger.info("Week-level paired bootstrap (95%% CI):\n%s", bootstrap_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    return comparison, bootstrap_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_relative_residual_compensation()
