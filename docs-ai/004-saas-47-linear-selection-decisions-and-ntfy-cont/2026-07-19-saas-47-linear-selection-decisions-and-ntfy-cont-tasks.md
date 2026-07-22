# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Execution Tasks

## Status and authority

- Workflow: semi-autonomous selected issue `SAAS-47`; target repository: `ai-config`.
- Completion boundary: authorized squash merge, preceded by clean local validation at the exact PR head and followed by the aggregate validation from a separate clean worktree at the exact returned merge SHA.
- This task artifact grants no Linear, ntfy, GitHub, branch, commit, push, PR, or merge mutation authority. Implementation must acquire and use the supervisor editing reservation and per-mutation authorization prescribed by the active entry.
- Design is not required: this is a fixture-backed transport/control-plane and documentation change with no product UI or interaction change.
- The implementation remains disabled from live autonomous use. `LINEAR_API_KEY` may be read only by runtime code from the process environment; ntfy values remain intentionally unconfigured and no live provider call is in scope.

## Audit notes

- Light completeness check: the plan identifies the provider contracts, deterministic selection and reconciliation rules, failure/rollback posture, focused fixture coverage, docs impact, and exact merge validation gates. No material product, security, tenancy, billing, cost, destructive-data, or UI decision remains unresolved for tasking.
- The public engine operation names and schema shapes for tracking are deliberately not fixed in the plan. Task 2 must make the smallest explicit, schema/runtime-parity-compatible choice and document it; it must not add an open-ended command or raw authority input.
- The configured Linear owner, workspace/project/repository IDs, ordinary state IDs, labels, and endpoint policy need fixture-backed configuration values before mutation-capable paths can be tested. Missing, duplicate, drifting, or incompatible observations must fail closed rather than becoming defaults.
- The independent auditor must verify all acceptance criteria against the plan and this breakdown, especially no secret/authority leakage, complete pagination, race safety, the no-live-provider boundary, and the exact-head/exact-merge-SHA gates. These notes are not an independent audit or a PASS verdict.

## Dependency graph

`T1 contracts + transport` → `T2 configuration/preflight + composition` → `T3 selection/WIP` and `T4 decisions/follow-ups` → `T5 ntfy + migration/status` → `T6 integration tests, durable docs, generated projections, and merge evidence`.

### T1 — Define redacted provider transport and durable control-plane contracts

- Goal: Add standard-library, dependency-injected Linear and ntfy transport primitives plus strict schemas/records that make retries, pagination, reconciliation, idempotency, redaction, and fail-closed error classification testable without network access.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: new `src/skills/linear-delivery-loop/scripts/linear_transport.py`, `ntfy_transport.py`, `control_plane_records.py`, and shared redaction helpers; new schemas under `src/skills/linear-delivery-loop/references/` for tracking configuration, durable requests/notifications, and migration report records; new `tests/linear_delivery_control_plane/test_linear_transport.py`, `test_ntfy_transport.py`, `test_control_plane_records.py`, and fixture JSON beneath `tests/linear_delivery_control_plane/fixtures/`.
- Acceptance criteria: Linear uses GraphQL variables, an allowed configured endpoint, explicit timeout, bounded retry/backoff, and an environment-supplied API key that never enters state, fixture, evidence, exception, or log output. It follows pagination only while a non-empty cursor progresses and stops only at `hasNextPage: false`. Redirect/host drift, malformed payload, GraphQL `200` errors, 429, retryable 5xx, non-retryable failure, and ambiguous write/readback have distinct fail-closed outcomes. Writes support stable operation IDs with read-before/write/read-after reconciliation. ntfy delivery uses an injectable request/sleep/clock interface, bounded retry, redacted payload construction, and an outcome model that callers can persist idempotently.
- Local test and runtime QA notes: Fixture tests cover wrong/missing key resolution, allowed-host rejection, redirect/host drift, GraphQL errors, cursor missing/repeated, all retry classes and retry exhaustion, ambiguous mutation reconciliation, and secret-sentinel scans of returned/evidenced values. Run `python -m unittest discover -s tests\\linear_delivery_control_plane -p test_linear_transport.py -v` and the matching ntfy/record tests during development; no live Linear or ntfy request is permitted.
- Documentation impact: Add concise contract/reference material defining endpoint/key handling, provider error classes, redaction, operation identifiers, and fixture-only use. Do not copy the canonical delivery protocol.
- Dependencies / blocks: None; this task establishes the interfaces consumed by T2–T5. It must reuse SAAS-46 state/journal primitives rather than reimplementing them.
- Risks and non-goals: Incorrectly serializing a secret or treating a 200 response as success would weaken the safety model. This does not configure credentials, publish a notification, or modify a live Linear issue.
- Completion/publication boundary: Working-tree code and focused tests only; any commit/PR/merge remains subject to the workflow boundary and later exact-SHA gates.

### T2 — Add schema-validated tracking configuration, preflight, and explicit supervisor composition

- Goal: Bind the transport/control-plane contracts to the existing SAAS-46 supervisor through narrow, schema-validated configuration and explicitly registered handlers, without weakening the public command union, repository identity, journal, reservation, or authority rules.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: new `src/skills/linear-delivery-loop/scripts/tracking_config.py`, `tracking_preflight.py`, and `control_plane.py`; extend only as required `src/skills/linear-delivery-loop/scripts/cli.py`, `supervisor.py`, `contracts.py`, and `src/skills/linear-delivery-loop/references/engine-command.schema.json`; new/extended configuration schemas in `src/skills/linear-delivery-loop/references/`; focused `tests/linear_delivery_control_plane/test_tracking_config.py`, `test_tracking_preflight.py`, `test_control_plane_composition.py`, and preflight fixtures.
- Acceptance criteria: Configuration contains only identifiers, endpoint/topic policy, environment-variable names, and compatible supervisor/version requirements—never secret values. Preflight read-verifies workspace, `SAAS` team, project, owner, ordinary states, labels, repository key, Linear endpoint, ntfy policy, and supervisor compatibility before any claim or mutation. It reports redacted evidence and fails closed for missing/ambiguous/wrong observations, invalid endpoint/config, unavailable key, or incompatible supervisor. An actionable terminal or ambiguous worker/preflight failure creates one durable attention event consumed by T5; retryable in-budget failures remain quiet. New operations (if any) are an exact closed schema/runtime/CLI union, receive engine-owned result paths and operation journals, and do not accept raw capabilities, caller-selected authority, or arbitrary network commands.
- Local test and runtime QA notes: Run focused config/preflight/composition tests for wrong workspace/team/project/owner/state/label/repository, missing or malformed configuration, key-name versus key-value handling, unsupported command fields, journal replay, supervisor compatibility, and actionable-versus-transient worker/preflight event classification. Re-run `python -m unittest discover -s tests\\linear_delivery_supervisor -v` for compatibility after command/handler changes.
- Documentation impact: Extend the supervisor reference with the tracking adapter boundary, required redacted configuration shape, and preflight guarantee; document that configuration is fixture-backed and live use is disabled.
- Dependencies / blocks: Requires T1 contracts and transport. Downstream selection and records may not bypass this preflight or directly construct supervisor authority.
- Risks and non-goals: Schema/CLI parity drift or an implicit operation could create an unauditable authority surface. This task does not select a queue item or mutate Linear/ntfy.
- Completion/publication boundary: Working-tree code and local tests only; no provider/Git publication.

### T3 — Implement deterministic WIP reconciliation and one-issue autonomous selection

- Goal: Implement pure, fully observed queue classification and deterministic candidate ordering, then safely bind selection/re-read/claim to the existing lease, reservation, worktree, and journal model.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: new `src/skills/linear-delivery-loop/scripts/selection.py` and `wip_reconciliation.py`; extend `control_plane.py` and only required command/schema surfaces from T2; focused `tests/linear_delivery_control_plane/test_selection.py`, `test_wip_reconciliation.py`, `test_selection_claim.py`, and queue/reservation fixtures.
- Acceptance criteria: The implementation fully paginates observations before classification; counts `In Progress` and `In Review` globally; fails closed on multiple WIP and emits one durable actionable attention event; remains quiet for manual/semi WIP; resumes only exact autonomous WIP; and selects only at zero WIP. Eligible issues are local-first achievable code leaves in `Todo + autonomous` with no parent, broad/cross-repository/incomplete/external scope, or stop/external/refinement label. Fully filtered candidates sort by Linear priority, oldest `createdAt`, then numeric issue identifier. It rereads the winner immediately before mutation. Under one durable operation identity it compare-and-swaps the repository reservation plus persistent issue-worktree mapping to an authoritative prepared state first, performs the Linear claim second, and reconciles provider readback third. Local preparation failure performs no claim; claim/readback failure rolls back only independently proven-safe preparation, otherwise protects the original mapping/WIP for recovery. Every interruption or ambiguous boundary fails closed without claim-first behavior, orphaned WIP, discarded protected state, or a second candidate. User-selected manual/semi work removes `autonomous` only after exact matching lease/reservation reconciliation and otherwise makes no artifact/issue mutation.
- Local test and runtime QA notes: Fixture matrices prove every rejection reason, empty queue, complete pagination, ordering ties, manual WIP, exact autonomous resume, multiple-WIP notify-once classification, selection re-read drift, stale state/reservation revisions, journal replay, and claim races. Inject failure/crash at pre-prepare, post-reservation, post-worktree-map, pre-claim, ambiguous claim response, and pre/post-readback; assert durable operation identity, local-before-remote ordering, safe-only rollback, protected recovery, no orphan claim, and no second candidate. Run the selection-focused suite and relevant existing reservation/lease/worktree/recovery tests; all provider observations remain injected fixtures.
- Documentation impact: Document the eligibility/rejection taxonomy, WIP precedence, ordering tie-breakers, re-read-before-claim rule, and quiet outcomes in the control-plane reference.
- Dependencies / blocks: Requires T1 and T2. T4/T5 may consume reconciled state but may not cause a second candidate selection.
- Risks and non-goals: Pagination or classification shortcuts can violate one-issue/WIP safety. This does not migrate statuses, delete labels, or turn autonomous use on.
- Completion/publication boundary: Working-tree code and local tests only; no live queue claim, GitHub action, or provider publication.

### T4 — Persist and reconcile decisions, publication retries, and bounded follow-up proposals

- Goal: Add deterministic durable records and reconciliation for incomplete/external work, material decisions, authorized publication-retry requests, and the single permissible independently actionable prerequisite proposal.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: new `src/skills/linear-delivery-loop/scripts/decisions.py`, `follow_ups.py`, and `publication_requests.py`; extend `control_plane_records.py`, `control_plane.py`, related schemas, and status projection in `supervisor.py` only where needed; focused `tests/linear_delivery_control_plane/test_decisions.py`, `test_follow_ups.py`, `test_publication_requests.py`, and record/reply fixtures.
- Acceptance criteria: Durable records carry canonical IDs, source timestamps, redacted evidence, actor authorization, links, and consumed markers. Incomplete goals create deterministic `Backlog + needs-refinement` proposals; deferred provider work creates `Backlog + external-integration`; material product/security/cost ambiguity creates exactly one deduplicated `Backlog + needs-human` request with options, consequences, recommendation, and exact reply syntax. Only a newer exact reply by the configured owner is consumed once. Publication refusals preserve existing issue/WIP/reservation/worktree/branch/PR evidence and recognize only `RETRY-PUBLICATION <operation-id> <head-sha>` after reconciliation; malformed, stale, unauthorized, duplicate, or early replies are inert. A valid reply emits one idempotent SAAS-48 retry authorization and does not execute publication. Transient failures stay on the existing issue; at most one deduplicated child proposal is allowed only for a separately actionable achievable external prerequisite, and that blocker emits one durable actionable attention event. Decisions create no speculative child.
- Local test and runtime QA notes: Fixture tests cover authorization, reply ordering/replay, consumed markers, deduplication, exact retry parsing, stale head/operation rejection, retained metadata, refinement/external labels, external prerequisite eligibility plus attention-event deduplication, and no-child behavior for decisions/transient errors. Run applicable existing journal/status/reservation suites to confirm records do not disclose opaque authority.
- Documentation impact: Add a concise operator/reference section for decision lifecycle, reply grammar, deduplication, follow-up limit, and the SAAS-48-only publication boundary.
- Dependencies / blocks: Requires T1–T3. The configured owner and required Linear identifiers must pass T2 preflight before any mutation-capable reconciliation.
- Risks and non-goals: Accepting loose reply syntax, losing evidence, or generating speculative work changes authority/product intent. This task never performs a GitHub retry, PR action, or creation of a live speculative ticket.
- Completion/publication boundary: Working-tree code and fixture tests only; retry output is an authorization record for SAAS-48, not publication.

### T5 — Add idempotent ntfy attention handling, migration dry-run, and redacted status observability

- Goal: Deliver the remaining attention/reporting control-plane paths while preserving Linear as the durable source of truth and keeping routine or transient states silent.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: new `src/skills/linear-delivery-loop/scripts/notifications.py` and `migration_report.py`; extend `ntfy_transport.py`, `control_plane.py`, `supervisor.py`, control-plane schemas/references, and focused `tests/linear_delivery_control_plane/test_notifications.py`, `test_migration_report.py`, `test_status_projection.py` with fixtures.
- Acceptance criteria: Notification state is durable and keyed by issue/request/event identity. Every actionable unattended event—material `needs-human` decision, independently actionable external blocker, multiple-active-issue reconciliation failure, stable/exhausted/ambiguous publication refusal, and actionable worker/preflight failure—generates at most one redacted notification linked to its single durable Linear request/evidence record. Delivery is retry-bounded/idempotent across replay and recovery; failure is visible in status without supplanting Linear. Empty queue, held lease, manual WIP, routine stages, and publication retries or worker/preflight failures demonstrably still transient and within budget are silent. Migration dry-run fully paginates and performs no mutation, reporting every observed candidate, rejection reason, and deterministic ordinary-state/label proposal while preserving unrelated labels/metadata. Status/events expose only redacted pending-decision, publication-request, external-blocker, reconciliation-failure, worker/preflight-failure, and notification summaries and never authority references or secrets.
- Local test and runtime QA notes: Fixture tests exercise every positive trigger and every quiet state, notify-once behavior across replay/recovery, idempotent retry, exhaustion/failure visibility, redaction/link construction, migration complete pagination/repeated cursor rejection, deterministic report ordering, mutation-free request assertions, and status secret/authority sentinel assertions. No live ntfy publish or Linear migration is allowed.
- Documentation impact: Document ntfy as attention-only, the quiet-state policy, notification retry/visibility behavior, and migration dry-run interpretation/limitations.
- Dependencies / blocks: Requires T1–T4. Uses the records and preflight contracts rather than storing duplicate state outside the supervisor-controlled location.
- Risks and non-goals: Notification duplication or leaked state can create alert fatigue or disclose secrets; an incomplete dry-run can mislead operators. This task does not configure ntfy, schedule a process, or run a live migration.
- Completion/publication boundary: Working-tree code and fixture tests only; no live notification/migration/Git provider operation.

### T6 — Verify integration, publish durable guidance, generate projections, and prepare exact-SHA merge evidence

- Goal: Integrate the focused suite into repository-local validation, update durable documentation, generate `dist/` from canonical sources, and record the reproducible pre- and post-merge validation requirements without manufacturing a separate publication change.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: `README.md`; relevant canonical references under `src/skills/linear-delivery-loop/references/`; `tests/linear_delivery_control_plane/`; generated `dist/` projections emitted by `scripts/build.py`; `validation/manifest.json` only if the existing fixed aggregate cannot discover the focused tests without a minimal safe manifest change; no standalone publication script or live-provider configuration.
- Acceptance criteria: Canonical references and README accurately explain the fixture-only, disabled-live control plane, configuration/preflight, selection/WIP, decision/retry, ntfy, migration, rollback, and SAAS-48/SAAS-54 boundaries without duplicating the canonical delivery protocol. `python .\\scripts\\build.py` regenerates all required projections from `src/`; no hand-edited generated file remains. Focused tests plus `python .\\scripts\\validate.py` pass. Before authorized squash merge, run the aggregate from a fresh clean worktree at the exact approved PR head and retain redacted command/exit-code/head evidence. After the returned squash merge SHA is known, run the same aggregate from another fresh clean worktree at that exact SHA and retain redacted evidence; a dirty/mismatched checkout or missing exact identity fails the boundary.
- Local test and runtime QA notes: Run `python -m unittest discover -s tests\\linear_delivery_control_plane -v`, `python -m unittest discover -s tests\\linear_delivery_supervisor -v`, `python .\\scripts\\build.py`, and `python .\\scripts\\validate.py`. Independent code review and runtime QA must map all workflow acceptance criteria to the exact implementation; their separate artifacts are prerequisites, not replacements for these checks.
- Documentation impact: This is the durable-docs task. Update canonical `src/` references and README, regenerate matching `dist/` output, and keep per-work execution evidence in the registered `docs-ai` folder rather than copying it into reusable docs.
- Dependencies / blocks: Requires T1–T5 and passing independent audit before implementation, then separate code-review, QA, documentation verification, and explicit merge authority. The existing aggregate already discovers `tests/test*.py`; prefer it unchanged unless evidence proves a minimal canonical change is necessary.
- Risks and non-goals: Treating hosted checks, unverified provider responses, or a local run at another commit as merge evidence is invalid. This task does not itself commit, push, open a PR, merge, configure CI, or publish to any provider.
- Completion/publication boundary: Stop after the task artifact/worktree gates unless the active orchestrator has explicit publication and merge authority. Merge completes only after authorized squash merge and clean aggregate validation at the exact returned merge SHA.

## Sources consulted (paths)

- `AGENTS.md`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/workflow.json`
- `docs-ai/004-saas-47-linear-selection-decisions-and-ntfy-cont/2026-07-19-saas-47-linear-selection-decisions-and-ntfy-cont-plan.md`
- `README.md`
- `src/skills/goal-to-delivery/references/artifact-contract.md`
- `src/skills/goal-to-delivery/references/delivery-stages.md`
- `src/skills/goal-to-delivery/references/quality-gates.md`
- `src/skills/goal-to-delivery/references/completion-boundaries.md`
- `src/skills/linear-delivery-loop/references/supervisor-core.md`
- `src/skills/linear-delivery-loop/references/engine-command.schema.json`
- `src/skills/linear-delivery-loop/scripts/cli.py`
- `src/skills/linear-delivery-loop/scripts/contracts.py`
- `src/skills/linear-delivery-loop/scripts/supervisor.py`
- `tests/linear_delivery_supervisor/`
- `validation/manifest.json`
- `scripts/validate.py`
- `C:/Users/lucas/.codex/skills/task-audit-breakdown/SKILL.md`
- `C:/Users/lucas/.codex/skills/task-audit-breakdown/references/task-template.md`
