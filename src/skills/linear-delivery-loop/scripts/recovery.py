"""Deterministic recovery from canonical local state and journal evidence."""

from __future__ import annotations

import copy
import os
import time
from pathlib import Path
from typing import Any, Mapping

from .operations import OperationJournal
from .store import SupervisorRecoveryError, SupervisorStore


class RecoveryManager:
    def __init__(
        self,
        store: SupervisorStore,
        *,
        lease_manager: Any | None = None,
        reservation_manager: Any | None = None,
        worktree_manager: Any | None = None,
    ):
        self.store = store
        self.journal = OperationJournal(store)
        self.lease_manager = lease_manager
        self.reservation_manager = reservation_manager
        self.worktree_manager = worktree_manager

    def recover(self, *, ignore_operation_id: str | None = None) -> dict[str, Any]:
        """Reconcile interrupted transactions, commands, reservations, and leases.

        Exact authoritative completion evidence is replayed as a completed
        journal. An unchanged state pair proves a pre-mutation interruption and
        is finalized as failed. Anything else is marked ambiguous and moves the
        repository behind the recovery authority barrier.
        """

        recovered_transactions = self.store.recover()
        worktree_allocations = (
            self.worktree_manager.reconcile_worktree_allocations()
            if self.worktree_manager is not None
            else {"schemaVersion": "1.0", "status": "ready", "allocations": []}
        )
        repaired_pre_action = self.journal.repair_pre_action_interruptions()
        recovered_operations: list[str] = []
        failed_operations: list[str] = []
        ambiguous_operations: list[str] = []

        pending_ids = self.journal.pending_ids(
            ignore_operation_id=ignore_operation_id
        )
        pending_ids.sort(
            key=lambda candidate: self.journal.load(candidate)["journal"]["operation"]
            == "Recover"
        )
        for operation_id in pending_ids:
            evidence = self.journal.load(operation_id)
            candidate = evidence.get("resultCandidate")
            if candidate is not None:
                classification = candidate["status"]
                result = candidate["result"]
            else:
                with self.store.mutex():
                    state, reservations = self.store.load_pair_unlocked()
                    classification, result = self._classify_pending(
                        evidence, state, reservations
                    )
            if classification == "ambiguous":
                self._protect_ambiguity(operation_id)
                ambiguous_operations.append(operation_id)
            elif classification == "completed":
                recovered_operations.append(operation_id)
            else:
                failed_operations.append(operation_id)
            self.journal.complete(
                operation_id=operation_id,
                operation=evidence["journal"]["operation"],
                request=evidence["request"],
                result=result,
                status=classification,
                error_code={
                    "completed": None,
                    "failed": "RECOVERED_NO_MUTATION",
                    "ambiguous": "AMBIGUOUS_OUTCOME",
                }[classification],
            )

        reclaimed_reservations: list[str] = []
        protected_reservations: list[str] = []
        lease_result: dict[str, Any] | None = None
        if not ambiguous_operations:
            reclaimed_reservations, protected_reservations = self._recover_reservations(
                ignore_operation_id=ignore_operation_id
            )
            lease_result = self._recover_lease()

        remaining = self.journal.pending_ids(ignore_operation_id=ignore_operation_id)
        recovery_state = self.store.load_state()["recovery"]
        protected = bool(
            ambiguous_operations
            or protected_reservations
            or remaining
            or recovery_state["status"] != "clean"
            or worktree_allocations.get("status") == "protected"
        ) or (lease_result is not None and lease_result.get("status") == "protected")
        return {
            "status": "protected" if protected else "ready",
            "recoveredTransactions": recovered_transactions,
            "repairedPreActionOperations": repaired_pre_action,
            "recoveredOperations": sorted(recovered_operations),
            "failedOperations": sorted(failed_operations),
            "ambiguousOperations": sorted(ambiguous_operations),
            "pendingOperations": remaining,
            "reclaimedReservations": sorted(reclaimed_reservations),
            "protectedReservations": sorted(protected_reservations),
            "lease": lease_result,
            "worktreeAllocations": worktree_allocations,
        }

    def _classify_pending(
        self,
        evidence: Mapping[str, Any],
        state: Mapping[str, Any],
        reservations: Mapping[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        journal = evidence["journal"]
        request = evidence["request"]
        operation = journal["operation"]
        current_hash = self.journal.pair_hash(state, reservations)
        if self._external_mutation_is_ambiguous(operation, request, state):
            return "ambiguous", {
                "status": "ambiguous",
                "error": "external-mutation-lacks-exact-reconciliation-proof",
            }
        if current_hash == journal["beforeStateHash"]:
            return "failed", {
                "status": "failed",
                "error": "interrupted-before-authoritative-mutation",
            }
        authoritative = self._authoritative_result(
            operation, request, state, reservations
        )
        if authoritative is not None:
            return "completed", authoritative
        known_failure = self._authoritative_failed_result(
            operation, request, state, reservations
        )
        if known_failure is not None:
            return "failed", known_failure
        if operation == "Handoff":
            return "ambiguous", {
                "status": "ambiguous",
                "error": "external-mutation-lacks-exact-reconciliation-proof",
            }
        return "ambiguous", {
            "status": "ambiguous",
            "error": "state-differs-without-exact-operation-proof",
        }

    @staticmethod
    def _authoritative_failed_result(
        operation: str,
        request: Mapping[str, Any],
        state: Mapping[str, Any],
        reservations: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        if operation != "Release":
            return None
        record = reservations.get("reservations", {}).get(
            request.get("reservationId")
        )
        if not isinstance(record, dict):
            return None
        summary = record.get("protectedWork", {})
        protected = bool(
            summary.get("dirty")
            or summary.get("unpushed")
            or summary.get("unmerged")
            or summary.get("prOpen")
            or not summary.get("accessible")
            or summary.get("ambiguous")
        )
        if (
            protected
            and record.get("status") == "live"
            and record.get("revision") == request.get("expectedReservationRevision")
            and record.get("releaseAuthorizationRef")
            == request.get("reservationControlRef")
            and state.get("revision") == request.get("expectedStateRevision")
            and reservations.get("revision")
            == request.get("expectedReservationsRevision", 0) + 1
        ):
            return {
                "status": "failed",
                "error": "protected-or-ambiguous-work-cannot-be-released",
            }
        return None

    @staticmethod
    def _external_mutation_is_ambiguous(
        operation: str,
        request: Mapping[str, Any],
        state: Mapping[str, Any],
    ) -> bool:
        if operation != "Cleanup":
            return False
        gate = state.get("gateWorktrees", {}).get(request.get("gateOperationId"))
        return (
            isinstance(gate, dict)
            and gate.get("status") in {"active", "cleanup-pending"}
            and not os.path.lexists(gate.get("worktreePath", ""))
        )

    def _authoritative_result(
        self,
        operation: str,
        request: Mapping[str, Any],
        state: Mapping[str, Any],
        reservations: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        expected_revision = request.get("expectedStateRevision")
        state_advanced_once = (
            isinstance(expected_revision, int)
            and state["revision"] == expected_revision + 1
        )
        lease = state.get("lease")
        if operation == "AcquireLease" and state_advanced_once and isinstance(lease, dict):
            if (
                lease.get("runId") == request.get("requestId")
                and lease.get("ownerId") == request.get("ownerId")
            ):
                return copy.deepcopy(lease)
        if operation == "RenewLease" and state_advanced_once and isinstance(lease, dict):
            if (
                lease.get("runId") == request.get("runId")
                and lease.get("ownerId") == request.get("ownerId")
                and self._lease_authority_matches_operation(
                    lease, request.get("requestId")
                )
            ):
                return copy.deepcopy(lease)
        if operation == "ReleaseLease" and state_advanced_once and lease is None:
            return {"status": "released", "stateRevision": state["revision"]}
        if operation == "PrepareIteration" and state_advanced_once:
            current = state.get("currentWork")
            if isinstance(current, dict) and all(
                current.get(key) == request.get(request_key)
                for key, request_key in (
                    ("runId", "runId"),
                    ("workflowId", "workflowId"),
                    ("issueId", "issueId"),
                    ("stage", "expectedStage"),
                )
            ):
                matches = [
                    capability
                    for capability in state["capabilities"].values()
                    if capability.get("status") == "issued"
                    and capability.get("kind") == "prepared-iteration"
                    and capability.get("runId") == current["runId"]
                    and capability.get("stage") == current["stage"]
                ]
                if len(matches) == 1:
                    capability = matches[0]
                    prepared_path = self.store.guard.leaf(
                        Path(capability["capabilityRef"]).parent
                        / f"{capability['capabilityId']}.prepared-iteration.json",
                        must_exist=True,
                    )
                    return self.store.guard.read_json(prepared_path)
        if operation == "ApplyCheckpoint" and state_advanced_once:
            checkpoint = state["checkpoints"].get(request.get("transitionId"))
            if checkpoint is not None:
                return copy.deepcopy(checkpoint)
        if operation == "Reserve":
            record = reservations["reservations"].get(request.get("requestId"))
            if (
                isinstance(record, dict)
                and record.get("reservationId") == request.get("requestId")
                and record.get("workflowId") == request.get("workflowId")
                and record.get("issueId") == request.get("issueId")
                and record.get("ownerId") == request.get("ownerId")
                and record.get("runId") == request.get("runId")
                and record.get("status") == "live"
                and record.get("revision") == 1
                and state["revision"] == request.get("expectedStateRevision")
                and reservations["revision"]
                == request.get("expectedReservationsRevision", 0) + 1
            ):
                return copy.deepcopy(record)
        if operation == "RenewReservation":
            record = reservations["reservations"].get(request.get("reservationId"))
            if (
                isinstance(record, dict)
                and record.get("status") == "live"
                and record.get("ownerId") == request.get("ownerId")
                and record.get("runId") == request.get("runId")
                and record.get("revision") == request.get("expectedReservationRevision", 0) + 1
                and state["revision"] == request.get("expectedStateRevision")
                and reservations["revision"]
                == request.get("expectedReservationsRevision", 0) + 1
            ):
                return copy.deepcopy(record)
        if operation == "AuthorizeMutation":
            authorization_id = request.get("requestId")
            if isinstance(authorization_id, str):
                path = self.store.guard.leaf(
                    self.store.directories["mutation-authorizations"]
                    / f"{authorization_id}.json"
                )
                if path.exists():
                    authorization = self.store.guard.read_json(path)
                    binding = authorization.get("binding", {})
                    record = reservations["reservations"].get(
                        request.get("reservationId")
                    )
                    if (
                        authorization.get("authorizationId") == authorization_id
                        and authorization.get("status") == "active"
                        and isinstance(binding, dict)
                        and isinstance(record, dict)
                        and binding.get("authorizationOperationId")
                        == authorization_id
                        and binding.get("operationId")
                        == request.get("targetOperationId")
                        and binding.get("reservationId")
                        == request.get("reservationId")
                        and binding.get("workflowId") == request.get("workflowId")
                        and binding.get("reservationRevision")
                        == request.get("expectedReservationRevision", 0) + 1
                        and record.get("revision")
                        == binding.get("reservationRevision")
                        and reservations["revision"]
                        == request.get("expectedReservationsRevision", 0) + 1
                        and isinstance(record.get("releaseAuthorizationRef"), str)
                    ):
                        return {
                            "schemaVersion": "1.0",
                            "authorizationId": authorization_id,
                            "operationId": binding.get("operationId"),
                            "reservationId": binding.get("reservationId"),
                            "authorizationRef": os.fspath(path),
                            "authorizationSha256": authorization.get("nonceSha256"),
                            "scope": binding.get("scope"),
                            "reservationRevision": binding.get(
                                "reservationRevision"
                            ),
                            "controlAuthorizationRef": record[
                                "releaseAuthorizationRef"
                            ],
                            "status": "active",
                        }
        if operation == "Release":
            record = reservations["reservations"].get(request.get("reservationId"))
            if (
                isinstance(record, dict)
                and record.get("status") == "released"
                and record.get("revision")
                == request.get("expectedReservationRevision", 0) + 1
                and reservations["revision"]
                == request.get("expectedReservationsRevision", 0) + 1
                and state["revision"]
                in {
                    request.get("expectedStateRevision"),
                    request.get("expectedStateRevision", 0) + 1,
                }
            ):
                return {
                    "status": "released",
                    "reservationId": record["reservationId"],
                    "reservationRevision": record["revision"],
                    "stateRevision": state["revision"],
                    "reservationsRevision": reservations["revision"],
                    "cleanupAuthorizationRefs": copy.deepcopy(
                        record["cleanupAuthorizationRefs"]
                    ),
                }
        if operation == "Cleanup":
            gate_id = request.get("gateOperationId")
            gate = state.get("gateWorktrees", {}).get(gate_id)
            record = reservations["reservations"].get(
                request.get("releasedReservationId")
            )
            if (
                isinstance(gate, dict)
                and gate.get("status") == "cleaned"
                and isinstance(record, dict)
                and record.get("status") == "released"
                and record.get("revision")
                == request.get("expectedReleasedReservationRevision", 0) + 1
                and reservations["revision"]
                == request.get("expectedReservationsRevision", 0) + 1
                and state["revision"]
                == request.get("expectedStateRevision", 0) + 1
            ):
                public_gate = (
                    self.worktree_manager._gate_public_record(gate)
                    if self.worktree_manager is not None
                    else copy.deepcopy(gate)
                )
                return {
                    "status": "clean",
                    "removed": [gate["worktreePath"]],
                    "gate": public_gate,
                    "cleanupAuthorizationRefs": copy.deepcopy(
                        record["cleanupAuthorizationRefs"]
                    ),
                    "reservationRevision": record["revision"],
                    "stateRevision": state["revision"],
                    "reservationsRevision": reservations["revision"],
                }
        if operation == "Recover" and self._recover_request_is_satisfied(
            request, state, reservations
        ):
            return {
                "status": "ready",
                "recoveredTransactions": [],
                "repairedPreActionOperations": [],
                "recoveredOperations": [],
                "failedOperations": [],
                "ambiguousOperations": [],
                "pendingOperations": [],
                "reclaimedReservations": [],
                "protectedReservations": [],
                "lease": None,
                "worktreeAllocations": {
                    "schemaVersion": "1.0",
                    "status": "ready",
                    "allocations": [],
                },
            }
        # Assembled Handoff owns richer destination/rollback evidence. Missing
        # exact proof remains ambiguous here and is never inferred from a
        # registry fingerprint alone.
        return None

    def _lease_authority_matches_operation(
        self, lease: Mapping[str, Any], operation_id: Any
    ) -> bool:
        """Prove that the current rotated lease came from one exact renewal."""

        if not isinstance(operation_id, str):
            return False
        reference = lease.get("capabilityRef")
        digest = lease.get("capabilitySha256")
        if (
            self.lease_manager is None
            or not isinstance(reference, str)
            or not isinstance(digest, str)
        ):
            return False
        try:
            self.lease_manager._verify_sidecar(reference, digest, "lease")
            authority = self.store.guard.read_json(
                self.store.guard.leaf(reference, must_exist=True)
            )
        except Exception:
            return False
        return (
            authority.get("schemaVersion") == "1.0"
            and authority.get("capabilityId") == operation_id
            and authority.get("kind") == "lease"
            and authority.get("status") == "active"
            and authority.get("nonceSha256") == digest
        )

    def _recover_request_is_satisfied(
        self,
        request: Mapping[str, Any],
        state: Mapping[str, Any],
        reservations: Mapping[str, Any],
    ) -> bool:
        if state["recovery"]["status"] != "clean" or state["handoffPending"] is not None:
            return False
        lease = state.get("lease")
        if isinstance(lease, dict) and self.lease_manager is not None:
            if self.lease_manager.clock.now_ns() >= lease["expiresAtNs"]:
                return False
        if self.reservation_manager is not None:
            now = self.reservation_manager._now()
            if any(
                record.get("status") in {"live", "handoff-pending"}
                and now >= record.get("expiresAtNs", now + 1)
                for record in reservations["reservations"].values()
            ):
                return False
        for pending_id in self.journal.pending_ids(
            ignore_operation_id=request.get("requestId")
        ):
            if self.journal.load(pending_id)["journal"]["operation"] != "Recover":
                return False
        return True

    def _protect_ambiguity(self, operation_id: str) -> None:
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            reason = f"ambiguous-operation:{operation_id}"
            if (
                state["recovery"]["status"] == "ambiguous"
                and state["recovery"]["reason"] == reason
            ):
                return
            after = copy.deepcopy(state)
            after["recovery"] = {
                "status": "ambiguous",
                "reason": reason,
                "updatedAtNs": max(
                    time.time_ns(), state["clockEvidence"]["lastObservedNowNs"]
                ),
            }
            after["revision"] = state["revision"] + 1
            self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation=f"Recover:ambiguous:{operation_id}",
            )

    def _recover_reservations(
        self, *, ignore_operation_id: str | None
    ) -> tuple[list[str], list[str]]:
        if self.reservation_manager is None:
            return [], []
        reclaimed: list[str] = []
        protected: list[str] = []
        snapshot = self.store.load_reservations()
        now = self.reservation_manager._now()
        candidates = [
            record["reservationId"]
            for record in snapshot["reservations"].values()
            if record.get("status") in {"live", "handoff-pending"}
            and now >= record.get("expiresAtNs", now + 1)
        ]
        for reservation_id in sorted(candidates):
            state = self.store.load_state()
            reservations = self.store.load_reservations()
            try:
                self.reservation_manager.reclaim_expired(
                    reservation_id=reservation_id,
                    expected_state_revision=state["revision"],
                    expected_reservations_revision=reservations["revision"],
                    ignore_operation_id=ignore_operation_id,
                )
                reclaimed.append(reservation_id)
            except Exception:
                protected.append(reservation_id)
        return reclaimed, protected

    def _recover_lease(self) -> dict[str, Any] | None:
        if self.lease_manager is None:
            return None
        state = self.store.load_state()
        return self.lease_manager.recover_expired(
            expected_revision=state["revision"]
        )


def recover_supervisor(
    store: SupervisorStore,
    *,
    ignore_operation_id: str | None = None,
    lease_manager: Any | None = None,
    reservation_manager: Any | None = None,
    worktree_manager: Any | None = None,
) -> dict[str, Any]:
    return RecoveryManager(
        store,
        lease_manager=lease_manager,
        reservation_manager=reservation_manager,
        worktree_manager=worktree_manager,
    ).recover(ignore_operation_id=ignore_operation_id)
