"""Evaluate promoted production stack vs pre-promotion M1-005 / M2 baselines.

Production stack (2026-07-29):
- Module 1: additive residuals + M1-006B Feature Group 6 (default paths)
- Module 2: isotonic Stage 2, single threshold tau=0.14, no ramp rule
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
    MODULE1_COMBINED_METRICS_PATH,
    MODULE1_FINAL_PREDICTIONS_PATH,
    MODULE1_METRICS_DIR,
    MODULE2_METRICS_DIR,
    MODULE2_RISK_TIER_PREDICTIONS_PATH,
    MODULE2_STAGE2_PREDICTIONS_PATH,
)
from src.module1_forecasting.evaluate import smape  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402

BACKUP_DIR = PROJECT_ROOT / "outputs" / "metrics" / "production_promotion_backup_2026-07-29"
M1_PRE_METRICS = BACKUP_DIR / "m1_combined_metrics_pre.csv"
M1_PRE_PREDS = BACKUP_DIR / "m1_final_combined_predictions_pre.csv"
M2_PRE_STAGE2 = BACKUP_DIR / "m2_stage2_predictions_pre.csv"

M1_BASELINE_MEDIAN_MASE = 0.386
M1_BASELINE_MEDIAN_SMAPE = 35.0
M2_BASELINE_PR_AUC = 0.412
M2_BASELINE_ALERT_RECALL = 0.60
M2_BASELINE_ALERT_PRECISION = 0.338
ALERT_THRESHOLD = 0.14


def _m1_holdout_hybrid(metrics_df: pd.DataFrame) -> pd.DataFrame:
    return metrics_df[
        (metrics_df["model"] == "stage1_plus_stage2") & (metrics_df["fold_id"] == "holdout")
    ].set_index("District")


def _m1_comparison(pre_metrics: pd.DataFrame, post_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pre_h = _m1_holdout_hybrid(pre_metrics)
    post_h = _m1_holdout_hybrid(post_metrics)
    rows = []
    for district in sorted(set(pre_h.index) & set(post_h.index)):
        b, v = pre_h.loc[district], post_h.loc[district]
        mase_delta_pct = 100 * (v["mase"] - b["mase"]) / b["mase"] if b["mase"] else np.nan
        rows.append({
            "District": district,
            "pre_mase": round(b["mase"], 4),
            "post_mase": round(v["mase"], 4),
            "mase_delta_pct": round(mase_delta_pct, 2),
            "pre_smape": round(b["smape"], 2),
            "post_smape": round(v["smape"], 2),
            "smape_delta_pp": round(v["smape"] - b["smape"], 2),
            "improved_mase": v["mase"] < b["mase"],
        })
    comparison = pd.DataFrame(rows)
    summary = pd.DataFrame([{
        "module": "M1",
        "pre_median_mase": round(float(comparison["pre_mase"].median()), 4),
        "post_median_mase": round(float(comparison["post_mase"].median()), 4),
        "pre_median_smape": round(float(comparison["pre_smape"].median()), 2),
        "post_median_smape": round(float(comparison["post_smape"].median()), 2),
        "districts_improved_mase": int(comparison["improved_mase"].sum()),
        "n_districts": len(comparison),
        "vs_m1_005_baseline_median_mase": M1_BASELINE_MEDIAN_MASE,
        "vs_m1_005_baseline_median_smape": M1_BASELINE_MEDIAN_SMAPE,
    }])
    return comparison, summary


def _m2_holdout_row(stage2_df: pd.DataFrame, architecture: str = "isotonic") -> dict:
    rows = stage2_df[(stage2_df["architecture"] == architecture) & (stage2_df["split"] == "holdout")]
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


def run_evaluation() -> None:
    out_dir = MODULE1_METRICS_DIR
    m2_out = MODULE2_METRICS_DIR

    if not M1_PRE_METRICS.exists():
        raise FileNotFoundError(f"Missing pre-promotion backup: {M1_PRE_METRICS}")

    pre_m1_metrics = pd.read_csv(M1_PRE_METRICS)
    post_m1_metrics = pd.read_csv(MODULE1_COMBINED_METRICS_PATH)
    m1_cmp, m1_summary = _m1_comparison(pre_m1_metrics, post_m1_metrics)

    if M1_PRE_PREDS.exists() and MODULE1_FINAL_PREDICTIONS_PATH.exists():
        pre_preds = pd.read_csv(M1_PRE_PREDS)
        post_preds = pd.read_csv(MODULE1_FINAL_PREDICTIONS_PATH)
        for name, df in ("pre", pre_preds), ("post", post_preds):
            holdout = df[(df["split"] == "holdout") & (~df["is_imputed"])]
            m1_summary[f"{name}_pooled_smape"] = round(
                smape(holdout["Number_of_Cases"], holdout["final_prediction"]), 2
            )
        wk = lambda d: d[(d["Year"] == 2026) & d["Week"].isin([22, 23]) & (d["split"] == "holdout") & (~d["is_imputed"])]
        m1_summary["wk22_23_smape_delta_pp"] = round(
            smape(wk(post_preds)["Number_of_Cases"], wk(post_preds)["final_prediction"])
            - smape(wk(pre_preds)["Number_of_Cases"], wk(pre_preds)["final_prediction"]),
            2,
        )

    m1_cmp.to_csv(out_dir / "production_stack_m1_district_comparison.csv", index=False)
    m1_summary.to_csv(out_dir / "production_stack_m1_summary.csv", index=False)

    post_m2 = pd.read_csv(MODULE2_STAGE2_PREDICTIONS_PATH)
    m2_rows = [_m2_holdout_row(post_m2, "isotonic")]
    if M2_PRE_STAGE2.exists():
        pre_m2 = pd.read_csv(M2_PRE_STAGE2)
        m2_rows.insert(0, _m2_holdout_row(pre_m2, "isotonic") | {"era": "pre_promotion"})
        for row in m2_rows[1:]:
            row["era"] = "post_promotion"
    else:
        for row in m2_rows:
            row["era"] = "post_promotion"

    m2_cmp = pd.DataFrame(m2_rows)
    post_row = m2_cmp[m2_cmp.get("era", "post_promotion") == "post_promotion"].iloc[0]
    m2_summary = pd.DataFrame([{
        "module": "M2",
        "architecture": "isotonic",
        "alert_threshold": ALERT_THRESHOLD,
        "ramp_rule": False,
        "post_pr_auc": round(post_row["pr_auc"], 4),
        "post_alert_recall": round(post_row["alert_recall_at_0.14"], 3),
        "post_alert_precision": round(post_row["alert_precision_at_0.14"], 3),
        "baseline_pr_auc": M2_BASELINE_PR_AUC,
        "baseline_alert_recall": M2_BASELINE_ALERT_RECALL,
        "baseline_alert_precision": M2_BASELINE_ALERT_PRECISION,
    }])

    if MODULE2_RISK_TIER_PREDICTIONS_PATH.exists():
        tiers = pd.read_csv(MODULE2_RISK_TIER_PREDICTIONS_PATH, low_memory=False)
        holdout_tiers = tiers[(tiers["split"] == "holdout") & (tiers["architecture"] == "isotonic")]
        m2_summary["holdout_alert_count"] = int(holdout_tiers["alert_flag"].sum())
        m2_summary["alert_threshold_used"] = ALERT_THRESHOLD

    m2_cmp.to_csv(m2_out / "production_stack_m2_holdout_comparison.csv", index=False)
    m2_summary.to_csv(m2_out / "production_stack_m2_summary.csv", index=False)

    combined = pd.concat([m1_summary.assign(stack="production"), m2_summary.assign(stack="production")], ignore_index=True)
    combined.to_csv(PROJECT_ROOT / "outputs" / "metrics" / "production_stack_evaluation_summary.csv", index=False)

    print("=== Production stack evaluation ===\n")
    print("--- Module 1 (M1-006B promoted to default paths) ---")
    print(m1_summary.to_string(index=False))
    print(f"\nDistrict comparison: {out_dir / 'production_stack_m1_district_comparison.csv'}")
    print("\n--- Module 2 (isotonic, tau=0.14, no ramp) ---")
    print(m2_cmp.to_string(index=False))
    print(f"\nSummary: {PROJECT_ROOT / 'outputs' / 'metrics' / 'production_stack_evaluation_summary.csv'}")


if __name__ == "__main__":
    run_evaluation()
