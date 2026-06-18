---
name: multi-agent-delivery
description: Coordinate multi-agent software delivery across planning, clarification, UX review, task breakdown, and implementation. Use when Codex needs to route a feature or bug through planner, product-designer, tasker, and implementer agents in the correct order with explicit handoffs, required artifacts, and stop conditions.
---

# Multi-Agent Delivery

Use this skill to route work through the right agents in the right order. It does not replace the role agents; it enforces clean handoffs between them.

## Default Order

1. `planner` owns understanding, research, clarifying questions, and the first plan.
2. `product-designer` owns UX/UI review and the design spec when a screen, flow, or user-facing behavior changes materially.
3. `tasker` owns plan audit and task breakdown after plan and design inputs are stable enough.
4. `dotnet`, `nextjs-mui`, `react`, and `jekyll-site-builder` implement only after the artifacts are concrete enough.
5. `product-designer` or `tasker` can perform a final review when the change needs it.

## Routing Rules

- Treat clarification as part of `planner` or `feature-driver`, not a separate agent stage.
- Send UI work to `product-designer` before `tasker` unless the UI change is purely mechanical.
- Do not send implementers vague work. Require a usable artifact first.
- Route backend or service work through `planner`, `tasker`, and `dotnet` using repo-local docs and patterns.
- Route Jekyll and GitHub Pages site work through `$jekyll-github-pages` and `jekyll-site-builder`; include `product-designer` first when visual direction changes materially.
- Allow backend-only and service-only changes to skip `product-designer`.
- Allow tiny, low-risk fixes to skip `tasker` only when the scope is obvious and no coordination is needed.

## Required Artifacts

- Workflow folder: `/docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/`
- Plan: `/docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/<YYYY-MM-DD>-<slug>-plan.md`
- Design spec when needed: `/docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/<YYYY-MM-DD>-<slug>-design.md`
- Task list when needed: `/docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/<YYYY-MM-DD>-<slug>-tasks.md`
- Audit when needed: `/docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/<YYYY-MM-DD>-<slug>-audit.md`
- Choose `<NNN>` by scanning folders under `/docs-ai/` and `/docs-ai/history/`, then using the next highest three-digit number.
- Keep related plan, clarification, design, task, audit, and AI workflow notes in the same folder.
- New workflow artifacts must use this folder format. Older flat `/docs-ai/*` artifacts may be read as legacy fallback only.

## Stop Conditions

Stop and escalate when:

- docs and code conflict
- product requirements are ambiguous
- design-system rules and requested UI conflict
- task breakdown reveals missing architecture or design decisions
- a plan is missing the explicit selected test strategy

Read [references/handoff-order.md](./references/handoff-order.md) for the routing rules. Read [references/output-contracts.md](./references/output-contracts.md) for the minimum artifact quality bar before handing work to the next agent.
