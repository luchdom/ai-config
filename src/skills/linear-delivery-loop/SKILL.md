---
name: linear-delivery-loop
description: Execute one unattended autonomous delivery iteration from a schema-valid capability prepared by the deterministic Linear adapter. Use only when explicitly invoked as `$linear-delivery-loop` by the versioned scheduled prompt or an attended pilot; never accept a raw goal, choose queue work, or implement Linear mutations in model policy.
---

# Linear Delivery Loop

Apply autonomous advancement policy to one adapter-prepared issue. This skill is a thin policy entry; deterministic code owns selection, WIP, authority, state, retry, external mutation, and checkpoints.

## Invocation

Require an explicit invocation with exactly one schema-valid `PreparedIteration` file/capability:

```text
$linear-delivery-loop <adapter-prepared-iteration>
```

Fail without repository or external mutation when the capability is missing, invalid, expired, replayed, mismatched to the observed repository/worktree, or contains more than one issue. A raw issue key, goal, label, or prompt is not a capability.

Read and follow the sole healthy-run policy reference: [autonomous-runtime-contract.md](../goal-to-delivery/references/autonomous-runtime-contract.md). Keep diagnostic architecture, detailed protocol references, schemas, and scripts out of routine context; deterministic validation owns their enforcement. Apply stricter repository rules first and fail closed on conflict.

## Policy

1. Accept only the issue and authority already prepared by the deterministic adapter after its preflight, lease, reservation, authorization, eligibility, WIP, and issue-contract checks.
2. Use the same planner, optional product designer, tasker, independent auditor, implementers, code reviewer, runtime QA, and documentation skills used by the other entries.
3. Continue routine stages during the current invocation while the prepared capability remains valid.
4. Return structured stage results, proposed external transitions, and a real-file change manifest to the adapter. Renew authority and apply checkpoints only through the adapter; model output is never authority.
5. Stop on completion, pause, external wait, retry exhaustion, non-retryable failure, capability/lease loss, interruption, or any material decision requiring a human.
6. Never select again after the prepared issue completes or pauses, and never start a second issue in the same invocation.

Safe assumptions may be recorded. A material decision becomes a structured pause proposal; the deterministic adapter owns the durable Linear request and attention notification. This skill does not implement GraphQL, queue-selection, label/state mutation, notification, Git publication, merge, or provider-retry behavior.

Autonomous code targets the `merge` boundary and is complete only after all exact-head local gates, independent code review, applicable runtime QA, documentation checks, authorized squash merge, and clean validation of the exact returned merge SHA. Hosted provider status is neither queried nor accepted as quality evidence.
