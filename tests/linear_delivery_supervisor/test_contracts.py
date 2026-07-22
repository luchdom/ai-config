from __future__ import annotations

import copy
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from tests.linear_delivery_supervisor import load_supervisor_package


runtime_package = load_supervisor_package()
contracts = runtime_package.contracts


def identifier() -> str:
    return str(uuid.uuid4())


class SupervisorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="supervisor-contracts-")
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name).resolve()
        self.repository = root / "repository"
        self.state_home = root / "state" / "repo-aaaaaaaaaaaaaaaaaaaaaaaa"
        self.repository.mkdir()
        self.state_home.mkdir(parents=True)
        self.now = "2026-07-18T12:00:00Z"
        self.later = "2026-07-18T12:05:00Z"
        self.workflow_id = identifier()
        self.run_id = identifier()
        self.issue_id = "SAAS-46"
        self.repository_id = "repo-" + "a" * 24
        self.fingerprint = "sha256:" + "b" * 64
        self.hash = "sha256:" + "c" * 64

    def common_command(self, operation: str) -> dict:
        return {
            "schemaVersion": "1.0",
            "operation": operation,
            "requestId": identifier(),
            "repositoryKey": "ai-config",
            "repositoryRoot": str(self.repository),
            "stateHome": str(self.state_home),
            "requestedAt": self.now,
        }

    def command_variants(self) -> dict[str, dict]:
        state_file = self.state_home / "runs" / self.run_id / "prepared-iteration.json"
        lease_capability_ref = self.state_home / "runs" / self.run_id / "lease-capability.json"
        reservation_control_ref = self.state_home / "reservation-authorizations" / "control.json"
        worker_result = self.repository / "docs-ai" / "worker-result.json"
        variants = {
            "Preflight": {"configPath": str(self.repository / "delivery-config.json")},
            "AcquireLease": {"ownerId": "scheduled-owner", "expectedStateRevision": 1},
            "RenewLease": {"runId": self.run_id, "ownerId": "scheduled-owner", "leaseCapabilityRef": str(lease_capability_ref), "expectedStateRevision": 1},
            "PrepareIteration": {"runId": self.run_id, "issueId": self.issue_id, "workflowId": self.workflow_id, "worktreePath": str(self.repository), "leaseCapabilityRef": str(lease_capability_ref), "expectedStateRevision": 1, "expectedStage": "audit"},
            "ApplyCheckpoint": {"runId": self.run_id, "preparedIterationRef": str(state_file), "workerResultPath": str(worker_result), "transitionId": identifier(), "expectedStateRevision": 1, "expectedStage": "implement"},
            "Status": {"workflowId": self.workflow_id},
            "Reserve": {"workflowId": self.workflow_id, "issueId": self.issue_id, "worktreePath": str(self.repository), "policy": "semi-autonomous", "ownerId": "interactive-owner", "runId": None, "autonomousCapabilityRef": None, "expectedStateRevision": 1, "expectedReservationsRevision": 1},
            "RenewReservation": {"reservationId": identifier(), "ownerId": "interactive-owner", "runId": None, "reservationControlRef": str(reservation_control_ref), "autonomousCapabilityRef": None, "expectedReservationRevision": 1, "expectedStateRevision": 1, "expectedReservationsRevision": 1},
            "AuthorizeMutation": {"reservationId": identifier(), "workflowId": self.workflow_id, "targetOperationId": identifier(), "operationScope": ["docs-ai/result.md"], "reservationControlRef": str(reservation_control_ref), "autonomousCapabilityRef": None, "expectedReservationRevision": 1, "expectedStateRevision": 1, "expectedReservationsRevision": 1},
            "Release": {"reservationId": identifier(), "reservationControlRef": str(reservation_control_ref), "autonomousCapabilityRef": None, "trustedObservationRef": None, "expectedReservationRevision": 1, "expectedStateRevision": 1, "expectedReservationsRevision": 1},
            "Recover": {"operationId": None, "expectedStateRevision": 1},
            "Cleanup": {"releasedReservationId": identifier(), "gateOperationId": identifier(), "cleanupAuthorizationRef": str(self.state_home / "cleanup-authorizations" / "cleanup.json"), "expectedReleasedReservationRevision": 1, "expectedStateRevision": 1, "expectedReservationsRevision": 1},
            "Handoff": {"workflowId": self.workflow_id, "sourcePath": str(self.repository), "destinationPath": str(self.state_home / "worktrees" / self.issue_id), "expectedPaths": ["src/feature.py"], "reservationId": identifier(), "reservationControlRef": str(reservation_control_ref), "autonomousCapabilityRef": None, "expectedReservationRevision": 1, "expectedStateRevision": 1, "expectedReservationsRevision": 1, "runId": None},
            "ReleaseLease": {"runId": self.run_id, "ownerId": "scheduled-owner", "leaseCapabilityRef": str(lease_capability_ref), "expectedStateRevision": 1},
        }
        return {name: self.common_command(name) | fields for name, fields in variants.items()}

    def valid_contracts(self) -> dict[str, dict]:
        authorization = {
            "schemaVersion": "1.0", "authorizationId": identifier(),
            "authorizationRef": str(self.state_home / "authorizations" / "release.json"),
            "operationId": identifier(), "reservationId": identifier(), "workflowId": self.workflow_id,
            "issueId": self.issue_id, "runId": None, "repositoryId": self.repository_id,
            "repositoryKey": "ai-config", "stateHome": str(self.state_home),
            "physicalWorktreeFingerprint": self.fingerprint, "scope": "ReservationControl",
            "stateRevision": 1, "reservationRevision": 1, "nonceHash": self.hash,
            "createdAt": self.now, "expiresAt": self.later, "consumedAt": None, "status": "issued",
        }
        return {
            "project-config": {
                "schemaVersion": "1.0", "engineVersion": "1.0",
                "baseVersions": {"basePackage": "1.0", "identity": "1.0", "stateHome": "2.0", "registry": "1.0", "workDescriptor": "2.0"},
                "repositoryKey": "ai-config", "baseBranch": "main",
                "aggregateCommand": [str(Path(sys.executable).resolve()), "scripts/validate.py"],
                "writableRoots": [str(self.repository)],
                "commandPolicy": {
                    "pythonExecutable": str(Path(sys.executable).resolve()), "powerShellExecutable": str(self.repository / "tools" / "pwsh.exe"),
                    "gitExecutable": str(self.repository / "tools" / "git.exe"), "ghExecutable": str(self.repository / "tools" / "gh.exe"),
                    "workerWrapper": str(self.repository / "scripts" / "agent-worker-engine.ps1"),
                    "allowedGitArgv": [["status", "--porcelain=v1"]], "allowedGhArgv": [["auth", "status"]],
                },
                "scheduledPolicy": {"sandboxMode": "workspace-write", "networkAccess": True, "approvalPolicy": "never", "profileComposition": "none"},
                "networkPolicy": {"allowedHosts": ["api.linear.app"], "loopbackHost": "127.0.0.1", "loopbackPorts": [4318]},
                "environmentPolicy": {"requiredVariableNames": ["LINEAR_API_KEY"], "allowedInheritedVariableNames": ["PATH"], "forbiddenSecretNamePatterns": ["TOKEN", "PASSWORD"]},
                "probeAdapter": {"adapterId": "luchdom.supervisor.read-only", "adapterVersion": "1.0", "executable": str(Path(sys.executable).resolve()), "fixedArgv": ["probe.py"]},
                "clockPolicy": {"leaseSeconds": 300, "reservationSeconds": 1800, "maxForwardStepSeconds": 60},
            },
            "prepared-iteration": {
                "schemaVersion": "1.0", "preparedIterationId": identifier(), "issueId": self.issue_id,
                "workflowId": self.workflow_id, "runId": self.run_id, "repositoryId": self.repository_id,
                "repositoryKey": "ai-config", "stateHome": str(self.state_home),
                "physicalWorktreeFingerprint": self.fingerprint, "worktreePath": str(self.repository),
                "stateRevision": 1, "stage": "implement", "expiresAt": self.later,
                "capabilityRef": str(self.state_home / "runs" / self.run_id / "capability.bin"), "capabilityHash": self.hash,
            },
            "checkpoint": {
                "schemaVersion": "1.0", "checkpointId": identifier(), "preparedIterationId": identifier(),
                "runId": self.run_id, "workflowId": self.workflow_id, "issueId": self.issue_id,
                "transitionId": identifier(), "expectedStateRevision": 1, "expectedPreviousStage": "implement",
                "nextStage": "review", "workerResultPath": str(self.repository / "docs-ai" / "result.json"),
                "artifactManifest": ["docs-ai/002/implementation.md"], "changedPaths": ["src/feature.py"],
                "observed": {"repositoryId": self.repository_id, "physicalWorktreeFingerprint": self.fingerprint, "headSha": "d" * 40},
                "createdAt": self.now,
            },
            "supervisor-state": {
                "schemaVersion": "1.0", "revision": 1,
                "repository": {"repositoryId": self.repository_id, "repositoryKey": "ai-config", "normalizedCommonDir": str(self.repository / ".git"), "basePackageVersion": "1.0", "identityVersion": "1.0", "stateHomeVersion": "2.0", "registryVersion": "1.0", "workDescriptorVersion": "2.0"},
                "lease": None, "capabilities": {}, "worktreeAllocations": {}, "issueWorktrees": {}, "gateWorktrees": {}, "checkpoints": {}, "currentWork": None,
                "recovery": {"status": "clean", "reason": None, "updatedAtNs": 1}, "handoffPending": None,
                "clockEvidence": {"lastObservedNowNs": 1, "maxForwardStepNs": 60000000000, "status": "stable"},
            },
            "editing-reservation": {"schemaVersion": "1.0", "revision": 1, "reservations": {}, "consumedObservationIds": [], "consumedAuthorizationIds": []},
            "operation-journal": {"schemaVersion": "1.0", "operationId": identifier(), "idempotencyKey": "request-1", "operation": "Status", "requestHash": self.hash, "status": "completed", "attemptCount": 1, "beforeStateHash": self.hash, "afterStateHash": self.hash, "resultRef": str(self.state_home / "operations" / "result.json"), "errorCode": None, "createdAt": self.now, "updatedAt": self.later},
            "worker-result": {"schemaVersion": "1.0", "preparedIterationId": identifier(), "runId": self.run_id, "workflowId": self.workflow_id, "issueId": self.issue_id, "transitionId": identifier(), "outcome": "advanced", "completedStage": "implement", "proposedNextStage": "review", "artifactManifest": ["docs-ai/002/implementation.md"], "changedPaths": ["src/feature.py"], "summary": "Implementation completed", "proposedExternalTransitions": [], "pause": None, "observed": {"repositoryId": self.repository_id, "physicalWorktreeFingerprint": self.fingerprint, "headSha": "d" * 40}},
            "engine-command": self.command_variants()["Status"],
            "release-authorization": authorization,
            "handoff-authorization": {
                "schemaVersion": "1.0", "revision": 1, "operationId": identifier(),
                "workflowId": self.workflow_id, "repositoryKey": "ai-config",
                "sourceFingerprint": self.fingerprint, "destinationFingerprint": "sha256:" + "e" * 64,
                "expectedPathDigest": self.hash, "requestHash": self.hash,
                "reservationId": identifier(), "reservationRevision": 1,
                "nonceSha256": self.hash, "status": "prepared",
            },
            "trusted-observation": {
                "schemaVersion": "1.0", "observationId": identifier(), "observationRef": str(self.state_home / "observations" / "one.json"),
                "adapterId": "fixture-github", "adapterVersion": "1.0", "adapterKind": "fixture", "operationId": identifier(),
                "repositoryId": self.repository_id, "repositoryKey": "ai-config", "stateHome": str(self.state_home),
                "normalizedCommonDir": str(self.repository / ".git"), "branch": "main", "headSha": "d" * 40,
                "pullRequest": {"provider": "github", "id": "46", "state": "merged", "headSha": "d" * 40},
                "observedAt": self.now, "expiresAt": self.later, "journalHash": self.hash, "attestationHash": self.hash,
                "consumedAt": None, "status": "issued",
            },
            "tracking-config": {
                "schemaVersion": "1.0", "controlPlaneVersion": "1.0",
                "supervisorVersion": "1.0", "repositoryKey": "ai-config",
                "workspace": {"id": "workspace-1", "name": "Luchdom"},
                "team": {"id": "team-1", "key": "SAAS"},
                "project": {"id": "project-1", "name": "SaaS"},
                "owner": {"id": "owner-1", "name": "Lucas"},
                "states": {
                    name: {"id": f"state-{name}", "name": display}
                    for name, display in (
                        ("backlog", "Backlog"), ("todo", "Todo"),
                        ("inProgress", "In Progress"), ("inReview", "In Review"),
                        ("done", "Done"),
                    )
                },
                "labels": {
                    name: {"id": f"label-{name}", "name": display}
                    for name, display in (
                        ("autonomous", "autonomous"),
                        ("needsRefinement", "needs-refinement"),
                        ("needsHuman", "needs-human"),
                        ("externalIntegration", "external-integration"),
                        ("stop", "stop"),
                    )
                },
                "linear": {
                    "endpoint": "https://api.linear.app/graphql",
                    "allowedHost": "api.linear.app",
                    "apiKeyEnvironmentVariable": "LINEAR_API_KEY",
                    "timeoutSeconds": 15, "maxAttempts": 3,
                },
                "ntfy": {
                    "enabled": False,
                    "endpointEnvironmentVariable": "NTFY_URL",
                    "topicEnvironmentVariable": "NTFY_TOPIC",
                    "tokenEnvironmentVariable": "NTFY_TOKEN",
                    "allowedHosts": ["ntfy.sh"], "maxAttempts": 3,
                },
            },
            "control-plane-state": {
                "schemaVersion": "1.0", "revision": 0, "decisions": [],
                "publicationRequests": [], "followUps": [],
                "attentionEvents": [], "notifications": [], "selectionClaims": [],
            },
            "migration-report": {
                "schemaVersion": "1.0", "generatedAt": self.now,
                "mutationFree": True, "issues": [],
            },
        }

    def test_runtime_parity_inventory_and_every_valid_contract(self) -> None:
        contracts.assert_runtime_parity()
        fixtures = self.valid_contracts()
        self.assertEqual(set(fixtures), set(contracts.SCHEMA_FILENAMES))
        for name, value in fixtures.items():
            with self.subTest(contract=name):
                self.assertEqual(value, contracts.validate_contract(name, value))

    def test_engine_command_union_accepts_exactly_all_fourteen_operations(self) -> None:
        variants = self.command_variants()
        self.assertEqual(tuple(variants), contracts.OPERATION_NAMES)
        for operation, value in variants.items():
            with self.subTest(operation=operation):
                self.assertEqual(operation, contracts.validate_engine_command(value)["operation"])

    def test_local_reservation_and_release_allow_null_issue(self) -> None:
        fixtures = self.valid_contracts()
        reserve = copy.deepcopy(self.command_variants()["Reserve"])
        reserve["issueId"] = None
        contracts.validate_engine_command(reserve)

        release = copy.deepcopy(fixtures["release-authorization"])
        release["issueId"] = None
        contracts.validate_contract("release-authorization", release)

        reservation_id = identifier()
        reservation = {
            "reservationId": reservation_id, "workflowId": self.workflow_id, "issueId": None,
            "repositoryId": self.repository_id, "repositoryKey": "ai-config",
            "physicalWorktreeFingerprint": self.fingerprint, "worktreePath": str(self.repository),
            "policy": "manual", "ownerId": "interactive-owner", "runId": None,
            "status": "live", "revision": 1, "heartbeatNs": 1, "expiresAtNs": 2,
            "protectedWork": {
                "dirty": False, "branch": "main", "headSha": "d" * 40,
                "unpushed": False, "unmerged": False, "prOpen": False,
                "prId": None, "prState": "not-applicable", "accessible": True,
                "ambiguous": False, "planningOnly": True,
            },
            "releaseAuthorizationRef": None, "cleanupAuthorizationRefs": {},
            "pendingHandoffOperationId": None,
        }
        document = {
            "schemaVersion": "1.0", "revision": 1,
            "reservations": {reservation_id: reservation},
            "consumedObservationIds": [], "consumedAuthorizationIds": [],
        }
        contracts.validate_contract("editing-reservation", document)

    def test_engine_command_rejects_unknown_raw_authority_output_and_escaped_paths(self) -> None:
        baseline = self.command_variants()["Preflight"]
        cases = []
        for key, value in (("unknown", True), ("capability", "raw-value"), ("outputPath", str(self.repository / "out.json"))):
            changed = copy.deepcopy(baseline)
            changed[key] = value
            cases.append(changed)
        escaped = copy.deepcopy(baseline)
        escaped["configPath"] = str(self.state_home / "config.json")
        cases.append(escaped)
        escaped_control = copy.deepcopy(self.command_variants()["RenewReservation"])
        escaped_control["reservationControlRef"] = str(self.repository / "control.json")
        cases.append(escaped_control)
        escaped_capability = copy.deepcopy(self.command_variants()["Reserve"])
        escaped_capability["policy"] = "autonomous"
        escaped_capability["runId"] = self.run_id
        escaped_capability["autonomousCapabilityRef"] = str(self.repository / "capability.json")
        cases.append(escaped_capability)
        escaped_cleanup = copy.deepcopy(self.command_variants()["Cleanup"])
        escaped_cleanup["cleanupAuthorizationRef"] = str(self.repository / "cleanup.json")
        cases.append(escaped_cleanup)
        for value in cases:
            with self.assertRaises(contracts.ContractValidationError):
                contracts.validate_engine_command(value)

    def test_engine_command_rejects_missing_authority_references(self) -> None:
        required_references = {
            "RenewLease": "leaseCapabilityRef",
            "PrepareIteration": "leaseCapabilityRef",
            "RenewReservation": "reservationControlRef",
            "AuthorizeMutation": "reservationControlRef",
            "Release": "reservationControlRef",
            "Handoff": "reservationControlRef",
            "ReleaseLease": "leaseCapabilityRef",
        }
        variants = self.command_variants()
        for operation, reference_name in required_references.items():
            with self.subTest(operation=operation, missing=reference_name):
                value = copy.deepcopy(variants[operation])
                value.pop(reference_name)
                with self.assertRaises(contracts.ContractValidationError):
                    contracts.validate_engine_command(value)

        stale_reserve = copy.deepcopy(variants["Reserve"])
        stale_reserve.pop("expectedReservationsRevision")
        with self.assertRaises(contracts.ContractValidationError):
            contracts.validate_engine_command(stale_reserve)

    def test_rejects_malformed_uuid_hash_path_timestamp_cross_field_and_secret(self) -> None:
        fixtures = self.valid_contracts()
        cases = []
        malformed_uuid = copy.deepcopy(fixtures["prepared-iteration"]); malformed_uuid["runId"] = "NOT-A-UUID"; cases.append(("prepared-iteration", malformed_uuid))
        malformed_hash = copy.deepcopy(fixtures["prepared-iteration"]); malformed_hash["capabilityHash"] = "sha256:1234"; cases.append(("prepared-iteration", malformed_hash))
        escaped_path = copy.deepcopy(fixtures["prepared-iteration"]); escaped_path["capabilityRef"] = str(self.state_home.parent / "escaped.bin"); cases.append(("prepared-iteration", escaped_path))
        malformed_time = copy.deepcopy(fixtures["trusted-observation"]); malformed_time["expiresAt"] = "2026-07-18 12:05"; cases.append(("trusted-observation", malformed_time))
        crossed = copy.deepcopy(fixtures["handoff-authorization"]); crossed["destinationFingerprint"] = crossed["sourceFingerprint"]; cases.append(("handoff-authorization", crossed))
        consumed = copy.deepcopy(fixtures["release-authorization"]); consumed["status"] = "consumed"; cases.append(("release-authorization", consumed))
        secret = copy.deepcopy(fixtures["worker-result"]); secret["summary"] = "Bearer abc.def"; cases.append(("worker-result", secret))
        for name, value in cases:
            with self.subTest(contract=name):
                with self.assertRaises(contracts.ContractValidationError):
                    contracts.validate_contract(name, value)


if __name__ == "__main__":
    unittest.main()
