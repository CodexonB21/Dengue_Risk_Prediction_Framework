"""Generate Figure 5.4 - Module 2 high-level architecture (four-column layout:
Inputs | Stage 1 - Base Classifier | Stage 2 - Compensation | Output).

Content mirrors figure_5_4_module2_architecture.drawio - regenerate this PNG
after editing that file's text so the two never drift apart again.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent

C = {
    "bg": "#FFFFFF",
    "title": "#1F2937",
    "subtitle": "#4B5563",
    "col_in": "#F3F4F6",
    "col_in_edge": "#D1D5DB",
    "col_s1": "#DBEAFE",
    "col_s1_edge": "#93C5FD",
    "col_s2": "#EDE9FE",
    "col_s2_edge": "#C4B5FD",
    "col_out": "#DCFCE7",
    "col_out_edge": "#86EFAC",
    "green": "#86EFAC",
    "green_edge": "#15803D",
    "green_text": "#14532D",
    "blue": "#BFDBFE",
    "blue_edge": "#2563EB",
    "blue_text": "#1E3A8A",
    "purple": "#E9D5FF",
    "purple_edge": "#7C3AED",
    "purple_text": "#4C1D95",
    "navy": "#1E3A8A",
    "grey_box": "#E5E7EB",
    "grey_edge": "#4B5563",
    "red": "#FECACA",
    "red_edge": "#DC2626",
    "red_text": "#7F1D1D",
    "note_red": "#FEE2E2",
    "note_red_edge": "#DC2626",
    "note_red_text": "#991B1B",
    "note_amber": "#FEF3C7",
    "note_amber_edge": "#D97706",
    "note_amber_text": "#92400E",
    "white": "#FFFFFF",
    "grey_light": "#F9FAFB",
    "grey_line": "#9CA3AF",
}


def box(ax, x, y, w, h, text, fc, ec, tc="#111827", fs=9.5, weight="normal", dashed=False, ls="-"):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.5,
        linestyle="dashed" if dashed else ls,
        facecolor=fc,
        edgecolor=ec,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
             color=tc, fontweight=weight, wrap=True, linespacing=1.3)
    return patch


def arrow(ax, x1, y1, x2, y2, color="#4B5563", lw=1.6, ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, linestyle=ls, shrinkA=2, shrinkB=2))


def col_bg(ax, x, y, w, h, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.01",
                                 linewidth=1, facecolor=fc, edgecolor=ec, alpha=0.35, zorder=0))


def main() -> Path:
    fig, ax = plt.subplots(figsize=(14, 9.5))
    ax.set_xlim(0, 116)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    ax.text(58, 97.5, "Module 2: Hybrid Outbreak Risk Classification", ha="center", va="top",
             fontsize=17, fontweight="bold", color=C["title"])
    ax.text(58, 94.3, "Figure 5.4 — High-level architecture (tuned Random Forest baseline → "
                       "Platt-scaling probability compensation)",
             ha="center", va="top", fontsize=10.5, color=C["subtitle"])

    col_y, col_h = 8, 82
    cols = [(2, 27, C["col_in"], C["col_in_edge"], "Inputs", "#374151"),
            (30, 27, C["col_s1"], C["col_s1_edge"], "Stage 1 — Base Classifier", "#1E40AF"),
            (58, 28, C["col_s2"], C["col_s2_edge"], "Stage 2 — Compensation", "#5B21B6"),
            (87, 27, C["col_out"], C["col_out_edge"], "Output", "#166534")]
    for x0, w, fc, ec, label, tc in cols:
        col_bg(ax, x0, col_y, w, col_h, fc, ec)
        ax.text(x0 + w / 2, col_y + col_h - 0.8, label, ha="center", va="top",
                 fontsize=12.5, fontweight="bold", color=tc)

    # --- Inputs column ---
    in_cases = box(ax, 4, 78.5, 23, 8.5, "Weekly Dengue Cases\nHistorical district-week counts\n(25 districts; MoH epi-weeks)",
                    C["green"], C["green_edge"], C["green_text"], fs=8.3)
    in_climate = box(ax, 4, 67, 23, 9.5, "Climate Features\nPrecipitation / temp / humidity\n(lags + current week)\nFold-aware anomalies",
                      C["blue"], C["blue_edge"], C["blue_text"], fs=8.3)
    in_eng = box(ax, 4, 55, 23, 9.5, "Engineered Features\nCase lags 1–4 · rolling stats\nSeasonal / monsoon\nCase-anomaly lags · District",
                 C["blue"], C["blue_edge"], C["blue_text"], fs=8.3)
    in_pre = box(ax, 4, 44.5, 23, 8, "Module 2 Preprocessing\nWeek-53 kept unmerged\nSeasonal-naive gaps · is_imputed mask",
                 "#E0E7FF", "#4F46E5", "#312E81", fs=7.8)
    in_src = box(ax, 4, 34.5, 23, 7.5, "Data Sources\nEpidemiology Unit, MoH\nOpen-Meteo climate API",
                 C["white"], "#6B7280", "#374151", fs=8.3)
    box(ax, 5.5, 25, 20, 6.5, "Unlike Module 1:\nweek 53 NOT merged",
        C["note_red"], C["note_red_edge"], C["note_red_text"], fs=8, dashed=True)

    # --- Stage 1 column ---
    s1_label = box(ax, 32, 76, 23, 10.5, "Epidemic-Threshold Labels\noutbreak = 1 if cases >\nmean + k × SD\n(prior years only · harmonic)",
                    C["purple"], C["purple_edge"], C["purple_text"], fs=8.3)
    s1_model = box(ax, 32, 60, 23, 10, "Random Forest (tuned)\nPooled outbreak classifier\n(climate included in Stage 1)",
                   C["navy"], C["navy"], C["white"], fs=9.5, weight="bold")
    s1_prob = box(ax, 32, 47.5, 23, 7.5, "Predicted Probability\np̂ per district-week",
                  C["grey_box"], C["grey_edge"], "#111827", fs=9)
    box(ax, 33.5, 37, 20, 6.5, "Class imbalance via\nclass_weight (no SMOTE)",
        C["note_red"], C["note_red_edge"], C["note_red_text"], fs=8, dashed=True)
    box(ax, 33.5, 27.5, 20, 6.5, "Climate enters Stage 1\n(unlike Module 1)",
        C["note_amber"], C["note_amber_edge"], C["note_amber_text"], fs=8, dashed=True)

    arrow(ax, 15.5, 78.5, 43.5, 86.5, C["green_edge"], lw=1.6)
    arrow(ax, 15.5, 78.5, 43.5, 70, C["green_edge"], lw=1.6)
    arrow(ax, 27, 71.5, 32, 66, C["blue_edge"], lw=1.4)
    arrow(ax, 27, 59.5, 32, 65, C["blue_edge"], lw=1.4)
    arrow(ax, 27, 48.5, 32, 62, C["grey_edge"], lw=1.1, ls=(0, (4, 3)))
    arrow(ax, 43.5, 76, 43.5, 70, C["purple_edge"], lw=1.6)
    arrow(ax, 43.5, 60, 43.5, 55, "#1E40AF", lw=1.6)

    # --- Stage 2 column ---
    s2_model = box(ax, 60.5, 68.5, 23, 9.5, "Platt Scaling\nProbability compensation\n/ calibration layer",
                   C["navy"], C["navy"], C["white"], fs=9.5, weight="bold")
    s2_cal = box(ax, 60.5, 56.5, 23, 7.5, "Calibrated Probability\np̃ = g(logit(p̂))",
                 C["red"], C["red_edge"], C["red_text"], fs=9)
    box(ax, 62, 46.5, 20, 6.5, "Not case-residual regression\n— probability calibration",
        C["note_amber"], C["note_amber_edge"], C["note_amber_text"], fs=7.8, dashed=True)
    box(ax, 60.5, 37, 23, 6, "Benchmarked vs isotonic\nand stacked XGBoost",
        C["grey_light"], C["grey_line"], "#374151", fs=8, dashed=True)

    arrow(ax, 55, 52, 60.5, 73, C["purple_edge"], lw=1.6)
    arrow(ax, 72, 68.5, 72, 64, C["navy"], lw=1.6)

    # --- Output column ---
    out_dec = box(ax, 89, 71, 23, 9.5, "Decision Outputs\nalert_flag\nrisk_tier (low / medium / high)",
                  C["green"], C["green_edge"], C["green_text"], fs=9)
    out_eval = box(ax, 89, 58.5, 23, 10, "Evaluation\nPR-AUC · ROC-AUC\nBrier · BSS\nWalk-forward + holdout",
                   C["white"], "#6B7280", "#374151", fs=8.3)
    box(ax, 89, 47, 23, 6.5, "Fixed absolute\nprobability thresholds",
        C["grey_light"], C["grey_line"], "#374151", fs=8, dashed=True)

    arrow(ax, 83.5, 60, 89, 75, C["green_edge"], lw=1.6)
    arrow(ax, 100.5, 71, 100.5, 68.5, "#6B7280", lw=1.3)

    fig.tight_layout(pad=0.4)
    out = OUT / "figure_5_4_module2_architecture.png"
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print("Wrote", out)
    return out


if __name__ == "__main__":
    main()
