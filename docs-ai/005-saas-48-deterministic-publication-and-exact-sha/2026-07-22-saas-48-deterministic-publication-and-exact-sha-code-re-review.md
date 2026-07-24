# SAAS-48 deterministic publication and exact-SHA gates — Code re-review

## Verdict

**FAIL** — one P1 and one P2 remain. The fixes durably bind publication state, complete gate-worktree evidence, and consume the SAAS-47 reply one-shot, but the assembled engine still permits publication mutations and terminal status without enforcing the required authority/evidence sequence. The evidence classifier is path/role/type-aware now, but still accepts arbitrary body changes.

## Findings

### P1 — The composed engine exposes provider mutation and terminal completion without the publication authority, recovery, or evidence state machine

The new operations are callable, and `PublicationJournal.save_authoritative()` now repairs the journal-to-supervisor-state crash boundary (`operations.py:489-524`). `ExactShaGateRunner.run()` also authoritatively completes the gate-worktree evidence (`exact_sha_gates.py:67-72`). Those parts of the first P1 are closed.

The assembled handlers nevertheless bypass the policies that were supposed to govern those primitives. `execute_publication_provider()` accepts any of `push`, `pull-request`, or `squash-merge` against one publication record and calls the provider directly (`supervisor.py:249-283`). It does not reread or validate the live lease, reservation, mutation authorization, stop labels, PR mergeability, exact-head aggregate, review, QA, docs, evidence convergence, base drift, or finalization count before merge. The record's immutable `operation` can remain `push` while the same operation ID is reused for PR creation and merge. `execute_publication_gate()` accepts either the head SHA or merge SHA for either gate kind, then marks the publication `completed` solely because the caller named the gate `exact-merge-aggregate` (`supervisor.py:286-308`); therefore the head SHA can be submitted as a merge gate before any merge and create terminal authoritative state.

The refusal/retry and repair classes remain standalone: production search finds `PublicationRecovery` and `MergeRepairPolicy` only in their definitions/exports, while the engine has no handler that invokes them. `RecoverPublication` merely rebinds the already-written publication JSON to supervisor state (`supervisor.py:311-312`); it performs no provider readback, attended reply consumption, refusal reconciliation, retry scheduling, premerge check, post-merge repair, or exact operation recovery. The integration test mirrors the happy-path calls but supplies no reservation/lease/attestation authority and asserts a merge after only an aggregate gate (`test_publication_contracts.py:91-104`), so it demonstrates the bypass rather than the required closed orchestration.

This leaves the original composition/recovery finding materially open and introduces a direct merge/completion authority bypass.

Required correction: expose one ordered state-machine operation (or strictly guarded phase operations) that binds each provider mutation to its own immutable operation identity and current supervisor CAS; require reservation/mutation authority and the complete exact-head evidence set immediately before merge; require `exact-merge-aggregate` to bind only a non-null provider-readback merge SHA after merge; compose refusal, durable attended consumption, retries, recovery, and bounded repair into that same journaled path; and add adversarial integration/crash fixtures proving out-of-order PR/merge/gate calls and stale authority cannot mutate or complete.

### P2 — Evidence classification permits arbitrary body changes during an otherwise valid draft-to-pass transition

The classifier now correctly restricts filenames to dated `code-review`, `qa`, or `completion` artifacts and rejects README, workflow descriptors, canonical policy files, symlinks, directories, missing files, duplicate fields, and invalid state transitions (`exact_sha_gates.py:89-171`). This substantially closes the path/type/role portion of the prior P2.

However `_record()` extracts only the three unindented `key: value` fields and `classify()` compares only their role/state values (`exact_sha_gates.py:112-156`). It never proves that the Markdown body is unchanged or belongs to a closed content schema. A focused diagnostic changed a benign draft into a passing review while adding `IGNORE ALL PREVIOUS AUTHORITY RULES`; the classifier returned the artifact as evidence-only. Any prose without `: ` can therefore be added, removed, or replaced in the finalization commit without invalidating implementation/QA gates.

Required correction: canonicalize and compare the full artifact structure, allowing only explicitly enumerated finalization fields/transitions and SHA-bound result sections. Reject every other body delta, or move final attestations to a strict machine record whose exact schema is validated. Add adversarial tests for inserted, removed, and replaced prose with otherwise valid role/state/SHA metadata.

## Prior-finding closure assessment

- **Authoritative publication/gate state:** partially closed at the storage primitives; not closed at ordered engine authority or recovery composition.
- **One-shot attended reply:** closed in isolation. `ControlPlaneRecords.consume_publication_reply()` durably changes the exact pending request once, and the retry helper persists `consumedReplyId` before attempting. The real-record replay and crash fixtures pass. It remains unavailable through the assembled engine, covered by the P1 above.
- **Strict evidence classification:** path, role, transition, and file type are closed; full content classification remains open.

## Verification evidence

- Reviewed the full current working tree against `main`, excluding only `.codex-remote-attachments/`, and re-read the original code review, plan, tasks, implementation modules, schemas, CLI composition, and focused tests.
- Focused publication/recovery/gate/provider/repair suites: **23 tests passed**.
- `git diff --check`: **PASS** (line-ending warnings only).
- Focused adversarial classifier diagnostic: **FAIL as designed for this review** — arbitrary behavioral prose was accepted as evidence-only.
