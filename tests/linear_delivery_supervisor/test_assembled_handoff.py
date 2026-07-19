from __future__ import annotations

import copy
import importlib
import os
import uuid
from unittest import mock

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    clean_observer,
    git,
    package,
)


assembled = importlib.import_module(package.__name__ + ".assembled_handoff")
cli = importlib.import_module(package.__name__ + ".cli")
supervisor = importlib.import_module(package.__name__ + ".supervisor")


class AssembledHandoffTests(StateEngineTestCase):
    def _engine(self):
        return supervisor.SupervisorEngine(
            manager=self.manager,
            local_observer=clean_observer,
        )

    def _reserve(self, engine, *, workflow_id=None):
        state, reservations = engine.store.load_state(), engine.store.load_reservations()
        return engine.reservations.reserve(
            workflow_id=workflow_id or self.descriptor["workflowId"],
            issue_id=None,
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="interactive-owner",
            run_id=None,
            expected_state_revision=state["revision"],
            expected_reservations_revision=reservations["revision"],
        )

    def _request(self, reserved, destination, *, workflow_id=None):
        state = self.store.load_state()
        reservations = self.store.load_reservations()
        return {
            "schemaVersion": "1.0",
            "operation": "Handoff",
            "requestId": str(uuid.uuid4()),
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.manager.home.repository),
            "requestedAt": "2026-07-18T12:00:00Z",
            "workflowId": workflow_id or self.descriptor["workflowId"],
            "sourcePath": os.fspath(self.repository),
            "destinationPath": os.fspath(destination),
            "expectedPaths": ["README.md"],
            "reservationId": reserved["reservationId"],
            "reservationControlRef": reserved["releaseAuthorizationRef"],
            "autonomousCapabilityRef": None,
            "expectedReservationRevision": reserved["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
            "runId": None,
        }

    def _leave_base_failure_for_recovery(self, engine, request, *, partial_rollback=False):
        operation_id = request["requestId"]
        engine.operations.begin(
            operation_id=operation_id,
            operation="Handoff",
            request=request,
        )
        source_identity = engine.runtime.observe_repository_identity(self.repository)
        destination = self.root / "destination"
        destination_identity = engine.runtime.observe_repository_identity(destination)
        engine.reservations.prepare_handoff_authorization(
            reservation_id=request["reservationId"],
            operation_id=operation_id,
            workflow_id=request["workflowId"],
            source_fingerprint=source_identity.physical_worktree_fingerprint,
            destination_fingerprint=destination_identity.physical_worktree_fingerprint,
            expected_paths=request["expectedPaths"],
            request=request,
            control_authorization_ref=request["reservationControlRef"],
            capability_ref=request["autonomousCapabilityRef"],
            expected_reservation_revision=request["expectedReservationRevision"],
            expected_state_revision=request["expectedStateRevision"],
            expected_reservations_revision=request["expectedReservationsRevision"],
        )
        context = assembled._write_recovery_context(
            engine,
            operation_id=operation_id,
            workflow_id=request["workflowId"],
            source_fingerprint=source_identity.physical_worktree_fingerprint,
            destination_fingerprint=destination_identity.physical_worktree_fingerprint,
            destination_path=destination,
            expected_paths=request["expectedPaths"],
            prior_evidence_ids=assembled._evidence_ids(engine, request["workflowId"]),
            destination_observation=assembled._destination_observation(engine, destination),
        )
        nonce = engine.reservations.resolve_handoff_authorization(operation_id)
        interlock = importlib.import_module(
            f"{engine.runtime.package.__name__}.reservation_interlock"
        )
        internal = interlock.InternalHandoffAuthorization(
            operation_id=operation_id,
            nonce=nonce,
        )
        handoff_module = importlib.import_module(
            f"{engine.runtime.package.__name__}.handoff"
        )
        original_rollback = handoff_module._rollback_paths

        def rollback_then_leave_partial(*args, **kwargs):
            original_rollback(*args, **kwargs)
            (destination / "README.md").write_text("partial destination\n", encoding="utf-8")

        rollback = rollback_then_leave_partial if partial_rollback else original_rollback
        injected = engine.runtime.HandoffError("injected post-apply base failure")
        with mock.patch.object(
            handoff_module,
            "_validate_transfer_content",
            side_effect=injected,
        ):
            with mock.patch.object(handoff_module, "_rollback_paths", side_effect=rollback):
                with self.assertRaises(engine.runtime.HandoffError):
                    self.manager.workflow_managed_handoff(
                        workflow_id=request["workflowId"],
                        destination_root=destination,
                        expected_paths=request["expectedPaths"],
                        _reservation_authorization=internal,
                    )
        return context

    def test_live_reservation_requires_assembled_transfer_and_revokes_source(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("handoff change\n", encoding="utf-8")

        with self.assertRaisesRegex(Exception, "assembled Handoff"):
            self.manager.workflow_managed_handoff(
                workflow_id=self.descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["README.md"],
            )

        request = self._request(reserved, destination)
        result = assembled.execute_assembled_handoff(engine, request)
        self.assertEqual("transferred", result["status"])
        self.assertEqual("handoff change\n", (destination / "README.md").read_text(encoding="utf-8"))

        current_reservations = engine.store.load_reservations()
        transferred = current_reservations["reservations"][reserved["reservationId"]]
        self.assertEqual("live", transferred["status"])
        self.assertNotEqual(
            self.manager.identity.physical_worktree_fingerprint,
            transferred["physicalWorktreeFingerprint"],
        )
        current_state = engine.store.load_state()
        with self.assertRaisesRegex(Exception, "not current"):
            engine.reservations.renew(
                reservation_id=reserved["reservationId"],
                owner_id="interactive-owner",
                expected_record_revision=transferred["revision"],
                expected_state_revision=current_state["revision"],
                expected_reservations_revision=current_reservations["revision"],
                control_authorization_ref=reserved["releaseAuthorizationRef"],
            )

        destination_manager = engine.runtime.WorkflowManager(
            destination,
            repository_key="test-repository",
            state_home_override=self.root / "state",
        )
        destination_engine = supervisor.SupervisorEngine(
            manager=destination_manager,
            local_observer=clean_observer,
        )
        renewed = destination_engine.reservations.renew(
            reservation_id=reserved["reservationId"],
            owner_id="interactive-owner",
            expected_record_revision=transferred["revision"],
            expected_state_revision=current_state["revision"],
            expected_reservations_revision=current_reservations["revision"],
            control_authorization_ref=transferred["releaseAuthorizationRef"],
        )
        self.assertGreater(renewed["revision"], transferred["revision"])

    def test_foreign_workflow_reservation_blocks_public_and_forged_assembled_handoff(self) -> None:
        other = self.manager.initialize_local(
            workflow="semi-autonomous", goal="Other workflow reservation"
        )
        engine = self._engine()
        reserved = self._reserve(engine, workflow_id=other["workflowId"])
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("cross-workflow bypass\n", encoding="utf-8")

        with self.assertRaisesRegex(Exception, "assembled Handoff"):
            self.manager.workflow_managed_handoff(
                workflow_id=self.descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["README.md"],
            )

        request = self._request(
            reserved, destination, workflow_id=other["workflowId"]
        )
        destination_identity = engine.runtime.observe_repository_identity(destination)
        engine.reservations.prepare_handoff_authorization(
            reservation_id=reserved["reservationId"],
            operation_id=request["requestId"],
            workflow_id=other["workflowId"],
            source_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            destination_fingerprint=destination_identity.physical_worktree_fingerprint,
            expected_paths=request["expectedPaths"],
            request=request,
            control_authorization_ref=request["reservationControlRef"],
            capability_ref=request["autonomousCapabilityRef"],
            expected_reservation_revision=reserved["revision"],
            expected_state_revision=request["expectedStateRevision"],
            expected_reservations_revision=request["expectedReservationsRevision"],
        )
        nonce = engine.reservations.resolve_handoff_authorization(request["requestId"])
        interlock = importlib.import_module(
            f"{engine.runtime.package.__name__}.reservation_interlock"
        )
        internal = interlock.InternalHandoffAuthorization(
            operation_id=request["requestId"], nonce=nonce
        )
        with self.assertRaisesRegex(Exception, "another workflow"):
            self.manager.workflow_managed_handoff(
                workflow_id=self.descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["README.md"],
                _reservation_authorization=internal,
            )

    def test_multiple_active_reservations_reject_one_shot_authorization(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        reservations_path = self.manager.home.repository / "reservations.json"
        index = self.manager.state_paths.read_json(reservations_path)
        duplicate = copy.deepcopy(index["reservations"][reserved["reservationId"]])
        duplicate_id = str(uuid.uuid4())
        duplicate["reservationId"] = duplicate_id
        duplicate["workflowId"] = str(uuid.uuid4())
        index["reservations"][duplicate_id] = duplicate
        index["revision"] += 1
        self.manager.state_paths.write_json(
            reservations_path,
            index,
            expected_revision=index["revision"] - 1,
        )
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("multiple reservations\n", encoding="utf-8")
        request = self._request(reserved, destination)
        destination_identity = engine.runtime.observe_repository_identity(destination)
        engine.reservations.prepare_handoff_authorization(
            reservation_id=reserved["reservationId"],
            operation_id=request["requestId"],
            workflow_id=self.descriptor["workflowId"],
            source_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            destination_fingerprint=destination_identity.physical_worktree_fingerprint,
            expected_paths=request["expectedPaths"],
            request=request,
            control_authorization_ref=request["reservationControlRef"],
            capability_ref=request["autonomousCapabilityRef"],
            expected_reservation_revision=reserved["revision"],
            expected_state_revision=request["expectedStateRevision"],
            expected_reservations_revision=request["expectedReservationsRevision"],
        )
        nonce = engine.reservations.resolve_handoff_authorization(request["requestId"])
        interlock = importlib.import_module(
            f"{engine.runtime.package.__name__}.reservation_interlock"
        )
        internal = interlock.InternalHandoffAuthorization(
            operation_id=request["requestId"], nonce=nonce
        )
        with self.assertRaisesRegex(Exception, "Multiple active repository reservations"):
            self.manager.workflow_managed_handoff(
                workflow_id=self.descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["README.md"],
                _reservation_authorization=internal,
            )

    def test_crash_recovery_restores_only_with_complete_failure_and_rollback_readback(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("recoverable failure\n", encoding="utf-8")
        request = self._request(reserved, destination)
        self._leave_base_failure_for_recovery(engine, request)

        recovered = assembled.recover_assembled_handoff(engine, request["requestId"])
        self.assertEqual("restored", recovered["status"])
        self.assertIsNone(engine.store.load_state()["handoffPending"])
        self.assertEqual("base\n", (destination / "README.md").read_text(encoding="utf-8"))

    def test_crash_after_phase_a_recovers_from_precommitted_context_idempotently(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        request = self._request(reserved, destination)
        engine.operations.begin(
            operation_id=request["requestId"],
            operation="Handoff",
            request=request,
        )
        prepare = engine.reservations.prepare_handoff_authorization

        def prepare_then_crash(**kwargs):
            prepare(**kwargs)
            raise SystemExit("injected crash after Phase A")

        with mock.patch.object(
            engine.reservations,
            "prepare_handoff_authorization",
            side_effect=prepare_then_crash,
        ):
            with self.assertRaises(SystemExit):
                assembled.execute_assembled_handoff(engine, request)

        self.assertTrue(assembled._context_path(engine, request["requestId"]).exists())
        self.assertEqual(
            request["requestId"],
            engine.store.load_state()["handoffPending"]["operationId"],
        )
        recovered = cli._execute(
            engine,
            {
                "operation": "Recover",
                "requestId": str(uuid.uuid4()),
                "operationId": request["requestId"],
                "expectedStateRevision": engine.store.load_state()["revision"],
            },
        )
        self.assertEqual("restored", recovered["handoffs"][0]["status"])
        self.assertIsNone(engine.store.load_state()["handoffPending"])
        self.assertEqual(
            "failed", engine.operations.load(request["requestId"])["journal"]["status"]
        )

        repeated = cli._execute(
            engine,
            {
                "operation": "Recover",
                "requestId": str(uuid.uuid4()),
                "operationId": request["requestId"],
                "expectedStateRevision": engine.store.load_state()["revision"],
            },
        )
        self.assertNotIn("handoffs", repeated)
        self.assertEqual(
            "failed", engine.operations.load(request["requestId"])["journal"]["status"]
        )

    def test_crash_after_context_before_phase_a_closes_pending_journal(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        request = self._request(reserved, destination)
        engine.operations.begin(
            operation_id=request["requestId"],
            operation="Handoff",
            request=request,
        )

        with mock.patch.object(
            engine.reservations,
            "prepare_handoff_authorization",
            side_effect=SystemExit("injected crash before Phase A"),
        ):
            with self.assertRaises(SystemExit):
                assembled.execute_assembled_handoff(engine, request)

        self.assertTrue(assembled._context_path(engine, request["requestId"]).exists())
        self.assertIsNone(engine.store.load_state()["handoffPending"])
        recovered = cli._execute(
            engine,
            {
                "operation": "Recover",
                "requestId": str(uuid.uuid4()),
                "operationId": request["requestId"],
                "expectedStateRevision": engine.store.load_state()["revision"],
            },
        )
        self.assertEqual("restored", recovered["handoffs"][0]["status"])
        self.assertEqual(
            "not-started", recovered["handoffs"][0]["baseHandoff"]
        )
        current = engine.store.load_reservations()["reservations"][
            reserved["reservationId"]
        ]
        self.assertEqual("live", current["status"])
        self.assertEqual(
            reserved["releaseAuthorizationRef"], current["releaseAuthorizationRef"]
        )
        self.assertEqual(
            "failed", engine.operations.load(request["requestId"])["journal"]["status"]
        )

        repeated = cli._execute(
            engine,
            {
                "operation": "Recover",
                "requestId": str(uuid.uuid4()),
                "operationId": request["requestId"],
                "expectedStateRevision": engine.store.load_state()["revision"],
            },
        )
        self.assertNotIn("handoffs", repeated)
        self.assertEqual(
            "failed", engine.operations.load(request["requestId"])["journal"]["status"]
        )

    def test_pre_phase_a_recovery_rejects_rewritten_clean_destination_baseline(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        request = self._request(reserved, destination)
        engine.operations.begin(
            operation_id=request["requestId"],
            operation="Handoff",
            request=request,
        )
        with mock.patch.object(
            engine.reservations,
            "prepare_handoff_authorization",
            side_effect=SystemExit("injected crash before Phase A"),
        ):
            with self.assertRaises(SystemExit):
                assembled.execute_assembled_handoff(engine, request)

        (destination / "README.md").write_text("tampered\n", encoding="utf-8")
        git(destination, "add", "README.md")
        git(destination, "commit", "-m", "rewrite destination baseline")
        context_path = assembled._context_path(engine, request["requestId"])
        context = engine.store.guard.read_json(context_path)
        context["destinationObservation"] = assembled._destination_observation(
            engine, destination
        )
        engine.store.guard.write_json(context_path, context)
        anchor_path = assembled._context_bundle_path(
            engine, request["requestId"]
        ) / "anchor.json"
        anchor = engine.store.guard.read_json(anchor_path)
        anchor["contextSha256"] = "sha256:" + assembled.sha256_json(context)
        engine.store.guard.write_json(anchor_path, anchor)

        with self.assertRaises(assembled.AssembledHandoffError):
            cli._execute(
                engine,
                {
                    "operation": "Recover",
                    "requestId": str(uuid.uuid4()),
                    "operationId": request["requestId"],
                    "expectedStateRevision": engine.store.load_state()["revision"],
                },
            )
        self.assertEqual(
            "pending", engine.operations.load(request["requestId"])["journal"]["status"]
        )
        self.assertEqual("ambiguous", engine.store.load_state()["recovery"]["status"])

    def test_proven_base_failure_journals_restored_control_authority(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text(
            "restored authority\n", encoding="utf-8"
        )
        request = self._request(reserved, destination)
        handoff_module = importlib.import_module(
            f"{engine.runtime.package.__name__}.handoff"
        )
        injected = engine.runtime.HandoffError("injected proven base failure")

        with mock.patch.object(
            handoff_module,
            "_validate_transfer_content",
            side_effect=injected,
        ):
            result = cli._journaled(
                engine,
                request,
                lambda: assembled.execute_assembled_handoff(engine, request),
            )

        self.assertEqual("restored", result["status"])
        self.assertEqual("proven-failure", result["baseHandoff"])
        restored = result["reservation"]
        self.assertEqual("restored", restored["status"])
        self.assertNotEqual(
            reserved["releaseAuthorizationRef"],
            restored["controlAuthorizationRef"],
        )
        current = engine.store.load_reservations()["reservations"][
            reserved["reservationId"]
        ]
        self.assertEqual("live", current["status"])
        self.assertEqual(
            restored["controlAuthorizationRef"],
            current["releaseAuthorizationRef"],
        )
        control = engine.reservations._resolve_authorization(
            restored["controlAuthorizationRef"],
            expected_kind="release",
        )
        self.assertEqual(current["revision"], control["binding"]["reservationRevision"])
        with self.assertRaises(Exception):
            engine.reservations._resolve_authorization(
                reserved["releaseAuthorizationRef"],
                expected_kind="release",
            )

        journaled = engine.operations.load(request["requestId"])
        self.assertEqual("completed", journaled["journal"]["status"])
        self.assertEqual(result, journaled["result"])

    def test_recover_closes_pending_outer_journal_after_phase_c_transfer(self) -> None:
        engine = self._engine()
        state = engine.store.load_state()
        lease = engine.leases.acquire(
            run_id=str(uuid.uuid4()),
            owner_id="controller-owner",
            expected_revision=state["revision"],
        )
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text(
            "phase-c transfer\n", encoding="utf-8"
        )
        request = self._request(reserved, destination)
        engine.operations.begin(
            operation_id=request["requestId"],
            operation="Handoff",
            request=request,
        )

        transferred = assembled.execute_assembled_handoff(engine, request)

        self.assertEqual("transferred", transferred["status"])
        self.assertIsNone(engine.store.load_state()["handoffPending"])
        finalized_state = engine.store.load_state()
        finalized_lease = finalized_state["lease"]
        self.assertEqual(finalized_state["revision"], finalized_lease["revision"])
        lease_sidecar = engine.store.guard.read_json(lease["capabilityRef"])
        self.assertEqual(
            engine.manager.identity.physical_worktree_fingerprint,
            lease_sidecar["physicalWorktreeFingerprint"],
        )
        self.assertNotEqual(
            engine.runtime.observe_repository_identity(destination).physical_worktree_fingerprint,
            lease_sidecar["physicalWorktreeFingerprint"],
        )
        pending = engine.operations.load(request["requestId"])
        self.assertEqual("pending", pending["journal"]["status"])

        state = finalized_state
        recovered = cli._execute(
            engine,
            {
                "operation": "Recover",
                "requestId": str(uuid.uuid4()),
                "operationId": request["requestId"],
                "expectedStateRevision": state["revision"],
            },
        )

        self.assertEqual("transferred", recovered["handoffs"][0]["status"])
        self.assertEqual(
            "recovered-after-phase-c",
            recovered["handoffs"][0]["baseHandoff"],
        )
        completed = engine.operations.load(request["requestId"])
        self.assertEqual("completed", completed["journal"]["status"])
        self.assertEqual("transferred", completed["result"]["status"])
        self.assertNotIn(request["requestId"], engine.operations.pending_ids())

    def test_recover_protects_finalized_incomplete_evidence_before_closing_journal(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text(
            "phase-c then tamper\n", encoding="utf-8"
        )
        request = self._request(reserved, destination)
        engine.operations.begin(
            operation_id=request["requestId"],
            operation="Handoff",
            request=request,
        )
        transferred = assembled.execute_assembled_handoff(engine, request)
        self.assertEqual("transferred", transferred["status"])
        self.assertIsNone(engine.store.load_state()["handoffPending"])

        # Phase C is durable, but the transfer proof is no longer complete.
        (destination / "README.md").write_text("tampered after phase c\n", encoding="utf-8")
        state = engine.store.load_state()
        recovery_at_handoff_completion: list[str] = []
        original_complete = engine.operations.complete

        def observe_completion(*args, **kwargs):
            if kwargs.get("operation") == "Handoff":
                recovery_at_handoff_completion.append(
                    engine.store.load_state()["recovery"]["status"]
                )
            return original_complete(*args, **kwargs)

        with mock.patch.object(
            engine.operations,
            "complete",
            side_effect=observe_completion,
        ):
            recovered = cli._execute(
                engine,
                {
                    "operation": "Recover",
                    "requestId": str(uuid.uuid4()),
                    "operationId": request["requestId"],
                    "expectedStateRevision": state["revision"],
                },
            )

        self.assertEqual(["ambiguous"], recovery_at_handoff_completion)
        self.assertEqual("protected", recovered["status"])
        self.assertEqual("protected", recovered["handoffs"][0]["status"])
        protection = engine.store.load_state()["recovery"]
        self.assertEqual("ambiguous", protection["status"])
        self.assertEqual(
            f"ambiguous-operation:{request['requestId']}",
            protection["reason"],
        )
        completed = engine.operations.load(request["requestId"])
        self.assertEqual("ambiguous", completed["journal"]["status"])

    def test_crash_recovery_protects_partial_destination_even_with_rollback_complete_claim(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("ambiguous failure\n", encoding="utf-8")
        request = self._request(reserved, destination)
        self._leave_base_failure_for_recovery(
            engine, request, partial_rollback=True
        )

        recovered = assembled.recover_assembled_handoff(engine, request["requestId"])
        self.assertEqual("protected", recovered["status"])
        self.assertEqual(
            request["requestId"],
            engine.store.load_state()["handoffPending"]["operationId"],
        )
        record = engine.store.load_reservations()["reservations"][reserved["reservationId"]]
        self.assertEqual("handoff-pending", record["status"])

    def test_crash_recovery_protects_tampered_rollback_evidence(self) -> None:
        engine = self._engine()
        reserved = self._reserve(engine)
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("tampered failure\n", encoding="utf-8")
        request = self._request(reserved, destination)
        context = self._leave_base_failure_for_recovery(engine, request)
        new_ids = assembled._evidence_ids(engine, request["workflowId"]) - set(
            context["priorEvidenceIds"]
        )
        self.assertEqual(1, len(new_ids))
        evidence = (
            self.manager.home.repository
            / "handoffs"
            / request["workflowId"]
            / next(iter(new_ids))
            / "result.json"
        )
        result = self.manager.state_paths.read_json(evidence)
        result.pop("rollbackStatus")
        self.manager.state_paths.write_json(evidence, result)

        recovered = assembled.recover_assembled_handoff(engine, request["requestId"])
        self.assertEqual("protected", recovered["status"])
        self.assertEqual(
            request["requestId"],
            engine.store.load_state()["handoffPending"]["operationId"],
        )
