---
name: multi-agent-delivery
description: Coordinate multi-agent software delivery across planning, clarification, UX review, task breakdown, and implementation. Use when Codex needs to route a feature or bug through planner, product_designer, tasker, and implementer agents in the correct order with explicit handoffs, required artifacts, and stop conditions.
---

# Multi Agent Delivery

Use this skill to route work through the right agents in the right order. It does not replace the role agents; it enforces clean handoffs between them.

## Default Order

1. `planner` owns understanding, research, clarifying questions, and the first plan.
2. `product_designer` owns UX/UI review and the design spec when a screen, flow, or user-facing behavior changes materially.
3. `tasker` owns plan audit and task breakdown after plan and design inputs are stable enough.
4. `nextjs_mui` and `dotnet` implement only after tasks are concrete.
5. `product_designer` or `tasker` can perform a final review when the change needs it.

## Routing Rules

- Treat clarification as part of `planner`, not a separate agent stage.
- Send UI work to `product_designer` before `tasker` unless the UI change is purely mechanical.
- Do not send implementers vague work. Require a usable artifact first.
- Allow backend-only changes to skip `product_designer`.
- Allow tiny, low-risk fixes to skip `tasker` only when the scope is obvious and no coordination is needed.

## Required Artifacts

- Plan: `/docs-ai/PLAN-<slug>-YYYY-MM-DD.md`
- Design spec when needed: `/docs-ai/DESIGN-<slug>-YYYY-MM-DD.md`
- Task list when needed: `/docs-ai/TASKS-<slug>-YYYY-MM-DD.md`

## Stop Conditions

Stop and escalate when:

- docs and code conflict
- product requirements are ambiguous
- design-system rules and requested UI conflict
- task breakdown reveals missing architecture or design decisions

Read [references/handoff-order.md](./references/handoff-order.md) for the routing rules. Read [references/output-contracts.md](./references/output-contracts.md) for the minimum artifact quality bar before handing work to the next agent.
