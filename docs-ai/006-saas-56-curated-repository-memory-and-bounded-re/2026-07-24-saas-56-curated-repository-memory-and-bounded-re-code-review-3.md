# SAAS-56 curated repository memory and bounded retrieval — Code review 3

## Verdict

**PASS** — zero P1 findings, zero P2 findings, and zero P3 findings for the repaired RM-01–RM-05 review boundary. The prior journal/authorization P1, both remaining P2s, and the isolation/CLI test-adequacy P3 are resolved in the current working tree.

## Review boundary and evidence

- Reviewed base: `main` / `1a5190f1815ae25b0a3cba6e81b50ae221c62052`.
- Reviewed target: the exact current uncommitted tracked and untracked SAAS-56 RM-01–RM-05 working-tree implementation on 2026-07-24.
- Requirements: `AGENTS.md`; registered workflow descriptor; full plan, tasks, and `*-re-audit-3.md`; code reviews 1 and 2 in this folder.
- `python -m unittest tests.linear_delivery_repository_memory.test_contracts -v` — **exit 0**, six tests, 31.312 seconds.
- Targeted authority/source/graph command containing five named `PromotionTests` — **exit 0**, five tests, 74.639 seconds:
  - `test_authority_transition_faults_never_make_journal_itself_authoritative`
  - `test_actual_process_termination_after_prepared_journal_requires_authoritative_retry`
  - `test_current_delivery_source_requires_registry_identity_while_legacy_null_is_explicit`
  - `test_prospective_graph_accepts_ordered_chain_and_rejects_double_successor_before_consumption`
  - `test_manifest_and_source_replacement_at_mutex_boundary_fail_before_consumption`
- Targeted CLI/status command containing two named `ContextTests` — **exit 0**, two tests, 24.524 seconds:
  - `test_public_memory_cli_query_rebuild_repair_and_context`
  - `test_supervisor_status_reports_healthy_cross_repository_and_corrupt_index_without_repair`
- No build/aggregate command was run because RM-06 generated projections and final clean-head gates remain a later delivery stage and would mutate generated files in this review-only handoff.

## Prior finding disposition

### PASS — P1 journal/consumed-authorization atomic proof

- Promotion acquires the canonical mutex, recovers any torn paired store transaction, rereads the state/reservation pair, and never treats journal presence alone as sufficient (`repository_memory.py:391-410`, `431-458`).
- On replay, the request is accepted only with its exact validated digest and authorization identity. Before any repository create, promotion checks that the request's authorization ID is present in authoritative `consumedAuthorizationIds`; if absent, it must re-enter the engine-owned authorization consumer and prove the post-commit readback (`repository_memory.py:679-703`).
- The unlocked consumer still persists prepared evidence before the consumed pair, but `commit_pair_unlocked()` supplies recoverable transaction evidence. Promotion calls `recover_unlocked()` before consulting consumption state, so a torn pair deterministically reaches its authoritative before/after decision (`reservations.py:624-648`; `repository_memory.py:391-394`).
- Fault coverage now spans before/after prepared evidence, before/within/after the consumed commit, before/after opaque cleanup, and an actual child-process termination after the prepared journal. The targeted tests prove that a journal without authoritative consumption cannot create records/marker and that exact retry converges only after authority is proven.

### PASS — P2 under-lock current-source validation and prospective in-batch graph

- Manifest bytes/value, registry, descriptors, source files/digests, head, physical worktree, and mode-specific attestation are reread/revalidated under the repository mutex before request preparation or authority consumption (`repository_memory.py:391-410`; `validate_promotion_manifest_source()` at `129-211`).
- Under `current-completion-v2`, every `docs-ai/` source requires non-null workflow/work identity, completion stage, exact registry folder/work key, descriptor identity/stage, inventory membership, and current digest. Explicit legacy compatibility retains its separate null-identity fallback (`repository_memory.py:156-189`).
- Candidate provenance must match the approved exact path/digest set. The prospective graph maintains a canonical-order terminal set and known-record map, so an earlier candidate may satisfy a later candidate while a second successor, missing/nonterminal predecessor, duplicate identity, restore mismatch, redacted revival, or invalid prepared graph fails before consumption (`repository_memory.py:486-589`, `648-668`).
- Targeted tests cover current-null rejection versus explicit legacy, ordered v1→v2 acceptance, double-successor rejection before consumption, and manifest/source replacement at the mutex boundary.

### PASS — P2 registered strict request/result schemas and real-object projections

- `repository-memory-batch-request.schema.json` and `repository-memory-promotion-result.schema.json` are strict, versioned, additional-properties-false contracts registered in `MEMORY_SCHEMA_FILENAMES` and `MEMORY_RUNTIME_CONSTRAINTS` (`contracts.py:59-69`, `201-210`).
- Runtime dispatch validates both registered contracts; the batch request binds canonical candidate order, exact record-plus-marker scope/operation, safe paths, repository/head/worktree identity, and its acyclic request digest. Promotion results enforce the no-candidate and committed/reconstruction cross-field inventories.
- Manifest candidates and nested record/index/query/result/context structures are closed by schema plus exact runtime inventories; `assert_runtime_parity()` now includes the two new schema files.
- Contract tests use full real-layer manifest, record, request, marker, committed result, index, context envelope, and accounting objects, compare canonical bytes/digests, and exercise included/excluded boundary tampering. The six-test contract suite passes.

### PASS — P3 path/state/secret isolation, CLI compatibility, status, and bounded tests

- Repository file reads reject symlink/reparse and hard-link aliases; creates use create-new plus `O_NOFOLLOW` where available and verify link count. Operational memory requires one canonical manager/store/reservation assembly and canonical state home.
- Secret-like assertion keys and redactor-detected values fail closed. The focused isolation test covers hard links, reparse aliases when the platform permits them, and cross-state assembly rejection.
- The public memory CLI keeps the existing engine operation union unchanged and successfully exercises query, rebuild, repair, and registry-authenticated context through `--repository-memory-request`.
- Supervisor status remains mutation-free and bounded while reporting healthy, cross-repository/corrupt, marker/input/build observations, and safe error state. The targeted public CLI/status tests pass.

## Other reviewed behavior

- Marker-last create-new/readback remains the sole repository-memory commit point; valid marker replay revalidates the complete bound record set.
- Prepared record, marker, and index bytes are durable before repository creation; post-marker failures reconstruct derived state without rollback.
- Index/query behavior retains deterministic source freshness, lifecycle, duplicate/conflict, provenance, ranking, whole-item budget, and bounded diagnostic semantics.
- Context remains fixed developer precedence plus tool-role escaped untrusted data, engine-derived selector evidence, and exact equal-width inclusive final accounting.
- Memory records, markers, indexes, results, context, and status remain non-authorizing evidence and do not expand supervisor operation, provider, tracking, Git, publication, or merge authority.

## Remaining delivery gates

This PASS covers independent code review of RM-01–RM-05 only. RM-06 durable documentation, generated `dist/` projections, repository aggregate, runtime QA, exact clean PR-head gates, authorized publication/merge, and exact returned-merge-SHA validation remain separate required stages. This review grants none of that authority.
