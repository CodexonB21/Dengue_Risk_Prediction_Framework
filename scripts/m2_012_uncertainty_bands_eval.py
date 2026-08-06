"""M2-012: evaluate the new Venn-Abers uncertainty bands
(`src/module2_classification/uncertainty_bands.py`) - does the interval
behave sensibly, and is it worth keeping as a companion output?

Read-only. Joins `stage2_uncertainty_bands.csv` (new) with the official
`stage2_risk_tier_predictions.csv` (unchanged) to check:

1. **Point-estimate agreement** - does the Venn-Abers merged point track the
   official isotonic `calibrated_probability` closely? (Both are built from
   the same Stage 1 input and the same fold structure - they SHOULD agree
   closely; large disagreement would be a red flag, not a feature.)
2. **Validity spot-check** - binned by the Venn-Abers point estimate, does
   the observed outbreak rate usually fall inside [mean(p0), mean(p1)]?
3. **Width behaviour** - mean interval width by risk tier. The whole point
   of building this is that width should be SMALLER for confident
   (low/high) tiers and LARGER for the borderline medium tier / near the
   0.140 alert threshold - if width is flat everywhere, the band carries no
   extra information over the point estimate and isn't worth shipping.
4. **Concrete near-threshold examples** - a handful of real holdout rows
   near the 0.140 alert threshold, printed as an evaluator would see them.

Output: `outputs/metrics/module2/m2_012_uncertainty_band_summary.csv`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import (  # noqa: E402
    MODULE2_METRICS_DIR,
    MODULE2_PROCESSED_DIR,
    MODULE2_RISK_TIER_PREDICTIONS_PATH,
)

BANDS_PATH = MODULE2_PROCESSED_DIR / "stage2_uncertainty_bands.csv"
OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_012_uncertainty_band_summary.csv"
ALERT_THRESHOLD = 0.140


def section(title: str) -> None:
    print("\n" + "=" * 92)
    print(title)
    print("=" * 92)


def load_merged() -> pd.DataFrame:
    bands = pd.read_csv(BANDS_PATH, low_memory=False)
    official = pd.read_csv(MODULE2_RISK_TIER_PREDICTIONS_PATH, low_memory=False)
    official = official[official["is_selected_architecture"]]
    key_cols = ["District", "Year", "Week", "split"]
    merged = bands.merge(
        official[key_cols + ["calibrated_probability", "risk_tier", "alert_flag"]],
        on=key_cols, how="inner",
    )
    return merged


def point_estimate_agreement(df: pd.DataFrame) -> None:
    section("1. POINT-ESTIMATE AGREEMENT: Venn-Abers point vs. official isotonic calibrated_probability")
    diff = (df["venn_abers_point"] - df["calibrated_probability"]).abs()
    corr = df["venn_abers_point"].corr(df["calibrated_probability"])
    print(f"Correlation: {corr:.4f}")
    print(f"Mean |difference|: {diff.mean():.4f}, max |difference|: {diff.max():.4f}")
    print(f"95th percentile |difference|: {diff.quantile(0.95):.4f}")


def validity_spot_check(df: pd.DataFrame, split: str, n_bins: int = 8) -> pd.DataFrame:
    section(f"2. VALIDITY SPOT-CHECK ({split}): is the observed rate usually inside [mean(p0), mean(p1)]?")
    sub = df[(df["split"] == split) & df["label"].notna()].copy()
    sub["bin"] = pd.qcut(sub["venn_abers_point"], q=min(n_bins, sub["venn_abers_point"].nunique()), duplicates="drop")
    rows = []
    for b, g in sub.groupby("bin", observed=True):
        rows.append(
            {
                "bin": str(b),
                "n": len(g),
                "mean_p0": g["venn_abers_p0"].mean(),
                "mean_point": g["venn_abers_point"].mean(),
                "mean_p1": g["venn_abers_p1"].mean(),
                "observed_rate": g["label"].mean(),
            }
        )
    result = pd.DataFrame(rows)
    result["observed_within_band"] = (result["observed_rate"] >= result["mean_p0"] - 1e-9) & (
        result["observed_rate"] <= result["mean_p1"] + 1e-9
    )
    print(result.to_string(index=False))
    print(f"\nBins where observed rate fell inside [mean_p0, mean_p1]: {result['observed_within_band'].sum()}/{len(result)}")
    print(
        "CAVEAT (do not over-read a low hit count here): IVAP's interval is a PER-POINT bound, often far "
        "narrower than a BINNED group's own empirical-rate sampling noise once thousands of calibration rows "
        "back that score region - a narrow, well-behaved interval will routinely fail to bracket a noisy group "
        "average by construction, especially in the dominant low-probability bins. This check is a rough "
        "sanity read on the POINT estimate (compare mean_point to observed_rate directly), not a real test of "
        "IVAP's own validity property, which is per-point, not per-bin."
    )
    return result


def width_by_tier(df: pd.DataFrame, split: str) -> pd.DataFrame:
    section(f"3. INTERVAL WIDTH BY RISK TIER ({split})")
    sub = df[df["split"] == split]
    result = sub.groupby("risk_tier")["venn_abers_width"].agg(["mean", "median", "std", "count"]).reindex(["low", "medium", "high"])
    print(result.to_string())
    return result.reset_index()


def near_threshold_examples(df: pd.DataFrame, split: str = "holdout", band: float = 0.08, n: int = 8) -> None:
    section(f"4. CONCRETE EXAMPLES near the alert threshold (calibrated_probability within +/-{band} of {ALERT_THRESHOLD}, {split})")
    sub = df[(df["split"] == split) & ((df["calibrated_probability"] - ALERT_THRESHOLD).abs() <= band)]
    cols = ["District", "Year", "Week", "label", "calibrated_probability", "venn_abers_p0", "venn_abers_p1", "venn_abers_width", "risk_tier"]
    print(sub[cols].sort_values("calibrated_probability").head(n).to_string(index=False))


def main() -> None:
    df = load_merged()
    print(f"Merged rows: {len(df)} (validation={len(df[df['split']=='validation'])}, holdout={len(df[df['split']=='holdout'])})")

    point_estimate_agreement(df)
    val_validity = validity_spot_check(df, "validation")
    holdout_validity = validity_spot_check(df, "holdout")
    val_width = width_by_tier(df, "validation")
    holdout_width = width_by_tier(df, "holdout")
    near_threshold_examples(df, "holdout")

    section("VERDICT")
    low_w = holdout_width.set_index("risk_tier")["mean"].get("low", float("nan"))
    med_w = holdout_width.set_index("risk_tier")["mean"].get("medium", float("nan"))
    high_w = holdout_width.set_index("risk_tier")["mean"].get("high", float("nan"))
    print(f"Holdout mean width - low: {low_w:.3f}, medium: {med_w:.3f}, high: {high_w:.3f}")
    informative = med_w > low_w
    print(f"Medium tier wider than low tier (band carries real information beyond the point estimate): {informative}")

    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    val_validity.assign(split="validation").to_csv(OUTPUT_PATH, index=False)
    holdout_validity.assign(split="holdout").to_csv(
        MODULE2_METRICS_DIR / "m2_012_uncertainty_band_summary_holdout.csv", index=False
    )
    print(f"\nSummary written to {OUTPUT_PATH} and its holdout counterpart.")


if __name__ == "__main__":
    main()
