"""Composed deterministic supervisor facade for state-engine operations."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .base_runtime import load_base_runtime
from .lease import Clock, LeaseManager
from .operations import OperationJournal
from .recovery import RecoveryManager
from .reservations import ReservationManager
from .store import SupervisorStore, SupervisorStoreError
from .worktrees import WorktreeManager


class SupervisorEngine:
    """One repository-bound state engine; transport and selection remain outside."""

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
        }
    )

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

    def status(self) -> dict[str, Any]:
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
                "recovery": copy.deepcopy(state["recovery"]),
                "handoffPending": copy.deepcopy(state["handoffPending"]),
                "reservations": public_reservations,
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


# Concise compatibility name for adapters without creating another engine.
Supervisor = SupervisorEngine
