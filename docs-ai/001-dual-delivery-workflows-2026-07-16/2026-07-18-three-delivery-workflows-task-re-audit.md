# Three Delivery Workflows — Independent Plan and Task Re-audit

## Verdict

**FAIL — one P2 contract correction remains, then repeat the independent plan-plus-task audit.**

The revised plan and task breakdown fully resolve the four findings from `2026-07-18-three-delivery-workflows-task-audit.md`, including the user's authoritative local-only clarification. Phase 1 now adds no CI pipeline and treats repository-specific clean local validation, review, documentation checks, and applicable runtime QA as its evidence gates.

One new contradiction prevents a final PASS: the documents correctly make hosted checks non-authoritative, but repeatedly claim that GitHub branch-protection/check state cannot *block* delivery. A remote repository can still refuse the push or squash-merge operation. The engine may ignore hosted checks as evidence; it cannot make provider enforcement disappear. This edge needs a deterministic fail-closed pause/recovery contract and fixture coverage.

No product clarification and no new Linear child are required. Preserve `SAAS-44` through `SAAS-55` and correct the existing `SAAS-48` scope/tests plus the shared wording in the plan and affected SaaS tasks.

This audit created only this report. It did not revise the plan/tasks, implement code, build/sync/install, mutate Git/GitHub/Linear, configure or publish ntfy, run a pilot, or create/enable a schedule.

## Findings by severity

### P0 — Critical

None.

### P1 — High

None.

### P2 — Medium

#### P2.1 — Non-authoritative hosted checks are conflated with GitHub being unable to enforce them

**Confirmed evidence**

- The user's local-only clarification is represented correctly: no hosted check is required and no pipeline is added (`2026-07-17-three-delivery-workflows-plan.md:39-50`, `:115-119`, `:459-472`).
- The plan then makes a stronger operational claim: hosted status, provider availability, and branch-protection configuration can never block, pass, or authorize a transition (`2026-07-17-three-delivery-workflows-plan.md:115-118`, especially `:116`; `:459-463`; `:924`).
- The task breakdown repeats that arbitrary Actions results cannot block a transition and requires a test for that assertion (`2026-07-17-three-delivery-workflows-tasks.md:245-264`, especially `:252`, `:262`). `SAAS-50` explicitly says branch-protection state cannot block delivery (`2026-07-17-three-delivery-workflows-tasks.md:310-321`, especially `:313`).
- The same documents require an actual GitHub squash merge and independently re-read mergeability before it (`2026-07-17-three-delivery-workflows-plan.md:654-672`, especially `:667-670`; `2026-07-17-three-delivery-workflows-tasks.md:253-264`, especially `:257-259`). They also forbid settings changes or bypass behavior (`2026-07-17-three-delivery-workflows-plan.md:449-457`).
- The plan has a generic transient GitHub PR/mergeability wait (`2026-07-17-three-delivery-workflows-plan.md:640-650`) and a generic external-prerequisite pause (`:698-707`), but neither reconciles the absolute “cannot block” wording or assigns the stable provider-enforcement rejection test.
- Current read-only repository inspection reduces the immediate rollout risk but does not validate the reusable absolute claim: `ai-config` reports `main` as unprotected and no rulesets; the private SaaS repository's protection/ruleset endpoints return a plan/visibility `403`, so this audit cannot prove a protection rule exists or is absent. The tracked SaaS Actions workflow does exist and runs `./scripts/validate-all.ps1 -CI` (`C:\dev\luchdom\saas\.github\workflows\validate.yml:1-9`, `:26-32`).

**Impact**

An implementation following the current acceptance text could treat a provider-refused merge as impossible or retry forever, even though it must not query hosted checks, weaken repository rules, bypass protection, or mark the issue `Done`. This is not a request to add CI. It is a missing external-enforcement failure transition in the otherwise deterministic merge state machine.

The finding is P2 rather than P1 because the authoritative quality gate is now locally complete, both current repositories have a feasible local validation path, and current read-only inspection did not confirm an active required-check rule. The gap affects safe reusable publication/rollout behavior, not the correctness of the local validation evidence itself.

**Deterministic correction — no user decision required**

1. Replace every “hosted status/provider/branch protection cannot block delivery/transition” assertion with the narrower invariant: hosted checks are never required, queried, polled, waited on as a gate, or accepted as evidence/authorization in phase 1.
2. State separately that GitHub may physically refuse push or merge because of repository policy, rulesets, required checks, merge queues, provider availability, permissions, or other enforcement. The adapter must never bypass or mutate those controls.
3. Extend the existing external-wait/failure contract:
   - a demonstrably transient GitHub transport/mergeability refusal stays `In Review + autonomous`, releases only the run lease, retains the repository reservation/persistent worktree, and uses a bounded retry;
   - a stable or ambiguous repository-policy refusal fails closed, never reaches `Done`, records the exact redacted provider response and current PR/head/local attestations, pauses under the existing `needs-human` or independently actionable `blocked` classification, retains protected state until reconciliation, and notifies through Linear plus ntfy;
   - resolving it requires attended repository-policy action or a separately planned provider capability, not automatic check polling, settings mutation, or CI work in this program.
4. Assign `SAAS-48` fixture tests for pending/failing required-check, branch/ruleset, merge-queue, permission, and provider-unavailable merge refusals. Assert no bypass/settings mutation/check query, no duplicate merge, no `Done`, correct retry-versus-pause state, reservation/worktree preservation, redacted evidence, and idempotent resume after the external condition is independently resolved.
5. Update `SAAS-50`, `SAAS-51`, and `SAAS-52` wording/fixtures only as needed to preserve “non-authoritative local-only validation” while acknowledging provider-enforced publication refusal. Do not edit `.github/workflows/validate.yml` and do not add a pipeline.

### P3 — Low / precision

None beyond the assigned implementation precision already present in the plan/tasks.

## Failed-audit resolution readback

Every finding from `2026-07-18-three-delivery-workflows-task-audit.md` was independently checked against both revised artifacts.

| Failed-audit finding | Independent readback | Result |
|---|---|---|
| `P1.1` — impossible exact-head CI gate | Phase 1 now has an explicit repository matrix: `ai-config` creates and extends `python .\scripts\validate.py`; SaaS uses `pwsh ./scripts/validate-all.ps1` plus applicable exact-head real HTTP/Playwright QA. Both rerun the aggregate from a separate clean worktree at the exact returned merge SHA. No hosted check is required and no pipeline task exists (`three-delivery-workflows-plan.md:39-50`, `:115-119`, `:459-472`; `three-delivery-workflows-tasks.md:45-48`, `:152-160`, `:200`, `:229`, `:264`, `:287-292`, `:320-323`, `:500-507`). | **Resolved.** P2.1 narrows only the separate remote-enforcement failure wording; it does not restore CI as a gate. |
| `P1.2` — circular/duplicate `SAAS-45`/`SAAS-46` ownership | `SAAS-45` solely owns the versioned identity/state-home/allocation mutex/registry/exact binding/local allocation-resume-attach/registry-only workflow-managed Handoff package. `SAAS-46` imports those exact modules and adds lease/capability, editing reservations, supervisor state/journal, persistent worktrees, permissions/recovery, and assembled live-reservation transfer. Base and assembled tests are separate and dependency direction is one-way (`three-delivery-workflows-plan.md:340-342`, `:496-526`, `:610-625`, `:762-767`, `:962-981`; `three-delivery-workflows-tasks.md:121-165`, `:167-205`). | **Resolved.** No circular acceptance or duplicate primitive remains. |
| `P2.1` — unsafe/ambiguous Windows work key and path | The work-key example now uses one concrete provider value and explains provider/local alternatives; model/user values cannot override the key. The plan/task define bounded slug grammar, invalid/reserved-name rejection, case-insensitive allocation, strict-descendant containment, reparse rejection before/after allocation, and complete Windows test cases (`three-delivery-workflows-plan.md:291-322`, `:324-342`, `:360-384`; `three-delivery-workflows-tasks.md:141-160`). | **Resolved.** |
| `P3.1` — custom Handoff confused with native Codex Hand off | Both artifacts consistently name **workflow-managed Handoff**, explicitly deny authority transfer from native **Hand off**, define mismatch recovery, separate registry-only from live-reservation transfer, and require superseded-source write rejection (`three-delivery-workflows-plan.md:340-355`, `:612-625`, `:870-876`; `three-delivery-workflows-tasks.md:30-33`, `:149-158`, `:183-198`, `:343`, `:377`, `:471-479`). | **Resolved.** |

## New contradiction checks

### Checks that passed

- **Task graph and ownership:** the declared graph is acyclic; `SAAS-45` is the sole base-package owner and all autonomous layers consume it. Every code child names one repository and one primary PR; operational children produce external/state-home evidence without fake PRs (`three-delivery-workflows-tasks.md:50-94`, `:456-469`, `:481-509`).
- **Implementation gates:** planning/task audit must pass before Linear descriptions change, and separate explicit `Implement` approval remains required before source, sync/install, migration, pilot, ntfy, Git/GitHub, or schedule work (`three-delivery-workflows-plan.md:18-20`, `:786-794`, `:991-1006`; `three-delivery-workflows-tasks.md:3-15`, `:575-579`).
- **Three workflow semantics:** autonomous, semi-autonomous, and manual entries have distinct advancement/authority policies over one specialist stack; semi/manual cannot self-elevate and manual mode cannot auto-advance (`three-delivery-workflows-plan.md:52-66`, `:124-156`, `:187-287`; `three-delivery-workflows-tasks.md:133-140`, `:159`).
- **Local goals and tracking:** local work can allocate without Linear, later attach atomically, and resume only by exact registered identity. Same-repository deliverable edits remain reservation-protected while another repository does not block SaaS (`three-delivery-workflows-plan.md:318-358`, `:420-447`; `three-delivery-workflows-tasks.md:141-159`, `:183-197`).
- **Linear ordinary states/labels:** eligibility is `Todo + autonomous`; `Ready for Codex` is migration input only and must reach zero references before manual deletion. Program-building issues remain `Backlog` without `autonomous` (`three-delivery-workflows-plan.md:102-108`, `:576-608`, `:682-696`; `three-delivery-workflows-tasks.md:69-76`, `:394-413`).
- **Global WIP and reservations:** one tracked SaaS `In Progress`/`In Review` slot composes with same-repository issue/editing reservations, lease reconciliation, protected stale-work behavior, Release, abandonment, and workflow-managed Handoff (`three-delivery-workflows-plan.md:344-356`, `:436-447`, `:576-625`; `three-delivery-workflows-tasks.md:183-198`, `:216-228`, `:371-385`).
- **Stable state and persistent worktrees:** machine state and issue/gate worktrees live outside every scheduled checkout; two-control-worktree, cleanup, crash/replay, containment, status, and recovery proofs are assigned (`three-delivery-workflows-plan.md:496-526`, `:733-756`, `:897-925`; `three-delivery-workflows-tasks.md:177-200`, `:371-385`, `:436-454`).
- **Least privilege:** the plan/tasks consistently use `workspace-write`, `sandbox_workspace_write`, `approval_policy = "never"`, explicit roots/hosts/loopback/commands, a minimal environment, and mutation-free preflight; they explicitly reject beta named-profile mixing and full-access fallback (`three-delivery-workflows-plan.md:528-551`; `three-delivery-workflows-tasks.md:30-33`, `:188-201`, `:378-385`).
- **Evidence and exact SHA:** draft tracked evidence precedes the executable/final heads; evidence-only classification, final-head aggregate/review and QA rerun/reuse, exact returned merge identity, clean merge-SHA validation, same-issue repairs, and no post-merge repository mutation are owned and tested (`three-delivery-workflows-plan.md:627-672`; `three-delivery-workflows-tasks.md:236-269`, `:481-507`).
- **Real behavior QA:** `SAAS-50` owns pinned repository Playwright, real HTTP/browser behavior, Development/loopback enforcement, unique resources, bounded readiness, production-secret rejection, and cleanup. Project/pilot tasks reassemble it (`three-delivery-workflows-tasks.md:301-327`, `:360-390`, `:415-434`).
- **Searchable docs/wiki:** `SAAS-51` owns three-mode/current-state migration, local-goal guidance, Handoff terminology, MkDocs `1.6.1`, strict build/search/navigation, drift rules, and history exceptions (`three-delivery-workflows-tasks.md:329-358`).
- **Notifications and follow-ups:** Linear remains the durable decision source; ntfy is actionable attention; Scheduled is run visibility. Follow-up issues are limited to deduplicated independently actionable prerequisites, while product/security/cost decisions use `needs-human` (`three-delivery-workflows-plan.md:674-707`; `three-delivery-workflows-tasks.md:207-234`, `:415-434`).
- **Rollout and rollback:** migration, attended publish/pilot, one five-minute task, two-worktree recovery, kill switch, observation, and local-first backlog expansion are ordered after merged/installed code and have reversible evidence (`three-delivery-workflows-plan.md:844-858`, `:991-1016`; `three-delivery-workflows-tasks.md:394-454`).

### Check requiring correction

- **Hosted checks versus remote enforcement:** local attestations are correctly authoritative, but provider enforcement can still refuse the required GitHub operation. Resolve P2.1 without introducing CI/check authority.

## Requirements, task, test, and rollout ownership

| Requirement | Primary task owner(s) | Assembled proof | Audit result |
|---|---|---|---|
| Three entries over one specialist stack | `SAAS-45`, `SAAS-49` | installed semantics + SaaS docs | Covered |
| Local goal, exact resume, later attachment, Windows-safe allocation | `SAAS-45` | `SAAS-49`, `SAAS-52` | Covered |
| Stable home, lease/state/reservations/persistent worktrees/permissions | `SAAS-46` | `SAAS-52`, `SAAS-55` | Covered |
| Linear WIP/selection/decisions/follow-ups and ntfy | `SAAS-47` | `SAAS-53`, `SAAS-54` | Covered |
| PR/squash/exact-SHA local evidence and repair | `SAAS-48` | `SAAS-52`, `SAAS-54` | Covered except provider-refusal transition in P2.1 |
| Build/sync/source-dist-installed parity | `SAAS-49` | installed-version preflight in `SAAS-52` | Covered |
| SaaS local aggregate and real HTTP/Playwright QA | `SAAS-50` | `SAAS-52`, `SAAS-54` | Covered; correct impossible branch-protection wording |
| Three-mode docs and searchable MkDocs wiki | `SAAS-51` | `SAAS-52` doc/config checks | Covered |
| Thin adapter/config/prompt/kill switch | `SAAS-52` | attended pilot and Scheduled rollout | Covered; inherit P2.1 failure behavior |
| Ordinary-state/label migration | `SAAS-53` | complete before/after/readback evidence | Covered |
| Notification/decision/end-to-end pilot | `SAAS-54` | one separate bounded product leaf | Covered |
| Five-minute recurring Codex task | `SAAS-55` | observed no-op/resume/recovery/terminal runs | Covered |

## Repository truth checks

### `ai-config`

- `src/` is canonical and `dist/` is generated/ignored (`C:\dev\luchdom\ai-config\AGENTS.md:16-19`; `C:\dev\luchdom\ai-config\.gitignore:1`). The tasks correctly target source and regenerate/test projections rather than hand-editing `dist`.
- `scripts/validate.py` does not yet exist; `SAAS-45` explicitly creates it and includes the first complete manifest (`three-delivery-workflows-tasks.md:121-165`). Current local surfaces are `scripts/build.py` and `scripts/test_sync_markers.py`; build validates source and renders all tool projections (`C:\dev\luchdom\ai-config\scripts\build.py:87-100`, `:118-165`).
- Current sync supports Codex, Claude, Copilot, and project-local Cursor and defaults to rebuilding first (`C:\dev\luchdom\ai-config\scripts\sync.py:18-25`, `:93-173`, `:176-197`), so temporary-home/project parity work is feasible.
- Current templates still contain the retired “portable summaries” ownership sentence (`C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md:4-6` and corresponding Claude/Cursor templates), confirming that `SAAS-45`/`SAAS-49` own a real intentional migration.

### `saas`

- Current `AGENTS.md` still documents two modes, `Build it all`, flat artifact names, and `codex/LUC-*` (`C:\dev\luchdom\saas\AGENTS.md:138-175`, `:177-227`); `SAAS-51` correctly owns their current-guidance migration.
- Current `docs/LINEAR.md`, `docs/SLACK-APPROVALS.md`, and drift rules still require `Ready for Codex`/Slack/old mode language (`C:\dev\luchdom\saas\docs\LINEAR.md:5-17`; `C:\dev\luchdom\saas\docs\SLACK-APPROVALS.md:1-35`; `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1:23-30`). These are implementation targets, not current blockers.
- `pwsh ./scripts/validate-all.ps1` already aggregates tooling, architecture, docs, web type/build, smoke, .NET build, and tests with nonzero failure (`C:\dev\luchdom\saas\scripts\validate-all.ps1:1-102`). Its current `cmd /c` web commands are locally usable on the user's Windows environment; cross-platform hosted repair is intentionally out of scope.
- Playwright is not currently pinned in `apps/web/package.json` (`C:\dev\luchdom\saas\apps\web\package.json:21-26`), and `smoke.ps1` currently downloads a floating Playwright CLI (`C:\dev\luchdom\saas\scripts\smoke.ps1:370-410`); `SAAS-50` correctly owns the local pin and deterministic runtime surface.
- `mkdocs.yml` and `requirements-docs.txt` do not yet exist; `SAAS-51` explicitly creates them and assigns strict local build/search/navigation tests.
- The existing Actions workflow is real but out of edit/quality-authority scope (`C:\dev\luchdom\saas\.github\workflows\validate.yml:1-32`). P2.1 requires only honest handling if GitHub itself refuses publication; it does not require querying or repairing the workflow.

## Linear mapping decision

The corrected task graph still fits the existing hierarchy:

- retain `SAAS-44` as the non-executable parent;
- retain `SAAS-45` through `SAAS-52` as the eight single-repository code-bearing children;
- retain `SAAS-53` through `SAAS-55` as three manual-operational outcomes;
- assign the provider-enforcement failure transition/tests to existing `SAAS-48` and propagate wording/config fixtures through existing `SAAS-50`/`51`/`52`;
- keep every program-building issue in `Backlog` without `autonomous` and make no Linear mutation before a PASS.

No new child is justified.

## Gate and next action

1. Revise the plan and task documents only for P2.1. Preserve both existing audit records.
2. Repeat a fresh independent plan-plus-task audit. PASS requires no actionable P0/P1/P2 finding.
3. Only after PASS, update `SAAS-44` through `SAAS-55` descriptions/dependencies in place with readback and no duplicates.
4. Explicit user `Implement` approval is still required before code, build/sync installation, Linear workflow migration, Git/GitHub mutation, ntfy configuration/publishing, pilot execution, or schedule enablement.

The plan/tasks are therefore **not yet finalized for the pre-implementation gate**, but the remaining correction is deterministic and does not need user input. No CI pipeline or hosted-check authority should be introduced while resolving it.

## Sources consulted (paths and read-only checks)

### User requirement and workflow artifacts

- User requirements and clarifications in the current conversation, especially: phase 1 must work locally and no CI pipeline is required now
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-tasks.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-18-three-delivery-workflows-task-audit.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-re-audit.md`

### Audit policy and `ai-config` truth

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\.gitignore`
- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\SKILL.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\audit-checklist.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\task-template.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md`
- `C:\dev\luchdom\ai-config\src\project-templates\claude\CLAUDE.md`
- `C:\dev\luchdom\ai-config\src\project-templates\copilot\.github\copilot-instructions.md`
- `C:\dev\luchdom\ai-config\src\project-templates\cursor\AGENTS.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py`

### SaaS repository truth

- `C:\dev\luchdom\saas\AGENTS.md`
- `C:\dev\luchdom\saas\README.md`
- `C:\dev\luchdom\saas\docs\HARNESS.md`
- `C:\dev\luchdom\saas\docs\WORKFLOW.md`
- `C:\dev\luchdom\saas\docs\LINEAR.md`
- `C:\dev\luchdom\saas\docs\DECISIONS.md`
- `C:\dev\luchdom\saas\docs\QUALITY.md`
- `C:\dev\luchdom\saas\docs\AI-TOOLING.md`
- `C:\dev\luchdom\saas\docs\LOCAL-DEVELOPMENT.md`
- `C:\dev\luchdom\saas\docs\SLACK-APPROVALS.md`
- `C:\dev\luchdom\saas\.github\workflows\validate.yml`
- `C:\dev\luchdom\saas\apps\web\package.json`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\scripts\smoke.ps1`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`

### Read-only environment/repository checks

- `git status --short`, `git rev-parse --show-toplevel`, `git remote -v`, and tracked-path existence checks in both repositories
- `gh auth status`
- read-only GitHub API calls for `luchdom/ai-config` and `luchdom/saas` `main` branch protection and repository rulesets; no setting or repository state was changed
