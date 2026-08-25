---
name: linear-delivery-loop
description: Run one lightweight autonomous delivery iteration from a repository's Linear backlog. Use only when explicitly invoked as `$linear-delivery-loop` by a Codex scheduled task or attended pilot; select or resume at most one labeled issue, work within local budgets, request decisions in Linear, and stop after merge or checkpoint.
---

# Linear Delivery Loop

Complete at most one Linear issue using Linear as the durable queue and checkpoint store. Do not build or require a separate supervisor, lease database, memory service, telemetry pipeline, or CI system.

## Setup

Read `.ai/loop.json` from the target repository and [project-config.example.json](./references/project-config.example.json). Stop without mutation when the file is missing, invalid, or `enabled` is false. Read the canonical shared protocol:

- [delivery-stages.md](../goal-to-delivery/references/delivery-stages.md)
- [design-gates.md](../goal-to-delivery/references/design-gates.md)
- [artifact-contract.md](../goal-to-delivery/references/artifact-contract.md)
- [clarification-policy.md](../goal-to-delivery/references/clarification-policy.md)
- [quality-gates.md](../goal-to-delivery/references/quality-gates.md)
- [completion-boundaries.md](../goal-to-delivery/references/completion-boundaries.md)
- [worktree-policy.md](../goal-to-delivery/references/worktree-policy.md)
- [work-descriptor.schema.json](../goal-to-delivery/references/work-descriptor.schema.json)

Repository-specific commands and stricter safety rules take precedence. Never expose API keys or notification topics.

The normal state mapping is Backlog for eligible intake, In Progress for the single active issue, and Done only after the configured completion boundary.

## Acquire the run lease

After validating that `.ai/loop.json` exists and is enabled, acquire the deterministic cross-run lease before reading or mutating Linear, Git, notifications, or repository work. Run `python <this-skill-directory>/scripts/loop_lock.py acquire --repo-root <repository-root>` and retain the returned token only for release.

- Exit `0` with `status: acquired`: continue this invocation.
- Exit `3` with `status: busy`: another invocation owns this Linear queue; stop immediately without comments, notifications, or repository mutation.
- Any other result: fail closed and report the local lock error without attempting delivery.

The helper scopes the lock by repository key plus Linear team/project, so worktrees and separate local checkouts of the same queue contend. Its lease is `maxRunMinutes + 15` minutes. An expired valid lease is recovered atomically; malformed state is never overwritten.

On Windows, the default lease root is `%LOCALAPPDATA%\Luchdom\ai-toolkit`. Set `LUCHDOM_AI_STATE_HOME` to an absolute user-state path only when an installation requires an explicit override; never point it at this repository or its `docs` directory.

Before every return after acquisition—including completion, checkpoint, decision request, validation failure, or unexpected error—run `python <this-skill-directory>/scripts/loop_lock.py release --repo-root <repository-root> --token <token>`. Never store the token in Linear, Git, docs, or notifications. If the process is killed before release, a later invocation recovers the lease after expiry.

## Select or resume one issue

Query the configured Linear team/project and re-read the result immediately before claiming:

1. If more than one issue is in the active state, comment on none and stop with a human-attention result.
2. If one active issue lacks the configured autonomous label, assume attended work is in progress and stop.
3. If one active autonomous issue has the configured human-decision label, inspect only newer owner comments that match `DECIDE <ISSUE> <OPTION>` or `DECIDE <ISSUE> CUSTOM <SUGGESTION>`. For a listed option, acknowledge the decision, remove the label, and continue. For `CUSTOM`, use the remaining non-empty text as the owner's proposed direction; continue only when it resolves the latest question safely, otherwise keep the label, post one focused follow-up, and stop. Ignore ordinary comments as authorization.
4. If one eligible active autonomous issue exists, resume it.
5. Otherwise select the highest-priority backlog issue with the autonomous label and without the human-decision label. Break ties by oldest creation time. Select no work when none is eligible.

Before claiming new work, confirm the issue states one achievable, bounded, locally testable goal with acceptance criteria. External-only setup, unclear product behavior, and oversized work are not eligible. Move one eligible issue to the active state, assign it to the configured owner when present, and add a short claim comment. Re-query active work; if the one-issue invariant no longer holds, stop.

## Archive quiet standalone runs

A quiet run is a standalone scheduled invocation that finds an expected no-work condition, produces no new actionable result, and makes no Linear, Git/GitHub, repository, pull-request, or notification mutation. Transient lease acquisition and release do not make a run non-quiet. Expected quiet outcomes are: the loop is disabled; the lease is busy; attended work is active; no eligible backlog issue exists; or an active `needs-human` issue has no newer valid owner decision and needs no new follow-up.

After releasing any acquired lease, archive only the current quiet standalone scheduled run when the host exposes a native current-task archival capability. In Codex, call `set_thread_archived`; never emit a raw archive directive, automate the app UI, archive another task, or invent a filesystem workaround. If native archiving is unavailable, return one concise no-op result normally.

Never archive an attended pilot, a scheduled task attached to an existing long-lived chat, or a run that claimed or resumed delivery work. Keep the run visible when it created or changed anything, requested or refined a decision, sent a notification, checkpointed work, encountered an error or invalid configuration, found multiple active issues, or discovered another condition that needs attention.

## Deliver within the MVP budget

Use the lightest applicable stages. Plan and task inline for routine work; create a concise work note only when useful. Use specialists selectively based on risk, not as a mandatory chain.

- Prefer one branch and pull request per issue.
- For frontend/UI work, require product-designer input when `design-gates.md` requires a pre-build specification, and require a current rendered design conformance `PASS` after implementation. Risk-based specialist selection cannot waive either applicable gate.
- Run focused checks first and one repository-owned local validation command before merge.
- Perform applicable UI design conformance, one independent code review, and applicable runtime QA. Use HTTP, CLI, or browser behavior only when acceptance criteria require it.
- Update durable documentation only when behavior, setup, architecture, or operations changed.
- Keep total validation within `maxTestMinutes`, the run within `maxRunMinutes`, and the normal change within `maxFiles` and `maxChangedLines`. Treat the file and changed-line budgets as planning thresholds, not targets or reasons to abandon a coherent edit midway.
- When a limit is reached and the remaining scope is still too large for one more normal run, create at most one linked Linear continuation issue for a coherent, independently testable remainder. Preserve the original outcome across the parent and continuation acceptance criteria, state what is complete and what remains, retain the same project and priority, and add the autonomous label only when the continuation is bounded and locally testable. Leave it in Backlog and never select it during the current invocation.
- Complete the current issue before the continuation only when its retained acceptance criteria are satisfied at a reviewable boundary. If the work cannot be split without incomplete behavior, silently dropping an acceptance criterion, or making a product decision, do not create or close around a continuation; checkpoint the same issue or request a human decision instead.

For safe interruptions or the run-time limit, commit and push coherent work when safe, add a concise Linear checkpoint with branch/PR, completed checks, and next action, leave the issue active, and stop. After bounded repair attempts, treat a technical blocker as a human decision instead of looping indefinitely.

## Ask for a decision

Keep the issue active, add the configured human-decision label, and comment with:

- the blocked decision;
- two or three concrete options and consequences;
- one recommendation;
- the listed-choice reply syntax `DECIDE <ISSUE> <OPTION>`;
- the owner-suggestion reply syntax `DECIDE <ISSUE> CUSTOM <SUGGESTION>`.

Send at most one best-effort ntfy notification when enabled. Use the Linear issue URL as the notification click target so opening the notification opens the decision, and include the URL in the message as a fallback when the transport cannot expose a click action. The Linear comment is authoritative; notification failure must not create retries or duplicate comments. Stop after requesting the decision.

## Complete

For code, target the `merge` boundary: validate locally, open the PR, complete applicable UI design conformance, one code review, and applicable QA, squash merge when authorized by this entry and repository policy, verify the provider reports the PR merged into the configured default branch, then move the issue to Done with a short result comment. Do not rerun the full suite in a clean post-merge worktree.

For a non-code artifact, use the `artifact` boundary and close the issue only after its acceptance checks pass. Never select a second issue in the same invocation.
