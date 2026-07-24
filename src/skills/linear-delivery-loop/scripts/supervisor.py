"""Composed deterministic supervisor facade for state-engine operations."""

from __future__ import annotations

import copy
import os
from datetime import datetime, timedelta, timezone
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .base_runtime import load_base_runtime
from .lease import Clock, LeaseManager
from .operations import OperationJournal, PublicationJournal
from .recovery import RecoveryManager
from .reservations import ReservationManager
from .store import SupervisorStore, SupervisorStoreError
from .worktrees import WorktreeManager
from .publication_provider import PublicationProviderCoordinator, ProviderOperationRefused
from .exact_sha_gates import EvidenceConvergence, ExactShaGateRunner, ExactShaGateError
from .publication_recovery import MergeRepairPolicy, PublicationRecovery, TRANSIENT, classify_refusal
from .publication_records import ATTESTATION_PRODUCERS, retry_delay_minutes, sha256_json


def _linear_issue_link(issue_id: str) -> str:
    return f"https://linear.app/issue/{issue_id}"


class SupervisorEngine:
    """One repository-bound state engine; transport and selection remain outside."""

    __slots__ = (
        "runtime", "manager", "store", "operations", "leases", "reservations",
        "worktrees", "recovery", "publication_operations", "publication_provider",
        "publication_gate_runner", "extra_handlers",
        "publication_recovery",
        "publication_git",
    )

    OPERATION_NAMES = frozenset(
        {
            "Preflight",
            "AcquireLease",
            "RenewLease",
            "PrepareIteration",
            "ApplyCheckpoint",
            "Status",
            "Reserve",
            "RenewReservation",
            "AuthorizeMutation",
            "Release",
            "Recover",
            "Cleanup",
            "Handoff",
            "ReleaseLease",
            "PreparePublication",
            "PublicationProvider",
            "PublicationGate",
            "RecoverPublication",
            "RecordPublicationAttestation",
            "PublicationRepair",
        }
    )

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {
            "_control_plane_registries", "_control_plane_registry",
            "describe_control_plane_reference", "execute_control_plane_operation",
        }:
            raise AttributeError("Control-plane ownership cannot be caller-replaced")
        object.__setattr__(self, name, value)

    def __init__(
        self,
        repository_root: str | Path | None = None,
        *,
        repository_key: str | None = None,
        state_home_override: str | Path | None = None,
        environment: dict[str, str] | None = None,
        manager: Any | None = None,
        clock: Clock | None = None,
        reservation_clock: Callable[[], int] | None = None,
        local_observer: Callable[..., dict[str, Any]] | None = None,
        extra_handlers: Mapping[str, Callable[..., dict[str, Any]]] | None = None,
        publication_provider: Any | None = None,
        publication_gate_runner: Callable[..., Any] | None = None,
        publication_recovery: PublicationRecovery | None = None,
        publication_git: Any | None = None,
    ):
        runtime = load_base_runtime()
        if manager is None:
            if repository_root is None or repository_key is None:
                raise SupervisorStoreError(
                    "Supervisor requires a canonical manager or repository root/key"
                )
            manager = runtime.WorkflowManager(
                repository_root,
                repository_key=repository_key,
                state_home_override=state_home_override,
                environment=environment,
            )
        elif not isinstance(manager, runtime.WorkflowManager):
            raise SupervisorStoreError("Supervisor manager is not the canonical base runtime")
        self.runtime = runtime
        self.manager = manager
        self.store = SupervisorStore(manager, runtime=runtime)
        self.operations = OperationJournal(self.store)
        self.publication_operations = PublicationJournal(self.store)
        self.publication_provider = (
            PublicationProviderCoordinator(publication_provider)
            if publication_provider is not None else None
        )
        self.publication_gate_runner = publication_gate_runner
        self.publication_recovery = publication_recovery
        self.publication_git = publication_git
        self.leases = LeaseManager(self.store, clock=clock)
        self.reservations = ReservationManager(
            manager,
            self.store,
            clock=reservation_clock,
            local_observer=local_observer,
        )
        self.worktrees = WorktreeManager(
            manager.repository_root,
            repository_key=manager.repository_key,
            state_home_override=manager.home.base,
            store=self.store,
        )
        self.recovery = RecoveryManager(
            self.store,
            lease_manager=self.leases,
            reservation_manager=self.reservations,
            worktree_manager=self.worktrees,
        )
        self.extra_handlers = dict(extra_handlers or {})
        unknown = set(self.extra_handlers) - self.OPERATION_NAMES
        if unknown:
            raise SupervisorStoreError("Supervisor received an unknown operation handler")

    def describe_control_plane_reference(self, reference: str) -> dict[str, str]:
        """Return non-authority metadata for an engine-owned opaque reference.

        SAAS-47 deliberately does not activate a live provider.  A later
        integration may implement this closed operation against durable engine
        configuration; production callers cannot install adapters here.
        """

        raise SupervisorStoreError("Control-plane provider is not activated")

    def execute_control_plane_operation(
        self,
        reference: str,
        operation: str,
        payload: Mapping[str, Any],
        *,
        linear: Any,
    ) -> Any:
        """Execute one closed provider/repository operation inside the owner.

        No callback, adapter, registry entry, or repository authority crosses
        this boundary.  Fixture composition is supplied only by test support.
        """

        allowed = {
            "observe-issues", "observe-selection", "claim-reread", "claim",
            "claim-readback", "current-execution-lease", "authorize-recovery",
            "prepare", "commit", "rollback-if-safe", "protect", "recover",
        }
        if operation not in allowed or not isinstance(payload, Mapping):
            raise SupervisorStoreError("Control-plane operation is not closed")
        raise SupervisorStoreError("Control-plane provider is not activated")

    def status(self) -> dict[str, Any]:
        from .repository_memory import memory_status_snapshot

        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            public_reservations = copy.deepcopy(reservations["reservations"])
            for record in public_reservations.values():
                # Status is observation, never an authority-distribution channel.
                # Reserve/Renew/Authorize/Release return their newly issued opaque
                # references only to the exact journaled operation that created them.
                record.pop("releaseAuthorizationRef", None)
                record.pop("cleanupAuthorizationRefs", None)
            public_lease = copy.deepcopy(state["lease"])
            if public_lease is not None:
                # Run/owner/timing data is useful for scheduling, but the
                # opaque sidecar reference and its digest are mutation
                # authority distributed only by AcquireLease/RenewLease.
                public_lease.pop("capabilityRef", None)
                public_lease.pop("capabilitySha256", None)
            return {
                "schemaVersion": "1.0",
                "repositoryId": self.manager.identity.repository_id,
                "repositoryKey": self.manager.repository_key,
                "stateRevision": state["revision"],
                "reservationsRevision": reservations["revision"],
                "lease": public_lease,
                "currentWork": copy.deepcopy(state["currentWork"]),
                "publication": copy.deepcopy(state["publication"]),
                "recovery": copy.deepcopy(state["recovery"]),
                "handoffPending": copy.deepcopy(state["handoffPending"]),
                "reservations": public_reservations,
                "memory": memory_status_snapshot(
                    self.store.root,
                    repository_id=self.manager.identity.repository_id,
                    repository_key=self.manager.repository_key,
                    state_guard=self.store.guard,
                ),
            }

    def dispatch(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if operation not in self.OPERATION_NAMES:
            raise SupervisorStoreError("Unknown supervisor operation")
        if not isinstance(payload, Mapping):
            raise SupervisorStoreError("Supervisor operation payload must be an object")
        arguments = dict(payload)
        handlers: dict[str, Callable[..., dict[str, Any]]] = {
            "AcquireLease": self.leases.acquire,
            "RenewLease": self.leases.renew,
            "PrepareIteration": self.leases.prepare_iteration,
            "ApplyCheckpoint": self.leases.apply_checkpoint,
            "Status": lambda **_: self.status(),
            "Reserve": self.reservations.reserve,
            "RenewReservation": self.reservations.renew,
            "AuthorizeMutation": self.reservations.authorize_mutation,
            "Release": self.reservations.release,
            "Recover": lambda **_: self.recovery.recover(),
            "ReleaseLease": self.leases.release,
            "PreparePublication": self.prepare_publication,
            "PublicationProvider": self.execute_publication_provider,
            "PublicationGate": self.execute_publication_gate,
            "RecoverPublication": self.recover_publication,
            "RecordPublicationAttestation": self.record_publication_attestation,
            "PublicationRepair": self.next_publication_repair,
        }
        handler = self.extra_handlers.get(operation) or handlers.get(operation)
        if handler is None:
            raise SupervisorStoreError(
                f"Operation {operation} requires its assembled deterministic handler"
            )
        return handler(**arguments)

    # Stable explicit names used by CLI adapters and tests.
    def acquire_lease(self, **arguments: Any) -> dict[str, Any]:
        return self.leases.acquire(**arguments)

    def renew_lease(self, **arguments: Any) -> dict[str, Any]:
        return self.leases.renew(**arguments)

    def release_lease(self, **arguments: Any) -> dict[str, Any]:
        return self.leases.release(**arguments)

    def prepare_iteration(self, **arguments: Any) -> dict[str, Any]:
        return self.leases.prepare_iteration(**arguments)

    def apply_checkpoint(self, **arguments: Any) -> dict[str, Any]:
        return self.leases.apply_checkpoint(**arguments)

    def reserve(self, **arguments: Any) -> dict[str, Any]:
        return self.reservations.reserve(**arguments)

    def renew_reservation(self, **arguments: Any) -> dict[str, Any]:
        return self.reservations.renew(**arguments)

    def authorize_mutation(self, **arguments: Any) -> dict[str, Any]:
        return self.reservations.authorize_mutation(**arguments)

    def release_reservation(self, **arguments: Any) -> dict[str, Any]:
        return self.reservations.release(**arguments)

    def _publication_authority(
        self, publication: Mapping[str, Any], *, expected_state_revision: int,
        for_merge: bool = False,
    ) -> dict[str, Any]:
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            if state["revision"] != expected_state_revision:
                raise SupervisorStoreError("Publication supervisor CAS is stale")
            self._publication_local_authority(state, reservations, publication)
        observed = publication.get("authorityReadback")
        if not isinstance(observed, Mapping):
            raise SupervisorStoreError("Publication lacks durable provider/control-plane readback")
        labels = set(observed["labels"])
        if "autonomous" not in labels or labels & {"stop", "blocked", "needs-human"}:
            raise SupervisorStoreError("Publication stop/authorization labels forbid mutation")
        if for_merge:
            pull_request = publication.get("pullRequest")
            if (
                not isinstance(pull_request, Mapping)
                or str(pull_request.get("id")) != str(observed["pullRequestId"])
                or observed["baseRef"] != publication["baseRef"]
                or observed["headSha"] != publication["headSha"]
                or observed["mergeability"] is not True
            ):
                raise SupervisorStoreError("Pre-merge PR/base/head/mergeability reread is stale")
        return observed

    def _publication_local_authority(
        self, state: Mapping[str, Any], reservations: Mapping[str, Any],
        publication: Mapping[str, Any],
    ) -> None:
        now = self.reservations._now()
        lease = state.get("lease")
        current = state.get("currentWork")
        reservation = reservations["reservations"].get(
            publication["preservedState"]["reservationId"]
        )
        if (
            not isinstance(lease, Mapping) or lease.get("status") != "live"
            or lease.get("expiresAtNs", 0) <= now
            or not isinstance(current, Mapping)
            or current.get("workflowId") != publication["workflowId"]
            or current.get("issueId") != publication["issueId"]
            or current.get("stage") not in {"review", "qa", "docs", "publication", "completion"}
            or not isinstance(reservation, Mapping) or reservation.get("status") != "live"
            or reservation.get("expiresAtNs", 0) <= now
            or reservation.get("workflowId") != publication["workflowId"]
            or reservation.get("issueId") != publication["issueId"]
            or reservation.get("physicalWorktreeFingerprint")
            != publication["preservedState"]["physicalWorktreeFingerprint"]
        ):
            raise SupervisorStoreError("Publication lease/reservation/stage authority is stale")
        return None

    def _consume_publication_authorization(
        self, *, publication: Mapping[str, Any], mutation_id: str, mutation_kind: str,
        reservation_id: str, authorization_ref: str,
        expected_record_revision: int, expected_state_revision: int,
        expected_reservations_revision: int, physical_worktree_fingerprint: str,
    ) -> None:
        """Consume one exact, revision-bound grant for one publication mutation."""
        expected_scope = [
            f"publication/{publication['operationId']}/{mutation_kind}/{mutation_id}.json"
        ]
        self.reservations.execute_authorized_mutation(
            reservation_id=reservation_id,
            authorization_ref=authorization_ref,
            operation_id=mutation_id,
            required_scope=expected_scope,
            expected_record_revision=expected_record_revision,
            expected_state_revision=expected_state_revision,
            expected_reservations_revision=expected_reservations_revision,
            physical_worktree_fingerprint=physical_worktree_fingerprint,
            mutation=lambda _record, _state: {
                "operationId": mutation_id, "scope": expected_scope,
                "status": "authorized",
            },
        )

    def _require_consumed_publication_authorization(
        self, *, publication: Mapping[str, Any], mutation_id: str,
        mutation_kind: str, reservation_id: str, authorization_ref: str,
        expected_record_revision: int, expected_state_revision: int,
        physical_worktree_fingerprint: str,
    ) -> None:
        """Prove an exact replay grant was consumed before the Git commit."""

        authorization_path = self.store.guard.leaf(authorization_ref, must_exist=True)
        if authorization_path.parent != self.store.directories["mutation-authorizations"]:
            raise SupervisorStoreError("Committed replay authorization is outside its namespace")
        authorization = self.store.guard.read_json(authorization_path)
        authorization_id = authorization.get("authorizationId")
        sidecar = self.store.guard.read_json(
            self.store.guard.leaf(
                authorization_path.parent / f"{authorization_id}.capability.json",
                must_exist=True,
            )
        )
        reservations = self.store.load_reservations()
        record = reservations["reservations"].get(reservation_id)
        expected_scope = [
            f"publication/{publication['operationId']}/{mutation_kind}/{mutation_id}.json"
        ]
        binding = authorization.get("binding") or {}
        expected = {
            "reservationId": reservation_id,
            "workflowId": publication["workflowId"],
            "issueId": publication["issueId"],
            "repositoryId": publication["repositoryId"],
            "repositoryKey": publication["repositoryKey"],
            "runId": record.get("runId") if isinstance(record, Mapping) else None,
            "operationId": mutation_id,
            "stateRevision": expected_state_revision,
            "reservationRevision": expected_record_revision,
            "physicalWorktreeFingerprint": physical_worktree_fingerprint,
            "scope": expected_scope,
        }
        if (
            not isinstance(record, Mapping) or record.get("status") != "live"
            or authorization.get("status") != "consumed"
            or sidecar.get("status") != "consumed"
            or sidecar.get("authorizationId") != authorization_id
            or sidecar.get("kind") != "mutation"
            or sidecar.get("nonceSha256") != authorization.get("nonceSha256")
            or authorization_id not in reservations.get("consumedAuthorizationIds", [])
            or any(binding.get(key) != value for key, value in expected.items())
            or record.get("workflowId") != publication["workflowId"]
            or record.get("issueId") != publication["issueId"]
            or record.get("repositoryId") != publication["repositoryId"]
            or record.get("repositoryKey") != publication["repositoryKey"]
            or record.get("physicalWorktreeFingerprint") != physical_worktree_fingerprint
        ):
            raise SupervisorStoreError("Committed publication replay lacks exact consumed authority")

    def _require_merge_evidence(self, publication: Mapping[str, Any]) -> None:
        evidence = publication["attestations"]
        required = {"pre-staging-aggregate", "exact-head-aggregate", "review", "docs", "evidence-convergence"}
        if not required.issubset(evidence) or not ({"qa", "qa-reuse"} & set(evidence)):
            raise SupervisorStoreError("Pre-merge exact-head evidence set is incomplete")
        for name in required | ({"qa"} if "qa" in evidence else {"qa-reuse"}):
            record = evidence[name]
            self.publication_operations.require_issued_attestation(record)
            if (
                record.get("publicationOperationId") != publication["operationId"]
                or record.get("exactSha") != publication["headSha"]
                or record.get("result") != "passed"
            ):
                raise SupervisorStoreError(f"Pre-merge {name} attestation is stale or failed")
        if publication["evidenceFinalizationCount"] != 1:
            raise SupervisorStoreError("Evidence convergence has not finalized exactly once")
        finalization = publication.get("evidenceFinalization")
        preparation = publication.get("preparation")
        if not isinstance(finalization, Mapping) or finalization.get("headSha") != publication["headSha"]:
            raise SupervisorStoreError("Engine-owned evidence finalization is absent or stale")
        if not isinstance(preparation, Mapping) or preparation.get("baseSha") != publication["baseSha"]:
            raise SupervisorStoreError("Engine-owned manifest preparation is absent or stale")
        policy_attestations = {
            name: {"exactSha": record["exactSha"]}
            for name, record in evidence.items()
            if name in {"exact-head-aggregate", "review", "qa", "docs"}
        }
        if "qa" not in policy_attestations and "qa-reuse" in evidence:
            policy_attestations["qa"] = {"exactSha": evidence["qa-reuse"]["exactSha"]}
        MergeRepairPolicy.premerge(
            head_sha=publication["headSha"], base_ref=publication["baseRef"],
            authority={"orderedState": True, "evidenceConverged": True},
            attestations=policy_attestations,
        )
        EvidenceConvergence.require_final_evidence(
            exact_sha_value=publication["headSha"], attestations=evidence,
            qa_reuse={"fromSha": evidence.get("qa-reuse", {}).get("provenanceRef"),
                "toSha": publication["headSha"], "safeNoBehavioralEffect": True,
                "reviewer": evidence.get("qa-reuse", {}).get("attestationId")}
            if "qa-reuse" in evidence else None,
        )
        if publication["repairAttempt"]:
            repair_gates = {
                name: {"exactSha": evidence[name]["exactSha"], "passed": evidence[name]["result"] == "passed"}
                for name in ("pre-staging-aggregate", "exact-head-aggregate", "review", "qa", "docs", "evidence-convergence")
            }
            MergeRepairPolicy.require_repair_pipeline(
                repair_head=publication["headSha"], gates=repair_gates, phase="pre-merge"
            )

    def _bind_repair_worktree(self, publication: Mapping[str, Any]) -> None:
        """CAS-bind a real numbered repair branch/head to the existing issue worktree."""
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            mapping = state["issueWorktrees"].get(publication["issueId"])
            if (
                not isinstance(mapping, Mapping)
                or mapping.get("status") != "active"
                or os.path.normcase(os.path.realpath(mapping.get("worktreePath", "")))
                != os.path.normcase(os.path.realpath(publication["preservedState"]["worktreePath"]))
                or mapping.get("physicalWorktreeFingerprint")
                != publication["preservedState"]["physicalWorktreeFingerprint"]
            ):
                raise SupervisorStoreError("repair worktree mapping authority changed")
            after = copy.deepcopy(state)
            after["issueWorktrees"][publication["issueId"]]["branch"] = publication["branch"]
            after["issueWorktrees"][publication["issueId"]]["headSha"] = publication["headSha"]
            after["revision"] = state["revision"] + 1
            lease = after.get("lease")
            current = after.get("currentWork") or {}
            if isinstance(lease, dict) and lease.get("status") == "live":
                lease["revision"] = after["revision"]
                for capability in after.get("capabilities", {}).values():
                    if (
                        capability.get("status") == "issued"
                        and capability.get("runId") == lease.get("runId")
                        and capability.get("stage") == current.get("stage")
                    ):
                        capability["stateRevision"] = after["revision"]
            self.store.commit_pair_unlocked(
                before_state=state, after_state=after,
                before_reservations=reservations, after_reservations=reservations,
                operation=f"PublicationRepairWorktree:{publication['operationId']}:{publication['repairAttempt']}",
            )

    def _attended_publication_rereads(
        self, *, publication: Mapping[str, Any], observed: Mapping[str, Any],
        attended: Mapping[str, Any], reservation_id: str, authorization_ref: str,
        recovery_operation_id: str, physical_worktree_fingerprint: str,
    ) -> dict[str, bool]:
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
        reservation = reservations["reservations"].get(reservation_id)
        request_state = self.publication_recovery.requests.store.load()
        request = next((item for item in request_state["publicationRequests"] if item["id"] == attended.get("request_id")), None)
        authorization = self.reservations._resolve_authorization(authorization_ref, expected_kind="mutation")
        binding = authorization["binding"]
        issue_worktree = state["issueWorktrees"].get(publication["issueId"])
        summary = state.get("publication") or {}
        refusal = self.publication_operations.require_refusal(
            publication["operationId"], publication["providerEvidenceRef"]
        )
        attestations_valid = True
        try:
            for record in publication["attestations"].values():
                self.publication_operations.require_issued_attestation(record)
        except Exception:
            attestations_valid = False
        pull_request = publication.get("pullRequest") or {}
        request_data = (request or {}).get("data", {})
        branch_valid = observed.get("expectedHeadSha") == publication["headSha"]
        if publication["repairAttempt"] and self.publication_git is not None:
            branch_valid = branch_valid and self.publication_git.branch_head(publication["branch"]) == publication["headSha"]
        return {
            "issue": bool(request) and request.get("status") == "pending" and request.get("issueId") == publication["issueId"] and request_data.get("evidence", {}).get("issueState") == publication["preservedState"]["issueState"] and {"autonomous", "blocked", "needs-human"}.issubset(set(observed.get("labels", []))) and "stop" not in observed.get("labels", []),
            "authorization": authorization.get("status") == "active" and binding.get("operationId") == recovery_operation_id and binding.get("reservationId") == reservation_id and binding.get("scope") == [f"publication/{publication['operationId']}/provider-{publication['activeProviderOperation']}/{recovery_operation_id}.json"],
            "reservation": isinstance(reservation, Mapping) and reservation.get("status") == "live" and reservation.get("issueId") == publication["issueId"] and reservation.get("physicalWorktreeFingerprint") == physical_worktree_fingerprint,
            "worktree": isinstance(issue_worktree, Mapping) and issue_worktree.get("status") == "active" and os.path.normcase(os.path.realpath(issue_worktree.get("worktreePath", ""))) == os.path.normcase(os.path.realpath(publication["preservedState"]["worktreePath"])) and issue_worktree.get("physicalWorktreeFingerprint") == physical_worktree_fingerprint,
            "journal": self.publication_operations.load(publication["operationId"]) == publication and summary.get("transitionDigest") == sha256_json(publication),
            "branch": branch_valid,
            "pullRequest": str(observed.get("pullRequestId")) == str(pull_request.get("id")),
            "head": (
                observed.get("expectedHeadSha") == publication["headSha"]
                and (
                    observed.get("headSha") == publication["headSha"]
                    or publication.get("activeProviderOperation") == "push"
                )
            ),
            "base": observed.get("baseRef") == publication["baseRef"],
            "mergeability": observed.get("mergeability") is True,
            "attestations": attestations_valid,
            "provider": refusal["digest"] == publication["providerEvidenceRef"] and publication["providerOperationIds"].get(publication["activeProviderOperation"]) is not None,
        }

    def prepare_publication(
        self, *, publication_state: Mapping[str, Any], expected_state_revision: int,
        artifact_manifest: list[str], preexisting_paths: list[str], preparation_operation_id: str,
        reservation_id: str, authorization_ref: str, expected_record_revision: int,
        expected_reservations_revision: int, physical_worktree_fingerprint: str,
        replay_committed: bool = False,
    ) -> dict[str, Any]:
        existing = None
        try:
            existing = self.publication_operations.load(publication_state["operationId"])
        except Exception:
            pass
        if isinstance(existing, Mapping) and existing.get("status") == "base-drift":
            publication_state = copy.deepcopy(dict(existing))
            if replay_committed:
                replay = self.publication_git.reconcile_committed_operation(
                    operation_id=preparation_operation_id, paths=artifact_manifest,
                    trailer="Publication-Operation", preexisting_paths=preexisting_paths,
                )
                if replay is None:
                    raise SupervisorStoreError("Drift replay lacks its immutable committed operation")
                self._require_consumed_publication_authorization(
                    publication=publication_state, mutation_id=preparation_operation_id,
                    mutation_kind="prepare", reservation_id=reservation_id,
                    authorization_ref=authorization_ref, expected_record_revision=expected_record_revision,
                    expected_state_revision=expected_state_revision,
                    physical_worktree_fingerprint=physical_worktree_fingerprint,
                )
                expected_state_revision = self.store.load_state()["revision"]
            else:
                self._consume_publication_authorization(
                    publication=publication_state, mutation_id=preparation_operation_id,
                    mutation_kind="prepare", reservation_id=reservation_id,
                    authorization_ref=authorization_ref, expected_record_revision=expected_record_revision,
                    expected_state_revision=expected_state_revision,
                    expected_reservations_revision=expected_reservations_revision,
                    physical_worktree_fingerprint=physical_worktree_fingerprint,
                )
            preparation = self.publication_git.reprepare_committed_head(
                branch=publication_state["branch"], manifest=artifact_manifest,
                preexisting_paths=preexisting_paths, operation_id=preparation_operation_id,
            )
            publication_state.update({"status": "prepared", "preparation": preparation,
                "baseSha": preparation["baseSha"], "headSha": preparation["headSha"]})
            aggregate_attestation = {
                "schemaVersion": "1.0", "attestationId": preparation_operation_id,
                "publicationOperationId": publication_state["operationId"], "kind": "pre-staging-aggregate",
                "producer": "gate-runner", "stage": "pre-merge", "result": "passed",
                "provenanceRef": preparation["aggregateDigest"], "exactSha": preparation["headSha"],
                "issuedStateRevision": expected_state_revision, "recordedAt": publication_state["updatedAt"],
            }
            self.publication_operations.issue_attestation(aggregate_attestation)
            publication_state["attestations"] = {"pre-staging-aggregate": aggregate_attestation}
            publication_state["authorityReadback"] = self.publication_provider.authority_readback(
                issue_id=publication_state["issueId"], branch=publication_state["branch"],
                base_ref=publication_state["baseRef"], head_sha=publication_state["headSha"],
            )
            saved = self.publication_operations.save_authoritative(
                publication_state, expected_state_revision=self.store.load_state()["revision"]
            )
            self._bind_repair_worktree(publication_state)
            return saved
        if publication_state.get("status") != "prepared" or any(
            value is not None for value in publication_state.get("providerOperationIds", {}).values()
        ) or publication_state.get("attestations") != {} or publication_state.get("evidenceFinalizationCount") != 0 or publication_state.get("authorityReadback") is not None:
            raise SupervisorStoreError("Publication preparation state is not initial")
        if self.publication_provider is None or self.publication_git is None:
            raise SupervisorStoreError("Publication Git/provider boundaries are not activated")
        publication_state = copy.deepcopy(dict(publication_state))
        if replay_committed:
            replay = self.publication_git.reconcile_committed_operation(
                operation_id=preparation_operation_id, paths=artifact_manifest,
                trailer="Publication-Operation", preexisting_paths=preexisting_paths,
            )
            if replay is None:
                raise SupervisorStoreError("Primary replay lacks its immutable committed operation")
            self._require_consumed_publication_authorization(
                publication=publication_state, mutation_id=preparation_operation_id,
                mutation_kind="prepare", reservation_id=reservation_id,
                authorization_ref=authorization_ref, expected_record_revision=expected_record_revision,
                expected_state_revision=expected_state_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
            expected_state_revision = self.store.load_state()["revision"]
        else:
            self._consume_publication_authorization(
                publication=publication_state, mutation_id=preparation_operation_id,
                mutation_kind="prepare", reservation_id=reservation_id,
                authorization_ref=authorization_ref,
                expected_record_revision=expected_record_revision,
                expected_state_revision=expected_state_revision,
                expected_reservations_revision=expected_reservations_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
        preparation = self.publication_git.prepare_primary(
            issue_id=publication_state["issueId"], branch=publication_state["branch"],
            manifest=artifact_manifest, preexisting_paths=preexisting_paths,
            operation_id=preparation_operation_id,
        )
        publication_state.update({
            "branch": preparation["branch"], "baseSha": preparation["baseSha"],
            "headSha": preparation["headSha"], "preparation": preparation,
        })
        aggregate_attestation = {
            "schemaVersion": "1.0", "attestationId": publication_state["operationId"] + ".prepare",
            "publicationOperationId": publication_state["operationId"], "kind": "pre-staging-aggregate",
            "producer": "gate-runner", "stage": "pre-merge", "result": "passed",
            "provenanceRef": preparation["aggregateDigest"], "exactSha": preparation["headSha"],
            "issuedStateRevision": expected_state_revision, "recordedAt": publication_state["updatedAt"],
        }
        self.publication_operations.issue_attestation(aggregate_attestation)
        publication_state["attestations"]["pre-staging-aggregate"] = aggregate_attestation
        publication_state["authorityReadback"] = self.publication_provider.authority_readback(
            issue_id=publication_state["issueId"], branch=publication_state["branch"],
            base_ref=publication_state["baseRef"], head_sha=publication_state["headSha"],
        )
        self._publication_authority(publication_state, expected_state_revision=expected_state_revision)
        saved = self.publication_operations.save_authoritative(
            publication_state, expected_state_revision=expected_state_revision,
            authority_check=lambda state, reservations: self._publication_local_authority(
                state, reservations, publication_state
            ),
        )
        self._bind_repair_worktree(publication_state)
        return saved

    def finalize_publication_evidence(
        self, *, operation_id: str, finalization_operation_id: str,
        evidence_paths: list[str], draft_inventory: Mapping[str, Any],
        design_required: bool, expected_state_revision: int,
        reservation_id: str, authorization_ref: str, expected_record_revision: int,
        expected_reservations_revision: int, physical_worktree_fingerprint: str,
        replay_committed: bool = False,
    ) -> dict[str, Any]:
        publication = self.publication_operations.load(operation_id)
        if publication["status"] != "pr-open" or publication["evidenceFinalizationCount"] != 0:
            raise SupervisorStoreError("Evidence finalization is out of order or already consumed")
        if self.publication_git is None or self.publication_provider is None:
            raise SupervisorStoreError("Evidence finalization boundaries are not activated")
        if replay_committed:
            replay = self.publication_git.reconcile_committed_operation(
                operation_id=finalization_operation_id, paths=evidence_paths,
                trailer="Evidence-Finalization-Operation",
            )
            if replay is None:
                raise SupervisorStoreError("Finalization replay lacks its immutable committed operation")
            self._require_consumed_publication_authorization(
                publication=publication, mutation_id=finalization_operation_id,
                mutation_kind="finalize-evidence", reservation_id=reservation_id,
                authorization_ref=authorization_ref, expected_record_revision=expected_record_revision,
                expected_state_revision=expected_state_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
            expected_state_revision = self.store.load_state()["revision"]
        else:
            self._publication_authority(publication, expected_state_revision=expected_state_revision)
            self._consume_publication_authorization(
                publication=publication, mutation_id=finalization_operation_id,
                mutation_kind="finalize-evidence", reservation_id=reservation_id,
                authorization_ref=authorization_ref, expected_record_revision=expected_record_revision,
                expected_state_revision=expected_state_revision,
                expected_reservations_revision=expected_reservations_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
            EvidenceConvergence(repository_root=publication["preservedState"]["worktreePath"]).require_drafts(
                draft_inventory, design_required=design_required,
                read_draft=self.publication_git.read_head_bytes,
            )
        result = self.publication_git.finalize_evidence(
            evidence_paths, operation_id=finalization_operation_id,
        )
        publication["headSha"] = result["headSha"]
        publication["evidenceFinalizationCount"] = 1
        publication["evidenceFinalization"] = {
            "headSha": result["headSha"], "stagedPaths": result["stagedPaths"],
            "deltaDigest": result["deltaDigest"], "providerEvidenceRef": "sha256:" + "0" * 64,
        }
        publication["attestations"] = {
            key: value for key, value in publication["attestations"].items()
            if key == "pre-staging-aggregate"
        }
        # Finalization changes the branch head after the PR exists. Re-enter
        # push/PR readback under fresh immutable provider operation identities
        # before any final-head gate can be accepted.
        publication["status"] = "prepared"
        publication["providerOperationIds"] = {
            "push": None, "pull-request": None, "squash-merge": None,
        }
        publication["activeProviderOperation"] = None
        publication["providerEvidenceRef"] = None
        publication["attemptCount"] = 0
        publication["retryCount"] = 0
        publication["authorityReadback"] = None
        self.publication_operations.save_authoritative(
            publication, expected_state_revision=self.store.load_state()["revision"]
        )
        self._bind_repair_worktree(publication)
        return copy.deepcopy(publication["evidenceFinalization"])

    def record_publication_attestation(
        self, *, operation_id: str, attestation_id: str, source_operation_id: str,
        expected_state_revision: int, reservation_id: str, authorization_ref: str,
        expected_record_revision: int, expected_reservations_revision: int,
        physical_worktree_fingerprint: str,
    ) -> dict[str, Any]:
        publication = self.publication_operations.load(operation_id)
        self._publication_authority(publication, expected_state_revision=expected_state_revision)
        self._consume_publication_authorization(
            publication=publication, mutation_id=attestation_id,
            mutation_kind="evidence", reservation_id=reservation_id,
            authorization_ref=authorization_ref,
            expected_record_revision=expected_record_revision,
            expected_state_revision=expected_state_revision,
            expected_reservations_revision=expected_reservations_revision,
            physical_worktree_fingerprint=physical_worktree_fingerprint,
        )
        result_record = self.publication_operations.resolve_checkpoint_result(
            publication=publication,
            source_operation_id=source_operation_id,
        )
        kind = result_record["kind"]
        if kind not in ATTESTATION_PRODUCERS or kind.startswith("exact-"):
            raise SupervisorStoreError("attestation kind is produced by a different closed operation")
        if result_record["exactSha"] != publication["headSha"]:
            raise SupervisorStoreError("attestation is not bound to the current exact head")
        attestation = {
            "schemaVersion": "1.0", "attestationId": attestation_id,
            "publicationOperationId": operation_id, "kind": kind,
            "producer": result_record["producer"], "stage": result_record["stage"],
            "result": result_record["outcome"],
            "provenanceRef": result_record["sourceRecordDigest"],
            "exactSha": result_record["exactSha"],
            "issuedStateRevision": expected_state_revision,
            "recordedAt": result_record["recordedAt"],
        }
        self.publication_operations.issue_attestation(attestation)
        publication["attestations"][kind] = attestation
        if kind == "evidence-convergence" and publication.get("evidenceFinalization") is None:
            raise SupervisorStoreError("evidence convergence requires engine-owned finalization")
        self.publication_operations.save_authoritative(
            publication, expected_state_revision=expected_state_revision
        )
        return attestation

    def execute_publication_provider(
        self, *, operation_id: str, provider_operation: str,
        provider_operation_id: str, expected_state_revision: int,
        reservation_id: str, authorization_ref: str, expected_record_revision: int,
        expected_reservations_revision: int, physical_worktree_fingerprint: str,
        mutation_operation_id: str | None = None,
        authorization_already_consumed: bool = False,
    ) -> dict[str, Any]:
        if self.publication_provider is None:
            raise SupervisorStoreError("Publication provider is not activated")
        publication = self.publication_operations.load(operation_id)
        if not authorization_already_consumed:
            self._consume_publication_authorization(
                publication=publication, mutation_id=mutation_operation_id or provider_operation_id,
                mutation_kind=f"provider-{provider_operation}", reservation_id=reservation_id,
                authorization_ref=authorization_ref,
                expected_record_revision=expected_record_revision,
                expected_state_revision=expected_state_revision,
                expected_reservations_revision=expected_reservations_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
        publication["authorityReadback"] = self.publication_provider.authority_readback(
            issue_id=publication["issueId"], branch=publication["branch"],
            base_ref=publication["baseRef"], head_sha=publication["headSha"],
        )
        self.publication_operations.save_authoritative(
            publication, expected_state_revision=expected_state_revision
        )
        expected_state_revision = self.store.load_state()["revision"]
        if provider_operation == "squash-merge":
            observed_base_sha = publication["authorityReadback"]["baseSha"]
            if observed_base_sha != publication["baseSha"]:
                if self.publication_git is None:
                    raise SupervisorStoreError("base drift requires the contained Git boundary")
                drift = MergeRepairPolicy.base_drift(
                    observed_base_sha=observed_base_sha,
                    attested_base_sha=publication["baseSha"],
                    merge_origin_main=lambda: self.publication_git.merge_origin_main(observed_base_sha),
                )
                publication.update({
                    "headSha": drift["headSha"], "baseSha": observed_base_sha,
                    "attestations": {}, "evidenceFinalizationCount": 0,
                    "evidenceFinalization": None, "preparation": None,
                    "status": "base-drift", "providerEvidenceRef": None,
                    "providerOperationIds": {"push": None, "pull-request": None, "squash-merge": None},
                    "activeProviderOperation": None, "attemptCount": 0, "retryCount": 0,
                })
                publication["authorityReadback"] = self.publication_provider.authority_readback(
                    issue_id=publication["issueId"], branch=publication["branch"],
                    base_ref=publication["baseRef"], head_sha=publication["headSha"],
                )
                self.publication_operations.save_authoritative(
                    publication, expected_state_revision=expected_state_revision
                )
                return {"status": "base-drift", "headSha": publication["headSha"], "invalidated": drift["invalidated"]}
        self._publication_authority(
            publication, expected_state_revision=expected_state_revision,
            for_merge=provider_operation == "squash-merge",
        )
        expected_phase = {
            "push": "prepared", "pull-request": "pushed",
            "squash-merge": "head-gated",
        }.get(provider_operation)
        bound_id = publication["providerOperationIds"][provider_operation]
        completed_phase = {
            "push": "pushed", "pull-request": "pr-open",
            "squash-merge": "merged",
        }.get(provider_operation)
        if expected_phase is None or (
            publication["status"] != expected_phase
            and not (
                bound_id == provider_operation_id
                and publication["status"] in {completed_phase, "attempting", "retry-wait"}
            )
        ):
            raise SupervisorStoreError("Publication provider phase is out of order")
        if provider_operation == "squash-merge":
            self._require_merge_evidence(publication)
        if bound_id is not None and bound_id != provider_operation_id:
            raise SupervisorStoreError("Provider mutation identity changed on replay")
        if provider_operation_id in {
            value for key, value in publication["providerOperationIds"].items()
            if key != provider_operation and value is not None
        }:
            raise SupervisorStoreError("Provider mutation identity was reused across phases")
        publication["providerOperationIds"][provider_operation] = provider_operation_id
        if publication["status"] == "retry-wait":
            publication["attemptCount"] = publication["retryCount"] + 1
        elif publication["attemptCount"] == 0:
            publication["attemptCount"] = 1
        publication["status"] = "attempting"
        publication["activeProviderOperation"] = provider_operation
        self.publication_operations.save_authoritative(
            publication, expected_state_revision=expected_state_revision
        )
        self._publication_authority(
            publication,
            expected_state_revision=self.store.load_state()["revision"],
            for_merge=provider_operation == "squash-merge",
        )
        try:
            if provider_operation == "push":
                outcome = self.publication_provider.push(
                    operation_id=provider_operation_id, branch=publication["branch"],
                    head_sha=publication["headSha"],
                )
                publication["status"] = "pushed"
            elif provider_operation == "pull-request":
                outcome = self.publication_provider.pull_request(
                    operation_id=provider_operation_id, branch=publication["branch"],
                    base_ref=publication["baseRef"], head_sha=publication["headSha"],
                )
                publication["pullRequest"] = outcome["pullRequest"]
                publication["status"] = "pr-open"
            elif provider_operation == "squash-merge":
                pull_request = publication.get("pullRequest")
                if not isinstance(pull_request, Mapping) or not pull_request.get("id"):
                    raise SupervisorStoreError("Publication merge lacks an exact pull request")
                outcome = self.publication_provider.merge(
                    operation_id=provider_operation_id, pull_request_id=str(pull_request["id"]),
                    base_ref=publication["baseRef"], head_sha=publication["headSha"],
                )
                publication["mergeSha"] = outcome["mergeSha"]
                merge_readback = {
                    "schemaVersion": "1.0", "attestationId": provider_operation_id,
                    "publicationOperationId": operation_id, "kind": "merge-readback",
                    "producer": "provider-readback", "stage": "post-merge",
                    "result": "passed", "provenanceRef": outcome["evidenceRef"],
                    "exactSha": publication["headSha"],
                    "issuedStateRevision": self.store.load_state()["revision"],
                    "recordedAt": publication["updatedAt"],
                }
                self.publication_operations.issue_attestation(merge_readback)
                publication["attestations"]["merge-readback"] = merge_readback
                publication["status"] = "merged"
            else:
                raise SupervisorStoreError("Publication provider operation is not closed")
        except ProviderOperationRefused as exc:
            kind = classify_refusal(exc.response, exc.readback)
            publication["refusalKind"] = kind
            publication["providerEvidenceRef"] = self.publication_operations.record_refusal(
                operation_id, exc.response, exc.readback
            )
            if self.publication_recovery is None:
                raise SupervisorStoreError("provider refusal recovery policy is not assembled")
            preserved = publication["preservedState"]
            publication = self.publication_recovery.refusal(
                publication=publication, response=exc.response, readback=exc.readback,
                now=publication["updatedAt"],
                request_context={
                    "issue_id": publication["issueId"], "operation_id": operation_id,
                    "head_sha": publication["headSha"],
                    "source_timestamp": publication["updatedAt"],
                    "created_at": publication["updatedAt"],
                    "link": _linear_issue_link(publication["issueId"]),
                    "reason": f"publication {provider_operation} refused",
                    "evidence": {
                        "issueState": preserved["issueState"],
                        "reservationId": preserved["reservationId"],
                        "worktreePath": preserved["worktreePath"],
                        "branch": publication["branch"],
                        "prId": str((publication.get("pullRequest") or {}).get("id", "none")),
                    },
                    "owner_id": publication["preservedState"].get("ownerId", "owner"),
                    "config_digest": "sha256:" + "0" * 64,
                    "repository_id": publication["repositoryId"],
                    "refusal_kind": "exhausted" if kind in TRANSIENT else (
                        "ambiguous" if kind in {"ambiguous", "unclassified"} else "stable"
                    ),
                },
            )
            self.publication_operations.save_authoritative(
                publication, expected_state_revision=self.store.load_state()["revision"]
            )
            return copy.deepcopy(publication)
        publication["activeProviderOperation"] = None
        publication["refusalKind"] = None
        publication["nextRetryAt"] = None
        publication["providerEvidenceRef"] = outcome["evidenceRef"]
        publication["authorityReadback"] = self.publication_provider.authority_readback(
            issue_id=publication["issueId"], branch=publication["branch"],
            base_ref=publication["baseRef"], head_sha=publication["headSha"],
        )
        if provider_operation in {"push", "pull-request"} and (
            publication["authorityReadback"].get("headSha") != publication["headSha"]
            or publication["authorityReadback"].get("expectedHeadSha") != publication["headSha"]
        ):
            raise SupervisorStoreError("Provider final-head readback differs after publication mutation")
        if provider_operation == "pull-request" and str(
            publication["authorityReadback"].get("pullRequestId")
        ) != str((publication.get("pullRequest") or {}).get("id")):
            raise SupervisorStoreError("Provider pull-request identity differs after readback")
        if provider_operation == "push" and isinstance(publication.get("evidenceFinalization"), Mapping):
            publication["evidenceFinalization"]["providerEvidenceRef"] = publication["authorityReadback"]["evidenceRef"]
        self.publication_operations.save_authoritative(
            publication, expected_state_revision=self.store.load_state()["revision"]
        )
        return outcome

    def execute_publication_gate(
        self, *, operation_id: str, gate_operation_id: str, exact_sha: str,
        kind: str, started_at: str, completed_at: str,
        expected_state_revision: int, reservation_id: str, authorization_ref: str,
        expected_record_revision: int, expected_reservations_revision: int,
        physical_worktree_fingerprint: str,
    ) -> dict[str, Any]:
        publication = self.publication_operations.load(operation_id)
        self._publication_authority(
            publication, expected_state_revision=expected_state_revision
        )
        self._consume_publication_authorization(
            publication=publication, mutation_id=gate_operation_id,
            mutation_kind=f"gate-{kind}", reservation_id=reservation_id,
            authorization_ref=authorization_ref,
            expected_record_revision=expected_record_revision,
            expected_state_revision=expected_state_revision,
            expected_reservations_revision=expected_reservations_revision,
            physical_worktree_fingerprint=physical_worktree_fingerprint,
        )
        if kind == "pre-staging-aggregate":
            if publication["status"] not in {"prepared", "pr-open"} or exact_sha != publication["headSha"]:
                raise SupervisorStoreError("Pre-staging gate is out of order or wrong-SHA")
        elif kind == "exact-head-aggregate":
            if publication["status"] != "pr-open" or exact_sha != publication["headSha"]:
                raise SupervisorStoreError("Exact-head gate is out of order or wrong-SHA")
        elif kind == "exact-merge-aggregate":
            if publication["status"] != "merged" or publication["mergeSha"] is None or exact_sha != publication["mergeSha"]:
                raise SupervisorStoreError("Exact-merge gate requires provider-readback merge SHA")
        else:
            raise SupervisorStoreError("Publication gate kind is not closed")
        runner = ExactShaGateRunner(
            repository_id=self.manager.identity.repository_id,
            workflow_id=publication["workflowId"], issue_id=publication["issueId"],
            worktrees=self.worktrees,
            runner=self.publication_gate_runner or __import__("subprocess").run,
        )
        try:
            attestation = runner.run(
                operation_id=gate_operation_id, exact_commit=exact_sha,
                started_at=started_at, completed_at=completed_at, kind=kind,
            )
        except ExactShaGateError:
            if kind == "exact-merge-aggregate":
                publication["status"] = "post-merge-validating"
                self.publication_operations.save_authoritative(
                    publication, expected_state_revision=self.store.load_state()["revision"]
                )
            raise
        issued = {
            "schemaVersion": "1.0", "attestationId": attestation["attestationId"],
            "publicationOperationId": operation_id, "kind": kind,
            "producer": "gate-runner",
            "stage": "post-merge" if kind == "exact-merge-aggregate" else "pre-merge",
            "result": "passed", "provenanceRef": attestation["evidenceDigest"],
            "exactSha": attestation["exactSha"],
            "issuedStateRevision": expected_state_revision, "recordedAt": completed_at,
        }
        self.publication_operations.issue_attestation(issued)
        publication["attestations"][kind] = issued
        if kind == "exact-head-aggregate":
            publication["status"] = "head-gated"
        if kind == "exact-merge-aggregate":
            if publication["repairAttempt"]:
                gates = {}
                for name in (
                    "pre-staging-aggregate", "exact-head-aggregate", "review", "qa",
                    "docs", "evidence-convergence", "merge-readback",
                ):
                    record = publication["attestations"].get(name)
                    if record is not None:
                        gates[name] = {"exactSha": record["exactSha"], "passed": record["result"] == "passed"}
                gates["exact-merge-aggregate"] = {
                    "repairHeadSha": publication["headSha"], "passed": True,
                }
                if "merge-readback" in gates:
                    gates["merge-readback"] = {
                        "repairHeadSha": publication["headSha"],
                        "passed": gates["merge-readback"]["passed"],
                    }
                MergeRepairPolicy.require_repair_pipeline(
                    repair_head=publication["headSha"], gates=gates
                )
            publication["status"] = "completed"
        self.publication_operations.save_authoritative(publication)
        return attestation

    def recover_publication(
        self, *, operation_id: str,
        attended: Mapping[str, Any] | None = None,
        now: str | None = None,
        reservation_id: str, authorization_ref: str,
        recovery_operation_id: str, expected_record_revision: int,
        expected_state_revision: int, expected_reservations_revision: int,
        physical_worktree_fingerprint: str,
    ) -> dict[str, Any]:
        publication = self.publication_operations.reconcile_authoritative(operation_id)
        if publication["status"] in {"attempting", "retry-wait"}:
            if publication.get("consumedReplyId") is not None or publication.get("refusalKind") not in TRANSIENT | {None}:
                raise SupervisorStoreError("attended or stable publication cannot retry automatically")
            if publication["status"] == "retry-wait":
                if now is None or datetime.fromisoformat(now.replace("Z", "+00:00")) < datetime.fromisoformat(publication["nextRetryAt"].replace("Z", "+00:00")):
                    raise SupervisorStoreError("Publication retry backoff has not elapsed")
            provider_operation = publication.get("activeProviderOperation")
            if provider_operation is None:
                raise SupervisorStoreError("Attempting publication lacks provider identity")
            provider_operation_id = publication["providerOperationIds"][provider_operation]
            self.execute_publication_provider(
                operation_id=operation_id, provider_operation=provider_operation,
                provider_operation_id=provider_operation_id,
                expected_state_revision=self.store.load_state()["revision"],
                reservation_id=reservation_id, authorization_ref=authorization_ref,
                expected_record_revision=expected_record_revision,
                expected_reservations_revision=expected_reservations_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
                mutation_operation_id=recovery_operation_id,
            )
            return self.publication_operations.load(operation_id)
        if publication["status"] == "paused":
            if publication.get("consumedReplyId") is not None and attended is None:
                raise SupervisorStoreError("consumed attended publication is reconcile-only")
            if self.publication_recovery is None or attended is None:
                raise SupervisorStoreError("Paused publication requires durable attended recovery")
            provider_operation = publication.get("activeProviderOperation")
            if provider_operation is None:
                raise SupervisorStoreError("paused publication lacks provider operation")
            records = self.publication_recovery.requests
            consume_method = getattr(records, "consume_publication_reply", None)
            reopen_method = getattr(records, "reopen_publication_request", None)
            if not callable(consume_method) or not callable(reopen_method):
                raise SupervisorStoreError("durable publication reply boundary is unavailable")
            observed = self.publication_provider.authority_readback(
                issue_id=publication["issueId"], branch=publication["branch"],
                base_ref=publication["baseRef"], head_sha=publication["headSha"],
            )
            with self.store.mutex():
                state, reservations = self.store.load_pair_unlocked()
                if state["revision"] != expected_state_revision:
                    raise SupervisorStoreError("Publication supervisor CAS is stale")
                self._publication_local_authority(state, reservations, publication)
            arguments = dict(attended)
            if publication.get("consumedReplyId") is not None and (
                arguments.get("reply_id") == publication["consumedReplyId"]
            ):
                raise SupervisorStoreError("attended publication reply identity was already consumed")
            rereads = self._attended_publication_rereads(
                publication=publication, observed=observed, attended=arguments,
                reservation_id=reservation_id, authorization_ref=authorization_ref,
                recovery_operation_id=recovery_operation_id,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
            consume_args = {
                name: arguments[name] for name in (
                    "request_id", "actor_id", "reply_id", "reply_created_at", "body",
                    "owner_id", "config_digest", "repository_id",
                )
            }
            consume_args["reconciled"] = all(rereads.values())
            def attempt() -> Mapping[str, Any]:
                outcome = self.execute_publication_provider(
                    operation_id=operation_id, provider_operation=provider_operation,
                    provider_operation_id=publication["providerOperationIds"][provider_operation],
                    expected_state_revision=self.store.load_state()["revision"],
                    reservation_id=reservation_id, authorization_ref=authorization_ref,
                    expected_record_revision=expected_record_revision,
                    expected_reservations_revision=expected_reservations_revision,
                    physical_worktree_fingerprint=physical_worktree_fingerprint,
                    mutation_operation_id=recovery_operation_id,
                    authorization_already_consumed=True,
                )
                authoritative = self.publication_operations.load(operation_id)
                return {"applied": outcome.get("status") not in {"paused", "retry-wait"},
                    "publication": authoritative}
            def reconcile_attended_application() -> Mapping[str, Any]:
                reconciled = dict(self.publication_provider.reconcile_application(
                    provider_operation=provider_operation, branch=publication["branch"],
                    base_ref=publication["baseRef"], head_sha=publication["headSha"],
                    pull_request_id=str((publication.get("pullRequest") or {}).get("id"))
                    if publication.get("pullRequest") else None,
                ))
                if reconciled.get("applied") is True and provider_operation == "squash-merge":
                    merge_readback = {
                        "schemaVersion": "1.0", "attestationId": publication["providerOperationIds"][provider_operation],
                        "publicationOperationId": operation_id, "kind": "merge-readback",
                        "producer": "provider-readback", "stage": "post-merge", "result": "passed",
                        "provenanceRef": reconciled["evidenceRef"], "exactSha": publication["headSha"],
                        "issuedStateRevision": self.store.load_state()["revision"],
                        "recordedAt": publication["updatedAt"],
                    }
                    self.publication_operations.issue_attestation(merge_readback)
                    reconciled["mergeReadback"] = merge_readback
                return reconciled
            return self.publication_recovery.attended_retry(
                publication=publication,
                consume_reply=lambda: consume_method(**consume_args), rereads=rereads,
                persist_consumption=lambda value: self.publication_operations.save_authoritative(
                    value, expected_state_revision=self.store.load_state()["revision"]
                ),
                attempt=attempt,
                authorize_attempt=lambda: self._consume_publication_authorization(
                    publication=publication, mutation_id=recovery_operation_id,
                    mutation_kind=f"provider-{provider_operation}",
                    reservation_id=reservation_id, authorization_ref=authorization_ref,
                    expected_record_revision=expected_record_revision,
                    expected_state_revision=expected_state_revision,
                    expected_reservations_revision=expected_reservations_revision,
                    physical_worktree_fingerprint=physical_worktree_fingerprint,
                ),
                reconcile_application=reconcile_attended_application,
                reopen_request=lambda reply_id: reopen_method(
                    request_id=arguments["request_id"], consumed_reply_id=reply_id,
                ),
            )
        return publication

    def next_publication_repair(
        self, *, operation_id: str, repair_operation_id: str, current_main_sha: str,
        artifact_manifest: list[str] | None = None,
        preexisting_paths: list[str] | None = None,
        expected_state_revision: int, reservation_id: str, authorization_ref: str,
        expected_record_revision: int, expected_reservations_revision: int,
        physical_worktree_fingerprint: str,
        replay_committed: bool = False,
    ) -> dict[str, Any]:
        publication = self.publication_operations.load(operation_id)
        if replay_committed:
            if publication["status"] != "prepared" or publication["repairAttempt"] <= 0 or not artifact_manifest:
                raise SupervisorStoreError("Repair replay is not at a committed preparation boundary")
            replay = self.publication_git.reconcile_committed_operation(
                operation_id=repair_operation_id, paths=artifact_manifest,
                trailer="Publication-Operation", preexisting_paths=preexisting_paths or [],
            )
            if replay is None:
                raise SupervisorStoreError("Repair replay lacks its immutable committed operation")
            self._require_consumed_publication_authorization(
                publication=publication, mutation_id=repair_operation_id,
                mutation_kind="repair", reservation_id=reservation_id,
                authorization_ref=authorization_ref, expected_record_revision=expected_record_revision,
                expected_state_revision=expected_state_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
            expected_state_revision = self.store.load_state()["revision"]
        else:
            self._publication_authority(publication, expected_state_revision=expected_state_revision)
            self._consume_publication_authorization(
                publication=publication, mutation_id=repair_operation_id,
                mutation_kind="repair", reservation_id=reservation_id,
                authorization_ref=authorization_ref,
                expected_record_revision=expected_record_revision,
                expected_state_revision=expected_state_revision,
                expected_reservations_revision=expected_reservations_revision,
                physical_worktree_fingerprint=physical_worktree_fingerprint,
            )
        if publication["status"] == "prepared" and publication["repairAttempt"] > 0:
            if self.publication_git is None or not artifact_manifest:
                raise SupervisorStoreError("repair preparation requires an engine-owned manifest")
            preparation = self.publication_git.prepare_repair(
                issue_id=publication["issueId"], attempt=publication["repairAttempt"],
                manifest=artifact_manifest, preexisting_paths=preexisting_paths or [],
                operation_id=repair_operation_id,
            )
            observed = preparation["headSha"]
            if observed == current_main_sha:
                raise SupervisorStoreError("repair preparation did not create a new head")
            publication.update({"headSha": observed, "baseSha": preparation["baseSha"],
                "preparation": preparation})
            if self.publication_provider is None:
                raise SupervisorStoreError("repair head transition requires provider readback")
            publication["authorityReadback"] = self.publication_provider.authority_readback(
                issue_id=publication["issueId"], branch=publication["branch"],
                base_ref=publication["baseRef"], head_sha=observed,
            )
            self.publication_operations.save_authoritative(
                publication, expected_state_revision=expected_state_revision
            )
            self._bind_repair_worktree(publication)
            return {"status": "repair-head", "attempt": publication["repairAttempt"], "headSha": observed}
        if publication["status"] != "post-merge-validating":
            raise SupervisorStoreError("Publication repair requires a failed exact-merge gate")
        result = MergeRepairPolicy.next_repair(
            issue_id=publication["issueId"],
            previous_attempt=publication["repairAttempt"],
            current_main_sha=current_main_sha,
        )
        if result["status"] == "repairing":
            if self.publication_git is None:
                raise SupervisorStoreError("publication repair requires injected Git boundary")
            branch = self.publication_git.create_repair_branch(
                issue_id=publication["issueId"], attempt=result["attempt"],
                current_main_sha=current_main_sha,
            )
            if branch != result["branch"] or self.publication_git.branch_head(branch) != current_main_sha:
                raise SupervisorStoreError("repair branch readback differs from policy")
            if self.publication_provider is None:
                raise SupervisorStoreError("publication repair requires provider authority readback")
            repair_readback = self.publication_provider.authority_readback(
                issue_id=publication["issueId"], branch=branch,
                base_ref=publication["baseRef"], head_sha=current_main_sha,
            )
            publication["repairAttempt"] = result["attempt"]
            publication.update({
                "status": "prepared", "branch": result["branch"],
                "headSha": result["baseSha"], "mergeSha": None,
                "pullRequest": None, "attestations": {},
                "evidenceFinalizationCount": 0, "providerEvidenceRef": None,
                "providerOperationIds": {"push": None, "pull-request": None, "squash-merge": None},
                "activeProviderOperation": None, "authorityReadback": repair_readback,
                "attemptCount": 0, "retryCount": 0, "nextRetryAt": None,
                "refusalKind": None,
                "preparation": None, "evidenceFinalization": None,
            })
            self.publication_operations.save_authoritative(
                publication, expected_state_revision=expected_state_revision
            )
            self._bind_repair_worktree(publication)
        else:
            if self.publication_recovery is not None:
                publication = self.publication_recovery.repair_exhausted(
                    publication=publication,
                    request_context={
                        "issue_id": publication["issueId"],
                        "operation_id": publication["operationId"],
                        "head_sha": publication["headSha"],
                        "source_timestamp": publication["updatedAt"],
                        "created_at": publication["updatedAt"],
                        "link": _linear_issue_link(publication["issueId"]),
                        "reason": "three post-merge repair attempts were exhausted",
                        "evidence": {
                            "issueState": publication["preservedState"]["issueState"],
                            "reservationId": publication["preservedState"]["reservationId"],
                            "worktreePath": publication["preservedState"]["worktreePath"],
                            "branch": publication["branch"],
                            "prId": str((publication.get("pullRequest") or {}).get("id", "none")),
                        },
                        "owner_id": "publication-repair",
                        "config_digest": "sha256:" + "0" * 64,
                        "repository_id": publication["repositoryId"],
                        "refusal_kind": "exhausted",
                    },
                )
            else:
                publication.update({"status": "paused", "refusalKind": "policy", "nextRetryAt": None})
            self.publication_operations.save_authoritative(
                publication, expected_state_revision=expected_state_revision
            )
            result = copy.deepcopy(publication)
        return result


# Concise compatibility name for adapters without creating another engine.
Supervisor = SupervisorEngine
