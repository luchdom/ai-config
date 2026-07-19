"""Narrow in-mutex reservation interlock for the canonical base Handoff.

The supervisor owns reservations and authority transfer.  This module owns only
the final allow/deny decision that must run while the base registry mutex is
held.  Public CLI input can never construct the internal authorization type.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import HandoffError, ValidationError

if TYPE_CHECKING:
    from .workflow_init import WorkflowManager


INTERLOCK_VERSION = "1.0"
_TERMINAL_STATUSES = {"released", "reclaimed"}
_BLOCKING_STATUSES = {"live", "handoff-pending", "expired", "protected"}
_KNOWN_STATUSES = _TERMINAL_STATUSES | _BLOCKING_STATUSES


@dataclass(frozen=True)
class InternalHandoffAuthorization:
    """Engine-held Phase-B value; deliberately absent from every public CLI."""

    operation_id: str
    nonce: str


def handoff_request_hash(
    *,
    operation_id: str,
    workflow_id: str,
    repository_key: str,
    source_fingerprint: str,
    destination_fingerprint: str,
    expected_paths: list[str],
    reservation_id: str,
    reservation_revision: int,
) -> str:
    value = {
        "destinationFingerprint": destination_fingerprint,
        "expectedPaths": sorted(expected_paths, key=str.casefold),
        "operationId": operation_id,
        "repositoryKey": repository_key,
        "reservationId": reservation_id,
        "reservationRevision": reservation_revision,
        "sourceFingerprint": source_fingerprint,
        "workflowId": workflow_id,
    }
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _canonical_uuid(value: Any, label: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HandoffError(f"{label} must be a canonical UUID") from exc
    if str(parsed) != value:
        raise HandoffError(f"{label} must be a canonical UUID")
    return value


def _reservations(source: "WorkflowManager") -> tuple[Path, dict[str, Any]] | None:
    reservations_path = source.home.repository / "reservations.json"
    if not os.path.lexists(reservations_path):
        return None
    value = source.state_paths.read_json(reservations_path)
    if (
        set(value)
        != {
            "schemaVersion",
            "revision",
            "reservations",
            "consumedObservationIds",
            "consumedAuthorizationIds",
        }
        or value.get("schemaVersion") != INTERLOCK_VERSION
        or not isinstance(value.get("revision"), int)
        or value["revision"] < 1
        or not isinstance(value.get("reservations"), dict)
        or not isinstance(value.get("consumedObservationIds"), list)
        or not isinstance(value.get("consumedAuthorizationIds"), list)
    ):
        raise HandoffError("Supervisor reservation index is malformed; Handoff fails closed")
    return reservations_path, value


def _active_reservations(value: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every non-terminal record, without pre-filtering authority.

    The reservation index is repository-scoped.  Filtering by the requested
    workflow before deciding whether the base Handoff is blocked would let a
    caller bypass another workflow's exclusive reservation. Expired and
    protected records remain blockers until an explicit safe transition marks
    them released or reclaimed.
    """

    active: list[dict[str, Any]] = []
    for reservation_id, record in value["reservations"].items():
        if not isinstance(record, dict):
            raise HandoffError("Supervisor reservation record is malformed; Handoff fails closed")
        if record.get("reservationId") != reservation_id:
            raise HandoffError("Supervisor reservation identity mismatch; Handoff fails closed")
        status = record.get("status")
        if status not in _KNOWN_STATUSES:
            raise HandoffError("Supervisor reservation status is unknown; Handoff fails closed")
        if status in _BLOCKING_STATUSES:
            active.append(record)
    return active


def _normalized_path(value: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(value)))).replace(
        "\\", "/"
    )


def _validate_editing_source_mapping_unlocked(
    *,
    source: "WorkflowManager",
    workflow_id: str,
    operation_id: str,
    reservation: dict[str, Any],
    editing_source_path: Path,
    editing_source_fingerprint: str,
) -> None:
    normalized_source = _normalized_path(editing_source_path)
    if (
        reservation.get("repositoryId") != source.identity.repository_id
        or reservation.get("repositoryKey") != source.repository_key
        or reservation.get("workflowId") != workflow_id
        or reservation.get("worktreePath") != normalized_source
        or reservation.get("physicalWorktreeFingerprint")
        != editing_source_fingerprint
    ):
        raise HandoffError(
            "Handoff reservation path/fingerprint differs from the effective editing source"
        )

    registry = source._load_registry_unlocked()
    entry = registry.get("workflows", {}).get(workflow_id)
    if (
        not isinstance(entry, dict)
        or entry.get("repositoryId") != source.identity.repository_id
        or entry.get("repositoryKey") != source.repository_key
        or entry.get("physicalWorktreeFingerprint") != editing_source_fingerprint
        or _normalized_path(Path(entry.get("artifactPath", "")).parent.parent)
        != normalized_source
    ):
        raise HandoffError(
            "Handoff registry mapping differs from the effective editing source"
        )

    state_path = source.home.repository / "supervisor-state.json"
    if not os.path.lexists(state_path):
        raise HandoffError("Supervisor Handoff state is absent; Handoff fails closed")
    state = source.state_paths.read_json(state_path)
    if not isinstance(state, dict):
        raise HandoffError("Supervisor state is malformed; Handoff fails closed")
    pending = state.get("handoffPending")
    if not isinstance(pending, dict) or any(
        pending.get(field) != expected
        for field, expected in {
            "operationId": operation_id,
            "reservationId": reservation.get("reservationId"),
            "workflowId": workflow_id,
            "status": "prepared",
        }.items()
    ):
        raise HandoffError(
            "Supervisor Handoff pending barrier differs from the internal authorization"
        )

    issue_id = reservation.get("issueId")
    policy = reservation.get("policy")
    if issue_id is None:
        if policy == "autonomous":
            raise HandoffError("Autonomous Handoff requires a persistent issue mapping")
        return

    mapping = state.get("issueWorktrees", {}).get(issue_id)
    allocation = state.get("worktreeAllocations", {}).get(f"issue:{issue_id}")
    exact = {
        "issueId": issue_id,
        "workflowId": workflow_id,
        "repositoryId": source.identity.repository_id,
        "repositoryKey": source.repository_key,
        "worktreePath": normalized_source,
        "physicalWorktreeFingerprint": editing_source_fingerprint,
        "status": "active",
    }
    if not isinstance(mapping, dict) or any(
        mapping.get(field) != expected for field, expected in exact.items()
    ):
        raise HandoffError(
            "Handoff issue mapping differs from the effective editing source"
        )
    mapping_operation_id = mapping.get("handoffOperationId")
    if (
        not isinstance(allocation, dict)
        or allocation.get("kind") != "issue"
        or allocation.get("subjectId") != issue_id
        or allocation.get("repositoryId") != source.identity.repository_id
        or allocation.get("repositoryKey") != source.repository_key
        or allocation.get("worktreePath") != normalized_source
        or allocation.get("physicalWorktreeFingerprint") != editing_source_fingerprint
        or allocation.get("branch") != mapping.get("branch")
        or allocation.get("exactSha") != mapping.get("headSha")
        or allocation.get("handoffOperationId") != mapping_operation_id
        or (
            mapping_operation_id is None
            and allocation.get("status") != "completed"
        )
        or (
            mapping_operation_id is not None
            and allocation.get("status") != "transferred"
        )
    ):
        raise HandoffError(
            "Handoff allocation mapping differs from the effective editing source"
        )


def validate_and_consume_handoff_authorization_unlocked(
    *,
    source: "WorkflowManager",
    workflow_id: str,
    editing_source_path: Path,
    editing_source_fingerprint: str,
    destination_fingerprint: str,
    expected_paths: list[str],
    authorization: InternalHandoffAuthorization | None,
) -> str | None:
    """Validate/consume assembled authority while the caller holds allocation.lock."""

    observed = _reservations(source)
    if observed is None:
        if authorization is not None:
            raise HandoffError("Internal Handoff authorization has no matching live reservation")
        return None
    _, reservation_index = observed
    active = _active_reservations(reservation_index)
    if not active:
        if authorization is not None:
            raise HandoffError("Internal Handoff authorization has no matching live reservation")
        return None
    if authorization is None:
        raise HandoffError(
            "A live repository reservation requires assembled Handoff; base-only Handoff is denied"
        )
    if len(active) != 1:
        raise HandoffError("Multiple active repository reservations make Handoff authority ambiguous")
    reservation = active[0]
    if (
        reservation.get("workflowId") != workflow_id
        or reservation.get("repositoryKey") != source.repository_key
    ):
        raise HandoffError(
            "The sole active repository reservation belongs to another workflow or repository"
        )
    if type(authorization) is not InternalHandoffAuthorization:
        raise HandoffError("Handoff authorization must be the internal engine-held type")
    operation_id = _canonical_uuid(authorization.operation_id, "Handoff operation ID")
    _validate_editing_source_mapping_unlocked(
        source=source,
        workflow_id=workflow_id,
        operation_id=operation_id,
        reservation=reservation,
        editing_source_path=editing_source_path,
        editing_source_fingerprint=editing_source_fingerprint,
    )
    if reservation.get("status") != "handoff-pending":
        raise HandoffError("Live reservation is not prepared for assembled Handoff")
    if reservation.get("pendingHandoffOperationId") != operation_id:
        raise HandoffError("Handoff operation does not match the reservation pending barrier")
    reservation_revision = reservation.get("revision")
    if not isinstance(reservation_revision, int) or reservation_revision < 1:
        raise HandoffError("Reservation revision is invalid")

    authorization_root = source.state_paths.directory(
        source.home.repository / "handoff-authorizations"
    )
    authorization_path = source.state_paths.leaf(
        authorization_root / f"{operation_id}.json",
        must_exist=True,
    )
    record = source.state_paths.read_json(authorization_path)
    required = {
        "schemaVersion",
        "revision",
        "operationId",
        "workflowId",
        "repositoryKey",
        "sourceFingerprint",
        "destinationFingerprint",
        "expectedPathDigest",
        "requestHash",
        "reservationId",
        "reservationRevision",
        "nonceSha256",
        "status",
    }
    if set(record) != required or record.get("schemaVersion") != INTERLOCK_VERSION:
        raise HandoffError("Handoff authorization record is malformed")
    if record.get("status") != "prepared" or record.get("revision") != 1:
        raise HandoffError("Handoff authorization is consumed, replayed, or invalid")
    expected_path_digest = "sha256:" + hashlib.sha256(
        "\n".join(sorted(expected_paths, key=str.casefold)).encode("utf-8")
    ).hexdigest()
    bindings = {
        "operationId": operation_id,
        "workflowId": workflow_id,
        "repositoryKey": source.repository_key,
        "sourceFingerprint": editing_source_fingerprint,
        "destinationFingerprint": destination_fingerprint,
        "expectedPathDigest": expected_path_digest,
        "reservationId": reservation.get("reservationId"),
        "reservationRevision": reservation_revision,
    }
    for field, expected in bindings.items():
        if record.get(field) != expected:
            raise HandoffError(f"Handoff authorization {field} binding mismatch")
    expected_request_hash = handoff_request_hash(
        operation_id=operation_id,
        workflow_id=workflow_id,
        repository_key=source.repository_key,
        source_fingerprint=editing_source_fingerprint,
        destination_fingerprint=destination_fingerprint,
        expected_paths=expected_paths,
        reservation_id=reservation["reservationId"],
        reservation_revision=reservation_revision,
    )
    if record.get("requestHash") != expected_request_hash:
        raise HandoffError("Handoff authorization request binding mismatch")
    nonce = authorization.nonce
    if not isinstance(nonce, str) or len(nonce) < 32:
        raise HandoffError("Internal Handoff authorization nonce is invalid")
    nonce_sha256 = "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(str(record.get("nonceSha256")), nonce_sha256):
        raise HandoffError("Internal Handoff authorization nonce mismatch")

    consumed = copy.deepcopy(record)
    consumed["revision"] = 2
    consumed["status"] = "consumed"
    try:
        source.state_paths.write_json(authorization_path, consumed, expected_revision=1)
    except (OSError, ValidationError) as exc:
        raise HandoffError("Handoff authorization could not be consumed atomically") from exc
    return operation_id
