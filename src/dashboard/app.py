"""Sri Lanka dengue early-warning dashboard (Streamlit).

Four pages, in a fixed order that mirrors the project's own evidence-tier
discipline (validated -> operational-live -> operational-forward ->
still-accumulating). Each page is a real file under `views/`, registered by
path (not by callable) so Streamlit's own navigation identity is stable
across reruns and independently testable via `AppTest.switch_page()`:

  1. **Overview** — 30-second cold-open story, no prior context required.
  2. **Research Evidence** — holdout-validated metrics (thesis-safe).
  3. **Operational Monitoring** — live/forward monitoring (not accuracy proof).
  4. **Prospective Tracking** — self-checking mechanism for forward predictions.

Run::

    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DISTRICTS  # noqa: E402
from src.dashboard.components import render_glossary_sidebar  # noqa: E402

REFRESH_SCRIPT = PROJECT_ROOT / "scripts" / "refresh_dashboard_data.py"


def _run_refresh(skip_weather: bool) -> None:
    cmd = [sys.executable, str(REFRESH_SCRIPT)]
    if skip_weather:
        cmd.append("--skip-weather")
    with st.spinner("Running refresh pipeline (this may take several minutes)..."):
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    st.code((result.stdout or "") + (result.stderr or ""))
    if result.returncode != 0:
        st.error(f"Refresh failed (exit {result.returncode}).")
    else:
        st.success("Refresh completed.")
        st.cache_data.clear()


def main() -> None:
    st.set_page_config(page_title="Dengue Research & Early Warning", layout="wide")
    st.title("Sri Lanka Dengue — Research Framework & Early Warning")

    st.caption(
        "Team Codexon FYP · Residual compensation framework · "
        "Thesis metrics and operational views are **deliberately separated**."
    )

    with st.sidebar:
        st.header("Controls")
        # `key="district_select"` is load-bearing: `views/operational_monitoring.py`
        # reads `st.session_state["district_select"]` directly, since a
        # file-based page script has no way to receive this as a function
        # argument the way the pre-multipage `render_operational_page()` call
        # used to.
        st.selectbox("District (operational page)", DISTRICTS, key="district_select")
        skip_weather = st.checkbox("Skip weather fetch", value=False)
        if st.button("Refresh operational data"):
            _run_refresh(skip_weather)
            st.rerun()

        st.divider()
        render_glossary_sidebar()

    pg = st.navigation(
        [
            st.Page("views/overview.py", title="Overview", icon="🏠", default=True),
            st.Page("views/research_evidence.py", title="Research Evidence", icon="✅"),
            st.Page("views/operational_monitoring.py", title="Operational Monitoring", icon="📡"),
            st.Page("views/prospective_tracking.py", title="Prospective Tracking", icon="🔵"),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
