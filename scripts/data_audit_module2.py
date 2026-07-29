"""Module 2 outbreak-label class-balance audit.

Read-only diagnostic script. Does not modify any files. Computes the
fold-aware epidemic-threshold label (Decision 019,
`research_context/RESEARCH_DECISIONS.md`) across a few candidate `k` values
directly against the shared, module-agnostic base table
(`data/processed/shared/epidemiological_weekly.csv`), and reports the
resulting per-district class balance.

Purpose: catch degenerate label distributions (e.g. a sparse,
zero-inflated district producing a near-0% or near-100% outbreak rate) BEFORE
`k` is locked in for Stage 1 training - mirrors how
`scripts/data_audit_module1.py` characterized zero-inflation before Module 1's
SARIMA design was finalized.

Label formula (per (District, Week), historical stats from strictly-prior
years only - no leakage):

    threshold = historical_mean + k * historical_SD
    outbreak  = 1 if Number_of_Cases > threshold else 0

A row's label is UNDEFINED (not defaulted to 0) if fewer than
MIN_PRIOR_YEARS strictly-prior years of data exist for that (District, Week).

This script intentionally reimplements the label formula standalone (does not
import `src/module2_classification/label_definition.py`) since it predates
that module's existence and is meant to be a simple, inspectable, one-off
check - once `label_definition.py` exists, both implementations should be
kept consistent; any divergence found later should be treated as a bug in
whichever one is wrong.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SHARED_EPI_PATH = ROOT / "data" / "processed" / "shared" / "epidemiological_weekly.csv"
OUTPUT_DIR = ROOT / "outputs" / "metrics" / "module2"
OUTPUT_PATH = OUTPUT_DIR / "label_balance_audit.csv"

CANDIDATE_K_VALUES = [1.5, 2.0, 2.5]
MIN_PRIOR_YEARS = 3

# Flag a district/k combination as "degenerate" if the outbreak rate among
# rows with a defined label falls outside this range - not itself a decision
# rule, just a threshold for what this script prints as a warning.
DEGENERATE_LOW_PCT = 2.0
DEGENERATE_HIGH_PCT = 40.0


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def load_epi() -> pd.DataFrame:
    df = pd.read_csv(
        SHARED_EPI_PATH,
        parse_dates=["Week_Start_Date", "Week_End_Date"],
    )
    return df.sort_values(["District", "Week", "Year"]).reset_index(drop=True)


def compute_label(df: pd.DataFrame, k: float) -> pd.DataFrame:
    """Return `df` with `historical_mean`, `historical_sd`, `threshold`,
    `label` columns added, for one candidate `k`.

    Historical mean/SD for a given (District, Week, Year) row use ONLY that
    (District, Week)'s case counts from years strictly before `Year` - an
    expanding window, never the full series (Decision 019's leakage guard).
    Implemented as `expanding(min_periods=MIN_PRIOR_YEARS).agg().shift(1)`:
    shifting AFTER expanding means row i receives the expanding statistic
    computed through row i-1, i.e. strictly-prior rows only.
    """
    df = df.copy()
    grouped = df.groupby(["District", "Week"], sort=False)["Number_of_Cases"]

    df["historical_mean"] = grouped.transform(
        lambda s: s.expanding(min_periods=MIN_PRIOR_YEARS).mean().shift(1)
    )
    df["historical_sd"] = grouped.transform(
        lambda s: s.expanding(min_periods=MIN_PRIOR_YEARS).std().shift(1)
    )
    df["threshold"] = df["historical_mean"] + k * df["historical_sd"]
    df["label"] = pd.NA
    defined = df["threshold"].notna()
    df.loc[defined, "label"] = (
        df.loc[defined, "Number_of_Cases"] > df.loc[defined, "threshold"]
    ).astype(int)
    return df


def summarize_for_k(df: pd.DataFrame, k: float) -> pd.DataFrame:
    labeled = compute_label(df, k)
    total_rows = len(labeled)
    defined_mask = labeled["label"].notna()
    n_defined = int(defined_mask.sum())
    n_undefined = total_rows - n_defined

    section(f"k = {k}: OVERALL")
    print(f"Total rows: {total_rows}")
    print(
        f"Rows with a defined label: {n_defined} ({n_defined / total_rows * 100:.1f}%)"
    )
    print(
        f"Rows with UNDEFINED label (< {MIN_PRIOR_YEARS} strictly-prior years): "
        f"{n_undefined} ({n_undefined / total_rows * 100:.1f}%)"
    )
    pooled_outbreak_pct = labeled.loc[defined_mask, "label"].astype(float).mean() * 100
    print(f"Pooled outbreak-week rate (among defined labels): {pooled_outbreak_pct:.2f}%")

    per_district = (
        labeled.groupby("District")
        .apply(
            lambda g: pd.Series(
                {
                    "n_rows": len(g),
                    "n_defined": int(g["label"].notna().sum()),
                    "outbreak_pct": (
                        g.loc[g["label"].notna(), "label"].astype(float).mean() * 100
                        if g["label"].notna().any()
                        else float("nan")
                    ),
                }
            )
        )
        .reset_index()
    )
    per_district["k"] = k
    per_district = per_district.sort_values("outbreak_pct")

    section(f"k = {k}: PER-DISTRICT OUTBREAK RATE (sorted ascending)")
    print(per_district.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    degenerate = per_district[
        (per_district["outbreak_pct"] < DEGENERATE_LOW_PCT)
        | (per_district["outbreak_pct"] > DEGENERATE_HIGH_PCT)
    ]
    if not degenerate.empty:
        section(f"k = {k}: DISTRICTS FLAGGED AS POTENTIALLY DEGENERATE")
        print(
            f"(outbreak_pct outside [{DEGENERATE_LOW_PCT}%, {DEGENERATE_HIGH_PCT}%])"
        )
        print(degenerate.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    else:
        print(f"\nNo districts flagged as degenerate at k = {k}.")

    return per_district


def main() -> None:
    df = load_epi()
    section("MODULE 2 LABEL CLASS-BALANCE AUDIT")
    print(f"Source: {SHARED_EPI_PATH}")
    print(f"Rows: {len(df)}, Districts: {df['District'].nunique()}")
    print(f"Candidate k values: {CANDIDATE_K_VALUES}")
    print(f"Minimum strictly-prior years required for a defined label: {MIN_PRIOR_YEARS}")

    all_summaries = [summarize_for_k(df, k) for k in CANDIDATE_K_VALUES]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined = pd.concat(all_summaries, ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    section("DONE")
    print(f"Per-district, per-k summary written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
