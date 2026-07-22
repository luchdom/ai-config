# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Code Review 6

## Verdict

**FAIL / CHANGES REQUESTED.** Review 5's durable recovery-generation and complete issue-normalization repairs are present, but the adapter registry is still caller-composable, caller-replaceable, and directly resolvable. A recovery generation that loses its lease is also not fenced from resuming after a successor generation takes ownership, allowing duplicate provider mutation and duplicate local commit. No P2 or P3 findings were identified.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 2 | Fail |
| P2 | 0 | Pass |
| P3 | 0 | Pass |

## Review identity and target

- Reviewer: fresh independent post-fix code reviewer 6 (`/root/saas47_code_review_6`)
- Base/working-tree HEAD: `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4`
- Branch: `codex/saas-47-linear-control-plane`
- Workflow: `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`
- Scope: exact current tracked and untracked SAAS-47 working-tree delta, approved plan/tasks/re-audit, and Reviews 1–5
- Review time: `2026-07-21T23:07:45-03:00`

## Review-5 correction matrix

| Required re-probe | Result | Evidence |
|---|---|---|
| `TrackingPreflight` receives only an opaque reference resolved by the exact supervisor/state owner; raw composition and registry replacement cannot redirect operations | **Unresolved (P1)** | The facade receives a reference, but `SupervisorEngine._install_control_plane_test_fixture` still composes arbitrary callbacks on any exact engine instance, `resolve_control_plane_registry` returns the entry, and `_control_plane_registries` remains replaceable through the caller-held engine. A post-attestation replacement completed through the fake claim port and authority with zero original-adapter events. |
| Each recovery generation has durable owner/revision/expiry and a crashed owner can be superseded while a live lease remains inert | **Partially resolved; stale-worker fencing P1 remains** | Durable generation fields and expired/dead proof are persisted, live-lease takeover is inert, and second-generation crash fixtures pass. However, the superseded generation can resume after takeover and execute provider claim and local commit because no ownership/fencing check surrounds those side effects. |
| Default Linear query and strict normalizer materialize the complete issue contract used by selection and migration, rejecting incomplete nested nodes | **Resolved** | The query requests every consumed field; `_normalize_issue_node` validates and normalizes nested state/labels/parent/project before business policy; both selection and migration use the same observation adapter. Query-respecting, incomplete-node, multi-page, selection, and migration fixtures pass. |

## Earlier retained-guarantee matrix

| Guarantee | Result |
|---|---|
| Exact-field issuer-verifiable preflight attestation and config/repository/owner/transport binding | Pass |
| Fresh matching attestation after TTL preserves logical request/selection identity | Pass |
| Configured-owner reply authorization, exact reply grammar, and one-time consumption | Pass |
| Pending/protected/foreign authority blocks a second ordinary selection | Pass |
| Global WIP precedence and deterministic complete-page candidate ordering | Pass |
| Source-to-attention taxonomy, quiet proposals, cardinality, metadata equality, redaction, and notify-once behavior | Pass |
| Strict durable-record variants, canonical IDs, consumption parity, and terminal replay | Pass |
| Post-dispatch mutation ambiguity enters readback; pre-dispatch/read failures remain distinct | Pass |
| Original-owner hard-crash recovery and hard-crashed recovery-owner generation advancement | Pass, subject to the stale-worker fencing P1 |
| Selection and migration require terminal progressing pagination evidence and migration remains mutation-free | Pass |

## Findings

### P1 — The opaque registry can still be manufactured, returned, and replaced by its caller

`SupervisorEngine._install_control_plane_test_fixture` accepts raw claim, repository-authority, credential, and observation callbacks and turns them into the accepted registry entry (`src/skills/linear-delivery-loop/scripts/supervisor.py:102-148`). The same caller-held engine exposes `resolve_control_plane_registry`, which returns that entry and its authority callbacks directly (`supervisor.py:161-167`). `TrackingPreflight` stores the caller-supplied engine object and later trusts its resolution result (`src/skills/linear-delivery-loop/scripts/tracking.py:108-155`); matching string IDs are the only subsequent binding check (`src/skills/linear-delivery-loop/scripts/control_plane.py:64-74`).

A direct post-attestation probe created an alternate exact-engine entry with copied IDs plus a fake claim port/authority, then replaced the legitimate engine's `_control_plane_registries` mapping under the existing opaque reference. The already-issued attestation remained valid and `claim` returned `claimed`; all lease, reread, local prepare, provider claim, readback, and commit events went to the replacements, while the original adapters received zero events. This is the Review-5 exploit moved from a module factory to a caller-held `SupervisorEngine`, not an engine/state-owned authority boundary.

Required repair: eliminate raw callback composition and entry resolution from the production `SupervisorEngine` surface. Fixture construction must live in test-only composition that cannot be accepted by runtime preflight. The runtime resolver should execute closed operations inside the engine/state owner or return non-authority data, and it must bind the issued reference to immutable, durable adapter identities that cannot be redirected by replacing an attribute/mapping on a caller-held Python object. Add direct initial fake-install, direct resolver-authority access, and same-reference post-attestation replacement probes; all must refuse before lease, local preparation, or provider access.

### P1 — A superseded recovery owner is not fenced and can duplicate provider and local mutations

An expired/dead recovery lease can correctly CAS the record to a new generation (`src/skills/linear-delivery-loop/scripts/control_plane.py:382-396`), but the old generation keeps its copied record and continues `_recover_selection` without rechecking generation ownership or lease validity before provider claim or local commit (`control_plane.py:493-523`). Ownership is checked only by the final state CAS, after both external side effects have already occurred.

A direct probe paused generation 1 inside the provider claim, advanced time past its recovery lease, and let generation 2 acquire and enter the same provider claim. Releasing both workers produced **two provider claim calls and two local commits**. Generation 2 returned `recovered`; generation 1 failed only at terminal CAS with `Selection terminal CAS does not own the operation`. Stable operation identity does not by itself prove every injected provider/local adapter is idempotent, and the approved claim contract explicitly requires no duplicate provider mutation.

Required repair: carry the recovery generation/lease revision as a fencing token through repository recovery, provider mutation, readback, and commit, and verify current ownership immediately before every side effect. The engine-owned adapters/state owner must reject a superseded token, including a formerly live worker that resumes after lease-expiry takeover. Add a two-generation paused-worker fixture covering takeover before provider claim, during provider claim, before readback, and before local commit; exactly one provider mutation and one commit may occur.

## Probes and verification

- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — **PASS**, 52 tests.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — **PASS**, 6 tests.
- `git diff --check` — **PASS** (line-ending conversion warnings only).
- Direct same-reference post-attestation registry replacement probe — **FAIL**: fake callbacks returned `claimed`; fake path received all six mutation events and original adapters received none.
- Direct expired generation-1 worker plus generation-2 takeover probe — **FAIL**: two provider claim calls, two local commits, one late terminal-CAS rejection.
- Existing initial/live recovery, hard-crashed recovery owner, second-generation concurrent winner, and per-boundary crash fixtures — **PASS**.
- Existing query-respecting raw GraphQL, incomplete nested-node, identical selection/migration normalization, multi-page, and mutation-free migration fixtures — **PASS**.
- No fix, build, aggregate validation, QA, Git publication, Linear mutation, network/provider request, `dist/` mutation, or `workflow.json` mutation was performed by this reviewer.

## Gate result

Code review 6 fails. Close the engine-owned adapter boundary and fence superseded recovery generations before side effects, add the adversarial concurrency fixtures, and obtain another fresh exact-diff independent review before QA or publication.
