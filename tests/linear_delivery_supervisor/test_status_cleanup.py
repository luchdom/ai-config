from __future__ import annotations

import importlib
import json
import os
import subprocess
import uuid
from pathlib import Path
from unittest import mock

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    clean_observer,
    package,
)


cli = importlib.import_module(package.__name__ + ".cli")
operations = importlib.import_module(package.__name__ + ".operations")
supervisor = importlib.import_module(package.__name__ + ".supervisor")
worktrees = importlib.import_module(package.__name__ + ".worktrees")


class StatusCleanupTests(StateEngineTestCase):
    def _engine(self):
        return supervisor.SupervisorEngine(
            manager=self.manager,
            local_observer=clean_observer,
        )

    def _base_command(self, operation: str, request_id: str) -> dict:
        return {
            "schemaVersion": "1.0",
            "operation": operation,
            "requestId": request_id,
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.manager.home.repository),
            "requestedAt": "2026-07-18T12:00:00Z",
        }

    def _write_request(self, name: str, command: dict) -> Path:
        path = self.repository / name
        path.write_text(json.dumps(command), encoding="utf-8")
        return path

    def _gate(self, engine, *, operation_id: str | None = None):
        gates = worktrees.WorktreeManager(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.root / "state",
            store=engine.store,
        )
        gate_operation_id = operation_id or str(uuid.uuid4())
        head = subprocess.run(
            ["git", "-C", os.fspath(self.repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        ).stdout.strip()
        gate = gates.create_gate_worktree(gate_operation_id, exact_sha=head)
        state = engine.store.load_state()
        gates.set_gate_evidence(
            gate_operation_id,
            expected_state_revision=state["revision"],
            operation_status="resolved",
            attestation_status="complete",
        )
        return gate_operation_id, gate

    def _reserve(self, engine):
        state, reservations = engine.store.load_state(), engine.store.load_reservations()
        return engine.reservations.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id=None,
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="manual-owner",
            run_id=None,
            expected_state_revision=state["revision"],
            expected_reservations_revision=reservations["revision"],
        )

    def _release(self, engine, reservation):
        state, reservations = engine.store.load_state(), engine.store.load_reservations()
        return engine.reservations.release(
            reservation_id=reservation["reservationId"],
            authorization_ref=reservation["releaseAuthorizationRef"],
            operation_id=str(uuid.uuid4()),
            expected_record_revision=reservation["revision"],
            expected_state_revision=state["revision"],
            expected_reservations_revision=reservations["revision"],
            capability_ref=None,
            trusted_observation_ref=None,
        )

    def _cleanup_command(
        self,
        engine,
        release,
        gate_operation_id: str,
        *,
        request_id: str | None = None,
        authorization_ref: str | None = None,
    ) -> dict:
        state, reservations = engine.store.load_state(), engine.store.load_reservations()
        selected_ref = authorization_ref or release["cleanupAuthorizationRefs"][
            gate_operation_id
        ]
        if request_id is None:
            authorization = engine.reservations._resolve_authorization(
                selected_ref,
                expected_kind="cleanup",
            )
            request_id = authorization["binding"]["operationId"]
        return {
            **self._base_command("Cleanup", request_id),
            "releasedReservationId": release["reservationId"],
            "gateOperationId": gate_operation_id,
            "cleanupAuthorizationRef": selected_ref,
            "expectedReleasedReservationRevision": reservations["reservations"][
                release["reservationId"]
            ]["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }

    def test_operation_result_does_not_invalidate_authority_revision(self) -> None:
        journal = operations.OperationJournal(self.store)
        before = self.store.load_state()["revision"]
        operation_id = str(uuid.uuid4())
        request = {"workflowId": self.descriptor["workflowId"]}
        journal.begin(operation_id=operation_id, operation="Status", request=request)
        journal.complete(
            operation_id=operation_id,
            operation="Status",
            request=request,
            result={"status": "ready"},
        )
        self.assertEqual(before, self.store.load_state()["revision"])

    def test_status_cannot_disclose_or_reconstruct_lease_authority(self) -> None:
        engine = self._engine()
        run_id = str(uuid.uuid4())
        acquired = engine.leases.acquire(
            run_id=run_id,
            owner_id="scheduled-owner",
            expected_revision=engine.store.load_state()["revision"],
        )

        status = engine.status()
        self.assertEqual(run_id, status["lease"]["runId"])
        self.assertNotIn("capabilityRef", status["lease"])
        self.assertNotIn("capabilitySha256", status["lease"])
        self.assertNotIn(acquired["capabilityRef"], json.dumps(status))
        self.assertNotEqual(
            Path(acquired["capabilityRef"]).name,
            "lease.capability.json",
        )

        with self.assertRaisesRegex(Exception, "Existing or expired lease"):
            engine.leases.acquire(
                run_id=status["lease"]["runId"],
                owner_id=status["lease"]["ownerId"],
                expected_revision=status["lease"]["revision"],
            )

        guessed_ref = self.manager.home.repository / "runs" / run_id / "lease.capability.json"
        denied = {
            **self._base_command("RenewLease", str(uuid.uuid4())),
            "runId": run_id,
            "ownerId": "scheduled-owner",
            "leaseCapabilityRef": os.fspath(guessed_ref),
            "expectedStateRevision": status["stateRevision"],
        }
        request_path = self.manager.home.repository / "guessed-renew.json"
        request_path.write_text(json.dumps(denied), encoding="utf-8")
        with self.assertRaisesRegex(Exception, "capability authority is mismatched"):
            cli.run_request(request_path)

    def test_renew_rotates_authority_and_old_result_cannot_release(self) -> None:
        engine = self._engine()
        run_id = str(uuid.uuid4())
        acquired = engine.leases.acquire(
            run_id=run_id,
            owner_id="scheduled-owner",
            expected_revision=engine.store.load_state()["revision"],
        )
        renew_id = str(uuid.uuid4())
        renewed = engine.leases.renew(
            run_id=run_id,
            owner_id="scheduled-owner",
            expected_revision=engine.store.load_state()["revision"],
            capability_ref=acquired["capabilityRef"],
            operation_id=renew_id,
        )
        self.assertNotEqual(acquired["capabilityRef"], renewed["capabilityRef"])
        self.assertNotIn(renew_id, Path(renewed["capabilityRef"]).name)
        self.assertEqual(
            renew_id,
            engine.store.guard.read_json(renewed["capabilityRef"])["capabilityId"],
        )
        with self.assertRaisesRegex(Exception, "capability authority is mismatched"):
            engine.leases.release(
                run_id=run_id,
                owner_id="scheduled-owner",
                expected_revision=engine.store.load_state()["revision"],
                capability_ref=acquired["capabilityRef"],
            )

    def test_release_mints_cleanup_authorization_bound_to_gate_and_revisions(self) -> None:
        engine = self._engine()
        gate_operation_id, gate = self._gate(engine)
        release = self._release(engine, self._reserve(engine))

        authorization_ref = release["cleanupAuthorizationRefs"][gate_operation_id]
        authorization = engine.reservations._resolve_authorization(
            authorization_ref,
            expected_kind="cleanup",
        )
        binding = authorization["binding"]
        state, reservations = engine.store.load_state(), engine.store.load_reservations()
        released = reservations["reservations"][release["reservationId"]]

        self.assertEqual("released", released["status"])
        self.assertEqual(release["reservationRevision"], released["revision"])
        self.assertEqual(release["reservationId"], binding["reservationId"])
        self.assertEqual(gate_operation_id, binding["gateOperationId"])
        self.assertEqual(gate["path"], binding["gatePath"])
        self.assertEqual(released["revision"], binding["releasedReservationRevision"])
        self.assertEqual(state["revision"], binding["stateRevision"])
        self.assertEqual(reservations["revision"], binding["reservationsRevision"])
        self.assertEqual([gate["path"]], binding["scope"])

    def test_public_cleanup_requires_release_and_consumes_exact_one_shot_gate_scope(self) -> None:
        engine = self._engine()
        gate_operation_id, gate = self._gate(engine)
        release = self._release(engine, self._reserve(engine))
        command = self._cleanup_command(engine, release, gate_operation_id)
        request_path = self._write_request("cleanup.json", command)

        result = cli.run_request(request_path)

        self.assertEqual("clean", result["status"])
        self.assertEqual([gate["path"]], result["removed"])
        self.assertFalse(Path(gate["path"]).exists())
        self.assertEqual(
            "cleaned",
            engine.store.load_state()["gateWorktrees"][gate_operation_id]["status"],
        )
        released = engine.store.load_reservations()["reservations"][release["reservationId"]]
        self.assertEqual({}, released["cleanupAuthorizationRefs"])

        # Exact replay returns the durable result without re-running Git removal.
        self.assertEqual(result, cli.run_request(request_path))
        changed = self._cleanup_command(
            engine,
            {**release, "cleanupAuthorizationRefs": {gate_operation_id: command["cleanupAuthorizationRef"]}},
            gate_operation_id,
            request_id=str(uuid.uuid4()),
        )
        with self.assertRaisesRegex(Exception, "absent or inactive"):
            cli.run_request(self._write_request("cleanup-changed.json", changed))

    def test_cleanup_refuses_live_reservation_and_live_lease_after_release(self) -> None:
        engine = self._engine()
        gate_operation_id, gate = self._gate(engine)
        first_release = self._release(engine, self._reserve(engine))

        live = self._reserve(engine)
        live_denied = self._cleanup_command(engine, first_release, gate_operation_id)
        with self.assertRaisesRegex(Exception, "live lease or editing authority"):
            cli.run_request(self._write_request("cleanup-live-reservation.json", live_denied))
        self.assertTrue(Path(gate["path"]).exists())

        second_release = self._release(engine, live)
        state = engine.store.load_state()
        engine.leases.acquire(
            run_id=str(uuid.uuid4()),
            owner_id="scheduled-owner",
            expected_revision=state["revision"],
        )
        lease_denied = self._cleanup_command(engine, second_release, gate_operation_id)
        with self.assertRaisesRegex(Exception, "live lease or editing authority"):
            cli.run_request(self._write_request("cleanup-live-lease.json", lease_denied))
        self.assertTrue(Path(gate["path"]).exists())

    def test_cleanup_denies_authorization_for_another_gate_without_deleting_either(self) -> None:
        engine = self._engine()
        first_id, first_gate = self._gate(engine)
        second_id, second_gate = self._gate(engine)
        release = self._release(engine, self._reserve(engine))
        denied = self._cleanup_command(
            engine,
            release,
            second_id,
            authorization_ref=release["cleanupAuthorizationRefs"][first_id],
        )

        with self.assertRaisesRegex(Exception, "not current for this gate"):
            cli.run_request(self._write_request("cleanup-wrong-gate.json", denied))

        self.assertTrue(Path(first_gate["path"]).exists())
        self.assertTrue(Path(second_gate["path"]).exists())
        state = engine.store.load_state()
        self.assertEqual("active", state["gateWorktrees"][first_id]["status"])
        self.assertEqual("active", state["gateWorktrees"][second_id]["status"])

    def test_cleanup_denies_stale_released_reservation_revision(self) -> None:
        engine = self._engine()
        gate_operation_id, gate = self._gate(engine)
        release = self._release(engine, self._reserve(engine))
        denied = self._cleanup_command(engine, release, gate_operation_id)
        denied["expectedReleasedReservationRevision"] -= 1

        with self.assertRaisesRegex(Exception, "released-reservation binding is stale"):
            cli.run_request(self._write_request("cleanup-stale-release.json", denied))

        self.assertTrue(Path(gate["path"]).exists())
        self.assertEqual(
            "active",
            engine.store.load_state()["gateWorktrees"][gate_operation_id]["status"],
        )

    def test_cleanup_post_remove_commit_failure_is_ambiguous_and_protected(self) -> None:
        engine = self._engine()
        gate_operation_id, gate = self._gate(engine)
        release = self._release(engine, self._reserve(engine))
        command = self._cleanup_command(
            engine,
            release,
            gate_operation_id,
        )
        request_id = command["requestId"]
        request_path = self._write_request("cleanup-ambiguous.json", command)
        store_type = type(engine.store)
        original_commit = store_type.commit_pair_unlocked
        tripped = False

        def fail_once(instance, *args, **kwargs):
            nonlocal tripped
            if not tripped and kwargs.get("operation") == f"Cleanup:{request_id}":
                tripped = True
                raise RuntimeError("injected post-remove commit failure")
            return original_commit(instance, *args, **kwargs)

        with mock.patch.object(store_type, "commit_pair_unlocked", new=fail_once):
            with self.assertRaises(cli.CleanupAmbiguousError):
                cli.run_request(request_path)

        observed = engine.store.load_state()
        self.assertTrue(tripped)
        self.assertFalse(Path(gate["path"]).exists())
        self.assertEqual(
            "ambiguous", observed["gateWorktrees"][gate_operation_id]["status"]
        )
        self.assertEqual("ambiguous", observed["recovery"]["status"])
        evidence = engine.operations.load(request_id)
        self.assertEqual("ambiguous", evidence["journal"]["status"])
