# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Independent Re-audit

## Verdict

**PASS.** The revised plan/task package resolves both prior P2 findings and is actionable for implementation. No P1, P2, or P3 findings were identified in this fresh readback. This artifact passes only the pre-implementation audit gate; it grants no implementation, Git/GitHub, Linear, ntfy, migration, publication, or merge authority.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 0 | Pass |
| P2 | 0 | Pass |
| P3 | 0 | Pass |

## Prior finding resolution

### P2.1 — Complete actionable ntfy taxonomy

**Resolved.** The revised plan now requires notifications for every source-required actionable unattended category: material `needs-human` decisions, independently actionable external blockers, multiple-active-issue reconciliation failures, stable/exhausted/ambiguous publication refusal, and actionable worker or preflight failures (`plan.md:66-73`). It also requires a durable issue/request/event identity, notify-at-most-once behavior across replay and recovery, a single Linear link, redacted summaries, bounded idempotent delivery, status-visible delivery failure, and Linear remaining the decision source (`plan.md:68-73`).

The task breakdown makes those requirements independently implementable rather than leaving them as examples. T2 creates durable actionable events for terminal/ambiguous worker and preflight failures while classifying retryable in-budget failures as quiet (`tasks.md:34-43`). T3 emits one durable event for multiple WIP and tests notify-once classification (`tasks.md:46-56`). T4 emits and deduplicates the event for an independently actionable external prerequisite (`tasks.md:58-68`). T5 owns the complete positive taxonomy, durable identity, replay/recovery idempotency, redaction, Linear linkage, retry exhaustion/failure visibility, and status projection (`tasks.md:70-80`). Its negative matrix explicitly keeps empty queues, held leases, manual WIP, routine stages, and demonstrably transient in-budget publication or worker/preflight failures quiet, and requires fixtures for every positive and quiet case (`tasks.md:75-76`). This matches the authoritative program notification contract (`program plan:685-691`) and the final passing program re-audit.

### P2.2 — Atomic local-before-Linear claim and recovery

**Resolved.** The revised plan fixes the ordering and recovery invariant: re-read the winner; under one durable operation identity compare-and-swap the repository reservation and persistent issue-worktree mapping into a proven local prepared state before Linear; claim second; read back third; and at each injected failure either roll back only independently proven-safe local preparation or retain the original candidate in protected fail-closed recovery (`plan.md:46-55`). It expressly forbids claim-first behavior, orphaned Linear WIP, discarded ambiguous local work, and selection of a second candidate (`plan.md:54`).

T3 carries the invariant into implementation acceptance criteria and test ownership (`tasks.md:46-56`). Its fixture matrix injects failure/crash at pre-prepare, post-reservation, post-worktree-map, pre-claim, ambiguous claim response, and pre/post-readback boundaries, then asserts the durable operation identity, local-before-remote ordering, safe-only rollback, protected recovery, no orphan claim, and no second candidate (`tasks.md:51-52`). This is at least as strict as the authoritative program selection contract (`program plan:578-610`) and closes the under-specification identified by the failed audit.

## Fresh full-package audit

- **Goal, scope, and layout:** One observable SAAS-47 goal, explicit non-goals, target repository, helper-registered current artifact folder, physical-worktree binding, and merge completion boundary are present. The fixture-only boundary consistently excludes live Linear/ntfy use, migration, scheduling, GitHub publication implementation, and reimplementation of SAAS-45/SAAS-46 primitives.
- **Architecture and contracts:** Standard-library injectable transports, progressing complete pagination, bounded retries, explicit endpoint validation, GraphQL error handling, read-before/write/read-after reconciliation, stable operation IDs, schema/runtime/CLI parity, and reuse of supervisor state/journal/authority primitives are assigned to bounded tasks and focused fixtures.
- **Secrets, authority, and provider boundaries:** Secrets remain environment-only and are excluded from state, fixtures, evidence, exceptions, logs, status, and notifications. Configuration stores names/identifiers rather than values. Specialists receive no raw capability or caller-chosen authority. Linear remains the durable decision source, ntfy remains attention-only, and SAAS-48 alone consumes retry authorization for publication execution.
- **Selection, WIP, and recovery:** Global WIP reconciliation, exact autonomous resume, manual/semi quiet exit, zero-WIP-only selection, local-first eligibility, full-set deterministic ordering, winner re-read, atomic local preparation, provider claim/readback, replay/race/failure handling, protected recovery, and the one-issue/no-second-selection invariant are explicit.
- **Decisions and follow-ups:** Canonical durable identities, source ordering, configured-owner authorization, exact one-time reply consumption, decision deduplication, publication evidence preservation, exact retry grammar, inert invalid replies, one bounded achievable external prerequisite, and no speculative child for decisions/transient failures are covered.
- **Migration and observability:** The dry-run is fully paginated and mutation-free, accounts for every candidate and rejection/proposal, preserves unrelated metadata, and has deterministic report and cursor-failure fixtures. Status/events expose only redacted summaries and retain notification-delivery failure visibility without disclosing secrets or opaque authority.
- **Validation and stage separation:** Focused suites, existing supervisor compatibility tests, build-generated `dist`, the repository aggregate, independent exact-diff code review, runtime QA mapped to acceptance criteria, and durable documentation remain distinct gates. Exact approved-PR-head validation and separate clean exact-returned-merge-SHA validation satisfy the merge boundary; hosted checks are not substituted for local evidence.
- **Rollout, rollback, and residual risk:** Live activation is deferred to later integration and attended configuration/pilot work. Rollback uses a normal reviewed PR and preserves supervisor state, operation evidence, reservations, and worktrees. Provider ambiguity, pagination, credential leakage, and cross-task publication ownership have explicit mitigations. No unresolved material product, security, tenancy, billing, cost, destructive-data, or UI decision remains.
- **Contradiction check:** The plan, tasks, workflow descriptor, repository instructions, authoritative SAAS-47 program sections, final passing program re-audit, and installed canonical audit/stage/quality/completion contracts are mutually compatible. The declared merge boundary does not itself grant publication authority, and the no-live-provider implementation boundary is maintained throughout. No new contradiction or missing implementation dependency was found.

## Gate result

The pre-implementation audit gate passes. Implementation may begin only through the active workflow with a valid editing reservation and the required authority. Later code review, runtime QA, documentation, publication, merge, and exact-merge-SHA validation gates remain mandatory and separate.

## Sources consulted

- `AGENTS.md`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/workflow.json`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-plan.md`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-tasks.md`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-audit.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`, especially sections 7.3–7.10
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`, especially `DDW-AIC-003`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- Installed `goal-to-delivery/references/{artifact-contract,autonomous-runtime-contract,clarification-policy,completion-boundaries,delivery-stages,quality-gates,work-descriptor.schema.json}`
- Installed `task-audit-breakdown/SKILL.md` and `task-audit-breakdown/references/audit-checklist.md`
