---
name: module1-storytelling-prompt
description: Ready-to-paste prompt for a new chat session to build a first-person narrative storytelling poster script for Module 1
metadata:
  type: report_support
---

# Prompt to paste into a new chat

Copy everything in the fenced block below into a fresh conversation, run in the same
project working directory (`Dengue_Risk_Prediction_Framework`), so the project's
`CLAUDE.md` rules and file layout are already loaded.

```
I need you to act as my thesis presentation coach and scriptwriter. We are building a
first-person, narrative "storytelling" script for presenting the Module 1 poster
(Hybrid Time-Series Case Forecasting — SARIMA baseline + XGBoost residual compensation)
to a final-year-project evaluator. Team name: Codexon.

This is NOT the same thing as a dry technical walkthrough. I already have one of those
saved at `research_context/poster/MODULE1_POSTER_NARRATION.md` (a why/how, point-and-
explain script). Read it for verified facts and phrasing you can reuse, but do not copy
its structure or voice. What I need now is different: a flowing, first-person-plural
("we") narrative that tells the story of how this module came to be — the problem we
set out to solve, the decisions we made and why, the experiments we ran (including the
ones that failed), how the result improved over time, the challenges we hit and how we
worked through them, and where we landed — so that an evaluator stays emotionally
engaged, not just informed. Think "research journey," not "technical spec read aloud."

## Step 0 — mandatory reading before writing anything

Per this project's CLAUDE.md, read the current source of truth before drafting. At minimum:

- `research_context/PROJECT_CONTEXT.md`, `CURRENT_ARCHITECTURE.md`, `RESEARCH_DECISIONS.md`
- `module_1_forecasting/MODULE_CONTEXT.md` — especially the section "Investigation
  Summary: Module 1 Remediation Arc (M1-007–M1-021, 2026-08-04 to 2026-08-06)" near the
  end of the file — this is the richest "challenges faced and overcome" material in the
  whole module and should be the emotional spine of the middle of the story.
- `module_1_forecasting/EXPERIMENT_LOG.md` for the detailed narrative behind each
  experiment ID you plan to mention (M1-001 through M1-021).
- `research_context/QUESTIONS_FOR_DEFENSE.md` for pre-built defensible answers to hard
  questions — weave the strongest of these into the story rather than treating them as
  a separate Q&A appendix.
- `research_context/poster/MODULE1_POSTER_NARRATION.md` for already-verified numbers,
  chart-reading instructions, and the exact poster panel layout.

Do not invent or round any number beyond what these files state. If something needed
for a strong story beat isn't documented (e.g., a subjective feeling like "this is when
we got worried"), say so and either ask me or mark it as a placeholder — never fabricate
a decision, date, or metric to make the story flow better.

## Step 1 — what the physical poster actually shows (so every story beat can point at something real)

The poster has two panels, already finalized. Panel 1 (main): title bar, an Input
bullet list, a Methodology block (Data Preprocessing / Stage 1 SARIMA / Stage 2 XGBoost
/ Model Evaluation / Output), a system-flow diagram (Weekly Dengue Cases → Data
Preprocessing → SARIMA → Base Prediction → Residuals; Climate + Engineered Features →
Feature Engineering → XGBoost → Residual Correction; both → Combine Outputs → Final
Forecast Output), and a purple-bordered per-district holdout MASE dot plot (grey =
Stage 1 only, orange = Stage 1+2 improved, red diamond = the two districts that didn't
improve, reference line at MASE=1 for seasonal-naive). Panel 2 ("Key Outcomes"):
a headline paragraph, three bolded headline metrics (holdout MASE improvement 32.7%,
validation MASE improvement 43.5%, districts improved on holdout 23/25), and a Colombo
actual-vs-Stage-1-vs-Stage-1+2 line chart with two annotated "flagged reporting-delay
catch-up spike" markers.

Also available as separate figure files if useful as secondary "proof" material to cut
to during the story (check they still exist before citing a filename):
`research_context/poster/diagrams/poster_figure_module1.png` (poster version of the
diagram), `research_context/report_drafts/diagrams/figure_5_3_module1_architecture.png`
(report's more detailed 4-column architecture figure), and the report's Figure
7.2/7.3 generator outputs for the holdout forecast and MASE comparison charts.

## Step 2 — the story spine I want you to build around

Use the Remediation Arc section as the turning point of the story, not a footnote.
Rough shape (adjust once you've read the source material — this is a sketch, not a
rigid template):

1. **The problem** — district-level dengue forecasting matters for early warning; why a
   naive/plain approach isn't good enough.
2. **The first idea** — why we chose a two-stage hybrid instead of one big model, and
   the deliberate choice to keep Stage 1 climate-free (Decision 001) so the residual
   has a clean meaning.
3. **Building Stage 1** — SARIMA per district, auto_arima order selection, the
   surprise finding that many districts show no seasonal component and why we didn't
   panic and force one in.
4. **Building Stage 2** — the residual-compensation idea explained simply, the feature
   engineering, the leakage discipline (out-of-sample residuals only), and the pooled-
   vs-per-district test as a real turning point (we tested our own assumption and it
   held, decisively).
5. **First validated result** — walk-forward + holdout numbers, what they meant, why we
   trusted them (14 folds, DM test).
6. **The critique that started a second act** — a supervisor/reviewer critique
   surfaced weak points (thin holdout significance, surviving residual autocorrelation,
   two underperforming districts) and instead of defending the first result, we went
   looking for real improvements.
7. **The investigation arc** — 15 experiments, most rejected on their own pre-
   registered evidence (warm-starting, refit cadence, robust aggregation, real-time
   reporting-dip detector, hyperparameter search that failed its holdout check,
   per-district Stage 2). Tell this as genuine scientific honesty, not as failure — the
   fact that almost everything plausible was actually tested, not assumed, is the
   point. Land on the one real win: vintage-ensembled SARIMA promoted to the production
   nowcast.
8. **The data-quality ceiling discovery** — the Wk14 and Wk24-25 Colombo/Gampaha
   reporting-delay finding, spotted directly on a holdout chart, and why a real-time
   fix was tested and rejected rather than force-adopted. This is your best "we hit a
   wall and made the harder, more honest choice" beat — use it.
9. **Where we honestly stand** — the headline numbers, the two exceptions
   (Kilinochchi/Mannar) shown openly, non-significant by DM test, and what's
   deliberately left as future work rather than pretending it's finished.
10. **Close** — what this module actually proves, in one sentence, tied back to the
    opening problem statement.

## Step 3 — process: outline first, then sections on request

Do NOT write the full flowing script in one shot. First produce **only an outline**:
a numbered list of story beats (using the spine above as a starting point, revised
after your reading), where each beat states:
- the story point in one line,
- which poster element / figure / table to point at or switch to as visual proof,
- which decision/experiment IDs it's grounded in (e.g., "Decision 001", "M1-020"),
  and
- a rough spoken-time estimate.

Show me that outline and stop. I will approve it or ask for changes. Only after I
approve the outline should you draft the actual narrative prose, and even then, do it
section by section (one beat, or a small cluster of beats, per turn) so I can react and
redirect before you write the next part — not the whole script at once.

## Step 4 — voice and constraints for the prose itself

- First-person plural, spoken register ("We started with...", "That's when we
  found...", "So we went back and tested..."), flowing paragraphs — not the
  labeled **How:**/**Why:** format of the existing narration script.
- Every number, date, and decision must trace to the source files — no rounding
  beyond what's documented, no invented emotions attributed to the team beyond what's
  reasonable framing of a documented decision (e.g., "we were surprised" is fine to say
  about a documented surprising result; "we were devastated" is not, unless I tell you
  to write it that way).
- Keep academic honesty: this is still a research defense, not a sales pitch. No
  claims like "our model is highly accurate" or "clinically ready" — this project's
  CLAUDE.md explicitly bans that framing. Confident, engaging storytelling and
  academic caution are not in conflict here; use them together.
- Include bracketed stage directions for what to point at / switch to at each beat,
  the same way the existing narration script does, so I can physically navigate the
  poster while speaking.
- Target total spoken length: ask me for the time budget if I haven't given one
  before you draft prose (a full poster defense slot and a 90-second lightning version
  are usually both needed — check what I want rather than assuming).
- Save the finished script to `research_context/poster/MODULE1_POSTER_STORYTELLING_SCRIPT.md`
  once I've approved it in full — do not overwrite `MODULE1_POSTER_NARRATION.md`.

Start with Step 0 (read the files), then give me the Step 2 outline for approval.
```
