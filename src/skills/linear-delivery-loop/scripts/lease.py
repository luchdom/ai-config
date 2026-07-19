"""Renewable lease and single-use prepared-capability state machine."""

from __future__ import annotations

import copy
import hashlib
import os
import re
import secrets
import subprocess
import time
import uuid
from datetime import datetime, timezone
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from .contracts import validate_contract
from .store import (
    SupervisorConflictError,
    SupervisorStore,
    SupervisorStoreError,
    assert_public_data,
    sha256_json,
)


class Clock(Protocol):
    def now_ns(self) -> int: ...


class SystemClock:
    def now_ns(self) -> int:
        return time.time_ns()


class ManualClock:
    """Dependency-free deterministic clock for boundary/race tests."""

    def __init__(self, now_ns: int):
        self.value = now_ns

    def now_ns(self) -> int:
        return self.value

    def set(self, value: int) -> None:
        self.value = value

    def advance(self, delta_ns: int) -> None:
        self.value += delta_ns


class LeaseError(SupervisorStoreError):
    """Lease, capability, or checkpoint authority was rejected."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_STAGES = (
    "initialized",
    "plan",
    "clarify",
    "task",
    "audit",
    "implement",
    "review",
    "qa",
    "docs",
    "publication",
    "completion",
)
_TRANSITIONS = frozenset(zip(_STAGES, _STAGES[1:])) | frozenset(
    (stage, "paused") for stage in _STAGES[:-1]
)


class LeaseManager:
    DEFAULT_LEASE_NS = 5 * 60 * 1_000_000_000
    DEFAULT_CAPABILITY_NS = 5 * 60 * 1_000_000_000
    DEFAULT_MAX_FORWARD_STEP_NS = 30 * 60 * 1_000_000_000

    def __init__(
        self,
        store: SupervisorStore,
        *,
        clock: Clock | None = None,
        max_forward_step_ns: int = DEFAULT_MAX_FORWARD_STEP_NS,
    ):
        if max_forward_step_ns <= 0:
            raise LeaseError("Maximum clock step must be positive")
        self.store = store
        self.clock = clock or SystemClock()
        self.max_forward_step_ns = max_forward_step_ns

    def acquire(
        self,
        *,
        run_id: str,
        owner_id: str,
        expected_revision: int,
        duration_ns: int = DEFAULT_LEASE_NS,
    ) -> dict[str, Any]:
        self._safe_id(run_id, "run ID")
        self._safe_id(owner_id, "owner ID")
        self._duration(duration_ns)
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected(state, expected_revision)
            self._authority_barrier(state)
            now = self._observe_clock(state, reservations, "AcquireLease")
            existing = state["lease"]
            if existing is not None:
                # Exact public request replay is handled by the immutable
                # operation journal before dispatch.  Identifiers visible in
                # Status must never be sufficient to make the manager
                # redistribute an already-issued opaque authority reference.
                raise SupervisorConflictError(
                    "Existing or expired lease requires attended reconciliation before acquisition"
                )
            capability_id = str(uuid.uuid4())
            reference, digest = self._create_sidecar(
                run_id=run_id,
                # A run identifier is public coordination metadata.  The lease
                # authority path must therefore carry independent entropy and
                # must never be derivable from that identifier.
                filename=f"{capability_id}.lease-capability.json",
                capability_id=capability_id,
                kind="lease",
            )
            after = copy.deepcopy(state)
            self._apply_clock(after, now)
            after_revision = state["revision"] + 1
            lease = {
                "runId": run_id,
                "ownerId": owner_id,
                "revision": after_revision,
                "heartbeatNs": now,
                "expiresAtNs": now + duration_ns,
                "capabilityRef": reference,
                "capabilitySha256": digest,
                "status": "live",
            }
            after["lease"] = lease
            after["revision"] = after_revision
            committed, _ = self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="AcquireLease",
            )
            return copy.deepcopy(committed["lease"])

    def renew(
        self,
        *,
        run_id: str,
        owner_id: str,
        expected_revision: int,
        capability_ref: str,
        operation_id: str | None = None,
        duration_ns: int = DEFAULT_LEASE_NS,
    ) -> dict[str, Any]:
        if operation_id is None:
            operation_id = str(uuid.uuid4())
        self._safe_id(operation_id, "renew operation ID")
        self._duration(duration_ns)
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected(state, expected_revision)
            self._renewal_barrier(state)
            now = self._observe_clock(state, reservations, "RenewLease")
            lease = self._require_lease(
                state, run_id=run_id, owner_id=owner_id, capability_ref=capability_ref
            )
            self._verify_sidecar(capability_ref, lease["capabilitySha256"], "lease")
            self._require_manager_authority(state)
            # Successful renewal rotates the opaque authority.  Holding the
            # previous Acquire/Renew result is required to renew, while only
            # this exact renewal receives the next authority reference.
            renewed_authority_id = str(uuid.uuid4())
            renewed_reference, renewed_digest = self._create_sidecar(
                run_id=run_id,
                filename=f"{renewed_authority_id}.lease-capability.json",
                capability_id=operation_id,
                kind="lease",
            )
            after = copy.deepcopy(state)
            self._apply_clock(after, now)
            if (
                after["recovery"]["status"] == "required"
                and after["recovery"]["reason"] == "expired-lease"
            ):
                after["recovery"] = {
                    "status": "clean",
                    "reason": None,
                    "updatedAtNs": now,
                }
            after_revision = state["revision"] + 1
            after["lease"].update(
                {
                    "revision": after_revision,
                    "heartbeatNs": now,
                    "expiresAtNs": now + duration_ns,
                    "capabilityRef": renewed_reference,
                    "capabilitySha256": renewed_digest,
                }
            )
            for capability in after["capabilities"].values():
                if capability["capabilityRef"] == capability_ref:
                    capability["expiresAtNs"] = now + duration_ns
                    capability["stateRevision"] = after_revision
                elif capability["status"] == "issued":
                    capability["stateRevision"] = after_revision
                    prepared_path = self.store.guard.leaf(
                        Path(capability["capabilityRef"]).parent
                        / f"{capability['capabilityId']}.prepared-iteration.json",
                        must_exist=True,
                    )
                    prepared = self.store.guard.read_json(prepared_path)
                    prepared["stateRevision"] = after_revision
                    self.store.guard.write_json(prepared_path, prepared)
            after["revision"] = after_revision
            committed, _ = self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="RenewLease",
            )
            self._revoke_sidecar(capability_ref, lease["capabilitySha256"], "lease")
            return copy.deepcopy(committed["lease"])

    def release(
        self,
        *,
        run_id: str,
        owner_id: str,
        expected_revision: int,
        capability_ref: str,
    ) -> dict[str, Any]:
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected(state, expected_revision)
            self._authority_barrier(state)
            now = self._observe_clock(state, reservations, "ReleaseLease")
            lease = self._require_lease(
                state, run_id=run_id, owner_id=owner_id, capability_ref=capability_ref
            )
            self._verify_sidecar(capability_ref, lease["capabilitySha256"], "lease")
            self._require_manager_authority(state)
            if any(
                record["status"] not in {"released", "reclaimed"}
                and record.get("runId") == run_id
                for record in reservations["reservations"].values()
            ):
                raise LeaseError("Lease remains protected by an active editing reservation")
            after = copy.deepcopy(state)
            self._apply_clock(after, now)
            after["lease"] = None
            for capability in after["capabilities"].values():
                if capability["capabilityRef"] == capability_ref:
                    capability["status"] = "revoked"
            after["revision"] = state["revision"] + 1
            committed, _ = self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="ReleaseLease",
            )
            self._revoke_sidecar(capability_ref, lease["capabilitySha256"], "lease")
            return {"status": "released", "stateRevision": committed["revision"]}

    def recover_expired(self, *, expected_revision: int) -> dict[str, Any]:
        """Reconcile an expired/killed run from authoritative local state.

        The lease and all outstanding prepared capabilities are revoked only
        after their clock expiry is proven and no active reservation still
        protects that run. ``currentWork`` is deliberately retained so a new
        lease can resume the registered goal at its last applied checkpoint.
        """

        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected(state, expected_revision)
            now = self.clock.now_ns()
            if not isinstance(now, int) or isinstance(now, bool) or now < 0:
                raise LeaseError("Clock must return a non-negative integer nanosecond value")
            if state["handoffPending"] is not None:
                return {"status": "protected", "reason": "handoff-pending"}
            if state["recovery"]["status"] in {"ambiguous", "recovering"}:
                return {
                    "status": "protected",
                    "reason": state["recovery"]["reason"] or "recovery-barrier",
                }
            if (
                state["recovery"]["status"] == "required"
                and state["recovery"]["reason"]
                not in {"expired-lease", "clock-discontinuity"}
            ):
                return {
                    "status": "protected",
                    "reason": state["recovery"]["reason"],
                }
            evidence = state["clockEvidence"]
            if evidence["status"] == "clock-discontinuity" and (
                now < evidence["lastObservedNowNs"]
                or now - evidence["lastObservedNowNs"] > evidence["maxForwardStepNs"]
            ):
                return {"status": "protected", "reason": "clock-discontinuity"}
            lease = state["lease"]
            after = copy.deepcopy(state)
            self._apply_clock(after, now)
            if lease is None:
                if after["recovery"]["reason"] in {
                    "expired-lease",
                    "clock-discontinuity",
                }:
                    after["recovery"] = {
                        "status": "clean",
                        "reason": None,
                        "updatedAtNs": now,
                    }
                if after != state:
                    after["revision"] = state["revision"] + 1
                    committed, _ = self.store.commit_pair_unlocked(
                        before_state=state,
                        after_state=after,
                        before_reservations=reservations,
                        after_reservations=reservations,
                        operation="RecoverLease:clock",
                    )
                    return {"status": "ready", "stateRevision": committed["revision"]}
                return {"status": "ready", "stateRevision": state["revision"]}
            if lease["status"] == "live" and now < lease["expiresAtNs"]:
                return {"status": "active", "runId": lease["runId"]}
            protecting = [
                record["reservationId"]
                for record in reservations["reservations"].values()
                if record.get("runId") == lease["runId"]
                and record.get("status") not in {"released", "reclaimed"}
            ]
            if protecting:
                protected = copy.deepcopy(state)
                protected["recovery"] = {
                    "status": "required",
                    "reason": "expired-lease",
                    "updatedAtNs": now,
                }
                self._apply_clock(protected, now)
                if protected != state:
                    protected["revision"] = state["revision"] + 1
                    self.store.commit_pair_unlocked(
                        before_state=state,
                        after_state=protected,
                        before_reservations=reservations,
                        after_reservations=reservations,
                        operation="RecoverLease:protected",
                    )
                return {
                    "status": "protected",
                    "reason": "active-reservation",
                    "reservationIds": sorted(protecting),
                }
            revoked = []
            for capability_id, capability in after["capabilities"].items():
                if capability.get("runId") == lease["runId"] and capability["status"] == "issued":
                    capability["status"] = "revoked"
                    revoked.append(
                        (
                            capability_id,
                            capability["capabilityRef"],
                            capability["capabilitySha256"],
                            capability["kind"],
                        )
                    )
            after["lease"] = None
            after["recovery"] = {
                "status": "clean",
                "reason": None,
                "updatedAtNs": now,
            }
            after["revision"] = state["revision"] + 1
            committed, _ = self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="RecoverLease:expired",
            )
            self._revoke_sidecar(
                lease["capabilityRef"], lease["capabilitySha256"], "lease"
            )
            for _, reference, digest, kind in revoked:
                self._revoke_sidecar(reference, digest, kind)
            return {
                "status": "recovered",
                "runId": lease["runId"],
                "revokedCapabilityIds": sorted(item[0] for item in revoked),
                "stateRevision": committed["revision"],
            }

    def prepare_iteration(
        self,
        *,
        run_id: str,
        owner_id: str,
        workflow_id: str,
        issue_id: str,
        worktree_path: str | Path,
        physical_worktree_fingerprint: str,
        expected_revision: int,
        lease_capability_ref: str,
        stage: str = "initialized",
        duration_ns: int = DEFAULT_CAPABILITY_NS,
        expected_facts: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        for value, label in (
            (run_id, "run ID"),
            (owner_id, "owner ID"),
            (workflow_id, "workflow ID"),
            (issue_id, "issue ID"),
        ):
            self._safe_id(value, label)
        if stage not in _STAGES[:-1]:
            raise LeaseError("Prepared iteration stage is invalid")
        self._duration(duration_ns)
        facts = copy.deepcopy(dict(expected_facts or {}))
        assert_public_data(facts, location="prepared expected facts")
        if facts:
            raise LeaseError("Prepared expected facts belong to the deterministic checkpoint contract")
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            self._expected(state, expected_revision)
            self._authority_barrier(state)
            now = self._observe_clock(state, reservations, "PrepareIteration")
            lease = self._require_lease(
                state,
                run_id=run_id,
                owner_id=owner_id,
                capability_ref=lease_capability_ref,
            )
            if now >= lease["expiresAtNs"]:
                raise LeaseError("Expired lease cannot prepare work")
            self._verify_sidecar(
                lease_capability_ref, lease["capabilitySha256"], "lease"
            )
            mapping = state["issueWorktrees"].get(issue_id)
            if not isinstance(mapping, dict) or mapping.get("status") != "active":
                raise LeaseError("Prepared issue lacks an authoritative issue-worktree mapping")
            observed = self._observe_worktree(worktree_path)
            expected_mapping = {
                "repositoryId": self.store.manager.identity.repository_id,
                "repositoryKey": self.store.manager.repository_key,
                "normalizedCommonDir": os.path.normcase(
                    os.path.realpath(self.store.manager.identity.common_dir)
                ).replace("\\", "/"),
                "worktreePath": observed["worktreePath"],
                "physicalWorktreeFingerprint": physical_worktree_fingerprint,
            }
            if (
                any(mapping.get(key) != value for key, value in expected_mapping.items())
                or mapping.get("issueId") != issue_id
                or mapping.get("workflowId") not in {None, workflow_id}
                or observed["physicalWorktreeFingerprint"]
                != physical_worktree_fingerprint
                or observed["branch"] != mapping.get("branch")
                or self.store.manager.identity.physical_worktree_fingerprint
                == physical_worktree_fingerprint
                or os.path.normcase(os.path.realpath(self.store.manager.repository_root))
                == os.path.normcase(os.path.realpath(mapping["worktreePath"]))
            ):
                raise LeaseError("Prepared worktree differs from its authoritative issue mapping")
            self._validate_workflow_unlocked(workflow_id, mapping=mapping)
            current = state["currentWork"]
            if current is not None and (
                current["workflowId"] != workflow_id or current["issueId"] != issue_id
            ):
                raise LeaseError("A run cannot prepare a second issue")
            capability_id = str(uuid.uuid4())
            filename = f"{capability_id}.capability.json"
            reference, digest = self._create_sidecar(
                run_id=run_id,
                filename=filename,
                capability_id=capability_id,
                kind="prepared-iteration",
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
            run_dir = self.store.guard.directory(
                self.store.directories["runs"] / run_id, create=True
            )
            prepared_path = self.store.guard.leaf(
                run_dir / f"{capability_id}.prepared-iteration.json"
            )
            after_revision = state["revision"] + 1
            allowed = [right for left, right in _TRANSITIONS if left == stage]
            prepared = {
                "schemaVersion": "1.0",
                "preparedIterationId": capability_id,
                "runId": run_id,
                "workflowId": workflow_id,
                "issueId": issue_id,
                "repositoryId": self.store.manager.identity.repository_id,
                "repositoryKey": self.store.manager.repository_key,
                "stateHome": os.fspath(self.store.root),
                "worktreePath": observed["worktreePath"],
                "physicalWorktreeFingerprint": physical_worktree_fingerprint,
                "stateRevision": after_revision,
                "stage": stage,
                "expiresAt": self._iso_time(now + duration_ns),
                "capabilityRef": reference,
                "capabilityHash": digest,
            }
            self.store.guard.write_json(prepared_path, prepared)
            after = copy.deepcopy(state)
            self._apply_clock(after, now)
            after["issueWorktrees"][issue_id]["workflowId"] = workflow_id
            after["issueWorktrees"][issue_id]["headSha"] = observed["headSha"]
            after["capabilities"][capability_id] = {
                "capabilityId": capability_id,
                "kind": "prepared-iteration",
                "runId": run_id,
                "workflowId": workflow_id,
                "issueId": issue_id,
                "worktreePath": prepared["worktreePath"],
                "physicalWorktreeFingerprint": physical_worktree_fingerprint,
                "stateRevision": after_revision,
                "stage": stage,
                "expiresAtNs": now + duration_ns,
                "capabilityRef": reference,
                "capabilitySha256": digest,
                "status": "issued",
                "allowedTransitions": allowed,
            }
            after["currentWork"] = {
                "runId": run_id,
                "workflowId": workflow_id,
                "issueId": issue_id,
                "stage": stage,
                "worktreePath": prepared["worktreePath"],
                "physicalWorktreeFingerprint": physical_worktree_fingerprint,
            }
            after["lease"]["revision"] = after_revision
            after["revision"] = after_revision
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation="PrepareIteration",
            )
            return copy.deepcopy(prepared)

    def apply_checkpoint(
        self,
        *,
        prepared_ref: str | Path,
        transition_id: str,
        expected_revision: int,
        expected_stage: str,
        worker_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._safe_id(transition_id, "transition ID")
        if expected_stage not in _STAGES[:-1]:
            raise LeaseError("Engine expected stage is invalid")
        result = validate_contract("worker-result", worker_result)
        assert_public_data(result, location="worker result")
        prepared_path = self.store.guard.leaf(prepared_ref, must_exist=True)
        prepared = self.store.guard.read_json(prepared_path)
        capability_id = prepared.get("preparedIterationId")
        self._safe_id(capability_id, "prepared capability ID")
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            existing = state["checkpoints"].get(transition_id)
            run_dir = self.store.guard.directory(
                self.store.directories["runs"] / prepared["runId"]
            )
            evidence_path = self.store.guard.leaf(
                run_dir / f"checkpoint-{transition_id}.json"
            )
            result_hash = sha256_json(result)
            if existing is not None:
                evidence = self.store.guard.read_json(evidence_path)
                if evidence.get("resultSha256") != result_hash:
                    raise LeaseError("Checkpoint transition replay changed its worker result")
                return copy.deepcopy(existing)
            self._expected(state, expected_revision)
            self._authority_barrier(state)
            now = self._observe_clock(state, reservations, "ApplyCheckpoint")
            capability = state["capabilities"].get(capability_id)
            if capability is None or capability["status"] != "issued":
                raise LeaseError("Prepared capability is unknown, consumed, or revoked")
            if capability["stateRevision"] != state["revision"]:
                raise LeaseError("Prepared capability state revision is stale")
            if now >= capability["expiresAtNs"]:
                raise LeaseError("Prepared capability is expired")
            self._verify_sidecar(
                capability["capabilityRef"],
                capability["capabilitySha256"],
                "prepared-iteration",
                physical_worktree_fingerprint=capability[
                    "physicalWorktreeFingerprint"
                ],
            )
            self._require_manager_authority(state, capability)
            self._validate_checkpoint_bindings(
                state, prepared, result, transition_id, expected_stage
            )
            previous = expected_stage
            next_stage = self._worker_next_stage(result)
            if (previous, next_stage) not in _TRANSITIONS:
                raise LeaseError("Checkpoint stage transition is not allowed")
            if next_stage not in capability["allowedTransitions"]:
                raise LeaseError("Checkpoint transition was not granted by prepared authority")
            evidence = {
                "schemaVersion": "1.0",
                "transitionId": transition_id,
                "preparedRef": os.fspath(prepared_path),
                "resultSha256": result_hash,
                "result": result,
            }
            if evidence_path.exists():
                if self.store.guard.read_json(evidence_path) != evidence:
                    raise LeaseError("Checkpoint evidence is mismatched or tampered")
            else:
                self.store.guard.write_json(evidence_path, evidence)
            after = copy.deepcopy(state)
            self._apply_clock(after, now)
            after_revision = state["revision"] + 1
            after["capabilities"][capability_id]["status"] = "consumed"
            after["currentWork"]["stage"] = next_stage
            observed = self._observe_worktree(prepared["worktreePath"])
            after["issueWorktrees"][prepared["issueId"]]["headSha"] = observed[
                "headSha"
            ]
            if after["lease"] is not None:
                after["lease"]["revision"] = after_revision
            checkpoint_id = str(uuid.uuid4())
            after["checkpoints"][transition_id] = {
                "transitionId": transition_id,
                "checkpointId": checkpoint_id,
                "status": "applied",
                "stateRevision": after_revision,
            }
            after["revision"] = after_revision
            committed, _ = self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation=f"ApplyCheckpoint:{transition_id}",
            )
            self._revoke_sidecar(
                capability["capabilityRef"], capability["capabilitySha256"], "prepared-iteration"
            )
            return copy.deepcopy(committed["checkpoints"][transition_id])

    def _observe_clock(
        self,
        state: dict[str, Any],
        reservations: dict[str, Any],
        operation: str,
    ) -> int:
        now = self.clock.now_ns()
        if not isinstance(now, int) or isinstance(now, bool) or now < 0:
            raise LeaseError("Clock must return a non-negative integer nanosecond value")
        evidence = state["clockEvidence"]
        if evidence["status"] == "clock-discontinuity":
            raise LeaseError("Clock discontinuity requires attended reconciliation")
        previous = evidence["lastObservedNowNs"]
        max_step = evidence["maxForwardStepNs"]
        discontinuity = previous != 0 and (
            now < previous or now - previous > max_step
        )
        if discontinuity:
            after = copy.deepcopy(state)
            after["clockEvidence"] = {
                "lastObservedNowNs": now,
                "maxForwardStepNs": self.max_forward_step_ns,
                "status": "clock-discontinuity",
            }
            after["recovery"] = {
                "status": "required",
                "reason": "clock-discontinuity",
                "updatedAtNs": now,
            }
            after["revision"] = state["revision"] + 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation=f"{operation}:clock-discontinuity",
            )
            raise LeaseError("Clock discontinuity requires attended reconciliation")
        return now

    def _apply_clock(self, state: dict[str, Any], now: int) -> None:
        state["clockEvidence"] = {
            "lastObservedNowNs": now,
            "maxForwardStepNs": self.max_forward_step_ns,
            "status": "stable",
        }

    def _create_sidecar(
        self,
        *,
        run_id: str,
        filename: str,
        capability_id: str,
        kind: str,
        physical_worktree_fingerprint: str | None = None,
    ) -> tuple[str, str]:
        run_dir = self.store.guard.directory(
            self.store.directories["runs"] / run_id, create=True
        )
        path = self.store.guard.leaf(run_dir / filename)
        if path.exists():
            raise LeaseError("Capability sidecar already exists")
        nonce = secrets.token_urlsafe(48)
        digest = "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        self.store.guard.write_json(
            path,
            {
                "schemaVersion": "1.0",
                "capabilityId": capability_id,
                "kind": kind,
                "nonce": nonce,
                "nonceSha256": digest,
                "physicalWorktreeFingerprint": physical_worktree_fingerprint
                or self.store.manager.identity.physical_worktree_fingerprint,
                "status": "active",
            },
        )
        return os.fspath(path), digest

    def _verify_sidecar(
        self,
        reference: str | Path,
        digest: str,
        kind: str,
        *,
        physical_worktree_fingerprint: str | None = None,
    ) -> None:
        path = self.store.guard.leaf(reference, must_exist=True)
        value = self.store.guard.read_json(path)
        nonce = value.get("nonce")
        if (
            value.get("schemaVersion") != "1.0"
            or value.get("kind") != kind
            or value.get("status") != "active"
            or value.get("physicalWorktreeFingerprint")
            != (
                physical_worktree_fingerprint
                or self.store.manager.identity.physical_worktree_fingerprint
            )
            or not isinstance(nonce, str)
            or "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest() != digest
            or value.get("nonceSha256") != digest
        ):
            raise LeaseError("Capability sidecar is absent, revoked, or tampered")

    def _revoke_sidecar(self, reference: str | Path, digest: str, kind: str) -> None:
        path = self.store.guard.leaf(reference, must_exist=True)
        value = self.store.guard.read_json(path)
        if value.get("nonceSha256") != digest or value.get("kind") != kind:
            raise LeaseError("Capability sidecar cannot be safely revoked")
        self.store.guard.write_json(
            path,
            {
                "schemaVersion": "1.0",
                "capabilityId": value["capabilityId"],
                "kind": kind,
                "nonceSha256": digest,
                "physicalWorktreeFingerprint": value.get("physicalWorktreeFingerprint"),
                "status": "revoked",
            },
        )

    def _validate_workflow_unlocked(
        self, workflow_id: str, *, mapping: Mapping[str, Any] | None = None
    ) -> None:
        registry = self.store.manager.registry.load_unlocked()
        entry = registry["workflows"].get(workflow_id)
        if (
            entry is None
            or entry["repositoryId"] != self.store.manager.identity.repository_id
            or entry["repositoryKey"] != self.store.manager.repository_key
            or (
                mapping is not None
                and (
                    entry.get("physicalWorktreeFingerprint")
                    != mapping.get("physicalWorktreeFingerprint")
                    or os.path.normcase(
                        os.path.realpath(Path(entry["artifactPath"]).parent.parent)
                    )
                    != os.path.normcase(os.path.realpath(mapping["worktreePath"]))
                )
            )
        ):
            raise LeaseError("Prepared workflow is not registered to this repository authority")

    def _require_manager_authority(
        self, state: Mapping[str, Any], capability: Mapping[str, Any] | None = None
    ) -> None:
        current = state["currentWork"]
        if capability is not None and (
            current is None
            or capability.get("issueId") != current.get("issueId")
            or capability.get("worktreePath") != current.get("worktreePath")
            or capability.get("physicalWorktreeFingerprint")
            != current.get("physicalWorktreeFingerprint")
        ):
            raise LeaseError("Prepared capability is not the current issue-worktree authority")

    def _validate_checkpoint_bindings(
        self,
        state: dict[str, Any],
        prepared: dict[str, Any],
        result: dict[str, Any],
        transition_id: str,
        expected_stage: str,
    ) -> None:
        expected = {
            "preparedIterationId": prepared["preparedIterationId"],
            "runId": prepared["runId"],
            "workflowId": prepared["workflowId"],
            "issueId": prepared["issueId"],
            "transitionId": transition_id,
            "completedStage": expected_stage,
        }
        for field, value in expected.items():
            if result.get(field) != value:
                raise LeaseError(f"Checkpoint {field} binding is mismatched")
        if state["currentWork"] is None or state["currentWork"]["stage"] != expected_stage:
            raise LeaseError("Checkpoint EngineCommand expectedStage is stale")
        mapping = state["issueWorktrees"].get(prepared["issueId"])
        if not isinstance(mapping, dict) or mapping.get("status") != "active":
            raise LeaseError("Checkpoint issue-worktree mapping is absent")
        if (
            mapping.get("workflowId") != prepared["workflowId"]
            or mapping.get("worktreePath") != prepared["worktreePath"]
            or mapping.get("physicalWorktreeFingerprint")
            != prepared["physicalWorktreeFingerprint"]
            or self.store.manager.identity.physical_worktree_fingerprint
            == mapping.get("physicalWorktreeFingerprint")
            or os.path.normcase(os.path.realpath(self.store.manager.repository_root))
            == os.path.normcase(os.path.realpath(mapping["worktreePath"]))
        ):
            raise LeaseError("Checkpoint differs from the authoritative issue worktree")
        self._validate_workflow_unlocked(prepared["workflowId"], mapping=mapping)
        fresh = self._observe_worktree(prepared["worktreePath"])
        if (
            fresh["repositoryId"] != mapping.get("repositoryId")
            or fresh["worktreePath"] != mapping.get("worktreePath")
            or fresh["physicalWorktreeFingerprint"]
            != mapping.get("physicalWorktreeFingerprint")
            or fresh["branch"] != mapping.get("branch")
        ):
            raise LeaseError("Checkpoint worktree no longer matches its authoritative mapping")
        observed = result.get("observed", {})
        if observed.get("repositoryId") != fresh["repositoryId"]:
            raise LeaseError("Checkpoint observed repository binding is mismatched")
        if (
            observed.get("physicalWorktreeFingerprint")
            != fresh["physicalWorktreeFingerprint"]
            or observed.get("headSha") != fresh["headSha"]
        ):
            raise LeaseError("Checkpoint observed worktree binding is mismatched")
        changed = self._canonical_changed_paths(result.get("changedPaths", []))
        artifacts = self._canonical_changed_paths(result.get("artifactManifest", []))
        if changed != fresh["changedPaths"]:
            raise LeaseError("Checkpoint changed-path evidence differs from Git")
        if not set(artifacts).issubset(set(changed)):
            raise LeaseError("Checkpoint artifact manifest is not present in Git changes")

    def _observe_worktree(self, worktree_path: str | Path) -> dict[str, Any]:
        identity = self.store.runtime.observe_repository_identity(worktree_path)
        repository = Path(identity.repository_root)

        def git(*arguments: str, allowed: tuple[int, ...] = (0,)) -> bytes:
            completed = subprocess.run(
                ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
                check=False,
                capture_output=True,
                shell=False,
            )
            if completed.returncode not in allowed:
                raise LeaseError("Checkpoint Git observation failed")
            return completed.stdout

        head = git("rev-parse", "--verify", "HEAD").decode("ascii", "strict").strip()
        symbolic = git("symbolic-ref", "--quiet", "--short", "HEAD", allowed=(0, 1))
        branch = symbolic.decode("utf-8", "strict").strip() or None
        changed = set(
            item.decode("utf-8", "strict")
            for item in git("diff", "--name-only", "-z", "HEAD", "--").split(b"\0")
            if item
        )
        changed.update(
            item.decode("utf-8", "strict")
            for item in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
            if item
        )
        return {
            "repositoryId": identity.repository_id,
            "physicalWorktreeFingerprint": identity.physical_worktree_fingerprint,
            "worktreePath": os.path.normcase(
                os.path.realpath(identity.repository_root)
            ).replace("\\", "/"),
            "headSha": head,
            "branch": branch,
            "changedPaths": self._canonical_changed_paths(changed),
        }

    @staticmethod
    def _canonical_changed_paths(values: Any) -> list[str]:
        if not isinstance(values, (list, tuple, set)):
            raise LeaseError("Checkpoint path evidence must be an array")
        result: list[str] = []
        folded: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not value or "\\" in value:
                raise LeaseError("Checkpoint path evidence is not canonical")
            path = Path(value)
            if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
                raise LeaseError("Checkpoint path evidence escapes the worktree")
            normalized = path.as_posix()
            key = normalized.casefold()
            if key in folded:
                raise LeaseError("Checkpoint path evidence contains a case alias")
            folded.add(key)
            result.append(normalized)
        return sorted(result, key=str.casefold)

    @staticmethod
    def _worker_next_stage(result: Mapping[str, Any]) -> str:
        outcome = result.get("outcome")
        proposed = result.get("proposedNextStage")
        if outcome in {"advanced", "completed"}:
            if not isinstance(proposed, str) or proposed == "paused":
                raise LeaseError("Advancing worker result requires a concrete next stage")
            return proposed
        if outcome in {"paused", "failed", "external-wait"}:
            if proposed not in {None, "paused"}:
                raise LeaseError("Non-advancing worker result may only propose paused")
            return "paused"
        raise LeaseError("Worker result outcome is invalid")

    @staticmethod
    def _expected(state: dict[str, Any], expected_revision: int) -> None:
        if state["revision"] != expected_revision:
            raise SupervisorConflictError("Supervisor state revision is stale")

    @staticmethod
    def _authority_barrier(state: dict[str, Any]) -> None:
        if state["handoffPending"] is not None:
            raise LeaseError("Handoff pending barrier suspends lease/capability mutation")
        if state["recovery"]["status"] != "clean":
            raise LeaseError("Protected recovery state blocks lease/capability mutation")

    @staticmethod
    def _renewal_barrier(state: dict[str, Any]) -> None:
        """Allow only exact lease lifecycle recovery through an expiry barrier."""

        if state["handoffPending"] is not None:
            raise LeaseError("Handoff pending barrier suspends lease/capability mutation")
        recovery = state["recovery"]
        if recovery["status"] == "clean":
            return
        if recovery["status"] == "required" and recovery["reason"] == "expired-lease":
            return
        raise LeaseError("Protected recovery state blocks lease renewal")

    @staticmethod
    def _duration(value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise LeaseError("Duration must be a positive integer nanosecond value")

    @staticmethod
    def _safe_id(value: Any, label: str) -> None:
        if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
            raise LeaseError(f"{label} is not a safe canonical identifier")

    @staticmethod
    def _require_lease(
        state: dict[str, Any], *, run_id: str, owner_id: str, capability_ref: str
    ) -> dict[str, Any]:
        lease = state["lease"]
        if (
            lease is None
            or lease["status"] != "live"
            or lease["runId"] != run_id
            or lease["ownerId"] != owner_id
            or lease["capabilityRef"] != capability_ref
        ):
            raise LeaseError("Lease owner, run, or capability authority is mismatched")
        return lease

    @staticmethod
    def _iso_time(value_ns: int) -> str:
        return datetime.fromtimestamp(value_ns / 1_000_000_000, timezone.utc).isoformat().replace("+00:00", "Z")
