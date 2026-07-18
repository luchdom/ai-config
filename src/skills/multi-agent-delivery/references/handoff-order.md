# Specialist Handoff Order

The caller entry policy controls advancement and authority throughout.

| Owner | Owns | Must not own |
|---|---|---|
| `planner` | Discovery-backed plan and clarification record | Tasks, audit verdict, implementation |
| `product-designer` | Current-screen analysis and design spec | Implementation, code review, QA |
| `tasker` | Ordered execution tasks and light audit notes | Independent audit verdict |
| `auditor` | Independent pre-implementation audit | Tasks, code changes, code review |
| implementer | Scoped changes, tests, real-file manifest | Independent gates or external authority |
| `code-reviewer` | Exact-diff/head review findings | Fixes, plan audit, runtime QA |
| `qa` | Acceptance-mapped runtime evidence | Fixes or code-review substitution |
| docs skills | Durable docs update or no-impact record | Review/QA substitution |

Hand back a failed artifact to its owner. Do not silently let one specialist absorb another's independence contract.

Specialists never mutate Linear independently. Under autonomous policy they also never perform state-changing Git/provider operations; they return structured proposals to deterministic code. Semi/manual authority remains limited by the explicit caller boundary/stage.
