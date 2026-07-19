from __future__ import annotations

import copy

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    contracts,
    store_module,
)


class StoreRecoveryTests(StateEngineTestCase):
    def test_topology_contract_cas_and_crash_recovery(self) -> None:
        self.assertEqual(1, contracts.validate_contract("supervisor-state", self.store.load_state())["revision"])
        self.assertEqual(1, contracts.validate_contract("editing-reservation", self.store.load_reservations())["revision"])
        for name in self.store.TOPOLOGY_DIRECTORIES:
            self.assertTrue(self.store.directories[name].is_dir())

        def fail_after_first(stage, _transaction):
            if stage == "after-first-write":
                raise RuntimeError("injected interruption")

        self.store.fault_injector = fail_after_first
        state, reservations = self.store.load_state(), self.store.load_reservations()
        with self.assertRaises(RuntimeError):
            self.store.commit_pair(
                expected_state_revision=state["revision"],
                expected_reservations_revision=reservations["revision"],
                operation="test-crash",
                mutate=lambda next_state, _: next_state["recovery"].update(
                    {"status": "required", "reason": "test", "updatedAtNs": 1}
                ),
            )
        self.store.fault_injector = None
        recovered = self.store.recover()
        self.assertEqual(1, len(recovered))
        self.assertEqual("required", self.store.load_state()["recovery"]["status"])

    def test_changed_replay_and_secret_like_state_fail_closed(self) -> None:
        state, reservations = self.store.load_state(), self.store.load_reservations()
        with self.assertRaises(store_module.SupervisorConflictError):
            self.store.commit_pair(
                expected_state_revision=state["revision"] + 1,
                expected_reservations_revision=reservations["revision"],
                operation="stale",
                mutate=lambda *_: None,
            )
        with self.assertRaises(store_module.SupervisorStoreError):
            self.store.commit_pair(
                expected_state_revision=state["revision"],
                expected_reservations_revision=reservations["revision"],
                operation="secret",
                mutate=lambda next_state, _: next_state["checkpoints"].update(
                    {"x": {"api_key": "lin_api_abcdefghijklmnopqrstuvwxyz"}}
                ),
            )

    def test_nested_persisted_documents_are_contract_validated_on_read(self) -> None:
        state = self.store.load_state()
        state["recovery"]["status"] = "invented"
        self.store.guard.write_json(
            self.store.state_path, state, expected_revision=state["revision"]
        )
        with self.assertRaisesRegex(
            store_module.SupervisorStoreError, "complete persisted contract"
        ):
            self.store.load_state()

    def test_nested_reservation_corruption_is_rejected_on_read(self) -> None:
        reservations = self.store.load_reservations()
        reservation_id = "00000000-0000-4000-8000-000000000046"
        reservations["reservations"][reservation_id] = {
            "reservationId": reservation_id,
            "status": "protected",
        }
        self.store.guard.write_json(
            self.store.reservations_path,
            reservations,
            expected_revision=reservations["revision"],
        )
        with self.assertRaisesRegex(
            store_module.SupervisorStoreError, "complete persisted contract"
        ):
            self.store.load_reservations()

    def test_invalid_nested_commit_is_rejected_before_persistence(self) -> None:
        state = self.store.load_state()
        reservations = self.store.load_reservations()
        with self.assertRaisesRegex(
            store_module.SupervisorStoreError, "complete persisted contract"
        ):
            self.store.commit_pair(
                expected_state_revision=state["revision"],
                expected_reservations_revision=reservations["revision"],
                operation="invalid-nested-state",
                mutate=lambda next_state, _: next_state["clockEvidence"].update(
                    {"status": "invented"}
                ),
            )
        self.assertEqual(state, self.store.load_state())
        self.assertEqual(reservations, self.store.load_reservations())
