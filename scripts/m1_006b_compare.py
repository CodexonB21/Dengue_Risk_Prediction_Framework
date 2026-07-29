"""Compare M1-006B reporting-delay features vs M1-005 additive baseline."""

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

BASELINE_MEDIAN_MASE = 0.386
BASELINE_MEDIAN_SMAPE = 35.0


def _holdout_hybrid(metrics_df: pd.DataFrame) -> pd.DataFrame:
    return metrics_df[
        (metrics_df["model"] == "stage1_plus_stage2") & (metrics_df["fold_id"] == "holdout")
    ].set_index("District")


def main() -> None:
    baseline_metrics = pd.read_csv(MODULE1_COMBINED_METRICS_PATH)
    variant_paths = module1_stage2_paths("additive", feature_variant="m1_006_b")
    variant_metrics = pd.read_csv(variant_paths["combined_metrics"])
    variant_preds = pd.read_csv(variant_paths["final_predictions"])

    base_h = _holdout_hybrid(baseline_metrics)
    var_h = _holdout_hybrid(variant_metrics)

    rows = []
    for district in sorted(set(base_h.index) & set(var_h.index)):
        b, v = base_h.loc[district], var_h.loc[district]
        mase_delta_pct = 100 * (v["mase"] - b["mase"]) / b["mase"] if b["mase"] else np.nan
        rows.append({
            "District": district,
            "baseline_mase": round(b["mase"], 4),
            "variant_mase": round(v["mase"], 4),
            "mase_delta_pct": round(mase_delta_pct, 2),
            "baseline_smape": round(b["smape"], 2),
            "variant_smape": round(v["smape"], 2),
            "smape_delta_pp": round(v["smape"] - b["smape"], 2),
            "variant_improved_mase": v["mase"] < b["mase"],
        })

    comparison = pd.DataFrame(rows)
    median_mase = float(comparison["variant_mase"].median())
    median_smape = float(comparison["variant_smape"].median())
    n_improved = int(comparison["variant_improved_mase"].sum())

    holdout = variant_preds[(variant_preds["split"] == "holdout") & (~variant_preds["is_imputed"])]
    base_preds = pd.read_csv(PROJECT_ROOT / "data/processed/module1/final_combined_predictions.csv")
    base_holdout = base_preds[(base_preds["split"] == "holdout") & (~base_preds["is_imputed"])]

    pooled_variant_smape = smape(holdout["Number_of_Cases"], holdout["final_prediction"])
    pooled_baseline_smape = smape(base_holdout["Number_of_Cases"], base_holdout["final_prediction"])

    wk22_23 = holdout[(holdout["Year"] == 2026) & holdout["Week"].isin([22, 23])]
    base_wk22_23 = base_holdout[(base_holdout["Year"] == 2026) & base_holdout["Week"].isin([22, 23])]
    slice_variant_smape = smape(wk22_23["Number_of_Cases"], wk22_23["final_prediction"]) if len(wk22_23) else np.nan
    slice_baseline_smape = smape(base_wk22_23["Number_of_Cases"], base_wk22_23["final_prediction"]) if len(base_wk22_23) else np.nan
    slice_delta_pp = slice_variant_smape - slice_baseline_smape

    accept = (
        median_mase <= BASELINE_MEDIAN_MASE
        or (slice_delta_pp <= -5 and median_smape <= BASELINE_MEDIAN_SMAPE + 2)
    )

    summary = pd.DataFrame([{
        "variant": "m1_006_b",
        "median_holdout_mase": round(median_mase, 4),
        "median_holdout_smape": round(median_smape, 2),
        "pooled_holdout_smape": round(pooled_variant_smape, 2),
        "baseline_median_mase": BASELINE_MEDIAN_MASE,
        "baseline_median_smape": BASELINE_MEDIAN_SMAPE,
        "baseline_pooled_smape": round(pooled_baseline_smape, 2),
        "districts_improved_mase": n_improved,
        "pooled_smape_2026_wk22_23": round(slice_variant_smape, 2),
        "baseline_smape_2026_wk22_23": round(slice_baseline_smape, 2),
        "wk22_23_smape_delta_pp": round(slice_delta_pp, 2),
        "accept_criterion": accept,
    }])

    out = MODULE1_METRICS_DIR / "m1_006_b_vs_baseline.csv"
    summary_out = MODULE1_METRICS_DIR / "m1_006_b_vs_baseline_summary.csv"
    comparison.to_csv(out, index=False)
    summary.to_csv(summary_out, index=False)

    print("=== M1-006B reporting-delay vs M1-005 baseline (holdout) ===")
    print(summary.to_string(index=False))
    print(f"\nWrote {out}")
    print(f"Wrote {summary_out}")


if __name__ == "__main__":
    main()
