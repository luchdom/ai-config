---
name: task-audit-breakdown
description: Audit implementation plans against requirements, docs, and design specs, then split the work into concrete execution tasks. Use when Codex needs to validate a plan, check for missing risks, tests, rollout steps, or design dependencies, and generate independent tasks for implementers.
---

# Task Audit Breakdown

Turn a plan into execution-ready tasks. Audit completeness first, then split the work so implementers can move with minimal coordination.

## Audit Workflow

1. Read the user requirement.
2. Read the plan in `/docs-ai`.
3. Read the design spec in `/docs-ai` when UI work exists.
4. Read the smallest relevant subset of `AGENTS.md` and `/docs`.
5. Check for missing risks, tests, rollout steps, dependencies, and unclear assumptions.
6. Write `/docs-ai/TASKS-<slug>-YYYY-MM-DD.md`.

## Task Rules

- Group tasks by area such as Backend, Frontend, and Shared or Infra.
- Give each task a concrete goal.
- Name likely files or modules when they can be inferred.
- Include acceptance criteria and test notes.
- Call out dependencies explicitly.
- Split work so separate implementers can pick it up without constant coordination.

## Audit Rules

- Do not rewrite the product or design direction unless it is missing or contradictory.
- Surface missing decisions before creating a misleading task list.
- Cite exact source paths.
- Distinguish confirmed requirements from inferred work.

Read [references/audit-checklist.md](./references/audit-checklist.md) when evaluating plan completeness. Read [references/task-template.md](./references/task-template.md) when writing the final task document.
