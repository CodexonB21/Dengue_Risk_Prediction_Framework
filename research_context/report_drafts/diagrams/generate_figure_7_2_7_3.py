"""Generate Chapter 7 Figures 7.2 and 7.3 from Module 1 artefacts."""
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "research_context" / "report_drafts" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def week_to_date(year: pd.Series, week: pd.Series) -> pd.Series:
    dates = pd.to_datetime(
        year.astype(str) + "-W" + week.astype(str).str.zfill(2) + "-1",
        format="%G-W%V-%u",
        errors="coerce",
    )
    missing = dates.isna()
    if missing.any():
        fallback = pd.to_datetime(
            {"year": year[missing], "month": 1, "day": 1}
        ) + pd.to_timedelta((week[missing] - 1) * 7, unit="D")
        dates = dates.copy()
        dates.loc[missing] = fallback
    return dates


def make_figure_7_2() -> Path:
    pred = pd.read_csv(ROOT / "data/processed/module1/final_combined_predictions.csv")
    pred = pred[(pred["split"] == "holdout") & (~pred["is_imputed"])].copy()
    pred["date"] = week_to_date(pred["Year"], pred["Week"])

    districts = ["Colombo", "Gampaha"]
    fig, axes = plt.subplots(2, 1, figsize=(10, 7.2), sharex=True)
    colors = {
        "actual": "#1f2937",
        "stage1": "#9ca3af",
        "stage12": "#b45309",
    }
    for ax, dist in zip(axes, districts):
        d = pred[pred["District"] == dist].sort_values(["Year", "Week"])
        ax.plot(
            d["date"],
            d["Number_of_Cases"],
            color=colors["actual"],
            lw=1.6,
            label="Actual cases",
        )
        ax.plot(
            d["date"],
            d["sarima_prediction"],
            color=colors["stage1"],
            lw=1.3,
            ls="--",
            label="Stage 1 (SARIMA)",
        )
        ax.plot(
            d["date"],
            d["final_prediction"],
            color=colors["stage12"],
            lw=1.5,
            label="Stage 1+2 (compensated)",
        )
        ax.set_ylabel("Weekly cases")
        ax.set_title(dist, loc="left", fontsize=11, fontweight="semibold")
        ax.grid(True, axis="y", alpha=0.25)
        ax.set_ylim(bottom=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].legend(loc="upper left", frameon=False, ncol=3, fontsize=9)
    axes[1].set_xlabel("Holdout week")
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.suptitle(
        "Actual vs Stage 1 vs Stage 1+2 forecasts (holdout)",
        fontsize=12,
        y=0.995,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = OUT_DIR / "figure_7_2_module1_holdout_forecasts.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def make_figure_7_3() -> Path:
    metrics = pd.read_csv(
        ROOT / "outputs/metrics/module1/combined_vs_baseline_metrics.csv"
    )
    holdout = metrics[metrics["fold_id"].astype(str) == "holdout"].copy()
    s1 = holdout[holdout["model"] == "stage1_only"][["District", "mase"]].rename(
        columns={"mase": "stage1_mase"}
    )
    s2 = holdout[holdout["model"] == "stage1_plus_stage2"][
        ["District", "mase"]
    ].rename(columns={"mase": "stage12_mase"})
    cmp = s1.merge(s2, on="District")
    cmp["improved"] = cmp["stage12_mase"] < cmp["stage1_mase"]
    cmp = cmp.sort_values("stage1_mase", ascending=True).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(10.5, 7.5))
    ypos = list(range(len(cmp)))
    ax.hlines(
        ypos,
        cmp["stage12_mase"],
        cmp["stage1_mase"],
        color="#d1d5db",
        lw=1.2,
        zorder=1,
    )
    ax.scatter(
        cmp["stage1_mase"],
        ypos,
        color="#6b7280",
        s=36,
        label="Stage 1 only",
        zorder=2,
    )
    improved_idx = [i for i, ok in enumerate(cmp["improved"]) if ok]
    worse_idx = [i for i, ok in enumerate(cmp["improved"]) if not ok]
    ax.scatter(
        cmp.loc[cmp["improved"], "stage12_mase"],
        improved_idx,
        color="#b45309",
        s=42,
        label="Stage 1+2 improved",
        zorder=3,
    )
    ax.scatter(
        cmp.loc[~cmp["improved"], "stage12_mase"],
        worse_idx,
        color="#b91c1c",
        s=52,
        marker="D",
        label="Stage 1+2 not improved",
        zorder=3,
    )
    ax.axvline(1.0, color="#9ca3af", ls=":", lw=1, label="MASE = 1 (seasonal-naive)")
    ax.set_yticks(ypos)
    ax.set_yticklabels(cmp["District"].tolist(), fontsize=9)
    ax.set_xlabel("Holdout MASE (lower is better)")
    ax.set_title("District holdout MASE: Stage 1 vs Stage 1+2", fontsize=12)
    ax.grid(True, axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    fig.tight_layout()
    out = OUT_DIR / "figure_7_3_module1_holdout_mase.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    exceptions = cmp.loc[
        ~cmp["improved"], ["District", "stage1_mase", "stage12_mase"]
    ]
    print("Holdout exceptions:\n", exceptions.to_string(index=False))
    print(
        "Median Stage1 MASE:",
        round(cmp["stage1_mase"].median(), 3),
        "Median Stage1+2 MASE:",
        round(cmp["stage12_mase"].median(), 3),
    )
    return out


if __name__ == "__main__":
    p72 = make_figure_7_2()
    p73 = make_figure_7_3()
    print("Wrote", p72)
    print("Wrote", p73)
