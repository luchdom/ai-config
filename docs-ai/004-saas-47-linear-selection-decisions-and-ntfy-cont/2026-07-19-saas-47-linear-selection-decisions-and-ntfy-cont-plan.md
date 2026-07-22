# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Plan

## Status and authority

- Workflow: semi-autonomous, selected issue `SAAS-47`
- Repository: `ai-config`
- Completion boundary: squash merge plus clean validation of the exact returned merge SHA
- Design: not required; this is a transport/state-machine and documentation change with no product UI
- External boundary: fixture-backed implementation only. This delivery does not migrate the live backlog, publish to ntfy, configure a scheduled task, or implement GitHub publication.

## Goal

Add deterministic, fixture-compatible Linear tracking, queue selection, decision/follow-up, migration-dry-run, and ntfy attention behavior on top of the SAAS-46 supervisor. The engine must preserve one-issue/WIP and reservation authority, keep specialists mutation-free, and expose stable interfaces for SAAS-48 publication recovery.

## Non-goals

- Live backlog/status/label migration or deletion of a Linear status
- Live ntfy configuration or attended publish
- Git, GitHub, PR, merge, hosted-check, repair, SaaS wrapper, scheduler, or product-feature implementation
- Reimplementation of repository identity, state home, mutex, registry, lease, reservation, worktree, journal, or recovery primitives
- Inferring product/security/cost decisions or creating speculative follow-up issues

## Current state and constraints

- SAAS-46 provides dependency-free Python supervisor modules, schema validation, revisioned state, operation journals, reservations, authorization, preflight, recovery, and persistent worktrees under `src/skills/linear-delivery-loop/scripts/`.
- The public engine command union is exact and schema/runtime parity is enforced. New tracking behavior must compose behind explicit handlers/contracts without weakening existing operations or duplicating supervisor primitives.
- `LINEAR_API_KEY` is already available to the attended environment, but code may read it only from the process environment and may never serialize or log it. ntfy environment values are intentionally absent because live publication belongs to SAAS-54.
- `scripts/validate.py` and `validation/manifest.json` are the authoritative local aggregate. No hosted check is evidence.

## Architecture and contracts

### 1. Provider-neutral transport boundary

Add a small transport package beside the existing supervisor modules, implemented with the Python standard library and injectable request/sleep/clock dependencies for deterministic tests.

- Linear requests use GraphQL variables, bounded retry/backoff, explicit timeout and allowed endpoint validation.
- Pagination continues until `pageInfo.hasNextPage` is false and requires a progressing non-empty cursor.
- HTTP failures, GraphQL `200` responses with `errors`, `429`, retryable `5xx`, redirects/host drift, malformed payloads, and ambiguous writes have distinct fail-closed outcomes.
- Mutations use read-before/write/read-after reconciliation and stable idempotency/operation identifiers; ambiguous results never cause duplicate mutation.
- The transport accepts the API key as a call dependency resolved from `LINEAR_API_KEY`; the key is excluded from request evidence, exceptions, state, fixtures, and logs.

### 2. Configuration and preflight

Introduce schema-validated tracking/notification configuration containing identifiers and environment-variable names, never secret values. Preflight resolves and read-verifies the configured workspace, team `SAAS`, project, owner, ordinary states, labels, repository key, Linear endpoint, ntfy endpoint/topic policy, and supervisor compatibility before any mutation or queue claim.

### 3. WIP reconciliation and deterministic selection

Build pure classification/ordering functions over fully paginated observations, then bind them to the supervisor reservation interface.

- Reconcile pending decisions/publication requests and repository reservations before ordinary selection.
- Count `In Progress` and `In Review` globally. Multiple active issues fail closed; manual/semi WIP exits quietly; exact autonomous WIP resumes; only zero WIP may select.
- Eligible candidates are bounded, local-first, achievable code leaves in `Todo + autonomous`, with no stop/external/refinement labels and no parent, broad, cross-repository, incomplete, or external-integration scope.
- Sort the fully filtered set by Linear priority, oldest `createdAt`, then numeric issue identifier.
- Re-read the selected candidate immediately before mutation. Under one durable operation identity, compare-and-swap the repository reservation and persistent issue-worktree mapping to a proven local prepared state **before** the Linear claim. Claim second, then read back provider state. Injected failure at local prepare, provider claim, and provider readback must either roll back only independently proven-safe local preparation or enter fail-closed recovery with the original candidate protected; no path may claim first, orphan Linear WIP, discard ambiguous local work, or select a second candidate.
- User-selected manual/semi work may remove `autonomous` only after exact lease/reservation reconciliation; conflicting authority fails before artifact or issue mutation.

### 4. Issue contract, decisions, and follow-ups

Define schema-validated durable records with canonical IDs, source timestamps, actor authorization, consumed markers, links, and redacted evidence.

- Incomplete goals produce a deterministic `Backlog + needs-refinement` proposal; deferred provider work produces `Backlog + external-integration`.
- Material product/security/cost ambiguity produces one deduplicated `Backlog + needs-human` decision request with options, consequences, recommendation, and exact reply syntax. Only a newer exact reply by the configured owner is consumed once.
- Publication refusal records preserve the existing issue/WIP/reservation/worktree/branch/PR evidence and parse only `RETRY-PUBLICATION <operation-id> <head-sha>`. Malformed, stale, unauthorized, duplicate, or pre-reconciliation replies are inert. A valid reply yields one idempotent retry authorization for SAAS-48; it does not execute publication here.
- Transient failures stay on the original issue. Only a separately actionable, achievable external prerequisite may yield one deduplicated child proposal. Decisions do not yield speculative tasks.

### 5. ntfy attention channel

Add an injectable ntfy transport and durable notification state keyed by issue/request/event identity.

- Notify every actionable unattended state: material `needs-human` decisions, independently actionable external blockers, multiple-active-issue reconciliation failures, stable/exhausted/ambiguous publication refusal, and actionable worker or preflight failures. Each logical request/event notifies at most once even across replay or recovery.
- Notifications link to the single Linear request and contain only redacted summaries.
- Delivery is retry-bounded and idempotent. Failure remains visible in supervisor status without replacing Linear as the decision source.
- Empty queue, held lease, manual WIP, routine stages, and demonstrably transient publication retries still within budget remain quiet.

### 6. Migration dry-run and observability

Add a fully paginated, mutation-free migration report that lists every observed candidate, rejection reason, and proposed ordinary-state/label action. Extend supervisor status/events with redacted pending-decision, publication-request, and notification summaries without exposing authority references or secrets.

## Likely files

- New Python modules under `src/skills/linear-delivery-loop/scripts/` for Linear transport, tracking configuration/preflight, selection, decisions/follow-ups, notifications, and migration reporting
- New JSON schemas and concise references under `src/skills/linear-delivery-loop/references/`
- Focused fixtures/tests under `tests/linear_delivery_control_plane/`
- Existing composition/parity surfaces in `scripts/validate.py`, `validation/manifest.json`, `src/skills/linear-delivery-loop/scripts/contracts.py`, `supervisor.py`, and `cli.py` only where required by the approved interface
- Durable shared documentation in `src/skills/linear-delivery-loop/references/` and a concise overview/update in `README.md`
- Generated `dist/` projections produced only by the repository build

## Validation strategy

1. Focused dependency-free tests cover missing/wrong key, wrong workspace, redirects/host drift, GraphQL `200` errors, pagination/cursor failures, `429`/`5xx` backoff, ambiguous mutation/readback, and secret sentinels.
2. Pure selection and claim tests cover empty queue, manual WIP, autonomous resume, multiple WIP, full candidate rejection reasons, complete ordering, re-read drift, reservation races, local-prepare/provider-claim/readback ordering, and interruption or ambiguity at every boundary with no second candidate.
3. Decision/publication/follow-up tests cover authorization, ordering, replay, exact retry syntax, deduplication, metadata preservation, and no speculative child.
4. Notification tests cover material decisions, external blockers, multiple WIP, stable/exhausted/ambiguous publication refusal, actionable worker/preflight failures, every quiet state, notify-once replay/recovery, retry/failure visibility, links, and redaction without live network calls.
5. Migration tests prove complete pagination, deterministic proposals, mutation-free execution, and preserved unrelated labels/metadata.
6. Run `python .\scripts\build.py`, focused suites, and `python .\scripts\validate.py`.
7. Independent code review and QA inspect the exact implementation. Before merge, rerun the aggregate from a fresh clean worktree at the exact PR head; after squash merge, rerun it from another fresh clean worktree at the exact returned merge SHA.

## Rollout and rollback

- Land the transport/control-plane package disabled from live autonomous use until SAAS-49/SAAS-52 integration and SAAS-54 attended configuration/pilot.
- Roll back through a normal reviewed PR. Preserve supervisor state and operation evidence; do not delete state homes or worktrees manually.
- A transport/config mismatch, missing secret, denied host, ambiguous provider result, or incompatible supervisor version fails before claim/mutation and leaves current work protected.

## Risks and mitigations

- Provider ambiguity or replay: operation-bound idempotency plus read-before/write/read-after reconciliation.
- Incomplete pagination selecting the wrong issue: cursor-progress validation and full-page fixture matrices.
- Credential leakage: environment-only resolution, shared redaction checks, and sentinel assertions across all outputs.
- Linear/ntfy becoming competing truth: Linear remains durable decision authority; ntfy is attention only.
- Scope collision with SAAS-48: this task emits publication-request/retry authorization records but performs no GitHub operation.
- Prompt/runtime growth: detailed schemas and fixtures remain deterministic assets rather than mandatory prompt context.

## Safe assumptions

- Existing Python SAAS-46 module patterns supersede the earlier provisional PowerShell module examples in the program task document.
- Standard-library implementation and injected fixture transports preserve the dependency-free aggregate.
- The configured Linear owner is the only actor authorized to resolve unattended decision and publication-retry requests.
- No UI design artifact is required.

## Sources consulted

- `AGENTS.md`
- `README.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-plan.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-17-three-delivery-workflows-tasks.md`
- `docs-ai/001-dual-delivery-workflows-2026-07-16/2026-07-18-three-delivery-workflows-task-re-audit-2.md`
- `src/skills/linear-delivery-loop/references/supervisor-core.md`
- `src/skills/linear-delivery-loop/references/engine-command.schema.json`
- `src/skills/linear-delivery-loop/scripts/{contracts,supervisor,cli,preflight,operations,reservations,store}.py`
- `tests/linear_delivery_supervisor/`
- `validation/manifest.json`
- Installed canonical `goal-to-delivery/references/` protocol
