# SAAS-48 deterministic publication and exact-SHA gates — Code review 8

## Verdict

**FAIL** — the schema/runtime attestation parity defect and the specific attended-crash second-call defect are closed. The broader publication path is not ready: base drift cannot resume, repair preparation still bypasses the engine-owned manifest boundary, evidence finalization does not enforce the accepted lifecycle and is not crash-replay safe, and a successful attended retry overwrites the provider's authoritative phase result. The refusal sidecar is structurally allowlisted but still accepts arbitrary provider strings as durable data.

## Findings

### P1 — Base drift deadlocks publication, and repair heads still bypass engine-owned manifest preparation

The primary path now exposes `PreparePublication` and calls `PublicationGit.prepare_primary()` (`cli.py:475-488`, `supervisor.py:460-511`). That closes the disconnected-library defect only for the first primary commit.

The base-drift path performs the permitted ordinary merge and clears evidence, but it leaves `status: pr-open` and the old push/PR operation identities in place (`supervisor.py:631-656`). The resulting merge head must be pushed before provider head readback and final gates can be authoritative. No public transition can do that: `push` requires `prepared` (or replay states `pushed`/`attempting`/`retry-wait`), so a `pr-open` publication is rejected before the provider call (`supervisor.py:661-677`). The public regression stops immediately after asserting invalidation (`test_publication_public_cli.py:31-45`) and never proves that the drifted head can be pushed, re-finalized, re-gated, and merged. Updating the old `preparation` record's base/head without rerunning preparation (`supervisor.py:646-648`) also preserves an aggregate digest from before the base merge.

Repair preparation still follows the exact caller-created-head bypass identified in code-review-7. `PublicationRepair` accepts `repairHeadSha`; the engine merely compares it with the local branch, then fabricates `preparation.paths` as `docs-ai/repair-evidence.md` and an `aggregateDigest` for `pending: pre-staging-rerun` (`supervisor.py:994-1018`). It never receives/reconciles a repair manifest, proves pre-existing scope, stages the classifier-approved repair diff, or runs the issue-worktree aggregate before the caller's commit. The public fixture itself writes, stages, and commits the repair outside the engine before submitting that SHA (`support_publication.py:410-424`). Its later `PublicationGate(pre-staging-aggregate)` is an isolated exact-SHA gate, not the required aggregate-before-staging boundary.

Required correction: add an engine-owned repair preparation transition using the same real manifest/pre-existing-diff/stage/readback boundary as primary preparation. After base drift, persist a resumable phase that can idempotently push/read back the new head, then rerun the complete affected preparation/finalization/gate set before merge. Add public end-to-end regressions that continue from drift through merge and that cannot supply a pre-created repair commit.

### P1 — Evidence finalization is public but does not enforce the accepted evidence lifecycle

`RecordPublicationAttestation` can now dispatch to `finalize_publication_evidence()`, but that operation is allowed in `prepared` state before any push or PR and accepts only a caller-supplied list of evidence paths (`cli.py:514-526`, `supervisor.py:513-555`). The runnable engine never calls `EvidenceConvergence.require_drafts()` or `require_final_evidence()`; both remain unit-test-only (`exact_sha_gates.py:102-110,199-208`). Consequently the engine does not require the complete draft plan/design-or-not-required/tasks/audit/review/QA/completion set before the sole commit. The public fixture finalizes one code-review file before push and before producing review, QA, docs, or completion checkpoints (`support_publication.py:156-169,305-317`). Later attestation checks cannot prove that the required draft artifact set existed at finalization.

The new Git mutations are also not deterministic after a crash. `prepare_primary()` commits before the publication journal is saved (`publication_git.py:169-193`, `supervisor.py:482-509`); replay sees an empty real diff and cannot reconcile the original manifest. `finalize_evidence()` likewise commits before state/provider readback is saved (`publication_git.py:195-215`, `supervisor.py:533-553`); replay reads the already-finalized pass artifact from `HEAD`, so the required draft-to-pass classification fails. The public journal deliberately resumes pending publication commands (`cli.py:579-587`), but neither mutation has post-crash Git reconciliation tests or a convergent replay path.

Required correction: bind finalization to the complete validated draft inventory and proper post-PR lifecycle, enforce final-head rerun/reuse policy through the public engine, and reconcile an already-created primary/finalization commit by immutable operation identity and exact readback before attempting another mutation. Add crash points after Git commit and before publication-state save for both operations.

### P1 — Successful attended recovery discards the authoritative provider phase result

The attended exception branch now reconciles provider application, durably returns non-application to `paused/ambiguous`, persists the consumed reply, and the generic recovery branch rejects another automatic attempt (`publication_recovery.py:153-163`, `supervisor.py:881-905`). The public crash regression proves no second provider call (`test_publication_public_cli.py:108-125`). That specific prior finding is closed.

However, the success path is not usable. `attempt()` calls `execute_publication_provider()`, which saves the correct phase result (`pushed`, `pr-open` with PR identity, or `merged` with merge SHA) (`supervisor.py:702-783`). `PublicationRecovery.attended_retry()` then updates its stale copy of the original paused publication to generic `status: succeeded` and persists it over that authoritative result (`publication_recovery.py:123-145,153-172`). For a push refusal this makes the next pull-request operation fail because it requires `pushed`; for PR/merge it can also discard the newly observed PR or merge identity. The public test codifies `succeeded` as the expected durable status and does not continue the pipeline (`test_publication_public_cli.py:95-106`).

Required correction: make attended recovery return and retain the reconciled provider operation's exact phase state and identities. Prove public continuation after attended success separately for push, PR, and merge, as well as the already-covered crash/no-second-call case.

### P2 — Refusal persistence still admits arbitrary provider strings

The previous raw-object persistence is improved: `record_refusal()` now stores only `normalized_refusal()` and its digest (`operations.py:725-750`), and nested/body fields are dropped by a focused test (`test_publication_provider.py:36-54`).

The allowlist is only on field names and scalar shape. `_closed_fields()` copies arbitrary strings for `code`, `pullRequestId`, `baseRef`, and related fields (`publication_provider.py:36-60`). Unknown refusals are explicitly classified as `unclassified`, so an arbitrary provider `code` string is still durably written. `assert_public_data()` catches only a small credential-pattern set, not actor data, URLs, diagnostics, or other privacy-bearing strings carried in an allowed field. This does not meet the closed redacted-evidence contract.

Required correction: normalize classification to a closed code vocabulary and validate/hash or omit all readback identifiers that are not required for recovery. Add sentinels inside every allowed string field, including unknown `code` and `pullRequestId`, not only in rejected nested keys.

## Prior-finding closure assessment

- Code-review-7 P1 engine-owned preparation/finalization and base drift: **not closed**. Primary preparation is connected, but repair preparation remains caller-created; base drift cannot push/resume; and finalization omits the required draft/final-head lifecycle.
- Code-review-7 P1 attended crash/no second call: **closed for the exact crash case**. A separate P1 remains because attended success overwrites the real provider phase result.
- Code-review-7 P2 schema/runtime lifecycle parity: **closed**. The schema includes `pre-staging-aggregate`, `merge-readback`, and `provider-readback`, and complete primary/repair/merged/completed parity fixtures pass.
- Code-review-7 P2 redacted refusal persistence: **partially closed, still failing**. Raw nested payloads are gone, but arbitrary provider strings remain durable through allowed fields.

## Additional boundary assessment

- Public mutation commands remain reservation/CAS scoped, and operation IDs remain unique and phase-bound in the normal provider path.
- Exact-head and exact returned merge-SHA gates retain fixed argv, no-shell execution, isolated contained worktrees, clean-before/after checks, and provider merge readback binding.
- No new hosted-check, provider-settings, bypass/admin merge, force, rebase, direct-main push, tag/release, arbitrary-shell, or auto-revert capability was found.
- The Git commit-before-journal gaps above mean publication replay is not yet deterministic even though the generic command journal permits replay.

## Verification evidence

- Reviewed the exact current working tree on `codex/SAAS-48-deterministic-publication-exact-sha`, excluding `.codex-remote-attachments`, against the approved plan/tasks/re-audit and code-review-7.
- Traced public schema and `cli.run_request()` dispatch through reservation authorization, publication journaling, Git preparation/finalization, provider reconciliation, attended recovery, base drift, repair, and state validation.
- `python -u -m unittest tests.linear_delivery_supervisor.test_contracts.SupervisorContractTests -v`: **PASS** (7 tests).
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_provider.PublicationRefusalPrivacyTests.test_persisted_refusal_is_closed_allowlisted_and_nested_payload_free ...`: privacy test **PASS**; the combined command was **FAIL** only because the second requested class name did not exist.
- A combined focused command including contracts, provider, recovery, base-drift public CLI, and attended-crash public CLI exceeded 240 seconds with buffered output and was terminated; no result was claimed from it.
- `git diff --check`: **PASS** (line-ending conversion warnings only).

## Finding counts

- P1: 3
- P2: 1
- P3: 0
