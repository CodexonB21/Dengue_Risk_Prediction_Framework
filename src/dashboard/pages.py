"""Dashboard page renderers: validated research evidence vs operational prototype."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st

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

        fig = _hybrid_risk_choropleth(district_geometry, latest, district, latest_year, latest_week)
        st.plotly_chart(fig, use_container_width=True)

        district_row = latest.loc[latest["District"] == district]
        if not district_row.empty:
            row = district_row.iloc[0]
            m1, m2 = st.columns(2)
            m1.metric(f"{district}: Hybrid Risk", f"{row['Risk']:.1f}")
            m2.metric(f"{district}: Actual cases (same week)", int(row["Number_of_Cases"]))
