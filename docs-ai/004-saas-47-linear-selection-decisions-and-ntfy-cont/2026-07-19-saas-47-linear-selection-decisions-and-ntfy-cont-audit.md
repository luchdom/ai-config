# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Independent Audit

## Verdict

**FAIL.** Two P2 findings remain. Under the independent audit checklist, any P1 or P2 finding fails the pre-implementation gate. No implementation, publication, Linear mutation, ntfy publish, or other live-provider action is authorized by this artifact.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 0 | — |
| P2 | 2 | Fail |
| P3 | 0 | — |

## Findings

### P2.1 — The task excludes required actionable ntfy alerts

The source contract requires ntfy for more than decisions and publication refusals. The corresponding program plan requires alerts for `needs-human`, external blockers, stable/exhausted/ambiguous publication refusal, multiple active issues, and worker/preflight failure, while keeping empty queues, held leases, manual WIP, in-budget transient publication retries, and routine stages quiet (`docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md:685-691`). The original `DDW-AIC-003` requirement likewise makes ntfy mandatory for actionable unattended states (`docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md:218-234`). The final passing program re-audit explicitly certifies this broader actionable-alert contract and quiet-state boundary (`docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`, “Contradiction and traceability checks / User requirements”).

The current plan mentions material decisions and stable/exhausted/ambiguous publication refusal only as examples, so it does not necessarily erase the broader source rule (`2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-plan.md:67-75`). The execution task does erase it: T5 says **only** actionable unattended material decisions and stable/exhausted/ambiguous publication refusals generate notifications (`2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-tasks.md:75`). T2 has no notification acceptance path for terminal/ambiguous preflight failure, T3 fails closed on multiple WIP without the required notify-once behavior, and T4 permits an actionable external prerequisite without requiring the source-mandated attention notification (`tasks.md:39-43`, `:51-52`, `:63-64`). Its fixture matrix therefore cannot prove the complete required trigger set.

This is a source-fidelity and operational-safety failure: unattended states that require human action can remain durable in Linear yet never attract attention. Revise the plan/tasks so the trigger taxonomy includes external blockers, multiple-active-issue reconciliation failure, and actionable worker/preflight failure, with notify-once/idempotency, redaction, durable failure visibility, and explicit positive/quiet fixture coverage.

### P2.2 — The claim task omits the required atomic local-before-remote ordering and rollback proof

The authoritative selection contract requires the re-read winner’s repository reservation and persistent issue-worktree mapping to be created atomically **before** the Linear claim; failure must roll back or reconcile the prepared local operation and perform no claim (`docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md:578-610`). `DDW-AIC-003` carries the same boundary through immediate re-read, atomic reservation/worktree preparation, claim, and ambiguity reconciliation (`docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md:221-224`). This ordering prevents remotely claiming an issue whose local protected work identity was never durably established.

The current plan says only to re-read before “reservation/worktree preparation and claim” and to reconcile changed eligibility or an ambiguous claim (`2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-plan.md:46-55`). T3 repeats that combined phrase without specifying that the local mapping is atomically durable before the provider mutation, or what happens when local preparation, the claim, or readback fails between boundaries (`2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-tasks.md:48-52`). “Claim race/ambiguity” and journal replay tests do not require crash/failure injection at each local-prepare/provider-claim/readback boundary and do not forbid claim-first implementations.

This leaves an architecture boundary under-specified and permits orphaned Linear WIP or unprotected local work. Revise T3 acceptance and tests to require: compare-and-swap local reservation plus persistent worktree mapping first; durable operation identity; provider claim second; readback reconciliation; rollback only when independently safe; and fail-closed recovery with no second candidate at every interruption/ambiguous boundary.

## Checklist readback

- **Goal, non-goals, layout, and ownership:** one bounded `SAAS-47` control-plane goal is registered in the current helper-managed folder. Design is reasonably marked not required because this is transport/control-plane work with no product UI. The audit artifact is the auditor’s only output.
- **Architecture and authority:** provider transports are dependency-injected and fixture-compatible; specialists receive no provider mutation authority; configuration stores identifiers and environment-variable names rather than secret values; Linear remains the durable decision source and SAAS-48 owns publication execution. The two P2 gaps above prevent this area from passing.
- **Secrets and endpoints:** `LINEAR_API_KEY` is environment-only, ntfy values are intentionally absent, redirects/host drift fail closed, and sentinel/redaction tests cover state, evidence, errors, fixtures, and status. No live Linear, ntfy, GitHub, migration, or queue claim is in scope.
- **Pagination, authorization, replay, and idempotency:** transport and migration pagination, progressing cursor enforcement, bounded retries, read-before/write/read-after reconciliation, stable operation IDs, configured-owner replies, exact publication retry grammar, consumed markers, replay rejection, and notification persistence are assigned to focused fixtures. P2.1 and P2.2 identify the remaining incomplete paths.
- **WIP and races:** global `In Progress`/`In Review` reconciliation, manual-WIP quiet exit, exact autonomous resume, zero-WIP selection, deterministic full-set ordering, winner re-read, no second selection, and manual/semi authority reconciliation are present. Atomic local-before-remote claim safety is not yet task-ready.
- **Decisions and follow-ups:** source timestamps, canonical IDs, owner authorization, exact/new/one-time reply consumption, retained publication evidence, no speculative decision child, and one separately achievable prerequisite proposal are explicit.
- **Notifications:** retry bounds, durable idempotency keys, redaction, Linear links, quiet states, and status-visible failure are present, but the required actionable trigger taxonomy is narrowed and fails the gate.
- **Validation and completion:** focused tests, the repository aggregate, generated `dist`, durable source docs, independent code review, runtime QA, clean exact-PR-head aggregate evidence, authorized squash merge, and separate clean exact-returned-merge-SHA aggregate evidence are distinct. Hosted checks are not treated as authority. Publication remains separately authorized.
- **Rollout and rollback:** live activation is deferred to later integration/attended work; mismatch or ambiguity fails before mutation; rollback preserves supervisor evidence and avoids destructive state/worktree cleanup.

## Required re-audit boundary

After the plan and tasks are corrected, create a fresh dated independent audit artifact. Do not overwrite this failed evidence. Implementation must remain blocked until a new audit has no P1/P2 findings.

## Sources consulted

- `AGENTS.md`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/workflow.json`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-plan.md`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-tasks.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`, especially `DDW-AIC-003`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`, especially sections 7.3–7.5 and 7.8.1–7.11
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- Installed `goal-to-delivery/references/{artifact-contract,delivery-stages,quality-gates,completion-boundaries,clarification-policy,autonomous-runtime-contract,work-descriptor.schema.json}`
- Installed `task-audit-breakdown/SKILL.md` and `task-audit-breakdown/references/audit-checklist.md`
