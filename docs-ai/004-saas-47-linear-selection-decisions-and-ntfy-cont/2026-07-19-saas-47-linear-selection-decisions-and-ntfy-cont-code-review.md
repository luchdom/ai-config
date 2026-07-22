# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Code Review

## Verdict

**FAIL / CHANGES REQUESTED.** Two P1 authority/one-work-item defects and four P2 contract, notification, and validation defects prevent this implementation from satisfying the approved SAAS-47 plan. No P3 findings were identified.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 2 | Fail |
| P2 | 4 | Fail |
| P3 | 0 | Pass |

## Reviewed target

- Base: `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4`
- Target: uncommitted working tree on `codex/saas-47-linear-control-plane`
- Workflow: `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`
- Review snapshot: 22 implementation/reference/test files, combined SHA-256 `fe2a1e1cbd4d7e2fa40592f97e80a9300197804c0a6595e4f1cadc376ca3454e`
- Scope: the complete tracked and untracked SAAS-47 implementation delta plus the approved plan, tasks, failed audit, and passing re-audit under this workflow folder; this review artifact itself is excluded from the snapshot digest.
- Review date: 2026-07-19

## Findings

### P1 — Selection ignores pending control-plane work and foreign reservations, permitting a second issue

`LinearControlPlane.choose_or_resume` copies the supplied issues, reconciles only Linear WIP, and immediately selects whenever no Linear issue is active (`src/skills/linear-delivery-loop/scripts/control_plane.py:53-76`). `reconcile_wip` consults `reservation_issue_ids` only when one Linear WIP item already exists (`src/skills/linear-delivery-loop/scripts/selection.py:82-95`); it neither refuses a foreign/live reservation when Linear has zero WIP nor reconciles `pending` decisions, publication requests, or protected recovery records from `ControlPlaneRecords`.

A targeted probe created a pending SAAS-47 decision and supplied a live SAAS-47 reservation with zero Linear WIP; the control plane returned `selected` for SAAS-48. This violates the approved precedence rule that pending decisions/publication recovery and repository reservations are reconciled before ordinary selection, and breaks the one-issue/no-second-selection safety boundary.

Required repair: make selection consume one mutex-protected authoritative snapshot of Linear WIP, pending/recovery records, reservations, and issue-worktree mappings. Selection must be possible only after that snapshot proves zero active/pending/protected work and no conflicting reservation. Add replay/race tests for pending decision, pending publication request, foreign reservation, protected claim recovery, and concurrent selection.

### P1 — Reply authorization is caller-selected rather than bound to the configured owner

Decision records do not persist the authorized owner (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:146-165`). Consumption accepts both `owner_id` and `actor_id` from the caller and authorizes merely when those two caller inputs are equal (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:167-187`). Publication retry consumption repeats the same pattern (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:212-238`). A targeted probe passed `owner_id="attacker"` and `actor_id="attacker"`; the decision was consumed successfully.

This bypasses the configured-owner boundary and contradicts the requirement that durable records carry actor authorization and only the preflight-verified owner may resolve a decision or publication retry.

Required repair: bind the verified owner identity into the durable request when it is created (or into an immutable preflight-bound authority record), remove caller-selected owner authority from the consume API, and compare the observed reply actor only to that persisted identity. The schema and tests must reject substituted owner IDs, changed configuration, replay, stale replies, and cross-request replies.

### P2 — Preflight is optional and does not validate the resolved ntfy endpoint policy

`LinearControlPlane.verify` is an independent convenience call; `choose_or_resume` and `claim` accept no preflight attestation and can execute without it (`src/skills/linear-delivery-loop/scripts/control_plane.py:32-41`, `43-92`). There is no state transition or immutable configuration digest tying a claim callback, repository, provider transport, or owner to a successful verification. In addition, `resolve_environment` checks only that enabled ntfy URL/topic values are non-empty (`src/skills/linear-delivery-loop/scripts/tracking.py:28-45`), while `TrackingPreflight.run` returns `ready` without validating that the resolved URL is HTTPS and belongs to `allowedHosts` (`src/skills/linear-delivery-loop/scripts/tracking.py:65-111`). A targeted probe with `NTFY_URL=https://evil.invalid` returned `ready`.

Transport-level refusal during a later notification is not equivalent to proving the complete configured boundary before selection/provider mutation, as required by T2.

Required repair: produce a short-lived immutable preflight result bound to the validated config digest, repository identity, supervisor version, provider endpoints, and owner; require and verify it on every selection/claim/mutation entry. Validate the resolved ntfy endpoint/topic policy during preflight and prove that injected transports use the same validated timeout, retry, and endpoint settings. Add direct-call bypass and config-drift tests.

### P2 — Most required attention events and refinement/external proposals are not composed into behavior

The only path that automatically creates an attention event is multiple-WIP handling (`src/skills/linear-delivery-loop/scripts/control_plane.py:59-69`). `request_decision`, `publication_refusal`, and `propose_follow_up` merely append their own records (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:146-165`, `192-210`, `243-256`); they do not emit the required linked attention event. `TrackingPreflight` raises an error without recording actionable/ambiguous preflight attention, and there is no worker-failure composition. There is also no durable API that creates the promised `Backlog + needs-refinement` incomplete-goal proposal or the ordinary deferred-provider `Backlog + external-integration` proposal. The migration report is mutation-free reporting and cannot substitute for those issue lifecycle records.

The focused taxonomy test calls `attention` directly for every kind (`tests/linear_delivery_control_plane/test_records_notifications.py:96-110`), so it proves the enum accepts those strings, not that the originating workflows emit exactly one linked event.

Required repair: add atomic composed operations that create/deduplicate each durable source request/proposal and its single attention event under one state mutation. Cover material decisions, actionable external prerequisites, stable/exhausted/ambiguous publication refusal, and actionable worker/preflight failures, along with all quiet states. Implement and test the refinement and deferred-provider proposal contracts without live Linear mutation.

### P2 — Notification deduplication has a publish-before-record race

`notify` loads state and checks for an existing notification, publishes outside the store mutex, then records the outcome (`src/skills/linear-delivery-loop/scripts/control_plane.py:94-121`). Two workers can both observe no record and both publish before either `_add_once` persists the same notification ID. `_add_once` prevents duplicate state rows but cannot undo the duplicate external messages. A crash after publish and before `record_notification` has the same replay problem. The `Idempotency-Key` header in `NtfyTransport` (`src/skills/linear-delivery-loop/scripts/ntfy_transport.py:62-64`) is not a locally enforced provider result and does not close the race for injected or self-hosted ntfy requesters.

Required repair: introduce a durable CAS notification attempt state under the shared cross-process mutex before publication, with explicit in-flight/recovery/terminal semantics and a documented provider idempotency contract. Exercise concurrent callers, crash-after-send recovery, failed delivery visibility, and replay without a second publish.

### P2 — The generic state schema does not enforce the declared record contracts or canonical identities

All five collections share one permissive record shape whose `data` is any object and whose `kind`/`status` are generic strings/enums (`src/skills/linear-delivery-loop/references/control-plane-state.schema.json:5-15`). Runtime parity described as `canonical-record-identities` checks only for duplicate IDs within each collection (`src/skills/linear-delivery-loop/scripts/contracts.py:518-527`); it does not recompute stable IDs, bind collection to kind/status/data shape, validate configured-owner authorization, require consumed-marker/status parity, or validate publication/refinement/follow-up/notification fields.

Consequently a corrupted or forged on-disk record can pass `ControlPlaneStore.load` and become authority-bearing state even though it was not produced by the helper methods. This is a schema/runtime-parity and recovery-safety gap, particularly for publication retry authorization.

Required repair: define strict per-collection record variants with closed `data` objects and cross-field runtime checks for canonical ID derivation, actor binding, source/consumption ordering, status transitions, exact publication evidence, and notification attempt state. Add negative tests that mutate each authority-relevant field in persisted JSON and prove load fails closed.

## Verification performed

- Inspected the exact tracked and untracked implementation delta against base `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4` and the approved SAAS-47 plan/tasks/re-audit.
- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — **PASS**, 22 tests.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — **PASS**, 6 tests.
- Targeted read-only probes demonstrated: selection with a pending SAAS-47 decision plus live SAAS-47 reservation returned `selected` for SAAS-48; a substituted caller owner consumed a decision; and preflight accepted an enabled ntfy URL outside the allowlist.
- The passing focused tests do not close the findings above because the unsafe paths are absent from their matrices. Build, aggregate validation, exact-head validation, publication, and merge were not performed by this review role.

## Gate result

Code review fails. Resolve both P1 and all P2 findings, add the missing negative/race/recovery fixtures, and submit a fresh exact-diff re-review before QA or publication.
