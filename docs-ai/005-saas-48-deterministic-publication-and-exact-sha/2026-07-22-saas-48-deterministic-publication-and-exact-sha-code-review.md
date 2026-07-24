# SAAS-48 deterministic publication and exact-SHA gates — Code review

## Verdict

**FAIL** — two P1 findings and one P2 finding. The individual fixture helpers are a useful foundation, but the working-tree implementation does not yet expose a composed, durable publication flow and two authority/evidence boundaries remain bypassable.

## Findings

### P1 — The publication helpers are not composed into the supervisor runtime or its authoritative state

`SupervisorEngine.OPERATION_NAMES` still contains only the pre-SAAS-48 operations, so no engine command can invoke manifest preparation, push/PR/merge reconciliation, exact-SHA gates, refusal recovery, or repair. Construction merely exposes a standalone `PublicationJournal` (`supervisor.py:27-47,85`), while `PublicationJournal.save()` writes a separate `operations/<id>/publication-state.json` (`operations.py:445-486`) and never updates the supervisor state's new `publication` reference. Consequently `Status` continues to report `publication: null` (`supervisor.py:168`) even after a publication record is saved.

The exact-SHA runner has the same disconnect: it allocates a gate worktree and returns a process-local attestation (`exact_sha_gates.py:40-66`), but never calls the existing authoritative `WorktreeManager.set_gate_evidence()` boundary (`worktrees.py:928-963`). The gate therefore remains active with pending attestation/operation state, and no composed path binds that result to publication state, merge authorization, cleanup, or recovery.

This fails SAAS48-06's composition criterion and the issue's requirement that exact PR/head/base, local-gate, review, QA, docs, merge, and post-merge identities be stored in supervisor state. The isolated class tests cannot demonstrate an end-to-end runnable or recoverable engine.

Required correction: add closed supervisor operations/handlers that orchestrate the existing reservation, journal, worktree, control-plane and publication boundaries; atomically maintain the supervisor `publication` reference; authoritatively complete gate evidence; and add crash/replay integration fixtures from prepared publication through exact-head gate, pause/resume, merge readback, exact-merge gate, and repair.

### P1 — An attended publication authorization can be replayed more than once

`PublicationRecovery.attended_retry()` accepts any caller-supplied mapping with `status == "authorized"`, checks boolean reread flags, and directly calls `attempt()` (`publication_recovery.py:111-134`). It does not invoke or verify SAAS-47's durable `consume_publication_reply` record, bind a consumption marker/reply identity, or persist the consumed transition before granting the mutation. Reusing the same paused publication and the same authorized reply calls `attempt()` again.

A focused diagnostic invoked the method twice with the identical paused state, reply and rereads; the attempt counter reached `2`. Provider readback may sometimes prevent a duplicate applied mutation, but that does not satisfy the one-shot authority contract and leaves retries vulnerable before a composed provider call or across crashes.

Required correction: consume the exact owner reply through the existing durable control-plane boundary in the same replay-safe orchestration transaction before granting one operation; require a fresh consumption identity and reconciled journal state; reject consumed/stale replies on replay; and add a crash-boundary test proving the same authorization cannot execute `attempt()` twice.

### P2 — The evidence-only classifier has no meaningful content rule

`EvidenceConvergence.classify()` treats every text file below `docs-ai/` and arbitrary text replacing `README.md` as evidence-only (`exact_sha_gates.py:83-105`). Its only content checks are that the value is a string and contains no NUL. A focused diagnostic successfully classified `README.md` containing replacement behavioral instructions. In this repository README and workflow artifacts can affect agent/operator behavior, so path-only acceptance can misclassify behavioral or authority changes and permit the single evidence commit without invalidating implementation/QA gates.

This contradicts the issue's strict path **and content** rule. The positive test (`test_exact_sha_gates.py:13-21`) checks only a benign review file, while the negative test checks only an executable path (`test_exact_sha_gates.py:23-26`); neither exercises behavioral text, workflow JSON, canonical documentation, symlink/type changes, or allowed-path content transitions.

Required correction: define a narrow role-aware inventory for draft/final evidence artifacts and validate their schemas/allowed transitions. Exclude README, workflow descriptors, canonical policy, symlinks and non-regular files from automatic evidence-only classification unless a deterministic content-specific rule proves the delta cannot alter behavior or authority. Add adversarial fixtures for each rejected class.

## Diagnostic evidence

- Reviewed the complete working-tree scope against `main`, including all untracked SAAS-48 files and excluding only `.codex-remote-attachments/`.
- Read Linear SAAS-48 and the current plan, tasks, three audits, implementation record, and workflow descriptor.
- `git diff --check`: PASS.
- Focused read-only diagnostics confirmed: no SAAS-48 operation in `SupervisorEngine.OPERATION_NAMES`; arbitrary README text is classified evidence-only; and one authorized reply invokes the attended attempt twice when replayed.

