# Delivery Stages

These stages and specialists are reusable capabilities, not a mandatory fixed chain. The active entry decides which stages apply and whether to advance.

| Stage | Typical owner | Minimum useful outcome |
|---|---|---|
| `discover` | active agent with `$repo-discovery` | Relevant instructions, patterns, and commands |
| `plan` | planner or active agent | Bounded approach, acceptance criteria, risks, and tests |
| `clarify` | planner or active agent | Safe assumptions recorded or one material question raised |
| `design` | product-designer when `design-gates.md` requires a specification | Implementer-ready direction tied to binding design sources |
| `task` | tasker or active agent | Ordered implementation steps when decomposition helps |
| `audit` | independent auditor for risky or complex plans | Pre-implementation gaps and verdict |
| `implement` | matching implementer or active agent | Scoped changes and focused tests |
| `design_review` | product-designer for changed rendered UI or interaction | Real-browser design-system and approved-spec conformance verdict |
| `review` | code-reviewer | One independent exact-diff review |
| `qa` | qa with `$qa-verification` | Applicable real-behavior evidence |
| `docs` | `$docs-as-code`; `$luchdom-docs` where applicable | Durable docs update or concrete no-impact result |
| `publish` | authorized active agent | Requested commit or PR boundary |
| `merge` | user or autonomous entry | Authorized merge after required local gates |
| `post_merge` | explicit manual stage | Optional verification requested by the user or repository |

The auditor evaluates a plan before implementation; the product-designer checks rendered UI conformance; the code reviewer examines implemented changes; QA exercises behavior. Use each when its distinct evidence is valuable. Low-risk routine work may plan and task inline, but autonomous code still requires applicable UI design conformance, one code review, and applicable QA before merge.

- Semi-autonomous: continue applicable stages automatically, repair scoped findings within a small retry budget, and stop at its boundary.
- Manual: perform exactly the named stage and never auto-advance.
- Autonomous: select or resume at most one eligible Linear issue, checkpoint or request a decision when blocked, and stop after that issue completes or pauses.

Apply [design-gates.md](./design-gates.md) to all frontend/UI work. A pre-implementation design spec is required whenever a UI decision remains. A narrowly mechanical change may record that no new spec is required only when a binding source dictates every UI decision. Every changed rendered UI or interaction still requires a current post-implementation product-designer design conformance review before downstream gates can pass. Documentation-only, backend-only, and configuration-only work do not require these UI gates.
