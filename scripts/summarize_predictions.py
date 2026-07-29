"""One-off summary of final M1/M2 prediction outputs."""
from __future__ import annotations

import pandas as pd

M1_COLS = [
    "District", "Year", "Week", "Number_of_Cases",
    "sarima_prediction", "predicted_residual", "final_prediction", "split",
]
M2_COLS = [
    "District", "Year", "Week", "Number_of_Cases",
    "calibrated_probability", "alert_flag", "risk_tier", "feature_completeness_pct",
]


def main() -> None:
    m1 = pd.read_csv("data/processed/module1/final_combined_predictions.csv")
    m1_latest = m1.sort_values(["District", "Year", "Week"]).groupby("District").tail(1)
    print("=== M1 final_combined_predictions (latest week per district) ===")
    print(f"Rows total: {len(m1)}, holdout: {(m1['split'] == 'holdout').sum()}")
    print(m1_latest[M1_COLS].sort_values("final_prediction", ascending=False).head(8).to_string(index=False))

    print("\n=== M1 Colombo/Gampaha 2026 Wk20-25 (holdout) ===")
    sub = m1[
        (m1["District"].isin(["Colombo", "Gampaha"]))
        & (m1["Year"] == 2026)
        & (m1["Week"] >= 20)
        & (m1["split"] == "holdout")
    ]
    print(sub[M1_COLS].to_string(index=False))

    live = pd.read_csv("data/processed/module2/live_risk_predictions.csv")
    live_latest = live.sort_values(["District", "Year", "Week"]).groupby("District").tail(1)
    print("\n=== M2 live_risk_predictions (latest week per district) ===")
    print(f"Rows: {len(live)}")
    print(live_latest.sort_values("calibrated_probability", ascending=False).head(10)[M2_COLS].to_string(index=False))

    print("\n=== M2 Colombo/Gampaha recent weeks (live) ===")
    lsub = live[live["District"].isin(["Colombo", "Gampaha"])].sort_values(["District", "Year", "Week"])
    print(lsub[M2_COLS].to_string(index=False))

    hold = pd.read_csv("data/processed/module2/stage2_risk_tier_predictions.csv")
    arch = hold["architecture"].value_counts().idxmax() if "architecture" in hold.columns else "isotonic"
    h = hold[(hold["split"] == "holdout") & (hold["architecture"] == arch)]
    print(f"\n=== M2 holdout ({arch}) Colombo/Gampaha 2026 Wk20-25 ===")
    hsub = h[(h["District"].isin(["Colombo", "Gampaha"])) & (h["Year"] == 2026) & (h["Week"] >= 20)]
    print(hsub[["District", "Year", "Week", "label", "calibrated_probability", "alert_flag", "risk_tier"]].to_string(index=False))

    roll_path = "data/processed/module1/rolling_one_step_predictions.csv"
    try:
        roll = pd.read_csv(roll_path)
        print(f"\n=== M1 rolling_one_step ({len(roll)} rows, {roll['District'].nunique()} districts) ===")
        rsub = roll[(roll["District"].isin(["Colombo", "Gampaha"])) & (roll["Year"] == 2026) & (roll["Week"] >= 20)]
        print(rsub[["District", "Year", "Week", "Number_of_Cases", "final_prediction"]].to_string(index=False))
    except FileNotFoundError:
        print("\n=== M1 rolling_one_step: still running ===")


if __name__ == "__main__":
    main()
