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
    load_m2_uncertainty_bands,
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
        is **not** equivalent to Module 2 outbreak alerting (see M2-009 table below).
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        module_badge("m1")
        st.subheader("Module 1 — holdout forecasting")
        if m1:
            st.metric("Median MASE (SARIMA only)", f"{m1['median_mase_sarima']:.3f}", help="MASE")
            st.metric("Median MASE (SARIMA + residual correction)", f"{m1['median_mase_hybrid']:.3f}", help="MASE")
            st.metric(
                "Districts improved (MASE)",
                f"{m1['districts_improved_mase']} / {m1['n_districts']}",
            )
            st.metric("Median sMAPE (hybrid)", f"{m1['median_smape_hybrid']:.1f}%", help="sMAPE")
        else:
            st.warning("Production stack summary not found — run evaluation pipeline.")

    with col2:
        module_badge("m2")
        st.subheader("Module 2 — holdout outbreak alerting")
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
            st.caption(
                "F2-optimal alert threshold, re-selected fresh from validation folds each time "
                "Stage 1/2 is retrained (currently read live, never hardcoded)."
            )
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

        regressed = m1_districts.loc[
            m1_districts["District"].isin(M1_REGRESSED_DISTRICTS) & ~m1_districts["improved_mase"]
        ]
        if not regressed.empty:
            st.caption(
                f"**Honest limitation, not hidden**: {', '.join(regressed['District'])} regressed under "
                "residual correction on this holdout block (investigated in M1-009/Decision 034 and "
                "M1-018 — a fold-specific effect, not fixable without risking overfit to this one "
                "holdout). The pooled model is still kept for these districts rather than a per-district "
                "override, per Decision 002/014's confirmed pooling result."
            )

    if RELIABILITY_HOLDOUT_FIG.exists():
        module_badge("m2")
        st.subheader("Module 2 — calibration (holdout)")
        st.image(
            str(RELIABILITY_HOLDOUT_FIG),
            caption=f"Stage 1 raw vs {m2_stage2_label.lower()} — holdout reliability diagram",
        )

    uncertainty = load_m2_uncertainty_bands()
    if not uncertainty.empty:
        st.subheader("Module 2 — per-prediction uncertainty (holdout)")
        evidence_badge("validated")
        st.caption(
            "Venn-Abers interval `[venn_abers_p0, venn_abers_p1]` around each calibrated probability "
            "(M2-012) — same no-leakage fold structure as Stage 2's own calibrator. Width scales with "
            "risk: an evaluator can see not just the probability, but how much that specific number "
            "should be trusted."
        )
        holdout_bands = uncertainty.loc[
            (uncertainty["split"] == "holdout") & (uncertainty["is_selected_model"])
        ]
        if not holdout_bands.empty:
            fig = px.scatter(
                holdout_bands,
                x="predicted_probability",
                y="venn_abers_width",
                title="Uncertainty interval width vs. Stage 1 probability (holdout)",
                labels={
                    "predicted_probability": "Stage 1 raw probability",
                    "venn_abers_width": "Interval width (venn_abers_p1 − venn_abers_p0)",
                },
                opacity=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Bands are computed on holdout/validation folds only. Forward-week (operational) "
                "predictions do not yet have bands — treat that as a documented gap, not a fabricated "
                "error bar."
            )

    st.divider()
    module_badge("m3")
    st.subheader("Module 3 — spatial hotspot detection (KDE + RF residual compensation)")
    st.caption(
        "Stage 1: Kernel Density Estimation + Global Moran's I spatial baseline. "
        "Stage 2: Random Forest RELATIVE-residual compensation (own-district relative-"
        "residual lag features, M3-015 — target is (Actual - Risk_0) / (Risk_0 + 1), "
        "not the raw difference, since the raw residual was found strongly "
        "heteroscedastic), capped at 1 iteration by design — the lag features are "
        "fixed relative to Risk_0, so retraining past iteration 1 is not well-founded "
        "for this feature set (see MODULE_CONTEXT.md)."
    )

    morans_df = load_m3_morans_i()
    morans = m3_morans_i_summary(morans_df)
    convergence = m3_convergence_summary(load_m3_convergence_log())
    m3_comparison = load_m3_stage_comparison()
    m3_importance = load_m3_feature_importance()
    m3_persistence = load_m3_persistence_baseline()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Stage 1 — spatial clustering validation**")
        if morans:
            st.metric("Global Moran's I", f"{morans['I']:.3f}", help="Moran's I")
            st.metric("p-value (permutation, 999 runs)", f"{morans['p_sim']:.3f}")
            st.metric("Clustering significant?", "Yes" if morans["significant"] else "No")
        else:
            st.warning("Moran's I validation file not found — run `python -m src.module3_spatial.kde_baseline`.")

        ne_row = morans_df.loc[morans_df.get("check") == "ne_monsoon"] if not morans_df.empty else pd.DataFrame()
        if not ne_row.empty:
            r = ne_row.iloc[0]
            st.caption(
                f"**Not universal, shown honestly**: the NE-monsoon representative week "
                f"({int(r['Year'])} Wk{int(r['Week'])}) shows **no** significant spatial clustering "
                f"(I={r['I']:.3f}, p={r['p_sim']:.3f}) — the aggregated result above should not be read "
                "as 'every week is spatially clustered.'"
            )

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
        st.dataframe(display, width="stretch", hide_index=True)
        st.success("Genuinely improves fit vs. Stage 1 alone (M3-015) — see below for how this was verified.")
    else:
        st.warning("Stage 1 vs Stage 2 comparison file not found — run `python -m src.module3_spatial.evaluate`.")

    st.markdown("**Is Stage 2 actually beating a trivial baseline?**")
    if not m3_persistence.empty:
        display = m3_persistence.copy()
        for col in ("corr", "mae", "rmse"):
            if col in display.columns:
                display[col] = display[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        st.dataframe(display, width="stretch", hide_index=True)
        st.success("Now genuinely beats the naive-persistence baseline too (M3-015) — see below.")
    else:
        st.warning("Persistence baseline file not found — run `python -m src.module3_spatial.persistence_baseline`.")

    with st.expander("How Stage 2 evolved — M3-005 → M3-008 → M3-015"):
        st.markdown(
            "1. **Climate/demographic covariates alone (M3-005):** null result — no "
            "genuine improvement over Stage 1.\n"
            "2. **+ own-district absolute-residual lags (M3-008):** beat Stage 1 "
            "(MAE 20.54 → 9.96, ~51% reduction) but still lost to naive persistence "
            "on MAE (9.44 vs. 9.96) — only won on correlation and RMSE.\n"
            "3. **Relative residual instead of absolute (M3-015):** a direct diagnostic "
            "found the absolute residual strongly heteroscedastic (error scales with "
            "predicted magnitude), letting the largest outbreak weeks dominate the "
            "learning signal. Predicting the RELATIVE residual instead (MAE 20.54 → "
            "8.03, ~61% reduction; correlation 0.824 → 0.959) beats BOTH Stage 1 and "
            "naive persistence on every metric, confirmed via a week-level bootstrap, "
            "not just the aggregate table above.\n\n"
            "**Two honest caveats remain**: the RMSE gain is proportionally larger in "
            "the highest-case-volume spatial fold, and the model is noticeably weaker "
            "at the NE-monsoon week already flagged above as non-clustered — see "
            "`EXPERIMENT_LOG.md` M3-015 for the full numbers."
        )

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
        "**Honest limitation**: Module 3 has no temporal holdout (only spatial K-means CV) — "
        "every map shown elsewhere in this app is already out-of-fold by construction, but there is "
        "no held-back future block the way Module 1/2 have. See `QUESTIONS_FOR_DEFENSE.md`."
    )

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


# This file is loaded as a `st.Page` FILE (registered by path in `app.py`),
# so it must render on load like every other page file in `views/`.
render_evidence_page()
