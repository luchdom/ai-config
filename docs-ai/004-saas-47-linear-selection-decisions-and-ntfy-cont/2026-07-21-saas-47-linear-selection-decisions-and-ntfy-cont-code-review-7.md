# SAAS-47 Linear Selection, Decisions, and ntfy Control Plane — Code Review 7

## Verdict

**PASS.** The current SAAS-47 working-tree implementation resolves both Review 6 blockers without weakening the earlier control-plane guarantees. No P1, P2, or P3 findings were identified.

| Severity | Count | Gate result |
|---|---:|---|
| P1 | 0 | Pass |
| P2 | 0 | Pass |
| P3 | 0 | Pass |

## Review identity and target

- Reviewer: fresh independent correctness reviewer 7 (`/root/saas47_review7`)
- Base/working-tree HEAD: `e4537482a01b3ac367a6a2efe9b6ce0f1a8b3ee4`
- Branch: `codex/saas-47-linear-control-plane`
- Workflow: `b2a59c64-d8a8-4e5f-ade6-1a4a7818da6d`
- Scope: the complete tracked and untracked SAAS-47 working-tree delta, workflow acceptance criteria, approved tasks/re-audit, and Review 6 findings

## Review 6 resolution

### Production authority boundary — resolved

`SupervisorEngine` has a closed slot inventory and refuses caller replacement of control-plane ownership surfaces (`src/skills/linear-delivery-loop/scripts/supervisor.py:22-52`). Its production reference-description and operation-execution methods expose no adapter installation, raw callbacks, registry entry, or authority-returning resolver and remain fail-closed while the live provider is disabled (`supervisor.py:109-140`). `TrackingPreflight` accepts only the exact canonical `SupervisorEngine` type, binds the opaque reference into its attestation, and later invokes only a named closed operation with a copied payload (`src/skills/linear-delivery-loop/scripts/tracking.py:108-157`).

Fixture composition is confined to the isolated test package. It patches that isolated package's exact class and keeps raw callbacks in test support (`tests/linear_delivery_control_plane/support.py:15-123`); the canonical runtime class is neither patched nor able to accept that separately loaded class. Direct tests also prove the production surface has no fixture installer or resolver, instance replacement is refused, and a differently bound engine cannot use an already attested reference (`tests/linear_delivery_control_plane/test_selection_claim.py:772-820`). Runtime execution therefore receives a closed operation rather than adapter authority, and a registry reference cannot be redirected after binding.

### Recovery generation fencing — resolved

Every selection execution acquires an operation-wide nonblocking thread/process fence before generation acquisition or any side effect (`src/skills/linear-delivery-loop/scripts/control_plane.py:290-318`; `src/skills/linear-delivery-loop/scripts/control_plane_records.py:140-232`). A live worker retains that fence even after its logical lease expires; a successor sees recovery in flight rather than taking ownership. A dead process releases recoverability through PID evidence, preserving crash takeover.

Recovery additionally verifies the current durable generation, owner, lease revision, and fence token before repository recovery, provider readback/claim, and local commit (`src/skills/linear-delivery-loop/scripts/control_plane.py:554-614`). The four paused-boundary probes cover before provider work, during provider work, before readback, and before commit; each records exactly one provider claim and one local commit while the contender remains inert (`tests/linear_delivery_control_plane/test_selection_claim.py:697-752`). Hard-crash and second-generation fixtures retain successful recovery and reconciliation coverage (`test_selection_claim.py:822-1015`).

## Retained acceptance coverage

- Linear transport is endpoint-bound, retry-bounded, fully paginated with progressing terminal evidence, and reconciles ambiguous mutations through readback (`src/skills/linear-delivery-loop/scripts/linear_transport.py:109-293`).
- Complete provider-node normalization precedes both selection and migration; selection uses global WIP precedence, complete-set deterministic ordering, a durable single candidate claim, and local-before-provider execution (`src/skills/linear-delivery-loop/scripts/control_plane_registry.py:126-215`; `src/skills/linear-delivery-loop/scripts/selection.py:37-166`; `src/skills/linear-delivery-loop/scripts/control_plane.py:116-376`).
- Decisions, publication retries, bounded follow-ups, attention taxonomy, owner/time/exact-syntax reply consumption, canonical IDs, and redaction are persisted and contract-validated (`src/skills/linear-delivery-loop/scripts/control_plane_records.py:235-594`; `src/skills/linear-delivery-loop/scripts/contracts.py:511-779`).
- ntfy remains an injected, redacted, bounded attention channel with durable one-attempt ownership and status-visible recovery/failure; routine and transient sources do not create attention records (`src/skills/linear-delivery-loop/scripts/ntfy_transport.py:15-86`; `src/skills/linear-delivery-loop/scripts/control_plane.py:756-797`).
- Migration consumes the same verified complete observation and produces a deterministic `mutationFree: true` report without provider writes (`src/skills/linear-delivery-loop/scripts/control_plane.py:798-816`; `src/skills/linear-delivery-loop/scripts/migration.py:14-61`).

## Verification performed

- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — **PASS**, 53 tests.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — **PASS**, 6 tests.
- `python -m compileall -q src\skills\linear-delivery-loop\scripts tests\linear_delivery_control_plane` — **PASS**.
- `git diff --check` — **PASS**; only Git line-ending conversion warnings were emitted.
- A larger supervisor subset was started but produced no incremental output within the review window and was stopped; it is not counted as review evidence. Repository aggregate validation remains a later QA/publication gate.
- No source, test, workflow descriptor, generated projection, Git state, Linear state, provider/network state, or live ntfy state was modified by this reviewer.

## Gate result

Code review 7 passes with zero findings. Both Review 6 findings are resolved. The implementation may proceed to the separate QA, documentation, build/projection, exact-head validation, publication, merge, and exact-merge-SHA validation gates required by the workflow.
