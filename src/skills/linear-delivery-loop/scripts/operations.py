"""Replay-safe, schema-validated operation journals."""

from __future__ import annotations

import copy
import os
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from .contracts import ContractValidationError, validate_contract
from .store import (
    SupervisorConflictError,
    SupervisorStore,
    SupervisorStoreError,
    assert_public_data,
    sha256_json,
)


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TERMINAL = frozenset({"completed", "failed", "ambiguous"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _pair_hash(state: Mapping[str, Any], reservations: Mapping[str, Any]) -> str:
    return "sha256:" + sha256_json(
        {"state": dict(state), "reservations": dict(reservations)}
    )


class OperationJournal:
    """Bind an operation ID to one request and one canonical durable journal."""

    def __init__(self, store: SupervisorStore):
        self.store = store

    def begin(
        self,
        *,
        operation_id: str,
        operation: str,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_id(operation_id, "operation ID")
        self._validate_id(operation, "operation name")
        request_value = copy.deepcopy(dict(request))
        assert_public_data(request_value, location="operation request")
        request_hash = "sha256:" + sha256_json(request_value)
        operation_dir = self.store.guard.directory(
            self.store.directories["operations"] / operation_id, create=True
        )
        journal_path = self.store.guard.leaf(operation_dir / "journal.json")
        request_path = self.store.guard.leaf(operation_dir / "request.json")
        with self.store.mutex():
            if journal_path.exists() or request_path.exists():
                if not journal_path.exists() or not request_path.exists():
                    raise SupervisorStoreError("Operation evidence is incomplete or tampered")
                journal = self._read_journal(journal_path)
                existing_request = self._read_request(request_path)
                self._assert_binding(
                    journal,
                    existing_request,
                    operation_id=operation_id,
                    operation=operation,
                    request_hash=request_hash,
                    request=request_value,
                )
                if journal["status"] in _TERMINAL:
                    result = self._read_result_for(journal, operation_dir)
                    return {"status": "replayed", "result": copy.deepcopy(result)}
                return {
                    "status": "pending",
                    "operationId": operation_id,
                    "requestSha256": request_hash,
                }
            state, reservations = self.store.load_pair_unlocked()
            created = _now()
            request_record = {
                "schemaVersion": "1.0",
                "operationId": operation_id,
                "operation": operation,
                "requestSha256": request_hash,
                "request": request_value,
            }
            journal = {
                "schemaVersion": "1.0",
                "operationId": operation_id,
                "idempotencyKey": operation_id,
                "operation": operation,
                "requestHash": request_hash,
                "status": "pending",
                "attemptCount": 1,
                "beforeStateHash": _pair_hash(state, reservations),
                "afterStateHash": None,
                "resultRef": None,
                "errorCode": None,
                "createdAt": created,
                "updatedAt": created,
            }
            validate_contract("operation-journal", journal)
            self.store.guard.write_json(request_path, request_record)
            self.store.guard.write_json(journal_path, journal)
            return {
                "status": "created",
                "operationId": operation_id,
                "requestSha256": request_hash,
            }

    def complete(
        self,
        *,
        operation_id: str,
        operation: str,
        request: Mapping[str, Any],
        result: Mapping[str, Any],
        status: str = "completed",
        error_code: str | None = None,
    ) -> dict[str, Any]:
        if status not in _TERMINAL:
            raise SupervisorStoreError("Operation result status is invalid")
        if status == "completed" and error_code is not None:
            raise SupervisorStoreError("Completed operation cannot carry an error code")
        if status != "completed" and error_code is None:
            error_code = "OPERATION_FAILED" if status == "failed" else "AMBIGUOUS_OUTCOME"
        request_value = copy.deepcopy(dict(request))
        result_value = copy.deepcopy(dict(result))
        assert_public_data(request_value, location="operation request")
        assert_public_data(result_value, location="operation result")
        request_hash = "sha256:" + sha256_json(request_value)
        operation_dir = self.store.guard.directory(
            self.store.directories["operations"] / operation_id
        )
        request_path = self.store.guard.leaf(operation_dir / "request.json", must_exist=True)
        journal_path = self.store.guard.leaf(operation_dir / "journal.json", must_exist=True)
        result_path = self.store.guard.leaf(operation_dir / "result.json")
        with self.store.mutex():
            request_record = self._read_request(request_path)
            journal = self._read_journal(journal_path)
            self._assert_binding(
                journal,
                request_record,
                operation_id=operation_id,
                operation=operation,
                request_hash=request_hash,
                request=request_value,
            )
            if journal["status"] in _TERMINAL:
                existing_result = self._read_result_for(journal, operation_dir)
                if existing_result != result_value or journal["status"] != status:
                    raise SupervisorConflictError(
                        "Operation result was replayed with changed evidence"
                    )
                return copy.deepcopy(existing_result)
            state, reservations = self.store.load_pair_unlocked()
            result_record = {
                "schemaVersion": "1.0",
                "operationId": operation_id,
                "operation": operation,
                "requestHash": request_hash,
                "status": status,
                "resultHash": "sha256:" + sha256_json(result_value),
                "result": result_value,
            }
            self._validate_result(result_record, operation_id, operation, request_hash)
            if result_path.exists():
                existing_result = self.store.guard.read_json(result_path)
                self._validate_result(
                    existing_result, operation_id, operation, request_hash
                )
                if existing_result != result_record:
                    raise SupervisorConflictError(
                        "Operation result candidate differs from completion"
                    )
            else:
                self.store.guard.write_json(result_path, result_record)
            completed = copy.deepcopy(journal)
            completed.update(
                {
                    "status": status,
                    "afterStateHash": _pair_hash(state, reservations),
                    "resultRef": os.fspath(result_path),
                    "errorCode": error_code,
                    "updatedAt": _now(),
                }
            )
            validate_contract("operation-journal", completed)
            self.store.guard.write_json(journal_path, completed)
            # Journals have a separate evidence revision domain. Updating them
            # must not invalidate state-bound capabilities minted by the action.
            return result_value

    def load(self, operation_id: str) -> dict[str, Any]:
        """Load and validate all durable evidence for one operation."""

        self._validate_id(operation_id, "operation ID")
        operation_dir = self.store.guard.directory(
            self.store.directories["operations"] / operation_id
        )
        journal = self._read_journal(
            self.store.guard.leaf(operation_dir / "journal.json", must_exist=True)
        )
        request = self._read_request(
            self.store.guard.leaf(operation_dir / "request.json", must_exist=True)
        )
        self._assert_binding(
            journal,
            request,
            operation_id=operation_id,
            operation=journal["operation"],
            request_hash=journal["requestHash"],
            request=request["request"],
        )
        result = None
        result_candidate = None
        if journal["status"] in _TERMINAL:
            result = self._read_result_for(journal, operation_dir)
        elif journal["resultRef"] is not None:
            raise SupervisorStoreError("Pending journal unexpectedly references a result")
        else:
            candidate_path = self.store.guard.leaf(operation_dir / "result.json")
            if candidate_path.exists():
                candidate = self.store.guard.read_json(candidate_path)
                self._validate_result(
                    candidate,
                    journal["operationId"],
                    journal["operation"],
                    journal["requestHash"],
                )
                result_candidate = {
                    "status": candidate["status"],
                    "result": copy.deepcopy(candidate["result"]),
                }
        return {
            "journal": journal,
            "request": request["request"],
            "result": result,
            "resultCandidate": result_candidate,
        }

    def pending_ids(self, *, ignore_operation_id: str | None = None) -> list[str]:
        pending: list[str] = []
        operations_root = self.store.guard.directory(self.store.directories["operations"])
        for candidate in operations_root.iterdir():
            if not candidate.is_dir():
                raise SupervisorStoreError("Operations home contains a non-directory entry")
            if candidate.name == ignore_operation_id:
                continue
            evidence = self.load(candidate.name)
            if evidence["journal"]["status"] == "pending":
                pending.append(candidate.name)
        return sorted(pending)

    def repair_pre_action_interruptions(self) -> list[str]:
        """Repair only crash shapes that prove the action never started.

        ``begin`` writes the immutable request before the canonical journal and
        does not return to its caller until both exist. Therefore a request-only
        directory is safely reconstructed as pending at the current exact state
        pair; normal recovery will then finalize it as interrupted-before-
        mutation. Empty allocation directories are removed. Every other partial
        shape remains tamper/ambiguity and fails closed.
        """

        repaired: list[str] = []
        operations_root = self.store.guard.directory(self.store.directories["operations"])
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            for candidate in list(operations_root.iterdir()):
                operation_dir = self.store.guard.directory(candidate)
                request_path = self.store.guard.leaf(operation_dir / "request.json")
                journal_path = self.store.guard.leaf(operation_dir / "journal.json")
                result_path = self.store.guard.leaf(operation_dir / "result.json")
                existing = [path.exists() for path in (request_path, journal_path, result_path)]
                if existing == [False, False, False]:
                    operation_dir.rmdir()
                    continue
                if existing == [True, False, False]:
                    request = self._read_request(request_path)
                    if request["operationId"] != operation_dir.name:
                        raise SupervisorStoreError(
                            "Pre-action request directory binding is mismatched"
                        )
                    created = _now()
                    journal = {
                        "schemaVersion": "1.0",
                        "operationId": request["operationId"],
                        "idempotencyKey": request["operationId"],
                        "operation": request["operation"],
                        "requestHash": request["requestSha256"],
                        "status": "pending",
                        "attemptCount": 1,
                        "beforeStateHash": _pair_hash(state, reservations),
                        "afterStateHash": None,
                        "resultRef": None,
                        "errorCode": None,
                        "createdAt": created,
                        "updatedAt": created,
                    }
                    validate_contract("operation-journal", journal)
                    self.store.guard.write_json(journal_path, journal)
                    repaired.append(request["operationId"])
                elif not all(existing[:2]):
                    raise SupervisorStoreError(
                        "Operation evidence has an ambiguous partial shape"
                    )
        return sorted(repaired)

    def execute(
        self,
        *,
        operation_id: str,
        operation: str,
        request: Mapping[str, Any],
        action: Callable[[], Mapping[str, Any]],
    ) -> dict[str, Any]:
        begun = self.begin(operation_id=operation_id, operation=operation, request=request)
        if begun["status"] == "replayed":
            return begun["result"]
        if begun["status"] == "pending":
            raise SupervisorConflictError(
                "Operation has no durable result and requires recovery before re-execution"
            )
        try:
            result = action()
        except Exception:
            self.complete(
                operation_id=operation_id,
                operation=operation,
                request=request,
                result={"error": "operation-failed"},
                status="failed",
            )
            raise
        return self.complete(
            operation_id=operation_id,
            operation=operation,
            request=request,
            result=result,
        )

    @staticmethod
    def pair_hash(state: Mapping[str, Any], reservations: Mapping[str, Any]) -> str:
        return _pair_hash(state, reservations)

    @staticmethod
    def _validate_id(value: str, label: str) -> None:
        if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
            raise SupervisorStoreError(f"{label} is not a safe canonical identifier")

    def _read_request(self, path: Any) -> dict[str, Any]:
        # Kept as a strict private companion because the public journal schema
        # stores the request digest rather than arbitrary request content.
        record = self.store.guard.read_json(path)
        required = {"schemaVersion", "operationId", "operation", "requestSha256", "request"}
        if set(record) != required or record.get("schemaVersion") != "1.0":
            raise SupervisorStoreError("Operation request evidence is malformed")
        if record.get("requestSha256") != "sha256:" + sha256_json(record.get("request")):
            raise SupervisorStoreError("Operation request evidence is tampered")
        return record

    def _read_journal_path(self, path: Any) -> dict[str, Any]:
        try:
            value = self.store.guard.read_json(path)
            return validate_contract("operation-journal", value)
        except ContractValidationError as exc:
            raise SupervisorStoreError("Operation journal is malformed or tampered") from exc

    def _read_journal(self, path: Any) -> dict[str, Any]:
        return self._read_journal_path(path)

    def _read_result_for(self, journal: Mapping[str, Any], operation_dir: Any) -> dict[str, Any]:
        reference = journal.get("resultRef")
        if not isinstance(reference, str):
            raise SupervisorStoreError("Terminal journal lacks a result reference")
        expected = self.store.guard.leaf(operation_dir / "result.json", must_exist=True)
        actual = self.store.guard.leaf(reference, must_exist=True)
        if actual != expected:
            raise SupervisorStoreError("Operation result reference escapes its journal")
        value = self.store.guard.read_json(actual)
        self._validate_result(
            value, journal["operationId"], journal["operation"], journal["requestHash"]
        )
        if value["status"] != journal["status"]:
            raise SupervisorStoreError("Operation journal/result status differs")
        return copy.deepcopy(value["result"])

    @staticmethod
    def _assert_binding(
        journal: Mapping[str, Any],
        request_record: Mapping[str, Any],
        *,
        operation_id: str,
        operation: str,
        request_hash: str,
        request: Mapping[str, Any],
    ) -> None:
        if (
            journal.get("operationId") != operation_id
            or journal.get("operation") != operation
            or journal.get("requestHash") != request_hash
            or journal.get("idempotencyKey") != operation_id
            or request_record.get("operationId") != operation_id
            or request_record.get("operation") != operation
            or request_record.get("requestSha256") != request_hash
            or request_record.get("request") != dict(request)
        ):
            raise SupervisorConflictError(
                "Operation ID was replayed with a changed immutable request"
            )

    @staticmethod
    def _validate_result(
        value: dict[str, Any], operation_id: str, operation: str, request_hash: str
    ) -> None:
        required = {
            "schemaVersion",
            "operationId",
            "operation",
            "requestHash",
            "status",
            "resultHash",
            "result",
        }
        if (
            set(value) != required
            or value.get("schemaVersion") != "1.0"
            or value.get("operationId") != operation_id
            or value.get("operation") != operation
            or value.get("requestHash") != request_hash
            or value.get("status") not in _TERMINAL
            or value.get("resultHash") != "sha256:" + sha256_json(value.get("result"))
        ):
            raise SupervisorStoreError("Operation result evidence is malformed or tampered")
