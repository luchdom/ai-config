# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Code Review 4

## Verdict

**FAIL / CHANGES REQUESTED.** Terminal replay and post-dispatch transport reconciliation are repaired, and the live-owner/two-recoverer cases now have the intended CAS behavior. Three P1 authority/recovery/pagination defects and one P2 migration-pagination defect remain. No P3 findings were identified.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 3 | Fail |
| P2 | 1 | Fail |
| P3 | 0 | Pass |

## Review identity and target

- Reviewer: fresh independent post-fix code reviewer 4 (`/root/saas47_code_review_4`)
- Base/working-tree HEAD: `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4`
- Branch: `codex/saas-47-linear-control-plane`
- Workflow: `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`
- Scope: exact current tracked and untracked SAAS-47 working-tree delta, approved plan/tasks/re-audit, and all three earlier failed code-review artifacts
- Review time: `2026-07-20T02:51:54Z`

## Review-3 blocker matrix

| Required re-probe | Result | Evidence |
|---|---|---|
| Copied-ID same-transport port/fake authority cannot enter the mutation facade; engine binding cannot be swapped | **Unresolved (P1)** | The facade no longer accepts port arguments and resolves a one-time bundle, but `TrackingPreflight.bind_claim_adapters` remains a public raw-capability input and the supposedly engine-owned bundle is a writable `_claim_adapters` attribute. Replacing that tuple after attestation caused the copied port/fake authority to perform lease, prepare, provider claim, readback, and commit while the original adapters received no calls. |
| Live owner versus recovery plus two recoverers require dead/expired proof and one exclusive generation | **Partially resolved (P1 remains)** | A recovery call against a live `in-flight` operation stays inert, and two recovery callers against `protected` state have one CAS generation/provider call. However, an actual hard crash leaves the durable record `in-flight`; even after the exact lease expires and the authority reports the owner dead, `recovery=True` returns `in-flight` without asking for recovery proof or acquiring a generation. |
| Exact terminal same-operation replay returns a stable result; a different operation rejects | **Resolved** | Focused consumed/recovered and inert fixtures return the persisted terminal result on exact replay, retain one provider call, and reject a different operation ID. Runtime validation binds terminal result issue/operation/status to the record. |
| Every malformed JSON/missing-data/envelope mutation outcome after dispatch enters readback; pre-dispatch/read failures remain distinct | **Resolved** | Mutation `execute` converts requester/protocol/redirect/status/GraphQL/missing-data uncertainty to `LinearAmbiguousWrite`; `reconciled_mutation` performs readback for applied, not-applied, and ambiguous-readback outcomes. Empty credential/operation validation happens before dispatch and read-only malformed responses retain protocol/GraphQL classifications. |

## Retained-guarantee matrix

| Guarantee from earlier reviews | Result |
|---|---|
| Exact-field issuer-verifiable preflight attestation; config/repository/owner/transport-settings binding | Pass |
| Fresh matching attestation after TTL preserves logical decision/publication/selection identity | Pass |
| Configured-owner reply authorization and exact one-time reply syntax | Pass |
| Pending/protected/foreign authority blocks a second ordinary selection for the supplied snapshot | Pass |
| Source-to-attention taxonomy, quiet proposals, cardinality, and metadata equality | Pass |
| Notification pre-send CAS, replay safety, redaction, and status-visible failure | Pass |
| Strict record variants, canonical IDs, consumption parity, recovery/terminal cross-fields | Pass |
| GraphQL mutation errors enter readback; read GraphQL errors remain distinct | Pass |

## Findings

### P1 — The claimed engine-owned mutation bundle is caller-replaceable

`TrackingPreflight.bind_claim_adapters` accepts raw port and authority objects and stores them in the writable `_claim_adapters` attribute (`src/skills/linear-delivery-loop/scripts/tracking.py:120-149`). `LinearControlPlane._verified_claim_ports` subsequently trusts whatever objects that mutable tuple currently contains (`src/skills/linear-delivery-loop/scripts/control_plane.py:64-78`). The signed `claimBindingId` proves only the preflight instance's string binding; it does not bind the concrete object identities into an immutable supervisor-owned registry.

A direct probe bound legitimate adapters, created a valid attestation and selection, replaced `preflight._claim_adapters` with a copied-ID same-transport port and a fake structural authority, and invoked `claim`. The claim returned `claimed`; every lease/prepare/claim/readback/commit event occurred on the replacements and no original adapter was called. Initial binding is likewise structural and accepts caller-created objects. The constructor/`__slots__` negative test only prevents adding `claim_port` to the facade; it does not test or protect the actual resolver.

Required repair: resolve mutation capabilities from the SAAS-46 supervisor's authority/journal registry by opaque engine-owned reference, with no public raw-capability bind/replace surface. The attested reference, resolved provider adapter, journal, and repository authority must be immutable for the engine lifetime. Add direct initial-fake-bind, post-attestation bundle-swap, copied-port, and fake-authority probes proving refusal before lease/local/provider access.

### P1 — A hard crash in `in-flight` state can never be recovered

`_acquire_selection` treats every same-operation `in-flight` record as live and returns `in-progress`, regardless of `recovery=True`, owner-death evidence, or lease expiry (`src/skills/linear-delivery-loop/scripts/control_plane.py:343-344`). Recovery proof and the `recovering` generation are reachable only from `protected`. A Python exception passes through the handler and normally marks `protected`, but process termination after the durable pending-to-in-flight CAS cannot run that handler.

A direct crash-boundary probe persisted the normal `in-flight` acquisition and then simulated the worker disappearing. At `12:06`, after the recorded `12:05` lease expiry and with the authority reporting the owner dead, an exact-operation recovery returned `in-flight`, left the record unchanged, and made zero `authorize_recovery` calls. This permanently protects neither a recoverable worker nor forward progress and fails the required interruption-at-every-boundary behavior.

Required repair: for `in-flight + recovery`, have the engine authority distinguish a still-live owner from durable dead/expired proof. Keep a live owner inert; otherwise CAS the exact operation to one `recovering` generation before local/provider access. Add a hard-crash immediately after acquisition, hard-crash during prepare/claim/readback, live-lease refusal, expired/dead takeover, and two-takeover race matrix.

### P1 — Selection trusts an arbitrary, unproven partial issue snapshot

`choose_or_resume` accepts a raw `snapshot_observer` callback and trusts its returned `issues` collection after checking only the five top-level keys (`src/skills/linear-delivery-loop/scripts/control_plane.py:106-136`). The callback is not the attested Linear adapter, carries no page/cursor completion proof, and is not reconciled with a transport-owned fully paginated observation. The snapshot digest faithfully persists an incomplete list but cannot prove completeness. Claim then rereads only the chosen issue, not global WIP.

Consequently a caller/adapter can omit a later page containing `In Progress`/`In Review` work or a higher-priority candidate; the control plane can persist and remotely claim a second issue. The focused pagination test covers `LinearTransport.paginate` in isolation, while selection tests inject already-materialized lists and never prove that selection consumes that complete transport result.

Required repair: remove the raw selection snapshot capability and obtain the authoritative issue/reservation/worktree/recovery snapshot through engine-owned adapters under the shared supervisor boundary. Linear issue observation must carry transport-verified terminal pagination evidence, and selection must reject missing/repeated/incomplete cursors before recording a claim. Add a multi-page fixture with active WIP and the winning candidate only on later pages plus truncated/repeated-cursor negative cases.

### P2 — Migration dry-run does not perform or prove complete pagination

The migration API accepts an arbitrary `Iterable` (`src/skills/linear-delivery-loop/scripts/control_plane.py:645-652`), and `build_migration_report` simply loops over it (`src/skills/linear-delivery-loop/scripts/migration.py:13-20`). It neither invokes `LinearTransport.paginate` nor accepts/verifies pagination-completion evidence. Its only test supplies one in-memory list; there are no migration-level missing/repeated-cursor or multi-page fixtures, despite T5 requiring those exact cases.

An incomplete report is still stamped `mutationFree: true`, validates successfully, and appears authoritative while silently omitting candidates. This violates the approved requirement that the migration dry-run fully paginate and report every observed issue.

Required repair: compose migration reporting with the verified Linear pagination adapter (or require a strict, engine-issued completed-observation record) and fail closed unless terminal pagination is proven. Add migration-level multi-page, repeated/empty cursor, incomplete last-page, mutation-count-zero, and preserved-metadata fixtures.

## Probes and verification

- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — **PASS**, 42 tests.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — **PASS**, 6 tests.
- `git diff --check` — **PASS** (line-ending conversion warnings only).
- Direct mutation-bundle swap probe — **FAIL**: copied port/fake authority claimed and committed; legitimate adapters had zero events.
- Direct hard-crash/expired-owner recovery probe — **FAIL**: status remained `in-flight`; no recovery proof request or generation acquisition occurred.
- Direct API/pagination composition inspection — **FAIL**: selection accepts a raw snapshot callback and migration accepts a raw iterable; neither surface requires completed pagination evidence.
- Existing live-owner, two-recoverer, terminal replay, and malformed post-dispatch response fixtures — **PASS**.
- No fix, build, aggregate validation, QA, Git publication, Linear mutation, network/provider request, `dist/` mutation, or `workflow.json` mutation was performed by this reviewer.

## Gate result

Code review 4 fails. Resolve all three P1 findings and the P2 migration finding, add the missing adversarial fixtures, and obtain another fresh exact-diff independent review before QA or publication.
