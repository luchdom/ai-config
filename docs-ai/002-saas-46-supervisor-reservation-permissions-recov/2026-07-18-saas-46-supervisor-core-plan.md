# SAAS-46 — Machine-stable supervisor core plan

## Workflow context

- Workflow ID: `1a0fa044-199b-4f57-ac46-1cc38061debb`
- Entry: `$goal-to-delivery`
- Policy: semi-autonomous
- Selected issue: `SAAS-46` / `DDW-AIC-002`
- Repository key: `ai-config`
- Base branch/SHA: `main` / `e1f44b9dd3f4d281d104b4df06a94267c36eacee`
- Completion boundary: `merge`
- Design: not required; this changes local delivery tooling and has no product UI or interaction surface.

## 1. Overview

Consume the exact versioned local-work primitives merged by SAAS-45 and add the deterministic local supervisor layer needed by the future autonomous Linear loop. The supervisor will own machine-stable revisioned state, short command serialization, renewable run leases, prepared capabilities, editing reservations, replay-safe operation journals, persistent issue worktrees, exact-SHA gate-worktree records, permission preflight, recovery/cleanup, status, and reservation-aware workflow-managed Handoff.

This issue does not select Linear work, call live Linear/ntfy/GitHub mutation transports, publish code autonomously, create a scheduled task, or implement model reasoning. It publishes local contracts and dependency-free fixtures that SAAS-47 and SAAS-48 will consume.

## 2. Discovery evidence

### Relevant repository sources

- `AGENTS.md`: `src/` is canonical, `dist/` is generated, project templates stay thin, and `python .\scripts\validate.py` is the sole aggregate gate.
- `README.md`: documents the three entry policies, base workflow identity, state-home binding, Handoff boundary, build, validation, and sync behavior.
- `src/skills/goal-to-delivery/scripts/`: canonical SAAS-45 base package. It exclusively owns repository identity, state-home derivation, state path containment, allocation mutex, workflow registry, descriptor lifecycle, exact physical-worktree binding, and registry-only workflow-managed Handoff.
- `src/skills/linear-delivery-loop/SKILL.md`: thin autonomous policy entry; deterministic code must prepare and validate authority.
- `validation/manifest.json` and `scripts/validate.py`: fixed, dependency-free aggregate that already discovers every `tests/test*.py`; no second validator is needed.
- `tests/goal_to_delivery_base/`: nearest patterns for temporary repositories, linked worktrees, Windows junctions, crash/race coverage, and fail-closed state-path tests.
- Finalized program plan/tasks/audit under `docs-ai/001-dual-delivery-workflows-2026-07-16/`: locked SAAS-46 scope, topology, safety constraints, test ownership, bootstrap exception, and exact-SHA publication gates.

### Existing base versions to require

- Base package: `1.0`
- Repository identity: `1.0`
- State home: `2.0`
- Registry: `1.0`
- Work descriptor: `2.0`

The autonomous layer will load the sibling `goal-to-delivery/scripts` package through one canonical, version-checking loader. No file under `linear-delivery-loop` may rederive repository identity, choose a state-home fallback, implement another allocation mutex/registry, or copy base Handoff logic.

## 3. Goals and non-goals

### Goals

1. Define versioned JSON contracts for project configuration, prepared iteration, checkpoint, supervisor state, reservation, operation journal, and worker result.
2. Derive one authoritative supervisor home from any linked worktree through the SAAS-45 identity/state-home modules.
3. Implement atomic compare-and-swap state transitions and crash-recoverable paired state/reservation updates under the base repository mutex.
4. Implement renewable leases and single-use prepared capability nonces that reject expiry, replay, wrong repository/worktree, wrong stage, and stale revisions.
5. Protect autonomous, semi-autonomous, and manual repository-deliverable mutation with one repository-scoped reservation namespace.
6. Map one selected issue idempotently to one contained persistent issue worktree and track contained exact-SHA gate worktrees.
7. Expose one exhaustive deterministic command surface: `Preflight`, `AcquireLease`, `RenewLease`, `PrepareIteration`, `ApplyCheckpoint`, `Status`, `Reserve`, `RenewReservation`, `AuthorizeMutation`, `Release`, `Recover`, `Cleanup`, `Handoff`, and `ReleaseLease`, using structured files.
8. Assemble the base registry-only Handoff with live reservation/capability transfer and source revocation.
9. Add dependency-free positive, negative, race, replay, crash, Windows containment, permission, redaction, and import-boundary tests to the existing aggregate.
10. Document the reusable state topology, reservation lifecycle, permission model, recovery, cleanup, and Handoff behavior without copying the canonical delivery protocol.

### Non-goals

- Linear queue selection, issue mutation, pagination, decisions, or follow-up transport.
- ntfy publication or notification delivery.
- GitHub push/PR/merge transport, provider-refusal classification, exact-SHA gate orchestration, or hosted-check integration.
- SaaS-specific team, repository, command, loopback, or label configuration.
- Scheduled task creation or enablement.
- Nested `codex exec`, arbitrary shell execution, arbitrary Git flags, or model-supplied authority.
- Reimplementation of the SAAS-45 base primitives. The only permitted base-package change is the narrow, additive in-mutex reservation interlock required to make canonical Handoff safe; identity, state-home, mutex, registry, descriptor, transaction, and copy semantics remain base-owned.

## 4. Assumptions and constraints

### Safe assumptions

- Python 3.12 and PowerShell are available because the current repository build/test/sync surfaces already depend on them.
- Runtime code remains standard-library-only; JSON Schema files are normative portable contracts and have dependency-free runtime validators/tests.
- Nanosecond UTC timestamps and UUIDs are generated by deterministic engine code, never accepted as authority from a worker result.
- The actual capability nonce is stored only in authoritative machine-local run state/prepared files; durable logs and public results contain only identifiers or hashes.
- External permission/connectivity checks use a strict probe-adapter interface in SAAS-46. Dependency-free fixtures prove the contract; live Linear/ntfy/GitHub adapters arrive in later issues.
- The current interactive run uses the audited bootstrap exception because SAAS-46 creates the reservation machinery. Root orchestration alone owns tracking and Git publication until merge.

### Hard constraints

- State remains outside every checkout under the verified SAAS-45 state home.
- Time alone never releases dirty, unmerged, unpushed, open-PR, inaccessible, live, or ambiguous protected work.
- Every state mutation revalidates repository key, common Git identity, physical worktree authority, expected revision, lease, reservation, and capability as applicable.
- Scheduled control worktrees are never registered as implementation worktrees.
- Cleanup is contained, journaled, and fail-closed; no cross-shell recursive deletion.
- Secret-like values are rejected/redacted before serialization or output.
- `workspace-write`, `sandbox_workspace_write`, and `approval_policy = "never"` are the only scheduled-policy vocabulary; no full-access fallback or beta profile composition.

## 5. Architecture and contracts

### 5.1 Canonical base loader

Add one `base_runtime.py` loader under `linear-delivery-loop/scripts`. It resolves the exact sibling `goal-to-delivery/scripts/__init__.py`, loads it as a package with submodule search locations, verifies the five required versions, and returns the canonical classes/functions. It fails closed when the package path, version, export, or module origin differs. Static contract tests reject duplicate filenames/definitions for identity, state home, mutex, registry, descriptor allocation, or base Handoff in the autonomous package.

### 5.2 Authoritative topology

Use the base `WorkflowManager` to obtain the verified identity, repository-scoped state home, `StatePathGuard`, workflow registry, and repository mutex. Add only these children:

```text
<state-home>/
  supervisor-state.json
  reservations.json
  supervisor-transactions/<transaction-id>.json
  operations/<operation-id>/request.json
  operations/<operation-id>/result.json
  runs/<run-id>/request.json
  runs/<run-id>/prepared-iteration.json
  runs/<run-id>/result.json
  final-attestations/<attestation-id>.json
  worktrees/<issue-id>/
  validation-worktrees/<operation-id>/
```

The existing `repository.json`, `registry.json`, allocation lock, base transactions, quarantine, stale-lock evidence, and base Handoff evidence remain base-owned.

### 5.3 Supervisor state and transactions

`supervisor-state.json` contains repository identity/bound versions, monotonic revision, optional lease, capability hashes/status, issue-to-worktree mappings, operation references, retry counters, and terminal/recovery summaries. `reservations.json` contains a monotonic revision and repository-scoped reservation records.

All ordinary supervisor commands acquire the base repository mutex for their short state transition. A paired transaction record stores exact before/after state and reservation documents. Recovery accepts only three states: both before, both after, or a proven split pair. It completes/rolls back deterministically from immutable transaction evidence and rejects tampered or ambiguous records. Compare-and-swap rejects stale expected revisions.

The canonical base Handoff is the deliberate exception: it acquires the same non-reentrant mutex internally. The assembled protocol therefore uses a split-phase pending barrier instead of nesting the lock. Phase A records `handoff-pending`, suspends source capability/reservation mutation, mints a one-shot internal base-Handoff authorization, and releases the mutex. Phase B invokes the self-locking canonical base Handoff once with that engine-held authorization. Inside its own mutex, a narrow base-package interlock validates and consumes the authorization against the pending operation before existing copy/registry logic may run. Phase C reacquires the mutex, verifies authoritative base evidence, and either transfers/revokes authority or restores the source after a proven base failure. Every authority-bearing supervisor command must check the pending barrier first and stop or reconcile; it cannot renew, checkpoint, reserve, release, clean, or start another Handoff through the interval.

### 5.4 Lease and prepared capability

A lease records run id, owner id, heartbeat/expiry, last observed wall time, revision, and capability hash. Renewal requires the current run/owner, expected revision, compatible repository, and non-revoked capability. Time is supplied through an injectable clock. A backward jump or a forward jump beyond the configured maximum step marks `clock-discontinuity` and requires reconciliation; expiry or clock movement never grants immediate takeover.

`PreparedIteration` contains exactly one issue/workflow, run, repository identity/key, persistent worktree fingerprint/path, state revision/stage, expiry, and an opaque engine-owned capability reference/hash. The raw high-entropy nonce lives only in an engine-created sidecar beneath the authoritative run directory. It is never placed in a worker-authored request, checkout, artifact, patch, manifest, stdout/stderr, or caller-selected output. `ApplyCheckpoint` receives the prepared reference plus a non-authoritative worker result, resolves and hashes the sidecar internally, consumes one transition id once, validates the expected previous stage and observed identities, and revokes or rotates capability authority after accepted transitions.

### 5.5 Reservations

A reservation records workflow/issue, repository identity/key, physical worktree fingerprint/path, policy, owner/run, state revision, heartbeat/expiry, and protected-work summary: dirty, branch, unpushed, unmerged, PR id/state, accessibility, ambiguity, and planning-only status.

- `Reserve` is idempotent for the exact owner/workflow/context and conflicts for a different live owner.
- `Reserve` creates an engine-owned opaque authorization record beneath state home. Semi/manual `AuthorizeMutation`, renewal, Release, and Handoff reference that contained one-workflow authorization path; owner/run strings or caller prose never grant authority. Autonomous commands use the current engine capability instead.
- `Release` requires the engine-owned one-shot authorization/capability plus engine-observed local Git facts and, whenever PR/provider state is relevant, a fresh adapter-attested external observation already journaled by a trusted versioned adapter. The request cannot supply a clean/protected summary as authority.
- A trusted external observation binds adapter version/id, one-time observation id, repository/common identity, branch/head, PR id/state when applicable, observed timestamp/expiry, and journal hash. Unknown, stale, replayed, unavailable, caller/model-authored, mismatched, or unjournaled evidence becomes `ambiguous` and remains protected. Until SAAS-47/48 provide live adapters, fixtures may issue such observations only through the engine-owned fixture adapter interface.
- Expired clean planning-only reservations may be reclaimed only after registry, physical-worktree, engine-observed Git, operation, and applicable trusted external-observation reconciliation.
- Any dirty, unmerged, unpushed, open-PR, inaccessible, or ambiguous summary remains protected regardless of time.
- Repository identity provides the namespace, so another repository never blocks this one.

### 5.6 Persistent and gate worktrees

`WorktreeManager` builds fixed subprocess argument lists and never accepts command fragments. One canonical issue id maps to one direct child of `<state-home>/worktrees`; mapping creation/reuse verifies common Git identity, path containment, reparse safety, branch/HEAD expectations, and physical fingerprint. Implementation/checkpoint commands reject the scheduled control worktree and any worktree not equal to the registered issue mapping.

Gate-worktree records are exact-SHA, contained, temporary mappings under `validation-worktrees`. SAAS-46 proves allocation/status/cleanup safety; SAAS-48 later runs publication gates there.

### 5.7 Operation journal and recovery

Every idempotent action has an engine-generated operation id/idempotency key, immutable request hash, status, attempt count, before/after observations, and redacted result. Repeating the exact request returns the prior result; changed content under the same id fails. Pending operations reconcile from authoritative local observations before retry. This issue does not call external mutation transports.

### 5.8 Permission preflight

`ProjectConfig` separates:

- engine/base/config versions;
- repository key/base branch and fixed aggregate command;
- exact writable roots;
- fixed wrapper/Git/`gh` argv shapes;
- external host allowlist and exact loopback host/ports;
- required environment variable names and forbidden provider-secret patterns;
- probe-adapter contract/version.

Preflight validates local paths, installed engine/version, state sentinel create/read/remove, base mutex, contained worktree-root sentinel, aggregate presence, environment minimization, command allowlists, host/redirect/loopback policy, and redaction. Read-only Git/`gh`/provider/connectivity outcomes arrive through a structured probe adapter and are independently validated. Failure occurs before claim/reservation/worktree/Git/external mutation and emits only redacted actionable evidence.

### 5.9 Assembled workflow-managed Handoff

The actual base API is self-locking, so assembled Handoff is an explicit three-phase state machine plus a minimal in-lock base interlock:

1. **Prepare under the base mutex:** revalidate the exact live source workflow, reservation, lease/capability, expected changed scope, destination identity/cleanliness, and absence of another pending barrier. Write an immutable pending operation, mark the reservation `handoff-pending`, suspend source capability mutation, and mint an engine-owned one-shot Handoff authorization. Its authoritative JSON stores only a hash and exact operation/workflow/repository/source/destination/expected-path/request/reservation-revision bindings; the raw nonce is held in a path-guarded engine sidecar and never enters CLI input/output, repository files, or model-authored content. Release the mutex.
2. **Execute without a caller-held mutex:** the assembled engine resolves the sidecar internally and invokes the canonical base `workflow_managed_handoff` once with a kw-only internal authorization value that the public CLI cannot accept. After the base function acquires its existing mutex, the narrow base interlock re-reads reservations/pending operation/authorization from the canonical state home, verifies every binding and nonce hash, rejects forged/expired/replayed/wrong-scope grants, and atomically marks the grant consumed before existing base Handoff transfer logic proceeds. With a live/pending reservation, missing or invalid authorization always rejects. With no reservation, ordinary registry-only Handoff remains allowed.
3. **Finalize under the base mutex:** re-read the base registry/evidence. If the base source mapping still owns authority and the operation proves failure, restore the exact source reservation/capability. If the destination mapping and evidence prove success, compare-and-swap the reservation/capability fingerprint/path to the destination and permanently revoke source authority. Ambiguous evidence leaves the barrier protected for attended recovery. Persist completion and expose success only after readback.

Recovery follows the same observations after a crash at any phase and never invokes the base copy twice for an already-proven result. A consumed authorization plus proven no-transfer is a failed operation that requires a newly prepared operation; an ambiguous transfer remains protected and cannot reuse or remint authority. Concurrent renew, checkpoint, reserve, release, cleanup, another assembled Handoff, and the public base-Handoff route are tested while the barrier is prepared, executing, and finalizing. The no-reservation `Reserve` versus direct-base-Handoff race is tested in both lock orders: if Reserve wins, Handoff sees the reservation and rejects; if Handoff wins, Reserve revalidates the changed base registry/source authority and rejects. Later source renew, metadata mutation, artifact-write authorization, or checkpoint fails on both base and supervisor physical-worktree authority.

### 5.10 Structured command surface

Add a Python CLI and a thin `agent-worker-engine.ps1` wrapper. One strict discriminated `EngineCommand` envelope exhaustively covers `Preflight`, `AcquireLease`, `RenewLease`, `PrepareIteration`, `ApplyCheckpoint`, `Status`, `Reserve`, `RenewReservation`, `AuthorizeMutation`, `Release`, `Recover`, `Cleanup`, `Handoff`, and `ReleaseLease`. `AcquireLease` establishes autonomous run authority; `RenewLease` extends only the exact live run/owner/revision/capability; `RenewReservation` extends only the exact live reservation owner/revision after protected-state reconciliation; `AuthorizeMutation` emits a scoped one-operation mutation authorization after checking the current reservation/capability. Every variant has exact fields, `additionalProperties: false`, proposal-versus-authority classification, and versioned path rules.

Proposal/config/worker-result files may be read from a verified repository or workflow path only when their schema contains no authority or raw capability. Authority references, release authorization, trusted external observations, pending requests, prepared capability sidecars, authoritative results, and nonce-bearing content must be engine-created direct descendants of the verified state home. The caller cannot choose an authoritative output path. CLI stdout/stderr contains one redacted public result without capability material, traceback, or secret. The wrapper accepts only the named envelope path, invokes the installed sibling Python engine with fixed arguments, and never launches Codex.

### 5.11 Semi/manual reservation and Handoff integration

The common reservation system is not autonomous-only. Update `$goal-to-delivery` and `$spec-driven-delivery` to call deterministic `Reserve`, `RenewReservation`, `AuthorizeMutation`, `Status`, `Release`, and assembled `Handoff` operations before repository-deliverable mutation. Autonomous entry additionally uses `AcquireLease`, `RenewLease`, `PrepareIteration`, checkpoint, and `ReleaseLease`. Implementer authorization checks fail closed when the workflow has no matching live reservation/authorization, while isolated plan/clarify/task/audit files retain the documented planning exception.

The public SAAS-45 base CLI remains the registry-only primitive for workflows with no live reservation and exposes no argument for the internal Handoff authorization. The canonical base Handoff function gains only the in-mutex interlock and kw-only internal authorization input described in §5.9, not copied reservation transfer logic. Generated Codex/Claude/Copilot skill projections and project routing remain source-derived through the normal build.

## 6. Schemas

Create version `1.0` schemas under `src/skills/linear-delivery-loop/references/`:

- `project-config.schema.json`
- `prepared-iteration.schema.json`
- `checkpoint.schema.json`
- `supervisor-state.schema.json`
- `editing-reservation.schema.json`
- `operation-journal.schema.json`
- `worker-result.schema.json`
- `engine-command.schema.json`
- `release-authorization.schema.json`
- `handoff-authorization.schema.json`
- `trusted-observation.schema.json`

Each uses `additionalProperties: false`, strict enumerations/patterns, exact required fields, and an `x-luchdom-runtimeParity` inventory for OS identity, path containment, secret redaction, cross-field equality, temporal ordering, and hash/nonce constraints enforced by runtime validators.

## 7. Likely implementation modules

```text
src/skills/linear-delivery-loop/
  references/*.schema.json
  references/supervisor-core.md
  scripts/__init__.py
  scripts/base_runtime.py
  scripts/contracts.py
  scripts/store.py
  scripts/lease.py
  scripts/reservations.py
  scripts/operations.py
  scripts/worktrees.py
  scripts/preflight.py
  scripts/recovery.py
  scripts/assembled_handoff.py
  scripts/supervisor.py
  scripts/cli.py
  scripts/agent-worker-engine.ps1
```

The integration slice also updates `goal-to-delivery/SKILL.md`, `spec-driven-delivery/SKILL.md`, the base Handoff API plus a narrow in-mutex `reservation_interlock.py`, shared implementer guidance/templates where necessary, and semantic tests. It does not move or duplicate supervisor reservation transfer logic into the base package.

Tests live under `tests/linear_delivery_supervisor/`, with shared temporary-repository and fixture-probe helpers. Existing base tests remain unchanged except where an import-boundary assertion intentionally needs shared inventory.

## 8. Testing strategy

### Focused tests

- Exact base package path/export/version loading and failure on drift/duplicate primitive definitions.
- Same supervisor home/state/mutex from two linked scheduled control worktrees and after either control worktree is removed.
- Atomic state/reservation creation, monotonic revisions, stale CAS, split-write crash recovery, tampered journal failure, and readback.
- Lease acquire/renew/release races, expiry with safe versus ambiguous reconciliation, injected backward/large-forward clock discontinuity, capability reference replay/revocation, wrong worktree/repository/stage/revision, and one-issue-per-run terminal behavior.
- Reservation races across autonomous/semi/manual policies, deterministic entry-surface acquisition/authorization enforcement, forged release owner/run/path, protected expired work, engine-observed Git, trusted observation freshness/replay/repository/head/PR binding, unavailable external state, clean planning reclaim, explicit safe release, and different-repository independence.
- Idempotent persistent issue worktree reuse, scheduled-control rejection, containment/reparse/case collision, exact gate SHA mapping, and protected cleanup refusal.
- Every preflight denial: engine/version, state/mutex/root, command shape, environment minimization, required secret presence, forbidden secret inheritance, external host/redirect, loopback, Git/`gh`, provider probe, aggregate path, and redaction; plus one exact approved fixture.
- Sentinel credentials absent from state, operations, results, exceptions, wrapper output, patches, and manifests.
- Assembled live-reservation Handoff success, split-phase barrier concurrency at prepare/execute/finalize, crash recovery, source revocation, destination authority, base-CLI live-reservation rejection, native Hand off mismatch, and failed base transfer preserving source authority.
- CLI/PowerShell discriminated request variants, proposal/authority path roots, forged identity/authority, raw-capability leakage scanning across every operation, fixed operations, generic redacted failures, and no nested Codex/arbitrary shell.
- Build projection and source/dist reference parity for all new schemas/scripts/docs.

### Aggregate and publication gates

1. Run focused suites during implementation.
2. Run `python .\scripts\validate.py` before review-ready status.
3. Run independent code review and acceptance-mapped QA against the exact implementation target.
4. From a fresh detached worktree at the exact PR head, require clean before/after and rerun `python .\scripts\validate.py`.
5. Squash merge only after the exact-head gate passes.
6. From a second fresh detached worktree at the exact returned merge SHA, require clean before/after and rerun `python .\scripts\validate.py`.
7. Hosted checks are not queried or accepted as evidence.

## 9. Documentation impact

- Extend `README.md` with the supervisor core topology, common semi/manual/autonomous reservation lifecycle, boundary, structured commands, and later-transport distinction.
- Add `linear-delivery-loop/references/supervisor-core.md` as the reusable technical reference for state, lease, reservation, preflight, worktrees, recovery, cleanup, and assembled Handoff.
- Update `linear-delivery-loop/SKILL.md` only enough to reference the deterministic engine interface; retain thin policy and no transport logic.
- Keep the canonical stage/artifact/quality protocol under `goal-to-delivery/references/` unchanged.

## 10. Risks and mitigations

- **Accidental base duplication:** one loader plus static source-boundary tests.
- **Split state/reservation writes:** immutable paired transaction record and deterministic recovery under the base mutex.
- **Capability leakage/replay:** high-entropy nonce, hash-only authoritative comparison, redacted output, expiry, transition-id deduplication, and revocation/rotation.
- **Unsafe stale release:** protected-work summary and reconciliation; time is never sufficient.
- **Worktree escape/deletion:** strict direct-child containment, reparse checks, observed Git common identity, journaled cleanup, and protected-state refusal.
- **Handoff split authority/deadlock:** use the explicit pending barrier and an engine-owned one-shot authorization validated/consumed by the base interlock inside its own mutex; never hold the non-reentrant mutex while calling base Handoff; test both Reserve/direct-Handoff lock orders; block/reconcile every competing authority command; recover from authoritative base evidence and expose success only after supervisor CAS.
- **Preflight claiming too much:** structured probe adapter and explicit fixture evidence; live transports remain deferred.
- **Long Windows race suite:** focused subsets during implementation and one aggregate command at review/publication boundaries.

## 11. Rollout and rollback

One primary PR publishes the versioned schemas/module interfaces, dependency-free tests, and docs. No user-environment sync is part of implementation validation. After exact merged-SHA validation and Linear completion evidence, SAAS-47 may consume only the published interfaces.

Rollback never deletes protected state/worktrees. If a production defect is found before merge, preserve the workflow folder and local changes and repair the same branch. If found after merge, create a separately authorized repair task/PR from current `main`; do not auto-revert machine-state formats or discard reservations.

## 12. Clarification record

No material product, security, billing, destructive-data, cloud-cost, or UX decision remains open. The audited program artifacts already lock the local-only scope, security boundaries, transport deferrals, bootstrap exception, and merge gate. Implementation may resolve only reversible internal naming/layout details consistent with this plan and must record them in tasks or code review.

## 13. Sources consulted

- `AGENTS.md`
- `README.md`
- `src/skills/goal-to-delivery/SKILL.md`
- `src/skills/goal-to-delivery/references/{delivery-stages,artifact-contract,clarification-policy,quality-gates,completion-boundaries}.md`
- `src/skills/goal-to-delivery/references/work-descriptor.schema.json`
- `src/skills/goal-to-delivery/scripts/{__init__,identity,state_home,state_paths,mutex,registry,workflow_init,handoff,redaction,atomic_files,descriptor}.py`
- `src/skills/linear-delivery-loop/SKILL.md`
- `scripts/{build,validate}.py`
- `validation/{manifest.json,delivery_contracts.py}`
- `tests/goal_to_delivery_base/`
- `tests/test_delivery_contracts.py`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- Linear issue `SAAS-46`, read 2026-07-18.
