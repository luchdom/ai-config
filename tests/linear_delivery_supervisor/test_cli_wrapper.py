from __future__ import annotations

import importlib
import json
import os
import subprocess
import uuid
from pathlib import Path

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    git,
    package,
)


cli = importlib.import_module(package.__name__ + ".cli")
worktrees = importlib.import_module(package.__name__ + ".worktrees")


class CliWrapperTests(StateEngineTestCase):
    def status_request(self) -> dict:
        return {
            "schemaVersion": "1.0",
            "operation": "Status",
            "requestId": str(uuid.uuid4()),
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.manager.home.repository),
            "requestedAt": "2026-07-18T12:00:00Z",
            "workflowId": self.descriptor["workflowId"],
        }

    def test_status_cli_uses_contained_request_and_does_not_mutate_revision(self) -> None:
        request_path = self.repository / "status-request.json"
        request_path.write_text(json.dumps(self.status_request()), encoding="utf-8")
        before = cli.SupervisorEngine(
            manager=self.manager
        ).store.load_state()["revision"]
        result = cli.run_request(request_path)
        self.assertEqual("test-repository", result["repositoryKey"])
        after = cli.SupervisorEngine(
            manager=self.manager
        ).store.load_state()["revision"]
        self.assertEqual(before, after)

    def test_powershell_wrapper_is_fixed_and_emits_one_json_result(self) -> None:
        request_path = self.repository / "wrapper-status.json"
        request_path.write_text(json.dumps(self.status_request()), encoding="utf-8")
        wrapper = Path(package.__path__[0]) / "agent-worker-engine.ps1"
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-File",
                os.fspath(wrapper),
                "-RequestPath",
                os.fspath(request_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIsInstance(json.loads(completed.stdout), dict)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def write_request(
        self, name: str, request: dict, *, state_owned: bool = False
    ) -> Path:
        root = self.manager.home.repository if state_owned else self.repository
        path = root / name
        path.write_text(json.dumps(request), encoding="utf-8")
        return path

    def run_cli(self, name: str, request: dict) -> dict:
        return cli.run_request(self.write_request(name, request, state_owned=True))

    def base_request(self, operation: str, *, request_id: str | None = None) -> dict:
        return {
            "schemaVersion": "1.0",
            "operation": operation,
            "requestId": request_id or str(uuid.uuid4()),
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.manager.home.repository),
            "requestedAt": "2026-07-18T12:00:00Z",
        }

    def test_public_lease_lifecycle_success_and_authority_negatives(self) -> None:
        acquire = {
            **self.base_request("AcquireLease"),
            "ownerId": "scheduled-owner",
            "expectedStateRevision": 1,
        }
        lease = self.run_cli("acquire.json", acquire)
        self.assertEqual(acquire["requestId"], lease["runId"])

        wrong_renew = {
            **self.base_request("RenewLease"),
            "runId": acquire["requestId"],
            "ownerId": "wrong-owner",
            "leaseCapabilityRef": lease["capabilityRef"],
            "expectedStateRevision": 2,
        }
        with self.assertRaisesRegex(Exception, "owner"):
            self.run_cli("renew-denied.json", wrong_renew)

        renew = dict(wrong_renew, requestId=str(uuid.uuid4()), ownerId="scheduled-owner")
        renewed = self.run_cli("renew.json", renew)
        self.assertEqual(acquire["requestId"], renewed["runId"])

        wrong_release = {
            **self.base_request("ReleaseLease"),
            "runId": str(uuid.uuid4()),
            "ownerId": "scheduled-owner",
            "leaseCapabilityRef": renewed["capabilityRef"],
            "expectedStateRevision": 3,
        }
        with self.assertRaisesRegex(Exception, "run"):
            self.run_cli("release-lease-denied.json", wrong_release)

        release = dict(
            wrong_release,
            requestId=str(uuid.uuid4()),
            runId=acquire["requestId"],
        )
        released = self.run_cli("release-lease.json", release)
        self.assertEqual("released", released["status"])

    def test_public_reserve_success_and_repository_conflict(self) -> None:
        reserve = {
            **self.base_request("Reserve"),
            "workflowId": self.descriptor["workflowId"],
            "issueId": None,
            "worktreePath": os.fspath(self.repository),
            "policy": "semi-autonomous",
            "ownerId": "interactive-owner",
            "runId": None,
            "autonomousCapabilityRef": None,
            "expectedStateRevision": 1,
            "expectedReservationsRevision": 1,
        }
        record = self.run_cli("reserve.json", reserve)
        self.assertEqual("live", record["status"])

        other = self.manager.initialize_local(
            workflow="semi-autonomous", goal="Conflicting workflow"
        )
        conflict = dict(
            reserve,
            requestId=str(uuid.uuid4()),
            workflowId=other["workflowId"],
            ownerId="other-owner",
            expectedReservationsRevision=2,
        )
        with self.assertRaisesRegex(Exception, "already has"):
            self.run_cli("reserve-denied.json", conflict)

    def test_public_reserve_rejects_a_queued_stale_reservation_revision(self) -> None:
        git(self.repository, "add", "docs-ai")
        git(self.repository, "commit", "-m", "track workflow descriptor")
        stale = {
            **self.base_request("Reserve"),
            "workflowId": self.descriptor["workflowId"],
            "issueId": None,
            "worktreePath": os.fspath(self.repository),
            "policy": "semi-autonomous",
            "ownerId": "queued-owner",
            "runId": None,
            "autonomousCapabilityRef": None,
            "expectedStateRevision": 1,
            "expectedReservationsRevision": 1,
        }
        first = dict(
            stale,
            requestId=str(uuid.uuid4()),
            ownerId="first-owner",
        )
        record = self.run_cli("first-reserve.json", first)
        release = {
            **self.base_request("Release"),
            "reservationId": record["reservationId"],
            "reservationControlRef": record["releaseAuthorizationRef"],
            "autonomousCapabilityRef": None,
            "trustedObservationRef": None,
            "expectedReservationRevision": record["revision"],
            "expectedStateRevision": 1,
            "expectedReservationsRevision": 2,
        }
        self.assertEqual("released", self.run_cli("first-release.json", release)["status"])

        with self.assertRaisesRegex(Exception, "revision is stale"):
            self.run_cli("queued-stale-reserve.json", stale)
        evidence = cli.SupervisorEngine(manager=self.manager).operations.load(
            stale["requestId"]
        )
        self.assertEqual(
            1, evidence["request"]["expectedReservationsRevision"]
        )
        self.assertEqual("failed", evidence["journal"]["status"])

    def checkpoint_request(self, *, expected_stage: str) -> tuple[dict, dict]:
        controller_repository = self.repository
        issue_record = self.use_authoritative_issue_worktree()
        issue_repository = Path(issue_record["path"])
        self.repository = controller_repository
        engine = cli.SupervisorEngine(manager=self.manager)
        acquire = {
            **self.base_request("AcquireLease"),
            "ownerId": "worker-owner",
            "expectedStateRevision": engine.store.load_state()["revision"],
        }
        lease = self.run_cli("checkpoint-acquire.json", acquire)
        run_id = acquire["requestId"]
        prepare = {
            **self.base_request("PrepareIteration"),
            "runId": run_id,
            "issueId": "SAAS-46",
            "workflowId": self.descriptor["workflowId"],
            "worktreePath": os.fspath(issue_repository),
            "leaseCapabilityRef": lease["capabilityRef"],
            "expectedStateRevision": engine.store.load_state()["revision"],
            "expectedStage": "implement",
        }
        prepared = self.run_cli("prepare-iteration.json", prepare)
        transition_id = str(uuid.uuid4())
        (issue_repository / "docs-ai").mkdir(exist_ok=True)
        (issue_repository / "docs-ai" / "review.md").write_text(
            "review evidence\n", encoding="utf-8"
        )
        (issue_repository / "README.md").write_text(
            "implemented\n", encoding="utf-8"
        )
        head = subprocess.run(
            ["git", "-C", os.fspath(issue_repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        ).stdout.strip()
        worker_result = {
            "schemaVersion": "1.0",
            "preparedIterationId": prepared["preparedIterationId"],
            "runId": run_id,
            "workflowId": self.descriptor["workflowId"],
            "issueId": "SAAS-46",
            "transitionId": transition_id,
            "outcome": "advanced",
            "completedStage": "implement",
            "proposedNextStage": "review",
            "artifactManifest": ["docs-ai/review.md"],
            "changedPaths": [],
            "summary": "Schema-valid worker evidence is ready for review.",
            "proposedExternalTransitions": [],
            "pause": None,
            "observed": {
                "repositoryId": self.manager.identity.repository_id,
                "physicalWorktreeFingerprint": issue_record[
                    "physicalWorktreeFingerprint"
                ],
                "headSha": head,
            },
        }
        worker_path = issue_repository / "worker-result.json"
        worker_path.write_text(json.dumps(worker_result), encoding="utf-8")
        changed = set(
            item.decode("utf-8", "strict")
            for item in subprocess.run(
                [
                    "git",
                    "--no-optional-locks",
                    "-C",
                    os.fspath(issue_repository),
                    "diff",
                    "--name-only",
                    "-z",
                    "HEAD",
                    "--",
                ],
                check=True,
                capture_output=True,
                shell=False,
            ).stdout.split(b"\0")
            if item
        )
        changed.update(
            item.decode("utf-8", "strict")
            for item in subprocess.run(
                [
                    "git",
                    "--no-optional-locks",
                    "-C",
                    os.fspath(issue_repository),
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "-z",
                ],
                check=True,
                capture_output=True,
                shell=False,
            ).stdout.split(b"\0")
            if item
        )
        worker_result["changedPaths"] = sorted(changed)
        worker_path.write_text(json.dumps(worker_result), encoding="utf-8")
        command = {
            "schemaVersion": "1.0",
            "operation": "ApplyCheckpoint",
            "requestId": str(uuid.uuid4()),
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.manager.home.repository),
            "requestedAt": "2026-07-18T12:00:00Z",
            "runId": run_id,
            "preparedIterationRef": os.fspath(
                self.manager.home.repository
                / "runs"
                / run_id
                / f"{prepared['preparedIterationId']}.prepared-iteration.json"
            ),
            "workerResultPath": os.fspath(worker_path),
            "transitionId": transition_id,
            "expectedStateRevision": prepared["stateRevision"],
            "expectedStage": expected_stage,
        }
        return command, worker_result

    def test_public_apply_checkpoint_enforces_expected_stage(self) -> None:
        command, _ = self.checkpoint_request(expected_stage="implement")
        result = self.run_cli("checkpoint-request.json", command)
        self.assertEqual("applied", result["status"])
        self.assertEqual(
            "review",
            cli.SupervisorEngine(manager=self.manager).store.load_state()[
                "currentWork"
            ]["stage"],
        )

    def test_public_apply_checkpoint_rejects_stage_mismatch(self) -> None:
        command, _ = self.checkpoint_request(expected_stage="audit")
        with self.assertRaisesRegex(Exception, "completedStage binding is mismatched"):
            self.run_cli("checkpoint-denied.json", command)
        self.assertEqual(
            "implement",
            cli.SupervisorEngine(manager=self.manager).store.load_state()["currentWork"]["stage"],
        )

    def test_public_reservation_control_release_and_post_release_cleanup(self) -> None:
        git(self.repository, "add", "docs-ai")
        git(self.repository, "commit", "-m", "track workflow descriptor")
        engine = cli.SupervisorEngine(manager=self.manager)
        gates = worktrees.WorktreeManager(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.root / "state",
            store=engine.store,
        )
        gate_operation_id = str(uuid.uuid4())
        head = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        gate = gates.create_gate_worktree(gate_operation_id, exact_sha=head)
        state = engine.store.load_state()
        gates.set_gate_evidence(
            gate_operation_id,
            expected_state_revision=state["revision"],
            operation_status="resolved",
            attestation_status="complete",
        )

        reserve = {
            **self.base_request("Reserve"),
            "workflowId": self.descriptor["workflowId"],
            "issueId": None,
            "worktreePath": os.fspath(self.repository),
            "policy": "semi-autonomous",
            "ownerId": "interactive-owner",
            "runId": None,
            "autonomousCapabilityRef": None,
            "expectedStateRevision": engine.store.load_state()["revision"],
            "expectedReservationsRevision": engine.store.load_reservations()["revision"],
        }
        record = self.run_cli("lifecycle-reserve.json", reserve)
        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        renew = {
            **self.base_request("RenewReservation"),
            "reservationId": record["reservationId"],
            "ownerId": "interactive-owner",
            "runId": None,
            "reservationControlRef": record["releaseAuthorizationRef"],
            "autonomousCapabilityRef": None,
            "expectedReservationRevision": record["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }
        renewed = self.run_cli("renew-reservation.json", renew)

        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        stale_authorize = {
            **self.base_request("AuthorizeMutation"),
            "reservationId": record["reservationId"],
            "workflowId": self.descriptor["workflowId"],
            "targetOperationId": str(uuid.uuid4()),
            "operationScope": ["README.md"],
            "reservationControlRef": record["releaseAuthorizationRef"],
            "autonomousCapabilityRef": None,
            "expectedReservationRevision": renewed["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }
        with self.assertRaisesRegex(Exception, "control authorization"):
            self.run_cli("authorize-stale-control.json", stale_authorize)

        authorize = dict(
            stale_authorize,
            requestId=str(uuid.uuid4()),
            reservationControlRef=renewed["releaseAuthorizationRef"],
        )
        mutation = self.run_cli("authorize-mutation.json", authorize)
        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        release = {
            **self.base_request("Release"),
            "reservationId": record["reservationId"],
            "reservationControlRef": mutation["controlAuthorizationRef"],
            "autonomousCapabilityRef": None,
            "trustedObservationRef": None,
            "expectedReservationRevision": mutation["reservationRevision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }
        released = self.run_cli("release-reservation.json", release)
        cleanup_ref = released["cleanupAuthorizationRefs"][gate_operation_id]
        cleanup_authorization = self.manager.state_paths.read_json(cleanup_ref)
        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        cleanup = {
            **self.base_request(
                "Cleanup", request_id=cleanup_authorization["authorizationId"]
            ),
            "releasedReservationId": record["reservationId"],
            "gateOperationId": gate_operation_id,
            "cleanupAuthorizationRef": cleanup_ref,
            "expectedReleasedReservationRevision": released[
                "reservationRevision"
            ],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }
        cleaned = self.run_cli("cleanup.json", cleanup)
        self.assertEqual("clean", cleaned["status"])
        self.assertEqual([gate["path"]], cleaned["removed"])
        self.assertFalse(Path(gate["path"]).exists())

    def test_public_handoff_requires_exact_revisions_and_transfers(self) -> None:
        destination = self.linked_worktree()
        reserve = {
            **self.base_request("Reserve"),
            "workflowId": self.descriptor["workflowId"],
            "issueId": None,
            "worktreePath": os.fspath(self.repository),
            "policy": "semi-autonomous",
            "ownerId": "interactive-owner",
            "runId": None,
            "autonomousCapabilityRef": None,
            "expectedStateRevision": self.store.load_state()["revision"],
            "expectedReservationsRevision": self.store.load_reservations()["revision"],
        }
        record = self.run_cli("handoff-reserve.json", reserve)
        (self.repository / "README.md").write_text(
            "handoff change\n", encoding="utf-8"
        )
        state = self.store.load_state()
        reservations = self.store.load_reservations()
        handoff = {
            **self.base_request("Handoff"),
            "workflowId": self.descriptor["workflowId"],
            "sourcePath": os.fspath(self.repository),
            "destinationPath": os.fspath(destination),
            "expectedPaths": ["README.md"],
            "reservationId": record["reservationId"],
            "reservationControlRef": record["releaseAuthorizationRef"],
            "autonomousCapabilityRef": None,
            "expectedReservationRevision": record["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
            "runId": None,
        }
        stale = dict(
            handoff,
            requestId=str(uuid.uuid4()),
            expectedReservationsRevision=reservations["revision"] - 1,
        )
        with self.assertRaisesRegex(Exception, "revision"):
            self.run_cli("handoff-stale.json", stale)

        result = self.run_cli("handoff.json", handoff)
        self.assertEqual("transferred", result["status"])
        self.assertEqual(
            "handoff change\n",
            (destination / "README.md").read_text(encoding="utf-8"),
        )

    def test_public_autonomous_handoff_transfers_complete_issue_authority(self) -> None:
        controller = self.repository
        issue_record = self.use_authoritative_issue_worktree()
        source = Path(issue_record["path"])
        self.repository = controller
        engine = cli.SupervisorEngine(manager=self.manager)

        acquire = {
            **self.base_request("AcquireLease"),
            "ownerId": "autonomous-owner",
            "expectedStateRevision": engine.store.load_state()["revision"],
        }
        lease = self.run_cli("autonomous-handoff-acquire.json", acquire)
        prepare = {
            **self.base_request("PrepareIteration"),
            "runId": acquire["requestId"],
            "issueId": "SAAS-46",
            "workflowId": self.descriptor["workflowId"],
            "worktreePath": os.fspath(source),
            "leaseCapabilityRef": lease["capabilityRef"],
            "expectedStateRevision": engine.store.load_state()["revision"],
            "expectedStage": "implement",
        }
        prepared = self.run_cli("autonomous-handoff-prepare.json", prepare)
        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        reserve = {
            **self.base_request("Reserve"),
            "workflowId": self.descriptor["workflowId"],
            "issueId": "SAAS-46",
            "worktreePath": os.fspath(source),
            "policy": "autonomous",
            "ownerId": "autonomous-owner",
            "runId": acquire["requestId"],
            "autonomousCapabilityRef": prepared["capabilityRef"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }
        reserved = self.run_cli("autonomous-handoff-reserve.json", reserve)

        destination = self.manager.home.repository / "worktrees" / "SAAS-46-transfer"
        git(
            controller,
            "worktree",
            "add",
            "-b",
            "delivery/saas-46-transfer",
            destination,
            "HEAD",
        )
        (source / "README.md").write_text("autonomous transfer\n", encoding="utf-8")
        artifact_relative = Path(self.descriptor["artifactPath"]).relative_to(source)
        expected_paths = [
            "README.md",
            (artifact_relative / "fixture.md").as_posix(),
        ]
        with self.assertRaisesRegex(Exception, "exact internal Handoff authorization"):
            self.manager.workflow_managed_handoff(
                workflow_id=self.descriptor["workflowId"],
                destination_root=destination,
                expected_paths=expected_paths,
                _editing_source_root=source,
            )
        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        handoff = {
            **self.base_request("Handoff"),
            "workflowId": self.descriptor["workflowId"],
            "sourcePath": os.fspath(source),
            "destinationPath": os.fspath(destination),
            "expectedPaths": expected_paths,
            "reservationId": reserved["reservationId"],
            "reservationControlRef": reserved["releaseAuthorizationRef"],
            "autonomousCapabilityRef": prepared["capabilityRef"],
            "expectedReservationRevision": reserved["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
            "runId": acquire["requestId"],
        }
        tampered_source = dict(
            handoff,
            requestId=str(uuid.uuid4()),
            sourcePath=os.fspath(controller),
        )
        with self.assertRaisesRegex(Exception, "source|path|binding"):
            self.run_cli("autonomous-handoff-tampered-source.json", tampered_source)

        ordinary_destination = self.root / "ordinary-autonomous-destination"
        git(
            controller,
            "worktree",
            "add",
            "-b",
            "ordinary-autonomous-destination",
            ordinary_destination,
            "HEAD",
        )
        uncontained = dict(
            handoff,
            requestId=str(uuid.uuid4()),
            destinationPath=os.fspath(ordinary_destination),
        )
        with self.assertRaisesRegex(Exception, "direct contained|escapes"):
            self.run_cli("autonomous-handoff-uncontained.json", uncontained)

        transferred = self.run_cli("autonomous-handoff.json", handoff)
        self.assertEqual("transferred", transferred["status"])

        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        current = reservations["reservations"][reserved["reservationId"]]
        mapping = state["issueWorktrees"]["SAAS-46"]
        allocation = state["worktreeAllocations"]["issue:SAAS-46"]
        self.assertEqual(os.path.normcase(os.path.realpath(destination)).replace("\\", "/"), mapping["worktreePath"])
        self.assertEqual(handoff["requestId"], mapping["handoffOperationId"])
        self.assertEqual("transferred", allocation["status"])
        self.assertEqual(mapping["worktreePath"], allocation["worktreePath"])
        transferred_worktrees = worktrees.WorktreeManager(
            controller,
            repository_key="test-repository",
            state_home_override=self.root / "state",
            store=engine.store,
        )
        validated_mapping = transferred_worktrees.ensure_issue_worktree(
            "SAAS-46", base_branch="main"
        )
        self.assertEqual(mapping["worktreePath"], validated_mapping["path"])
        self.assertEqual(
            handoff["requestId"], validated_mapping["handoffOperationId"]
        )

        with self.assertRaisesRegex(Exception, "control authorization"):
            engine.reservations.renew(
                reservation_id=reserved["reservationId"],
                owner_id="autonomous-owner",
                expected_record_revision=current["revision"],
                expected_state_revision=state["revision"],
                expected_reservations_revision=reservations["revision"],
                control_authorization_ref=reserved["releaseAuthorizationRef"],
                capability_ref=prepared["capabilityRef"],
            )
        with self.assertRaises(Exception):
            self.manager.workflow_managed_handoff(
                workflow_id=self.descriptor["workflowId"],
                destination_root=source,
                expected_paths=expected_paths,
            )

        renew = {
            **self.base_request("RenewReservation"),
            "reservationId": reserved["reservationId"],
            "ownerId": "autonomous-owner",
            "runId": acquire["requestId"],
            "reservationControlRef": current["releaseAuthorizationRef"],
            "autonomousCapabilityRef": prepared["capabilityRef"],
            "expectedReservationRevision": current["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }
        renewed = self.run_cli("autonomous-handoff-renew.json", renew)
        state = engine.store.load_state()
        reservations = engine.store.load_reservations()
        authorize = {
            **self.base_request("AuthorizeMutation"),
            "reservationId": reserved["reservationId"],
            "workflowId": self.descriptor["workflowId"],
            "targetOperationId": str(uuid.uuid4()),
            "operationScope": ["README.md"],
            "reservationControlRef": renewed["releaseAuthorizationRef"],
            "autonomousCapabilityRef": prepared["capabilityRef"],
            "expectedReservationRevision": renewed["revision"],
            "expectedStateRevision": state["revision"],
            "expectedReservationsRevision": reservations["revision"],
        }
        mutation = self.run_cli("autonomous-handoff-authorize.json", authorize)
        self.assertEqual("active", mutation["status"])

        def worker_result(path: Path, fingerprint: str, transition_id: str) -> Path:
            result_path = path / f"worker-{transition_id}.json"
            head = git(path, "rev-parse", "HEAD").stdout.strip()
            result = {
                "schemaVersion": "1.0",
                "preparedIterationId": prepared["preparedIterationId"],
                "runId": acquire["requestId"],
                "workflowId": self.descriptor["workflowId"],
                "issueId": "SAAS-46",
                "transitionId": transition_id,
                "outcome": "advanced",
                "completedStage": "implement",
                "proposedNextStage": "review",
                "artifactManifest": [],
                "changedPaths": [],
                "summary": "Transferred worktree evidence is ready.",
                "proposedExternalTransitions": [],
                "pause": None,
                "observed": {
                    "repositoryId": self.manager.identity.repository_id,
                    "physicalWorktreeFingerprint": fingerprint,
                    "headSha": head,
                },
            }
            result_path.write_text(json.dumps(result), encoding="utf-8")
            changed = set(
                item
                for item in git(path, "diff", "--name-only", "HEAD", "--").stdout.splitlines()
                if item
            )
            changed.update(
                item
                for item in git(path, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
                if item
            )
            result["changedPaths"] = sorted(changed)
            result_path.write_text(json.dumps(result), encoding="utf-8")
            return result_path

        stale_transition = str(uuid.uuid4())
        stale_worker = worker_result(
            source, issue_record["physicalWorktreeFingerprint"], stale_transition
        )
        prepared_ref = (
            self.manager.home.repository
            / "runs"
            / acquire["requestId"]
            / f"{prepared['preparedIterationId']}.prepared-iteration.json"
        )
        stale_checkpoint = {
            **self.base_request("ApplyCheckpoint"),
            "runId": acquire["requestId"],
            "preparedIterationRef": os.fspath(prepared_ref),
            "workerResultPath": os.fspath(stale_worker),
            "transitionId": stale_transition,
            "expectedStateRevision": engine.store.load_state()["revision"],
            "expectedStage": "implement",
        }
        with self.assertRaisesRegex(Exception, "worktree|fingerprint"):
            self.run_cli("autonomous-handoff-stale-checkpoint.json", stale_checkpoint)

        destination_identity = package.base_runtime.load_base_runtime().observe_repository_identity(
            destination
        )
        transition_id = str(uuid.uuid4())
        worker = worker_result(
            destination,
            destination_identity.physical_worktree_fingerprint,
            transition_id,
        )
        checkpoint = dict(
            stale_checkpoint,
            requestId=str(uuid.uuid4()),
            workerResultPath=os.fspath(worker),
            transitionId=transition_id,
        )
        applied = self.run_cli("autonomous-handoff-checkpoint.json", checkpoint)
        self.assertEqual("applied", applied["status"])

    def test_public_recover_reconciles_pending_journal(self) -> None:
        engine = cli.SupervisorEngine(manager=self.manager)
        pending_id = str(uuid.uuid4())
        engine.operations.begin(
            operation_id=pending_id,
            operation="Status",
            request={"probe": "interrupted-before-mutation"},
        )
        request = {
            "schemaVersion": "1.0",
            "operation": "Recover",
            "requestId": str(uuid.uuid4()),
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.manager.home.repository),
            "requestedAt": "2026-07-18T12:00:00Z",
            "operationId": None,
            "expectedStateRevision": 1,
        }
        result = self.run_cli("recover-request.json", request)
        self.assertIn(pending_id, result["failedOperations"])
        self.assertEqual([], result["pendingOperations"])

    def test_request_outside_repository_and_state_home_is_rejected(self) -> None:
        request_path = self.root / "outside.json"
        request_path.write_text(json.dumps(self.status_request()), encoding="utf-8")
        with self.assertRaisesRegex(Exception, "contained"):
            cli.run_request(request_path)
