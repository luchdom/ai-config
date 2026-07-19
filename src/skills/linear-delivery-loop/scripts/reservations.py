"""Repository-scoped editing reservations and protected-work reconciliation."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
import re
import secrets
import subprocess
import time
import uuid
from datetime import datetime, timezone
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .store import (
    SupervisorConflictError,
    SupervisorStore,
    SupervisorStoreError,
    assert_public_data,
    sha256_json,
)


class ReservationError(SupervisorStoreError):
    """Reservation authority or protected-work reconciliation was rejected."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_POLICIES = {"autonomous", "semi-autonomous", "manual"}
_ACTIVE = {"live", "handoff-pending"}
_TERMINAL = {"released", "reclaimed"}
_BLOCKING_STATUSES = _ACTIVE | {"expired", "protected"}
_STATUSES = _BLOCKING_STATUSES | _TERMINAL


def _blocking_records(reservations: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return every record that has not reached an explicit safe terminal state."""

    records = reservations.get("reservations")
    if not isinstance(records, Mapping):
        raise ReservationError("Reservation index is malformed and blocks editing")
    blocking: list[Mapping[str, Any]] = []
    for record in records.values():
        if not isinstance(record, Mapping):
            raise ReservationError("Reservation record is malformed and blocks editing")
        status = record.get("status")
        if status not in _STATUSES:
            raise ReservationError("Reservation status is unknown and blocks editing")
        if status not in _TERMINAL:
            blocking.append(record)
    return blocking


def _system_now_ns() -> int:
    return time.time_ns()


def _normalized_path(value: str | Path) -> str:
    return os.path.normcase(
        os.path.realpath(os.path.abspath(os.fspath(value)))
    ).replace("\\", "/")


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        shell=False,
    )


def observe_local_protected_work(
    store: SupervisorStore,
    worktree_path: str | Path,
    *,
    planning_only: bool = False,
) -> dict[str, Any]:
    """Observe local Git facts; request/model prose cannot supply this authority."""

    try:
        observed = store.runtime.observe_repository_identity(worktree_path)
        if observed.repository_id != store.manager.identity.repository_id:
            raise ReservationError("Worktree belongs to another normalized repository")
        repository = Path(observed.repository_root)
        status = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")
        branch_result = _git(repository, "branch", "--show-current")
        head_result = _git(repository, "rev-parse", "HEAD")
        if any(item.returncode for item in (status, branch_result, head_result)):
            raise ReservationError("Git protected-work observation failed")
        branch = branch_result.stdout.strip() or "detached"
        head = head_result.stdout.strip()
        upstream = _git(repository, "rev-parse", "--abbrev-ref", "@{upstream}")
        if upstream.returncode == 0:
            ahead = _git(repository, "rev-list", "--count", "@{upstream}..HEAD")
            if ahead.returncode != 0:
                raise ReservationError("Git upstream comparison failed")
            unpushed = int(ahead.stdout.strip()) > 0
        else:
            # A clean default branch in a local-only repository is not fabricated
            # protected work. Non-default branches without an upstream are.
            unpushed = branch not in {"main", "master", "detached"}
        base = "main" if _git(repository, "show-ref", "--verify", "--quiet", "refs/heads/main").returncode == 0 else "master"
        if branch in {base, "detached"}:
            unmerged = False
        else:
            ancestor = _git(repository, "merge-base", "--is-ancestor", "HEAD", base)
            unmerged = ancestor.returncode != 0
        return {
            "dirty": bool(status.stdout.strip()),
            "branch": branch,
            "headSha": head,
            "unpushed": unpushed,
            "unmerged": unmerged,
            "prOpen": False,
            "prId": None,
            "prState": "not-applicable",
            "accessible": True,
            "ambiguous": False,
            "planningOnly": bool(planning_only),
        }
    except Exception:
        return {
            "dirty": False,
            "branch": "unknown",
            "headSha": "0" * 40,
            "unpushed": False,
            "unmerged": False,
            "prOpen": False,
            "prId": None,
            "prState": "unknown",
            "accessible": False,
            "ambiguous": True,
            "planningOnly": bool(planning_only),
        }


def is_protected(summary: Mapping[str, Any]) -> bool:
    return bool(
        summary.get("dirty")
        or summary.get("unpushed")
        or summary.get("unmerged")
        or summary.get("prOpen")
        or not summary.get("accessible")
        or summary.get("ambiguous")
    )


class ReservationManager:
    DEFAULT_DURATION_NS = 10 * 60 * 1_000_000_000
    OBSERVATION_MAX_AGE_NS = 5 * 60 * 1_000_000_000

    def __init__(
        self,
        manager: Any,
        store: SupervisorStore | None = None,
        *,
        clock: Callable[[], int] | None = None,
        local_observer: Callable[[SupervisorStore, str | Path, bool], dict[str, Any]] | None = None,
        transfer_fault_injector: Callable[[str, str], None] | None = None,
    ):
        self.store = store or SupervisorStore(manager)
        if self.store.manager is not manager:
            raise ReservationError("Reservation manager/store authority differs")
        self.manager = manager
        self.clock = clock or _system_now_ns
        self.local_observer = local_observer
        self.transfer_fault_injector = transfer_fault_injector

    def reserve(
        self,
        *,
        workflow_id: str,
        issue_id: str | None,
        worktree_path: str | Path,
        physical_worktree_fingerprint: str,
        policy: str,
        owner_id: str,
        run_id: str | None,
        expected_state_revision: int,
        expected_reservations_revision: int,
        capability_ref: str | None = None,
        duration_ns: int = DEFAULT_DURATION_NS,
        planning_only: bool = False,
        reservation_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_request_ids(workflow_id, issue_id, owner_id, run_id)
        if policy not in _POLICIES:
            raise ReservationError("Reservation policy is invalid")
        if reservation_id is not None:
            self._safe_id(reservation_id, "reservation ID")
        self._duration(duration_ns)
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected_revisions(
                state,
                reservations,
                expected_state_revision,
                expected_reservations_revision,
            )
            self._barrier(state)
            observed = self.store.runtime.observe_repository_identity(worktree_path)
            if (
                observed.repository_id != self.manager.identity.repository_id
                or observed.physical_worktree_fingerprint != physical_worktree_fingerprint
            ):
                raise ReservationError("Reservation worktree authority is mismatched")
            self._validate_workflow_unlocked(
                workflow_id,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
                worktree_path=observed.repository_root,
            )
            now = self._now()
            existing = _blocking_records(reservations)
            if existing:
                raise SupervisorConflictError(
                    "Repository already has a live or protected editing reservation; "
                    "only the original journaled Reserve request may replay its authority"
                )
            if policy == "autonomous":
                self._validate_current_capability(
                    state,
                    {
                        "runId": run_id,
                        "workflowId": workflow_id,
                        "issueId": issue_id,
                        "repositoryId": self.manager.identity.repository_id,
                        "repositoryKey": self.manager.repository_key,
                        "worktreePath": _normalized_path(observed.repository_root),
                        "physicalWorktreeFingerprint": physical_worktree_fingerprint,
                    },
                    capability_ref,
                )
            summary = self._observe(worktree_path, planning_only)
            reservation_id = reservation_id or str(uuid.uuid4())
            authorization_ref = self._mint_control_authorization(
                reservation_id=reservation_id,
                workflow_id=workflow_id,
                issue_id=issue_id,
                repository_id=self.manager.identity.repository_id,
                repository_key=self.manager.repository_key,
                run_id=run_id,
                reservation_revision=1,
                state_revision=state["revision"],
                physical_worktree_fingerprint=physical_worktree_fingerprint,
                created_at_ns=now,
                expires_at_ns=now + duration_ns,
            )
            record = {
                "reservationId": reservation_id,
                "workflowId": workflow_id,
                "issueId": issue_id,
                "repositoryId": self.manager.identity.repository_id,
                "repositoryKey": self.manager.repository_key,
                "physicalWorktreeFingerprint": physical_worktree_fingerprint,
                "worktreePath": _normalized_path(observed.repository_root),
                "policy": policy,
                "ownerId": owner_id,
                "runId": run_id,
                "status": "live",
                "revision": 1,
                "heartbeatNs": now,
                "expiresAtNs": now + duration_ns,
                "protectedWork": summary,
                "releaseAuthorizationRef": authorization_ref,
                "cleanupAuthorizationRefs": {},
                "pendingHandoffOperationId": None,
            }
            after_reservations = copy.deepcopy(reservations)
            after_reservations["reservations"][reservation_id] = record
            after_reservations["revision"] = reservations["revision"] + 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation="Reserve",
            )
            return copy.deepcopy(record)

    def renew(
        self,
        *,
        reservation_id: str,
        owner_id: str,
        expected_record_revision: int,
        expected_state_revision: int,
        expected_reservations_revision: int,
        control_authorization_ref: str | Path,
        capability_ref: str | None = None,
        duration_ns: int = DEFAULT_DURATION_NS,
    ) -> dict[str, Any]:
        self._safe_id(reservation_id, "reservation ID")
        self._safe_id(owner_id, "owner ID")
        self._duration(duration_ns)
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected_revisions(
                state,
                reservations,
                expected_state_revision,
                expected_reservations_revision,
            )
            self._barrier(state)
            record = self._record_in_statuses(
                reservations,
                reservation_id,
                {"live", "expired", "protected"},
                "Editing reservation is absent or cannot be reauthorized",
            )
            self._require_manager_authority(state, record)
            if record["ownerId"] != owner_id or record["revision"] != expected_record_revision:
                raise SupervisorConflictError("Reservation owner or record revision is stale")
            now = self._now()
            self._validate_control_authorization(
                state,
                record,
                control_authorization_ref,
                now=now,
                allow_expired_lifecycle=True,
            )
            if record["policy"] == "autonomous":
                self._validate_current_capability(
                    state,
                    record,
                    capability_ref,
                    allow_expired_capability=True,
                )
            summary = self._observe(record["worktreePath"], record["protectedWork"]["planningOnly"])
            new_revision = record["revision"] + 1
            new_ref = self._mint_control_authorization(
                reservation_id=reservation_id,
                workflow_id=record["workflowId"],
                issue_id=record["issueId"],
                repository_id=record["repositoryId"],
                repository_key=record["repositoryKey"],
                run_id=record["runId"],
                reservation_revision=new_revision,
                state_revision=state["revision"],
                physical_worktree_fingerprint=record["physicalWorktreeFingerprint"],
                created_at_ns=now,
                expires_at_ns=now + duration_ns,
            )
            after_reservations = copy.deepcopy(reservations)
            updated = after_reservations["reservations"][reservation_id]
            old_ref = updated["releaseAuthorizationRef"]
            updated.update(
                {
                    "revision": new_revision,
                    "heartbeatNs": now,
                    "expiresAtNs": now + duration_ns,
                    "status": "live",
                    "protectedWork": summary,
                    "releaseAuthorizationRef": new_ref,
                }
            )
            after_reservations["revision"] = reservations["revision"] + 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation="RenewReservation",
            )
            self._revoke_authorization(old_ref)
            return copy.deepcopy(updated)

    def authorize_mutation(
        self,
        *,
        reservation_id: str,
        authorization_id: str,
        target_operation_id: str,
        scope: Iterable[str],
        expected_record_revision: int,
        expected_state_revision: int,
        expected_reservations_revision: int,
        control_authorization_ref: str | Path,
        capability_ref: str | None = None,
        duration_ns: int = DEFAULT_DURATION_NS,
    ) -> dict[str, Any]:
        self._safe_id(authorization_id, "authorization ID")
        self._safe_id(target_operation_id, "target operation ID")
        self._duration(duration_ns)
        canonical_scope = self._canonical_mutation_scope(scope)
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected_revisions(
                state,
                reservations,
                expected_state_revision,
                expected_reservations_revision,
            )
            self._barrier(state)
            record = self._active_record(reservations, reservation_id)
            self._require_manager_authority(state, record)
            if record["revision"] != expected_record_revision:
                raise SupervisorConflictError("Reservation revision is stale")
            now = self._now()
            self._validate_control_authorization(
                state, record, control_authorization_ref, now=now
            )
            if record["policy"] == "autonomous":
                self._validate_current_capability(state, record, capability_ref)
            next_record_revision = record["revision"] + 1
            reference, digest = self._create_authorization(
                directory="mutation-authorizations",
                authorization_id=authorization_id,
                kind="mutation",
                binding={
                    "reservationId": reservation_id,
                    "workflowId": record["workflowId"],
                    "issueId": record["issueId"],
                    "repositoryId": record["repositoryId"],
                    "repositoryKey": record["repositoryKey"],
                    "runId": record["runId"],
                    "operationId": target_operation_id,
                    "authorizationOperationId": authorization_id,
                    "stateRevision": state["revision"],
                    "reservationRevision": next_record_revision,
                    "physicalWorktreeFingerprint": record[
                        "physicalWorktreeFingerprint"
                    ],
                    "scope": canonical_scope,
                    "createdAtNs": now,
                    "expiresAtNs": now + duration_ns,
                },
            )
            new_control_ref = self._mint_control_authorization(
                reservation_id=reservation_id,
                workflow_id=record["workflowId"],
                issue_id=record["issueId"],
                repository_id=record["repositoryId"],
                repository_key=record["repositoryKey"],
                run_id=record["runId"],
                reservation_revision=next_record_revision,
                state_revision=state["revision"],
                physical_worktree_fingerprint=record["physicalWorktreeFingerprint"],
                created_at_ns=now,
                expires_at_ns=record["expiresAtNs"],
            )
            after_reservations = copy.deepcopy(reservations)
            updated = after_reservations["reservations"][reservation_id]
            updated["revision"] = next_record_revision
            updated["releaseAuthorizationRef"] = new_control_ref
            after_reservations["revision"] = reservations["revision"] + 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation=f"AuthorizeMutation:{target_operation_id}",
            )
            self._revoke_authorization(control_authorization_ref)
            return {
                "schemaVersion": "1.0",
                "authorizationId": authorization_id,
                "operationId": target_operation_id,
                "reservationId": reservation_id,
                "authorizationRef": reference,
                "authorizationSha256": digest,
                "scope": canonical_scope,
                "reservationRevision": next_record_revision,
                "controlAuthorizationRef": new_control_ref,
                "status": "active",
            }

    def execute_authorized_mutation(
        self,
        *,
        reservation_id: str,
        authorization_ref: str | Path,
        operation_id: str,
        required_scope: Iterable[str],
        expected_record_revision: int,
        expected_state_revision: int,
        expected_reservations_revision: int,
        physical_worktree_fingerprint: str,
        mutation: Callable[
            [Mapping[str, Any], dict[str, Any]], Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        """Validate, execute, and consume one exact mutation grant under the mutex.

        The callback receives a deep copy of the authoritative reservation and
        a mutable next-state copy so contained external mutation and its
        authoritative gate-state transition share one paired commit. A
        crash after external mutation remains protected by the operation
        journal, while the authorization can never be consumed twice in a live
        process or after its authoritative consumed-ID commit.
        """

        self._safe_id(operation_id, "operation ID")
        scope = self._canonical_mutation_scope(required_scope)
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected_revisions(
                state,
                reservations,
                expected_state_revision,
                expected_reservations_revision,
            )
            self._barrier(state)
            record = self._active_record(reservations, reservation_id)
            self._require_manager_authority(state, record)
            if record["revision"] != expected_record_revision:
                raise SupervisorConflictError("Reservation revision is stale")
            authorization = self._resolve_authorization(
                authorization_ref, expected_kind="mutation"
            )
            binding = authorization["binding"]
            expected = {
                "reservationId": reservation_id,
                "workflowId": record["workflowId"],
                "issueId": record["issueId"],
                "repositoryId": record["repositoryId"],
                "repositoryKey": record["repositoryKey"],
                "runId": record["runId"],
                "operationId": operation_id,
                "stateRevision": state["revision"],
                "reservationRevision": record["revision"],
                "physicalWorktreeFingerprint": physical_worktree_fingerprint,
                "scope": scope,
            }
            if any(binding.get(key) != value for key, value in expected.items()):
                raise ReservationError("Mutation authorization binding is forged or stale")
            if physical_worktree_fingerprint != record["physicalWorktreeFingerprint"]:
                raise ReservationError("Mutation worktree authority differs from reservation")
            if self._now() >= binding.get("expiresAtNs", 0):
                raise ReservationError("Mutation authorization is expired")
            authorization_id = authorization["authorizationId"]
            if authorization_id in reservations["consumedAuthorizationIds"]:
                raise ReservationError("Mutation authorization was already consumed")
            after_state = copy.deepcopy(state)
            result = copy.deepcopy(
                dict(mutation(copy.deepcopy(record), after_state))
            )
            assert_public_data(result, location="authorized mutation result")
            if {**after_state, "revision": 0} != {**state, "revision": 0}:
                after_state["revision"] = state["revision"] + 1
            after_reservations = copy.deepcopy(reservations)
            after_reservations["consumedAuthorizationIds"].append(authorization_id)
            after_reservations["revision"] = reservations["revision"] + 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after_state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation=f"AuthorizedMutation:{operation_id}",
            )
            self._consume_authorization(authorization_ref)
            return result

    def execute_cleanup_authorization(
        self,
        *,
        reservation_id: str,
        authorization_ref: str | Path,
        operation_id: str,
        gate_operation_id: str,
        expected_state_revision: int,
        expected_reservations_revision: int,
        mutation: Callable[
            [Mapping[str, Any], Mapping[str, Any], dict[str, Any]],
            Mapping[str, Any],
        ],
    ) -> dict[str, Any]:
        """Consume one post-release, exact-gate cleanup grant atomically."""

        self._safe_id(operation_id, "cleanup operation ID")
        self._safe_id(gate_operation_id, "gate operation ID")
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected_revisions(
                state,
                reservations,
                expected_state_revision,
                expected_reservations_revision,
            )
            if (
                state["lease"] is not None
                or state["handoffPending"] is not None
                or state["recovery"]["status"] != "clean"
            ):
                raise ReservationError("Cleanup refuses lease, Handoff, or recovery authority")
            if _blocking_records(reservations):
                raise ReservationError("Cleanup refuses every non-terminal editing reservation")
            record = reservations["reservations"].get(reservation_id)
            if record is None or record.get("status") != "released":
                raise ReservationError("Cleanup requires its released reservation record")
            current_ref = record["cleanupAuthorizationRefs"].get(gate_operation_id)
            if not isinstance(current_ref, str) or os.path.normcase(
                os.path.realpath(os.fspath(authorization_ref))
            ) != os.path.normcase(os.path.realpath(current_ref)):
                raise ReservationError("Cleanup authorization is not current for this gate")
            authorization = self._resolve_authorization(
                authorization_ref, expected_kind="cleanup"
            )
            gate = state["gateWorktrees"].get(gate_operation_id)
            if not isinstance(gate, dict):
                raise ReservationError("Cleanup gate authority is absent")
            binding = authorization["binding"]
            expected = {
                "reservationId": reservation_id,
                "workflowId": record["workflowId"],
                "repositoryId": record["repositoryId"],
                "repositoryKey": record["repositoryKey"],
                "runId": record["runId"],
                "operationId": operation_id,
                "releasedReservationRevision": record["revision"],
                "stateRevision": state["revision"],
                "reservationsRevision": reservations["revision"],
                "physicalWorktreeFingerprint": record[
                    "physicalWorktreeFingerprint"
                ],
                "gateOperationId": gate_operation_id,
                "gatePath": gate["worktreePath"],
                "gateFingerprint": gate["physicalWorktreeFingerprint"],
                "exactSha": gate["exactSha"],
                "scope": [gate["worktreePath"]],
            }
            if any(binding.get(key) != value for key, value in expected.items()):
                raise ReservationError("Cleanup authorization binding is forged or stale")
            if (
                gate.get("status") != "active"
                or gate.get("operationStatus") != "resolved"
                or gate.get("attestationStatus") != "complete"
                or self._now() >= binding["expiresAtNs"]
            ):
                raise ReservationError("Cleanup gate evidence or authorization is stale")
            authorization_id = authorization["authorizationId"]
            if authorization_id in reservations["consumedAuthorizationIds"]:
                raise ReservationError("Cleanup authorization was already consumed")
            after_state = copy.deepcopy(state)
            result = copy.deepcopy(
                dict(
                    mutation(
                        copy.deepcopy(record),
                        copy.deepcopy(gate),
                        after_state,
                    )
                )
            )
            assert_public_data(result, location="cleanup mutation result")
            updated_gate = after_state["gateWorktrees"].get(gate_operation_id)
            if not isinstance(updated_gate, dict) or updated_gate.get("status") != "cleaned":
                raise ReservationError("Cleanup callback did not prove the exact gate cleaned")
            if {**after_state, "revision": 0} != {**state, "revision": 0}:
                after_state["revision"] = state["revision"] + 1
            after_reservations = copy.deepcopy(reservations)
            updated_record = after_reservations["reservations"][reservation_id]
            prior_remaining = {
                key: value
                for key, value in updated_record["cleanupAuthorizationRefs"].items()
                if key != gate_operation_id
            }
            next_record_revision = record["revision"] + 1
            next_reservations_revision = reservations["revision"] + 1
            rotated: dict[str, str] = {}
            for remaining_gate_id in sorted(prior_remaining):
                remaining_gate = after_state["gateWorktrees"].get(remaining_gate_id)
                if (
                    isinstance(remaining_gate, dict)
                    and remaining_gate.get("status") == "active"
                    and remaining_gate.get("operationStatus") == "resolved"
                    and remaining_gate.get("attestationStatus") == "complete"
                ):
                    rotated[remaining_gate_id] = self._mint_cleanup_authorization(
                        record=updated_record,
                        gate=remaining_gate,
                        released_reservation_revision=next_record_revision,
                        state_revision=after_state["revision"],
                        reservations_revision=next_reservations_revision,
                        created_at_ns=self._now(),
                    )
            updated_record["revision"] = next_record_revision
            updated_record["cleanupAuthorizationRefs"] = rotated
            after_reservations["consumedAuthorizationIds"].append(authorization_id)
            after_reservations["revision"] = next_reservations_revision
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after_state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation=f"Cleanup:{operation_id}",
            )
            self._consume_authorization(authorization_ref)
            for old_ref in prior_remaining.values():
                self._revoke_authorization(old_ref)
            result["cleanupAuthorizationRefs"] = copy.deepcopy(rotated)
            result["reservationRevision"] = next_record_revision
            result["stateRevision"] = after_state["revision"]
            result["reservationsRevision"] = next_reservations_revision
            return result

    def release(
        self,
        *,
        reservation_id: str,
        authorization_ref: str | Path,
        operation_id: str,
        expected_record_revision: int,
        expected_state_revision: int,
        expected_reservations_revision: int,
        capability_ref: str | None = None,
        trusted_observation_ref: str | Path | None = None,
    ) -> dict[str, Any]:
        self._safe_id(operation_id, "operation ID")
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected_revisions(
                state,
                reservations,
                expected_state_revision,
                expected_reservations_revision,
            )
            self._barrier(state)
            record = self._record_in_statuses(
                reservations,
                reservation_id,
                {"live", "protected", "expired"},
                "Editing reservation is absent or cannot be safely released",
            )
            self._require_manager_authority(state, record)
            if record["revision"] != expected_record_revision:
                raise SupervisorConflictError("Reservation revision is stale")
            now = self._now()
            authorization = self._validate_control_authorization(
                state, record, authorization_ref, now=now
            )
            if record["policy"] == "autonomous":
                self._validate_current_capability(state, record, capability_ref)
            summary = self._observe(
                record["worktreePath"], record["protectedWork"]["planningOnly"]
            )
            observation_id: str | None = None
            if record["protectedWork"].get("prId") is not None or summary.get("prId") is not None:
                try:
                    observation = self._validate_trusted_observation(
                        trusted_observation_ref,
                        record=record,
                        local_summary=summary,
                        consumed=reservations["consumedObservationIds"],
                    )
                    observation_id = observation["observationId"]
                    summary["prId"] = observation["pullRequest"]["id"]
                    summary["prState"] = observation["pullRequest"]["state"]
                    summary["prOpen"] = observation["pullRequest"]["state"] == "open"
                    if observation["pullRequest"]["state"] == "merged":
                        # Exact provider evidence binds the merged PR to this
                        # local HEAD, so squash/rebase integration need not make
                        # the feature commit an ancestor of main.
                        summary["unpushed"] = False
                        summary["unmerged"] = False
                except ReservationError:
                    summary["ambiguous"] = True
            if is_protected(summary):
                if record.get("protectedWork") == summary:
                    raise ReservationError("Protected or ambiguous work cannot be released")
                after_reservations = copy.deepcopy(reservations)
                protected = after_reservations["reservations"][reservation_id]
                protected["protectedWork"] = summary
                # A refused Release must not strand the reservation by making
                # its current opaque control authorization stale without a
                # successful response that can return a rotated reference.
                # The collection revision still advances for CAS/recovery,
                # while the record revision and control authority remain usable
                # for a later attended retry after the work is reconciled.
                after_reservations["revision"] += 1
                self.store.commit_pair_unlocked(
                    before_state=state,
                    after_state=state,
                    before_reservations=reservations,
                    after_reservations=after_reservations,
                    operation="Release:protected",
                )
                raise ReservationError("Protected or ambiguous work cannot be released")
            authorization_id = authorization["authorizationId"]
            if authorization_id in reservations["consumedAuthorizationIds"]:
                raise ReservationError("Release authorization was already consumed")
            after_state = copy.deepcopy(state)
            revoked_capabilities: list[tuple[str, str, str]] = []
            lease = state.get("lease")
            if lease is not None:
                if (
                    record["policy"] != "autonomous"
                    or lease.get("runId") != record.get("runId")
                    or lease.get("status") != "live"
                ):
                    raise ReservationError("Release refuses an unrelated live lease")
                revoked_capabilities.append(
                    (lease["capabilityRef"], lease["capabilitySha256"], "lease")
                )
                after_state["lease"] = None
                for capability in after_state["capabilities"].values():
                    if (
                        capability.get("runId") == record["runId"]
                        and capability.get("status") == "issued"
                    ):
                        capability["status"] = "revoked"
                        revoked_capabilities.append(
                            (
                                capability["capabilityRef"],
                                capability["capabilitySha256"],
                                capability["kind"],
                            )
                        )
                after_state["revision"] = state["revision"] + 1
            post_state_revision = after_state["revision"]
            post_record_revision = record["revision"] + 1
            post_reservations_revision = reservations["revision"] + 1
            cleanup_refs: dict[str, str] = {}
            for gate_operation_id, gate in sorted(state["gateWorktrees"].items()):
                if (
                    gate.get("status") == "active"
                    and gate.get("operationStatus") == "resolved"
                    and gate.get("attestationStatus") == "complete"
                ):
                    cleanup_refs[gate_operation_id] = self._mint_cleanup_authorization(
                        record=record,
                        gate=gate,
                        released_reservation_revision=post_record_revision,
                        state_revision=post_state_revision,
                        reservations_revision=post_reservations_revision,
                        created_at_ns=now,
                    )
            after_reservations = copy.deepcopy(reservations)
            updated = after_reservations["reservations"][reservation_id]
            updated.update(
                {
                    "status": "released",
                    "revision": post_record_revision,
                    "protectedWork": summary,
                    "releaseAuthorizationRef": None,
                    "cleanupAuthorizationRefs": cleanup_refs,
                    "pendingHandoffOperationId": None,
                }
            )
            after_reservations["consumedAuthorizationIds"].append(authorization_id)
            if observation_id is not None:
                if observation_id in after_reservations["consumedObservationIds"]:
                    raise ReservationError("Trusted external observation was replayed")
                after_reservations["consumedObservationIds"].append(observation_id)
            after_reservations["revision"] = reservations["revision"] + 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after_state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation="Release",
            )
            self._consume_authorization(authorization_ref)
            for reference, digest, kind in revoked_capabilities:
                self._revoke_capability_sidecar(reference, digest, kind)
            return {
                "status": "released",
                "reservationId": reservation_id,
                "reservationRevision": updated["revision"],
                "stateRevision": post_state_revision,
                "reservationsRevision": post_reservations_revision,
                "cleanupAuthorizationRefs": copy.deepcopy(cleanup_refs),
            }

    def record_trusted_observation(
        self,
        *,
        adapter_id: str,
        adapter_version: str,
        operation_id: str,
        repository_id: str,
        head_sha: str,
        pr_id: str | None,
        pr_state: str | None,
        branch: str = "main",
        adapter_kind: str = "fixture",
        ttl_ns: int = OBSERVATION_MAX_AGE_NS,
    ) -> dict[str, Any]:
        """Fixture-adapter boundary; live adapters replace this issuer in SAAS-47/48."""

        for value, label in (
            (adapter_id, "adapter ID"),
            (adapter_version, "adapter version"),
            (operation_id, "operation ID"),
        ):
            self._safe_id(value, label)
        self._duration(ttl_ns)
        if repository_id != self.manager.identity.repository_id:
            raise ReservationError("Trusted observation repository differs")
        now = self._now()
        observation_id = str(uuid.uuid4())
        path = self.store.guard.leaf(
            self.store.directories["final-attestations"] / f"{observation_id}.json"
        )
        pull_request = (
            None
            if pr_id is None
            else {
                "provider": "github",
                "id": pr_id,
                "state": pr_state,
                "headSha": head_sha,
            }
        )
        body = {
            "schemaVersion": "1.0",
            "observationId": observation_id,
            "observationRef": os.fspath(path),
            "adapterId": adapter_id,
            "adapterVersion": adapter_version,
            "adapterKind": adapter_kind,
            "operationId": operation_id,
            "repositoryId": repository_id,
            "repositoryKey": self.manager.repository_key,
            "stateHome": os.fspath(self.store.root),
            "normalizedCommonDir": os.path.normcase(
                os.path.realpath(self.manager.identity.common_dir)
            ),
            "branch": branch,
            "headSha": head_sha,
            "pullRequest": pull_request,
            "observedAt": self._iso_time(now),
            "expiresAt": self._iso_time(now + ttl_ns),
        }
        body["journalHash"] = "sha256:" + sha256_json(body)
        body["attestationHash"] = "sha256:" + hashlib.sha256(
            (adapter_id + "\0" + body["journalHash"]).encode("utf-8")
        ).hexdigest()
        body["consumedAt"] = None
        body["status"] = "issued"
        assert_public_data(body, location="trusted observation")
        self.store.guard.write_json(path, body)
        return copy.deepcopy(body)

    def reclaim_expired(
        self,
        *,
        reservation_id: str,
        expected_state_revision: int,
        expected_reservations_revision: int,
        ignore_operation_id: str | None = None,
    ) -> dict[str, Any]:
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected_revisions(
                state,
                reservations,
                expected_state_revision,
                expected_reservations_revision,
            )
            if state["handoffPending"] is not None:
                raise ReservationError("Handoff pending barrier blocks reservation reclaim")
            if (
                state["recovery"]["status"] != "clean"
                and not (
                    state["recovery"]["status"] == "required"
                    and state["recovery"]["reason"] == "expired-lease"
                )
            ):
                raise ReservationError("Protected recovery state blocks reservation reclaim")
            record = self._record_in_statuses(
                reservations,
                reservation_id,
                _BLOCKING_STATUSES,
                "Editing reservation is absent or already terminal",
            )
            self._require_manager_authority(state, record)
            if self._now() < record["expiresAtNs"]:
                raise ReservationError("Live reservation cannot be reclaimed")
            if not record["protectedWork"].get("planningOnly", False):
                raise ReservationError(
                    "Expired implementation reservations remain protected until explicit release"
                )
            lease = state.get("lease")
            if isinstance(lease, dict) and lease.get("status") == "live":
                raise ReservationError("A live autonomous lease blocks reservation reclaim")
            current = state.get("currentWork")
            if isinstance(current, dict) and (
                current.get("workflowId") == record["workflowId"]
                or current.get("issueId") == record["issueId"]
            ):
                raise ReservationError("Registered current work blocks reservation reclaim")
            summary = self._observe(record["worktreePath"], True)
            registry = self.manager.registry.load_unlocked()
            entry = registry["workflows"].get(record["workflowId"])
            issue_mapping = (
                state["issueWorktrees"].get(record["issueId"])
                if record["issueId"] is not None
                else None
            )
            if (
                is_protected(summary)
                or entry is None
                or entry.get("physicalWorktreeFingerprint")
                != record["physicalWorktreeFingerprint"]
                or os.path.normcase(
                    os.path.realpath(Path(entry["artifactPath"]).parent.parent)
                )
                != os.path.normcase(os.path.realpath(record["worktreePath"]))
                or (
                    issue_mapping is not None
                    and (
                        issue_mapping.get("status") != "active"
                        or issue_mapping.get("workflowId")
                        not in {None, record["workflowId"]}
                        or issue_mapping.get("physicalWorktreeFingerprint")
                        != record["physicalWorktreeFingerprint"]
                    )
                )
                or state["handoffPending"] is not None
                or self._has_pending_operation_evidence(
                    ignore_operation_id=ignore_operation_id
                )
            ):
                raise ReservationError("Expired reservation remains protected or ambiguous")
            after_reservations = copy.deepcopy(reservations)
            updated = after_reservations["reservations"][reservation_id]
            updated.update(
                {
                    "status": "reclaimed",
                    "revision": record["revision"] + 1,
                    "protectedWork": summary,
                }
            )
            after_reservations["revision"] += 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation="ReclaimReservation",
            )
            self._revoke_authorization(record["releaseAuthorizationRef"])
            return copy.deepcopy(updated)

    def prepare_handoff_authorization(
        self,
        *,
        reservation_id: str,
        operation_id: str,
        workflow_id: str,
        source_fingerprint: str,
        destination_fingerprint: str,
        expected_paths: Iterable[str],
        request: Mapping[str, Any],
        control_authorization_ref: str | Path,
        capability_ref: str | None = None,
        expected_reservation_revision: int | None = None,
        expected_state_revision: int | None = None,
        expected_reservations_revision: int | None = None,
    ) -> dict[str, Any]:
        self._safe_id(operation_id, "Handoff operation ID")
        paths = self._canonical_scope(expected_paths)
        request_value = copy.deepcopy(dict(request))
        assert_public_data(request_value, location="Handoff request")
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            if expected_state_revision is not None and expected_reservations_revision is not None:
                self._expected_revisions(
                    state,
                    reservations,
                    expected_state_revision,
                    expected_reservations_revision,
                )
            self._barrier(state)
            record = self._active_record(reservations, reservation_id)
            self._require_manager_authority(state, record)
            source_path = request_value.get("sourcePath")
            destination_path = request_value.get("destinationPath")
            try:
                observed_source = self.store.runtime.observe_repository_identity(source_path)
                observed_destination = self.store.runtime.observe_repository_identity(
                    destination_path
                )
            except Exception as exc:
                raise ReservationError(
                    "Handoff source or destination worktree identity is unavailable"
                ) from exc
            if record["workflowId"] != workflow_id or record[
                "physicalWorktreeFingerprint"
            ] != source_fingerprint:
                raise ReservationError("Handoff reservation source binding is mismatched")
            if (
                observed_source.repository_id != self.manager.identity.repository_id
                or observed_source.physical_worktree_fingerprint != source_fingerprint
                or _normalized_path(observed_source.repository_root)
                != record["worktreePath"]
                or observed_destination.repository_id
                != self.manager.identity.repository_id
                or observed_destination.physical_worktree_fingerprint
                != destination_fingerprint
            ):
                raise ReservationError(
                    "Handoff proposed paths differ from their reservation/repository bindings"
                )
            self._validate_handoff_issue_authority(state, record)
            if record["policy"] == "autonomous":
                issue_root = self.store.guard.directory(
                    self.store.root / "worktrees", create=True
                )
                canonical_destination = self.store.guard.directory(
                    observed_destination.repository_root
                )
                if canonical_destination.parent != issue_root:
                    raise ReservationError(
                        "Autonomous Handoff destination must be a direct contained issue worktree"
                    )
            if (
                expected_reservation_revision is not None
                and record["revision"] != expected_reservation_revision
            ):
                raise SupervisorConflictError("Handoff reservation revision is stale")
            now = self._now()
            self._validate_control_authorization(
                state, record, control_authorization_ref, now=now
            )
            if record["policy"] == "autonomous":
                self._validate_current_capability(state, record, capability_ref)
            auth_dir = self.store.directories["handoff-authorizations"]
            auth_path = self.store.guard.leaf(auth_dir / f"{operation_id}.json")
            sidecar_path = self.store.guard.leaf(
                auth_dir / f"{operation_id}.capability.json"
            )
            if auth_path.exists() or sidecar_path.exists():
                raise ReservationError("Handoff operation ID was already allocated")
            nonce = secrets.token_urlsafe(48)
            digest = "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
            next_record_revision = record["revision"] + 1
            expected_path_digest = "sha256:" + hashlib.sha256(
                "\n".join(paths).encode("utf-8")
            ).hexdigest()
            interlock = importlib.import_module(
                f"{self.store.runtime.package.__name__}.reservation_interlock"
            )
            request_hash = interlock.handoff_request_hash(
                operation_id=operation_id,
                workflow_id=workflow_id,
                repository_key=self.manager.repository_key,
                source_fingerprint=source_fingerprint,
                destination_fingerprint=destination_fingerprint,
                expected_paths=paths,
                reservation_id=reservation_id,
                reservation_revision=next_record_revision,
            )
            authorization = {
                "schemaVersion": "1.0",
                "revision": 1,
                "operationId": operation_id,
                "workflowId": workflow_id,
                "repositoryKey": self.manager.repository_key,
                "sourceFingerprint": source_fingerprint,
                "destinationFingerprint": destination_fingerprint,
                "expectedPathDigest": expected_path_digest,
                "requestHash": request_hash,
                "reservationId": reservation_id,
                "reservationRevision": next_record_revision,
                "nonceSha256": digest,
                "status": "prepared",
            }
            self.store.guard.write_json(auth_path, authorization)
            self.store.guard.write_json(
                sidecar_path,
                {
                    "schemaVersion": "1.0",
                    "operationId": operation_id,
                    "nonce": nonce,
                    "nonceSha256": digest,
                    "status": "active",
                },
            )
            after_state = copy.deepcopy(state)
            after_reservations = copy.deepcopy(reservations)
            after_state["handoffPending"] = {
                "operationId": operation_id,
                "reservationId": reservation_id,
                "workflowId": workflow_id,
                "status": "prepared",
            }
            after_state["revision"] += 1
            pending = after_reservations["reservations"][reservation_id]
            pending.update(
                {
                    "status": "handoff-pending",
                    "revision": next_record_revision,
                    "releaseAuthorizationRef": None,
                    "pendingHandoffOperationId": operation_id,
                }
            )
            after_reservations["revision"] += 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after_state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation=f"Handoff:{operation_id}:phase-a",
            )
            self._revoke_authorization(control_authorization_ref)
            return copy.deepcopy(authorization)

    def resolve_handoff_authorization(self, operation_id: str) -> str:
        """Resolve the raw nonce internally for assembled Phase B only."""

        self._safe_id(operation_id, "Handoff operation ID")
        with self.store.mutex():
            auth_path = self.store.guard.leaf(
                self.store.directories["handoff-authorizations"] / f"{operation_id}.json",
                must_exist=True,
            )
            sidecar_path = self.store.guard.leaf(
                self.store.directories["handoff-authorizations"]
                / f"{operation_id}.capability.json",
                must_exist=True,
            )
            authorization = self.store.guard.read_json(auth_path)
            sidecar = self.store.guard.read_json(sidecar_path)
            nonce = sidecar.get("nonce")
            if (
                authorization.get("status") != "prepared"
                or sidecar.get("status") != "active"
                or authorization.get("nonceSha256") != sidecar.get("nonceSha256")
                or not isinstance(nonce, str)
                or "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
                != authorization.get("nonceSha256")
            ):
                raise ReservationError("Internal Handoff authorization is revoked or tampered")
            return nonce

    def finalize_handoff(
        self,
        *,
        operation_id: str,
        outcome: str,
        destination_fingerprint: str | None = None,
        destination_worktree_path: str | Path | None = None,
    ) -> dict[str, Any]:
        if outcome not in {"succeeded", "proven-failure", "ambiguous"}:
            raise ReservationError("Handoff outcome classification is invalid")
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            pending = state["handoffPending"]
            if pending is None or pending["operationId"] != operation_id:
                raise ReservationError("Handoff pending barrier does not match operation")
            reservation_id = pending["reservationId"]
            record = reservations["reservations"].get(reservation_id)
            if (
                record is None
                or record["status"] != "handoff-pending"
                or record["pendingHandoffOperationId"] != operation_id
            ):
                raise ReservationError("Handoff reservation pending evidence is inconsistent")
            self._validate_handoff_issue_authority(state, record)
            auth_path = self.store.guard.leaf(
                self.store.directories["handoff-authorizations"] / f"{operation_id}.json",
                must_exist=True,
            )
            authorization = self.store.guard.read_json(auth_path)
            if authorization["reservationId"] != reservation_id:
                raise ReservationError("Handoff authorization reservation is mismatched")
            if outcome == "ambiguous":
                return {
                    "status": "protected",
                    "operationId": operation_id,
                    "reservationId": reservation_id,
                }
            after_state = copy.deepcopy(state)
            after_reservations = copy.deepcopy(reservations)
            updated = after_reservations["reservations"][reservation_id]
            if outcome == "succeeded":
                if destination_fingerprint != authorization["destinationFingerprint"]:
                    raise ReservationError("Handoff destination fingerprint is mismatched")
                if destination_worktree_path is None:
                    raise ReservationError("Successful Handoff requires destination worktree path")
                observed = self.store.runtime.observe_repository_identity(
                    destination_worktree_path
                )
                if (
                    observed.repository_id != self.manager.identity.repository_id
                    or observed.physical_worktree_fingerprint != destination_fingerprint
                ):
                    raise ReservationError("Handoff destination worktree authority differs")
                updated["worktreePath"] = _normalized_path(observed.repository_root)
                updated["physicalWorktreeFingerprint"] = destination_fingerprint
                updated["status"] = "live"
                destination_branch_result = _git(
                    Path(observed.repository_root), "branch", "--show-current"
                )
                destination_head_result = _git(
                    Path(observed.repository_root), "rev-parse", "HEAD"
                )
                destination_branch = destination_branch_result.stdout.strip()
                destination_head = destination_head_result.stdout.strip()
                if (
                    destination_branch_result.returncode != 0
                    or destination_head_result.returncode != 0
                    or not destination_branch
                    or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", destination_head)
                ):
                    raise ReservationError(
                        "Handoff destination branch/HEAD evidence is unavailable"
                    )
                after_revision = state["revision"] + 1
                self._transfer_fault("before-capability-transfer", operation_id)
                if after_state["currentWork"] is not None:
                    after_state["currentWork"][
                        "physicalWorktreeFingerprint"
                    ] = destination_fingerprint
                    after_state["currentWork"]["worktreePath"] = updated["worktreePath"]
                issue_id = updated.get("issueId")
                if issue_id is not None:
                    mapping = after_state["issueWorktrees"][issue_id]
                    mapping.update(
                        {
                            "worktreePath": updated["worktreePath"],
                            "physicalWorktreeFingerprint": destination_fingerprint,
                            "branch": destination_branch,
                            "headSha": destination_head,
                            "handoffOperationId": operation_id,
                        }
                    )
                    allocation = after_state["worktreeAllocations"][f"issue:{issue_id}"]
                    allocation.update(
                        {
                            "worktreePath": updated["worktreePath"],
                            "physicalWorktreeFingerprint": destination_fingerprint,
                            "branch": destination_branch,
                            "exactSha": destination_head,
                            "handoffOperationId": operation_id,
                            "status": "transferred",
                        }
                    )
                # The run lease belongs to the scheduled controller checkout,
                # not to the persistent editing target. Handoff moves current
                # work and prepared issue capabilities only; the controller
                # lease remains bound to its original physical worktree.
                for capability_id, capability in after_state["capabilities"].items():
                    if capability["status"] != "issued":
                        continue
                    if (
                        capability.get("runId") != updated.get("runId")
                        or capability.get("workflowId") != updated.get("workflowId")
                        or capability.get("issueId") != updated.get("issueId")
                    ):
                        raise ReservationError(
                            "Handoff found issued capability outside the selected work authority"
                        )
                    source_capability_binding = (
                        capability["physicalWorktreeFingerprint"],
                        capability["worktreePath"],
                        capability["stateRevision"],
                    )
                    self._transfer_capability_sidecar(
                        capability["capabilityRef"],
                        source_fingerprint=authorization["sourceFingerprint"],
                        destination_fingerprint=destination_fingerprint,
                    )
                    self._transfer_fault("after-capability-sidecar", operation_id)
                    capability["physicalWorktreeFingerprint"] = destination_fingerprint
                    capability["worktreePath"] = updated["worktreePath"]
                    capability["stateRevision"] = after_revision
                    prepared_path = self.store.guard.leaf(
                        Path(capability["capabilityRef"]).parent
                        / f"{capability_id}.prepared-iteration.json",
                        must_exist=True,
                    )
                    prepared = self.store.guard.read_json(prepared_path)
                    prepared_binding = (
                        prepared.get("physicalWorktreeFingerprint"),
                        prepared.get("worktreePath"),
                        prepared.get("stateRevision"),
                    )
                    source_binding = source_capability_binding
                    destination_binding = (
                        destination_fingerprint,
                        updated["worktreePath"],
                        after_revision,
                    )
                    if prepared_binding == source_binding:
                        prepared["physicalWorktreeFingerprint"] = destination_fingerprint
                        prepared["worktreePath"] = updated["worktreePath"]
                        prepared["stateRevision"] = after_revision
                        self.store.guard.write_json(prepared_path, prepared)
                    elif prepared_binding != destination_binding:
                        raise ReservationError(
                            "Prepared capability transfer has an ambiguous third binding"
                        )
                    self._transfer_fault("after-prepared-transfer", operation_id)
                self._transfer_fault("after-capability-transfer", operation_id)
                final_status = "transferred"
            else:
                updated["status"] = "live"
                final_status = "restored"
            now = self._now()
            final_record_revision = updated["revision"] + 1
            final_state_revision = state["revision"] + 1
            if after_state["lease"] is not None:
                after_state["lease"]["revision"] = final_state_revision
            for capability_id, capability in after_state["capabilities"].items():
                if capability["status"] != "issued":
                    continue
                capability["stateRevision"] = final_state_revision
                prepared_path = self.store.guard.leaf(
                    Path(capability["capabilityRef"]).parent
                    / f"{capability_id}.prepared-iteration.json",
                    must_exist=True,
                )
                prepared = self.store.guard.read_json(prepared_path)
                prepared["stateRevision"] = final_state_revision
                self.store.guard.write_json(prepared_path, prepared)
            control_ref = self._mint_control_authorization(
                reservation_id=reservation_id,
                workflow_id=updated["workflowId"],
                issue_id=updated["issueId"],
                repository_id=updated["repositoryId"],
                repository_key=updated["repositoryKey"],
                run_id=updated["runId"],
                reservation_revision=final_record_revision,
                state_revision=final_state_revision,
                physical_worktree_fingerprint=updated[
                    "physicalWorktreeFingerprint"
                ],
                created_at_ns=now,
                expires_at_ns=now + self.DEFAULT_DURATION_NS,
            )
            updated["revision"] = final_record_revision
            updated["heartbeatNs"] = now
            updated["expiresAtNs"] = now + self.DEFAULT_DURATION_NS
            updated["releaseAuthorizationRef"] = control_ref
            updated["pendingHandoffOperationId"] = None
            after_state["handoffPending"] = None
            after_state["revision"] += 1
            after_reservations["revision"] += 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after_state,
                before_reservations=reservations,
                after_reservations=after_reservations,
                operation=f"Handoff:{operation_id}:phase-c:{outcome}",
            )
            authorization["status"] = "consumed" if outcome == "succeeded" else "revoked"
            authorization["revision"] += 1
            self.store.guard.write_json(auth_path, authorization)
            sidecar = self.store.guard.leaf(
                self.store.directories["handoff-authorizations"]
                / f"{operation_id}.capability.json",
                must_exist=True,
            )
            sidecar_value = self.store.guard.read_json(sidecar)
            self.store.guard.write_json(
                sidecar,
                {
                    "schemaVersion": "1.0",
                    "operationId": operation_id,
                    "nonceSha256": sidecar_value["nonceSha256"],
                    "status": "consumed" if outcome == "succeeded" else "revoked",
                },
            )
            return {
                "status": final_status,
                "operationId": operation_id,
                "reservationId": reservation_id,
                "controlAuthorizationRef": control_ref,
                "reservationRevision": final_record_revision,
            }

    def recover_handoff(
        self,
        *,
        operation_id: str,
        proven_outcome: str,
        destination_fingerprint: str | None = None,
        destination_worktree_path: str | Path | None = None,
    ) -> dict[str, Any]:
        return self.finalize_handoff(
            operation_id=operation_id,
            outcome=proven_outcome,
            destination_fingerprint=destination_fingerprint,
            destination_worktree_path=destination_worktree_path,
        )

    def _observe(self, worktree_path: str | Path, planning_only: bool) -> dict[str, Any]:
        if self.local_observer is None:
            return observe_local_protected_work(
                self.store, worktree_path, planning_only=planning_only
            )
        value = self.local_observer(self.store, worktree_path, planning_only)
        required = {
            "dirty",
            "branch",
            "headSha",
            "unpushed",
            "unmerged",
            "prOpen",
            "prId",
            "prState",
            "accessible",
            "ambiguous",
            "planningOnly",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise ReservationError("Local protected-work observer returned an invalid shape")
        assert_public_data(value, location="protected-work observation")
        return copy.deepcopy(value)

    def _transfer_capability_sidecar(
        self,
        reference: str | Path,
        *,
        source_fingerprint: str,
        destination_fingerprint: str,
    ) -> None:
        path = self.store.guard.leaf(reference, must_exist=True)
        value = self.store.guard.read_json(path)
        if value.get("status") != "active" or not isinstance(value.get("nonce"), str):
            raise ReservationError("Live capability cannot be transferred safely")
        observed = value.get("physicalWorktreeFingerprint")
        if observed == destination_fingerprint:
            return
        if observed != source_fingerprint:
            raise ReservationError("Live capability has an ambiguous third worktree binding")
        value["physicalWorktreeFingerprint"] = destination_fingerprint
        self.store.guard.write_json(path, value)

    def _revoke_capability_sidecar(
        self, reference: str | Path, digest: str, kind: str
    ) -> None:
        path = self.store.guard.leaf(reference, must_exist=True)
        value = self.store.guard.read_json(path)
        if value.get("nonceSha256") != digest or value.get("kind") != kind:
            raise ReservationError("Capability sidecar cannot be safely revoked")
        if value.get("status") == "revoked":
            return
        nonce = value.get("nonce")
        if (
            value.get("status") != "active"
            or not isinstance(nonce, str)
            or "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
            != digest
        ):
            raise ReservationError("Capability sidecar cannot be safely revoked")
        self.store.guard.write_json(
            path,
            {
                "schemaVersion": "1.0",
                "capabilityId": value["capabilityId"],
                "kind": kind,
                "nonceSha256": digest,
                "physicalWorktreeFingerprint": value.get(
                    "physicalWorktreeFingerprint"
                ),
                "status": "revoked",
            },
        )

    def _transfer_fault(self, stage: str, operation_id: str) -> None:
        if self.transfer_fault_injector is not None:
            self.transfer_fault_injector(stage, operation_id)

    def _create_authorization(
        self,
        *,
        directory: str,
        authorization_id: str,
        kind: str,
        binding: Mapping[str, Any],
    ) -> tuple[str, str]:
        self._safe_id(authorization_id, "authorization ID")
        root = self.store.directories[directory]
        record_path = self.store.guard.leaf(root / f"{authorization_id}.json")
        sidecar_path = self.store.guard.leaf(
            root / f"{authorization_id}.capability.json"
        )
        if record_path.exists() or sidecar_path.exists():
            raise ReservationError("Authorization ID was already allocated")
        nonce = secrets.token_urlsafe(48)
        digest = "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        binding_value = copy.deepcopy(dict(binding))
        assert_public_data(binding_value, location="authorization binding")
        if kind == "release":
            record = {
                "schemaVersion": "1.0",
                "authorizationId": authorization_id,
                "authorizationRef": os.fspath(record_path),
                "operationId": binding_value["operationId"],
                "reservationId": binding_value["reservationId"],
                "workflowId": binding_value["workflowId"],
                "issueId": binding_value["issueId"],
                "runId": binding_value["runId"],
                "repositoryId": binding_value["repositoryId"],
                "repositoryKey": binding_value["repositoryKey"],
                "stateHome": os.fspath(self.store.root),
                "physicalWorktreeFingerprint": binding_value[
                    "physicalWorktreeFingerprint"
                ],
                "scope": binding_value["scope"],
                "stateRevision": binding_value["stateRevision"],
                "reservationRevision": binding_value["reservationRevision"],
                "nonceHash": digest,
                "createdAt": self._iso_time(binding_value["createdAtNs"]),
                "expiresAt": self._iso_time(binding_value["expiresAtNs"]),
                "consumedAt": None,
                "status": "issued",
            }
        else:
            record = {
                "schemaVersion": "1.0",
                "authorizationId": authorization_id,
                "kind": kind,
                "binding": binding_value,
                "nonceSha256": digest,
                "status": "active",
            }
        self.store.guard.write_json(record_path, record)
        self.store.guard.write_json(
            sidecar_path,
            {
                "schemaVersion": "1.0",
                "authorizationId": authorization_id,
                "kind": kind,
                "nonce": nonce,
                "nonceSha256": digest,
                "status": "active",
            },
        )
        return os.fspath(record_path), digest

    def _mint_control_authorization(
        self,
        *,
        reservation_id: str,
        workflow_id: str,
        issue_id: str | None,
        repository_id: str,
        repository_key: str,
        run_id: str | None,
        reservation_revision: int,
        state_revision: int,
        physical_worktree_fingerprint: str,
        created_at_ns: int,
        expires_at_ns: int,
    ) -> str:
        authorization_id = str(uuid.uuid4())
        reference, _ = self._create_authorization(
            directory="reservation-authorizations",
            authorization_id=authorization_id,
            kind="release",
            binding={
                "reservationId": reservation_id,
                "workflowId": workflow_id,
                "issueId": issue_id,
                "repositoryId": repository_id,
                "repositoryKey": repository_key,
                "runId": run_id,
                "operationId": authorization_id,
                "reservationRevision": reservation_revision,
                "stateRevision": state_revision,
                "physicalWorktreeFingerprint": physical_worktree_fingerprint,
                "scope": "ReservationControl",
                "createdAtNs": created_at_ns,
                "expiresAtNs": expires_at_ns,
            },
        )
        return reference

    def _mint_cleanup_authorization(
        self,
        *,
        record: Mapping[str, Any],
        gate: Mapping[str, Any],
        released_reservation_revision: int,
        state_revision: int,
        reservations_revision: int,
        created_at_ns: int,
    ) -> str:
        authorization_id = str(uuid.uuid4())
        reference, _ = self._create_authorization(
            directory="mutation-authorizations",
            authorization_id=authorization_id,
            kind="cleanup",
            binding={
                "reservationId": record["reservationId"],
                "workflowId": record["workflowId"],
                "repositoryId": record["repositoryId"],
                "repositoryKey": record["repositoryKey"],
                "runId": record["runId"],
                "operationId": authorization_id,
                "releasedReservationRevision": released_reservation_revision,
                "stateRevision": state_revision,
                "reservationsRevision": reservations_revision,
                "physicalWorktreeFingerprint": record[
                    "physicalWorktreeFingerprint"
                ],
                "gateOperationId": gate["operationId"],
                "gatePath": gate["worktreePath"],
                "gateFingerprint": gate["physicalWorktreeFingerprint"],
                "exactSha": gate["exactSha"],
                "scope": [gate["worktreePath"]],
                "createdAtNs": created_at_ns,
                "expiresAtNs": created_at_ns + self.DEFAULT_DURATION_NS,
            },
        )
        return reference

    def _validate_control_authorization(
        self,
        state: Mapping[str, Any],
        record: Mapping[str, Any],
        reference: str | Path,
        *,
        now: int,
        allow_expired_lifecycle: bool = False,
    ) -> dict[str, Any]:
        current = record.get("releaseAuthorizationRef")
        if not isinstance(current, str) or os.path.normcase(
            os.path.realpath(os.fspath(reference))
        ) != os.path.normcase(os.path.realpath(current)):
            raise ReservationError("Reservation control authorization is not current")
        authorization = self._resolve_authorization(
            reference, expected_kind="release"
        )
        binding = authorization["binding"]
        expected = {
            "reservationId": record["reservationId"],
            "workflowId": record["workflowId"],
            "issueId": record["issueId"],
            "repositoryId": record["repositoryId"],
            "repositoryKey": record["repositoryKey"],
            "runId": record["runId"],
            "reservationRevision": record["revision"],
            "physicalWorktreeFingerprint": record[
                "physicalWorktreeFingerprint"
            ],
            "scope": "ReservationControl",
        }
        if any(binding.get(key) != value for key, value in expected.items()):
            raise ReservationError("Reservation control binding is forged or stale")
        if binding.get("stateRevision", 0) > state["revision"]:
            raise ReservationError("Reservation control state provenance is impossible")
        if (
            not allow_expired_lifecycle
            and (now >= binding["expiresAtNs"] or now >= record["expiresAtNs"])
        ):
            raise ReservationError("Reservation control authorization is expired")
        return authorization

    def _resolve_authorization(
        self, reference: str | Path, *, expected_kind: str
    ) -> dict[str, Any]:
        record_path = self.store.guard.leaf(reference, must_exist=True)
        if expected_kind not in {"release", "mutation", "cleanup"}:
            raise ReservationError("Authorization kind is not supported")
        expected_root = self.store.directories[
            "reservation-authorizations"
            if expected_kind == "release"
            else "mutation-authorizations"
        ]
        if record_path.parent != expected_root:
            raise ReservationError("Authorization reference is outside its engine-owned namespace")
        record = self.store.guard.read_json(record_path)
        authorization_id = record.get("authorizationId")
        self._safe_id(authorization_id, "authorization ID")
        sidecar_path = self.store.guard.leaf(
            record_path.parent / f"{authorization_id}.capability.json", must_exist=True
        )
        sidecar = self.store.guard.read_json(sidecar_path)
        nonce = sidecar.get("nonce")
        record_digest = record.get("nonceHash") if expected_kind == "release" else record.get("nonceSha256")
        record_status = record.get("status")
        expected_status = "issued" if expected_kind == "release" else "active"
        if (
            record_status != expected_status
            or sidecar.get("status") != "active"
            or sidecar.get("kind") != expected_kind
            or sidecar.get("authorizationId") != authorization_id
            or not isinstance(nonce, str)
            or "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
            != record_digest
            or sidecar.get("nonceSha256") != record_digest
        ):
            raise ReservationError("Authorization is forged, revoked, or tampered")
        if expected_kind == "release":
            try:
                from .contracts import validate_contract

                validate_contract("release-authorization", record)
            except Exception as exc:
                raise ReservationError("Release authorization contract is invalid") from exc
            return {
                "authorizationId": authorization_id,
                "binding": {
                    "reservationId": record["reservationId"],
                    "workflowId": record["workflowId"],
                    "issueId": record["issueId"],
                    "repositoryId": record["repositoryId"],
                    "repositoryKey": record["repositoryKey"],
                    "runId": record["runId"],
                    "operationId": record["operationId"],
                    "stateRevision": record["stateRevision"],
                    "reservationRevision": record["reservationRevision"],
                    "physicalWorktreeFingerprint": record[
                        "physicalWorktreeFingerprint"
                    ],
                    "scope": record["scope"],
                    "expiresAtNs": self._parse_iso_time(record["expiresAt"]),
                },
            }
        required_binding = {
            "reservationId",
            "workflowId",
            "issueId",
            "repositoryId",
            "repositoryKey",
            "runId",
            "operationId",
            "authorizationOperationId",
            "stateRevision",
            "reservationRevision",
            "physicalWorktreeFingerprint",
            "scope",
            "createdAtNs",
            "expiresAtNs",
        }
        cleanup_binding = {
            "reservationId",
            "workflowId",
            "repositoryId",
            "repositoryKey",
            "runId",
            "operationId",
            "releasedReservationRevision",
            "stateRevision",
            "reservationsRevision",
            "physicalWorktreeFingerprint",
            "gateOperationId",
            "gatePath",
            "gateFingerprint",
            "exactSha",
            "scope",
            "createdAtNs",
            "expiresAtNs",
        }
        expected_binding = required_binding if expected_kind == "mutation" else cleanup_binding
        if (
            set(record) != {
                "schemaVersion",
                "authorizationId",
                "kind",
                "binding",
                "nonceSha256",
                "status",
            }
            or record.get("kind") != expected_kind
            or not isinstance(record.get("binding"), dict)
            or set(record["binding"]) != expected_binding
            or (
                expected_kind == "mutation"
                and record["binding"]["authorizationOperationId"] != authorization_id
            )
            or record["binding"]["expiresAtNs"] <= record["binding"]["createdAtNs"]
        ):
            raise ReservationError(
                f"{expected_kind.capitalize()} authorization contract is invalid"
            )
        return record

    def _consume_authorization(self, reference: str | Path) -> None:
        record_path = self.store.guard.leaf(reference, must_exist=True)
        record = self.store.guard.read_json(record_path)
        authorization_id = record["authorizationId"]
        sidecar_path = self.store.guard.leaf(
            record_path.parent / f"{authorization_id}.capability.json", must_exist=True
        )
        sidecar = self.store.guard.read_json(sidecar_path)
        is_release = "nonceHash" in record
        record["status"] = "consumed"
        if is_release:
            record["consumedAt"] = self._iso_time(self._now())
        self.store.guard.write_json(record_path, record)
        self.store.guard.write_json(
            sidecar_path,
            {
                "schemaVersion": "1.0",
                "authorizationId": authorization_id,
                "kind": "release" if is_release else record["kind"],
                "nonceSha256": sidecar["nonceSha256"],
                "status": "consumed",
            },
        )

    def _revoke_authorization(self, reference: str | Path) -> None:
        """Revoke superseded authority without claiming it authorized mutation."""

        record_path = self.store.guard.leaf(reference, must_exist=True)
        record = self.store.guard.read_json(record_path)
        authorization_id = record["authorizationId"]
        sidecar_path = self.store.guard.leaf(
            record_path.parent / f"{authorization_id}.capability.json", must_exist=True
        )
        sidecar = self.store.guard.read_json(sidecar_path)
        kind = "release" if "nonceHash" in record else record["kind"]
        record["status"] = "revoked"
        if "consumedAt" in record:
            record["consumedAt"] = None
        self.store.guard.write_json(record_path, record)
        self.store.guard.write_json(
            sidecar_path,
            {
                "schemaVersion": "1.0",
                "authorizationId": authorization_id,
                "kind": kind,
                "nonceSha256": sidecar["nonceSha256"],
                "status": "revoked",
            },
        )

    def _validate_trusted_observation(
        self,
        reference: str | Path | None,
        *,
        record: Mapping[str, Any],
        local_summary: Mapping[str, Any],
        consumed: list[str],
    ) -> dict[str, Any]:
        if reference is None:
            raise ReservationError("Required trusted external observation is unavailable")
        path = self.store.guard.leaf(reference, must_exist=True)
        try:
            path.relative_to(self.store.directories["final-attestations"])
        except ValueError as exc:
            raise ReservationError("Trusted observation path is not engine-owned") from exc
        observation = self.store.guard.read_json(path)
        required = {
            "schemaVersion",
            "observationId",
            "observationRef",
            "adapterId",
            "adapterVersion",
            "adapterKind",
            "operationId",
            "repositoryId",
            "repositoryKey",
            "stateHome",
            "normalizedCommonDir",
            "branch",
            "headSha",
            "pullRequest",
            "observedAt",
            "expiresAt",
            "journalHash",
            "attestationHash",
            "consumedAt",
            "status",
        }
        if set(observation) != required or observation.get("schemaVersion") != "1.0":
            raise ReservationError("Trusted observation shape/version is invalid")
        pull_request = observation["pullRequest"]
        expires_ns = self._parse_iso_time(observation["expiresAt"])
        observed_ns = self._parse_iso_time(observation["observedAt"])
        journal_body = {
            key: value
            for key, value in observation.items()
            if key not in {"journalHash", "attestationHash", "consumedAt", "status"}
        }
        expected_journal = "sha256:" + sha256_json(journal_body)
        expected_attestation = "sha256:" + hashlib.sha256(
            (observation["adapterId"] + "\0" + expected_journal).encode("utf-8")
        ).hexdigest()
        if (
            observation["observationId"] in consumed
            or observation["journalHash"] != expected_journal
            or observation["attestationHash"] != expected_attestation
            or observation["observationRef"] != os.fspath(path)
            or observation["repositoryId"] != record["repositoryId"]
            or observation["repositoryKey"] != record["repositoryKey"]
            or observation["stateHome"] != os.fspath(self.store.root)
            or observation["normalizedCommonDir"]
            != os.path.normcase(os.path.realpath(self.manager.identity.common_dir))
            or observation["branch"] != local_summary["branch"]
            or observation["headSha"] != local_summary["headSha"]
            or pull_request is None
            or pull_request["id"] != record["protectedWork"].get("prId")
            or pull_request["headSha"] != local_summary["headSha"]
            or pull_request["state"] not in {"open", "closed", "merged"}
            or observation["status"] != "issued"
            or observation["consumedAt"] is not None
            or self._now() > expires_ns
            or observed_ns > self._now()
        ):
            raise ReservationError("Trusted observation is stale, replayed, or mismatched")
        return observation

    def _validate_current_capability(
        self,
        state: Mapping[str, Any],
        record: Mapping[str, Any],
        capability_ref: str | None,
        *,
        allow_expired_capability: bool = False,
    ) -> None:
        if not isinstance(capability_ref, str) or not capability_ref:
            raise ReservationError("Autonomous commands require an exact capability reference")
        now = self._now()
        lease = state.get("lease")
        if (
            not isinstance(lease, dict)
            or lease.get("status") != "live"
            or lease.get("runId") != record.get("runId")
            or now >= lease.get("expiresAtNs", 0)
            or lease.get("revision") != state["revision"]
        ):
            raise ReservationError("Autonomous lease authority is expired or stale")
        lease_sidecar = self.store.guard.read_json(
            self.store.guard.leaf(lease["capabilityRef"], must_exist=True)
        )
        lease_nonce = lease_sidecar.get("nonce")
        if (
            lease_sidecar.get("status") != "active"
            or lease_sidecar.get("kind") != "lease"
            or lease_sidecar.get("physicalWorktreeFingerprint")
            != self.manager.identity.physical_worktree_fingerprint
            or not isinstance(lease_nonce, str)
            or "sha256:"
            + hashlib.sha256(lease_nonce.encode("utf-8")).hexdigest()
            != lease.get("capabilitySha256")
        ):
            raise ReservationError("Autonomous lease sidecar is revoked or tampered")
        current = state.get("currentWork")
        if not isinstance(current, dict) or (
            current.get("runId") != record.get("runId")
            or current.get("workflowId") != record.get("workflowId")
            or current.get("issueId") != record.get("issueId")
            or current.get("worktreePath") != record.get("worktreePath")
            or current.get("physicalWorktreeFingerprint")
            != record.get("physicalWorktreeFingerprint")
        ):
            raise ReservationError("Autonomous current-work authority is mismatched")
        matches = [
            capability
            for capability in state["capabilities"].values()
            if capability["status"] == "issued"
            and capability["capabilityRef"] == capability_ref
            and capability["runId"] == record["runId"]
            and capability["workflowId"] == record["workflowId"]
            and capability["issueId"] == record["issueId"]
            and capability["worktreePath"] == record["worktreePath"]
            and capability["physicalWorktreeFingerprint"]
            == record["physicalWorktreeFingerprint"]
            and capability["stateRevision"] == state["revision"]
            and (allow_expired_capability or now < capability["expiresAtNs"])
            and capability["stage"] == current["stage"]
        ]
        if len(matches) != 1:
            raise ReservationError("Autonomous reservation capability is not current")
        capability = matches[0]
        sidecar = self.store.guard.read_json(
            self.store.guard.leaf(capability["capabilityRef"], must_exist=True)
        )
        nonce = sidecar.get("nonce")
        if (
            sidecar.get("status") != "active"
            or sidecar.get("kind") != capability["kind"]
            or sidecar.get("physicalWorktreeFingerprint")
            != record["physicalWorktreeFingerprint"]
            or not isinstance(nonce, str)
            or "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
            != capability["capabilitySha256"]
        ):
            raise ReservationError("Autonomous capability sidecar is revoked or tampered")

    def _validate_workflow_unlocked(
        self,
        workflow_id: str,
        *,
        physical_worktree_fingerprint: str,
        worktree_path: str | Path,
    ) -> None:
        registry = self.manager.registry.load_unlocked()
        entry = registry["workflows"].get(workflow_id)
        if (
            entry is None
            or entry["repositoryId"] != self.manager.identity.repository_id
            or entry["repositoryKey"] != self.manager.repository_key
            or entry["physicalWorktreeFingerprint"] != physical_worktree_fingerprint
            or os.path.normcase(
                os.path.realpath(Path(entry["artifactPath"]).parent.parent)
            )
            != os.path.normcase(os.path.realpath(worktree_path))
        ):
            raise ReservationError(
                "Reservation workflow is not registered to the exact physical worktree"
            )

    def _require_manager_authority(
        self, state: Mapping[str, Any], record: Mapping[str, Any]
    ) -> None:
        """Prove repository controller authority and the exact editing target.

        Persistent issue worktrees deliberately live below the repository state
        home, so the canonical WorkflowManager cannot itself be rooted there.
        The scheduled checkout remains the repository controller; registry and
        issue-mapping evidence bind the separate physical editing target.
        """

        if (
            self.manager.identity.repository_id != record["repositoryId"]
            or self.manager.repository_key != record["repositoryKey"]
        ):
            raise ReservationError("Reservation belongs to another repository authority")
        self._validate_workflow_unlocked(
            record["workflowId"],
            physical_worktree_fingerprint=record["physicalWorktreeFingerprint"],
            worktree_path=record["worktreePath"],
        )
        mapping = (
            state.get("issueWorktrees", {}).get(record.get("issueId"))
            if record.get("issueId") is not None
            else None
        )
        if record.get("policy") == "autonomous" or mapping is not None:
            if not isinstance(mapping, dict) or any(
                mapping.get(name) != value
                for name, value in {
                    "issueId": record.get("issueId"),
                    "workflowId": record["workflowId"],
                    "repositoryId": record["repositoryId"],
                    "repositoryKey": record["repositoryKey"],
                    "worktreePath": os.path.normcase(
                        os.path.realpath(record["worktreePath"])
                    ).replace("\\", "/"),
                    "physicalWorktreeFingerprint": record[
                        "physicalWorktreeFingerprint"
                    ],
                    "status": "active",
                }.items()
            ):
                raise ReservationError(
                    "Reservation editing target differs from its issue-worktree authority"
                )

    def _validate_handoff_issue_authority(
        self, state: Mapping[str, Any], record: Mapping[str, Any]
    ) -> None:
        issue_id = record.get("issueId")
        if issue_id is None:
            if record.get("policy") == "autonomous":
                raise ReservationError(
                    "Autonomous Handoff requires a persistent issue-worktree mapping"
                )
            return
        mapping = state.get("issueWorktrees", {}).get(issue_id)
        allocation = state.get("worktreeAllocations", {}).get(f"issue:{issue_id}")
        normalized_source = _normalized_path(record["worktreePath"])
        exact_mapping = {
            "issueId": issue_id,
            "workflowId": record["workflowId"],
            "repositoryId": record["repositoryId"],
            "repositoryKey": record["repositoryKey"],
            "worktreePath": normalized_source,
            "physicalWorktreeFingerprint": record[
                "physicalWorktreeFingerprint"
            ],
            "status": "active",
        }
        if not isinstance(mapping, Mapping) or any(
            mapping.get(name) != value for name, value in exact_mapping.items()
        ):
            raise ReservationError(
                "Handoff issue mapping differs from the reserved editing source"
            )
        handoff_operation_id = mapping.get("handoffOperationId")
        expected_allocation_status = (
            "completed" if handoff_operation_id is None else "transferred"
        )
        allocation_bindings = {
            "allocationId": f"issue:{issue_id}",
            "kind": "issue",
            "subjectId": issue_id,
            "repositoryId": record["repositoryId"],
            "repositoryKey": record["repositoryKey"],
            "worktreePath": normalized_source,
            "physicalWorktreeFingerprint": record[
                "physicalWorktreeFingerprint"
            ],
            "branch": mapping.get("branch"),
            "exactSha": mapping.get("headSha"),
            "handoffOperationId": handoff_operation_id,
            "status": expected_allocation_status,
        }
        if not isinstance(allocation, Mapping) or any(
            allocation.get(name) != value
            for name, value in allocation_bindings.items()
        ):
            raise ReservationError(
                "Handoff issue allocation differs from the reserved editing source"
            )

    @staticmethod
    def _canonical_scope(scope: Iterable[str]) -> list[str]:
        observed: set[str] = set()
        result: list[str] = []
        for raw in scope:
            if not isinstance(raw, str) or not raw or "\\" in raw:
                raise ReservationError("Authorization scope path is not canonical")
            path = PurePosixPath(raw)
            if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
                raise ReservationError("Authorization scope path escapes repository authority")
            canonical = path.as_posix()
            if canonical.casefold() in observed:
                raise ReservationError("Authorization scope has a case-insensitive duplicate")
            observed.add(canonical.casefold())
            result.append(canonical)
        if not result:
            raise ReservationError("Authorization scope cannot be empty")
        return sorted(result, key=str.casefold)

    def _canonical_mutation_scope(self, scope: Iterable[str]) -> list[str]:
        relative: list[str] = []
        absolute: list[str] = []
        for raw in scope:
            if isinstance(raw, str) and os.path.isabs(raw):
                normalized = os.path.realpath(os.path.abspath(raw))
                if os.path.normpath(raw) != raw or normalized != raw:
                    raise ReservationError("Absolute mutation scope path is not canonical")
                try:
                    contained = os.path.commonpath(
                        [os.fspath(self.store.root), normalized]
                    ) == os.fspath(self.store.root)
                except ValueError:
                    contained = False
                if not contained:
                    raise ReservationError("Absolute mutation scope escapes state authority")
                absolute.append(normalized)
            else:
                relative.append(raw)
        combined = self._canonical_scope(relative) if relative else []
        combined.extend(absolute)
        folded = [item.casefold() for item in combined]
        if len(folded) != len(set(folded)):
            raise ReservationError("Authorization scope has a case-insensitive duplicate")
        if not combined:
            raise ReservationError("Authorization scope cannot be empty")
        return sorted(combined, key=str.casefold)

    @staticmethod
    def _active_record(
        reservations: Mapping[str, Any], reservation_id: str
    ) -> dict[str, Any]:
        return ReservationManager._record_in_statuses(
            reservations,
            reservation_id,
            _ACTIVE,
            "Editing reservation is absent or inactive",
        )

    @staticmethod
    def _record_in_statuses(
        reservations: Mapping[str, Any],
        reservation_id: str,
        allowed_statuses: set[str],
        error: str,
    ) -> dict[str, Any]:
        record = reservations["reservations"].get(reservation_id)
        if not isinstance(record, dict) or record.get("status") not in allowed_statuses:
            raise ReservationError(error)
        return record

    def _has_pending_operation_evidence(
        self, *, ignore_operation_id: str | None = None
    ) -> bool:
        from .operations import OperationJournal

        return bool(
            OperationJournal(self.store).pending_ids(
                ignore_operation_id=ignore_operation_id
            )
        )

    @staticmethod
    def _expected_revisions(
        state: Mapping[str, Any],
        reservations: Mapping[str, Any],
        expected_state_revision: int,
        expected_reservations_revision: int,
    ) -> None:
        if state["revision"] != expected_state_revision:
            raise SupervisorConflictError("Supervisor state revision is stale")
        if reservations["revision"] != expected_reservations_revision:
            raise SupervisorConflictError("Reservation document revision is stale")

    @staticmethod
    def _barrier(state: Mapping[str, Any]) -> None:
        if state["handoffPending"] is not None:
            raise ReservationError("Handoff pending barrier suspends reservation mutation")
        if state["recovery"]["status"] != "clean":
            raise ReservationError("Protected recovery state suspends reservation mutation")

    @staticmethod
    def _duration(value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ReservationError("Reservation duration must be positive nanoseconds")

    @staticmethod
    def _safe_id(value: Any, label: str) -> None:
        if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
            raise ReservationError(f"{label} is not a safe canonical identifier")

    def _validate_request_ids(
        self,
        workflow_id: str,
        issue_id: str | None,
        owner_id: str,
        run_id: str | None,
    ) -> None:
        for value, label in (
            (workflow_id, "workflow ID"),
            (owner_id, "owner ID"),
        ):
            self._safe_id(value, label)
        if issue_id is not None:
            self._safe_id(issue_id, "issue ID")
        if run_id is not None:
            self._safe_id(run_id, "run ID")

    def _now(self) -> int:
        value = self.clock()
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ReservationError("Reservation clock returned an invalid value")
        return value

    @staticmethod
    def _iso_time(value_ns: int) -> str:
        return datetime.fromtimestamp(value_ns / 1_000_000_000, timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_iso_time(value: str) -> int:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ReservationError("Trusted observation timestamp is invalid") from exc
        if parsed.tzinfo is None:
            raise ReservationError("Trusted observation timestamp must carry UTC offset")
        return int(parsed.timestamp() * 1_000_000_000)


def inspect_handoff_interlock(
    manager: Any, workflow_id: str, *, already_locked: bool = False
) -> dict[str, Any] | None:
    """Read authoritative pending reservation/auth metadata under the base mutex."""

    store = SupervisorStore(manager, initialize=not already_locked)

    def inspect() -> dict[str, Any] | None:
        state, reservations = store.load_pair_unlocked()
        matches = [
            record
            for record in reservations["reservations"].values()
            if record["workflowId"] == workflow_id and record["status"] in _ACTIVE
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise ReservationError("Multiple live workflow reservations require reconciliation")
        record = matches[0]
        result = {"reservation": copy.deepcopy(record), "handoffPending": None}
        if record["status"] == "handoff-pending":
            operation_id = record["pendingHandoffOperationId"]
            auth_path = store.guard.leaf(
                store.directories["handoff-authorizations"] / f"{operation_id}.json",
                must_exist=True,
            )
            result["handoffPending"] = {
                "state": copy.deepcopy(state["handoffPending"]),
                "authorization": store.guard.read_json(auth_path),
                "authorizationPath": os.fspath(auth_path),
            }
        return result

    if already_locked:
        return inspect()
    with store.mutex():
        return inspect()
