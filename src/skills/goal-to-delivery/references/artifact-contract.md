# Artifact Contract

Workflow evidence must help the next run without becoming a second work-management system.

## Current layout

When local workflow evidence is useful, initialize it under the effectively ignored workspace:

```text
.ai/work/<YYYY-MM-DD>--<work-token>--<slug>[--<sequence>]/
  workflow.json                 # optional helper-owned metadata
  <date>-<slug>-delivery.md     # concise plan, decisions, checks, and outcome
```

Use additional plan, design, task, audit, review, or QA files only when their content is substantial and independently useful. Routine autonomous work may use the Linear issue, commits, and pull request as its complete record.

`<work-token>` is the observed external key or `local-<numeric-workKey>`. Exact collisions append `--02`, `--03`, and later deterministic sequences. `.ai/work` must be effectively ignored and contain no tracked path before initialization, while `.ai/loop.json` must remain visible to Git.

If the optional workflow helper creates `workflow.json`, do not edit its identity fields manually. The descriptor and registry's exact absolute `artifactFolder` is the authority for every stage reader and writer. Resume from an explicit issue, branch/PR, workflow ID, or that exact registered path; never reconstruct a root, adopt an unregistered folder, or guess from similar text or the newest folder. Folder rendering does not change descriptor schema `2.0` or its existing `workKey` semantics.

## Registered legacy compatibility

An exact workflow already registered below `docs-ai/<legacy-folder>/` remains readable and writable in that same folder until completion. Registration is the compatibility authority: no broad path fallback may adopt an unregistered `docs-ai` folder. New workflows always allocate below `.ai/work`.

## Historical read-only fallback

Existing numbered-and-dated folders, `docs-ai/history`, and flat `docs-ai/*` artifacts remain historical read fallback. Never rename, rewrite, renumber, or synthesize metadata for historical evidence.

## Workflow-managed handoff

Because `.ai/work` is ignored, workflow-managed Handoff enumerates every regular file below the exact registered artifact folder instead of relying on Git status. It also transfers the explicitly approved working-tree scope, but never scans adjacent ignored data or `.ai/worktrees`.

Handoff fails closed on containment/case conflicts, traversal, reparse points, hardlinks, destination collisions, concurrent inventory/content changes, failed hashes, or rollback uncertainty. One transfer is limited to 512 files, 16 MiB per file, and 64 MiB total. Evidence redacts sensitive paths and content-derived hashes; the source remains authoritative until the descriptor/registry pair commits atomically. Exact registered legacy folders use the same handoff protections.

## Durable knowledge

Keep per-work evidence in its exact registered `artifactFolder`. Put reusable setup, architecture, operations, troubleshooting, and product behavior in the repository's curated docs. Link instead of copying full logs or canonical policy.

Never store secrets, tokens, notification topics, or unredacted customer data in workflow artifacts, Linear comments, commits, or pull requests.
