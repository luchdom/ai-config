# SAAS-56 curated repository memory and bounded retrieval — Code review

## Verdict

**FAIL** — one P1 finding, five P2 findings, and one P3 finding. The reviewed working-tree implementation does not satisfy RM-01–RM-05 or the passing re-audit contract. In particular, repository-memory promotion can be authorized by an arbitrary library caller, pre-marker process death is not recoverable, and the context adapter does not authenticate or bind its selectors.

## Review boundary and evidence

- Reviewed base: `main` / `1a5190f1815ae25b0a3cba6e81b50ae221c62052`.
- Reviewed target: the current uncommitted tracked and untracked RM-01–RM-05 working-tree change set reported by `git status --short` on 2026-07-24.
- Requirements: `AGENTS.md`, the registered workflow descriptor, the full plan, tasks, and `*-re-audit-3.md` in this folder.
- Focused feature command: `python -m unittest discover -s tests/linear_delivery_repository_memory -t . -v` — **exit 0**, 17 tests.
- Existing contract command: `python -m unittest tests.test_delivery_contracts ... -v` — the 21 valid `tests.test_delivery_contracts` cases ran; `test_repository_satisfies_delivery_contracts` failed because `dist/manifest.json` is stale for the new canonical sources. The two additionally named supervisor modules did not exist under those names. This is expected RM-06 projection work and is not the basis of the RM-01–RM-05 verdict.
- Existing supervisor subset: `python -m unittest tests.linear_delivery_supervisor.test_contracts tests.linear_delivery_supervisor.test_cli_wrapper tests.linear_delivery_supervisor.test_status_cleanup -v` — timed out after 124 seconds without output; unverified.

## Findings

### P1 — Promotion trusts caller-created authority and non-authoritative workflow files

`RepositoryMemory.promote()` accepts an arbitrary `authorization` mapping and an arbitrary caller-provided `consume_authorization` callback. The only enforcement is that the callback invokes the supplied `persist_prepared` closure; there is no call to an engine-owned authorization consumer, reservation validator, or registry-bound workflow resolver (`repository_memory.py:255-295`, `357-374`). The focused tests demonstrate the bypass by supplying `lambda _e, _r, persist: persist()` as the complete authority implementation (`tests/linear_delivery_repository_memory/test_promotion.py:108-111`, with the same pattern throughout the query/index/context fixtures).

The provenance check reads mutable checkout-local `workflow.json` files directly and even treats a missing descriptor `repositoryId` as matching the manifest (`repository_memory.py:117-144`). It never resolves either curation or source workflow through the authoritative registry, validates the live head/worktree identity, or requires the engine-owned autonomous docs attestation. Consequently, a caller that can invoke the library can fabricate the evidence mapping/callback and local descriptors and create reviewed-looking repository records and the commit marker without the ordinary reservation/`AuthorizeMutation` authority required by the plan.

Required correction: promotion must be reachable only through an engine-owned unlocked authorization primitive under the canonical repository mutex; resolve curation/source identities through the registry, validate live repository/head/worktree state and mode-specific docs evidence, and make it impossible for a caller callback or evidence-shaped object to stand in for authority. Add negative tests that use forged descriptors, callbacks, grants, stale heads, wrong physical worktrees, and missing autonomous attestations.

### P2 — Marker-last creation is not crash-recoverable and can report an invalid marker as committed

The reviewed protocol requires final record bytes, marker bytes, and the next index to be prepared, flushed, and read back under state home before any repository target is created. The implementation persists only a small journal, then serializes/writes records directly into the repository; it creates no prepared record, marker, or index files (`repository_memory.py:357-403`). Replay never reads the journal. If a process dies after record N but before the marker, the next call encounters the existing target and fails `stale-record-target` (`repository_memory.py:324-335`) instead of verifying an exact prepared prefix and resuming or performing proof-bound rollback. Cleanup depends only on the current process's in-memory `created` list and exact complete bytes, not durable pre-absence/create-intent/prefix proof (`repository_memory.py:422-429`).

The marker replay path checks only the marker's self-digest and matching request digest, then returns `promoted`; it does not validate the marker's repository/manifest binding or reread its complete bound record set (`repository_memory.py:317-321`, `431-450`). An exception during marker readback can also leave a marker on disk while `marker_committed` is still false and trigger record rollback. These behaviors violate the valid-marker sole commit point and whole-batch recovery guarantees.

Required correction: implement phase-exact durable prepared files and journaled ownership, validate/recover every create boundary, set commitment from a fully validated marker rather than an in-memory flag, and reconstruct results only after complete marker/record binding validation. Add process-death fixtures at every record/marker/index/result boundary, partial-write/prefix and ambiguous-owner cases, missing/corrupt journal/result/index cases, and cross-process/linked-worktree contenders.

### P2 — RM-01 strict contract and digest-projection parity is incomplete

There are no schemas or registered runtime validators for the required atomic promotion request/result contracts. `promotion_batch_request()` and `_reconstruct_result()` return unchecked dictionaries (`repository_memory.py:147-183`, `431-450`). Several present schemas leave security- and digest-relevant nested objects open: promotion candidates are unrestricted objects (`repository-memory-promotion.schema.json:7`), index markers/entries/diagnostics/counts are unrestricted (`repository-memory-index.schema.json:4`), result items/diagnostics are unrestricted (`repository-memory-result.schema.json:4`), and context `authenticated` is unrestricted (`repository-memory-context-envelope.schema.json:4`). Runtime checks do not close all of those inventories.

Only five of the named canonical projections have functions (`contracts.py:521-558`); there are no explicit `PromotionBatchRequestV1`, `RetrievalQueryV1`, `RetrievalResultV1`, or `ContextEnvelopePayloadV1` projection contracts. The purported known-answer test checks only generic canonical JSON and one generic hash, not the required manifest, record, request, marker, result, index, envelope, and accounting byte strings/hashes or field-boundary tampering (`tests/linear_delivery_repository_memory/test_contracts.py:13-43`).

Required correction: add strict additional-properties-false request/result and nested schemas, exact runtime inventories, every named acyclic projection, and real known-answer/tamper/replay fixtures for each layer.

### P2 — Source freshness, graph/lifecycle, and committed-predecessor rules are incomplete

Promotion validates manifest `sourceArtifacts` but never verifies that each candidate provenance entry belongs to that approved source set or rereads every candidate provenance digest before commit (`repository_memory.py:109-144`, `324-356`). For versions greater than one it loads the predecessor directly from the record path without proving that the predecessor is owned by a valid marker or is the current terminal record (`repository_memory.py:325-330`), so an uncommitted orphan can seed `createdBy` and a newly committed successor that later quarantines itself.

The index never evaluates provenance digests, `freshness.reviewAfter`, or `retention.reviewAt`; every entry is initialized with `stale: False` and only expiry is computed (`repository_memory_index.py:211-236`). The graph projection checks missing links, branches, and cycles but does not enforce current terminal fan-in, restoration only from an archived predecessor, or the prohibition on restoring/reproducing a redacted chain (`repository_memory_index.py:125-157`; `contracts.py:688-701`). Retrieval later collapses all record/source/path failures into a generic `stale` count (`repository_memory.py:546-557`), which loses the required visible corrupt/missing/quarantine distinctions.

Required correction: bind candidate provenance to approved exact sources and validate it before authority consumption; require marker-owned terminal predecessors and all reviewed lifecycle rules prospectively; derive fresh/stale/review-due/expired and safe graph state deterministically in the index; preserve bounded reason-specific diagnostics. Add the full lifecycle, graph, source-drift, legacy, and injected-clock matrices named by RM-03/RM-04.

### P2 — The context adapter accepts spoofed selectors and does not enforce post-composition selector equality

The public memory CLI accepts the object named `authenticated` directly from its request file (`cli.py:666-705`). `compose_context()` checks only that the object has eight keys and that repository ID/key match the retrieval result (`repository_memory.py:630-639`). It does not obtain those values from authenticated engine state, bind query `work`/stage to workflow/issue/stage, validate provider/boundary/mutation scope, or compare those selectors after composition. The emitted authenticated section then discards all selectors except stage and the envelope digest (`repository_memory.py:651-658`). A caller can therefore retrieve one work/stage and label the delivered tool context as another authenticated workflow, issue, stage, provider, boundary, or mutation scope.

The equal-width final character/byte accounting itself is implemented and the focused adversarial strings pass, but the test matrix never exercises selector drift, spoofed CLI authentication, omission 9→10, count 9,999→10,000, maximum budgets, wrapper-only failure, or independently measured adapter-owned final messages (`tests/linear_delivery_repository_memory/test_context.py:12-55`).

Required correction: construct selectors from engine-owned authenticated state, bind the query and delivery to exact workflow/issue/stage/boundary/provider identities and non-authorizing mutation-scope digest/count evidence, verify equality immediately before emission, and add the required cross-work/stage and accounting-boundary fixtures.

### P2 — Path/state-home and secret isolation do not meet the reviewed boundary

The default library state root is caller-controlled and, when omitted, is created inside the repository (`repository_memory.py:189-207`), contrary to the repository-bound shared state-home design and the prohibition on caller-chosen output roots. Without a supplied `StatePathGuard`, state files and the mutex use bespoke path handling. `safe_repository_path()` rejects a symlink leaf and resolves the current parent, but it does not reject hard-linked files and has a check/use gap before `mkdir`/create (`repository_memory_records.py:40-60`, `74-90`).

The global secret check rejects redactor-detected string values and a small list of raw-authority key spellings, but it does not reject general secret-like keys (`contracts.py:201-209`, `421-431`); assertion/provenance metadata can therefore carry names such as `api_key` when the value itself does not trigger redaction. No focused test covers reparse/junction/hard-link aliases, state-root substitution, secret-like keys, or path races.

Required correction: require the canonical registry-bound state home and `StatePathGuard` for operational library/CLI use, harden no-follow/hard-link-safe opens and creation, and enforce conservative secret-like key and value rejection across every persisted/returned contract. Add Windows reparse/hard-link and cross-repository/state-home tests.

### P3 — Status omits required build/input observations and regression coverage is too shallow

Status is bounded and does not rebuild, but its public memory summary omits the plan-required last marker/input digest and build observation; it exposes only `indexSemanticSha256`, counts, and a generic error code (`repository_memory.py:679-709`). The focused status test checks only the missing-index shape and unchanged operation names, not a healthy, stale, corrupt, cross-repository, authority-sentinel, or mutation-free snapshot (`tests/linear_delivery_repository_memory/test_context.py:50-55`).

Required correction: add the bounded non-authorizing input/build observation fields and exercise healthy/corrupt/cross-repository/status-stability cases through `SupervisorEngine.status()` and the public CLI.

## Passing observations

- The repository commit marker is written after record targets during the uninterrupted happy path, with create-new, flush, and readback primitives.
- Marker scanning excludes an invalid marker's entire batch and excludes unmarked records from retrieval.
- Duplicate grouping uses the complete canonical scope and assertion map, preserving strict assertion supersets.
- Query ordering and whole-item byte removal are deterministic in the covered fixtures.
- Context strings are placed in a fixed tool-role payload and escaped for the reviewed delimiter/control characters; equal-width six-digit final accounting passes the covered cases.
- `SupervisorEngine.OPERATION_NAMES` is unchanged and status does not implicitly rebuild.

These passing points do not offset the authority, recovery, contract, selector, and isolation blockers above. This review grants no implementation, Git, provider, tracking, workflow-advancement, publication, or merge authority.
