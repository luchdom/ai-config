# SAAS-48 deterministic publication and exact-SHA gates — Independent re-audit

## Verdict

**FAIL** — the three findings from the first audit are resolved, but two remaining P2 gaps still weaken authoritative evidence-convergence and post-merge repair requirements. Implementation must not begin until the plan/tasks are corrected and a fresh independent audit passes.

## Findings

### P2 — The final-evidence convergence protocol is not fully assigned

The accepted source and Linear issue require a bounded finalization sequence: only a proven evidence-only delta may receive one evidence commit; that commit stages only the classified evidence files; the provider-observed final head is reread and gated; repeated finalization must converge or fail closed; and final PR/head/base, local-gate, review, QA/reuse, docs, merge, and post-merge identities are stored in supervisor state and concise Linear evidence without another branch commit.

The revised plan item 5 and task `SAAS48-04` now cover conditional design evidence, strict evidence-only classification, invalidation, and final-head reruns, but they omit the single-evidence-commit bound, exact evidence-file staging, explicit non-convergence failure, and the terminal no-further-commit supervisor/Linear record. A generic “evidence ordering/convergence” fixture does not define these state transitions. An implementation could therefore loop on tracked completion reports or create additional self-attesting commits while still appearing to satisfy the current task.

Evidence:

- Linear `SAAS-48`, acceptance criteria for final report deltas and final identities.
- Historical accepted plan §7.8 items 8–11 and task `DDW-AIC-004` evidence criteria/tests.
- Current plan, architecture item 5 and risks item “Evidence recursion.”
- Current tasks, `SAAS48-04` acceptance/tests and `SAAS48-06` documentation criteria.

Required correction: explicitly assign the one evidence-only commit, exact classified-file staging, provider-head reread, bounded convergence/fail-closed transition, and external terminal-attestation record with no subsequent branch mutation. Add positive and negative fixtures for a valid single evidence commit, an attempted second finalization commit, non-converging reports, and terminal state/Linear evidence that does not change the head.

### P2 — Post-merge repair no longer requires every gate to rerun

Linear `SAAS-48` and the accepted historical plan require each numbered same-issue repair PR to rerun **all** gates. The revised plan item 7 and task `SAAS48-05` preserve the issue, state, branch naming, attempt limit, notification, and no-auto-revert rules, but only say that a repair attempt/branch is created. Neither makes the complete PR-head local aggregate, independent review, applicable QA, docs/evidence convergence, merge readback, and exact returned merge-SHA aggregate mandatory for every repair attempt.

This omission can allow a post-merge repair to use a narrower path than the primary publication flow, even though it changes already-merged behavior and therefore needs at least the same evidence. The test note’s “three same-issue repair attempts” proves cardinality, not gate completeness.

Evidence:

- Linear `SAAS-48`, failed post-merge validation acceptance criterion.
- Historical accepted plan §7.8 final paragraph and task `DDW-AIC-004` repair criterion.
- Current plan, architecture item 7 and gate fixtures.
- Current tasks, `SAAS48-05` acceptance/test notes.

Required correction: state that every repair attempt re-enters the complete publication/evidence pipeline and must pass all applicable exact-head local, review, QA, docs/evidence, merge-readback, and exact-merge-SHA gates before success. Add a negative fixture proving a repair cannot merge or complete when any one gate is missing, stale, or bound to the wrong repair head.

## Prior findings verified as resolved

- Complete transient/stable refusal state, labels, WIP, reservation, worktree, branch/PR, evidence, run-lease-only release, Linear request, ntfy, attended rereads, and label clearing are now explicit.
- The issue-worktree aggregate-before-staging check and conditional required/not-required design evidence are now explicit with fixtures.
- Retry accounting now separates the initial attempt from retries 1/2/3, maps the 5/15/30-minute sequence, and defines exhaustion/replay boundaries.

## Checks without remaining findings

- One observable fixture-first goal, one repository, one primary PR, dependency order, completion boundary, and non-goals are coherent.
- Closed injected provider operations, exact operation/head binding, readback reconciliation, redaction, worktree containment, fixed no-shell aggregate execution, exact-SHA cleanliness, provider-refusal classification, one-shot attended recovery, base-drift merge without rebase/force, returned squash-merge identity, and forbidden-capability tests are otherwise covered.
- Product design is correctly declared not required for this transport-free engine change while the reusable contract still handles conditional design evidence.
- Rollout remains local/fixture-only and rollback preserves journals, reservations, worktrees, provider-paused state, and evidence.

## Sources consulted

- `AGENTS.md`
- Linear issue `SAAS-48`, including full description and relations
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/workflow.json`
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-plan.md`
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-tasks.md`
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-audit.md`
- Installed `task-audit-breakdown` auditor checklist
