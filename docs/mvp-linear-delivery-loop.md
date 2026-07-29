# MVP Linear Delivery Loop

This is a small, local-first loop for one developer completing a repository backlog. It has no CI dependency, supervisor service, lease database, or telemetry stack. A deterministic local lease file prevents overlapping scheduled invocations from working the same queue.

## Prerequisites

- Codex can open the target repository and use its local tools.
- Linear access is available through the installed connector/skill.
- GitHub CLI is authenticated when the repository uses pull requests.
- Required credentials are environment variables, never committed files.

## Linear contract

Use ordinary workflow states such as `Backlog`, `In Progress`, and `Done` plus labels with distinct responsibilities:

- `autonomous`: the issue may be selected by the scheduled loop.
- `needs-decision`: the backlog issue needs one owner choice before it can be refined or made autonomous.
- `needs-human`: the active issue is paused for an owner decision.

An eligible issue describes one bounded, achievable, locally testable goal with acceptance criteria. Keep external-only infrastructure work out of the autonomous queue until the locally runnable product foundation is complete.

`needs-decision` is optional backlog-curation metadata, not loop state and not a fourth delivery entry. Use it only when a specific owner choice blocks readiness. Ordinary issue cleanup—comparing a description with current code, splitting stale scope, or adding acceptance criteria—can happen collaboratively without a formal delivery workflow or another label. Record the material decision in Linear, remove `needs-decision` after it is resolved, and add `autonomous` only when the issue is actually eligible.

The one-issue rule is intentionally visible: at most one issue may be in `In Progress`. An active issue without `autonomous` belongs to the attended workflow, so the scheduled loop stops without claiming anything.

## Repository configuration

Copy the shape from [`project-config.example.json`](../src/skills/linear-delivery-loop/references/project-config.example.json) to `.ai/loop.json` in the target repository. Set the Linear team/project, default branch, and limits, then change `enabled` to `true` for an attended pilot. Keep it enabled for scheduled runs only after that pilot passes.

Recommended starting budgets are 90 minutes per invocation, 30 changed files, 5,000 changed lines, and 30 total test minutes. These are configurable planning thresholds and stop-and-split signals, not targets or reasons to abandon a coherent edit midway.

## Codex scheduled task

Create one scheduled task in a dedicated Codex chat/project context, initially every 15 minutes. Use the repository as its working directory and this prompt:

```text
$linear-delivery-loop
Run one MVP autonomous delivery iteration for this repository. Obey .ai/loop.json, select or resume at most one issue, and stop after completion, checkpoint, or a human-decision request.
```

Start with an attended run. Confirm that the task can acquire and release the lease, read Linear, find the repository configuration, leave a checkpoint, and stop cleanly.

Every invocation acquires a local lease before reading or mutating Linear, Git, notifications, or repository work. The lease is shared by worktrees and local checkouts configured for the same repository key plus Linear team/project. A concurrent invocation exits without mutation; the active owner may continue or checkpoint. The lease expires 15 minutes after the configured `maxRunMinutes`, allowing recovery after a killed process without permitting a normal in-budget run to overlap.

Lock files live under the user state directory: `LUCHDOM_AI_STATE_HOME` when set, otherwise the platform-local Luchdom state folder. Valid expired locks recover automatically. Malformed lock state fails closed; verify that no invocation is active before moving that file aside for troubleshooting.

## Decisions and notifications

When product input is required, the loop keeps the issue active, adds `needs-human`, and posts options plus a recommendation. Choose a listed option in Linear with:

```text
DECIDE SAAS-123 B
```

Or propose your own direction with:

```text
DECIDE SAAS-123 CUSTOM Keep the existing API and adapt only the client.
```

The next run acknowledges the latest matching owner decision and resumes when the selected option or custom direction resolves the question safely. If a custom suggestion is still ambiguous, the loop asks one focused follow-up and remains paused. Ordinary comments do not authorize work. Linear is authoritative. The Codex scheduled-task inbox provides task visibility; ntfy may send one best-effort alert when enabled through `NTFY_TOPIC`. The alert uses the Linear issue URL as its click target and includes the URL as a fallback, but notification delivery never controls workflow state.

## Completion and recovery

For code, the loop runs focused checks, one standard local project gate, one review, and applicable behavior QA before squash merging the pull request. It verifies the provider reports the PR merged into the configured default branch, then moves the Linear issue to Done. It does not run a second full suite after merge.

If time or test budgets expire, the loop pushes coherent work when safe, adds a concise checkpoint with the branch/PR and next action, leaves the issue active, and stops. If a size limit is reached and the remaining scope is too large for another normal run, the loop creates at most one linked Linear continuation issue for a coherent, independently testable remainder. The parent and continuation acceptance criteria must preserve the original outcome without dropping scope; the continuation stays in Backlog and is not selected during the same invocation. When no safe boundary exists, the loop checkpoints the same issue or requests a decision instead. Repeated technical failure becomes `needs-human`; use a separate child issue only for a genuinely independent prerequisite or continuation.

## Porting to another project

Sync the shared skills and project instructions, add a project-specific `.ai/loop.json`, create the `autonomous` and `needs-human` runtime labels, optionally add `needs-decision` for backlog curation, and document that repository's local validation command. No shared service or copied supervisor code is required.
