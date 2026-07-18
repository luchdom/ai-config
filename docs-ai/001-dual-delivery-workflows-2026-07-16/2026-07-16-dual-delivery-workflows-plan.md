# Dual Interactive and Autonomous Delivery Workflows Plan

## 1. Overview

Create two explicit engineering workflows that share the same specialist agents but have different entry points and control policies:

1. **Interactive delivery** for work selected by the user. It preserves planning, clarification, design, tasking, independent audit, and explicit implementation approval.
2. **Autonomous delivery** for a recurring Codex Scheduled task. Every five minutes it invokes the reusable `$linear-delivery-loop` skill, resumes or claims one eligible Linear issue, drives it through the same engineering stages, opens a PR, performs code review and runtime acceptance testing, and merges only after those gates pass.

Linear will use only the team's regular workflow states. Autonomous eligibility will be expressed by the existing `autonomous` label together with the ordinary `Todo` state. `Ready for Codex` will be removed rather than replaced by another readiness label.

The shared AI configuration repository will own the reusable agents, skill behavior, and deterministic delivery-loop engine. The SaaS repository will own only a thin configuration/wrapper, project policy, validation commands, branch conventions, and operational documentation.

### Goals

- Preserve a deliberate, human-gated workflow for manually selected work.
- Add a safe, resumable, single-issue autonomous loop triggered by a five-minute Codex task heartbeat.
- Reuse planner, product designer, tasker, auditor, implementers, and QA across both workflows.
- Keep Linear authoritative for issue state and `.artifacts/harness` authoritative for local run state.
- Use the `SAAS-*` Linear team key in all current operational guidance and future branch examples.
- Make failure, escalation, notification, and retry behavior deterministic and testable.
- Enforce one global work-in-progress slot across `In Progress` and `In Review`, whether the owner is the user or the autonomous worker.
- Require every executable Linear issue to describe one bounded, observable, locally testable goal.
- Require every executable code-bearing issue to target exactly one repository and one primary PR; coordinate multi-repository programs through a non-autonomous parent and ordered child issues.
- Prioritize locally runnable product capability before external infrastructure and analytics integrations.
- Keep plan, audit, task, review, QA, and completion evidence in the repository and link it from Linear.
- Maintain a searchable docs-as-code wiki for durable product and technical guidance.

### Non-goals

- Do not create separate planner, designer, auditor, implementer, or QA agents for each workflow.
- Do not let the Codex task or another LLM process own concurrency locks, leases, retry counters, or transition state; keep those in the deterministic adapter.
- Do not bulk-rewrite historical `docs-ai` artifacts that accurately record the former `LUC-*` key.
- Do not autonomously provision AWS resources, create recurring spend, rotate secrets, delete data, or perform production operations.
- Do not add parallel issue execution in the initial release.
- Do not install or depend on Windows Task Scheduler in phase 1. It remains a future fallback only if execution must continue while the Codex desktop app is closed.

## 2. Assumptions & Constraints

- The Linear project remains named `SaaS Boilerplate`; `SAAS` is the team key and issue identifier prefix.
- The normal Linear states are `Backlog`, `Todo`, `In Progress`, `In Review`, `Done`, `Canceled`, and `Duplicate`.
- `Backlog` means the issue is not yet execution-ready. `Todo` means the issue is refined enough to start.
- The existing `autonomous` label grants the recurring Codex task scoped permission to claim or resume an issue and to request the issue-bound Git/GitHub mutations defined in section 4.9.
- `blocked`, `needs-human`, `needs-refinement`, and `external-integration` labels will be added for exception and sequencing policy. A separate `manual` label is optional and is not required for correctness.
- Interactive delivery is the default when a user explicitly selects an issue or starts work without requesting autonomous completion.
- An interactive claim removes `autonomous` before changing the issue to `In Progress`, preventing the recurring Codex task from touching it.
- The autonomous worker processes only issues that retain `autonomous` and excludes `blocked`, `needs-human`, `needs-refinement`, and, during the local-first milestone, `external-integration`.
- One recurring Codex task and one global active issue are allowed at a time in phase 1. `In Progress` and `In Review` both consume that slot.
- If the active issue is autonomous, the next Codex heartbeat resumes its durable stage. If the active issue is manual, that heartbeat exits successfully without claiming work.
- The five-minute cadence is a wake-up/recovery interval, not a one-stage throttle. One heartbeat claims or resumes at most one issue and continues through routine stages until `Done`, an external-wait checkpoint such as pending CI, a paused/human condition, bounded retry exhaustion, a non-retryable failure, or Codex ends/interrupts the run.
- After completing or pausing its issue, the heartbeat stops. It never claims a second issue in the same run; the next scheduled heartbeat may claim the next eligible item.
- A paused issue is moved to `Backlog` with `blocked`, `needs-human`, or `needs-refinement`, releasing the WIP slot while retaining the durable reason and evidence.
- Create the recurring automation from a dedicated Codex task rooted at the SaaS project and running in Worktree mode. Each heartbeat returns to that task's context; durable correctness still comes from Linear, Git, and `.artifacts/harness`, not conversation memory.
- Local Codex Scheduled runs require the computer to remain powered on, the desktop app to remain running, and the SaaS project to remain accessible. The loop is resumable after missed heartbeats but is not a 24/7 service in phase 1.
- The automation prompt explicitly invokes `$linear-delivery-loop`. It does not rely on automatic skill selection or a documented direct custom-agent selector; the skill owns specialist delegation.
- The canonical supervisor engine lives under `ai-config/src/skills/linear-delivery-loop/` and is generated/synced with the skill. SaaS must not duplicate its GraphQL, lease, state-machine, notification, or Git/GitHub implementation.
- New changes use one primary branch and one primary PR per issue. A failed post-merge smoke check permits bounded repair branches/PRs on the same Linear issue as the only phase-1 exception. The deterministic supervisor is the sole automation owner of state-changing Git/GitHub commands. The `autonomous` label grants it permission to create the issue branch/worktree, stage the issue change set, commit, push, open/update the PR, and squash-merge after all gates pass; unresolved product, security, cost, revert, or other destructive-operation decisions still require the user.
- `Done` means the PR is merged to `main` and the post-merge validation or smoke check has passed. Passing tests on an unmerged branch is not Done.
- The PR-based `Done` rule applies to code-bearing work, including docs-as-code changes. A manual non-code operational issue may reach `Done` only through its explicit evidence-based acceptance contract; it must not create an empty or artificial PR.
- A configured Linear owner identity is used for assignment, `@mention` delivery, and authorization of structured decision replies.
- The deterministic adapter talks directly to Linear's GraphQL API at `https://api.linear.app/graphql`; it does not depend on the interactive Codex Linear MCP session.
- Linear authentication uses the personal API key in the `LINEAR_API_KEY` process environment variable. The key is persisted outside the repositories at Windows user scope and must never appear in command arguments, config files, logs, state, artifacts, comments, or notifications.
- A personal API key acts as its owning Linear user. Until a separate automation actor exists, supervisor-authored comments and mentions may be self-authored, so native Linear push delivery must be verified rather than assumed.
- Linear comments and state are the durable decision record. Until a separate Linear automation actor exists, ntfy is the required attention channel for actionable autonomous escalations. The Codex Scheduled inbox is the run-observability inbox, while Linear native notifications remain an opportunistic addition.
- The Linear connector available to Codex does not expose workflow-status deletion. Removing `Ready for Codex` is a manual Linear workspace administration step.
- Existing `LUC-*` historical artifacts and already-published branch names remain valid historical evidence. Current operational docs, active workflow artifacts, new branches, comments, and examples use `SAAS-*`.
- The current `codex/LUC-43-conflict-resolution` branch is a legacy-name branch created before the team-key rename; it should not be renamed as part of this workflow project unless separately authorized.
- This change affects workflow and automation rather than product UI, so `product-designer` and a `*-design.md` artifact are not required for this implementation.

## 3. Architecture / Approach

### 3.1 Shared specialist pipeline

Both workflows reuse the same delivery pipeline:

```text
planner
  -> product-designer when non-trivial UI work exists
  -> tasker
  -> auditor
  -> dotnet / nextjs-mui / react / jekyll-site-builder
  -> code-reviewer
  -> qa as runtime acceptance tester
  -> documentation check
```

The difference between workflows is orchestration policy, not specialist behavior.

### 3.2 Interactive workflow

Add an `interactive-driver` agent as the human-gated entry point.

```text
User selects SAAS-N
  -> remove autonomous if present
  -> move issue to In Progress
  -> plan
  -> clarify with the user
  -> design when required
  -> task breakdown
  -> independent audit
  -> wait for explicit Implement approval
  -> implement
  -> deterministic repository adapter commits, pushes, and opens or updates PR
  -> In Review
  -> code review
  -> runtime acceptance QA
  -> user merges, or explicitly authorizes the deterministic repository adapter to merge
  -> post-merge smoke check on main
  -> Done
```

Interactive-driver rules:

- Never select another issue from Linear.
- Never cross the implementation gate without explicit approval in the active conversation.
- Ask one focused clarification at a time.
- Allow returning to plan, design, tasking, or audit at the user's request.
- Keep issue comments concise and write only meaningful state transitions or decisions.
- Use the issue identifier in the workflow artifact, branch, and handoff summary.

### 3.3 Autonomous workflow

Refactor the current one-shot `feature-driver` behavior into a clearly named `autonomous-driver`. Keep `feature-driver` temporarily as a backward-compatible router or alias so existing installed configurations do not fail immediately.

The recurring Codex task is the autonomous orchestrator. Its durable prompt explicitly invokes `$linear-delivery-loop`; that skill calls the deterministic supervisor adapter for selection, leases, state transitions, Linear, and Git/GitHub mutations, then delegates reasoning work to `autonomous-driver` and the shared specialists. The adapter never launches a nested `codex exec` process.

```text
Five-minute Codex task heartbeat
  -> invoke $linear-delivery-loop explicitly
  -> adapter atomically acquires or renews the run lease
  -> adapter loads and reconciles durable state
  -> inspect the global In Progress/In Review WIP slot
  -> resume autonomous issue when it owns the slot
  -> exit successfully when a manual issue owns the slot
  -> otherwise select Todo + autonomous
  -> revalidate issue eligibility and dependencies
  -> reuse the dedicated Codex task worktree and issue branch
  -> skill delegates to autonomous-driver and specialists
  -> collect and apply a schema-validated checkpoint
  -> continue immediately to the next routine stage while terminal/pause conditions are false
  -> adapter validates and applies Linear, Git/PR, state, and notification transitions at every checkpoint
  -> adapter releases or renews the lease according to the durable next stage
  -> stop after this issue completes, pauses, exhausts retry, or the Codex run ends
```

Autonomous-driver rules:

- Continue through planning, safe clarification resolution, tasking, audit, implementation, and QA without intermediate user prompts.
- Stop only for documented high-risk conditions.
- Record every auto-resolved assumption in workflow artifacts and the final structured result.
- Never choose another Linear issue; selection belongs to the supervisor.
- Never decide that a run owns a lock or retry slot; those belong to the supervisor.
- Never run state-changing Git or GitHub commands. Edit and validate only the assigned worktree, inspect Git read-only when useful, and return a change manifest plus proposed commit/PR metadata to the supervisor.
- Return defects from QA to the appropriate implementer within the same run while the retry budget remains.
- Do not stop merely because planning, tasking, audit, implementation, review, QA, or merge produced a successful intermediate checkpoint. Continue to the next stage in the same heartbeat.
- Return the change manifest and PR metadata so the supervisor opens or updates a PR for every implementation, moves it to `In Review`, and runs the code-review and acceptance-test gates against that PR branch.
- Merge an autonomous PR only when the issue contract is satisfied, review has no unresolved blocking findings, runtime acceptance QA passes, docs impact is addressed, and no human decision is pending.
- Re-check `main` after merge and move the Linear issue to `Done` only after the post-merge smoke check passes.
- If that check fails, keep the same issue in `In Review`, preserve the failing merge SHA and evidence, and use the bounded repair flow in section 4.9. Never revert `main` automatically.

### 3.4 Linear state and label contract

Regular state meanings:

| State | Meaning |
|---|---|
| `Backlog` | Unrefined, incomplete, deprioritized, or not ready to execute. |
| `Todo` | Refined and eligible to start. |
| `In Progress` | Actively owned by a human or the autonomous worker. |
| `In Review` | A PR exists and code review, runtime acceptance QA, merge, or post-merge validation is active. |
| `Done` | Code-bearing: latest PR/repair is merged and post-merge validation passed. Manual-operational: explicit evidence contract passed. |
| `Canceled` / `Duplicate` | Normal terminal outcomes. |

Label meanings:

| Label | Meaning |
|---|---|
| `autonomous` | The recurring Codex task may claim or resume this issue through the deterministic adapter. |
| `blocked` | An external dependency prevents progress. Worker must ignore it. |
| `needs-human` | A clarification or approval is required. Worker must ignore it. |
| `needs-refinement` | The issue is too vague, too large, or missing its executable contract. Worker must ignore it. |
| `external-integration` | The issue depends on hosted infrastructure, analytics, a live provider, or another non-local service. It is deferred during the local-first milestone. |

Autonomous selection predicate:

```text
project = SaaS Boilerplate
team key = SAAS
state = Todo
labels contains autonomous
issue kind = code-bearing
labels excludes blocked
labels excludes needs-human
labels excludes needs-refinement
labels excludes external-integration during the local-first milestone
issue is not an epic/parent selected instead of an executable child
target repository = the repository key configured for this worker
dependencies are complete or explicitly non-blocking
the executable issue contract is complete
```

Resume predicate:

```text
state = In Progress or In Review
labels contains autonomous
labels excludes blocked
labels excludes needs-human
issue matches the locally persisted active run, branch, or worktree
```

Before selection, the supervisor queries both `In Progress` and `In Review`. A matching autonomous issue is resumed. Any manual issue in either state consumes the single WIP slot, so the iteration records `manual-wip-present` and exits without claiming another issue.

Executable issue contract:

- issue kind: `code-bearing` or `manual-operational`
- exactly one target repository key and base branch for code-bearing work
- one outcome stated in observable product or system behavior
- bounded scope that fits one reviewable PR
- explicit acceptance criteria and non-goals
- dependencies and prerequisite issues
- local validation command or executable API/browser scenario
- docs impact: `none` with a reason, or the exact how-to/reference/ADR/runbook page to update
- risk flags for product decisions, tenant/security boundaries, billing behavior, data migration, spend, destructive actions, and external services

If this contract is incomplete, the issue is not claimable. The workflow moves it to `Backlog + needs-refinement`, comments the missing fields and a proposed split, and does not invent product intent while implementing.

Backlog migration and deterministic queue order:

1. Before enabling the heartbeat, inventory every project issue carrying `autonomous` in both `Backlog` and `Todo`, plus every issue currently in `Ready for Codex`, including each issue's parent/children and blocking dependencies. Auditing only `Todo` is insufficient, and the custom state cannot be deleted until its issue count is zero.
2. For a broad parent, epic-like issue, or multi-goal item, keep/move it to `Backlog`, add `needs-refinement`, remove `autonomous`, and create or reuse linked executable leaf issues with complete contracts. The parent remains a grouping record and is never claimable.
3. For hosted infrastructure, live analytics/monitoring, AWS, hosted pipelines, production secrets, or another deferred external dependency, keep/move it to `Backlog`, add `external-integration`, and remove `autonomous` until the local-first milestone is explicitly complete.
4. Split mixed local/external issues at the boundary. Only the locally runnable leaf receives `Todo + autonomous`; its external child remains deferred.
5. Move a leaf to `Todo + autonomous` only when its executable contract is complete, dependencies are satisfied, it is locally runnable, and unattended execution is intended. A ready manual issue uses `Todo` without `autonomous`.
6. Make the migration idempotent, preserve unrelated labels, avoid duplicate child issues, and write one redacted local report under ignored `.artifacts/harness/operations/` plus concise Linear evidence only where classification changed. Do not create a repository PR for the operations-only run.

After complete pagination and eligibility/dependency filtering, sort claimable candidates by:

1. Linear priority: Urgent, High, Normal, Low, then No priority.
2. `createdAt` ascending so the oldest issue wins within a priority.
3. Numeric issue identifier ascending as the final stable tie-breaker.

The adapter performs this sort locally, records the ordered candidate/rejection report in `-DryRun`, and re-reads the first candidate immediately before claim.

Cross-repository program contract:

- Use one non-autonomous parent issue to describe the overall outcome, child map, integration acceptance, and completion roll-up. Keep it in `Backlog` while children execute so it does not consume the global `In Progress`/`In Review` WIP slot.
- Every executable code-bearing child names exactly one repository key, one base branch, one primary PR, its own observable acceptance criteria, and its repository-local evidence folder.
- Split shared-engine work into an `ai-config` child and SaaS integration into one or more dependent `saas` children. The SaaS worker rejects a child whose repository key is not `saas`; a future ai-config worker would require its own config and heartbeat.
- Express cross-repository order with Linear blocking dependencies. Merge and validate the upstream repository child before unblocking the dependent repository child; never edit or commit two repositories under one executable issue.
- Use a separate `manual-operational` child for Linear workspace administration, notification setup, pilot approval, or another task with no repository diff. It never carries `autonomous`, follows the manual workflow, and consumes the global WIP slot only while explicitly `In Progress`.
- A manual-operational issue defines exact evidence such as before/after state, IDs, screenshots, API readback, or a documented verification result. It moves to `Done` only when that evidence passes; no placeholder branch or PR is created.
- When all children are terminal and the parent's integration acceptance is satisfied, close the parent manually with a roll-up comment linking child outcomes. The parent itself never receives `autonomous`.

### 3.5 Control-plane components

Shared in `ai-config`:

- `src/agents/interactive-driver.md`
- `src/agents/autonomous-driver.md`
- `src/agents/code-reviewer.md`
- strengthened `src/agents/qa.md` contract for running API and browser acceptance scenarios against a live local stack
- compatibility update to `src/agents/feature-driver.md`
- `src/skills/linear-delivery-loop/SKILL.md`
- `src/skills/linear-delivery-loop/references/issue-contract.md`
- `src/skills/linear-delivery-loop/references/state-machine.md`
- `src/skills/linear-delivery-loop/references/failure-policy.md`
- `src/skills/linear-delivery-loop/references/worker-result.schema.json`
- `src/skills/linear-delivery-loop/references/project-config.schema.json`
- `src/skills/linear-delivery-loop/references/codex-scheduled-prompt.md` as the reusable, versioned heartbeat prompt template
- `src/skills/linear-delivery-loop/scripts/agent-worker-engine.ps1` as the canonical checkpoint command surface
- `src/skills/linear-delivery-loop/scripts/modules/` for config, lease/state, Linear GraphQL, Git/GitHub, notification, redaction, and recovery modules
- `src/skills/docs-as-code/SKILL.md` with reusable how-to, concept, reference, ADR, runbook, and troubleshooting templates
- update `luchdom-docs` to apply the reusable docs skill plus Luchdom-specific source-of-truth rules
- updates to `task-audit-breakdown` so new artifact routing uses `docs-ai/<SAAS-N-or-local-sequence>-<slug>/` while preserving legacy fallback
- updates to `qa-verification` so its reusable runtime contract enforces localhost/Development isolation, disposable data, production-secret rejection, bounded readiness, and cleanup evidence
- updates to `multi-agent-delivery`, project templates, README, build validation, and sync verification

Project-specific in `saas`:

- `automation/linear-delivery-loop.config.json`: versioned project adapter values; it contains environment-variable names but no secret values
- `scripts/agent-worker.ps1`: thin manual shim that resolves and forwards to the installed shared engine; it contains no GraphQL, lease, transition, notification, or Git/GitHub implementation
- `scripts/test-agent-worker.ps1`: project contract tests that invoke the shared engine with SaaS config and fixture data
- `automation/codex-scheduled-linear-loop.md`: rendered SaaS-specific prompt and setup values used when creating or updating the Codex Scheduled task; this file is versioned documentation, not an automatically discovered Codex config surface
- `.artifacts/harness/runs/`: ignored run output and structured logs
- `mkdocs.yml` plus the existing `docs/` tree as the searchable local wiki
- project docs and doc-drift assertions

The shared skill defines orchestration behavior, the heartbeat prompt, contracts, and executable engine. The SaaS config supplies only fixed repository commands, paths, and Linear project/team values; the wrapper forwards manual calls. Codex Scheduled owns timing and run visibility. Neither the config nor wrapper owns scheduling, agent execution, or state-machine logic.

Do not create a separate automation repository yet. `ai-config` already has the correct reusable ownership boundary, while SaaS should remain a thin project adapter. Extract a dedicated harness repository or plugin only after a second project reveals concrete differences that cannot be expressed as adapter configuration.

## 4. API / Contracts

### 4.1 Interactive-driver input contract

Required input:

- selected issue identifier such as `SAAS-44`, or a user request that will be attached to an explicitly selected issue before implementation
- repository root
- workflow mode `interactive`

Required behavior:

- fetch issue details read-first
- ensure the issue is not simultaneously owned by the autonomous loop
- remove `autonomous` when the user claims the issue
- write/reuse the workflow folder
- stop at the explicit implementation gate

### 4.2 Codex automation and supervisor command contracts

Create one recurring heartbeat from a dedicated Codex task rooted at the SaaS project in Worktree mode. Configure a five-minute interval and keep the prompt versioned in `automation/codex-scheduled-linear-loop.md`. The durable prompt must explicitly invoke `$linear-delivery-loop`, work on at most one claimed/resumed issue, continue through all routine stages in that same run, use the deterministic adapter for every checkpoint/mutation, and stop cleanly only for no work, manual WIP, a held lease, external wait, issue completion/pause, bounded retry exhaustion, non-retryable failure, or Codex run interruption.

Use a task heartbeat rather than a standalone scheduled task so each recurrence returns to the same Codex task context. Do not make correctness depend on that context: every heartbeat starts by reconciling Linear, Git/GitHub, and `.artifacts/harness`. The computer must be on and the Codex desktop app running for local scheduled execution.

The PowerShell adapter is a short-lived deterministic command surface; it never launches `codex exec`. Representative calls:

```powershell
pwsh ./scripts/agent-worker.ps1 -Action PrepareIteration -RunId <uuid>
pwsh ./scripts/agent-worker.ps1 -Action ApplyCheckpoint -InputPath <absolute-json-path>
pwsh ./scripts/agent-worker.ps1 -Action Status
```

Supported parameters:

- `-Action PrepareIteration`: atomically acquire or renew the durable lease, run preflight/reconciliation, and return a schema-validated claim/resume/no-op payload.
- `-Action ApplyCheckpoint`: consume a schema-validated result file, renew the caller-owned lease, and apply only the authorized Linear, state, notification, or Git/GitHub transition requested by that checkpoint.
- `-Action Status`: report lease, active issue/stage, last heartbeat, pending decision/notification, and retry state without mutation.
- `-Action ReleaseLease`: release only the caller-owned lease after a durable terminal or paused checkpoint.
- `-DryRun`: read, select, and report without Linear, Git, or worktree mutations.
- `-Issue SAAS-N`: pilot or recover a specific eligible issue.
- `-MaxAttempts <n>`: bounded autonomous repair attempts for one stage.
- `-NoNotify`: disable ntfy only for `-DryRun`, fixture tests, or an attended manual diagnostic. Codex Scheduled execution rejects this flag.

The adapter accepts structured payloads through absolute files, not large or sensitive command-line arguments. A short-lived OS mutex protects each adapter invocation; an atomic durable lease with owner run ID, heartbeat, and expiry prevents overlapping Codex heartbeats from working concurrently after the adapter process exits.

Lease/run rules:

- Renew immediately before and after every specialist stage and long-running validation/QA command, and on every accepted checkpoint.
- Configure lease duration from the maximum allowed single project command plus a safety margin; it must never be shorter than three schedule intervals.
- A later heartbeat with a healthy lease exits `10` without notification. An expired lease is not sufficient proof of abandonment: reclaim only after Linear/Git/GitHub reconciliation shows no newer owner/mutation and the previous scheduled run is terminal when that signal is available; otherwise fail closed and escalate reconciliation.
- Within one heartbeat, consume the configured retry budget for implementation, review, QA, merge, and post-merge defects before pausing. Bounded transient transport backoff may also happen in-run; a still-retryable external outage persists state and waits for the next heartbeat.
- Once the owned issue reaches `Done` or a paused state, release the lease and end the heartbeat without running selection again.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | No eligible work or successful checkpoint. |
| `10` | Another heartbeat owns the durable lease. |
| `20` | Retryable/transient failure recorded. |
| `30` | Human input or approval required. |
| `40` | Non-retryable harness/configuration failure. |

### 4.3 Linear transport and adapter contract

The deterministic adapter uses direct HTTPS GraphQL calls so selection, arbitration, recovery, and Linear mutations do not depend on an LLM session or MCP availability.

Authentication and startup rules:

- Read `LINEAR_API_KEY` only from the process environment and send it as the `Authorization` header value for personal-key authentication.
- Never accept the key as a command-line parameter. Never serialize the header or key into diagnostic output.
- On every supervisor start, run a read-only preflight that resolves `viewer`, team `SAAS`, project `SaaS Boilerplate`, workflow states, configured labels, and configured owner to stable UUIDs.
- Fail closed with exit `40` before any mutation when the key is missing, invalid, lacks access, resolves to an unexpected workspace, or required workflow metadata is ambiguous.
- The Codex desktop app must be restarted after a new user-scoped secret is added so future local scheduled runs inherit it. Preflight verifies access without printing the value.

Adapter behavior:

- Expose explicit operations for preflight, paginated WIP/candidate reads, issue re-read, claim, assignment, comment creation/readback, label changes, state changes, dependency reads, follow-up creation, and decision-reply reads.
- Use GraphQL variables rather than interpolating issue content into query documents.
- Check both HTTP status and the GraphQL `errors` array; a `200` response with errors is not success.
- Follow cursors until the required collection is exhausted and record rate-limit metadata without recording authorization headers.
- Retry only transport, `429`, and eligible `5xx` failures with bounded exponential backoff and jitter. Treat validation, authorization, and schema errors as non-retryable configuration failures.
- Make supervisor mutations idempotent through durable operation keys plus read-before-write and read-after-write reconciliation. Preserve unrelated issue labels and comments.
- Keep the adapter behind a fixture-compatible interface so contract tests never need live mutations. Live validation starts with a read-only `-DryRun` preflight.

### 4.4 Run result contract

Every recurring Codex heartbeat uses a schema-validated checkpoint envelope. The deterministic adapter owns identity, state, Git/GitHub observations, revisions, and transition metadata; specialist agents can propose only the reasoning fields nested under `agentProposal`:

```json
{
  "schemaVersion": "1.0",
  "runId": "string",
  "mode": "autonomous",
  "issueId": "SAAS-44",
  "stateRevision": 7,
  "transitionId": "uuid",
  "expectedPreviousStage": "implementation",
  "stage": "claimed|planning|design|tasking|audit|implementation|local_validation|publish|ci_wait|code_review|runtime_qa|merge_ready|merge|post_merge|post_merge_repair|done|paused",
  "codexTaskId": "string-or-null",
  "scheduledRunId": "string-or-null",
  "observed": {
    "linearRevision": "string-or-null",
    "branch": "codex/SAAS-44-short-name",
    "baseSha": "string-or-null",
    "headSha": "string-or-null",
    "pullRequests": [],
    "mergeCommits": [],
    "ci": { "required": ["Validate / validate"], "headSha": null, "status": "not_started", "firstObservedAt": null, "deadlineAt": null }
  },
  "attempts": { "implementation": 1, "ci": 0, "postMerge": 0 },
  "agentProposal": {
    "outcome": "continue|waiting_external|completed|retryable|blocked|needs_human|needs_refinement|failed",
    "assumptions": [],
    "changeManifest": [],
    "artifacts": [],
    "validationClaims": [],
    "blocker": null,
    "decisionRequest": null,
    "followUpProposal": null,
    "nextAction": "string",
    "requestedTransition": "string-or-null"
  },
  "acceptedTransition": "string-or-null",
  "operationIds": []
}
```

The adapter constructs and validates the outer envelope from its own inputs and fresh external reads. It rejects an agent result that echoes a different issue/run identity, and it independently observes branch, SHA, PR, CI, attempts, and current Linear state rather than trusting agent prose. Specialist prose is evidence only and cannot directly cause a mutation. Each accepted checkpoint records its schema version, expected state revision/stage, transition ID, observed external state, operation IDs, and resulting durable revision/stage so restart recovery is deterministic. A revision or expected-stage mismatch fails closed and forces reconciliation.

### 4.5 WIP and claim contract

At the start of every iteration:

1. Query every project issue in `In Progress` or `In Review`.
2. If more than one exists, fail closed, notify once, and require reconciliation.
3. If exactly one manual issue exists, record a no-op result and exit `0`.
4. If exactly one autonomous issue exists and ownership reconciles with local/Git state, resume it from its durable stage.
5. Only when the global WIP query is empty may the supervisor select a new `Todo + autonomous` issue.

Claiming an issue requires all of the following:

1. Acquire the short invocation mutex and atomically claim the durable run lease.
2. Re-read the candidate immediately before mutation.
3. Verify the selection predicate still holds.
4. Move the issue to `In Progress`.
5. Retain `autonomous` and assign the configured worker identity when available.
6. Add one Linear comment with run ID, machine/worker identity, branch, and timestamp.
7. Re-read the issue and abort if ownership no longer matches.
8. Persist local run state before returning the prepared iteration to `$linear-delivery-loop` for specialist work.

### 4.6 Failure and follow-up contract

- Transient tool/network error: retain the original issue, increment a bounded retry counter, and resume later.
- Interrupted or missed Codex heartbeat: allow only the bounded lease to expire, then have the next heartbeat reconcile external state and resume from the last accepted durable checkpoint. Task conversation context is helpful but never authoritative.
- Implementation or test defect: return to the responsible implementer while the retry budget remains.
- Independent external blocker: move the issue to `Backlog + blocked`, and create a linked child issue only when the blocker is separately actionable and not already tracked.
- Product/security/cost ambiguity: move the issue to `Backlog + needs-human`, and do not create a speculative implementation issue unless a separate action is clear.
- Incomplete or oversized issue contract: move the issue to `Backlog + needs-refinement`, and post a bounded split proposal rather than attempting the vague scope.
- Repeated non-progress: attach evidence, logs, attempted fixes, and next recommendation to the original issue before notification.
- A follow-up issue must state its own achievable outcome and acceptance criteria. Do not create generic tickets such as "fix tests" or "investigate blocker" without an observable completion condition.
- Failed post-merge validation: keep the original issue in `In Review`, retain `autonomous`, record the exact failing merge SHA and evidence, and enter the repair-PR flow. Do not create a second Linear issue for the repair and do not auto-revert `main`.
- Exhausted or unsafe post-merge repair: move the original issue to `Backlog + needs-human`, attach the complete PR/merge/validation history and a recommended decision, release the WIP lease, and notify through Linear plus ntfy.

### 4.7 Notification contract

Linear remains the durable source of truth for the request, reply, and consumed decision. The supervisor must assign the configured owner and `@mention` that owner in the decision comment, but self-authored Linear notifications are not the phase-1 attention guarantee. Keep Linear desktop and/or mobile notifications enabled as an additional channel and verify them during the pilot.

Decision-request comment contract:

```text
Decision required: <decision-id>
Issue: SAAS-N — <title>
Question: <one focused product question>
A: <option and consequence>
B: <option and consequence>
C: <optional option and consequence>
Recommendation: <option with rationale>
Reply exactly: Decision <decision-id>: <A|B|C>
Artifacts: <repo links>
```

The supervisor accepts a decision only when the reply:

- is authored by the configured Linear owner
- was created after the matching request
- contains the exact decision ID and one offered option
- has not already been consumed

Before ordinary WIP/queue selection, `PrepareIteration` paginates `Backlog + needs-human + autonomous` issues carrying the machine-readable pending-decision marker and reconciles them with local pending-decision state. After accepting an exact reply, record the decision in the issue comment and workflow artifact, remove `needs-human`, move the issue to `Todo + autonomous`, and mark that same issue `resume-pending`. The next heartbeat reclaims it before normal candidate ordering after revalidating its contract and dependencies. Malformed, duplicate, stale, or unauthorized replies are ignored and the issue remains paused.

ntfy is the required phase-1 attention adapter for unattended actionable escalations:

- publish over HTTP POST to the configured ntfy server/topic
- keep `NTFY_BASE_URL`, `NTFY_TOPIC`, and `NTFY_TOKEN` outside the repository and redact them everywhere
- send actionable alerts for `needs-human`, `blocked`, retry exhaustion, multiple-active-issue reconciliation, and worker configuration failure
- include the issue ID/title, decision or blocker summary, recommendation, and a click action that opens the Linear issue
- keep decision entry in Linear for phase 1; do not add an inbound callback service or ntfy HTTP decision button yet
- allow an optional configuration flag for PR-ready and completed notifications, disabled by default to limit noise
- fail the unattended startup preflight when the ntfy configuration is absent or invalid; permit the no-op adapter only in fixture tests and explicit attended diagnostics

The Codex Scheduled view is the operational inbox for runs and unread results. It complements ntfy but does not replace Linear as the decision record or ntfy as the phase-1 actionable-attention guarantee.

Do not notify for an empty queue, a held lock, or ordinary intermediate stages. A failure to deliver ntfy must be retried idempotently and surfaced by worker health, but must not roll back the durable Linear pause/comment or allow the paused issue to resume silently.

### 4.8 Linear interaction and evidence contract

Only the interactive driver or autonomous supervisor mutates Linear. Specialist agents write artifacts and return a proposed status/comment payload to the driver; they do not independently race to update the issue.

Required repository artifacts for a code-bearing issue:

```text
docs-ai/<SAAS-N-or-local-sequence>-<slug>/
  <date>-<slug>-plan.md
  <date>-<slug>-design.md            # only when non-trivial UI/UX scope requires it
  <date>-<slug>-audit.md
  <date>-<slug>-tasks.md
  <date>-<slug>-code-review.md
  <date>-<slug>-qa.md
  <date>-<slug>-completion.md
```

Use `SAAS-N-<slug>` for work attached to a Linear issue and a zero-padded local sequence such as `001-<slug>` before an issue exists. Preserve the existing flat historical `docs-ai` files without mechanical relocation; only new workflow artifacts use the folder convention. A design artifact is required only for non-trivial user-interface layout, interaction, usability, or accessibility changes; backend, infrastructure, documentation-only, and workflow-only changes explicitly record `design: not required` in the plan/task metadata.

Required Linear updates are concise transition summaries rather than copies of the documents:

- claim: run ID, branch, workflow mode, and artifact folder
- paused: exact blocker/decision, evidence, recommendation, and follow-up issue when one exists
- `In Review`: PR, plan/audit/tasks/review/QA links, validation summary, and remaining gate
- `Done`: merge commit, post-merge validation, durable docs updated, and any non-blocking follow-ups

Once the branch is pushed, use immutable repository blob links at the recorded head SHA, or merged-`main` links after completion, so Linear remains navigable. Keep full evidence in Git where it can be versioned, reviewed, and searched.

Commit plan/design/audit/task and draft review/QA/completion evidence before the final gated head. If adding evidence changes the head, the adapter verifies that the delta is evidence-only, reruns documentation and local validation, obtains exact-head CI, and performs a final exact-head code-review attestation. Runtime QA may be reused only when the post-QA delta is confined to non-executable evidence files and the final reviewer explicitly records that behavior is unaffected; otherwise rerun it. Store the final SHA-bound gate attestations in durable run state and the Linear `In Review`/`Done` summaries without another branch mutation.

For a `manual-operational` issue, replace repository artifacts with redacted local run evidence under ignored `.artifacts/harness/operations/` plus a concise Linear evidence record. Record the acceptance checks, actor, timestamp, before/after state, and durable references. Do not create a repository folder or PR solely to satisfy the code-bearing template. `DDW-SAS-001` owns the reusable migration procedure/report schema; an actual post-run repository report is outside the baseline and, if later required, must be a separately approved code-bearing documentation issue.

### 4.9 Git and GitHub mutation contract

The deterministic repository adapter used by the supervisor is the sole automation component allowed to run state-changing `git` or `gh` operations. Specialist agents may edit files, run repository validation, and use read-only inspection such as `git status` and `git diff`; they return a structured change manifest and proposed commit/PR metadata instead of staging, committing, pushing, opening a PR, or merging.

Authorization rules:

- For autonomous work, re-read the Linear issue before each externally visible Git/GitHub transition. The issue must still carry `autonomous`, remain owned by the active run, and have no stop label or pending decision.
- The `autonomous` label authorizes only the named issue's isolated worktree, `codex/SAAS-N-<slug>` branch, PR targeting `main`, and gated squash merge. It does not authorize force-push, direct writes to `main`, unrelated repository changes, tag/release mutations, workflow-secret changes, or destructive cleanup outside the configured worktree root.
- After a recorded post-merge failure, the same authorization permits `codex/SAAS-N-repair-<attempt>` and its PR targeting the current `main`, subject to the same gates and retry budget. It never authorizes an automatic revert.
- For interactive work, the same deterministic adapter may create commits, push, or open/update a PR only after the active conversation grants the corresponding explicit implementation/publish authority. Merge remains user-owned unless the user explicitly requests it.
- The human user may always perform Git/GitHub operations directly; "sole owner" applies to automated components, not to the repository owner.
- **Bootstrap exception for this program:** the adapter and SaaS wrapper do not exist early enough to deliver their own implementation. After the user explicitly approves `Implement`, every `DDW-*` code child is delivered through Interactive Delivery, and only the root Codex task or human user—not specialist subagents—may perform the user-approved branch, commit, push, PR, and merge actions. Each child still uses one issue branch, one primary PR, squash merge, review/QA/docs gates, and exact-SHA validation. This narrow exception ends after `DDW-SAS-003` is merged and the shared engine/SaaS adapter are installed and verified; later autonomous product work must use the deterministic adapter.

Mutation and PR rules:

1. Snapshot the issue worktree's base SHA and pre-existing status before agent execution.
2. After agent execution, compare the returned change manifest with the real diff. Fail closed on unexpected paths, changes outside the issue worktree, conflict markers, or unrelated pre-existing edits.
3. Run `pwsh ./scripts/validate-all.ps1` before staging. Stage only the reconciled issue change set, create an issue-prefixed commit, and push without force.
4. Create or reuse exactly one primary PR whose head is the issue branch and whose base is `main`; record its number, URL, head SHA, and current base SHA in durable state.
5. Query GitHub Actions/checks directly for the exact PR head SHA and require workflow `.github/workflows/validate.yml`, job `validate`, displayed check `Validate / validate`, produced by the `pull_request` event. The workflow must trigger once for feature PR heads and on `push` only for `main`, avoiding duplicate push/PR runs for the same feature SHA. If multiple logical runs still exist because of a rerun, accept only the latest run/attempt for that workflow, event, job, and head when it is successful and no newer attempt is pending; ambiguous identity fails closed. The supervisor enforces this gate itself because branch protection/rulesets are unavailable for the current private-repository plan.
6. When the required check is pending or not yet present, record `ci_wait` with the exact head SHA and first-observed timestamp, keep the issue `In Review + autonomous`, release the run lease, and end the heartbeat. The next heartbeat resumes the same WIP issue.
7. Allow 30 minutes total for the required check to appear and complete for one head SHA. At the deadline, a still-missing/pending check becomes `Backlog + needs-human` with Linear/ntfy evidence. Canceled, skipped, timed-out, or failed required checks are failures, never passes.
8. A failed CI head returns to implementation and consumes one CI repair attempt. A new repaired head reruns local validation and resets its own 30-minute pending timer. Three failed CI heads exhaust the stage and become `Backlog + needs-human`.
9. Immediately before merge, fetch `origin/main` and compare it with the base SHA used by the passing gates. If `main` advanced, merge `origin/main` into the issue branch without rebasing or force-pushing, resolve routine conflicts within the retry budget, and rerun local validation, runtime QA where affected, and `Validate / validate` on the new exact head.
10. Re-read Linear authorization, PR review/QA evidence, docs gate, exact current head SHA, exact current base SHA, required check result, and mergeability immediately before merge.
11. Squash-merge through GitHub; never merge the local branch directly into `main`. Capture the returned merge commit SHA, then validate that exact commit from a clean isolated `main` worktree before moving Linear to `Done`.

Every Git/GitHub mutation is logged as a redacted structured operation with its authorization basis, expected prior state, observed result, and idempotency key. On ambiguous CLI/API output, re-read Git and GitHub state before retrying.

Post-merge repair exception:

1. A failed smoke check records `post_merge_failed`, the exact merge SHA, failing command/scenario, logs, and reproduction evidence while the Linear issue remains `In Review`.
2. Reconcile the current remote `main`, then create or reuse `codex/SAAS-N-repair-<attempt>` from that exact current base. One repair attempt maps to one repair branch and one PR on the original issue.
3. Scope the repair only to restoring the original issue contract and the failed post-merge behavior. New product scope or an ambiguous remedy requires `needs-human`.
4. Run the complete local validation, code-review, runtime-QA, docs, exact-head GitHub-check, authorization, and mergeability gates again; prior PR evidence cannot be reused as a passing gate for a new repair head.
5. Squash-merge the repair PR, append its PR and merge SHA to durable history, and validate the new exact merge SHA from a clean worktree.
6. Repeat for at most the configured three post-merge repair attempts. Move to `Done` only when the latest exact merge SHA passes.
7. On exhaustion or an unsafe/unclear repair, move the original issue to `Backlog + needs-human`, notify with the ordered repair history and recommendation, and release WIP. Never create a speculative repair issue or automatically revert `main`.

### 4.10 Shared-engine and project-adapter boundary

`ai-config/src/skills/linear-delivery-loop/` is the only source of truth for the executable supervisor engine. `scripts/build.py` copies the complete skill, including scripts and schemas, into generated tool distributions; `scripts/sync.py` installs that version as one unit. Do not hand-edit generated or installed copies.

The shared engine owns:

- project-config and checkpoint schema validation
- atomic lease/state persistence and reconciliation
- Linear GraphQL transport, pagination, retry, idempotency, and mutations
- Git/GitHub authorization, manifest reconciliation, PR/check/merge, and post-merge repair
- Linear/ntfy notification delivery and secret redaction
- exit codes, structured logs, health/status, fixture interfaces, and recovery semantics

The SaaS adapter owns:

- repository key (`saas`) and permitted base branch
- team key, project name/ID, status and label names
- base branch and issue/repair branch templates
- repository-relative artifact, docs, and validation locations
- fixed local validation commands and required GitHub check names
- local-first policy flags and project-specific runtime-QA hooks
- environment-variable names such as `LINEAR_API_KEY` and `NTFY_TOKEN`, never their values

The recurring skill invocation executes `agent-worker-engine.ps1` relative to its own installed skill directory and passes the absolute SaaS config path. The SaaS manual wrapper accepts an explicit `-EnginePath` or a configured `LINEAR_DELIVERY_LOOP_ENGINE` path for attended diagnostics, validates that the engine/config schema versions are compatible, and fails closed if the engine cannot be resolved. It never downloads code at runtime or silently falls back to a copied implementation.

Project commands are fixed config arrays controlled by the repository. Never construct a shell command from Linear issue text. A second project should require only its own config, prompt rendering, thin wrapper, fixtures, and documentation. Extract a separate repository only after a real second-project constraint cannot be represented by the shared schema.

### 4.11 Durable stage and transition matrix

The engine accepts only the following stage progression and documented repair loops:

| Current stage | Success transition | Repair/wait transition |
|---|---|---|
| `idle` | `claimed`, or terminal no-op while remaining `idle` | reconciliation failure, no claim |
| `claimed` | `planning` | `paused` when contract changed after claim |
| `planning` | `design` when needed, otherwise `tasking` | `paused` for unresolved product/security/cost intent |
| `design` | `tasking` | `planning` for invalidated assumptions |
| `tasking` | `audit` | `planning` when scope no longer fits one issue |
| `audit` | `implementation` | `planning`/`tasking`, then re-audit; max three audit repair cycles |
| `implementation` | `local_validation` | same stage for bounded implementation repair |
| `local_validation` | `publish` | `implementation`; max three failed validation attempts |
| `publish` | `ci_wait` after PR/head is recorded | `implementation` for deterministic publish defects |
| `ci_wait` | `code_review` only for exact-head `Validate / validate` success | end heartbeat while pending; `implementation` on failure; `paused` at timeout/exhaustion |
| `code_review` | `runtime_qa` | `implementation`; max three review repair cycles |
| `runtime_qa` | `merge_ready` | `implementation`; max three QA repair cycles |
| `merge_ready` | `merge` | base-sync loop to `local_validation` when `main` advanced; `implementation` for conflicts/defects |
| `merge` | `post_merge` | reconcile ambiguous GitHub result before retrying |
| `post_merge` | `done` | `post_merge_repair` on exact-SHA smoke failure |
| `post_merge_repair` | `local_validation` for numbered repair PR | `paused` after three attempts or unsafe/ambiguous repair |
| `paused` | `claimed` only after the blocking label/decision is validly cleared | remain paused |
| `done` | terminal | no transition |

Transition invariants:

- `claimed` through pre-PR `publish` maps to Linear `In Progress`. Once a PR exists, `ci_wait` through `post_merge_repair` maps to `In Review`. `paused` maps to `Backlog` plus exactly the applicable stop label. `done` maps to Linear `Done`.
- Every `ApplyCheckpoint` uses compare-and-swap semantics over `stateRevision` and `expectedPreviousStage`. Replaying the same `transitionId` returns the already-recorded result; a different transition against an old revision fails closed.
- Persist the new local state atomically before or together with an idempotent external mutation record. If a crash happens between remote mutation and local commit, the next heartbeat re-reads Linear/GitHub and completes reconciliation instead of repeating blindly.
- A transient failure remains on the same stage and increments only that stage's transport counter. A behavior defect follows the repair transition and increments that stage's repair counter. Neither creates a new Linear issue unless the blocker is independently actionable.
- `ci_wait` is an active autonomous WIP state, not a pause: the issue remains `In Review + autonomous`, the run lease is released, and the next heartbeat resumes it before queue selection.
- A valid structured decision reply clears `needs-human`, moves the original issue to `Todo + autonomous`, and marks it as the preferred resume issue. The next heartbeat reclaims that issue before applying ordinary queue ordering, provided its contract and dependencies are still valid.
- A non-retryable engine/configuration failure before claim mutates no issue. After claim, it records evidence and moves the issue to `Backlog + needs-human` before releasing WIP.
- Any state/Linear/Git/GitHub disagreement that cannot be reconciled deterministically produces one `needs-human` escalation and no further mutation.

## 5. Data Model & Storage

No product database changes are required.

Local worker state is stored outside version control:

```text
.artifacts/harness/
  worker-state.json
  runs/
    <run-id>/
      request.json
      events.jsonl
      result.json
      validation.md
      stdout.log
      stderr.log
```

`worker-state.json` fields:

- engine, config, and state schema versions
- active run ID
- Codex task ID and latest scheduled-run ID when the product exposes them
- durable lease owner, heartbeat, and expiry
- issue identifier
- Linear issue UUID when available
- current stage, monotonically increasing `stateRevision`, last accepted `transitionId`, and expected previous stage
- last observed Linear state/labels/comment revision and reconciliation timestamp
- preferred resume issue and pending/consumed decision IDs
- branch and worktree path
- ordered primary/repair PR history, active PR kind/attempt, and merge commit history
- expected and observed base/current HEAD SHA plus the SHA bound to each review/QA gate
- CI required-check names, exact head SHA, status, first-observed time, deadline, and failure history
- attempt counters by stage
- code-review and runtime-QA gate results
- idempotent external-operation journal with operation ID, expected prior state, observed result, and completion status
- last heartbeat timestamp
- last result/outcome
- pending notification state

State rules:

- Write state atomically through a temporary file and rename.
- Keep secrets and tokens out of state and logs.
- Treat a stale state file as a reconciliation input, not proof that the issue is still owned.
- Reconstruct ownership from local state, Git branch/worktree, and current Linear state before resuming.
- Use compare-and-swap over revision/stage and return the already-recorded result for a replayed transition or operation ID.
- Retain completed run summaries for debugging; apply a bounded retention policy to verbose logs and worktrees.

## 6. Implementation Steps

### Phase 1: Shared workflow doctrine and orchestrators

1. Add `interactive-driver` with hard user gates and a prohibition on backlog selection.
2. Add `autonomous-driver` for one already-selected issue.
3. Convert `feature-driver` into a compatibility router/alias with a deprecation note; do not keep independent overlapping policy in three prompts.
4. Add `code-reviewer` for post-implementation diff review against the issue, approved plan, repo conventions, tenant/security boundaries, and test evidence.
5. Strengthen `qa` into a runtime acceptance tester. It must start or connect only to an asserted localhost/Development stack, use unique per-run ports/resource names and disposable test data, reject production credentials/endpoints, wait with bounded readiness timeouts, make real HTTP requests and/or use Playwright for user-visible flows, and record cleanup evidence. It must never reset the user's ordinary development database implicitly. Static plan review remains the auditor's job.
6. Update `planner`, `tasker`, and `auditor` only where needed to consume an explicit workflow mode and preserve their existing ownership boundaries.
7. Add the reusable `docs-as-code` skill and make `luchdom-docs` a Luchdom policy layer over it. Prefer a skill invoked by every docs-impacting task over a permanently separate docs agent; add a docs-writer agent later only if doc-heavy work proves it needs independent orchestration.
8. Update `task-audit-breakdown` and `multi-agent-delivery` so their producer/consumer contracts agree on the new per-workflow artifact folder, conditional `*-design.md`, the two entry routes, and shared handoffs; preserve explicit legacy-folder fallback for existing artifacts.
9. Update `qa-verification` together with `qa` so both enforce the same localhost/Development, isolated-resource, disposable-data, secret-rejection, bounded-readiness, and cleanup contract.
10. Add `linear-delivery-loop` with state, WIP, issue-contract, selection, claim, PR/merge, retry, escalation, notification, and result-schema references.
11. Add the reusable Codex Scheduled heartbeat prompt reference. It explicitly invokes `$linear-delivery-loop`, forbids nested `codex exec`, and treats the deterministic adapter as the only control-plane mutator.
12. Update the Codex, Claude, Copilot, and Cursor project templates so interactive delivery is the default and autonomous delivery must be explicitly invoked by the project harness, a Codex Scheduled prompt, or the user.

### Phase 2: Shared engine, build, and sync support

1. Implement the canonical engine and modules under `src/skills/linear-delivery-loop/scripts/` for config, leases/state, direct Linear GraphQL, deterministic transitions, Git/GitHub, ntfy, redaction, health, and post-merge recovery.
2. Add versioned project-config, prepared-iteration, checkpoint-result, and worker-state schemas plus fixture interfaces under the skill.
3. Add dependency-free shared-engine contract tests covering selection/WIP, overlapping leases, GraphQL failures, the complete transition matrix, revision/transition idempotency, crash recovery, exact-head CI, Git/PR gates, post-merge repair, notification delivery, and redaction.
4. Extend `scripts/build.py` validation to check:
   - unique agent names
   - referenced repo-managed skills exist
   - interactive-driver contains the explicit implementation gate
   - autonomous-driver does not pause on routine clarification stages
   - feature-driver compatibility routing points to the two current orchestrators
   - code-reviewer cannot mark runtime acceptance as passed
   - QA requires real behavior evidence for API/UI acceptance criteria
   - docs-as-code templates and required references exist
   - worker-result schema is valid JSON Schema
   - project-config and worker-state schemas are valid and version compatible
   - the engine, required modules, and fixture interfaces exist in the canonical skill
   - the Scheduled prompt explicitly invokes `$linear-delivery-loop` and does not invoke `codex exec` or depend on automatic agent selection
5. Extend sync verification so the new agents and complete skill runtime are installed for supported tools with one engine/schema version.
6. Add tests for build output, generated engine parity, a generic fixture wrapper's resolution/boundary behavior, version mismatch failure, and sync into temporary roots without touching real user homes. The real SaaS wrapper boundary is verified only after `DDW-SAS-003` creates it.
7. Add one local aggregate validation command for build and all shared-engine tests. Defer creation of a new hosted ai-config pipeline to the external-integration milestone; existing repository-hosted checks may continue to be consumed where already available.
8. Update `README.md` and root `AGENTS.md` to document the two entry-point workflows and the shared-engine/project-config boundary.

### Phase 3: SaaS Linear and documentation migration

1. Update `AGENTS.md` to name the modes `Interactive Delivery` and `Autonomous Delivery`, with exact routing and stop conditions.
2. Update `docs/WORKFLOW.md` with both flows and their state transitions.
3. Update `docs/HARNESS.md` so the autonomous gate is `Todo + autonomous` and blocked/human labels pause work.
4. Rewrite `docs/LINEAR.md` to define:
   - team key `SAAS`
   - regular-state meanings
   - label meanings
   - selection/resume predicates
   - manual claim behavior
   - the achievable issue template and `needs-refinement` behavior
   - local-first sequencing and `external-integration`
   - exactly which driver is allowed to mutate Linear and when it comments
   - issue kind and one-target-repository contract
   - non-autonomous program parents, repository-specific child dependencies, and manual-operational completion evidence
   - legacy `LUC-*` history note
5. Update `docs/DECISIONS.md` with `blocked`, `needs-human`, `needs-refinement`, structured Linear decision replies, ntfy escalation, retry exhaustion, PR, and automatic-merge rules.
6. Update `docs/QUALITY.md` with the shared definition of done, code-review/acceptance-test distinction, and `In Review`/`Done` policy.
7. Refresh `docs/AI-TOOLING.md` with the current Codex, Linear-notification, and ntfy state rather than the April workstation snapshot. Remove Slack and Telegram as configured workflow channels.
8. Add `docs/AUTOMATION.md` describing the dedicated Codex task, Worktree mode, the versioned heartbeat prompt, five-minute cadence, app-on requirement, Scheduled inbox, pause/archive controls, environment preflight, and Windows Task Scheduler fallback boundary.
9. Add `mkdocs.yml`, a docs index, deliberate navigation over durable `docs/` content, and a committed `requirements-docs.txt` pinned to `mkdocs==1.6.1`. Build with the repository-managed environment; do not rely on a floating global MkDocs install. Keep task evidence under `docs-ai/`; link relevant artifacts from durable pages instead of mixing every run log into wiki navigation.
10. Add documentation templates for how-to, concept, reference, ADR, runbook, and troubleshooting pages. A setting such as "how to configure X" belongs in a task-oriented how-to, with prerequisites, exact steps, verification, rollback, and troubleshooting.
11. Update `scripts/check-doc-drift.ps1` to reject `Ready for Codex` in operational docs, reject Slack/Telegram as configured notification routes, and require `Todo`, `autonomous`, the issue contract, and the `SAAS-` branch example.
12. Change future branch examples to `codex/SAAS-<number>-<short-name>`.
13. Replace the stale Slack decision workflow in `docs/HARNESS.md`, `docs/DECISIONS.md`, and `docs/AI-TOOLING.md`; retire `docs/SLACK-APPROVALS.md` after any still-valid generic guidance is moved to Linear/ntfy documentation.
14. Adopt `docs-ai/<SAAS-N-or-local-sequence>-<slug>/` for new plan/design/audit/task/review/QA/completion evidence, while preserving historical flat `docs-ai` content and adding the prefix migration note rather than mechanically rewriting history.
15. Add `@playwright/test` version `1.61.1` as a direct exact-version dev dependency in `apps/web/package.json` and `apps/web/package-lock.json` (no caret/range and no reliance on Next's optional peer or a global install). Invoke the repository-local binary through the documented test script/`npx playwright`, and make browser installation/cache preflight explicit.
16. Repair the existing SaaS validation gate before relying on it: make `scripts/validate-all.ps1 -CI` cross-platform instead of calling Windows-only `cmd`, require it to pass on the Ubuntu GitHub runner, and change `.github/workflows/validate.yml` to run for `pull_request` plus `push` limited to `main`. Preserve workflow/job identity `Validate / validate` and add a contract test for trigger/check identity.

### Phase 4: SaaS thin adapter

1. Add `automation/linear-delivery-loop.config.json` and validate it against the shared schema. Include SAAS identifiers, ordinary states/labels, branch templates, repo-relative paths, fixed validation commands, required checks, QA/docs hooks, local-first flags, and secret environment-variable names only. Lock the local validation command to `pwsh ./scripts/validate-all.ps1` and the required GitHub check identity to `Validate / validate`.
2. Add the thin `scripts/agent-worker.ps1` manual shim. It resolves an explicit/installed engine, verifies engine/config versions, forwards structured arguments, and contains no generic control-plane implementation.
3. Add SaaS fixtures and `scripts/test-agent-worker.ps1` to exercise the installed shared engine against project commands and policy without live mutations.
4. Verify that the shared engine accepts the SaaS config, uses direct Linear GraphQL from `LINEAR_API_KEY`, arbitrates the global WIP/lease, and rejects the user's primary checkout.
5. Configure clean-worktree post-merge validation, `scripts/validate-all.ps1`, repository-local Playwright runtime-QA hooks, exact required GitHub check `Validate / validate`, artifact paths, and branch naming through the project config.
6. Add the rendered `automation/codex-scheduled-linear-loop.md` prompt and documented Codex-app create/update procedure. The prompt explicitly invokes `$linear-delivery-loop`; no operating-system scheduler integration is added.
7. Add explicit pause, archive, and removal instructions for the Codex Scheduled task plus a repository kill switch. Preflight verifies the installed engine version and app-inherited secrets without printing them.

### Phase 5: Linear workspace administration and backlog migration

1. Create `blocked`, `needs-human`, `needs-refinement`, and `external-integration` labels.
2. Produce fully paginated dry-run inventories of (a) every `Backlog` or `Todo` issue carrying `autonomous` and (b) every issue currently in `Ready for Codex`, including parent/child/dependency relationships, executable-contract gaps, local/external classification, and the proposed regular-state/label mutation.
3. Apply the idempotent migration contract from section 3.4: remove `autonomous` from parents, broad work, and deferred external integrations; split/reuse bounded leaf issues; move only complete locally runnable unattended leaves to `Todo + autonomous`; map every `Ready for Codex` issue to `Backlog` or `Todo` with the appropriate labels.
4. Store raw redacted before/after exports under ignored `.artifacts/harness/operations/` and write concise durable Linear evidence. Preserve unrelated labels and add comments only to issues whose readiness/classification changed. Do not create a repository PR for the operations-only run.
5. Verify zero issues remain in `Ready for Codex` and no automation query/config/doc depends on it.
6. Only then remove `Ready for Codex` from the team workflow in the Linear UI.
7. Verify new issue identifiers and all newly generated branches/comments use `SAAS-*`.
8. Run both inventories again and assert zero `Ready for Codex` issues plus that every remaining `autonomous` issue is an executable leaf or an intentionally active autonomous WIP item; no `Backlog + autonomous` issue remains after migration.
9. Enable and test Linear desktop or mobile notifications for the configured owner, including one test `@mention` from an automation-authored comment.

For this dual-workflow implementation, task breakdown must create one non-autonomous program parent plus repository-specific code-bearing children for `ai-config` and `saas`, followed by manual-operational children for Linear administration and pilot enablement. Dependencies must prevent SaaS integration from starting before the required shared-engine version is merged and synced.

### Phase 6: Pilot and scheduled rollout

1. Run fixture tests and local dry runs until selection is deterministic.
2. Run a live Linear dry run that makes no mutations.
3. Select one bounded, safe, locally runnable leaf issue and set it to `Todo + autonomous`.
4. Create a dedicated Codex task rooted at SaaS in Worktree mode, explicitly invoke `$linear-delivery-loop`, and run a specific-issue pilot manually using `-Issue SAAS-N` before scheduling it.
5. Configure a private/authenticated ntfy topic and store its base URL, topic, and token outside the repository.
6. Review artifacts, Linear comments/mentions, a structured decision round trip, branch/worktree behavior, code review, live HTTP/Playwright QA, PR merge, post-merge validation, and ntfy delivery.
7. From that same Codex task, create a recurring five-minute task heartbeat using the reviewed versioned prompt. Do not use a standalone scheduled task or Windows Task Scheduler.
8. Confirm the computer-on/app-running prerequisite, environment preflight, Scheduled-inbox visibility, held-lease no-op behavior, and pause/kill-switch procedure.
9. Observe the first several scheduled iterations and tune lease, retry, prompt, and retention settings before adding more autonomous issues.

### Phase 7: Local-first backlog sequencing

Use the following milestone order when refining and ranking SaaS issues:

1. **Locally runnable product core:** authentication, tenant isolation, organization/user management, roles/permissions, primary product features, billing domain model, plans/entitlements, and a local fake or sandbox adapter where practical.
2. **Local operability and confidence:** deterministic seed data, developer setup, migrations, error handling, API integration tests, browser acceptance tests, and durable how-to/reference documentation.
3. **External integrations after the core works:** live billing-provider/webhook integration, hosted CI/CD, PostHog, AWS hosting, production secrets, monitoring, and other deployment infrastructure.

Split mixed issues at the boundary. For example, implement the billing model, entitlement rules, and fake provider locally in one or more bounded issues; track live provider credentials, webhooks, and production reconciliation as later `external-integration` issues.

## 7. Testing Strategy

### ai-config tests

- `python .\scripts\build.py`
- Existing marker-management tests.
- New build validation tests for agent names, skill references, schemas, and required workflow gates.
- Temporary-directory sync tests for Codex, Claude, Copilot, and Cursor outputs without touching user homes.
- Golden/semantic assertions proving:
  - interactive-driver stops before implementation
  - autonomous-driver continues through routine stages
  - both reuse the same specialist ownership contracts
  - auditor, code-reviewer, and runtime QA have distinct gates
  - every issue with docs impact invokes the docs-as-code contract
  - generated adapters preserve the canonical instructions
  - the Codex Scheduled prompt invokes `$linear-delivery-loop` explicitly and never nests `codex exec`
  - generated/installed skill copies include the same engine modules and schema version
  - project wrappers cannot override engine-owned transition, Linear, Git/GitHub, notification, or redaction behavior
- CI runs the same build and test commands used locally.

### SaaS worker contract tests

Use fixture-backed, mutation-free tests for:

1. Missing, empty, invalid, or wrong-workspace `LINEAR_API_KEY` fails closed before mutation and never leaks secret material.
2. GraphQL `200` responses containing errors, pagination, rate limits, transient retries, and partial data follow the documented adapter policy.
3. Adapter mutations preserve unrelated labels, reconcile ambiguous writes by re-reading, and remain idempotent across restart.
4. Empty queue returns success without notification.
5. Manual `In Progress` or `In Review` returns `manual-wip-present` and claims nothing.
6. Autonomous `In Progress` issue matching local state is resumed.
7. Autonomous `In Review` resumes review, QA, merge, or post-merge validation from the durable stage.
8. More than one active issue fails closed and sends one reconciliation notification.
9. `Todo + autonomous` issue is selected and claimed only when global WIP is empty.
10. `Backlog + autonomous` is ignored.
11. `Todo` without `autonomous` is ignored.
12. `blocked`, `needs-human`, `needs-refinement`, and deferred `external-integration` issues are ignored.
13. Missing issue-contract fields return the issue to `Backlog + needs-refinement` with a bounded split proposal.
14. Parent/epic selection is rejected when an executable child is required.
15. Concurrent or overlapping Codex heartbeats leave only one valid lease owner; a stale lease is reclaimed only after external-state reconciliation.
16. Stale state reconciles against Linear, Git, and PR state before resuming.
17. Interrupted or missed heartbeat resumes from the last accepted durable stage without requiring a conversation/session identifier.
18. Transient failure increments retry state without creating a new issue.
19. Independent blocker creates at most one achievable linked follow-up.
20. Retry exhaustion produces one durable Linear comment/mention and one idempotent ntfy escalation when configured.
21. Code-review failure and QA failure return to implementation without merging.
22. A passed branch validation without merge cannot produce `Done`.
23. Merge plus failed post-merge smoke records the exact failing SHA, remains `In Review`, and opens or resumes the first same-issue repair branch/PR without creating another Linear issue.
24. Only an exact, unconsumed decision reply from the configured Linear owner resumes a `needs-human` issue.
25. ntfy send failures do not corrupt Linear or worker state and are retried idempotently.
26. Invalid structured output fails closed without marking the issue Done.
27. Worktree paths cannot escape the configured root.
28. Secrets are redacted from logs, Linear comments, ntfy messages, and committed artifacts.
29. Scheduled/unattended mode fails preflight when ntfy is disabled, absent, or cannot pass an authenticated delivery probe; dry-run and attended diagnostic exceptions are explicit.
30. Specialist output cannot directly stage, commit, push, open/update a PR, merge, or write to `main`; only the deterministic repository adapter can emit those mutations.
31. Removing `autonomous`, adding a stop label, changing issue ownership, or changing the PR head after a gate prevents the next mutation and forces reconciliation.
32. Unexpected files, unrelated pre-existing changes, force-push attempts, direct-main updates, and stale or missing required checks fail closed.
33. A normal successful autonomous path produces one primary issue branch, one primary PR, a squash merge, and post-merge validation of the exact GitHub merge SHA.
34. The adapter never launches `codex exec`; the active Codex Scheduled heartbeat performs orchestration through `$linear-delivery-loop`.
35. Closing the Codex app or making the project unavailable causes no external mutation; a later heartbeat reconciles and resumes from the last accepted checkpoint.
36. Every post-merge repair attempt starts from current `main`, uses `codex/SAAS-N-repair-<attempt>`, reruns every gate, appends ordered PR/merge history, and keeps the original Linear issue as the only WIP item.
37. No autonomous outcome can issue a GitHub revert, create a revert commit, or treat a failed post-merge SHA as `Done`.
38. Three failed post-merge repairs move the original issue to `Backlog + needs-human`, release WIP, and send one idempotent decision escalation containing the complete history.
39. Backlog migration removes `autonomous` from parents/broad items and deferred external integrations, reuses existing children when equivalent, and never duplicates a split on rerun.
40. Candidate ordering is Urgent/High/Normal/Low/None, then oldest `createdAt`, then numeric identifier, after complete pagination and eligibility/dependency filtering.
41. A SaaS-configured worker rejects an otherwise eligible issue whose contract targets `ai-config`, multiple repositories, or no repository.
42. A program parent remains non-autonomous and outside active WIP; its code-bearing children each map to one repository/primary PR and obey blocking dependencies.
43. A manual-operational issue cannot be autonomously claimed and reaches `Done` only after its explicit non-PR evidence contract passes.
44. One heartbeat can progress the same issue across planning, tasking, audit, implementation, review, QA, merge, and post-merge checkpoints without waiting for another five-minute tick.
45. Completion or pause releases the lease and ends the heartbeat; selection is not run again, so one heartbeat never claims two issues.
46. A healthy lease makes an overlapping heartbeat exit `10`; an expired but ambiguous lease fails closed instead of being stolen.
47. A checkpoint with the expected revision/stage applies once; replaying its transition ID is a no-op, while a different transition against the stale revision fails closed.
48. A crash before or after a Linear/GitHub mutation is reconciled through the external-operation journal without duplicating the comment, label change, PR, or merge.
49. Pending decision reconciliation runs before queue selection; only an exact current reply reclaims the same issue, while malformed, duplicate, stale, or unauthorized replies leave it paused.
50. A missing or pending `Validate / validate` check for the exact PR head enters `ci_wait`, releases the lease, and resumes the same issue without claiming another.
51. A required check still missing/pending after 30 minutes pauses with `needs-human`; canceled, skipped, timed-out, and failed checks never pass.
52. Each failed exact-head CI result consumes one CI repair attempt; a repaired head gets its own timer, and three failed heads exhaust the stage.
53. If `main` advances after a gate, the adapter merges current `origin/main` into the issue branch without rebase/force, invalidates stale gates, and reruns local validation, affected runtime QA, and exact-head CI.
54. Review/QA evidence commits cannot silently reuse a prior SHA approval: the final head gets a code-review attestation, docs/local validation, CI, and runtime-QA rerun or an explicit evidence-only reuse decision.
55. Runtime QA rejects non-localhost/non-Development targets, production-like secrets, shared destructive databases, unbounded readiness waits, and missing cleanup evidence.
56. Documentation drift rejects operational `Ready for Codex`, Slack, Telegram, and current `LUC-*` examples while preserving explicitly marked history.
57. `requirements-docs.txt` pins `mkdocs==1.6.1`, and `apps/web/package.json`/lockfile pin direct dev dependency `@playwright/test` to exactly `1.61.1`; tests do not fall back to floating global or optional-peer installations.
58. The SaaS workflow fails contract validation unless `pwsh ./scripts/validate-all.ps1 -CI` is cross-platform/passable on Ubuntu, feature heads run once through `pull_request`, pushes are limited to `main`, and the workflow/job/check identity is `Validate / validate`; project config also fails when its local command/check identity differs.

### SaaS repository validation

- `pwsh ./scripts/check-doc-drift.ps1`
- `pwsh ./scripts/validate-all.ps1`
- `mkdocs build --strict`
- Conflict-marker scan before claim and before handoff.
- Dry-run worker execution with fixture and live read-only Linear inputs.
- For API criteria, start the real local services, wait on a health/readiness endpoint, issue real HTTP requests, and assert status, payload, persistence, authorization, and tenant isolation where relevant.
- For UI criteria, use Playwright against the running application to execute the user flow, assert visible outcomes, check keyboard/focus behavior and obvious accessibility failures, and retain screenshots/traces only when useful.
- Assert localhost and Development mode, allocate unique per-run ports/resource names, use disposable data, reject production credentials, and never reset the user's normal development database implicitly.
- Prefer deterministic setup/teardown, bounded explicit readiness checks, and cleanup evidence; do not use arbitrary fixed sleeps.
- One manual autonomous pilot that verifies branch, worktree, artifacts, code review, live API/browser QA, docs, PR merge, post-merge validation, and state transitions end to end.

## 8. Observability / Debuggability

- Generate a unique run ID for every supervisor claim or resume operation.
- Emit structured JSONL events for selection, claim, worktree, Codex stage, validation, Linear mutation, notification, and cleanup.
- Record durations, exit codes, retry counts, issue ID, branch, worktree, stage, and final outcome.
- Keep one concise Linear comment at claim, blocker/approval, review handoff, and completion; do not post a comment every five minutes.
- Treat Linear comments/mentions as the durable notification record. Require ntfy delivery attempts for actionable unattended escalations, record delivery and retry status, and never treat ntfy as the source of truth for the decision itself.
- Include artifact paths and a short diagnostic summary in blocker notifications without exposing secrets.
- Add a `-DryRun` report explaining exactly why each candidate was selected or rejected.
- Include the deterministic rank tuple for every eligible candidate and the proposed backlog-migration action for every audited `Backlog`/`Todo + autonomous` issue.
- Add a health/status command that reports lock owner, active run, last successful iteration, last failure, and next retry.

## 9. Rollout Plan

1. Merge shared doctrine, orchestrators, skill, build validation, and tests in `ai-config`.
2. Build and sync the new adapters locally, verifying installed files.
3. Repair the SaaS cross-platform validation workflow/check, then update operational docs, pinned tooling, and doc-drift checks.
4. Land and validate the SaaS supervisor/config/prompt in disabled-by-default mode; run the complete fixture suite and live read-only dry run.
5. Add labels, inventory both `Backlog`/`Todo + autonomous` and every `Ready for Codex` issue, validate executable contracts, and migrate issues to regular states/labels.
6. Verify zero issues remain in `Ready for Codex`, then remove that workflow state manually.
7. Configure notifications and run one explicit attended issue pilot.
8. Create the five-minute heartbeat from the dedicated Codex task, verify the Scheduled inbox and app-on prerequisite, and enable it with a global kill switch and one global WIP slot across manual and autonomous work.
9. Review early runs and convert recurring manual recovery into tests or policy updates.
10. Consider multi-issue concurrency only after the single-issue loop is stable and observable.

Rollback:

- Pause or remove the Codex Scheduled heartbeat and archive its dedicated task when no longer needed.
- Remove `autonomous` from all issues or set the worker kill switch.
- Leave ordinary Linear states and interactive delivery unaffected.
- Preserve run artifacts for diagnosis.
- Revert shared agent/skill changes through normal source-first ai-config build/sync if needed.

## 10. Risks & Mitigations

- **Risk: interactive and autonomous workers edit the same issue.**
  - Mitigation: interactive claim removes `autonomous`; supervisor checks global `In Progress`/`In Review` WIP before selection; one local lock; isolated worktrees.
- **Risk: mode confusion lets interactive work cross the approval gate.**
  - Mitigation: separate entry-point agents and semantic tests for their stop/continue contracts.
- **Risk: autonomous worker selects an epic or vague issue.**
  - Mitigation: use `Todo + autonomous`, the executable issue contract, `needs-refinement`, dependency checks, and leaf-task validation.
- **Risk: legacy `Backlog + autonomous` parents or external-integration issues become an accidental future queue.**
  - Mitigation: audit both Backlog and Todo before rollout, remove `autonomous` from non-executable/deferred work, split idempotently into linked leaves, and assert no Backlog-autonomous residue after migration.
- **Risk: status deletion creates an intake gap.**
  - Mitigation: update worker/docs and migrate issues before removing `Ready for Codex`.
- **Risk: old `LUC-*` references become misleading.**
  - Mitigation: update operational docs and future examples; retain historical artifacts with a dated prefix-migration note.
- **Risk: a failed run creates ticket spam.**
  - Mitigation: retry the original issue first; create only one separately actionable, deduplicated child blocker.
- **Risk: stale local state resumes the wrong issue or branch.**
  - Mitigation: reconcile local state with Linear and Git on every iteration; fail closed on disagreement.
- **Risk: five-minute scheduling creates overlapping Codex processes.**
  - Mitigation: atomically acquire a renewable durable lease at `PrepareIteration`, protect each adapter call with a short mutex, and return exit `10`/no-op to later heartbeats while the lease is healthy.
- **Risk: a long implementation or QA command outlives the lease and another heartbeat starts conflicting work.**
  - Mitigation: derive lease duration from command limits, renew around every long operation/checkpoint, require external-state reconciliation before reclaim, and fail closed when prior-run liveness is ambiguous.
- **Risk: worktrees accumulate or conflict with user work.**
  - Mitigation: use a heartbeat on one dedicated Codex task in Worktree mode rather than standalone scheduled runs, validate worktree identity on every checkpoint, bound auxiliary validation-worktree retention, and archive the task when decommissioned.
- **Risk: local automation silently stops because the computer is off, the Codex app is closed, or the project path is unavailable.**
  - Mitigation: document that phase 1 is app-dependent, expose last-heartbeat health in the Scheduled inbox and adapter status, reconcile safely on return, and consider Windows Task Scheduler or a hosted runner only if 24/7 execution becomes a real requirement.
- **Risk: automation runs with excessive permissions.**
  - Mitigation: keep state-changing Git/GitHub commands in the deterministic repository adapter, scope authorization to `autonomous` plus the active issue, use least-privilege agent sandbox/config, and prohibit force-push/direct-main/cloud/destructive actions.
- **Risk: an LLM bypasses review or merges a stale/unrelated diff.**
  - Mitigation: specialists return proposals only; the supervisor reconciles the real manifest, re-checks Linear authorization and exact SHAs, polls required GitHub checks itself, and performs only a gated squash merge.
- **Risk: Linear or ntfy notifications are missed.**
  - Mitigation: assign and `@mention` the configured owner, keep the request and reply in Linear, require ntfy for unattended actionable escalation until a separate Linear actor exists, retry ntfy idempotently, and include undelivered alerts plus `needs-human`/`blocked` queues in worker health.
- **Risk: an ordinary Linear comment is mistaken for a product decision.**
  - Mitigation: require a unique decision ID, exact option syntax, configured-author verification, request-time ordering, and one-time consumption before resuming.
- **Risk: autonomous merge lands behavior that compiles but does not work.**
  - Mitigation: primary PR per issue, independent code-review gate, live HTTP/Playwright acceptance QA, docs verification, and exact-SHA post-merge smoke before `Done`; a failure stays on the same issue and enters bounded repair.
- **Risk: post-merge recovery causes ticket/WIP duplication or an unsafe automatic rollback.**
  - Mitigation: keep the original issue as the sole WIP record, permit only numbered repair PRs with all gates rerun, cap attempts at three, and require the user for any revert or ambiguous repair.
- **Risk: documentation artifacts become noisy and impossible to navigate.**
  - Mitigation: keep per-task evidence in `docs-ai`, keep curated durable guidance in `docs`, use templates and MkDocs navigation/search, and link rather than duplicate content in Linear.
- **Risk: shared automation is extracted too early into another repository.**
  - Mitigation: keep reusable policy in `ai-config` and thin project configuration in SaaS; extract only from demonstrated second-project variation.
- **Risk: SaaS duplicates or drifts from the shared engine.**
  - Mitigation: prohibit generic logic in the wrapper, validate engine/config versions, test generated/installed parity, and fail closed rather than copying or downloading a fallback runtime.
- **Risk: local and CI definitions of done diverge.**
  - Mitigation: lock local validation to `pwsh ./scripts/validate-all.ps1`, require existing check `Validate / validate`, and bind both to the exact PR head.
- **Risk: the private-repository plan cannot enforce branch protection/rulesets, or the required check name drifts.**
  - Mitigation: first repair `validate-all.ps1 -CI` to run cross-platform on Ubuntu and make `.github/workflows/validate.yml` emit one PR-head run (`pull_request`, plus `push` only for `main`); then make the deterministic adapter the fail-closed enforcement point, validate workflow/event/job/check/head/run-attempt identity, and pause rather than merge when it is absent, stale, duplicated ambiguously, or failing.
- **Risk: `main` advances after review or QA and invalidates the approved merge base.**
  - Mitigation: compare exact base/head SHAs immediately before merge; merge current `origin/main` into the issue branch without rebase/force and rerun invalidated gates.
- **Risk: committed review/QA evidence changes the head it claims to approve.**
  - Mitigation: commit evidence before the final gated head, verify evidence-only deltas, and store the final SHA-bound attestations in durable state and Linear without another branch mutation.
- **Risk: browser or documentation tooling changes underneath the workflow.**
  - Mitigation: pin `mkdocs==1.6.1` and direct dev dependency `@playwright/test` to `1.61.1` in committed lock/config files and prohibit global/optional-peer fallback.
- **Risk: scheduled runtime QA damages a developer or non-local environment.**
  - Mitigation: require localhost/Development assertions, unique resources, disposable data, production-secret rejection, bounded readiness, and cleanup evidence; never reset the ordinary development database implicitly.
- **Risk: stale Slack, Telegram, flat-artifact, or `LUC-*` operational guidance sends agents down the wrong path.**
  - Mitigation: migrate current docs to Linear + ntfy + Codex Scheduled visibility, retire the Slack approvals page, enforce the new workflow-folder convention, and preserve old forms only as clearly marked history.
- **Risk: one Linear issue edits ai-config and SaaS, producing ambiguous ownership, branches, and Done evidence.**
  - Mitigation: use a non-autonomous parent, require one repository key and primary PR per code-bearing child, order repositories with blocking dependencies, and track non-code administration as manual-operational children.

## 11. Open Questions / Decisions and Defaults

All planning choices and audit resolutions are locked. No open questions or blocking clarifications remain; this plan is ready for task breakdown and the required post-task independent audit.

1. **Done policy:** for code-bearing work, move to `In Review` when the primary PR exists and to `Done` only after the latest merge to `main` and a successful exact-SHA post-merge smoke check. A failed smoke check remains on the original issue and enters bounded repair. A manual-operational issue uses its explicit evidence contract and never creates a fake PR.
2. **Interactive marker:** label-less is the default interactive mode; do not add a `manual` label unless reporting later requires it.
3. **Merge policy:** always use a PR and squash merge. Interactive work is merged by the user or on explicit request. `autonomous` authorizes the deterministic supervisor to perform issue-scoped branch/commit/push/PR operations and automatic squash merge only after issue-contract, code-review, runtime-QA, docs, exact-head checks, and authorization gates pass with no human decision pending.
4. **Notification:** Linear assignment, `@mention`, and structured reply form the durable decision record. Until a separate Linear automation actor exists, ntfy is required to attract attention to unattended actionable escalations and links back to Linear. The Codex Scheduled inbox is the run-observability surface; Linear native notifications are opportunistic additions.
5. **WIP:** exactly one project issue may be in `In Progress` or `In Review`. Resume it when autonomous; idle when manual.
6. **Issue readiness:** one bounded, observable, locally testable outcome per executable issue; otherwise use `Backlog + needs-refinement`.
7. **Product sequencing:** locally runnable product core and tests/docs before live CI/CD, PostHog, AWS, and other external integrations.
8. **Documentation:** keep full workflow evidence under `docs-ai`, curated technical guidance under `docs`, and use MkDocs in the same repository for local search and later GitHub Pages publishing.
9. **Retry budget:** default to three repair attempts per stage before `needs-human` or non-retryable failure handling.
10. **Schedule:** one recurring five-minute heartbeat attached to a dedicated SaaS Codex task in Worktree mode, explicitly invoking `$linear-delivery-loop`; one durable lease and one global WIP slot. No Windows Task Scheduler in phase 1.
11. **Historical identifiers:** do not rewrite old `docs-ai` history; add a dated note that `LUC-*` became `SAAS-*` on 2026-07-16.
12. **Legacy feature-driver:** retain as a compatibility router for one migration cycle, then remove after all generated/installed references use the new entry points.
13. **Linear transport:** the deterministic adapter uses Linear's direct GraphQL API with the personal key supplied only through `LINEAR_API_KEY`; Codex MCP is not part of the deterministic control plane.
14. **Git/GitHub authority:** specialist agents edit and validate only. The deterministic repository adapter is the sole automated Git/GitHub mutator; it enforces the scoped `autonomous` authorization and performs the gated PR/squash-merge workflow.
15. **Automation surface:** Codex Scheduled owns timing, task context, skill invocation, and the Scheduled inbox. `$linear-delivery-loop` owns orchestration and delegation. `agent-worker.ps1` owns deterministic checkpoints and never launches a nested Codex process.
16. **Post-merge recovery:** keep the original issue in `In Review`, create numbered repair branches/PRs from current `main`, rerun every gate, and allow at most three attempts. Never auto-revert `main`; exhaustion becomes `Backlog + needs-human` with ntfy escalation.
17. **Reuse boundary:** canonical engine code and schemas live inside the `ai-config` `linear-delivery-loop` skill. SaaS contains only config, a rendered prompt, fixtures, docs, and a thin manual wrapper; no separate automation repository yet.
18. **Backlog and queue:** audit all `Backlog`/`Todo + autonomous` issues before rollout. Parents/broad work become `Backlog + needs-refinement` without `autonomous`; external work becomes `Backlog + external-integration` without `autonomous`; only complete local leaves become `Todo + autonomous`. Claim order is priority, oldest creation time, then identifier.
19. **Cross-repository work:** use a non-autonomous Backlog parent and ordered children. Every code-bearing child targets one repository and one primary PR; manual Linear/admin work uses non-autonomous operational children with evidence-based completion.
20. **Heartbeat scope:** five minutes is only the wake-up cadence. Each heartbeat works on at most one issue but continues across every routine stage until completion, pause/human input, retry exhaustion, non-retryable failure, or Codex interruption; it never claims a second issue before ending.
21. **CI gate:** local authority is `pwsh ./scripts/validate-all.ps1`; CI runs `pwsh ./scripts/validate-all.ps1 -CI` cross-platform on Ubuntu. Autonomous merge requires the latest unambiguous exact-head `pull_request` run of `.github/workflows/validate.yml`, job/check `Validate / validate`; feature branches do not also receive a push run. Pending/missing checks enter `ci_wait`; the per-head deadline is 30 minutes; canceled/skipped/timed-out/failed are failures; three failed CI heads exhaust the stage.
22. **Base drift:** immediately before merge, compare the passing base/head with current `origin/main`. If `main` advanced, merge it into the issue branch without rebase/force and rerun local validation, affected runtime QA, and exact-head CI before squash merge.
23. **Durable state:** use the explicit transition matrix, compare-and-swap state revisions, replay-safe transition IDs, an idempotent external-operation journal, and reconciliation before retry. Linear/PR/CI identity is supervisor-observed, never model-owned.
24. **Decision resume:** pending `Backlog + needs-human` decisions are reconciled before queue selection. An exact authorized reply restores the same issue as preferred `resume-pending`; malformed, stale, duplicate, or unauthorized replies do nothing.
25. **Runtime QA isolation:** scheduled acceptance tests run only against asserted localhost/Development resources with unique names/ports, disposable data, bounded readiness, production-secret rejection, and cleanup evidence. The user's ordinary development database is never reset implicitly.
26. **Evidence ordering:** commit workflow evidence before the final gated head. Final review/QA attestations bind to that exact head in durable state and Linear; any executable change after a gate invalidates it.
27. **Documentation layout:** new evidence uses `docs-ai/<SAAS-N-or-local-sequence>-<slug>/`; conditional UI design artifacts use `*-design.md`; historical flat artifacts remain untouched. Durable guidance stays in searchable MkDocs-backed `docs/`.
28. **Notification cleanup:** configured channels are Linear for durable state/decisions, ntfy for unattended attention, and Codex Scheduled for run visibility. Telegram is not used, Slack workflow guidance is removed, and `docs/SLACK-APPROVALS.md` is retired.
29. **Tool pins:** commit `requirements-docs.txt` with `mkdocs==1.6.1` and direct exact dev dependency `@playwright/test` version `1.61.1` plus the npm lockfile. Repository-local tools are mandatory.
30. **Hosted pipeline boundary:** repair and consume the SaaS repository's existing `Validate / validate` check because it is already the merge gate, but do not create new hosted ai-config pipeline infrastructure in this implementation; that remains in the external-integration milestone.
31. **Bootstrap delivery:** the `DDW-*` program creates its own adapter, so after explicit `Implement` approval its code children use Interactive Delivery with root/human-controlled, conversation-authorized Git/PR mutations. Specialist subagents remain non-mutating. The exception ends once `DDW-SAS-003` is merged and verified.
32. **Operations evidence:** raw migration/pilot/schedule evidence is redacted and kept under ignored `.artifacts/harness/operations/`, with concise durable Linear readback. Operations-only issues create no repository PR; `DDW-SAS-001` owns the reusable procedure/schema, and a later repository report requires a separate code-bearing docs issue.
33. **Custom-state removal:** fully paginate and migrate every issue in `Ready for Codex`, verify the state has zero issues and zero operational references, retain before/after rollback evidence, and only then delete it manually.

## 12. Audit Resolution Ledger

The historical independent audit remains unchanged as the record of issues found. This plan revision resolves every planning finding as follows:

| Audit finding | Locked resolution |
|---|---|
| Linear transport/authentication and actor ambiguity | Direct Linear GraphQL using environment-only `LINEAR_API_KEY`; startup identity/workspace preflight; owner-authored decision validation; ntfy required until a separate automation actor exists. |
| Paused decisions unreachable | Pre-selection pending-decision reconciliation and preferred same-issue `resume-pending`, with malformed/stale/duplicate/unauthorized tests. |
| Autonomous Git authorization conflict | Narrow canonical exception for `autonomous`; deterministic adapter alone may perform issue-scoped branch/commit/push/PR/squash merge; interactive authority remains explicitly gated. |
| Merge integrity without branch protection | Exact-head `Validate / validate`, exact base/head reconciliation, mergeability/authorization rechecks, squash merge, and fail-closed adapter enforcement. |
| Model-owned control-plane fields | Supervisor-owned checkpoint envelope and fresh Linear/Git/GitHub observations; agent output restricted to nested proposals/evidence. |
| Backlog migration scope | Audit all `Backlog` and `Todo` issues carrying `autonomous`, split/reuse executable leaves, remove eligibility from parents/external work, and verify no residue. |
| Missing task artifact | This locked plan proceeds next to repository-specific task breakdown; implementation remains blocked until tasks receive an independent audit. |
| Runtime-QA safety | Localhost/Development-only, isolated per-run resources, disposable data, production-secret rejection, bounded readiness, and cleanup proof. |
| Evidence changes approved SHA | Commit reports before final gates; bind final attestations to exact head in state/Linear and invalidate/re-run when executable content changes. |
| Non-interactive invocation | Codex Scheduled prompt explicitly invokes `$linear-delivery-loop`; valid short PowerShell checkpoint commands; no nested `codex exec` or unsupported agent selector. |
| Non-deterministic selection | Complete pagination/filtering followed by priority, oldest `createdAt`, and numeric identifier ordering with dry-run rejection evidence. |
| Hosted CI before local-first | Defer new ai-config hosted pipeline; use local aggregate validation and only consume the already-existing SaaS merge check. |
| Canonical artifact naming/section drift | `Open Questions / Decisions and Defaults`, explicit none remaining, conditional `*-design.md`, and per-workflow evidence folders. |
| Post-merge failure policy | Same issue, numbered repair PRs from current `main`, all gates repeated, maximum three, never auto-revert, then `Backlog + needs-human`. |
| Cross-repository ambiguity | Non-autonomous program parent plus ordered single-repository code children and evidence-based manual-operational children. |
| Shared/reusable boundary | Canonical engine/schemas inside the ai-config skill; SaaS config/wrapper remains thin; no new repo until a second project proves the need. |
| Documentation/tooling drift discovered during clarification | Remove Slack/Telegram routes and current `LUC-*` examples, retire Slack approvals doc, pin MkDocs/Playwright, and enforce through drift/contract tests. |
| Bootstrap cannot use the adapter it is building | Explicit Interactive Delivery bootstrap exception for `DDW-*` children; root/human Git/PR authority after `Implement`; deterministic adapter mandatory after SaaS integration. |
| Current SaaS CI is Windows-specific and duplicate-prone | `DDW-SAS-002` owns cross-platform `-CI`, Ubuntu proof, `pull_request` plus main-only push triggers, and deterministic workflow/run-attempt identity. |
| `Ready for Codex` issues omitted from deletion inventory | Separate fully paginated custom-state inventory, regular-state/label mapping, zero-count proof, and rollback evidence before manual deletion. |
| Manual migration evidence ownership conflict | Raw redacted local operation artifacts plus concise Linear evidence; no fake PR; reusable procedure belongs to `DDW-SAS-001`. |
| Reusable task/QA contracts omitted | `DDW-AIC-001` owns `task-audit-breakdown` artifact routing and `qa-verification` runtime-safety parity with semantic tests. |

**Audit status:** PASS on 2026-07-17 with no remaining actionable P1/P2 findings. The audited Linear hierarchy was created in `Backlog` as `SAAS-44` through `SAAS-55`; implementation remains gated pending explicit `Implement` approval.

## 13. Sources Consulted

### ai-config

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\planner.md`
- `C:\dev\luchdom\ai-config\src\agents\tasker.md`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\task-audit-breakdown\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\SKILL.md`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py`
- `C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md` (fresh Codex manual fetched 2026-07-16)

### SaaS

- `C:\dev\luchdom\saas\AGENTS.md`
- `C:\dev\luchdom\saas\README.md`
- `C:\dev\luchdom\saas\docs\HARNESS.md`
- `C:\dev\luchdom\saas\docs\WORKFLOW.md`
- `C:\dev\luchdom\saas\docs\LINEAR.md`
- `C:\dev\luchdom\saas\docs\DECISIONS.md`
- `C:\dev\luchdom\saas\docs\QUALITY.md`
- `C:\dev\luchdom\saas\docs\AI-TOOLING.md`
- `C:\dev\luchdom\saas\docs\SLACK-APPROVALS.md`
- `C:\dev\luchdom\saas\.github\workflows\validate.yml`
- `C:\dev\luchdom\saas\apps\web\package.json`
- `C:\dev\luchdom\saas\apps\web\package-lock.json`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`

### Live Linear context verified on 2026-07-16

- Team/project name: `SaaS Boilerplate`
- Team key and current issue prefix: `SAAS`
- Existing relevant label: `autonomous`
- Current workflow still includes `Ready for Codex`, which must be removed manually after migration

### Official external documentation verified on 2026-07-16

- [Linear GraphQL getting started, endpoint, personal-key authentication, and error handling](https://linear.app/developers/graphql)
- [Linear API pagination](https://linear.app/developers/pagination)
- [Linear API rate limiting](https://linear.app/developers/rate-limiting)
- [Codex/ChatGPT notifications](https://learn.chatgpt.com/docs/notifications)
- [Codex/ChatGPT scheduled tasks](https://learn.chatgpt.com/docs/automations)
- [Linear notifications](https://linear.app/docs/notifications)
- [ntfy publishing and notification actions](https://docs.ntfy.sh/publish/)
- [MkDocs configuration and built-in search](https://www.mkdocs.org/user-guide/configuration/#search)
- [MkDocs deployment to GitHub Pages](https://www.mkdocs.org/user-guide/deploying-your-docs/#github-pages)
- [MkDocs package metadata (`1.6.1` verified 2026-07-16)](https://pypi.org/project/mkdocs/)
- [Playwright package metadata (`@playwright/test` `1.61.1` verified 2026-07-16)](https://www.npmjs.com/package/@playwright/test)
