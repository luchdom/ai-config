---
name: task-audit-breakdown
description: Audit implementation plans against requirements, docs, and design specs, then split the work into concrete execution tasks. Use when Codex needs to validate a plan, check for missing risks, tests, rollout steps, or design dependencies, and generate independent tasks for implementers.
---

# Task Audit Breakdown

Turn a plan into execution-ready tasks. Audit completeness first, then split the work so implementers can move with minimal coordination.

## Audit Workflow

1. Read the user requirement.
2. Read the plan in the current `/docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/` workflow artifact folder.
3. Read the design spec in the same workflow artifact folder when UI work exists.
4. Read the smallest relevant subset of `AGENTS.md` and `/docs`.
5. Check for missing risks, tests, rollout steps, dependencies, unclear assumptions, and the selected test strategy for the affected boundaries.
6. Write `/docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/<YYYY-MM-DD>-<slug>-tasks.md`.

## Artifact Folder Rules

- Reuse the same workflow artifact folder for related plan, clarification, design, task, audit, and AI workflow notes.
- Choose `<NNN>` by scanning folders under `/docs-ai/` and `/docs-ai/history/`, then using the next highest three-digit number when no workflow folder exists yet.
- If multiple active folders could match the current work, ask which one to use instead of creating a duplicate.
- New workflow artifacts must use the folder format. Older flat `/docs-ai/*` artifacts may be read as legacy fallback only.

## Task Rules

- Group tasks by area such as Backend, Frontend, and Shared or Infra.
- Give each task a concrete goal.
- Name likely files or modules when they can be inferred.
- Include acceptance criteria and test notes.
- Preserve the selected test strategy instead of silently re-deciding it.
- Call out dependencies explicitly.
- Split work so separate implementers can pick it up without constant coordination.

## Audit Rules

- Do not rewrite the product or design direction unless it is missing or contradictory.
- Surface missing decisions before creating a misleading task list.
- Cite exact source paths.
- Distinguish confirmed requirements from inferred work.

Read [references/audit-checklist.md](./references/audit-checklist.md) when evaluating plan completeness. Read [references/task-template.md](./references/task-template.md) when writing the final task document.
