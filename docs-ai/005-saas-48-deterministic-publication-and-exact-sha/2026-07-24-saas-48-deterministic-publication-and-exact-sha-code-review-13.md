# SAAS-48 deterministic publication and exact-SHA gates — Code review 13

## Verdict

**PASS** — the post-review-12 change establishes an explicit control-plane state 1.1 boundary and closes the same-version watermark remigration defect without introducing a legacy-data, CAS, or authority regression.

## Finding counts

- P1: 0
- P2: 0
- P3: 0

## Closed checks

- **Exact migration boundary:** `ControlPlaneStore._read_unlocked()` enters migration only when `schemaVersion` is exactly the string `1.0`. It backfills only a missing publication reply watermark, preserves every existing field and existing watermark, changes the document to 1.1, advances the revision once, validates the complete current contract, and only then persists atomically (`control_plane_records.py:110-137`). A second load of the resulting 1.1 document is read-only, so same-version remigration is eliminated.
- **Current-state tamper failure:** a 1.1 publication request missing `lastConsumedReplyTimestamp` is not eligible for migration. The closed 1.1 schema rejects it, and the store does not call its writer after validation fails (`control-plane-state.schema.json:31-39`, `control_plane_records.py:117-137`). The focused regression also proves that the exact tampered bytes remain unchanged after the failed load (`test_migration_status.py:80-85`).
- **Version/schema/runtime/fixture parity:** the schema identifier, title, `schemaVersion` constant, and runtime-parity metadata all bind 1.1; runtime parity selects 1.1 specifically for `control-plane-state`; the store and control-plane test support use the same 1.1 constant; and the supervisor contract fixture is 1.1 (`control-plane-state.schema.json:3-10,79`, `contracts.py:18-20,858-865`, `control_plane_records.py:29-30,97-108`, `support.py:13`, `test_contracts.py:200-204`).
- **No ambiguous version acceptance or unintended rewrite:** direct disposable probes rejected `"1"`, `"1.00"`, `"1.2"`, numeric `1.0`, and null versions, with the source file unchanged in every case. Only exact string `"1.0"` receives the migration path.
- **Legacy preservation and revision/CAS behavior:** pending legacy requests derive the new lower bound from `sourceTimestamp`, authorized legacy requests derive it from their active consumed timestamp, and all other legacy data is retained. Migration occurs inside the same shared store guard as ordinary mutation and advances the revision before persistence, so callers holding the legacy revision become stale rather than gaining authority (`control_plane_records.py:88-95,117-137`). No authority or CAS path is bypassed.
- **Monotonic reply and capability behavior:** new requests start at the source timestamp; consumption requires a timestamp strictly above both source and durable lower bound; successful consumption advances the bound; reopen clears only active consumption evidence; and older, equal-time, or repeated replies remain inert while exactly one genuinely newer reply can authorize (`control_plane_records.py:402-517`). The state-version change does not mint, revive, widen, or consume capabilities, and the previously reviewed capability refresh predicates and paired publication CAS remain unchanged.

## Verification evidence

- Read code review 12 and inspected the exact state schema, runtime version dispatch and validation, store migration/persistence path, reply consumption/reopen logic, support constants, and focused fixtures/tests.
- `python -u -m unittest tests.linear_delivery_control_plane.test_migration_status.MigrationStatusTests.test_control_plane_store_migrates_publication_reply_lower_bounds_once tests.linear_delivery_control_plane.test_records_notifications.RecordTests -v`: **PASS**, 10 tests in 0.806s.
- Earlier narrow parity run including `SupervisorContractTests.test_runtime_parity_inventory_and_every_valid_contract`: **PASS**, 4 tests in 0.414s.
- Direct disposable unsupported-version probe: all five ambiguous/unsupported forms failed closed and left their persisted bytes unchanged.
- No aggregate, Git, provider, network, live-system, or publication mutation was run.
