"""Generate Figure 5.6 - Integration and Early-Warning Dashboard (four columns:
Module Outputs | Integration Layer | Dashboard Views | Evidence Tiers).

Content mirrors figure_5_6_integration_dashboard.drawio - regenerate this PNG
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
    "col1": "#F3F4F6", "col1_edge": "#D1D5DB",
    "col2": "#DBEAFE", "col2_edge": "#93C5FD",
    "col3": "#EDE9FE", "col3_edge": "#C4B5FD",
    "col4": "#DCFCE7", "col4_edge": "#86EFAC",
    "green": "#86EFAC", "green_edge": "#15803D", "green_text": "#14532D",
    "blue": "#BFDBFE", "blue_edge": "#2563EB", "blue_text": "#1E3A8A",
    "purple": "#DDD6FE", "purple_edge": "#7C3AED", "purple_text": "#4C1D95",
    "amber": "#FDE68A", "amber_edge": "#B45309", "amber_text": "#78350F",
    "navy": "#1E3A8A",
    "grey_box": "#E5E7EB", "grey_edge": "#4B5563",
    "note_red": "#FEE2E2", "note_red_edge": "#DC2626", "note_red_text": "#991B1B",
    "note_amber": "#FEF3C7", "note_amber_edge": "#D97706", "note_amber_text": "#92400E",
    "white": "#FFFFFF", "grey_light": "#F9FAFB", "grey_line": "#9CA3AF",
}


def box(ax, x, y, w, h, text, fc, ec, tc="#111827", fs=9.5, weight="normal", dashed=False):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.5,
        linestyle="dashed" if dashed else "-",
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
    fig, ax = plt.subplots(figsize=(14, 9.2))
    ax.set_xlim(0, 116)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    ax.text(58, 97.5, "Integration and Early-Warning Dashboard", ha="center", va="top",
             fontsize=17, fontweight="bold", color=C["title"])
    ax.text(58, 94.2, "Figure 5.6 — Module outputs feed a 4-page Streamlit decision-support app\n"
                       "(research, operational, and prospective evidence tiers)",
             ha="center", va="top", fontsize=10, color=C["subtitle"])

    col_y, col_h = 6, 82
    cols = [(2, 27, C["col1"], C["col1_edge"], "Module Outputs", "#374151"),
            (30, 27, C["col2"], C["col2_edge"], "Integration Layer", "#1E40AF"),
            (58, 28, C["col3"], C["col3_edge"], "Dashboard Views", "#5B21B6"),
            (87, 27, C["col4"], C["col4_edge"], "Evidence Tiers", "#166534")]
    for x0, w, fc, ec, label, tc in cols:
        col_bg(ax, x0, col_y, w, col_h, fc, ec)
        ax.text(x0 + w / 2, col_y + col_h - 0.9, label, ha="center", va="top",
                 fontsize=12.5, fontweight="bold", color=tc)

    # --- Module Outputs ---
    m1 = box(ax, 4, 73, 23, 9, "Module 1\nCompensated weekly\ncase forecasts",
              C["green"], C["green_edge"], C["green_text"], fs=8.6)
    m2 = box(ax, 4, 61, 23, 9, "Module 2\nCalibrated probability\nalert_flag · risk_tier",
             C["blue"], C["blue_edge"], C["blue_text"], fs=8.6)
    m3 = box(ax, 4, 49, 23, 9, "Module 3\nHybrid hotspot /\nspatial risk surface",
             C["purple"], C["purple_edge"], C["purple_text"], fs=8.6)
    box(ax, 6, 39, 19, 6.5, "Magnitude · probability ·\ngeography kept distinct",
        C["note_amber"], C["note_amber_edge"], C["note_amber_text"], fs=7.8, dashed=True)

    # --- Integration layer ---
    app = box(ax, 33, 60, 21, 12, "Streamlit Multipage App\nSidebar + st.navigation\nRead-only consumer of\nversioned analytical artifacts",
              C["navy"], C["navy"], C["white"], fs=8.8, weight="bold")
    box(ax, 34.5, 51, 18, 6, "Not a fourth\nmodelling stage",
        C["note_red"], C["note_red_edge"], C["note_red_text"], fs=8, dashed=True)
    box(ax, 33, 41.5, 21, 7, "M1 → M2 lag substitution:\noperational forward only",
        C["grey_light"], C["grey_line"], "#374151", fs=7.8, dashed=True)

    arrow(ax, 27, 77.5, 33, 68, C["green_edge"], lw=1.6)
    arrow(ax, 27, 65.5, 33, 66, C["blue_edge"], lw=1.6)
    arrow(ax, 27, 53.5, 33, 64, C["purple_edge"], lw=1.6)

    # --- Dashboard views (four pages, fixed order) ---
    v1 = box(ax, 61, 76, 23, 7, "1. Overview\nCold-open story",
              C["grey_box"], C["grey_edge"], "#111827", fs=8.6)
    v2 = box(ax, 61, 67, 23, 7, "2. Research Evidence\nHoldout-validated metrics",
              C["grey_box"], C["grey_edge"], "#111827", fs=8.6)
    v3 = box(ax, 61, 58, 23, 7, "3. Operational Monitoring\nLive / forward outputs",
              C["grey_box"], C["grey_edge"], "#111827", fs=8.6)
    v4 = box(ax, 61, 49, 23, 7, "4. Prospective Tracking\nSelf-checking accuracy trackers",
              C["grey_box"], C["grey_edge"], "#111827", fs=8.6)
    box(ax, 62.5, 40, 20, 6.5, "No scenario simulation\n/ Command Centre stack",
        C["note_red"], C["note_red_edge"], C["note_red_text"], fs=7.8, dashed=True)

    for vy in (79.5, 70.5, 61.5, 52.5):
        arrow(ax, 54, 66, 61, vy, C["purple_edge"], lw=1.3)

    # --- Evidence tiers (three) ---
    e_res = box(ax, 89, 74, 23, 8, "Research Evidence\nHoldout-validated metrics\n(basis for thesis claims)",
                C["green"], C["green_edge"], C["green_text"], fs=8.6)
    e_ops = box(ax, 89, 63, 23, 8, "Operational Prototype\nForward forecasts / live risk\n(labeled separately)",
                C["amber"], C["amber_edge"], C["amber_text"], fs=8.6)
    e_pro = box(ax, 89, 52, 23, 8, "Prospective Tracking\nLogged forward predictions,\nreconciled once real weeks resolve",
                C["blue"], C["blue_edge"], C["blue_text"], fs=8.3)
    box(ax, 89, 42, 23, 7, "Intended users\nPublic health analysts\n(decision support)",
        C["white"], "#6B7280", "#374151", fs=8.3)

    arrow(ax, 56, 66, 89, 78, C["green_edge"], lw=1.6)
    arrow(ax, 56, 63, 89, 67, C["amber_edge"], lw=1.6, ls=(0, (4, 3)))
    arrow(ax, 56, 60, 89, 56, C["blue_edge"], lw=1.6, ls=(0, (4, 3)))

    fig.tight_layout(pad=0.4)
    out = OUT / "figure_5_6_integration_dashboard.png"
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print("Wrote", out)
    return out


if __name__ == "__main__":
    main()
