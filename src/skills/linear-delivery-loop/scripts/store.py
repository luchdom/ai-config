"""Path-guarded, revisioned supervisor state and paired transactions."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .base_runtime import BaseRuntime, load_base_runtime
from .contracts import ContractValidationError, validate_contract


SUPERVISOR_STATE_VERSION = "1.0"
SUPERVISOR_TRANSACTION_VERSION = "1.0"
_SECRET_KEY = re.compile(
    r"(?:^|[_-])(token|secret|password|passwd|api[_-]?key|private[_-]?key|nonce)(?:$|[_-])",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?:lin_api_[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|sk-[A-Za-z0-9_-]{12,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----)",
)


class SupervisorStoreError(RuntimeError):
    """Persisted supervisor state is unsafe, inconsistent, or invalid."""


class SupervisorConflictError(SupervisorStoreError):
    """A compare-and-swap or authority conflict rejected a transition."""


class SupervisorRecoveryError(SupervisorStoreError):
    """Transaction evidence cannot prove a safe deterministic recovery."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def assert_public_data(value: Any, *, location: str = "value") -> None:
    """Reject obvious credentials before they reach durable/public documents."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SupervisorStoreError(f"{location} contains a non-string object key")
            if _SECRET_KEY.search(key):
                raise SupervisorStoreError(f"{location} contains a prohibited secret-like field")
            assert_public_data(child, location=f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            assert_public_data(child, location=f"{location}[{index}]")
        return
    if isinstance(value, str) and _SECRET_VALUE.search(value):
        raise SupervisorStoreError(f"{location} contains a prohibited secret-like value")


def _normalized_common_dir(manager: Any) -> str:
    return os.path.normcase(os.path.realpath(manager.identity.common_dir))


class SupervisorStore:
    """Authoritative state store built only from the canonical WorkflowManager."""

    TOPOLOGY_DIRECTORIES = (
        "supervisor-transactions",
        "operations",
        "runs",
        "final-attestations",
        "worktrees",
        "validation-worktrees",
        "reservation-authorizations",
        "mutation-authorizations",
        "handoff-authorizations",
    )

    def __init__(
        self,
        manager: Any,
        *,
        runtime: BaseRuntime | None = None,
        fault_injector: Callable[[str, str], None] | None = None,
        initialize: bool = True,
    ):
        self.runtime = runtime or load_base_runtime()
        if not isinstance(manager, self.runtime.WorkflowManager):
            raise SupervisorStoreError("SupervisorStore requires the canonical WorkflowManager")
        self.manager = manager
        self.guard = manager.state_paths
        self.root = self.guard.validate_root()
        self.fault_injector = fault_injector
        self.state_path = self.guard.leaf(self.root / "supervisor-state.json")
        self.reservations_path = self.guard.leaf(self.root / "reservations.json")
        self.transaction_dir = self.guard.directory(
            self.root / "supervisor-transactions", create=initialize
        )
        self.directories = {
            name: self.guard.directory(self.root / name, create=initialize)
            for name in self.TOPOLOGY_DIRECTORIES
        }
        if initialize:
            with self.manager.registry.mutex():
                self._ensure_documents_unlocked()
                self.recover_unlocked()
        else:
            self.guard.leaf(self.state_path, must_exist=True)
            self.guard.leaf(self.reservations_path, must_exist=True)

    def mutex(self):
        return self.manager.registry.mutex()

    def _ensure_documents_unlocked(self) -> None:
        if not self.state_path.exists():
            self.guard.write_json(self.state_path, self.empty_state())
        if not self.reservations_path.exists():
            self.guard.write_json(self.reservations_path, self.empty_reservations())
        self.load_pair_unlocked()

    def empty_state(self) -> dict[str, Any]:
        return {
            "schemaVersion": SUPERVISOR_STATE_VERSION,
            "revision": 1,
            "repository": {
                "repositoryId": self.manager.identity.repository_id,
                "repositoryKey": self.manager.repository_key,
                "normalizedCommonDir": _normalized_common_dir(self.manager),
                "basePackageVersion": self.runtime.package_version,
                "identityVersion": self.runtime.identity_version,
                "stateHomeVersion": self.runtime.state_home_version,
                "registryVersion": self.runtime.registry_version,
                "workDescriptorVersion": self.runtime.work_descriptor_version,
            },
            "lease": None,
            "capabilities": {},
            "worktreeAllocations": {},
            "issueWorktrees": {},
            "gateWorktrees": {},
            "checkpoints": {},
            "currentWork": None,
            "recovery": {"status": "clean", "reason": None, "updatedAtNs": 0},
            "handoffPending": None,
            "clockEvidence": {
                "lastObservedNowNs": 0,
                "maxForwardStepNs": 30 * 60 * 1_000_000_000,
                "status": "stable",
            },
        }

    def empty_reservations(self) -> dict[str, Any]:
        return {
            "schemaVersion": SUPERVISOR_STATE_VERSION,
            "revision": 1,
            "reservations": {},
            "consumedObservationIds": [],
            "consumedAuthorizationIds": [],
        }

    def load_state(self) -> dict[str, Any]:
        with self.mutex():
            state, _ = self.load_pair_unlocked()
            return copy.deepcopy(state)

    def load_reservations(self) -> dict[str, Any]:
        with self.mutex():
            _, reservations = self.load_pair_unlocked()
            return copy.deepcopy(reservations)

    def load_pair_unlocked(self) -> tuple[dict[str, Any], dict[str, Any]]:
        state = self.guard.read_json(self.state_path)
        reservations = self.guard.read_json(self.reservations_path)
        self._validate_state(state)
        self._validate_reservations(reservations)
        return state, reservations

    def commit_pair(
        self,
        *,
        expected_state_revision: int,
        expected_reservations_revision: int,
        mutate: Callable[[dict[str, Any], dict[str, Any]], None],
        operation: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        with self.mutex():
            before_state, before_reservations = self.load_pair_unlocked()
            if before_state["revision"] != expected_state_revision:
                raise SupervisorConflictError("Supervisor state revision is stale")
            if before_reservations["revision"] != expected_reservations_revision:
                raise SupervisorConflictError("Reservation state revision is stale")
            after_state = copy.deepcopy(before_state)
            after_reservations = copy.deepcopy(before_reservations)
            mutate(after_state, after_reservations)
            self._advance_changed_revisions(
                before_state, after_state, before_reservations, after_reservations
            )
            return self.commit_pair_unlocked(
                before_state=before_state,
                after_state=after_state,
                before_reservations=before_reservations,
                after_reservations=after_reservations,
                operation=operation,
            )

    def commit_pair_unlocked(
        self,
        *,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        before_reservations: dict[str, Any],
        after_reservations: dict[str, Any],
        operation: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        current_state, current_reservations = self.load_pair_unlocked()
        if current_state != before_state or current_reservations != before_reservations:
            raise SupervisorConflictError("Supervisor paired transaction observed stale input")
        self._validate_transition(before_state, after_state, "supervisor state")
        self._validate_transition(
            before_reservations, after_reservations, "reservation state"
        )
        assert_public_data(after_state, location="supervisor state")
        assert_public_data(after_reservations, location="reservation state")
        self._validate_state(after_state)
        self._validate_reservations(after_reservations)

        transaction_id = str(uuid.uuid4())
        transaction_path = self.guard.leaf(
            self.transaction_dir / f"{transaction_id}.json"
        )
        transaction = {
            "schemaVersion": SUPERVISOR_TRANSACTION_VERSION,
            "transactionId": transaction_id,
            "operation": operation,
            "statePath": os.fspath(self.state_path),
            "reservationsPath": os.fspath(self.reservations_path),
            "beforeState": before_state,
            "afterState": after_state,
            "beforeReservations": before_reservations,
            "afterReservations": after_reservations,
            "beforeStateSha256": sha256_json(before_state),
            "afterStateSha256": sha256_json(after_state),
            "beforeReservationsSha256": sha256_json(before_reservations),
            "afterReservationsSha256": sha256_json(after_reservations),
            "decision": "commit-after",
        }
        self._fault("before-journal", transaction_id)
        self.guard.write_json(transaction_path, transaction)
        self._fault("after-journal", transaction_id)
        if before_state != after_state:
            self.guard.write_json(
                self.state_path,
                after_state,
                expected_revision=before_state["revision"],
            )
        self._fault("after-first-write", transaction_id)
        if before_reservations != after_reservations:
            self.guard.write_json(
                self.reservations_path,
                after_reservations,
                expected_revision=before_reservations["revision"],
            )
        self._fault("after-second-write", transaction_id)
        observed_state, observed_reservations = self.load_pair_unlocked()
        if observed_state != after_state or observed_reservations != after_reservations:
            raise SupervisorRecoveryError("Supervisor paired transaction readback mismatch")
        self._fault("before-journal-completion", transaction_id)
        self.guard.unlink(transaction_path)
        return copy.deepcopy(after_state), copy.deepcopy(after_reservations)

    def recover(self) -> list[str]:
        with self.mutex():
            return self.recover_unlocked()

    def recover_unlocked(self) -> list[str]:
        recovered: list[str] = []
        for transaction_path in self.guard.glob_files(self.transaction_dir, "*.json"):
            transaction = self.guard.read_json(transaction_path)
            self._validate_transaction(transaction, transaction_path)
            current_state, current_reservations = self.load_pair_unlocked()
            before_state = transaction["beforeState"]
            after_state = transaction["afterState"]
            before_reservations = transaction["beforeReservations"]
            after_reservations = transaction["afterReservations"]
            state_side = self._side(current_state, before_state, after_state)
            reservations_side = self._side(
                current_reservations, before_reservations, after_reservations
            )
            if state_side == "unknown" or reservations_side == "unknown":
                raise SupervisorRecoveryError(
                    "Supervisor transaction evidence is ambiguous or tampered"
                )
            if state_side == "before" and reservations_side == "before":
                # The durable commit decision exists, so complete the exact after pair.
                if before_state != after_state:
                    self.guard.write_json(
                        self.state_path,
                        after_state,
                        expected_revision=before_state["revision"],
                    )
                if before_reservations != after_reservations:
                    self.guard.write_json(
                        self.reservations_path,
                        after_reservations,
                        expected_revision=before_reservations["revision"],
                    )
            elif state_side == "before" and before_state != after_state:
                self.guard.write_json(
                    self.state_path,
                    after_state,
                    expected_revision=before_state["revision"],
                )
            elif reservations_side == "before" and before_reservations != after_reservations:
                self.guard.write_json(
                    self.reservations_path,
                    after_reservations,
                    expected_revision=before_reservations["revision"],
                )
            observed = self.load_pair_unlocked()
            if observed != (after_state, after_reservations):
                raise SupervisorRecoveryError(
                    "Supervisor transaction could not recover its exact after pair"
                )
            self.guard.unlink(transaction_path)
            recovered.append(transaction["transactionId"])
        return recovered

    @staticmethod
    def _advance_changed_revisions(
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        before_reservations: dict[str, Any],
        after_reservations: dict[str, Any],
    ) -> None:
        if {**before_state, "revision": 0} != {**after_state, "revision": 0}:
            after_state["revision"] = before_state["revision"] + 1
        else:
            after_state["revision"] = before_state["revision"]
        if {**before_reservations, "revision": 0} != {
            **after_reservations,
            "revision": 0,
        }:
            after_reservations["revision"] = before_reservations["revision"] + 1
        else:
            after_reservations["revision"] = before_reservations["revision"]

    @staticmethod
    def _validate_transition(
        before: dict[str, Any], after: dict[str, Any], label: str
    ) -> None:
        expected = before["revision"] + (0 if before == after else 1)
        # Callers commonly mutate a deep copy before assigning its final revision.
        changed_ignoring_revision = {**before, "revision": 0} != {**after, "revision": 0}
        expected = before["revision"] + int(changed_ignoring_revision)
        if after.get("revision") != expected:
            raise SupervisorConflictError(f"{label} revision is not the next monotonic value")

    def _validate_state(self, state: dict[str, Any]) -> None:
        try:
            validate_contract("supervisor-state", state)
        except ContractValidationError as exc:
            raise SupervisorStoreError(
                "Supervisor state does not satisfy its complete persisted contract"
            ) from exc
        required = {
            "schemaVersion",
            "revision",
            "repository",
            "lease",
            "capabilities",
            "worktreeAllocations",
            "issueWorktrees",
            "gateWorktrees",
            "checkpoints",
            "currentWork",
            "recovery",
            "handoffPending",
            "clockEvidence",
        }
        if set(state) != required or state.get("schemaVersion") != SUPERVISOR_STATE_VERSION:
            raise SupervisorStoreError("Supervisor state has unknown, missing, or versioned fields")
        if not isinstance(state.get("revision"), int) or state["revision"] < 1:
            raise SupervisorStoreError("Supervisor state revision must be positive")
        expected_repository = self.empty_state()["repository"]
        if state.get("repository") != expected_repository:
            raise SupervisorStoreError("Supervisor state repository/base binding differs")
        for field in (
            "capabilities",
            "worktreeAllocations",
            "issueWorktrees",
            "gateWorktrees",
            "checkpoints",
        ):
            if not isinstance(state.get(field), dict):
                raise SupervisorStoreError(f"Supervisor state {field} must be an object")
        if any(
            allocation_id != record.get("allocationId")
            for allocation_id, record in state["worktreeAllocations"].items()
        ):
            raise SupervisorStoreError("Worktree allocation keys must equal allocation IDs")
        if any(
            issue_id != record.get("issueId")
            for issue_id, record in state["issueWorktrees"].items()
        ):
            raise SupervisorStoreError("Issue worktree keys must equal issue IDs")
        if any(
            operation_id != record.get("operationId")
            for operation_id, record in state["gateWorktrees"].items()
        ):
            raise SupervisorStoreError("Gate worktree keys must equal operation IDs")

    def _validate_reservations(self, reservations: dict[str, Any]) -> None:
        try:
            validate_contract("editing-reservation", reservations)
        except ContractValidationError as exc:
            raise SupervisorStoreError(
                "Reservation state does not satisfy its complete persisted contract"
            ) from exc
        required = {
            "schemaVersion",
            "revision",
            "reservations",
            "consumedObservationIds",
            "consumedAuthorizationIds",
        }
        if set(reservations) != required or reservations.get("schemaVersion") != SUPERVISOR_STATE_VERSION:
            raise SupervisorStoreError("Reservation state has unknown, missing, or versioned fields")
        if not isinstance(reservations.get("revision"), int) or reservations["revision"] < 1:
            raise SupervisorStoreError("Reservation revision must be positive")
        if not isinstance(reservations.get("reservations"), dict):
            raise SupervisorStoreError("Reservation records must be an object")
        for field in ("consumedObservationIds", "consumedAuthorizationIds"):
            values = reservations.get(field)
            if not isinstance(values, list) or len(values) != len(set(values)):
                raise SupervisorStoreError(f"{field} must be a unique array")

    def _validate_transaction(self, value: dict[str, Any], path: Path) -> None:
        required = {
            "schemaVersion",
            "transactionId",
            "operation",
            "statePath",
            "reservationsPath",
            "beforeState",
            "afterState",
            "beforeReservations",
            "afterReservations",
            "beforeStateSha256",
            "afterStateSha256",
            "beforeReservationsSha256",
            "afterReservationsSha256",
            "decision",
        }
        if set(value) != required or value.get("schemaVersion") != SUPERVISOR_TRANSACTION_VERSION:
            raise SupervisorRecoveryError("Supervisor transaction shape is invalid")
        transaction_id = value.get("transactionId")
        try:
            if str(uuid.UUID(transaction_id)) != transaction_id:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise SupervisorRecoveryError("Supervisor transaction ID is invalid") from exc
        if path.name != f"{transaction_id}.json":
            raise SupervisorRecoveryError("Supervisor transaction filename is mismatched")
        if value["statePath"] != os.fspath(self.state_path) or value[
            "reservationsPath"
        ] != os.fspath(self.reservations_path):
            raise SupervisorRecoveryError("Supervisor transaction paths are not canonical")
        if value.get("decision") != "commit-after":
            raise SupervisorRecoveryError("Supervisor transaction decision is not authoritative")
        pairs = (
            ("beforeState", "beforeStateSha256"),
            ("afterState", "afterStateSha256"),
            ("beforeReservations", "beforeReservationsSha256"),
            ("afterReservations", "afterReservationsSha256"),
        )
        if any(sha256_json(value[document]) != value[digest] for document, digest in pairs):
            raise SupervisorRecoveryError("Supervisor transaction hash evidence was tampered")
        self._validate_state(value["beforeState"])
        self._validate_state(value["afterState"])
        self._validate_reservations(value["beforeReservations"])
        self._validate_reservations(value["afterReservations"])
        self._validate_transition(value["beforeState"], value["afterState"], "state")
        self._validate_transition(
            value["beforeReservations"], value["afterReservations"], "reservations"
        )

    @staticmethod
    def _side(current: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> str:
        if current == after:
            return "after"
        if current == before:
            return "before"
        return "unknown"

    def _fault(self, stage: str, transaction_id: str) -> None:
        if self.fault_injector is not None:
            self.fault_injector(stage, transaction_id)


def build_manager(
    repository_root: str | Path,
    *,
    repository_key: str,
    state_home_override: str | Path | None = None,
    environment: dict[str, str] | None = None,
) -> Any:
    runtime = load_base_runtime()
    return runtime.WorkflowManager(
        repository_root,
        repository_key=repository_key,
        state_home_override=state_home_override,
        environment=environment,
    )
