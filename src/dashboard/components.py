"""Reusable dashboard UI components: evidence-tier/module badges, a glossary,
and a single cached entry point for production risk thresholds.

These exist to replace three sources of drift found while auditing the
dashboard: (1) evidence-tier labeling that was inconsistently a `st.success`
banner in one place, a `st.warning` banner in another, and a bare
`evidence_tier` column elsewhere; (2) jargon column meanings that lived only
in `DASHBOARD_GUIDE.md`, a document the running app never shows; (3) a
hardcoded alert threshold (0.14) that silently went stale when Stage 1/2 was
retuned (Decision 047) while the actual production value moved to 0.10.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import streamlit as st

from src.module2_classification.scoring_utils import load_production_thresholds
from src.dashboard.theme import EVIDENCE_TIER_COLORS, EVIDENCE_TIER_LABELS, MODULE_COLORS, MODULE_LABELS

EvidenceTier = Literal["validated", "operational_live", "operational_prospective"]
Module = Literal["shared", "m1", "m2", "m3", "dash"]


def evidence_badge(tier: EvidenceTier, *, extra: str | None = None) -> None:
    """Render a small colored pill naming this content's evidence tier.

    Use at the top of any section showing numbers, so an evaluator never has
    to infer (from a caption's tone, or nothing at all) whether a figure is
    safe to cite as validated skill or is an unresolved operational forecast.
    """
    c = EVIDENCE_TIER_COLORS[tier]
    label = EVIDENCE_TIER_LABELS[tier]
    if extra:
        label = f"{label} — {extra}"
    st.markdown(
        f"""<div style="display:inline-block;padding:4px 12px;border-radius:14px;
        background-color:{c['fill']};border:1.5px solid {c['edge']};color:{c['text']};
        font-size:0.85rem;font-weight:600;margin-bottom:8px;">
        {c['icon']} {label}</div>""",
        unsafe_allow_html=True,
    )


def module_badge(module: Module) -> None:
    """Render a small colored pill naming which module (M1/M2/M3/shared) a
    section belongs to, using the exact colors from the thesis's Figure 5.1
    system-architecture diagram so the dashboard reads as the same visual
    language an evaluator already saw in Chapter 5.
    """
    c = MODULE_COLORS[module]
    label = MODULE_LABELS[module]
    st.markdown(
        f"""<div style="display:inline-block;padding:4px 12px;border-radius:14px;
        background-color:{c['fill']};border:1.5px solid {c['edge']};color:{c['text']};
        font-size:0.85rem;font-weight:600;margin-bottom:8px;">
        {label}</div>""",
        unsafe_allow_html=True,
    )


GLOSSARY: dict[str, str] = {
    "calibrated_probability": "Outbreak probability (0-1) after Stage 2 recalibration of Stage 1's raw score.",
    "risk_tier": "Low / medium / high, derived from calibrated_probability using the current production thresholds.",
    "alert_flag": "True if calibrated_probability is at or above the current alert threshold — 'worth attention', not 'outbreak confirmed'.",
    "feature_completeness_pct": "Share of numeric input features that were non-missing when this row was scored (100% = fully informed).",
    "already_scored_in_pipeline": "True if this week's data was inside the model's own training/evaluation history — not an independent validation point.",
    "horizon_step": "0 = latest real week; 1 = next week; 2-8 = further forward weeks with compounding uncertainty.",
    "prediction_type": "'observed_week' (horizon 0, real data) or 'forward_week' (horizon >= 1, a genuine forecast).",
    "cases_source": "Where this row's case count came from: 'actual' (real), 'na' (withheld, next-week leakage guard), or 'module1_forecast' (Module 1 prediction feeding a lag feature).",
    "climate_source": "'observed', 'forecast' (Open-Meteo forecast API), 'mixed', or 'missing'.",
    "uses_module1_cases": "True when Module 1's forecast feeds this row's case-lag features (horizon >= 2 only).",
    "evidence_tier": "Which of the three evidence tiers (validated / operational-live / operational-prospective) this row belongs to.",
    "MASE": "Mean Absolute Scaled Error — forecast error relative to a naive seasonal baseline; below 1.0 beats the baseline.",
    "sMAPE": "Symmetric Mean Absolute Percentage Error — scale-free forecast error, 0-100%.",
    "PR-AUC": "Precision-Recall Area Under Curve — discrimination skill for a rare/imbalanced outcome (here, outbreak weeks).",
    "Brier Skill Score": "Calibration skill relative to always predicting the base rate; positive means the model's probabilities beat that naive baseline.",
    "Moran's I": "A statistic for spatial autocorrelation — positive and significant means nearby districts have similar risk (real clustering, not noise).",
}


def column_help(columns: list[str]) -> dict[str, "st.column_config.Column"]:
    """`st.dataframe(column_config=...)` mapping for whichever of `columns`
    have a `GLOSSARY` entry - just-in-time hover definitions on the exact
    jargon columns (`calibrated_probability`, `horizon_step`, etc.) instead of
    requiring a reader to already know the external guide's column tables.
    """
    return {
        col: st.column_config.Column(help=GLOSSARY[col])
        for col in columns
        if col in GLOSSARY
    }


def render_glossary_sidebar() -> None:
    """A persistent sidebar glossary, not a popover/dialog — so a committee
    member flipping rapidly between charts doesn't have to hover over each
    column one at a time or dismiss a modal to see the next term.
    """
    with st.sidebar.expander("📖 Glossary", expanded=False):
        for term, definition in GLOSSARY.items():
            st.markdown(f"**{term}** — {definition}")


@st.cache_data(show_spinner=False)
def get_thresholds() -> tuple[float, float]:
    """The ONLY place dashboard code should reference Module 2's alert/high
    thresholds. Thin cached wrapper around
    `scoring_utils.load_production_thresholds()`, which reads the current
    values from `risk_threshold_scan.csv` live — never hardcode 0.14/0.35 (or
    any other specific pair) anywhere else in the dashboard, since Stage 1/2
    retuning re-selects both values from scratch (this already happened once:
    Decision 024/025's 0.170/0.570 became Decision 047's 0.100/0.500).
    """
    return load_production_thresholds()


def prospective_tracker_panel(name: str, log_df: pd.DataFrame, accuracy_df: pd.DataFrame) -> None:
    """Shared panel for a prospective (non-backtested) accuracy tracker.

    Both Module 1's nowcast tracker and Module 2's risk tracker log genuinely
    forward predictions now and can only check them once real weeks resolve.
    `accuracy_df` (from `reconcile_*_log()`) contains ONLY resolved rows by
    construction — an unresolved prediction is simply absent from it, never a
    row with some "pending" flag — so at any given moment it may legitimately
    be empty. Render that state explicitly and honestly ("N logged, 0
    resolved so far - check back") since a bare empty dataframe reads as
    broken, not as "working as designed."
    """
    evidence_badge("operational_prospective")
    n_logged = len(log_df) if log_df is not None else 0
    n_resolved = len(accuracy_df) if accuracy_df is not None else 0

    c1, c2 = st.columns(2)
    c1.metric(f"{name}: predictions logged", n_logged)
    c2.metric(
        f"{name}: resolved so far",
        f"{n_resolved} / {n_logged}",
        help="A logged prediction 'resolves' once the real target week's outcome is known. "
        "0 resolved does not mean the tracker is broken — it means those weeks haven't happened yet.",
    )
    if n_resolved == 0:
        st.info(
            f"No {name} predictions have resolved yet — this tracker accumulates evidence "
            "honestly over real calendar time, not on demand. Check back as weeks pass."
        )
    else:
        st.dataframe(accuracy_df.tail(20), use_container_width=True)

    if log_df is not None and not log_df.empty:
        with st.expander(f"{name}: recent logged predictions"):
            st.dataframe(log_df.tail(20), use_container_width=True)
