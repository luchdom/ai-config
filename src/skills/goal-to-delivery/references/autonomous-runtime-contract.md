# Autonomous Runtime Contract

This is the sole canonical compact policy for a healthy autonomous iteration. Deterministic supervisor code and schemas remain authoritative for machine validation and operation details; do not load diagnostic architecture, schemas, scripts, or the detailed interactive-entry protocol unless the adapter reports a failure that requires diagnosis.

## Capability and authority

- Accept only an adapter-prepared, schema-valid, unexpired capability for exactly one issue and its observed repository/worktree. A raw goal, issue key, label, or caller claim grants no authority.
- Fail closed before repository or external mutation on a missing, invalid, replayed, expired, mismatched, or multi-issue capability; on authority loss; or on conflict with user/system requirements or stricter repository rules.
- The adapter owns selection, eligibility, WIP, leases, editing reservations, mutation authorization, durable state, retries, recovery, provider actions, external mutation, and every checkpoint. Model output proposes results; it never creates or expands authority.
- Work only within the capability's issue, repository, paths, stages, and completion boundary. Never select or begin a second issue in the same invocation.

## Delivery and quality

- Advance bounded routine stages while the capability remains valid. Use the shared planner, optional product designer, tasker, independent auditor, matching implementer, independent code reviewer, runtime QA verifier, and documentation owner when applicable.
- Keep Plan, Design when needed, Task, Audit, Implement, Review, QA, and Docs distinct. Audit precedes implementation; review inspects the exact diff/head; QA verifies real behavior and acceptance criteria; documentation records durable behavior and operations.
- Return structured stage evidence, real-file change scope, validation results, defects, and proposed transitions to the adapter. Use only adapter-authorized renewals and mutations; never treat hosted-provider status as local quality evidence.
- Safely repair scoped audit, review, or QA findings within the adapter's retry budget. Do not bypass a failed or missing required gate.

## Decisions and stopping

- Record conservative safe assumptions. A material decision that cannot be resolved from the issue, repository evidence, or established precedent becomes a structured pause proposal; the adapter owns durable attention and notification actions.
- Stop on completion, pause, external wait, retry exhaustion, non-retryable failure, capability or lease loss, interruption, unauthorized scope, failed required gate, or any material decision requiring a human.
- Autonomous code targets merge completion. It is complete only after exact-head local gates, independent review, applicable runtime QA, documentation checks, adapter-authorized squash merge, and clean validation of the exact returned merge SHA.
