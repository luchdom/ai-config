# SAAS-48 deterministic publication and exact-SHA gates — Code review 3

## Verdict

**FAIL** — two P1 findings remain. The second repair closes ordered phase enforcement, distinct provider operation identities, provider-readback merge-SHA binding, and full-body evidence-delta rejection. It still does not establish engine-owned publication authority/evidence or integrate refusal/retry/repair into the runnable state machine.

## Findings

### P1 — Merge authority and non-aggregate attestations remain caller-asserted

`SupervisorEngine._publication_authority()` trusts an injected `publication_authority_observer` mapping for live lease, reservation, mutation authorization, labels, PR identity, head, base, and mergeability (`supervisor.py:252-292`). It does not derive or verify those facts against the engine's authoritative lease/reservation/control-plane records. The integration fixture demonstrates the gap by returning every authority boolean as `True` without acquiring a lease, reservation, or mutation authorization (`test_publication_contracts.py:89-96`).

The same boundary accepts arbitrary attestation objects in `PublicationState`: runtime validation requires only that `attestations` is a dictionary (`publication_records.py:115-126`), and the JSON schema permits any object values. `prepare_publication()` permits those caller-supplied attestations and a pre-set `evidenceFinalizationCount`; `_require_merge_evidence()` then trusts only caller-provided `exactSha` and `passed` fields (`supervisor.py:294-317`). Only the aggregate attestation is produced by the exact-SHA runner. Consequently a caller can preload fabricated review, QA, docs, and evidence-convergence claims and reach merge under a fabricated authority observer.

Required correction: derive publication authority from current engine-owned lease, reservation, mutation-authorization, issue/label, and provider-readback records under the same CAS boundary. Store typed, provenance-bound attestations through closed engine operations; reject preloaded/untrusted evidence and validate each required attestation's immutable identity, exact SHA, producer/stage, and result before merge.

### P1 — Provider refusal, scheduled retry, attended recovery, and post-merge repair are still disconnected from provider/gate execution

`execute_publication_provider()` calls the provider coordinator directly and has no refusal classification or transition to `retry-wait`/`paused` (`supervisor.py:333-411`). Provider non-application raises from `PublicationProviderCoordinator`; the journal remains `attempting`, and `recover_publication()` immediately repeats that provider phase (`supervisor.py:451-470`). It never invokes `PublicationRecovery.refusal()`, applies the documented 5/15/30-minute schedule, enforces the retry limit, or creates the durable attended request. The attended branch is reachable only if some out-of-band writer has already forced the record to `paused`.

Post-merge repair is likewise not composed. A failed exact-merge aggregate raises while publication remains `merged`; no engine path moves the same issue into repair. `next_publication_repair()` is absent from `OPERATION_NAMES`, the command schema, CLI dispatch, and recovery dispatch, and it only records `repairing` metadata. Nothing invokes `base_drift()`, `require_repair_pipeline()`, or `repair_exhausted()` in the runnable flow. Thus the documented bounded same-issue repair pipeline cannot execute or recover.

Required correction: make provider refusal/readback a journaled result of each phase, feed it through the retry/pause policy, honor `nextRetryAt`, and consume attended authority through the assembled recovery operation. Route failed post-merge validation into a public CAS-bound repair operation that creates the numbered branch, invalidates stale evidence, requires the complete repair pipeline, and invokes exhaustion handling after attempt three. Add integration/crash tests for transient refusal, retry exhaustion, attended resume, failed merge gate, each repair, and final exhaustion.

## Prior-finding closure assessment

- Ordered publication phases and distinct push/PR/merge operation identities: **closed**.
- Current authority and exact-head evidence immediately before merge: **not closed**; values are injected/caller-authored rather than engine-owned.
- Provider-readback merge SHA before terminal completion: **closed**.
- Integrated retry, recovery, and repair: **not closed**.
- Full-body evidence-delta rejection: **closed**; `_immutable_body()` permits only the enumerated state/SHA transition and adversarial insert/remove/replace tests pass.

## Verification evidence

- Reviewed the complete working tree against `main`, including untracked SAAS-48 files and excluding only `.codex-remote-attachments/`, plus both prior code-review artifacts.
- Focused publication, gate, provider, recovery, and repair suites: **24 tests passed** with `python -m unittest`.
- `git diff --check`: **PASS** (line-ending warnings only).
- `pytest` is not installed in the active Python environment; the repository's focused `unittest` suites were used.
