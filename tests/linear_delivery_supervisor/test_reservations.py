from __future__ import annotations

import copy
import os
import uuid
from pathlib import Path

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    clean_observer,
    contracts,
    git,
    lease_module,
    reservations_module,
    store_module,
)


class ReservationTests(StateEngineTestCase):
    def manager_for_reservations(self, observer=clean_observer):
        return reservations_module.ReservationManager(
            self.manager, self.store, local_observer=observer
        )

    def reserve(self, manager):
        return manager.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="interactive-owner",
            run_id=None,
            expected_state_revision=1,
            expected_reservations_revision=1,
        )

    def register_issue_worktree(self) -> tuple[int, Path, str]:
        worktree = self.store.root / "worktrees" / "SAAS-46"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        git(self.repository, "worktree", "add", "-b", "saas-46-test", worktree, "HEAD")
        fixture_path = self.repository / "handoff-fixture.txt"
        fixture_path.write_text("issue worktree authority\n", encoding="utf-8")
        self.manager.workflow_managed_handoff(
            workflow_id=self.descriptor["workflowId"],
            destination_root=worktree,
            expected_paths=[fixture_path.relative_to(self.repository).as_posix()],
        )
        observed = self.store.runtime.observe_repository_identity(worktree)
        head_sha = git(worktree, "rev-parse", "HEAD").stdout.strip()
        branch = git(worktree, "branch", "--show-current").stdout.strip()
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            after = copy.deepcopy(state)
            after["issueWorktrees"]["SAAS-46"] = {
                "issueId": "SAAS-46",
                "workflowId": self.descriptor["workflowId"],
                "repositoryId": self.manager.identity.repository_id,
                "repositoryKey": self.manager.repository_key,
                "normalizedCommonDir": os.path.normcase(
                    os.path.realpath(self.manager.identity.common_dir)
                ).replace("\\", "/"),
                "worktreePath": os.path.normcase(
                    os.path.realpath(observed.repository_root)
                ).replace("\\", "/"),
                "physicalWorktreeFingerprint": observed.physical_worktree_fingerprint,
                "branch": branch,
                "headSha": head_sha,
                "handoffOperationId": None,
                "status": "active",
            }
            after["worktreeAllocations"]["issue:SAAS-46"] = {
                "allocationId": "issue:SAAS-46",
                "kind": "issue",
                "subjectId": "SAAS-46",
                "repositoryId": self.manager.identity.repository_id,
                "repositoryKey": self.manager.repository_key,
                "normalizedCommonDir": os.path.normcase(
                    os.path.realpath(self.manager.identity.common_dir)
                ).replace("\\", "/"),
                "worktreePath": os.path.normcase(
                    os.path.realpath(observed.repository_root)
                ).replace("\\", "/"),
                "branch": branch,
                "exactSha": head_sha,
                "physicalWorktreeFingerprint": observed.physical_worktree_fingerprint,
                "handoffOperationId": None,
                "status": "completed",
            }
            after["revision"] = state["revision"] + 1
            committed, _ = self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="TestFixture:RegisterIssueWorktree",
            )
            return (
                committed["revision"],
                Path(observed.repository_root),
                observed.physical_worktree_fingerprint,
            )

    def test_clean_release_is_one_shot_and_contract_valid(self) -> None:
        reservations = self.manager_for_reservations()
        record = self.reserve(reservations)
        contracts.validate_contract("editing-reservation", self.store.load_reservations())
        authorization = self.store.guard.read_json(record["releaseAuthorizationRef"])
        contracts.validate_contract("release-authorization", authorization)
        result = reservations.release(
            reservation_id=record["reservationId"],
            authorization_ref=record["releaseAuthorizationRef"],
            operation_id=authorization["operationId"],
            expected_record_revision=1,
            expected_state_revision=1,
            expected_reservations_revision=2,
        )
        self.assertEqual("released", result["status"])
        with self.assertRaises(reservations_module.ReservationError):
            reservations.release(
                reservation_id=record["reservationId"],
                authorization_ref=record["releaseAuthorizationRef"],
                operation_id=authorization["operationId"],
                expected_record_revision=2,
                expected_state_revision=1,
                expected_reservations_revision=3,
            )

    def test_duplicate_reserve_cannot_retrieve_existing_control_authority(self) -> None:
        reservations = self.manager_for_reservations()
        record = self.reserve(reservations)
        before = self.store.load_reservations()
        with self.assertRaises(store_module.SupervisorConflictError):
            self.reserve(reservations)
        self.assertEqual(before, self.store.load_reservations())
        self.assertEqual(
            record["releaseAuthorizationRef"],
            before["reservations"][record["reservationId"]]["releaseAuthorizationRef"],
        )

    def test_protected_work_never_releases_on_time_or_prose(self) -> None:
        is_dirty = [False]

        def dirty(store, worktree, planning_only):
            value = clean_observer(store, worktree, planning_only)
            value["dirty"] = is_dirty[0]
            return value

        reservations = self.manager_for_reservations(dirty)
        record = self.reserve(reservations)
        authorization = self.store.guard.read_json(record["releaseAuthorizationRef"])
        is_dirty[0] = True
        with self.assertRaises(reservations_module.ReservationError):
            reservations.release(
                reservation_id=record["reservationId"],
                authorization_ref=record["releaseAuthorizationRef"],
                operation_id=authorization["operationId"],
                expected_record_revision=1,
                expected_state_revision=1,
                expected_reservations_revision=2,
            )
        reservation_document = self.store.load_reservations()
        current = reservation_document["reservations"][record["reservationId"]]
        self.assertEqual("live", current["status"])
        self.assertTrue(current["protectedWork"]["dirty"])
        self.assertEqual(1, current["revision"])
        self.assertEqual(record["releaseAuthorizationRef"], current["releaseAuthorizationRef"])
        self.assertEqual(3, reservation_document["revision"])

        is_dirty[0] = False
        retry = reservations.release(
            reservation_id=record["reservationId"],
            authorization_ref=record["releaseAuthorizationRef"],
            operation_id=authorization["operationId"],
            expected_record_revision=1,
            expected_state_revision=1,
            expected_reservations_revision=3,
        )
        self.assertEqual("released", retry["status"])

    def test_mutation_authorization_enforces_every_binding_expiry_and_one_shot(self) -> None:
        now = [1_000_000_000]
        reservations = reservations_module.ReservationManager(
            self.manager,
            self.store,
            clock=lambda: now[0],
            local_observer=clean_observer,
        )
        record = self.reserve(reservations)
        target_operation_id = str(uuid.uuid4())
        authorization = reservations.authorize_mutation(
            reservation_id=record["reservationId"],
            authorization_id=str(uuid.uuid4()),
            target_operation_id=target_operation_id,
            scope=["README.md"],
            expected_record_revision=1,
            expected_state_revision=1,
            expected_reservations_revision=2,
            control_authorization_ref=record["releaseAuthorizationRef"],
            duration_ns=100,
        )

        called = []

        def mutate(_record, _after_state):
            called.append(True)
            return {"status": "clean"}

        with self.assertRaises(reservations_module.ReservationError):
            reservations.execute_authorized_mutation(
                reservation_id=record["reservationId"],
                authorization_ref=authorization["authorizationRef"],
                operation_id=str(uuid.uuid4()),
                required_scope=["README.md"],
                expected_record_revision=2,
                expected_state_revision=1,
                expected_reservations_revision=3,
                physical_worktree_fingerprint=record["physicalWorktreeFingerprint"],
                mutation=mutate,
            )

        self.assertEqual([], called)
        now[0] += 100
        with self.assertRaises(reservations_module.ReservationError):
            reservations.execute_authorized_mutation(
                reservation_id=record["reservationId"],
                authorization_ref=authorization["authorizationRef"],
                operation_id=target_operation_id,
                required_scope=["README.md"],
                expected_record_revision=2,
                expected_state_revision=1,
                expected_reservations_revision=3,
                physical_worktree_fingerprint=record["physicalWorktreeFingerprint"],
                mutation=mutate,
            )
        self.assertEqual([], called)

        second = reservations.authorize_mutation(
            reservation_id=record["reservationId"],
            authorization_id=str(uuid.uuid4()),
            target_operation_id=target_operation_id,
            scope=["README.md"],
            expected_record_revision=2,
            expected_state_revision=1,
            expected_reservations_revision=3,
            control_authorization_ref=authorization["controlAuthorizationRef"],
        )
        result = reservations.execute_authorized_mutation(
            reservation_id=record["reservationId"],
            authorization_ref=second["authorizationRef"],
            operation_id=target_operation_id,
            required_scope=["README.md"],
            expected_record_revision=3,
            expected_state_revision=1,
            expected_reservations_revision=4,
            physical_worktree_fingerprint=record["physicalWorktreeFingerprint"],
            mutation=mutate,
        )
        self.assertEqual("clean", result["status"])
        with self.assertRaises(reservations_module.ReservationError):
            reservations.execute_authorized_mutation(
                reservation_id=record["reservationId"],
                authorization_ref=second["authorizationRef"],
                operation_id=target_operation_id,
                required_scope=["README.md"],
                expected_record_revision=3,
                expected_state_revision=1,
                expected_reservations_revision=5,
                physical_worktree_fingerprint=record["physicalWorktreeFingerprint"],
                mutation=mutate,
            )

    def test_reservation_control_rejects_missing_stale_and_expired_references(self) -> None:
        now = [1_000_000_000]
        reservations = reservations_module.ReservationManager(
            self.manager,
            self.store,
            clock=lambda: now[0],
            local_observer=clean_observer,
        )
        record = self.reserve(reservations)
        with self.assertRaises(reservations_module.ReservationError):
            reservations.release(
                reservation_id=record["reservationId"],
                authorization_ref=self.store.root / "reservation-authorizations" / "missing.json",
                operation_id=str(uuid.uuid4()),
                expected_record_revision=1,
                expected_state_revision=1,
                expected_reservations_revision=2,
            )

        renewed = reservations.renew(
            reservation_id=record["reservationId"],
            owner_id="interactive-owner",
            expected_record_revision=1,
            expected_state_revision=1,
            expected_reservations_revision=2,
            control_authorization_ref=record["releaseAuthorizationRef"],
        )
        with self.assertRaises(reservations_module.ReservationError):
            reservations.release(
                reservation_id=record["reservationId"],
                authorization_ref=record["releaseAuthorizationRef"],
                operation_id=str(uuid.uuid4()),
                expected_record_revision=2,
                expected_state_revision=1,
                expected_reservations_revision=3,
            )

        now[0] += reservations.DEFAULT_DURATION_NS
        with self.assertRaises(reservations_module.ReservationError):
            reservations.release(
                reservation_id=record["reservationId"],
                authorization_ref=renewed["releaseAuthorizationRef"],
                operation_id=str(uuid.uuid4()),
                expected_record_revision=2,
                expected_state_revision=1,
                expected_reservations_revision=3,
            )

    def test_expired_semi_autonomous_reservation_can_reauthorize_then_release(self) -> None:
        now = [1_000_000_000]
        reservations = reservations_module.ReservationManager(
            self.manager,
            self.store,
            clock=lambda: now[0],
            local_observer=clean_observer,
        )
        record = self.reserve(reservations)
        now[0] = record["expiresAtNs"]

        with self.assertRaises(reservations_module.ReservationError):
            reservations.release(
                reservation_id=record["reservationId"],
                authorization_ref=record["releaseAuthorizationRef"],
                operation_id=str(uuid.uuid4()),
                expected_record_revision=record["revision"],
                expected_state_revision=1,
                expected_reservations_revision=2,
            )

        renewed = reservations.renew(
            reservation_id=record["reservationId"],
            owner_id="interactive-owner",
            expected_record_revision=record["revision"],
            expected_state_revision=1,
            expected_reservations_revision=2,
            control_authorization_ref=record["releaseAuthorizationRef"],
        )
        self.assertEqual("live", renewed["status"])
        with self.assertRaises(reservations_module.ReservationError):
            reservations.renew(
                reservation_id=record["reservationId"],
                owner_id="interactive-owner",
                expected_record_revision=renewed["revision"],
                expected_state_revision=1,
                expected_reservations_revision=3,
                control_authorization_ref=record["releaseAuthorizationRef"],
            )

        authorization = self.store.guard.read_json(renewed["releaseAuthorizationRef"])
        released = reservations.release(
            reservation_id=record["reservationId"],
            authorization_ref=renewed["releaseAuthorizationRef"],
            operation_id=authorization["operationId"],
            expected_record_revision=renewed["revision"],
            expected_state_revision=1,
            expected_reservations_revision=3,
        )
        self.assertEqual("released", released["status"])

    def test_protected_and_expired_reservations_remain_exclusive_and_block_base_handoff(self) -> None:
        reservations = self.manager_for_reservations()
        record = self.reserve(reservations)
        destination = self.linked_worktree()

        for status in ("protected", "expired"):
            with self.subTest(status=status):
                document = self.store.load_reservations()
                document["reservations"][record["reservationId"]]["status"] = status
                contracts.validate_contract("editing-reservation", document)
                self.store.guard.write_json(
                    self.store.reservations_path,
                    document,
                    expected_revision=document["revision"],
                )
                with self.assertRaisesRegex(Exception, "already has"):
                    reservations.reserve(
                        reservation_id=str(uuid.uuid4()),
                        workflow_id=self.descriptor["workflowId"],
                        issue_id="SAAS-46",
                        worktree_path=self.repository,
                        physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
                        policy="semi-autonomous",
                        owner_id="other-owner",
                        run_id=None,
                        expected_state_revision=1,
                        expected_reservations_revision=document["revision"],
                    )
                with self.assertRaisesRegex(Exception, "reservation requires assembled Handoff"):
                    self.manager.workflow_managed_handoff(
                        workflow_id=self.descriptor["workflowId"],
                        destination_root=destination,
                        expected_paths=["README.md"],
                    )

        released = reservations.release(
            reservation_id=record["reservationId"],
            authorization_ref=record["releaseAuthorizationRef"],
            operation_id=str(uuid.uuid4()),
            expected_record_revision=record["revision"],
            expected_state_revision=1,
            expected_reservations_revision=2,
        )
        self.assertEqual("released", released["status"])
        replacement = reservations.reserve(
            reservation_id=str(uuid.uuid4()),
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="replacement-owner",
            run_id=None,
            expected_state_revision=1,
            expected_reservations_revision=3,
        )
        self.assertEqual("live", replacement["status"])

    def test_unknown_reservation_status_fails_closed_for_store_and_base_handoff(self) -> None:
        reservations = self.manager_for_reservations()
        record = self.reserve(reservations)
        destination = self.linked_worktree()
        document = self.store.load_reservations()
        document["reservations"][record["reservationId"]]["status"] = "invented"
        self.store.guard.write_json(
            self.store.reservations_path,
            document,
            expected_revision=document["revision"],
        )
        with self.assertRaisesRegex(store_module.SupervisorStoreError, "persisted contract"):
            self.store.load_reservations()
        with self.assertRaisesRegex(Exception, "status is unknown"):
            self.manager.workflow_managed_handoff(
                workflow_id=self.descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["README.md"],
            )

    def test_merged_pr_observation_clears_remote_protection_for_release(self) -> None:
        def merged_elsewhere(store, worktree, planning_only):
            value = clean_observer(store, worktree, planning_only)
            value.update(
                {
                    "unpushed": True,
                    "unmerged": True,
                    "prOpen": True,
                    "prId": "46",
                    "prState": "open",
                }
            )
            return value

        reservations = self.manager_for_reservations(merged_elsewhere)
        record = self.reserve(reservations)
        observation = reservations.record_trusted_observation(
            adapter_id="fixture-github",
            adapter_version="1.0",
            operation_id=str(uuid.uuid4()),
            repository_id=self.manager.identity.repository_id,
            head_sha=record["protectedWork"]["headSha"],
            pr_id="46",
            pr_state="merged",
            branch=record["protectedWork"]["branch"],
        )
        result = reservations.release(
            reservation_id=record["reservationId"],
            authorization_ref=record["releaseAuthorizationRef"],
            operation_id=str(uuid.uuid4()),
            expected_record_revision=1,
            expected_state_revision=1,
            expected_reservations_revision=2,
            trusted_observation_ref=observation["observationRef"],
        )
        self.assertEqual("released", result["status"])
        released = self.store.load_reservations()["reservations"][record["reservationId"]]
        self.assertFalse(released["protectedWork"]["unpushed"])
        self.assertFalse(released["protectedWork"]["unmerged"])
        self.assertEqual("merged", released["protectedWork"]["prState"])

    def test_handoff_pending_record_and_internal_nonce_are_bound(self) -> None:
        reservations = self.manager_for_reservations()
        record = reservations.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id=None,
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            policy="semi-autonomous",
            owner_id="interactive-owner",
            run_id=None,
            expected_state_revision=1,
            expected_reservations_revision=1,
        )
        destination = self.linked_worktree()
        observed = self.store.runtime.observe_repository_identity(destination)
        operation_id = str(uuid.uuid4())
        authorization = reservations.prepare_handoff_authorization(
            reservation_id=record["reservationId"],
            operation_id=operation_id,
            workflow_id=self.descriptor["workflowId"],
            source_fingerprint=self.manager.identity.physical_worktree_fingerprint,
            destination_fingerprint=observed.physical_worktree_fingerprint,
            expected_paths=["src/feature.py"],
            request={
                "operationId": operation_id,
                "sourcePath": os.fspath(self.repository),
                "destinationPath": os.fspath(destination),
            },
            control_authorization_ref=record["releaseAuthorizationRef"],
            expected_reservation_revision=1,
            expected_state_revision=1,
            expected_reservations_revision=2,
        )
        contracts.validate_contract("handoff-authorization", authorization)
        nonce = reservations.resolve_handoff_authorization(operation_id)
        self.assertGreaterEqual(len(nonce), 32)
        with self.manager.registry.mutex():
            inspected = reservations_module.inspect_handoff_interlock(
                self.manager, self.descriptor["workflowId"], already_locked=True
            )
        self.assertEqual(operation_id, inspected["handoffPending"]["state"]["operationId"])

    def test_autonomous_reservation_rejects_missing_expired_and_stale_capabilities(self) -> None:
        clock = lease_module.ManualClock(1_000_000_000)
        leases = lease_module.LeaseManager(self.store, clock=clock)
        reservations = reservations_module.ReservationManager(
            self.manager,
            self.store,
            clock=clock.now_ns,
            local_observer=clean_observer,
        )
        run_id = str(uuid.uuid4())
        mapping_revision, issue_worktree, issue_fingerprint = self.register_issue_worktree()
        lease = leases.acquire(
            run_id=run_id,
            owner_id="owner",
            expected_revision=mapping_revision,
        )
        stale = leases.prepare_iteration(
            run_id=run_id,
            owner_id="owner",
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            expected_revision=mapping_revision + 1,
            lease_capability_ref=lease["capabilityRef"],
            stage="implement",
        )
        current = leases.prepare_iteration(
            run_id=run_id,
            owner_id="owner",
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            expected_revision=mapping_revision + 2,
            lease_capability_ref=lease["capabilityRef"],
            stage="implement",
            duration_ns=100,
        )
        state_revision = mapping_revision + 3

        for capability_ref in (None, stale["capabilityRef"]):
            with self.subTest(capability_ref=capability_ref):
                with self.assertRaises(reservations_module.ReservationError):
                    reservations.reserve(
                        workflow_id=self.descriptor["workflowId"],
                        issue_id="SAAS-46",
                        worktree_path=issue_worktree,
                        physical_worktree_fingerprint=issue_fingerprint,
                        policy="autonomous",
                        owner_id="owner",
                        run_id=run_id,
                        expected_state_revision=state_revision,
                        expected_reservations_revision=1,
                        capability_ref=capability_ref,
                    )

        record = reservations.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            policy="autonomous",
            owner_id="owner",
            run_id=run_id,
            expected_state_revision=state_revision,
            expected_reservations_revision=1,
            capability_ref=current["capabilityRef"],
        )
        clock.set(1_000_000_100)
        with self.assertRaises(reservations_module.ReservationError):
            reservations.authorize_mutation(
                reservation_id=record["reservationId"],
                authorization_id=str(uuid.uuid4()),
                target_operation_id=str(uuid.uuid4()),
                scope=["README.md"],
                expected_record_revision=1,
                expected_state_revision=state_revision,
                expected_reservations_revision=2,
                control_authorization_ref=record["releaseAuthorizationRef"],
                capability_ref=current["capabilityRef"],
            )

    def test_expired_autonomous_authority_can_reauthorize_lifecycle_without_mutation(self) -> None:
        clock = lease_module.ManualClock(1_000_000_000)
        leases = lease_module.LeaseManager(self.store, clock=clock)
        reservations = reservations_module.ReservationManager(
            self.manager,
            self.store,
            clock=clock.now_ns,
            local_observer=clean_observer,
        )
        run_id = str(uuid.uuid4())
        mapping_revision, issue_worktree, issue_fingerprint = self.register_issue_worktree()
        lease = leases.acquire(
            run_id=run_id,
            owner_id="owner",
            expected_revision=mapping_revision,
            duration_ns=1_000_000,
        )
        prepared = leases.prepare_iteration(
            run_id=run_id,
            owner_id="owner",
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            expected_revision=mapping_revision + 1,
            lease_capability_ref=lease["capabilityRef"],
            stage="implement",
            duration_ns=1_000_000,
        )
        record = reservations.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            policy="autonomous",
            owner_id="owner",
            run_id=run_id,
            expected_state_revision=mapping_revision + 2,
            expected_reservations_revision=1,
            capability_ref=prepared["capabilityRef"],
            duration_ns=1_000_000,
        )

        clock.set(1_001_000_000)
        recovery = leases.recover_expired(expected_revision=mapping_revision + 2)
        self.assertEqual("protected", recovery["status"])
        protected_revision = self.store.load_state()["revision"]
        renewed_lease = leases.renew(
            run_id=run_id,
            owner_id="owner",
            expected_revision=protected_revision,
            capability_ref=lease["capabilityRef"],
        )
        renewed_record = reservations.renew(
            reservation_id=record["reservationId"],
            owner_id="owner",
            expected_record_revision=record["revision"],
            expected_state_revision=renewed_lease["revision"],
            expected_reservations_revision=2,
            control_authorization_ref=record["releaseAuthorizationRef"],
            capability_ref=prepared["capabilityRef"],
        )

        with self.assertRaises(reservations_module.ReservationError):
            reservations.authorize_mutation(
                reservation_id=record["reservationId"],
                authorization_id=str(uuid.uuid4()),
                target_operation_id=str(uuid.uuid4()),
                scope=["README.md"],
                expected_record_revision=renewed_record["revision"],
                expected_state_revision=renewed_lease["revision"],
                expected_reservations_revision=3,
                control_authorization_ref=renewed_record["releaseAuthorizationRef"],
                capability_ref=prepared["capabilityRef"],
            )

        current = leases.prepare_iteration(
            run_id=run_id,
            owner_id="owner",
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            expected_revision=renewed_lease["revision"],
            lease_capability_ref=renewed_lease["capabilityRef"],
            stage="implement",
        )
        authorization = self.store.guard.read_json(
            renewed_record["releaseAuthorizationRef"]
        )
        released = reservations.release(
            reservation_id=record["reservationId"],
            authorization_ref=renewed_record["releaseAuthorizationRef"],
            operation_id=authorization["operationId"],
            expected_record_revision=renewed_record["revision"],
            expected_state_revision=self.store.load_state()["revision"],
            expected_reservations_revision=3,
            capability_ref=current["capabilityRef"],
        )
        self.assertEqual("released", released["status"])

    def test_partial_capability_transfer_recovers_and_rotates_source_authority(self) -> None:
        class InjectedTransferFailure(Exception):
            pass

        clock = lease_module.ManualClock(1_000_000_000)
        leases = lease_module.LeaseManager(self.store, clock=clock)
        run_id = str(uuid.uuid4())
        mapping_revision, issue_worktree, issue_fingerprint = self.register_issue_worktree()
        lease = leases.acquire(
            run_id=run_id, owner_id="owner", expected_revision=mapping_revision
        )
        prepared = leases.prepare_iteration(
            run_id=run_id,
            owner_id="owner",
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            expected_revision=mapping_revision + 1,
            lease_capability_ref=lease["capabilityRef"],
            stage="implement",
        )
        reservations = reservations_module.ReservationManager(
            self.manager,
            self.store,
            clock=clock.now_ns,
            local_observer=clean_observer,
        )
        record = reservations.reserve(
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=issue_worktree,
            physical_worktree_fingerprint=issue_fingerprint,
            policy="autonomous",
            owner_id="owner",
            run_id=run_id,
            expected_state_revision=mapping_revision + 2,
            expected_reservations_revision=1,
            capability_ref=prepared["capabilityRef"],
        )
        destination = self.store.root / "worktrees" / "SAAS-46-transfer"
        git(
            self.repository,
            "worktree",
            "add",
            "-b",
            "saas-46-transfer-partial",
            destination,
            "HEAD",
        )
        observed = self.store.runtime.observe_repository_identity(destination)
        operation_id = str(uuid.uuid4())
        reservations.prepare_handoff_authorization(
            reservation_id=record["reservationId"],
            operation_id=operation_id,
            workflow_id=self.descriptor["workflowId"],
            source_fingerprint=issue_fingerprint,
            destination_fingerprint=observed.physical_worktree_fingerprint,
            expected_paths=["src/feature.py"],
            request={
                "operationId": operation_id,
                "sourcePath": os.fspath(issue_worktree),
                "destinationPath": os.fspath(destination),
            },
            control_authorization_ref=record["releaseAuthorizationRef"],
            capability_ref=prepared["capabilityRef"],
            expected_reservation_revision=1,
            expected_state_revision=mapping_revision + 2,
            expected_reservations_revision=2,
        )

        def interrupt(stage, _operation):
            if stage == "after-capability-transfer":
                raise InjectedTransferFailure("partial transfer")

        reservations.transfer_fault_injector = interrupt
        with self.assertRaises(InjectedTransferFailure):
            reservations.finalize_handoff(
                operation_id=operation_id,
                outcome="succeeded",
                destination_fingerprint=observed.physical_worktree_fingerprint,
                destination_worktree_path=destination,
            )
        self.assertIsNotNone(self.store.load_state()["handoffPending"])
        self.assertEqual(
            observed.physical_worktree_fingerprint,
            self.store.guard.read_json(prepared["capabilityRef"])[
                "physicalWorktreeFingerprint"
            ],
        )
        reservations.transfer_fault_injector = None
        result = reservations.recover_handoff(
            operation_id=operation_id,
            proven_outcome="succeeded",
            destination_fingerprint=observed.physical_worktree_fingerprint,
            destination_worktree_path=destination,
        )
        self.assertEqual("transferred", result["status"])
        renewed = leases.renew(
            run_id=run_id,
            owner_id="owner",
            expected_revision=mapping_revision + 4,
            capability_ref=lease["capabilityRef"],
        )
        self.assertEqual("live", renewed["status"])
        prepared_ref = (
            self.store.root
            / "runs"
            / run_id
            / f"{prepared['preparedIterationId']}.prepared-iteration.json"
        )
        authoritative_prepared = self.store.guard.read_json(prepared_ref)
        self.assertEqual(observed.physical_worktree_fingerprint, authoritative_prepared["physicalWorktreeFingerprint"])
        self.assertEqual(
            os.path.normcase(os.path.realpath(destination)).replace("\\", "/"),
            authoritative_prepared["worktreePath"],
        )
        current_record = self.store.load_reservations()["reservations"][record["reservationId"]]
        self.assertEqual(result["controlAuthorizationRef"], current_record["releaseAuthorizationRef"])
        self.assertNotEqual(record["releaseAuthorizationRef"], current_record["releaseAuthorizationRef"])
