# Three Delivery Workflows — Fresh Independent Plan and Task Re-audit 2

## Verdict

**PASS.** No actionable P0, P1, or P2 finding remains.

The current `2026-07-17-three-delivery-workflows-plan.md` and `2026-07-17-three-delivery-workflows-tasks.md` are internally consistent, trace the user's requirements, fit the current repositories, and assign deterministic proof for the risky boundaries. The latest correction is valid: phase 1 is local-only and adds no CI pipeline, while GitHub publication remains honestly provider-dependent and can pause without losing protected work or weakening provider controls.

The plan and tasks are therefore **finalized at the pre-implementation gate**. This PASS does not authorize Linear updates, implementation, build/sync installation, Git/GitHub mutation, ntfy configuration or publishing, a pilot, Linear workflow migration, or schedule creation/enablement. Those remain separate later actions under the authority rules in the plan and tasks (`2026-07-17-three-delivery-workflows-plan.md:18-20`, `:798-805`; `2026-07-17-three-delivery-workflows-tasks.md:12-16`, `:599-603`).

This audit created only this report. It did not revise the plan/tasks, source code, generated output, either repository, or any external system.

## Findings by severity

### P0 — Critical

None.

### P1 — High

None.

### P2 — Medium

None.

### P3 — Low / implementation precision

No new actionable P3 note is needed. The two earlier P3 implementation notes are now explicit task acceptance and regression obligations rather than unassigned advice:

- Scheduled configuration consistently uses `workspace-write`, `sandbox_workspace_write`, `approval_policy = "never"`, and fixed command rules without mixing beta named permission profiles (`2026-07-17-three-delivery-workflows-tasks.md:31-34`, `:191-203`, `:394-402`, `:490-499`).
- Registry-only and assembled workflow-managed Handoff tests distinguish native Codex **Hand off**, preserve the source on failure, atomically revoke it on success, and reject every later workflow-managed source write (`2026-07-17-three-delivery-workflows-tasks.md:152-161`, `:188-203`, `:390-402`, `:490-499`).

## All-audit resolution readback

### Findings from `2026-07-17-three-delivery-workflows-audit.md`

| Prior finding | Independent readback from the current plan/tasks | Result |
|---|---|---|
| `P1.1` — worktree-relative durable state | Scheduled worktrees are disposable control surfaces. Normalized Git identity resolves one machine-stable per-repository home outside all checkouts; it owns state, mutex, registry, lease, reservations, operations, persistent issue worktrees, and isolated validation worktrees. Cleanup and recovery fail closed on protected/ambiguous work (`plan:498-528`; `tasks:180-203`, `:475-499`). | **Resolved** |
| `P1.2` — interactive/local work invisible to autonomous selection | Linear tracked WIP is composed with a repository-scoped reservation covering autonomous and interactive repository edits. Selected manual issues remove autonomous ownership before Plan; local evidence-only planning has a narrow exception; dirty/unmerged/open-PR/inaccessible state is never released by time alone; other repositories do not block SaaS (`plan:337-356`, `:437-448`, `:578-610`; `tasks:186-200`, `:391-402`, `:490-499`). | **Resolved** |
| `P1.3` — missing unattended permission contract | The plan defines the least-privilege sandbox, writable roots, minimal environment, host/loopback restrictions, fixed commands, and a mutation-free pre-claim permission/connectivity preflight. Tests cover every denied boundary and one approved configuration (`plan:530-553`; `tasks:191-203`, `:394-402`). | **Resolved** |
| `P2.1` — tracked evidence changes the head it attests | Draft evidence is committed before the gated head. Review/QA bind to the executable SHA; final report deltas are classified; evidence-only deltas rerun final-head aggregate/review and either QA or a named two-SHA reuse proof. Terminal attestations live externally without a post-merge repository mutation (`plan:656-674`; `tasks:254-277`, `:513-529`). | **Resolved** |
| `P2.2` — canonical policy ownership conflict | Canonical cross-tool protocol ownership intentionally moves to `src/skills/goal-to-delivery/references/`; repo guidance retains repository-specific and stricter rules. All projections receive version/hash/reference parity and competing normative copies are rejected (`plan:210-236`, `:774-794`; `tasks:141-168`, `:284-310`). | **Resolved** |
| `P2.3` — unsafe allocation/resume | `workflow-init` owns atomic allocation, immutable workflow ID, exact selectors, registry readback, collision retry/quarantine, physical-worktree binding, atomic later Linear attachment, historical fallback, and explicit workflow-managed Handoff (`plan:292-385`; `tasks:144-163`). | **Resolved** |

### Findings from `2026-07-18-three-delivery-workflows-task-audit.md`

| Prior finding | Independent readback from the current plan/tasks | Result |
|---|---|---|
| `P1.1` — impossible universal exact-head CI gate | Phase 1 now has repository-specific local authority only: `ai-config` introduces and extends `python .\scripts\validate.py`; SaaS uses `pwsh ./scripts/validate-all.ps1` plus applicable exact-head HTTP/Playwright QA. Both rerun the aggregate in a clean isolated worktree at the exact returned merge SHA. No hosted check or new pipeline is required (`plan:116-120`, `:461-474`, `:839-846`; `tasks:48-50`, `:520-529`). | **Resolved** |
| `P1.2` — `SAAS-45`/`SAAS-46` circular primitive ownership | `SAAS-45` solely owns repository identity, stable-home derivation, base mutex, registry, worktree binding, allocation/resume/attach, and registry-only transfer. `SAAS-46` imports those exact versioned modules and adds supervisor state, lease/capability, editing reservations, persistent worktrees, journal, preflight/recovery, and assembled reservation-aware transfer (`plan:502-508`, `:612-627`, `:774-778`; `tasks:124-208`). | **Resolved** |
| `P2.1` — Windows-unsafe work key/path contract | Keys are provider-observed or allocator-generated only. Slugs have bounded grammar; allocation rejects invalid/reserved names, traversal, case collisions, containment ambiguity, and reparse escapes before and after creation. Windows-focused fixtures are explicit (`plan:319-323`, `:377-383`; `tasks:145-160`). | **Resolved** |
| `P3.1` — custom Handoff confused with native Codex **Hand off** | Both artifacts consistently use **workflow-managed Handoff**, deny authority transfer from native **Hand off**, and require deterministic mismatch recovery plus superseded-source rejection (`plan:341-343`, `:627`, `:1044`; `tasks:152-161`, `:188-203`, `:356`). | **Resolved and assigned** |

### Finding from `2026-07-18-three-delivery-workflows-task-re-audit.md`

#### `P2.1` — provider-enforced publication refusal

The correction is complete and deterministic:

- There is no remaining absolute claim that hosted checks or repository policy cannot physically block publication. The only `cannot block SaaS` wording concerns reservations from another normalized repository, not publication (`plan:339`; `tasks:45`). The current invariant is narrower: hosted checks are not required, queried, polled, waited on, budgeted, or accepted as phase-1 evidence/authorization, while GitHub may refuse push, PR, or merge (`plan:116-119`, `:450-465`, `:676-683`; `tasks:48-49`, `:257-262`, `:527-529`).
- A refusal is transient only for an explicit retryable response (`429`, `5xx`/unavailable service, or temporary mergeability) plus readback proving the operation did not already succeed. It retains the correct ordinary state, `autonomous`, WIP, reservation, worktree, branch/PR/evidence, releases only the run lease, and uses a maximum of three operation/head retries with bounded backoff (`plan:678-680`; `tasks:257-259`).
- Stable, exhausted, ambiguous, policy, permission, required-check, ruleset/protection, merge-queue, or unclassified refusal preserves the same protected state, adds `blocked + needs-human`, writes one deduplicated Linear operational request, sends ntfy, and never reaches `Done` (`plan:681`; `tasks:260`, `:446-447`).
- Recovery requires exact owner-only `RETRY-PUBLICATION <operation-id> <head-sha>` after attended external reconciliation. One new authorized reply is consumed once, all identities and local attestations are re-read, and at most one idempotent push/PR/merge operation is attempted. Stale, malformed, duplicate, unauthorized, changed-head, unresolved, and ambiguous cases remain paused on the same request (`plan:681-683`, `:687-691`; `tasks:227-230`, `:260-262`, `:274`).
- The adapter cannot query hosted-check status, mutate repository settings/rules/protection/required checks/permissions/merge queues, use admin or bypass merge, add or repair a pipeline, create a speculative child, duplicate publication, release protected work, or claim `Done` (`plan:458`, `:678-683`; `tasks:262`, `:275`, `:281`, `:529`).
- Fixture ownership is complete: `SAAS-48` owns push, PR, and merge refusal fixtures and exact retry behavior; `SAAS-52` proves SaaS propagation; `SAAS-54` runs an attended recovery simulation before the pilot; `SAAS-55` observes transient and stable scheduled behavior with fixture/simulation state (`tasks:241-282`, `:393-402`, `:437-447`, `:459-468`, `:479-499`).

**Result: resolved.** The correction does not introduce CI authority, pipeline work, or an unbounded provider wait.

## Contradiction and traceability checks

### User requirements

- Three reusable workflows are explicit and policy-distinct over one specialist stack: autonomous `$linear-delivery-loop`, semi-autonomous `$goal-to-delivery`, and manually advanced `$spec-driven-delivery` (`plan:53-67`, `:125-157`; `tasks:36-50`, `:136-143`).
- A local goal without a Linear issue is first class, receives deterministic artifacts, can attach later without renaming/recreating history, and can run in another repository without consuming SaaS Linear WIP (`plan:325-343`; `tasks:145-163`).
- Autonomous selection is one achievable local-first `Todo + autonomous` executable leaf, with full issue contract, dependency filtering, deterministic order, one issue per heartbeat, and no second selection after pause/completion (`plan:555-610`; `tasks:218-239`, `:396`).
- Ordinary states plus labels replace `Ready for Codex`; migration requires complete pagination, zero remaining issue/reference proof, and manual status deletion only after readback (`plan:693-707`; `tasks:411-430`).
- Product decisions use durable Linear requests and ntfy attention; Codex Scheduled provides run visibility. Telegram and Slack are excluded, routine/no-work paths stay quiet, and secrets remain environment-only (`plan:685-691`; `tasks:219-235`, `:432-452`).
- Autonomous code uses one primary PR, review, real behavior QA, squash merge, and exact-merge-SHA local validation before `Done`; direct-main delivery and auto-revert are excluded (`plan:450-459`, `:656-674`; `tasks:241-282`, `:501-529`).
- SaaS runtime QA uses real HTTP/Playwright behavior with Development/loopback enforcement, unique disposable resources, bounded readiness, production-secret rejection, and cleanup (`plan:942-956`; `tasks:314-340`).
- Durable docs and a searchable local MkDocs wiki are owned by `SAAS-51`; per-run evidence remains in `docs-ai` and is linked instead of becoming a second protocol copy (`plan:387-397`; `tasks:342-373`).
- Local product capability is explicitly ordered before hosted CI/CD, live billing providers, PostHog, AWS, production secrets, monitoring, and deployment (`plan:866-871`; `tasks:50`).

### Internal consistency

- Quality authority and publication transport are separate. Passing a clean exact-SHA local gate does not imply GitHub accepted push/merge; provider refusal does not invalidate local evidence or authorize bypass (`plan:461-474`, `:676-683`; `tasks:323-336`, `:527-529`).
- State transitions remain ordinary and deterministic: pre-PR refusal stays `In Progress`; post-PR/merge refusal stays `In Review`; stable refusal retains WIP so a scheduled run cannot select another issue; pending publication replies are reconciled before ordinary queue selection (`plan:646-654`, `:678-689`).
- A failed/ambiguous merge never reaches post-merge or `Done`; successful merge requires returned-SHA readback and a separate clean exact-merge worktree (`plan:669-674`; `tasks:267-269`, `:516-529`).
- The bootstrap exception is attended and explicitly authorized: before the engine exists, root/human owns Git actions and a refusal is preserved/reported rather than treated as success. Automated provider-refusal fixtures become the responsibility of the later `SAAS-48` engine layer (`plan:461-465`; `tasks:503-518`). This avoids a circular dependency on an engine that has not yet been built.
- No product-design artifact is required for this program because it changes tooling/workflow rather than product UI; routed product work still requires design when interaction/usability changes materially (`plan:20-22`; `tasks:10-11`).

## Dependency and task-readiness checks

- The declared dependency graph is acyclic (`tasks:80-96`). `SAAS-45` publishes the base modules before `SAAS-46`; `SAAS-47` and `SAAS-48` consume supervisor/transport interfaces; `SAAS-49` validates/distributes the complete shared harness; SaaS adapter work waits for the merged/installed shared version and local validation/docs (`tasks:59-69`, `:165-168`, `:205-208`, `:236-239`, `:279-310`, `:404-407`).
- All eight code-bearing children target exactly one repository and one primary PR. The three operational children have bounded external outcomes and explicitly create no fake PR (`tasks:22-29`, `:100-120`, `:409-473`).
- Each child has a concrete goal, likely files/modules, acceptance criteria, tests, docs impact, dependencies, blocks, non-goals, and handoff/evidence boundary. Cross-repository integration occurs through versioned contracts rather than mixed-repository changes (`tasks:124-407`, `:501-531`).
- The program parent is non-executable and closes only after every child and assembled acceptance proof completes (`tasks:100-120`, `:533-549`).
- No additional Linear child is necessary: the latest provider behavior belongs coherently to existing `SAAS-48`, with propagation and rollout proof in existing `SAAS-52`, `SAAS-54`, and `SAAS-55`.

## Test, rollout, and rollback checks

- Primary versus assembled test ownership is explicit for every contract area, and lower-level fixtures cannot replace the SaaS project-boundary rerun (`tasks:475-499`).
- Exact-head and exact-merge local gates are fixed by repository rather than implementer choice; no hosted gate is silently optional or universal (`plan:467-474`; `tasks:520-529`).
- Windows path safety, simultaneous allocation, exact resume, native/workflow-managed Handoff distinction, reservations, two-scheduled-worktree recovery, permission denial, redaction, publication refusal, evidence convergence, runtime QA, and no-hosted-check behavior all have explicit positive and negative cases (`plan:875-956`; `tasks:156-163`, `:196-203`, `:270-277`, `:333-335`, `:399-402`, `:490-499`).
- Rollout is ordered: audit PASS, Linear description update, explicit implementation approval, shared code/distribution, SaaS quality/docs/disabled adapter, Linear migration, attended ntfy/refusal/pilot proof, then one observed five-minute Scheduled task (`plan:1008-1023`; `tasks:411-473`).
- Rollback pauses/removes scheduling and eligibility while preserving machine state, reservations, worktrees, branches/PRs, evidence, and provider-paused operations until attended reconciliation makes cleanup safe (`plan:1025-1034`; `tasks:430`, `:452`, `:473`).

## Repository truth checks

### `ai-config`

- `src/` is canonical and `dist/` is generated (`C:\dev\luchdom\ai-config\AGENTS.md:16-19`; `C:\dev\luchdom\ai-config\README.md:12-19`, `:126-132`). Tasks target canonical `src`, then build and temporary sync/parity validation; they do not hand-edit installed projections.
- `scripts/validate.py` does not exist yet. `SAAS-45` explicitly creates the first aggregate and later shared tasks extend its manifest, so the local-only gate has a clear owner rather than pretending current evidence exists (`tasks:135-168`, `:284-310`).
- Current build renders Codex, Claude, Copilot, Cursor, skills, and project templates (`C:\dev\luchdom\ai-config\scripts\build.py:87-100`, `:118-165`); sync installs user-level skills/agents and marker-manages project guidance (`C:\dev\luchdom\ai-config\scripts\sync.py:18-37`, `:93-197`). `SAAS-49`'s source/dist/temporary-installed parity work is therefore feasible.
- Current templates still say skill references are portable summaries (`C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md:4-15`), confirming that the planned canonical-ownership change is an intentional implementation target, not assumed current truth.

### `saas`

- Current repo guidance still has two modes, a one-shot `Build it all` trigger, flat artifact naming, and `codex/LUC-*` examples (`C:\dev\luchdom\saas\AGENTS.md:138-175`, `:177-230`). Current Linear/decision docs still require `Ready for Codex` and Slack (`C:\dev\luchdom\saas\docs\LINEAR.md:3-17`; `C:\dev\luchdom\saas\docs\DECISIONS.md:34-48`). These are correctly scoped migration targets for `SAAS-51`/`SAAS-53`, not prerequisites silently assumed complete.
- `pwsh ./scripts/validate-all.ps1` already aggregates tooling, architecture, docs, web type/build, smoke, .NET build, and tests and exits nonzero on failure (`C:\dev\luchdom\saas\scripts\validate-all.ps1:28-102`). The plan preserves it as the local authority and makes its runtime-QA surface deterministic.
- Playwright is not currently pinned in the web manifest (`C:\dev\luchdom\saas\apps\web\package.json:21-26`) and smoke currently downloads a floating CLI (`C:\dev\luchdom\saas\scripts\smoke.ps1:370-410`). `SAAS-50` correctly owns the exact dependency pin and repository-local runtime surface.
- The existing GitHub Actions workflow exists and runs the aggregate on Ubuntu (`C:\dev\luchdom\saas\.github\workflows\validate.yml:1-32`), but the current plan/tasks neither edit it nor treat its result as phase-1 authority. Its existence is compatible with provider-refusal handling and does not reintroduce a pipeline requirement.

## Linear mapping decision

Preserve the existing hierarchy exactly:

- `SAAS-44` remains the non-executable parent.
- `SAAS-45` through `SAAS-52` remain the eight single-repository code-bearing children.
- `SAAS-53` through `SAAS-55` remain the three manual-operational outcomes.
- Every program-building record remains `Backlog` without `autonomous`.
- No new child is justified by this audit.

No Linear record was read or mutated by this audit. Updating the existing records in place remains a separate unauthorized administration step even though this audit gate now permits it to be proposed (`plan:979-998`; `tasks:52-78`).

## Gate and next action

The plan/task pair is **finalized at the pre-implementation gate**.

The next possible actions are separate and still require the appropriate authority:

1. update `SAAS-44` through `SAAS-55` descriptions, titles, and dependencies in place with readback and no duplicates;
2. obtain an explicit user `Implement` instruction before source changes, build/sync installation, Git/GitHub mutation, Linear workflow migration, ntfy setup/publishing, pilot execution, or schedule enablement.

No further revise/re-audit loop is required unless the requirements, repositories, or selected architecture materially change.

## Sources consulted (paths and line citations)

### Requirements and workflow artifacts

- User requirements and clarifications in the current conversation, especially that phase 1 must work locally and no CI pipeline is required now
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-plan.md:1-1161`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-tasks.md:1-603`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-audit.md:1-137`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-re-audit.md:1-137`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-18-three-delivery-workflows-task-audit.md:1-244`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-18-three-delivery-workflows-task-re-audit.md:1-199`

### Audit policy and `ai-config` truth

- `C:\dev\luchdom\ai-config\AGENTS.md:1-31`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md:1-39`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\SKILL.md:1-41`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\audit-checklist.md:1-20`
- `C:\dev\luchdom\ai-config\README.md:1-141`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md:1-147`
- `C:\dev\luchdom\ai-config\scripts\build.py:1-176`
- `C:\dev\luchdom\ai-config\scripts\sync.py:1-201`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py:1-74`

### SaaS repository truth

- `C:\dev\luchdom\saas\AGENTS.md:1-246`
- `C:\dev\luchdom\saas\docs\LINEAR.md:1-46`
- `C:\dev\luchdom\saas\docs\DECISIONS.md:1-48`
- `C:\dev\luchdom\saas\docs\QUALITY.md:1-72`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1:1-102`
- `C:\dev\luchdom\saas\scripts\smoke.ps1:350-436`
- `C:\dev\luchdom\saas\apps\web\package.json:1-27`
- `C:\dev\luchdom\saas\.github\workflows\validate.yml:1-32`

### Read-only checks

- `git status --short` in both repositories
- tracked-path existence and `Test-Path` checks, including confirmation that `scripts/validate.py` is not yet present and that the requested re-audit file did not exist before this report
- targeted case-insensitive text searches across the current plan/tasks for hosted CI/check authority, publication blocking, provider refusal, settings/bypass prohibition, and pipeline scope
