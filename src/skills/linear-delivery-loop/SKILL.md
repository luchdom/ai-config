---
name: linear-delivery-loop
description: Run one lightweight autonomous delivery iteration from a repository's Linear backlog. Use only when explicitly invoked as `$linear-delivery-loop` by a Codex scheduled task or attended pilot; select or resume at most one labeled issue, work within local budgets, request decisions in Linear, and stop after merge or checkpoint.
---

# Linear Delivery Loop

Complete at most one Linear issue using Linear as the durable queue and checkpoint store. Do not build or require a separate supervisor, lease database, memory service, telemetry pipeline, or CI system.

## Setup

Read `.ai/loop.json` from the target repository and [project-config.example.json](./references/project-config.example.json). Stop without mutation when the file is missing, invalid, or `enabled` is false. Read the canonical shared protocol:

- [delivery-stages.md](../goal-to-delivery/references/delivery-stages.md)
- [artifact-contract.md](../goal-to-delivery/references/artifact-contract.md)
- [clarification-policy.md](../goal-to-delivery/references/clarification-policy.md)
- [quality-gates.md](../goal-to-delivery/references/quality-gates.md)
- [completion-boundaries.md](../goal-to-delivery/references/completion-boundaries.md)
- [work-descriptor.schema.json](../goal-to-delivery/references/work-descriptor.schema.json)

Repository-specific commands and stricter safety rules take precedence. Never expose API keys or notification topics.

The normal state mapping is Backlog for eligible intake, In Progress for the single active issue, and Done only after the configured completion boundary.

## Select or resume one issue

Query the configured Linear team/project and re-read the result immediately before claiming:

1. If more than one issue is in the active state, comment on none and stop with a human-attention result.
2. If one active issue lacks the configured autonomous label, assume attended work is in progress and stop.
3. If one active autonomous issue has the configured human-decision label, resume only after a newer owner comment exactly matching `DECIDE <ISSUE> <OPTION>` answers the latest open question. Acknowledge the decision, remove the label, and continue. Otherwise stop.
4. If one eligible active autonomous issue exists, resume it.
5. Otherwise select the highest-priority backlog issue with the autonomous label and without the human-decision label. Break ties by oldest creation time. Select no work when none is eligible.

Before claiming new work, confirm the issue states one achievable, bounded, locally testable goal with acceptance criteria. External-only setup, unclear product behavior, and oversized work are not eligible. Move one eligible issue to the active state, assign it to the configured owner when present, and add a short claim comment. Re-query active work; if the one-issue invariant no longer holds, stop.

## Deliver within the MVP budget

Use the lightest applicable stages. Plan and task inline for routine work; create a concise work note only when useful. Use specialists selectively based on risk, not as a mandatory chain.

- Prefer one branch and pull request per issue.
- Run focused checks first and one repository-owned local validation command before merge.
- Perform one independent code review and applicable runtime QA. Use HTTP, CLI, or browser behavior only when acceptance criteria require it.
- Update durable documentation only when behavior, setup, architecture, or operations changed.
- Keep total validation within `maxTestMinutes`, the run within `maxRunMinutes`, and the normal change within `maxFiles` and `maxChangedLines`.
- When a limit would be exceeded, split a genuinely independent prerequisite into a child issue or request a human decision. Do not silently expand scope.

For safe interruptions or the run-time limit, commit and push coherent work when safe, add a concise Linear checkpoint with branch/PR, completed checks, and next action, leave the issue active, and stop. After bounded repair attempts, treat a technical blocker as a human decision instead of looping indefinitely.

## Ask for a decision

Keep the issue active, add the configured human-decision label, and comment with:

- the blocked decision;
- two or three concrete options and consequences;
- one recommendation;
- the exact reply syntax `DECIDE <ISSUE> <OPTION>`.

Send at most one best-effort ntfy notification when enabled. The Linear comment is authoritative; notification failure must not create retries or duplicate comments. Stop after requesting the decision.

## Complete

For code, target the `merge` boundary: validate locally, open the PR, complete one review and applicable QA, squash merge when authorized by this entry and repository policy, verify the provider reports the PR merged into the configured default branch, then move the issue to Done with a short result comment. Do not rerun the full suite in a clean post-merge worktree.

For a non-code artifact, use the `artifact` boundary and close the issue only after its acceptance checks pass. Never select a second issue in the same invocation.
