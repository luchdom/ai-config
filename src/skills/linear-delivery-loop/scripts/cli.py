"""Strict structured-file command surface for the local supervisor core."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.assembled_handoff import (
        AssembledHandoffError,
        execute_assembled_handoff,
        recover_assembled_handoff,
    )
    from scripts.contracts import validate_contract, validate_engine_command
    from scripts.preflight import PreflightValidator
    from scripts.supervisor import SupervisorEngine
    from scripts.worktrees import WorktreeManager
else:
    from .assembled_handoff import (
        AssembledHandoffError,
        execute_assembled_handoff,
        recover_assembled_handoff,
    )
    from .contracts import validate_contract, validate_engine_command
    from .preflight import PreflightValidator
    from .supervisor import SupervisorEngine
    from .worktrees import WorktreeManager


class SupervisorCommandError(RuntimeError):
    """A public command failed without exposing an implementation traceback."""


@dataclass(frozen=True)
class FixtureAssembly:
    """Closed local-only assembly consumed by run_request fixture tests."""
    publication_provider: Any
    publication_recovery: Any
    publication_git: Any = None
    publication_gate_runner: Any = None
    clock: Any = None
    reservation_clock: Any = None
    fixture_mode: bool = True


_FIXTURE_ASSEMBLIES: dict[str, FixtureAssembly] = {}


def register_fixture_assembly(state_home: str | Path, assembly: FixtureAssembly) -> None:
    if not isinstance(assembly, FixtureAssembly) or assembly.fixture_mode is not True:
        raise SupervisorCommandError("only a closed fixture assembly may be registered")
    _FIXTURE_ASSEMBLIES[_normalized(state_home)] = assembly


def unregister_fixture_assembly(state_home: str | Path) -> None:
    _FIXTURE_ASSEMBLIES.pop(_normalized(state_home), None)


class CleanupAmbiguousError(SupervisorCommandError):
    """Gate removal may have occurred without a conclusive paired state commit."""


def _normalized(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))


def _contained(root: str | Path, candidate: str | Path) -> bool:
    try:
        return os.path.commonpath([_normalized(root), _normalized(candidate)]) == _normalized(root)
    except ValueError:
        return False


def _read_public_json(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute() or not candidate.exists() or not candidate.is_file():
        raise SupervisorCommandError("Structured request path must be an existing absolute file")
    if candidate.is_symlink() or candidate.stat().st_nlink != 1:
        raise SupervisorCommandError("Structured request path must be a single-link regular file")
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SupervisorCommandError("Structured request is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SupervisorCommandError("Structured request must be a JSON object")
    return value


def _validate_command_path(path: str | Path, command: Mapping[str, Any]) -> None:
    if not (
        _contained(command["repositoryRoot"], path)
        or _contained(command["stateHome"], path)
    ):
        raise SupervisorCommandError(
            "EngineCommand path must be contained by its repository or canonical state home"
        )


def _state_pair(engine: SupervisorEngine) -> tuple[dict[str, Any], dict[str, Any]]:
    with engine.store.mutex():
        return engine.store.load_pair_unlocked()


def _reservation(
    reservations: Mapping[str, Any], reservation_id: str
) -> dict[str, Any]:
    record = reservations["reservations"].get(reservation_id)
    if not isinstance(record, dict):
        raise SupervisorCommandError("Reservation ID is not registered")
    return record


def _execute_probe(
    config: Mapping[str, Any], environment: Mapping[str, str], *, repository_root: str
) -> dict[str, Any]:
    adapter = config["probeAdapter"]
    executable = adapter["executable"]
    if not os.path.isabs(executable):
        raise SupervisorCommandError("Preflight probe executable must be absolute")
    try:
        completed = subprocess.run(
            [executable, *adapter["fixedArgv"]],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            timeout=60,
            env=dict(environment),
            input=json.dumps(
                {"config": dict(config), "repositoryRoot": repository_root},
                sort_keys=True,
            ),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SupervisorCommandError("Read-only preflight probe could not execute") from exc
    if completed.returncode != 0:
        raise SupervisorCommandError("Read-only preflight probe returned failure")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SupervisorCommandError("Read-only preflight probe returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise SupervisorCommandError("Read-only preflight probe result must be an object")
    return value


def _preflight(command: Mapping[str, Any]) -> dict[str, Any]:
    config = _read_public_json(command["configPath"])
    validate_contract("project-config", config)
    validator = PreflightValidator(
        command["repositoryRoot"],
        repository_key=command["repositoryKey"],
        state_home_override=Path(command["stateHome"]).parent,
    )
    if _normalized(validator.state_root) != _normalized(command["stateHome"]):
        raise SupervisorCommandError("EngineCommand state home differs from canonical authority")
    # This must precede subprocess construction: repository config is untrusted
    # until the engine-owned adapter identity, argv, and environment are proven.
    validator.validate_probe_request(config)
    child_environment = validator.build_child_environment(config)
    probe = _execute_probe(
        config,
        child_environment,
        repository_root=command["repositoryRoot"],
    )
    return validator.validate(config, probe)


def _cleanup(engine: SupervisorEngine, command: Mapping[str, Any]) -> dict[str, Any]:
    state, reservations = _state_pair(engine)
    if state["revision"] != command["expectedStateRevision"]:
        raise SupervisorCommandError("Cleanup supervisor state revision is stale")
    if reservations["revision"] != command["expectedReservationsRevision"]:
        raise SupervisorCommandError("Cleanup reservations revision is stale")
    if state["handoffPending"] is not None or state["recovery"]["status"] != "clean":
        raise SupervisorCommandError("Cleanup refuses protected recovery or Handoff state")
    reservation = _reservation(reservations, command["releasedReservationId"])
    if (
        reservation.get("status") != "released"
        or reservation.get("revision")
        != command["expectedReleasedReservationRevision"]
    ):
        raise SupervisorCommandError("Cleanup released-reservation binding is stale")
    if state["lease"] is not None or any(
        record.get("status") in {"live", "handoff-pending"}
        for record in reservations["reservations"].values()
    ):
        raise SupervisorCommandError("Cleanup refuses live lease or editing authority")
    gate = state["gateWorktrees"].get(command["gateOperationId"])
    if not isinstance(gate, dict) or gate.get("status") != "active":
        raise SupervisorCommandError("Cleanup gate mapping is absent or inactive")
    if gate.get("operationStatus") != "resolved" or gate.get("attestationStatus") != "complete":
        raise SupervisorCommandError("Cleanup gate evidence is incomplete")
    pending = engine.operations.pending_ids(ignore_operation_id=command["requestId"])
    if pending:
        raise SupervisorCommandError("Cleanup refuses unresolved operation evidence")
    manager = WorktreeManager(
        command["repositoryRoot"],
        repository_key=command["repositoryKey"],
        state_home_override=Path(command["stateHome"]).parent,
        store=engine.store,
    )
    def mutation(
        authoritative_reservation: Mapping[str, Any],
        authoritative_gate: Mapping[str, Any],
        mutable_state: dict[str, Any],
    ) -> dict[str, Any]:
        if authoritative_gate.get("operationId") != command["gateOperationId"]:
            raise SupervisorCommandError("Cleanup gate authority changed")
        cleaned = manager._cleanup_gate_worktree_authorized(
            command["gateOperationId"], mutable_state=mutable_state
        )
        return {"status": "clean", "removed": [cleaned["path"]], "gate": cleaned}

    try:
        return engine.reservations.execute_cleanup_authorization(
            reservation_id=command["releasedReservationId"],
            authorization_ref=command["cleanupAuthorizationRef"],
            operation_id=command["requestId"],
            gate_operation_id=command["gateOperationId"],
            expected_state_revision=command["expectedStateRevision"],
            expected_reservations_revision=command["expectedReservationsRevision"],
            mutation=mutation,
        )
    except Exception as exc:
        # A paired-commit interruption after Git removal is first resolved from
        # its exact transaction evidence. If that cannot prove completion, the
        # missing gate is protected as ambiguous rather than reported failed.
        try:
            engine.store.recover()
        except Exception:
            pass
        try:
            observed = engine.store.load_state()
            observed_gate = observed["gateWorktrees"].get(command["gateOperationId"])
            gate_missing = not os.path.lexists(gate["worktreePath"])
            if (
                isinstance(observed_gate, dict)
                and observed_gate.get("status") == "cleaned"
                and gate_missing
            ):
                return {
                    "status": "clean",
                    "removed": [observed_gate["worktreePath"]],
                    "gate": manager._gate_public_record(observed_gate),
                    "recovered": True,
                }
            if gate_missing:
                _protect_cleanup_ambiguity(engine, command)
                raise CleanupAmbiguousError(
                    "Cleanup outcome is ambiguous and protected for recovery"
                ) from exc
        except CleanupAmbiguousError:
            raise
        except Exception:
            if not os.path.lexists(gate["worktreePath"]):
                raise CleanupAmbiguousError(
                    "Cleanup outcome is ambiguous and protected for recovery"
                ) from exc
        raise


def _protect_cleanup_ambiguity(
    engine: SupervisorEngine, command: Mapping[str, Any]
) -> None:
    with engine.store.mutex():
        state, reservations = engine.store.load_pair_unlocked()
        gate = state["gateWorktrees"].get(command["gateOperationId"])
        if not isinstance(gate, dict):
            raise CleanupAmbiguousError("Cleanup gate evidence is unavailable")
        if gate.get("status") == "ambiguous" and state["recovery"]["status"] == "ambiguous":
            return
        after = copy.deepcopy(state)
        after["gateWorktrees"][command["gateOperationId"]]["status"] = "ambiguous"
        after["recovery"] = {
            "status": "ambiguous",
            "reason": f"ambiguous-cleanup:{command['requestId']}",
            "updatedAtNs": max(
                time.time_ns(), state["clockEvidence"]["lastObservedNowNs"]
            ),
        }
        after["revision"] = state["revision"] + 1
        engine.store.commit_pair_unlocked(
            before_state=state,
            after_state=after,
            before_reservations=reservations,
            after_reservations=reservations,
            operation=f"CleanupAmbiguous:{command['requestId']}",
        )


def _execute(engine: SupervisorEngine, command: Mapping[str, Any]) -> dict[str, Any]:
    operation = command["operation"]
    committed_replay = command.get("_committedReplay") is True
    state, reservations = _state_pair(engine)
    if operation == "AcquireLease":
        return engine.leases.acquire(
            run_id=command["requestId"],
            owner_id=command["ownerId"],
            expected_revision=command["expectedStateRevision"],
        )
    if operation in {"RenewLease", "ReleaseLease"}:
        lease = state.get("lease")
        if not isinstance(lease, dict):
            raise SupervisorCommandError("Lease operation has no current lease")
        arguments = {
            "run_id": command["runId"],
            "owner_id": command["ownerId"],
            "expected_revision": command["expectedStateRevision"],
            "capability_ref": command["leaseCapabilityRef"],
        }
        return (
            engine.leases.renew(operation_id=command["requestId"], **arguments)
            if operation == "RenewLease"
            else engine.leases.release(**arguments)
        )
    if operation == "PrepareIteration":
        lease = state.get("lease")
        if not isinstance(lease, dict) or lease.get("runId") != command["runId"]:
            raise SupervisorCommandError("PrepareIteration run does not own the live lease")
        observed = engine.runtime.observe_repository_identity(command["worktreePath"])
        return engine.leases.prepare_iteration(
            run_id=command["runId"],
            owner_id=lease["ownerId"],
            workflow_id=command["workflowId"],
            issue_id=command["issueId"],
            worktree_path=command["worktreePath"],
            physical_worktree_fingerprint=observed.physical_worktree_fingerprint,
            expected_revision=command["expectedStateRevision"],
            lease_capability_ref=command["leaseCapabilityRef"],
            stage=command["expectedStage"],
        )
    if operation == "ApplyCheckpoint":
        worker_result = _read_public_json(command["workerResultPath"])
        validate_contract("worker-result", worker_result)
        if worker_result.get("runId") != command["runId"]:
            raise SupervisorCommandError("Worker result run differs from EngineCommand")
        return engine.leases.apply_checkpoint(
            prepared_ref=command["preparedIterationRef"],
            transition_id=command["transitionId"],
            expected_revision=command["expectedStateRevision"],
            expected_stage=command["expectedStage"],
            worker_result=worker_result,
        )
    if operation == "Reserve":
        autonomous_ref = command["autonomousCapabilityRef"]
        if (command["policy"] == "autonomous") != isinstance(autonomous_ref, str):
            raise SupervisorCommandError(
                "Reserve capability reference does not match its policy"
            )
        observed = engine.runtime.observe_repository_identity(command["worktreePath"])
        return engine.reservations.reserve(
            reservation_id=command["requestId"],
            workflow_id=command["workflowId"],
            issue_id=command["issueId"],
            worktree_path=command["worktreePath"],
            physical_worktree_fingerprint=observed.physical_worktree_fingerprint,
            policy=command["policy"],
            owner_id=command["ownerId"],
            run_id=command["runId"],
            expected_state_revision=command["expectedStateRevision"],
            expected_reservations_revision=command["expectedReservationsRevision"],
            capability_ref=autonomous_ref,
        )
    if operation == "RenewReservation":
        record = _reservation(reservations, command["reservationId"])
        if record.get("runId") != command["runId"]:
            raise SupervisorCommandError("RenewReservation run binding is mismatched")
        if (record.get("policy") == "autonomous") != isinstance(
            command["autonomousCapabilityRef"], str
        ):
            raise SupervisorCommandError(
                "RenewReservation capability reference does not match its policy"
            )
        return engine.reservations.renew(
            reservation_id=command["reservationId"],
            owner_id=command["ownerId"],
            expected_record_revision=command["expectedReservationRevision"],
            expected_state_revision=command["expectedStateRevision"],
            expected_reservations_revision=command["expectedReservationsRevision"],
            control_authorization_ref=command["reservationControlRef"],
            capability_ref=command["autonomousCapabilityRef"],
        )
    if operation == "AuthorizeMutation":
        record = _reservation(reservations, command["reservationId"])
        if record.get("workflowId") != command["workflowId"]:
            raise SupervisorCommandError("AuthorizeMutation workflow binding is mismatched")
        if (record.get("policy") == "autonomous") != isinstance(
            command["autonomousCapabilityRef"], str
        ):
            raise SupervisorCommandError(
                "AuthorizeMutation capability reference does not match its policy"
            )
        return engine.reservations.authorize_mutation(
            reservation_id=command["reservationId"],
            authorization_id=command["requestId"],
            target_operation_id=command["targetOperationId"],
            scope=command["operationScope"],
            expected_record_revision=command["expectedReservationRevision"],
            expected_state_revision=command["expectedStateRevision"],
            expected_reservations_revision=command["expectedReservationsRevision"],
            control_authorization_ref=command["reservationControlRef"],
            capability_ref=command["autonomousCapabilityRef"],
        )
    if operation == "Release":
        record = _reservation(reservations, command["reservationId"])
        if (record.get("policy") == "autonomous") != isinstance(
            command["autonomousCapabilityRef"], str
        ):
            raise SupervisorCommandError(
                "Release capability reference does not match its policy"
            )
        return engine.reservations.release(
            reservation_id=command["reservationId"],
            authorization_ref=command["reservationControlRef"],
            operation_id=command["requestId"],
            expected_record_revision=command["expectedReservationRevision"],
            expected_state_revision=command["expectedStateRevision"],
            expected_reservations_revision=command["expectedReservationsRevision"],
            capability_ref=command["autonomousCapabilityRef"],
            trusted_observation_ref=command["trustedObservationRef"],
        )
    if operation == "Handoff":
        return execute_assembled_handoff(engine, command)
    if operation == "Recover":
        if state["revision"] != command["expectedStateRevision"]:
            raise SupervisorCommandError("Recover supervisor state revision is stale")
        handoffs: list[dict[str, Any]] = []
        pending_handoffs = [
            operation_id
            for operation_id in engine.operations.pending_ids(
                ignore_operation_id=command["requestId"]
            )
            if engine.operations.load(operation_id)["journal"]["operation"] == "Handoff"
        ]
        if command["operationId"] is not None:
            pending_handoffs = [
                operation_id
                for operation_id in pending_handoffs
                if operation_id == command["operationId"]
            ]
        for operation_id in pending_handoffs:
            evidence = engine.operations.load(operation_id)
            result = recover_assembled_handoff(engine, operation_id)
            status = (
                "completed"
                if result.get("status") == "transferred"
                else "failed"
                if result.get("status") == "restored"
                else "ambiguous"
            )
            engine.operations.complete(
                operation_id=operation_id,
                operation="Handoff",
                request=evidence["request"],
                result=result,
                status=status,
                error_code=None if status == "completed" else "RECOVERED_HANDOFF",
            )
            handoffs.append(result)
        recovered = engine.recovery.recover(ignore_operation_id=command["requestId"])
        if handoffs:
            recovered["handoffs"] = handoffs
        return recovered
    if operation == "Cleanup":
        return _cleanup(engine, command)
    if operation == "PreparePublication":
        if state["revision"] != command["expectedStateRevision"] and not committed_replay:
            raise SupervisorCommandError("PreparePublication supervisor revision is stale")
        publication = _read_public_json(command["publicationStateRef"])
        validate_contract("publication-state", publication)
        return engine.prepare_publication(
            publication_state=publication,
            artifact_manifest=command["artifactManifest"],
            preexisting_paths=command["preexistingPaths"],
            preparation_operation_id=command["preparationOperationId"],
            expected_state_revision=command["expectedStateRevision"],
            reservation_id=command["reservationId"], authorization_ref=command["authorizationRef"],
            expected_record_revision=command["expectedRecordRevision"], expected_reservations_revision=command["expectedReservationsRevision"],
            physical_worktree_fingerprint=command["physicalWorktreeFingerprint"],
            replay_committed=committed_replay,
        )
    if operation == "PublicationProvider":
        if state["revision"] != command["expectedStateRevision"]:
            raise SupervisorCommandError("PublicationProvider supervisor revision is stale")
        return engine.execute_publication_provider(
            operation_id=command["publicationOperationId"],
            provider_operation=command["providerOperation"],
            provider_operation_id=command["providerOperationId"],
            expected_state_revision=command["expectedStateRevision"],
            reservation_id=command["reservationId"], authorization_ref=command["authorizationRef"],
            expected_record_revision=command["expectedRecordRevision"], expected_reservations_revision=command["expectedReservationsRevision"],
            physical_worktree_fingerprint=command["physicalWorktreeFingerprint"],
        )
    if operation == "PublicationGate":
        if state["revision"] != command["expectedStateRevision"]:
            raise SupervisorCommandError("PublicationGate supervisor revision is stale")
        return engine.execute_publication_gate(
            operation_id=command["publicationOperationId"],
            gate_operation_id=command["gateOperationId"],
            exact_sha=command["exactSha"], kind=command["gateKind"],
            started_at=command["startedAt"], completed_at=command["completedAt"],
            expected_state_revision=command["expectedStateRevision"],
            reservation_id=command["reservationId"], authorization_ref=command["authorizationRef"],
            expected_record_revision=command["expectedRecordRevision"], expected_reservations_revision=command["expectedReservationsRevision"],
            physical_worktree_fingerprint=command["physicalWorktreeFingerprint"],
        )
    if operation == "RecordPublicationAttestation":
        if state["revision"] != command["expectedStateRevision"] and not (
            committed_replay and "evidencePaths" in command
        ):
            raise SupervisorCommandError("RecordPublicationAttestation supervisor revision is stale")
        if "evidencePaths" in command:
            return engine.finalize_publication_evidence(
                operation_id=command["publicationOperationId"],
                finalization_operation_id=command["attestationId"],
                evidence_paths=command["evidencePaths"],
                draft_inventory=command["draftInventory"],
                design_required=command["designRequired"],
                expected_state_revision=command["expectedStateRevision"],
                reservation_id=command["reservationId"], authorization_ref=command["authorizationRef"],
                expected_record_revision=command["expectedRecordRevision"], expected_reservations_revision=command["expectedReservationsRevision"],
                physical_worktree_fingerprint=command["physicalWorktreeFingerprint"],
                replay_committed=committed_replay,
            )
        return engine.record_publication_attestation(
            operation_id=command["publicationOperationId"],
            attestation_id=command["attestationId"], source_operation_id=command["sourceOperationId"],
            expected_state_revision=command["expectedStateRevision"],
            reservation_id=command["reservationId"], authorization_ref=command["authorizationRef"],
            expected_record_revision=command["expectedRecordRevision"], expected_reservations_revision=command["expectedReservationsRevision"],
            physical_worktree_fingerprint=command["physicalWorktreeFingerprint"],
        )
    if operation == "PublicationRepair":
        if state["revision"] != command["expectedStateRevision"] and not committed_replay:
            raise SupervisorCommandError("PublicationRepair supervisor revision is stale")
        return engine.next_publication_repair(
            operation_id=command["publicationOperationId"],
            repair_operation_id=command["repairOperationId"],
            current_main_sha=command["currentMainSha"],
            artifact_manifest=command.get("artifactManifest"),
            preexisting_paths=command.get("preexistingPaths"),
            expected_state_revision=command["expectedStateRevision"],
            reservation_id=command["reservationId"], authorization_ref=command["authorizationRef"],
            expected_record_revision=command["expectedRecordRevision"], expected_reservations_revision=command["expectedReservationsRevision"],
            physical_worktree_fingerprint=command["physicalWorktreeFingerprint"],
            replay_committed=committed_replay,
        )
    if operation == "RecoverPublication":
        if state["revision"] != command["expectedStateRevision"]:
            raise SupervisorCommandError("RecoverPublication supervisor revision is stale")
        return engine.recover_publication(
            operation_id=command["publicationOperationId"], now=command["requestedAt"],
            attended=command.get("attended"), recovery_operation_id=command["recoveryOperationId"],
            expected_state_revision=command["expectedStateRevision"], reservation_id=command["reservationId"],
            authorization_ref=command["authorizationRef"], expected_record_revision=command["expectedRecordRevision"],
            expected_reservations_revision=command["expectedReservationsRevision"],
            physical_worktree_fingerprint=command["physicalWorktreeFingerprint"],
        )
    raise SupervisorCommandError(f"Operation {operation} is not assembled")


def _journaled(
    engine: SupervisorEngine,
    command: Mapping[str, Any],
    action: Callable[[], Mapping[str, Any]],
    committed_replay_action: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    operation_id = command["requestId"]
    operation = command["operation"]
    begun = engine.operations.begin(
        operation_id=operation_id,
        operation=operation,
        request=command,
    )
    if begun["status"] == "replayed":
        replay = begun["result"]
        if replay.get("status") in {"failed", "ambiguous"}:
            raise SupervisorCommandError(f"Replayed {operation} remains {replay['status']}")
        return replay
    if begun["status"] == "pending":
        if operation not in {
            "PreparePublication", "PublicationProvider", "PublicationGate",
            "RecordPublicationAttestation", "PublicationRepair", "RecoverPublication",
        }:
            raise SupervisorCommandError("Operation requires deterministic recovery before replay")
        # Publication operations are exact-ID/head bound and every external
        # mutation performs authoritative readback before repeating. Resume the
        # same action so its operation result can converge after a crash.
    try:
        result = dict(
            committed_replay_action()
            if begun["status"] == "pending" and committed_replay_action is not None
            else action()
        )
    except Exception as exc:
        from .publication_git import PublicationGitCommittedInterruption
        if isinstance(exc, PublicationGitCommittedInterruption):
            # A real process crash would leave the request pending. Preserve
            # that exact replay boundary in fixtures rather than terminalizing
            # the command after the immutable Git commit already exists.
            raise
        status = "failed"
        if isinstance(exc, CleanupAmbiguousError) or (
            isinstance(exc, AssembledHandoffError)
            and any(word in str(exc).casefold() for word in ("ambiguous", "protected"))
        ):
            status = "ambiguous"
        engine.operations.complete(
            operation_id=operation_id,
            operation=operation,
            request=command,
            result={"status": status, "error": f"{operation} failed closed"},
            status=status,
        )
        raise
    return engine.operations.complete(
        operation_id=operation_id,
        operation=operation,
        request=command,
        result=result,
    )


def run_request(request_path: str | Path) -> dict[str, Any]:
    raw = _read_public_json(request_path)
    command = validate_engine_command(raw)
    _validate_command_path(request_path, command)
    if command["operation"] == "Preflight":
        return _preflight(command)
    assembly = _FIXTURE_ASSEMBLIES.get(_normalized(command["stateHome"]))
    engine = SupervisorEngine(
        command["repositoryRoot"],
        repository_key=command["repositoryKey"],
        state_home_override=Path(command["stateHome"]).parent,
        publication_provider=assembly.publication_provider if assembly else None,
        publication_recovery=assembly.publication_recovery if assembly else None,
        publication_git=assembly.publication_git if assembly else None,
        publication_gate_runner=assembly.publication_gate_runner if assembly else None,
        clock=assembly.clock if assembly else None,
        reservation_clock=assembly.reservation_clock if assembly else None,
    )
    if _normalized(engine.store.root) != _normalized(command["stateHome"]):
        raise SupervisorCommandError("EngineCommand state home differs from canonical authority")
    if command["operation"] == "Status":
        return engine.status()
    return _journaled(
        engine, command, lambda: _execute(engine, command),
        committed_replay_action=lambda: _execute(
            engine, {**command, "_committedReplay": True}
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-worker-engine")
    parser.add_argument("--request", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = run_request(arguments.request)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        # Load the base redactor only when available; never print a traceback.
        try:
            if __package__ in {None, ""}:
                from scripts.base_runtime import load_base_runtime
            else:
                from .base_runtime import load_base_runtime

            error = load_base_runtime().redact_value(str(exc))
        except Exception:
            error = "Supervisor command failed closed"
        print(
            json.dumps({"status": "failed", "error": error}, sort_keys=True),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
