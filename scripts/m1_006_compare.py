"""Compare M1-006A log-residual variant vs M1-005 additive baseline (holdout).

Writes ``outputs/metrics/module1/m1_006_log_vs_baseline.csv``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE1_COMBINED_METRICS_PATH, MODULE1_METRICS_DIR, module1_stage2_paths  # noqa: E402
from src.module1_forecasting.evaluate import smape  # noqa: E402

BASELINE_HOLDOUT_MASE = 0.386
BASELINE_HOLDOUT_SMAPE = 35.0
BASELINE_DISTRICTS_IMPROVED = 23


def _holdout_hybrid(metrics_df: pd.DataFrame) -> pd.DataFrame:
    return metrics_df[
        (metrics_df["model"] == "stage1_plus_stage2") & (metrics_df["fold_id"] == "holdout")
    ].set_index("District")


def main() -> None:
    baseline_path = MODULE1_COMBINED_METRICS_PATH
    variant_paths = module1_stage2_paths("log")
    variant_metrics_path = variant_paths["combined_metrics"]

    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline metrics missing: {baseline_path}")
    if not variant_metrics_path.exists():
        raise FileNotFoundError(f"Variant metrics missing: {variant_metrics_path}")

    baseline = pd.read_csv(baseline_path)
    variant = pd.read_csv(variant_metrics_path)

    base_h = _holdout_hybrid(baseline)
    var_h = _holdout_hybrid(variant)

    rows = []
    for district in sorted(set(base_h.index) & set(var_h.index)):
        b, v = base_h.loc[district], var_h.loc[district]
        mase_delta_pct = 100 * (v["mase"] - b["mase"]) / b["mase"] if b["mase"] else np.nan
        smape_delta_pp = v["smape"] - b["smape"]
        rows.append({
            "District": district,
            "baseline_mase": round(b["mase"], 4),
            "variant_mase": round(v["mase"], 4),
            "mase_delta_pct": round(mase_delta_pct, 2),
            "baseline_smape": round(b["smape"], 2),
            "variant_smape": round(v["smape"], 2),
            "smape_delta_pp": round(smape_delta_pp, 2),
            "variant_improved_mase": v["mase"] < b["mase"],
            "severely_harmed_mase": mase_delta_pct > 25 if np.isfinite(mase_delta_pct) else False,
        })

    comparison = pd.DataFrame(rows)
    n_improved = int(comparison["variant_improved_mase"].sum())
    n_severe = int(comparison["severely_harmed_mase"].sum())
    median_mase = float(comparison["variant_mase"].median())
    median_smape = float(comparison["variant_smape"].median())

    # Pooled holdout sMAPE (non-imputed rows)
    base_preds = pd.read_csv(PROJECT_ROOT / "data/processed/module1/final_combined_predictions.csv")
    var_preds = pd.read_csv(variant_paths["final_predictions"])
    holdout_mask = (base_preds["split"] == "holdout") & (~base_preds["is_imputed"])
    pooled_baseline_smape = smape(
        base_preds.loc[holdout_mask, "Number_of_Cases"],
        base_preds.loc[holdout_mask, "final_prediction"],
    )
    holdout_mask_v = (var_preds["split"] == "holdout") & (~var_preds["is_imputed"])
    pooled_variant_smape = smape(
        var_preds.loc[holdout_mask_v, "Number_of_Cases"],
        var_preds.loc[holdout_mask_v, "final_prediction"],
    )

    accept_mase = median_mase <= BASELINE_HOLDOUT_MASE and (25 - n_improved) <= 2  # ≥20/25 not worse by >5% — approx via improved count
    accept_smape = median_smape <= (BASELINE_HOLDOUT_SMAPE - 3) and n_severe <= 2

    summary = pd.DataFrame([{
        "variant": "m1_006_log",
        "median_holdout_mase": round(median_mase, 4),
        "median_holdout_smape": round(median_smape, 2),
        "pooled_holdout_smape": round(pooled_variant_smape, 2),
        "baseline_median_mase": BASELINE_HOLDOUT_MASE,
        "baseline_median_smape": BASELINE_HOLDOUT_SMAPE,
        "baseline_pooled_smape": round(pooled_baseline_smape, 2),
        "districts_improved_mase_vs_additive": n_improved,
        "districts_severely_harmed_mase_gt25pct": n_severe,
        "accept_mase_criterion": accept_mase,
        "accept_smape_criterion": accept_smape,
    }])

    out_dir = MODULE1_METRICS_DIR / "module1"
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = MODULE1_METRICS_DIR / "m1_006_log_vs_baseline.csv"
    comparison.to_csv(comparison_path, index=False)
    summary_path = MODULE1_METRICS_DIR / "m1_006_log_vs_baseline_summary.csv"
    summary.to_csv(summary_path, index=False)

    print("=== M1-006A log vs M1-005 additive (holdout) ===")
    print(summary.to_string(index=False))
    print(f"\nWrote per-district comparison -> {comparison_path}")
    print(f"Wrote summary -> {summary_path}")


if __name__ == "__main__":
    main()
