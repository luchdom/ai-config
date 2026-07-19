# SAAS-46 supervisor core — Independent pre-implementation re-audit

## Verdict

**FAIL.** Revision 3 corrects the earlier release/trust, strict-envelope, artifact-registration, and clock-discontinuity findings, and it substantially improves the split-phase Handoff and semi/manual integration design. It is still not implementation-ready because one P1 authority-transfer contradiction and one P2 command-contract inconsistency remain. This audit does not authorize implementation.

## Audit target and scope

- Workflow: `1a0fa044-199b-4f57-ac46-1cc38061debb`, descriptor revision `3`, stage `audit`.
- Entry/boundary: semi-autonomous `$goal-to-delivery`, explicit `merge`.
- Audited package:
  - `2026-07-18-saas-46-supervisor-core-plan.md`
  - `2026-07-18-saas-46-supervisor-core-tasks.md`
  - prior `2026-07-18-saas-46-supervisor-core-audit.md`
  - `workflow.json`
- Exact base lock/API paths inspected:
  - `src/skills/goal-to-delivery/scripts/workflow_init.py`
  - `src/skills/goal-to-delivery/scripts/handoff.py`
  - `src/skills/goal-to-delivery/scripts/registry.py`
- Design remains correctly not required because this is local tooling with no product UI or interaction change.

## Findings

### P1 — Critical

#### P1.1 — The base-Handoff reservation interlock has no race-free, assembled-call-safe placement in the specified API

The revised plan correctly recognizes that canonical base Handoff is self-locking and defines a three-phase pending barrier (`plan`, lines 115–121 and 165–173; `tasks`, S46-07 lines 180–191). It also requires the public base Handoff to reject a live or pending supervisor reservation (`plan`, lines 170 and 185; `tasks`, lines 187 and 191).

Those two requirements are not yet assembled into an implementable authority contract:

- `WorkflowManager.workflow_managed_handoff` accepts only workflow ID, destination, and expected paths, then directly calls the base function (`workflow_init.py`, lines 388–404).
- The base function has the same inputs and unconditionally acquires the repository mutex (`handoff.py`, lines 379–402).
- That mutex is always the repository-scoped `allocation.lock` (`registry.py`, lines 121–129).
- Phase A deliberately leaves the reservation as `handoff-pending` while Phase B calls that exact base function (`plan`, lines 167–171; `tasks`, lines 185–188).

If the interlock is evaluated inside the base function's mutex, it cannot distinguish the legitimate assembled Phase-B call from a direct base call and must reject the assembled operation's own live/pending reservation. If it is evaluated only in the public CLI before the function acquires the mutex, a competing `Reserve` can win the mutex after the check and before base Handoff, after which the unchecked base function can move registry authority while a live source reservation exists. A direct Python call also bypasses a CLI-only check. Acquiring the mutex in the CLI across check-and-call is not viable because the base function acquires the same non-reentrant lock itself.

The plan/tasks define neither an engine-owned, one-shot assembled-Handoff interlock authorization bound to the pending operation nor an equivalent base API/callback that validates it inside the existing mutex. The test list covers direct-base rejection and commands during the pending phases, but not the decisive no-reservation `Reserve` versus direct-base-Handoff race or rejection of forged/replayed assembled bypass authority.

This leaves the earlier P1.1/P1.2 safety objective incomplete: the split-phase supervisor barrier is described, but the only base transfer primitive cannot both enforce the global reservation interlock and admit the legitimate assembled transition without a specified unforgeable in-lock distinction.

### P2 — Medium

#### P2.1 — The public command inventory contradicts the semi/manual authorization and renewal requirements

The architecture says the strict `EngineCommand` union includes `AuthorizeMutation` (`plan`, line 177), and semi/manual entry integration must call `Reserve`, `AuthorizeMutation`, renewal/status, `Release`, and assembled `Handoff` (`plan`, lines 181–185; `tasks`, S46-08 lines 210–217).

However, both the top-level command goal (`plan`, line 52) and the task that must implement the CLI (`tasks`, S46-07 lines 180–182) enumerate `Preflight`, `PrepareIteration`, `ApplyCheckpoint`, `Status`, `Reserve`, `Release`, `Recover`, `Cleanup`, `Handoff`, and `ReleaseLease` while omitting `AuthorizeMutation`. They also expose no explicit lease-renew command despite the renewable lease contract (`plan`, lines 123–127; `tasks`, S46-03 lines 88–95), and neither artifact assigns renewal semantics to another command.

S46-01 can define a schema branch, but S46-07's acceptance criteria do not require the CLI/supervisor implementation to dispatch it. S46-08 therefore depends on an operation its implementation task may validly omit. The corrected tasks must publish one consistent exhaustive operation set and assign exact acquire/renew/authorize/release semantics for autonomous and semi/manual callers.

## Prior-finding disposition

| Prior finding | Result | Re-audit evidence |
|---|---|---|
| P1.1 self-locking base Handoff versus supervisor lock | **Partially corrected; still fails** | Explicit three-phase pending barrier and competing-command checks now exist, but P1.1 above shows the mandatory base interlock cannot safely admit the assembled call with the current specified API. |
| P1.2 semi/manual reservation and base-Handoff bypass | **Partially corrected; still fails** | Plan §5.11 and S46-08 now assign entry/projection integration; P1.1 leaves a base-transfer bypass/deadlock-equivalent contradiction and P2.1 omits the required authorization dispatch. |
| P2.1 release/reclaim authority and observation trust | **Corrected** | Plan §5.5 and S46-01/S46-04 require engine-owned one-shot authorization, engine-observed Git state, versioned journaled observations, freshness, repository/head/PR binding, and fail-closed replay/unavailability/mismatch behavior. |
| P2.2 strict structured command/path/capability boundary | **Corrected at architecture level; implementation inventory gap is P2.1 above** | Plan §§5.10 and 6 add a discriminated strict command schema, canonical input/result roots, engine-owned authority files, no caller-selected authoritative output, and leakage/forgery tests. |
| P2.3 workflow artifact registration | **Corrected for the audited inputs** | Descriptor revision 3 inventories the revised plan, tasks, and prior audit and records stage `audit` plus pending-independent-reaudit state. This fresh artifact must be registered by the authorized workflow owner after creation and before implementation advancement. |
| P3.1 wall-clock discontinuity | **Corrected** | Plan §5.4 and S46-03 require an injected clock, backward/large-forward detection, fail-closed reconciliation, and focused tests. |

## Checklist readback

| Audit area | Result |
|---|---|
| Observable goal, non-goals, repository scope, and source evidence | Pass |
| Architecture, storage, recovery, capability secrecy, and worktree containment | Pass except the Handoff authority contradiction |
| Reservation acquire/release/reclaim trust | Fail: P1.1 and P2.1 |
| Strict command and path boundaries | Fail: P2.1 implementation inventory mismatch |
| Task ordering, dependencies, tests, review, QA, docs, rollout/rollback | Pass |
| Completion boundary, exact-head/exact-merge evidence, publication authority | Pass |
| Current artifact layout/identity | Pass for revision-3 inputs; register this fresh audit before advancement |

## Required next re-audit conditions

1. Specify a race-free in-mutex base-Handoff interlock that admits only the exact engine-prepared assembled transition, including authority lifecycle and forged/replayed/racing-call tests, without nested acquisition of `allocation.lock`.
2. Make the plan, schema task, CLI task, and entry-integration task use one exhaustive public operation inventory, including `AuthorizeMutation` and an explicit lease/reservation renewal route with exact semantics.
3. Produce and register a fresh audit artifact after those plan/task corrections. Any P1/P2 continues to fail the gate.

## Sources consulted

- `AGENTS.md`
- canonical `artifact-contract.md`, `clarification-policy.md`, `completion-boundaries.md`, `delivery-stages.md`, `quality-gates.md`, and `work-descriptor.schema.json`
- the task-audit-breakdown independent auditor checklist
- `docs-ai/002-saas-46-supervisor-reservation-permissions-recov/workflow.json`
- the revised SAAS-46 plan and tasks plus the prior audit named above
- `src/skills/goal-to-delivery/scripts/workflow_init.py`
- `src/skills/goal-to-delivery/scripts/handoff.py`
- `src/skills/goal-to-delivery/scripts/registry.py`
