# SAAS-56 curated repository memory and bounded retrieval — Independent re-audit

## Verdict

**FAIL** — four P2 findings and one P3 finding. All six findings from the first audit have been materially addressed at the architectural level, but the revised plan/tasks introduce or expose four new implementation-blocking contract gaps. Implementation must not begin until the planner/tasker correct them and a fresh independent audit passes.

## Prior finding disposition

| Prior finding | Disposition | Evidence in revised package |
|---|---|---|
| Documentation-stage promotion provenance had no feasible source contract | **Resolved** | Plan §5.2 chooses one optional `<date>-<slug>-memory-promotion.json` artifact, assigns `$docs-as-code` ownership, stores/inventories it only in a distinct curation workflow, defines manual/semi/autonomous and legacy validation, and represents `no-candidates`; tasks `RM-01`/`RM-02` own the protocol and fixtures. The new digest and multi-candidate defects below are separate flaws in that chosen contract. |
| Record omitted creation/update identity, confidence, and archive semantics | **Resolved** | Plan §5.1 defines closed `createdBy`/`updatedBy`, confidence and freshness; §8 defines append-only archive/restoration/redaction/retention. Tasks `RM-01`/`RM-03` carry exact schema/runtime and lifecycle fixtures. |
| Retrieval ordering and budgets were deferred to implementation | **Resolved** | Plan §7 and task `RM-01` fix field/cardinality limits, exact item/character/byte defaults/minima/maxima, Unicode-scalar accounting, complete rank order, kind/confidence priority, and boundary fixtures. The post-retrieval context expansion defect below remains new. |
| Immutable versions contradicted reciprocal supersession links | **Resolved** | Plan §8 uses forward-only immutable `supersedes` links and derives reverse/terminal state in the index, with bounded consolidation, branching/cycle quarantine, archive/restoration, and redaction rules. Task `RM-03` owns the graph projection and tests. |
| Promotion lacked crash/concurrency protocol and tests | **Resolved** | Plan §6 and task `RM-02` define one repository mutex, operation journal, exact authorization binding, compare-create/no-overwrite behavior, phase recovery, exact temporary cleanup, and real cross-process/linked-worktree contention tests. The multi-candidate and digest issues below prevent that protocol from being complete, but the original concurrency/recovery omission itself is corrected. |
| Prompt-injection handling was not an enforceable context boundary | **Resolved** | Plan §9.1 and task `RM-05` define an opt-in tool-role untrusted envelope, trusted precedence outside data, canonical escaping, no decoding/command parsing, authenticated-selector equality checks, stage-specific evidence use, and adversarial fixtures for all four consumers. The context-size accounting issue below is distinct from the trust-boundary correction. |

## New findings

### P2 — Manifest, record, and digest fields form undefined self-referential and mutual digest cycles

The revised contract requires each record to contain a `content digest`; its `createdBy`/`updatedBy` contains the SHA-256 manifest digest. Each manifest candidate in turn contains the resulting curated-record digest. Promotion then binds and readbacks the manifest digest, target record digest, and journal request hash before publishing the record.

If the record digest covers the canonical record file, its embedded digest is self-referential. Even if `content digest` means a payload-only digest, the manifest digest still depends on the candidate's resulting record digest while the resulting record contains the manifest digest. No canonical projection/exclusion rule breaks that cycle, and no post-write result artifact is defined to hold the final file digest instead. An implementer therefore cannot deterministically construct the two immutable files or test exact digest agreement without inventing a material serialization rule.

Evidence:

- Plan §5.1 lines defining record content digest and manifest digest in `createdBy`/`updatedBy`.
- Plan §5.2 `promoted` candidate shape requiring resulting curated-record digest.
- Plan §6 journal/request/readback rules.
- Tasks `RM-01` record/manifest digest agreement and `RM-02` target digest/readback criteria.

Required correction: define named canonical digest projections for every digest. State exactly which fields are excluded or replaced with a sentinel before hashing. Break the manifest/record cycle explicitly—for example, have the manifest bind a candidate payload digest and target identity while a separate promotion result/journal binds the final record-file digest, or make the record bind a manifest payload digest that excludes all resulting-record digests. Add known-answer fixtures proving serialization, manifest construction, record construction, tamper rejection, and exact replay.

### P2 — The 1–32 candidate manifest has only a single-record promotion transaction

The manifest permits one to 32 candidates and the Linear mapping says the documentation owner promotes zero or more candidates idempotently. The promotion request/flow, however, has one `promotionId`, one proposed record target, one filename/version/digest, one predecessor set, one final record path, and one compare-create. Tasks likewise describe a single exact new record path/version.

The package does not say whether a multi-candidate manifest is promoted atomically as one operation, through one operation per candidate, or through a selected subset. It does not define candidate identity/idempotency keys, authorization scope for all targets, ordering, partial success, rollback/replay after candidate N, cross-candidate conflicts/dependencies, index rebuild frequency, or the final result shape. `createdBy`/`updatedBy` also requires a promotion UUID, but the manifest shape does not bind one promotion ID per candidate.

This is observable behavior for the first Linear acceptance criterion and changes the crash/concurrency protocol materially.

Evidence:

- Linear `SAAS-56`, acceptance that a completed workflow proposes zero or more candidates and approved promotion is idempotent/versioned.
- Plan §5.2 candidate cardinality and §5.4 singular proposed target.
- Plan §6 singular journal/request/record phases.
- Tasks `RM-01` manifest cardinality and `RM-02` singular transaction acceptance.

Required correction: choose exact batch semantics. If promotion is per candidate, give every candidate a stable candidate/promotion identity, define authorized subset selection, independent journal/result, ordering, replay, and how one manifest can end partially promoted without misreporting completion. If promotion is atomic batch, bind the complete ordered target set and authorization scope, define prepare/no-clobber/all-record publication, crash recovery and conflict behavior for every phase, and one deterministic index/result commit. Add 2-, 32-, partial-failure, conflicting-candidate, and concurrent-batch fixtures.

### P2 — Conflict and confidence claims still depend on undefined semantic judgment over free text

Records contain a free-text summary and zero to 16 bounded facts. Promotion is required to detect an overlapping active record with “incompatible normalized facts,” and confidence classes assert that “every claim” is directly supported or corroborated by current sources/evidence. The plan defines scope overlap, normalization, source digests, and confidence vocabulary, but it never defines a machine-decidable fact identity, contradiction relation, claim-to-source binding, or deterministic validation algorithm.

String normalization can determine equality, not whether two different natural-language facts conflict or whether a source semantically supports them. Letting the implementer or model decide violates deterministic rebuild/promotion requirements; treating every unequal fact in overlapping scope as conflicting is also an unstated and likely unusable product rule. Merely checking that current-source digests exist does not enforce the stated confidence meaning.

Evidence:

- Plan §5.1 free-text content and confidence definitions.
- Plan §6 conflict rule and §8 conflict behavior.
- Tasks `RM-01` “closed confidence evidence,” `RM-02` conflict behavior, and `RM-03` conflict projection.
- Linear `SAAS-56`, deterministic validation/conflict requirements and prohibition on implicit trust in model prose.

Required correction: make conflict and confidence validation structural. Define facts as closed keyed assertions with explicit normalized identity/value/comparison semantics and per-assertion source bindings, or limit deterministic conflict to an explicitly declared conflict/supersession set reviewed in the docs-owned manifest and describe confidence as a provenance class rather than machine proof of semantic support. Specify scope intersection, duplicate/deduplication rules, incompatible-value rules, manifest assertions, and positive/negative fixtures without runtime model judgment.

### P2 — Context-envelope escaping can exceed the requested and repository-owned byte budget

Retrieval enforces `maxCharacters` on canonical `items` JSON and `maxBytes` on the complete canonical retrieval-result document. Context composition then reserializes those items with additional escaping for `<`, `>`, `&`, backticks, controls, U+2028/U+2029, quotes, and backslashes. Several of these transformations expand one scalar into multiple ASCII bytes. Neither plan §9.1 nor task `RM-05` recharges the final tool-role envelope or drops whole lowest-ranked items after context serialization.

As a result, a retrieval result that fits the 98,304-byte repository maximum can produce a substantially larger prompt-context message. That breaks the bounded-context goal and the configured item/character budget's purpose at the actual planner/implementer/reviewer/QA consumption boundary. Field limits provide an outer bound, but not the declared caller-selected/repository-owned bound.

Evidence:

- Linear `SAAS-56`, bounded digest context and configured item/character budget requirements.
- Plan §7 character/byte accounting and §9.1 additional context escaping.
- Tasks `RM-04` result accounting and `RM-05` context-envelope construction/tests.

Required correction: define and enforce final envelope accounting after all trust-boundary escaping. Either use the exact same canonical escaped representation for retrieval accounting and context embedding, or add envelope maxima and deterministically remove lowest-ranked whole items until the final serialized tool message fits. Include trusted wrapper text, keys, digests, accounting, and escaped item content in the charge. Add worst-case repeated escapable-character fixtures at min/default/max budgets and prove the final bytes delivered to each stage never exceed the requested/repository cap.

### P3 — RM-06 does not restate the full exact-head evidence set

The plan and canonical quality contract correctly require the aggregate at the exact PR head in a fresh clean worktree and exact-head review, applicable QA, and docs evidence. `RM-06` says to run build/validate and separately names only exact-head review and QA. Its goal references exact-head gates, so the package is not materially ambiguous when read with the plan, but the execution task should name the exact-head aggregate and docs evidence explicitly to prevent an earlier dirty-worktree validation from being misreported as final-head acceptance.

Evidence:

- Plan §11 Repository gates and Linear acceptance-to-evidence mapping.
- Task `RM-06` acceptance criteria.
- `src/skills/goal-to-delivery/references/quality-gates.md`.

Required correction: update `RM-06` to require exact-head aggregate, review, applicable QA, and docs evidence in the fresh clean PR-head worktree, then the aggregate in another clean worktree at the exact returned merge SHA, with exact commands/SHAs/exit codes recorded by the proper owners.

## Checks that passed

- The observable goal, local-only architecture, no-network/no-vector non-goals, source-of-truth precedence, raw-history exclusions, repository identity, fixed record root, path containment, redaction, and authority separation remain aligned with Linear and repository instructions.
- The optional docs-owned artifact is a concrete, versioned provenance decision rather than a role-string grant. It keeps earlier completed/current-layout and historical evidence read-only and routes legacy curation through a new registered workflow.
- Creation/update identity, confidence vocabulary, freshness states, lifecycle, archive/restoration, redaction, retention, append-only forward graph, derived reverse links, and no-delete policy now have bounded owners and tests.
- Rank order, field/cardinality bounds, item/Unicode-character/UTF-8-byte limits, canonical omission behavior, source reread, and deterministic result output are explicit at the retrieval-result boundary.
- Repository/worktree binding, registry lookup, exact-path mutation authority, single mutex, no-clobber compare-create, journal recovery, derived-only repair, bounded quarantine, and status non-mutation are preserved.
- Prompt data is opt-in, tool-role, escaped, labeled untrusted, subordinate to trusted policy outside the data, and mechanically prohibited from supplying selectors/configuration/commands/authority. All four consumer stages receive adversarial fixtures.
- Manual, semi-autonomous, autonomous, and legacy provenance paths remain distinct without changing advancement or clarification policy. Healthy autonomous prompt doctrine is not bulk-expanded and implicit loading stays disabled.
- Design remains correctly not required for the repository-data/runtime/CLI/documentation change.
- `src/` remains canonical, `dist/` generated, the aggregate remains `python .\scripts\validate.py`, and audit/review/QA/docs/publication/merge/post-merge ownership remains distinct.
- The current helper-registered workflow identity/layout remains valid; this re-audit reads Linear only and does not grant implementation, Git/provider, tracking, reservation, or workflow authority.

## Sources consulted

- `AGENTS.md`
- Linear issue `SAAS-56`, including full description, acceptance criteria, test notes, documentation impact, dependencies, non-goals, status, labels, and relations (read-only on 2026-07-24)
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/workflow.json`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-plan.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-tasks.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-audit.md`
- `src/skills/goal-to-delivery/references/{artifact-contract,autonomous-runtime-contract,clarification-policy,completion-boundaries,delivery-stages,quality-gates}.md`
- `src/skills/goal-to-delivery/references/work-descriptor.schema.json`
- `src/skills/linear-delivery-loop/scripts/{reservations,store,operations,publication_records,supervisor}.py`
- `src/skills/linear-delivery-loop/references/publication-state.schema.json`
- Installed `task-audit-breakdown` skill and independent audit checklist
