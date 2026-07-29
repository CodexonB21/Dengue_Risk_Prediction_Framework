"""Sri Lanka dengue early-warning dashboard (Streamlit).

Two views:
  1. **Research evidence** — holdout-validated metrics (thesis-safe).
  2. **Operational prototype** — live/forward monitoring (not accuracy proof).

Observer guide: ``DASHBOARD_GUIDE.md``.

Run::

    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DASHBOARD_REFRESH_MANIFEST_PATH,
    DISTRICTS,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
    MODULE2_LIVE_RISK_PREDICTIONS_PATH,
    SHARED_CLIMATE_WEEKLY_PATH,
)
from src.dashboard.pages import render_evidence_page, render_operational_page  # noqa: E402

REFRESH_SCRIPT = PROJECT_ROOT / "scripts" / "refresh_dashboard_data.py"

PAGE_LABELS = {
    "research": "Research evidence (holdout-validated)",
    "operational": "Operational prototype (live / forward)",
}


@st.cache_data(show_spinner=False)
def load_csv(path_str: str, mtime: float | None) -> pd.DataFrame:
    _ = mtime
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for col in ("Week_Start_Date", "Week_End_Date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _file_mtime(path: Path) -> float | None:
    return path.stat().st_mtime if path.exists() else None


def _load(path: Path) -> pd.DataFrame:
    return load_csv(str(path), _file_mtime(path))


def _latest_case_week(modeling: pd.DataFrame) -> tuple[int | None, int | None]:
    if modeling.empty:
        return None, None
    row = modeling.sort_values(["Year", "Week"]).iloc[-1]
    return int(row["Year"]), int(row["Week"])


def _latest_climate_week(climate: pd.DataFrame) -> tuple[int | None, int | None]:
    if climate.empty or "Year" not in climate.columns:
        return None, None
    row = climate.sort_values(["Year", "Week"]).iloc[-1]
    return int(row["Year"]), int(row["Week"])


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
        st.header("View")
        page_key = st.radio(
            "Select page",
            options=list(PAGE_LABELS.keys()),
            format_func=lambda k: PAGE_LABELS[k],
            index=0,
            label_visibility="collapsed",
        )

        st.divider()
        st.header("Controls")
        district = st.selectbox("District (operational page)", DISTRICTS)
        skip_weather = st.checkbox("Skip weather fetch", value=False)
        if st.button("Refresh operational data"):
            _run_refresh(skip_weather)
            st.rerun()

        st.divider()
        st.markdown(
            "**Demo order (viva):**\n"
            "1. Research evidence page first\n"
            "2. Operational prototype second\n"
            "3. State operational numbers are not validated accuracy"
        )

    if page_key == "research":
        render_evidence_page()
        return

    live = _load(MODULE2_LIVE_RISK_PREDICTIONS_PATH)
    future_risk = _load(MODULE2_FUTURE_RISK_PREDICTIONS_PATH)
    future_cases = _load(MODULE1_FUTURE_FORECAST_PATH)
    m1_weekly = _load(MODULE1_WEEKLY_MODELING_TABLE_PATH)
    climate = _load(SHARED_CLIMATE_WEEKLY_PATH)
    manifest = _load(DASHBOARD_REFRESH_MANIFEST_PATH)

    case_y, case_w = _latest_case_week(m1_weekly)
    clim_y, clim_w = _latest_climate_week(climate)
    refresh_ts = (
        manifest["refreshed_at_utc"].iloc[0]
        if not manifest.empty and "refreshed_at_utc" in manifest.columns
        else None
    )
    if refresh_ts:
        st.sidebar.caption(f"Last refresh (UTC): {refresh_ts}")

    render_operational_page(
        live=live,
        future_risk=future_risk,
        future_cases=future_cases,
        m1_weekly=m1_weekly,
        climate=climate,
        manifest=manifest,
        case_y=case_y,
        case_w=case_w,
        clim_y=clim_y,
        clim_w=clim_w,
        refresh_ts=refresh_ts,
        district=district,
    )


if __name__ == "__main__":
    main()
