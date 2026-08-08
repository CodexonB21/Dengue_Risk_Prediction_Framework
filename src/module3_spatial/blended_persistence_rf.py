"""Blend the official Stage 2 RF's final prediction with naive persistence's
final prediction (EXPERIMENT_LOG.md M3-013 candidate) - a different mechanism
from the already-rejected M3-011 stacking attempt, which changed the RF's
TRAINING TARGET (`residual_rescaled - residual_rescaled_lag_1`) and failed on
every metric.

Here, both models are left exactly as already built and validated
(`compensation_model.py`'s RF, `persistence_baseline.py`'s naive predictor);
only their two already-computed FINAL predictions are mixed:

    Risk_blend = w * Risk_RF + (1 - w) * Risk_persistence

Motivation: M3-010/M3-012 established persistence and the RF have different
error profiles - persistence wins on typical-case MAE and rank/precision@k,
the RF wins on RMSE and outlier/clipping control. A convex blend has a real
chance of beating BOTH on MAE (by pulling partway from persistence's
sometimes-severe overshoots) while keeping most of the RF's RMSE advantage -
something neither pure model achieves alone. This may also simply fail, like
M3-011 - reported honestly either way.

Weight selection is kept genuinely out-of-fold: for each of the same 5
spatial K-means folds `compensation_model.py` already uses, the best `w` (by
training-fold MAE) is grid-searched on the OTHER 4 folds only, then applied
to the held-out fold - the same out-of-fold discipline the RF itself uses,
not a single global w fit and reported on the same data it is evaluated on.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_BLENDED_PERSISTENCE_RF_BOOTSTRAP_PATH,
    MODULE3_BLENDED_PERSISTENCE_RF_FOLD_BREAKDOWN_PATH,
    MODULE3_BLENDED_PERSISTENCE_RF_PATH,
    MODULE3_BLENDED_PERSISTENCE_RF_REPWEEKS_PATH,
    MODULE3_BLENDED_PERSISTENCE_RF_WEIGHTS_PATH,
    MODULE3_METRICS_DIR,
)
from src.module3_spatial.compensation_model import build_spatial_folds  # noqa: E402
from src.module3_spatial.hotspot_ranking_evaluation import (  # noqa: E402
    MODEL_PERSISTENCE,
    MODEL_RF,
    MODEL_STAGE1,
    build_model_predictions,
    compute_weekly_rank_metrics,
    representative_week_breakout,
)

logger = logging.getLogger(__name__)

MODEL_BLEND = "Blended (w*RF + (1-w)*persistence)"
WEIGHT_GRID = np.round(np.linspace(0.0, 1.0, 41), 3)  # step 0.025


def _mae(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - pred)))


def _fit_metrics(pred: np.ndarray, actual: np.ndarray) -> dict:
    return {
        "corr": float(np.corrcoef(pred, actual)[0, 1]),
        "mae": _mae(pred, actual),
        "rmse": float(np.sqrt(np.mean((actual - pred) ** 2))),
    }


def best_weight_by_mae(rf_pred: np.ndarray, persistence_pred: np.ndarray, actual: np.ndarray) -> float:
    maes = [
        _mae(w * rf_pred + (1 - w) * persistence_pred, actual)
        for w in WEIGHT_GRID
    ]
    return float(WEIGHT_GRID[int(np.argmin(maes))])


def out_of_fold_blend(df: pd.DataFrame, folds_df: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    fold_assignment = df[["District"]].merge(folds_df, on="District", how="left")["spatial_fold"]
    if fold_assignment.isna().any():
        raise ValueError("Some districts missing spatial_fold assignment.")
    fold_assignment = fold_assignment.to_numpy()

    actual = df["Number_of_Cases"].to_numpy(dtype=float)
    rf_pred = df[MODEL_RF].to_numpy(dtype=float)
    persistence_pred = df[MODEL_PERSISTENCE].to_numpy(dtype=float)

    blended = np.empty(len(df))
    weight_rows = []

    for fold_id in np.unique(fold_assignment):
        test_mask = fold_assignment == fold_id
        train_mask = ~test_mask

        w = best_weight_by_mae(rf_pred[train_mask], persistence_pred[train_mask], actual[train_mask])
        blended[test_mask] = w * rf_pred[test_mask] + (1 - w) * persistence_pred[test_mask]

        weight_rows.append({
            "fold": int(fold_id),
            "best_w": w,
            "n_train_rows": int(train_mask.sum()),
            "n_test_rows": int(test_mask.sum()),
        })
        logger.info("Fold %d: best w (selected on other 4 folds) = %.3f", fold_id, w)

    return blended, pd.DataFrame(weight_rows)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_blended_persistence_rf() -> tuple[pd.DataFrame, pd.DataFrame]:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    predictions = build_model_predictions()
    folds_df = build_spatial_folds()

    blended, weights_df = out_of_fold_blend(predictions, folds_df)
    predictions = predictions.copy()
    predictions[MODEL_BLEND] = blended

    actual = predictions["Number_of_Cases"].to_numpy(dtype=float)
    comparison = pd.DataFrame([
        {"model": MODEL_STAGE1, **_fit_metrics(predictions[MODEL_STAGE1].to_numpy(dtype=float), actual)},
        {"model": MODEL_PERSISTENCE, **_fit_metrics(predictions[MODEL_PERSISTENCE].to_numpy(dtype=float), actual)},
        {"model": MODEL_RF, **_fit_metrics(predictions[MODEL_RF].to_numpy(dtype=float), actual)},
        {"model": MODEL_BLEND, **_fit_metrics(blended, actual)},
    ])

    rank_metrics = compute_weekly_rank_metrics(predictions, [MODEL_PERSISTENCE, MODEL_RF, MODEL_BLEND])
    rank_agg = rank_metrics.groupby("model")[["spearman_rho", "precision_at_3", "precision_at_5"]].mean()
    comparison = comparison.merge(rank_agg, on="model", how="left")

    comparison.to_csv(MODULE3_BLENDED_PERSISTENCE_RF_PATH, index=False)
    weights_df.to_csv(MODULE3_BLENDED_PERSISTENCE_RF_WEIGHTS_PATH, index=False)

    logger.info("Per-fold optimal weights:\n%s", weights_df.to_string(index=False))
    logger.info(
        "Blend vs. persistence vs. RF vs. Stage 1 (MAE/RMSE + rank metrics):\n%s",
        comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"),
    )
    logger.info("Comparison written to %s.", MODULE3_BLENDED_PERSISTENCE_RF_PATH)
    logger.info("Fold weights written to %s.", MODULE3_BLENDED_PERSISTENCE_RF_WEIGHTS_PATH)

    return comparison, weights_df


# ---------------------------------------------------------------------------
# Stress test (before any promotion): is the blend's aggregate win driven by
# one fold or a handful of weeks, or does it hold broadly? Checked directly,
# not assumed - the same discipline every other Module 3 finding has required
# before being trusted (M3-009's reproducibility check, M3-010/011's honest
# null results).
# ---------------------------------------------------------------------------

BOOTSTRAP_SEED = 42
N_BOOTSTRAP = 2000


def per_fold_breakdown(predictions: pd.DataFrame, folds_df: pd.DataFrame, model_cols: list[str]) -> pd.DataFrame:
    """MAE/RMSE per spatial fold (row-level - a fold IS a set of whole
    districts, so this partitions cleanly). Rank metrics (Spearman/
    precision@k) are NOT broken down by fold: each fold has only ~5
    districts, so "top-3 of 5" is a different, much weaker statement than
    "top-3 of 25" and would not be a fair like-for-like comparison.
    """
    merged = predictions.merge(folds_df, on="District", how="left")
    rows = []
    for fold_id, group in merged.groupby("spatial_fold"):
        actual = group["Number_of_Cases"].to_numpy(dtype=float)
        for model in model_cols:
            pred = group[model].to_numpy(dtype=float)
            rows.append({
                "fold": int(fold_id), "model": model, "n_rows": len(group),
                **_fit_metrics(pred, actual),
            })
    return pd.DataFrame(rows)


def per_week_metric_table(predictions: pd.DataFrame, model_cols: list[str], metric: str = "mae") -> pd.DataFrame:
    """Per-(Year, Week) MAE for each model - the row-level analogue of
    `compute_weekly_rank_metrics`'s per-week Spearman/precision@k, so both
    can be paired into the same bootstrap below."""
    def _week_metric(g: pd.DataFrame) -> pd.Series:
        actual = g["Number_of_Cases"].to_numpy(dtype=float)
        out = {}
        for m in model_cols:
            pred = g[m].to_numpy(dtype=float)
            out[m] = np.mean(np.abs(pred - actual)) if metric == "mae" else np.sqrt(np.mean((pred - actual) ** 2))
        return pd.Series(out)

    return predictions.groupby(["Year", "Week"]).apply(_week_metric, include_groups=False).reset_index()


def bootstrap_ci_diff(per_week_df: pd.DataFrame, model_a: str, model_b: str, seed: int = BOOTSTRAP_SEED, n_boot: int = N_BOOTSTRAP) -> dict:
    """Paired week-level bootstrap (same resampled weeks used for both
    models each draw, preserving the pairing) for mean(model_a) -
    mean(model_b). If the resulting 95% CI straddles 0, the point estimate's
    sign is not distinguishable from noise at this sample size."""
    rng = np.random.default_rng(seed)
    a = per_week_df[model_a].to_numpy(dtype=float)
    b = per_week_df[model_b].to_numpy(dtype=float)
    n = len(a)
    draws = rng.integers(0, n, size=(n_boot, n))
    diffs = a[draws].mean(axis=1) - b[draws].mean(axis=1)
    point = float(np.mean(a) - np.mean(b))
    ci_low, ci_high = np.percentile(diffs, [2.5, 97.5])
    win_rate = float(np.mean(a < b) if a.mean() < b.mean() else np.mean(a > b))
    return {"point_diff": point, "ci_low": float(ci_low), "ci_high": float(ci_high)}


def run_stress_test(predictions: pd.DataFrame, folds_df: pd.DataFrame, rank_metrics: pd.DataFrame) -> dict:
    model_cols = [MODEL_PERSISTENCE, MODEL_RF, MODEL_BLEND]

    fold_df = per_fold_breakdown(predictions, folds_df, model_cols)
    fold_df.to_csv(MODULE3_BLENDED_PERSISTENCE_RF_FOLD_BREAKDOWN_PATH, index=False)
    logger.info("Per-fold MAE/RMSE breakdown:\n%s", fold_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    mae_weekly = per_week_metric_table(predictions, model_cols, metric="mae")
    p5_weekly = rank_metrics.pivot(index=["Year", "Week"], columns="model", values="precision_at_5").reset_index()
    rho_weekly = rank_metrics.pivot(index=["Year", "Week"], columns="model", values="spearman_rho").reset_index()

    comparisons = [
        ("MAE", mae_weekly, MODEL_BLEND, MODEL_PERSISTENCE, "lower_better"),
        ("MAE", mae_weekly, MODEL_BLEND, MODEL_RF, "lower_better"),
        ("precision_at_5", p5_weekly, MODEL_BLEND, MODEL_PERSISTENCE, "higher_better"),
        ("precision_at_5", p5_weekly, MODEL_BLEND, MODEL_RF, "higher_better"),
        ("spearman_rho", rho_weekly, MODEL_BLEND, MODEL_PERSISTENCE, "higher_better"),
        ("spearman_rho", rho_weekly, MODEL_BLEND, MODEL_RF, "higher_better"),
    ]

    bootstrap_rows = []
    for metric_name, table, model_a, model_b, direction in comparisons:
        ci = bootstrap_ci_diff(table, model_a, model_b)
        a_vals, b_vals = table[model_a].to_numpy(dtype=float), table[model_b].to_numpy(dtype=float)
        blend_wins = float(np.mean(a_vals < b_vals) if direction == "lower_better" else np.mean(a_vals > b_vals))
        bootstrap_rows.append({
            "metric": metric_name, "comparison": f"{model_a} vs. {model_b}",
            "point_diff (blend - other)": ci["point_diff"], "ci_low": ci["ci_low"], "ci_high": ci["ci_high"],
            "pct_weeks_blend_better": round(100 * blend_wins, 1),
        })

    bootstrap_df = pd.DataFrame(bootstrap_rows)
    bootstrap_df.to_csv(MODULE3_BLENDED_PERSISTENCE_RF_BOOTSTRAP_PATH, index=False)
    logger.info(
        "Week-level paired bootstrap (95%% CI, %d resamples), + %% of weeks blend is strictly better:\n%s",
        N_BOOTSTRAP, bootstrap_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"),
    )

    rep_df = representative_week_breakout(rank_metrics, predictions)
    rep_df.to_csv(MODULE3_BLENDED_PERSISTENCE_RF_REPWEEKS_PATH, index=False)
    logger.info("Representative-week breakout (incl. blend):\n%s", rep_df.to_string(index=False))

    return {"fold_breakdown": fold_df, "bootstrap": bootstrap_df, "representative_weeks": rep_df}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    comparison_df, weights_df = run_blended_persistence_rf()

    _predictions = build_model_predictions()
    _folds_df = build_spatial_folds()
    _blended, _ = out_of_fold_blend(_predictions, _folds_df)
    _predictions[MODEL_BLEND] = _blended
    _rank_metrics = compute_weekly_rank_metrics(_predictions, [MODEL_PERSISTENCE, MODEL_RF, MODEL_BLEND])

    run_stress_test(_predictions, _folds_df, _rank_metrics)
