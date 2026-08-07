"""Dashboard page renderers: validated research evidence vs operational prototype."""

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


def render_operational_page(
    *,
    live: pd.DataFrame,
    future_risk: pd.DataFrame,
    future_cases: pd.DataFrame,
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

        # A radio switcher, not st.tabs(): Streamlit mounts every st.tabs()
        # panel's content on every script run and only CSS-hides the
        # inactive ones - a Leaflet map mounted inside a display:none
        # container sizes itself to zero and never recovers (this is
        # exactly what made the Folium map render totally blank earlier,
        # see MODULE_CONTEXT.md's root-cause note). A radio button instead
        # means Python only ever constructs the ONE currently-selected
        # map each run, so the other two are never mounted hidden at all.
        view = st.radio(
            "Module 3 map view",
            [
                "District boundaries (choropleth)",
                "Heat cloud (Folium)",
                "Hotspot markers (precise)",
                "Heat glow (Uber-style)",
            ],
            horizontal=True,
            label_visibility="collapsed",
            key="module3_map_view",
        )

        if view == "District boundaries (choropleth)":
            st.caption(
                "Precise district polygons colored by Hybrid Risk (YlOrRd) - each district "
                "reads as a single flat value, the exact number driving the other two views' "
                "color/size but without their spatial blending or double-encoding."
            )
            fig = _hybrid_risk_choropleth(district_geometry, latest, district, latest_year, latest_week)
            st.plotly_chart(fig, use_container_width=True)
        elif view == "Heat cloud (Folium)":
            st.caption(
                "Continuous heat-cloud intensity weighted by Hybrid Risk, interpolated via "
                "nearest-neighbour distance weighting — risk visibly concentrates toward the "
                "border between two high-risk neighbouring districts rather than blobbing "
                "solidly around each district's own centroid. Click a pin for that district's "
                "exact values."
            )
            heatmap = _hybrid_risk_folium_heatmap(district_geometry, latest, district)
            st_folium(heatmap, use_container_width=True, height=600, returned_objects=[])
        elif view == "Hotspot markers (precise)":
            st.caption(
                "One marker per district centroid, both SIZE and COLOR driven by that "
                "district's Hybrid Risk (bigger and redder = higher risk) - a precise, "
                "double-encoded complement to the heat-cloud's smoothed, border-blended view. "
                "Click a marker for that district's exact values."
            )
            circle_map = _hybrid_risk_circle_map(district_geometry, latest, district)
            st_folium(circle_map, use_container_width=True, height=600, returned_objects=[])
        else:
            st.caption(
                "Uber Rider-app style heat glow: dark blue-tinted basemap, each district's "
                "own real shape glowing green-to-red by Hybrid Risk (blurred edges, not a "
                "generic circle). A stylistic view, not the fine-grained interpolation the "
                "Heat cloud tab uses."
            )
            uber_map = _hybrid_risk_uber_heatmap(district_geometry, latest, district)
            st_folium(uber_map, use_container_width=True, height=600, returned_objects=[])

        district_row = latest.loc[latest["District"] == district]
        if not district_row.empty:
            row = district_row.iloc[0]
            m1, m2 = st.columns(2)
            m1.metric(f"{district}: Hybrid Risk", f"{row['Risk']:.1f}")
            m2.metric(f"{district}: Actual cases (same week)", int(row["Number_of_Cases"]))

        st.markdown(f"##### {district}: actual vs. predicted, full history")
        st.caption(
            "Predicted (Hybrid Risk) is out-of-fold (5-fold spatial K-means CV) — a model "
            "that never trained on this district. The panel below shows Predicted minus "
            "Actual: green above zero = over-predicted, red below zero = under-predicted. "
            "Change the district in the sidebar to update both panels together."
        )
        history_fig = _hybrid_risk_actual_vs_predicted_chart(hybrid_risk, district)
        st.plotly_chart(history_fig, use_container_width=True)

    st.divider()
    st.subheader("Module 3 — next-week hotspot forecast")
    st.warning(
        "**Evidence tier: operational** — the forecast week's CASE COUNT is Module 1's "
        "forward forecast (`cases_source=module1_forecast`), not yet reported. Its CLIMATE "
        "is real observed weather, not a meteorological forecast — Module 3's case-count "
        "reporting lags real calendar time by several weeks, so the forecast week's dates "
        "have already passed by the time this runs. See Decision 031 "
        "(`research_context/RESEARCH_DECISIONS.md`) for the full reasoning."
    )
    if hotspot_forecast.empty or district_geometry.empty:
        st.info(
            "Forecast not found — run `python -m src.module3_spatial.forecast_future`."
        )
    else:
        fc_latest = hotspot_forecast.sort_values(["Year", "Week"]).groupby(["Year", "Week"]).tail(len(DISTRICTS))
        fc_year = int(fc_latest["Year"].iloc[0])
        fc_week = int(fc_latest["Week"].iloc[0])
        st.caption(f"Forecast district-week: **{fc_year} Wk{fc_week}** (selected district **{district}** outlined in black).")

        fc_adapter = fc_latest.rename(columns={"Risk_forecast": "Risk", "cases_forecast": "Number_of_Cases"})
        fc_heatmap = _hybrid_risk_folium_heatmap(district_geometry, fc_adapter, district)
        st_folium(fc_heatmap, use_container_width=True, height=600, returned_objects=[], key="module3_forecast_heatmap")

        fc_row = fc_adapter.loc[fc_adapter["District"] == district]
        if not fc_row.empty:
            row = fc_row.iloc[0]
            m1, m2 = st.columns(2)
            m1.metric(f"{district}: Forecast Hybrid Risk", f"{row['Risk']:.1f}")
            m2.metric(f"{district}: Forecast cases (Module 1)", f"{row['Number_of_Cases']:.1f}")
