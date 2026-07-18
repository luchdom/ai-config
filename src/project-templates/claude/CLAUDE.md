<!-- AI-CONFIG-LUCHDOM:START -->
# Project AI Instructions

Use this file as the repository-specific router for shared delivery skills.

## Sources and precedence

- The sole canonical cross-tool delivery protocol is the installed `$goal-to-delivery` reference set: `delivery-stages.md`, `artifact-contract.md`, `clarification-policy.md`, `quality-gates.md`, `completion-boundaries.md`, and `work-descriptor.schema.json`. Its source is `ai-config/src/skills/goal-to-delivery/references/`; installed files are generated projections.
- This repository's `AGENTS.md` and curated docs own project-specific commands, domain rules, definitions of done, and stricter safety constraints. Do not copy the shared protocol into repository docs.
- Additional curated docs path: `{{LUCHDOM_AI_CONFIG_DOCS}}`.
- Precedence is user/system requirements and repository-specific stricter safety, then the explicitly invoked entry policy, then the canonical shared contract. A weaker rule cannot override a stronger one; unresolved conflict fails closed before implementation or external mutation.

## Three explicit workflow entries

There are exactly three delivery entries:

- `$goal-to-delivery <goal-or-selected-issue>`: semi-autonomous delivery of one user-selected goal. It never selects queue work, defaults to local source and the `working-tree` boundary, and cannot self-elevate to autonomous mode.
- `$spec-driven-delivery <stage> <goal-or-selector>`: manual delivery. It performs exactly the requested stage, never auto-advances, and requires separate explicit Implement, QA, Commit, PR, and Merge actions.
- `$linear-delivery-loop <adapter-prepared-iteration>`: the only autonomous entry. It requires one schema-valid capability from the deterministic adapter and never accepts a raw goal or performs queue selection in model policy.

For non-trivial work without an explicit entry, default to `$spec-driven-delivery`. Never infer a workflow from a label, branch, prior chat, or artifact folder.

## Work identity and artifacts

- Initialize or resume work through the deterministic helper bundled with `$goal-to-delivery`; agents do not invent workflow IDs, work keys, paths, or authority.
- New work uses `docs-ai/<work-key>-<slug>/workflow.json` plus dated artifact filenames such as `<date>-<slug>-plan.md`.
- Resume only by exact registered workflow ID, exact artifact path, or unique external ID in a compatible physical worktree.
- Existing numbered-and-dated folders and flat `docs-ai/*` files are historical read fallback only. Never rename, rewrite, renumber, or add synthetic descriptors to them.
- Per-work evidence belongs in `docs-ai/`; durable how-tos, concepts, references, ADRs, runbooks, and troubleshooting belong in curated repository docs.
- Follow the canonical artifact contract for workflow-managed Handoff: repository authority remains registry-bound, expected paths must equal the observed Git-changed scope, and the base transfer carries no reservation. Native Codex **Hand off** grants no workflow authority.

## Shared specialists and quality

- Reuse one shared specialist set for all three entries. The caller entry controls advancement and authority.
- Keep the independent plan auditor, exact-diff code reviewer, runtime QA verifier, and documentation stage distinct. None substitutes for another, and reviewers/QA report rather than fix production code.
- Use `$repo-discovery` for repo context, `$multi-agent-delivery` for specialist handoffs, `$task-audit-breakdown` for task/audit checklists, `$qa-verification` for behavior verification, and `$docs-as-code` for durable documentation.
- Repository-owned local commands and real acceptance behavior are authoritative. Map every acceptance criterion to observed evidence and report anything unverified.

## Authority and Git safety

- Read-only repository inspection is allowed unless local guidance is stricter.
- Manual `Implement` and the default semi-autonomous boundary authorize scoped edits and local validation, not branch/stage/commit/push/PR/merge actions.
- Semi-autonomous publication requires an explicit completion boundary or later grant. Manual publication requires each named action.
- Autonomous external and Git mutation belongs only to deterministic adapter code while its prepared capability is valid; specialists return structured proposals and real-file manifests.
- Before any attended state-changing Git/provider action, summarize the exact action and file scope and preserve unrelated user work.

## Pull request text

Use `$pr-description`. Follow `.github/pull_request_template.md` exactly when present; otherwise use Overview, Changes, Security Impact, Testing, Related Work. Keep the title under 70 characters and store draft text in the registered workflow folder as `<date>-<slug>-pr-description.md`.
<!-- AI-CONFIG-LUCHDOM:END -->
