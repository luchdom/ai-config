# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Code Re-review

## Verdict

**FAIL / CHANGES REQUESTED.** The post-review changes close notification send deduplication and persist configured-owner identity, but three P1 authority/lifecycle defects and three P2 behavior/validation defects remain. No P3 findings were identified.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 3 | Fail |
| P2 | 3 | Fail |
| P3 | 0 | Pass |

## Reviewed target

- Base: `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4`
- Target: uncommitted working tree on `codex/saas-47-linear-control-plane`
- Workflow: `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`
- Post-fix snapshot: 22 implementation/reference/test files, combined SHA-256 `9812bd7e6289f441bfe1db21ff9f7ad038e9ecfbe5436fec17eb140e0d0f1024`
- Scope: the complete tracked and untracked SAAS-47 implementation delta, the approved plan/tasks/re-audit, and the first failed code review; workflow metadata and this re-review artifact are excluded from the implementation digest.
- Review date: 2026-07-19

## Resolution matrix for the first review

| Original finding | Re-review result | Evidence |
|---|---|---|
| P1: selection ignored pending/protected/foreign authority | **Partially resolved** | `choose_or_resume` now combines pending records with one mutex-protected observed snapshot and blocks foreign reservation/worktree and protected recovery states. Concurrent selectors create one selection record. However, the selected record is not atomically acquired for claim, so concurrent claimers can still execute provider mutation twice (new P1 below). |
| P1: reply owner was caller-selected | **Resolved for owner substitution** | Decision and publication records persist the preflight owner, config digest, and attestation identity; direct substituted actors are inert. A separate durable-request lifecycle P1 remains because binding to the expiring attestation makes later legitimate replies and recovery impossible. |
| P2: preflight was optional and ntfy allowlist was not verified | **Partially resolved** | Resolved ntfy URL/topic policy now fails outside the HTTPS host allowlist, and facade entry points require an attestation argument. The attestation itself is caller-forgeable and therefore does not prove `TrackingPreflight.run` occurred; claim mutation callbacks are also not bound to the verified transport (P1 below). |
| P2: decisions/proposals/failures did not compose attention | **Partially resolved** | Source and attention records are now inserted atomically for the major paths. The implementation also emits attention for `needs-refinement` and for every deferred-provider proposal, exceeding the approved trigger taxonomy (P2 below). |
| P2: notification had publish-before-record race | **Resolved** | A durable in-flight CAS is created before publication. Concurrent callers and crash replay do not send twice; terminal failure stays status-visible. |
| P2: state schema/runtime validation was permissive | **Partially resolved** | Per-collection closed variants, canonical IDs, owner/config binding, consumption parity, and notification attempt parity were added. Required source-to-attention semantics/cardinality and full notification/source equality are still not enforced (P2 below). |

## Findings

### P1 — A caller can fabricate a valid-looking attestation without running preflight

`validate_preflight_attestation` checks caller-provided fields and freshness, but it neither recomputes `attestationId` nor verifies that the `TrackingPreflight` instance issued it (`src/skills/linear-delivery-loop/scripts/tracking.py:166-207`). `LinearControlPlane._attest` treats that structural check as proof of provider observation (`src/skills/linear-delivery-loop/scripts/control_plane.py:34-50`). The required-key check is also a subset check, so it does not make the result an exact closed contract. Claim then accepts caller-injected `reread`, `claim`, and `readback` callbacks rather than a mutation port proven to be the verified `self.linear` transport (`src/skills/linear-delivery-loop/scripts/control_plane.py:222-260`).

A targeted probe constructed the documented fields, a made-up `preflight-ffff...` ID, and `providerObserved=True` without invoking the observer. `choose_or_resume` returned `selected` and the observer call count remained zero. This bypasses the mandatory workspace/team/project/owner/provider verification boundary and can be followed by a caller-selected claim mutation.

Required repair: make attestations issuer-verifiable and exact—such as a supervisor-state-backed opaque reference or another integrity-protected issuance record—and reject any attestation not issued by the bound preflight instance/state. Bind claim/readback to the verified provider adapter and operation journal rather than accepting an unrelated raw mutation callback. Add fabricated-ID, copied-field, extra-field, different-preflight-instance, and different-claim-port tests.

### P1 — Concurrent claimers can both mutate Linear before one loses the terminal record update

`claim` reads a pending selection record with `store.load`, performs local preparation and provider mutation outside a record CAS, and only afterward calls `_finish_selection` (`src/skills/linear-delivery-loop/scripts/control_plane.py:235-266`). The persisted selection record does not bind a single `operationId`, and there is no `pending -> in-flight` acquisition before calling `claim_selected`.

A barrier-based two-thread probe invoked the same `selectionClaimId` with `op-a` and `op-b`. Both threads ran `authority.prepare`, both provider claim callbacks ran, and both authority commits ran. One caller raised `TrackingPreflightError` only when the already-consumed record was finished. The losing terminal update does not undo the duplicate provider mutation.

Required repair: under the shared mutex, atomically acquire the selection record and bind one operation identity before any local or provider action. Replay of the same operation must reconcile; a competing operation must fail before `prepare`. Terminal consume/inert/protected transitions must compare-and-set that exact in-flight operation. Add same/different-operation races plus crash points before and after provider claim/readback.

### P1 — Expiring preflight IDs make durable human replies and protected recovery unusable and non-deduplicated

Decision identity includes `preflightAttestationId`, and consumption requires the later attestation to equal that exact ID (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:204-207`, `231-260`). Publication requests repeat the same coupling (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:273-276`, `303-337`). Preflight attestations expire after five minutes by default and every new run derives a different ID from its issuance time (`src/skills/linear-delivery-loop/scripts/tracking.py:136-161`). Selection claims have the same exact-attestation coupling (`src/skills/linear-delivery-loop/scripts/control_plane.py:235-245`).

A targeted probe created a decision at 12:00 and replied at 12:06. The original attestation failed as expired; a fresh valid preflight attestation passed facade validation but record consumption returned `None` because its ID differed. Recreating the same logical request after refresh also yields a different canonical ID, so replay can create a second decision/publication request rather than deduplicating the first. A pending selection that crosses the TTL similarly cannot be claimed with either the expired original or a refreshed attestation and remains a permanent protected blocker.

Required repair: keep immutable configured-owner and config/repository binding in durable records, but do not use an ephemeral issuance ID as the logical request identity or require that exact expired issuance for a later reply/recovery. Accept a fresh issuer-verified attestation only when its owner/config/repository binding matches the durable record. Preserve one canonical logical request/selection operation across attestation refresh, and add beyond-TTL decision, publication, selection-recovery, and replay-dedup tests.

### P2 — The attention taxonomy alerts on states not approved for unattended notification

`propose_issue_contract` creates an attention event for every `needs-refinement` proposal and every generic `external-integration` proposal (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:364-387`), and the free attention API explicitly allows `needs-refinement` (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:412-429`). The approved taxonomy alerts for material decisions, independently actionable external blockers, multiple WIP, actionable publication refusal, and actionable worker/preflight failure. It does not alert merely because an incomplete goal was moved for refinement or because provider work was deferred for later.

This conflates durable issue-contract proposals with independently actionable blockers and can publish unnecessary ntfy alerts. The focused composition test proves the extra events exist rather than proving the required quiet boundary.

Required repair: keep `Backlog + needs-refinement` and deferred `Backlog + external-integration` proposals durable but quiet. Create external-blocker attention only when the prerequisite is separately achievable and independently actionable. Remove `needs-refinement` from the notifyable event-kind union and add negative integration tests from originating workflows, not direct enum calls.

### P2 — Runtime validation permits semantically forged or missing attention/source bindings

Runtime validation builds a source map and checks only that an attention `sourceId` exists, has the same issue, and matches an ID recomputed from the caller-supplied event kind (`src/skills/linear-delivery-loop/scripts/contracts.py:629-662`). It does not require the event kind appropriate to the source record, require source timestamp/link/summary equality, or require exactly one attention event for every actionable source. Notification validation similarly does not bind its issue/link/summary/source timestamp back to the attention event (`src/skills/linear-delivery-loop/scripts/contracts.py:663-682`).

A targeted persisted-state probe changed a decision's attention kind from `needs-human` to `worker-failure`, recomputed the canonical attention ID, and `ControlPlaneStore.load` accepted it. Deleting a required attention row is also not rejected by the source-to-attention validation direction. These self-consistent corruptions can alter or suppress the notification taxonomy while passing the claimed strict recovery boundary.

Required repair: define and enforce the exact source-kind to attention-kind mapping, required/quiet source cardinality, and equality of issue/timestamp/link/summary across source, attention, and notification records. Add negative fixtures for changed kind/metadata, missing required attention, extra quiet attention, and mismatched notification source fields.

### P2 — GraphQL mutation errors bypass ambiguous-write readback reconciliation

`LinearTransport.execute` raises `LinearGraphQLError` for every HTTP-200 GraphQL `errors` response even when executing a mutation (`src/skills/linear-delivery-loop/scripts/linear_transport.py:133-134`). `reconciled_mutation` performs readback only for `LinearAmbiguousWrite` (`src/skills/linear-delivery-loop/scripts/linear_transport.py:173-193`). GraphQL may return errors with partial mutation data or after the provider applied work, so treating this as a definitive non-applied result violates fail-closed mutation reconciliation.

A targeted probe returned HTTP 200 with both `errors` and mutation data. `reconciled_mutation` raised `LinearGraphQLError` and performed zero post-mutation observations.

Required repair: classify mutation GraphQL errors as ambiguous unless a provider-specific proof makes them definitive, and always perform the stable-operation readback before allowing retry or recovery. Retain the distinct `LinearGraphQLError` classification for reads. Add partial-data, errors-only, and readback-applied/not-applied/ambiguous mutation fixtures.

## Verification performed

- Inspected the complete 22-file post-fix implementation snapshot against the approved plan/tasks/re-audit and the first failed code review.
- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — **PASS**, 32 tests.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — **PASS**, 6 tests.
- `git diff --check` — **PASS** (line-ending conversion warnings only).
- Targeted probes demonstrated: fabricated preflight evidence selected work without invoking the observer; two concurrent claimers both prepared, called the provider, and committed; no valid attestation could consume a reply after the original TTL; semantic attention-kind corruption passed state load; and a GraphQL mutation error triggered no readback.
- Build, aggregate validation, exact-head validation, publication, and merge were not performed by this independent review role.

## Gate result

Code re-review fails. Resolve all three P1 and three P2 findings, extend the missing negative/race/TTL/ambiguity fixtures, and obtain another fresh exact-diff review before QA or publication.
