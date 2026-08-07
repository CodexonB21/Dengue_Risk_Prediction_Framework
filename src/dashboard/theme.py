"""Shared color constants for the dashboard.

Two separate color languages are used across the app, deliberately kept apart:

1. **Module identity** (`MODULE_COLORS`) — chrome only: section headers, badges,
   dividers, and non-risk-magnitude chart series (e.g. "SARIMA only" vs.
   "Hybrid" MASE bars). Copied verbatim from
   `research_context/report_drafts/diagrams/generate_figure_5_1_architecture.py`
   so new dashboard chrome visually matches the Figure 5.1 system-architecture
   diagram evaluators will already have seen in the thesis.
2. **Risk magnitude** (`RISK_COLORSCALE`) — the existing epidemiological
   red-scale convention (choropleth, heat-cloud, calibrated-probability bars).

Never use `MODULE_COLORS` to encode risk magnitude, and never use
`RISK_COLORSCALE` for module identity/chrome — mixing the two would make a
chart's color meaning ambiguous (is redder "Module X" or "higher risk"?).
"""

from __future__ import annotations

MODULE_COLORS: dict[str, dict[str, str]] = {
    "shared": {"fill": "#1E3A8A", "edge": "#1E3A8A", "text": "#FFFFFF"},
    "m1": {"fill": "#DCFCE7", "edge": "#15803D", "text": "#14532D"},
    "m2": {"fill": "#DBEAFE", "edge": "#1D4ED8", "text": "#1E3A8A"},
    "m3": {"fill": "#FEF3C7", "edge": "#B45309", "text": "#78350F"},
    "dash": {"fill": "#ECFDF5", "edge": "#047857", "text": "#065F46"},
}

MODULE_LABELS: dict[str, str] = {
    "shared": "Shared",
    "m1": "Module 1 — Forecasting",
    "m2": "Module 2 — Classification",
    "m3": "Module 3 — Spatial",
    "dash": "Dashboard",
}

# Epidemiological risk-map convention — reserved for risk magnitude only.
RISK_COLORSCALE = "YlOrRd"

EVIDENCE_TIER_COLORS: dict[str, dict[str, str]] = {
    "validated": {"fill": "#DCFCE7", "edge": "#15803D", "text": "#14532D", "icon": "✅"},
    "operational_live": {"fill": "#FEF3C7", "edge": "#B45309", "text": "#78350F", "icon": "🟡"},
    "operational_prospective": {"fill": "#DBEAFE", "edge": "#1D4ED8", "text": "#1E3A8A", "icon": "🔵"},
}

EVIDENCE_TIER_LABELS: dict[str, str] = {
    "validated": "Validated (holdout / walk-forward)",
    "operational_live": "Operational — live/forward",
    "operational_prospective": "Operational — prospective (tracked, not yet resolved)",
}
