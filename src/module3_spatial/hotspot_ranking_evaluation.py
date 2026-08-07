"""Companion evaluation lens for Stage 2 (EXPERIMENT_LOG.md M3-012):
does the official RF actually rank districts by hotspot risk better than
Stage 1 alone or naive persistence, independent of its absolute-error
performance (MAE/RMSE, already reported in `evaluate.py`/M3-010)?

Module 3's own scope is spatial HOTSPOT DETECTION (MODULE_CONTEXT.md's
Purpose section), not case-count regression - that is Module 1's job.
MAE/RMSE judge absolute magnitude; a model can be "wrong" on magnitude every
week while still correctly identifying which districts are the hottest.
This script adds two rank-based metrics per (Year, Week), computed
identically for all three models already compared in
`persistence_baseline.py` (Stage 1 alone, naive persistence, the official
Stage 2 RF) so the comparison is exactly like-for-like:

1. Spearman rank correlation between predicted risk and actual
   Number_of_Cases across the 25 districts that week.
2. Precision@k (k in {3, 5}): overlap between the model's top-k
   highest-risk districts and the actual top-k highest-case districts,
   divided by k.

This is a COMPANION lens, not a replacement for MAE/RMSE - reported
alongside it in results_summary.txt, not instead of it.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_HOTSPOT_RANKING_PATH,
    MODULE3_HYBRID_RISK_MAP_PATH,
    MODULE3_METRICS_DIR,
)
from src.module3_spatial.compensation_model import prepare_training_table  # noqa: E402
from src.module3_spatial.iterative_loop import SHRINKAGE_ALPHA  # noqa: E402
from src.module3_spatial.kde_baseline import select_representative_weeks  # noqa: E402

logger = logging.getLogger(__name__)

TOP_K_VALUES = (3, 5)
MODEL_STAGE1 = "Stage 1 alone (Risk_0)"
MODEL_PERSISTENCE = "Naive persistence (no model)"
MODEL_RF = "Stage 2 RF, official"


# ---------------------------------------------------------------------------
# Step 1: assemble the same 3 predictions persistence_baseline.py compares,
# on the same merged table (identical merge-and-validate guard).
# ---------------------------------------------------------------------------

def build_model_predictions(rf_risk_col: str = "Risk", rf_risk_path: Path = MODULE3_HYBRID_RISK_MAP_PATH) -> pd.DataFrame:
    df = prepare_training_table()
    hybrid = pd.read_csv(rf_risk_path)[["District", "Year", "Week", rf_risk_col]]
    merged = df.merge(hybrid, on=["District", "Year", "Week"], how="inner")
    if len(merged) != len(hybrid):
        raise ValueError(
            f"Expected the merge to preserve all {len(hybrid)} rows from {rf_risk_path}, "
            f"got {len(merged)}."
        )

    risk_0 = merged["kde_baseline_rescaled"].to_numpy(dtype=float)
    predicted_residual_persistence = merged["residual_rescaled_lag_1"].to_numpy(dtype=float)
    risk_persistence = np.clip(risk_0 + SHRINKAGE_ALPHA * predicted_residual_persistence, 0.0, None)

    out = merged[["District", "Year", "Week", "Number_of_Cases"]].copy()
    out[MODEL_STAGE1] = risk_0
    out[MODEL_PERSISTENCE] = risk_persistence
    out[MODEL_RF] = merged[rf_risk_col].to_numpy(dtype=float)
    return out


# ---------------------------------------------------------------------------
# Step 2: per-week rank metrics for one model column
# ---------------------------------------------------------------------------

def _precision_at_k(actual: pd.Series, predicted: pd.Series, k: int) -> float:
    actual_top_k = set(actual.nlargest(k).index)
    predicted_top_k = set(predicted.nlargest(k).index)
    return len(actual_top_k & predicted_top_k) / k


def compute_weekly_rank_metrics(predictions: pd.DataFrame, model_cols: list[str]) -> pd.DataFrame:
    rows = []
    for (year, week), week_df in predictions.groupby(["Year", "Week"]):
        actual = week_df.set_index("District")["Number_of_Cases"]
        if actual.var() == 0:
            # Zero-variance week (every district ties, usually all-zero-case) -
            # Spearman is undefined (divides by the input's variance); skip,
            # same precedent as kde_baseline.select_representative_weeks()
            # excluding zero-variance weeks from its own picks.
            continue

        for model_col in model_cols:
            predicted = week_df.set_index("District")[model_col]
            rho, _ = spearmanr(actual, predicted)
            row = {"Year": year, "Week": week, "model": model_col, "spearman_rho": rho}
            for k in TOP_K_VALUES:
                row[f"precision_at_{k}"] = _precision_at_k(actual, predicted, k)
            rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Step 3: aggregate (all valid weeks) + representative-week breakout
# ---------------------------------------------------------------------------

def aggregate_rank_metrics(weekly_df: pd.DataFrame) -> pd.DataFrame:
    metric_cols = ["spearman_rho"] + [f"precision_at_{k}" for k in TOP_K_VALUES]
    agg = weekly_df.groupby("model")[metric_cols].mean().reset_index()
    agg.insert(1, "n_weeks", weekly_df.groupby("model").size().to_numpy())
    return agg


def representative_week_breakout(weekly_df: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    kde_like = predictions.rename(columns={MODEL_STAGE1: "KDE_baseline"})[
        ["District", "Year", "Week", "Number_of_Cases", "KDE_baseline"]
    ]
    representative = select_representative_weeks(kde_like)

    rows = []
    for label, (year, week) in representative.items():
        subset = weekly_df[(weekly_df["Year"] == year) & (weekly_df["Week"] == week)]
        for _, r in subset.iterrows():
            rows.append({"representative_week": label, "Year": year, "Week": week, **r.drop(["Year", "Week"]).to_dict()})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_hotspot_ranking_evaluation(
    rf_risk_col: str = "Risk", rf_risk_path: Path = MODULE3_HYBRID_RISK_MAP_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    predictions = build_model_predictions(rf_risk_col=rf_risk_col, rf_risk_path=rf_risk_path)
    model_cols = [MODEL_STAGE1, MODEL_PERSISTENCE, MODEL_RF]

    weekly_df = compute_weekly_rank_metrics(predictions, model_cols)
    n_total_weeks = predictions.groupby(["Year", "Week"]).ngroups
    n_valid_weeks = weekly_df.groupby("model").size().iloc[0] if not weekly_df.empty else 0
    logger.info(
        "Computed rank metrics for %d/%d weeks per model (%d skipped as zero-variance).",
        n_valid_weeks, n_total_weeks, n_total_weeks - n_valid_weeks,
    )

    agg_df = aggregate_rank_metrics(weekly_df)
    rep_df = representative_week_breakout(weekly_df, predictions)

    weekly_df.to_csv(MODULE3_HOTSPOT_RANKING_PATH, index=False)
    logger.info("Per-week hotspot ranking metrics written to %s.", MODULE3_HOTSPOT_RANKING_PATH)
    logger.info("Aggregate hotspot ranking comparison:\n%s", agg_df.to_string(index=False))
    logger.info("Representative-week breakout:\n%s", rep_df.to_string(index=False))

    return weekly_df, agg_df, rep_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_hotspot_ranking_evaluation()
