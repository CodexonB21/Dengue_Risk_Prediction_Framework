# Dashboard Viva Demo Guide

## Purpose

This is a **live-demo script**, not a developer reference — see `src/dashboard/DASHBOARD_GUIDE.md`
for how to run it, its file architecture, and troubleshooting. This file covers what to actually
click, in what order, during a defense, and which question each page/section is built to answer.

**One rule this whole guide follows, deliberately:** no specific threshold, metric, or count value
is written down here. The app itself is the single source of truth for those (read live from
`get_thresholds()`, the metrics CSVs, etc.) — this exact duplication is what let the dashboard go
stale once already (Decision 047 changed the production threshold while a separate guide still
quoted the old value for over a week). Where this guide needs to reference a number, it tells you
*where on the page* to look, not what the number currently is.

**How to use this:** read the page-by-page section once to know what exists, then use the
"suggested demo path" as a rehearsable click-through, and keep the "likely questions" table open
during a live Q&A.

---

## Before You Start

Launch per `DASHBOARD_GUIDE.md`: `streamlit run src/dashboard/app.py` from the project root, venv
activated, dashboard CSVs already generated (run `python scripts/refresh_dashboard_data.py` once
if you haven't recently).

The **sidebar** (visible on every page) has three controls, in order:
1. **District (operational page)** — a dropdown of all 25 districts. This drives every
   district-specific chart on the Operational Monitoring page. Set it *before* switching to that
   page if you have a specific district story ready (e.g. Colombo/Gampaha, since they're the
   districts with the real 2026 outbreak).
2. **Skip weather fetch** checkbox + **Refresh operational data** button — reruns the whole
   pipeline live. **Do not click this mid-demo unless you mean it** — it takes several minutes and
   will visibly block the UI with a spinner. Rehearse this once beforehand if you want to show it
   live; otherwise mention it exists and move on.
3. **📖 Glossary** expander at the bottom — every jargon column (`calibrated_probability`,
   `horizon_step`, `feature_completeness_pct`, etc.) defined in one place. If an evaluator asks
   "what does column X mean," this is faster than explaining verbally — open it and point.

The four pages are listed in the main nav in a fixed, deliberate order — **validated evidence
before operational prototype before the tracking mechanism** — mirroring the project's own
evidence-tier discipline. Presenting them out of order (e.g. leading with the map) undersells that
discipline; consider following the built-in order live.

---

## Page 1 — Overview

**What it's for:** a 30-second cold-open — the single page you'd show someone who has never seen
this project before anything else.

**What's on it, top to bottom:**
- A one-paragraph plain-language description of the "baseline + correction" pattern shared by all
  three modules.
- Three columns, one per module, each with a module-colored badge, the module's one-line research
  question (*"how many cases next week?"* / *"is this district-week an outbreak?"* / *"where is
  risk spatially clustering?"*), and one headline holdout metric (Module 1's hybrid MASE, Module
  2's PR-AUC, Module 3's Global Moran's I) — **all three metric values are read live from the
  underlying CSVs**, never hardcoded.
- An **evidence-tier legend**: the three colored badges (validated / operational-live /
  operational-prospective) used consistently on every other page, each with a one-line meaning.
  This is worth reading aloud once — it's the interpretive key for everything that follows.
- A **"how to read this dashboard"** numbered list, which is literally the page order below.

**What to say:** "Every number on this dashboard carries one of three evidence-tier badges. That
badge — not the page it's on — tells you whether a number is safe to cite as validated model
skill, or is a live/forward output with no ground truth yet. I'll point out the badge as we go."

**Questions this page is built to pre-empt:** "why are there three separate modules instead of
one model" (answered by the three-column framing) and "how do I know which numbers are the real
result vs. a demo" (answered by the evidence-tier legend).

---

## Page 2 — Research Evidence

**What it's for:** every number here is holdout-validated — this is the page whose numbers you can
directly cite in the viva/thesis. If challenged on any headline claim, this is where you show the
receipts.

**What's on it, top to bottom:**
- A **framework table**: Module 1 vs. Module 2's Stage 1/Stage 2/research-question, with an
  explicit note that thresholding Module 1's forecast is *not* the same as Module 2's alerting
  (cross-references the M2-009 comparison further down).
- **Two columns**: Module 1's holdout metrics (SARIMA-only MASE, hybrid MASE, districts improved,
  sMAPE) and Module 2's holdout metrics (PR-AUC, Brier Skill Score, alert recall/precision at the
  current threshold).
- The **M2-009 table** — Module 2's alerting vs. simply thresholding Module 1's case forecast.
  This is the concrete answer to "why do you need Module 2 if Module 1 already forecasts cases."
- A **per-district Module 1 MASE bar chart** (SARIMA-only vs. hybrid, sorted), with an explicit
  caption naming the districts that *regressed* under residual correction and why they weren't
  force-fixed. **This is deliberately on the page, not hidden** — if an evaluator asks about
  underperforming districts, you don't need to volunteer names yourself; the chart already shows
  them.
- Module 2's **reliability diagram** (Stage 1 raw vs. calibrated) and, below it, a **Venn-Abers
  uncertainty scatter** (interval width vs. probability) — both explicitly captioned as
  validated/holdout-only, with forward-week predictions noted as not yet having bands.
- A full **Module 3 section**: Moran's I clustering validation (including the NE-monsoon
  representative-week counter-example, shown honestly rather than omitted), the iterative loop's
  convergence result, a Stage-1-vs-Stage-2 fit comparison, a naive-persistence-baseline comparison,
  an expandable **"How Stage 2 evolved" walkthrough** (M3-005 → M3-008 → M3-015, including the
  intermediate null and near-miss results), and Stage 2 feature importance.
- A closing expander, **"Operational vs. validation — what not to cite"** — a direct table
  contrasting this page against the next one.

**What to say:** "Everything above this line came from walk-forward folds and an untouched
holdout block. If you want to check a specific district or a specific claim, it's on this page."

**Questions this page is built to pre-empt:** "did every district improve" (no — shown honestly),
"why do you need Module 2 separately" (M2-009 table), "does Module 3 actually work" (the
evolution expander shows the honest path there, including the parts that didn't work at first).

---

## Page 3 — Operational Monitoring

**What it's for:** a live/forward decision-support **prototype**. Explicitly labeled
`operational_live` at the top — **never cite anything on this page as validated accuracy**; it's
there to demonstrate the integration works end to end, not to prove skill.

**What's on it, top to bottom:**
1. A **data-freshness banner** (last case epi-week, last climate epi-week, last refresh
   timestamp) — useful to point at if asked "how current is this."
2. The **Module 1 nowcast panel** — the genuine single-step "predict next week using everything
   known right now" number (distinct from the 8-week recursive forecast further down), for
   whichever district is selected in the sidebar, plus a national top-5 table.
3. **National triage** — count of districts flagged at the nearest forward horizon and across the
   next 4 weeks, explicitly captioned as "early-warning flags, not validated detections," plus a
   top-5-by-probability table.
4. A **district drill-down** with three tabs, for the sidebar-selected district:
   - **Recent risk** — a table plus a time-series chart of calibrated probability with the current
     alert threshold drawn as a line. Weeks that immediately follow a flagged reporting-delay dip
     are marked with an orange ✕ — point this out if the chart looks like it has an unexplained
     wobble.
   - **Case forecast** — actual case history plus the 8-week forward forecast, same
     reporting-anomaly markers overlaid directly on the case-count line.
   - **Forward risk** — a horizon-indexed table and bar chart; explicitly warns that horizon ≥ 2
     uses Module 1's *predicted* case counts as an input, so treat it as a scenario view.
5. **Module 3's spatial hotspot map** — a single continuous heat-cloud (folium `ImageOverlay`,
   IDW-interpolated), with a **"This week" / "Next week (forecast)"** toggle above it and (under
   "This week" only) an expander to scrub to an earlier week via a slider. An expander above the
   map, **"How this map is built,"** explains the interpolation and the this-week/next-week
   distinction in plain language — open it if asked how the color blending works. Below the map:
   a top-5-by-risk table and an **"out-of-fold model accuracy"** expander showing actual-vs-predicted
   history for the selected district.

**What to say:** "This page shows the same frozen, already-validated models applied to the most
current data — it's a decision-support demo, not additional proof of accuracy. That proof lives on
the Research Evidence page."

**Questions this page is built to pre-empt:** "can I see this working on real, current data" (yes
— this whole page), "why does the map look smooth instead of having hard district borders" (the
"How this map is built" expander), "what if the input weather/cases are themselves forecasts"
(the `cases_source`/`climate_source` columns and the reporting-anomaly markers make this explicit
rather than silent).

**A note on the map, since documentation elsewhere says otherwise:** some project documentation
(`module_3_spatial/MODULE_CONTEXT.md`) describes four switchable Module 3 map styles from an
earlier iteration (choropleth, heat-cloud, circle markers, "Uber-style" glow). **The current live
app only shows one — the heat-cloud** — behind the "This week / Next week" toggle described above.
The other three view functions still exist in `operational_monitoring.py` but aren't wired into
the page anymore. Don't promise a style switcher that isn't there; if asked, you can honestly say
alternative map styles were prototyped and the current version was kept as the primary view.

---

## Page 4 — Prospective Tracking

**What it's for:** the self-checking mechanism for the *forward* predictions shown on page 3 — not
a backtest, and not a live snapshot, but a log that gets checked against reality once real weeks
pass.

**What's on it, top to bottom:**
- An explanatory framing distinguishing this from the other two evidence tiers, plus an explicit
  **"why this page can legitimately look empty right now"** notice.
- **Module 1's nowcast tracker**: predictions logged vs. resolved, and (once any exist) a table of
  resolved accuracy.
- **Module 2's forward-risk tracker**: same structure, for outbreak-alert predictions.
- **Module 3's forward hotspot-forecast tracker** (added Decision 052/M3-016): same log/resolved
  structure, for the spatial Hybrid Risk forecast. Reconciliation recomputes Stage 1's KDE baseline
  from the real reported case count once available and reapplies the already-logged Stage 2
  residual unchanged, separating total forecast error from the portion inherited specifically from
  Module 1's case-count forecast — a concrete, if early, read on the error-compounding limitation
  named on the Operational Monitoring page.
- A closing note that Module 2's own outbreak prevalence is low (~1.5% on holdout), so
  accumulating enough resolved *outbreak* weeks specifically to say anything meaningful here will
  take real calendar time — framed as an honest, slow-arriving evidence tier, not a shortcut. Module
  3's tracker is newer still and currently limited to one week ahead, since the forecast itself is.

**What to say, if it shows 0 resolved (likely, unless a lot of real time has passed since the last
refresh):** "This is expected, not broken — a logged prediction only resolves once its target
week's real outcome exists in the data. The page says so explicitly." Do not apologize for an
empty table here; the page's own copy already explains it.

**Questions this page is built to pre-empt:** "how do you know your live predictions are actually
any good" (this is the honest answer: not yet fully known, and here's the exact mechanism built to
find out over time, rather than an unfounded claim either way).

---

## Suggested Demo Path (rehearsable click-through)

1. **Sidebar**: pick a district with a good story (e.g. Colombo or Gampaha, given the real 2026
   outbreak) before navigating away from Overview.
2. **Overview** — read the three-column summary and the evidence-tier legend aloud once.
3. **Research Evidence** — walk the two module columns, then the M2-009 table, then the
   per-district MASE chart (point out the regressed-districts caption unprompted — it's stronger
   to show you're not hiding it than to wait for the question), then briefly open the Module 3
   "how Stage 2 evolved" expander.
4. **Operational Monitoring** — nowcast panel for your chosen district, then the "Recent risk" tab
   (point out an orange ✕ marker if one is visible), then the map ("This week" mode, then toggle to
   "Next week (forecast)" to show the integration with Module 1's forecast).
5. **Prospective Tracking** — a brief pass explaining the mechanism, even if it currently shows 0
   resolved.

## Things to Actively Avoid Saying While Demoing

- Don't quote a specific threshold, MASE, or PR-AUC value from memory — read it off the current
  page. The values here can change on retune (Decision 047 already changed the alert threshold and
  Stage 2 architecture once).
- Don't call anything on the Operational Monitoring or Prospective Tracking pages "proof" or
  "validation" — both pages say so themselves; echo that framing rather than contradicting it.
- Don't promise a map style that isn't currently in the app (see the note in Page 3 above).
- Don't claim the "Refresh operational data" button retrains models — `DASHBOARD_GUIDE.md`'s
  Known Limitations section is explicit that it only reruns scoring on frozen model weights.
