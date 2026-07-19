# SAAS-46 supervisor core — Independent pre-implementation audit

## Verdict

**FAIL.** The package is not implementation-ready because it contains two P1 findings and three P2 findings. A fresh audit artifact is required after the plan/tasks and workflow registration are corrected. This audit does not authorize implementation.

## Audit target and authority

- Workflow: `1a0fa044-199b-4f57-ac46-1cc38061debb`
- Selected issue: Linear `SAAS-46` / `DDW-AIC-002`, read directly on 2026-07-18 while it was `In Progress`
- Entry/boundary: semi-autonomous `$goal-to-delivery`, explicit `merge`
- Repository/base: `ai-config`, `main` at `e1f44b9dd3f4d281d104b4df06a94267c36eacee`
- Audited artifacts:
  - `2026-07-18-saas-46-supervisor-core-plan.md`
  - `2026-07-18-saas-46-supervisor-core-tasks.md`
- Design: correctly recorded as not required because the change has no product UI or interaction surface.
- Bootstrap exception: correctly limited to the attended root orchestrator for this engine-building issue; specialists receive no Linear/GitHub publication authority.

## Findings

### P1 — Critical

#### P1.1 — The assembled-Handoff lock choreography is incompatible with the only base Handoff API and does not define a concurrency-safe split-phase alternative

The focused plan says all supervisor commands mutate under the base repository mutex (`plan`, §5.3) and describes assembled Handoff as running “under the supervisor/base mutex” before invoking canonical base `workflow_managed_handoff` (`plan`, §5.9 steps 1–4). `S46-07` repeats that the assembled command journals pending, invokes the canonical base Handoff once, and then transfers reservation/capability authority.

The merged SAAS-45 implementation does not expose a caller-held-lock variant. `src/skills/goal-to-delivery/scripts/handoff.py:402` unconditionally acquires `source.registry.mutex()` itself; `src/skills/goal-to-delivery/scripts/registry.py:124-129` points every such mutex to the same `allocation.lock`; and `src/skills/goal-to-delivery/scripts/mutex.py:34-36` explicitly rejects re-entry on an instance while another instance contends on the same OS byte lock. Holding the base mutex around the call therefore deadlocks/times out on Windows. Releasing it before the call creates an observable interval in which the registry can move while the reservation/capability still authorizes the source.

The crash-recovery language is not enough to close that interval: neither the plan nor `S46-07` requires every competing supervisor command to detect the pending assembled operation and reconcile or stop before reading/using authority, and the test list covers crash boundaries but not a concurrent renew/checkpoint/reserve/base-Handoff attempt in each split phase. The promised atomic source revocation and destination authority cannot be implemented from the stated choreography without either a compatible canonical base API or an explicit split-phase protocol with a mandatory pending-operation barrier on every authority-bearing command.

This violates Linear SAAS-46’s live-reservation Handoff acceptance, the canonical completion-boundary rule that a reservation survives until a valid workflow-managed Handoff, and the program regression obligation in `2026-07-17-three-delivery-workflows-tasks.md:490-499`.

#### P1.2 — Semi-autonomous and manual delivery have no enforceable route to the reservation engine, and the existing public base-Handoff route can bypass assembled transfer

SAAS-46 requires one repository reservation namespace to cover autonomous, semi-autonomous, and manual repository-deliverable mutation. The focused plan makes this Goal 5 and `S46-04` tests the three policies. However, all proposed runtime/command work is under `src/skills/linear-delivery-loop/`, while `S46-08` updates only the `linear-delivery-loop` entry skill plus docs/build contracts.

The currently merged user-facing entries prove the gap:

- `src/skills/goal-to-delivery/SKILL.md:44` requires a reservation before edits, but its documented deterministic CLI at `:60-63` has only `init`, `resume`, `attach`, and the registry-only base `handoff`.
- `src/skills/spec-driven-delivery/SKILL.md:18` exposes `Reserve` and `Release`, and `:48` requires a reservation for deliverable mutation, but `:55` documents only base workflow initialization and provides no deterministic reservation command.
- `src/skills/goal-to-delivery/SKILL.md:63` will continue to route Handoff directly to the SAAS-45 registry-only CLI, which intentionally reports `reservationTransferred: false`; the focused task package contains no change that reroutes a live reservation through the assembled command or rejects a base-only transfer while such a reservation exists.

Unit-testing a reservation manager with a `policy` enum does not make the existing semi/manual workflows acquire, renew, release, or transfer it. After the planned change, those entries could still edit without deterministic reservation enforcement, and the documented base Handoff could move registry authority while leaving live reservation authority on the source. That defeats the global WIP/race safety goal and makes the assembled acceptance path optional rather than authoritative.

The plan/tasks must assign explicit source integration and semantic tests for `$goal-to-delivery` and `$spec-driven-delivery` (and their generated projections) so all repository-deliverable mutations fail closed without the common reservation, and so a live-reservation Handoff can use only the assembled transition.

### P2 — Medium

#### P2.1 — Release/reclaim authority and external-observation trust are asserted but not specified

`plan` §5.5 says `Release` needs “explicit authority” and clean planning reclaim uses “supplied external-observation reconciliation”; `S46-04` repeats the rule but defines neither an unforgeable authority mechanism for semi/manual owners nor a trusted source, freshness window, repository/head binding, and replay rule for the supplied observation. The seven schemas in `plan` §6 contain no release/reclaim request or external-observation envelope. Tests mention wrong source fingerprint and protected summary bits, but not forged owner/run identifiers, model-supplied clean/closed-PR assertions, stale provider observations, observation replay, or observation/repository/head disagreement.

Owner/run strings and a caller-provided clean summary are not authority. This is especially important before SAAS-47/48 provide live Linear/GitHub transports: an unavailable trusted PR observation must remain `ambiguous` and protected, not become releasable. The corrected contract needs a deterministic one-shot authority for manual/semi Release (or a strictly attended boundary) and must distinguish engine-observed Git facts from versioned adapter-attested external facts. Unknown, stale, unavailable, caller/model-authored, or mismatched evidence must fail closed.

#### P2.2 — The structured command surface lacks a complete versioned request contract and containment/trust boundary

`plan` §5.10 and `S46-07` expose ten state-changing/read operations through structured input/output files, but `plan` §6 and `S46-01` define schemas only for project config, prepared iteration, checkpoint, supervisor state, editing reservation, operation journal, and worker result. There is no discriminated command/request schema for `Reserve`, `Release`, `Recover`, `Cleanup`, `Handoff`, `ReleaseLease`, or `Status`, and no exact rule identifies which input/output paths must be inside machine state, which actor creates them, or which fields are untrusted proposals versus authority-bearing adapter data.

This omission conflicts with Linear’s requirement that the commands never trust model-supplied identity/authority. It also leaves capability handling underspecified: the raw nonce is promised to exist only in authoritative run/prepared files (`plan` §4 and §5.4), while `ApplyCheckpoint` must receive and consume it, but no command-envelope rule prevents a nonce-bearing input/result from being written in a checkout, patch, artifact, or caller-chosen output path. `S46-07` mentions a generic path-escape test but does not define the allowed root or secret-bearing file lifecycle.

A corrected public contract must enumerate exact fields for every operation, reject unknown fields, bind request/response paths to approved state roots, keep raw capabilities out of worker-authored/public files, and test forged identity/authority plus nonce leakage through every command boundary.

#### P2.3 — The plan and task artifacts are not registered in the active workflow descriptor

The current `workflow.json` still has `currentArtifactStage: "initialized"` and `artifactInventory: ["workflow.json"]`, even though the plan and tasks being audited already exist in its folder. The canonical `artifact-contract.md` requires descriptor-registered exact artifact paths and stage metadata for current work, and the audit checklist requires current artifact-layout/identity integrity.

This makes the claim that these are the registered focused plan/tasks false at audit time and leaves exact resume/evidence navigation incomplete. The deterministic descriptor/registry pair must be advanced atomically to include the plan, tasks, and eventual fresh audit artifact before implementation approval; the auditor must not repair `workflow.json` or registry state.

### P3 — Low / implementation precision

#### P3.1 — Lease tests do not cover wall-clock discontinuity

The plan chooses UTC nanosecond timestamps and tests expiry boundary timestamps, killed owners, and ambiguity, but it does not require an injected clock or backward/forward wall-clock jump cases. A large forward jump can make a still-running lease appear expired; a backward jump can extend it unexpectedly. Because expiry never grants takeover by itself, this is not currently a P1/P2, but the lease contract should use an injected time source and prove that clock discontinuity enters reconciliation/fail-closed behavior without concurrent authority.

## Checklist readback

| Audit area | Result | Evidence |
|---|---|---|
| One achievable goal and non-goals | Pass | `plan` §§1–3; Linear SAAS-46 |
| Repository/user precedence and local-only scope | Pass | `AGENTS.md`; `plan` §§3–4; no CI/provider mutation/scheduled-task scope |
| Current-state/base evidence | Pass with registration failure above | `plan` §2; merged base modules and tests; P2.3 |
| Architecture/storage/recovery | Fail | P1.1; P2.2 |
| Secret/capability handling | Fail | P2.2; redaction goals/tests are otherwise comprehensive |
| Reservation acquisition/release | Fail | P1.2; P2.1 |
| Worktree containment and cleanup | Pass | `plan` §§5.6, 5.7, 10; `S46-05`/`S46-07` include direct-child, reparse, protected-state, and cleanup tests |
| Mutation-free preflight scope | Pass | `plan` §5.8; `S46-06` separates fixture/read-only probes from target/external mutation and tests every denial |
| Assembled Handoff atomicity | Fail | P1.1 and P1.2 |
| Task ordering/ownership | Pass except routed-entry omissions | `S46-01`–`S46-10` dependency graph; P1.2 |
| Independent audit/review/QA/docs gates | Pass | `plan` §8; `S46-09`; canonical quality gates |
| Bootstrap reservation exception | Pass | `plan` §4 and `tasks` Status and authority; program tasks `:501-529` |
| Rollout/rollback | Pass | `plan` §11 preserves protected state and uses a separate authorized repair after merge |
| Merge-boundary evidence | Pass | `plan` §8 and `S46-10` require clean exact PR-head and exact returned merge-SHA local aggregates, no hosted-check authority, and no post-merge repository mutation |

## Required re-audit conditions

A new audit may pass only after a new plan/task revision:

1. defines an implementable assembled-Handoff lock/state choreography against the actual non-reentrant base API and tests concurrent commands in every split phase;
2. integrates the common reservation and assembled Handoff into the semi/manual entry surfaces and generated projections, not only autonomous modules;
3. defines Release/reclaim authority and trusted, fresh external-observation semantics;
4. publishes complete strict request/path/secret boundaries for every structured command; and
5. atomically registers the corrected artifacts in the active workflow descriptor/registry.

## Sources consulted

- `AGENTS.md`
- Linear issue `SAAS-46`, including acceptance, test notes, dependencies, and non-goals
- `README.md`
- `src/skills/goal-to-delivery/SKILL.md`
- `src/skills/spec-driven-delivery/SKILL.md`
- `src/skills/linear-delivery-loop/SKILL.md`
- `src/skills/goal-to-delivery/references/{delivery-stages,artifact-contract,clarification-policy,quality-gates,completion-boundaries}.md`
- `src/skills/goal-to-delivery/references/work-descriptor.schema.json`
- `src/skills/goal-to-delivery/scripts/{__init__,identity,state_home,state_paths,mutex,registry,workflow_init,handoff,redaction,atomic_files,descriptor}.py`
- `tests/goal_to_delivery_base/`
- `validation/manifest.json`
- `scripts/validate.py`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- `docs-ai/002-saas-46-supervisor-reservation-permissions-recov/workflow.json`
- `docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-plan.md`
- `docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-tasks.md`
