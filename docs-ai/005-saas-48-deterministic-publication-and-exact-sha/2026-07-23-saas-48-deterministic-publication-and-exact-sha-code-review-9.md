# SAAS-48 deterministic publication and exact-SHA gates — Code review 9

## Verdict

**FAIL** — the ordinary base-drift/repair continuation and the normal attended push/PR/merge success paths are now connected end to end. The accepted deterministic evidence lifecycle is still not crash-resumable through the public engine, finalization incorrectly requires the provider to observe an unpushed head, and the attended crash-after-application branch still persists a generic non-phase status. Refusal values and raw porcelain rename parsing also remain open P2 boundaries.

## Findings

### P1 — Evidence commit recovery is helper-only, and finalization requires an impossible pre-push provider head

`PublicationGit` now marks primary and evidence commits with immutable operation trailers and can reconcile the same operation when called directly (`publication_git.py:194-303`). The focused helper regression passes (`test_publication_git.py:14-36`). That does not close the public crash boundary.

Both public mutations consume their reservation authorization before making the Git commit (`supervisor.py:480-491,519-532,573-587`). Consumption advances supervisor/reservation state. A `PublicationGitCommittedInterruption` deliberately leaves the public command journal pending (`cli.py:566-600`), but replay re-enters `_dispatch()` with the command's original `expectedStateRevision`; `PreparePublication` and `RecordPublicationAttestation` reject that stale revision before reaching the helper's `_replay_commit()` (`cli.py:475-489,515-529`). Even if that check were bypassed, the same already-consumed authorization is presented again. No public CLI crash/replay regression exists; the only test invokes `PublicationGit` directly. Repair preparation also commits without `_replay_commit()` or a committed-interruption recovery point (`publication_git.py:305-325`). The accepted commit-before-state-save crash boundary therefore remains non-resumable through the runnable engine.

There is a second ordering defect in the same lifecycle. After creating the evidence finalization commit, the supervisor immediately calls `authority_readback()` and requires its observed `headSha` to equal the new local commit (`supervisor.py:585-615`), before the fresh push at `status: prepared`. A real provider's PR/remote head must still be the prior head until that push. The public fixture masks this by implementing provider authority readback with local `git rev-parse HEAD`, not its `remote_refs` or PR readback (`support_publication.py:84-96`). Consequently the fixture passes a state that a real injected provider cannot report and does not prove the required re-push followed by final provider reread.

Required correction: make the public journal reconcile consumed authorization plus advanced revisions and the already-created commit before any second mutation; cover primary, evidence-finalization, drift, and repair commit boundaries through `cli.run_request()`. Persist the local finalization result first, re-push it, then bind final provider/PR readback to the pushed head. The fixture authority reader must report provider-observed state.

### P1 — Attended recovery still loses exact phase state when reconciliation proves application after an exception

The normal attended success path is corrected: `attempt()` reloads authoritative publication state (`supervisor.py:1003-1017`), `attended_retry()` retains it (`publication_recovery.py:168-176`), and public tests continue successfully from `pushed`, `pr-open`, and `merged` (`test_publication_public_cli.py:73-124`).

The exception path still violates the same phase contract. If the provider mutation applies and then raises before the authoritative phase save, `reconcile_application()` can return `applied: true`; `attended_retry()` persists generic `status: succeeded` from its stale pre-attempt copy (`publication_recovery.py:153-163`). That value is not a valid continuation phase for push, PR, or merge and can omit the newly observed PR or merge identity. The only public crash fixture crashes before application and therefore exercises the `paused/ambiguous` branch, not applied-after-crash reconciliation (`support_publication.py:41-46`, `test_publication_public_cli.py:126-145`).

Required correction: reconcile the exact provider operation into `pushed`, `pr-open` plus PR identity, or `merged` plus merge SHA and persist that authoritative phase. Add one applied-then-crash public regression for each attended provider phase.

### P2 — Refusal persistence still allows arbitrary strings through typed allowlisted fields

Unknown `code` values are now collapsed to `unclassified`, invalid SHA values are omitted, and non-`main` base refs are omitted (`publication_provider.py:36-76`). The focused privacy test passes.

`_closed_fields()` still accepts any scalar type for every allowed key (`publication_provider.py:48-57`). Thus arbitrary provider strings remain persistable through `statusCode`, `retryAfterSeconds`, `ambiguous`, `applied`, `merged`, or `mergeability`; only `code`, SHA fields, and `baseRef` receive value-level normalization. The regression puts its sentinel in rejected keys and invalid SHA/base fields but does not put sentinels into every allowed typed field (`test_publication_provider.py:34-53`). This remains outside the accepted closed redacted-evidence contract.

Required correction: validate each allowed field against its exact closed type/range/vocabulary and omit or canonicalize every mismatch. Exercise privacy sentinels in every allowed field.

### P2 — Raw porcelain parsing does not handle worktree-column rename/copy records

The parser correctly preserves the leading porcelain status column by using raw `-z` output, and the Windows-separator regression covers a leading-space ` M` record (`publication_git.py:39-70`, `test_publication_git.py:9-13`).

Rename/copy continuation is detected only when `status[0]` is `R` or `C` (`publication_git.py:64`). Porcelain v1 has two status columns; an unstaged worktree rename/copy is represented in the second column. For ` R`/` C`, the following NUL field is incorrectly parsed as a new status record, corrupting the reconciled path inventory. No fixture covers either status column, both NUL path fields, spaces, or Windows separators together.

Required correction: recognize rename/copy in either porcelain status column, validate the two-field record, and add raw `-z` fixtures for staged and unstaged rename/copy paths on Windows-style names.

## Closure assessment against code-review 8

- Base-drift resumable reprepare/finalize/push/PR/gates/merge: **PASS for the ordinary non-crash path**. The public fixture continues from `base-drift` through reprepare, fresh push/PR, final gates, merge, and exact merge gate.
- Repair engine-owned manifest/pre-existing aggregate/stage/commit/readback with no caller `repairHeadSha`: **PASS for the ordinary non-crash path**. The public schema has no `repairHeadSha`; the engine creates the numbered branch, then accepts a manifest and owns aggregate-first staging, commit, and branch readback. Crash replay remains part of the first P1.
- Evidence lifecycle with post-PR inventory, re-push/final reread, and commit crash replay: **FAIL** for the first P1.
- Attended success exact push/PR/merge states: **PASS for ordinary returns; FAIL for applied-after-exception reconciliation** under the second P1.
- Closed refusal values: **FAIL** for the first P2.
- Windows raw porcelain parsing: **FAIL** for the second P2.

## Additional boundary assessment

- Complete draft inventory and design-required/not-required validation are now invoked by the public finalization path after PR creation (`supervisor.py:560-587`). Final merge validation calls `require_final_evidence()` and requires final-head review/QA/docs/evidence attestations (`supervisor.py:339-387`).
- Base drift resets provider identities, attestations, preparation, and finalization state and enters a dedicated `base-drift` phase before engine-owned reprepare (`supervisor.py:696-721,467-511`).
- Repair callers no longer supply a prepared head. The two-step repair transition creates the branch from real current `main`, then runs `prepare_repair()` from caller-supplied working-tree manifest changes (`supervisor.py:1043-1123`).
- No hosted-check, provider-settings, bypass/admin merge, force, rebase, direct-main push, tag/release, arbitrary-shell, or auto-revert capability was found in the reviewed closure diff.

## Verification evidence

- Reviewed the exact working tree on `codex/SAAS-48-deterministic-publication-exact-sha`, excluding `.codex-remote-attachments`, against the approved plan, tasks, audits, and code-review 8.
- Traced public schemas and `cli.run_request()` through journaling, authorization consumption, Git preparation/finalization, provider readback, base drift, repair, attended reconciliation, exact-SHA gates, and durable publication state.
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_git.PublicationGitTests.test_primary_and_finalization_commits_reconcile_after_commit_crash -v`: **PASS** (1 test; helper-level only).
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_provider.PublicationRefusalPrivacyTests.test_persisted_refusal_is_closed_allowlisted_and_nested_payload_free tests.linear_delivery_supervisor.test_publication_git.PublicationGitTests.test_status_paths_normalize_windows_separators -v`: **PASS** (2 tests; neither covers the failing value/type and second-status-column cases).
- A combined focused command including publication Git, refusal privacy, base drift, and attended push/PR/merge exceeded 240 seconds with no yielded output and was terminated; no result is claimed from it.
- `git diff --check`: **PASS** (line-ending conversion warnings only).

## Finding counts

- P1: 2
- P2: 2
- P3: 0
