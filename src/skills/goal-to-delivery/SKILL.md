---
name: goal-to-delivery
description: Deliver one user-selected local goal or explicitly selected issue semi-autonomously to a declared completion boundary. Use only when the user explicitly invokes `$goal-to-delivery`; continue routine stages automatically, ask for material decisions, and never perform queue selection or self-declare autonomous mode.
---

# Goal to Delivery

Deliver one bounded goal using the lightest applicable workflow.

## Invocation

```text
$goal-to-delivery <goal-or-selected-issue> [--completion artifact|working-tree|commit|pr|merge]
```

Default to a local goal and the `working-tree` boundary. Accept a Linear issue only when the user selected it explicitly. Never perform queue selection, start a second goal, or accept `mode: autonomous`; backlog polling belongs to `$linear-delivery-loop`.

Read the canonical shared protocol:

- [delivery-stages.md](./references/delivery-stages.md)
- [design-gates.md](./references/design-gates.md)
- [artifact-contract.md](./references/artifact-contract.md)
- [clarification-policy.md](./references/clarification-policy.md)
- [quality-gates.md](./references/quality-gates.md)
- [completion-boundaries.md](./references/completion-boundaries.md)
- [worktree-policy.md](./references/worktree-policy.md)
- [work-descriptor.schema.json](./references/work-descriptor.schema.json)

Repository-specific commands and stricter safety rules take precedence; unresolved conflicts fail closed before implementation or external mutation.

## Policy

1. Discover the repository and define a bounded outcome and acceptance criteria.
2. Plan and task inline for routine work. Use a formal plan, task breakdown, or independent audit when risk or complexity justifies it. For frontend/UI work, apply `design-gates.md`; initialize or resume the registered `artifactFolder` before design or implementation, and never let risk waive a required design spec or post-build conformance review.
3. Advance automatically through applicable implementation, UI design conformance, one code review, runtime QA, and documentation checks.
4. Repair scoped findings within a small retry budget. Ask one focused question when a material decision cannot be safely derived.
5. Stop exactly at the declared completion boundary.

The invocation authorizes scoped repository edits and local validation through `working-tree`. `commit`, `pr`, and `merge` require the declared boundary or a later explicit grant. A selected Linear issue may be updated only when repository tracking policy allows it; a local goal performs no Linear mutation.

Use the workflow helper when durable multi-session evidence is valuable or an applicable stage requires a persisted specialist artifact. It is optional for a small goal only when no such artifact is required; frontend/UI design gates require it. Resume explicit work by issue, branch/PR, workflow ID, or exact artifact path; never guess from the newest folder or similar goal text.

Report the achieved boundary, changed scope, validation, assumptions, and any remaining decision.
