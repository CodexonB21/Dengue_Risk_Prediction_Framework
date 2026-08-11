"""Research Evidence page — holdout-validated metrics, safe to cite in the thesis/viva."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import MODULE3_FEATURE_IMPORTANCE_PLOT_PATH
from src.dashboard.components import evidence_badge, module_badge
from src.dashboard.data_loaders import (
    RELIABILITY_HOLDOUT_FIG,
    load_m1_district_holdout,
    load_m2_009_baseline,
    load_m3_convergence_log,
    load_m3_feature_importance,
    load_m3_morans_i,
    load_m3_persistence_baseline,
    load_m3_stage_comparison,
    load_production_stack,
    m1_holdout_summary,
    m2_holdout_summary,
    m3_convergence_summary,
    m3_morans_i_summary,
)

# Districts where M1's Stage 2 residual correction regressed holdout MASE
# (production_stack_m1_district_comparison.csv, improved_mase == False) —
# already investigated (M1-009/Decision 034, M1-018) and knowingly NOT
# "fixed": their problem is fold-specific, not validation-visible, so
# forcing a fix would very likely overfit to this one holdout block. Flagged
# here rather than smoothed over, per the project's own stated stance on
# reporting negative results honestly.
M1_REGRESSED_DISTRICTS = ["Kilinochchi", "Mannar", "Vavuniya"]


def render_evidence_page() -> None:
    st.header("Validated research performance")
    evidence_badge("validated")
    st.caption(
        "Metrics below come from walk-forward folds and an untouched 2-year holdout block. "
        "They are the numbers safe to cite in the thesis or viva."
    )

    stack = load_production_stack()
    m1 = m1_holdout_summary(stack)
    m2 = m2_holdout_summary(stack)
    m2_009 = load_m2_009_baseline()
    m1_districts = load_m1_district_holdout()
    m2_stage2_label = m2["architecture"].capitalize() if m2 else "calibration"

    st.markdown(
        f"""
        ### Framework (what we proved)

        | Module | Stage 1 | Stage 2 | Research question |
        |---|---|---|---|
        | **Module 1** | SARIMA (cases only) | XGBoost residual + climate | How many cases next week? |
        | **Module 2** | Outbreak classifier | {m2_stage2_label} calibration | Is this week abnormally high *for this district-week*? |

        Module 1 and Module 2 answer **different questions**. Thresholding Module 1 case forecasts
        is **not** equivalent to Module 2 outbreak alerting.
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        module_badge("m1")
        st.subheader("Module 1: holdout forecasting")
        if m1:
            st.metric("Median MASE (SARIMA only)", f"{m1['median_mase_sarima']:.3f}", help="MASE")
            st.metric("Median MASE (SARIMA + residual correction)", f"{m1['median_mase_hybrid']:.3f}", help="MASE")
            st.metric(
                "Districts improved (MASE)",
                f"{m1['districts_improved_mase']} / {m1['n_districts']}",
            )
            st.metric("Median sMAPE (hybrid)", f"{m1['median_smape_hybrid']:.1f}%", help="sMAPE")
        else:
            st.warning("Production stack summary not found. Run the evaluation pipeline.")

    with col2:
        module_badge("m2")
        st.subheader("Module 2: holdout outbreak alerting")
        if m2:
            st.metric(f"Holdout PR-AUC ({m2['architecture']})", f"{m2['pr_auc']:.3f}", help="PR-AUC")
            st.metric(
                f"Holdout Brier Skill Score ({m2['architecture']})",
                f"{m2['brier_skill_score']:.3f}",
                help="Brier Skill Score",
            )
            if m2.get("alert_recall") is not None:
                st.metric(
                    f"Alert recall @ τ={m2['alert_threshold']}",
                    f"{100 * float(m2['alert_recall']):.1f}%",
                )
                st.metric(
                    f"Alert precision @ τ={m2['alert_threshold']}",
                    f"{100 * float(m2['alert_precision']):.1f}%",
                )
            st.caption("The alert threshold is automatically re-tuned whenever the model is retrained, so it never goes stale.")
        else:
            st.warning("Production stack summary not found.")

    st.divider()
    st.subheader("Why Module 2 is not redundant")
    st.caption("Compares Module 2 alerts against thresholding Module 1's forecasted cases, on the same holdout data.")
    if not m2_009.empty:
        display = m2_009.copy()
        display = display.loc[
            display["rule"].str.startswith("M2 production") | display["rule"].str.startswith("M1 forecast > epidemic")
        ]
        display["rule"] = display["rule"].str.replace(r",\s*tau~=[0-9.]+", "", regex=True)
        for col in ("pr_auc", "recall", "precision", "f2", "prevalence"):
            if col in display.columns:
                display[col] = display[col].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
        display = display.rename(columns={
            "rule": "Method",
            "pr_auc": "PR-AUC",
            "recall": "Recall",
            "precision": "Precision",
            "f2": "F2 Score",
            "n_alerts": "Alerts",
            "n_scored": "Weeks Scored",
            "n_outbreaks": "Outbreaks",
            "prevalence": "Prevalence",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("Run `python scripts/m2_009_m1_alert_baseline.py` to generate comparison table.")

    if not m1_districts.empty and "post_mase" in m1_districts.columns:
        st.subheader("Module 1: per-district holdout MASE")
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

        regressed = m1_districts.loc[
            m1_districts["District"].isin(M1_REGRESSED_DISTRICTS) & ~m1_districts["improved_mase"]
        ]
        if not regressed.empty:
            st.caption(
                f"{', '.join(regressed['District'])} regressed under residual correction on this "
                "holdout block. The pooled model is still kept for these districts rather than a "
                "per-district override."
            )

    if RELIABILITY_HOLDOUT_FIG.exists():
        module_badge("m2")
        st.subheader("Module 2: calibration (holdout)")
        st.image(
            str(RELIABILITY_HOLDOUT_FIG),
            caption=f"Stage 1 raw vs {m2_stage2_label.lower()}: holdout reliability diagram",
        )

    st.divider()
    module_badge("m3")
    st.subheader("Module 3: spatial hotspot detection")
    st.caption(
        "Stage 1 estimates a spatial risk baseline and checks for real geographic clustering. "
        "Stage 2 uses a Random Forest model to correct Stage 1's errors, run for one correction pass."
    )

    morans_df = load_m3_morans_i()
    morans = m3_morans_i_summary(morans_df)
    convergence = m3_convergence_summary(load_m3_convergence_log())
    m3_comparison = load_m3_stage_comparison()
    m3_importance = load_m3_feature_importance()
    m3_persistence = load_m3_persistence_baseline()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Stage 1: spatial clustering validation**")
        if morans:
            st.metric("Global Moran's I", f"{morans['I']:.3f}", help="Moran's I")
            st.metric("p-value (permutation, 999 runs)", f"{morans['p_sim']:.3f}")
            st.metric("Clustering significant?", "Yes" if morans["significant"] else "No")
        else:
            st.warning("Moran's I validation file not found. Run `python -m src.module3_spatial.kde_baseline`.")

        ne_row = morans_df.loc[morans_df.get("check") == "ne_monsoon"] if not morans_df.empty else pd.DataFrame()
        if not ne_row.empty:
            r = ne_row.iloc[0]
            st.caption(
                f"Not every week shows this pattern: the NE-monsoon week ({int(r['Year'])} Wk{int(r['Week'])}) "
                "had no significant spatial clustering. The result above is an overall pattern, not "
                "true for every single week."
            )

    with col2:
        st.markdown("**Stage 2: iterative loop convergence**")
        if convergence:
            st.metric("Converged after", f"{convergence['n_iterations']} iteration(s)")
            st.metric(
                "max|Risk delta| vs. epsilon",
                f"{convergence['max_delta']:.2f} / {convergence['epsilon']:.2f}",
            )
            st.metric("Converged?", "Yes" if convergence["converged"] else "No (hit iteration cap)")
        else:
            st.warning("Convergence log not found. Run `python -m src.module3_spatial.iterative_loop`.")

    st.markdown("**Does Stage 2 improve fit over Stage 1 alone?**")
    if not m3_comparison.empty:
        display = m3_comparison.copy()
        for col in ("corr", "mae", "rmse"):
            if col in display.columns:
                display[col] = display[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        st.dataframe(display, width="stretch", hide_index=True)
        st.success("Genuinely improves fit vs. Stage 1 alone.")
    else:
        st.warning("Stage 1 vs Stage 2 comparison file not found. Run `python -m src.module3_spatial.evaluate`.")

    st.markdown("**Is Stage 2 actually beating a trivial baseline?**")
    if not m3_persistence.empty:
        display = m3_persistence.copy()
        for col in ("corr", "mae", "rmse"):
            if col in display.columns:
                display[col] = display[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        st.dataframe(display, width="stretch", hide_index=True)
        st.success("Now genuinely beats the naive-persistence baseline too.")
    else:
        st.warning("Persistence baseline file not found. Run `python -m src.module3_spatial.persistence_baseline`.")

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

    st.caption(
        "Module 3 does not have a held-out future time block for testing, only cross-validation "
        "across districts. Every map elsewhere in this app already uses out-of-sample predictions, "
        "but there is no separate future period reserved for testing, unlike Module 1 and 2."
    )

    with st.expander("Operational vs validation: what not to cite"):
        st.markdown(
            """
            | | **This page (validation)** | **Operational prototype page** |
            |---|---|---|
            | Purpose | Thesis / viva evidence | Decision-support sketch |
            | Case inputs | Real observed lags only | Module 1 forecasts for forward lags |
            | Climate | Historical observed | Observed + forecast data |
            | Safe to cite PR-AUC/MASE | **Yes** | **No** |
            """
        )


# This file is loaded as a `st.Page` FILE (registered by path in `app.py`),
# so it must render on load like every other page file in `views/`.
render_evidence_page()
