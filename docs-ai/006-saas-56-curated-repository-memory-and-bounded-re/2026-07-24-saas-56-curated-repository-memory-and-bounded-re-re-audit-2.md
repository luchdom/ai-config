# SAAS-56 curated repository memory and bounded retrieval — Independent re-audit 2

## Verdict

**FAIL** — two P2 findings and one P3 finding. The latest revision resolves the prior digest-cycle, candidate-batch cardinality, provenance-confidence, prompt-context budget, and exact-gate omissions in substantial detail. However, the atomic batch commit order remains internally contradictory and the record-level duplicate rule can discard unique assertions. Both are observable correctness/fail-closed defects, so implementation is not ready without material correction and a fresh audit.

## Required focus-area disposition

| Focus area | Disposition | Audit conclusion |
|---|---|---|
| Acyclic named digest projections | **PASS** | Plan §5.5 defines exact `CandidateIntentV1`, `PromotionManifestPayloadV1`, `RecordPayloadV1`, `PromotionBatchRequestV1`, `IndexSemanticV1`, `RetrievalQueryV1`, `RetrievalResultV1`, `ContextEnvelopePayloadV1`, and `ContextDeliveryV1` projections. Manifest payload contains no record digest; record payload may bind the already-known manifest payload digest; final file digests live only in journal/result/index. Canonical JSON/hash rules and known-answer/tamper fixtures are explicit. No self-hash or manifest↔record cycle remains. |
| Atomic multi-candidate batch/recovery | **FAIL (P2)** | Candidate IDs, whole-batch authorization, 1/2/32 cardinality, no subsets, prepared bytes, no-clobber creates, candidate-boundary journaling, rollback/protection, and concurrency fixtures are specified. The final index/journal commit order nevertheless exposes a non-atomic visibility gap and contradicts `RM-03`; see finding 1. |
| Structural assertion/conflict/confidence | **FAIL (P2)** | Typed normalized keyed assertions, provenance topology, weakest-confidence derivation, scope intersection, exact value conflict, and no prose/model judgment are specified. The record-level deduplication condition is incomplete and can hide nonduplicate assertions; see finding 2. |
| Final context-envelope budgeting | **PASS with P3 clarification** | Plan §9.1 and task `RM-05` charge the complete fixed developer/tool bundle after every escape, enforce requested/repository item/Unicode-scalar/UTF-8 limits, remove whole lowest-ranked items, and fail without delivery if the fixed wrapper cannot fit. Worst-case min/default/max tests cover actual delivered bytes. The remaining P3 concerns exact accounting-field semantics, not the cap mechanism. |
| Complete exact-head/merge gates | **PASS** | Plan §11 and task `RM-06` require a distinct fresh clean worktree at exact provider-observed PR head for aggregate exit 0, independent exact-diff review, acceptance-mapped QA, and docs/projection/link verification with exact evidence; authorized squash merge follows only after all four. Another distinct fresh clean worktree runs the aggregate at the exact returned merge SHA. Earlier dirty and hosted checks are explicitly non-substitutes. |

## Findings

### P2 — Index visibility and journal commitment cannot satisfy the stated atomic-batch invariant

The batch protocol says only a `committed` journal/result makes the batch current, and `RM-03` says the index excludes every target belonging to a noncommitted/protected batch. But plan §6 step 5 orders the writes as:

1. all record targets exist;
2. rebuild and atomically replace the index **including the entire batch**;
3. persist the `committed` journal/result.

Between steps 2 and 3, or after a crash there, the visible index contains the batch while its journal is noncommitted. If retrieval trusts the new index, it exposes an uncommitted batch. If retrieval enforces the journal state, the index is not a self-contained committed projection and every query must safely join mutable operation state. If `RM-03` literally excludes noncommitted targets during rebuild, step 2 cannot build the required committed index until after step 3, while step 3 currently requires the committed index digest. The two separate files cannot become visible atomically by ordering alone.

The problem persists across loss/corruption of state-home promotion journals. Curated records do not carry `batchPromotionId`, complete ordered batch membership, or a repository-owned commit marker; the manifest is approval input and intentionally not completion evidence. Therefore a rebuild scanning the fixed authoritative record root cannot distinguish all committed records from a crash-created strict subset if the journal/result is missing. It either risks admitting a partial batch or fails to rebuild from curated sources, contrary to the source-of-truth architecture and Linear's deterministic rebuild/repair requirement.

Evidence:

- Plan §4 two-tier source-of-truth architecture.
- Plan §5.1 record fields, §5.2 manifest approval semantics, and §5.3 index projection.
- Plan §6 steps 4–7, especially “Only this journal state makes the batch current.”
- Plan §8 rebuild requirement.
- Tasks `RM-02` committed result ordering and `RM-03` noncommitted-batch exclusion.
- Linear `SAAS-56`, idempotent approved promotion, crash/replay/concurrent promotion, and deterministic rebuild/repair requirements.

Required correction: define one recoverable commit point with no exposure window and no disposable-state dependency. A repository-owned immutable batch commit marker included in the exact authorized scope can bind the manifest payload, complete ordered target/digest set, and batch identity; rebuild can then include records only when the complete marker-bound set validates. Alternatively, redesign publication so a single atomic repository namespace operation makes the whole set visible and the index is rebuilt only after that durable commit. In either design, order journal/result/index transitions so a crash yields either the old index or a reconstructably committed batch, never an index that presents noncommitted records. Specify missing/corrupt journal behavior and add a query racing the index-before-journal boundary plus total state-home loss/rebuild fixtures.

### P2 — The duplicate-group rule can suppress records containing unique assertions

Plan §8 says that across intersecting terminal records, an equal key/type/value is compatible and, when complete scopes are equal, the index forms one duplicate group and returns only the highest-ranked record. It does not require the complete canonical assertion maps to be equal.

For example, two same-scope records may both contain `runtime.python = "3.13"`, while one additionally contains `validation.command = "python scripts/validate.py"` and the other contains `build.command = "python scripts/build.py"`. The shared assertion is compatible and their scopes are equal, so the written rule groups the whole records and suppresses one, losing a unique reviewed assertion. Different keys “never conflict” does not make the records duplicates.

This is deterministic but violates the goal of retrieving relevant curated knowledge and makes output depend on rank rather than assertion completeness. Current tests ask for equal-value grouping and different-key non-conflict, but do not explicitly cover partial overlap/superset records and preservation of unique assertions.

Evidence:

- Plan §5.1 multi-assertion records.
- Plan §8 Structural duplicate/conflict rules.
- Plan §11 structural assertion fixtures.
- Tasks `RM-03` duplicate/conflict acceptance criteria.

Required correction: define record duplicates only when complete canonical scope **and complete canonical assertion map** are equal (with an explicit decision about display/provenance differences), or perform assertion-level deduplication while preserving the union and provenance of unique assertions. Add same-scope identical-map, strict-superset, partial-overlap, disjoint-key, same-key-conflict, and differing-provenance fixtures. Retrieval must prove no unique assertion disappears solely because another record shares one compatible key/value.

### P3 — Final accounting fields need a precise self-accounting convention

`ContextDeliveryV1` includes count-only accounting values, while final character/byte counts cover the complete serialized delivery containing those decimal values. The plan says to recompute accounting, digest, and serialization until the caps fit, but does not state whether `charactersUsed`/`bytesUsed` must equal the final serialization containing themselves, whether they describe a named projection that excludes the accounting fields, or what fixed-point/convergence algorithm is canonical at digit boundaries.

This does not undermine the newly explicit final cap—the implementation can always measure the emitted bytes and drop an item—but it can cause schema/runtime/fixture disagreement about reported usage.

Evidence:

- Plan §5.5 `ContextEnvelopePayloadV1`/`ContextDeliveryV1`.
- Plan §9.1 final budgeting/recomputation.
- Tasks `RM-01` and `RM-05`.

Required correction: name the accounting projection and define whether usage values are inclusive or excluded. If inclusive, require deterministic iteration to a stable final serialization and rejection on nonconvergence; publish a known-answer fixture at a decimal digit boundary. Assert reported counts exactly match the chosen projection and emitted delivery stays within the independent caps.

## Prior audit finding disposition

- Audit 1's six P2 findings remain materially resolved: the package now owns docs-stage promotion provenance, creation/update identity, topology confidence, archive/restoration, exact rank/budget constants, forward-only supersession, crash/concurrency mechanics, and a mechanical untrusted prompt boundary.
- Re-audit 1's digest-cycle finding is resolved by §5.5's named acyclic projections and final-file-digest placement.
- Re-audit 1's singular promotion-flow finding is resolved at the contract level by ordered atomic 1–32 candidate batches, complete exact authorization scope, no subsets, candidate identities, whole-batch results, and candidate-boundary recovery. The remaining P2 is the final visibility/commit-point defect, not missing batch cardinality.
- Re-audit 1's semantic conflict/confidence finding is mostly resolved by typed keyed assertions and structural provenance topology. The remaining P2 is the narrower but material record-deduplication condition.
- Re-audit 1's context-expansion finding is resolved by final `ContextDeliveryV1` accounting after escaping and wrapper insertion.
- Re-audit 1's exact-head task mismatch is resolved in both the plan and `RM-06`.

## Checks that passed

- The goal/non-goals remain aligned with Linear: local curated records, no raw-history ingestion, no vector/network dependency, no uncontrolled accumulation, and no memory-derived product/security/mutation authority.
- The optional docs-owned manifest is registered as current-layout workflow evidence, supports manual/semi/autonomous and explicit legacy sources, records zero candidates durably, and does not retrofit completed evidence or authenticate a role.
- Record/source/workflow/repository/worktree identity, path normalization/containment, redaction, secret rejection, lifecycle, retention, archive/restoration, supersession, staleness, and bounded quarantine remain fail-closed and append-only.
- Named digest projections are acyclic, exact, bounded, tamper-evident, and accompanied by known-answer requirements.
- Batch candidate ordering, identities, exact authorization scope, no-clobber target creation, predecessor ordering, protected ambiguity, whole-batch failure results, and real concurrency/fault fixtures are otherwise implementation-ready.
- Assertion values and confidence are structural rather than natural-language/model decisions; display prose is non-decisional and current sources remain authoritative.
- Retrieval filters/ranking, result item/character/byte budgets, provenance/source reread, omission behavior, and deterministic repeat output are exact.
- Prompt context is opt-in, tool-role, escaped, fixed-precedence, selector-independent, stage-bound, and finally budgeted across the actual developer/tool delivery.
- Status remains bounded, redacted, observation-only, does not rebuild, and does not expand the existing supervisor operation union.
- Design is correctly not required. Tasks are ordered, repository-specific, bounded, source-first, generated-output-safe, and retain distinct audit/review/QA/docs/publication/merge/post-merge owners.
- `src/` remains canonical, `dist/` is build-generated, `python .\scripts\validate.py` remains the repository aggregate, and exact identities/evidence are mandatory at PR head and returned merge SHA.
- The current registered `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/` layout is valid. This audit does not mutate Linear, Git, workflow authority, or source artifacts.

## Sources consulted

- `AGENTS.md`
- Linear issue `SAAS-56`, including full description, acceptance criteria, test notes, documentation impact, dependencies, non-goals, status, labels, and relations (read-only on 2026-07-24)
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/workflow.json`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-plan.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-tasks.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-audit.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-re-audit.md`
- `src/skills/goal-to-delivery/references/{artifact-contract,autonomous-runtime-contract,clarification-policy,completion-boundaries,delivery-stages,quality-gates}.md`
- `src/skills/goal-to-delivery/references/work-descriptor.schema.json`
- `src/skills/linear-delivery-loop/scripts/{reservations,store,operations,publication_records,supervisor}.py`
- `src/skills/linear-delivery-loop/references/publication-state.schema.json`
- Installed `task-audit-breakdown` skill and independent audit checklist
