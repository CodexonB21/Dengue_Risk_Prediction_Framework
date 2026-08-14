---
name: evaluator-qa-bank-prompt
description: Ready-to-paste prompt for a new chat session to build a mechanism-level, cross-module "evaluator-style" Q&A bank across all three project modules
metadata:
  type: report_support
---

# Prompt to paste into a new chat

Copy everything in the fenced block below into a fresh conversation, run in the same
project working directory (`Dengue_Risk_Prediction_Framework`), so the project's
`CLAUDE.md` rules and file layout are already loaded.

```
I need you to act as my thesis defense coach and build a Q&A prep bank in a very
specific style — one calibrated to a real pattern I've noticed in how my evaluator
actually questions this project, not generic "tell me about your project" prep.

## The pattern (calibration examples — study these before writing anything)

My evaluator does not ask "does it work" or "what did you build." They ask questions
that probe the exact mechanism, challenge whether a result is actually meaningful, look
for contradictions between two things I've claimed, and check whether differences
across the three modules are deliberate decisions or just incidental side-effects of
which model happened to win a benchmark. Concrete examples of the actual question
style, from a prior working session on this same project:

- "What is the technique used to get feature importance in each module?" — not "there's
  feature importance," but which exact statistic, computed how, on which specific model
  object, verified in the code — and then: is it the same technique across all three
  modules, and if not, is that a decision or a coincidence?
- "But 14-24% sMAPE doesn't mean good, right?" — refusing to accept a positive-sounding
  number without a comparison point; forcing the actual scoped truth (this number
  excluded exactly the weeks that mattered most, and those weeks were ~97% error for a
  specific, documented reason).
- "Does this mean the image is wrong? It has 2 not-improved districts!" — catching an
  apparent contradiction between two numbers (25/25 validation vs. 23/25 holdout) that
  were both true but under-explained, and forcing a precise, honest reconciliation
  instead of picking one number to hide.
- "This pooled model is regarding XGBoost right, not SARIMA?" — catching an ambiguous
  reference that could be misread as applying to the wrong component of a two-stage
  system.
- "I can't just tell I found that method from an AI, I need proof from somewhere like
  in a past research" — refusing an internal decision record as sufficient justification
  for a methodology choice; demanding an actual external, citable academic precedent.
- "Why does SARIMA give a flat line?" — a "why does this behave this way, mechanically"
  question about an artifact visible on a chart, not answerable by restating the
  headline result.
- Asking me to correctly categorize `is_reporting_anomaly` as shared vs. module-specific
  and add it to the right list, rather than accepting a vague "it's shared" answer, once
  it turned out to actually be a third, undocumented category (used by two modules via a
  helper file, not the true shared layer, and not used by the third module at all).

The common thread: **mechanism over label, evidence over restatement, and an honest
"that's incidental, not deliberate" when that's actually the truth** rather than
manufacturing a justification that doesn't exist.

## What I need you to build

A Q&A bank in exactly this style, covering all three modules — Module 1 (Hybrid
Time-Series Case Forecasting), Module 2 (Hybrid Outbreak Risk Classification), Module 3
(Hybrid Spatial Hotspot Detection) — organized around four recurring question shapes:

1. **Mechanism-level**: "what exact technique/statistic/function computes X, and how
   does it actually work" (not just naming the tool).
2. **Is-that-actually-good**: numbers or claims that sound positive on their face but
   need a comparison point, a scope caveat, or a significance check to actually mean
   what they seem to mean.
3. **Contradiction-check**: two true things stated elsewhere in the project's docs,
   scripts, or figures that could be read as conflicting unless the scope difference
   between them is made explicit.
4. **Deliberate-vs-incidental**: places where two or three modules do the same thing, or
   different things, and the honest answer requires knowing whether that was an actual
   decision (cite the Decision #) or just how the benchmark happened to land.

## Step 0 — mandatory reading before writing anything

Per this project's CLAUDE.md, read the current source of truth before drafting anything.
At minimum:

- `research_context/PROJECT_CONTEXT.md`, `CURRENT_ARCHITECTURE.md`,
  `RESEARCH_DECISIONS.md`, `FEATURE_ENGINEERING_SPEC.md`
- `module_1_forecasting/MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md`
- `module_2_classification/MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md`
- `module_3_spatial/MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md`
- `research_context/QUESTIONS_FOR_DEFENSE.md` — this already exists. Read it fully
  first and identify what it already covers in this style versus what's missing, so you
  extend it rather than duplicate it.
- The actual source code, not just the docs, for anything mechanism-level — e.g. don't
  describe a feature-importance method from a doc's prose summary if you can instead
  grep the real function call in `src/` and quote it directly. Prior work on this
  project found real cases where the docs' own prose didn't match what the code actually
  did, or left a mechanism completely undocumented despite the code doing something
  specific and checkable — treat every mechanism-level claim as something to verify
  against code, not just against MODULE_CONTEXT.md's narrative.

Do not invent or round any number, mechanism, or citation beyond what these files (or
the code itself) state. If something needed for a strong question-and-answer isn't
documented or verifiable, say so and mark it as a placeholder — never fabricate a
decision, a statistic's exact name, or an academic citation to make an answer sound more
complete than it is.

## Step 1 — audit existing coverage first

Before writing anything new, go through `QUESTIONS_FOR_DEFENSE.md` and classify its
existing entries against the four question shapes above. Report back: which shapes are
already well covered, which modules are thin, and which of the four shapes barely exist
yet (my guess, to check: Module 1 has the most existing depth; Modules 2 and 3 have real
gaps; "is-that-actually-good" and "deliberate-vs-incidental" are probably the two
thinnest shapes across all three modules, since those require actively challenging a
claim rather than just explaining a decision that was already flagged as needing
defense).

## Step 2 — propose an outline first, not full answers

Do NOT write full Q&A entries in one shot. First produce **only an outline**: a list of
proposed questions, grouped by module and by shape, where each entry states:
- the question, phrased in the same direct, slightly adversarial register as the
  calibration examples above (not softened into a generic FAQ tone),
- which shape it is (mechanism / is-it-good / contradiction-check /
  deliberate-vs-incidental),
- which specific file(s), function(s), or decision number(s) you expect the answer to
  come from (so I can sanity-check you're not about to guess), and
- a one-line note if you already suspect the honest answer is "this is incidental, not
  deliberate" or "this isn't actually verifiable from what's documented."

Aim for roughly 8-12 questions per module in this first pass — prioritize the sharpest,
highest-value questions over exhaustive coverage. Show me that outline and stop. I will
approve it, cut entries, or ask for specific additions before you write any full answers.

## Step 3 — write approved answers, verified, not assumed

Only after I approve the outline, write full entries for the approved questions, one
module (or a small cluster of questions) at a time so I can react before you continue.
For each entry:

- State the precise mechanism/answer, citing the exact file/function/line or Decision
  number/EXPERIMENT_LOG entry it comes from — the same evidentiary standard used in the
  calibration examples (e.g. "`get_score(importance_type='gain')` in
  `compensation_model.py:827`," not "XGBoost has a feature importance method").
- Where the honest answer is that something is incidental rather than deliberate, or
  that a cross-module inconsistency exists, say so plainly — that is itself a valid and
  valuable defense answer, not a gap to paper over.
- If you discover a genuine inconsistency between two docs, or between a doc and the
  code, while researching an answer (this project has precedent for this — e.g. a
  significance-count mismatch between two poster scripts, and an undocumented
  cross-module helper function), flag it explicitly as a finding, separate from the Q&A
  entry itself, per this project's CLAUDE.md conflict-handling rules. Do not silently
  fix it or silently ignore it.
- Keep the answer register terse and precise, matching the tone of the calibration
  examples — this is defense ammunition to internalize, not report prose. No filler
  sentences, no restating the question back before answering it.

## Step 4 — where this lives

Once a first batch of entries is approved, ask me whether to merge them directly into
`research_context/QUESTIONS_FOR_DEFENSE.md` (extending the existing canonical file) or
keep them as a separate companion file cross-referenced from it — don't assume either
way. Whichever we land on, update `research_context/CHANGELOG.md` per the living-
documentation rule once the bank is saved.

Start with Step 0 (read the files) and Step 1 (audit existing coverage), then give me
the Step 1 report plus the Step 2 outline for approval — in that order, in one message.
```
