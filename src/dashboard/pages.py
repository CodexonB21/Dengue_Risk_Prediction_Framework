"""Dashboard page renderers: validated research evidence vs operational prototype."""

from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium

from src.config import (
    DASHBOARD_REFRESH_MANIFEST_PATH,
    DISTRICTS,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
    MODULE2_LIVE_RISK_PREDICTIONS_PATH,
    MODULE3_FEATURE_IMPORTANCE_PLOT_PATH,
    SHARED_CLIMATE_WEEKLY_PATH,
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
from src.dashboard.evidence_data import (
    RELIABILITY_HOLDOUT_FIG,
    load_m1_district_holdout,
    load_m2_009_baseline,
    load_m3_convergence_log,
    load_m3_feature_importance,
    load_m3_morans_i,
    load_m3_stage_comparison,
    load_production_stack,
    m1_holdout_summary,
    m2_holdout_summary,
    m3_convergence_summary,
    m3_morans_i_summary,
)


def render_evidence_page() -> None:
    st.header("Validated research performance")
    st.success(
        "**Evidence tier: validation** — metrics below come from walk-forward folds and an "
        "untouched 2-year holdout block. They are the numbers safe to cite in the thesis or viva."
    )

    stack = load_production_stack()
    m1 = m1_holdout_summary(stack)
    m2 = m2_holdout_summary(stack)
    m2_009 = load_m2_009_baseline()
    m1_districts = load_m1_district_holdout()

    st.markdown(
        """
        ### Framework (what we proved)

        | Module | Stage 1 | Stage 2 | Research question |
        |---|---|---|---|
        | **Module 1** | SARIMA (cases only) | XGBoost residual + climate | How many cases next week? |
        | **Module 2** | Outbreak classifier | Isotonic calibration | Is this week abnormally high *for this district-week*? |

        Module 1 and Module 2 answer **different questions**. Thresholding Module 1 case forecasts
        is **not** equivalent to Module 2 outbreak alerting (see M2-009 table below).
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Module 1 — holdout forecasting")
        if m1:
            st.metric("Median MASE (SARIMA only)", f"{m1['median_mase_sarima']:.3f}")
            st.metric("Median MASE (SARIMA + residual correction)", f"{m1['median_mase_hybrid']:.3f}")
            st.metric(
                "Districts improved (MASE)",
                f"{m1['districts_improved_mase']} / {m1['n_districts']}",
            )
            st.metric("Median sMAPE (hybrid)", f"{m1['median_smape_hybrid']:.1f}%")
        else:
            st.warning("Production stack summary not found — run evaluation pipeline.")

    with col2:
        st.subheader("Module 2 — holdout outbreak alerting")
        if m2:
            st.metric("Holdout PR-AUC (isotonic)", f"{m2['pr_auc']:.3f}")
            st.metric(
                f"Alert recall @ τ={m2['alert_threshold']}",
                f"{100 * float(m2['alert_recall']):.1f}%",
            )
            st.metric(
                f"Alert precision @ τ={m2['alert_threshold']}",
                f"{100 * float(m2['alert_precision']):.1f}%",
            )
            st.caption("F2-optimal alert threshold from validation folds (Decision 024/025).")
        else:
            st.warning("Production stack summary not found.")

    st.divider()
    st.subheader("Why Module 2 is not redundant (M2-009 holdout)")
    st.caption(
        "Same holdout block and epidemic-threshold label. Compares Module 2 alerts vs "
        "thresholding Module 1 `final_prediction`."
    )
    if not m2_009.empty:
        display = m2_009.copy()
        for col in ("pr_auc", "recall", "precision", "f2", "prevalence"):
            if col in display.columns:
                display[col] = display[col].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("Run `python scripts/m2_009_m1_alert_baseline.py` to generate comparison table.")

    if not m1_districts.empty and "post_mase" in m1_districts.columns:
        st.subheader("Module 1 — per-district holdout MASE")
        plot_df = m1_districts.sort_values("post_mase").copy()
        plot_df = plot_df.rename(columns={"pre_mase": "SARIMA only", "post_mase": "Hybrid (SARIMA + correction)"})
        fig = px.bar(
            plot_df,
            x="District",
            y=["SARIMA only", "Hybrid (SARIMA + correction)"],
            barmode="group",
            title="Holdout MASE by district (lower is better)",
        )
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="MASE")
        st.plotly_chart(fig, use_container_width=True)

    if RELIABILITY_HOLDOUT_FIG.exists():
        st.subheader("Module 2 — calibration (holdout)")
        st.image(str(RELIABILITY_HOLDOUT_FIG), caption="Stage 1 raw vs isotonic — holdout reliability diagram")

    st.divider()
    st.subheader("Module 3 — spatial hotspot detection (KDE + RF residual compensation)")
    st.caption(
        "Stage 1: Kernel Density Estimation + Global Moran's I spatial baseline. "
        "Stage 2: Random Forest residual compensation, wrapped in an iterative "
        "refinement loop (max 4 iterations, dual convergence check)."
    )

    morans = m3_morans_i_summary(load_m3_morans_i())
    convergence = m3_convergence_summary(load_m3_convergence_log())
    m3_comparison = load_m3_stage_comparison()
    m3_importance = load_m3_feature_importance()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Stage 1 — spatial clustering validation**")
        if morans:
            st.metric("Global Moran's I", f"{morans['I']:.3f}")
            st.metric("p-value (permutation, 999 runs)", f"{morans['p_sim']:.3f}")
            st.metric("Clustering significant?", "Yes" if morans["significant"] else "No")
        else:
            st.warning("Moran's I validation file not found — run `python -m src.module3_spatial.kde_baseline`.")

    with col2:
        st.markdown("**Stage 2 — iterative loop convergence**")
        if convergence:
            st.metric("Converged after", f"{convergence['n_iterations']} iteration(s)")
            st.metric(
                "max|Risk delta| vs. epsilon",
                f"{convergence['max_delta']:.2f} / {convergence['epsilon']:.2f}",
            )
            st.metric("Converged?", "Yes" if convergence["converged"] else "No (hit iteration cap)")
        else:
            st.warning("Convergence log not found — run `python -m src.module3_spatial.iterative_loop`.")

    st.markdown("**Does Stage 2 improve fit over Stage 1 alone?**")
    if not m3_comparison.empty:
        display = m3_comparison.copy()
        for col in ("corr", "mae", "rmse"):
            if col in display.columns:
                display[col] = display[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.info(
            "**Null result, reported honestly**: Stage 2's residual correction does NOT "
            "improve aggregate fit to actual case counts (correlation -0.0037, MAE +1.7%, "
            "RMSE +0.9% vs. Stage 1 alone). This is expected, not a bug — the shrinkage "
            "term (alpha=0.05) was chosen for stable, immediate convergence, not accuracy. "
            "Stage 2's real value is diagnostic: the feature importance below reveals "
            "*which* factors (population density, climate timing) drive district-level "
            "burden beyond pure spatial proximity — something Stage 1's KDE baseline, "
            "with zero covariates, structurally cannot provide."
        )
    else:
        st.warning("Stage 1 vs Stage 2 comparison file not found — run `python -m src.module3_spatial.evaluate`.")

    if not m3_importance.empty:
        st.markdown("**Stage 2 feature importance**")
        if MODULE3_FEATURE_IMPORTANCE_PLOT_PATH.exists():
            st.image(
                str(MODULE3_FEATURE_IMPORTANCE_PLOT_PATH),
                caption="Random Forest feature importance (final model, all 25 districts)",
            )
        else:
            fig = px.bar(
                m3_importance.sort_values("importance"),
                x="importance",
                y="feature",
                orientation="h",
                title="Stage 2 feature importance",
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Operational vs validation — what not to cite"):
        st.markdown(
            """
            | | **This page (validation)** | **Operational prototype page** |
            |---|---|---|
            | Purpose | Thesis / viva evidence | Decision-support sketch |
            | Case inputs | Real observed lags only | M1 forecasts for forward lags |
            | Climate | Historical observed | Observed + forecast API |
            | Safe to cite PR-AUC/MASE | **Yes** | **No** |

            See `research_context/QUESTIONS_FOR_DEFENSE.md` and `src/dashboard/DASHBOARD_GUIDE.md`.
            """
        )


def _latest_hybrid_risk(hybrid_risk: pd.DataFrame) -> pd.DataFrame:
    if hybrid_risk.empty:
        return pd.DataFrame()
    latest_key = hybrid_risk.sort_values(["Year", "Week"]).iloc[-1]
    return hybrid_risk.loc[
        (hybrid_risk["Year"] == latest_key["Year"]) & (hybrid_risk["Week"] == latest_key["Week"])
    ]


# 1500m - finer than the risk_surface.py report figure's 1000m would be
# overkill for a browser-rendered PNG, but this needs to stay well below
# any resolution a user could zoom in far enough to visually resolve as
# separate raster cells (unlike the old point-based Leaflet HeatMap, this
# is a real image scaled to `bounds`, so higher resolution only costs a
# larger PNG, not per-zoom-level correctness).
DASHBOARD_GRID_RESOLUTION_M = 1500.0


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


def render_operational_page(
    *,
    live: pd.DataFrame,
    future_risk: pd.DataFrame,
    future_cases: pd.DataFrame,
    m1_weekly: pd.DataFrame,
    climate: pd.DataFrame,
    manifest: pd.DataFrame,
    hybrid_risk: pd.DataFrame,
    district_geometry: "gpd.GeoDataFrame",
    case_y: int | None,
    case_w: int | None,
    clim_y: int | None,
    clim_w: int | None,
    refresh_ts: str | None,
    district: str,
) -> None:
    st.header("Operational monitoring prototype")
    st.warning(
        "**Evidence tier: operational** — not holdout-validated. Use for integration demo only. "
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
        st.caption("Recent observed weeks — production checkpoint; weeks may overlap training history.")
        if live.empty:
            st.warning("No live risk predictions.")
        else:
            dlive = live.loc[live["District"] == district].sort_values(["Year", "Week"])
            st.dataframe(
                dlive[
                    [
                        "Year", "Week", "calibrated_probability", "risk_tier", "alert_flag",
                        "feature_completeness_pct", "already_scored_in_pipeline",
                    ]
                ],
                use_container_width=True,
            )
            fig = px.line(
                dlive,
                x="Week_Start_Date",
                y="calibrated_probability",
                markers=True,
                title=f"{district}: recent calibrated probability (operational)",
            )
            fig.add_hline(y=0.14, line_dash="dot", annotation_text="alert threshold")
            st.plotly_chart(fig, use_container_width=True)

    with tab_cases:
        st.caption("Module 1 forward forecast — recursive multi-step; **not** holdout MASE.")
        hist = m1_weekly.loc[m1_weekly["District"] == district].sort_values(["Year", "Week"]).tail(52)
        fut = future_cases.loc[future_cases["District"] == district].sort_values("horizon_step")
        if hist.empty and fut.empty:
            st.warning("No case forecast data.")
        else:
            fig = px.line(title=f"{district}: cases — history + 8-week forward (operational)")
            if not hist.empty:
                fig.add_scatter(
                    x=hist["Week_Start_Date"],
                    y=hist["Number_of_Cases"],
                    mode="lines+markers",
                    name="Actual",
                )
            if not fut.empty:
                fig.add_scatter(
                    x=fut["Week_Start_Date"],
                    y=fut["final_prediction"],
                    mode="lines+markers",
                    name="Forecast (M1)",
                )
            st.plotly_chart(fig, use_container_width=True)

    with tab_forward:
        st.warning(
            "Horizon ≥ 2 uses Module 1 predicted case lags and forecast climate. "
            "Uncertainty compounds — treat as scenario view, not validated probability."
        )
        dfwd = future_risk.loc[future_risk["District"] == district].sort_values("horizon_step")
        if dfwd.empty:
            st.warning("No forward risk predictions.")
        else:
            st.dataframe(
                dfwd[
                    [
                        "horizon_step", "prediction_type", "Year", "Week",
                        "calibrated_probability", "risk_tier", "alert_flag",
                        "cases_source", "climate_source", "feature_completeness_pct",
                        "uses_module1_cases", "evidence_tier",
                    ]
                ],
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
    st.subheader("Module 3 — spatial hotspot map (Hybrid Risk)")
    st.warning(
        "**Evidence tier: operational** — Hybrid Risk is Stage 2's output (KDE spatial "
        "baseline + RF residual correction), not a validated forecast. See the "
        "**Research evidence** page for Stage 1/Stage 2 validation numbers "
        "(Moran's I, convergence, fit comparison)."
    )

    if hybrid_risk.empty or district_geometry.empty:
        st.info(
            "Hybrid risk map or district geometry not found — run "
            "`python -m src.module3_spatial.iterative_loop`."
        )
    else:
        latest = _latest_hybrid_risk(hybrid_risk)
        latest_year = int(latest["Year"].iloc[0])
        latest_week = int(latest["Week"].iloc[0])
        st.caption(
            f"Latest available district-week: **{latest_year} Wk{latest_week}** "
            f"(selected district **{district}** outlined in black)."
        )

        st.caption(
            "Continuous heat-cloud intensity weighted by Hybrid Risk, interpolated via "
            "nearest-neighbour distance weighting — risk visibly concentrates toward the "
            "border between two high-risk neighbouring districts rather than blobbing "
            "solidly around each district's own centroid. Click a pin for that district's "
            "exact values."
        )
        heatmap = _hybrid_risk_folium_heatmap(district_geometry, latest, district)
        st_folium(heatmap, use_container_width=True, height=600, returned_objects=[])

        district_row = latest.loc[latest["District"] == district]
        if not district_row.empty:
            row = district_row.iloc[0]
            m1, m2 = st.columns(2)
            m1.metric(f"{district}: Hybrid Risk", f"{row['Risk']:.1f}")
            m2.metric(f"{district}: Actual cases (same week)", int(row["Number_of_Cases"]))
