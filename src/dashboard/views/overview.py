"""Overview page — the 30-second cold-open story for an evaluator who has
never seen this dashboard before. No numbers here are hardcoded: everything
is read live from the same sources the other three pages use, so this page
can never drift out of sync with what they actually show.
"""

from __future__ import annotations

import streamlit as st

from src.dashboard.components import evidence_badge, module_badge
from src.dashboard.data_loaders import (
    load_m3_morans_i,
    load_production_stack,
    m1_holdout_summary,
    m2_holdout_summary,
    m3_morans_i_summary,
)


def render_overview_page() -> None:
    st.header("Sri Lanka Dengue — Residual Compensation Risk Prediction Framework")
    st.markdown(
        "A **hybrid, two-stage** framework: a statistical or classical baseline model makes a "
        "first-pass prediction, and a machine-learning model then corrects that baseline's *errors* "
        "(its residual, or its miscalibration) rather than predicting the target from scratch. The "
        "same pattern is applied to three different questions about dengue in Sri Lanka's 25 "
        "districts."
    )

    stack = load_production_stack()
    m1 = m1_holdout_summary(stack)
    m2 = m2_holdout_summary(stack)
    morans = m3_morans_i_summary(load_m3_morans_i())

    c1, c2, c3 = st.columns(3)
    with c1:
        module_badge("m1")
        st.subheader("Forecasting")
        st.caption("SARIMA → XGBoost residual")
        st.metric(
            "Holdout MASE (hybrid)",
            f"{m1['median_mase_hybrid']:.3f}" if m1 else "—",
            help="Median across 25 districts on an untouched 2-year holdout block. Below 1.0 beats a naive seasonal baseline.",
        )
        st.caption("*How many cases next week?*")
    with c2:
        module_badge("m2")
        st.subheader("Classification")
        st.caption(f"Random Forest → {m2['architecture'].capitalize() if m2 else 'calibration'}")
        st.metric(
            "Holdout PR-AUC",
            f"{m2['pr_auc']:.3f}" if m2 else "—",
            help="Discrimination skill for a rare outcome (~1.5% holdout outbreak-week prevalence).",
        )
        st.caption("*Is this district-week an outbreak?*")
    with c3:
        module_badge("m3")
        st.subheader("Spatial hotspots")
        st.caption("KDE + Moran's I → RF residual")
        st.metric(
            "Global Moran's I",
            f"{morans['I']:.3f}" if morans else "—",
            help="Spatial autocorrelation statistic — positive & significant means nearby districts have genuinely similar risk, not noise.",
        )
        st.caption("*Where is risk spatially clustering?*")

    st.divider()
    st.subheader("Evidence tiers used throughout this dashboard")
    st.caption(
        "Every number on every page carries one of these three badges. This is the single most "
        "important thing to track while exploring — a number's badge tells you whether it is safe "
        "to cite as validated model skill, or is a live/forward output with no ground truth yet."
    )
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        evidence_badge("validated")
        st.caption("Walk-forward folds + an untouched holdout block. Safe to cite as model skill.")
    with ec2:
        evidence_badge("operational_live")
        st.caption("The frozen production models applied to the latest/forward data. Decision-support, not a skill claim.")
    with ec3:
        evidence_badge("operational_prospective")
        st.caption("Forward predictions logged now, checked against reality only once real weeks resolve.")

    st.divider()
    st.subheader("How to read this dashboard")
    st.markdown(
        """
        1. **Research Evidence** — start here. Holdout-validated numbers for all three modules,
           including the per-district and per-week honest limitations (a few districts and one
           seasonal window where a model underperforms, reported rather than hidden).
        2. **Operational Monitoring** — the same frozen models applied to the most recent and
           forward-looking data: national triage, a per-district drill-down, and the spatial
           hotspot map. Useful for a decision-support demo; **not** additional validation evidence.
        3. **Prospective Tracking** — the self-checking mechanism built so operational forward
           predictions can eventually be verified against reality, not just trusted on faith.
        """
    )
    st.caption(
        "Module 1's forecasts feed Module 2's forward risk scoring for horizons ≥ 2 weeks ahead "
        "(an intentional integration, not a validation shortcut) — see the Operational Monitoring "
        "page's Forward risk tab for the `uses_module1_cases` flag on every affected row."
    )


# This file is loaded as a `st.Page` FILE (registered by path in `app.py`),
# so it must render on load like every other page file in `views/`.
render_overview_page()
