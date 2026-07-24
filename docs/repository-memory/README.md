# Curated repository memory

This directory is the repository-owned home for compact, reviewed memory. It contains immutable records and atomic batch commit markers. The detailed architecture, schemas, deterministic retrieval rules, runtime commands, and recovery codes live in the shared [repository-memory reference](../../src/skills/linear-delivery-loop/references/repository-memory.md).

Memory is navigation and evidence, not a competing source of truth. `AGENTS.md`, curated documentation, source code, and canonical workflow policy take precedence. A record, manifest, digest, producer name, or status never grants workflow, reservation, mutation, provider, publication, or completion authority.

## Layout and taxonomy

```text
docs/repository-memory/
  README.md
  records/<record-id>.v<four-digit-version>.json
  commits/<batch-promotion-id>.json
```

Record kinds are `concept`, `decision`, `how-to`, `runbook`, `troubleshooting`, `constraint`, and `reference`. Use typed assertions for machine-comparable knowledge; title and summary are display-only. Every assertion must point to digest-bound repository-relative provenance. Confidence records the source topology—current source, source plus completed evidence, or explicit legacy evidence—not a machine judgment that prose is true.

Do not store raw workflow folders, chats, comments, logs, patches, tool payloads, credentials, authority references, or full source documents here.

## Curation and promotion

Promotion is part of an authorized documentation stage:

1. Start or resume a distinct registered curation workflow according to the canonical [artifact contract](../../src/skills/goal-to-delivery/references/artifact-contract.md).
2. Review exact completed evidence and current repository sources. Create the optional inventoried `*-memory-promotion.json` artifact as `$docs-as-code`; use `no-candidates` when nothing durable should be promoted.
3. For each approved candidate, choose a stable record ID, the next append-only version, kind/scope, concise display text, typed assertions, exact provenance, confidence, freshness/retention, and lifecycle links.
4. Obtain ordinary repository mutation authority for the exact complete batch: all record targets plus its deterministic commit-marker target. The manifest itself is not authority.
5. Invoke the authenticated promotion adapter. Do not hand-create record or marker files.
6. Verify the structured result, query the intended scope, review the Git diff, and run the focused and aggregate checks from the shared reference.

Promotion is atomic across 1–32 ordered candidates. Record files are created without overwrite and read back first. The marker is created last and binds every target and digest. Its valid presence is the sole durable commit point. Before the marker, records are invisible orphans; after it, the entire valid batch is committed even if derived index/result persistence fails.

Never edit a committed record or marker. A replay must use the identical request. A changed replay, subset retry, target reuse, overwrite, or partial success is rejected.

## Lifecycle and review

- Update knowledge with a new immutable version and a forward `supersedes` link. The index derives reverse/current state.
- Consolidate conflicts only through an explicit reviewed version-one successor of the terminal records.
- Archive with an assertion-free reviewed successor; restore with a later active successor containing newly reviewed content and current digests.
- Redact with a content-free successor. Git-history remediation is separate and attended.
- Treat `review-on` and `expire-on` as suppression policies, not deletion instructions. No lifecycle operation automatically removes files.

Current sources win. Source digest drift, missing or unsafe sources, conflicts, invalid graphs, expiry, archive, redaction, supersession, and default-excluded legacy evidence remain visible through bounded diagnostics but are not returned as current memory.

## Recovery rules

The machine-local index and promotion journals are not repository truth. Rebuild scans only valid commit markers and each complete bound record set. It excludes unmarked records and an entire invalid marker batch; it never repairs or rewrites repository files.

- Missing/corrupt index or total state-home loss: restore normal state-home setup and run explicit rebuild.
- Marker present but index result failed: keep the committed files; query can reconstruct transiently, then rebuild.
- Unmarked orphan: do not delete it or invent a marker. Cleanup requires exact journal proof that the file was pre-absent and created by the incomplete batch; otherwise preserve and escalate.
- Invalid marker/record or stale provenance: repair through reviewed repository history or an append-only successor, not by weakening validation.

Rollback removes or rebuilds only derived state and may disable opt-in loading. It preserves committed records, markers, and completed evidence unless a separately reviewed lifecycle change says otherwise.

## Operations

Use the separate strict memory request surface documented in the [module runbook](../../src/skills/linear-delivery-loop/references/repository-memory.md#setup-cli-and-status) for `query`, `rebuild`, `repair`, and authenticated `context`. Supervisor status is observation-only and does not rebuild. Memory context is opt-in, escaped, budgeted, tool-role untrusted data for planner, implementer, code reviewer, and QA; it cannot change authenticated selectors, scope, authority, or gate outcomes.
