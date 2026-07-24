# SAAS-56 curated repository memory and bounded retrieval — Independent re-audit 3

## Verdict

**PASS** — zero P1 findings, zero P2 findings, and one P3 finding. The latest plan/tasks are implementable without material clarification. The immutable repository commit marker closes the prior visibility/rebuild gap; complete-map deduplication preserves unique assertions; `ContextDeliveryAccountingV1` removes self-accounting ambiguity; and the exact-head/merge evidence sequence is complete. The remaining P3 is audit-source traceability only and does not block implementation.

## Required focus-area validation

### PASS — Immutable repository commit marker, authorization, and sole commit point

- `docs/repository-memory/commits/<batch-promotion-id>.json` is an immutable repository-owned marker, not machine-local derived state.
- One issued `AuthorizeMutation` scope must equal the union of every one-to-32 exact record target plus the one deterministic marker target. Missing, extra, wildcard, subset, or replacement paths are rejected.
- Records are prepared and create-new/read back first; the marker is created last with create-new, flush, and exact readback. Its valid durable presence is the sole promotion commit point.
- Before the marker, all records are uncommitted and invisible. Proof-bound rollback may remove only exact batch-created pre-marker files; ambiguity protects rather than guesses. After a valid marker, rollback is forbidden and recovery may only reconstruct derived state or use later reviewed successors.
- Marker creation binds the full ordered batch; strict subsets, duplicate ownership, absent/mismatched records, wrong paths, IDs, or digests invalidate/exclude the whole named batch.
- The normal query/promotion/rebuild/repair paths serialize on the existing repository mutex, so a concurrent query sees the old complete marker set or the new complete marker set, never in-progress records.

Evidence: plan §§4, 5.3–5.5, 6; tasks `RM-01`–`RM-03`; promotion/query-race fixtures in plan §11 and `RM-02`.

### PASS — Digest acyclicity and named canonical projections

- `CandidateIntentV1` excludes its intent digest.
- `PromotionManifestPayloadV1` contains candidate intent digests but no record/marker/index/result digest.
- `RecordPayloadV1` is constructed only after the manifest payload digest and excludes its record payload digest; the record-file digest is downstream only.
- `PromotionBatchRequestV1` binds authorization/repository/manifest/ordered targets without record/marker result digests.
- `BatchCommitPayloadV1` is constructed only after all record bytes/digests and excludes its own payload digest; marker-file digest remains downstream.
- `IndexSemanticV1`, retrieval, context-envelope, and delivery-accounting projections explicitly exclude or sentinel only their named fields. No projection hashes itself or a value that depends on it.
- Canonical sorted-key compact `ensure_ascii=true` UTF-8 JSON, lowercase SHA-256 syntax, exact field inventories, known-answer byte strings, replay, and boundary tamper tests make schema/runtime parity observable.

Evidence: plan §5.5 and §11 contract fixtures; tasks `RM-01`, `RM-02`.

### PASS — Atomic multi-candidate recovery and total state-home loss

- Promotion is exactly one ordered atomic batch for one, two, or 32 candidates; selected subsets and per-candidate success are forbidden.
- Candidate/batch/promotion identities, target uniqueness, predecessor ordering, prospective graph/conflict validation, exact authorization scope, prepared bytes, no-clobber creation, and candidate/marker boundary journals are explicit.
- A valid marker remains authoritative if journal, result, or index is absent/corrupt. A committed journal without a marker has no effect.
- Query validates the current repository marker-set digest. A stale, divergent, missing, or corrupt index is ignored and the complete marker-derived projection is built transiently without mutation.
- After process death at marker-before-index, the next query returns the complete newly committed marker-bound batch. Invalid markers exclude their entire batch while independently valid batches remain available with bounded diagnostics.
- After total state-home loss, markers plus their complete record sets deterministically reconstruct the exact index/result. Unmarked crash leftovers remain excluded and are never automatically deleted.
- Fault fixtures cover every record/marker/index/result boundary, query races, journal loss/corruption, state-home deletion, protected ambiguity, and real cross-process/linked-worktree contenders.

Evidence: plan §6, §8 rebuild, §11 promotion/rebuild fixtures; tasks `RM-02`–`RM-04`.

### PASS — Structural assertion, conflict, confidence, and whole-map duplicates

- Free-text facts are replaced by bounded typed keyed assertions with exact normalization, `equals` comparison, safe numeric range, canonical sets, and explicit provenance references. Title/summary are display-only.
- Confidence is explicitly provenance topology, not machine proof of prose: assertion confidence is derived from source categories and record confidence is the weakest assertion class.
- Scope intersection is deterministic across repository/work/stage/path/topic dimensions with explicit wildcard and ancestor behavior.
- A duplicate group requires byte-equal complete canonical scope **and** byte-equal complete canonical assertion map. The semantic map excludes provenance intentionally; all distinct provenance metadata and suppressed record IDs remain bounded and preserved.
- Strict subset/superset, partial overlap, disjoint maps, and equal maps under different scopes remain separate eligible records. Unique assertions cannot disappear merely because another record shares one compatible key/value.
- Same shared key with different type/value conflicts; different keys do not. Conflict resolution requires explicit reviewed supersession/consolidation, never timestamps, fuzzy matching, prose parsing, or model judgment.
- Fixtures explicitly cover identical maps, display/provenance differences, strict subset/superset, partial overlap, disjoint keys, different scopes, conflicts, and unique-assertion preservation.

Evidence: plan §§5.1, 8, 11; tasks `RM-01`, `RM-03`.

### PASS — Exact `ContextDeliveryAccountingV1` and final prompt budgets

- Accounting covers the complete adapter-owned canonical developer/tool bundle after all JSON-within-JSON escaping, roles, names, fixed trusted text, authenticated fields/digests, omissions, punctuation, and both accounting fields. Only provider transport framing outside the object is excluded.
- `ContextDeliveryAccountingV1` replaces only the two usage values with fixed six-character `"000000"` sentinels. Requested/repository maxima are below 100,000, so substitution with zero-padded six-digit results cannot change serialized length.
- The adapter measures the sentinel projection, substitutes both results once, then independently verifies final emitted scalar/UTF-8 lengths equal the reports exactly. Mismatch fails closed with no delivery; no iterative self-count ambiguity remains.
- Variable-width omission counts are updated before measurement. If the final escaped bundle exceeds either requested cap, the whole lowest-ranked item is removed and the complete accounting/digest procedure repeats. Wrapper-only overflow returns no memory messages.
- Known-answer and adversarial fixtures cover minimum/default/maximum caps, worst-case escape expansion, omission 9→10, serialized counts 9,999→10,000, actual delivered bytes, wrapper-only failure, and all four consumer stages.

Evidence: plan §§5.5, 9.1, 11; tasks `RM-01`, `RM-05`.

### PASS — Exact-head, merge, and post-merge evidence

- Implementation-time focused suites/build/aggregate are early feedback only.
- Final PR-head acceptance uses a separate fresh clean worktree at the exact provider-observed head, clean before and after.
- The four exact-head gates are explicitly: `python .\scripts\validate.py` exit 0, independent exact-diff/head review, applicable acceptance-mapped runtime QA, and `$docs-as-code` verification of exact docs/links/generated projections/docs impact.
- Exact SHA, commands/arguments, tool versions, timestamps, exit codes, and evidence paths are required. Hosted or earlier dirty-worktree checks cannot substitute.
- Authorized squash merge occurs only after all exact-head gates. A second distinct fresh clean worktree checks the exact returned merge SHA and reruns the aggregate to exit 0; failure or absence is not completion.
- Audit, implementation, review, QA, docs, publication, merge, and post-merge ownership/authority remain distinct.

Evidence: plan §11 Repository gates and §17 mapping; task `RM-06`; canonical quality/completion contracts.

## Prior audit finding disposition

- **Audit 1, six P2:** resolved. Promotion provenance, creation/update identity, confidence/archive, rank/budget constants, append-only supersession, crash/concurrency behavior, and the mechanical untrusted-context boundary are fixed and tasked.
- **Re-audit 1, four P2 and one P3:** resolved. Digest projections are acyclic; promotion is a whole ordered batch; assertion/confidence decisions are structural; final context is charged after wrapping/escaping; exact-head docs/aggregate evidence is explicit.
- **Re-audit 2, two P2:** resolved. The marker-last repository commit point removes the non-atomic index/journal visibility dependency and enables total-state-loss reconstruction. Duplicate grouping now requires identical complete scope and assertion map, preserving unique assertions.
- **Re-audit 2, one P3:** resolved. `ContextDeliveryAccountingV1` defines inclusive exact self-accounting through equal-width sentinels and digit-boundary known answers.

## Finding

### P3 — Revised task source inventory omits the three re-audit artifacts

The task package's `Sources consulted` lists the original audit but not `*-re-audit.md`, `*-re-audit-2.md`, or this correction lineage, even though its Audit notes and criteria directly implement those findings. The plan likewise lists the original audit lineage incompletely. The omission does not create implementation ambiguity because the corrections are fully incorporated and independently verified above, but it weakens durable traceability from finding to task revision.

Evidence:

- Tasks `Sources consulted (paths)`.
- Prior audit artifacts in the registered workflow folder.

Recommended correction: in the next task artifact revision, list every audit/re-audit artifact actually used. Do not overwrite historical audit evidence.

## Other checks that passed

- The observable goal/non-goals and Linear acceptance map remain complete: curated local memory, no bulk raw history, no vectors/network dependency, no uncontrolled accumulation, and no memory-derived workflow/product/security/provider/mutation authority.
- Exact registry/workflow/repository/worktree identity, fixed roots, path normalization/containment, reparse/hard-link tests, source reread, redaction, secret rejection, and safe diagnostics remain fail closed.
- Manual, semi-autonomous, autonomous, and explicit legacy provenance share the memory contract without changing their advancement or clarification policies. No completed source workflow is retrofitted or rewritten.
- Lifecycle, freshness, retention, archive/restoration, redaction, forward-only supersession, bounded consolidation, conflict visibility, and derived-only repair are deterministic and append-only.
- Retrieval filters/ranking, result item/character/byte limits, whole-item omission, provenance, source digest validation, stable repeat output, and no-network/model ranking are exact.
- Status remains bounded, redacted, observation-only, excludes authority and bodies, and performs no implicit rebuild. The existing supervisor operation union remains unchanged.
- Design is correctly not required. Tasks are ordered, bounded, repository-specific, dependency-aware, and assign plausible canonical source/test/documentation locations.
- `src/` remains canonical, `dist/` build-generated, and rollback preserves committed curated history while removing only reproducible derived state unless a separately reviewed lifecycle change authorizes otherwise.
- The current registered workflow folder and identity are valid. This audit grants no reservation, mutation, Git/provider, tracking, workflow advancement, publication, or merge authority.

## Sources consulted

- `AGENTS.md`
- Linear issue `SAAS-56`, including full description, acceptance criteria, test notes, documentation impact, dependencies, non-goals, status, labels, and relations (read-only on 2026-07-24)
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/workflow.json`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-plan.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-tasks.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-audit.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-re-audit.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-re-audit-2.md`
- `src/skills/goal-to-delivery/references/{artifact-contract,autonomous-runtime-contract,clarification-policy,completion-boundaries,delivery-stages,quality-gates}.md`
- `src/skills/goal-to-delivery/references/work-descriptor.schema.json`
- `src/skills/linear-delivery-loop/scripts/{reservations,store,operations,publication_records,supervisor}.py`
- `src/skills/linear-delivery-loop/references/publication-state.schema.json`
- Installed `task-audit-breakdown` skill and independent audit checklist
