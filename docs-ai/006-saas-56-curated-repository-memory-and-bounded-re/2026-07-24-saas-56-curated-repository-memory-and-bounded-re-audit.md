# SAAS-56 curated repository memory and bounded retrieval — Independent audit

## Verdict

**FAIL** — six P2 findings. The two-tier architecture, authority separation, repository binding, status non-mutation, generated-output discipline, and merge-boundary gates are directionally sound, but the current plan/tasks are not implementable without material contract decisions and do not cover several explicit Linear requirements. Any P2 fails the pre-implementation gate. Implementation must not begin until the planner/tasker correct the package and a fresh independent audit passes.

## Findings

### P2 — Documentation-stage promotion provenance has no feasible, complete source contract

The plan requires every promotion to validate a documentation-owner manifest produced during an authorized docs stage and bound to exact input paths/digests, proposed scope, target/source references, and resulting record identity. It simultaneously admits that durable evidence for non-autonomous completed workflows may not exist and directs implementation to pause if it cannot be obtained. The tasker's Audit notes repeat that unresolved dependency, and `RM-02` explicitly blocks on clarification.

The existing canonical artifact contract has no documentation-stage artifact type: it assigns plan, optional design, tasks, audit, code review, QA, and completion artifacts. `workflow.json` inventories only registered workflow artifacts and currently has no docs-stage promotion manifest. Existing publication attestations can prove a `docs` gate at an exact SHA through an issued provenance hash, but their contract does not bind the proposed memory fields, source paths/digests, resulting record identity, or a per-candidate zero-or-more decision. Consequently, an implementer must invent whether the source is a new workflow artifact, a completion payload member, a publication attestation extension, or another durable record. That choice affects artifact ownership, schema compatibility, completed manual/semi-autonomous workflows, and canonical protocol scope.

Evidence:

- Plan §6 item 3 and §16 final paragraph.
- Tasks Audit notes item 2 and `RM-02` dependencies/blocks.
- `src/skills/goal-to-delivery/references/artifact-contract.md`, current layout and artifact ownership.
- `src/skills/linear-delivery-loop/scripts/publication_records.py`, `validate_publication_attestation` exact fields.
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/workflow.json`, current artifact inventory.

Required correction: choose and specify one versioned durable promotion-provenance contract before implementation. Define its canonical owner, storage/inventory location, producer and validation path for manual, semi-autonomous, and autonomous completed workflows, zero-candidate representation, compatibility behavior for earlier completed workflows, exact digest/identity bindings, and how it remains evidence rather than mutation authority. Update `RM-01`, `RM-02`, and fixtures accordingly. If this requires a canonical artifact/protocol change, own that change explicitly rather than leaving it conditional on implementation discovery.

### P2 — The record contract omits required Linear fields and explicit archive semantics

Linear requires each record to bind creation/update identity, a confidence class, and freshness/supersession state, and requires explicit retention, archive, rebuild, and repair behavior. The proposed record fields include timestamps, `promotedByRole`, lifecycle, and retention, but no closed confidence class and no defined creation/update identity. A descriptive role is neither a stable creation/update identity nor authority. The lifecycle vocabulary has `active`, `superseded`, `redacted`, and `retired`, but neither the plan nor tasks defines whether `retired` is the required archive state, how archive is requested, or how archive differs from expiry/retirement/redaction.

This gap is absent from `workflow.json` acceptance criteria as well, showing that the issue-to-workflow mapping lost source scope before tasking.

Evidence:

- Linear `SAAS-56`, Scope bullets for record bindings and explicit retention/archive behavior.
- Plan §5.1 and §8.
- Tasks `RM-01` and `RM-03` acceptance criteria.
- `workflow.json`, `acceptanceCriteria`.

Required correction: add closed, bounded creation/update provenance identity and confidence-class semantics to schema/runtime parity and fixtures. Define archive as a precise lifecycle transition or explicitly map it to a named existing state with request, visibility, retrieval, retention, and restoration behavior. Restore these source requirements to the acceptance/evidence map and task criteria.

### P2 — Deterministic retrieval leaves acceptance-critical ordering and budget decisions to implementation

The plan specifies the ranking dimensions but never defines the `kind` priority. It requires repository-owned maxima but provides no exact `maxRecords`, `maxBytes`, title/summary/fact limits, topic/path limits, or deterministic accounting rules for provenance and diagnostic overhead. The tasks tell the auditor to verify that hard maxima are selected "in schema/runtime code," even though this is a pre-implementation audit and no code exists. These values govern context size and denial-of-service resistance and cannot be delegated to the implementer as incidental constants.

Linear additionally requires a configured item/**character** budget. The package silently substitutes UTF-8 bytes and does not define whether character and byte ceilings coexist, which Unicode unit a character budget uses, or why byte-only behavior satisfies the source requirement. Canonical byte output can be useful, but it is not the stated acceptance contract.

Evidence:

- Linear `SAAS-56`, Scope and Acceptance criteria for configured item/character budgets and deterministic ordering.
- Plan §5.3, §7, and §16.
- Tasks Audit notes item 3, `RM-01`, and `RM-04`.

Required correction: specify exact repository-owned defaults/maxima, the complete kind-priority table, normalization and tie behavior, and precisely which serialized fields count toward each limit. Preserve the Linear character budget with a defined Unicode counting unit, or obtain an explicit source-level decision that a byte budget replaces it; if both exist, define enforcement order and omission accounting. Add exact boundary fixtures for multibyte text, metadata/provenance overhead, a single record larger than the remaining/all budget, and stable repeated results.

### P2 — Immutable versions contradict required reciprocal supersession links

The plan says prior curated versions are immutable and promotion never rewrites an earlier record. It also requires supersession to have reciprocal validated `supersedes`/`supersededBy` links. A newly appended successor can name its predecessor, but the already immutable predecessor cannot acquire `supersededBy` after the successor identity exists. The tasks repeat both immutable-prior-version and reciprocal/cross-field expectations without supplying a separate append-only edge/tombstone mechanism or defining the index as the sole reverse-link projection.

This is not a cosmetic schema choice: it changes the canonical digest of prior records, replay identity, conflict resolution, terminal-successor calculation, redaction behavior, and Git review history.

Evidence:

- Plan §5.1 lifecycle fields, §6 item 6, and §8 Supersession.
- Tasks `RM-01`, `RM-02`, and `RM-03`.
- Linear `SAAS-56`, acceptance criterion requiring versioned idempotent promotion that preserves superseded history without presenting it as current.

Required correction: choose one append-only representation. For example, require only successor-to-predecessor links in immutable records and derive reverse links/terminal state in the index, or define a separate immutable lifecycle-edge record. Specify version-vs-record succession, branching/fan-in rules, cycle detection over the full graph, redaction/tombstone interaction, and deterministic conflict behavior; then align schemas, tasks, and fixtures.

### P2 — Promotion lacks the required crash/concurrency protocol and tests

Linear explicitly calls for crash/replay and concurrent-promotion coverage. The package gives the derived index shared-mutex, atomic-replacement, interruption, and cross-worktree tests, but `RM-02` does not require promotion record writes or next-version allocation to run under a repository-scoped concurrency protocol. Its readback and replay tests do not prevent two promoters from both observing the same latest version and selecting/writing the same next filename with different content, nor do they define recovery from interruption between curated-record persistence and index rebuild.

Because curated records are repository changes while the index is machine-local state, simply reusing the state-home mutex also needs an explicit lock ordering and failure contract; otherwise promotion can deadlock with rebuild/status or leave a valid new record paired with an old index and ambiguous replay result.

Evidence:

- Linear `SAAS-56`, Test notes for crash/replay and concurrent promotion.
- Plan §4.2, §6 item 6, and §11 rebuild/repair fixtures.
- Tasks `RM-02` and `RM-03` acceptance/test notes.

Required correction: define the promotion transaction boundary, repository-scoped lock/compare-and-create behavior, lock ordering relative to index rebuild, atomic file creation/readback, idempotency key and conflicting-replay result, and recovery for crashes before record creation, after record creation, and before/after index replacement. Add real concurrent cross-process/cross-worktree promotion fixtures and prove no overwrite, lost version, split-brain replay, curated-record mutation, or unsafe cleanup.

### P2 — Prompt-injection handling is a doctrine statement, not an enforceable context boundary

The package correctly says retrieved memory is evidence rather than instruction and cannot mint deterministic authority. However, the proposed record accepts bounded free-text title/summary/facts from completed evidence, and the adapter may place that content into planner/implementer/reviewer/QA context. Closed JSON fields and secret redaction do not neutralize instruction-like or delimiter-breaking content. The planned test that retrieved text cannot alter command shape protects the deterministic command schema, but it does not define safe serialization into prompts, trusted/untrusted boundary labels, escaping, role/channel placement, or how downstream stage prompts must ignore commands embedded in memory.

This leaves the Linear malicious-record acceptance test underspecified and allows an implementer to satisfy it only at the CLI boundary while still exposing agents to active prompt injection.

Evidence:

- Linear `SAAS-56`, Scope for planner/implementer/reviewer/QA digest context and Test note requiring a malicious record not to alter authority, completion boundary, issue selection, provider configuration, or mutation scope.
- Plan §7 final paragraph, §11 retrieval fixtures, and §15 Prompt injection mitigation.
- Tasks `RM-04` and `RM-05`.

Required correction: define the exact context-adapter contract or keep model-context composition out of this delivery explicitly. If composition is included, require canonical encoding/escaping, an untrusted-data envelope, fixed non-user role placement, explicit precedence text outside retrieved content, no parsing of memory into commands/configuration, and adversarial delimiter/instruction fixtures across each named stage. Prove the deterministic adapter derives authority and workflow selectors solely from authenticated state, never from retrieved values.

## Checks that passed

- The observable goal and non-goals match the Linear issue's local, curated, no-vector/no-network scope and correctly reject bulk-loading raw `docs-ai`, chat, Linear comments, logs, tool payloads, credentials, and model prose.
- The plan preserves repository/source/canonical-protocol precedence and separates ordinary scoped repository mutation from memory evidence. No role string, record, result, status field, CLI request, or index entry is intended to mint workflow, lease, reservation, provider, tracking, product, or security authority.
- Repository identity and path safety are materially addressed through exact registry resolution, descriptor/registry/physical-worktree agreement, mandatory repository binding, fixed record root, `StatePathGuard`, traversal/case/reparse/hard-link tests, and rejection of caller-chosen roots/state paths/globs.
- The derived index is correctly treated as disposable state-home projection with canonical input digests, bounded quarantine, atomic replacement/readback, explicit rebuild/repair, and no automatic mutation of curated records.
- Stale, missing, corrupt, cross-repository, conflicting, redacted, retired, expired, superseded, and over-budget records are intended to fail closed or be visibly excluded without leaking content. Retention uses injected-clock fixtures and no automatic physical deletion.
- Status remains observation-only: the existing engine operation union does not grow, status performs no implicit repair, and the proposed summary excludes bodies, sensitive paths, journals, leases, reservations, capabilities, release/mutation fields, and promotion inputs.
- Manual, semi-autonomous, and autonomous advancement/clarification policies remain distinct; detailed memory assets are not added to the healthy autonomous prompt and implicit autonomous retrieval remains disabled.
- Design is reasonably not required because the work changes repository data/runtime/CLI/documentation contracts without a product screen or interaction flow.
- The six tasks are ordered, name one target repository, keep `src/` canonical and `dist/` generated, and preserve distinct audit, exact-diff review, runtime QA, docs, publication, merge, and post-merge gates.
- The merge boundary requires focused tests and `python .\scripts\validate.py`, exact-head review/QA/docs evidence in a fresh clean worktree, authorized squash-merge readback, and another clean aggregate at the exact returned merge SHA. Hosted checks are not substituted for local evidence.
- The registered `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/` layout and workflow ID are current-layout identities, not inferred historical fallback. This audit does not mutate the Backlog Linear issue, Git, registry, or `workflow.json`.

## Sources consulted

- `AGENTS.md`
- Linear issue `SAAS-56`, including full description, acceptance criteria, test notes, documentation impact, dependencies, non-goals, status, labels, and relations (read-only on 2026-07-24)
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/workflow.json`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-plan.md`
- `docs-ai/006-saas-56-curated-repository-memory-and-bounded-re/2026-07-24-saas-56-curated-repository-memory-and-bounded-re-tasks.md`
- `src/skills/goal-to-delivery/references/{artifact-contract,autonomous-runtime-contract,clarification-policy,completion-boundaries,delivery-stages,quality-gates}.md`
- `src/skills/goal-to-delivery/references/work-descriptor.schema.json`
- `src/skills/linear-delivery-loop/scripts/publication_records.py`
- `src/skills/linear-delivery-loop/references/publication-state.schema.json`
- Installed `task-audit-breakdown` skill and independent audit checklist
