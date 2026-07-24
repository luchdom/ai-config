# SAAS-48 deterministic publication and exact-SHA gates — Implementation

## Outcome

Implemented the fixture-first deterministic publication subsystem without live GitHub, Linear, ntfy, hosted-check, or network calls. The implementation adds strict durable publication records, legacy supervisor-state migration, contained manifest staging with a pre-staging aggregate, injected provider readback/idempotency, clean exact-SHA gates, bounded evidence convergence, complete refusal/attended retry behavior, squash-merge identity checks, and three-attempt same-issue repair policy.

Live autonomous activation, provider credentials/SDKs, hosted-check authority, direct-main delivery, force/rebase, provider-control mutation, bypass/admin merge, tags/releases, auto-revert, and speculative follow-up issues remain absent.

## Real-file manifest

Runtime and contracts:

- `src/skills/linear-delivery-loop/scripts/__init__.py`
- `src/skills/linear-delivery-loop/scripts/contracts.py`
- `src/skills/linear-delivery-loop/scripts/operations.py`
- `src/skills/linear-delivery-loop/scripts/store.py`
- `src/skills/linear-delivery-loop/scripts/supervisor.py`
- `src/skills/linear-delivery-loop/scripts/publication_records.py`
- `src/skills/linear-delivery-loop/scripts/publication_git.py`
- `src/skills/linear-delivery-loop/scripts/publication_provider.py`
- `src/skills/linear-delivery-loop/scripts/exact_sha_gates.py`
- `src/skills/linear-delivery-loop/scripts/publication_recovery.py`
- `src/skills/linear-delivery-loop/references/operation-journal.schema.json`
- `src/skills/linear-delivery-loop/references/supervisor-state.schema.json`
- `src/skills/linear-delivery-loop/references/publication-state.schema.json`

Focused fixtures:

- `tests/linear_delivery_supervisor/test_contracts.py`
- `tests/linear_delivery_supervisor/test_publication_contracts.py`
- `tests/linear_delivery_supervisor/test_publication_git.py`
- `tests/linear_delivery_supervisor/test_publication_provider.py`
- `tests/linear_delivery_supervisor/test_exact_sha_gates.py`
- `tests/linear_delivery_supervisor/test_publication_recovery.py`
- `tests/linear_delivery_supervisor/test_publication_merge_repair.py`

Durable documentation:

- `README.md`
- `src/skills/linear-delivery-loop/references/publication.md`
- `src/skills/linear-delivery-loop/references/supervisor-core.md`
- `src/skills/linear-delivery-loop/references/linear-control-plane.md`
- `src/skills/goal-to-delivery/references/quality-gates.md`
- `src/skills/goal-to-delivery/references/completion-boundaries.md`

Evidence:

- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-implementation.md`

## Observed validation

Focused and directly affected suite:

```text
python -m unittest tests.linear_delivery_supervisor.test_contracts tests.linear_delivery_supervisor.test_store_recovery tests.linear_delivery_supervisor.test_publication_contracts tests.linear_delivery_supervisor.test_publication_git tests.linear_delivery_supervisor.test_publication_provider tests.linear_delivery_supervisor.test_exact_sha_gates tests.linear_delivery_supervisor.test_publication_recovery tests.linear_delivery_supervisor.test_publication_merge_repair -v
Ran 31 tests in 50.663s
OK
```

The suite proves schema/runtime parity, deterministic and idempotent legacy migration, pending-transaction refusal, immutable operation/head replay, manifest/diff containment, aggregate-before-stage ordering, narrow provider capabilities and duplicate prevention, fixed no-shell exact-SHA execution in a fresh clean gate worktree, conditional design evidence, one evidence-only commit, QA reuse bounds, transient/stable refusal behavior, exact attended rereads, repair-exhaustion notification, base-drift invalidation, and complete wrong-head repair-gate refusal.

`git diff --check` passed before the final evidence write and is rerun at handoff. The full `python .\scripts\validate.py` aggregate was intentionally not run in this implementation pass at the coordinating agent's request; independent QA owns the single authoritative aggregate run. `python .\scripts\build.py` was not run because this task explicitly prohibited editing generated `dist/` output.

## Recovery and rollback

Existing valid supervisor state is migrated once by adding deterministic `publication: null` before strict validation. A legacy state with a pending paired transaction fails closed for attended reconciliation rather than rewriting transaction hashes. Rollback must preserve supervisor state, operation journals, reservations, worktrees, branches/PR identities, and paused provider evidence; it must not delete protected state to force progress.

## Code-review-6 public-command matrix closure

- Added `support_publication.py`, a reusable fixture-only scenario assembly registered through the closed CLI fixture registry. Provider/refusal, durable request/reply, exact-SHA gate, real numbered Git repair branch, notification, label, state, and lease-release seams are injected only in-process; every acceptance transition is a schema-valid `cli.run_request` command.
- The public matrix covers transient attempts and retries 1–3 with 5/15/30-minute backoff and capped `Retry-After`, the first refusal after exhaustion, stable pause preservation/deduplication, malformed/stale/duplicate attended replies, consume-before-attempt crash and non-application behavior, successful one-shot resume, and provider identity reuse without duplicate mutation.
- The repair matrix executes the initial publication and three numbered same-issue repair cycles with real branch/head transitions, pre-staging and exact-head aggregates, checkpoint-derived review/QA/docs/convergence, squash-merge readback, and failed exact-merge validation before the next repair. A fourth repair request takes the durable exhaustion path. Missing, stale, and wrong-SHA premerge evidence is rejected through the same public surface.
- Public scenarios exposed and corrected five integration defects: retry recovery invalidated its own state-bound grant before consumption; attended recovery did the same after durable reply consumption; repair branch/head transitions did not update the authoritative issue-worktree mapping; repair exhaustion supplied an invalid control-plane request payload; and the fourth repair returned the intermediate policy result instead of its persisted paused publication readback. Windows path rereads now compare canonical physical paths while retaining exact fingerprint binding.
- The fixture registry accepts an optional deterministic clock only for registered fixture assemblies, preventing long serial acceptance scenarios from expiring otherwise-valid leases while leaving production assembly unchanged.

Focused public-matrix evidence:

```text
transient public retry/exhaustion: 1 test passed in 150.706s
stable/malformed/stale/duplicate/success/crash/non-application attended matrix: 3 tests passed in 428.065s
three complete public repair cycles reached fourth exhaustion in 1031.222s; the run exposed and led to correction of the returned-readback defect
narrow persisted-readback regression after that correction: 1 test passed
related recovery and merge-repair policy suite: 13 tests passed
changed Python modules compile; scoped git diff --check passes (line-ending notices only)
```

The complete public repair test remains in the suite so the repository aggregate executes the final corrected fourth-exhaustion return and exact-command replay once. No live provider, Linear, ntfy, network, or Git publication call was made.

## Code-review finding closure

The failed code-review findings were corrected in the same working tree:

- **Composed authoritative runtime:** the exhaustive engine union now includes `PreparePublication`, `PublicationProvider`, `PublicationGate`, and `RecoverPublication`. `PublicationJournal.save_authoritative` recoverably binds the strict journal record into supervisor `publication`; replay repairs a crash after journal persistence. Provider push/PR/merge uses injected readback, exact-SHA gates complete `WorktreeManager.set_gate_evidence`, and gate/merge identities update the authoritative publication reference. A disposable integration fixture covers prepare, duplicate-safe push, PR, exact-head gate, merge readback, exact-merge gate, terminal status, and journal/state crash recovery.
- **One-shot attended reply:** recovery now invokes SAAS-47's durable `consume_publication_reply`, requires its unique `consumedReplyId`, and persists the attempting transition before calling the provider operation. Identical reply replay returns no authority. Fixtures prove both ordinary replay and a crash after durable consumption cannot execute a second attempt.
- **Strict evidence-only delta:** automatic classification is limited to role-aware dated `code-review`, `qa`, and `completion` artifacts. Each must be an observed regular non-symlink file and make the exact deterministic `draft` to `pass` transition with a role matching its filename and an exact executable SHA. README, workflow descriptors, canonical policy, arbitrary paths/text, unchanged-pass transitions, symlinks, directories, and unobserved files fail closed.

Focused review-fix validation:

```text
python -m unittest tests.linear_delivery_supervisor.test_contracts tests.linear_delivery_supervisor.test_publication_contracts tests.linear_delivery_supervisor.test_publication_recovery tests.linear_delivery_supervisor.test_exact_sha_gates tests.linear_delivery_supervisor.test_publication_merge_repair -v
27 tests executed: 26 passed; one disposable fixture had a local NameError in its fake PR response.

python -m unittest tests.linear_delivery_supervisor.test_publication_contracts.PublicationContractTests.test_composed_publication_provider_gate_merge_and_replay -v
Ran 1 test in 9.954s
OK
```

The fixture typo was corrected from an undefined local to the request's exact `baseRef`; the corrected end-to-end composition test passed. No production/provider behavior was changed to address that fixture-only failure.

## Code re-review finding closure

The remaining ordered-authority and full-content findings were closed:

- Provider phases now advance by guarded CAS through `prepared -> attempting -> pushed -> attempting -> pr-open -> head-gated -> attempting -> merged -> completed`. Out-of-order phases, stale supervisor revisions, wrong gate SHAs, changed/reused provider operation identities, and missing evidence fail before provider mutation.
- Every push, PR, and squash merge receives its own immutable operation identity, persisted in the authoritative publication record before mutation. An `attempting` record can only recover the same phase/identity through provider readback.
- Every phase independently rereads an exact authority record bound to the current supervisor revision, workflow, issue, publication stage, live lease/reservation/mutation authorization, and stop labels. Merge additionally rereads PR/base/head/mergeability and requires exact-head aggregate, independent review, QA or named reuse, docs, evidence convergence, and exactly one evidence finalization.
- The exact-merge gate accepts only `merged` state and the non-null provider-readback merge SHA. Only its successful authoritative gate evidence advances to `completed`.
- `RecoverPublication` now reconciles journal/state crash boundaries and resumes an exact `attempting` provider operation. Paused recovery requires the composed durable `PublicationRecovery` one-shot boundary. `MergeRepairPolicy` participates in premerge validation and same-issue repair progression.
- Evidence classification canonicalizes the entire artifact after substituting only the enumerated `Evidence-State` and `Exact-SHA` fields. Any inserted, removed, or replaced prose fails closed.

Focused re-review validation:

```text
python -m unittest <ordered-state integration> <full-content adversarial> <engine-union parity> -v
Ran 3 tests in 16.212s
OK

python -m unittest <runtime/schema parity> <strict publication record> -v
Ran 2 tests in 3.245s
OK

git diff --check
PASS
```

## Code-review-3 P1 closure

- Removed the caller-installed publication authority observer. Publication now derives the live lease, current `publication` stage, same-issue reservation, and matching unexpired mutation authorization from the engine store under the publication CAS. Labels and PR/base/head/mergeability come from the closed provider readback surface and are persisted as redacted durable readback evidence.
- Preparation rejects preloaded authority readback, attestations, provider identities, or evidence finalization. Review, QA/reuse, docs, and convergence enter through `RecordPublicationAttestation`; exact-head/exact-merge attestations are produced only by the gate runner. Every record has a closed producer/stage/result/provenance/exact-SHA identity and an engine-owned sidecar. Merge rejects absent, fabricated, cross-operation, failed, or stale-head records.
- Provider non-application now carries response/readback into refusal classification. Transient refusals journal `retry-wait`, `nextRetryAt`, and bounded initial-plus-three attempt accounting; stable or exhausted refusals pause. Recovery preserves the same provider phase and idempotency identity, enforces elapsed backoff, and retains the existing durable one-shot attended-reply boundary.
- `PublicationRepair` is a public CAS-bound operation in the exhaustive 20-operation schema/CLI/runtime union. Failed exact-merge validation enters post-merge repair eligibility; repairs are same-issue numbered branches 1-3, invalidate all prior publication/evidence identities, and restart the full pipeline. A fourth request exhausts to paused policy state and composes the existing Backlog/needs-human/request/notification behavior when the recovery control plane is activated.

Final bounded validation:

```text
python -m unittest tests.linear_delivery_supervisor.test_contracts tests.linear_delivery_supervisor.test_publication_contracts tests.linear_delivery_supervisor.test_publication_recovery tests.linear_delivery_supervisor.test_exact_sha_gates tests.linear_delivery_supervisor.test_publication_merge_repair
Ran 28 tests in 54.892s
OK

git diff --check -- <authorized SAAS-48 implementation paths>
PASS (line-ending notices only)
```

## Code-review-4 P1 closure

- Every public prepare/provider/gate/evidence/repair/recovery mutation derives its exact publication scope and consumes a distinct operation-, reservation-, worktree-, state-, and reservation-revision-bound authorization through `ReservationManager.execute_authorized_mutation`. Unrelated scope and consumed/stale grants fail closed.
- `RecordPublicationAttestation` no longer accepts result, producer, stage, exact SHA, timestamp, or opaque provenance from the command. It resolves an immutable engine-owned trusted result sidecar and derives the typed attestation from that validated record.
- Publication persistence writes a non-authoritative proposal, commits its digest/reference through supervisor CAS, and only then materializes the authoritative journal. Reconciliation refuses a proposal that never won CAS or whose digest/reference differs.
- Provider refusals run `PublicationRecovery.refusal`. Attended recovery is public-schema-valid, derives authoritative rereads internally, consumes the exact durable control-plane reply, and uses a new exact mutation authorization for the resumed provider attempt.
- Repair uses an injected Git boundary to create/read the real numbered branch, supports an authority-bound later branch-head transition, clears prior evidence/provider identities, records merge readback evidence, and invokes `MergeRepairPolicy.require_repair_pipeline` before repair completion.

Focused validation:

```text
python -m unittest tests.linear_delivery_supervisor.test_publication_contracts tests.linear_delivery_supervisor.test_publication_recovery tests.linear_delivery_supervisor.test_exact_sha_gates tests.linear_delivery_supervisor.test_publication_merge_repair tests.linear_delivery_supervisor.test_publication_git tests.linear_delivery_supervisor.test_contracts
Ran 32 tests in 96.358s
OK

Changed Python modules compile; engine-command.schema.json and supervisor-state.schema.json parse.
```

## Code-review-5 P1 closure

- Removed unrestricted trusted-result issuance. `RecordPublicationAttestation` now resolves an existing terminal `ApplyCheckpoint` operation, verifies its authoritative checkpoint state and unique engine-owned checkpoint record, validates the embedded `worker-result` schema and digest, and derives evidence kind, producer, stage, passing outcome, exact SHA, timestamp, source identity, and provenance digest. Missing operations, changed checkpoints, invalid worker outcomes, stage mismatches, and digest drift fail closed.
- Added a closed fixture-only `FixtureAssembly` registry used by `cli.run_request`; no production provider is activated without explicit local fixture registration. The publication integration now crosses public schema validation, path validation, operation journaling, CLI parse/dispatch, and the real supervisor handler for specialist evidence.
- Attended recovery no longer manufactures reread booleans. It independently validates the durable control-plane request/ordinary state/labels, exact active recovery grant, live reservation, authoritative worktree mapping, publication CAS digest and journal, real branch head when applicable, provider PR/head/base/mergeability, every issued typed attestation, and the durable latest refusal response/readback sidecar before reply consumption.
- Repair start now persists provider authority readback for the real numbered branch and authorized repair-head advancement refreshes that readback. `pre-staging-aggregate` plus review, QA, docs, convergence, and exact-head evidence are required by `require_repair_pipeline(..., phase="pre-merge")` before squash merge; merge readback and exact-merge validation remain required afterward.

Bounded validation:

```text
python -m unittest tests.linear_delivery_supervisor.test_publication_contracts.PublicationContractTests.test_composed_publication_provider_gate_merge_and_replay
Ran 1 test in 61.668s
OK

Changed Python modules compile.
Scoped git diff --check: PASS (line-ending notices only).
```

### Exhaustive public recovery and repair matrices

- Transient refusal coverage now proves retry indexes 1/2/3 use 5/15/30 minutes and that oversized `Retry-After` is capped at 30 minutes. Existing exhaustion and stable-refusal cases prove the first refusal after retry three pauses and performs durable state/label/request/notification/lease-release effects.
- Attended coverage rejects absent, malformed, stale-head, and duplicate replies; proves reply consumption is persisted before the provider attempt; and proves a crash or non-application restores `autonomous + blocked + needs-human`. The matrix exposed and fixed stop-label ordering: labels are cleared only after durable consumption, restored on failure, and remain cleared only after success.
- Repair coverage now rejects every independently missing, failed, or wrong-SHA premerge member, and independently requires correct merge readback and exact-merge evidence after merge. The public-dispatch integration creates and reads real `repair-1`, `repair-2`, and `repair-3` branches, records later implementation heads through authorized transitions, then proves the fourth dispatch reaches exhaustion and pauses the same publication.

```text
Recovery/repair member matrices plus public run_request integration:
Ran 5 tests in 62.831s
OK

Public-dispatch real branch/head/attempts 1-3/exhaustion integration:
Ran 1 test in 94.689s
OK
```

## Code-review-6 P1 correction

- Evidence convergence now derives only from a real `publication -> completion` checkpoint: `completedStage=publication`, `proposedNextStage=completion`. The impossible synthetic `completedStage=completion` mapping and all fixture-manufactured checkpoint journals/state/sidecars were removed.
- Checkpoint resolution validates the schema-valid source command and terminal journal, exact prepared-iteration reference, authoritative checkpoint state/result and unique sidecar, worker-result schema/digest, repository key/state home, repository/workflow/issue/worktree/fingerprint/stage/SHA, producer, and current publication identity. Cross-issue, cross-workflow, cross-worktree, and cross-fingerprint sources fail closed.
- The fixture now executes real review→QA→docs→publication→completion iterations, using real `PrepareIteration` and public `cli.run_request` `ApplyCheckpoint` calls. Provider, exact-SHA gate, and all attestation phases also cross schema-valid `run_request` dispatch.
- The exact terminal publication capability remains expiry/run/worktree bound across the real completion checkpoint and subsequent authoritative publication revisions, allowing only the already-scoped completion mutations to obtain fresh revision-bound grants.
- The prior test-only direct publication-status edits and manufactured repair attempt loop were deleted. Therefore the earlier “public-dispatch attempts 1–3” evidence above is superseded and must not be treated as current proof; the complete recovery/repair `run_request` matrix remains a separately assigned coverage task.

```text
python -m unittest tests.linear_delivery_supervisor.test_publication_contracts.PublicationContractTests.test_composed_publication_provider_gate_merge_and_replay
Ran 1 test in 114.187s
OK
```

## Code-review-7 closure

- Public preparation now requires a manifest and pre-existing-path inventory and executes contained aggregate-first reconciliation, scoped staging, primary commit, and real branch/base/head readback. Durable state contains engine-produced preparation and pre-staging evidence, which merge requires.
- The closed `RecordPublicationAttestation` command has an evidence-finalization mode. It accepts candidate paths only; the engine reads Git content, proves draft-to-pass-only changes, stages classifier-returned paths, creates exactly one commit, reads back its head, and persists the finalization identity before convergence may be attested.
- Pre-merge provider readback includes exact base SHA. Drift performs only a contained normal `origin/main` merge, makes no squash-provider call, and invalidates the affected gate/finalization evidence for rerun.
- An attended-attempt exception independently reconciles provider application and durably records success or protected `paused + ambiguous` before rethrowing. Generic recovery rejects stable or consumed-reply attempts; a public regression proves a fresh recovery command causes no second provider call.
- Runtime and schema inventories now match for `pre-staging-aggregate`, `merge-readback`, and `provider-readback`. Contract fixtures cover complete primary, repair pre-merge, merged, and completed states.
- Provider refusal sidecars retain only closed scalar classification/reconciliation fields and their digest. Nested bodies, diagnostics, actor/request metadata, URLs, credentials, cookies, and privacy sentinels are removed before persistence.

Focused evidence:

```text
contracts + Git + exact-SHA/convergence + recovery + provider/privacy + base-drift policy:
Ran 29 tests in 21.931s
OK

public attended-crash/recovery-no-second-call regression:
Ran 1 test in 203.216s
OK

public preparation/finalization skip and caller-fabrication regression:
Ran 1 test in 271.409s
OK

updated legacy publication contract/composition module:
Ran 7 tests in 130.921s
OK

public exact-base drift/ordinary origin-main merge/no squash-call regression:
Ran 1 test in 256.774s
OK
```

The complete three-repair public matrix was intentionally not run during this correction pass. No live Git/provider/Linear/ntfy/network authority was used.

## Code-review-8 closure

- Base drift now enters a resumable `base-drift` phase. The next public preparation uses a fresh immutable identity, contains the `origin/main` merge result, commits and reads back the reconciled manifest, clears all old provider identities and SHA-bound evidence, and requires a new push, PR, finalization, and full gate cycle before merge.
- Repair callers no longer provide a repair head or pre-create its commit. `PublicationRepair` accepts only the manifest and pre-existing-path inventory; the Git boundary owns aggregate-first reconciliation, scoped staging, commit trailers, and exact branch/head readback.
- Evidence finalization is post-PR and validates the complete digest-bound plan/tasks/audit/review/QA/completion/design draft inventory from the prepared Git head before the exact classifier may commit. The new head re-enters push and PR readback with fresh operation identities before final-head gates, and final evidence convergence is explicitly revalidated before merge.
- Primary preparation and finalization commits use immutable operation trailers. A crash after Git commit leaves the operation pending; replay recognizes the exact paths/trailers and converges state without a duplicate commit.
- Attended recovery returns the authoritative persisted provider phase and preserves exact push, PR, or merge identities. Durable refusal strings are now restricted to a closed vocabulary or exact SHA/base-ref fields; unknown classifications become `unclassified` and provider IDs/free text are omitted.

Focused Review-8 evidence includes the contract rejection of caller-supplied `repairHeadSha`, engine-owned repair preparation, primary/finalization commit-crash replay, exact draft-inventory validation, privacy sentinels in every allowed string field, attended phase-state continuation, and public base-drift re-entry. No live Git/provider/Linear/ntfy/network authority was used.

```text
contracts + Git/replay/porcelain normalization + exact convergence + provider/privacy + recovery:
Ran 32 tests in 36.064s
OK

post-PR finalization + final push/PR readback + complete composed lifecycle:
Ran 1 test in 200.023s
OK

public attended push phase identity + one-shot command replay:
Ran 1 test in 180.864s
OK

public attended PR identity + full premerge continuation:
Ran 1 test in 567.564s
OK

public attended merge identity + exact-merge completion:
Ran 1 test in 599.682s
OK

public origin/main base-drift reprepare + final push/PR/gates/merge completion:
Ran 1 test in 678.442s
OK

Changed Python modules compile; all three changed JSON schemas parse; scoped git diff --check passes (line-ending notices only).
```

## Code-review-9 closure

- Pending public commands for primary, finalization, base-drift, and repair preparation now have a closed committed-replay path. Replay proves the exact consumed authorization binding, accepts only the advanced current revisions after that proof, verifies the immutable operation trailer and exact commit path/readback, then converges the original journal request without a second Git mutation.
- Evidence finalization persists its local commit with no provider-head claim. The subsequent fresh push binds provider-observed remote/PR head evidence; the public fixture now reports its remote ref or PR head instead of local `HEAD`.
- Applied-after-exception attended recovery reconstructs and persists exact `pushed`, `pr-open` plus PR identity, or `merged` plus merge SHA/readback state while retaining the consumed reply identity.
- Every refusal field now has an exact durable type/range/vocabulary. Privacy sentinels in every allowed field are omitted or canonicalized. Raw NUL porcelain preserves its leading status column, recognizes rename/copy in either status column, validates both path fields, and normalizes Windows separators.

```text
public primary commit crash/replay: 1 test in 49.440s, OK
public finalization commit crash/replay: 1 test in 130.288s, OK
public base-drift commit crash/replay: 1 test in 554.955s, OK
public repair commit crash/replay: 1 test in 598.654s, OK
public attended applied push: 1 test in 138.241s, OK
public attended applied PR: 1 test in 178.420s, OK
public attended applied merge + exact-merge continuation: 1 test in 513.459s, OK
Git/provider/privacy/recovery focused suite: 19 tests in 40.312s, OK
contract and composed publication lifecycle: 15 tests in 176.190s, OK
Changed Python modules compile; all three schemas parse; scoped git diff --check passes (line-ending notices only).
```

## Review-7 QA one-shot recovery closure

- Publication CAS transitions now preserve the current autonomous capability revision throughout every stage already admitted by publication authority (`review`, `qa`, `docs`, `publication`, and `completion`). This lets a fresh attended recovery command obtain its exact one-shot mutation grant after a stable refusal without broadening publication authority.
- When an attended provider call crashes and independent readback proves nonapplication, the same deduplicated request reopens as `pending`, while the authoritative publication remains `paused` with its stable refusal classification and consumed reply identity. Pending request consumption fields remain null per the control-plane contract; replay prevention remains publication-owned.
- The supervisor rejects the same consumed reply identity before a provider call, and an unattended recovery of that consumed publication remains reconcile-only. Protected labels are restored after proven nonapplication.

```text
public attended consumption/crash/nonapplication/reopen/replay: 1 test in 119.430s, OK
focused publication recovery policy: 9 tests in 0.051s, OK
Changed Python modules compile.
```

## Code-review-11 monotonic attended-reply closure

- Publication requests now carry a required non-null `lastConsumedReplyTimestamp` outside their nullable active-consumption fields. New requests initialize the lower bound from their source timestamp, every successful consumption advances it to the consumed reply timestamp, and reopening clears only the active reply ID/timestamp.
- Consumption requires a reply timestamp strictly greater than both the request source and durable lower bound. Identical, older-different, and equal-time-different replies therefore fail before provider dispatch; only a genuinely newer different reply can receive fresh attended authority.
- Existing valid 1.0 control-plane records receive a deterministic, persisted, one-time migration with a revision bump: pending requests backfill from `sourceTimestamp`, while authorized requests backfill from their active consumed timestamp. Schema and runtime validation require the watermark, forbid it from predating the source, and bind an authorized request's active timestamp to the watermark.

```text
public unattended/same/older/equal rejection plus newer success: 1 test in 194.372s, OK
control-plane records and migration/status: 13 tests in 1.212s, OK
supervisor contract/schema parity: 8 tests in 0.113s, OK
Changed Python modules compile; control-plane-state schema parses.
```

## Code-review-12 control-plane version-boundary closure

- Control-plane state now has an explicit 1.1 schema/runtime boundary, independent of the repository's remaining 1.0 contracts. Runtime-parity validation binds the control-plane schema and metadata to 1.1 while retaining 1.0 for other contracts.
- Store migration runs only for documents explicitly declaring `schemaVersion: 1.0`. It deterministically backfills publication reply watermarks, changes the document to 1.1, advances the revision once, and atomically persists the result. Subsequent loads are idempotent.
- A current 1.1 document missing `lastConsumedReplyTimestamp` enters no migration path: strict validation fails, and the malformed document is neither revised nor rewritten. This makes deletion tampering distinguishable from genuine legacy state without changing the monotonic provider boundary or capability behavior.

```text
control-plane records, migration/status, and supervisor contracts: 22 tests in 1.443s, OK
public monotonic reply and capability boundary: 1 test in 191.139s, OK
Changed Python modules compile; control-plane-state 1.1 schema parses; scoped diff check passes.
```
