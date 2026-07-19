# SAAS-46 supervisor core — Execution tasks

## Status and authority

- Workflow: `1a0fa044-199b-4f57-ac46-1cc38061debb`
- Entry: semi-autonomous `$goal-to-delivery`
- Selected issue: `SAAS-46`
- Repository: `ai-config`
- Base: `main` at `e1f44b9dd3f4d281d104b4df06a94267c36eacee`
- Completion boundary: `merge`
- Design: not required; no product UI or interaction changes.
- Bootstrap authority: the root orchestrator may edit/publish under the audited program exception because this issue creates the reservation system. Specialists never mutate Linear or GitHub.

## Audit notes

- The plan contains explicit goals/non-goals, topology, schemas, module ownership, failure/recovery behavior, security boundaries, tests, documentation, rollout, rollback, and exact-SHA gates.
- No unresolved product/security/billing/cost/destructive-data/UX decision blocks tasking.
- The auditor must specifically challenge cross-file atomicity, capability secrecy/replay, safe stale release, worktree containment, assembled-Handoff crash recovery, preflight claims, and accidental base duplication.
- These notes are a tasker completeness check only and are not independent audit sign-off.

## Dependency graph

```text
S46-01 -> S46-02 -> S46-03 -> S46-04 -> S46-07
                   |         -> S46-05 -> S46-07
                   |         -> S46-06 -> S46-07
                   +--------------------> S46-07
S46-01 ---------------------------------> S46-08
S46-02..S46-08 -------------------------> S46-09
S46-09 ---------------------------------> S46-10
```

### S46-01 — Publish strict supervisor contracts and canonical base loader

- Goal: define the SAAS-46 public contract surface and prove every autonomous module imports the exact SAAS-45 base package/version instead of copying primitives.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/references/{project-config,prepared-iteration,checkpoint,supervisor-state,editing-reservation,operation-journal,worker-result,engine-command,release-authorization,handoff-authorization,trusted-observation}.schema.json`
  - `src/skills/linear-delivery-loop/scripts/{__init__,base_runtime,contracts}.py`
  - `tests/linear_delivery_supervisor/test_base_runtime.py`
  - `tests/linear_delivery_supervisor/test_contracts.py`
- Acceptance criteria:
  - Schemas use version `1.0`, exact required fields, `additionalProperties: false`, strict patterns/enums, and a complete runtime-parity inventory.
  - `engine-command.schema.json` is one strict discriminated request union for every public operation; each branch declares its exact fields and rejects unknown fields, raw capabilities, caller-selected output paths, and paths outside the operation's canonical repository/state roots.
  - Release/Handoff authorizations and trusted observations are versioned engine-owned contracts with opaque references, repository/operation binding, issue/workflow/run scope where applicable, freshness and one-shot/replay fields, and no caller-authored authority material. Handoff authorization JSON carries only the nonce hash and exact source/destination/path/request/reservation-revision bindings; its raw nonce remains in an engine sidecar.
  - One loader resolves the exact sibling `goal-to-delivery/scripts` package in source and generated/installed layouts and verifies base `1.0`, identity `1.0`, state home `2.0`, registry `1.0`, and descriptor `2.0`.
  - Missing/wrong exports, paths, versions, origins, or schema/runtime parity fail before supervisor state mutation.
  - Static tests reject copied identity, state-home, mutex, registry, workflow-init, descriptor, or base-Handoff implementations under `linear-delivery-loop`.
- Local test and runtime QA notes:
  - Run the focused base-loader and contract suites.
  - Include valid fixtures plus unknown field, malformed UUID/hash/path/timestamp, cross-field mismatch, secret-like material, and runtime-parity drift cases.
- Documentation impact: schema descriptions identify downstream SAAS-47/48 ownership and do not copy shared stage policy.
- Dependencies / blocks: depends on merged SAAS-45; blocks every later task.
- Risks and non-goals: no copied/reimplemented base primitive and no live provider contract; the only base extension is the narrow in-mutex Handoff reservation interlock assigned in S46-07.
- Completion/publication boundary: included in the primary SAAS-46 PR.

### S46-02 — Implement the transactional supervisor store and operation journal

- Goal: add machine-stable, revisioned, redacted supervisor/reservation documents with crash-safe paired transactions and replay-safe operation evidence under the base repository mutex.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/scripts/{store,operations,recovery}.py`
  - `tests/linear_delivery_supervisor/test_store_recovery.py`
  - `tests/linear_delivery_supervisor/test_operations.py`
- Acceptance criteria:
  - Construct the supervisor only through canonical `WorkflowManager`, using its verified identity/home, state guard, registry, and mutex.
  - Create exact contained directories/files for supervisor state, reservations, supervisor transactions, runs, operations, final attestations, issue worktrees, and validation worktrees.
  - State and reservation revisions are positive monotonic integers; compare-and-swap rejects stale revisions.
  - Paired transaction evidence binds exact before/after hashes and paths. Recovery accepts both-before, both-after, or a proven split; it rejects tampering/ambiguity and never reads/writes outside state home.
  - Idempotent operations bind operation id/key to one immutable request hash. Exact replay returns the recorded result; changed replay fails.
  - All outputs/exceptions are redacted and secret-like data cannot be persisted.
- Local test and runtime QA notes:
  - Inject interruption before journal write, after journal, after first paired write, after second write, before readback, and before journal completion.
  - Exercise hard-link, junction/reparse, traversal, stale revision, concurrent process, malformed/tampered JSON, and readback mismatch cases.
- Documentation impact: topology and transaction/recovery semantics go into `supervisor-core.md`.
- Dependencies / blocks: depends on S46-01; blocks lease, reservation, worktree, preflight, and Handoff tasks.
- Risks and non-goals: no external-operation execution; journal records local deterministic operations only.
- Completion/publication boundary: primary PR.

### S46-03 — Implement lease, prepared capability, and checkpoint state machine

- Goal: prevent concurrent/replayed autonomous mutation with renewable run leases, hash-bound single-use capabilities, and CAS checkpoints.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/scripts/{lease,supervisor}.py`
  - `tests/linear_delivery_supervisor/test_lease_capability.py`
  - `tests/linear_delivery_supervisor/test_checkpoints.py`
- Acceptance criteria:
  - Lease acquisition/renewal/release validates run, owner, repository, revision, heartbeat, expiry, and current capability status under the mutex.
  - `AcquireLease`, `RenewLease`, and `ReleaseLease` have distinct exact semantics: acquire creates one autonomous run authority, renew extends only the matching live run/owner/revision/capability, and release reconciles then revokes that exact authority.
  - Capability nonces are engine-generated with sufficient entropy and persisted only in an engine-owned, path-guarded sidecar under the canonical state home. Prepared/worker/public documents carry an opaque reference plus capability hash, never the raw nonce; outputs/logs/errors/repository files cannot expose it.
  - Lease decisions use an injected monotonic-clock abstraction and persist enough last-observed clock evidence to detect backward movement and implausibly large forward steps. A discontinuity records `clock-discontinuity`, blocks authority, and requires reconciliation; elapsed time alone never reclaims protected state.
  - `PrepareIteration` creates exactly one issue/workflow capability with exact state revision/stage, repository identity/key, issue-worktree identity, expiry, and transition constraints.
  - `ApplyCheckpoint` rejects fabricated/stale/expired/replayed/revoked nonce, stage, revision, issue/workflow, repository, worktree, SHA/PR/gate fields, or transition id.
  - Accepted checkpoints are idempotent, advance only allowed stages, rotate/revoke authority as specified, and never start/select a second issue.
  - Expired lease is reclaimed only after reservation/worktree/registry/operation reconciliation proves safety; ambiguity pauses.
- Local test and runtime QA notes:
   - Simultaneous acquire/renew races, killed owner, boundary timestamps, backward/large-forward clock jumps, replay with same/different transition, wrong worktree/repo, terminal/no-second-selection, and sentinel nonce leakage scans across state, repository, CLI output, logs, and exceptions.
- Documentation impact: lease/capability/checkpoint lifecycle.
- Dependencies / blocks: depends on S46-02; blocks reservations, worktrees, assembled Handoff, and CLI completion.
- Risks and non-goals: no model output grants authority; no provider re-read until later transport tasks.
- Completion/publication boundary: primary PR.

### S46-04 — Implement repository editing reservations and reconciliation

- Goal: protect autonomous, semi-autonomous, and manual repository deliverable mutation across runs without releasing protected work based on time alone.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/scripts/reservations.py`
  - `tests/linear_delivery_supervisor/test_reservations.py`
- Acceptance criteria:
  - Reservation records exact workflow/issue, repository identity/key, physical worktree, policy, owner/run, revision, heartbeat/expiry, and dirty/branch/unpushed/unmerged/PR/accessibility/ambiguity/planning summary.
  - Exact-owner reserve/renew is idempotent; a different live owner conflicts.
  - `RenewReservation` extends only the matching live reservation owner/revision after reconciling current protected state; `AuthorizeMutation` issues a scoped one-operation authorization only after the current reservation and capability are proven.
  - `Reserve` creates an engine-owned opaque release-authorization reference bound to the reservation/repository/workflow/issue/run/operation/revision; `AuthorizeMutation` proves the current reservation/capability before any deliverable write.
  - `Release` requires the current engine-owned one-shot authorization and capability reference. The engine observes local Git/worktree state itself and accepts external state only through a versioned trusted-adapter observation bound to repository, operation, head SHA, PR when present, issuance/freshness, and replay identity.
  - Forged, stale, replayed, unavailable, model-authored, secret-bearing, wrong-repository, wrong-head, wrong-PR, or otherwise ambiguous external evidence keeps work protected.
  - Dirty, unmerged, unpushed, open-PR, inaccessible, or ambiguous work remains reserved after expiry.
  - Clean planning-only staleness may be reclaimed only after registry, physical worktree, operation, and supplied external-observation reconciliation.
  - Reservations in another normalized repository do not block this repository.
  - Manual/semi/autonomous races and abandonment outcomes preserve the documented state-transition proposal contract without directly mutating Linear.
- Local test and runtime QA notes:
  - Cross-process reserve race, renewal/staleness, each protected summary bit, clean planning reclaim, explicit release, forged/stale/replayed/wrong-scope authorization and trusted-observation fixtures, abandon/recover, same versus different repository, wrong source fingerprint, and sentinel redaction.
- Documentation impact: reservation lifecycle, WIP composition, safe release and recovery.
- Dependencies / blocks: depends on S46-02 and S46-03; blocks S46-07.
- Risks and non-goals: no direct Linear state/label mutation.
- Completion/publication boundary: primary PR.

### S46-05 — Implement persistent issue and exact-SHA gate worktree management

- Goal: make scheduled worktrees disposable while one issue maps idempotently to one persistent contained worktree and gate worktrees remain exact-SHA disposable records.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/scripts/worktrees.py`
  - `tests/linear_delivery_supervisor/test_worktrees.py`
- Acceptance criteria:
  - Use fixed subprocess argv with `shell=False`; issue/config content never becomes a command fragment.
  - One canonical issue id maps to one direct contained path under `<state-home>/worktrees` and one observed common Git repository.
  - Reuse is idempotent only when branch/HEAD/common-dir/fingerprint/path mapping agrees.
  - Implementation/checkpoint rejects the scheduled control worktree, unregistered linked worktree, different repository, overlap, dirty unexpected state, symlink/junction/mount/reparse escape, case collision, or missing/inaccessible mapping.
  - Two scheduled control worktrees derive the same supervisor mapping and remain recoverable after either is archived/removed.
  - Gate records bind one operation id, exact SHA, contained detached worktree, clean-before/after and attestation state. Cleanup refuses a live reservation, dirty/mismatched SHA, incomplete attestation, unresolved operation, or ambiguous path.
- Local test and runtime QA notes:
  - Temporary Git repository and linked worktrees on Windows; two control worktrees, archive/removal, idempotent reuse, same-name/case collision, traversal/reparse, scheduled-control rejection, protected cleanup, and different repository.
- Documentation impact: control versus persistent versus gate worktree topology and cleanup.
- Dependencies / blocks: depends on S46-02 and S46-03; blocks S46-07.
- Risks and non-goals: no branch publication, staging, commit, push, PR, merge, or actual quality gate orchestration.
- Completion/publication boundary: primary PR.

### S46-06 — Implement mutation-free permission preflight and fixture probes

- Goal: validate the unattended least-privilege contract before claim using local checks plus strictly structured read-only probe results.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/scripts/preflight.py`
  - `tests/linear_delivery_supervisor/fixtures/preflight/*.json`
  - `tests/linear_delivery_supervisor/test_preflight.py`
- Acceptance criteria:
  - Validate exact engine/base/config/probe versions, repository key/base, writable roots, state/mutex/worktree-root access, fixed wrapper/Git/`gh` argv shapes, aggregate path, host allowlist, loopback targets, required env names, forbidden unrelated provider-secret patterns, and redaction.
  - Accept only `workspace-write`, `sandbox_workspace_write.network_access`, and `approval_policy = "never"`; reject danger/full access, beta named profile composition, arbitrary shell/Git flags, force/history rewrite, hosted-check commands, provider settings/bypass commands, broad LAN/loopback, and unallowlisted redirect hosts.
  - State/worktree sentinel create-read-remove uses only authoritative roots and finishes before any claim/reservation/Git/external mutation.
  - Structured probe adapter supplies read-only Git/`gh`/remote/Linear/ntfy/loopback outcomes. Missing, wrong-version, mutated, ambiguous, or secret-bearing probe evidence fails.
  - Child environment retains only declared core/path/state and required secret variable names; unrelated AWS/Azure/GCP/deployment/analytics/production secrets fail before claim.
  - Failures are actionable but contain no secret values.
- Local test and runtime QA notes:
  - Deny each control independently; validate redirect/DNS target fields, exact loopback host/port, missing required variable, forbidden inherited variable, inaccessible roots/engine, command drift, Git/gh/probe failures, cleanup failure, and one exact passing profile.
- Documentation impact: permission/preflight contract and later live-adapter boundary.
- Dependencies / blocks: depends on S46-01 and S46-02; blocks S46-07.
- Risks and non-goals: fixtures prove the interface; no live provider mutation/publish and no scheduled profile installation.
- Completion/publication boundary: primary PR.

### S46-07 — Assemble recovery, reservation-aware Handoff, status, cleanup, and structured commands

- Goal: expose the deterministic supervisor lifecycle and prove base Handoff plus live authority transfer is crash-recoverable and revokes the source.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/scripts/{assembled_handoff,recovery,supervisor,cli}.py`
  - `src/skills/linear-delivery-loop/scripts/agent-worker-engine.ps1`
  - `src/skills/goal-to-delivery/scripts/{workflow_init,handoff,reservation_interlock}.py`
  - `tests/linear_delivery_supervisor/test_assembled_handoff.py`
  - `tests/linear_delivery_supervisor/test_cli_wrapper.py`
  - `tests/linear_delivery_supervisor/test_status_cleanup.py`
- Acceptance criteria:
  - Expose exactly the exhaustive structured operation set `Preflight`, `AcquireLease`, `RenewLease`, `PrepareIteration`, `ApplyCheckpoint`, `Status`, `Reserve`, `RenewReservation`, `AuthorizeMutation`, `Release`, `Recover`, `Cleanup`, `Handoff`, and `ReleaseLease`; every schema branch is dispatched and each acquire/renew/authorize/release operation enforces the semantics assigned in S46-03/S46-04.
  - CLI/wrapper accepts only the versioned discriminated `EngineCommand` envelope from a contained canonical request path, writes to the command's canonical engine-owned result path, emits one redacted JSON result/error, returns deterministic exit codes, and never accepts raw capabilities, caller-selected output paths, nested Codex, or arbitrary shell.
  - `Status` and `Recover` derive identical state from any linked worktree and after scheduled-control removal.
  - Cleanup is engine-owned, contained and journaled; protected/live/dirty/unresolved/ambiguous state fails closed.
  - Assembled Handoff is a mandatory three-phase barrier: under the supervisor/base mutex validate scope, journal `handoff-pending`, suspend source mutation, and mint an engine-owned one-shot Handoff authorization; release the mutex; invoke the self-locking canonical base Handoff exactly once with the internally resolved authorization; reacquire the mutex to verify base registry/evidence and CAS-transfer/revoke, or restore the source only on a proven base failure. It never calls base Handoff while holding the same non-reentrant mutex.
  - Every authority-bearing command detects `handoff-pending` and either reconciles that exact transition or fails closed. Crashes before, during, or after base/supervisor transfer cannot permit duplicate copy, split authority, or concurrent renewal/checkpoint/reserve/release/cleanup mutation.
  - After canonical base Handoff acquires its existing mutex, a narrow base-package interlock re-reads the authoritative reservation/pending-operation/Handoff-authorization records, validates every source/destination/path/request/revision/nonce-hash binding, and atomically consumes the grant before existing base transfer logic runs. Missing, forged, stale, replayed, wrong-scope, or public-CLI-supplied authority rejects whenever a live/pending reservation exists; no-reservation registry-only Handoff stays allowed.
  - The public base CLI cannot accept the internal authorization. A direct-base-Handoff versus first `Reserve` race is serialized safely in both lock orders: Reserve-first makes Handoff reject; Handoff-first changes base authority so Reserve's mandatory in-lock revalidation rejects.
  - Proven base failure restores source authority; ambiguous base outcome remains suspended/protected for recovery; successful transfer denies all later source renew, metadata mutation, artifact-write authorization and checkpoint while allowing the destination.
  - Native Codex Hand off remains outside this transition and fails with deterministic mismatch/recovery guidance.
- Local test and runtime QA notes:
  - Every crash boundary plus concurrent renew/checkpoint/reserve/release/cleanup during all three Handoff phases, direct-base-Handoff bypass, both `Reserve`/direct-Handoff race orders, forged/replayed Handoff authorization, consumed-grant proven-failure and ambiguous-outcome recovery, wrong expected path, destination dirty/different repo, capability/revision mismatch, evidence tampering, source/destination postconditions, CLI invalid JSON/unknown operation/path escape/caller output path/raw capability, PowerShell fixed invocation, and no secret/traceback.
- Documentation impact: full command/status/recovery/cleanup and assembled-Handoff runbook.
- Dependencies / blocks: depends on S46-03 through S46-06; blocks S46-08/09.
- Risks and non-goals: no live reservation is inferred from base transfer; no native Hand off automation.
- Completion/publication boundary: primary PR.

### S46-08 — Integrate build projections, semantic boundaries, and durable documentation

- Goal: make the new supervisor contracts discoverable, generated identically for supported tools, and documented without creating a second workflow protocol.
- Target repository: `ai-config`.
- Likely files/modules:
  - `src/skills/linear-delivery-loop/SKILL.md`
  - `src/skills/{goal-to-delivery,spec-driven-delivery}/SKILL.md`
  - `src/skills/goal-to-delivery/scripts/{workflow_init,handoff,reservation_interlock}.py` (narrow in-mutex live-reservation interlock only)
  - applicable project templates/shared implementer guidance
  - `src/skills/linear-delivery-loop/references/supervisor-core.md`
  - `README.md`
  - `validation/delivery_contracts.py`
  - `tests/test_delivery_contracts.py`
- Acceptance criteria:
  - Thin autonomous entry skill references structured prepared capability/worker result/checkpoint commands but contains no selection/transport implementation.
  - Semi-autonomous and manual spec-driven entry surfaces deterministically call `Reserve`, `RenewReservation`, `AuthorizeMutation`, `Status`, `Release`, recovery, and assembled `Handoff` before deliverable mutation. Autonomous entry additionally calls `AcquireLease`, `RenewLease`, `PrepareIteration`, checkpoints, and `ReleaseLease`. Planning-only work stays non-mutating until implementation authority is granted.
  - The canonical base Handoff API contains only the in-mutex live/pending-reservation interlock and an internal kw-only authorization value unavailable to its CLI; it does not copy supervisor transfer logic.
  - README/reference explain state topology, base ownership, reservations, permissions, recovery/cleanup, structured commands, and later SAAS-47/48 boundaries.
  - Build emits every schema/script/reference to Codex/Claude/Copilot projections and `dist/manifest.json` with exact source hashes.
  - Contract tests reject missing/drifting schemas, copied base primitives, bypassable semi/manual mutation or direct base Handoff, nested Codex, provider transports, hosted-check integration, arbitrary shell, SaaS identifiers, or competing canonical workflow doctrine.
  - Source edits regenerate identical supported-tool projections; semantic tests prove installed/generated entry surfaces inherit the reservation and assembled-Handoff requirements.
- Local test and runtime QA notes:
  - Run build, projection parity, link/reference, retired-term, wrapper-boundary, and semantic tests.
- Documentation impact: primary task output.
- Dependencies / blocks: depends on S46-01 and public surfaces from S46-07; blocks S46-09.
- Risks and non-goals: do not sync real user/project environments in validation.
- Completion/publication boundary: primary PR.

### S46-09 — Run focused and aggregate verification, independent review, and repair loops

- Goal: prove every SAAS-46 acceptance criterion against the exact working-tree target before publication.
- Target repository: `ai-config`.
- Likely files/modules:
  - all S46 implementation/tests/docs
  - registered `*-code-review.md` and `*-qa.md` artifacts
- Acceptance criteria:
  - All focused supervisor tests pass without skips for applicable Windows behavior.
  - `python .\scripts\validate.py`, compile checks, and `git diff --check` pass.
  - Exact implementation manifest and base SHA are recorded.
  - Independent code reviewer reports no P1/P2; defects return to the matching implementer and are rereviewed.
  - QA maps every issue acceptance criterion to a real test/CLI behavior result and records residual unverified live-transport work as intentional SAAS-47/48 scope.
  - Documentation gate passes and no secret-like sentinel appears anywhere in repository diff or emitted evidence.
- Local test and runtime QA notes:
  - Smallest affected suites first, then the full aggregate once per repaired target.
- Documentation impact: code-review and QA evidence in the registered folder; durable docs already owned by S46-08.
- Dependencies / blocks: depends on S46-01 through S46-08; blocks publication.
- Risks and non-goals: reviewer/QA report and do not fix production code.
- Completion/publication boundary: verified working tree, then continue because active boundary is merge.

### S46-10 — Publish, squash merge, and attest the exact merged SHA

- Goal: deliver one primary PR and complete SAAS-46 only after exact-head and exact-merge local evidence.
- Target repository: `ai-config` plus linked SAAS-46 tracking.
- Likely files/modules:
  - registered PR description and completion artifacts
  - GitHub PR and Linear comments/attachment/state
- Acceptance criteria:
  - Create one intentional branch/commit from the reviewed target; no unrelated files or secrets.
  - Push and open one PR using `$pr-description`; record exact head SHA.
  - In a fresh detached worktree at exact PR head, require clean before/after and run `python .\scripts\validate.py`; no hosted checks are queried.
  - Squash merge only if exact-head review/QA/docs/local gate remain valid.
  - Read back exact merge SHA; in a second fresh detached worktree require clean before/after and rerun the aggregate.
  - Record exact PR/head/merge/test evidence in GitHub/Linear without a post-merge repository mutation; remove temporary worktrees/remote feature branch safely.
  - Move SAAS-46 to Done only after merged-SHA PASS and stop without selecting SAAS-47.
- Local test and runtime QA notes: exact-head and exact-merge aggregate commands are mandatory; provider refusal preserves work and is reported, never bypassed.
- Documentation impact: completion evidence only; no artificial follow-up commit.
- Dependencies / blocks: depends on S46-09; unblocks SAAS-47 and SAAS-48 interfaces.
- Risks and non-goals: no force push, direct-main push, provider-setting change, hosted-check polling, auto-revert, or second issue.
- Completion/publication boundary: `merge`.

## Sources consulted

- `AGENTS.md`
- `README.md`
- `docs-ai/002-saas-46-supervisor-reservation-permissions-recov/workflow.json`
- `docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-plan.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-{plan,tasks}.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- `src/skills/goal-to-delivery/references/`
- `src/skills/goal-to-delivery/scripts/`
- `src/skills/linear-delivery-loop/SKILL.md`
- `validation/manifest.json`
- `scripts/{build,validate}.py`
- `tests/goal_to_delivery_base/`
- Linear issue `SAAS-46`.
