# SAAS-48 deterministic publication and exact-SHA gates — Code review 12

## Verdict

**FAIL** — the ordinary post-review-11 path now enforces a durable monotonic reply watermark, but the same-version legacy migration makes deletion tampering indistinguishable from a legacy record. Removing `lastConsumedReplyTimestamp` from a current reopened request silently resets the lower bound to `sourceTimestamp`, allowing an older different reply to regain one-shot provider authority.

## Finding counts

- P1: 1
- P2: 0
- P3: 0

## P1 — Same-version migration can erase a current reopened request's durable lower bound

`ControlPlaneStore._read_unlocked()` treats every publication request missing `lastConsumedReplyTimestamp` as legacy, regardless of whether the containing `schemaVersion: 1.0` document has already used the new field. For a pending reopened request, `consumedReplyTimestamp` is intentionally null, so migration backfills the missing watermark from the original `sourceTimestamp`, increments the revision, and persists the downgraded bound (`control_plane_records.py:108-132`). There is no schema-version or durable migration marker that distinguishes a genuine pre-watermark 1.0 record from deletion of the field in a current 1.0 record.

That reset defeats the otherwise-correct strict check in `consume_publication_reply()`, which requires a reply timestamp to be strictly greater than `max(sourceTimestamp, lastConsumedReplyTimestamp)` (`control_plane_records.py:438-471`). After the reset, a different reply newer than the source but older than the previously consumed reply is accepted. The supervisor then consumes fresh exact mutation authorization and can reach the provider (`supervisor.py:1121-1139`, `supervisor.py:1162-1181`). This restores the replay-authority defect that the durable watermark was intended to close whenever the persisted field is deleted or lost.

A disposable direct probe demonstrated the provider-authority precursor exactly: consume `first` at `12:10`, reopen, delete only `lastConsumedReplyTimestamp`, reload, then submit `older-different` at `12:05`. Reload changed revision 3 to 4, backfilled the watermark to the `12:00` source, and accepted the older reply. Current tamper coverage does not catch this case: `test_publication_retry_reopen_retains_monotonic_reply_lower_bound` changes an authorized record's watermark to its source, which fails because the active consumed timestamp must equal the watermark, but it never deletes the field from a reopened pending record (`test_records_notifications.py:88-150`).

The migration needs an unambiguous one-time boundary that preserves valid legacy compatibility while making a missing watermark in already-migrated/current state fail closed. Until then, the lower bound is not durable under the requested tamper model.

## Closed checks

- **Normal schema/runtime/reopen behavior:** the closed schema requires a non-null watermark and forbids unknown fields (`control-plane-state.schema.json:31-39`). Runtime validation rejects a watermark before the source and requires an authorized request's active timestamp to equal the watermark (`contracts.py:629-656`). New requests initialize it from the source, successful consumption advances it, and reopen clears only active reply ID/timestamp while retaining the bound (`control_plane_records.py:414-426`, `control_plane_records.py:468-471`, `control_plane_records.py:485-512`).
- **Strict monotonicity without tampering:** same-ID, older-different, and equal-time-different replies are inert; a genuinely newer different reply is accepted once. The record regression covers all four cases (`test_records_notifications.py:114-150`), and the public provider-boundary regression asserts no provider-call increase for unattended, identical, older, or equal replies and exactly one increase for the newer reply (`test_publication_public_cli.py:267-310`).
- **Legacy migration in the intended case:** pending legacy requests backfill from `sourceTimestamp`, authorized legacy requests backfill from their active consumed timestamp, the revision advances once, and a second load is idempotent (`test_migration_status.py:34-75`). The P1 is specifically the absence of a way to prove that the input is genuinely legacy.
- **CAS and journal behavior:** migration runs under the control-plane shared mutex and writes atomically. Publication persistence still rejects stale supervisor CAS before proposal authority, commits publication summary and capability revision through paired CAS, and materializes only the digest that won that CAS (`operations.py:535-600`, `operations.py:603-621`). No journal replay or head-binding regression was found.
- **Capability revision fix from QA:** `save_authoritative()` refreshes only capabilities that are already `issued`, belong to the live lease run, match the exact current stage, and are within the existing `review`/`qa`/`docs`/`publication`/`completion` stage set (`operations.py:573-592`). It does not mint or revive capabilities, alter run/stage/expiry/scope, or extend reservation authority. The attended recovery still requires a distinct revision-, reservation-, operation-, and scope-bound one-shot mutation grant. No broader authority was found.

## Verification evidence

- Inspected the exact post-review-11 schema, runtime validation, store migration, request consumption/reopen, attended supervisor recovery, publication CAS/capability refresh, and focused tests; no Git, provider, network, or live-system call was used.
- `python -u -m unittest tests.linear_delivery_control_plane.test_records_notifications.RecordTests.test_publication_retry_reopen_retains_monotonic_reply_lower_bound tests.linear_delivery_control_plane.test_migration_status.MigrationStatusTests.test_control_plane_store_migrates_publication_reply_lower_bounds_once -v`: **PASS**, 2 tests in 0.353s.
- Direct disposable deletion-tamper probe: **FAIL as required for this finding** — revision 3 became 4, the missing watermark was backfilled to the source timestamp, and the older different reply was accepted.
- The single long public provider-boundary regression was started in isolation but did not complete within the review's bounded run and was terminated with its child process cleaned up. Its exact assertions were inspected; the normal-path behavior is also supported by the passing record regression. No aggregate or broader matrix was run.
