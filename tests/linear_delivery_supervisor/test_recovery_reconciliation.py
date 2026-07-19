from __future__ import annotations

import copy
import uuid

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    clean_observer,
    lease_module,
    reservations_module,
    supervisor_module,
)


class RecoveryReconciliationTests(StateEngineTestCase):
    def test_pending_reserve_recovers_only_its_operation_bound_authority(self) -> None:
        engine = supervisor_module.SupervisorEngine(
            manager=self.manager,
            local_observer=clean_observer,
        )
        operation_id = str(uuid.uuid4())
        request = {
            "schemaVersion": "1.0",
            "requestId": operation_id,
            "operation": "Reserve",
            "workflowId": self.descriptor["workflowId"],
            "issueId": "SAAS-46",
            "ownerId": "owner",
            "runId": None,
            "expectedStateRevision": 1,
            "expectedReservationsRevision": 1,
        }
        engine.operations.begin(
            operation_id=operation_id,
            operation="Reserve",
            request=request,
        )
        committed = engine.reservations.reserve(
            reservation_id=operation_id,
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="owner",
            run_id=None,
            expected_state_revision=1,
            expected_reservations_revision=1,
        )
        recovered = engine.recovery.recover()
        self.assertEqual([operation_id], recovered["recoveredOperations"])
        journal = engine.operations.load(operation_id)
        self.assertEqual(committed, journal["result"])

        duplicate_id = str(uuid.uuid4())
        duplicate_request = dict(request, requestId=duplicate_id)
        engine.operations.begin(
            operation_id=duplicate_id,
            operation="Reserve",
            request=duplicate_request,
        )
        denied = engine.recovery.recover()
        self.assertEqual([duplicate_id], denied["failedOperations"])
        self.assertEqual(
            "failed", engine.operations.load(duplicate_id)["journal"]["status"]
        )

    def test_pending_renew_and_killed_expired_lease_recover_idempotently(self) -> None:
        clock = lease_module.ManualClock(1_000_000_000)
        engine = supervisor_module.SupervisorEngine(
            manager=self.manager,
            clock=clock,
            reservation_clock=clock.now_ns,
            local_observer=clean_observer,
        )
        run_id = str(uuid.uuid4())
        lease = engine.leases.acquire(
            run_id=run_id, owner_id="owner", expected_revision=1
        )
        operation_id = str(uuid.uuid4())
        request = {
            "schemaVersion": "1.0",
            "requestId": operation_id,
            "operation": "RenewLease",
            "runId": run_id,
            "ownerId": "owner",
            "expectedStateRevision": 2,
        }
        engine.operations.begin(
            operation_id=operation_id,
            operation="RenewLease",
            request=request,
        )
        renewed = engine.leases.renew(
            run_id=run_id,
            owner_id="owner",
            expected_revision=2,
            capability_ref=lease["capabilityRef"],
            operation_id=operation_id,
        )
        first = engine.recovery.recover()
        self.assertEqual([operation_id], first["recoveredOperations"])
        self.assertEqual("completed", engine.operations.load(operation_id)["journal"]["status"])
        self.assertEqual("ready", engine.recovery.recover()["status"])

        clock.set(renewed["expiresAtNs"] + 1)
        killed = engine.recovery.recover()
        self.assertEqual("recovered", killed["lease"]["status"])
        self.assertIsNone(engine.store.load_state()["lease"])
        current_revision = engine.store.load_state()["revision"]
        acquired = engine.leases.acquire(
            run_id=str(uuid.uuid4()),
            owner_id="next-owner",
            expected_revision=current_revision,
        )
        self.assertEqual("live", acquired["status"])

    def test_pending_renew_does_not_complete_after_unrelated_checkpoint(self) -> None:
        self.use_authoritative_issue_worktree()
        clock = lease_module.ManualClock(1_000_000_000)
        engine = supervisor_module.SupervisorEngine(
            manager=self.manager,
            clock=clock,
            reservation_clock=clock.now_ns,
            local_observer=clean_observer,
        )
        run_id = str(uuid.uuid4())
        lease = engine.leases.acquire(
            run_id=run_id,
            owner_id="owner",
            expected_revision=engine.store.load_state()["revision"],
        )
        expected_revision = engine.store.load_state()["revision"]
        operation_id = str(uuid.uuid4())
        request = {
            "schemaVersion": "1.0",
            "requestId": operation_id,
            "operation": "RenewLease",
            "runId": run_id,
            "ownerId": "owner",
            "expectedStateRevision": expected_revision,
        }
        engine.operations.begin(
            operation_id=operation_id,
            operation="RenewLease",
            request=request,
        )

        # Model an unrelated checkpoint-like state advance while the renewal
        # journal remains pending.  Revision/run/owner alone must not be
        # accepted as proof that this specific renewal committed.
        with engine.store.mutex():
            state, reservations = engine.store.load_pair_unlocked()
            after = copy.deepcopy(state)
            after["revision"] = state["revision"] + 1
            after["lease"]["revision"] = after["revision"]
            engine.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="test-unrelated-checkpoint",
            )

        recovered = engine.recovery.recover()
        self.assertEqual([operation_id], recovered["ambiguousOperations"])
        self.assertEqual(
            "ambiguous", engine.operations.load(operation_id)["journal"]["status"]
        )

    def test_only_expired_clean_planning_reservation_reclaims_and_ambiguous_journal_protects(self) -> None:
        now = [1_000_000_000]
        engine = supervisor_module.SupervisorEngine(
            manager=self.manager,
            reservation_clock=lambda: now[0],
            local_observer=clean_observer,
        )
        record = engine.reservations.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="owner",
            run_id=None,
            expected_state_revision=1,
            expected_reservations_revision=1,
            duration_ns=100,
            planning_only=True,
        )
        with self.assertRaises(reservations_module.ReservationError):
            engine.reservations.reclaim_expired(
                reservation_id=record["reservationId"],
                expected_state_revision=1,
                expected_reservations_revision=2,
            )
        live = engine.recovery.recover()
        self.assertEqual([], live["reclaimedReservations"])
        self.assertEqual(
            "live",
            engine.store.load_reservations()["reservations"][record["reservationId"]]["status"],
        )
        now[0] += 101
        recovered = engine.recovery.recover()
        self.assertEqual([record["reservationId"]], recovered["reclaimedReservations"])

        operation_id = str(uuid.uuid4())
        request = {
            "schemaVersion": "1.0",
            "requestId": operation_id,
            "operation": "Cleanup",
            "expectedStateRevision": engine.store.load_state()["revision"],
            "gateOperationId": str(uuid.uuid4()),
        }
        engine.operations.begin(
            operation_id=operation_id, operation="Cleanup", request=request
        )
        with engine.store.mutex():
            state, reservations = engine.store.load_pair_unlocked()
            after = copy.deepcopy(state)
            after["recovery"] = {
                "status": "required",
                "reason": "unrelated-state-change",
                "updatedAtNs": now[0],
            }
            after["revision"] = state["revision"] + 1
            engine.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="test-unrelated-change",
            )
        ambiguous = engine.recovery.recover()
        self.assertEqual([operation_id], ambiguous["ambiguousOperations"])
        self.assertEqual("protected", ambiguous["status"])
        self.assertEqual("ambiguous", engine.store.load_state()["recovery"]["status"])
        second = engine.recovery.recover()
        self.assertEqual("protected", second["status"])
        self.assertEqual([], second["pendingOperations"])

    def test_expired_non_planning_reservation_remains_protected(self) -> None:
        now = [1_000_000_000]
        engine = supervisor_module.SupervisorEngine(
            manager=self.manager,
            reservation_clock=lambda: now[0],
            local_observer=clean_observer,
        )
        record = engine.reservations.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="owner",
            run_id=None,
            expected_state_revision=1,
            expected_reservations_revision=1,
            duration_ns=100,
            planning_only=False,
        )
        now[0] += 101
        recovered = engine.recovery.recover()
        self.assertEqual([], recovered["reclaimedReservations"])
        self.assertEqual([record["reservationId"]], recovered["protectedReservations"])
        current = engine.store.load_reservations()["reservations"][record["reservationId"]]
        self.assertEqual("live", current["status"])
        self.assertFalse(current["protectedWork"]["planningOnly"])
