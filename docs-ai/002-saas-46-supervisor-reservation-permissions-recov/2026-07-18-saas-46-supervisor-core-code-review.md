# SAAS-46 supervisor core — independent code review

## Target identity

- Review role: independent `code-reviewer`; no production code, Linear state, or Git/provider state was mutated.
- Repository: `C:\dev\luchdom\ai-config`
- Base and current checked-out `HEAD`: `e1f44b9dd3f4d281d104b4df06a94267c36eacee`
- Target: the complete tracked and untracked working-tree implementation for SAAS-46 before this review artifact was added.
- Target file manifest: 59 unique files from `git diff --name-only <base>` plus `git ls-files --others --exclude-standard`; sorted path/content digest `sha256:d714ca82863c411f369be1afad7be55dd8c8cf7466aa6f4ea223690dea8eac6b`.
- Requirements: registered plan/tasks and passing pre-implementation re-audit in this workflow folder.

## Verdict

**FAIL — 6 P1 findings and 3 P2 findings.** The implementation must not advance to QA or publication. PASS requires zero P1/P2.

## Findings

### P1-1 — Preflight executes a repository-selected arbitrary program with repository-selected inherited secrets

`Preflight` reads `configPath` from the checkout and then executes the configured probe directly (`src/skills/linear-delivery-loop/scripts/cli.py:88-102`, `src/skills/linear-delivery-loop/scripts/cli.py:116-128`). Validation accepts any absolute existing file as `probeAdapter.executable` and accepts arbitrary non-empty `fixedArgv` except for a small token blacklist (`src/skills/linear-delivery-loop/scripts/preflight.py:324-337`). The same untrusted config can add any environment variable name to `allowedInheritedVariableNames`; the secret-pattern rejection applies only to names not declared by that config, and `build_child_environment` passes every declared value to the child (`src/skills/linear-delivery-loop/scripts/preflight.py:248-252`, `src/skills/linear-delivery-loop/scripts/preflight.py:403-422`).

A checkout can therefore select an arbitrary executable/script, allow inherited `AWS_SECRET_ACCESS_KEY` (or another unrelated credential) explicitly, and have preflight execute it with that credential before authority is claimed. This contradicts S46-06's strict probe adapter and unrelated-secret denial. Pin the adapter to an engine-owned/versioned executable or exact trusted adapter identity/hash and exact argv shape; enforce a non-configurable baseline allow/deny environment policy before launching it.

### P1-2 — Every schema-valid public `WorkerResult` is incompatible with `ApplyCheckpoint`

The normative `WorkerResult` requires `outcome`, `completedStage`, and `proposedNextStage`, and forbids unknown properties (`src/skills/linear-delivery-loop/references/worker-result.schema.json:6-14`). The CLI validates that schema and passes the object unchanged (`src/skills/linear-delivery-loop/scripts/cli.py:201-210`). The state machine instead requires the mutually incompatible fields `previousStage`, `nextStage`, `worktreePath`, `physicalWorktreeFingerprint`, and `status` (`src/skills/linear-delivery-loop/scripts/lease.py:590-610`), while `expectedStage` from the `EngineCommand` is never used.

A focused probe constructed a schema-valid worker result, passed `validate_contract("worker-result", ...)`, and received `LeaseError: Checkpoint previousStage binding is mismatched` from `apply_checkpoint`. Thus the autonomous loop cannot advance even one stage through its public command surface. Align the schema, CLI translation/checkpoint contract, and state-machine bindings, and add a real wrapper/CLI success test using only schema-valid files.

### P1-3 — A reservation for workflow A does not interlock base Handoff for workflow B in the same repository

The base interlock filters active reservations by the selected `workflow_id` before deciding whether Handoff requires assembled authority (`src/skills/goal-to-delivery/scripts/reservation_interlock.py:98-113`, `src/skills/goal-to-delivery/scripts/reservation_interlock.py:126-146`). Because the reservation namespace is repository-scoped, an active reservation for another workflow is still the exclusive repository editing authority. Today a direct base Handoff for an unreserved workflow sees no match and proceeds without assembled authorization while workflow A owns the repository reservation.

This is an authority bypass of the central repository-wide exclusion guarantee. The in-mutex decision must inspect every active reservation for the repository: any active reservation must block base-only Handoff, and assembled authority must bind the sole active reservation to the selected workflow.

### P1-4 — Handoff crash/recovery treats a source registry fingerprint as proof even when the destination is partially mutated

On any base exception, assembled Handoff checks only the workflow registry fingerprint; if it still names the source, it finalizes `proven-failure` and restores source authority (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:86-95`). Recovery makes the same classification from the registry alone (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:139-155`). But base Handoff writes destination files before authority commit (`src/skills/goal-to-delivery/scripts/handoff.py:494-505`) and explicitly reports attended reconciliation when rollback is incomplete or failure evidence cannot be written (`src/skills/goal-to-delivery/scripts/handoff.py:588-622`). A process kill during apply has the same source-registry/uncertain-destination shape.

The current assembly can clear `handoff-pending`, restore live source capability/reservation, and classify the operation failed while an unprotected destination contains partial deliverables. This violates the requirement that ambiguous outcomes remain suspended/protected. Source restoration needs positive base failure and rollback/readback evidence, including exact destination reconciliation; source fingerprint alone is insufficient. Missing, incomplete, or mismatched evidence must remain ambiguous.

### P1-5 — Killed/expired runs and pending journal operations have no deterministic recovery path

`AcquireLease` rejects every existing lease, including an expired one, with an attended-reconciliation error (`src/skills/linear-delivery-loop/scripts/lease.py:101-117`), and there is no lease reclaim/reconcile operation. `RecoveryManager` only recovers paired files and lists operation directories that lack a result (`src/skills/linear-delivery-loop/scripts/recovery.py:14-36`); the public `Recover` dispatch does not reconcile an expired lease, clock discontinuity, or ordinary pending command (`src/skills/linear-delivery-loop/scripts/cli.py:257-262`). `OperationJournal.begin` then permanently refuses replay of any pending request (`src/skills/linear-delivery-loop/scripts/operations.py:46-66`, `src/skills/linear-delivery-loop/scripts/cli.py:275-286`). Although `ReservationManager.reclaim_expired` exists, it is absent from the exhaustive public command route.

After a worker is killed, or after a crash between a command's state mutation and result write, the five-minute loop cannot recover or acquire a new run; it remains wedged until manual state repair. Implement observation-based idempotent reconciliation for every pending local action and an explicit safe lease/reservation reclaim path behind `Recover`, with ambiguity remaining protected.

### P1-6 — Worktree records are not authoritative, and destructive gate cleanup trusts caller assertions

`WorktreeManager.ensure_issue_worktree` and `create_gate_worktree` only return dictionaries; no implementation persists those mappings into the existing `supervisor-state.issueWorktrees` field or an authoritative gate index (`src/skills/linear-delivery-loop/scripts/worktrees.py:191-243`, `src/skills/linear-delivery-loop/scripts/worktrees.py:278-312`). Reuse therefore requires a caller-supplied `existing_record`. More seriously, `cleanup_gate_worktree` accepts caller-provided `live_reservation`, `operation_resolved`, `attestation_complete`, and mutable record status fields, then executes destructive `git worktree remove` (`src/skills/linear-delivery-loop/scripts/worktrees.py:335-360`). The public `Cleanup` command does not call this manager or validate a gate record; it consumes an authorization and always returns `removed: []` (`src/skills/linear-delivery-loop/scripts/cli.py:131-158`).

This fails both machine-stable mapping and engine-owned cleanup authority. Persist issue and gate mappings under the supervisor mutex, derive reservation/operation/attestation facts from authoritative state, bind cleanup authorization to the exact gate/path/operation/revision, and route the public command through that contained cleanup. Caller booleans/status dictionaries must never authorize removal.

### P2-1 — The implemented operation evidence does not implement its published contract

The normative journal requires `idempotencyKey`, status/attempt count, before/after state hashes, result reference, error code, and timestamps (`src/skills/linear-delivery-loop/references/operation-journal.schema.json:6-18`). Runtime instead writes one ad hoc `request.json` with four fields and one ad hoc `result.json` with seven fields (`src/skills/linear-delivery-loop/scripts/operations.py:67-79`, `src/skills/linear-delivery-loop/scripts/operations.py:111-130`). Neither document is validated against the published contract, attempt counts and state observations are absent, and `supervisor-state.operations` remains unused. This is contract/runtime drift in the core recovery evidence. Make the authoritative persisted record conform to the schema (or revise one canonical schema and every consumer together) and validate it on every read/recovery path.

### P2-2 — Release and mutation authorizations do not enforce their advertised freshness and full scope

Release authorization records carry expiry, state revision, physical worktree, and operation bindings, but `_resolve_authorization` checks only status and nonce hash and returns a reduced binding (`src/skills/linear-delivery-loop/scripts/reservations.py:1044-1083`). `release` compares only reservation/workflow/issue/repository/run/reservation revision and never checks authorization expiry, state revision, physical-worktree binding, or operation binding (`src/skills/linear-delivery-loop/scripts/reservations.py:418-437`). Mutation authorizations have no expiry, and `Cleanup` checks only workflow/repository identity before consuming one (`src/skills/linear-delivery-loop/scripts/cli.py:144-158`).

Enforce expiry and every recorded authority binding at consumption, including exact operation, reservation revision, state revision, physical worktree, and permitted scope; consume atomically under the same mutex as the authorized mutation.

### P2-3 — Passing tests exercise internal happy paths instead of the public security boundaries

The focused suites pass, but the checkpoint test calls `LeaseManager.apply_checkpoint` with a non-schema worker object (`tests/linear_delivery_supervisor/test_checkpoints.py:32-49`), the Handoff suite covers only a reservation for the selected workflow, preflight tests do not try a config-declared secret plus arbitrary executable, and gate cleanup tests supply the authority booleans themselves. There are no tests for killed-worker lease reclamation or a Phase-B kill/rollback failure that leaves destination files changed.

Add public CLI/wrapper tests for every operation variant, cross-workflow repository reservation races, crash points with partial destination state, malicious preflight config, authoritative gate cleanup, expired/killed run recovery, and contract validation of the exact durable journal documents.

## Checks run

- `python -m unittest tests.linear_delivery_supervisor.test_checkpoints tests.linear_delivery_supervisor.test_assembled_handoff tests.linear_delivery_supervisor.test_preflight tests.linear_delivery_supervisor.test_worktrees -v` — PASS, 14 tests, 86.697 s. These results demonstrate the current coverage gap; they do not resolve the findings above.
- Focused schema/runtime checkpoint probe — schema validation PASS; runtime `ApplyCheckpoint` FAIL with `LeaseError: Checkpoint previousStage binding is mismatched`.
- Static inspection covered all new supervisor scripts/contracts/tests, the narrow base Handoff interlock, generated-entry integration sources, and registered workflow plan/tasks/audits.

## Residual risks

- Live Linear, ntfy, GitHub mutation transports and exact-SHA publication orchestration are intentional SAAS-47/48 non-goals and were not treated as defects.
- No real secret value was used or emitted during review.
- Full aggregate PASS cannot compensate for the untested public-boundary and crash-state defects above; a fresh independent review is required after repair.
