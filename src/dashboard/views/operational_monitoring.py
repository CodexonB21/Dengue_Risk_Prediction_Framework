"""Operational Monitoring page — live/forward decision-support prototype (not accuracy proof)."""

from __future__ import annotations

import json
from pathlib import Path

import branca.colormap as branca_colormap
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from branca.element import MacroElement
from folium.raster_layers import ImageOverlay
from jinja2 import Template
from plotly.subplots import make_subplots
from streamlit_folium import st_folium

from src.config import (
    DASHBOARD_REFRESH_MANIFEST_PATH,
    DISTRICTS,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
    MODULE2_LIVE_RISK_PREDICTIONS_PATH,
    MODULE3_HYBRID_RISK_MAP_PATH,
    SHARED_CLIMATE_WEEKLY_PATH,
)
from src.dashboard.components import column_help, evidence_badge, get_thresholds, module_badge
from src.dashboard.data_loaders import (
    load_csv,
    load_district_geometry,
    load_m1_nowcast,
    load_m3_hotspot_forecast,
)
from src.module3_spatial.kde_baseline import (
    district_centroid_coords,
    load_district_boundaries,
)
from src.module3_spatial.risk_surface import (
    build_evaluation_grid,
    evaluate_risk_surface,
    grid_lonlat_bounds,
    risk_surface_rgba,
)


def _render_nowcast_panel(nowcast: pd.DataFrame, district: str) -> None:
    """Module 1's genuine single-week-ahead prediction (Decision 040/M1-016's
    vintage-ensembled SARIMA + Stage 2) - a distinct, more current headline
    number than the 4-week `future_forecast.csv` used below, and previously
    completely absent from the dashboard despite being production output."""
    module_badge("m1")
    st.subheader("Module 1 — next-week case nowcast")
    evidence_badge("operational_live")
    if nowcast.empty:
        st.info("Nowcast file not found — run `python -m src.module1_forecasting.forecast_future --nowcast`.")
        return

    row = nowcast.loc[nowcast["District"] == district]
    target = f"{int(nowcast['Year'].iloc[0])} Wk{int(nowcast['Week'].iloc[0])}" if not nowcast.empty else "—"
    st.caption(
        f"Single-step \"predict next week using all data up to now\" ({target}) — distinct from the "
        "recursive 4-week forecast further down this page. Uses a 4-vintage SARIMA ensemble "
        "(Decision 039/M1-016), the first broad accuracy improvement found across Module 1's full "
        "remediation arc, though still operational-tier (no holdout MASE for this specific path)."
    )
    if not row.empty:
        r = row.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{district}: predicted cases", f"{r['final_prediction']:.0f}")
        c2.metric("SARIMA component", f"{r['sarima_prediction']:.1f}")
        c3.metric("Residual correction", f"{r['predicted_residual']:.1f}")

    top5 = nowcast.sort_values("final_prediction", ascending=False).head(5)[["District", "final_prediction"]]
    st.write("Top 5 districts by predicted next-week cases (national context)")
    st.dataframe(top5, use_container_width=True, hide_index=True)


def render_operational_page(
    *,
    live: pd.DataFrame,
    future_risk: pd.DataFrame,
    future_cases: pd.DataFrame,
    nowcast: pd.DataFrame,
    m1_weekly: pd.DataFrame,
    climate: pd.DataFrame,
    manifest: pd.DataFrame,
    hybrid_risk: pd.DataFrame,
    hotspot_forecast: pd.DataFrame,
    district_geometry: "gpd.GeoDataFrame",
    case_y: int | None,
    case_w: int | None,
    clim_y: int | None,
    clim_w: int | None,
    refresh_ts: str | None,
    district: str,
) -> None:
    st.header("Operational monitoring prototype")
    evidence_badge("operational_live")
    st.caption(
        "Not holdout-validated. Use for integration demo only. "
        "Thesis accuracy claims must come from the **Research evidence** page."
    )

    st.info(
        f"**Data freshness:** last case epi-week **{case_y} Wk{case_w}** · "
        f"last observed climate **{clim_y} Wk{clim_w}** · "
        f"last refresh **{refresh_ts or 'unknown'}**."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Last case epi-week", f"{case_y} Wk{case_w}" if case_y else "—")
    c2.metric("Last climate epi-week", f"{clim_y} Wk{clim_w}" if clim_y else "—")
    c3.metric(
        "Output files loaded",
        sum(
            1
            for p in (
                MODULE2_LIVE_RISK_PREDICTIONS_PATH,
                MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
                MODULE1_FUTURE_FORECAST_PATH,
            )
            if Path(p).exists()
        ),
    )

    st.divider()
    _render_nowcast_panel(nowcast, district)

    st.divider()
    module_badge("m2")
    st.subheader("National triage (monitoring signals)")
    st.caption(
        "Counts below are **early-warning flags**, not validated detections. "
        "High predicted cases ≠ outbreak in high-baseline districts (Colombo, Gampaha)."
    )

    forward = future_risk.loc[future_risk["prediction_type"] == "forward_week"].copy() if not future_risk.empty else pd.DataFrame()
    if not forward.empty:
        latest_forward = forward.loc[forward["horizon_step"] == 1]
        next4 = forward.loc[forward["horizon_step"].between(1, 4)]
        alerts_now = int(latest_forward["alert_flag"].sum()) if not latest_forward.empty else 0
        alerts_next4 = int(next4.groupby(["District", "Year", "Week"])["alert_flag"].max().sum())
        m1, m2 = st.columns(2)
        m1.metric("Districts flagged (horizon 1)", alerts_now, help="Operational alert_flag; not holdout recall")
        m2.metric("District-week flags (horizons 1–4)", alerts_next4)

        top = (
            forward.groupby("District")["calibrated_probability"].max()
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
        )
        st.write("Top 5 districts by max **forward** calibrated probability (operational)")
        st.dataframe(top, use_container_width=True)
    else:
        st.info("Forward risk CSV not found — run `python scripts/refresh_dashboard_data.py`.")

    st.divider()
    st.subheader(f"District drill-down: {district}")

    tab_recent, tab_cases, tab_forward = st.tabs(["Recent risk", "Case forecast", "Forward risk"])

    with tab_recent:
        module_badge("m2")
        st.caption("Recent observed weeks — production checkpoint; weeks may overlap training history.")
        if live.empty:
            st.warning("No live risk predictions.")
        else:
            dlive = live.loc[live["District"] == district].sort_values(["Year", "Week"]).copy()
            # Merge in the reporting-anomaly flag (Decision 026/028) - live_risk_predictions.csv
            # doesn't carry it itself - so a genuine reporting-delay catch-up week reads as an
            # explained data-quality event here too, not just an unexplained low-probability
            # week sitting right next to a real case-count spike (same treatment as the
            # Case forecast tab below).
            anomaly_flags = m1_weekly.loc[
                m1_weekly["District"] == district, ["Year", "Week", "is_reporting_anomaly"]
            ]
            dlive = dlive.merge(anomaly_flags, on=["Year", "Week"], how="left")
            dlive["is_reporting_anomaly"] = dlive["is_reporting_anomaly"].fillna(False)
            dlive["catch_up_week"] = dlive["is_reporting_anomaly"].shift(1, fill_value=False)

            recent_cols = [
                "Year", "Week", "Number_of_Cases", "calibrated_probability", "risk_tier",
                "alert_flag", "feature_completeness_pct", "already_scored_in_pipeline",
            ]
            recent_cols = [c for c in recent_cols if c in dlive.columns]
            st.dataframe(
                dlive[recent_cols],
                column_config=column_help(recent_cols),
                use_container_width=True,
            )
            fig = px.line(
                dlive,
                x="Week_Start_Date",
                y="calibrated_probability",
                markers=True,
                title=f"{district}: recent calibrated probability (operational)",
            )
            alert_threshold, _ = get_thresholds()
            fig.add_hline(
                y=alert_threshold, line_dash="dot",
                annotation_text=f"alert threshold ({alert_threshold:.2f})",
            )
            flagged = dlive.loc[dlive["catch_up_week"]]
            if not flagged.empty:
                fig.add_scatter(
                    x=flagged["Week_Start_Date"],
                    y=flagged["calibrated_probability"],
                    mode="markers",
                    marker=dict(symbol="x", size=13, color="#B45309"),
                    name="Follows a flagged reporting-delay dip",
                )
            st.plotly_chart(fig, use_container_width=True)
            if dlive["catch_up_week"].any():
                st.caption(
                    "🟠 marker: this week immediately follows a week flagged as a likely reporting "
                    "dip/catch-up (Decision 026/028) — case-derived lag features for it were built "
                    "on an artificially low prior-week count, so the probability here should be read "
                    "alongside the actual `Number_of_Cases` column above, not on its own."
                )

    with tab_cases:
        module_badge("m1")
        st.caption("Module 1 forward forecast — recursive multi-step; **not** holdout MASE.")
        hist = m1_weekly.loc[m1_weekly["District"] == district].sort_values(["Year", "Week"]).tail(52)
        fut = future_cases.loc[future_cases["District"] == district].sort_values("horizon_step")
        if hist.empty and fut.empty:
            st.warning("No case forecast data.")
        else:
            fig = px.line(title=f"{district}: cases — history + 4-week forward (operational)")
            if not hist.empty:
                fig.add_scatter(
                    x=hist["Week_Start_Date"],
                    y=hist["Number_of_Cases"],
                    mode="lines+markers",
                    name="Actual",
                )
                # Reporting-anomaly weeks (Decision 026/028) surfaced directly on
                # the chart, not just as a hidden data-quality footnote - a
                # viva panel is likely to ask "why is there a spike/dip here."
                if "is_reporting_anomaly" in hist.columns:
                    flagged = hist.loc[hist["is_reporting_anomaly"].fillna(False)]
                    if not flagged.empty:
                        fig.add_scatter(
                            x=flagged["Week_Start_Date"],
                            y=flagged["Number_of_Cases"],
                            mode="markers",
                            marker=dict(symbol="x", size=11, color="#B45309"),
                            name="Flagged reporting anomaly",
                        )
            if not fut.empty:
                fig.add_scatter(
                    x=fut["Week_Start_Date"],
                    y=fut["final_prediction"],
                    mode="lines+markers",
                    name="Forecast (M1)",
                )
            st.plotly_chart(fig, use_container_width=True)
            if "is_reporting_anomaly" in hist.columns and hist["is_reporting_anomaly"].fillna(False).any():
                st.caption(
                    "🟠 markers are weeks flagged as a likely reporting dip/catch-up spike rather than a "
                    "genuine case-count change (Decision 026/028) — a documented data-quality signal, "
                    "not a model error."
                )

    with tab_forward:
        module_badge("m2")
        st.warning(
            "Horizon ≥ 2 uses Module 1 predicted case lags and forecast climate. "
            "Uncertainty compounds — treat as scenario view, not validated probability."
        )
        dfwd = future_risk.loc[future_risk["District"] == district].sort_values("horizon_step")
        if dfwd.empty:
            st.warning("No forward risk predictions.")
        else:
            forward_cols = [
                "horizon_step", "prediction_type", "Year", "Week",
                "calibrated_probability", "risk_tier", "alert_flag",
                "cases_source", "climate_source", "feature_completeness_pct",
                "uses_module1_cases", "evidence_tier",
            ]
            st.dataframe(
                dfwd[forward_cols],
                column_config=column_help(forward_cols),
                use_container_width=True,
            )
            fig = px.bar(
                dfwd,
                x="horizon_step",
                y="calibrated_probability",
                color="risk_tier",
                title=f"{district}: forward risk by horizon (operational)",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    module_badge("m3")
    st.subheader("Module 3 — spatial hotspot map")
    evidence_badge("operational_live")
    st.caption("Hybrid Risk = KDE spatial baseline + Random Forest relative-residual correction.")
    with st.expander("How this map is built"):
        st.markdown(
            "- **Colour** is the Hybrid Risk score (KDE spatial baseline + Stage 2 "
            "correction), interpolated continuously via nearest-neighbour distance "
            "weighting — risk blends across the border between two high-risk "
            "neighbouring districts rather than stopping dead at a district line.\n"
            "- **This week** uses real reported cases. **Next week (forecast)** uses "
            "Module 1's case forecast plus real *observed* climate — Module 3's "
            "reporting lag means the forecast week's weather has already happened. "
            "See Decision 052 (`research_context/RESEARCH_DECISIONS.md`).\n"
            "- Not a validated forecast — see the **Research evidence** page for "
            "Stage 1/Stage 2 validation numbers (Moran's I, convergence, fit comparison)."
        )

    mode = st.segmented_control(
        "Timeframe",
        ["This week", "Next week (forecast)"],
        default="This week",
        required=True,
        label_visibility="collapsed",
    )

    top5 = pd.DataFrame()

    if mode == "This week":
        if hybrid_risk.empty or district_geometry.empty:
            st.info(
                "Hybrid risk map or district geometry not found — run "
                "`python -m src.module3_spatial.iterative_loop`."
            )
        else:
            week_options_df = hybrid_risk[["Year", "Week"]].drop_duplicates().sort_values(["Year", "Week"])
            week_options = [f"{int(r.Year)} Wk{int(r.Week)}" for r in week_options_df.itertuples()]

            with st.expander(f"Explore an earlier week (showing latest: {week_options[-1]})"):
                selected_label = st.select_slider(
                    "Week",
                    options=week_options,
                    value=week_options[-1],
                    key="module3_map_week",
                    label_visibility="collapsed",
                )
            selected_year_str, selected_week_str = selected_label.split(" Wk")
            selected_year, selected_week = int(selected_year_str), int(selected_week_str)

            latest = hybrid_risk.loc[
                (hybrid_risk["Year"] == selected_year) & (hybrid_risk["Week"] == selected_week)
            ]

            heatmap = _hybrid_risk_folium_heatmap(district_geometry, latest, district)
            st_folium(heatmap, width="stretch", height=600, returned_objects=[], key="module3_map")

            district_row = latest.loc[latest["District"] == district]
            if not district_row.empty:
                row = district_row.iloc[0]
                c1, c2 = st.columns(2)
                c1.metric(f"{district}: Hybrid Risk", f"{row['Risk']:.1f}")
                c2.metric(f"{district}: actual cases (same week)", int(row["Number_of_Cases"]))

            top5 = latest.sort_values("Risk", ascending=False).head(5)[["District", "Risk"]]

    else:
        if hotspot_forecast.empty or district_geometry.empty:
            st.info("Forecast not found — run `python -m src.module3_spatial.forecast_future`.")
        else:
            fc_latest = hotspot_forecast.sort_values(["Year", "Week"]).groupby(["Year", "Week"]).tail(len(DISTRICTS))
            fc_year, fc_week = int(fc_latest["Year"].iloc[0]), int(fc_latest["Week"].iloc[0])
            st.caption(f"Forecast week: **{fc_year} Wk{fc_week}**.")

            fc_adapter = fc_latest.rename(columns={"Risk_forecast": "Risk", "cases_forecast": "Number_of_Cases"})
            heatmap = _hybrid_risk_folium_heatmap(district_geometry, fc_adapter, district)
            st_folium(heatmap, width="stretch", height=600, returned_objects=[], key="module3_map")

            fc_row = fc_adapter.loc[fc_adapter["District"] == district]
            if not fc_row.empty:
                row = fc_row.iloc[0]
                c1, c2, c3 = st.columns(3)
                c1.metric(f"{district}: forecast Hybrid Risk", f"{row['Risk']:.1f}")
                c2.metric("Stage 1 baseline (Risk_0)", f"{row['Risk_0_forecast']:.1f}")
                c3.metric("Relative correction", f"{row['predicted_relative_residual']:+.2f}")

            top5 = fc_adapter.sort_values("Risk", ascending=False).head(5)[["District", "Risk"]]

    if not top5.empty:
        st.write("Top 5 districts by Hybrid Risk (national context)")
        st.dataframe(top5, width="stretch", hide_index=True)

    if not hybrid_risk.empty:
        with st.expander(f"{district}: model accuracy detail (out-of-fold history)"):
            st.caption(
                "Predicted (Hybrid Risk) is out-of-fold (5-fold spatial K-means CV) — a "
                "model that never trained on this district. Green above zero = "
                "over-predicted, red below zero = under-predicted."
            )
            history_fig = _hybrid_risk_actual_vs_predicted_chart(hybrid_risk, district)
            st.plotly_chart(history_fig, width="stretch")


def _latest_hybrid_risk(hybrid_risk: pd.DataFrame) -> pd.DataFrame:
    if hybrid_risk.empty:
        return pd.DataFrame()
    latest_key = hybrid_risk.sort_values(["Year", "Week"]).iloc[-1]
    return hybrid_risk.loc[
        (hybrid_risk["Year"] == latest_key["Year"]) & (hybrid_risk["Week"] == latest_key["Week"])
    ]


# Same red/green identity used in the standalone actual-vs-predicted artifact
# shared with the team - kept consistent rather than falling back to Plotly's
# default categorical cycle, so "red = actual, green = predicted" reads the
# same way in both places.
_ACTUAL_COLOR = "#b3392f"
_PREDICTED_COLOR = "#1f7a5c"


def _hybrid_risk_actual_vs_predicted_chart(hybrid_risk: pd.DataFrame, district: str) -> go.Figure:
    """District history: actual `Number_of_Cases` vs. predicted `Risk`
    (top panel), with a synchronized error panel below it (Predicted minus
    Actual, positive = over-predicted / green, negative = under-predicted /
    red) - same encoding as the standalone HTML version. `hybrid_risk_map.csv`
    has no date column, only integer Year/Week, so the x-axis is a plain row
    index with tick labels placed at each year's first index (avoids the
    ISO week-53 date-parsing edge case some epi-week/year combinations hit).
    """
    d = hybrid_risk.loc[hybrid_risk["District"] == district].sort_values(["Year", "Week"]).reset_index(drop=True)
    x = d.index.to_numpy()
    week_label = d["Year"].astype(str) + " Wk" + d["Week"].astype(str)
    diff = d["Risk"] - d["Number_of_Cases"]
    diff_over = diff.clip(lower=0)
    diff_under = diff.clip(upper=0)

    year_starts = d.groupby("Year").head(1)
    tick_x = year_starts.index.to_numpy()
    tick_text = year_starts["Year"].astype(str).to_numpy()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[0.68, 0.32],
        subplot_titles=(f"{district}: actual vs. predicted (Hybrid Risk)", "Error (Predicted − Actual)"),
    )
    fig.add_scatter(
        x=x, y=d["Number_of_Cases"], mode="lines", name="Actual (Number_of_Cases)",
        line=dict(color=_ACTUAL_COLOR, width=1.75), customdata=week_label,
        hovertemplate="%{customdata}<br>Actual: %{y:.0f}<extra></extra>", row=1, col=1,
    )
    fig.add_scatter(
        x=x, y=d["Risk"], mode="lines", name="Predicted (Hybrid Risk)",
        line=dict(color=_PREDICTED_COLOR, width=1.75, dash="dash"), customdata=week_label,
        hovertemplate="%{customdata}<br>Predicted: %{y:.1f}<extra></extra>", row=1, col=1,
    )
    fig.add_scatter(
        x=x, y=diff_over, mode="lines", name="Over-predicted", fill="tozeroy",
        line=dict(color=_PREDICTED_COLOR, width=0.5), fillcolor="rgba(31,122,92,0.28)",
        customdata=week_label, hovertemplate="%{customdata}<br>Error: +%{y:.1f}<extra></extra>",
        row=2, col=1,
    )
    fig.add_scatter(
        x=x, y=diff_under, mode="lines", name="Under-predicted", fill="tozeroy",
        line=dict(color=_ACTUAL_COLOR, width=0.5), fillcolor="rgba(179,57,47,0.28)",
        customdata=week_label, hovertemplate="%{customdata}<br>Error: %{y:.1f}<extra></extra>",
        row=2, col=1,
    )
    fig.add_hline(y=0, line_width=1, line_color="rgba(120,120,120,0.6)", row=2, col=1)

    fig.update_xaxes(tickmode="array", tickvals=tick_x, ticktext=tick_text, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_layout(
        height=560,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="left", x=0),
        margin=dict(t=70, b=10),
    )
    return fig


# 1500m - finer than the risk_surface.py report figure's 1000m would be
# overkill for a browser-rendered PNG, but this needs to stay well below
# any resolution a user could zoom in far enough to visually resolve as
# separate raster cells (unlike the old point-based Leaflet HeatMap, this
# is a real image scaled to `bounds`, so higher resolution only costs a
# larger PNG, not per-zoom-level correctness).
DASHBOARD_GRID_RESOLUTION_M = 1500.0


def _hybrid_risk_choropleth(
    geometry: "gpd.GeoDataFrame", latest: pd.DataFrame, district: str, year: int, week: int
):
    merged = geometry.merge(latest[["District", "Risk", "Number_of_Cases"]], on="District", how="left")
    geojson = json.loads(merged.to_json())

    # Highlight the selected district with a thick black outline - same
    # per-district drill-down concept the M1/M2 tabs use, applied to a map
    # instead of a time series. Non-selected borders are opaque white (not
    # a faint black) so district boundaries stay visible across the whole
    # YlOrRd range - a low-opacity dark border disappears against the dark
    # red high-risk fills at the top of the scale.
    line_widths = [5 if d == district else 1 for d in merged["District"]]
    line_colors = ["#0b0b0b" if d == district else "#ffffff" for d in merged["District"]]

    fig = px.choropleth(
        merged,
        geojson=geojson,
        locations="District",
        featureidkey="properties.District",
        color="Risk",
        color_continuous_scale="YlOrRd",  # standard epidemiological risk-map convention
    )
    fig.update_traces(
        marker_line_width=line_widths,
        marker_line_color=line_colors,
        customdata=merged[["District", "Number_of_Cases"]],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Hybrid Risk Score: %{z:.1f}<br>"
            "Actual Cases: %{customdata[1]}"
            "<extra></extra>"
        ),
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title=dict(
            text=f"Dengue Hybrid Risk Map — {year} Week {week}",
            x=0.5,
            xanchor="center",
            font=dict(size=20),
        ),
        height=700,
        margin=dict(l=0, r=0, t=70, b=10),
        coloraxis_colorbar=dict(title=dict(text="Hybrid Risk<br>Score")),
    )
    return fig


@st.cache_data(show_spinner=False)
def _cached_risk_surface_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(district_coords, xx, yy, mask), all in the metric CRS (EPSG:32644)
    risk_surface.py's kernel math uses. This is static geography,
    independent of the selected Year/Week/District, so it's computed once
    and reused across every dashboard interaction.
    """
    boundaries = load_district_boundaries()
    district_coords = district_centroid_coords(boundaries)
    xx, yy, mask, _ = build_evaluation_grid(boundaries, DASHBOARD_GRID_RESOLUTION_M)
    return district_coords, xx, yy, mask


def _hybrid_risk_folium_heatmap(
    geometry: gpd.GeoDataFrame, latest: pd.DataFrame, district: str
) -> folium.Map:
    """Continuous heat-cloud view of Hybrid Risk, interpolated via
    k-nearest-neighbour Inverse Distance Weighting
    (`risk_surface.py::evaluate_risk_surface`) - at any point, only the
    physically closest few districts contribute at all, so risk visibly
    concentrates toward the border between two high-risk neighbouring
    districts instead of blobbing solidly around each district's own
    centroid, or (as a Gaussian-kernel attempt was found to do - see
    `evaluate_risk_surface`'s docstring) diluting that effect across the
    whole country.
    """
    merged = geometry.merge(latest[["District", "Risk", "Number_of_Cases"]], on="District", how="left")
    centroids = merged.geometry.centroid

    district_coords, xx, yy, mask = _cached_risk_surface_grid()
    grid_coords = np.column_stack([xx[mask], yy[mask]])
    # Genuinely-missing districts for this week are treated as 0 risk for
    # interpolation purposes only (mirrors kde_baseline.py's own 0-weight
    # treatment of absent (District, Year, Week) cells) - a NaN here would
    # otherwise poison the weighted average at every grid point, not just
    # the missing district's own.
    risk_by_district = merged.set_index("District")["Risk"].reindex(DISTRICTS).fillna(0.0)
    surface_values = evaluate_risk_surface(
        grid_coords, district_coords, risk_by_district.to_numpy(dtype=float)
    )

    # A fixed zoom_start, not fit_bounds() - fit_bounds computes its zoom
    # from the EMBEDDING IFRAME's measured width at the moment the map
    # script runs, which races against streamlit-folium's own container
    # sizing (observed: it consistently under-zoomed to show most of
    # southern India alongside Sri Lanka, regardless of
    # use_container_width). zoom_start=8 is tuned directly against Sri
    # Lanka's actual extent (~435km N-S, ~225km E-W) and has no such race.
    fmap = folium.Map(
        location=[centroids.y.mean(), centroids.x.mean()], zoom_start=8, tiles="OpenStreetMap"
    )

    # A geographically-anchored raster image, not Leaflet's point-based
    # HeatMap plugin: HeatMap's radius/blur are fixed SCREEN pixels, so the
    # surface only looks continuous at the one zoom level those pixel
    # values happen to match the grid spacing at - zoom in further and the
    # grid becomes visible as separate uniform blobs (exactly backwards for
    # a feature whose whole point is a continuous border-blended surface).
    # An ImageOverlay scales with the map like any tile layer, so it stays
    # a smooth gradient at every zoom level.
    rgba = risk_surface_rgba(xx, yy, mask, surface_values)
    bounds = grid_lonlat_bounds(xx, yy)
    ImageOverlay(rgba, bounds=bounds, opacity=0.85).add_to(fmap)

    # District boundary outlines drawn on top of the raster - the surface
    # itself is continuous and deliberately ignores district borders (that
    # is the whole point: risk should blend across a border between two
    # high-risk neighbours, not stop dead at it), but the borders still
    # need to be VISIBLE so a viewer can actually see the color pushing
    # past them, e.g. into a neighbouring district. No fill (fillOpacity=0)
    # - only the raster overlay should contribute color. White for
    # unselected borders (visible across the whole YlOrRd range, unlike a
    # low-opacity dark line which disappears against the dark-red high-risk
    # fills), thick black for the selected district - same convention the
    # old choropleth used.
    def _boundary_style(feature: dict) -> dict:
        is_selected = feature["properties"]["District"] == district
        return {
            "fillOpacity": 0,
            "color": "#0b0b0b" if is_selected else "#ffffff",
            "weight": 3 if is_selected else 1.2,
        }

    folium.GeoJson(
        merged[["District", "geometry"]].to_json(),
        style_function=_boundary_style,
        tooltip=folium.GeoJsonTooltip(fields=["District"]),
    ).add_to(fmap)

    for _, row in merged.iterrows():
        pt = row.geometry.centroid
        is_selected = row["District"] == district
        risk_text = f"{row['Risk']:.1f}" if pd.notna(row["Risk"]) else "—"
        cases_text = int(row["Number_of_Cases"]) if pd.notna(row["Number_of_Cases"]) else "—"
        folium.Marker(
            location=[pt.y, pt.x],
            popup=folium.Popup(
                f"<b>{row['District']}</b><br>"
                f"Hybrid Risk Score: {risk_text}<br>"
                f"Actual Cases: {cases_text}",
                max_width=220,
            ),
            tooltip=row["District"],
            icon=folium.Icon(
                color="red" if is_selected else "blue",
                icon="star" if is_selected else "info-sign",
            ),
        ).add_to(fmap)

    return fmap


def _hybrid_risk_circle_map(
    geometry: gpd.GeoDataFrame, latest: pd.DataFrame, district: str
) -> folium.Map:
    """Precise per-district hotspot view: one `folium.CircleMarker` per
    district centroid (same GADM centroids the choropleth and heat-cloud
    use), radius AND fill color both driven by that district's real Hybrid
    Risk value - double-encoded (bigger AND redder for higher risk) so the
    magnitude reads clearly even without hovering. A more "exact"
    complement to the heat-cloud's smoothed, border-blended interpolation -
    this view makes no spatial claim beyond each district's own single
    number, real data only (`hybrid_risk_map.csv`), nothing synthetic.
    """
    merged = geometry.merge(latest[["District", "Risk", "Number_of_Cases"]], on="District", how="left")
    centroids = merged.geometry.centroid

    risk = merged["Risk"].fillna(0.0)
    risk_min, risk_max = float(risk.min()), float(risk.max())
    # branca's YlOrRd_09 - same color family as the choropleth's
    # `color_continuous_scale="YlOrRd"` - so a district reads as roughly
    # the same color across both views, not two different visual languages
    # for the same underlying number.
    colormap = branca_colormap.linear.YlOrRd_09.scale(
        risk_min, risk_max if risk_max > risk_min else risk_min + 1
    )
    colormap.caption = "Hybrid Risk Score"

    MIN_RADIUS, MAX_RADIUS = 8, 25
    if risk_max > risk_min:
        radii = MIN_RADIUS + (risk - risk_min) / (risk_max - risk_min) * (MAX_RADIUS - MIN_RADIUS)
    else:
        radii = pd.Series(MIN_RADIUS, index=risk.index)

    # Same centering/zoom fix as the heat-cloud map (fixed zoom_start, not
    # fit_bounds() - see that function's docstring for the container-size
    # race this avoids).
    fmap = folium.Map(
        location=[centroids.y.mean(), centroids.x.mean()], zoom_start=8, tiles="OpenStreetMap"
    )

    for (_, row), radius in zip(merged.iterrows(), radii):
        pt = row.geometry.centroid
        is_selected = row["District"] == district
        risk_value = float(row["Risk"]) if pd.notna(row["Risk"]) else 0.0
        risk_text = f"{row['Risk']:.1f}" if pd.notna(row["Risk"]) else "—"
        cases_text = int(row["Number_of_Cases"]) if pd.notna(row["Number_of_Cases"]) else "—"

        # Fill color/radius stay purely risk-driven (that's the whole
        # point of the double-encoding) - selection is instead marked via
        # the marker's own BORDER (thick black vs thin white), same
        # convention the choropleth and heat-cloud's district outlines use.
        folium.CircleMarker(
            location=[pt.y, pt.x],
            radius=radius,
            color="#0b0b0b" if is_selected else "#ffffff",
            weight=3 if is_selected else 1,
            fill=True,
            fill_color=colormap(risk_value),
            fill_opacity=0.85,
            popup=folium.Popup(
                f"<b>{row['District']}</b><br>"
                f"Hybrid Risk Score: {risk_text}<br>"
                f"Actual Cases: {cases_text}",
                max_width=220,
            ),
            tooltip=row["District"],
        ).add_to(fmap)

    colormap.add_to(fmap)
    return fmap


class _InlineCss(MacroElement):
    """Injects a raw `<style>` block as a genuine child of a folium layer.

    `folium.Element(css).add_to(m)` was tried first and traced (via
    `branca.element` source, not assumed) to silently do nothing: a plain
    `Element.render()` just returns a string with no side effect, while
    `MacroElement.render()` - which is what actually walks a map's
    children and registers their `header`/`html`/`script` macros onto
    whichever Figure ends up being the map's root AT RENDER TIME - is what
    every working layer here (TileLayer, GeoJson) already relies on. A
    bare `Element` child is invisible to that mechanism; a `MacroElement`
    with an explicit `html` macro (this class) is not.
    """

    def __init__(self, css: str) -> None:
        super().__init__()
        self._name = "InlineCss"
        self._template = Template("{% macro html(this, kwargs) %}" + css + "{% endmacro %}")


UBER_GRADIENT_COLORS = ['#1a3a1a', '#6aaa00', '#f0a500', '#e8521a', '#cc1a00']


def _hybrid_risk_uber_heatmap(
    geometry: gpd.GeoDataFrame, latest: pd.DataFrame, district: str
) -> folium.Map:
    """Uber Rider-app style heat glow. Real data only (hybrid_risk_map.csv,
    GADM polygons), same as every other view - a purely stylistic fourth
    view, not a replacement for any of the other three.

    Two substantive rounds of feedback folded in:

    1. Glow shape: the original version used Leaflet's point-based
       `HeatMap` plugin, which can only ever render CIRCULAR radial
       gradients centered on a point - it has no concept of a district's
       real shape. Replaced with a `folium.GeoJson` fill of each district's
       ACTUAL polygon (same geometry the choropleth uses), colored by that
       district's Risk value, with a CSS `blur()` filter on the SVG paths
       to soften the polygon's hard edges into a glow - so the light now
       genuinely spreads FROM WITHIN each district's own real footprint,
       not a generic circle that ignores district shape entirely.
    2. Dark BLUE basemap (not black): took two real fixes, not one, both
       verified by inspecting the live rendered iframe DOM rather than
       assumed from a screenshot:
       - The CSS wasn't reaching the page AT ALL, regardless of its
         content - traced to `branca.element` source: a plain
         `folium.Element(css).add_to(m)` (or `get_root().html.add_child`)
         never registers itself when rendered as a map descendant, only a
         real `MacroElement` does (see `_InlineCss` below).
       - Once injection was fixed, confirmed by sampling actual rendered
         pixels (not assumed) that CartoDB `dark_all`'s ocean tiles are
         dark grey (~RGB 30-38), not pure black - so a direct
         `sepia→hue-rotate→saturate` filter chain on `.leaflet-tile-pane`
         does have real color channels to work with, and (verified in a
         screenshot) produces a genuine navy-blue basemap.
    """
    merged = geometry.merge(latest[["District", "Risk", "Number_of_Cases"]], on="District", how="left")
    centroids = merged.geometry.centroid

    risk = merged["Risk"].fillna(0.0)
    risk_min, risk_max = float(risk.min()), float(risk.max())
    colormap = branca_colormap.LinearColormap(
        colors=UBER_GRADIENT_COLORS, vmin=risk_min, vmax=risk_max if risk_max > risk_min else risk_min + 1
    )

    m = folium.Map(
        location=[centroids.y.mean(), centroids.x.mean()], zoom_start=8, tiles=None
    )

    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attr='CartoDB',
        name='Dark Map'
    ).add_to(m)

    def _glow_style(feature: dict) -> dict:
        risk_value = float(feature["properties"]["Risk"]) if feature["properties"]["Risk"] is not None else 0.0
        color = colormap(risk_value)
        return {"fillColor": color, "fillOpacity": 0.8, "color": color, "weight": 1, "opacity": 0.4}

    folium.GeoJson(
        merged[["District", "Risk", "geometry"]].to_json(),
        style_function=_glow_style,
        tooltip=folium.GeoJsonTooltip(fields=["District", "Risk"], aliases=["District", "Hybrid Risk Score"]),
    ).add_to(m)

    # CSS-only glow/tint - no new tile provider or JS dependency needed.
    #
    # Getting this CSS to actually reach the page at all took two real
    # fixes, both verified by inspecting the live rendered iframe DOM
    # rather than assumed from the screenshot alone:
    #
    # 1. Injection mechanism: `folium.Element(css).add_to(m)` (and
    #    `m.get_root().html.add_child(...)`) were both tried first and
    #    verified, via direct DOM inspection, to never appear in the
    #    rendered output at all. Root cause traced into `branca.element`
    #    source: `MacroElement.render()` (what TileLayer/GeoJson use, and
    #    what actually walks a map's children registering each one's
    #    `html`/`script` macro onto the CURRENT root Figure at render
    #    time) has this registration as a side effect; plain
    #    `Element.render()` only returns a string with no such side
    #    effect, so it's silently dropped regardless of where it's
    #    attached. Fixed with `_InlineCss` (a real `MacroElement`
    #    subclass) below - see its own docstring.
    # 2. Tint approach: with injection fixed, a `mix-blend-mode: screen`
    #    overlay `<div>` was tried first assuming the basemap was pure
    #    black - checked by sampling actual rendered pixels (not
    #    assumed): the ocean tiles are dark grey (~RGB 30-38, not 0), so
    #    that assumption was wrong, AND the overlay div still didn't show
    #    any visible tint (likely a z-index/stacking-context mismatch
    #    against Leaflet's own transform-positioned panes). Replaced with
    #    a direct `filter` on `.leaflet-tile-pane` instead - simpler, and
    #    doesn't depend on getting a separate element's stacking position
    #    right: `sepia(1)` converts the near-grayscale tiles into a warm
    #    brown tone (real RGB channel separation, verified nonzero at
    #    these pixel values), `hue-rotate(190deg)` spins that brown to
    #    navy blue, `saturate`/`brightness` tune the final intensity.
    #
    # `blur()` on the GeoJson layer's own SVG paths turns its hard polygon
    # edges into a soft glow that bleeds slightly past the district
    # boundary in every direction, rather than stopping at a sharp line
    # (the choropleth tab already covers the sharp-edged, precise view).
    _InlineCss(
        "<style>"
        ".leaflet-tile-pane { filter: sepia(1) hue-rotate(190deg) saturate(3) brightness(0.6); }"
        ".leaflet-overlay-pane svg path { filter: blur(4px); }"
        "</style>"
    ).add_to(m)

    return m


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


# This file is loaded as a `st.Page` FILE (registered by path in `app.py`),
# not imported for its function alone - so, matching every other page file
# in `views/`, it must actually render on load, not just define a function.
# `district` comes from `st.session_state["district_select"]`, the sidebar
# selectbox `app.py` always renders before `st.navigation(...).run()`
# dispatches to whichever page is currently active - by the time this
# module's top-level code executes, that key is already populated for the
# current script rerun.
_district = st.session_state.get("district_select", DISTRICTS[0])

_live = load_csv(MODULE2_LIVE_RISK_PREDICTIONS_PATH)
_future_risk = load_csv(MODULE2_FUTURE_RISK_PREDICTIONS_PATH)
_future_cases = load_csv(MODULE1_FUTURE_FORECAST_PATH)
_nowcast = load_m1_nowcast()
_m1_weekly = load_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH)
_climate = load_csv(SHARED_CLIMATE_WEEKLY_PATH)
_manifest = load_csv(DASHBOARD_REFRESH_MANIFEST_PATH)
_hybrid_risk = load_csv(MODULE3_HYBRID_RISK_MAP_PATH)
_hotspot_forecast = load_m3_hotspot_forecast()
_district_geometry = load_district_geometry()

_case_y, _case_w = _latest_case_week(_m1_weekly)
_clim_y, _clim_w = _latest_climate_week(_climate)
_refresh_ts = (
    _manifest["refreshed_at_utc"].iloc[0]
    if not _manifest.empty and "refreshed_at_utc" in _manifest.columns
    else None
)
if _refresh_ts:
    st.sidebar.caption(f"Last refresh (UTC): {_refresh_ts}")

render_operational_page(
    live=_live,
    future_risk=_future_risk,
    future_cases=_future_cases,
    nowcast=_nowcast,
    m1_weekly=_m1_weekly,
    climate=_climate,
    manifest=_manifest,
    hybrid_risk=_hybrid_risk,
    hotspot_forecast=_hotspot_forecast,
    district_geometry=_district_geometry,
    case_y=_case_y,
    case_w=_case_w,
    clim_y=_clim_y,
    clim_w=_clim_w,
    refresh_ts=_refresh_ts,
    district=_district,
)
