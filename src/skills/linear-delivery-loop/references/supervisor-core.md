# Local delivery supervisor core

This reference describes the reusable, transport-free supervisor introduced by SAAS-46. The canonical delivery stages and quality gates remain in the sibling [`goal-to-delivery` references](../../goal-to-delivery/references/); this page owns only local engine architecture and operation.

## What it owns

The supervisor consumes the exact versioned `goal-to-delivery/scripts` base package. That base remains authoritative for repository identity, state-home derivation, the repository mutex, workflow registry/descriptors, and registry-only Handoff. The supervisor adds:

- renewable autonomous run leases and prepared capabilities;
- one repository-scoped editing-reservation namespace shared by autonomous, semi-autonomous, and manual work;
- scoped mutation, release, and assembled-Handoff authorizations;
- revisioned supervisor/reservation state, operation journals, and deterministic recovery;
- persistent issue worktrees and disposable exact-SHA validation worktrees;
- mutation-free least-privilege preflight;
- structured status, cleanup, and reservation-aware assembled Handoff.

It does not select or mutate Linear issues, publish ntfy messages, push branches, create/merge pull requests, query hosted checks, launch hosted CI, or launch nested Codex. SAAS-46 supplies local contracts and fixture-backed observations only; live provider transports and hosted CI orchestration belong to later delivery tasks.

## Authoritative local state

Every linked checkout of one normalized Git common directory derives the same repository state home. Repository state is outside the checkout and guarded by the base `StatePathGuard` and `allocation.lock`.

```text
<state-home>/
  repository.json
  registry.json
  allocation.lock
  supervisor-state.json
  reservations.json
  supervisor-transactions/
  operations/
  runs/
  handoff-authorizations/
  final-attestations/
  worktrees/
  validation-worktrees/
```

State and reservation revisions are monotonic. Mutating commands compare the caller's observed state revision, and reservation mutations also compare the observed reservation revision. `Reserve` therefore requires both `expectedStateRevision` and `expectedReservationsRevision`; a queued request cannot claim the repository after an intervening reserve/release lifecycle. Each operation has one schema-validated `operations/<operation-id>/journal.json` with an immutable request hash. Only an exact request replay through that journal returns the recorded result; changed input, a reused identifier, or ambiguous crash evidence fails closed.

`supervisor-state.json` persists current work plus issue, allocation, and gate-worktree mappings so callers never supply cleanup authority as booleans or mutable records. The complete persisted state and reservation contracts are validated on reads and commits. Split transactions, malformed/unknown reservation state, path escapes, reparse/hard-link aliases, stale revisions, or uncertain external facts fail closed.

## Authority surfaces

`Status` is observation only and never distributes authority. It returns repository/revision metadata, lease identity and timing, current-work/recovery/Handoff state, and reservation summaries, but omits the lease capability reference and digest plus reservation control/release and cleanup authorization references. Those opaque references are returned only to the exact journaled operation that minted them.

`AcquireLease` creates a non-derivable sidecar reference. Once any lease record exists, a second acquire cannot reconstruct or redistribute it from public run/owner/revision fields; only replaying the exact original `AcquireLease` request through its operation journal returns the original result. `RenewLease` requires the current opaque reference, rotates it to a new non-derivable reference, and revokes the old reference. The same exact reference may reauthorize the lease lifecycle after ordinary expiry, including the `expired-lease` recovery barrier, but it does not refresh an expired prepared capability or grant mutation authority. Recovery recognizes a pending renewal only when the current sidecar is active, digest-bound, and carries the exact renewal request ID; an unrelated revision advance is ambiguous, not a successful renewal.

Reservations are repository-exclusive until an explicit safe terminal transition. `live`, `handoff-pending`, `expired`, and `protected` records all block a new `Reserve` and block base-only Handoff; only `released` and `reclaimed` are terminal. Unknown or malformed statuses fail contract validation and also block progress until attended reconciliation produces a valid safe terminal state. Expiry by itself never releases implementation authority. `RenewReservation` can rotate the exact current expired control into fresh lifecycle authority; autonomous renewal additionally requires the exact prior prepared capability plus a freshly renewed live lease. That renewal does not revive the expired prepared capability, so mutation remains denied until `PrepareIteration` issues a new one.

## Structured operations

The public engine accepts one version `1.0` `EngineCommand` JSON file. It rejects unknown fields, raw nonces/capabilities, caller-selected authoritative result paths, path escapes, and repository/state identity mismatches. Results are written beneath the engine-owned operation directory and stdout/stderr is redacted.

The exhaustive operation set is:

| Operation | Purpose |
|---|---|
| `Preflight` | Validate engine/base/config versions, paths, fixed command/network policy, minimal environment, and read-only probe evidence before mutation. The probe is pinned to the current engine script/interpreter/bytes and never inherits provider secrets. |
| `AcquireLease` / `RenewLease` / `ReleaseLease` | Create, rotate/extend, or reconcile/revoke one opaque autonomous run authority. |
| `PrepareIteration` / `ApplyCheckpoint` | Create one issue-bound prepared capability and accept one replay-safe stage transition. |
| `Status` | Return non-authorizing, redacted supervisor, lease-timing, current-work, reservation, and pending-recovery summaries. |
| `Reserve` / `RenewReservation` | Create or extend the exact repository editing reservation under state-and-reservation revision CAS. |
| `AuthorizeMutation` | Issue a one-operation authorization after checking the current reservation/capability/revision. |
| `Release` | Release only with engine-owned one-shot authority and reconciled clean/unprotected observations. |
| `Recover` / `Cleanup` | Reconcile journals/barriers or remove only proven disposable state. |
| `Handoff` | Transfer base workflow authority plus reservation/capability through the assembled three-phase protocol. |

`agent-worker-engine.ps1` is a thin fixed-argument wrapper around the sibling Python CLI. It never evaluates arbitrary shell content and never launches Codex.

## Entry workflow use

- Autonomous work runs `Preflight`, acquires/renews a lease, reserves, prepares exactly one iteration, authorizes bounded mutations, checkpoints, then safely releases both reservation and lease at a reconciled terminal boundary.
- `$goal-to-delivery` reserves before its first automatic repository-deliverable edit, renews when needed, authorizes bounded writes, and releases only after its declared completion boundary is safely reconciled.
- `$spec-driven-delivery` may write isolated planning evidence without a reservation. `Implement` or any other deliverable-changing stage requires `Reserve` plus `AuthorizeMutation`; `Renew`, `Status`, `Recover`, `Handoff`, and `Release` remain explicit manual stages.

Another normalized repository has a different state home and reservation namespace. A different live owner in the same repository conflicts. Expiry never discards dirty, unpushed, unmerged, open-PR, inaccessible, or ambiguous work.

## Assembled Handoff

Base Handoff is self-locking and intentionally carries no reservation. Its in-mutex interlock denies base-only calls while any blocking reservation exists, including `expired` and `protected`, and fails closed on an unknown status. The public EngineCommand keeps two paths distinct: `repositoryRoot` is the scheduled/controller checkout used to derive repository identity and state; `sourcePath` is the exact reserved editing checkout whose registry, path, and physical fingerprint must agree under the mutex. For autonomous work, that source is the persistent issue worktree rather than the controller checkout, and the destination must be a distinct direct child of the guarded issue-worktree root.

The assembled supervisor route is:

1. Before Phase A, atomically publish a request-bound recovery bundle containing the source/destination identities, a full clean destination observation, expected scope, existing base-evidence identities, and a separately sidecar-keyed HMAC over the context digest. Context-only recovery revalidates that anchored clean observation and fails closed if the destination, context, digest, MAC, or sidecar changed. Then, under `allocation.lock`, validate source/destination/scope, mark `handoff-pending`, suspend source mutation, and mint an engine-owned one-shot authorization whose durable record stores only a nonce hash and exact bindings.
2. Release the caller-held lock. Invoke canonical base Handoff once with the internal authorization. Inside its own mutex, the base interlock re-reads and consumes that exact grant before transfer logic can run.
3. Reacquire the mutex. Proven success accepts only the exact registry/descriptor transfer committed by Phase B, then completes the transfer set: reservation path/fingerprint and rotated control authority, `currentWork`, issued prepared capability records and sidecars, the issue-worktree mapping, and its allocation record all move to the destination. The source registry authority and stale reservation control are rejected after completion. The autonomous run lease remains controller-bound; only its revision advances with the supervisor commit. Proven failure restores the exact source, while ambiguity remains protected for attended recovery.

If direct base Handoff races the first Reserve, the shared mutex decides safely: Reserve-first makes Handoff reject; Handoff-first changes registry authority and Reserve's in-lock revalidation rejects. Native Codex **Hand off** never enters this protocol.

## Verification and recovery

Run the focused supervisor suite while developing, then the repository aggregate:

```powershell
python -m unittest discover -s tests\linear_delivery_supervisor -v
python .\scripts\validate.py
```

Use `Status` before recovery, but retain the exact prior command result when an opaque authority reference is required. `Recover` is idempotent for a proven request hash and reconciles request-only/result-only journals, safely expired leases, pre-Phase-B Handoff interruption from precommitted context, and only proven clean planning-only expired reservations from authoritative observations. Request-specific sidecar evidence is required for lease-renewal recovery. Ambiguous evidence activates the recovery barrier instead of granting a new lease. Do not delete state/worktrees manually: `Cleanup` requires an exact operation/scope/revision-bound one-shot authorization and refuses any nonterminal reservation, dirty/mismatched worktrees, incomplete attestations, unresolved operations, and ambiguous paths. If Git removal succeeds but the paired state commit cannot be proven, the gate and repository remain protected as ambiguous.

The focused local suite covers stale reservation CAS, Status authority non-disclosure, lease rotation and request-specific recovery, blocking protected/expired reservations, and public autonomous Handoff followed by destination renewal, mutation authorization, and checkpoint. Path coverage includes traversal and case aliases plus directory symlinks; on Windows it falls back to an actual directory junction when symlink privilege is unavailable and reports an explicit skip if the host cannot construct either reparse form. These are local tests, not live provider or hosted-CI coverage.

Common fail-closed results:

- `clock-discontinuity`: the injected lease clock moved backward or beyond the allowed forward step; reconcile before renewing or reclaiming.
- `handoff-pending`: another authority-bearing command must stop or reconcile the exact transition.
- protected stale reservation: inspect dirty/branch/unpushed/unmerged/PR/accessibility evidence; time alone cannot release it.
- expired reservation: do not reserve or call base Handoff; use exact credential rotation, prepare fresh autonomous mutation authority when applicable, then explicitly Release after safe reconciliation. Unknown reservation state requires attended repair and remains blocked.
- physical-worktree mismatch: return to the registered source or use assembled Handoff/attended recovery; native Hand off did not transfer authority.
- invalid trusted observation: obtain fresh adapter-attested evidence bound to the exact repository/head/PR/operation; never substitute model prose.

Rollback preserves protected state. Repair code/config and rerun recovery; do not erase reservations or rewrite machine-state formats to force progress.
