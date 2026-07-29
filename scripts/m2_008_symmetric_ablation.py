"""M2-008: Symmetric Module 1–style ablation for Module 2.

Stage 1: climate-free classifier (case history + seasonality + case-anomaly lags).
Stage 2: climate-driven stacked correction on ``predicted_probability``.

Compares holdout metrics against production (full Stage 1 + isotonic Stage 2).
Does not overwrite production artifacts.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE2_METRICS_DIR,
    MODULE2_STAGE2_PREDICTIONS_PATH,
    module2_stage1_paths,
    module2_stage2_paths,
)
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.baseline_classifier import run_stage1_pipeline  # noqa: E402
from src.module2_classification.compensation_model import (  # noqa: E402
    BASE_PROB_COL,
    PROBABILITY_LAG_COLUMNS,
    run_stage2_pipeline,
)
from src.module2_classification.feature_engineering import (  # noqa: E402
    FOLD_AWARE_FEATURE_COLUMNS,
    STAGE1_CLIMATE_FREE_FEATURE_COLUMNS,
    STAGE2_CLIMATE_COMPENSATION_FEATURE_COLUMNS,
)

VARIANT = "m2_008"
ALERT_THRESHOLD = 0.14
PRODUCTION_ISOTONIC_PR_AUC = 0.412

STAGE1_FEATURES = STAGE1_CLIMATE_FREE_FEATURE_COLUMNS + ["District"]
STACKED_CLIMATE_COLUMNS = (
    STAGE2_CLIMATE_COMPENSATION_FEATURE_COLUMNS
    + [BASE_PROB_COL]
    + PROBABILITY_LAG_COLUMNS
    + ["District"]
)

logger = logging.getLogger(__name__)


def _holdout_metrics(df: pd.DataFrame, architecture: str) -> dict:
    rows = df[(df["architecture"] == architecture) & (df["split"] == "holdout")]
    y_true = rows["label"].to_numpy(dtype=float)
    y_prob = rows["calibrated_probability"].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    alert = y_prob >= ALERT_THRESHOLD
    return {
        "architecture": architecture,
        "pr_auc": evaluate.pr_auc(y_true, y_prob, mask=mask),
        "roc_auc": evaluate.roc_auc(y_true, y_prob, mask=mask),
        "brier_skill_score": evaluate.brier_skill_score(y_true, y_prob, mask=mask),
        "alert_recall_at_0.14": evaluate.recall(y_true, alert.astype(float), mask=mask),
        "alert_precision_at_0.14": evaluate.precision(y_true, alert.astype(float), mask=mask),
        "n_obs_scored": int(mask.sum()),
    }


def _stage1_holdout_pr_auc(metrics_path: Path, official_model: str) -> float:
    metrics = pd.read_csv(metrics_path)
    row = metrics[(metrics["model"] == official_model) & (metrics["fold_id"] == "holdout")]
    return float(row["pr_auc"].iloc[0])


def run_m2_008_ablation() -> pd.DataFrame:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    stage1_paths = module2_stage1_paths(VARIANT)
    stage2_paths = module2_stage2_paths(VARIANT)

    logger.info("M2-008 Stage 1: climate-free features (%d cols)...", len(STAGE1_FEATURES))
    run_stage1_pipeline(feature_variant=VARIANT, feature_columns=STAGE1_FEATURES)

    stage1_metrics = pd.read_csv(stage1_paths["metrics"])
    official_stage1 = str(stage1_metrics.loc[stage1_metrics["selected"], "model"].iloc[0])
    stage1_holdout_pr = _stage1_holdout_pr_auc(stage1_paths["metrics"], official_stage1)
    logger.info("M2-008 Stage 1 official model=%s holdout PR-AUC=%.4f", official_stage1, stage1_holdout_pr)

    logger.info("M2-008 Stage 2: climate-only stacked correction (%d cols)...", len(STACKED_CLIMATE_COLUMNS))
    run_stage2_pipeline(
        feature_variant=VARIANT,
        baseline_predictions_path=stage1_paths["predictions"],
        stacked_feature_columns=STACKED_CLIMATE_COLUMNS,
    )

    variant_preds = pd.read_csv(stage2_paths["predictions"])
    production_preds = pd.read_csv(MODULE2_STAGE2_PREDICTIONS_PATH)

    rows = [{
        **_holdout_metrics(production_preds, "isotonic"),
        "pipeline": "production",
    }]
    for arch in ("isotonic", "platt", "stacked_xgboost"):
        if arch in variant_preds["architecture"].unique():
            row = _holdout_metrics(variant_preds, arch)
            row["pipeline"] = "symmetric_m2_008"
            rows.append(row)

    holdout = variant_preds[(variant_preds["split"] == "holdout")].drop_duplicates(
        subset=["District", "Year", "Week"]
    )
    y_true = holdout["label"].to_numpy(dtype=float)
    y_prob = holdout["stage1_predicted_probability"].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    alert = y_prob >= ALERT_THRESHOLD
    rows.append({
        "pipeline": "symmetric_m2_008",
        "architecture": "symmetric_stage1_raw",
        "pr_auc": evaluate.pr_auc(y_true, y_prob, mask=mask),
        "roc_auc": evaluate.roc_auc(y_true, y_prob, mask=mask),
        "brier_skill_score": evaluate.brier_skill_score(y_true, y_prob, mask=mask),
        "alert_recall_at_0.14": evaluate.recall(y_true, alert.astype(float), mask=mask),
        "alert_precision_at_0.14": evaluate.precision(y_true, alert.astype(float), mask=mask),
        "n_obs_scored": int(mask.sum()),
    })

    comparison = pd.DataFrame(rows)

    prod_iso = comparison[(comparison["pipeline"] == "production") & (comparison["architecture"] == "isotonic")].iloc[0]
    sym_stacked = comparison[
        (comparison["pipeline"] == "symmetric_m2_008") & (comparison["architecture"] == "stacked_xgboost")
    ]
    sym_iso = comparison[
        (comparison["pipeline"] == "symmetric_m2_008") & (comparison["architecture"] == "isotonic")
    ]
    sym_s1 = comparison[comparison["architecture"] == "symmetric_stage1_raw"].iloc[0]

    sym_stacked_row = sym_stacked.iloc[0] if not sym_stacked.empty else None
    sym_iso_row = sym_iso.iloc[0] if not sym_iso.empty else None

    stacked_beats_s1 = False
    stacked_pr_delta = np.nan
    if sym_stacked_row is not None:
        stacked_pr_delta = sym_stacked_row["pr_auc"] - sym_s1["pr_auc"]
        stacked_beats_s1 = stacked_pr_delta >= 0.02

    beats_production = False
    prod_delta = np.nan
    if sym_stacked_row is not None:
        prod_delta = sym_stacked_row["pr_auc"] - prod_iso["pr_auc"]
        beats_production = prod_delta >= 0.02

    summary = pd.DataFrame([{
        "variant": VARIANT,
        "stage1_official_model": official_stage1,
        "stage1_holdout_pr_auc": stage1_holdout_pr,
        "production_isotonic_pr_auc": prod_iso["pr_auc"],
        "symmetric_stage1_raw_pr_auc": sym_s1["pr_auc"],
        "symmetric_isotonic_pr_auc": sym_iso_row["pr_auc"] if sym_iso_row is not None else np.nan,
        "symmetric_stacked_pr_auc": sym_stacked_row["pr_auc"] if sym_stacked_row is not None else np.nan,
        "stacked_pr_auc_delta_vs_symmetric_s1": stacked_pr_delta,
        "stacked_pr_auc_delta_vs_production_isotonic": prod_delta,
        "stacked_improves_s1_by_0.02": stacked_beats_s1,
        "stacked_beats_production_isotonic": beats_production,
        "symmetric_stacked_bss": sym_stacked_row["brier_skill_score"] if sym_stacked_row is not None else np.nan,
        "symmetric_isotonic_bss": sym_iso_row["brier_skill_score"] if sym_iso_row is not None else np.nan,
    }])

    out_dir = MODULE2_METRICS_DIR
    comparison_path = out_dir / "m2_008_vs_production.csv"
    summary_path = out_dir / "m2_008_summary.csv"
    comparison.to_csv(comparison_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("=== M2-008 symmetric ablation (holdout) ===")
    print(comparison.to_string(index=False))
    print(f"\nStage 1 (climate-free) official={official_stage1} holdout PR-AUC={stage1_holdout_pr:.4f}")
    print(f"Stacked climate compensation improves Stage 1 by >=0.02 PR-AUC: {stacked_beats_s1}")
    print(f"Stacked beats production isotonic by >=0.02 PR-AUC: {beats_production}")
    print(f"Wrote {comparison_path}")
    print(f"Wrote {summary_path}")
    return comparison


if __name__ == "__main__":
    run_m2_008_ablation()
