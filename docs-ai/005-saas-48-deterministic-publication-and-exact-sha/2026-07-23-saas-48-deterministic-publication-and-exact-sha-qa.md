# SAAS-48 deterministic publication and exact-SHA gates — Runtime QA

## Verdict

**INCOMPLETE / FAIL** — runtime QA cannot pass because the required repository aggregate did not complete: `python .\scripts\validate.py` exceeded its bounded 40-minute timeout and exited `124`. A preceding diagnostic public CLI matrix also returned `1`, with one observed failed recovery test. No production code was changed.

## Target identity

- Repository: `ai-config`
- Target branch: `codex/SAAS-48-deterministic-publication-exact-sha`
- HEAD at start: `e90cd165b089e88f0b87e2527c50cb967c935258`
- Target type: current dirty working tree containing the intended SAAS-48 implementation and regenerated/documented scope; this is not a clean committed SHA.
- Excluded unrelated path: `.codex-remote-attachments/` was present as untracked and was not inspected, changed, or included in verification.
- Python: `3.12.0`

## Commands and results

| Command | Result |
| --- | --- |
| `git diff --check` | PASS; no whitespace errors. Git emitted only LF-to-CRLF notices. |
| `python -m unittest tests.linear_delivery_supervisor.test_publication_git tests.linear_delivery_supervisor.test_publication_provider tests.linear_delivery_supervisor.test_publication_recovery tests.linear_delivery_supervisor.test_exact_sha_gates -v` | PASS; 26 tests in 44.906s. Fixture-backed disposable repositories and injected provider ports exercised Git containment/reconciliation, provider readback/privacy, refusal/recovery, and exact-SHA/evidence paths. |
| `python -u -m unittest tests.linear_delivery_supervisor.test_publication_contracts tests.linear_delivery_supervisor.test_publication_merge_repair tests.linear_delivery_supervisor.test_publication_public_cli -v` | Diagnostic only, superseded by the required aggregate; exit 1 after 1180.6s. Captured output showed the preceding 13 contract/repair tests passing, then `test_attended_consumption_precedes_crash_and_nonapplication_restores_labels` failed. The captured stream did not include its traceback or a final test count, so root cause is unverified. |
| `python .\scripts\validate.py` | REQUIRED AGGREGATE: did not complete. Timed out after 2404.1s (40-minute bound), exit 124. It was terminated during cleanup with its unittest child; no aggregate pass/fail or total count is available. |

## Acceptance mapping

| # | Criterion | Observed evidence | QA state |
| --- | --- | --- | --- |
| 1 | Manifest reconciliation, pre-staging aggregate, approved-path staging | Focused Git suite passed `test_manifest_aggregate_then_scoped_stage`, unexpected/failed-aggregate refusal, branch naming, and crash replay. | PASS (focused fixture path) |
| 2 | One issue branch/primary PR via idempotent injected push, PR, squash merge/readback | Focused provider suite passed duplicate-operation readback and forbidden-capability tests; full public lifecycle aggregate did not complete. | UNVERIFIED |
| 3 | Clean isolated configured validation at provider PR/merge SHA | Focused exact-SHA test passed fixed no-shell argv and fresh clean exact-SHA handling; complete merge lifecycle aggregate did not complete. | UNVERIFIED |
| 4 | Preserved state and bounded retry/attended recovery | Focused recovery suite passed (including retry/backoff, replay, labels, request/notification and exhaustion cases), but the diagnostic public matrix observed a failure in `test_attended_consumption_precedes_crash_and_nonapplication_restores_labels`. | FAIL / defect requires implementation investigation |
| 5 | At-most-one classifier-scoped evidence commit and terminal attestations | Focused exact-SHA/evidence-convergence tests passed, including one scoped commit, invalid delta refusal, and explicit two-SHA QA reuse; full aggregate incomplete. | UNVERIFIED |
| 6 | At-most-three complete same-issue repair cycles | Focused repair tests passed the mandatory-gate and three-repair/exhaustion fixtures; the required complete public matrix was not authoritatively completed by the aggregate. | UNVERIFIED |
| 7 | No forbidden hosted/provider/direct-main/force/rebase/tag/release/revert/shell/live authority | Focused provider/Git negative-capability tests passed; full aggregate incomplete. | UNVERIFIED |
| 8 | Focused fixtures, generated projections, documentation checks, and repository aggregate pass | Focused fixture command passed, but the required aggregate timed out. Prior documentation PASS and code-review-10 PASS are read evidence only and do not replace runtime QA. | FAIL |

Counts: **1 passed, 2 failed, 5 unverified** of 8 workflow acceptance criteria.

## Cleanup and isolation

- No live GitHub, Linear, ntfy, hosted-check, or network mutation was performed. Provider behavior used injected fixtures; repository resources were disposable test fixtures.
- After aggregate timeout, the QA-started `scripts\\validate.py` process (PID 44452) and its unittest child (PID 43676) were explicitly stopped. A subsequent process query found no remaining `python.exe` process.
- No QA-created top-level temporary resource remained. Existing `tests/` is repository content, not a temporary resource.
- `.codex-remote-attachments/` remains untouched and excluded.

## Blockers and residual risk

1. Required aggregate validation is incomplete due to the 40-minute timeout; regenerated projection, marker-sync, and complete discovered-suite outcomes were not obtained from that command.
2. The observed public recovery-test failure needs a separately authorized implementation investigation and rerun with complete traceback capture. It may be order-sensitive, but that has not been established.
3. This dirty-worktree target cannot provide clean exact-commit identity evidence. No merge/publication decision should rely on this QA artifact until the defect is resolved and the aggregate completes successfully against the intended exact target.
