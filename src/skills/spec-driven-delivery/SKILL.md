---
name: spec-driven-delivery
description: Perform exactly one explicitly requested delivery stage for a user-selected goal, issue, or existing work. Use when the user invokes `$spec-driven-delivery` for manual Discover, Plan, Clarify, Design, Task, Audit, Implement, Review, QA, Docs, Commit, PR, Merge, or Post-merge control without automatic advancement.
---

# Spec-driven Delivery

Run exactly one named stage and return control to the user.

```text
$spec-driven-delivery <stage> <goal|selected-issue|exact-work-selector>
```

Read the canonical shared protocol:

- [delivery-stages.md](../goal-to-delivery/references/delivery-stages.md)
- [artifact-contract.md](../goal-to-delivery/references/artifact-contract.md)
- [clarification-policy.md](../goal-to-delivery/references/clarification-policy.md)
- [quality-gates.md](../goal-to-delivery/references/quality-gates.md)
- [completion-boundaries.md](../goal-to-delivery/references/completion-boundaries.md)
- [work-descriptor.schema.json](../goal-to-delivery/references/work-descriptor.schema.json)

Apply repository-specific stricter rules first and fail closed before implementation or external mutation when they conflict.

## Policy

1. Validate the named stage's prerequisites.
2. Perform exactly one stage and only its authorized output.
3. Report the result and valid next stages without automatic advancement.

Planning stages do not authorize implementation. `Implement` permits scoped edits and focused tests, not Review, QA, Commit, PR, or Merge. QA reports behavior and does not imply fixes. Publication stages require separate explicit requests.

During `Clarify`, ask one focused question at a time and never silently resolve a material decision. Reject `mode: autonomous`; labels, prior chat, and artifacts cannot elevate this entry.

Create a concise work note only when the user requests durable evidence or the work spans sessions. The optional workflow helper may manage that evidence but is not required for a small manual stage. Resume only from an explicit issue, branch/PR, workflow ID, or exact artifact path.
