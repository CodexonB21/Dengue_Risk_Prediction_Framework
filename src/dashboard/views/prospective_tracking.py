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
        "**Why this page can legitimately look empty right now**: a prediction only 'resolves' once "
        "its target week's real outcome exists in the dataset. Both trackers below were seeded "
        "recently — 0 resolved does not mean broken, it means check back."
    )

    module_badge("m1")
    st.subheader("Module 1 — next-week case nowcast tracker")
    st.caption(
        "`nowcast_tracking.py` logs every `run_nowcast()` prediction, then "
        "`reconcile_nowcast_log()` joins it against real case counts once available, computing "
        "absolute error and sMAPE per resolved (District, Year, Week)."
    )
    prospective_tracker_panel(
        "Module 1 nowcast", load_m1_nowcast_log(), load_m1_nowcast_accuracy()
    )

    st.divider()
    module_badge("m2")
    st.subheader("Module 2 — forward outbreak-risk tracker")
    st.caption(
        "`risk_tracking.py` logs every genuinely-forward (`prediction_type == 'forward_week'`) row "
        "from `forecast_future_risk.py`, then `reconcile_risk_log()` recomputes the real "
        "epidemic-threshold label fresh once the target week resolves, and checks whether "
        "`alert_flag` was actually correct."
    )
    prospective_tracker_panel(
        "Module 2 risk", load_m2_risk_log(), load_m2_risk_prospective_accuracy()
    )

    st.divider()
    module_badge("m3")
    st.subheader("Module 3 — forward hotspot-forecast tracker")
    st.caption(
        "`hotspot_tracking.py` logs every `forecast_future.run_forecast_future()` row, then "
        "`reconcile_hotspot_log()` recomputes Stage 1's KDE baseline using the REAL reported case "
        "count once the target week resolves, and reapplies the already-logged "
        "`predicted_relative_residual` unchanged (Stage 2 never sees this week's own case count, "
        "only backward-looking lag/climate features — so it needs no recomputation). This also "
        "isolates how much of Module 3's forward error is inherited from Module 1's case-count "
        "forecast feeding it (`risk_0_abs_error`), separately from the total forecast error "
        "(`abs_error`)."
    )
    prospective_tracker_panel(
        "Module 3 hotspot", load_m3_hotspot_log(), load_m3_hotspot_prospective_accuracy()
    )

    st.divider()
    st.caption(
        "Given Module 2's own holdout outbreak prevalence is only ~1.5%, accumulating enough "
        "resolved **outbreak** weeks specifically (not just resolved weeks generally) to say "
        "anything statistically meaningful here will take real calendar time by design — this is a "
        "slow-arriving evidence tier, not a shortcut around the Research Evidence page's holdout "
        "numbers. Module 3's tracker is newer still (Decision 052/M3-016, added 2026-08-10) and its "
        "own forecast is currently limited to one week ahead (`DEFAULT_HORIZON_WEEKS=1`) — see "
        "`module_3_spatial/MODULE_CONTEXT.md` for why multi-week Module 3 forecasting isn't "
        "implemented yet."
    )


# This file is loaded as a `st.Page` FILE (registered by path in `app.py`),
# so it must render on load like every other page file in `views/`.
render_prospective_page()
