# SAAS-56 curated repository memory and bounded retrieval — Code review 2

## Verdict

**FAIL** — one P1 finding, two P2 findings, and one P3 finding. The repair resolves substantial parts of the first review, including removal of the arbitrary promotion callback, registry/live-head binding, engine-derived context selectors, prepared record/marker/index files, freshness projection, hard-link checks, secret-like assertion keys, and richer status. However, promotion authority consumption and prepared-journal persistence are still not atomic, and replay treats the non-authoritative half of that transition as sufficient authority. PASS is therefore not available.

## Review boundary and evidence

- Reviewed base: `main` / `1a5190f1815ae25b0a3cba6e81b50ae221c62052`.
- Reviewed target: the current uncommitted tracked and untracked SAAS-56 RM-01–RM-05 working-tree change set on 2026-07-24, including the repairs in `reservations.py`, repository-memory modules/contracts/schemas, CLI/status integration, and focused tests.
- Requirements: `AGENTS.md`; the registered workflow descriptor; the full SAAS-56 plan, tasks, `*-re-audit-3.md`; and the first code review in this folder.
- `python -m unittest tests.linear_delivery_repository_memory.test_contracts -v` — **exit 0**, four tests, 13.349 seconds.
- `python -m unittest tests.linear_delivery_repository_memory.test_index tests.linear_delivery_repository_memory.test_query -v` — **exit 0**, six tests, 58.186 seconds.
- `python -m unittest discover -s tests/linear_delivery_repository_memory -t . -v` — **timed out** after 184.074 seconds without a completed result.
- `python -m unittest tests.linear_delivery_repository_memory.test_contracts tests.linear_delivery_repository_memory.test_index tests.linear_delivery_repository_memory.test_query tests.linear_delivery_repository_memory.test_context -v` — **timed out** after 124.064 seconds without a completed result.
- No aggregate/build command was run because RM-06 generated projections are outside this review boundary and those commands mutate generated files.

## Findings

### P1 — Prepared-journal persistence can survive without committed authorization consumption, and replay then bypasses authority

The new engine-owned primitive is an important improvement, but its two required effects are ordered rather than atomic. `consume_mutation_authorization_unlocked()` first writes and reads back `prepared_evidence_path`, then constructs/commits the consumed-authorization update (`reservations.py:622-641`). A process death, `commit_pair_unlocked()` failure, or store fault after the journal write and before the authoritative reservation commit leaves a valid-looking prepared journal while the mutation grant is unconsumed.

On the next promotion call, journal presence selects the replay branch. The code loads `promotionBatchRequest` and sets `state = reservations = None`; it does not resolve the opaque authorization reference, check the consumed-authorization ID, or prove that the paired authoritative commit occurred (`repository_memory.py:403-414`). Later, because the journal already exists, it skips `consume_mutation_authorization_unlocked()` entirely (`repository_memory.py:584-611`) and proceeds to create repository records and the marker. The caller must supply non-null placeholder parameters at the public signature gate, but those values are not consulted on this replay path.

This is precisely the fail-closed boundary the plan required to be atomic: a state-home recovery aid can become write authority after a torn transition. The added fault phases begin only after `consume_mutation_authorization_unlocked()` returns (`repository_memory.py:612`); they do not cover journal-written/authorization-not-committed. The test called “simulated process death” raises an ordinary exception inside the promotion `try`, so pre-marker cases execute in-process cleanup rather than proving an abrupt death at this authority boundary (`tests/linear_delivery_repository_memory/test_promotion.py:104-125`).

Required correction: make prepared evidence and the consumed-authorization ID one recoverable authoritative transaction, or persist a transaction identity whose replay is accepted only after readback proves the matching consumed commit. Journal presence alone must never suppress authorization validation. Add store fault/process-termination fixtures immediately before journal persistence, after journal persistence, before/within/after paired commit, and before opaque-reference cleanup; verify that no repository target can be created unless the authoritative consumed state is proven.

### P2 — Prospective source and graph validation still permits invalid or unreviewed committed batches

Current-completion source validation is conditional on `source.workflowId` being non-null (`repository_memory.py:153-171`). A `docs-ai/` source can therefore set `workflowId: null`, remain in `sourceArtifacts`, and avoid registry, completed-stage, and inventory validation even under `compatibilityClass: current-completion-v2`. The source-artifact schema permits null workflow/work keys and does not couple path/stage/kind to that choice (`repository-memory-promotion.schema.json:6`). Candidate provenance accepts the same path/digest pair, so unregistered delivery evidence can contribute to `source-evidence-bound` content. In addition, the manifest and source files are validated before acquiring the repository mutex and are not reread under it (`repository_memory.py:355-364`, then lock at `394`); promotion uses the pre-lock bytes/digests after the lock, leaving the source/manifest replacement window that plan §6.2 explicitly closed.

Prospective graph validation also evaluates predecessors only against the pre-batch `current["entries"]` map (`repository_memory.py:463-498`). It does not add earlier canonical candidates, so a valid in-batch v1→v2 dependency cannot be promoted. Conversely, two candidates can both supersede the same current predecessor: each sees that predecessor as current, and the pairwise preflight checks only assertion duplicate/conflict (`repository_memory.py:504-522`). `build_index(... prepared_marker=...)` will mark the resulting branch invalid, but promotion does not reject an invalid prepared graph; it can commit the marker for a batch whose successors are immediately quarantined. A mismatched `restores` reference likewise is not rejected prospectively—the promotion check only tests the predecessor lifecycle, while the index later labels it invalid (`repository_memory.py:492-498`; `repository_memory_index.py:132-140`).

Required correction: reread/revalidate the exact manifest and every source under the mutex; require every current-layout `docs-ai` source to resolve to exact registered completed evidence; build a canonical-order prospective graph that includes earlier candidates; reject branches, nonterminal/missing links, and restore mismatches before authority consumption and before preparation. Add current-vs-legacy source-null matrices, source/manifest replacement races, in-batch dependency chains, double-successor branches, fan-in, restore, archive, and redaction fixtures.

### P2 — Request/result and nested schema parity remains documentary rather than enforced

The repair adds exact runtime functions for promotion batch requests/results and more named digest helpers, but those contracts are not registered schemas in `MEMORY_SCHEMA_FILENAMES` (`contracts.py:59-67`). Instead, `promotionBatchRequest` and `promotionResult` appear only as unreferenced `$defs` inside the manifest schema, with unconstrained `{}` properties (`repository-memory-promotion.schema.json`, `$defs`). The manifest candidate schema is additional-properties-false but likewise assigns `{}` to every property and relies on separate runtime code for all types and bounds. `assert_runtime_parity()` therefore checks only the seven top-level schemas and never proves schema/runtime inventory parity for the required batch request/result contracts (`contracts.py:1313-1343`).

The expanded known-answer test is better than the original, but it hashes small toy objects rather than the audited one-candidate manifest, record, request, marker, committed result, index, context envelope, and final accounting objects, and it does not tamper every included/excluded boundary (`tests/linear_delivery_repository_memory/test_contracts.py:13-35`). This leaves the named strict-contract/projection gate substantially below RM-01 and the re-audit's required observability.

Required correction: publish and register strict versioned schemas for every named request/result/envelope contract (or reference fully constrained shared `$defs` from registered top-level schemas), make schema/runtime parity enumerate them, and add full canonical byte/hash fixtures plus field-by-field included/excluded tampering and replay tests.

### P3 — Isolation and full operational regressions remain under-tested

The implementation now rejects hard-linked existing files and uses `O_NOFOLLOW` where available (`repository_memory_records.py:40-61`, `76-95`), requires a canonical engine assembly/state home (`repository_memory.py:235-256`), rejects secret-like assertion keys (`contracts.py:212`, `651-656`), derives context selectors through the registry (`repository_memory.py:314-341`), and reports marker/source/build status (`repository_memory.py:962-1000`). These are meaningful repairs.

The focused suite still contains no reparse/junction/hard-link/state-home substitution fixture, no source/target path race, and no public CLI compatibility test for query/rebuild/repair/context. The full focused suite and the context-inclusive subset did not complete within their bounded timeouts, so the new cross-process/context/status paths lack a complete observed local gate in this review. The promotion crash test also uses caught exceptions rather than actual abrupt termination except for the separate happy-path contender case.

Required correction: add bounded platform-aware isolation and public CLI/status regressions, convert critical crash boundaries to actual child-process termination, and keep the focused suite within a predictable repository-owned timeout.

## Prior-finding disposition

- **Prior P1, arbitrary caller callback/non-registry authority:** partially resolved. The arbitrary callback is removed; registry, live head/worktree, and autonomous-attestation checks were added. Superseded by the narrower but still critical torn journal/authority transaction P1 above.
- **Prior P2, marker-last recovery:** substantially resolved through prepared files, marker validation, transient rebuild, and replay phases. The authority transition at the start of recovery remains unsafe, and graph-invalid batches can still reach the marker.
- **Prior P2, strict contracts/projections:** partially resolved through exact runtime functions, nested inventories, and named helpers; registered schema parity and full known-answer coverage remain incomplete.
- **Prior P2, lifecycle/freshness/source rules:** freshness/review-due/source diagnostics and several lifecycle checks were added. Current-source validation, under-lock reread, and prospective in-batch graph enforcement remain incomplete.
- **Prior P2, authenticated context:** resolved for the reviewed boundary. Raw mappings are rejected, selectors are registry-derived and sealed, query work/stage drift is checked, authenticated identities are emitted, and equal-width final accounting remains enforced.
- **Prior P2, path/state/secret isolation:** implementation is substantially resolved for the reviewed boundary; remaining concern is test coverage, recorded as P3.
- **Prior P3, status:** resolved in implementation. Status now exposes bounded marker/input/build observations and remains mutation-free in the covered code path.

## Passing observations

- Promotion requires one canonical manager/store/reservation assembly and live registry/head/worktree validation.
- Record, marker, and index bytes are prepared and read back before repository creation in the ordinary path.
- Marker replay validates the complete marker-bound set before reporting commitment.
- The index derives source drift, review-due, expiry, graph, conflict, and duplicate state and remains rebuildable from repository markers.
- Query/result inventories, deterministic ranking, whole-item budgets, and reason-specific reread diagnostics are materially stronger.
- Context is a fixed developer/tool delivery with escaped untrusted content, registry-derived selector evidence, and inclusive equal-width accounting.
- Status remains observation-only and the existing supervisor operation union remains unchanged.

This review grants no implementation, Git, provider, tracking, workflow-advancement, publication, or merge authority.
