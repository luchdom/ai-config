---
name: docs-as-code
description: Maintain durable, searchable repository documentation as a distinct delivery stage. Use when implementation or artifact work changes behavior, architecture, setup, operations, workflow, or troubleshooting guidance and the nearest curated docs must be updated or explicitly declared unaffected.
---

# Docs as Code

Own the documentation stage without replacing planning, code review, or runtime QA.

## Contract

1. Read repository instructions and the smallest relevant curated documentation set.
2. Read the approved work artifacts from the exact `artifactFolder` recorded by the active work descriptor/registry and inspect the implemented change; do not infer behavior from the task title alone.
3. Record docs impact as exact pages to update or `none` with a concrete reason.
4. Update the nearest durable source of truth. Prefer an existing page and links over a competing explanation.
5. Verify commands, links, navigation, and any repository documentation gate available locally.
6. Return changed pages, checks performed, and residual gaps. Do not claim code review or behavioral QA.

Use only the registered artifact identity:

- Do not reconstruct the artifact folder from a root literal or select it by recency or a similar slug.
- New/current registered work resolves under `.ai/work`; an exactly registered legacy workflow continues in its exact registered folder.
- Explicitly supplied unregistered or tracked historical artifacts are read-only fallback; never adopt, migrate, or rewrite them.

Keep evidence separate from durable knowledge:

- Store plans, decisions, task breakdowns, audits, review reports, QA evidence, and completion records in the workflow's exact registered `artifactFolder`.
- Store reusable concepts, how-tos, references, ADRs, runbooks, and troubleshooting under the curated `docs/` tree or repository-defined equivalent.
- Write setting how-tos with prerequisites, steps, verification, rollback, and troubleshooting.
- Link useful evidence; do not add raw run logs or whole workflow folders to primary documentation navigation.
- Keep Linear comments concise and link artifacts rather than copying full documents.

The canonical cross-tool delivery protocol remains under `$goal-to-delivery` references. Repository docs may link to it and add repository-specific commands or stricter rules; they must not create a second normative copy.

Edit docs only when the caller's active stage and repository authority allow it. A docs-only artifact can finish at the `artifact` boundary after its acceptance and documentation checks pass; never create an empty code change merely to publish evidence.
