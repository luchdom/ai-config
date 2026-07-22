# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Code Review 3

## Verdict

**FAIL / CHANGES REQUESTED.** The second-review fixes close the attestation, durable-reply, attention-taxonomy, semantic-record, and GraphQL-error gaps, and the earlier configured-owner and notification CAS fixes remain sound. Two P1 authority/concurrency defects and two P2 replay/reconciliation defects still prevent QA or publication.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 2 | Fail |
| P2 | 2 | Fail |
| P3 | 0 | Pass |

## Review identity and target

- Reviewer: fresh independent post-fix code reviewer 3 (`/root/saas47_code_review_3`)
- Base/working-tree HEAD: `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4`
- Branch: `codex/saas-47-linear-control-plane`
- Workflow: `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`
- Scope: exact current tracked and untracked SAAS-47 working-tree delta, approved plan/tasks/re-audit, and both earlier failed review artifacts
- Review time: `2026-07-20T02:30:03Z`

## Resolution matrix

| Re-probed blocker or retained guarantee | Result | Evidence |
|---|---|---|
| Forged/copy-modified/extra-field/different-issuer preflight attestation | **Resolved** | Exact-field HMAC verification recomputes signature and ID and binds issuer/config/repository/owner/adapter settings. Focused negative fixtures pass. |
| Claim-port and repository-authority binding | **Unresolved (P1)** | The binding trusts caller-supplied object attributes. A different same-transport port with copied IDs was accepted, and a fake authority with the expected string ID claimed Linear without repository preparation. |
| Concurrent same/different-operation claim CAS | **Partially resolved** | An ordinary same-operation concurrent caller returns `in-flight` and a different operation fails before prepare. An explicit same-operation `recovery=True` caller can race the still-live owner and execute a second provider claim (P1). |
| Crash/protected recovery | **Partially resolved** | Sequential protected recovery with the original operation and a fresh attestation works. Recovery lacks exclusive ownership/dead-owner proof and is unsafe when concurrent with the live operation (P1). |
| Fresh verified attestation after TTL and logical deduplication | **Resolved** | Decisions, publication requests, and selection claims bind stable owner/config/repository/logical identities rather than an expiring attestation ID. Beyond-TTL focused fixtures pass. |
| Quiet refinement/deferred-provider proposals and actionable external blocker | **Resolved** | Issue-contract proposals are quiet; only a separately achievable, independently actionable external prerequisite creates `external-blocker` attention. |
| Exact source-attention-notification taxonomy, cardinality, and metadata equality | **Resolved** | Runtime validation enforces required/quiet mapping, exactly-one/zero cardinality, canonical IDs, and issue/sourceTimestamp/link/summary equality through notification. Corruption fixtures pass. |
| GraphQL mutation errors and ambiguous readback | **Resolved for GraphQL `errors`; incomplete for other post-dispatch protocol ambiguity (P2)** | Partial-data and errors-only GraphQL mutation responses enter readback. An HTTP-200 malformed JSON mutation response raises `LinearProtocolError` without post-write readback. |
| Notification CAS and replay safety | **Resolved and retained** | Durable in-flight acquisition occurs before send; concurrent callers and crash replay produce one send and recovery-required/terminal visibility. |
| Configured-owner binding | **Resolved and retained** | Durable decision/publication records persist owner/config/repository binding; substituted actors/config are inert or rejected, including use of a fresh matching attestation. |

## Findings

### P1 — Claim port and repository authority remain caller-spoofable

`LinearControlPlane._verified_claim_ports` accepts any objects whose public attributes equal the attested string IDs and whose `port.transport` is the same Python object as `self.linear` (`src/skills/linear-delivery-loop/scripts/control_plane.py:65-79`). `TrackingPreflight` signs those caller-configured ID strings, but it does not issue or resolve an opaque engine-owned adapter/journal/authority reference. The facade constructor still accepts arbitrary duck-typed `claim_port` and `claim_authority` objects.

Two direct probes bypassed the intended boundary:

- A newly constructed claim port using the same transport object and copied `adapter_id`/`journal_id` was accepted and returned `claimed`.
- A fake authority exposing only `authority_id="repository-authority-v1"` and returning `{"status":"prepared"}`—without creating a reservation or worktree mapping—was accepted; the provider port moved the issue to `In Progress`.

This leaves the local-before-remote safety invariant caller-selected and does not satisfy the requirement to bind claim/readback to the verified provider adapter, operation journal, and real supervisor authority.

Required repair: resolve engine-owned concrete claim/journal/authority adapters from supervisor state or opaque authorizations that callers cannot self-assert. Remove arbitrary authority/port construction from the mutation-bearing facade boundary, and add same-transport spoofed-port plus fake-authority negative tests that prove refusal before local prepare or provider access.

### P1 — Recovery can race the live operation and perform a duplicate provider claim

`claim` treats `recovery=True` as sufficient authority to enter `_recover_selection` for both `in-progress` and `protected` acquisitions (`src/skills/linear-delivery-loop/scripts/control_plane.py:255-272`). `_acquire_selection` returns `in-progress` to every same-operation caller without atomically transferring the record to a single recovering owner (`src/skills/linear-delivery-loop/scripts/control_plane.py:290-320`). `_recover_selection` may then call `port.claim` while the original live caller is already inside the same call (`src/skills/linear-delivery-loop/scripts/control_plane.py:322-342`).

A barrier probe started the ordinary `op-race-recovery` claim, paused it inside the provider port, then invoked the same operation with `recovery=True`. Both callers executed `claim-port`; one completed and the other failed only at terminal record CAS. The terminal failure cannot undo the duplicate external mutation.

Required repair: recovery must require durable proof that the original executor/lease is no longer authoritative and atomically acquire an exclusive `recovering` ownership generation before any authority or provider call. A same-operation recovery contender must remain inert while the original operation is live. Add live-owner-versus-recovery, two-recovery-worker, and crash-takeover race fixtures.

### P2 — A completed same-operation replay fails instead of returning an idempotent result

After a selection reaches `consumed` or `inert`, `_acquire_selection` rejects even the exact bound operation as “competing or already terminal” (`src/skills/linear-delivery-loop/scripts/control_plane.py:310-320`). A direct probe completed `op-replay`, then replayed the identical request: the second call raised `TrackingPreflightError`. It did not duplicate the provider write, but it also did not provide the stable journal/reconciliation outcome required for unattended at-least-once execution.

Required repair: persist sufficient terminal result/evidence and return a deterministic `already-applied`/`reconciled`/`inert` result for the exact bound operation. Continue rejecting a different operation. Add post-terminal replay tests for consumed, reconciled, inert, and protected-to-terminal paths.

### P2 — Malformed post-dispatch mutation responses bypass readback reconciliation

`LinearTransport.execute` converts GraphQL `errors` during mutations to `LinearAmbiguousWrite`, but `_response` can first raise `LinearProtocolError` for malformed JSON/body/HTTP envelope (`src/skills/linear-delivery-loop/scripts/linear_transport.py:88-145`). `reconciled_mutation` catches only `LinearAmbiguousWrite` (`src/skills/linear-delivery-loop/scripts/linear_transport.py:177-203`).

A direct HTTP-200 malformed-JSON mutation probe performed the initial observation, dispatched the mutation, raised `LinearProtocolError`, and performed zero post-mutation observations. Since the server may have applied the mutation before returning a malformed/truncated response, retrying this outcome can duplicate work and violates read-before/write/read-after reconciliation.

Required repair: classify every post-dispatch mutation outcome that cannot prove non-application as ambiguous and run stable-operation readback. Preserve definitive configuration/pre-dispatch failures and read-only protocol classifications. Add malformed JSON, missing `data`, and malformed response-envelope mutation fixtures with applied/not-applied/ambiguous readbacks.

## Probes and tests

- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — **PASS**, 39 tests.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — **PASS**, 6 tests.
- `git diff --check` — **PASS** (line-ending conversion warnings only).
- Direct attestation and focused-suite re-probes confirmed rejection of forged ID, modified copied fields, extra fields, and a different issuer; a restored issuer with the same key accepts the unchanged signed attestation.
- Direct same-transport-port probe — **FAIL**: unrelated copied-ID port accepted and claimed.
- Direct fake-authority probe — **FAIL**: self-asserted authority ID accepted; remote state changed without real reservation/worktree preparation.
- Direct concurrent live-claim plus `recovery=True` probe — **FAIL**: two provider claim calls for the same operation; late terminal CAS rejected only one result.
- Direct terminal same-operation replay probe — **FAIL**: exact replay raised `TrackingPreflightError`; one original provider write was observed.
- Focused TTL/dedup, quiet-taxonomy, semantic-corruption, owner-binding, notification-CAS, and GraphQL-error fixtures — **PASS**.
- Direct malformed HTTP-200 mutation response probe — **FAIL**: `LinearProtocolError` after dispatch with no post-write readback.
- No build, aggregate validation, QA, Git publication, Linear mutation, network request, provider request, or `dist/` mutation was performed by this reviewer.

## Gate result

Code review 3 fails. Resolve both P1 and both P2 findings and obtain a fresh exact-diff independent review before QA or publication.
