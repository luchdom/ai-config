# SAAS-48 deterministic publication and exact-SHA gates — Independent audit

## Verdict

**FAIL** — one P1 and two P2 findings. The goal is coherent and the six-task decomposition is feasible, but the current plan/tasks weaken several authoritative refusal/recovery and evidence requirements. Implementation must not begin until the planner/tasker correct them and a fresh independent audit passes.

## Findings

### P1 — Refusal and attended-recovery tasks do not preserve the complete control-plane safety state

The selected Linear issue and accepted historical source require transient and stable publication refusals to preserve the ordinary state (`In Progress` before a PR and `In Review` after), the `autonomous` label, global WIP, reservation, worktree, branch/PR and evidence; stable refusal must add `blocked + needs-human`, create/update one deduplicated Linear request, send ntfy, and release only the run lease. A successful exact attended retry must clear the two stop labels and continue from the preserved stage. Repair exhaustion must also notify.

The current plan section **Refusal and attended recovery** and task `SAAS48-05` reduce this to preserving “ordinary issue state”/WIP and a pause request. They do not require the pre-PR/post-PR state mapping, preservation of `autonomous`, addition and later clearing of `blocked`/`needs-human`, ntfy emission, or ntfy on repair exhaustion. `SAAS48-05` also does not enumerate the required attended-retry rereads of issue state/labels/authorization, physical worktree, all SHA-bound attestations, and latest provider response before consuming the one-shot operation authority.

This is a fail-closed authority defect, not a documentation nicety: loss of `autonomous` or ordinary-state/WIP semantics can make preserved work invisible to scheduled recovery, while missing stop-label behavior can allow ordinary selection or falsely represent an unresolved publication as runnable/completed.

Evidence:

- Linear `SAAS-48`, acceptance criteria for transient refusal, stable refusal, exact attended retry, and repair exhaustion.
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`, §§7.8–7.9.
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`, `DDW-AIC-004`.
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-plan.md`, architecture items 6–7.
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-tasks.md`, `SAAS48-05`.

Required correction: the planner must restore the complete state/label/notification/reread invariants in the plan; the tasker must make each invariant and its positive/negative fixture proof explicit in `SAAS48-05` and the composition task. Ownership may continue to use SAAS-47's existing request/notification boundary; SAAS-48 must deterministically invoke and verify it rather than redesign it.

### P2 — The evidence sequence omits two authoritative inputs

The accepted source requires (1) the repository aggregate to run in the issue worktree before staging as an early feedback check, without replacing the later isolated exact-head gate, and (2) draft **design when required** to be committed with plan/tasks/audit/review/QA/completion evidence before the final gated head. The current plan and tasks omit the pre-staging aggregate. Their evidence inventory omits conditional design entirely.

Declaring design unnecessary for SAAS-48's own non-UI change does not permit the reusable publication engine to omit design evidence for later product work where the canonical stage contract requires it. Without an explicit conditional member and missing-member failure test, the engine can finalize an incomplete artifact set. Without the pre-staging aggregate, the package no longer implements the accepted two-level validation order.

Evidence:

- Linear `SAAS-48`, acceptance criteria beginning “The adapter snapshots…” and “Implementation plus plan/design/tasks/audit…”.
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`, §7.8 items 3–4.
- `src/skills/goal-to-delivery/references/delivery-stages.md`, conditional design stage.
- Current plan, architecture items 2 and 5; current tasks `SAAS48-02` and `SAAS48-04`.

Required correction: the planner must restore both ordering rules; the tasker must assign the pre-staging aggregate to the manifest/Git task and require a conditional design-evidence member plus missing/required/not-required fixtures in the evidence-convergence task.

### P2 — Retry cardinality is internally ambiguous

The issue and accepted source say the adapter may **retry** the same operation/head at most three times with the 5/15/30-minute sequence (or bounded `Retry-After`). The current plan and `SAAS48-05` instead say “at most three attempts.” These are different deterministic contracts: three retries permit the initial operation plus three retries, while three attempts permit only the initial operation plus two retries and leave the third backoff slot unexplained.

Evidence:

- Linear `SAAS-48`, transient-refusal acceptance criterion.
- Historical plan §7.8.1 item 1 and historical task `DDW-AIC-004`.
- Current plan, architecture item 6; current task `SAAS48-05` first acceptance criterion.

Required correction: the planner must define one counter model explicitly (initial attempt versus retry count, persisted fields, backoff index, and exhaustion transition). The tasker must require exact boundary fixtures across crash/replay and heartbeats, including the final allowed retry and the first refused attempt after exhaustion.

## Checks that passed

- The goal and non-goals match the fixture-first, local-only phase: no hosted-check authority, CI requirement, provider-control mutation, bypass/admin merge, direct-main push, force, rebase, tag/release, auto-revert, or live autonomous activation.
- SAAS-46 and SAAS-47 are merged and expose the expected supervisor, reservation, operation-journal, gate-worktree, publication-request, exact-reply, and notification seams; the dependency order is acyclic.
- The six tasks have bounded responsibilities, one target repository, plausible source/test locations, explicit dependencies, rollback preservation, and one-primary-PR scope.
- Git manifest reconciliation, physical-worktree containment, narrow injected provider operations, before/after mutation readback, crash/replay idempotency, secret redaction, exact-SHA clean worktrees, strict evidence-delta classification, base-drift invalidation, squash-merge readback, no post-merge mutation, and three same-issue repair branches are materially covered.
- Review, QA, docs, publication and post-merge validation remain distinct gates. The active `merge` boundary is explicit; the artifact itself does not improperly grant provider or tracking authority.
- `src/` remains canonical, `dist/` generated, and the aggregate remains `python .\scripts\validate.py` with no second or hosted gate.
- The current `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/` layout is helper-registered and valid; the program artifacts under `docs-ai/001-dual-delivery-workflows-2026-07-16/` were used only as historical read fallback.

## Sources consulted

- `AGENTS.md`
- Linear issue `SAAS-48`, including relations and full description
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/workflow.json`
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-plan.md`
- `docs-ai/005-saas-48-deterministic-publication-and-exact-sha/2026-07-22-saas-48-deterministic-publication-and-exact-sha-tasks.md`
- `src/agents/auditor.md`
- `src/skills/goal-to-delivery/references/{artifact-contract,completion-boundaries,delivery-stages,quality-gates}.md`
- `src/skills/linear-delivery-loop/scripts/{contracts,control_plane,control_plane_records,operations,supervisor,worktrees}.py`
- `tests/linear_delivery_supervisor/` and `tests/linear_delivery_control_plane/`
- Installed `task-audit-breakdown` skill and independent audit checklist

