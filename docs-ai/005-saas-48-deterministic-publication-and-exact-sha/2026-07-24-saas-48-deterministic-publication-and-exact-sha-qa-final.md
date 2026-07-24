# SAAS-48 deterministic publication and exact-SHA gates — Final runtime QA

## Verdict

**PASS** — the repository-owned aggregate completed successfully against the requested SAAS-48 working-tree target. All configured validation steps passed, including the complete discovered test suite: **308 tests in 6174.872s**. This final run supersedes neither the historical 2026-07-23 QA failure artifact nor its diagnostic observations; it supplies the required completed aggregate evidence after the fixes.

## Target identity

- Repository: `ai-config`
- Branch: `codex/SAAS-48-deterministic-publication-exact-sha`
- HEAD: `e90cd165b089e88f0b87e2527c50cb967c935258`
- Python: `3.12.0`
- Target form: the current dirty working tree containing the intended SAAS-48 implementation, documentation, and regenerated projections. This is the explicitly assigned target, not a clean committed implementation SHA.
- The unrelated untracked `.codex-remote-attachments/` path was excluded and untouched.

## Authoritative aggregate

Command:

```powershell
python -u .\scripts\validate.py
```

Result: **PASS**, exit code `0`, wall time `6179.4s` (1h 42m 59s).

| Aggregate step | Result |
| --- | --- |
| `build-generated-adapters` (`python scripts/build.py`) | PASS — adapters rebuilt into `dist/`. |
| `marker-managed-sync-regressions` (`python scripts/test_sync_markers.py`) | PASS — fresh-write/splice, legacy/force, and malformed-marker/newline cases passed. |
| `semantic-and-focused-contract-tests` (unittest discovery under `tests/`) | PASS — 308 tests in 6174.872s, `OK`. This includes the complete fixture-backed public publication, recovery, exact-SHA, merge, and bounded repair coverage. |

The aggregate uses local fixture ports and disposable repository resources. It did not perform live GitHub, Linear, ntfy, hosted-check, or network mutation.

## Acceptance mapping

| # | Acceptance criterion | Evidence | State |
| --- | --- | --- | --- |
| 1 | Reconcile manifest, run pre-staging aggregate, stage approved paths | Completed aggregate discovery includes the SAAS-48 publication-Git containment and manifest fixtures. | PASS |
| 2 | One issue branch/primary PR through idempotent injected push, PR, and squash-merge readback | Completed aggregate includes the injected provider and public publication lifecycle fixtures. | PASS |
| 3 | Configured local validation in clean isolated exact-PR-head and exact-merge-SHA worktrees | Completed aggregate includes exact-SHA gate and merge/repair fixtures. | PASS |
| 4 | Preserve state, labels, WIP, reservation, worktree, branch, PR, evidence, and lease across retry/recovery | Completed aggregate includes publication recovery and public attended-recovery fixtures; all discovered tests passed. | PASS |
| 5 | At most one classifier-scoped evidence commit and terminal attestations without later branch mutation | Completed aggregate includes evidence-convergence and exact-SHA fixtures. | PASS |
| 6 | Complete pipeline for at most three same-issue post-merge repairs | Completed aggregate includes the full public repair-cycle and repair-exhaustion fixtures. | PASS |
| 7 | No forbidden provider/hosted/direct-main/force/rebase/tag/release/revert/shell/live authority | Completed aggregate includes contract and negative-capability coverage. | PASS |
| 8 | Focused fixtures, generated projections, documentation checks, and aggregate pass | This aggregate rebuilt projections and passed all 308 tests; documentation stage is separately recorded PASS and code-review-13 is PASS. | PASS |

Counts: **8 passed, 0 failed, 0 unverified**.

## Cleanup and residual risk

- Post-run process check found no remaining `python.exe` process.
- The three temporary marker-test directories reported by the aggregate (`tmp5_qj7yi2`, `tmph1fpktys`, `tmpr1ecceps`) no longer existed after completion.
- Post-run `git diff --check` reported no whitespace errors; only existing LF-to-CRLF conversion notices were emitted.
- The working tree remains intentionally dirty and `.codex-remote-attachments/` remains untracked/excluded. This QA result validates the assigned working-tree target; a later merge-boundary gate must still follow repository policy for exact committed/merged SHA validation.
- No residual runtime defect was observed in this final aggregate.
