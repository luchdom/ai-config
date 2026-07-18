# Delivery Stages

Protocol version: `2.0`

This is the canonical cross-tool stage and ownership contract. Entry policy determines advancement; specialists do not.

| Stage | Primary owner | Required output or gate | Minimum prerequisite |
|---|---|---|---|
| `discover` | active orchestrator with `$repo-discovery` | Exact instructions, sources, patterns, tests, and conflicts | Goal or selected issue |
| `plan` | `planner` | Goal/non-goals, approach/contracts, risks, tests, rollout, sources | Discovery evidence |
| `clarify` | `planner` plus entry policy | Recorded assumptions and resolved or paused material decisions | Plan or focused ambiguity |
| `design` | `product-designer` when required | Implementer-ready design artifact, or explicit not-required reason | Plan and current UI evidence |
| `task` | `tasker` | Ordered tasks with acceptance, likely files, tests, and dependencies | Plan and required design |
| `audit` | independent `auditor` | Adversarial verdict against source requirements and task readiness | Plan, tasks, required design |
| `implement` | matching implementer | Scoped changes, tests, and real-file manifest | Passing audit and entry authority |
| `review` | `code-reviewer` | Exact-diff findings against acceptance, security, tenancy, and conventions | Implemented diff and target identity |
| `qa` | `qa` with `$qa-verification` | Real behavior evidence mapped to acceptance criteria | Review-ready implementation |
| `docs` | `$docs-as-code`; `$luchdom-docs` where applicable | Durable docs update or explicit no-impact reason | Actual change and docs-impact declaration |
| `publish` | authorized root or deterministic adapter | Requested commit/PR boundary with exact identities | Required local gates and explicit authority |
| `merge` | user or deterministic adapter | Authorized squash merge after exact-head gates | Approved exact PR head |
| `post_merge` | deterministic adapter or explicit manual stage | Clean repository gate at the exact returned merge SHA | Observed merge identity |

The auditor validates the plan before implementation. The code reviewer inspects what was implemented. QA exercises actual behavior. Documentation maintains durable guidance. Passing one contract never substitutes for another.

## Advancement

- Semi-autonomous: continue safe applicable stages, loop back for scoped fixes, stop at the declared boundary, and never select another item.
- Manual: validate prerequisites, execute exactly the named stage, report valid next stages, and never auto-advance.
- Autonomous: accept one adapter-prepared capability, checkpoint through deterministic code, and stop on completion, pause, external wait, retry exhaustion, authority loss, or interruption.

Design is required for a material user-facing screen, flow, interaction, or visual direction change. Record `design: not required` with a reason for backend-only, documentation-only, configuration-only, or purely mechanical UI work.
