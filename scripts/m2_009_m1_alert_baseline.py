"""M2-009: Module 1-derived outbreak alert baseline vs Module 2 production.

Tests the defense objection: "Module 2 is redundant if Module 1 already
forecasts cases — just threshold the forecast."

Compares holdout alert/discrimination metrics for:
  - M2 production (isotonic calibrated probability, tau=0.14)
  - M1 fair baseline (final_prediction > same epidemic threshold as M2 label)
  - M1 naive baseline (final_prediction > fixed 100 cases)
  - Oracle upper bound (actual cases > epidemic threshold — label definition)

Read-only: uses existing production CSVs; does not retrain models.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    EPIDEMIC_THRESHOLD_K,
    MODULE2_METRICS_DIR,
    MODULE2_PROCESSED_DIR,
    MODULE2_RISK_TIER_PREDICTIONS_PATH,
    MODULE1_FINAL_PREDICTIONS_PATH,
)
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.labels import compute_epidemic_threshold_labels  # noqa: E402

FIXED_CASE_THRESHOLD = 100


def _load_holdout_table() -> pd.DataFrame:
    m1 = pd.read_csv(MODULE1_FINAL_PREDICTIONS_PATH, low_memory=False)
    m1 = m1[m1["split"] == "holdout"][["District", "Year", "Week", "Number_of_Cases", "final_prediction"]]

    m2 = pd.read_csv(MODULE2_RISK_TIER_PREDICTIONS_PATH, low_memory=False)
    m2 = m2[
        (m2["split"] == "holdout") & (m2["is_selected_architecture"] == True)  # noqa: E712
    ][["District", "Year", "Week", "label", "calibrated_probability", "alert_flag", "architecture"]]

    weekly = pd.read_csv(MODULE2_PROCESSED_DIR / "weekly_modeling_table.csv")
    labeled = compute_epidemic_threshold_labels(weekly)
    thresh = labeled[["District", "Year", "Week", "historical_mean", "historical_sd"]].drop_duplicates(
        subset=["District", "Year", "Week"]
    )

    df = m1.merge(m2, on=["District", "Year", "Week"], how="inner")
    df = df.merge(thresh, on=["District", "Year", "Week"], how="left")
    df["epidemic_threshold"] = df["historical_mean"] + EPIDEMIC_THRESHOLD_K * df["historical_sd"]
    return df


def _metric_row(name: str, y_true: np.ndarray, score: np.ndarray, alert: np.ndarray) -> dict:
    return {
        "rule": name,
        "pr_auc": evaluate.pr_auc(y_true, score),
        "recall": evaluate.recall(y_true, alert),
        "precision": evaluate.precision(y_true, alert),
        "f2": evaluate.fbeta_score(y_true, alert, beta=2),
        "n_alerts": int(alert.sum()),
        "n_scored": int(len(y_true)),
        "n_outbreaks": int(y_true.sum()),
        "prevalence": float(y_true.mean()) if len(y_true) else float("nan"),
    }


def run_m2_009_evaluation() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = _load_holdout_table()
    scored = df[df["label"].notna()].copy()
    y = scored["label"].to_numpy(dtype=float)

    epidemic_threshold = scored["epidemic_threshold"].to_numpy(dtype=float)
    m1_pred = scored["final_prediction"].to_numpy(dtype=float)
    m1_excess = m1_pred - epidemic_threshold

    # Pulled from the data rather than hardcoded, so this label can never go
    # stale the way "isotonic, tau=0.14" silently did after Decision 047's
    # RF tuning flipped the official architecture and threshold.
    architecture = str(scored["architecture"].iloc[0])
    alerted = scored.loc[scored["alert_flag"].astype(bool), "calibrated_probability"]
    tau_display = float(alerted.min()) if not alerted.empty else float("nan")
    m2_label = f"M2 production ({architecture}, tau~={tau_display:.3f})"

    rows = [
        _metric_row(
            m2_label,
            y,
            scored["calibrated_probability"].to_numpy(dtype=float),
            scored["alert_flag"].to_numpy(dtype=float),
        ),
        _metric_row(
            f"M1 forecast > epidemic threshold (k={EPIDEMIC_THRESHOLD_K})",
            y,
            m1_pred,
            (m1_pred > epidemic_threshold).astype(float),
        ),
        _metric_row(
            "M1 excess score (pred - threshold) [PR-AUC only]",
            y,
            m1_excess,
            (m1_excess > 0).astype(float),
        ),
        _metric_row(
            "Oracle: actual cases > epidemic threshold",
            y,
            scored["Number_of_Cases"].to_numpy(dtype=float),
            (scored["Number_of_Cases"] > epidemic_threshold).astype(float),
        ),
        _metric_row(
            f"M1 forecast > fixed {FIXED_CASE_THRESHOLD} cases (naive)",
            y,
            m1_pred,
            (m1_pred > FIXED_CASE_THRESHOLD).astype(float),
        ),
    ]
    comparison = pd.DataFrame(rows)

    scored = scored.assign(
        m1_epidemic_alert=(scored["final_prediction"] > scored["epidemic_threshold"]).astype(int),
        m2_alert=scored["alert_flag"].astype(int),
        high_m1_pred=scored["final_prediction"] >= scored["final_prediction"].quantile(0.90),
    )
    discordant = pd.DataFrame([
        {
            "metric": "true_outbreaks_caught_by_m2_not_m1_threshold",
            "count": int(((scored.m2_alert == 1) & (scored.m1_epidemic_alert == 0) & (scored.label == 1)).sum()),
        },
        {
            "metric": "true_outbreaks_caught_by_m1_threshold_not_m2",
            "count": int(((scored.m1_epidemic_alert == 1) & (scored.m2_alert == 0) & (scored.label == 1)).sum()),
        },
        {
            "metric": "false_m1_epidemic_threshold_alerts",
            "count": int(((scored.m1_epidemic_alert == 1) & (scored.label == 0)).sum()),
        },
        {
            "metric": "false_m2_alerts",
            "count": int(((scored.m2_alert == 1) & (scored.label == 0)).sum()),
        },
        {
            "metric": "top_decile_m1_pred_not_outbreak",
            "count": int(((scored.high_m1_pred) & (scored.label == 0)).sum()),
        },
    ])

    top_decile_by_district = (
        scored.loc[(scored.high_m1_pred) & (scored.label == 0), "District"]
        .value_counts()
        .reset_index()
    )
    top_decile_by_district.columns = ["District", "top_decile_pred_not_outbreak_count"]

    m2_row = comparison[comparison["rule"].str.startswith("M2 production")].iloc[0]
    m1_row = comparison[comparison["rule"].str.startswith("M1 forecast > epidemic")].iloc[0]
    summary = pd.DataFrame([{
        "experiment": "m2_009",
        "holdout_n_scored": int(m2_row["n_scored"]),
        "holdout_n_outbreaks": int(m2_row["n_outbreaks"]),
        "holdout_prevalence": m2_row["prevalence"],
        "m2_pr_auc": m2_row["pr_auc"],
        "m2_recall": m2_row["recall"],
        "m2_precision": m2_row["precision"],
        "m2_f2": m2_row["f2"],
        "m1_threshold_pr_auc": m1_row["pr_auc"],
        "m1_threshold_recall": m1_row["recall"],
        "m1_threshold_precision": m1_row["precision"],
        "m1_f2": m1_row["f2"],
        "pr_auc_ratio_m2_over_m1_threshold": m2_row["pr_auc"] / m1_row["pr_auc"] if m1_row["pr_auc"] else np.nan,
        "m2_catches_outbreaks_m1_misses": int(discordant.loc[0, "count"]),
        "m1_catches_outbreaks_m2_misses": int(discordant.loc[1, "count"]),
    }])

    out_dir = MODULE2_METRICS_DIR
    comparison_path = out_dir / "m2_009_m1_alert_baseline.csv"
    summary_path = out_dir / "m2_009_summary.csv"
    discordant_path = out_dir / "m2_009_discordant_counts.csv"
    district_path = out_dir / "m2_009_top_decile_false_high_by_district.csv"

    comparison.to_csv(comparison_path, index=False)
    summary.to_csv(summary_path, index=False)
    discordant.to_csv(discordant_path, index=False)
    top_decile_by_district.to_csv(district_path, index=False)

    print("=== M2-009 M1-derived alert baseline vs Module 2 (holdout) ===")
    print(comparison.to_string(index=False))
    print("\nDiscordant counts:")
    print(discordant.to_string(index=False))
    print(f"\nWrote {comparison_path}")
    print(f"Wrote {summary_path}")
    return comparison, summary


if __name__ == "__main__":
    run_m2_009_evaluation()
