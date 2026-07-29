"""Sri Lanka dengue early-warning dashboard (Streamlit).

Read-only consumer of frozen model outputs. Run::

    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
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
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
    SHARED_CLIMATE_WEEKLY_PATH,
)

REFRESH_SCRIPT = PROJECT_ROOT / "scripts" / "refresh_dashboard_data.py"


def _file_mtime(path: Path) -> float | None:
    return path.stat().st_mtime if path.exists() else None


@st.cache_data(show_spinner=False)
def load_csv(path_str: str, mtime: float | None) -> pd.DataFrame:
    _ = mtime
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    parse_dates = ["Week_Start_Date", "Week_End_Date"] if path.name != "climate_weekly.csv" else []
    return pd.read_csv(path, parse_dates=parse_dates if parse_dates else None)


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
    st.set_page_config(page_title="Dengue Early Warning", layout="wide")
    st.title("Sri Lanka Dengue Early Warning Dashboard")
    st.caption(
        "Operational view combining Module 1 case forecasts and Module 2 outbreak risk. "
        "**Forward outputs are evidence tier: operational — not holdout-validated skill.**"
    )

    with st.sidebar:
        st.header("Controls")
        district = st.selectbox("District", DISTRICTS)
        skip_weather = st.checkbox("Skip weather fetch", value=False)
        if st.button("Refresh data"):
            _run_refresh(skip_weather)

        manifest = _load(DASHBOARD_REFRESH_MANIFEST_PATH)
        if not manifest.empty and "refreshed_at_utc" in manifest.columns:
            st.caption(f"Last refresh: {manifest['refreshed_at_utc'].iloc[0]}")

    live = _load(MODULE2_LIVE_RISK_PREDICTIONS_PATH)
    future_risk = _load(MODULE2_FUTURE_RISK_PREDICTIONS_PATH)
    future_cases = _load(MODULE1_FUTURE_FORECAST_PATH)
    m1_weekly = _load(MODULE1_WEEKLY_MODELING_TABLE_PATH)
    climate = _load(SHARED_CLIMATE_WEEKLY_PATH)

    case_y, case_w = _latest_case_week(m1_weekly)
    clim_y, clim_w = _latest_climate_week(climate)

    c1, c2, c3 = st.columns(3)
    c1.metric("Last case epi-week", f"{case_y} Wk{case_w}" if case_y else "—")
    c2.metric("Last climate epi-week", f"{clim_y} Wk{clim_w}" if clim_y else "—")
    c3.metric(
        "Data files loaded",
        sum(1 for p in (
            MODULE2_LIVE_RISK_PREDICTIONS_PATH,
            MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
            MODULE1_FUTURE_FORECAST_PATH,
        ) if p.exists()),
    )

    st.subheader("National overview")
    forward = future_risk.loc[future_risk["prediction_type"] == "forward_week"].copy()
    if not forward.empty:
        latest_forward = forward.loc[forward["horizon_step"] == 1]
        next4 = forward.loc[forward["horizon_step"].between(1, 4)]
        alerts_now = int(latest_forward["alert_flag"].sum()) if not latest_forward.empty else 0
        alerts_next4 = int(next4.groupby(["District", "Year", "Week"])["alert_flag"].max().sum())
        st.write(f"Districts with alert at horizon 1: **{alerts_now}**")
        st.write(f"District-week alerts across horizons 1–4: **{alerts_next4}**")

        top = (
            forward.groupby("District")["calibrated_probability"].max()
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
        )
        st.write("Top 5 districts by max forward calibrated probability")
        st.dataframe(top, use_container_width=True)
    else:
        st.info("Forward risk CSV not found — run refresh pipeline.")

    st.divider()
    st.subheader(f"District drill-down: {district}")

    tab_recent, tab_cases, tab_forward = st.tabs(["Recent risk", "Case forecast", "Forward risk"])

    with tab_recent:
        if live.empty:
            st.warning("No live risk predictions.")
        else:
            dlive = live.loc[live["District"] == district].sort_values(["Year", "Week"])
            st.dataframe(
                dlive[
                    ["Year", "Week", "calibrated_probability", "risk_tier", "alert_flag",
                     "feature_completeness_pct", "already_scored_in_pipeline"]
                ],
                use_container_width=True,
            )
            fig = px.line(
                dlive, x="Week_Start_Date", y="calibrated_probability",
                markers=True, title=f"{district}: recent calibrated outbreak probability",
            )
            fig.add_hline(y=0.14, line_dash="dot", annotation_text="alert threshold")
            st.plotly_chart(fig, use_container_width=True)

    with tab_cases:
        hist = m1_weekly.loc[m1_weekly["District"] == district].sort_values(["Year", "Week"]).tail(52)
        fut = future_cases.loc[future_cases["District"] == district].sort_values("horizon_step")
        if hist.empty and fut.empty:
            st.warning("No case forecast data.")
        else:
            fig = px.line(title=f"{district}: cases — history + 8-week forecast")
            if not hist.empty:
                fig.add_scatter(
                    x=hist["Week_Start_Date"], y=hist["Number_of_Cases"],
                    mode="lines+markers", name="Actual",
                )
            if not fut.empty:
                fig.add_scatter(
                    x=fut["Week_Start_Date"], y=fut["final_prediction"],
                    mode="lines+markers", name="Forecast (M1)",
                )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Module 1 forward forecast — operational tier, not holdout MASE.")

    with tab_forward:
        dfwd = future_risk.loc[future_risk["District"] == district].sort_values("horizon_step")
        if dfwd.empty:
            st.warning("No forward risk predictions.")
        else:
            st.dataframe(
                dfwd[
                    ["horizon_step", "prediction_type", "Year", "Week",
                     "calibrated_probability", "risk_tier", "alert_flag",
                     "cases_source", "climate_source", "feature_completeness_pct",
                     "uses_module1_cases", "evidence_tier"]
                ],
                use_container_width=True,
            )
            fig = px.bar(
                dfwd, x="horizon_step", y="calibrated_probability", color="risk_tier",
                title=f"{district}: forward risk by horizon step",
            )
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
