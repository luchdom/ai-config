# SAAS-48 deterministic publication and exact-SHA gates — Code review 7

## Verdict

**FAIL** — the prior evidence-source binding defect and the prior public repair-coverage gap are closed, but two P1 authority/correctness defects remain in the runnable publication path. Two P2 contract/security defects also remain.

## Findings

### P1 — The public engine does not execute manifest reconciliation, evidence finalization, or base-drift repair

The safety implementations exist only as disconnected library code. `PublicationGit.pre_stage_and_stage()` is referenced only by its focused unit tests; no supervisor or public command invokes it. `PreparePublication` accepts a caller-authored `publicationStateRef` and then persists its branch/head (`cli.py:475-486`, `supervisor.py:456-487`) without reconciling a specialist manifest to the real diff, running the issue-worktree aggregate before staging, staging the classifier-approved scope, or creating/readback-validating the primary branch. The public command schema contains no manifest/pre-existing-diff input that could drive that required transition (`engine-command.schema.json:175-180`).

The same disconnect exists for evidence convergence. `EvidenceConvergence.finalize()` and `require_final_evidence()` are referenced only by focused unit tests. In the runnable path, any schema-valid `publication -> completion` checkpoint at the current head becomes `evidence-convergence`, and `record_publication_attestation()` changes `evidenceFinalizationCount` from zero to one (`operations.py:681-714`, `supervisor.py:506-533`). It does not invoke the path/content classifier, prove a draft-to-pass-only delta, stage classifier-returned files, create/read back the one permitted evidence commit, or rerun final-head docs/review/aggregate/QA-or-reuse. The new public fixture demonstrates this bypass with an empty `artifactManifest` and no evidence commit (`support_publication.py:219-250, 335-365`).

`MergeRepairPolicy.base_drift()` is likewise referenced only by a unit test. Provider authority records only `baseRef: main`, not the observed base SHA, so the pre-merge path cannot detect base advancement, perform the required ordinary merge of `origin/main`, invalidate affected gates, and rerun them (`publication-state.schema.json:43`; `supervisor.py:557-587`).

These are core acceptance and merge-authority boundaries, not missing test assertions. The public repair scenario successfully traverses all three cycles precisely because it supplies already-created heads and checkpoint attestations around the disconnected preparation/convergence steps.

Required correction: expose closed schema-valid operations for contained manifest preparation and one-shot evidence finalization, bind their authoritative Git/readback results into publication state, and make merge consume those engine-produced records. Persist and compare exact base SHA immediately before merge; on drift, perform only the authorized normal merge and invalidate/rerun the complete affected gate set. Add public `run_request()` tests that fail when any of these operations is skipped or caller-manufactured.

### P1 — A crash during the one-shot attended attempt re-enables automatic publication mutation

`PublicationRecovery.attended_retry()` persists `status: attempting` before the provider call. If the call raises, it restores labels but does not persist a paused terminal recovery state (`publication_recovery.py:144-157`). The public crash test confirms the durable state remains `attempting` after the attended reply and authorization have been consumed (`test_publication_public_cli.py:74-84`).

`SupervisorEngine.recover_publication()` treats every `attempting` publication as automatically recoverable and invokes the provider again using a newly authorized recovery mutation, without checking `consumedReplyId` or the stable refusal class (`supervisor.py:789-808`). A caller retaining the publication capability can therefore issue another `RecoverPublication` command and obtain another provider attempt after the sole attended retry crashed. That violates both “paused publication never retries automatically” and “at most one attended operation follows the reply.”

Required correction: after an attended attempt exception, independently reconcile provider application and durably return to a protected paused/ambiguous state before surfacing failure. The generic automatic recovery branch must reject stable/attended operations and must not accept a fresh mutation grant for an already-consumed reply. Add a public regression that submits a new recovery command after the attended crash and proves no second provider call occurs.

### P2 — Publication-state schema and runtime disagree on legal authoritative attestations

The runtime permits and persists both `pre-staging-aggregate` and `merge-readback` attestations (`publication_records.py:29-41`, `supervisor.py:713-776`). The public `publication-state` schema's attestation enum omits both kinds and also omits the `provider-readback` producer (`publication-state.schema.json:55-56`). Consequently a real repair/merged state accepted by `validate_publication_state()` is rejected by `validate_contract("publication-state", ...)`. The existing parity fixture validates only an empty prepared attestation map, so it cannot catch the divergence (`test_contracts.py:209-229`).

Required correction: make schema and runtime inventories identical and add contract fixtures for complete primary, repair pre-merge, merged, and completed states rather than only the initial empty state.

### P2 — Raw provider refusal payloads are durably persisted despite the redacted-evidence contract

`PublicationJournal.record_refusal()` writes complete provider `response` and `readback` objects to `provider-refusal.json` (`operations.py:717-729`). `assert_public_data()` rejects a narrow set of credential-looking keys/values, but it neither redacts nor restricts arbitrary provider fields such as `body`, nested diagnostic payloads, actor data, URLs, or request metadata. This contradicts the schema description and publication reference that provider material is digest-referenced only and raw responses are never persisted. `_redacted_evidence()` does drop a few top-level keys for the digest path, but it is not used before the refusal sidecar write (`publication_provider.py:30-38`).

Required correction: normalize response/readback into a closed allowlisted refusal record sufficient for classification and reconciliation, persist only that redacted record plus its digest, and add nested/body/credential/privacy sentinel tests.

## Prior-finding closure assessment

- Code-review-6 P1 checkpoint convergence/binding: **closed**. The resolver now derives convergence from a real `publication -> completion` checkpoint and cross-checks request, prepared record, checkpoint, worker result, repository key/state home, workflow, issue, physical worktree, stage, exact SHA, and digests.
- Code-review-6 P2 public refusal/recovery/repair coverage: **closed as dispatch coverage**. `support_publication.py` routes the new scenarios through schema-valid `cli.run_request()`, and `test_publication_public_cli.py` covers bounded transient refusal, stable/attended paths, three numbered repair cycles, and fourth-attempt exhaustion. The crash assertion currently codifies the P1 state defect above.
- Exact-SHA isolated aggregate and returned merge-SHA gates: **substantially implemented**. Fixed no-shell argv, detached contained worktrees, clean-before/after checks, provider merge readback, and exact merge SHA binding are present.
- CAS/replay and fourth-repair persisted readback: **closed for the reviewed repair return defect**; the focused persisted-readback regression passes.
- Windows path handling: **no new defect found** in normalized worktree containment or fixed `.\\scripts\\validate.py` argv handling.

## Verification evidence

- Reviewed the exact current working tree on `codex/SAAS-48-deterministic-publication-exact-sha`, excluding `.codex-remote-attachments`, against the approved plan/tasks/re-audit and prior code-review-6 artifact.
- Traced all public publication command variants through schema validation, `cli.run_request()`, journaling, supervisor dispatch, provider/recovery/Git/gate boundaries, and persisted state.
- `python -m unittest tests.linear_delivery_supervisor.test_publication_merge_repair.MergeRepairTests.test_fourth_repair_returns_the_persisted_paused_readback -v`: **PASS** (1 test).
- A five-test focused public refusal/attended plus persisted-readback command exceeded the 180-second review limit before producing a buffered result and was terminated. The supplied transient/attended/repair evidence was considered, but passing current tests would not resolve the structural findings above.
- `git diff --check`: **PASS** (line-ending conversion warnings only).

## Finding counts

- P1: 2
- P2: 2
- P3: 0
