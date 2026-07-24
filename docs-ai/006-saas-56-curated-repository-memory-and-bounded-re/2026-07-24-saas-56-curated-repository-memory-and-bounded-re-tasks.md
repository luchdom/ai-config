# SAAS-56: Add curated repository memory and bounded retrieval — Execution Tasks

## Status and authority

- Workflow `8417f24e-b7e5-456e-9755-ff3befebeb2f`, `$goal-to-delivery` semi-autonomous, repository `ai-config`, completion boundary `merge`; design is not required.
- All six code-bearing tasks target only `C:\dev\luchdom\ai-config` and land as one scoped change set and one primary PR / authorized squash-merge boundary. `dist/` is generated only by `python .\scripts\build.py`.
- These tasks confer no reservation, mutation, workflow, provider, tracking, publication, or merge authority. Manifests, records, index, results, context, and status are non-authorizing evidence. No raw ingestion, seed curation, implicit autonomous load, vector/network capability, or evidence-only publication work is in scope.

## Audit notes

- Light completeness check: the latest plan fixes the digest projections, atomic batch behavior, typed assertion semantics, final-delivery context accounting, and exact clean-worktree gates. Each is made implementation-observable below.
- The independent auditor must verify schema/runtime/test parity for every named projection and all batch phases, and that final prompt-wrapper accounting—not retrieval accounting alone—governs actual delivered context.
- These notes are tasker completeness notes, not an independent audit verdict or permission to implement.

## Dependency graph

`RM-01 contract/projections` → `RM-02 atomic promotion batches` → `RM-03 index assertion/graph lifecycle` → `RM-04 bounded retrieval` → `RM-05 final context/CLI/status` → `RM-06 docs/projections/exact gates` → `one primary PR / merge boundary`.

### RM-01 — Define strict contracts, typed assertions, and acyclic digest projections

- Goal: Implement version `1.0` strict schemas/runtime parity for record, manifest, batch request/result, index, query/result, context envelope/delivery, the optional docs-owned artifact, and all named canonical hash projections.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: `src/skills/linear-delivery-loop/references/repository-memory-{record,promotion,index,query,result,context-envelope}.schema.json`; `src/skills/linear-delivery-loop/scripts/contracts.py`; canonicalization/digest helpers; `src/skills/goal-to-delivery/references/artifact-contract.md`; focused contract fixtures and base descriptor parity tests.
- Acceptance criteria:
  - Register optional `<date>-<slug>-memory-promotion.json`, owned/produced only by `docs-as-code`, stored/inventoried only in a distinct curation workflow. Require `batchPromotionId`, ordered 1–32 candidates by canonical lowercase `candidateId`, stable distinct candidate/candidate-promotion IDs, `promotion-approved` or idempotent `no-candidates`; it is evidence, never authority.
  - Add immutable repository commit-marker schema/path `docs/repository-memory/commits/<batch-promotion-id>.json`. `BatchCommitPayloadV1` binds repository/batch/manifest/request identities and the complete ordered candidate/promotion ID, record target, intent, payload, and final-file digest set; marker file adds only `batchCommitPayloadSha256`. A marker has no empty/partial set, a target belongs to one valid marker only, and it is the sole durable repository-memory commit point.
  - Define `CandidateIntentV1`, `PromotionManifestPayloadV1`, `RecordPayloadV1`, `PromotionBatchRequestV1`, `BatchCommitPayloadV1`, `IndexSemanticV1`, `RetrievalQueryV1`, `RetrievalResultV1`, `ContextEnvelopePayloadV1`, and `ContextDeliveryAccountingV1` as exact acyclic projections using canonical sorted-key, compact, `ensure_ascii=true` UTF-8 JSON and lowercase `sha256:<64-hex>`. Records bind candidate intent/manifest payload/record payload digests but never their own file digest; marker/index/journal/result hold downstream final-file digests only.
  - Publish known-answer canonical byte strings and expected hashes for one-candidate manifest, record, request, marker, committed result, index, envelope, and accounting projection; tampering every included/excluded boundary field fails appropriately and exact construction/replay is byte-identical without self-hash cycles.
  - Replace free-text facts with 0–16 keyed assertions: normalized key, `equals`, typed `string`/integer/boolean/string-set value, and 1–8 provenance refs. Validate NFC/trim/collapsed-whitespace strings, bounded safe integers, native booleans, sorted unique normalized string sets, keys/types/value/provenance topology; title/summary are display-only and never decide confidence, duplicate, conflict, or authority.
  - Derive active confidence from assertion provenance topology only: `current-source-bound`, `source-evidence-bound`, `legacy-evidence-bound`; record confidence is weakest assertion. Content-free archive/redaction uses `not-applicable`. Preserve exact creation/update evidence identities and lifecycle/freshness/retention bounds from the plan.
- Local test and runtime QA notes: Test all types/normalization/limits, source category/ref topology, confidence weakening, artifact inventory, no-candidate, legacy source, projection known answers, digest replay and layer tampering, schema/runtime inventories. No model/prose parsing is permitted in fixtures.
- Documentation impact: RM-06 explains contracts; this task owns only minimal canonical artifact ownership.
- Dependencies / blocks: First task; all later code consumes these fixed contracts.
- Risks and non-goals: Do not add a registry, schema dependency, or authority model.
- Completion/publication boundary: Worktree-complete after focused tests; included in the single PR/merge.

### RM-02 — Promote one atomic ordered 1–32 candidate batch with whole-batch recovery

- Goal: Validate docs-owned provenance and append one authorized batch without overwrite, partial committed success, scope drift, or ambiguous replay.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: new `src/skills/linear-delivery-loop/scripts/{repository_memory.py,repository_memory_records.py}`; existing workflow/registry/redaction/state primitives; approved supervisor/store mutex and unlocked authorization primitive; `tests/linear_delivery_repository_memory/test_promotion.py`.
- Acceptance criteria:
  - Resolve manual/semi/autonomous/legacy sources exactly; validate curation inventory/stage/head/worktree/digests (autonomous also exact passed docs attestation). `no-candidates` yields one durable no-op with no mutation authorization/journal. A promotion-approved manifest is only input, never a committed result.
  - Require one authorization with `targetOperationId=batchPromotionId` and sorted scope exactly equal to all 1–32 record targets plus the deterministic commit-marker target—no subset, wildcard, missing, or extra target. Same batch/candidate/candidate-promotion ID plus changed data is `conflicting-replay`; all candidates/targets/intents must be unique.
  - Persist `repository-memory/promotions/<batch-id>/journal.json`; lock only the repository `allocation.lock`, atomically consume/revalidate the exact authorization and write `prepared`, then prepare/flush/readback all candidate bytes in engine-owned state-home files before any repository target exists.
  - Under the sole lock, prospective-validate all targets, predecessor dependencies, assertion/scope duplicates/conflicts, and expected prior index digest. Any failure happens before consumption/create; post-winner stale contenders fail as an entire batch.
  - Create record targets in canonical order using create-new/no-clobber only, journal before/after each candidate, read back exact bytes, then create/readback the complete marker using the same no-clobber rule. Marker success is sole durable commit: index/result failure afterwards yields only `index-reconstruction-required`; query/rebuild reconstruct complete marker-bound state. No per-candidate index, overwrite fallback, subset retry, or partial success result.
  - Before marker creation, deterministic failure rolls back only exactly journal-proven, pre-absent, complete/prefix-owned records/engine temps; ambiguity is `protected-incomplete`. After valid marker creation, never roll back/hide the batch; reconstruct journal/result/index from marker if state home is absent/corrupt. Unmarked/protected records remain index-excluded.
- Local test and runtime QA notes: Fixtures for 1/2/32 candidates, exact record-plus-marker authorization scope, marker/request/record tamper, first/middle/last duplicate/conflict/stale target, dependency ordering, no-candidate, every record and marker create/readback boundary, sole index replacement, result commit, query race at marker-before-index, and full state-home loss/corruption. Real cross-process/linked-worktree contenders prove one atomic marker winner, whole-batch loser, no overwrite/lost version/partial visibility or success/split-brain/unsafe cleanup/deadlock.
- Documentation impact: RM-06 owns manifest, batch, recovery, and legacy guidance.
- Dependencies / blocks: Depends on RM-01; RM-03 consumes only committed record batches.
- Risks and non-goals: Never rewrite source history, mint authority, or silently reallocate a target.
- Completion/publication boundary: Worktree-complete with fault/concurrency fixtures; same PR/merge.

### RM-03 — Project typed assertion topology, duplicates/conflicts, graph, and lifecycle into the index

- Goal: Build deterministic repository-bound derived state from committed records only, including typed scope conflict/deduplication and immutable forward-only lifecycle graph.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: `repository_memory_index.py`, record modules, state guard/mutex primitives, `tests/linear_delivery_repository_memory/test_index.py`.
- Acceptance criteria:
  - Scan valid marker root plus each complete marker-bound record set only; unmarked files are never inputs. Atomically readback a compact index with marker-set semantic/file digests, repository/tree binding, safe lifecycle/graph/conflict counts; query can transiently reconstruct the same complete marker-derived projection without mutating missing/corrupt state home.
  - Scope intersects only when repository matches and work/stage/path/topic dimensions each intersect under exact wildcard/ancestor rules. Duplicate grouping requires byte-identical complete canonical scope *and* complete canonical assertion map; choose representative deterministically while retaining every member's bounded display and provenance metadata. Strict subset/superset, partial overlap, disjoint assertions, or equal maps under different scopes stay distinct so unique assertions never disappear. Same key with different type/value conflicts; different keys do not. Batch duplicate/conflict rejects the entire batch; display text never decides grouping.
  - Immutable records have only forward `supersedes`; derive reverse/terminal state. Enforce same-record immediate predecessor, v1 2–8 terminal fan-in only, one successor per predecessor, no branch/cycle/cross-repo/missing/nonterminal link. Explicit successor/consolidation resolves a conflict; runtime never uses prose, timestamps, or models.
  - Implement archive/restoration/redaction/retention/staleness exactly as reviewed append-only successors and computed state; rebuild/repair modifies only derived state, quarantines malformed input, and never deletes/rewrites curated records.
- Local test and runtime QA notes: Full typed scope wildcard/path-ancestor duplicate/conflict matrix; graph branch/cycle/fan-in/reverse terminal tests; archive/restore/redaction/expiry clock tests; noncommitted batch exclusion; enumeration/tamper/reparse/hard-link/corrupt index/atomic interruption/cross-worktree recovery fixtures.
- Documentation impact: RM-06 owns lifecycle and conflict guidance.
- Dependencies / blocks: Depends on RM-01–02; provides retrieval eligibility/status state.
- Risks and non-goals: Index is disposable and never auto-resolves semantic conflict or repairs source records.
- Completion/publication boundary: Worktree-complete with index/lifecycle fixtures; same PR/merge.

### RM-04 — Retrieve deterministic provenance results within exact query budgets

- Goal: Filter/rank/reread committed records and return canonical safe results within fixed item, Unicode-character, and UTF-8 byte ceilings.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: `repository_memory.py`, index/record modules, contracts, `tests/linear_delivery_repository_memory/test_query.py`.
- Acceptance criteria:
  - Require exact repository and bounded work/stage/path/topic filters; default to terminal active nonstale/nonexpired/nonconflicting/nonarchived/nonredacted/nonlegacy records. Reread record/source digests before return; drift is safe stale exclusion.
  - Enforce plan-fixed rank (work, path/ancestor, stage, topics, topology confidence, kind, version, record ID, filename) and limits 8/12,000/24,576 defaults, 1/1,000/4,096 minima, 32/48,000/98,304 maxima. Validate marker/record set on every return; no network, callbacks, embeddings, model ranking, or filesystem-order influence.
  - Count full canonical items JSON for Unicode scalars and final canonical retrieval document for bytes; include provenance/rank/digests/diagnostics, select count then characters then remove lowest whole items for bytes. Never truncate; oversized candidates omit deterministically, empty result remains valid.
- Local test and runtime QA notes: Filter/rank tie matrix; ASCII/multibyte/NFC/escaped values; every metadata/provenance/diagnostic charge; minimum/default/maximum, item larger than remaining/all, byte removal after character selection, no truncation, canonical repeat/tamper/stale result fixtures.
- Documentation impact: RM-06 owns retrieval bounds/provenance docs.
- Dependencies / blocks: Depends on RM-01–03; blocks RM-05.
- Risks and non-goals: Retrieval is read-only evidence and not direct prompt concatenation.
- Completion/publication boundary: Worktree-complete after behavioral suites; same PR/merge.

### RM-05 — Deliver final budgeted untrusted context and safe operational/status surfaces

- Goal: Compose opt-in retrieval only through `ContextDeliveryV1`, strict operations, and observation-only status.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: `src/skills/linear-delivery-loop/scripts/{cli.py,supervisor.py,repository_memory.py,contracts.py}`; focused context/CLI/status tests and supervisor regressions.
- Acceptance criteria:
  - Tool-role-only `repository_memory_context` uses escaped `ContextEnvelopePayloadV1`; fixed developer precedence is outside untrusted data. Authenticated repository/workflow/issue/stage/boundary/provider/mutation inputs alone select query; post-composition equality drift or unsupported role fails closed. Memory strings are never decoded as markup/template/nested command/shell/tool call.
  - Canonically escape `<`, `>`, `&`, backticks, controls, U+2028/U+2029, quotes, and backslashes. `ContextDeliveryV1` exactly contains fixed developer message, named tool message/escaped envelope, authenticated stage/digests/count-only accounting, no timestamp/self-digest. Fixed wrapper is <=800 scalars and <=2,048 bytes.
  - `ContextDeliveryAccountingV1` replaces only `accounting.charactersUsed`/`bytesUsed` with fixed six-ASCII-digit `"000000"` sentinels; final delivery stores zero-padded six-digit computed inclusive counts. Replacing sentinel values is equal-width under all caps, so final canonical scalar/UTF-8 lengths must equal reported counts exactly or fail `context-accounting-invariant` with no delivery.
  - Re-serialize final delivery after escaping; enforce requested/repository item/character/byte limits against final wrapper, not only retrieval. On overage remove whole lowest-ranked item, update ordinary included omission diagnostics/digest, and reserialize; wrapper-only overflow is `context-budget-too-small`, with no memory messages. Stages may cite only evidence and cannot derive commands, scope, completion, authority, or selection.
  - CLI/library accepts only strict contracts; promotion retains RM-02 authority, query read-only, repair/rebuild derived-only. Existing operation union stays unchanged. Status is bounded/redacted/mutation-free and excludes bodies, journals, paths, inputs, and authority values.
- Local test and runtime QA notes: At minimum/default/maximum for planner, implementer, reviewer, QA inject worst-case repeated escaping characters, controls and multibyte text plus malicious role/delimiter/tool/shell/merge/provider/mutation content. Prove exact final ContextDeliveryV1 inclusive char/byte caps, whole-item removal, wrapper-only/accounting-invariant failure, valid structural tool envelope, unchanged authenticated state, no authority field/command, and mutation-free status. Publish known answers across omission 9→10 and serialized count 9,999→10,000 digit boundaries.
- Documentation impact: RM-06 owns opt-in context/trust-boundary/status docs.
- Dependencies / blocks: Depends on RM-01–04.
- Risks and non-goals: No trusted memory role, implicit autonomous loading, queue/Linear/notification/provider/Git capability.
- Completion/publication boundary: Worktree-complete with four-stage adversarial final-delivery tests; same PR/merge.

### RM-06 — Document the durable contract, regenerate projections, and enforce exact clean-worktree gates

- Goal: Publish durable guidance and collect the distinct source/build/docs/review/QA evidence required for the one primary merge.
- Target repository: `C:\dev\luchdom\ai-config`.
- Likely files/modules: `src/skills/linear-delivery-loop/references/repository-memory.md`; `docs/repository-memory/README.md`; `README.md`; `src/skills/luchdom-docs/references/doc-targets.md`; canonical artifact contract; generated `dist/`.
- Acceptance criteria:
  - Document projections/digest evidence, immutable marker path/sole commit point, marker-based rebuild/state-home loss/orphan handling, atomic batch recovery, assertions/topology confidence/conflicts, lifecycle, inclusive ContextDeliveryAccountingV1 bounds, authority/trust boundaries, rebuild/repair/status, rollout/rollback. Link docs instead of copying raw evidence or canonical protocol.
  - Run focused suites, existing regressions, build, projection/link checks, and `python .\scripts\validate.py` as early feedback.
  - At exact provider-observed PR head, use a distinct fresh clean worktree (clean before/after) to run aggregate `python .\scripts\validate.py` exit 0, independent exact-diff review, applicable acceptance-mapped runtime QA, and `$docs-as-code` exact docs/projection/link verification. Record exact SHA, command/arguments, tool versions, timestamps, exit codes, and evidence paths.
  - Only then may authorized squash merge occur. At exact returned merge SHA, use another distinct fresh clean worktree (clean before/after) and rerun aggregate `python .\scripts\validate.py` exit 0 with exact evidence. Earlier/dirty worktree or hosted checks do not substitute.
- Local test and runtime QA notes: Docs stage does not replace independent audit, review, or QA; missing/failed exact-head or merge-SHA item is not completion.
- Documentation impact: Owns durable docs and generated projections.
- Dependencies / blocks: Depends on RM-01–05 plus distinct audit/review/QA/docs/publish authority.
- Risks and non-goals: Do not edit `dist/` directly, create empty PR work, auto-enable memory, or claim Git-history redaction.
- Completion/publication boundary: One authorized PR/squash merge after all exact-head gates; merge complete only after returned-SHA aggregate.

## Sources consulted (paths)

- `AGENTS.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/{workflow.json,2026-07-24-saas-56-curated-repository-memory-and-bounded-re-plan.md,2026-07-24-saas-56-curated-repository-memory-and-bounded-re-audit.md,2026-07-24-saas-56-curated-repository-memory-and-bounded-re-re-audit.md,2026-07-24-saas-56-curated-repository-memory-and-bounded-re-re-audit-2.md,2026-07-24-saas-56-curated-repository-memory-and-bounded-re-re-audit-3.md}`
- `C:/Users/lucas/.codex/skills/task-audit-breakdown/{SKILL.md,references/task-template.md}`
- `src/skills/goal-to-delivery/references/{artifact-contract,delivery-stages,quality-gates,completion-boundaries,autonomous-runtime-contract}.md`
- `src/skills/goal-to-delivery/scripts/{workflow_init,registry,descriptor,state_home,state_paths,redaction}.py`
- `src/skills/linear-delivery-loop/scripts/{contracts,supervisor,store,operations,publication_records}.py`
- `src/skills/linear-delivery-loop/references/{supervisor-core.md,publication-state.schema.json}`
- `src/skills/{docs-as-code,luchdom-docs}/`, `README.md`, `scripts/{build,validate}.py`, `tests/{goal_to_delivery_base,linear_delivery_supervisor,test_delivery_contracts.py}`
