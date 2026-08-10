"""Generate Figure 5.1 — high-level architecture of the residual compensation framework."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

# Palette aligned with existing Chapter 5/6 diagrams (avoid purple-on-white AI look)
C = {
    "bg": "#FFFFFF",
    "title": "#111827",
    "text": "#1F2937",
    "muted": "#4B5563",
    "raw": "#E0F2FE",
    "raw_edge": "#0284C7",
    "shared": "#1E3A8A",
    "shared_text": "#FFFFFF",
    "m1": "#DCFCE7",
    "m1_edge": "#15803D",
    "m2": "#DBEAFE",
    "m2_edge": "#1D4ED8",
    "m3": "#FEF3C7",
    "m3_edge": "#B45309",
    "eval": "#F3F4F6",
    "eval_edge": "#4B5563",
    "dash": "#ECFDF5",
    "dash_edge": "#047857",
}


def box(ax, x, y, w, h, text, fc, ec, tc="#1F2937", fs=9, weight="normal"):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        linewidth=1.4,
        facecolor=fc,
        edgecolor=ec,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        color=tc,
        fontweight=weight,
        wrap=True,
        linespacing=1.25,
    )
    return patch


def arrow(ax, x1, y1, x2, y2, color="#4B5563", lw=1.5, ls="-"):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=lw,
            linestyle=ls,
            shrinkA=2,
            shrinkB=2,
        ),
    )


def main() -> Path:
    fig, ax = plt.subplots(figsize=(13.5, 9.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    ax.text(
        50,
        97.5,
        "Figure 5.1  Top-level architecture of the Residual Compensation Modeling Framework",
        ha="center",
        va="top",
        fontsize=13,
        fontweight="bold",
        color=C["title"],
    )

    # Layer 1 — Data acquisition
    ax.text(50, 92.5, "1. Data acquisition", ha="center", fontsize=10, fontweight="semibold", color=C["muted"])
    box(ax, 8, 82, 26, 9, "MoH WER\nweekly dengue cases\n(25 districts)", C["raw"], C["raw_edge"], fs=8.5)
    box(ax, 37, 82, 26, 9, "Open-Meteo climate\nrainfall · temperature\nhumidity (weekly)", C["raw"], C["raw_edge"], fs=8.5)
    box(ax, 66, 82, 26, 9, "Spatial / demographic\nGADM L1 · census pop.\nelevation", C["raw"], C["raw_edge"], fs=8.5)

    # Layer 2 — Shared preprocessing
    arrow(ax, 21, 82, 50, 78, C["raw_edge"])
    arrow(ax, 50, 82, 50, 78, C["raw_edge"])
    arrow(ax, 79, 82, 50, 78, C["raw_edge"])
    box(
        ax,
        22,
        70,
        56,
        8,
        "2. Shared preprocessing (Decision 013 — module-agnostic only)\n"
        "Kalmunai→Ampara · epi-week calendar · weekly climate aggregation · population interpolate",
        C["shared"],
        C["shared"],
        tc=C["shared_text"],
        fs=8.5,
        weight="semibold",
    )

    # Layer 3 — three modules
    ax.text(50, 66.5, "3. Module-specific residual compensation pipelines (parallel peers)", ha="center", fontsize=10, fontweight="semibold", color=C["muted"])

    # Module columns
    cols = [
        (
            5,
            C["m1"],
            C["m1_edge"],
            "Module 1\nCase Forecasting",
            [
                "Module-specific prep\nweek-53 merge · case series",
                "Stage 1\nSARIMA (cases only)",
                "Stage 2\nXGBoost residual\n(+ climate lags/anomalies)",
                "Output\nweekly case forecast",
            ],
        ),
        (
            37,
            C["m2"],
            C["m2_edge"],
            "Module 2\nOutbreak Classification",
            [
                "Module-specific prep\nweek-53 keep · labels",
                "Stage 1\nRandom Forest (tuned)",
                "Stage 2\nPlatt scaling",
                "Output\nalert / risk tiers",
            ],
        ),
        (
            69,
            C["m3"],
            C["m3_edge"],
            "Module 3\nSpatial Hotspots",
            [
                "Module-specific prep\nspatial master table",
                "Stage 1\nKDE + Moran’s I",
                "Stage 2\nRF relative residual (α=1)",
                "Output\nhotspot risk surface",
            ],
        ),
    ]

    # fan-out from shared
    col_boxes = {}
    for x0, fc, ec, title, steps in cols:
        cx = x0 + 13
        arrow(ax, 50, 70, cx, 63.5, ec, lw=1.3)
        box(ax, x0, 60.5, 26, 3.2, title, fc, ec, fs=8.5, weight="bold")
        y = 55.5
        step_boxes = []
        for i, step in enumerate(steps):
            by = y - 0.2
            box(ax, x0, by, 26, 5.0, step, "#FFFFFF", ec, fs=7.8)
            step_boxes.append((x0, by, 26, 5.0))
            if i < len(steps) - 1:
                arrow(ax, cx, y - 0.2, cx, y - 1.0, ec, lw=1.1)
            y -= 6.2
        col_boxes[title] = step_boxes

    m1_output = col_boxes["Module 1\nCase Forecasting"][3]
    m3_output = col_boxes["Module 3\nSpatial Hotspots"][3]

    # Optional dashed operational link M1 -> M2 (Decision 027, forward risk features only)
    ax.annotate(
        "",
        xy=(37, 36),
        xytext=(31, 36),
        arrowprops=dict(arrowstyle="-|>", color="#9CA3AF", lw=1.2, linestyle=(0, (4, 3))),
    )
    ax.text(34, 37.3, "operational\nforward only", ha="center", va="bottom", fontsize=6.5, color="#6B7280")

    # Dashed operational link M1 -> M3 (Decision 031 — forecast case counts feed
    # forward Stage 1 KDE weighting only, never training/evaluation). Routed through
    # the empty band below the output row so it doesn't cross Module 2's boxes.
    y_out_mid = m1_output[1] + m1_output[3] / 2
    ax.annotate(
        "",
        xy=(m3_output[0], y_out_mid),
        xytext=(m1_output[0] + m1_output[2], y_out_mid),
        arrowprops=dict(
            arrowstyle="-|>",
            color="#9CA3AF",
            lw=1.2,
            linestyle=(0, (4, 3)),
            connectionstyle="arc3,rad=-0.35",
        ),
    )
    ax.text(63, 25.8, "operational forward only\n(Decision 031)", ha="center", fontsize=6.5, color="#6B7280")

    # Layer 4 — Evaluation
    box(
        ax,
        18,
        14.5,
        64,
        5.5,
        "4. Evaluation design\n"
        "Modules 1–2: walk-forward folds + untouched 2-year holdout · Module 3: spatial K-means CV\n"
        "Research evidence tier kept separate from operational live/forward outputs",
        C["eval"],
        C["eval_edge"],
        fs=8,
    )
    for x0, _, ec, _, _ in cols:
        arrow(ax, x0 + 13, 30.5, 50, 20.2, C["eval_edge"], lw=1.1)

    # Layer 5 — Dashboard
    box(
        ax,
        22,
        4.5,
        56,
        7.5,
        "5. Streamlit early-warning dashboard (read-only decision support)\n"
        "Case forecasts · calibrated outbreak risk / alerts · spatial hotspot maps\n"
        "Research vs operational evidence labels · no Command Centre / scenario-simulation claims",
        C["dash"],
        C["dash_edge"],
        fs=8.2,
        weight="semibold",
    )
    arrow(ax, 50, 14.5, 50, 12.2, C["dash_edge"], lw=1.5)

    ax.text(
        50,
        1.5,
        "Residual compensation philosophy: Stage 1 baseline + Stage 2 residual/error correction → improved module output",
        ha="center",
        fontsize=8,
        style="italic",
        color=C["muted"],
    )

    fig.tight_layout(pad=0.4)
    out = OUT / "figure_5_1_system_architecture.png"
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor=C["bg"])
    # Also alias as whole-system name for easy finding
    alias = OUT / "figure_high_level_system_architecture.png"
    fig.savefig(alias, dpi=220, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print("Wrote", out)
    print("Wrote", alias)
    return out


if __name__ == "__main__":
    main()
