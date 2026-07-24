# SAAS-48 deterministic publication and exact-SHA gates — Code review 6

## Verdict

**FAIL** — one P1 trust-boundary defect remains, and one P2 integration-coverage defect leaves the refusal/recovery and repair claims unproved through the public command surface.

## Findings

### P1 — Evidence convergence cannot come from a real checkpoint, and checkpoint evidence is not bound to this publication

`PublicationJournal.resolve_checkpoint_result()` maps `completedStage == "completion"` to the required `evidence-convergence` attestation (`operations.py:643-685`). A real `ApplyCheckpoint` can never produce that record: `completion` is the terminal stage excluded by both `PrepareIteration` and `ApplyCheckpoint` (`lease.py:425,564`), and advancing/completed worker results must propose a concrete next stage (`lease.py:937-943`). The passing publication fixture avoids those invariants by manually writing an operation journal, checkpoint state, and worker-result sidecar with `completedStage: completion` and `proposedNextStage: null` (`test_publication_contracts.py:114-139`). Therefore the exact required attestation that unlocks merge is accepted only from a synthetic record that the real public checkpoint path would reject.

The resolver also never compares the worker result's `workflowId`, `issueId`, repository identity, or physical-worktree fingerprint with the selected publication. It accepts any retained completed checkpoint in the repository state when its stage maps to a kind and its observed SHA happens to equal the publication head later in `record_publication_attestation()`. This permits a checkpoint from another issue/workflow/worktree to become review/QA/docs evidence for SAAS-48.

Required correction: derive convergence from the real `publication -> completion` checkpoint (that is, a worker result whose completed stage is `publication` and whose next stage is `completion`), and require the source operation request, prepared-iteration record, checkpoint record, worker result, current publication, repository, workflow, issue, worktree fingerprint, producer/stage, exact SHA, and digests to agree. Replace the synthetic journal construction with actual `PrepareIteration` + public `ApplyCheckpoint` calls and add cross-issue/workflow/worktree negative fixtures.

### P2 — Public dispatch coverage does not exercise the claimed refusal/recovery or complete repair paths

The composed test crosses `cli.run_request()` only once, for one review attestation (`test_publication_contracts.py:240-245`). Provider phases, gates, most attestations, and repair calls use `engine.dispatch()` directly. No test drives provider refusal or attended recovery through `run_request()`. The repair loop manually changes authoritative publication status to `post-merge-validating` (`test_publication_contracts.py:254-264,288-292`), then creates a branch and advances its head; it does not run push, PR, pre-staging aggregate, exact-head aggregate, review, QA, docs, convergence, merge readback, and exact-merge failure for each numbered attempt. As a result, the tests do not prove that fixture assembly, durable refusal side effects, attended label/reply semantics, or attempts 1–3/exhaustion work through the schema-valid public path.

The implementation now contains independent attended rereads, pre-merge repair enforcement, provider merge readback, and exact-merge validation, but the current tests can bypass those transitions by directly editing publication state. This is a material regression risk for the runnable loop even after the P1 evidence issue is corrected.

Required correction: add schema-valid `run_request()` scenarios for transient retries 1–3, stable/exhausted refusal, durable request/label/notification/lease effects, malformed/stale/duplicate attended replies, successful attended resume, and three complete repair cycles followed by exhaustion. Do not manufacture checkpoint journals or directly set publication status in those acceptance fixtures.

## Prior-finding closure assessment

- Trusted-result mappings supplied directly by callers: **substantially closed**, but the replacement resolver still accepts impossible and cross-work evidence, so the trust boundary remains open.
- Fixture-only public assembly and production-disabled provider construction: **closed by construction**; absent a registered in-process fixture assembly, `run_request()` installs no publication provider/recovery/Git adapter.
- Independently derived attended rereads: **closed in implementation**; the engine reads request, authorization, reservation, worktree, journal, Git/provider identity, attestations, and refusal evidence rather than accepting caller booleans.
- Provider refusal/reply/label semantics: **implemented but not proven through public dispatch**.
- Repair branch/head advancement and pre-merge/full post-merge gate sets: **implemented but not proven end to end**; current acceptance coverage forces intermediate state.

## Verification evidence

- Reviewed the full working tree against `main`, excluding `.codex-remote-attachments`, and read all five prior code-review artifacts.
- Traced the real `PrepareIteration`/`ApplyCheckpoint` stage invariants against `resolve_checkpoint_result()` and the publication integration fixture.
- Started the focused publication/gate/recovery suite; it exceeded the review window and was terminated without a result. The material findings above are structural and independently reproducible from the cited paths.
