# Repository memory

Repository memory is a local, reviewed knowledge layer for compact repository facts and precedents. It is evidence, never policy or authority. Current repository instructions, curated source documents, source code, and the canonical [delivery protocol](../../goal-to-delivery/references/) always win when they disagree with a memory record.

The feature is opt-in. It does not crawl `docs-ai/`, chat, Linear comments, logs, or tool payloads; use embeddings or a network service; select work; pass a gate; or grant reservation, mutation, provider, publication, or completion authority.

## Storage model

The portable tier is ordinary reviewed repository content:

```text
docs/repository-memory/
  README.md
  records/<record-id>.v<four-digit-version>.json
  commits/<batch-promotion-id>.json
```

The machine-local tier is derived state beneath the normalized repository's existing state home:

```text
repository-memory/
  index.json
  promotions/<batch-promotion-id>/...
```

All linked worktrees share the same repository identity, state home, `allocation.lock`, and memory projection. Records and commit markers are canonical; the index, promotion journals, prepared files, and results are disposable. Never edit `dist/` or machine state to change memory truth.

## Contracts and digest projections

Version `1.0` uses strict, unknown-field-rejecting contracts beside this page:

- [`repository-memory-record.schema.json`](repository-memory-record.schema.json): immutable curated record versions.
- [`repository-memory-promotion.schema.json`](repository-memory-promotion.schema.json): docs-owned candidate decision evidence.
- [`repository-memory-batch-request.schema.json`](repository-memory-batch-request.schema.json): exact ordered batch, repository binding, replay key, and mutation scope.
- [`repository-memory-commit.schema.json`](repository-memory-commit.schema.json): immutable repository commit marker.
- [`repository-memory-promotion-result.schema.json`](repository-memory-promotion-result.schema.json): no-op, committed, or derived-index-reconstruction result.
- [`repository-memory-index.schema.json`](repository-memory-index.schema.json): disposable marker-derived projection.
- [`repository-memory-query.schema.json`](repository-memory-query.schema.json), [`repository-memory-result.schema.json`](repository-memory-result.schema.json), and [`repository-memory-context-envelope.schema.json`](repository-memory-context-envelope.schema.json): bounded retrieval and final stage delivery.

Runtime validation in `scripts/contracts.py` mirrors invariants that JSON Schema cannot express. Canonical JSON sorts object keys recursively, preserves array order, uses compact separators and `ensure_ascii=true`, then hashes UTF-8 bytes as lowercase `sha256:<64-hex>`.

Digest dependencies are deliberately acyclic:

1. `CandidateIntentV1` excludes only `candidateIntentSha256`.
2. `PromotionManifestPayloadV1` excludes only `promotionManifestPayloadSha256` and contains no record result digest.
3. `RecordPayloadV1` binds the manifest payload digest and excludes only `recordPayloadSha256`; the final record-file digest appears downstream.
4. `PromotionBatchRequestV1` binds the manifest file/payload, ordered targets, expected index, repository/head/worktree, and consumed authorization identity, but no record or marker result digest.
5. `BatchCommitPayloadV1` binds every completed record digest and excludes only `batchCommitPayloadSha256`; the final marker-file digest appears only in derived evidence.
6. `IndexSemanticV1` excludes `builtAt` and `indexSemanticSha256`. Query and retrieval projections do not self-hash.
7. `ContextEnvelopePayloadV1` excludes its payload digest. `ContextDeliveryAccountingV1` replaces only both six-character usage values with `"000000"`, so the final inclusive character and byte counts have stable width.

A digest proves exact bytes and bindings, not semantic truth or mutation authority.

## Record taxonomy and assertions

Kinds are `concept`, `decision`, `how-to`, `runbook`, `troubleshooting`, `constraint`, and `reference`. Topics, repository-relative paths, applicable stages, and optional exact work identity form the retrieval scope. Title and summary are display-only.

An active record carries one to sixteen typed assertions. Each assertion has a normalized key, `equals` comparison, a `string`, safe JSON `integer`, `boolean`, or canonical `string-set` value, and one to eight provenance references. Runtime conflict and duplicate decisions use only canonical scope and the complete typed assertion map; they never interpret prose or invoke a model.

- Intersecting scopes conflict only when the same assertion key has a different type or value.
- A duplicate requires byte-identical complete scope and complete assertion map. Display or provenance differences remain bounded metadata on the chosen representative.
- Subsets, supersets, partial overlaps, disjoint keys, and equal maps under different scopes stay distinct.
- Conflict resolution requires an explicit reviewed successor or consolidation record; timestamps and ranking never resolve it.

Confidence describes provenance topology, not certainty: `current-source-bound`, `source-evidence-bound`, and `legacy-evidence-bound`. Archived and redacted tombstones use `not-applicable`. Every provenance reference is repository-relative and digest-bound. Retrieval rereads both the record and its sources; missing, unsafe, corrupt, or changed bytes exclude the record with count-only diagnostics. Current sources remain authoritative.

## Promotion and the marker commit point

The optional `*-memory-promotion.json` artifact is owned by `$docs-as-code` under the canonical [artifact contract](../../goal-to-delivery/references/artifact-contract.md). It must be inventoried in a distinct registered curation workflow at its docs or completion stage. Current completed workflows and explicit legacy evidence may be sources; no source workflow is retrofitted or rewritten. `no-candidates` is a durable, idempotent no-op.

An approved promotion is one ordered batch of 1–32 candidates. The existing delivery supervisor must first issue one `AuthorizeMutation` whose exact sorted scope is every target record plus `docs/repository-memory/commits/<batch-promotion-id>.json`. The manifest, producer name, role, digest, or status cannot replace that authority. Promotion is exposed through the authenticated library/adapter path; the read/maintenance public memory CLI intentionally does not accept `promote`.

Under the canonical repository mutex, promotion rereads registry, descriptor, manifest, source digests, repository/head/worktree identity, and applicable autonomous docs attestation. It validates the prospective graph, duplicates, conflicts, expected prior semantic index digest, and exact authorization before repository creation. Prepared bytes and recoverable authority consumption are state-home implementation evidence, not commit evidence.

Records are created in canonical order with create-new/no-clobber writes and exact readback. The marker is created last the same way and binds the complete ordered record set. A valid marker is the sole durable commit point:

- Before it exists, all batch records are uncommitted and retrieval-invisible. Cleanup may remove only journal-proven files that were pre-absent and are exactly owned by the incomplete batch; ambiguity becomes `protected-incomplete`.
- Once it exists and validates with every bound record, the whole batch is committed. It is never rolled back because index or result persistence failed.
- A replay with identical identities and bytes converges. Reused identities with changed input are `conflicting-replay`; no subset retry, overwrite, or partial committed success exists.

If the marker lands before the index/result, the result is `index-reconstruction-required`. Query reconstructs the complete marker-derived view transiently; rebuild or repair can persist it. Journals/results are never rebuild inputs.

## Lifecycle and freshness

Records are append-only. Never edit an existing version.

- Supersession is forward-only: a successor names predecessors; the index derives reverse links and terminal state. Same-record version `n` supersedes `n-1`. A version-one consolidation may join two to eight terminal records. Missing predecessors, branches, cycles, invalid restoration, or revival of a redacted chain are quarantined.
- Archive creates a reviewed, assertion-free same-record successor with a reason. Restore creates another reviewed active successor that exactly supersedes and names the terminal archived version; it does not reactivate old bytes.
- Redaction creates a content-free same-record successor. Its ancestor chain is suppressed. Removing sensitive Git history is a separate attended operation.
- Retention is `durable`, `review-on`, or `expire-on`. Review due and expiry are clock-derived; they do not mutate or delete records.
- Freshness is digest-on-read. The index reports `fresh`, `review-due`, `expired`, or `stale`; source digest drift, missing or unsafe source paths, and invalid committed input fail closed.

Default retrieval excludes non-active, superseded, invalid-graph, conflicted, expired, stale, duplicate-suppressed, and legacy-evidence-bound records. Explicit `includeLegacy` is available only for a manual query; context remains governed by its authenticated stage selectors.

## Deterministic retrieval and final context

Queries are repository-bound and filter by exact work, stage, path/ancestor relationship, and normalized topics. Ranking is stable in this order: exact work; path match kind and distance; exact stage; topic match count; confidence; kind (`constraint`, `decision`, `runbook`, `troubleshooting`, `how-to`, `reference`, `concept`); newest version; record ID; filename. Filesystem enumeration and wall-clock time never rank results.

| Budget | Minimum | Default | Maximum |
|---|---:|---:|---:|
| Records | 1 | 8 | 32 |
| Unicode scalar characters | 1,000 | 12,000 | 48,000 |
| UTF-8 bytes | 4,096 | 24,576 | 98,304 |

Selection keeps whole items only. The item array is charged against the character cap; the complete canonical retrieval result, including provenance, ranks, diagnostics, and accounting, is charged against bytes. Over-budget items are omitted deterministically and the lowest-ranked selected items are removed until the result fits.

Context is available only to `planner`, `implementer`, `code-reviewer`, and `qa` after the adapter derives repository, workflow, issue, stage, completion boundary, provider, and mutation-scope identity from authenticated state. Memory text is escaped and delivered as JSON in a tool message named `repository_memory_context`. A fixed developer message outside that untrusted data establishes precedence. The adapter never parses memory as markup, commands, configuration, selectors, or tool calls.

Final accounting covers the complete canonical developer/tool bundle after JSON-within-JSON escaping. If it exceeds the requested record, character, or byte limit, whole lowest-ranked items are removed and the digest/accounting is recomputed. The wrapper alone exceeding the limit is `context-budget-too-small`; an inclusive count mismatch is `context-accounting-invariant`. Either failure delivers no memory messages.

## Setup, CLI, and status

Prerequisites are Python, a normalized Git repository already initialized in the shared workflow registry/state home, and its configured `repositoryKey`. Work from canonical `src/` in this repository; for installed tool copies, follow the normal build/sync procedure documented in the repository's top-level `README.md`. Version 1 creates no seed records and enables no implicit autonomous loading.

The separate public CLI accepts `query`, `rebuild`, `repair`, or `context` and deliberately does not expand the supervisor `EngineCommand` operation union:

```powershell
python .\src\skills\linear-delivery-loop\scripts\cli.py --repository-memory-request .\memory-request.json
```

The request inventory is exact:

```json
{
  "schemaVersion": "1.0",
  "operation": "rebuild",
  "repositoryRoot": "C:\\path\\to\\repo",
  "repositoryKey": "configured-repository-key",
  "payload": {}
}
```

`repair` has the same empty payload and, in version 1, is an alias for a persistent derived-only rebuild. `query` takes a strict query payload including the canonical repository ID/key and budgets. `context` takes exactly `query`, `workflowId`, `issueId`, `stage`, `maxRecords`, `maxCharacters`, and `maxBytes`; its workflow stage and selectors must match authenticated registry/descriptor state. Do not put request files containing internal identifiers into Git.

The ordinary supervisor `Status` result includes a bounded `memory` object. `health` is `missing`, `healthy`, or `corrupt`, with builder version, semantic/marker-set digests, source-tree/build observation, safe counts, and a redacted error code. Status reads only the persisted index: it never rebuilds, repairs, returns bodies/paths/journals, or distributes authority. See [`supervisor-core.md`](supervisor-core.md) for the base command and authority model.

## Recovery and troubleshooting

Use status to observe, then choose an explicit action:

- `missing` or `corrupt` index: run `rebuild` (or `repair`). Curated records and markers are not changed.
- `index-reconstruction-required`: the marker committed successfully; query is safe immediately and a rebuild persists the projection.
- Total state-home loss: restore normal repository state-home setup, then rebuild from committed markers and their complete record sets. Unmarked files remain excluded.
- `uncommitted-orphan`: inspect the originating promotion journal if it exists. Never add a marker or delete the file by hand. Without exact proof, preserve it for attended recovery.
- Invalid marker or bound record: the whole named batch is excluded. Correct it with a separately reviewed successor/redaction or restore known repository bytes; never make the index accept altered content.
- Stale/source drift: update the authoritative source and curate a new reviewed version, or restore the exact source bytes. Rebuild does not make stale evidence current.
- Conflict, invalid graph, or duplicate promotion refusal: fix the next manifest structurally; do not edit earlier versions or rely on prose/ranking.
- Cross-repository, unsafe-path, reparse, hard-link, or secret-like rejection: correct repository identity/input and rerun. Do not weaken validation or copy machine state between repositories.
- Context budget/accounting failure: raise limits only within repository maxima or reduce requested scope; never concatenate raw retrieval output into a prompt.

Rollback disables the opt-in entry point/status integration and removes only reproducible derived state. Preserve committed records, commit markers, and completed workflow evidence. Correct bad curated knowledge through reviewed append-only lifecycle changes. Unknown newer schema/builder versions fail closed and must not be silently downgraded.

## Verification

From the repository root:

```powershell
python -m unittest discover -s tests\linear_delivery_repository_memory -t . -v
python .\scripts\build.py
python .\scripts\validate.py
```

Build regenerates `dist/` from canonical `src/`; never edit generated projections directly. Before publication, follow the canonical [quality gates](../../goal-to-delivery/references/quality-gates.md): focused tests are early feedback and do not replace exact-head independent review, runtime QA, docs/projection/link verification, or exact returned-merge-SHA validation.
