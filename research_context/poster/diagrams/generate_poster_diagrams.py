"""Poster-presentation diagrams for the final evaluation (2026-08-07).

Four figures, simplified from the report's Figure 5.1/5.3/5.4/5.5 for
at-a-distance poster legibility (bigger type, fewer words per box, one
headline result per module). Content verified against the latest
MODULE_CONTEXT.md / RESEARCH_DECISIONS.md at the time of writing:
  - Module 1: SARIMA -> XGBoost residual compensation (unchanged, current).
  - Module 2: Random Forest (tuned, Decision 047) -> Platt scaling
    (Decision 047/M2-013 - flipped from isotonic).
  - Module 3: KDE + Moran's I -> Random Forest residual + iterative loop,
    alpha=0.05 (unchanged, current).

Every box()/arrow() call below drives BOTH the rendered PNG (matplotlib)
and the companion .drawio XML (mxGraph cells recorded as a side effect) in
the same pass - the two outputs are generated from one source of truth and
cannot drift apart the way the report's Figure 5.1/5.4 diagrams did.

Usage: python generate_poster_diagrams.py [overall|module1|module2|module3|all]
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent

P = {
    "bg": "#FFFFFF",
    "ink": "#111827",
    "sub": "#4B5563",
    "m1": "#16A34A", "m1_fill": "#DCFCE7", "m1_dark": "#14532D",
    "m2": "#2563EB", "m2_fill": "#DBEAFE", "m2_dark": "#1E3A8A",
    "m3": "#D97706", "m3_fill": "#FEF3C7", "m3_dark": "#78350F",
    "navy": "#1E3A8A",
    "grey": "#E5E7EB", "grey_edge": "#6B7280",
    "result": "#111827", "result_fill": "#FDE68A", "result_edge": "#B45309",
}

# --- drawio recording state (reset per figure by new_fig()) ---
_cells = []
_next_id = [1]
_page = {"w": 1500, "h": 1060}


def _new_id():
    _next_id[0] += 1
    return f"c{_next_id[0]}"


def _to_mx(x, y, w, h):
    sx, sy = _page["w"] / 100.0, _page["h"] / 100.0
    return x * sx, (100 - y - h) * sy, w * sx, h * sy


def box(ax, x, y, w, h, text, fc, ec, tc="#111827", fs=15, weight="bold", pad=0.02, lw=2.2, round_size=0.03):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={pad},rounding_size={round_size}",
                                 linewidth=lw, facecolor=fc, edgecolor=ec))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
             fontweight=weight, linespacing=1.35, wrap=True)
    mx, my, mw, mh = _to_mx(x, y, w, h)
    bold = ";fontStyle=1" if weight == "bold" else ""
    value = escape(text).replace("\n", "&lt;br&gt;")
    style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fc};strokeColor={ec};"
             f"fontColor={tc};fontSize={fs}{bold};align=center;strokeWidth={lw};")
    _cells.append(("vertex", _new_id(), value, style, mx, my, mw, mh))


def arrow(ax, x1, y1, x2, y2, color="#374151", lw=3.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=3, shrinkB=3))
    sx, sy = _page["w"] / 100.0, _page["h"] / 100.0
    mx1, my1 = x1 * sx, (100 - y1) * sy
    mx2, my2 = x2 * sx, (100 - y2) * sy
    style = f"endArrow=block;endFill=1;html=1;strokeColor={color};strokeWidth={lw};"
    _cells.append(("edge", _new_id(), None, style, mx1, my1, mx2, my2))


def new_fig(w=15, h=10.6):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(P["bg"])
    _cells.clear()
    _next_id[0] = 1
    _page["w"], _page["h"] = w * 100, h * 100
    return fig, ax


def save_drawio(name, diagram_name):
    parts = [
        '<mxfile host="app.diagrams.net" agent="Codexon FYP Poster" version="22.1.0" type="device">',
        f'  <diagram id="{name.replace(".drawio", "")}" name="{escape(diagram_name)}">',
        f'    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
        f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{_page["w"]:.0f}" '
        f'pageHeight="{_page["h"]:.0f}" math="0" shadow="0">',
        "      <root>",
        '        <mxCell id="0" />',
        '        <mxCell id="1" parent="0" />',
    ]
    for kind, cid, value, style, a, b, c, d in _cells:
        if kind == "vertex":
            parts.append(f'        <mxCell id="{cid}" value="{value}" style="{style}" vertex="1" parent="1">')
            parts.append(f'          <mxGeometry x="{a:.1f}" y="{b:.1f}" width="{c:.1f}" height="{d:.1f}" as="geometry" />')
            parts.append("        </mxCell>")
        else:
            parts.append(f'        <mxCell id="{cid}" style="{style}" edge="1" parent="1">')
            parts.append('          <mxGeometry relative="1" as="geometry">')
            parts.append(f'            <mxPoint x="{a:.1f}" y="{b:.1f}" as="sourcePoint" />')
            parts.append(f'            <mxPoint x="{c:.1f}" y="{d:.1f}" as="targetPoint" />')
            parts.append("          </mxGeometry>")
            parts.append("        </mxCell>")
    parts += ["      </root>", "    </mxGraphModel>", "  </diagram>", "</mxfile>", ""]
    out = OUT / name
    out.write_text("\n".join(parts), encoding="utf-8")
    print("Wrote", out)


def save(fig, name):
    out = OUT / name
    fig.tight_layout(pad=0.5)
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor=P["bg"])
    plt.close(fig)
    print("Wrote", out)


def result_pill(ax, x, y, w, h, text):
    box(ax, x, y, w, h, text, P["result_fill"], P["result_edge"], P["result"], fs=13.5, weight="bold", round_size=0.5)


# ---------------------------------------------------------------------------

def overall():
    fig, ax = new_fig(17, 11)
    ax.text(50, 97, "Residual Compensation Framework for Dengue Risk Prediction",
             ha="center", va="top", fontsize=25, fontweight="bold", color=P["ink"])
    ax.text(50, 92.3, "A hybrid two-stage design: a simple baseline model, corrected by a learned compensation model",
             ha="center", va="top", fontsize=14.5, color=P["sub"], style="italic")

    # Data sources
    srcs = [(3, "Weekly Dengue Cases", "MoH, 25 districts, 2007–2026"),
            (37, "Climate Data", "Open-Meteo: rainfall, temperature, humidity"),
            (71, "Spatial & Demographic", "GADM districts, census population, elevation")]
    for x0, t1, t2 in srcs:
        box(ax, x0, 82, 26, 7, f"{t1}\n{t2}", "#E0F2FE", "#0284C7", "#0C4A6E", fs=12.5, weight="bold")
    for x0, *_ in srcs:
        arrow(ax, x0 + 13, 82, 50, 78.5, "#0284C7", lw=2.2)

    box(ax, 15, 71.5, 70, 6.5, "Shared Preprocessing  —  district merge · epi-week calendar · climate aggregation · population interpolation",
        P["navy"], P["navy"], "white", fs=13, weight="bold")

    cols = [
        (2, P["m1"], P["m1_fill"], P["m1_dark"], "MODULE 1\nCase Forecasting",
         "Stage 1\nSARIMA\n(per district)", "Stage 2\nXGBoost\n(residual compensation)",
         "Weekly Case\nForecast", "Median MASE\n↓ 43.5% (validation)\n↓ 32.7% (holdout)"),
        (35, P["m2"], P["m2_fill"], P["m2_dark"], "MODULE 2\nOutbreak Risk Classification",
         "Stage 1\nRandom Forest\n(tuned)", "Stage 2\nPlatt Scaling\n(probability calibration)",
         "Alert Flag &\nRisk Tier", "Holdout\nPR-AUC 0.42\nROC-AUC 0.91"),
        (68, P["m3"], P["m3_fill"], P["m3_dark"], "MODULE 3\nSpatial Hotspot Detection",
         "Stage 1\nKDE + Moran's I\n(spatial baseline)", "Stage 2\nRandom Forest\n(α = 0.05, iterative)",
         "Hybrid Risk /\nHotspot Map", "Moran's I\n= 0.70 (p = 0.001)"),
    ]
    for x0, edge, fill, dark, title, s1, s2, out, result in cols:
        w = 30
        box(ax, x0, 63, w, 5.5, title, fill, edge, dark, fs=13.5, weight="bold")
        arrow(ax, x0 + w / 2, 71.5, x0 + w / 2, 68.5, edge, lw=2.4)
        box(ax, x0, 53.5, w, 8, s1, "white", edge, dark, fs=12.5)
        arrow(ax, x0 + w / 2, 63, x0 + w / 2, 61.5, edge, lw=2.4)
        box(ax, x0, 43, w, 8.5, s2, edge, edge, "white", fs=12.5, weight="bold")
        arrow(ax, x0 + w / 2, 53.5, x0 + w / 2, 51.5, edge, lw=2.4)
        box(ax, x0, 35.5, w, 6, out, fill, edge, dark, fs=13, weight="bold")
        arrow(ax, x0 + w / 2, 43, x0 + w / 2, 41.5, edge, lw=2.4)
        result_pill(ax, x0 + 1.5, 27, w - 3, 6.5, result)
        arrow(ax, x0 + w / 2, 35.5, x0 + w / 2, 33.5, edge, lw=1.8)

    ax.annotate("", xy=(35, 47.2), xytext=(32, 47.2),
                arrowprops=dict(arrowstyle="-|>", color="#9CA3AF", lw=2.0, linestyle=(0, (5, 3))))
    ax.text(33.5, 48.7, "operational forward only", ha="center", fontsize=9.5, color="#6B7280", style="italic")

    box(ax, 15, 15.5, 70, 7.5,
        "Streamlit Early-Warning Dashboard  —  4 pages: Overview · Research Evidence · Operational Monitoring · Prospective Tracking",
        "#ECFDF5", "#047857", "#065F46", fs=13, weight="bold")
    for x0, edge, *_ in cols:
        arrow(ax, x0 + 15, 27, 50, 23.5, edge, lw=2.0)

    ax.text(50, 10.5, "Common principle: Stage 1 baseline  +  Stage 2 residual / error correction  →  compensated module output",
             ha="center", fontsize=14, style="italic", color=P["sub"])

    save(fig, "poster_figure_overall_framework.png")
    save_drawio("poster_figure_overall_framework.drawio", "Overall Framework")


def module1():
    fig, ax = new_fig(15, 10.6)
    ax.text(50, 96.5, "Module 1 — Hybrid Time-Series Case Forecasting", ha="center", va="top",
             fontsize=24, fontweight="bold", color=P["m1_dark"])
    ax.text(50, 90.8, "SARIMA baseline, corrected by an XGBoost model trained on the baseline's own errors",
             ha="center", va="top", fontsize=13.5, color=P["sub"], style="italic")

    box(ax, 5, 76, 90, 8, "Input: Weekly dengue case counts per district (25 districts, 2007–2026)",
        "#DCFCE7", P["m1"], P["m1_dark"], fs=14.5, weight="bold")
    arrow(ax, 50, 76, 50, 71, P["m1"], lw=3)

    box(ax, 8, 58, 40, 12.5, "Stage 1 — SARIMA\nPer-district baseline forecast\nfrom historical cases only\n(climate deliberately excluded)",
        "white", P["m1"], P["m1_dark"], fs=13.5)
    box(ax, 52, 58, 40, 12.5, "Stage 2 — XGBoost\nPooled model trained on\nout-of-sample residuals\n(climate + lag + seasonal features)",
        P["m1"], P["m1"], "white", fs=13.5, weight="bold")

    arrow(ax, 48, 64.2, 52, 64.2, "#374151", lw=3)
    ax.text(50, 67.2, "residual =\nactual − ŷ_SARIMA", ha="center", fontsize=11, color=P["ink"], style="italic")

    box(ax, 20, 42, 60, 8.5, "Final Prediction  =  ŷ_SARIMA  +  predicted residual  (clipped ≥ 0)",
        "#FEF3C7", "#D97706", "#78350F", fs=15, weight="bold")
    arrow(ax, 28, 58, 35, 50.5, P["m1"], lw=2.6)
    arrow(ax, 72, 58, 65, 50.5, P["m1"], lw=2.6)

    arrow(ax, 50, 42, 50, 36.5, "#374151", lw=3)
    box(ax, 15, 27, 70, 8, "Output: Compensated weekly case forecast per district",
        "#DCFCE7", P["m1"], P["m1_dark"], fs=14.5, weight="bold")

    result_pill(ax, 10, 6, 80, 15,
                "Validated result (walk-forward + 2-year untouched holdout):\n"
                "25/25 districts improve on validation MASE · 23/25 improve on holdout\n"
                "Median MASE improvement: 43.5% (validation) · 32.7% (holdout)\n"
                "Evaluated with RMSE, MAE, sMAPE, MASE, and the Diebold–Mariano test")

    save(fig, "poster_figure_module1.png")
    save_drawio("poster_figure_module1.drawio", "Module 1")


def module2():
    fig, ax = new_fig(15, 10.6)
    ax.text(50, 96.5, "Module 2 — Hybrid Outbreak Risk Classification", ha="center", va="top",
             fontsize=24, fontweight="bold", color=P["m2_dark"])
    ax.text(50, 90.8, "A tuned classifier's probabilities, corrected by a calibration model so the numbers can be trusted",
             ha="center", va="top", fontsize=13.5, color=P["sub"], style="italic")

    box(ax, 5, 76, 90, 8,
        "Input: Weekly cases + climate + engineered features  →  epidemic-threshold label (cases > mean + k·SD, k = 3.0, prior years only)",
        "#DBEAFE", P["m2"], P["m2_dark"], fs=12.8, weight="bold")
    arrow(ax, 50, 76, 50, 71, P["m2"], lw=3)

    box(ax, 8, 58, 40, 12.5, "Stage 1 — Random Forest\n(tuned)\nPooled outbreak classifier\nclimate included at this stage",
        "white", P["m2"], P["m2_dark"], fs=13.5)
    box(ax, 52, 58, 40, 12.5, "Stage 2 — Platt Scaling\nLogistic regression on the\nlog-odds of Stage 1's probability\n(calibration, not case regression)",
        P["m2"], P["m2"], "white", fs=13, weight="bold")

    arrow(ax, 48, 64.2, 52, 64.2, "#374151", lw=3)
    ax.text(50, 67.2, "p̂ per\ndistrict-week", ha="center", fontsize=11, color=P["ink"], style="italic")

    box(ax, 20, 42, 60, 8.5, "Calibrated Probability  p̃ = g(logit(p̂))",
        "#FEF3C7", "#D97706", "#78350F", fs=15, weight="bold")
    arrow(ax, 28, 58, 35, 50.5, P["m2"], lw=2.6)
    arrow(ax, 72, 58, 65, 50.5, P["m2"], lw=2.6)

    arrow(ax, 50, 42, 50, 36.5, "#374151", lw=3)
    box(ax, 15, 27, 70, 8, "Output: alert_flag  +  risk_tier (low / medium / high)",
        "#DBEAFE", P["m2"], P["m2_dark"], fs=14.5, weight="bold")

    result_pill(ax, 10, 6, 80, 15,
                "Validated result (walk-forward + 2-year untouched holdout):\n"
                "Holdout PR-AUC 0.42 · ROC-AUC 0.91 · Brier 0.018\n"
                "Risk tiers separate cleanly: observed outbreak rate\n"
                "0.6% (low) → 20.4% (medium) → 62.5% (high)")

    save(fig, "poster_figure_module2.png")
    save_drawio("poster_figure_module2.drawio", "Module 2")


def module3():
    fig, ax = new_fig(15, 10.6)
    ax.text(50, 96.5, "Module 3 — Hybrid Spatial Hotspot Detection", ha="center", va="top",
             fontsize=24, fontweight="bold", color=P["m3_dark"])
    ax.text(50, 90.8, "A spatial clustering baseline, refined by an iterative, environmentally-aware correction loop",
             ha="center", va="top", fontsize=13.5, color=P["sub"], style="italic")

    box(ax, 5, 76, 90, 8,
        "Input: Weekly cases + climate + spatial/demographic covariates (GADM Level-1, 25 districts)",
        "#FEF3C7", P["m3"], P["m3_dark"], fs=14, weight="bold")
    arrow(ax, 50, 76, 50, 71, P["m3"], lw=3)

    box(ax, 8, 58, 40, 12.5, "Stage 1 — KDE + Moran's I\nCase-weighted kernel density\nover district centroids,\nvalidated by spatial clustering",
        "white", P["m3"], P["m3_dark"], fs=13)
    box(ax, 52, 58, 40, 12.5, "Stage 2 — Random Forest\nIterative update:\nRiskₜ = Riskₜ₋₁ + α·Δ̂\n(α = 0.05, converges in 1 pass)",
        P["m3"], P["m3"], "white", fs=13, weight="bold")

    arrow(ax, 48, 64.2, 52, 64.2, "#374151", lw=3)
    ax.text(50, 67.2, "rescaled\nbaseline risk", ha="center", fontsize=11, color=P["ink"], style="italic")

    box(ax, 20, 42, 60, 8.5, "Residual = Actual case intensity − Current risk",
        "#DBEAFE", "#2563EB", "#1E3A8A", fs=14.5, weight="bold")
    arrow(ax, 28, 58, 35, 50.5, P["m3"], lw=2.6)
    arrow(ax, 72, 58, 65, 50.5, P["m3"], lw=2.6)

    arrow(ax, 50, 42, 50, 36.5, "#374151", lw=3)
    box(ax, 15, 27, 70, 8, "Output: Hybrid Risk / Hotspot Map (district-week; IDW surface for visualization only)",
        "#FEF3C7", P["m3"], P["m3_dark"], fs=13, weight="bold")

    result_pill(ax, 10, 6, 80, 15,
                "Validated result (spatial K-means cross-validation, 5 folds):\n"
                "Global Moran's I = 0.70 (p = 0.001) — genuine spatial clustering confirmed\n"
                "Stage 2 adds explanatory value (population density + climate timing)\n"
                "though the small, stability-tuned α leaves aggregate case-fit unchanged")

    save(fig, "poster_figure_module3.png")
    save_drawio("poster_figure_module3.drawio", "Module 3")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"overall": overall, "module1": module1, "module2": module2, "module3": module3}
    if target == "all":
        for fn in fns.values():
            fn()
    else:
        fns[target]()
