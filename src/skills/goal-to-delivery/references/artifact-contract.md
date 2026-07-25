# Artifact Contract

Workflow evidence must help the next run without becoming a second work-management system.

## Current layout

When durable evidence is useful, keep it under:

```text
docs-ai/<work-key>-<slug>/
  workflow.json                 # optional helper-owned metadata
  <date>-<slug>-delivery.md     # concise plan, decisions, checks, and outcome
```

Use additional plan, design, task, audit, review, or QA files only when their content is substantial and independently useful. Routine autonomous work may use the Linear issue, commits, and pull request as its complete record.

`<work-key>` is the observed issue key or a helper-allocated local key. If the optional workflow helper creates `workflow.json`, do not edit its identity fields manually. Resume from an explicit issue, branch/PR, workflow ID, or exact artifact path; never guess from similar text or the newest folder.

## Historical read fallback

Existing numbered-and-dated folders, `docs-ai/history`, and flat `docs-ai/*` artifacts remain historical read fallback. Never rename, rewrite, renumber, or synthesize metadata for historical evidence.

## Durable knowledge

Keep per-work evidence in `docs-ai/`. Put reusable setup, architecture, operations, troubleshooting, and product behavior in the repository's curated docs. Link instead of copying full logs or canonical policy.

Never store secrets, tokens, notification topics, or unredacted customer data in workflow artifacts, Linear comments, commits, or pull requests.
