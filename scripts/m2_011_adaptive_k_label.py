"""M2-011: district-specific / variance-adaptive k for the epidemic-threshold
label - does letting each district pick its own k fix the known problem that
one global k=3.0 (Decision 025) under-flags high-variance districts (the
documented Colombo 2025 Wk15 case) relative to low-variance ones?

Read-only diagnostic script. Does NOT modify `labels.py`, does NOT change the
harmonic historical_mean/historical_sd ESTIMATOR (Decision 025's
`compute_historical_stats_harmonic` is reused completely unchanged) - only
the threshold formula's `k` multiplier is varied, and only per district
instead of one shared global value.

Method:
1. Compute historical_mean/historical_sd once via the official harmonic
   estimator (k-independent - the fit itself never uses k).
2. Scan a k grid per district; for each (district, k) compute pooled
   outbreak prevalence and undefined-label rate.
3. Per-district selection rule: the SMALLEST grid k that brings that
   district's own pooled prevalence at or below `TARGET_PREVALENCE_PCT`
   (mirrors Decision 025's own stated goal of moving pooled prevalence
   toward a WHO/CDC-style single-digit-to-low-double-digit rate - just
   applied per district instead of once globally). If no grid k reaches the
   target, keep the largest k tested and flag it explicitly (not silently).
4. Compare the resulting adaptive-k label against the current global
   k=3.0 label on:
   - pooled prevalence and undefined rate (should stay in a similar,
     reasonable band - this is not supposed to change the OVERALL rate
     much, only how it is distributed across districts)
   - cross-district prevalence SPREAD (std/range) - the actual motivating
     problem is that k=3.0 forces very different real-world flagging
     behaviour onto low- vs high-variance districts; adaptive k should
     narrow this, not just move it around
   - two real, independently-documented sanity checks: 2017 Wk29 Colombo
     AND Gampaha (Sri Lanka's worst recorded dengue epidemic year - MUST
     stay flagged 1) and Colombo 2025 Wk15 (277 cases - the case Decision
     025 already found flips to 0 under the current global k=3.0; this is
     the specific case adaptive k is meant to address).

This script does NOT rerun Stage 1/Stage 2/thresholds - relabeling changes
the training target for the whole downstream pipeline, which is a much
larger, separate step (would need a `feature_variant`-suffixed full rerun,
mirroring M2-007/M2-008's pattern) taken only if this audit shows the idea
is actually worth that cost.

Output: `outputs/metrics/module2/m2_011_adaptive_k_audit.csv` (per-district,
per-candidate prevalence/undefined-rate table) and a console summary.
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
    EPIDEMIC_THRESHOLD_K,
    EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
    EPIDEMIC_THRESHOLD_N_HARMONICS,
    MODULE2_METRICS_DIR,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
)
from src.module2_classification.labels import compute_historical_stats_harmonic  # noqa: E402

OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_011_adaptive_k_audit.csv"

K_GRID = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
GLOBAL_K = EPIDEMIC_THRESHOLD_K  # 3.0, Decision 025's production value
TARGET_PREVALENCE_PCT = 10.0  # Decision 025's own WHO/CDC-style aspiration

SANITY_CHECKS = [
    {"label": "2017 Wk29 Colombo (worst recorded epidemic year - must stay flagged)", "District": "Colombo", "Year": 2017, "Week": 29, "expect": 1.0},
    {"label": "2017 Wk29 Gampaha (worst recorded epidemic year - must stay flagged)", "District": "Gampaha", "Year": 2017, "Week": 29, "expect": 1.0},
    {"label": "2025 Wk15 Colombo (277 cases - flips to 0 under global k=3.0, Decision 025)", "District": "Colombo", "Year": 2025, "Week": 15, "expect": None},
]


def section(title: str) -> None:
    print("\n" + "=" * 96)
    print(title)
    print("=" * 96)


def load_stats() -> pd.DataFrame:
    df = pd.read_csv(MODULE2_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    return compute_historical_stats_harmonic(
        df, n_harmonics=EPIDEMIC_THRESHOLD_N_HARMONICS, min_prior_years=EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
    )


def apply_k(stats_df: pd.DataFrame, k) -> pd.DataFrame:
    """`k` may be a scalar (global) or a dict {District: k} (per-district)."""
    out = stats_df.copy()
    if isinstance(k, dict):
        k_series = out["District"].map(k)
    else:
        k_series = k
    out["threshold"] = out["historical_mean"] + k_series * out["historical_sd"]
    out["label"] = np.nan
    defined = out["threshold"].notna() & ~out["is_imputed"]
    out.loc[defined, "label"] = (out.loc[defined, "Number_of_Cases"] > out.loc[defined, "threshold"]).astype(float)
    return out


def per_district_summary(labeled: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for district, g in labeled.groupby("District"):
        defined = g["label"].notna()
        n_defined = int(defined.sum())
        rows.append(
            {
                "District": district,
                "n_rows": len(g),
                "n_defined": n_defined,
                "pct_undefined": (len(g) - n_defined) / len(g) * 100,
                "outbreak_pct": float(g.loc[defined, "label"].mean() * 100) if n_defined else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def select_per_district_k(stats_df: pd.DataFrame, districts: list[str]) -> dict[str, float]:
    """Smallest grid k bringing pooled prevalence <= TARGET_PREVALENCE_PCT;
    if none qualifies, keep the largest grid k tested and flag it."""
    selected: dict[str, float] = {}
    flagged_districts: list[str] = []

    for district in districts:
        chosen = None
        for k in K_GRID:
            labeled = apply_k(stats_df[stats_df["District"] == district], k)
            defined = labeled["label"].notna()
            if not defined.any():
                continue
            prevalence_pct = float(labeled.loc[defined, "label"].mean() * 100)
            if prevalence_pct <= TARGET_PREVALENCE_PCT:
                chosen = k
                break
        if chosen is None:
            chosen = K_GRID[-1]
            flagged_districts.append(district)
        selected[district] = chosen

    if flagged_districts:
        print(
            f"\nNOTE: {len(flagged_districts)} district(s) never reached the {TARGET_PREVALENCE_PCT:.0f}% "
            f"target within the tested k grid (kept at the largest tested k={K_GRID[-1]}, not silently "
            f"extrapolated further): {', '.join(flagged_districts)}"
        )
    return selected


def run_sanity_checks(labeled: pd.DataFrame, tag: str) -> list[dict]:
    results = []
    for check in SANITY_CHECKS:
        row = labeled[
            (labeled["District"] == check["District"]) & (labeled["Year"] == check["Year"]) & (labeled["Week"] == check["Week"])
        ]
        if row.empty:
            continue
        row = row.iloc[0]
        label_val = row["label"]
        flag = "UNDEFINED" if pd.isna(label_val) else ("OUTBREAK (1)" if label_val == 1.0 else "no-outbreak (0)")
        print(
            f"  [{tag}] {check['label']}: cases={row['Number_of_Cases']:.0f}, "
            f"mean={row['historical_mean']:.1f}, sd={row['historical_sd']:.1f}, "
            f"threshold={row['threshold']:.1f} -> {flag}"
        )
        results.append({"tag": tag, "check": check["label"], "label": label_val})
    return results


def main() -> None:
    section("M2-011: DISTRICT-SPECIFIC / VARIANCE-ADAPTIVE k AUDIT")
    stats_df = load_stats()
    districts = sorted(stats_df["District"].unique())
    print(f"Districts: {len(districts)} | k grid: {K_GRID} | target pooled prevalence per district: <= {TARGET_PREVALENCE_PCT:.0f}%")

    section(f"BASELINE - current production global k={GLOBAL_K}")
    global_labeled = apply_k(stats_df, GLOBAL_K)
    global_summary = per_district_summary(global_labeled)
    global_summary["candidate"] = f"global_k_{GLOBAL_K}"
    pooled_defined = global_labeled["label"].notna()
    print(f"Pooled prevalence: {global_labeled.loc[pooled_defined, 'label'].mean() * 100:.2f}%")
    print(f"Pooled undefined rate: {(~pooled_defined).mean() * 100:.2f}%")
    print(f"Per-district prevalence spread: min={global_summary['outbreak_pct'].min():.2f}%, "
          f"max={global_summary['outbreak_pct'].max():.2f}%, std={global_summary['outbreak_pct'].std():.2f}pp")

    section("SELECTING PER-DISTRICT k (smallest grid k reaching the target)")
    per_district_k = select_per_district_k(stats_df, districts)
    k_table = pd.DataFrame(sorted(per_district_k.items()), columns=["District", "selected_k"])
    print(k_table.to_string(index=False))

    section("ADAPTIVE-k RESULT")
    adaptive_labeled = apply_k(stats_df, per_district_k)
    adaptive_summary = per_district_summary(adaptive_labeled)
    adaptive_summary["candidate"] = "adaptive_k"
    pooled_defined_a = adaptive_labeled["label"].notna()
    print(f"Pooled prevalence: {adaptive_labeled.loc[pooled_defined_a, 'label'].mean() * 100:.2f}%")
    print(f"Pooled undefined rate: {(~pooled_defined_a).mean() * 100:.2f}%")
    print(f"Per-district prevalence spread: min={adaptive_summary['outbreak_pct'].min():.2f}%, "
          f"max={adaptive_summary['outbreak_pct'].max():.2f}%, std={adaptive_summary['outbreak_pct'].std():.2f}pp")

    section("SANITY CHECKS")
    print("Under baseline global k=3.0:")
    sanity_rows = run_sanity_checks(global_labeled, "global_k_3.0")
    print("\nUnder adaptive per-district k:")
    sanity_rows += run_sanity_checks(adaptive_labeled, "adaptive_k")

    section("VERDICT")
    spread_before = float(global_summary["outbreak_pct"].std())
    spread_after = float(adaptive_summary["outbreak_pct"].std())
    undefined_before = float((~pooled_defined).mean() * 100)
    undefined_after = float((~pooled_defined_a).mean() * 100)
    colombo_2025_before = global_labeled[(global_labeled["District"] == "Colombo") & (global_labeled["Year"] == 2025) & (global_labeled["Week"] == 15)]["label"].iloc[0]
    colombo_2025_after = adaptive_labeled[(adaptive_labeled["District"] == "Colombo") & (adaptive_labeled["Year"] == 2025) & (adaptive_labeled["Week"] == 15)]["label"].iloc[0]

    print(f"Cross-district prevalence spread (std): {spread_before:.2f}pp -> {spread_after:.2f}pp "
          f"({'narrower - homogenized as intended' if spread_after < spread_before else 'NOT narrower - did not achieve its goal'})")
    print(f"Pooled undefined rate: {undefined_before:.2f}% -> {undefined_after:.2f}% "
          f"({'worse (more undefined)' if undefined_after > undefined_before else 'same or better'})")
    print(f"Colombo 2025 Wk15 (the motivating case): label {colombo_2025_before} -> {colombo_2025_after} "
          f"({'FIXED' if colombo_2025_after == 1.0 and colombo_2025_before != 1.0 else 'unchanged/still missed'})")

    colombo_2017 = [r for r in sanity_rows if "2017" in r["check"] and "Colombo" in r["check"]]
    gampaha_2017 = [r for r in sanity_rows if "2017" in r["check"] and "Gampaha" in r["check"]]
    real_epidemic_preserved = all(r["label"] == 1.0 for r in colombo_2017 + gampaha_2017)
    print(f"2017 Wk29 real epidemic still correctly flagged under BOTH candidates: {real_epidemic_preserved}")

    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    combined = pd.concat([global_summary, adaptive_summary], ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    section("DONE")
    print(f"Per-district audit table written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
