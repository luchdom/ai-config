---
name: goal-to-delivery
description: Deliver one user-selected local goal or explicitly selected issue through the shared specialist pipeline to a declared completion boundary. Use only when the user explicitly invokes `$goal-to-delivery` for semi-autonomous delivery; never select queue work or accept self-declared autonomous authority.
---

# Goal to Delivery

Deliver one bounded goal automatically. This is the semi-autonomous entry policy, not a separate agent stack.

## Invocation

Require an explicit invocation:

```text
$goal-to-delivery <goal-or-selected-issue> [--completion artifact|working-tree|commit|pr|merge]
```

Default to `workSource: local` and `completionBoundary: working-tree`. Use `artifact` for accepted non-code output. Accept an issue only when the user selected it explicitly; never search a queue or select a second item.

Reject `mode: autonomous`, an `autonomous` label as a mode switch, or any caller-supplied capability that did not come through `$linear-delivery-loop`. An explicit prepared autonomous iteration belongs to that entry instead.

## Canonical contract

Before delivery, read and follow:

- [delivery-stages.md](./references/delivery-stages.md)
- [artifact-contract.md](./references/artifact-contract.md)
- [clarification-policy.md](./references/clarification-policy.md)
- [quality-gates.md](./references/quality-gates.md)
- [completion-boundaries.md](./references/completion-boundaries.md)
- [work-descriptor.schema.json](./references/work-descriptor.schema.json)

These references are the sole canonical cross-tool delivery protocol. Repository guidance owns repository-specific commands, domain rules, definitions of done, and stricter safety constraints. Apply user/system requirements and stricter repository safety first, this entry policy second, then the shared contract. Fail closed on an unresolved conflict or attempted weakening.

## Policy

1. Initialize or exactly resume one schema-valid work descriptor with the bundled deterministic workflow helper. Never infer resume from chat history, similar goal text, a slug, or the latest folder.
2. Discover repository instructions and relevant patterns.
3. Advance through applicable Plan, Clarify, Design, Task, Audit, Implement, Review, QA, and Docs stages without routine approval.
4. Return to planning/tasking for safely repairable audit findings. Return to implementation for scoped review or QA defects within the active retry budget.
5. Record safe assumptions. Ask one focused question only when a material decision cannot be resolved safely from user requirements, repository evidence, or conservative precedent.
6. Stop exactly at the declared completion boundary and never infer additional Git, provider, or tracking authority.

Acquire the repository editing reservation before automatically changing repository deliverables. Planning evidence isolated to the workflow folder may defer that reservation. Preserve dirty or unmerged work and its reservation when a material clarification blocks progress.

## Authority boundary

The user's invocation authorizes scoped repository edits and local validation through `working-tree` unless a different boundary is explicit. It does not authorize queue selection, autonomous mode, unrelated work, or broader external mutation.

- `commit`, `pr`, and `merge` require the declared boundary or a later explicit grant.
- Linear is optional. A selected linked issue follows repository tracking policy; a local goal performs no Linear mutation.
- Specialists do not independently mutate Linear. Autonomous Git/provider mutation is never routed through this entry.
- Stop after one goal, including after completion or pause.

Report the achieved boundary, artifacts, validation evidence, assumptions, and any exact decision or authority still required.

Use the installed skill's deterministic CLI for local/semi work:

```text
python <installed-goal-to-delivery-skill>/scripts/cli.py init --repository-root <path> --repository-key <repository-key> --workflow semi-autonomous --goal <text> --completion-boundary <boundary> [--display-title <text>]
python <installed-goal-to-delivery-skill>/scripts/cli.py resume --repository-root <path> --repository-key <repository-key> (--workflow-id <uuid>|--artifact-path <absolute-path>|--external-id <canonical-id>)
python <installed-goal-to-delivery-skill>/scripts/cli.py attach --repository-root <path> --repository-key <repository-key> --workflow-id <uuid> --provider linear --external-id <canonical-id>
python <installed-goal-to-delivery-skill>/scripts/cli.py handoff --source-root <path> --destination-root <path> --repository-key <repository-key> --workflow-id <uuid> --expected-path <repo-relative-path> [--expected-path <repo-relative-path> ...]
```

Do not pass a work key to `init`; only the helper allocator or a later trusted provider adapter may supply one. `repository-key` is repository configuration, not the artifact work key, and is bound to the repository's state home. Use `attach` only after explicit tracking authority, and `handoff` only after explicit workflow-managed Handoff authorization.

For `handoff`, repeat `--expected-path` once for every intended Git-changed user path. The set must match the observed change scope exactly. Do not list the selected workflow's `workflow.json`; the helper includes that internal descriptor itself. See [artifact-contract.md](./references/artifact-contract.md) for the fail-closed scope, destination, evidence, and authority rules.
