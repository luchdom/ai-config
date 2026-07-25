---
name: spec-driven-delivery
description: Perform exactly one explicitly requested delivery stage for a user-selected local goal, workflow, or issue. Use only when the user explicitly invokes `$spec-driven-delivery` with a named stage and wants manual Plan, Clarify, Design, Task, Audit, Implement, Review, QA, Docs, Commit, PR, Merge, Reserve, or Release control without automatic advancement.
---

# Spec-driven Delivery

Run one named stage and return control to the user. This is the manual entry policy over the shared specialist pipeline.

## Invocation

Require an explicit invocation:

```text
$spec-driven-delivery <stage> <goal|selected-issue|exact-workflow-selector>
```

Accept `Discover`, `Plan`, `Clarify`, `Design`, `Task`, `Audit`, `Implement`, `Review`, `QA`, `Docs`, `Commit`, `PR`, `Merge`, `Post-merge`, `Reserve`, or `Release`. Reject `mode: autonomous`; labels and conversation context cannot elevate this entry.

Read the canonical shared protocol:

- [delivery-stages.md](../goal-to-delivery/references/delivery-stages.md)
- [artifact-contract.md](../goal-to-delivery/references/artifact-contract.md)
- [clarification-policy.md](../goal-to-delivery/references/clarification-policy.md)
- [quality-gates.md](../goal-to-delivery/references/quality-gates.md)
- [completion-boundaries.md](../goal-to-delivery/references/completion-boundaries.md)
- [work-descriptor.schema.json](../goal-to-delivery/references/work-descriptor.schema.json)

Repository-specific stricter rules take precedence. Fail closed on unresolved conflict.

## Policy

1. Initialize new work only when the requested stage needs it. Otherwise resume by exact registered workflow ID, exact artifact path, or unique external ID.
2. Validate the named stage's prerequisites from the canonical stage contract.
3. Perform only that stage. Write or change only the output authorized for it.
4. Report the result and valid next stages without invoking them.

Never infer later authority:

- `Plan`, `Clarify`, `Design`, `Task`, and `Audit` do not authorize implementation.
- `Implement` authorizes scoped edits and local implementation tests only. It does not imply Review, QA, Docs, Commit, PR, or Merge.
- `QA` reports; it does not authorize fixes.
- `Commit`, `PR`, and `Merge` are separate explicit actions.
- Tracking changes occur only when the named stage and repository policy require them.

During `Clarify`, never silently resolve material ambiguity. Ask one focused question at a time. When none remains, ask the user to confirm that the current decisions may be locked; do not advance.

Planning-only work may write inside its uniquely allocated workflow folder without an editing reservation. `Implement` and any stage changing repository deliverables require the repository reservation or an explicit prior `Reserve`. Retain it until explicit `Release`, valid workflow-managed Handoff, or terminal reconciliation.

Use the current artifact convention and retain the canonical historical-layout read fallback. Never rewrite historical evidence to make it look current.

For new manual work, call:

```text
python <installed-goal-to-delivery-skill>/scripts/cli.py init --repository-root <path> --repository-key <repository-key> --workflow manual --goal <text> --completion-boundary <boundary> [--display-title <text>]
```

For existing work, use the CLI's `resume` command with exactly one registered workflow ID, absolute artifact path, or unique external ID. Never pass or invent a work key.
