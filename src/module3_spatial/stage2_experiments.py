"""Stage 2 experimental ablation (2026-08-05) - tests 3 improvement
theories raised after M3-005/M3-006 established that the official model
(alpha=0.05) shows a null/negative aggregate-fit result and that NO alpha
in {1.0, 0.3, 0.15, 0.05} beats Stage 1 alone on out-of-fold accuracy.

**OUTCOME (2026-08-05, same day, EXPERIMENT_LOG.md M3-008)**: theory 1
(own-district residual lags) WAS promoted to the official pipeline -
`compensation_model.py`'s `STAGE2_FEATURE_COLUMNS`, `alpha=1.0`. Theories 2
(winsorizing) and 3 (leave-one-out CV) were NOT promoted - the ablation
below shows they changed almost nothing on their own. This script is
deliberately left UNCHANGED after promotion (still a standalone,
non-official ablation - see below) so its numbers remain the frozen,
reproducible record of the finding that justified the promotion, separate
from the officially promoted code in `compensation_model.py`/
`iterative_loop.py` itself.

**Standalone exploratory script - does NOT modify the official Stage 1/2
pipeline** (`kde_baseline.py`, `compensation_model.py`, `iterative_loop.py`,
`evaluate.py`, or any of their committed CSV/model outputs). Findings are
reported here for review before any promotion to official status.

Three theories tested, individually and combined:

1. **Own-district residual memory.** Every one of Stage 2's 16 features is
   either static per-district (population/elevation - 58.5% of feature
   importance) or current-week climate. The RF has zero information about
   a district's OWN recent burden trend, unlike Module 1's
   `residual_lag_1/2`. Tested by adding `residual_rescaled_lag_1/2/3/4`
   (own-district, chronologically prior weeks only - no leakage, same
   `.shift()` pattern `feature_engineering.py::compute_lag_features`
   already uses for climate).
2. **Outlier-dominated target.** M3-004 found alpha had to shrink to 0.05
   specifically because the raw out-of-fold prediction error is dominated
   by a handful of extreme district-weeks (the 2017/2026 outbreaks).
   Tested by winsorizing the TRAINING target at the 1st/99th percentile
   (fit on the winsorized target, but always EVALUATED against the true,
   un-winsorized residual/case counts - winsorizing is a training-time
   choice, not a ground-truth redefinition). `criterion="absolute_error"`
   was considered and rejected for this ablation on cost grounds - it is
   documented to be 10-30x slower to train than `squared_error` in
   scikit-learn, which would make a 5-config sweep impractically slow.
3. **CV granularity.** The official 5-fold spatial K-means CV holds out
   ~5 districts per fold. Tested against leave-one-district-out (25
   folds, one district held out at a time) to see whether the 5-fold
   estimate is itself noisy from having so few held-out districts per
   fold, independent of any feature/target change.

Alpha is NOT a training hyperparameter here - for a SINGLE-PASS model
(mirroring `compensation_model.py`'s own single-pass design, not
`iterative_loop.py`'s iterative one, where the target changes every
iteration), alpha is a pure post-hoc scalar applied to one fixed
out-of-fold `predicted_residual` array. A full alpha grid is therefore
evaluated per config at near-zero extra cost, unlike M3-006's
`alpha_sweep.py` (which needed to retrain per iteration).

Two metrics reported per config, at every alpha in the grid:
(a) residual-prediction accuracy: MAE/RMSE of `predicted_residual` against
    the TRUE `residual_rescaled` (this is what `rf_stage2_metrics.csv`
    reports at alpha's implicit value of 1.0 for the official config) -
    answers "did this change make the RF a better residual predictor at
    all", independent of alpha.
(b) final-fit accuracy: MAE/RMSE/corr of `Risk_0 + alpha * predicted_residual`
    against actual `Number_of_Cases` - the number that actually matters,
    and the one to compare against Stage 1 alone (MAE=20.4667, the
    official `results_summary.txt` reference line).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE3_METRICS_DIR, MODULE3_STAGE2_EXPERIMENTS_PATH  # noqa: E402
from src.module3_spatial.compensation_model import (  # noqa: E402
    FEATURE_COLUMNS,
    RF_PARAMS,
    build_spatial_folds,
    load_training_table,
    rescale_kde_baseline,
)

logger = logging.getLogger(__name__)

RESIDUAL_LAG_WEEKS = [1, 2, 3, 4]
RESIDUAL_LAG_COLUMNS = [f"residual_rescaled_lag_{lag}" for lag in RESIDUAL_LAG_WEEKS]
ALPHA_GRID = [1.0, 0.5, 0.3, 0.15, 0.05]
WINSORIZE_PERCENTILES = (1.0, 99.0)
LOO_CV_SEED = 42  # unused (LOO has no randomness in fold assignment) - kept for RF_PARAMS consistency


# ---------------------------------------------------------------------------
# Theory 1: own-district residual lag features
# ---------------------------------------------------------------------------

def add_residual_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["District", "Week_Start_Date"]).reset_index(drop=True)
    grouped = df.groupby("District")
    for lag, col in zip(RESIDUAL_LAG_WEEKS, RESIDUAL_LAG_COLUMNS):
        df[col] = grouped["residual_rescaled"].shift(lag)
    return df


# ---------------------------------------------------------------------------
# Theory 2: winsorized training target
# ---------------------------------------------------------------------------

def winsorize(series: pd.Series, percentiles: tuple[float, float] = WINSORIZE_PERCENTILES) -> pd.Series:
    lo, hi = np.percentile(series.to_numpy(dtype=float), percentiles)
    return series.clip(lo, hi)


# ---------------------------------------------------------------------------
# Theory 3: leave-one-district-out CV (25 folds)
# ---------------------------------------------------------------------------

def build_loo_folds(districts: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"District": sorted(districts), "spatial_fold": range(len(districts))})


# ---------------------------------------------------------------------------
# Generic out-of-fold predictor (reused across every config)
# ---------------------------------------------------------------------------

def out_of_fold_predict(
    df: pd.DataFrame, folds_df: pd.DataFrame, feature_cols: list[str], target: np.ndarray,
) -> np.ndarray:
    fold_assignment = df[["District"]].merge(folds_df, on="District", how="left")["spatial_fold"]
    if fold_assignment.isna().any():
        raise ValueError("Some districts missing spatial_fold assignment.")
    fold_assignment = fold_assignment.to_numpy()

    predicted = np.empty(len(df))
    X = df[feature_cols]

    for fold_id in np.unique(fold_assignment):
        test_mask = fold_assignment == fold_id
        train_mask = ~test_mask
        model = RandomForestRegressor(**RF_PARAMS)
        model.fit(X.loc[train_mask], target[train_mask])
        predicted[test_mask] = model.predict(X.loc[test_mask])

    return predicted


def evaluate_config(
    label: str,
    df: pd.DataFrame,
    folds_df: pd.DataFrame,
    feature_cols: list[str],
    fit_target: np.ndarray,
    true_residual: np.ndarray,
    risk_0: np.ndarray,
    number_of_cases: np.ndarray,
) -> pd.DataFrame:
    logger.info("Running config '%s' (%d features, %d folds, %d rows)...",
                label, len(feature_cols), folds_df["spatial_fold"].nunique(), len(df))
    predicted_residual = out_of_fold_predict(df, folds_df, feature_cols, fit_target)

    resid_mae = mean_absolute_error(true_residual, predicted_residual)
    resid_rmse = float(np.sqrt(mean_squared_error(true_residual, predicted_residual)))

    rows = []
    for alpha in ALPHA_GRID:
        risk = risk_0 + alpha * predicted_residual
        rows.append({
            "config": label,
            "alpha": alpha,
            "residual_mae": resid_mae,
            "residual_rmse": resid_rmse,
            "corr": float(np.corrcoef(risk, number_of_cases)[0, 1]),
            "mae": float(np.mean(np.abs(number_of_cases - risk))),
            "rmse": float(np.sqrt(np.mean((number_of_cases - risk) ** 2))),
        })
    result = pd.DataFrame(rows)
    logger.info(
        "Config '%s': residual_mae=%.3f | best final MAE=%.3f at alpha=%.2f",
        label, resid_mae, result["mae"].min(), result.loc[result["mae"].idxmin(), "alpha"],
    )
    return result


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_stage2_experiments() -> pd.DataFrame:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_training_table()
    df = rescale_kde_baseline(df)
    df = add_residual_lag_features(df)
    # A single consistent row set across every config (fair comparison) -
    # residual_lag_4's NaN rows are the same first-4-weeks-per-district as
    # the climate lag_4 NaN rows load_training_table() already dropped, so
    # this only removes rows genuinely missing residual history, not new
    # ones beyond what the official pipeline already excludes.
    before = len(df)
    df = df.dropna(subset=RESIDUAL_LAG_COLUMNS).reset_index(drop=True)
    logger.info("Dropped %d additional rows lacking residual_lag_4 history (%d remain).", before - len(df), len(df))

    number_of_cases = df["Number_of_Cases"].to_numpy(dtype=float)
    risk_0 = df["kde_baseline_rescaled"].to_numpy(dtype=float)
    residual_rescaled = df["residual_rescaled"].to_numpy(dtype=float)
    winsorized_target = winsorize(df["residual_rescaled"]).to_numpy(dtype=float)

    spatial_folds = build_spatial_folds()
    loo_folds = build_loo_folds(df["District"].unique().tolist())

    configs = [
        ("baseline_5fold", FEATURE_COLUMNS, spatial_folds, residual_rescaled),
        ("plus_residual_lags_5fold", FEATURE_COLUMNS + RESIDUAL_LAG_COLUMNS, spatial_folds, residual_rescaled),
        ("winsorized_target_5fold", FEATURE_COLUMNS, spatial_folds, winsorized_target),
        ("loo_25fold", FEATURE_COLUMNS, loo_folds, residual_rescaled),
        (
            "combo_lags_winsor_loo",
            FEATURE_COLUMNS + RESIDUAL_LAG_COLUMNS,
            loo_folds,
            winsorized_target,
        ),
    ]

    all_results = []
    for label, feature_cols, folds_df, fit_target in configs:
        result = evaluate_config(
            label, df, folds_df, feature_cols, fit_target, residual_rescaled, risk_0, number_of_cases,
        )
        all_results.append(result)

    stage1_alone = {
        "corr": float(np.corrcoef(risk_0, number_of_cases)[0, 1]),
        "mae": float(np.mean(np.abs(number_of_cases - risk_0))),
        "rmse": float(np.sqrt(np.mean((number_of_cases - risk_0) ** 2))),
    }
    logger.info(
        "Stage 1 alone (reference line): corr=%.4f mae=%.3f rmse=%.3f",
        stage1_alone["corr"], stage1_alone["mae"], stage1_alone["rmse"],
    )

    result = pd.concat(all_results, ignore_index=True)
    result.to_csv(MODULE3_STAGE2_EXPERIMENTS_PATH, index=False)
    logger.info("Stage 2 experiments written to %s.", MODULE3_STAGE2_EXPERIMENTS_PATH)

    best = result.loc[result["mae"].idxmin()]
    logger.info(
        "Best overall: config='%s' alpha=%.2f MAE=%.3f (Stage 1 alone MAE=%.3f, %s).",
        best["config"], best["alpha"], best["mae"], stage1_alone["mae"],
        "IMPROVEMENT" if best["mae"] < stage1_alone["mae"] else "still worse",
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_stage2_experiments()
