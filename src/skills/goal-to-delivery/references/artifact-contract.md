# Artifact Contract

Protocol version: `2.0`

## Current layout

New work uses one stable folder:

```text
docs-ai/<work-key>-<slug>/
  workflow.json
  <date>-<slug>-plan.md
  <date>-<slug>-design.md       # only when required
  <date>-<slug>-tasks.md
  <date>-<slug>-audit.md
  <date>-<slug>-code-review.md
  <date>-<slug>-qa.md
  <date>-<slug>-completion.md
```

`<work-key>` is a provider-observed canonical key or an allocator-generated zero-padded local sequence. It is never derived from model/user display text. The deterministic workflow helper allocates, validates, and registers the folder and `workflow.json`; agents must not hand-create identity metadata.

`workflow.json` is schema-validated navigation/evidence metadata. It contains immutable workflow identity, policy/source, repository and exact physical-worktree identity, goal, paths, completion boundary, artifact stage, and optional tracking references. It contains no secret, lease, capability, reservation, or external-mutation authority.

Resume only by exact registered workflow ID, exact artifact path, or unique external ID in a compatible physical worktree. Never infer from goal similarity, slug, chat history, or the newest folder.

## Historical read fallback

Existing `docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/` folders, archived `docs-ai/history/` content, and older flat `docs-ai/*` artifacts remain readable evidence. Producers always use the current layout for new work. Consumers:

1. prefer the descriptor's exact registered artifact paths;
2. accept an explicitly supplied historical folder/path when no current descriptor exists;
3. never rename, rewrite, renumber, or synthesize `workflow.json` inside historical evidence;
4. record that historical fallback was used.

Later Linear attachment updates the same descriptor/registry atomically. It preserves workflow ID, folder, and evidence; it never renames local work to resemble an issue-created folder.

## Artifact ownership

- Planner: `*-plan.md`
- Product designer: `*-design.md` when required
- Tasker: `*-tasks.md`
- Auditor: `*-audit.md`
- Code reviewer: `*-code-review.md`
- QA: `*-qa.md`
- Authorized orchestrator/adapter: `*-completion.md`

Per-work evidence stays in `docs-ai/`. Reusable concepts, how-tos, references, ADRs, runbooks, and troubleshooting belong in curated repository docs. Link between them instead of copying normative policy or full run evidence.

## Repository authority binding

`repositoryKey` is repository configuration rather than a work key. The deterministic helper binds it with normalized repository identity in the repository-scoped state-home sentinel and requires the descriptor and registry projection to agree. A legacy state home without that binding is not adopted automatically; it fails closed for attended migration or reconciliation.

The registry remains authoritative for the workflow's exact artifact path and physical-worktree binding. `workflow.json` is selected navigation/evidence metadata and cannot override the registry or grant authority.

## Workflow-managed Handoff

The CLI requires one or more repeated `--expected-path <repo-relative-path>` values. They declare the exact intended Git-changed user scope. Before any copy, the helper compares that set with the observed Git change set, rejects unlisted dirty paths, and rejects paths intersecting another registered workflow. The selected workflow's `workflow.json` is included internally and must not be supplied as an expected user path.

The destination must be a distinct, clean physical worktree in the same normalized repository, with no conflicting or overlapping destination changes. A successful transfer records immutable redacted manifest, patch, and result evidence whose hashes are bound into the authoritative registry record; later evidence drift fails validation. The registry mapping changes only after copy/readback succeeds, and the base transition explicitly records that no reservation was transferred.

Native Codex **Hand off** remains a separate action. By itself it does not update workflow registry, lease, reservation, or authority. A physical-worktree mismatch fails closed and directs the caller to the registered source or explicit workflow-managed Handoff/recovery.
