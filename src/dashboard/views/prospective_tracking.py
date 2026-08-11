"""Prospective Tracking page — the three self-updating, non-backtested
accuracy trackers (Decision 041/M1-017 for Module 1's nowcast, Decision
048/M2-015 for Module 2's forward risk, Decision 052/M3-016 for Module 3's
forward hotspot forecast). All three log genuinely forward predictions now
and can only be checked once real weeks resolve — 0 resolved is an honest,
expected state early on, not a broken page.
"""

from __future__ import annotations

import streamlit as st

from src.dashboard.components import module_badge, prospective_tracker_panel
from src.dashboard.data_loaders import (
    load_m1_nowcast_accuracy,
    load_m1_nowcast_log,
    load_m2_risk_log,
    load_m2_risk_prospective_accuracy,
    load_m3_hotspot_log,
    load_m3_hotspot_prospective_accuracy,
)


def render_prospective_page() -> None:
    st.header("Prospective accuracy tracking")
    st.caption(
        "Every other page's numbers come from either a backtested holdout block (Research Evidence) "
        "or a live/forward snapshot with no ground truth yet (Operational Monitoring). This page is "
        "different: it shows the mechanism built specifically to check operational predictions "
        "honestly, over real calendar time, as the weeks they predicted actually happen."
    )
    st.info(
        "**Why this page can look empty right now**: a prediction only counts once its target "
        "week's real outcome exists in the dataset. Both trackers were set up recently, so "
        "0 resolved does not mean something is broken; check back later."
    )

    module_badge("m1")
    st.subheader("Module 1: next-week case nowcast tracker")
    st.caption(
        "Every next-week forecast is logged, then automatically checked against the real case "
        "count once it becomes available, so we can track the error for each district and week."
    )
    prospective_tracker_panel(
        "Module 1 nowcast", load_m1_nowcast_log(), load_m1_nowcast_accuracy()
    )

    st.divider()
    module_badge("m2")
    st.subheader("Module 2: forward outbreak-risk tracker")
    st.caption(
        "Every genuine forward-looking risk prediction is logged, then checked against the real "
        "outbreak label once the target week resolves, to see whether the alert was actually correct."
    )
    prospective_tracker_panel(
        "Module 2 risk", load_m2_risk_log(), load_m2_risk_prospective_accuracy()
    )

    st.divider()
    module_badge("m3")
    st.subheader("Module 3: forward hotspot-forecast tracker")
    st.caption(
        "Every forward hotspot forecast is logged, then checked against the real reported case "
        "count once the target week resolves. This also shows how much of Module 3's forward "
        "error comes from Module 1's case forecast, separately from the model's own error."
    )
    prospective_tracker_panel(
        "Module 3 hotspot", load_m3_hotspot_log(), load_m3_hotspot_prospective_accuracy()
    )

    st.divider()
    st.caption(
        "Outbreak weeks are rare (~1.5% holdout prevalence), so accumulating enough resolved "
        "outbreak weeks to say anything statistically meaningful here will take real calendar "
        "time. Module 3's tracker is newer and currently limited to one week ahead."
    )


# This file is loaded as a `st.Page` FILE (registered by path in `app.py`),
# so it must render on load like every other page file in `views/`.
render_prospective_page()
