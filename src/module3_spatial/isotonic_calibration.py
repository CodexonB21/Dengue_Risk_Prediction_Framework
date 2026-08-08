"""Stage 2 via CALIBRATION, not covariate regression - a genuinely different
compensation mechanism from the RF (`compensation_model.py`), borrowed from
Module 2's own Stage 2 (Platt/isotonic calibration of Stage 1's raw score,
`module_2_classification/MODULE_CONTEXT.md`) and adapted to Module 3's
continuous regression setting.

Motivating diagnostic (scratchpad check, not committed as a script): binning
each model's predicted score into deciles and comparing mean actual cases
vs. mean predicted score per decile showed every model - even the official
RF - systematically UNDER-predicts in its own lowest-predicted-risk decile:
actual cases run 57% (RF) to 139% (naive persistence) higher than predicted
there. This is a real, exploitable bias in the SHAPE of the score-to-outcome
relationship, independent of any climate/demographic covariate - exactly what
a monotonic recalibration curve (isotonic regression) is built to fix,
without needing to explain WHY the bias exists.

Two calibration targets tested here (both use ZERO covariates - only the
score being calibrated and the actual case count):

1. Calibrate Risk_0 directly (Stage 1's own score) - the closest structural
   analogue to Module 2's Stage 1 -> Stage 2 calibration pipeline: a pure
   calibration-only alternative to the RF, not combined with it.
2. Calibrate the official RF's own output - tests whether the RF's
   REMAINING systematic bias (after its own covariate-based correction) can
   be fixed by a calibration layer on top, the same way Module 2 calibrates
   Stage 1's raw probability rather than trying to re-engineer Stage 1
   itself.

Uses sklearn.isotonic.IsotonicRegression (the same primitive Module 2's own
isotonic Stage 2 calibrator uses), fit OUT-OF-FOLD via the SAME 5 spatial
K-means CV folds `compensation_model.py` already builds - a district's
calibrated prediction always comes from a curve fit on the other 4 folds'
districts, never on itself, matching the RF's own out-of-fold discipline.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_ISOTONIC_CALIBRATION_BOOTSTRAP_PATH,
    MODULE3_ISOTONIC_CALIBRATION_DECILE_PATH,
    MODULE3_ISOTONIC_CALIBRATION_PATH,
    MODULE3_METRICS_DIR,
)
from src.module3_spatial.blended_persistence_rf import bootstrap_ci_diff, per_week_metric_table  # noqa: E402
from src.module3_spatial.compensation_model import build_spatial_folds  # noqa: E402
from src.module3_spatial.hotspot_ranking_evaluation import (  # noqa: E402
    MODEL_PERSISTENCE,
    MODEL_RF,
    MODEL_STAGE1,
    build_model_predictions,
    compute_weekly_rank_metrics,
)

logger = logging.getLogger(__name__)

MODEL_CALIBRATED_STAGE1 = "Calibrated Risk_0 (isotonic, no covariates)"
MODEL_CALIBRATED_RF = "Calibrated RF output (isotonic, no covariates)"
N_DECILES = 10


def _fit_metrics(pred: np.ndarray, actual: np.ndarray) -> dict:
    return {
        "corr": float(np.corrcoef(pred, actual)[0, 1]),
        "mae": float(np.mean(np.abs(actual - pred))),
        "rmse": float(np.sqrt(np.mean((actual - pred) ** 2))),
    }


# ---------------------------------------------------------------------------
# Decile bias diagnostic, persisted (the scratchpad check, promoted into a
# committed metric so the motivation for this script is reproducible, not
# just asserted).
# ---------------------------------------------------------------------------

def decile_bias_table(predictions: pd.DataFrame, model_cols: list[str]) -> pd.DataFrame:
    rows = []
    for col in model_cols:
        sub = predictions[["Number_of_Cases", col]].copy()
        sub = sub[sub[col] > 0]
        sub["decile"] = pd.qcut(sub[col], N_DECILES, labels=False, duplicates="drop")
        summary = sub.groupby("decile").agg(
            n=("Number_of_Cases", "size"),
            mean_actual=("Number_of_Cases", "mean"),
            mean_predicted=(col, "mean"),
        )
        summary["ratio_actual_over_predicted"] = summary["mean_actual"] / summary["mean_predicted"]
        summary.insert(0, "model", col)
        rows.append(summary.reset_index())
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------------------
# Out-of-fold isotonic calibration
# ---------------------------------------------------------------------------

def out_of_fold_isotonic_calibrate(df: pd.DataFrame, folds_df: pd.DataFrame, score_col: str) -> np.ndarray:
    fold_assignment = df[["District"]].merge(folds_df, on="District", how="left")["spatial_fold"]
    if fold_assignment.isna().any():
        raise ValueError("Some districts missing spatial_fold assignment.")
    fold_assignment = fold_assignment.to_numpy()

    score = df[score_col].to_numpy(dtype=float)
    actual = df["Number_of_Cases"].to_numpy(dtype=float)
    calibrated = np.empty(len(df))

    for fold_id in np.unique(fold_assignment):
        test_mask = fold_assignment == fold_id
        train_mask = ~test_mask

        iso = IsotonicRegression(out_of_bounds="clip", increasing=True)
        iso.fit(score[train_mask], actual[train_mask])
        calibrated[test_mask] = iso.predict(score[test_mask])
        logger.info(
            "Fold %d (%s): calibration curve fit on %d rows, applied to %d held-out rows.",
            fold_id, score_col, int(train_mask.sum()), int(test_mask.sum()),
        )

    return calibrated


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_isotonic_calibration() -> tuple[pd.DataFrame, pd.DataFrame]:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    predictions = build_model_predictions()
    folds_df = build_spatial_folds()

    decile_df = decile_bias_table(predictions, [MODEL_STAGE1, MODEL_RF, MODEL_PERSISTENCE])
    decile_df.to_csv(MODULE3_ISOTONIC_CALIBRATION_DECILE_PATH, index=False)
    logger.info("Decile bias table (motivating diagnostic):\n%s", decile_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    predictions[MODEL_CALIBRATED_STAGE1] = out_of_fold_isotonic_calibrate(predictions, folds_df, MODEL_STAGE1)
    predictions[MODEL_CALIBRATED_RF] = out_of_fold_isotonic_calibrate(predictions, folds_df, MODEL_RF)

    actual = predictions["Number_of_Cases"].to_numpy(dtype=float)
    model_cols = [MODEL_STAGE1, MODEL_PERSISTENCE, MODEL_RF, MODEL_CALIBRATED_STAGE1, MODEL_CALIBRATED_RF]

    comparison = pd.DataFrame([
        {"model": m, **_fit_metrics(predictions[m].to_numpy(dtype=float), actual)}
        for m in model_cols
    ])

    rank_metrics = compute_weekly_rank_metrics(predictions, model_cols)
    rank_agg = rank_metrics.groupby("model")[["spearman_rho", "precision_at_3", "precision_at_5"]].mean()
    comparison = comparison.merge(rank_agg, on="model", how="left")
    comparison.to_csv(MODULE3_ISOTONIC_CALIBRATION_PATH, index=False)

    logger.info(
        "Stage 1 / persistence / RF vs. both calibrated variants:\n%s",
        comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"),
    )

    # Stress test: paired week-level bootstrap, calibrated RF vs. the two
    # models it is meant to improve on (official RF and naive persistence) -
    # same discipline as blended_persistence_rf.py's stress test, reused
    # directly rather than re-implemented.
    mae_weekly = per_week_metric_table(predictions, [MODEL_RF, MODEL_PERSISTENCE, MODEL_CALIBRATED_RF, MODEL_CALIBRATED_STAGE1], metric="mae")
    p5_weekly = rank_metrics.pivot(index=["Year", "Week"], columns="model", values="precision_at_5").reset_index()
    rho_weekly = rank_metrics.pivot(index=["Year", "Week"], columns="model", values="spearman_rho").reset_index()

    comparisons = [
        ("MAE", mae_weekly, MODEL_CALIBRATED_RF, MODEL_RF),
        ("MAE", mae_weekly, MODEL_CALIBRATED_RF, MODEL_PERSISTENCE),
        ("MAE", mae_weekly, MODEL_CALIBRATED_STAGE1, MODEL_PERSISTENCE),
        ("precision_at_5", p5_weekly, MODEL_CALIBRATED_RF, MODEL_RF),
        ("precision_at_5", p5_weekly, MODEL_CALIBRATED_RF, MODEL_PERSISTENCE),
        ("spearman_rho", rho_weekly, MODEL_CALIBRATED_RF, MODEL_RF),
        ("spearman_rho", rho_weekly, MODEL_CALIBRATED_RF, MODEL_PERSISTENCE),
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
    bootstrap_df.to_csv(MODULE3_ISOTONIC_CALIBRATION_BOOTSTRAP_PATH, index=False)
    logger.info("Week-level paired bootstrap (95%% CI):\n%s", bootstrap_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    return comparison, bootstrap_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_isotonic_calibration()
