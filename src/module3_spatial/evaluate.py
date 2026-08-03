"""Stage 1 vs Stage 2 evaluation: fit comparison, convergence plot, feature
importance chart, and a consolidated Results-chapter summary table.

IMPORTANT - Stage 1 vs Stage 2 comparison result (verified, not assumed):
`compare_stage1_vs_stage2()` compares Risk_0 (Stage 1 alone - the
mass-conserving rescaled KDE_baseline, NOT the raw Stage 1 output; see
`MODULE_CONTEXT.md`'s "KDE_baseline: Two Valid Uses") against the final
Risk after the iterative loop (Stage 2). Checked directly before writing
this module: Stage 2 is marginally WORSE on every standard metric (corr
-0.0037, MAE +1.74%, RMSE +0.87%), not better. This is reported as a
plain, honest null/negative result, not dressed up - see EXPERIMENT_LOG.md
M3-005 for the full reasoning (alpha=0.05 was chosen for strict
convergence, not accuracy, so the correction is too small to move
aggregate fit metrics either way).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.inspection import partial_dependence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_CONVERGENCE_LOG_PATH,
    MODULE3_CONVERGENCE_PLOT_PATH,
    MODULE3_FEATURE_IMPORTANCE_PLOT_PATH,
    MODULE3_FIGURES_DIR,
    MODULE3_HYBRID_RISK_MAP_PATH,
    MODULE3_METRICS_DIR,
    MODULE3_MORANS_I_METRICS_PATH,
    MODULE3_POPULATION_DENSITY_PDP_PLOT_PATH,
    MODULE3_RF_FEATURE_IMPORTANCE_PATH,
    MODULE3_RF_FINAL_MODEL_PATH,
    MODULE3_RF_METRICS_PATH,
    MODULE3_RESULTS_SUMMARY_PATH,
    MODULE3_STAGE_COMPARISON_PATH,
)
from src.module3_spatial.compensation_model import FEATURE_COLUMNS, load_training_table, rescale_kde_baseline

logger = logging.getLogger(__name__)

# Chart chrome (light mode), from the project's validated reference palette
# (dataviz skill, references/palette.md) - not eyeballed.
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_BLUE = "#2a78d6"   # categorical slot 1 / sequential base hue
SERIES_ORANGE = "#eb6834"  # categorical slot 2 (validated adjacent pair with blue)


def _style_axes(ax) -> None:
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.xaxis.label.set_color(INK_PRIMARY)
    ax.yaxis.label.set_color(INK_PRIMARY)
    ax.title.set_color(INK_PRIMARY)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color(BASELINE)
    ax.grid(True, axis="y", color=GRIDLINE, linewidth=0.8)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# Step 1: Stage 1 alone vs Stage 2 final - fit to actual case counts
# ---------------------------------------------------------------------------

def compare_stage1_vs_stage2() -> pd.DataFrame:
    df = load_training_table()
    df = rescale_kde_baseline(df)
    hybrid = pd.read_csv(MODULE3_HYBRID_RISK_MAP_PATH)[["District", "Year", "Week", "Risk"]]
    merged = df.merge(hybrid, on=["District", "Year", "Week"], how="inner")

    if len(merged) != len(hybrid):
        raise ValueError(
            f"Expected the merge to preserve all {len(hybrid)} hybrid_risk_map.csv "
            f"rows, got {len(merged)}."
        )

    number_of_cases = merged["Number_of_Cases"].to_numpy(dtype=float)
    risk_0 = merged["kde_baseline_rescaled"].to_numpy(dtype=float)
    risk_final = merged["Risk"].to_numpy(dtype=float)

    def _metrics(pred: np.ndarray) -> dict:
        return {
            "corr": float(np.corrcoef(pred, number_of_cases)[0, 1]),
            "mae": float(np.mean(np.abs(number_of_cases - pred))),
            "rmse": float(np.sqrt(np.mean((number_of_cases - pred) ** 2))),
        }

    stage1 = _metrics(risk_0)
    stage2 = _metrics(risk_final)
    change = {k: stage2[k] - stage1[k] for k in stage1}

    return pd.DataFrame(
        [
            {"stage": "Stage 1 alone (Risk_0, rescaled KDE_baseline)", **stage1},
            {"stage": "Stage 2 final (Risk, post iterative loop)", **stage2},
            {"stage": "Change (Stage 2 - Stage 1)", **change},
        ]
    )


# ---------------------------------------------------------------------------
# Step 1b: negative-Risk footnote (Critique Point 6 - already documented in
# MODULE_CONTEXT.md, but was missing from the report-facing summary file)
# ---------------------------------------------------------------------------

def negative_risk_note(hybrid_df: pd.DataFrame) -> str:
    negative = hybrid_df.loc[hybrid_df["Risk"] < 0, "Risk"]
    if negative.empty:
        return "No rows have a negative final Risk value."
    pct = 100 * len(negative) / len(hybrid_df)
    return (
        f"Note: {len(negative)} rows ({pct:.2f}%) have a small negative final Risk "
        f"(min {negative.min():.2f}) - a minor overshoot on near-zero-case "
        f"district-weeks, NOT clipped (see MODULE_CONTEXT.md's Stage 2 "
        f"Implementation Status)."
    )


# ---------------------------------------------------------------------------
# Step 1c: population_density partial dependence (Critique Point 4) -
# checks whether the RF's dominant feature (population_density, 40.7%
# importance) is genuinely learning a nuanced relationship, or effectively
# just a population-size scaling that would make Estimated_Population's own
# 17.8% importance partly redundant with it. Partial dependence (not a raw
# residual-vs-feature scatter) holds every OTHER feature at its observed
# distribution and isolates population_density's own marginal effect on the
# predicted residual - the correct tool for this question, since
# population_density and Estimated_Population are themselves correlated
# (population_density is literally derived from Estimated_Population - see
# feature_engineering.py::compute_population_density) and a raw scatter
# would conflate the two.
# ---------------------------------------------------------------------------

def plot_population_density_pdp(path: Path) -> pd.DataFrame:
    df = load_training_table()
    df = rescale_kde_baseline(df)
    model = joblib.load(MODULE3_RF_FINAL_MODEL_PATH)

    pdp = partial_dependence(
        model, df[FEATURE_COLUMNS], features=["population_density"], kind="average", grid_resolution=50,
    )
    grid = pdp["grid_values"][0]
    avg_effect = pdp["average"][0]

    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    ax.plot(grid, avg_effect, color=SERIES_BLUE, linewidth=2)
    ax.set_xlabel("population_density (people / km^2)")
    ax.set_ylabel("Partial dependence: predicted residual_rescaled")
    ax.set_title("Stage 2 RF - Partial Dependence on population_density")
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    logger.info("population_density partial-dependence plot saved to %s.", path)

    return pd.DataFrame({"population_density": grid, "partial_dependence": avg_effect})


# ---------------------------------------------------------------------------
# Step 2: convergence plot
# ---------------------------------------------------------------------------

def plot_convergence(log_df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), facecolor=SURFACE)
    iterations = log_df["iteration"].to_numpy()

    ax = axes[0]
    ax.plot(iterations, log_df["max_delta"], marker="o", markersize=8, linewidth=2,
             color=SERIES_BLUE, label="max|Risk_t - Risk_(t-1)|")
    ax.axhline(log_df["epsilon"].iloc[0], linestyle="--", linewidth=1.5,
               color=INK_MUTED, label="epsilon (convergence threshold)")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("max_delta")
    ax.set_title("Risk convergence per iteration")
    ax.set_xticks(iterations)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_PRIMARY)
    _style_axes(ax)

    ax = axes[1]
    ax.plot(iterations, log_df["risk_min"], marker="o", markersize=8, linewidth=2,
             color=SERIES_BLUE, label="Risk min")
    ax.plot(iterations, log_df["risk_max"], marker="o", markersize=8, linewidth=2,
             color=SERIES_ORANGE, label="Risk max")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Risk value")
    ax.set_title("Risk range per iteration")
    ax.set_xticks(iterations)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_PRIMARY)
    _style_axes(ax)

    n_iter = len(log_df)
    fig.suptitle(
        f"Iterative loop: converged at iteration {n_iter} "
        f"({'stopped early' if log_df['stopped'].iloc[-1] else 'hit MAX_ITERATIONS'})",
        color=INK_PRIMARY, fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    logger.info("Convergence plot saved to %s.", path)


# ---------------------------------------------------------------------------
# Step 3: feature importance bar chart
# ---------------------------------------------------------------------------

def plot_feature_importance(importance_df: pd.DataFrame, path: Path) -> None:
    sorted_df = importance_df.sort_values("importance", ascending=True)

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=SURFACE)
    ax.barh(sorted_df["feature"], sorted_df["importance"], color=SERIES_BLUE, height=0.65)
    ax.set_xlabel("Importance (mean decrease in impurity)")
    ax.set_title("Stage 2 Random Forest - Feature Importance (final model)")
    _style_axes(ax)
    ax.grid(True, axis="x", color=GRIDLINE, linewidth=0.8)
    ax.grid(False, axis="y")

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    logger.info("Feature importance plot saved to %s.", path)


# ---------------------------------------------------------------------------
# Step 4: consolidated Results-chapter summary
# ---------------------------------------------------------------------------

def build_summary_text(
    comparison_df: pd.DataFrame,
    moransI_df: pd.DataFrame,
    rf_metrics_df: pd.DataFrame,
    convergence_df: pd.DataFrame,
    importance_df: pd.DataFrame,
    hybrid_df: pd.DataFrame,
) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("MODULE 3 - STAGE 1 & STAGE 2 RESULTS SUMMARY")
    lines.append("=" * 78)

    agg = moransI_df[moransI_df["check"] == "aggregated"].iloc[0]
    lines.append("")
    lines.append("-- Stage 1: KDE Baseline Spatial Validation --")
    lines.append(
        f"Global Moran's I (queen contiguity, aggregated across all weeks): "
        f"I = {agg['I']:.4f}, p_sim = {agg['p_sim']:.4f}, "
        f"significant = {bool(agg['significant'])}"
    )

    lines.append("")
    lines.append("-- Stage 1 alone vs Stage 2 final: fit to actual case counts --")
    lines.append(
        "(Stage 2's correction does NOT improve aggregate fit - a plain, "
        "verified null/negative result; see EXPERIMENT_LOG.md M3-005.)"
    )
    lines.append(comparison_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    lines.append(negative_risk_note(hybrid_df))

    rf_agg = rf_metrics_df[rf_metrics_df["fold"] == "mean_std"].iloc[0]
    lines.append("")
    lines.append("-- Stage 2 RF: out-of-fold residual prediction accuracy (spatial CV) --")
    lines.append(
        f"MAE = {rf_agg['mae']:.2f} +/- {rf_agg['mae_std']:.2f}, "
        f"RMSE = {rf_agg['rmse']:.2f} +/- {rf_agg['rmse_std']:.2f} "
        f"(mean +/- std across 5 spatial folds)"
    )

    lines.append("")
    lines.append("-- Iterative Loop Convergence --")
    lines.append(
        convergence_df[
            ["iteration", "risk_min", "risk_max", "max_delta", "epsilon",
             "morans_I", "morans_p_sim", "morans_significant", "stopped"]
        ].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )

    lines.append("")
    lines.append("-- Top 10 Feature Importance (final RF model) --")
    lines.append(
        importance_df.head(10).to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    lines.append("=" * 78)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_evaluation() -> str:
    MODULE3_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    comparison_df = compare_stage1_vs_stage2()
    comparison_df.to_csv(MODULE3_STAGE_COMPARISON_PATH, index=False)
    moransI_df = pd.read_csv(MODULE3_MORANS_I_METRICS_PATH)
    rf_metrics_df = pd.read_csv(MODULE3_RF_METRICS_PATH)
    convergence_df = pd.read_csv(MODULE3_CONVERGENCE_LOG_PATH)
    importance_df = pd.read_csv(MODULE3_RF_FEATURE_IMPORTANCE_PATH)

    hybrid_df = pd.read_csv(MODULE3_HYBRID_RISK_MAP_PATH)

    plot_convergence(convergence_df, MODULE3_CONVERGENCE_PLOT_PATH)
    plot_feature_importance(importance_df, MODULE3_FEATURE_IMPORTANCE_PLOT_PATH)
    plot_population_density_pdp(MODULE3_POPULATION_DENSITY_PDP_PLOT_PATH)

    summary = build_summary_text(comparison_df, moransI_df, rf_metrics_df, convergence_df, importance_df, hybrid_df)
    print(summary)

    MODULE3_RESULTS_SUMMARY_PATH.write_text(summary, encoding="utf-8")
    logger.info("Results summary written to %s.", MODULE3_RESULTS_SUMMARY_PATH)

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_evaluation()
