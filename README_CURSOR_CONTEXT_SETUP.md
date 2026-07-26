# Cursor Living Context Setup Guide

This pack contains Cursor rules and markdown files for maintaining a living research context for Team Codexon's FYP.

---

## 1. Place Files in Repo Root

Copy these folders/files into the root of your project repository:

```text
.cursor/
research_context/
module_1_forecasting/
module_2_classification/
module_3_spatial/
README_CURSOR_CONTEXT_SETUP.md
```

Expected structure:

```text
project-root/
├── .cursor/
│   └── rules/
│       └── codexon_fyp.mdc
├── research_context/
│   ├── PROJECT_CONTEXT.md
│   ├── CURRENT_ARCHITECTURE.md
│   ├── RESEARCH_DECISIONS.md
│   ├── DATA_DICTIONARY.md
│   ├── FEATURE_ENGINEERING_SPEC.md
│   ├── CHANGELOG.md
│   ├── EXPERIMENT_LOG.md
│   └── QUESTIONS_FOR_DEFENSE.md
├── module_1_forecasting/
│   ├── MODULE_CONTEXT.md
│   └── EXPERIMENT_LOG.md
├── module_2_classification/
│   ├── MODULE_CONTEXT.md
│   └── EXPERIMENT_LOG.md
└── module_3_spatial/
    ├── MODULE_CONTEXT.md
    └── EXPERIMENT_LOG.md
```

---

## 2. Open the Full Repo in Cursor

Open the full project root folder, not only `src/`, `notebooks/`, or a subfolder.

This allows Cursor to index:

- Code
- Data descriptions
- Research documents
- Module contexts
- Experiment logs
- Cursor rules

---

## 3. First Prompt to Use in Cursor

Use this once after placing the files:

```text
Read the Cursor rule file and all markdown files in research_context and module folders. Build a current understanding of the project. Then summarize:

1. Overall research goal
2. Current architecture
3. Module 1 status
4. Module 2 status
5. Module 3 status
6. Open questions
7. Which documents should be updated as we work

Do not modify files yet. Just summarize your understanding.
```

---

## 4. Prompt for Major Work

When doing a major task, use:

```text
Before starting, read the latest relevant context files. After completing the task, update any affected markdown documentation, including changelog and experiment logs if needed.
```

---

## 5. Prompt for Experiments

```text
Run/plan this experiment according to the current module context. After the result, update the relevant module EXPERIMENT_LOG.md and any changed feature or decision documents.
```

---

## 6. Team Workflow Recommendation

Each team member should mainly work inside their module folder:

- Forecasting member: `module_1_forecasting/`
- Classification member: `module_2_classification/`
- Spatial member: `module_3_spatial/`

But shared decisions should be recorded in:

- `research_context/CURRENT_ARCHITECTURE.md`
- `research_context/RESEARCH_DECISIONS.md`
- `research_context/CHANGELOG.md`

---

## 7. Important Note

Cursor is not being trained permanently like a model.

Instead, the repository becomes the project memory. Cursor reads and updates these files so future chats can use the latest version.
