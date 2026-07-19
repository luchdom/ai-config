# SAAS-46 supervisor core — independent code rereview 2

## Target identity

- Review role: fresh independent post-implementation `code-reviewer`; no production code, Linear state, Git/provider state, or ignored generated output was mutated.
- Repository: `C:\dev\luchdom\ai-config`.
- Base and checked-out `HEAD`: `e1f44b9dd3f4d281d104b4df06a94267c36eacee`.
- Target: every tracked diff against the base plus every non-ignored untracked file present before this review artifact was added. The review artifact itself is excluded from its own identity.
- Target manifest: 62 files.
- Manifest algorithm: sort repository-relative `/` paths; hash each file's exact bytes with SHA-256; hash the UTF-8 concatenation of `path + NUL + "sha256:" + file-hash + LF`.
- Target digest: `sha256:59b674ad66f6fac6f6ffe74dc9c48459318d250f0996d79d30959969aa93c60e`.

## Verdict

**FAIL — 4 P1 findings and 2 P2 findings.** This exact target must not advance to QA, publication, or merge. PASS requires zero P1/P2.

## Findings

### P1-1 — Unauthenticated Status output is sufficient to cancel or extend the live autonomous lease

`SupervisorEngine.status` deliberately removes reservation and cleanup authorization references, but returns the complete lease unchanged (`src/skills/linear-delivery-loop/scripts/supervisor.py:96-116`). That lease includes `runId`, `ownerId`, `capabilityRef`, and the current revision. Public `RenewLease` and `ReleaseLease` accept exactly those values (`src/skills/linear-delivery-loop/scripts/cli.py:284-297`); `_require_lease` only compares them to the record, after which the engine itself opens the sidecar and resolves the nonce (`src/skills/linear-delivery-loop/scripts/lease.py:949-960`, `src/skills/linear-delivery-loop/scripts/lease.py:713-737`). The Status command's `workflowId` is ignored by `run_request`, so the observation surface is repository-global.

A disposable-repository probe acquired a lease as `legitimate-owner`, called only `status()`, and then successfully called `release` using fields copied from that Status result: `STATUS_LEASE_CONTROL released True`. No raw nonce or prior lease result was needed. The path is also derivable from the exposed run ID (`runs/<run-id>/lease.capability.json`), so merely deleting the field from Status without changing authority design would still be insufficient.

This contradicts the code comment that Status is never an authority-distribution channel and the durable runbook's promise of a redacted lease summary. A different workflow or observer can terminate or perpetuate the current autonomous run. Make lease mutation require a non-derivable, non-Status capability/authorization possessed only by the exact acquiring adapter, and ensure Status cannot disclose or let a caller reconstruct it.

### P1-2 — Schema-valid protected/expired reservations are ignored by both repository exclusion and base Handoff

The normative reservation contract explicitly permits `expired` and `protected` statuses (`src/skills/linear-delivery-loop/references/editing-reservation.schema.json:22`). Runtime exclusion instead defines active authority as only `live` and `handoff-pending` (`src/skills/linear-delivery-loop/scripts/reservations.py:35`) and uses that set when admitting a new Reserve (`src/skills/linear-delivery-loop/scripts/reservations.py:201-210`) and resolving an existing reservation (`src/skills/linear-delivery-loop/scripts/reservations.py:2043-2053`). The base in-mutex interlock repeats the same omission (`src/skills/goal-to-delivery/scripts/reservation_interlock.py:27`, `src/skills/goal-to-delivery/scripts/reservation_interlock.py:98-114`). Thus a protected reservation is neither exclusive editing authority nor a base-Handoff blocker.

The store makes the problem broader: `_validate_state` and `_validate_reservations` validate only top-level shape and map keys, not the published nested contracts (`src/skills/linear-delivery-loop/scripts/store.py:372-437`). An unknown/corrupt status is also silently treated as terminal instead of failing closed.

A focused probe changed a live record to the schema-valid `protected` status, successfully ran `validate_contract("editing-reservation", ...)`, and then acquired a second live reservation in the same repository: `PROTECTED_RESERVATION_BYPASS live ['live', 'protected']`. Until an expired or protected record is explicitly proven safe and transitioned by Release/Reclaim, it must continue to block every new Reserve and base-only Handoff. Persisted state and reservation documents must be fully runtime-validated on every read and commit; unknown states must fail closed.

### P1-3 — Reserve erases its reservation-CAS boundary and accepts queued stale authority requests

The public Reserve schema contains `expectedStateRevision` but no `expectedReservationsRevision` (`src/skills/linear-delivery-loop/references/engine-command.schema.json:73-84`). The CLI compensates by reading the reservation document at execution time and passing that *current* revision into `ReservationManager.reserve` (`src/skills/linear-delivery-loop/scripts/cli.py:327-346`). This converts the manager's CAS parameter into a tautology rather than binding the caller's observed no-reservation state.

A focused probe prepared a Reserve command while the reservation revision was 1, executed and safely released another reservation (advancing the reservation revision to 3 while supervisor state stayed at 1), and then submitted the old command. It was accepted and minted a new live authority: `STALE_RESERVE_ACCEPTED 3 live 4`.

This violates the plan's required compare-and-swap semantics and permits delayed/queued work to claim the repository after a lifecycle it never observed. Add `expectedReservationsRevision` to the Reserve contract, require it from the caller, preserve it in recovery evidence, and reject it under the mutex when stale.

### P1-4 — Assembled Handoff cannot transfer a persistent issue reservation, and Phase C leaves its mapping at the source

Autonomous Prepare/Checkpoint correctly require a contained persistent issue mapping. The public Handoff path is incompatible with that authority:

- command validation requires `sourcePath == repositoryRoot` (`src/skills/linear-delivery-loop/scripts/contracts.py:394-395`), and rejects a repository root contained by state home (`src/skills/linear-delivery-loop/scripts/contracts.py:363-365`);
- persistent issue worktrees are direct descendants of state home;
- `execute_assembled_handoff` again requires the source to equal the controller manager root (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:455-469`);
- Phase A requires the reservation fingerprint to equal that source (`src/skills/linear-delivery-loop/scripts/reservations.py:1036-1041`).

Therefore a command cannot name the persistent issue worktree as its repository/source, while naming the scheduled controller makes the exact reservation binding fail. A real public-path probe acquired a lease, prepared the registered issue worktree, reserved it under autonomous policy, and submitted schema-valid Handoff from the required controller root. It failed before Phase B with `ReservationError: Handoff reservation source binding is mismatched`.

The internal finalizer is incomplete too. On success it transfers the reservation, `currentWork`, prepared capabilities, and sidecars (`src/skills/linear-delivery-loop/scripts/reservations.py:1214-1280`), but never updates `state.issueWorktrees`. Subsequent reservation commands require that mapping to equal the transferred record (`src/skills/linear-delivery-loop/scripts/reservations.py:1969-1993`), while checkpoint requires it to equal the transferred prepared capability (`src/skills/linear-delivery-loop/scripts/lease.py:813-836`). Even an internally forced transfer therefore leaves the destination unable to renew/authorize/checkpoint through the advertised authority.

Define one coherent controller-versus-editing-source model for public Handoff, prove the exact persistent mapping at Phase A/base interlock, and atomically transfer or deliberately retire/update every authoritative issue mapping in Phase C. Add a public autonomous Handoff success test followed by destination RenewReservation, AuthorizeMutation, and ApplyCheckpoint plus source rejection.

### P2-1 — Pending RenewLease can be falsely recovered as completed after an unrelated checkpoint

Operation journals do not stop another mutating command after `begin` returns. Recovery classifies RenewLease as completed whenever state advanced exactly once and the current lease has the same run/owner (`src/skills/linear-delivery-loop/scripts/recovery.py:222-239`); it does not prove that heartbeat or expiry changed, bind a lease-side transition identity, or distinguish the checkpoint that also advances the lease revision.

A focused probe journaled RenewLease but interrupted it before action, then applied a valid checkpoint at the same expected state revision. Checkpoint advanced state/lease revision without extending expiry. Recover nevertheless put the pending RenewLease in `recoveredOperations`, marked its journal `completed`, and returned the unchanged original expiry: `FALSE_RENEW_RECOVERY True True completed True`.

The durable result now claims a renewal that never occurred, so the five-minute loop can unexpectedly lose authority after a nominally successful recovery. Serialize/sequence pending mutations or persist operation-specific before/after evidence, and require an exact heartbeat/expiry transition attributable to that request before completing RenewLease.

### P2-2 — Green tests and durable documentation do not cover or describe the actual authority boundaries

Coverage improved substantially since the previous review, but the public tests still normalize only the safe shapes:

- Status only asserts repository identity/revision and never verifies absence of lease mutation material (`tests/linear_delivery_supervisor/test_cli_wrapper.py:34-45`).
- Lease lifecycle passes the reference returned by Acquire, not a forged command built from Status (`tests/linear_delivery_supervisor/test_cli_wrapper.py:91-130`).
- Reserve covers only a second `live` record and has no stale reservation-revision input to test (`tests/linear_delivery_supervisor/test_cli_wrapper.py:132-157`).
- public Handoff uses `issueId: null`, semi-autonomous policy, and the controller worktree (`tests/linear_delivery_supervisor/test_cli_wrapper.py:412-458`).
- public Recover tests only an interrupted read-only Status with no intervening mutation (`tests/linear_delivery_supervisor/test_cli_wrapper.py:460-481`).
- the worktree reparse test silently returns when Windows symlink creation fails instead of proving the applicable junction/reparse path or reporting a skip (`tests/linear_delivery_supervisor/test_worktrees.py:209-226`).

The runbook meanwhile promises a redacted Status and says assembled Handoff transfers reservation/capability authority (`src/skills/linear-delivery-loop/references/supervisor-core.md:52-57`, `src/skills/linear-delivery-loop/references/supervisor-core.md:69-76`). Both statements are false for the exact target above. Add the missing adversarial public-path and Windows cases and update documentation only after the behaviors are true.

## Prior-finding disposition

### First failed review (`2026-07-18-saas-46-supervisor-core-code-review.md`)

| Prior finding | Disposition | Evidence |
|---|---|---|
| P1-1 arbitrary preflight executable/config-declared secret | **Resolved** | Adapter interpreter/script/bytes and argv are pinned; environment is core-only; malicious config tests exist. |
| P1-2 schema-valid WorkerResult incompatible with ApplyCheckpoint | **Resolved** | Public WorkerResult reaches ApplyCheckpoint; exact prepared ID, expected stage, mapping, Git HEAD, and changed paths are now bound. |
| P1-3 foreign repository reservation bypasses base Handoff | **Partially resolved** | Foreign/multiple `live` records block, but schema-valid `protected`/`expired` records still bypass both Reserve and base Handoff (new P1-2). |
| P1-4 source fingerprint alone restores after partial destination mutation | **Resolved for the reported rollback shape** | Failure restoration now requires exact base failure evidence plus destination readback; partial destination remains protected. |
| P1-5 killed/expired lease and pending journal have no recovery | **Partially resolved** | Expired lease and ordinary journals have routes, but RenewLease can be falsely completed after an unrelated checkpoint (new P2-1). |
| P1-6 mappings absent and cleanup trusts caller booleans | **Partially resolved** | Allocation mappings and post-release cleanup authority are persisted; Handoff still fails to transfer issue mapping (new P1-4). |
| P2-1 durable journal differs from published contract | **Resolved** | Canonical journal is schema-validated; request/result companions are hash-bound. |
| P2-2 authorization expiry/scope/revision/fingerprint not enforced | **Resolved for reservation mutation/release consumption** | Detailed bindings and expiry are checked, but lease authority is newly redistributed by Status (new P1-1). |
| P2-3 tests miss public/crash security boundaries | **Not resolved** | Public coverage expanded, but the exact authority/recovery/Windows cases in P2-2 remain absent. |

### Second failed review (`2026-07-19-saas-46-supervisor-core-code-re-review.md`)

| Prior finding | Disposition | Evidence |
|---|---|---|
| P1-1 identifiers mint authority and autonomous capability freshness is absent | **Partially resolved** | Reservation control and autonomous freshness are now checked, but Status exposes every value needed for lease mutation (new P1-1). |
| P1-2 recovery rewrites/reclaims non-planning reservations | **Resolved** | Reclaim preserves classification, rejects non-planning work, and refuses live lease/current work. |
| P1-3 prepared/checkpoint authority is not issue-mapping-bound | **Resolved** | Prepare and checkpoint now require exact authoritative mapping and reject the controller worktree. |
| P1-4 post-Phase-C/pre-journal Handoff crash becomes ambiguous | **Resolved for the tested semi/manual transfer** | Recovery recognizes exact finalized success/failure evidence and closes the outer journal. Persistent issue transfer remains broken for a different reason (new P1-4). |
| P1-5 Cleanup requires a live reservation | **Resolved** | Cleanup now requires a released record and refuses any active reservation/lease/Handoff/recovery barrier. |
| P1-6 worktree allocation has Git-before-state crash window | **Resolved** | Allocation intent is persisted before Git and Recover adopts or protects exact observations. |
| P2-1 WorkerResult prepared ID/HEAD claims are unbound | **Resolved** | Prepared ID, observed HEAD/fingerprint/repository, mapping, and changed paths are checked against fresh Git observations. |
| P2-2 public/crash tests omit security boundaries | **Partially resolved** | All major public happy paths now exist, but P2-2 lists remaining adversarial gaps and one unsafe recovery interleaving. |

## Checks and evidence

- Implementation handoff reports `python -m unittest discover -s tests\linear_delivery_supervisor -v` — **PASS**, 77 tests in 721.867 s.
- Implementation handoff reports the delivery-contract suite — **PASS**, 14 tests.
- Reviewer ran `python -m unittest tests.linear_delivery_supervisor.test_contracts tests.linear_delivery_supervisor.test_store_recovery -v` — **PASS**, 8 tests in 10.141 s.
- Reviewer ran four isolated public/manager authority probes — confirmed Status-only lease release, protected-reservation double claim, stale Reserve acceptance, and public autonomous Handoff source mismatch.
- Reviewer ran one isolated recovery interleaving probe — confirmed RenewLease journal completion with unchanged expiry after ApplyCheckpoint.
- Static review covered every target file, both previous failed reviews, approved plan/tasks/audits, canonical base interlock/Handoff delta, all supervisor scripts and schemas, generated-entry sources, tests, documentation, repository isolation, and Windows-specific containment/test paths.
- No credential value, raw nonce, provider mutation, Linear mutation, Git state-changing action in the target repository, or ignored `dist/` output was used or emitted.

## Residual risks

- Live Linear, ntfy, GitHub mutation transports and exact-SHA publication orchestration remain intentional SAAS-47/48 non-goals and are not findings.
- Real process termination at every sidecar/state/journal boundary was not rerun by this reviewer; the target has injected-fault coverage, but the semantic failures above invalidate advancement regardless.
- Git SHA-256 repositories remain unverified: some runtime worktree patterns accept 64-character object IDs while several public schemas require 40. This was not promoted above because the approved artifacts do not explicitly require SHA-256 Git format support.
- The focused Windows run is meaningful for normal path/case behavior, but the silent symlink-return path means the exact supervisor suite does not prove reparse denial on a host lacking symlink privilege.

## Exact target manifest

```text
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-audit.md
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-code-review.md
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-plan.md
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit-2.md
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit.md
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-tasks.md
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-19-saas-46-supervisor-core-code-re-review.md
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/workflow.json
README.md
src/project-templates/claude/CLAUDE.md
src/project-templates/codex/AGENTS.md
src/project-templates/cursor/AGENTS.md
src/skills/goal-to-delivery/scripts/handoff.py
src/skills/goal-to-delivery/scripts/reservation_interlock.py
src/skills/goal-to-delivery/scripts/workflow_init.py
src/skills/goal-to-delivery/SKILL.md
src/skills/linear-delivery-loop/references/checkpoint.schema.json
src/skills/linear-delivery-loop/references/editing-reservation.schema.json
src/skills/linear-delivery-loop/references/engine-command.schema.json
src/skills/linear-delivery-loop/references/handoff-authorization.schema.json
src/skills/linear-delivery-loop/references/operation-journal.schema.json
src/skills/linear-delivery-loop/references/prepared-iteration.schema.json
src/skills/linear-delivery-loop/references/project-config.schema.json
src/skills/linear-delivery-loop/references/release-authorization.schema.json
src/skills/linear-delivery-loop/references/supervisor-core.md
src/skills/linear-delivery-loop/references/supervisor-state.schema.json
src/skills/linear-delivery-loop/references/trusted-observation.schema.json
src/skills/linear-delivery-loop/references/worker-result.schema.json
src/skills/linear-delivery-loop/scripts/__init__.py
src/skills/linear-delivery-loop/scripts/agent-worker-engine.ps1
src/skills/linear-delivery-loop/scripts/assembled_handoff.py
src/skills/linear-delivery-loop/scripts/base_runtime.py
src/skills/linear-delivery-loop/scripts/cli.py
src/skills/linear-delivery-loop/scripts/contracts.py
src/skills/linear-delivery-loop/scripts/lease.py
src/skills/linear-delivery-loop/scripts/operations.py
src/skills/linear-delivery-loop/scripts/preflight.py
src/skills/linear-delivery-loop/scripts/recovery.py
src/skills/linear-delivery-loop/scripts/reservations.py
src/skills/linear-delivery-loop/scripts/store.py
src/skills/linear-delivery-loop/scripts/supervisor.py
src/skills/linear-delivery-loop/scripts/worktrees.py
src/skills/linear-delivery-loop/SKILL.md
src/skills/spec-driven-delivery/SKILL.md
tests/linear_delivery_supervisor/__init__.py
tests/linear_delivery_supervisor/fixtures/preflight/passing-probe.template.json
tests/linear_delivery_supervisor/support_state_engine.py
tests/linear_delivery_supervisor/test_assembled_handoff.py
tests/linear_delivery_supervisor/test_base_runtime.py
tests/linear_delivery_supervisor/test_checkpoints.py
tests/linear_delivery_supervisor/test_cli_wrapper.py
tests/linear_delivery_supervisor/test_contracts.py
tests/linear_delivery_supervisor/test_lease_capability.py
tests/linear_delivery_supervisor/test_operations.py
tests/linear_delivery_supervisor/test_preflight.py
tests/linear_delivery_supervisor/test_recovery_reconciliation.py
tests/linear_delivery_supervisor/test_reservations.py
tests/linear_delivery_supervisor/test_status_cleanup.py
tests/linear_delivery_supervisor/test_store_recovery.py
tests/linear_delivery_supervisor/test_worktrees.py
tests/test_delivery_contracts.py
validation/delivery_contracts.py
```
