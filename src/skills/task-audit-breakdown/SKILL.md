---
name: task-audit-breakdown
description: "Support two separate roles over a delivery specification: help tasker turn a plan into concrete tasks with a light completeness check, or give the independent auditor a rigorous checklist. Use without combining task authorship and audit sign-off in one pass."
---

# Task Audit Breakdown

Keep task decomposition and independent audit separate. The calling role determines which operation is allowed.

Read the user requirement, repository instructions, relevant docs, registered plan, and required design from `docs-ai/<work-key>-<slug>/`. Use the canonical artifact/stage/quality contracts under `../goal-to-delivery/references/`. Recognize an explicitly selected historical numbered-and-dated folder or flat artifact as read fallback only; never rewrite it.

## Tasker operation

1. Perform a light completeness check for obviously missing decisions, risks, tests, rollout/rollback, docs impact, dependencies, and design inputs.
2. Surface gaps under `Audit notes`; do not claim they passed independent review.
3. Write only the dated `*-tasks.md` in the registered workflow folder using [task-template.md](./references/task-template.md).
4. Make each task bounded, ordered, achievable, repository-specific, and independently actionable.

## Auditor operation

1. Independently reread original requirements and source docs.
2. Use [audit-checklist.md](./references/audit-checklist.md) against the complete plan/design/task package.
3. Write only the dated `*-audit.md`; do not repair artifacts or generate tasks.
4. Require a fresh audit artifact after corrections. Do not overwrite prior evidence.

Neither operation chooses the workflow entry, advances stages, implements code, performs code review/runtime QA, mutates tracking, or expands Git/provider authority.
