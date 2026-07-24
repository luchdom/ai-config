# SAAS-48 deterministic publication and exact-SHA gates — Code review 10

## Verdict

**PASS** — the exact working-tree implementation on `codex/SAAS-48-deterministic-publication-exact-sha` at base `e90cd165b089e88f0b87e2527c50cb967c935258` closes both P1 and both P2 findings from code-review 9. No new correctness, exact-SHA, authority, privacy, or test-adequacy finding was identified in the reviewed scope.

## Finding counts

- P1: 0
- P2: 0
- P3: 0

## Code-review-9 closure

### PASS — public Git-commit crash replay and finalization ordering

- `cli.run_request()` preserves a `PublicationGitCommittedInterruption` as a pending public journal entry and routes only that pending command through committed replay. The stale command revision is bypassed only for the three closed Git-owning commands and finalization mode.
- Primary, finalization, base-drift, and repair replay each require the exact already-consumed authorization binding, live reservation/worktree identity, original operation ID/scope/revisions, immutable operation trailer, exact committed path set, and current Git readback before the authoritative publication state is advanced. Replay does not consume another grant or create another commit.
- Evidence finalization persists the local commit as `prepared`, clears provider operation identities and authority readback, and makes no claim that the provider has observed the new local head. A fresh push and PR readback must bind the provider-observed final head before final-head gates or merge can proceed.
- The provider fixture now derives publication authority from its remote ref or PR state. Its fallback is the provider-side base observation, not local feature `HEAD`, so the finalization regression exercises the required local-before-push ordering.

Public regressions exist for primary, finalization, base-drift, and repair commit interruption/replay through `cli.run_request()`. This review reran the primary and finalization cases; the drift and repair cases were inspected structurally but not rerun because their composed fixtures are the intentionally long paths excluded from this focused review.

### PASS — applied-after-exception attended phase recovery

- Attended recovery durably consumes the reply and one-shot authorization before the provider attempt.
- When independent reconciliation proves application after an exception, push persists `pushed` with exact head evidence, PR persists `pr-open` with the provider-observed PR identity, and squash merge persists `merged` with exact `mergeSha` and an issued merge-readback attestation. Each retains `consumedReplyId`, clears the active provider operation/refusal, and restores the correct labels.
- Public applied-then-exception regressions cover push, PR, and merge. The merge case continues through the exact returned merge-SHA gate to `completed`.

This review reran the applied-push public path and inspected the PR/merge paths and fixtures structurally.

### PASS — refusal fields are strictly typed and closed

- Durable response/readback fields are allowlisted individually.
- `statusCode` is an exact non-boolean integer in `100..599`; `retryAfterSeconds` is an exact non-boolean integer in `0..1800`; boolean fields require `type(value) is bool`; codes use a closed vocabulary with unknown strings canonicalized to `unclassified`; SHAs must be lowercase full Git SHAs; and the only durable base ref is `main`.
- Nested/free-text provider payloads and mismatched values are omitted. Tests place a privacy sentinel in every allowed field and prove it does not reach the refusal sidecar.

### PASS — raw NUL porcelain rename/copy parsing

- The raw `--porcelain=v1 -z` reader preserves both status columns and recognizes `R` or `C` in either X or Y.
- Rename/copy consumes and validates the required second NUL path field, retains both old and new paths, normalizes Windows separators, preserves spaces, rejects incomplete records, and feeds the result into the strict safe-relative manifest reconciliation boundary.
- Focused fixtures cover staged rename, worktree rename, worktree copy, both NUL path fields, spaces, and Windows-style separators.

## Overall boundary assessment

- Merge remains squash-only and provider/readback bound. Pre-merge requires exact provider base/head/mergeability plus issued final-head aggregate, review, QA or explicit two-SHA reuse, docs, evidence-convergence, engine-owned preparation, and exactly one finalization.
- Base drift performs only the contained ordinary `origin/main` merge, invalidates provider identities and SHA-bound evidence, and re-enters preparation, push, PR readback, finalization, gates, and merge.
- Repair remains same-issue and bounded to three numbered branches originating from current `main`; the engine owns aggregate-first manifest reconciliation, scoped stage/commit/trailers, exact branch/head readback, full pre-merge evidence, merge readback, and returned repair-merge-SHA validation.
- No hosted-check query, provider-setting mutation, bypass/admin path, force push, rebase, direct-main push, tag/release, arbitrary shell, auto-revert, raw provider client, or specialist-side publication authority was found.
- Runtime validators and JSON schemas remain closed and aligned for the reviewed publication state, journal, command, and attestation surfaces.

## Verification evidence

- Reviewed the exact working tree on `codex/SAAS-48-deterministic-publication-exact-sha`, excluding `.codex-remote-attachments`, against the approved plan, tasks, re-audit, implementation artifact, and code-review 9.
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_git tests.linear_delivery_supervisor.test_publication_provider tests.linear_delivery_supervisor.test_publication_recovery -v`: **PASS** — 19 tests in 38.387s.
- Public `cli.run_request()` primary commit replay, finalization commit replay/local-before-push, and applied-push exception recovery: **PASS** — 3 tests in 283.760s.
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_contracts tests.linear_delivery_supervisor.test_exact_sha_gates -v`: **PASS** — 14 tests in 175.195s.
- Changed publication Python modules compile with `py_compile`: **PASS**.
- `engine-command`, `operation-journal`, `supervisor-state`, and `publication-state` JSON schemas parse: **PASS**.
- `git diff --check`: **PASS** (line-ending conversion warnings only).
- The approximately 20-minute complete repair aggregate and full repository aggregate were not run in this focused review. Their prior results were not treated as current evidence; no claim is made for those unexecuted commands.

No live Git/provider/Linear/ntfy/network mutation was performed.
