---
name: luchdom-docs
description: Keep Luchdom repo docs aligned with code, workflow, setup, and AI harness changes. Use when a change touches architecture, delivery workflow, setup steps, tooling, planning artifacts, or operational assumptions.
---

# Luchdom Docs

Treat documentation maintenance as part of delivery, not as optional polish.

## When To Use

Use this skill when:

- code changes affect setup or runtime expectations
- workflow rules change in `AGENTS.md`
- harness behavior changes
- validation commands or CI behavior change
- Linear intake policy changes
- tool installation or MCP setup changes
- docs and code appear to disagree

## Workflow

1. Read `AGENTS.md` first.
2. Read the smallest relevant set of docs under `docs/`, plus `README.md`.
3. Inspect the changed files or the planned change.
4. Update the nearest docs in the same change.
5. Prefer updating the source-of-truth doc instead of adding duplicate explanations.
6. When multiple docs overlap, make them consistent and remove contradictions.
7. Run any available doc-drift checks before finishing.

## Common Targets

Typical docs to consider:

- `README.md`
- `AGENTS.md`
- `docs/HARNESS.md`
- `docs/WORKFLOW.md`
- `docs/DECISIONS.md`
- `docs/QUALITY.md`
- `docs/LOCAL-DEVELOPMENT.md`
- `docs/LINEAR.md`
- `docs/AI-TOOLING.md`
- module-specific docs when present

## Rules

- Do not leave workflow docs stale after changing the workflow.
- Do not leave setup docs stale after changing required tools or commands.
- Do not create new docs when an existing doc is the clearer source of truth.
- Prefer concise updates over sprawling duplicative prose.
- If a contradiction cannot be safely resolved, surface it explicitly.

## Deliverable

Leave behind:

- updated source-of-truth docs
- consistent cross-links when needed
- a brief note of what changed and which docs were touched

Read [references/doc-targets.md](./references/doc-targets.md) for the preferred doc ownership map.
