"""Module 1 Stage 2 - feature importance figure (gain-based, XGBoost).

Renders `outputs/metrics/module1/xgboost_feature_importance.csv` (written by
`compensation_model.run_stage2_pipeline()`) as a horizontal bar chart, colored
by `FEATURE_ENGINEERING_SPEC.md` feature group, so the report figure shows not
just which features rank highest but which category of engineered feature
they came from (Decision 001-consistent: Stage 2 is where climate/seasonal
signal is expected to matter, since Stage 1/SARIMA is climate-free).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH,
    MODULE1_XGBOOST_FEATURE_IMPORTANCE_PLOT_PATH,
)

logger = logging.getLogger(__name__)

# Maps each FEATURE_COLUMNS entry to its FEATURE_ENGINEERING_SPEC.md group.
# Prefix-matched first (lag/rolling families), then exact names for the
# remaining one-off features.
GROUP_PREFIXES = [
    ("residual_lag_", "Group 5: Residual-Specific"),
    ("cases_lag_", "Group 1: Case-Trend"),
    ("rolling_", "Group 1: Case-Trend"),
    ("rainfall_lag_", "Group 2: Lagged Climate"),
    ("temperature_lag_", "Group 2: Lagged Climate"),
    ("humidity_lag_", "Group 2: Lagged Climate"),
    ("rainfall_anomaly", "Group 3: Climate Anomaly"),
    ("temperature_anomaly", "Group 3: Climate Anomaly"),
    ("humidity_anomaly", "Group 3: Climate Anomaly"),
    ("monsoon_indicator_", "Group 4: Seasonal/Contextual"),
]
GROUP_EXACT = {
    "rate_of_change": "Group 1: Case-Trend",
    "sin_week": "Group 4: Seasonal/Contextual",
    "cos_week": "Group 4: Seasonal/Contextual",
    "sarima_prediction": "Group 5b: Pooled-Model Support",
    "District": "Group 5b: Pooled-Model Support",
    "weeks_since_reporting_anomaly": "Group 6: Reporting-Delay (M1-006B)",
    "reporting_rebound_ratio_lag1": "Group 6: Reporting-Delay (M1-006B)",
    "suspected_backfill_week": "Group 6: Reporting-Delay (M1-006B)",
}

GROUP_COLORS = {
    "Group 1: Case-Trend": "#4C72B0",
    "Group 2: Lagged Climate": "#55A868",
    "Group 3: Climate Anomaly": "#8172B2",
    "Group 4: Seasonal/Contextual": "#CCB974",
    "Group 5: Residual-Specific": "#C44E52",
    "Group 5b: Pooled-Model Support": "#937860",
    "Group 6: Reporting-Delay (M1-006B)": "#64B5CD",
}


def assign_feature_group(feature: str) -> str:
    if feature in GROUP_EXACT:
        return GROUP_EXACT[feature]
    for prefix, group in GROUP_PREFIXES:
        if feature.startswith(prefix):
            return group
    raise ValueError(f"Unmapped feature '{feature}' - add it to GROUP_PREFIXES/GROUP_EXACT.")


def plot_feature_importance(
    input_path: Path = MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH,
    output_path: Path = MODULE1_XGBOOST_FEATURE_IMPORTANCE_PLOT_PATH,
    top_n: int | None = None,
) -> None:
    df = pd.read_csv(input_path)
    df["group"] = df["feature"].apply(assign_feature_group)
    df = df.sort_values("gain", ascending=False).reset_index(drop=True)
    if top_n is not None:
        df = df.head(top_n)
    # Plot bottom-to-top so the highest-gain feature ends up at the top.
    df = df.iloc[::-1]

    colors = df["group"].map(GROUP_COLORS)

    fig, ax = plt.subplots(figsize=(8, 0.32 * len(df) + 1.5))
    ax.barh(df["feature"], df["gain"], color=colors)
    ax.set_xlabel("Gain (total loss reduction attributed to this feature)")
    ax.set_title("Module 1 Stage 2 (XGBoost) feature importance - gain-based")

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in GROUP_COLORS.values()]
    ax.legend(handles, GROUP_COLORS.keys(), loc="lower right", fontsize=7, framealpha=0.9)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved feature importance plot (%d features) -> %s", len(df), output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    plot_feature_importance()
