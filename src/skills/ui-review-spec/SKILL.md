---
name: ui-review-spec
description: Analyze existing product screens and flows, identify UX/UI improvements, and produce implementer-ready design specs using current repo components first. Use when Codex needs to inspect a screen with Playwright MCP or Playwright CLI, review usability or accessibility, or map recommendations to existing repo components, MUI, or shadcn before implementation.
---

# UI Review Spec

Turn a UI review into an implementer-ready design spec. Inspect the current experience first, prefer existing components, and tie every recommendation to a user goal.

## Review Workflow

1. Read `AGENTS.md` and the smallest relevant subset of `/docs`.
2. Inspect the current screen with Playwright MCP when available.
3. Fall back to Playwright CLI when MCP is unavailable.
4. Fall back to screenshots or provided images only when interactive inspection is not possible, and state the limitation.
5. Find existing repo components and patterns before proposing changes.
6. Check MUI and shadcn capabilities before suggesting a new component.
7. Write a concrete design spec in `/docs-ai/DESIGN-<slug>-YYYY-MM-DD.md`.

## Recommendation Rules

- Prefer existing repo components first.
- Prefer MUI or shadcn primitives next.
- Propose a new component only when the repo and approved libraries cannot support the need cleanly.
- Optimize for task completion, clarity, hierarchy, accessibility, and responsiveness before novelty.
- Cover default, hover, focus, active, disabled, loading, empty, error, success, and validation states when they matter.
- Cite the exact repo paths and tools consulted.

## Deliverable

Include these sections in the design spec:

- Context and user goal
- Current UX/UI issues found
- Recommended changes
- Component mapping
- Layout, spacing, sizing, and responsive behavior
- Color, typography, and hierarchy guidance
- Interaction and state behavior
- Accessibility notes
- Acceptance criteria
- Sources consulted (paths/tools)

Read [references/ui-audit-checklist.md](./references/ui-audit-checklist.md) when reviewing a screen. Read [references/component-selection.md](./references/component-selection.md) when deciding whether to reuse, compose, or introduce a component. Read [references/spec-template.md](./references/spec-template.md) when writing the final spec.
