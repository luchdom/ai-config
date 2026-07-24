# SAAS-48 deterministic publication and exact-SHA gates plan

## Discovery

- `AGENTS.md` makes `src/` canonical, `dist/` generated, and `python .\scripts\validate.py` the repository aggregate.
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md` sections 7.8-7.9 define publication, exact-SHA evidence, provider refusal, and same-issue repair policy.
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md` task DDW-AIC-004 is the detailed accepted source requirement.
- `src/skills/linear-delivery-loop/scripts/{supervisor,operations,worktrees,control_plane,control_plane_records}.py` provide the existing state, journal, worktree, and publication-request seams to extend.
- `src/skills/linear-delivery-loop/references/{engine-command,operation-journal,supervisor-state}.schema.json` and `scripts/contracts.py` are the closed runtime/schema boundary.
- `tests/linear_delivery_supervisor/` and `tests/linear_delivery_control_plane/` show the injected-port, disposable-repository, crash/replay, redaction, and runtime-parity test style.

No source conflict was found. The issue is fixture-first: implementation must model Git/GitHub operations without performing live provider mutations. Product design is not required because this is a transport-free engine and operator-contract change with no user-facing screen or interaction.

## Goal

Add a deterministic, idempotent publication subsystem that validates a reconciled Git manifest, models branch/push/PR/squash-merge operations, executes clean isolated repository-configured local gates at exact SHAs, records exact-head review/QA/docs evidence, classifies provider refusals, supports one authorized attended retry, and bounds post-merge repair without hosted-check or provider-control authority.

## Non-goals

- Live GitHub, Linear, or ntfy mutation during tests or implementation.
- Hosted-check discovery, queries, polling, waiting, budgeting, or authority.
- Repository settings, permissions, protection, ruleset, queue, pipeline, admin/bypass, force-push, rebase, direct-main push, tag/release, or auto-revert capability.
- SaaS-specific aggregate/runtime commands or live scheduled-loop enablement.
- A speculative follow-up issue for ordinary publication, implementation, QA, or merge failures.

## Architecture and contracts

1. **Publication records and schemas.** Add strict versioned request/readback, operation, refusal/retry, exact-SHA attestation, evidence-delta, and repair records. Bind repository/workflow/issue, branch, PR/base/head/merge SHA, operation identity, attempts, and redacted provider evidence. Extend supervisor state and operation-journal inventories with runtime/schema parity tests.
2. **Git and manifest boundary.** Add injected Git operations that snapshot base and pre-existing changes, verify the registered physical worktree, reconcile a specialist manifest to the real diff, reject conflicts/unexpected/unrelated paths, run the repository aggregate in the issue worktree before staging as an early feedback gate, and stage only the reconciled scope after it passes. This early gate never substitutes for the later clean isolated exact-head gate. Enforce `codex/SAAS-N-<slug>` and numbered repair branch naming plus prohibited-action denial.
3. **GitHub publication port.** Define a closed injected provider interface for push, primary-PR create/reuse/readback, merge readback, and squash merge. Every mutation is operation-ID/head-bound and reconciled by readback so replay cannot duplicate it. The production package exposes no raw provider client or hosted-check method.
4. **Exact-SHA local gates.** Resolve the configured aggregate command from trusted repository configuration, create a fresh contained disposable worktree at the provider-observed exact PR head or returned merge SHA, prove clean before/after, run fixed argv without a shell, capture redacted command/tool/timestamp/exit evidence, and fail closed on identity or cleanliness drift.
5. **Evidence convergence.** Require implementation plus draft plan, conditional design evidence when the canonical design stage is required (or an explicit validated not-required record), tasks, audit, review, QA, and completion evidence before final gating. A missing required design artifact or missing/invalid not-required declaration fails closed. Classify later deltas with a strict content/path allowlist. Executable or ambiguous deltas invalidate affected gates. Exactly one proven evidence-only finalization commit may be created, staging only the files returned by the classifier; the adapter then rereads the provider-observed final head and reruns final-head docs, aggregate, and review plus QA rerun or explicit two-SHA reuse. Any attempted second finalization commit or non-converging report delta fails closed. Final PR/head/base, exact-head local gate, review, QA/reuse, docs, merge, and post-merge identities are stored in supervisor state and concise Linear evidence without another branch mutation.
6. **Refusal and attended recovery.** Classify transient only for explicit retryable 429, provider 5xx/unavailable, or temporary mergeability when readback proves non-application. The persisted counter model records the initial attempt separately from `retryCount`; at most three retries are allowed after the initial attempt, indexed to the 5/15/30-minute sequence or a capped `Retry-After`. Crash/replay across heartbeats cannot advance or repeat a retry without exact journal/readback reconciliation, and the first refusal after retry count three transitions to exhausted pause. Every transient wait preserves `In Progress` before a PR or `In Review` after a PR, `autonomous`, global WIP, reservation, persistent worktree, branch/PR when present, and all evidence, while releasing only the run lease. Stable, exhausted, ambiguous, permission, policy, required-check, protection/ruleset, merge-queue, or unclassified refusal preserves the same state, adds `blocked + needs-human`, creates or updates one deduplicated Linear operational request, emits one idempotent redacted ntfy attention event, and permits no automatic publication retry. The request is consumed only through exact `RETRY-PUBLICATION <operation-id> <head-sha>` from the configured owner after attended reconciliation. Before granting at most one operation, independently reread issue ordinary state, labels and authorization; reservation and physical worktree; operation journal; branch, PR, head, base and mergeability; every SHA-bound local/review/QA/docs attestation; and the latest provider operation/response/readback. Success clears `blocked` and `needs-human` and resumes the preserved stage; stale, changed-head, unresolved, or ambiguous state remains paused and updates the same request.
7. **Merge and repair.** Re-read stop/authority/reservation/lease and every exact-head attestation immediately before merge. Handle base drift by ordinary merge of `origin/main` with gate invalidation; never rebase/force. Verify returned squash merge identity, run a clean merge-SHA aggregate, and release only after durable success. A failed post-merge gate remains on the same issue in `In Review`, preserves `autonomous` and protected work, and permits at most three numbered repair attempts from current `main`. Every repair re-enters the complete publication/evidence pipeline and must pass the repair head's pre-staging aggregate, final exact-head aggregate, independent review, applicable QA, docs/evidence convergence, squash-merge readback, and exact returned repair-merge-SHA aggregate; any missing, stale, or wrong-head gate prevents merge/completion. Exhaustion moves to `Backlog + needs-human`, updates durable evidence/request state, and emits idempotent redacted ntfy attention without auto-revert or a speculative child.
8. **Integration.** Expose publication operations through the deterministic engine/control-plane composition while preserving specialist non-mutation and current authority separation. Update canonical docs, build generated projections, and add all focused suites to the existing aggregate manifest through normal unittest discovery.

## Acceptance and verification

- Disposable Git repositories/remotes prove containment, manifest reconciliation, the issue-worktree aggregate-before-staging order, branch naming, scoped staging, base drift, dirty-worktree refusal, exact SHA identity, and prohibited Git actions.
- Fixture GitHub responses cover push, PR, and merge success/refusal/readback ambiguity; required-check/protection/ruleset/queue/permission cases; 429, 5xx/unavailable, temporary mergeability, and exhaustion.
- Replay/crash fixtures prove no duplicate push/PR/merge, immutable operation identity, the initial-attempt-plus-three-retries boundary and 5/15/30 indexing, redaction, exact ordinary-state and label transitions, protected WIP preservation, run-lease-only release, complete attended rereads, one-shot recovery, label clearing on success, and idempotent ntfy including repair exhaustion.
- Gate fixtures prove fixed `python .\scripts\validate.py` resolution for `ai-config`, clean-before/after isolated execution, command failure, SHA mismatch, evidence ordering/convergence, conditional required/not-required design evidence and missing-member refusal, one exact classified evidence commit, second-commit/non-convergence refusal, external terminal identities without head mutation, QA reuse rules, returned merge identity, no post-merge mutation, and three-attempt same-issue repair with every gate rebound to each repair head and merge SHA.
- Negative tests prove the public/runtime surface contains no hosted-check query, provider-setting mutation, bypass, direct-main, force, rebase, tag/release, auto-revert, arbitrary shell/command, or raw secret capability.
- Run focused new suites, existing supervisor/control-plane suites, `python .\scripts\build.py`, `git diff --check`, and finally `python .\scripts\validate.py`.

## Risks and mitigations

- **Provider ambiguity:** immutable journal plus independent readback; ambiguity protects state rather than retries.
- **Authority expansion:** closed schemas/ports, fixed argv, operation-specific authorization, and explicit negative tests.
- **False exact-SHA evidence:** bind every attestation to normalized repository, physical worktree, PR/base/head or merge SHA, command digest, and timestamp.
- **Evidence recursion:** strict evidence-only classifier and external final attestations prevent endless completion commits.
- **State migration drift:** versioned schema defaults/migration fixtures and fail-closed unknown fields.
- **Large surface area:** keep provider transport injected and split records, Git containment, gates, publication orchestration, and repair into cohesive modules with focused tests.

## Rollout and rollback

The subsystem remains fixture-only and disabled from live autonomous use. SAAS-49 validates/distributes it; SAAS-52 integrates the thin SaaS adapter; SAAS-54 owns attended activation. Rollback is a normal reviewed code change while preserving journals, reservations, worktrees, and protected publication state; never delete machine state to recover ambiguity.

## Safe assumptions

- Existing accepted SAAS-48 issue text and historical audited program artifacts are authoritative and require no product decision.
- `main` remains the target base and squash is the only merge strategy for this workflow.
- Existing control-plane publication requests remain the durable human-retry interface; SAAS-48 consumes their approval but does not redesign Linear/ntfy policy.
- Current repository validation remains dependency-free and discovers new unittest modules automatically.
