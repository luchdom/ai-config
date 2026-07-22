# SAAS-47 Runtime QA Evidence

## Verdict

**FAIL (incomplete required QA gate).** Focused runtime verification passed with **59 passed, 0 failed** tests, but the repository-required aggregate command did not complete in either bounded local attempt. It is therefore unverified and cannot satisfy acceptance criterion 10.

## Target and safety

- Target: the caller-designated current `C:\dev\luchdom\ai-config` working tree after Code Review 7; workflow `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`, work key `004`, issue `SAAS-47`.
- Identity binding: `workflow.json` and the active QA mutation authorization both bind physical worktree fingerprint `sha256:ec10d90a90d5d5aa018df7cfb870f5be7e7bb9167cf06ae30af1875a79e5ac32`; authorization scope is exactly this report. The workflow descriptor SHA-256 observed during QA was `c85e0614fc1a1429a3308933cb72af131acf953dd06b49f42f01df414030e05e`.
- Review input: `2026-07-21-saas-47-linear-selection-decisions-and-ntfy-cont-code-review-7.md` reports the same working-tree/base identity `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4` and a pass with 0 findings. QA did not perform Git operations, so that SHA is review evidence rather than a fresh QA Git observation.
- Environment guard: no Linear/ntfy credentials, live endpoints, provider calls, network calls, Git operations, or provider state were used. The exercised transports used injected local fixtures only.
- Python: `python` on the local repository environment (exit-code evidence below); no dependencies were installed.

## Commands and observed results

| Command | Result | Evidence |
|---|---:|---|
| `python -m unittest discover -s tests\linear_delivery_control_plane -v` | PASS | Exit 0; 53 tests passed in 2.333s. Exercised injected Linear/ntfy transports and disposable local state.
| `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` | PASS | Exit 0; 6 tests passed in 0.082s.
| `python src\skills\linear-delivery-loop\scripts\cli.py --help` | PASS | Exit 0; exposes only `agent-worker-engine --request REQUEST`, confirming this fixture-first control plane has no public live Linear/ntfy command path.
| `python scripts/validate.py` | UNVERIFIED | First attempt timed out without emitted step result after 124.1s (exit 124). Second attempt timed out without emitted step result after 364.0s (exit 124). The repository manifest requires generated-adapter build, marker-sync regression tests, then full `tests/test*.py` discovery; no individual aggregate step can be claimed passed from these attempts.

## Runtime acceptance mapping

| # | Acceptance criterion | Observed fixture/runtime evidence | Result |
|---:|---|---|---|
| 1 | Environment-key-only, paginated, bounded/reconciled/idempotent/redacted Linear GraphQL | Transport tests passed for bounded read retries, pagination completion/progress, redirect/GraphQL failure, and ambiguous mutation readback without duplicate write. | PASS |
| 2 | Complete read-only preflight before mutation | Preflight tests passed for full fixture success with no mutation/secret evidence, required environment values, workspace/version rejection, credential/config rejection, and forged/drifted attestation rejection. | PASS |
| 3 | Deterministic, race-safe, one-issue WIP/Todo selection | Selection tests passed for global WIP precedence, complete ordering, mandatory preflight, single concurrent claim, CAS, local-before-remote order, recovery fencing, and terminal replay. | PASS |
| 4 | Manual/semi-autonomous authority reconciliation/removal safety | `test_manual_label_removal_requires_matching_authority`, recovery, foreign-authority, and verified-attestation tests passed. | PASS |
| 5 | Deterministic refinement/external-integration proposals without invented intent | `test_composed_proposals_failures_and_quiet_states` and selection rejection taxonomy passed. | PASS |
| 6 | Deduplicated, owner-authorized, exact ordered decision/publication retry consumption | Decision and publication-retry fixture tests passed, including exact new-owner reply consumption and once-only reconciled retries. | PASS |
| 7 | One achievable independently actionable prerequisite only; no speculative decision task | `test_follow_up_is_only_for_achievable_external_prerequisite` passed. | PASS |
| 8 | Idempotent, redacted actionable ntfy; quiet routine/transient states | Notification tests passed for one sender under concurrency/replay, recovery-required handling, redacted status-visible failure, and quiet-state taxonomy. | PASS |
| 9 | Fully paginated, mutation-free migration report | Migration tests passed for verified-page use, incomplete/repeated-pagination refusal, every issue/rejection/action reporting, unrelated-label preservation, and no mutation. | PASS |
| 10 | Focused fixtures, projections, durable docs, and aggregate validation at exact PR head/merge SHA | Focused fixtures passed; however the required aggregate did not complete, QA did not verify generated projections/docs through that aggregate, and this working-tree QA cannot verify the later exact-merge-SHA gate. | FAIL / UNVERIFIED |

## Cleanup

Focused fixtures used `TemporaryDirectory` resources. After the suite, no temporary directories remained for `selection-snapshot-*`, `selection-publication-*`, `control-plane-records-*`, `migration-pages-*`, or `control-plane-status-*` in the local temporary directory. No persistent disposable resource, external state, or credentials were created by QA.

## Blocker and residual risk

The required local aggregate is blocked by non-completion: `python scripts/validate.py` produced no step-level result and exceeded both bounded QA windows. Consequently, aggregate build/projection, sync-marker, and complete repository-test results are not evidenced. Exact PR-head and exact merge-SHA validation are also not available from this working-tree QA run. A separately authorized follow-up should diagnose the aggregate hang/non-completion and rerun it successfully at the required exact identities; no production defect was diagnosed or fixed by QA.
