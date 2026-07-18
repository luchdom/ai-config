# Three Delivery Workflows — Revised Execution Tasks

## Task document status

- Current plan: `2026-07-17-three-delivery-workflows-plan.md`
- Earlier plan-only re-audit: `2026-07-17-three-delivery-workflows-re-audit.md` — historical **PASS** for the prior plan revision
- Plan-plus-task audit: `2026-07-18-three-delivery-workflows-task-audit.md` — **FAIL**; this document has been revised in place for all P1/P2 findings and the P3 naming note
- Plan-plus-task re-audit: `2026-07-18-three-delivery-workflows-task-re-audit.md` — **FAIL** for one provider-enforced publication-refusal P2; this document now includes the deterministic correction and still requires another fresh independent re-audit
- Workflow artifact folder: `001-dual-delivery-workflows-2026-07-16`
- Tasking date: 2026-07-17; in-place audit-resolution revision: 2026-07-18
- Product design: **not required**; this program changes delivery policy, automation, documentation, and test infrastructure rather than product UI
- Implementation status: **not approved and not started**
- Linear status: existing parent `SAAS-44` and children `SAAS-45` through `SAAS-55` remain provisional in `Backlog`, with no `autonomous` label; this tasking pass performs no Linear mutation
- Supersession: this document replaces `2026-07-17-dual-delivery-workflows-tasks.md` only as the forward execution breakdown for the revised three-workflow architecture. The earlier task document and its audits remain unchanged historical evidence.
- Authority: creating this document does not authorize code changes, build/sync, installation, Linear/Git/GitHub mutation, ntfy publishing/configuration, pilot execution, workflow migration, or schedule enablement
- Required next gate: a **fresh independent re-audit** of the revised plan and this revised task breakdown. This task document does not claim PASS. Linear updates and explicit user `Implement` approval remain later gates.

## Audit and readiness notes

This task document has been revised after both failed 2026-07-18 plan-plus-task audits. It adopts the user's authoritative clarification that phase 1 must work locally and requires no hosted CI pipeline, and it now treats a provider-enforced push/PR/merge refusal as real state-machine input. The corrected plan is complete enough to split into executable work, but the plan/task pair still requires another fresh independent re-audit. No blocking product, design, or architecture decision remains.

The split preserves the current Linear hierarchy and assigns each existing child one cohesive outcome:

1. five code-bearing `ai-config` children for shared policy, deterministic state, external integrations, GitHub delivery gates, and distribution;
2. three code-bearing `saas` children for repository validation/runtime QA, documentation/wiki, and the thin adapter;
3. three manual-operational children for Linear migration, notification/pilot proof, and scheduled rollout;
4. one non-executable program parent for integration closeout.

No code-bearing task edits both repositories. Every code-bearing child targets one repository and one primary PR. Operational children produce durable readback evidence and must not create empty branches or fake PRs.

The audit precision notes are mandatory task-level constraints:

- Scheduled permission work must use the established Codex configuration model consistently: `sandbox_mode = "workspace-write"`, `sandbox_workspace_write`, `approval_policy = "never"`, and explicit tested command rules. It must **not** mix that model with beta named permission profiles. Host/network allowlisting, exact loopback target/port validation, and deterministic wrapper/command validation remain separate controls.
- Every custom transfer is named **workflow-managed Handoff** and is distinct from Codex desktop's native **Hand off** action. Native **Hand off** alone never changes the workflow registry, lease, or reservation. Tests must prove that failure leaves the original worktree authoritative, while successful workflow-managed Handoff makes the destination authoritative and prevents the superseded source worktree from performing any later workflow-managed write.

Confirmed program constraints carried into all tasks:

- The three user-facing entries are `$linear-delivery-loop`, `$goal-to-delivery`, and `$spec-driven-delivery`.
- The entries compose one shared specialist pipeline; they do not duplicate planner, designer, tasker, auditor, implementer, code-reviewer, QA, or documentation agents.
- `$goal-to-delivery` defaults to a local goal and `working-tree` completion and never selects queue work or self-elevates to autonomous mode.
- `$spec-driven-delivery` executes exactly the requested stage and never auto-advances; material clarification is returned to the user.
- `$linear-delivery-loop` is the only autonomous entry and accepts only one deterministic adapter-prepared issue/capability.
- `Ready for Codex` is neither an execution state nor an operational concept. Eligibility is ordinary state `Todo` plus label `autonomous`, after issue-contract and dependency checks.
- SaaS has one global Linear WIP slot across `In Progress` and `In Review`, plus one machine-stable same-repository reservation protecting autonomous and interactive editing.
- Local work in another normalized repository has a separate supervisor home and cannot block SaaS.
- Autonomous code reaches `Done` only after one primary PR, squash merge, and clean validation of the exact returned merge SHA.
- Linear is the durable unattended decision record, ntfy is the actionable attention channel, and Codex Scheduled provides run visibility. Telegram and Slack are excluded.
- Phase-1 authorization is local-only. No hosted pipeline/check is required or authoritative in either repository, and no task in this program adds or repairs one. `ai-config` uses `python .\scripts\validate.py`; SaaS uses `pwsh ./scripts/validate-all.ps1` plus applicable real HTTP/Playwright acceptance at the exact PR head. Both aggregate commands rerun from clean isolated worktrees at the exact returned squash-merge SHA.
- Hosted checks are never phase-1 evidence or authorization and are never queried, polled, or waited on. GitHub may still physically refuse push, PR creation/update, or merge because of provider availability, permissions, required checks, branch protection/rulesets, merge queues, or other policy; the adapter preserves protected state and follows the deterministic retry/pause contract owned by `SAAS-48` without bypassing or weakening those controls.
- Locally runnable product work—authentication, tenant isolation, organizations/users, roles/permissions, product features, and local billing-domain behavior—precedes AWS, PostHog, hosted pipelines, live providers, and other external integrations.

## Linear program map

Preserve these records and update them in place only after the plan-plus-task audit passes. Stable task IDs remain useful in repository evidence even though the Linear title/description will be revised later.

| Stable task ID | Linear | Kind | Target | Initial state/label | Revised achievable outcome | Blocked by |
|---|---|---|---|---|---|---|
| `DDW-PROG-001` | `SAAS-44` | program parent | none | `Backlog`; no `autonomous` | Deliver and verify the three reusable delivery workflows | all children for closeout |
| `DDW-AIC-001` | `SAAS-45` | code-bearing | `ai-config` | `Backlog`; no `autonomous` | Add three entry skills, canonical shared protocol, sole base local-work modules, workflow-init/registry-only workflow-managed Handoff, specialist doctrine, and initial aggregate local gate | none |
| `DDW-AIC-002` | `SAAS-46` | code-bearing | `ai-config` | `Backlog`; no `autonomous` | Consume the versioned base modules and add supervisor state, lease/capability, reservations, persistent issue/gate worktrees, permission preflight, recovery, and assembled reservation-aware workflow-managed Handoff | `SAAS-45` |
| `DDW-AIC-003` | `SAAS-47` | code-bearing | `ai-config` | `Backlog`; no `autonomous` | Add deterministic Linear selection, decisions/follow-ups, and ntfy | `SAAS-46` |
| `DDW-AIC-004` | `SAAS-48` | code-bearing | `ai-config` | `Backlog`; no `autonomous` | Add deterministic Git/GitHub publication, exact-SHA local gates/evidence, provider-refusal retry/pause/recovery, merge, and repair without hosted-check integration or settings bypass | `SAAS-46`, `SAAS-47` |
| `DDW-AIC-005` | `SAAS-49` | code-bearing | `ai-config` | `Backlog`; no `autonomous` | Validate and distribute the complete three-workflow harness with version/hash/reference parity | `SAAS-45`–`SAAS-48` |
| `DDW-SAS-002` | `SAAS-50` | code-bearing | `saas` | `Backlog`; no `autonomous` | Make the authoritative local aggregate and real HTTP/Playwright QA pinned, isolated, and reliable; hosted Actions remain non-authoritative and out of scope | `SAAS-45` |
| `DDW-SAS-001` | `SAAS-51` | code-bearing | `saas` | `Backlog`; no `autonomous` | Document all three workflows, provider-publication pause/recovery, and the searchable local MkDocs wiki | `SAAS-45`, `SAAS-50` |
| `DDW-SAS-003` | `SAAS-52` | code-bearing | `saas` | `Backlog`; no `autonomous` | Integrate the disabled thin SaaS adapter, least-privilege configuration, provider-refusal propagation fixtures, and Scheduled prompt | `SAAS-49`, `SAAS-50`, `SAAS-51` |
| `DDW-OPS-001` | `SAAS-53` | manual-operational | none | `Backlog`; no `autonomous` | Migrate Linear to ordinary states/labels and refine the autonomous backlog | `SAAS-52` |
| `DDW-OPS-002` | `SAAS-54` | manual-operational | none | `Backlog`; no `autonomous` | Configure ntfy and pass one attended exact-SHA autonomous pilot | `SAAS-52`, `SAAS-53` |
| `DDW-OPS-003` | `SAAS-55` | manual-operational | none | `Backlog`; no `autonomous` | Enable and observe one five-minute Codex Scheduled heartbeat | `SAAS-54` |

Linear update rules for the later administration step:

- Preserve `SAAS-44` as parent and `SAAS-45` through `SAAS-55` as its children; do not create a replacement program.
- Express the dependency table with blocking relationships and verify it by readback.
- Keep every program-building issue in `Backlog` without `autonomous`. Only a separate audited local-first product leaf may carry `Todo + autonomous` for the attended pilot.
- Record repository key, one observable goal, acceptance criteria, non-goals, dependencies, validation, docs impact, risks, and one-primary-PR requirement in each code-bearing child.
- Record exact actor, timestamp, before/after/readback evidence, and rollback in operational children. They have no repository key or PR requirement.
- Create a new child only if the later independent task audit proves one of these outcomes cannot remain reviewable and achievable. This breakdown does not identify such a need.

## Dependency graph and critical path

The graph is acyclic:

```text
DDW-AIC-001
  -> DDW-AIC-002 -> DDW-AIC-003 -> DDW-AIC-004 -> DDW-AIC-005 ----+
  -> DDW-SAS-002 -> DDW-SAS-001 ----------------------------------+-> DDW-SAS-003
                                                                         -> DDW-OPS-001
                                                                         -> DDW-OPS-002
                                                                         -> DDW-OPS-003
                                                                         -> DDW-PROG-001 closeout
```

Critical path: `DDW-AIC-001` → `DDW-AIC-002` → `DDW-AIC-003` → `DDW-AIC-004` → `DDW-AIC-005` → `DDW-SAS-003` → `DDW-OPS-001` → `DDW-OPS-002` → `DDW-OPS-003` → parent closeout.

`DDW-SAS-002` can proceed after `DDW-AIC-001` while the shared engine is built. `DDW-SAS-001` follows it so the documentation PR is protected by the repaired validation gate. No live Linear migration, ntfy publish, pilot, or schedule work starts before all code children are merged and validated.

## Program parent

### `DDW-PROG-001` / `SAAS-44` — Deliver the three reusable delivery workflows

- **Goal:** coordinate and close the complete cross-repository outcome without treating the parent as executable work.
- **Linear mapping:** program parent; `Backlog`; no `autonomous`; no target repository, branch, commit, or PR.
- **Likely files/modules:** none; this parent owns only the Linear roll-up and linked completion evidence.
- **Scope:** shared workflow policy and engine, SaaS validation/docs/adapter, Linear migration, notification proof, attended pilot, and Scheduled rollout.
- **Acceptance criteria:**
  - All eight code-bearing children are independently merged into their named repository and have exact merge-SHA validation evidence.
  - The three entries exhibit their locked advancement, clarification, authority, tracking, and completion behavior while reusing one specialist pipeline.
  - The canonical cross-tool protocol is owned under `ai-config/src/skills/goal-to-delivery/references/`; generated and installed projections match its version/hash/reference graph.
  - The machine-stable supervisor state survives scheduled-worktree replacement and protects same-repository manual, semi-autonomous, and autonomous work.
  - SaaS has an authoritative local aggregate, a working real HTTP/Playwright QA surface, current three-workflow docs, a searchable MkDocs wiki, and a disabled thin adapter; existing hosted Actions is non-authoritative and untouched.
  - Linear uses only ordinary states plus labels; no operational `Ready for Codex` reference or backlog/autonomous residue remains.
  - One attended autonomous pilot demonstrates decision notification, one-issue/WIP behavior, clean exact-head local gates, review, runtime QA, squash merge, and clean exact-merge-SHA local validation.
  - Provider-enforced push/PR/merge refusal is fixture-proven to retry only bounded demonstrably transient operations, otherwise pause with preserved WIP/reservation/worktree/branch/PR/evidence, and resume only after one exact authorized attended retry; no check query, setting change, bypass, duplicate publication, speculative child, lost protected work, or false `Done` occurs.
  - One five-minute Codex Scheduled task is enabled and observed without duplicate scheduler/worker execution.
  - Rollback, kill switch, pause/archive, reservation recovery, and protected-work cleanup behavior are proven.
- **Validation/evidence:** parent roll-up links every child, primary PR and merge SHA, exact-SHA review/QA/completion records, migration readback, pilot report, scheduled task identifier, early run observations, and rollback instructions.
- **Dependencies:** every child in this document.
- **Blocks:** program completion only; it never occupies Linear WIP.
- **Non-goals:** product features, cloud provisioning, any hosted CI/pipeline work, parallel autonomous issues, Telegram, Slack, Windows Task Scheduler, or an empty parent PR.

## `ai-config` code-bearing children

### `DDW-AIC-001` / `SAAS-45` — Add the shared workflow protocol, sole base local-work package, and initial local gate

- **Goal:** create the canonical reusable delivery contract and three explicit policy entries, plus the sole versioned base modules for deterministic local-work identity, storage, allocation, exact resume/attachment, and registry-only workflow-managed Handoff.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; `Backlog`; no `autonomous`.
- **Likely files/modules:**
  - new `src/skills/goal-to-delivery/SKILL.md` and `references/{delivery-stages.md,artifact-contract.md,clarification-policy.md,quality-gates.md,completion-boundaries.md,work-descriptor.schema.json}`
  - new `src/skills/goal-to-delivery/scripts/` base package with canonical modules for normalized repository identity, stable state-home derivation, allocation mutex, registry, exact physical-worktree binding, Windows-safe allocation/resume/attach, registry-only workflow-managed Handoff, atomic files, containment, and redaction
  - new `src/skills/spec-driven-delivery/SKILL.md` and `src/skills/linear-delivery-loop/SKILL.md` entry-policy shell
  - new `src/agents/code-reviewer.md`; updates to `src/agents/{feature-driver,planner,product-designer,tasker,auditor,qa}.md`
  - new `src/skills/docs-as-code/`; updates to `src/skills/{luchdom-docs,multi-agent-delivery,task-audit-breakdown,qa-verification}/`
  - `src/project-templates/{codex,claude,copilot,cursor}/`, `README.md`, root `AGENTS.md`
  - new `scripts/validate.py` plus focused base-module/semantic tests and fixtures
- **Acceptance criteria:**
  - Exactly three user-facing skills exist with unambiguous descriptions and explicit invocations.
  - `$goal-to-delivery` starts only from a user goal/selected issue, defaults to local plus `working-tree`, auto-advances safe stages, stops at its declared boundary, and rejects forged autonomous mode.
  - `$spec-driven-delivery` validates prerequisites, performs only the named stage, asks one focused material clarification at a time, and never infers Implement/QA/Commit/PR/Merge.
  - `$linear-delivery-loop` accepts only a schema-valid adapter-prepared capability and contains no independent queue-selection or mutation implementation.
  - `src/skills/goal-to-delivery/references/` is the sole canonical cross-tool delivery protocol. Repo guidance owns repo-specific commands and stricter constraints; precedence and fail-closed conflict behavior match the plan.
  - `feature-driver` is only a one-migration-cycle alias to `$goal-to-delivery`, contains no copied workflow doctrine, and never routes autonomous work.
  - One shared specialist set is used by all modes; auditor, code reviewer, runtime QA, and documentation have distinct output/authority contracts.
  - This task solely owns and publishes versioned canonical module paths/schemas for normalized `git rev-parse --git-common-dir` repository identity, verified `<repo-id>`, `%LOCALAPPDATA%\Luchdom\ai-delivery\<repo-id>` or approved absolute override derivation, per-repository allocation mutex, workflow registry, and exact physical-worktree binding. Later tasks import these modules and may not copy or reimplement them.
  - Work keys are accepted only as provider-observed canonical keys or allocator-generated zero-padded sequences. Concrete valid alternatives are provider key `SAAS-123` and local key `001`; a model/user slug cannot set or override the key.
  - Linear keys validate `^SAAS-[1-9][0-9]*$`; local keys validate `^[0-9]{3,}$`. Slugs are deterministic lowercase ASCII, 1–48 characters, and validate `^[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?$`.
  - Unsafe explicit input is rejected before normalization: separators, `.`/`..`, controls, Windows-invalid `< > : " / \\ | ? *`, trailing dot/space, and case-insensitive `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, or `LPT1`–`LPT9` names never become trusted paths.
  - Before and after create-new allocation, the helper case-insensitively checks current `docs-ai/`, `docs-ai/history/`, and registry paths; verifies the resolved final folder is a strict descendant of the intended `docs-ai` root; and rejects symlink, junction, mount, or other reparse-point components/escapes.
  - Workflow-init atomically allocates a unique key/folder/UUID under the base mutex, schema-validates `workflow.json`, registers exact repository/worktree identity, uses bounded collision retry, and quarantines partial state.
  - Resume accepts only exact registered workflow ID, exact artifact path, or unique external ID in a compatible physical worktree; goal/slug/chat/latest-folder inference is rejected.
  - Later Linear attachment is atomic, preserves workflow ID/path/evidence, and prevents duplicate external-ID mappings.
  - Registry-only workflow-managed Handoff validates same repository plus clean/non-overlapping destination, records a redacted patch/manifest, performs no staging/commit/push/branch change, validates the applied result, and updates the registry mapping atomically only after success. It explicitly does not claim transfer of a live reservation or capability.
  - Native Codex **Hand off** is documented as a separate action. Native **Hand off** alone never changes workflow registry/lease/reservation or grants authority; a later mismatch fails closed and directs the caller to the registered source or explicit workflow-managed Handoff/recovery.
  - New artifact producers/consumers use `docs-ai/<work-key>-<slug>/` and dated files while retaining explicit historical-layout read fallback without rewriting history.
  - `python .\scripts\validate.py` is introduced as the authoritative `ai-config` aggregate local gate and includes every build, marker, semantic, base-module, schema, path-safety, and focused contract test available in this PR.
- **Test notes:**
  - Simultaneous allocation covers different/identical goal text, concrete `SAAS-123` versus `001`, create-new and case-only collisions, registry collision, partial-write quarantine, immutable UUID identity, and rejection of model-controlled keys.
  - Windows path tests cover slug lengths 1/48/49, separators, dot segments, traversal, controls, every invalid-character and reserved-device family, trailing dots/spaces, case-insensitive collisions, strict-descendant containment, and symlink/junction/mount/reparse escapes both before and after allocation.
  - Resume/attach covers exact accepted selectors, ambiguous external mapping, incompatible physical worktree, historical paths, and no folder rename.
  - Base workflow-managed Handoff covers failed/ambiguous transfer keeping the source authoritative, successful registry remap, redacted patch/manifest, no implicit Git mutation, and rejection of later registry/artifact writes from the superseded source. It does not simulate a live reservation; that assembled proof belongs only to `DDW-AIC-002`.
  - Native Codex **Hand off** without the helper produces a deterministic fingerprint mismatch, rejects writes, and gives exact recovery instructions.
  - Semantic tests prove three distinct policies, manual no-auto-advance, semi-autonomous no-selection/default boundary, autonomous capability requirement, shared-specialist reuse, and compatibility-router limits.
  - From a fresh isolated worktree at the exact PR head, require clean-before/after and run `python .\scripts\validate.py`; after squash merge, rerun the same command cleanly from a separate fresh isolated worktree at the exact returned merge SHA. Hosted checks are not queried.
- **Documentation impact:** update shared usage, workflow-managed Handoff versus native **Hand off**, local-work/path contract, and source-of-truth/precedence explanations in `README.md`, root `AGENTS.md`, project templates, and relevant skill references. Do not copy the full protocol into repository docs.
- **Dependencies:** none after a fresh passing plan-plus-task re-audit and explicit implementation approval.
- **Blocks:** `DDW-AIC-002`, `DDW-SAS-002`, and `DDW-SAS-001`.
- **Non-goals:** no supervisor lease/capability, editing reservation, persistent autonomous issue/gate worktree, operation journal, permission preflight, Linear/ntfy/GitHub transport, scheduled task, live mutation, hosted CI, build/sync installation, product UI, or duplicate per-mode agent stack.
- **Primary-PR handoff:** publish the sole versioned base module paths/schemas, canonical protocol version, initial aggregate manifest, and exact-PR-head/exact-merge-SHA local attestations for `DDW-AIC-002` consumption.

### `DDW-AIC-002` / `SAAS-46` — Build the machine-stable supervisor, reservation, permissions, and recovery core

- **Goal:** consume the exact versioned `DDW-AIC-001` base local-work package and add the autonomous supervisor, active editing reservations, persistent issue/gate worktrees, least-privilege preflight, recovery/cleanup, and assembled reservation-aware workflow-managed Handoff without reimplementing a base primitive.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; `Backlog`; no `autonomous`.
- **Likely files/modules:**
  - `src/skills/linear-delivery-loop/references/` schemas for project config, prepared iteration, checkpoint, supervisor state, editing reservation, operation journal, and worker result
  - `src/skills/linear-delivery-loop/scripts/agent-worker-engine.ps1`
  - autonomous modules for state/lease/capability, editing reservations, persistent issue/gate worktrees, operations, recovery, redaction, permission preflight, status, retention, cleanup, and reservation-aware transfer
  - fixture adapters and dependency-free tests under the skill
  - version-checked imports of the exact canonical identity/state-home/mutex/registry/worktree-binding/workflow-init/registry-transfer modules from `DDW-AIC-001`
- **Acceptance criteria:**
  - The engine imports and schema/version-checks `DDW-AIC-001`'s sole normalized repository identity, stable-home, base mutex, registry, exact-worktree-binding, and local workflow modules. Build/contract tests reject a duplicate identity, state-home, allocation-mutex, registry, or base transfer implementation anywhere under the autonomous engine.
  - Every linked worktree resolves through those imports to the same verified `%LOCALAPPDATA%\Luchdom\ai-delivery\<repo-id>` or approved absolute `LUCHDOM_DELIVERY_STATE_HOME\<repo-id>`; invalid roots retain the base fail-closed behavior with no later fallback.
  - On top of the base-owned repository metadata/mutex/registry, the supervisor home owns atomic revisioned supervisor state, lease/capability, editing reservations, operation journal, run evidence, final attestations, persistent issue worktrees, and temporary clean exact-SHA gate worktrees.
  - Scheduled worktrees are disposable control surfaces. One issue maps idempotently to one contained persistent worktree under the supervisor home, and autonomous implementation/checkpoints reject the scheduled control worktree.
  - Short OS mutex, renewable run lease, prepared capability nonce, compare-and-swap state transitions, idempotent operations, retry counters, and crash reconciliation prevent concurrent or replayed mutation.
  - Repository reservations cover autonomous, semi-autonomous, and manual repository-deliverable mutation; they record workflow/issue, repository, exact worktree, owner/run, revision, heartbeat/expiry, and dirty/branch/PR summary.
  - Time alone never releases dirty, unmerged, unpushed, open-PR, inaccessible, or ambiguous work. Clean planning-only staleness is reclaimed only after registry/physical/external reconciliation.
  - `Reserve`, `Release`, abandonment reconciliation, and assembled workflow-managed Handoff preserve the state/Linear transition contract; another repository has an independent reservation namespace.
  - Assembled workflow-managed Handoff first validates the base registry-only transfer, then atomically transfers the matching live reservation/capability and revokes the source before reporting success. Native Codex **Hand off** never enters this transition and never transfers authority.
  - `PrepareIteration`, `ApplyCheckpoint`, `Status`, and `ReleaseLease` consume structured files, expose deterministic results, never trust model-supplied identity/authority, and never launch nested `codex exec`.
  - Permission preflight is mutation-free with respect to target repositories and external systems and proves engine/config version, state/mutex/worktree-root access, fixed Git/`gh` capability using a disposable fixture, read-only connectivity/auth, configured loopback behavior, environment minimization, and redaction before claim.
  - Scheduled policy uses only the established `workspace-write` + `sandbox_workspace_write` + `approval_policy = "never"` model and fixed exec rules. It does not add or combine beta named permission profiles and has no full-access fallback.
  - Network host allowlists, exact loopback host/ports, fixed wrapper/Git/`gh` command shapes, writable roots, and minimal child environment are validated as distinct fail-closed controls.
  - Cleanup is engine-owned, path-contained, journaled, and refuses protected/live/ambiguous state; status/recovery is identical from any linked worktree after scheduled-worktree archive/removal.
  - The `ai-config` aggregate remains one command: this task extends the `scripts/validate.py` manifest with supervisor/import-boundary/reservation/permission/recovery tests rather than creating a second gate.
- **Test notes:**
  - Two separate scheduled control worktrees must derive one home/mutex/state, resume one persistent issue worktree, and prevent duplicate operations; deletion/archive of either control worktree must preserve recovery.
  - Cover simultaneous lease/reservation races, expired ambiguous lease, stale revisions, replay, interruption at every state/operation boundary, one-issue-per-run, and terminal/no-second-selection behavior.
  - Cover manual selected-issue planning versus autonomous preflight, local SaaS implementation versus claim, reservation renew/staleness, dirty-work fail-close, Release/workflow-managed Handoff/abandon, and different-repository non-blocking.
  - Run the assembled workflow-managed Handoff proof with a live reservation: the destination receives registry, reservation, and capability authority atomically and the superseded source cannot renew, mutate metadata, write artifacts, or submit checkpoints. Native **Hand off** without the helper must fail on physical-worktree mismatch and direct deterministic recovery.
  - Deny each required root, engine access, fixed command, protected `.git` capability, external host, redirect, loopback bind/request, required secret, and environment-minimization condition before claim; prove one exact approved least-privilege fixture passes.
  - Use sentinel credentials and assert no value appears in state, events, output, errors, patches, manifests, or diagnostics.
  - From a fresh isolated worktree at the exact PR head, require clean-before/after and run the then-current `python .\scripts\validate.py`; after squash merge, rerun it from a separate fresh isolated worktree at the exact returned merge SHA. No hosted check is discovered or polled.
- **Documentation impact:** shared state topology, reservation lifecycle, permissions/preflight, recovery/status, and cleanup references; exact distinction between established sandbox settings and unsupported beta-profile composition.
- **Dependencies:** `DDW-AIC-001` merged versioned base modules, schemas, registry-only workflow-managed Handoff, and initial aggregate local gate.
- **Blocks:** `DDW-AIC-003` and `DDW-AIC-004`.
- **Non-goals:** no reimplementation of repository identity/state-home/allocation mutex/registry/exact binding/base transfer, no SaaS-specific identifiers/commands, no live Linear/ntfy/GitHub mutation, no hosted-check integration, no scheduled task creation, no arbitrary shell, and no autonomous implementation reasoning.
- **Primary-PR handoff:** publish versioned schemas/module interfaces and a passing dependency-free core contract suite for later transports.

### `DDW-AIC-003` / `SAAS-47` — Add Linear selection, decisions/follow-ups, and ntfy

- **Goal:** add deterministic external tracking and attention behavior behind fixture-compatible interfaces without granting specialist agents mutation authority.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; `Backlog`; no `autonomous`.
- **Likely files/modules:**
  - `src/skills/linear-delivery-loop/scripts/modules/Linear.psm1` and selection/contract/decision/follow-up modules
  - ntfy transport, redaction, notification-state, and idempotency modules
  - issue-contract/failure/migration references and Linear/ntfy fixtures
- **Acceptance criteria:**
  - Direct Linear GraphQL reads `LINEAR_API_KEY` only from the process environment; variables, complete cursor pagination, HTTP/GraphQL errors, rate limits, bounded retries, idempotency, and read-before/write/read-after reconciliation are implemented.
  - Preflight resolves and verifies the configured workspace, team `SAAS`, project, ordinary states, labels, owner, and repository contract before mutation.
  - Before selection the adapter reconciles pending decisions, repository reservations, and fully paginated `In Progress`/`In Review` WIP. Multiple active issues fail closed; manual WIP exits cleanly; matching autonomous WIP resumes; only zero active WIP permits selection.
  - Eligibility is complete, bounded, local-first `Todo + autonomous`, excluding stop labels, parents/broad/cross-repository/non-code/incomplete/external leaves; ordering is priority, oldest `createdAt`, then numeric ID after full filtering.
  - The candidate is re-read immediately before atomic reservation/persistent-worktree preparation and claim; ambiguous rollback/reconciliation performs no duplicate claim.
  - User-selected linked manual/semi work reconciles any exact autonomous lease and removes `autonomous` before Plan; conflicts fail closed before artifacts or labels change.
  - Incomplete work becomes `Backlog + needs-refinement`; deferred external work becomes `Backlog + external-integration`; the adapter never invents product intent.
  - High-risk ambiguity uses one structured `Backlog + needs-human` decision with ID, options/consequences, recommendation, exact reply syntax, and links. Only an exact new authorized reply is consumed once before queue selection.
  - Publication refusal integration supports one deduplicated operational request on the preserved `In Progress`/`In Review + autonomous + blocked + needs-human` issue. It stores the operation/head/PR/local-attestation references and exact owner-only reply syntax `RETRY-PUBLICATION <operation-id> <head-sha>` without querying hosted-check status.
  - Before ordinary queue selection, pending publication requests are reconciled as preferred preserved work. Malformed, stale, duplicate, unauthorized, or pre-reconciliation replies do nothing; one exact new authorized reply is consumed once and delegates only one idempotent publication retry to `DDW-AIC-004`.
  - Transient failure stays on the original issue. A separately actionable external prerequisite creates at most one deduplicated achievable child; a product/security/cost decision creates no speculative task.
  - ntfy is mandatory for actionable unattended states, including stable/exhausted/ambiguous provider-publication refusal, links to the single Linear request, is idempotent/redacted, and remains an attention channel rather than the decision source. Empty queue, held lease, manual WIP, demonstrably transient publication retries still within budget, and routine stages remain quiet.
  - Migration dry-run is fully paginated, mutation-free, and reports every candidate/rejection and proposed ordinary-state/label action.
- **Test notes:** wrong/missing key, wrong workspace, GraphQL `200` errors, partial pages, 429/5xx retries, ambiguous writes, idempotent readback, complete selection order, issue-contract rejection, manual/autonomous WIP, multiple WIP, and reservation race.
- **Test notes:** decision and publication-request authorization/order/replay, exact `RETRY-PUBLICATION` parsing, single-request deduplication/update, follow-up deduplication/achievability, preservation of unrelated metadata, ntfy success/failure/retry/quiet behavior, and secret-sentinel absence.
- **Test notes:** extend the existing `scripts/validate.py` manifest with transport/selection/decision/notification fixture tests; run it cleanly from a fresh isolated exact-PR-head worktree and again from a separate fresh isolated exact returned merge-SHA worktree. Hosted checks are not phase-1 evidence.
- **Documentation impact:** canonical Linear issue contract, decision/follow-up policy, notification policy, migration dry-run, and redaction references.
- **Dependencies:** `DDW-AIC-002` state/reservation/operation interfaces.
- **Blocks:** `DDW-AIC-004` and `DDW-AIC-005`.
- **Non-goals:** no real backlog migration, ntfy publish, Git/PR/merge, hosted-check integration, SaaS wrapper, schedule, product feature, or specialist-owned Linear mutation.
- **Primary-PR handoff:** expose deterministic observed authorization/issue/notification operations to the GitHub gate task.

### `DDW-AIC-004` / `SAAS-48` — Add deterministic Git/GitHub publication, provider-refusal recovery, exact-SHA local gates, and repair

- **Goal:** make branch/worktree containment, push/PR/merge publication including provider-enforced refusal/recovery, clean isolated exact-SHA local-gate orchestration, evidence sequencing, review/QA attestations, squash merge, and bounded post-merge repair deterministic and fail closed without hosted-check integration or provider-control bypass.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; `Backlog`; no `autonomous`.
- **Likely files/modules:**
  - shared Git/worktree/manifest, GitHub push/PR/merge, provider-refusal operation/retry, and clean isolated local-gate orchestration modules under `src/skills/linear-delivery-loop/scripts/modules/`
  - evidence classifier/attestation, publication-request, redaction, and post-merge recovery modules
  - state-machine, quality-gate, publication-failure, attended-retry, and evidence references
  - disposable local Git/remote and GitHub fixture suites
- **Acceptance criteria:**
  - Specialists return proposals and real-file manifests but cannot stage, commit, push, create/update PRs, merge, or mutate Linear in autonomous mode.
  - The adapter snapshots base/pre-existing state, validates persistent worktree/path containment, reconciles manifest to real diff, rejects conflict/unexpected/unrelated paths, runs fixed validation, stages only reconciled paths, and never force-pushes, rebases, pushes `main`, tags/releases, changes settings/secrets, or auto-reverts.
  - One issue uses `codex/SAAS-N-<slug>`, one primary PR to `main`, and only numbered `codex/SAAS-N-repair-<attempt>` PRs for post-merge repair.
  - Implementation plus plan/design/tasks/audit and clearly marked draft code-review/QA/completion evidence is committed before the final gated head.
  - After creating/reusing the PR, the adapter independently reads the current PR head from GitHub, requires it to match the local observed commit, creates a fresh contained isolated worktree at that exact SHA, proves clean-before/after, and invokes the repository-configured aggregate local command with recorded arguments, tool versions, physical worktree identity, exit code, and timestamp.
  - The `ai-config` configuration resolves exactly `python .\scripts\validate.py`; SaaS later resolves exactly `pwsh ./scripts/validate-all.ps1` plus applicable real HTTP/Playwright acceptance at the exact PR head. A missing aggregate member, SHA mismatch, dirty worktree, failed command, incomplete required runtime QA, or ambiguous identity fails closed.
  - No phase-1 code discovers, queries, polls, waits for, budgets, or accepts hosted CI/checks as evidence or authorization. GitHub may nevertheless physically refuse push, PR, or merge; every refusal is classified only from the redacted requested-operation response plus idempotent readback of remote ref, PR/head/base, merge state, and the operation journal.
  - A refusal is transient only for an explicit retryable `429`, `5xx`/unavailable provider, or temporary mergeability response when readback proves the mutation did not already succeed. It preserves the current ordinary state (`In Progress` before a PR exists; `In Review` after), `autonomous`, global WIP, reservation, persistent worktree, branch, PR when present, and all evidence; releases only the run lease; records redacted operation identity; and retries that exact operation/head at most three times across heartbeats using bounded `Retry-After` capped at 30 minutes or 5/15/30-minute backoff.
  - Before every transient retry, the adapter independently reconciles remote state and the operation journal so it never duplicates push, PR, or merge. Exhaustion becomes a stable pause rather than an infinite retry.
  - A stable, exhausted, ambiguous, permission, required-check, branch-protection/ruleset, merge-queue, policy, or unclassified refusal never reaches `Done`. It preserves the same ordinary state plus `autonomous`, WIP, reservation, worktree, branch/PR/evidence, adds `blocked + needs-human`, releases only the run lease, and creates/updates one deduplicated Linear operational request plus ntfy with exact owner-only syntax `RETRY-PUBLICATION <operation-id> <head-sha>`.
  - No automatic publication retry occurs while paused. After attended external reconciliation, exactly one new authorized reply is consumed once; the adapter independently re-reads issue state/labels/authorization, reservation/worktree, operation journal, branch/PR/head/base/mergeability, every local SHA-bound attestation, and the latest provider operation/readback, then attempts at most one idempotent push/PR/merge. Success clears `blocked`/`needs-human` and continues from the preserved stage; changed-head, unresolved, or ambiguous results remain paused and update the same request.
  - The adapter never queries check status; mutates repository settings, permissions, branch protection, rulesets, required checks, or merge queues; uses admin/bypass merge; weakens controls; adds/repairs a pipeline; creates a speculative child for provider enforcement; duplicates publication; or releases/loses protected WIP, reservation, worktree, branch/PR, or evidence.
  - Independent code review and applicable real runtime QA bind to the exact executable SHA.
  - Final report deltas are classified against a strict allowlist/content rule. Only proven evidence-only changes receive one evidence commit; ambiguous or executable changes invalidate and rerun affected implementation/local-aggregate/review/QA/docs gates.
  - For a proven evidence-only final head, docs checks, the clean isolated exact-final-head aggregate, and final-head code-review attestation rerun. QA either reruns or records an explicit safe two-SHA reuse attestation proving no behavioral effect.
  - Final PR/head/base, exact-head local-gate attestation, final review, QA/reuse, docs, merge, and post-merge identities are stored in supervisor state and concise Linear evidence without another branch commit.
  - Immediately before merge, authorization/stop labels/decision/reservation/lease, PR/head/base, mergeability, and all exact-head local/review/QA/docs attestations are independently re-read. Base drift merges `origin/main` without rebase/force and invalidates/reruns affected gates.
  - Squash merge uses the exact returned merge SHA, independently verifies GitHub readback, creates a separate fresh isolated worktree at that commit, and reruns the repository aggregate cleanly before `Done`/reservation release. No post-merge repository mutation or completion commit is allowed.
  - Failed post-merge validation remains on the same issue in `In Review`, creates repair branches from current `main`, reruns all gates for at most three attempts, and never auto-reverts; exhaustion becomes `Backlog + needs-human` with evidence and ntfy.
- **Test notes:** use disposable fixture repositories/remotes and fixture GitHub responses; make no real push, PR, merge, or Linear mutation.
- **Test notes:** cover containment/unexpected diff, protected command denial, stop-label/authorization/head change, exact repository/PR/head/base/gate-worktree/merge identity, clean-before/after, aggregate-command failure, SHA mismatch, base drift, ambiguous operations, and replay.
- **Test notes:** fixture every operation boundary separately: push refusal before PR, PR creation/update refusal, and squash-merge refusal after PR/local attestations. Cover pending/failing required-check enforcement, branch protection/rulesets, required merge queue, permission denial, `429`, `5xx`/unavailable provider, temporary mergeability, ambiguous response/readback, and retry exhaustion.
- **Test notes:** prove transient versus stable classification, exact bounded backoff, redaction, operation journal idempotency, no duplicate push/PR/merge, `In Progress` before PR versus `In Review` after, preservation of `autonomous`/WIP/reservation/worktree/branch/PR/evidence, run-lease-only release, and no false `Done`.
- **Test notes:** exact `RETRY-PUBLICATION <operation-id> <head-sha>` fixtures reject malformed/unauthorized/stale/duplicate/pre-reconciliation replies, allow at most one reconciled operation for a new authorized reply, keep unresolved cases paused on the same request, and prove eventual successful authorized retry continues from the preserved stage.
- **Test notes:** explicitly prove that no path discovers/queries/polls/waits/budgets hosted checks, changes GitHub settings/rules/protection/permissions/queue, bypasses enforcement, creates a speculative child, duplicates publication, or accepts a hosted result as evidence/authorization.
- **Test notes:** explicitly cover draft evidence ordering, executable SHA review/QA, evidence-only versus executable/ambiguous classification, convergence, exact-final-head aggregate/review reruns, QA rerun or named two-SHA reuse, exact returned merge identity, clean merge-SHA aggregate rerun, no post-merge mutation, and three same-issue repair attempts.
- **Test notes:** extend the existing `scripts/validate.py` manifest with Git/GitHub/local-gate/evidence/repair fixture tests; run that aggregate from clean isolated exact PR-head and exact returned merge-SHA worktrees for this task's own PR.
- **Documentation impact:** Git/GitHub authority, provider-refusal transient/pause/exact-retry contract, operational request syntax, evidence/gate ordering, merge identity, base drift, and repair references.
- **Dependencies:** `DDW-AIC-002` and `DDW-AIC-003`.
- **Blocks:** `DDW-AIC-005`.
- **Non-goals:** no live GitHub mutation, no SaaS-specific implementation of configured commands, no hosted-check discovery/query/polling/wait/budget/acceptance, no GitHub settings/rules/protection/permission/queue mutation or bypass/admin merge, no pipeline changes, no direct-main delivery, no auto-revert, and no speculative child for provider enforcement or routine implementation/QA/local-gate/merge defects.
- **Primary-PR handoff:** deliver a fixture-proven exact-SHA engine boundary ready for distribution and SaaS configuration.

### `DDW-AIC-005` / `SAAS-49` — Validate and distribute the complete shared harness

- **Goal:** make the canonical three-workflow protocol and engine buildable, semantically validated, version-compatible, and synchronizable across supported tools without drift or hand-edited projections.
- **Linear mapping:** code-bearing child; `repositoryKey: ai-config`; base `main`; one primary PR; `Backlog`; no `autonomous`.
- **Likely files/modules:**
  - `scripts/build.py`, `scripts/sync.py`, and `scripts/test_sync_markers.py`
  - new semantic/build/sync/parity tests and extensions to the existing `scripts/validate.py` aggregate manifest introduced by `DDW-AIC-001`
  - canonical `README.md`, root `AGENTS.md`, project templates, and generated `dist/`
  - version/hash/reference manifest generation and verification
- **Acceptance criteria:**
  - Build validates unique entries/agents, resolvable skill references, three policy behaviors, canonical protocol ownership/precedence, schemas/modules/prompts, compatibility routing, historical fallback, and specialist authority boundaries.
  - Build rejects missing or duplicated shared references, competing normative policy, restored “portable summaries” doctrine, copied mode policy, unresolved routing, and malformed engine/schema/config versions.
  - Source, tracked/generated `dist`, and temporary installed Codex/Claude/Copilot/Cursor projections carry the same canonical contract/engine/schema version, hash, and resolved reference graph.
  - Temporary-home/project tests prove marker preservation, source-to-dist-to-installed parity, Cursor project-local routing, partial-sync/tampering/version mismatch rejection, and absence of edits to real user homes.
  - The Copilot projection receives the same ownership/precedence semantics even if its installed/project files are generated from another canonical template.
  - A generic fixture project proves wrappers/config cannot override engine-owned selection, state, reservation, transition, Linear/GitHub/ntfy, retry, redaction, or permission behavior.
  - The one authoritative `python .\scripts\validate.py` aggregate extends its existing manifest to run build, marker tests, semantic tests, schema/module tests, shared contract tests, engine fixtures, and temporary sync tests. No second aggregate or hosted gate is introduced.
  - Root docs explain the three workflows, exact entry syntax, completion boundaries, canonical/repo precedence, shared-engine/project-config boundary, source-first editing, build, sync, verification, and compatibility deprecation.
  - No new hosted `ai-config` CI is introduced.
- **Test notes:** run all shared tests, `python .\scripts\build.py`, marker tests, and `python .\scripts\validate.py`. Compare reference manifests across every generated temporary target.
- **Test notes:** from a fresh isolated worktree at the exact PR head, require clean-before/after and run `python .\scripts\validate.py`; after squash merge, rerun the same command from a separate fresh isolated worktree at the exact returned merge SHA. No hosted check is required or queried.
- **Test notes:** run `python .\scripts\sync.py --tool all` only after merge and separate user authorization to install; verify installed files exist and versions/hashes match without exposing secrets.
- **Documentation impact:** root usage/setup, supported-tool projections, source ownership, versioning, validation, and migration-cycle deprecation.
- **Dependencies:** `DDW-AIC-001`, `DDW-AIC-002`, `DDW-AIC-003`, and `DDW-AIC-004` merged.
- **Blocks:** `DDW-SAS-003` and shared installation.
- **Non-goals:** no hosted pipeline/check integration, no SaaS adapter/config, no live Linear/GitHub/ntfy operation, and no installation before separate authorization.
- **Primary-PR handoff:** record the merged source SHA, contract/engine/schema version and hashes, aggregate test result, and authorized installed-version proof for `DDW-SAS-003`.

## `saas` code-bearing children

### `DDW-SAS-002` / `SAAS-50` — Make the SaaS local aggregate and real runtime QA pinned, isolated, and reliable

- **Goal:** preserve `pwsh ./scripts/validate-all.ps1` as the authoritative SaaS local aggregate and provide safe repository-owned real HTTP/browser acceptance that autonomous QA can invoke deterministically; hosted Actions remains non-authoritative and out of scope.
- **Linear mapping:** code-bearing child; `repositoryKey: saas`; base `main`; one primary PR; `Backlog`; no `autonomous`.
- **Likely files/modules:**
  - `apps/web/package.json`, `apps/web/package-lock.json`, and new `apps/web/playwright.config.ts`
  - focused Playwright fixtures/specs under the repository's chosen web test convention
  - `scripts/validate-all.ps1`, `scripts/smoke.ps1`, `scripts/check-tools.ps1`, and possibly `scripts/test-all.ps1`
  - targeted `docs/QUALITY.md` and `docs/LOCAL-DEVELOPMENT.md` updates
- **Acceptance criteria:**
  - Direct dev dependency `@playwright/test` is pinned exactly to `1.61.1` in manifest and lockfile; no floating/global/`npx --yes --package` fallback remains.
  - `pwsh ./scripts/validate-all.ps1` is the sole authoritative aggregate, is locally runnable on the user's Windows environment, returns nonzero on every required member failure, and covers the repository's applicable build, type, test, docs, and runtime-QA entry checks without relying on a provider result.
  - Existing `.github/workflows/validate.yml` is not edited by this task and its status is never required, queried, polled, waited on, or accepted as phase-1 evidence/authorization. GitHub may still physically refuse push/PR/merge because of availability or repository policy; that external publication refusal is handled by `DDW-AIC-004` and does not invalidate successful local evidence or permit bypass.
  - A repository-local Playwright command and browser-install/cache preflight are documented and deterministic.
  - Runtime QA binds/requests only configured loopback hosts and unique per-run ports in Development, rejects production-like endpoints/secrets, uses bounded readiness, allocates unique disposable data/resources, and records cleanup.
  - API scenarios send real HTTP requests and validate response, persistence, authentication, authorization, and tenant boundaries where relevant.
  - Browser scenarios exercise representative anonymous/authenticated behavior, visible outcome, keyboard/focus behavior, and obvious accessibility failures; screenshots/traces are retained only when useful.
  - Tests never reset or reuse the developer's normal database implicitly and fail nonzero when readiness, behavior, isolation, or cleanup fails.
  - `scripts/smoke.ps1 -Live -Behavioral -Playwright` delegates to the pinned local surface.
- **Test notes:** run `npm ci`, typecheck/build, repository Playwright tests, behavioral smoke, and `pwsh ./scripts/validate-all.ps1` locally.
- **Test notes:** from a fresh isolated worktree at the exact PR head, require clean-before/after, run `pwsh ./scripts/validate-all.ps1`, and run applicable real HTTP/Playwright QA bound to that SHA; after squash merge, rerun the aggregate from a separate fresh isolated worktree at the exact returned merge SHA. Do not query hosted checks.
- **Test notes:** include negative non-loopback, non-Development, production-secret, shared/destructive database, duplicate resource, readiness timeout, broad LAN binding, and missing-cleanup cases.
- **Documentation impact:** exact local setup/commands, browser installation, safe Development/loopback contract, disposable data, local aggregate authority, hosted-check non-authority versus possible provider publication refusal, failure diagnosis, and cleanup in `QUALITY`/`LOCAL-DEVELOPMENT`.
- **Dependencies:** `DDW-AIC-001` QA/specialist contract.
- **Blocks:** `DDW-SAS-001` and `DDW-SAS-003`.
- **Non-goals:** no product UI redesign, new user-facing feature, scheduler, Linear integration, hosted deployment, or production test data.
- **Primary-PR handoff:** publish exact local aggregate/runtime-QA command hooks plus exact-PR-head and exact-merge-SHA local attestations for the SaaS adapter.

### `DDW-SAS-001` / `SAAS-51` — Document the three workflows and establish the local MkDocs wiki

- **Goal:** make current SaaS workflow/setup knowledge searchable and consistent with the three entries, ordinary Linear states/labels, local work, completion boundaries, and safe automation.
- **Linear mapping:** code-bearing documentation child; `repositoryKey: saas`; base `main`; one primary PR; `Backlog`; no `autonomous`; no product UI design.
- **Likely files/modules:**
  - `AGENTS.md`, `README.md`
  - `docs/HARNESS.md`, `WORKFLOW.md`, `LINEAR.md`, `DECISIONS.md`, `QUALITY.md`, `AI-TOOLING.md`, `LOCAL-DEVELOPMENT.md`, and relevant architecture pages
  - new `docs/AUTOMATION.md`, docs index/navigation, and reusable how-to/concept/reference/ADR/runbook/troubleshooting templates
  - retirement/replacement of `docs/SLACK-APPROVALS.md`
  - new `mkdocs.yml`, `requirements-docs.txt`, and updates to `scripts/check-doc-drift.ps1`
- **Acceptance criteria:**
  - Current guidance names Autonomous, Semi-autonomous, and Manual Spec-driven Delivery; shows exact skill invocation and each mode's advancement, clarification, authority, Linear, reservation, Git, and completion behavior.
  - The default non-trivial repo workflow is manual spec-driven; semi-autonomous and autonomous entries are explicit alternatives.
  - Local goals need no Linear issue, allocate stable workflow evidence, can attach later without renaming history, and do not consume Linear WIP; same-repository editing still requires a reservation.
  - Current guidance consistently says **workflow-managed Handoff** for the registered authority transfer and explicitly distinguishes Codex desktop's native **Hand off**. It states native **Hand off** alone updates no registry/lease/reservation, cannot transfer authority, and on mismatch must return to the registered worktree or use explicit workflow-managed Handoff/recovery.
  - Docs consistently use team `SAAS`, ordinary states, `Todo + autonomous`, one global tracked WIP slot, exception labels, achievable issue contracts, one repository/primary PR, squash/exact-SHA Done, and local-first product sequencing.
  - Linear/ntfy/Codex Scheduled are documented as durable decision/attention/run-visibility surfaces; Slack/Telegram routes are removed and any still-valid generic decision guidance is moved before `SLACK-APPROVALS.md` retirement.
  - `docs/AUTOMATION.md` covers ephemeral Scheduled control worktree, machine-stable supervisor home, persistent issue worktree, permissions model, mutation-free preflight, minimal environment, app/computer prerequisite, five-minute wake-up, no nested Codex/OS scheduler, kill switch, pause/archive, recovery, and safe cleanup.
  - Docs define phase 1 as local-only: no hosted pipeline/check is required or authoritative, existing SaaS Actions is out of scope, exact PR-head authority comes from clean isolated `pwsh ./scripts/validate-all.ps1` plus applicable real runtime QA, and the exact returned merge SHA reruns the local aggregate.
  - `docs/AUTOMATION.md` and the troubleshooting/runbook content explain that GitHub may refuse push, PR, or merge even though checks are not evidence. They distinguish demonstrably transient retry from preserved `In Progress`/`In Review + autonomous + blocked + needs-human` pause, show exact `RETRY-PUBLICATION <operation-id> <head-sha>` recovery after attended reconciliation, and state that WIP/reservation/worktree/branch/PR/evidence remain protected.
  - The publication runbook forbids automatic retry while paused, check-status query, GitHub setting/rules/protection/permission/queue mutation, bypass/admin merge, pipeline work, speculative child creation, and cleanup/release of protected state; it documents idempotent same-request recovery and escalation evidence.
  - Docs link to the canonical shared protocol and contain only SaaS-specific/stricter rules rather than a competing protocol copy.
  - `requirements-docs.txt` pins exactly `mkdocs==1.6.1`; MkDocs navigation/search is deliberate and excludes noisy per-run evidence from primary navigation.
  - Setting/how-to pages contain prerequisites, steps, verification, rollback, and troubleshooting. Each future task must record exact docs impact or `none` with reason.
  - Doc drift rejects operational `Ready for Codex`, Slack/Telegram configuration, current `LUC-*`, two-mode guidance, and duplicated normative protocol while permitting clearly marked historical evidence.
- **Test notes:** run doc drift, install pinned docs tooling in a repo-managed environment, run `mkdocs build --strict`, run `pwsh ./scripts/validate-all.ps1`, and search current operational files for rejected language with historical exceptions verified.
- **Test notes:** from a fresh isolated worktree at the exact PR head, require clean-before/after and run `pwsh ./scripts/validate-all.ps1`; after squash merge, rerun it from a separate fresh isolated worktree at the exact returned merge SHA. This docs-only task needs no runtime QA unless its executable/config delta affects runtime behavior, and no hosted check is queried.
- **Documentation impact:** this task owns current workflow/wiki documentation, provider-publication refusal/recovery runbook, and reusable operations evidence/report procedure; per-run evidence remains under `docs-ai` and is linked rather than copied into navigation/Linear.
- **Dependencies:** `DDW-AIC-001` canonical protocol/base local-work terminology and `DDW-SAS-002` authoritative local aggregate/runtime-QA surface.
- **Blocks:** `DDW-SAS-003` and Linear migration.
- **Non-goals:** no separate hosted wiki, product UI, external provider setup, copying full run reports into Linear, rewriting historical artifacts, or operations-only fake PR.
- **Primary-PR handoff:** provide exact merged docs SHA, strict MkDocs result, doc-drift result, and adapter configuration/setup references.

### `DDW-SAS-003` / `SAAS-52` — Integrate the disabled thin SaaS adapter and Scheduled prompt

- **Goal:** bind the merged installed shared engine to SaaS policy through versioned configuration, a thin wrapper, project fixtures, least-privilege setup, and a disabled-by-default Scheduled prompt.
- **Linear mapping:** code-bearing child; `repositoryKey: saas`; base `main`; one primary PR; `Backlog`; no `autonomous`.
- **Likely files/modules:**
  - `automation/linear-delivery-loop.config.json`
  - `automation/codex-scheduled-linear-loop.md`
  - least-privilege setup/reference files under `automation/`
  - `scripts/agent-worker.ps1` and `scripts/test-agent-worker.ps1`
  - project fixtures under `automation/fixtures/` or the repository test convention
  - `.gitignore`, `scripts/check-tools.ps1`, `scripts/check-doc-drift.ps1`, and `scripts/validate-all.ps1` integration assertions
- **Acceptance criteria:**
  - Config validates against the exact installed shared schema/version/hash and contains only SaaS identifiers, base `main`, ordinary states/labels, branch/artifact/docs templates, local-first flags, exact local aggregate/QA commands, repository key, state-home policy, writable roots, fixed wrapper/Git/`gh` shapes, allowed remote/network/loopback targets, and environment-variable names—never values. It carries no required hosted workflow/check identity.
  - `scripts/agent-worker.ps1` resolves the installed engine, verifies version compatibility, forwards structured file arguments, and contains no copied GraphQL/state/lease/reservation/transition/notification/Git/GitHub/recovery implementation or runtime download fallback.
  - `repositoryKey: saas`, `pwsh ./scripts/validate-all.ps1`, and the repository-pinned real HTTP/Playwright hooks are exact and contract-checked against repository files. Existing hosted Actions is neither queried nor accepted as an authority input, while the wrapper permits the shared engine to observe only requested publication-operation response/readback needed for provider-refusal classification.
  - The wrapper derives the same machine-stable supervisor home from the primary checkout and two separate Scheduled worktrees; persistent issue worktrees remain under that home and the control worktree is rejected for autonomous implementation.
  - Project tests prove global Linear WIP plus same-repository reservation composition for manual selected issues, local SaaS editing, autonomous resume/claim, stale protected work, explicit Release/workflow-managed Handoff, and other-repository non-blocking.
  - Project composition distinguishes workflow-managed Handoff from native Codex **Hand off**: native **Hand off** produces deterministic physical-worktree mismatch/recovery and transfers no authority; assembled workflow-managed Handoff transfers matching registry/reservation/capability authority atomically and prevents all later source writes.
  - Project configuration propagates the shared provider-refusal states and exact `RETRY-PUBLICATION` contract without adding check identity/status, provider-control mutation, or bypass capability. It preserves SaaS ordinary state, `autonomous`, WIP/reservation/worktree/branch/PR/evidence and releases only the run lease during transient wait or stable pause.
  - The unattended configuration uses `sandbox_mode = "workspace-write"`, `sandbox_workspace_write.network_access = true`, `approval_policy = "never"`, explicit writable roots, minimal environment, fixed exec rules, host allowlists, and exact loopback targets/ports. It does not add or combine beta named permission profiles and has no full-access fallback.
  - Project-boundary preflight proves installed engine/config, state/mutex/worktree-root sentinel, protected Git operations via disposable fixture, read-only Linear/GitHub/Git remote/ntfy connectivity, loopback bind/request, unrelated-provider-secret exclusion, and redaction before claim.
  - The versioned prompt explicitly invokes `$linear-delivery-loop`, prepares at most one issue, may continue routine stages for that issue, and stops on completion/pause/external wait/retry exhaustion/unsafe failure/interruption without selecting a second issue.
  - Kill switch, Status/recovery, pause/archive/removal, scheduled-worktree cleanup survival, and disabled-by-default behavior are documented and testable.
  - Integration adds no Windows Task Scheduler entry, nested `codex exec`, copied engine, secret, live Linear mutation, ntfy publish, or active recurring task.
- **Test notes:** run project fixtures over the complete shared suite, wrapper/config boundary tests, `Status`, and mutation-free prepared/dry-run checks only after attended preflight; then run doc drift, strict MkDocs, and full SaaS validation.
- **Test notes:** cover engine/version mismatch, wrong repository identity, invalid state home, control-worktree mutation, config override attempt, missing/wrong local aggregate or runtime hook, attempted hosted-check authority, denied writable root/command/host/loopback, beta-profile mixing, provider-secret inheritance, secret leakage, workflow-managed/native-Handoff mismatch, and scheduled-worktree archive/recovery.
- **Test notes:** assembled SaaS fixtures propagate push/PR/merge refusal for required-check enforcement, protection/ruleset, merge queue, permission, `429`, `5xx`/unavailable, temporary mergeability, and ambiguous readback; prove transient versus pause state, redaction/backoff/idempotency, preserved protected state, single request/ntfy, exact authorized retry, eventual success, no check query/settings mutation/bypass/speculative child/duplicate publication, and no `Done` while unresolved.
- **Test notes:** from a fresh isolated worktree at the exact PR head, require clean-before/after, run `pwsh ./scripts/validate-all.ps1`, and run applicable real HTTP/Playwright adapter behavior acceptance; after squash merge, rerun the aggregate from a separate fresh isolated worktree at the exact returned merge SHA. No hosted check is queried.
- **Documentation impact:** exact setup, permission/preflight, environment variables, state/recovery/status, provider-publication pause/retry commands, disabled state, kill switch, prompt versioning, and project-boundary troubleshooting in the SaaS wiki.
- **Dependencies:** `DDW-AIC-005` merged and explicitly synced/installed, plus `DDW-SAS-001` and `DDW-SAS-002` merged.
- **Blocks:** `DDW-OPS-001`, `DDW-OPS-002`, and any autonomous pilot.
- **Non-goals:** no generic engine logic, hosted-check integration or pipeline edits, live mutation/publish, schedule creation, Windows script scheduler, product feature, or external cloud integration.
- **Primary-PR handoff:** provide merged adapter/config/prompt SHA, exact installed shared version/hash, fixture/preflight report, disabled-state proof, and safe dry-run/status commands.

## Manual-operational children

### `DDW-OPS-001` / `SAAS-53` — Migrate Linear to ordinary states/labels and refine the autonomous backlog

- **Goal:** remove `Ready for Codex` completely and leave only complete, local-first, single-repository executable leaves eligible for autonomous selection.
- **Linear mapping:** manual-operational; `Backlog`; no `autonomous`; no repository key, branch, commit, or PR.
- **Likely files/modules:** none; the operation mutates Linear only through the approved deterministic adapter and stores authoritative evidence in the machine-stable operation journal.
- **Operational steps:**
  1. Verify/create `blocked`, `needs-human`, `needs-refinement`, and `external-integration` idempotently without duplicate labels.
  2. Run complete mutation-free inventories of all `Backlog`/`Todo + autonomous` issues and every issue/reference in `Ready for Codex`, including parent/child/dependency, repository, issue contract, local/external classification, and proposed mapping.
  3. Review the redacted dry-run before mutation.
  4. Apply idempotently: parents/broad/incomplete work to `Backlog + needs-refinement`; deferred hosted/external work to `Backlog + external-integration`; complete local code leaves to `Todo + autonomous`; ready manual work to ordinary `Todo` without autonomous; custom-state issues to the correct ordinary state/labels.
  5. Preserve unrelated metadata, reuse/split achievable children without duplicates, and comment only on material classification changes.
  6. Verify zero issues and zero operational references remain for `Ready for Codex`, then delete the custom state manually in Linear.
  7. Re-run inventories and prove zero custom-state issues/references, zero `Backlog + autonomous`, and no parent/broad/cross-repository/external/incomplete eligible issue.
- **Acceptance criteria:** before/after operation-journal evidence and concise Linear readback cover every issue, label/state ID, dependency, contract gap, proposed/applied mutation, result, actor, and timestamp; unrelated metadata is preserved and repeated execution is a no-op.
- **Validation/evidence:** authoritative redacted operation in the machine-stable state home plus concise Linear links/readback; optional ignored diagnostic export is non-authoritative. No repository PR is created.
- **Documentation impact:** none during this operational run; the reusable procedure/report schema is already owned by `DDW-SAS-001`. A durable doc correction discovered here requires a separate approved code-bearing docs task.
- **Dependencies:** `DDW-SAS-003` merged, installed-version compatible, fixture/preflight passing, and disabled by default.
- **Blocks:** `DDW-OPS-002`.
- **Non-goals:** no schedule, pilot PR, product feature, current-history rewrite, or restoration of `autonomous` to program-building issues.
- **Rollback:** kill switch/remove eligibility, preserve the before export, and map affected issues back to safe ordinary states/labels; do not assume the deleted custom state can be recreated automatically.

### `DDW-OPS-002` / `SAAS-54` — Configure notification attention and pass one attended autonomous pilot

- **Goal:** prove one bounded local-first SaaS leaf end to end under observation, including durable decision handling, actionable ntfy attention, exact-SHA delivery, and safe failure behavior.
- **Linear mapping:** manual-operational; `Backlog`; no `autonomous`; no repository key or PR for this operations issue. The pilot itself is a separate bounded `Todo + autonomous` code leaf with its own repository/PR contract.
- **Likely files/modules:** none for this operations issue; it consumes the already merged adapter/config/prompt and records external/state-home evidence.
- **Operational steps:**
  1. Configure private/authenticated ntfy host/topic/token outside repositories and confirm `LINEAR_API_KEY` remains environment-only; restart Codex desktop only if needed for environment inheritance.
  2. Run full shared/SaaS fixtures, installed version/hash checks, least-privilege permission preflight, `Status`, live read-only Linear dry-run, and one attended redacted ntfy test publish.
  3. Before live publication, pass the complete fixture-only provider-refusal matrix and one attended exact `RETRY-PUBLICATION <operation-id> <head-sha>` simulation through stable pause, rejected stale/duplicate reply, independently reconciled single retry, and eventual success without querying checks or changing GitHub controls.
  4. Select one safe, achievable, locally runnable SaaS code leaf with a complete goal, acceptance/non-goals, dependencies, validation, docs impact, risk flags, repository key, and one-primary-PR scope; only that leaf receives `Todo + autonomous`.
  5. From the dedicated SaaS Codex task in Worktree mode, explicitly invoke `$linear-delivery-loop` in attended mode.
  6. Exercise one structured product/decision request, ntfy alert, exact authorized Linear reply, one-time consumption, and same-issue resume.
  7. Observe reservation/WIP arbitration, persistent issue worktree, artifact stages, manifest containment, local validation, draft evidence, one PR, clean isolated exact-PR-head `pwsh ./scripts/validate-all.ps1`, independent code review, exact-head real HTTP/Playwright QA, final evidence/attestations, squash merge, and clean isolated exact-merge-SHA aggregate rerun. If GitHub refuses a real publication operation, follow the preserved-state provider-refusal contract rather than weakening controls or expanding scope.
  8. Exercise kill switch, manual-WIP no-op, and publication-pause no-op without an exact authorized retry before rollout.
- **Acceptance criteria:** no secret leaks; ntfy opens the correct Linear request; routine/empty/held/manual-WIP and in-budget transient paths remain quiet; decision/publication reply authorization/order/replay rules hold; only one issue/repository/primary PR is processed; provider refusal never loses WIP/reservation/worktree/branch/PR/evidence or reaches `Done`; `Done` occurs only after exact merge validation or the issue remains safely paused.
- **Validation/evidence:** redacted preflight/publish readback, provider-refusal fixture matrix, attended `RETRY-PUBLICATION` simulation, Linear decision/publication threads, pilot issue/PR/head/merge SHAs, exact local-aggregate/review/QA-or-reuse/docs/post-merge attestations, provider operation/attempt/backoff/redacted-response IDs, clean isolated worktree identities, state/reservation/run IDs, kill-switch/manual-WIP/publication-pause results, and rollback proof. Hosted checks are neither queried nor accepted. No fake PR belongs to `SAAS-54`.
- **Documentation impact:** none unless the pilot exposes an incorrect durable instruction; route that correction through a separately approved code-bearing docs change.
- **Dependencies:** every code child merged; `DDW-OPS-001` complete; adapter remains manually invoked and schedule disabled.
- **Blocks:** `DDW-OPS-003`.
- **Non-goals:** no broad backlog enablement, production/cloud resource, Telegram/Slack, recurring task, or speculative follow-up for a product decision.
- **Rollback:** remove pilot eligibility, set kill switch, pause/archive the dedicated task, retain protected state/worktree/artifacts, and reconcile before any release/cleanup.

### `DDW-OPS-003` / `SAAS-55` — Enable and observe one five-minute Codex Scheduled heartbeat

- **Goal:** turn the reviewed prompt into one recurring local Codex heartbeat and demonstrate stable unattended no-op, resume, recovery, and terminal behavior before expanding eligibility.
- **Linear mapping:** manual-operational; `Backlog` until the pilot passes; no `autonomous`; no repository key, branch, commit, or PR.
- **Likely files/modules:** none; enablement uses the already merged prompt and Codex Scheduled configuration, with evidence stored outside repository code.
- **Operational steps:**
  1. From the same dedicated SaaS Codex task used for the pilot, create/update exactly one five-minute recurring task using the merged versioned prompt.
  2. Verify Worktree mode, explicit `$linear-delivery-loop`, exact repository/config/shared versions, established least-privilege sandbox/exec model, minimal environment, state-home roots, network/loopback allowlists, app/computer prerequisites, and Scheduled inbox visibility.
  3. Run two distinct Scheduled control worktrees and archive/remove one; prove both use the same supervisor home, persistent issue worktree, reservation/lease/journal, and status/recovery without duplicate mutation.
  4. Observe empty queue, manual WIP, healthy overlapping lease, retryable local-gate failure/resume, native **Hand off** mismatch recovery, missed-heartbeat/crash recovery, publication-pause no-op without an exact authorized retry, and one normal resume/terminal path as safely available.
  5. Using fixture/simulation state rather than weakening live controls, observe one demonstrably transient publication retry retain the ordinary state/`autonomous`/protected work while releasing only the run lease, and one stable refusal remain paused until an exact fresh attended authorization triggers at most one reconciled operation.
  6. Confirm one heartbeat never selects a second issue after completion/pause and no other Windows/standalone duplicate scheduler exists.
  7. Observe the first several iterations before adding any further audited local-first leaves.
- **Acceptance criteria:** exactly one active five-minute recurring task exists; preflight/kill-switch/prerequisite failure causes no external mutation; empty/manual-WIP/held-lease/publication-paused-without-authorization paths are quiet; pending work resumes the same issue first; transient publication backoff is bounded/idempotent; `Status` and Scheduled inbox show redacted run/stage/lease/reservation/publication-operation/retry/decision/notification state; pause/remove/archive and recovery preserve protected state and are reversible.
- **Validation/evidence:** Scheduled task ID/cadence/prompt SHA, permission/environment readback, two-worktree and cleanup proof, several redacted run/status records, transient/pause/exact-retry scenario results, preserved WIP/reservation/worktree/branch/PR proof, no-duplicate-publication/scheduler checks, and tested rollback. No repository PR belongs to `SAAS-55`.
- **Documentation impact:** none during enablement; any persistent correction becomes a separate approved docs task.
- **Dependencies:** `DDW-OPS-002` attended pilot passes.
- **Blocks:** parent closeout and broader autonomous eligibility.
- **Non-goals:** Windows Task Scheduler, multiple Codex tasks, parallel issues, automatic queue broadening, cloud hosting, or full-access fallback.
- **Rollback:** pause/remove the recurring task, set kill switch, remove autonomous eligibility, archive the dedicated task, and retain machine-stable protected state/worktrees until attended reconciliation permits cleanup.

## Cross-task test ownership

Every plan-level behavior has one primary owner and an assembled project-boundary rerun. A lower-level passing fixture does not allow the assembled SaaS test to be removed or weakened.

| Contract area | Primary owner | Assembled proof |
|---|---|---|
| Three entry policies, canonical protocol, artifact layout, normalized repository identity/stable home, allocation mutex, registry, exact worktree binding, Windows-safe workflow-init/attach/resume, registry-only workflow-managed Handoff, specialist boundaries, initial `ai-config` aggregate | `DDW-AIC-001` | `DDW-AIC-005` generated/installed semantics; `DDW-SAS-003` project composition |
| Imported base-module boundary, supervisor lease/capability/state, editing reservations, persistent issue/gate worktrees, operation journal, assembled reservation-aware workflow-managed Handoff, permissions preflight, recovery/cleanup | `DDW-AIC-002` | `DDW-SAS-003` exact SaaS config; `DDW-OPS-003` two-worktree scheduled proof |
| Linear transport, WIP/selection, issue contract, manual ownership, decisions, deduplicated publication requests/exact retry replies, follow-ups, migration dry-run, ntfy | `DDW-AIC-003` | `DDW-SAS-003` fixture boundary; `DDW-OPS-001` migration; `DDW-OPS-002` attended decision/publication simulation |
| Git/worktree/manifest, clean isolated exact-head local gates, draft/final evidence, exact review/QA, push/PR/merge provider-refusal classification/backoff/pause/exact retry, merge/base drift/post-merge repair, hosted-check non-authority | `DDW-AIC-004` | `DDW-SAS-003` refusal/project fixtures; `DDW-OPS-002` attended exact-SHA pilot |
| Source/dist/installed version/hash/reference parity and supported-tool routing | `DDW-AIC-005` | `DDW-SAS-003` installed-engine compatibility/preflight |
| Authoritative local `pwsh ./scripts/validate-all.ps1`, exact-head real HTTP/Playwright isolation/cleanup, hosted-check non-authority versus possible provider refusal | `DDW-SAS-002` | `DDW-SAS-003` fixed hooks; `DDW-OPS-002` attended runtime QA |
| Current three-workflow guidance, provider-publication runbook, history exceptions, MkDocs strict/search/nav, rejected doctrine/state/channel drift | `DDW-SAS-001` | `DDW-SAS-003` doc/config checks; final program closeout |
| Thin-wrapper boundary, exact least-privilege SaaS profile, refusal-state propagation, versioned prompt, disabled/kill-switch/status | `DDW-SAS-003` | `DDW-OPS-002` attended pilot; `DDW-OPS-003` Scheduled recovery runs |

Mandatory cross-cutting regression cases:

- Registry-only workflow-managed Handoff failure keeps the source authoritative and `DDW-AIC-001` proves base remapping semantics; assembled workflow-managed Handoff success in `DDW-AIC-002` transfers all live authority and the superseded source cannot perform a later workflow-managed write. Native Codex **Hand off** alone transfers none and follows mismatch recovery.
- Established Codex sandbox/exec configuration is validated without beta named permission-profile mixing.
- Two Scheduled worktrees and cleanup share one persistent supervisor state/worktree and never duplicate Linear/GitHub operations.
- Same-repository manual planning/editing races fail closed through issue/repository reservations, while another repository does not block SaaS.
- Draft evidence precedes gated heads; final attestations bind exact SHAs and no post-merge repo mutation is required.
- Phase 1 has no hosted-check dependency: exact PR-head and exact merge-SHA authority comes only from each repository's clean isolated local aggregate, plus applicable exact-head runtime QA for SaaS.
- Provider fixtures distinguish push, PR, and merge refusal across required-check enforcement, protection/ruleset, merge queue, permission, `429`, `5xx`/unavailable, temporary mergeability, ambiguous readback, and exhaustion. They prove bounded transient backoff versus preserved-state pause, one deduplicated request/ntfy, exact attended one-operation retry/eventual success, redaction/idempotency, and no check query/settings mutation/bypass/speculative child/duplicate publication/lost protected work/false `Done`.
- Secret sentinels never appear in repository files, process output, state, journals, logs, patches, manifests, Linear, ntfy, or generated/installed config.

## Per-code-child delivery contract

These tasks bootstrap the deterministic adapter. After the plan-plus-task audit passes and the user explicitly approves implementation, `DDW-AIC-001` through `005` and `DDW-SAS-001` through `003` use the documented bootstrap exception: manual/semi-autonomous delivery with Git/GitHub mutations performed only by the root task or human under explicit active-conversation authority. Specialist agents remain proposal/edit/validation workers and never mutate Linear or publish autonomously.

Each code-bearing child must:

1. use its assigned `SAAS-N`, one target repository, base `main`, and one primary PR;
2. re-read this task, the revised plan, repository `AGENTS.md`, canonical/repo docs, and dependency handoff;
3. create/resume one exact workflow descriptor/artifact folder and record `design: not required` for this non-UI program;
4. acquire the applicable repository/issue ownership before implementation and preserve unrelated dirty user work;
5. implement only the stated goal/non-goals and update exact nearest source-of-truth docs or record `none` with reason;
6. run focused tests and the repository's full relevant aggregate validation;
7. commit implementation plus plan/task/audit and draft review/QA/completion evidence before the final gated head;
8. have the authorized root/human reconcile the real manifest, create `codex/SAAS-N-<slug>`, stage scoped files, commit, push without force, and open/update one PR; if GitHub refuses push/PR, preserve the current ordinary state and protected work and follow the deterministic publication-refusal contract rather than assuming publication succeeded;
9. from a fresh isolated worktree checked out at the independently observed exact PR head, require clean-before/after and run the repository-specific aggregate below; bind independent review, applicable real runtime QA, docs, and final evidence to the exact executable/final SHAs using the evidence-only rerun/reuse rules;
10. reconcile base drift, require the clean exact-final-head local gates, request squash merge, and, only when GitHub succeeds, independently verify the returned merge SHA and rerun the repository aggregate from a separate fresh isolated worktree at that exact commit before Linear `Done`; a refused/ambiguous merge follows the same preserved-state retry/pause contract and never reaches `Done`;
11. store final attestations externally/Linear without a follow-up completion commit or any post-merge repository mutation;
12. keep implementation/local-gate/review/QA/merge defects on the same issue within bounded repair rather than creating ticket noise or auto-reverting.

Repository-specific phase-1 gate ownership is fixed, not implementer-selectable:

| Code children | Exact PR/final-head authority | Exact merge-SHA authority |
|---|---|---|
| `DDW-AIC-001`–`DDW-AIC-005` | In a clean isolated worktree at the exact observed PR head, run `python .\scripts\validate.py`, independent review, and applicable docs checks. `DDW-AIC-001` creates the aggregate and each later child extends its manifest with its new focused/contract tests. | In a separate clean isolated worktree at the exact returned and read-back squash-merge SHA, rerun `python .\scripts\validate.py`; require clean-before/after. |
| `DDW-SAS-001`–`DDW-SAS-003` | In a clean isolated worktree at the exact observed PR head, run `pwsh ./scripts/validate-all.ps1`, independent review/docs checks, and repository-pinned real HTTP/Playwright acceptance for every affected behavior with disposable resources and cleanup evidence. | In a separate clean isolated worktree at the exact returned and read-back squash-merge SHA, rerun `pwsh ./scripts/validate-all.ps1`; require clean-before/after. |

Hosted CI/checks are not required, queried, waited on, budgeted, or accepted as phase-1 authority. Existing SaaS Actions is non-authoritative and outside every task's edit/acceptance boundary.

Publication success is still provider-dependent. Demonstrably transient `429`/`5xx`/unavailable/temporary-mergeability refusal uses bounded redacted idempotent retry while preserving ordinary state, `autonomous`, WIP, reservation, worktree, branch/PR/evidence and releasing only the run lease. Stable/exhausted/ambiguous policy/permission/required-check/protection/ruleset/merge-queue refusal adds `blocked + needs-human`, creates one deduplicated Linear request plus ntfy, and permits no automatic retry until exact `RETRY-PUBLICATION <operation-id> <head-sha>` authorization after attended reconciliation. The retry independently re-reads all identities/attestations and performs at most one operation; unresolved work stays paused. No task may query check status, change/bypass provider controls, repair a pipeline, create a speculative child, duplicate publication, release protected state, or claim `Done`.

No code task may silently expand to the other repository. Cross-repository integration is achieved through versioned contracts and dependency handoffs, not a mixed-repository PR.

## Final program acceptance and closeout

After `DDW-OPS-003`, manually verify:

- `$goal-to-delivery` accepts a supplied local goal/issue, selects no queue work, advances automatically only to its declared boundary, and defaults to tested working-tree output.
- `$spec-driven-delivery` performs only the explicitly invoked Plan/Clarify/Task/Audit/Implement/Review/QA/Docs/Commit/PR/Merge stage and returns control without auto-advance.
- `$linear-delivery-loop` selects/resumes exactly one prepared eligible issue, never accepts forged authority, and stops at documented wait/pause/terminal conditions.
- All three modes reuse the same planner/designer/tasker/auditor/implementer/reviewer/QA/docs contracts with no duplicated workflow doctrine.
- Source, generated, and installed supported-tool outputs match canonical contract/engine/schema version, hash, ownership, precedence, and reference graph.
- `ai-config` and SaaS aggregates pass from clean isolated exact PR-head and exact returned merge-SHA worktrees; SaaS exact-head real HTTP/Playwright QA is proven where behavior is affected; no hosted pipeline/check is required or authoritative.
- Push/PR/merge provider refusal is proven through complete fixtures and an attended retry simulation: transient operations back off boundedly; stable/exhausted/ambiguous enforcement pauses with protected state; exact retry is owner-authorized, one-shot, idempotent, and eventually recoverable; no provider control is queried/weakened/bypassed and unresolved work never reaches `Done`.
- Current docs/config/prompts/labels/examples agree on `SAAS`, ordinary states plus labels, global WIP plus repository reservation, Linear/ntfy/Scheduled notification roles, PR/squash/exact-SHA Done, and local-first sequencing.
- `Ready for Codex`, Slack/Telegram operations, current `LUC-*`, competing shared protocol copies, and two-workflow operational guidance are absent outside clearly marked history.
- Machine-stable state, persistent issue worktrees, exact resume, workflow-managed Handoff, native **Hand off** mismatch recovery, least-privilege preflight, kill switch, pause/archive, scheduled-worktree cleanup, crash recovery, and safe terminal cleanup behave as specified.
- Every code child has one primary PR and exact merge validation; every operations child has authoritative non-PR evidence; no secrets or fake PRs were introduced.

Then add one concise parent roll-up comment with child/evidence links and move `SAAS-44` to `Done` manually. Never add `autonomous` to the parent or program-building children.

## Sources consulted

### Current workflow artifacts

- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-re-audit.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-18-three-delivery-workflows-task-audit.md` (failed independent audit that caused this in-place task revision)
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-18-three-delivery-workflows-task-re-audit.md` (failed re-audit whose provider-enforced publication-refusal finding caused the second in-place task revision)
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-dual-delivery-workflows-tasks.md` (historical task mapping/readiness reference)

### Tasking and repository contracts

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\SKILL.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\audit-checklist.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\task-template.md`
- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\planner.md`
- `C:\dev\luchdom\ai-config\src\agents\tasker.md`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\SKILL.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py`

### SaaS repository boundaries carried from the revised plan

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
- `C:\dev\luchdom\saas\apps\web\package-lock.json`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\scripts\smoke.ps1`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`

## Blockers and next gate

No task-breakdown blocker remains. Implementation remains deliberately blocked.

The next authorized action is **another fresh independent audit of `2026-07-17-three-delivery-workflows-plan.md` together with this revised task breakdown**. Only after that audit passes may the existing Linear `SAAS-44` through `SAAS-55` descriptions/dependencies be updated in place. Code, build/sync, installation, Linear workflow migration, Git/GitHub mutation, ntfy configuration/publishing, pilot execution, and schedule enablement still require the user's later explicit `Implement` approval.
