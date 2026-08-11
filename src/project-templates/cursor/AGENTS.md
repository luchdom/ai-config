<!-- AI-TOOLKIT-LUCHDOM:START -->
# Project AI Instructions

Use this file as the repository-specific router for shared delivery skills.

## Sources and precedence

- The canonical cross-tool protocol is under `goal-to-delivery/references`; project docs link to it instead of copying it.
- This repository owns repository-specific commands, domain rules, definitions of done, and stricter safety constraints.
- Additional curated docs path: `{{LUCHDOM_AI_TOOLKIT_DOCS}}`.
- Precedence is user/system requirements and repository-specific stricter safety, then the explicit entry policy, then the shared contract. Unresolved conflict fails closed before implementation or external mutation.

## Three entries

- `$goal-to-delivery <goal-or-selected-issue>`: semi-autonomous delivery of one user-selected goal, defaulting to tested `working-tree` output.
- `$spec-driven-delivery <stage> <goal-or-selector>`: manual delivery of exactly one requested stage. Use this for non-trivial work when no entry was explicitly chosen.
- `$linear-delivery-loop`: autonomous delivery of at most one eligible Linear issue using `.ai/loop.json`. Only an explicit scheduled task or attended pilot may invoke it.

Never infer a workflow from a label, branch, prior chat, or artifact folder.

## Lightweight delivery

- Use the smallest applicable stages. Routine work may plan and task inline; add design, independent audit, runtime QA, or durable evidence when risk or acceptance criteria justify them.
- Keep one independent code review and applicable behavior QA before autonomous merge.
- Linear is the durable autonomous queue and decision record. An active attended issue blocks autonomous selection.
- Per-work evidence may use `docs-ai/<work-key>-<slug>/`; reusable guidance belongs in curated repository docs.
- Repository-owned local commands and real acceptance behavior are authoritative. Respect `.ai/loop.json` time, test, file, and changed-line budgets.

## Authority and Git safety

- Manual implementation and the default semi-autonomous boundary permit scoped edits and local validation, not publication.
- Semi-autonomous Commit, PR, or Merge requires the declared boundary or a later grant. Manual publication requires each named stage.
- The explicit autonomous entry may claim/update its selected issue and use a branch, PR, and squash merge within repository policy.
- Preserve unrelated work. Never infer force-push, history rewrite, direct default-branch push, destructive cleanup, provider-setting changes, or unrelated external mutation.

Use `$pr-description` for pull request text and follow the repository template when present.
<!-- AI-TOOLKIT-LUCHDOM:END -->
