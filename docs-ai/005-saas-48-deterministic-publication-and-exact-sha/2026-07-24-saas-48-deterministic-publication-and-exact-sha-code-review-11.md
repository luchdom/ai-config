# SAAS-48 deterministic publication and exact-SHA gates — Code review 11

## Verdict

**FAIL** — one P1 remains in the post-QA recovery fix. The revision-preservation change closes the observed capability-staleness failure without widening publication stages, and identical-reply plus unattended replay stop before the provider. However, reopening erases the consumed reply timestamp, so a different reply that is older than the consumed reply can be accepted as fresh attended authority and can reach a provider mutation.

## Finding counts

- P1: 1
- P2: 0
- P3: 0

## P1 — Reopened requests accept an older alternate reply as fresh attended authority

`PublicationRecovery.attended_retry()` correctly persists the consumed reply identity before attempting, and after proven non-application it preserves that identity in the authoritative publication while reopening the request (`publication_recovery.py:145-152`, `publication_recovery.py:176-187`). The reopening transition then clears both `consumedReplyId` and `consumedReplyTimestamp` from the request (`control_plane_records.py:479-484`). Consequently, the next `consume_publication_reply()` can compare only against the request's original `sourceTimestamp`; its intended monotonic comparison against the prior consumed timestamp is disabled because that field is now null (`control_plane_records.py:433-438`). The publication record cannot supply the missing bound because its closed schema persists only `consumedReplyId`, not the consumed timestamp.

The supervisor rejects only an attended reply whose ID equals the publication's retained ID (`supervisor.py:1111-1114`). A different ID therefore passes this guard. Once the reopened control-plane record accepts it, the engine consumes a fresh exact mutation authorization and invokes the provider (`supervisor.py:1121-1139`, `supervisor.py:1162-1181`). This is not merely a record-layer concern: a public fixture probe consumed `reply-first` at `00:10`, crashed with independently proven non-application, rejected the same reply without another provider call, then accepted `reply-older-alternate` at `00:05` and advanced the publication to `pushed`; provider calls increased from 2 to 3.

This violates the stated requirement that the reopened request admit a **genuinely newer** attended reply. A delayed or previously observed alternate owner reply can trigger push, PR, or merge recovery despite predating the reply whose one-shot authority was already consumed. Preserve a durable monotonic lower bound outside the pending request's nullable active-consumption fields, and require the next reply timestamp to be strictly greater before authorizing any provider attempt. Add a public regression covering older-different rejection and newer-different success, in addition to identical reply and unattended replay.

## Closed checks

- **Capability revision preservation:** `PublicationJournal.save_authoritative()` refreshes only already-`issued` capabilities for the live lease run, exact current stage, and the closed `review`/`qa`/`docs`/`publication`/`completion` set (`operations.py:573-592`). It does not mint a capability, revive a consumed/revoked capability, change expiry, run, issue, worktree, or allowed transitions. Reservation authorization still requires the exact current capability and a distinct revision-, reservation-, operation-, and scope-bound one-shot mutation grant. No stage or reservation-authority broadening was found.
- **Identical consumed reply:** the authoritative publication retains `consumedReplyId`; `recover_publication()` rejects that exact ID before consumption/provider dispatch (`supervisor.py:1111-1114`). The public adversarial probe observed no provider-call increase for the same reply after reopen.
- **Unattended replay:** a paused publication with a consumed reply and no attended payload is rejected before provider dispatch (`supervisor.py:1088-1092`). The formerly failing public test asserts provider calls remain unchanged on this path.
- **CAS and journal replay:** publication persistence still checks the caller's expected supervisor revision, commits the publication summary and refreshed capability revision in one paired CAS, and materializes the authoritative journal afterward (`operations.py:535-600`). Immutable/head-bound journal replay remained passing in the focused regression.

## Test adequacy

The updated public test now proves crash/non-application reopening, preserved refusal/consumed identity, restored labels, and unattended no-provider replay (`test_publication_public_cli.py:267-284`). The focused recovery test proves the policy callback reopens and retains publication identity (`test_publication_recovery.py:62-77`). Neither test exercises a different reply older than the consumed reply or proves that only a strictly newer alternate reply may proceed. The implementation evidence's "strictly newer reply" claim is therefore not supported by its cited tests and is contradicted by the public probe above.

## Verification evidence

- Read code-review 10, the runtime-QA FAIL artifact, the updated implementation evidence, the exact formerly failing public test, and the post-fix `operations.py`, `supervisor.py`, `publication_recovery.py`, and `control_plane_records.py` paths. No Git/provider/live-network command was used.
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_public_cli.PublicationPublicCliTests.test_attended_consumption_precedes_crash_and_nonapplication_restores_labels -v`: **PASS** — 1 test in 119.658s.
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_recovery -v`: **PASS** — 9 tests in 0.052s.
- `python -u -m unittest tests.linear_delivery_supervisor.test_publication_contracts.PublicationContractTests.test_publication_journal_replay_is_immutable_and_head_bound -v`: **PASS** — 1 test in 3.706s.
- Changed recovery/publication Python modules compile with `py_compile`: **PASS**.
- Direct control-plane monotonicity diagnostic: **FAIL as required for this review finding** — after consuming at `00:10` and reopening, a different reply at `00:05` was accepted.
- Public provider-boundary adversarial probe: **FAIL as required for this review finding** — same reply caused no extra provider call; older alternate reply advanced to `pushed` and added one provider call (2 → 3).

The repository aggregate and long publication/repair matrices were not run in this narrow review. The prior QA aggregate timeout remains separate runtime-QA evidence and is not converted into a code-review finding here.
