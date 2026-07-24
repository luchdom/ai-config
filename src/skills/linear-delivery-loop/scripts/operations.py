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
from .publication_records import validate_publication_state


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
                "retryCount": 0,
                "headSha": request_value.get("headSha"),
                "providerEvidenceRef": None,
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


class PublicationJournal:
    """Persist one strict publication state beneath its immutable operation ID."""

    def __init__(self, store: SupervisorStore, *, fault_injector: Callable[[str, str], None] | None = None):
        self.store = store
        self.fault_injector = fault_injector

    def state_path(self, operation_id: str, *, must_exist: bool = False):
        if not isinstance(operation_id, str) or _SAFE_ID.fullmatch(operation_id) is None:
            raise SupervisorStoreError("Publication operation ID is unsafe")
        directory = self.store.guard.directory(
            self.store.directories["operations"] / operation_id,
            create=not must_exist,
        )
        return self.store.guard.leaf(
            directory / "publication-state.json", must_exist=must_exist
        )

    def proposal_path(self, operation_id: str, *, must_exist: bool = False):
        directory = self.store.guard.directory(
            self.store.directories["operations"] / operation_id,
            create=not must_exist,
        )
        return self.store.guard.leaf(
            directory / "publication-proposal.json", must_exist=must_exist
        )

    def save(self, value: Mapping[str, Any]) -> dict[str, Any]:
        state = validate_publication_state(value)
        operation_id = state["operationId"]
        if _SAFE_ID.fullmatch(operation_id) is None:
            raise SupervisorStoreError("Publication operation ID is unsafe")
        assert_public_data(state, location="publication state")
        path = self.state_path(operation_id)
        with self.store.mutex():
            if path.exists():
                previous = self.store.guard.read_json(path)
                validate_publication_state(previous)
                immutable = (
                    "schemaVersion", "repositoryId", "repositoryKey", "workflowId",
                    "issueId", "operationId", "idempotencyKey", "operation",
                    "baseRef", "createdAt",
                )
                if any(previous[name] != state[name] for name in immutable):
                    raise SupervisorConflictError(
                        "Publication operation was replayed with changed identity/head"
                    )
                if (previous["branch"], previous["headSha"]) != (state["branch"], state["headSha"]):
                    evidence_finalization = (
                        previous["branch"] == state["branch"]
                        and previous["evidenceFinalizationCount"] == 0
                        and state["evidenceFinalizationCount"] == 1
                        and state.get("evidenceFinalization", {}).get("headSha") == state["headSha"]
                    )
                    drift_preparation = previous["status"] == "base-drift" and state["status"] == "prepared" and previous["branch"] == state["branch"] and state.get("preparation", {}).get("headSha") == state["headSha"]
                    if not (
                        previous["status"] == "post-merge-validating"
                        and state["repairAttempt"] == previous["repairAttempt"] + 1
                        and state["status"] == "prepared"
                    ) and not (
                        previous["status"] == state["status"] == "prepared"
                        and previous["repairAttempt"] == state["repairAttempt"] > 0
                        and previous["branch"] == state["branch"]
                        and not previous["attestations"] and not state["attestations"]
                    ) and not evidence_finalization and not drift_preparation:
                        raise SupervisorConflictError(
                            "Publication head may change only for a numbered repair"
                        )
                if previous == state:
                    return copy.deepcopy(state)
            self.store.guard.write_json(path, state)
        return copy.deepcopy(state)

    def save_authoritative(
        self, value: Mapping[str, Any], *, expected_state_revision: int | None = None,
        authority_check: Callable[[Mapping[str, Any], Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """CAS-bind an exact proposal before exposing an authoritative journal.

        A proposal written before the paired supervisor commit is deliberately
        non-authoritative.  Reconciliation accepts it only when the supervisor
        summary contains the digest committed by the successful CAS.
        """

        publication = validate_publication_state(value)
        operation_id = publication["operationId"]
        assert_public_data(publication, location="publication state")
        proposal_path = self.proposal_path(operation_id)
        path = self.state_path(operation_id)
        transition_digest = "sha256:" + sha256_json(publication)
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            if (
                expected_state_revision is not None
                and state["revision"] != expected_state_revision
            ):
                raise SupervisorConflictError("Publication supervisor CAS is stale")
            if authority_check is not None:
                authority_check(state, reservations)
            if path.exists():
                previous = validate_publication_state(self.store.guard.read_json(path))
                immutable = ("schemaVersion", "repositoryId", "repositoryKey", "workflowId", "issueId", "operationId", "idempotencyKey", "operation", "baseRef", "createdAt")
                if any(previous[name] != publication[name] for name in immutable):
                    raise SupervisorConflictError("publication authoritative identity changed")
                if (previous["branch"], previous["headSha"]) != (publication["branch"], publication["headSha"]):
                    repair_start = previous["status"] == "post-merge-validating" and publication["status"] == "prepared" and publication["repairAttempt"] == previous["repairAttempt"] + 1
                    repair_head = previous["status"] == publication["status"] == "prepared" and previous["repairAttempt"] == publication["repairAttempt"] > 0 and previous["branch"] == publication["branch"] and not previous["attestations"] and not publication["attestations"]
                    evidence_finalization = previous["branch"] == publication["branch"] and previous["evidenceFinalizationCount"] == 0 and publication["evidenceFinalizationCount"] == 1 and publication.get("evidenceFinalization", {}).get("headSha") == publication["headSha"]
                    base_drift = previous["branch"] == publication["branch"] and previous["baseSha"] != publication["baseSha"] and publication["status"] == "base-drift" and not publication["attestations"]
                    drift_preparation = previous["status"] == "base-drift" and publication["status"] == "prepared" and previous["branch"] == publication["branch"] and publication.get("preparation", {}).get("headSha") == publication["headSha"]
                    if not (repair_start or repair_head or evidence_finalization or base_drift or drift_preparation):
                        raise SupervisorConflictError("publication authoritative head changed illegally")
            self.store.guard.write_json(proposal_path, publication)
            summary = {
                "operationId": operation_id,
                "issueId": publication["issueId"],
                "headSha": publication["headSha"],
                "status": publication["status"],
                "stateRef": os.fspath(path),
                "proposalRef": os.fspath(proposal_path),
                "transitionDigest": transition_digest,
            }
            existing = state.get("publication")
            if existing == summary:
                return copy.deepcopy(publication)
            if existing is not None and existing.get("operationId") != operation_id:
                if existing.get("status") not in {"completed"}:
                    raise SupervisorConflictError("another publication remains authoritative")
            after = copy.deepcopy(state)
            after["publication"] = summary
            after["revision"] = state["revision"] + 1
            # A bounded publication transition preserves, but never extends,
            # the already-live run capability.  This lets the reservation
            # manager issue the next distinct one-shot grant without turning
            # a supervisor-owned journal revision into accidental lease loss.
            if isinstance(after.get("lease"), dict) and after["lease"].get("status") == "live":
                after["lease"]["revision"] = after["revision"]
                current = after.get("currentWork") or {}
                for capability in after.get("capabilities", {}).values():
                    if (
                        capability.get("status") == "issued"
                        and capability.get("runId") == after["lease"].get("runId")
                        and capability.get("stage") == current.get("stage")
                        and current.get("stage") in {
                            "review", "qa", "docs", "publication", "completion",
                        }
                    ):
                        capability["stateRevision"] = after["revision"]
            self.store.commit_pair_unlocked(
                before_state=state, after_state=after,
                before_reservations=reservations, after_reservations=reservations,
                operation=f"PublicationState:{operation_id}:{publication['status']}",
            )
            if self.fault_injector is not None:
                self.fault_injector("after-publication-cas", operation_id)
            self.store.guard.write_json(path, publication)
        return copy.deepcopy(publication)

    def reconcile_authoritative(self, operation_id: str) -> dict[str, Any]:
        """Materialize only a proposal whose exact digest won supervisor CAS."""

        with self.store.mutex():
            state, _ = self.store.load_pair_unlocked()
            summary = state.get("publication")
            if not isinstance(summary, Mapping) or summary.get("operationId") != operation_id:
                raise SupervisorConflictError("publication proposal never won authoritative CAS")
            proposal_path = self.proposal_path(operation_id, must_exist=True)
            if summary.get("proposalRef") != os.fspath(proposal_path):
                raise SupervisorConflictError("publication proposal reference is not authoritative")
            publication = validate_publication_state(self.store.guard.read_json(proposal_path))
            if summary.get("transitionDigest") != "sha256:" + sha256_json(publication):
                raise SupervisorConflictError("publication proposal digest is not authoritative")
            self.store.guard.write_json(self.state_path(operation_id), publication)
            return copy.deepcopy(publication)

    def load(self, operation_id: str) -> dict[str, Any]:
        if not isinstance(operation_id, str) or _SAFE_ID.fullmatch(operation_id) is None:
            raise SupervisorStoreError("Publication operation ID is unsafe")
        path = self.state_path(operation_id, must_exist=True)
        return validate_publication_state(self.store.guard.read_json(path))

    def issue_attestation(self, value: Mapping[str, Any]) -> dict[str, Any]:
        """Persist the engine-issued attestation sidecar used by merge verification."""

        from .publication_records import validate_publication_attestation
        attestation = validate_publication_attestation(value)
        filename = f"{attestation['attestationId']}.json"
        path = self.store.guard.leaf(
            self.store.directories["publication-attestations"] / filename
        )
        with self.store.mutex():
            if path.exists():
                existing = validate_publication_attestation(self.store.guard.read_json(path))
                if existing != attestation:
                    raise SupervisorConflictError("publication attestation identity was replayed differently")
                return existing
            self.store.guard.write_json(path, attestation)
        return copy.deepcopy(attestation)

    def require_issued_attestation(self, value: Mapping[str, Any]) -> dict[str, Any]:
        from .publication_records import validate_publication_attestation
        attestation = validate_publication_attestation(value)
        path = self.store.guard.leaf(
            self.store.directories["publication-attestations"]
            / f"{attestation['attestationId']}.json", must_exist=True,
        )
        issued = validate_publication_attestation(self.store.guard.read_json(path))
        if issued != attestation:
            raise SupervisorConflictError("publication attestation is not engine-issued evidence")
        return issued

    def resolve_checkpoint_result(
        self, *, publication: Mapping[str, Any], source_operation_id: str
    ) -> dict[str, Any]:
        """Derive publication evidence from an immutable ApplyCheckpoint journal."""
        source_dir = self.store.directories["operations"] / source_operation_id
        if not source_dir.is_dir():
            raise SupervisorStoreError("publication evidence source operation is absent")
        evidence = OperationJournal(self.store).load(source_operation_id)
        journal, request, result = evidence["journal"], evidence["request"], evidence["result"]
        if journal["operation"] != "ApplyCheckpoint" or journal["status"] != "completed":
            raise SupervisorStoreError("publication evidence source is not a completed checkpoint")
        validate_contract("engine-command", request)
        if request.get("operation") != "ApplyCheckpoint":
            raise SupervisorStoreError("publication evidence source command is mismatched")
        transition_id = request.get("transitionId")
        state = self.store.load_state()
        checkpoint = state["checkpoints"].get(transition_id)
        if not isinstance(checkpoint, Mapping) or checkpoint != result or checkpoint.get("status") != "applied":
            raise SupervisorStoreError("publication evidence checkpoint is absent or mismatched")
        matches = []
        for run_dir in self.store.directories["runs"].iterdir():
            candidate = run_dir / f"checkpoint-{transition_id}.json"
            if candidate.is_file():
                matches.append(self.store.guard.leaf(candidate, must_exist=True))
        if len(matches) != 1:
            raise SupervisorStoreError("publication evidence checkpoint record is ambiguous")
        checkpoint_record = self.store.guard.read_json(matches[0])
        required = {"schemaVersion", "transitionId", "preparedRef", "resultSha256", "result"}
        if set(checkpoint_record) != required or checkpoint_record.get("transitionId") != transition_id:
            raise SupervisorStoreError("publication checkpoint result record is malformed")
        worker = validate_contract("worker-result", checkpoint_record["result"])
        if checkpoint_record["resultSha256"] != sha256_json(worker):
            raise SupervisorStoreError("publication worker result digest is mismatched")
        prepared_ref = self.store.guard.leaf(request["preparedIterationRef"], must_exist=True)
        prepared = validate_contract("prepared-iteration", self.store.guard.read_json(prepared_ref))
        if checkpoint_record["preparedRef"] != os.fspath(prepared_ref):
            raise SupervisorStoreError("publication checkpoint prepared-iteration reference differs")
        stage_to_kind = {"review": "review", "qa": "qa", "docs": "docs"}
        kind = stage_to_kind.get(worker["completedStage"])
        if worker["completedStage"] == "publication" and worker["proposedNextStage"] == "completion":
            kind = "evidence-convergence"
        if kind is None or worker["outcome"] not in {"advanced", "completed"} or worker["pause"] is not None:
            raise SupervisorStoreError("worker result does not establish passing publication evidence")
        worker_expected = {"workflowId": publication["workflowId"], "issueId": publication["issueId"]}
        if any(worker.get(name) != value for name, value in worker_expected.items()) or worker["observed"].get("repositoryId") != publication["repositoryId"] or worker["observed"].get("physicalWorktreeFingerprint") != publication["preservedState"]["physicalWorktreeFingerprint"]:
            raise SupervisorStoreError("publication worker result belongs to another authority")
        expected = {
            **worker_expected, "repositoryId": publication["repositoryId"],
            "physicalWorktreeFingerprint": publication["preservedState"]["physicalWorktreeFingerprint"],
        }
        if any(prepared.get(name) != value for name, value in expected.items()):
            raise SupervisorStoreError("publication prepared iteration belongs to another authority")
        if prepared.get("repositoryKey") != publication["repositoryKey"] or request.get("repositoryKey") != publication["repositoryKey"]:
            raise SupervisorStoreError("publication checkpoint repository key differs")
        if os.path.normcase(os.path.realpath(request.get("stateHome", ""))) != os.path.normcase(os.path.realpath(self.store.root)):
            raise SupervisorStoreError("publication checkpoint state home differs")
        normalized_worktree = os.path.normcase(os.path.realpath(publication["preservedState"]["worktreePath"]))
        if os.path.normcase(os.path.realpath(prepared["worktreePath"])) != normalized_worktree:
            raise SupervisorStoreError("publication prepared worktree differs")
        if request.get("expectedStage") != worker["completedStage"] or prepared["stage"] != worker["completedStage"]:
            raise SupervisorStoreError("publication checkpoint stage binding differs")
        if worker["observed"]["headSha"] != publication["headSha"]:
            raise SupervisorStoreError("publication checkpoint exact SHA differs")
        from .publication_records import ATTESTATION_PRODUCERS
        return {
            "schemaVersion": "1.0", "resultId": source_operation_id,
            "publicationOperationId": publication["operationId"], "kind": kind,
            "producer": ATTESTATION_PRODUCERS[kind], "stage": "pre-merge",
            "exactSha": worker["observed"]["headSha"], "outcome": "passed",
            "recordedAt": journal["updatedAt"], "sourceOperationId": source_operation_id,
            "sourceRecordDigest": "sha256:" + sha256_json(checkpoint_record),
        }

    def record_refusal(
        self, operation_id: str, response: Mapping[str, Any], readback: Mapping[str, Any]
    ) -> str:
        from .publication_provider import normalized_refusal

        safe = normalized_refusal(response, readback)
        value = {"schemaVersion": "1.0", "operationId": operation_id,
                 **safe}
        assert_public_data(value, location="publication refusal")
        digest = "sha256:" + sha256_json(safe)
        directory = self.store.guard.directory(self.store.directories["operations"] / operation_id)
        path = self.store.guard.leaf(directory / "provider-refusal.json")
        value["digest"] = digest
        with self.store.mutex():
            self.store.guard.write_json(path, value)
        return digest

    def require_refusal(self, operation_id: str, expected_digest: str) -> dict[str, Any]:
        directory = self.store.guard.directory(self.store.directories["operations"] / operation_id)
        path = self.store.guard.leaf(directory / "provider-refusal.json", must_exist=True)
        value = self.store.guard.read_json(path)
        if set(value) != {"schemaVersion", "operationId", "classification", "reconciliation", "digest"} or value.get("schemaVersion") != "1.0" or value.get("operationId") != operation_id:
            raise SupervisorStoreError("publication refusal record is malformed")
        actual = "sha256:" + sha256_json({"classification": value["classification"], "reconciliation": value["reconciliation"]})
        if value.get("digest") != actual or actual != expected_digest:
            raise SupervisorStoreError("publication refusal record digest is mismatched")
        return copy.deepcopy(value)
