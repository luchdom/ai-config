# Dual Interactive and Autonomous Delivery Workflows — Execution Tasks

## Task document status

- Plan: `2026-07-16-dual-delivery-workflows-plan.md`
- Workflow artifact: `001-dual-delivery-workflows-2026-07-16`
- Tasking date: 2026-07-17
- Product design: not required; this is workflow, automation, documentation, and test infrastructure rather than product UI work
- Implementation status: **not approved and not started**
- Independent audit: **PASS** on 2026-07-17; no remaining actionable P1/P2 findings
- Linear hierarchy: created in `Backlog` as parent `SAAS-44` with children `SAAS-45` through `SAAS-55`; readback verified parentage, blockers, and absence of `autonomous`
- Required next gate: explicit user `Implement` approval
- Implementation approval: this `Task it out` request authorizes creation of the planning issue hierarchy only. After a passing audit, wait for the user's explicit `Implement` instruction before changing code, installing/syncing the runtime, moving an implementation child to `Todo`, migrating Linear workflow/backlog state, creating the pilot, or enabling the schedule

## Audit notes

The locked plan supplies the architecture, contracts, transition matrix, test strategy, rollout, rollback, and risk decisions required for tasking. No blocking product, design, or architecture decision remains.

The work is split into:

1. one non-autonomous Linear program parent;
2. five ordered, code-bearing `ai-config` children, each targeting only `ai-config` and one primary PR;
3. three ordered, code-bearing `saas` children, each targeting only `saas` and one primary PR;
4. three non-autonomous `manual-operational` children for Linear administration, notification/pilot validation, and scheduled enablement;
5. manual parent closure after every child and the integration acceptance contract pass.

This split preserves the source-of-truth boundary: reusable agents, skills, schemas, and deterministic control-plane code live in `ai-config`; SaaS owns project policy, pinned runtime-QA tooling, fixed commands, project configuration, fixtures, and the thin wrapper. No executable child edits both repositories.

Confirmed constraints carried into every task:

- `Ready for Codex` is not an execution state and is removed only after the replacement selection logic and docs are merged.
- Autonomous eligibility is ordinary state `Todo` plus label `autonomous`.
- There is one global WIP slot across `In Progress` and `In Review`.
- Every code-bearing child has one target repository, one base branch, and one primary PR.
- State-changing Linear, Git, and GitHub operations belong to the deterministic adapter, not specialist agents.
- A code-bearing issue reaches `Done` only after squash merge and exact-merge-SHA post-merge validation.
- The existing SaaS local authority is `pwsh ./scripts/validate-all.ps1`; the required GitHub check identity is `Validate / validate`.
- The five-minute wake-up belongs to Codex Scheduled; phase 1 adds no Windows Task Scheduler integration and launches no nested `codex exec` process.
- Linear is the durable decision record, ntfy is the required unattended attention route, and Codex Scheduled is run visibility. Telegram and Slack are not part of the workflow.
- Locally runnable product work precedes external integrations after this program is enabled.

## Linear program map

The following audited Linear records were created on 2026-07-17. Preserve both the stable task ID and assigned `SAAS-N` in repository evidence, branches, PRs, and completion summaries.

| Stable ID | Linear issue | Linear kind | Target repository | Initial state and labels | Title | Blocked by |
|---|---|---|---|---|---|---|
| `DDW-PROG-001` | `SAAS-44` | program parent | none | `Backlog`; no `autonomous` | Establish interactive and autonomous delivery workflows | all children for closeout |
| `DDW-AIC-001` | `SAAS-45` | code-bearing child | `ai-config` | `Backlog`; no `autonomous` | Define shared delivery agents and workflow doctrine | none |
| `DDW-AIC-002` | `SAAS-46` | code-bearing child | `ai-config` | `Backlog`; no `autonomous` | Build the durable supervisor core and schemas | `SAAS-45` |
| `DDW-AIC-003` | `SAAS-47` | code-bearing child | `ai-config` | `Backlog`; no `autonomous` | Add Linear selection, decisions, and ntfy control plane | `SAAS-46` |
| `DDW-AIC-004` | `SAAS-48` | code-bearing child | `ai-config` | `Backlog`; no `autonomous` | Add deterministic GitHub delivery and repair gates | `SAAS-46`, `SAAS-47` |
| `DDW-AIC-005` | `SAAS-49` | code-bearing child | `ai-config` | `Backlog`; no `autonomous` | Distribute and validate the complete shared harness | `SAAS-45` through `SAAS-48` |
| `DDW-SAS-001` | `SAAS-51` | code-bearing child | `saas` | `Backlog`; no `autonomous` | Migrate SaaS workflow documentation and local wiki | `SAAS-45`, `SAAS-50` |
| `DDW-SAS-002` | `SAAS-50` | code-bearing child | `saas` | `Backlog`; no `autonomous` | Make validation and runtime QA cross-platform, pinned, and isolated | `SAAS-45` |
| `DDW-SAS-003` | `SAAS-52` | code-bearing child | `saas` | `Backlog`; no `autonomous` | Integrate the thin SaaS delivery-loop adapter | `SAAS-49`, `SAAS-50`, `SAAS-51` |
| `DDW-OPS-001` | `SAAS-53` | manual-operational child | none | `Backlog`; no `autonomous` | Migrate the Linear workflow and autonomous backlog | `SAAS-52` |
| `DDW-OPS-002` | `SAAS-54` | manual-operational child | none | `Backlog`; no `autonomous` | Configure notifications and pass one attended pilot | `SAAS-52`, `SAAS-53` |
| `DDW-OPS-003` | `SAAS-55` | manual-operational child | none | `Backlog`; no `autonomous` | Enable and observe the five-minute Codex heartbeat | `SAAS-54` |

Linear mapping rules:

- Parent every child under `DDW-PROG-001` and express the table's edges with Linear blocking relationships.
- Keep the parent non-autonomous and in `Backlog` while children execute so it never occupies the global WIP slot.
- Create every child in `Backlog`; only after a passing audit and explicit `Implement` approval may `DDW-AIC-001` move to `Todo` for interactive delivery. Promote later children only as their dependencies complete.
- Store `repositoryKey: ai-config` or `repositoryKey: saas`, base branch `main`, code-bearing kind, acceptance criteria, validation commands, docs impact, risks, and one-primary-PR requirement in each code child.
- Store `issueKind: manual-operational`, exact evidence, actor, timestamp, and readback requirements in each operations child. Never make an empty branch or PR for an operations-only issue.
- Do not put `autonomous` on the program-construction tasks. The autonomous label is introduced only for the bounded pilot leaf selected in `DDW-OPS-002` and for later audited product leaves.
- After a code child's implementation is approved, use `codex/<assigned-SAAS-ID>-<short-name>` and one PR to `main`; preserve the stable task ID in the PR description and workflow artifact.

## Required implementation order

1. Audit the plan plus this task document independently.
2. Obtain explicit user approval to implement.
3. Execute `DDW-AIC-001` through `DDW-AIC-005` in order; build and sync the merged shared version.
4. `DDW-SAS-002` may start after `DDW-AIC-001` and must make the existing CI gate passable before later SaaS PRs rely on it. Run `DDW-SAS-001` after that validation repair. Do not start `DDW-SAS-003` until `DDW-AIC-005` is merged and the exact shared engine version is available.
5. Merge and validate every SaaS code child before any Linear workflow mutation.
6. Run `DDW-OPS-001`, then `DDW-OPS-002`, then `DDW-OPS-003` manually.
7. Close `DDW-PROG-001` manually only after all child evidence and the program-level integration acceptance checks pass.

## Program parent

### `DDW-PROG-001` — Establish interactive and autonomous delivery workflows

- **Goal:** coordinate the cross-repository outcome without treating the program itself as executable work.
- **Linear mapping:** non-autonomous program parent; `Backlog`; no target repository, branch, or PR; all `DDW-*` records in this document are children.
- **Scope:** shared doctrine and runtime, SaaS integration, Linear migration, notifications, attended pilot, and scheduled rollout.
- **Acceptance criteria:**
  - Every code-bearing child is merged independently into its named repository and has exact-SHA validation evidence.
  - The shared engine is built from `ai-config/src`, synced as one versioned unit, and consumed by SaaS without copied generic logic.
  - SaaS docs describe Interactive Delivery and Autonomous Delivery without operational dependence on `Ready for Codex`, Slack, Telegram, or current `LUC-*` examples.
  - The Linear workflow uses only normal states plus the locked labels and contains no remaining `Ready for Codex` state.
  - One attended pilot demonstrates deterministic claim/resume, evidence generation, PR gates, runtime QA, squash merge, exact-SHA post-merge validation, and notifications.
  - One recurring five-minute Codex task is enabled from the dedicated SaaS task, and held-lease/no-work/manual-WIP behavior is observed without duplicate work.
  - Kill switch, pause, archive, secret preflight, and missed-heartbeat recovery are verified.
  - All operations children include durable before/after evidence and no artificial PR.
- **Validation/evidence:** roll-up Linear comment linking every child, repository PR and merge SHA, code-review/QA/completion artifacts, migration report, pilot report, scheduled-task identifier, and rollback instructions.
- **Dependencies:** all child tasks.
- **Non-goals:** no product feature implementation, cloud provisioning, new hosted ai-config pipeline, multi-issue concurrency, Telegram, Slack, or Windows Task Scheduler.

## `ai-config` code-bearing children

### `DDW-AIC-001` — Define shared delivery agents and workflow doctrine

- **Goal:** establish the two explicit entry routes and reusable specialist/documentation contracts before executable control-plane work.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; docs impact `README`, root/project instructions, agent/skill references; no UI design artifact.
- **Likely files/modules:**
  - `src/agents/interactive-driver.md`
  - `src/agents/autonomous-driver.md`
  - `src/agents/code-reviewer.md`
  - `src/agents/feature-driver.md`
  - `src/agents/planner.md`, `tasker.md`, `auditor.md`, and `qa.md`
  - `src/skills/docs-as-code/SKILL.md` and reusable page templates/references
  - `src/skills/luchdom-docs/SKILL.md` and `references/doc-targets.md`
  - `src/skills/multi-agent-delivery/SKILL.md` and its references
  - `src/skills/task-audit-breakdown/SKILL.md` and its artifact/audit/task references
  - `src/skills/qa-verification/SKILL.md` and `references/qa-checklist.md`
  - `src/project-templates/{codex,claude,copilot,cursor}/...`
  - `README.md` and `AGENTS.md`
- **Acceptance criteria:**
  - `interactive-driver` accepts a user-selected issue, never selects backlog work, removes autonomous ownership on manual claim, and stops at an explicit implementation gate.
  - `autonomous-driver` operates only on the supervisor-selected issue, continues through routine stages, returns structured proposals/evidence, and never claims locks or performs state-changing Git/GitHub/Linear operations.
  - `feature-driver` is a documented one-migration-cycle compatibility router to the interactive/autonomous entry points and contains no third copy of policy.
  - `code-reviewer`, auditor, and runtime QA are distinct: auditor checks approved intent before implementation, reviewer checks the implemented exact-head diff, and QA exercises real behavior without fixing defects.
  - QA requires localhost/Development assertions, isolated resources, disposable data, bounded readiness, production-secret rejection, and cleanup evidence.
  - `docs-as-code` provides how-to, concept, reference, ADR, runbook, and troubleshooting contracts; `luchdom-docs` adds only Luchdom source-of-truth routing.
  - Project templates make Interactive Delivery the default and require explicit skill/harness/user invocation for Autonomous Delivery.
  - Workflow artifacts use per-workflow folders and conditional `*-design.md`; implementation remains gated in interactive mode.
  - `task-audit-breakdown`, `multi-agent-delivery`, project templates, and agents agree on the new `docs-ai/<SAAS-N-or-local-sequence>-<slug>/` convention while preserving explicit legacy-folder fallback.
  - `qa`, `qa-verification`, and their checklist agree on localhost/Development isolation, unique resources, disposable data, production-secret rejection, bounded readiness, and cleanup evidence.
  - All supported agent adapters can be generated from canonical `src` without duplicate names or unresolved skill references.
- **Test notes:**
  - Add semantic assertions for the explicit interactive approval gate, autonomous routine-stage continuation, specialist boundaries, runtime behavior evidence, artifact-folder consistency, QA/qa-verification safety consistency, and explicit `$linear-delivery-loop` routing references.
  - Run `python .\scripts\build.py`.
  - Run existing marker tests with `python .\scripts\test_sync_markers.py`.
  - Inspect generated Codex, Claude, Copilot, and Cursor entry points for semantic parity; do not hand-edit `dist`.
- **Dependencies:** independent starting task.
- **Handoff:** merge before the supervisor schema is finalized and before SaaS documentation adopts the new names.

### `DDW-AIC-002` — Build the durable supervisor core and schemas

- **Goal:** create the dependency-free, deterministic state/lease/config/checkpoint foundation that all integrations use.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; docs impact shared skill references and schema documentation.
- **Likely files/modules:**
  - `src/skills/linear-delivery-loop/SKILL.md`
  - `references/issue-contract.md`, `state-machine.md`, and `failure-policy.md`
  - `references/project-config.schema.json`
  - `references/prepared-iteration.schema.json`
  - `references/worker-result.schema.json`
  - `references/worker-state.schema.json`
  - `references/codex-scheduled-prompt.md`
  - `scripts/agent-worker-engine.ps1`
  - `scripts/modules/Config.psm1`, `State.psm1`, `Redaction.psm1`, `Recovery.psm1`, and fixture abstractions
  - dependency-free test runner and fixture files under the skill
- **Acceptance criteria:**
  - The schemas encode the locked stage enum, supervisor-owned envelope, observed external identities, attempt counters, state revision, transition ID, expected previous stage, CI timer, operation journal, pending decision, and engine/config versions.
  - `PrepareIteration`, `ApplyCheckpoint`, `Status`, and `ReleaseLease` expose the documented exit codes and accept structured payload files rather than secrets or issue content on command lines.
  - A short OS mutex protects individual adapter calls; the durable lease is atomic, renewable, owner-bound, at least three schedule intervals, and not stolen merely because it expired.
  - State writes are atomic; compare-and-swap rejects stale revision/stage updates; replaying a transition or operation ID is safe.
  - Recovery reconciles stale local state with fixture-observed external state and does not trust conversation identity or model-supplied branch/PR/CI fields.
  - Exactly one issue may be processed per heartbeat while routine stage transitions may continue in the same heartbeat.
  - Completion or pause releases the lease and ends without another selection pass.
  - Redaction removes configured secret values from events, state, logs, and errors.
  - The reusable Scheduled prompt explicitly invokes `$linear-delivery-loop`, never launches `codex exec`, and identifies the deterministic adapter as the mutator.
- **Test notes:** primary owner of plan contract tests `15–18`, `26–28`, `34–35`, and `44–48`; include healthy/expired-ambiguous lease behavior, interrupted recovery, invalid output, worktree containment, one-issue-per-heartbeat, transition replay, stale revision, and crash-boundary recovery.
  - Run the new dependency-free skill test runner directly.
  - Run JSON parsing/schema self-tests for every valid and invalid fixture.
  - Run `python .\scripts\build.py` to prove the complete skill tree copies into `dist`.
- **Dependencies:** `DDW-AIC-001`.
- **Handoff:** expose stable module interfaces and schema version before Linear or GitHub modules are added.

### `DDW-AIC-003` — Add Linear selection, decisions, and ntfy control plane

- **Goal:** implement deterministic Linear GraphQL, WIP/queue arbitration, issue contracts, decision resume, backlog-migration planning, and redacted ntfy delivery behind fixture-compatible interfaces.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; docs impact Linear/notification skill references.
- **Likely files/modules:**
  - `src/skills/linear-delivery-loop/scripts/modules/Linear.psm1`
  - selection/contract and notification modules under `scripts/modules/`
  - Linear/ntfy fixtures and contract-test cases
  - `references/issue-contract.md` and `failure-policy.md`
- **Acceptance criteria:**
  - Startup reads `LINEAR_API_KEY` only from the process environment and resolves viewer, expected workspace, team `SAAS`, project `SaaS Boilerplate`, normal states, required labels, and configured owner before mutation.
  - GraphQL uses variables, complete cursor pagination, HTTP plus GraphQL error handling, bounded retry for transport/429/eligible 5xx, and read-before/write/read-after reconciliation.
  - Global WIP checks both `In Progress` and `In Review`; more than one active issue fails closed; manual WIP produces a clean no-op; matching autonomous WIP resumes before claim.
  - Queue eligibility and ordering exactly follow the locked predicate: priority, oldest `createdAt`, numeric identifier after complete filtering.
  - Incomplete contracts, parent/broad issues, cross-repository issues, and deferred external integrations are rejected or classified without inventing intent.
  - Claim re-reads the candidate, mutates state/assignment/comment idempotently, persists the run, and verifies ownership.
  - Pending `Backlog + needs-human + autonomous` decisions are reconciled before normal queue selection. Only an exact, new, unconsumed reply from the configured owner restores the same issue as preferred resume.
  - ntfy is required in unattended mode, uses environment-only configuration, includes a Linear click target, retries idempotently, and never becomes the decision source of truth.
  - `-DryRun` has no mutations and reports every candidate's rank/rejection plus proposed backlog migration action.
- **Test notes:** primary owner of plan tests `1–14`, `19–20`, `24–25`, `29`, `39–43`, and `49`; also exercise wrong workspace, GraphQL `200` with errors, pagination, partial data, rate limits, preservation of unrelated labels, duplicate prevention, notification failure, and decision authorization.
  - Fixture tests must contain sentinel secrets and assert their absence from all outputs.
  - A live check, if performed during later rollout, is read-only `-DryRun`; this task performs no live Linear mutation.
- **Dependencies:** `DDW-AIC-002`.
- **Handoff:** the following task consumes only supervisor-observed authorization/issue state, never agent prose.

### `DDW-AIC-004` — Add deterministic GitHub delivery and repair gates

- **Goal:** make branch/worktree, manifest, validation, PR, exact-head CI, merge, base-drift, and post-merge repair behavior deterministic and fail closed.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; docs impact Git/GitHub and recovery skill references.
- **Likely files/modules:**
  - `src/skills/linear-delivery-loop/scripts/modules/GitHub.psm1` and Git/worktree helpers
  - recovery and operation-journal integration
  - Git/GitHub fixture adapters and contract cases
  - `references/state-machine.md` and `failure-policy.md`
- **Acceptance criteria:**
  - Specialists can edit/validate and return a change manifest but cannot stage, commit, push, open/update PRs, merge, force-push, update `main`, or revert.
  - The adapter snapshots base/status, confines changes to the configured worktree, rejects unexpected/pre-existing/unrelated changes and conflict markers, runs the fixed local command, stages only reconciled paths, commits with the issue ID, and pushes without force.
  - One primary PR targets `main`; exact head/base/PR identity is journaled and reconciled after ambiguous output.
  - The latest unambiguous `.github/workflows/validate.yml` `pull_request` run, job/check `Validate / validate`, must pass for the exact head; workflow, event, head, and run attempt are verified. Missing/pending enters `ci_wait`, releases the lease, and uses a 30-minute per-head deadline. Failure consumes one of three CI repair heads.
  - Review, runtime QA, docs, authorization, mergeability, head, base, and CI are re-read immediately before squash merge.
  - If `origin/main` advances, merge it into the issue branch without rebase/force, then rerun local validation, affected QA, and exact-head CI.
  - Merge occurs through GitHub squash merge; `Done` is impossible until a clean worktree validates the returned merge SHA.
  - A failed post-merge smoke remains on the original issue, creates numbered repair branch/PR history from current `main`, reruns every gate, permits three attempts, and never auto-reverts.
  - Gate evidence binds to exact SHAs; executable changes invalidate prior review/QA/CI evidence.
- **Test notes:** primary owner of plan tests `21–23`, `30–38`, and `50–54`; cover authorization removal, stop labels, changed head, direct-main/force/revert rejection, missing/stale checks, pending timeout, CI repair budgets, base drift, evidence-only deltas, exact merge SHA, and ordered repair history.
  - Use disposable fixture repositories/remotes and fixture GitHub responses; no real push, PR, merge, or Linear mutation in contract tests.
  - Run the shared dependency-free test runner and `python .\scripts\build.py`.
- **Dependencies:** `DDW-AIC-002`, `DDW-AIC-003`.
- **Handoff:** merge only when every successful path is exact-SHA-bound and every ambiguous mutation has reconciliation coverage.

### `DDW-AIC-005` — Distribute and validate the complete shared harness

- **Goal:** make the canonical runtime buildable, testable, installable, version-compatible, and documented across supported tools without hand-edited generated copies.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; docs impact root usage/setup and project templates.
- **Likely files/modules:**
  - `scripts/build.py`
  - `scripts/sync.py`
  - `scripts/test_sync_markers.py` plus new build/sync/semantic tests
  - a repository-local aggregate validation script
  - `README.md`, `AGENTS.md`, and all project templates
  - generated `dist/` output produced by the build, if this repository tracks it
- **Acceptance criteria:**
  - Build validates unique agents, repo-managed skill references, the two driver contracts, compatibility routing, reviewer/QA separation, docs templates, all JSON Schemas, required engine modules, fixture interface, and the Scheduled prompt restrictions.
  - Sync copies the complete skill runtime and one coherent engine/schema version to Codex, Claude, and Copilot; Cursor project outputs retain the correct instruction routing.
  - Tests install into temporary homes/projects only, preserve marker-managed external content, verify generated/installed parity, reject version mismatch, and prove through a generic fixture adapter that project wrappers cannot override engine-owned behavior. The real SaaS wrapper is not required by this task and is verified in `DDW-SAS-003`.
  - Root docs explain both workflows, the shared-engine/project-config boundary, source-first changes, and build/sync/verification commands.
  - One local aggregate command runs build, existing marker tests, semantic/build tests, and all shared-engine contract tests.
  - No new hosted ai-config pipeline is introduced.
  - A release/version identifier is recorded for SaaS integration, and an attended build/sync verification confirms the installed files exist.
- **Test notes:**
  - Run `python .\scripts\build.py`.
  - Run `python .\scripts\test_sync_markers.py` plus every new build/sync test.
  - Run the new aggregate validation command.
  - Run `python .\scripts\sync.py --tool all` only as the separately acknowledged local installation step after the PR is merged; verify installed agents, skills, scripts, modules, and schema versions without printing secrets.
- **Dependencies:** `DDW-AIC-001`, `DDW-AIC-002`, `DDW-AIC-003`, `DDW-AIC-004`.
- **Handoff:** record the merged commit and installed engine/config schema version in `DDW-SAS-003` evidence.

## `saas` code-bearing children

### `DDW-SAS-001` — Migrate SaaS workflow documentation and local wiki

- **Goal:** replace stale workflow guidance with the locked dual-delivery policy and create searchable, pinned docs-as-code navigation.
- **Linear mapping:** code-bearing child; `repositoryKey: saas`; base `main`; one primary PR; docs impact all operational workflow sources; no product UI design.
- **Likely files/modules:**
  - `AGENTS.md`, `README.md`
  - `docs/HARNESS.md`, `WORKFLOW.md`, `LINEAR.md`, `DECISIONS.md`, `QUALITY.md`, `AI-TOOLING.md`, `LOCAL-DEVELOPMENT.md`
  - new `docs/AUTOMATION.md`, docs index, and reusable page templates
  - retirement of `docs/SLACK-APPROVALS.md`
  - `mkdocs.yml`, `requirements-docs.txt`
  - `scripts/check-doc-drift.ps1`
- **Acceptance criteria:**
  - Docs consistently name Interactive Delivery and Autonomous Delivery and preserve the explicit interactive implementation gate.
  - Current operational guidance uses `SAAS-*`, `Todo + autonomous`, normal Linear states, one global WIP slot, labels, achievable issue contracts, one-repository/one-PR children, and local-first sequencing.
  - Historical flat `docs-ai` and historical `LUC-*` records remain intact and are clearly distinguished from current conventions.
  - New evidence uses `docs-ai/<SAAS-N-or-local-sequence>-<slug>/` with conditional design artifacts.
  - Linear is the durable decision record, ntfy is unattended attention, and Codex Scheduled is run visibility. Slack/Telegram configuration guidance is removed and `docs/SLACK-APPROVALS.md` is retired after any still-valid generic guidance is moved.
  - `docs/AUTOMATION.md` documents Worktree mode, five-minute wake-up, app/computer prerequisite, no nested Codex process, no OS scheduler in phase 1, secrets/preflight, pause/archive/kill-switch, and recovery boundaries.
  - `requirements-docs.txt` pins exactly `mkdocs==1.6.1`; `mkdocs.yml` has deliberate navigation/search and excludes noisy run evidence from primary wiki navigation.
  - Documentation templates cover how-to, concept, reference, ADR, runbook, and troubleshooting.
  - The reusable Linear migration procedure defines the ignored `.artifacts/harness/operations/` before/after report schema and concise Linear readback contract without requiring an operations-only repository PR.
  - Doc drift rejects operational `Ready for Codex`, configured Slack/Telegram routes, and current `LUC-*` branch examples while permitting clearly marked history.
- **Test notes:** primary owner of plan test `56` and the MkDocs half of `57`.
  - Run `pwsh ./scripts/check-doc-drift.ps1`.
  - Install the pinned docs requirements in a repo-managed environment and run `mkdocs build --strict`.
  - Run `pwsh ./scripts/validate-all.ps1`.
  - Search current operational files for rejected phrases and manually verify historical exceptions remain documented.
- **Dependencies:** `DDW-AIC-001`, `DDW-SAS-002` so the documentation PR is protected by the repaired passable validation gate.
- **Handoff:** merge before adapter rollout or Linear workflow mutation.

### `DDW-SAS-002` — Make validation and runtime QA cross-platform, pinned, and isolated

- **Goal:** repair the existing Ubuntu CI validation path and replace floating Playwright CLI use with a repository-pinned acceptance-test surface that safely exercises the real local API and browser flows.
- **Linear mapping:** code-bearing child; `repositoryKey: saas`; base `main`; one primary PR; docs impact local development and quality commands.
- **Likely files/modules:**
  - `apps/web/package.json` and `apps/web/package-lock.json`
  - `apps/web/playwright.config.ts`
  - focused Playwright specs/fixtures under `apps/web/tests/` or the existing web test convention
  - `.github/workflows/validate.yml`
  - `scripts/validate-all.ps1`, `scripts/smoke.ps1`, and `scripts/check-tools.ps1`
  - targeted updates to `docs/QUALITY.md` and `docs/LOCAL-DEVELOPMENT.md`
- **Acceptance criteria:**
  - `@playwright/test` is a direct dev dependency pinned exactly to `1.61.1` in both web manifest and lockfile; no caret/range, optional-peer, `npx --yes --package`, or global fallback remains.
  - `scripts/validate-all.ps1` invokes npm cross-platform without Windows-only `cmd`, and `pwsh ./scripts/validate-all.ps1 -CI` passes on the workflow's Ubuntu runner.
  - `.github/workflows/validate.yml` runs for `pull_request` and for `push` only on `main`, so a feature PR head does not receive duplicate push/PR `Validate / validate` runs.
  - Workflow `Validate`, job `validate`, displayed check `Validate / validate`, event, head SHA, and run attempt have fixture/semantic coverage; a later rerun is deterministically identified by the latest workflow run/attempt, while ambiguity fails closed.
  - A documented repository-local command runs browser acceptance tests and a documented preflight installs/verifies the matching browser binaries/cache.
  - Runtime QA starts/connects only to asserted loopback API/web endpoints in Development, allocates unique per-run ports/names, rejects production-like credentials/endpoints, and uses bounded readiness checks rather than arbitrary unbounded waits.
  - API scenarios issue real HTTP requests and verify status, payload/persistence, auth, and tenant isolation where relevant.
  - UI scenarios use Playwright to exercise a representative anonymous/authenticated flow, assert visible results, keyboard/focus behavior, and obvious accessibility failures, and retain screenshots/traces only when useful.
  - Tests use disposable data and record cleanup; they never reset the user's ordinary development database implicitly.
  - `scripts/smoke.ps1 -Live -Behavioral -Playwright` delegates to the pinned local test surface and exits nonzero on failure.
- **Test notes:** primary owner of plan test `55` and the Playwright half of `57`.
  - Run `npm ci`, `npm run typecheck`, `npm run build`, and the new Playwright test command from `apps/web`.
  - Run `pwsh ./scripts/smoke.ps1 -Live -Behavioral -Playwright` against disposable local dependencies.
  - Run `pwsh ./scripts/validate-all.ps1` locally and verify `pwsh ./scripts/validate-all.ps1 -CI` through the Ubuntu GitHub workflow for the PR head.
  - Include negative tests for non-loopback URL, non-Development environment, production-like secret, shared destructive database, readiness timeout, and missing cleanup evidence.
- **Dependencies:** `DDW-AIC-001` for the locked QA safety contract; otherwise this is the first SaaS code child and repairs the gate used by later SaaS PRs.
- **Handoff:** provide fixed runtime-QA hooks and commands for the project adapter; do not add scheduler or Linear logic.

### `DDW-SAS-003` — Integrate the thin SaaS delivery-loop adapter

- **Goal:** bind the merged shared engine to SaaS policy through a versioned config, thin manual shim, project fixtures, and versioned Codex Scheduled prompt while remaining disabled by default.
- **Linear mapping:** code-bearing child; `repositoryKey: saas`; base `main`; one primary PR; docs impact automation setup and validation.
- **Likely files/modules:**
  - `automation/linear-delivery-loop.config.json`
  - `automation/codex-scheduled-linear-loop.md`
  - `scripts/agent-worker.ps1`
  - `scripts/test-agent-worker.ps1`
  - project fixtures under `automation/fixtures/` or a test-local equivalent
  - `.gitignore` for `.artifacts/harness/runs/`
  - `scripts/check-tools.ps1`, `check-doc-drift.ps1`, and `validate-all.ps1` integration assertions
- **Acceptance criteria:**
  - Config validates against the exact installed schema and contains only `repositoryKey: saas`, `main`, team `SAAS`, project identifiers, normal states/labels, branch templates, artifact/docs paths, fixed commands, local-first flags, runtime-QA hooks, required checks, and environment-variable names—not values.
  - Local validation is exactly `pwsh ./scripts/validate-all.ps1`; required check is exactly `Validate / validate` and is contract-checked against `.github/workflows/validate.yml`.
  - `scripts/agent-worker.ps1` resolves an explicit or installed shared engine, verifies versions, forwards structured arguments, rejects the primary checkout for autonomous mutation, and contains no GraphQL, state, lease, transition, notification, Git, or GitHub implementation.
  - Contract tests prove the real SaaS wrapper/config cannot override engine-owned transition, Linear, Git/GitHub, notification, retry, or redaction behavior; this is the project-specific completion of the generic boundary proved in `DDW-AIC-005`.
  - Project fixtures run the complete shared suite against SaaS config without live mutations, including every numbered plan scenario `1–58` at the project boundary.
  - The versioned prompt explicitly invokes `$linear-delivery-loop`, handles at most one issue while continuing routine stages, and has the documented no-work/manual-WIP/lease/external-wait/pause/completion stop conditions.
  - Preflight checks app-inherited `LINEAR_API_KEY` and ntfy variable presence/validity without printing values; unattended `-NoNotify` is rejected.
  - A repository kill switch and pause/archive/removal procedure are documented and testable.
  - The integration lands disabled by default and adds no Windows Task Scheduler entry, nested `codex exec`, copied engine, secret, or live Linear mutation.
- **Test notes:** primary owner of plan test `58` and project-level execution of all shared cases.
  - Run `pwsh ./scripts/test-agent-worker.ps1` using fixtures.
  - Run `pwsh ./scripts/agent-worker.ps1 -Action Status` and mutation-free `-Action PrepareIteration -DryRun` only after an attended preflight.
  - Run `pwsh ./scripts/check-doc-drift.ps1`, `mkdocs build --strict`, and `pwsh ./scripts/validate-all.ps1`.
  - Verify missing/mismatched engine versions, wrong config commands/check names, primary-checkout paths, and missing unattended ntfy config fail closed.
- **Dependencies:** `DDW-AIC-005` merged and synced, `DDW-SAS-001`, `DDW-SAS-002`.
- **Handoff:** provide merged commit, exact installed shared-engine version, disabled-state proof, fixture report, and dry-run command to operations.

## Manual-operational children

### `DDW-OPS-001` — Migrate the Linear workflow and autonomous backlog

- **Goal:** move the SaaS project to regular states plus labels and leave only complete, locally runnable leaf issues eligible for autonomous claim.
- **Linear mapping:** `manual-operational`; no repository key, branch, or PR; `Backlog`; no `autonomous`; exact before/after evidence required.
- **Operational steps:**
  1. Create/verify labels `blocked`, `needs-human`, `needs-refinement`, and `external-integration` without duplicating existing labels.
  2. Run mutation-free, completely paginated inventories of (a) every `Backlog` or `Todo` issue carrying `autonomous` and (b) every issue currently in `Ready for Codex`, including parents, children, blockers, repository contract, local/external classification, and proposed regular-state/label mapping.
  3. Review the dry-run report manually.
  4. Apply the idempotent migration: parents/broad/multi-goal work becomes `Backlog + needs-refinement` without `autonomous`; deferred hosted/external work becomes `Backlog + external-integration` without `autonomous`; only complete local leaves become `Todo + autonomous`; ready manual work remains `Todo` without the label; every `Ready for Codex` issue is mapped to `Backlog` or `Todo` with its correct labels.
  5. Preserve unrelated labels, reuse equivalent child issues, split mixed local/external scope, and comment only where classification changes.
  6. Confirm no automation eligibility depends on `Ready for Codex`, verify its issue count is zero, then remove that workflow state manually in Linear UI.
  7. Run both inventories again and verify zero `Ready for Codex` issues, no `Backlog + autonomous` residue, and every eligible issue is a bounded leaf for exactly one repository.
- **Acceptance criteria:**
  - Before/after exports record state, labels, parent/child/dependency, repository key, contract gaps, rank tuple, and mutation for every audited issue, including all issues originally in `Ready for Codex`.
  - No parent, broad item, cross-repository issue, external integration, or incomplete contract remains eligible.
  - No duplicate split child was created; unrelated issue metadata is preserved.
  - `Ready for Codex` no longer exists and no current doc/config/query references it as an operational state.
  - New identifiers/comments/branch examples use `SAAS-*`; historical `LUC-*` evidence is not rewritten.
- **Validation/evidence:** timestamped redacted dry-run and post-migration reports under ignored `.artifacts/harness/operations/`, label UUID/readback, screenshots or API readback of workflow states, before/after `Ready for Codex` counts, issue counts by classification, and changed-issue links. Store the concise durable record in Linear. `DDW-SAS-001` owns the reusable procedure/report schema; no repository migration-run report is required by this operations task, and any later durable report must be a separately approved code-bearing docs issue rather than a fake PR here.
- **Dependencies:** `DDW-SAS-003` merged, validated, and disabled by default.
- **Rollback:** pause via label removal/kill switch and restore issue state/labels from the before export if necessary. Because the deleted custom status cannot be assumed automatically restorable through the connector, retain the original `Ready for Codex` membership export and map restored issues to regular states while workspace administration is handled manually; ordinary interactive delivery remains available.

### `DDW-OPS-002` — Configure notifications and pass one attended pilot

- **Goal:** prove one bounded autonomous issue end to end under observation before recurring scheduling.
- **Linear mapping:** `manual-operational`; no repository key, branch, or PR for this operations issue; no `autonomous`. The separate pilot product/code leaf is an existing or newly refined `Todo + autonomous` issue with its own repository/PR contract.
- **Operational steps:**
  1. Configure a private/authenticated ntfy base URL, topic, and token outside both repositories; restart Codex desktop if required for user-scoped environment inheritance.
  2. Verify Linear owner assignment/mention and native desktop/mobile notification settings; treat native delivery as opportunistic.
  3. Run shared and SaaS fixture suites, config/version preflight, `Status`, and live read-only `-DryRun`.
  4. Select one safe, locally runnable, review-sized SaaS leaf with a complete issue contract; set only that issue to `Todo + autonomous`.
  5. From the dedicated SaaS Codex task in Worktree mode, invoke `$linear-delivery-loop` for the specific issue in attended mode.
  6. Exercise at least one structured decision request/reply round trip without bypassing authorization or accepting malformed/stale replies.
  7. Observe branch/worktree confinement, artifacts, local validation, one PR, exact-head CI, code review, real HTTP/Playwright QA, squash merge, and clean exact-merge-SHA post-merge validation.
- **Acceptance criteria:**
  - No secret appears in command history, repository files, state, logs, Linear, ntfy, or artifacts.
  - Required ntfy delivery opens the correct Linear issue and retry state is observable; empty queue/held lease/routine stages do not notify.
  - Decision acceptance requires the configured owner, exact ID/option, correct ordering, and one-time consumption.
  - The pilot touches one repository, one primary branch/PR, and one Linear issue; no second issue is claimed in its heartbeat.
  - The pilot reaches `Done` only after merge and exact-SHA post-merge success, or pauses safely with complete evidence if a real gate fails.
  - Kill switch and manual-WIP no-op are tested before schedule enablement.
- **Validation/evidence:** redacted preflight report, ntfy delivery/readback, Linear decision thread, Codex task link/identifier, pilot issue/PR/merge SHA, workflow artifact links, CI check, QA report, post-merge result, and kill-switch test.
- **Dependencies:** `DDW-OPS-001`, `DDW-SAS-003`; all code children merged.
- **Rollback:** remove `autonomous` from the pilot, activate kill switch, pause the Codex task, and preserve artifacts for diagnosis.

### `DDW-OPS-003` — Enable and observe the five-minute Codex heartbeat

- **Goal:** enable the reviewed versioned prompt as one recurring local Codex heartbeat and verify stable unattended behavior before expanding the queue.
- **Linear mapping:** `manual-operational`; no repository key, branch, or PR; `Backlog` until pilot passes; no `autonomous`.
- **Operational steps:**
  1. From the same dedicated SaaS Codex task used by the pilot, create/update one recurring five-minute task using the merged `automation/codex-scheduled-linear-loop.md` prompt.
  2. Confirm Worktree mode, project root, explicit `$linear-delivery-loop` invocation, app/computer-on prerequisite, inherited environment preflight, and Scheduled inbox visibility.
  3. Observe empty queue, manual WIP, healthy held lease, pending CI resume, and at least one normal resume/terminal path as safely available.
  4. Confirm one heartbeat never claims a second issue after completion/pause and that missed heartbeats reconcile on return.
  5. Review the first several scheduled iterations before adding more autonomous leaves; tune only documented lease/retry/retention configuration and record any change.
- **Acceptance criteria:**
  - Exactly one active recurring task exists at a five-minute cadence; no Windows scheduled task or standalone duplicate is present.
  - The schedule is disabled automatically or manually when preflight fails, kill switch is set, or app/project prerequisites are unavailable; no external mutation occurs in those states.
  - Held lease exits `10` without noise; manual WIP and empty queue exit successfully without claim/notification.
  - Pending external CI releases the lease and resumes the same issue before queue selection.
  - Scheduled inbox and worker `Status` expose last heartbeat, issue/stage, lease, retry, and pending notification/decision without exposing secrets.
  - Pause, removal, and dedicated-task archive procedures are tested and reversible.
- **Validation/evidence:** Codex Scheduled task ID and cadence screenshot/readback, merged prompt SHA, several redacted run IDs/status outputs, scenario results, confirmation that no duplicate scheduler exists, and documented rollback test.
- **Dependencies:** `DDW-OPS-002` passing attended pilot.
- **Rollback:** pause/remove the schedule, set the repository kill switch, remove autonomous eligibility, and archive the dedicated Codex task while retaining run evidence.

## Cross-task test ownership

The plan's numbered SaaS worker scenarios remain one acceptance suite. The primary implementation owner prevents gaps, while `DDW-SAS-003` reruns all scenarios against the assembled SaaS configuration.

| Plan scenarios | Primary owner | Boundary |
|---|---|---|
| `1–14`, `19–20`, `24–25`, `29`, `39–43`, `49` | `DDW-AIC-003` | Linear transport, WIP/selection, issue contracts, decisions, backlog classification, notifications |
| `15–18`, `26–28`, `34–35`, `44–48` | `DDW-AIC-002` | lease/state/recovery, schema trust, containment, heartbeat progression, idempotency |
| `21–23`, `30–38`, `50–54` | `DDW-AIC-004` | review/QA return, Git/GitHub authorization, CI, merge, base drift, evidence SHA, post-merge repair |
| `55` | `DDW-SAS-002` | safe live runtime-QA isolation |
| `56` | `DDW-SAS-001` | documentation drift and history exception |
| `57` | `DDW-SAS-001` for MkDocs; `DDW-SAS-002` for Playwright | exact repository-owned tool pins |
| `58` | `DDW-SAS-002` for cross-platform workflow/check identity; `DDW-SAS-003` for project config | exact SaaS validation command, unique PR-head workflow gate, and GitHub check config |
| `1–58` assembled | `DDW-SAS-003` | installed shared engine plus SaaS config, wrapper, and fixtures |

No contract case may be deleted or weakened merely because a lower layer already tests it. Project-level tests may reuse the shared fixture runner, but their output must prove the exact SaaS config was loaded.

## Per-code-child delivery contract

Every code-bearing task must follow this sequence after explicit implementation approval. This program is the bootstrap that creates the deterministic adapter, so `DDW-AIC-001` through `005` and `DDW-SAS-001` through `003` use Interactive Delivery: only the root Codex task or human user may perform explicitly approved Git/GitHub mutations; specialist subagents still edit/validate only. The deterministic adapter becomes mandatory for later autonomous product work after `DDW-SAS-003` is merged, installed, and verified.

1. Use its assigned `SAAS-N` and repository-specific workflow folder.
2. Re-read the task, plan, repository instructions, and dependency handoff.
3. Implement only the named repository scope; do not mutate Linear from specialist agents.
4. Update the nearest source-of-truth docs in the same change.
5. Run focused tests, then the repository's full relevant aggregate validation.
6. Write code-review and QA evidence before the final gated head, then repeat invalidated gates after executable changes.
7. For these bootstrap children, have the root Codex task or human user reconcile the manifest and, under the active conversation's approval, create `codex/SAAS-N-<slug>`, stage scoped changes, commit, push, and open one PR. Do not pretend the not-yet-built adapter delivered itself.
8. Require exact-head review/QA/docs/CI and base-drift reconciliation before squash merge.
9. Validate the exact merge SHA from a clean worktree before Linear `Done`.
10. If post-merge validation fails, stay on the same issue and use the bounded repair flow rather than a new implementation issue or automatic revert.

## Final program acceptance and closeout

After `DDW-OPS-003`, manually verify:

- Interactive Delivery still stops for clarification/approval and cannot be claimed by the recurring worker.
- Autonomous Delivery selects/resumes exactly one eligible SaaS leaf, uses the shared specialists, and stops at only documented terminal/wait/pause conditions.
- Shared and project validation commands pass from clean checkouts.
- All current docs, config, prompts, labels, and examples agree on `SAAS`, ordinary Linear states, labels, notifications, PR/squash/exact-SHA Done policy, and local-first sequencing.
- Every child has a completion record; every code child has one primary PR and exact merge evidence; every operations child has its non-PR readback evidence.
- Rollback leaves normal interactive delivery and ordinary Linear states intact.

Then add a parent roll-up comment and move `DDW-PROG-001` to `Done` manually. Do not label the parent `autonomous` at any point.

## Sources consulted

### Workflow artifacts and contracts

- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-16-dual-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\SKILL.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\audit-checklist.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\task-template.md`
- `C:\Users\lucas\.codex\skills\multi-agent-delivery\SKILL.md`
- `C:\Users\lucas\.codex\skills\multi-agent-delivery\references\handoff-order.md`
- `C:\Users\lucas\.codex\skills\multi-agent-delivery\references\output-contracts.md`

### `ai-config` ownership evidence

- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\references\doc-targets.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py`

### SaaS ownership evidence

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
- `C:\dev\luchdom\saas\scripts\common.ps1`
- `C:\dev\luchdom\saas\scripts\check-tools.ps1`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\scripts\smoke.ps1`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`

## Blockers

No task-breakdown blocker remains. Implementation is deliberately blocked until an independent auditor validates the locked plan and this task document and the user then explicitly approves `Implement`.
