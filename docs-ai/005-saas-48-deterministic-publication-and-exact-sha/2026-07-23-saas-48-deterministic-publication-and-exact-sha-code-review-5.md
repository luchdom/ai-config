# SAAS-48 deterministic publication and exact-SHA gates — Code review 5

## Verdict

**FAIL** — three P1 findings remain. Review 4's proposal/CAS ordering and per-mutation authorization defects are substantially closed, but trusted evidence is still self-issued without authoritative provenance, the public CLI cannot assemble refusal or attended recovery, and the repair flow cannot advance or prevent an incomplete repair from merging.

## Findings

### P1 — “Trusted” review/QA/docs/convergence results are still forgeable records

`RecordPublicationAttestation` no longer accepts the result directly and each evidence mutation consumes an exact scoped grant. However, its source record is created by `PublicationJournal.issue_result()`, which accepts a caller-built mapping and validates only field shape and fixed producer names (`operations.py:643-659`; `publication_records.py:257-280`). It does not resolve `sourceOperationId`, compare `sourceRecordDigest` with an authoritative operation result, prove the named specialist/stage ran, or derive the outcome from an engine-owned journal.

The main integration test demonstrates the bypass: it directly calls `engine.publication_operations.issue_result()` with an arbitrary `sourceOperationId`, a repeated fabricated digest, and `outcome: passed` for review, QA, docs, and evidence convergence, then merges (`test_publication_contracts.py:160-205`). `require_result()` proves only that this unverified mapping was written under `trusted-results`; it does not establish provenance.

Required correction: make trusted-result issuance a closed operation owned by the actual specialist/gate result journal, bind it to an existing immutable source operation and exact digest under CAS, and remove unrestricted mapping-based issuance from the assembled engine surface. Add adversarial tests proving arbitrary/nonexistent source operations, mismatched digests/producers, and caller-selected pass outcomes cannot become merge evidence.

### P1 — Refusal and attended recovery still do not run through the public assembled CLI, and attended “rereads” are asserted

The command schema and CLI dispatch now carry an attended payload, but `run_request()` constructs `SupervisorEngine` without a publication provider, `PublicationRecovery`, control-plane request store, label/state mutations, notifier, lease-release callback, or publication Git boundary (`cli.py:574-584`; `supervisor.py:68-110`). Therefore a schema-valid public `PublicationProvider`/`RecoverPublication` request cannot execute the durable behavior being claimed; all passing refusal/recovery tests call the standalone policy or an injected engine directly, and none crosses `run_request`.

Even in the injected path, `recover_publication()` manufactures every required attended reread as `True` and changes only the provider entry from one shallow comparison (`supervisor.py:727-743`). It does not independently prove the issue, authorization, reservation, worktree, operation journal, branch, PR, base, mergeability, attestations, and latest provider response/readback. This defeats the fail-closed purpose of `REQUIRED_ATTENDED_REREADS` while allowing the reply to be durably consumed.

Required correction: assemble the closed fixture/local adapters through the public construction path and derive every reread from its authoritative owner, including the latest refusal operation/readback. Add `run_request` tests covering transient retries 1–3, stable/exhausted pause side effects, malformed/stale/duplicate reply, durable consumption-before-attempt, and successful attended resume.

### P1 — Numbered repair cannot advance, and the full repair pipeline is enforced only after merge

The first repair operation now creates and reads back a real numbered branch and clears stale evidence. It then persists `authorityReadback: None` (`supervisor.py:803-824`). The next required repair-head transition starts by calling `_publication_authority()` (`supervisor.py:773-790`), which rejects any publication without an authority readback (`supervisor.py:268-270`). Thus the public repair flow cannot record the implementation head after creating the repair branch.

Separately, pre-merge enforcement still calls `_require_merge_evidence()`, whose required set omits `pre-staging-aggregate` (`supervisor.py:338-365`). `require_repair_pipeline()` is invoked only while processing the post-merge aggregate (`supervisor.py:658-678`), after squash merge has already mutated `main`. A repair can therefore be merged without the required pre-staging evidence and only be rejected afterward. The repair tests exercise `MergeRepairPolicy` in isolation; they never drive branch creation, head advancement, attempts 1–3, exhaustion, and all missing/stale members through dispatch.

Required correction: establish a provider/control-plane readback appropriate to the new repair branch before repair-head advancement, persist the resulting implementation head in an authorized journal transition, and require every repair pipeline member before squash merge. Add end-to-end public-engine fixtures that independently omit or stale each member and drive all three numbered attempts plus exhaustion.

## Prior-finding closure assessment

- Exact per-phase mutation grants: **closed** for scope/revision validation and one-shot consumption. Invalid phase requests can consume their grant before later phase checks, but cannot reuse it to mutate.
- Proposal → CAS → authoritative journal recovery: **closed**. A stale/failed CAS has no committed digest, and reconciliation accepts only the exact proposal referenced by the supervisor summary.
- Ordered provider phases, distinct provider IDs, provider-readback merge SHA, and full-body evidence delta classification: **remain closed**.
- Engine-owned/provenance-bound specialist evidence: **not closed**.
- Public refusal and attended recovery with real rereads/durable effects: **not closed**.
- Executable complete bounded repair pipeline: **not closed**.

## Verification evidence

- Reviewed the full current tree against `main`, excluding `.codex-remote-attachments`, and read all four prior code-review artifacts.
- `python -m unittest discover -s tests/linear_delivery_supervisor -t . -p "test_publication*.py" -v`: **21 tests passed** in 90.105 seconds. The coverage remains mostly primitive/policy-level and the happy-path fixture itself fabricates the trusted specialist results described above.
- Structural adversarial trace: repair start clears `authorityReadback`; the immediately following public repair-head operation necessarily fails `_publication_authority`, and repair completeness is checked only after the provider merge.
