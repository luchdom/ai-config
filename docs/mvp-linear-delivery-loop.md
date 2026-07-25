# MVP Linear Delivery Loop

This is a small, local-first loop for one developer completing a repository backlog. It has no CI dependency, supervisor service, lease database, or telemetry stack.

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

Copy the shape from [`project-config.example.json`](../src/skills/linear-delivery-loop/references/project-config.example.json) to `.ai/loop.json` in the target repository. Set the Linear team/project, default branch, and limits, then change `enabled` to `true` only for an attended pilot.

Recommended starting budgets are 45 minutes per invocation, 15 changed files, 800 changed lines, and 15 total test minutes. These are stop-and-split signals, not targets.

## Codex scheduled task

Create one scheduled task in a dedicated Codex chat/project context, initially every 15 minutes. Use the repository as its working directory and this prompt:

```text
$linear-delivery-loop
Run one MVP autonomous delivery iteration for this repository. Obey .ai/loop.json, select or resume at most one issue, and stop after completion, checkpoint, or a human-decision request.
```

Start with an attended run. Confirm that the task can read Linear, find the repository configuration, leave a checkpoint, and stop cleanly. The current Codex task documentation does not promise overlap serialization, so do not reduce the interval unless observed runs reliably finish before the next invocation. If overlap becomes a real problem, add the smallest repository-local lock then.

## Decisions and notifications

When product input is required, the loop keeps the issue active, adds `needs-human`, and posts options plus a recommendation. Reply in Linear with:

```text
DECIDE SAAS-123 B
```

The next run acknowledges the latest matching owner decision, removes `needs-human`, and resumes. Linear is authoritative. The Codex scheduled-task inbox provides task visibility; ntfy may send one best-effort alert when enabled through `NTFY_TOPIC`, but notification delivery never controls workflow state.

## Completion and recovery

For code, the loop runs focused checks, one standard local project gate, one review, and applicable behavior QA before squash merging the pull request. It verifies the provider reports the PR merged into the configured default branch, then moves the Linear issue to Done. It does not run a second full suite after merge.

If time or test budgets expire, the loop pushes coherent work when safe, adds a concise checkpoint with the branch/PR and next action, leaves the issue active, and stops. Repeated technical failure becomes `needs-human`; create a child issue only for a genuinely separate prerequisite.

## Porting to another project

Sync the shared skills and project instructions, add a project-specific `.ai/loop.json`, create the `autonomous` and `needs-human` runtime labels, optionally add `needs-decision` for backlog curation, and document that repository's local validation command. No shared service or copied supervisor code is required.
