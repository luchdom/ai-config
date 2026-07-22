# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Code Review 5

## Verdict

**FAIL / CHANGES REQUESTED.** The Review-4 pagination and original-worker crash paths are repaired, but the claimed engine-owned adapter boundary remains caller-manufacturable and replaceable. A hard crash by the first recovery owner also leaves the operation permanently `recovering`. In addition, the default Linear observation query cannot produce the normalized issue contract consumed by selection and migration. No P3 findings were identified.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 2 | Fail |
| P2 | 1 | Fail |
| P3 | 0 | Pass |

## Review identity and target

- Reviewer: fresh independent post-fix code reviewer 5 (`/root/saas47_code_review_5`)
- Base/working-tree HEAD: `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4`
- Branch: `codex/saas-47-linear-control-plane`
- Workflow: `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`
- Scope: exact current tracked and untracked SAAS-47 working-tree delta, approved plan/tasks/re-audit, and Reviews 1–4
- Review time: `2026-07-22T01:42:35Z` (`2026-07-21` local)

## Review-4 resolution matrix

| Required re-probe | Result | Evidence |
|---|---|---|
| Engine-owned opaque adapter registry rejects initial fake bindings and cannot be replaced after issuance | **Unresolved (P1)** | Normal attribute assignment is sealed, but the module-level `_compose_engine_registry` accepts arbitrary caller callbacks and returns the exact registry type accepted by `TrackingPreflight`. A direct initial-fake probe issued a ready attestation. Replacing the legitimate registry entry with that manufactured exact entry after attestation caused the copied port/fake authority to lease, reread, prepare, claim, read back, and commit; original adapters received no calls. |
| Hard-crashed `in-flight` claims require dead/expired proof and one exclusive recovery generation | **Resolved for the original owner; new recovery-lifecycle P1 remains** | Live-owner recovery is inert. Expired/dead proof moves `in-flight` or `protected` to one CAS-owned `recovering` generation, and concurrent contenders do not call the provider twice. However, process death immediately after the `recovering` CAS is not recoverable: every later caller returns `recovery-in-flight` forever without re-authorizing a new owner/generation. |
| Selection consumes engine-owned terminal pagination evidence and sees later-page WIP/winner | **Resolved, subject to the registry P1 and provider-shape P2** | `choose_or_resume` obtains observations from the registry entry, which calls `LinearTransport.paginate_verified`. Multi-page later-WIP and later-winner fixtures pass; missing completion and repeated cursor fixtures fail before a selection record is written. |
| Migration consumes the same verified pagination evidence, is complete/mutation-free, and preserves unrelated labels | **Resolved, subject to the provider-shape P2** | The facade obtains `observe_issues()` from the same registry adapter, then `build_migration_report` revalidates the completed observation. Multi-page, incomplete/repeated evidence, mutation-count-zero, deterministic ordering, and unrelated-label tests pass. |

## Earlier retained-guarantee matrix

| Guarantee | Result |
|---|---|
| Exact-field issuer-verifiable preflight attestation and config/repository/owner/transport binding | Pass |
| Fresh matching attestation after TTL preserves logical request/selection identity | Pass |
| Configured-owner reply authorization, exact reply grammar, and one-time consumption | Pass |
| Pending/protected/foreign authority blocks a second ordinary selection | Pass |
| Global WIP precedence and deterministic candidate ordering over the supplied completed observation | Pass |
| Source-to-attention taxonomy, quiet proposals, cardinality, metadata equality, redaction, and notify-once behavior | Pass |
| Strict durable-record variants, canonical IDs, consumption parity, and terminal replay | Pass |
| Post-dispatch mutation ambiguity enters readback; pre-dispatch/read failures remain distinct | Pass |
| Local-before-provider claim ordering and original-owner dead/expired takeover | Pass |

## Findings

### P1 — The “engine-owned” registry is still caller-manufacturable and replaceable

`_compose_engine_registry` accepts arbitrary `reread`, `claim`, `readback`, repository-authority operations, credential callback, and local observer, then supplies the private composition token internally (`src/skills/linear-delivery-loop/scripts/control_plane_registry.py:187-214`). `TrackingPreflight` accepts any exact `EngineAdapterRegistry` instance as authoritative (`src/skills/linear-delivery-loop/scripts/tracking.py:107-134`). There is no supervisor-owned registry lookup or issuance record that distinguishes an engine-created entry from one manufactured by a facade caller. The “private” factory and entry remain ordinary module attributes.

A direct probe composed a copied same-transport claim adapter plus fake repository authority through `_compose_engine_registry`; `TrackingPreflight.run` issued it a ready signed attestation. A second probe issued an attestation against the legitimate registry, replaced its `_entry` using Python's base object setter with the manufactured exact entry, and called `claim`. The result was `claimed`; all lease/reread/prepare/provider/readback/commit events occurred on the replacements and the legitimate adapters had zero events. The focused negative test checks only ordinary assignment and the tokenless public constructor, so it does not exercise either actual bypass.

Required repair: the mutation facade must resolve an opaque reference through a supervisor-owned registry/state boundary that callers cannot construct from raw callbacks. Do not expose a composition function that turns arbitrary callbacks into an accepted authority. Resolution must verify an engine-issued registry record/capability and bind immutable concrete adapter identities independently of caller-held mutable Python objects. Add direct initial-factory fake binding and post-attestation replacement probes proving refusal before lease, local preparation, or provider access.

### P1 — A hard crash by the recovery owner permanently strands `recovering`

The first eligible takeover atomically changes the record to `recovering` and records a generation/owner (`src/skills/linear-delivery-loop/scripts/control_plane.py:346-368`). If that process terminates before `_recover_selection` finishes or the exception handler runs, later recovery calls encounter `recovering` and unconditionally return `recovery-in-flight` (`src/skills/linear-delivery-loop/scripts/control_plane.py:369-370`). No lease/owner-death proof is requested for the recovery owner, and no later generation can be acquired.

A direct probe hard-stopped immediately after `_acquire_selection` returned `recovery-acquired`. Six minutes later, with a fresh valid attestation, an exact-operation recovery returned `recovery-in-flight`, left the record `recovering`, and made no second `authorize_recovery` call. Thus the new hard-crash mechanism protects only the original worker; an unattended crash at the recovery-acquisition boundary has no deterministic forward path.

Required repair: bind each recovery generation to a durable recovery execution lease (owner, revision, expiry), keep a live recovery owner inert, and permit one CAS winner to advance to a new generation only with exact dead-owner/expired proof for the prior recovery generation. Test process death immediately after recovery acquisition and after local recover/provider claim/readback, plus two concurrent second-generation contenders, with no duplicate provider mutation.

### P2 — The default Linear observation cannot materialize the issue contract used by selection and migration

The engine observation adapter's default GraphQL query requests only `nodes { id }` (`src/skills/linear-delivery-loop/scripts/control_plane_registry.py:101-108`, `187-202`). Selection requires normalized fields including `identifier`, state name, labels, repository key, scope, goal completeness, external dependency, priority, creation time, title, and parent evidence. Migration immediately indexes `identifier` and consumes the same normalized fields (`src/skills/linear-delivery-loop/scripts/migration.py:20-47`). There is no provider-node normalization or strict node-shape validation between `paginate_verified` and either consumer.

The focused requesters ignore the query text and return fully normalized fixture objects, masking the production adapter contract. A direct id-only response—the exact shape requested by the default query—made selection report an empty queue and made migration raise `KeyError: 'identifier'`. This is fail-safe for selection but makes the advertised adapter unusable and migration non-diagnostic.

Required repair: make the engine observation adapter request and normalize every field required by WIP, eligibility, ordering, and migration, or require a separate exact engine-owned normalizer with a closed validated issue-observation schema. Reject incomplete node shapes with a domain error before selection/report construction. Add query-respecting raw GraphQL fixtures, including nested state/labels/parent/project shapes, and prove the same normalized completed observation drives both selection and migration.

## Probes and verification

- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — **PASS**, 48 tests.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — **PASS**, 6 tests.
- `git diff --check` — **PASS** (line-ending conversion warnings only).
- Direct initial manufactured-registry probe — **FAIL**: arbitrary copied/fake callbacks received a ready signed attestation.
- Direct post-attestation registry-entry replacement probe — **FAIL**: replacement authority/port completed the claim; original adapters had zero calls.
- Direct original-owner hard-crash, live-owner, expired/dead takeover, provider-applied reconciliation, and two-concurrent-takeover fixtures — **PASS**.
- Direct recovery-owner hard-crash probe — **FAIL**: state remained permanently `recovering`; later exact recovery did not request new authority proof.
- Selection multi-page later-WIP/later-winner and missing/repeated-cursor fixtures — **PASS**.
- Migration multi-page, mutation-free, metadata-label preservation, and incomplete/repeated evidence fixtures — **PASS**.
- Direct query-respecting id-only observation probe — **FAIL**: selection returned `empty`; migration raised `KeyError`.
- No fix, build, aggregate validation, QA, Git publication, Linear mutation, network/provider request, `dist/` mutation, or `workflow.json` mutation was performed by this reviewer.

## Gate result

Code review 5 fails. Resolve both P1 findings and the P2 observation-contract finding, add the missing adversarial/crash/query-shape fixtures, and obtain another fresh exact-diff independent review before QA or publication.
