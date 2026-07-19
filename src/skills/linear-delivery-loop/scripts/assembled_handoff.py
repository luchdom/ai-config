"""Crash-recoverable reservation-aware assembly over canonical base Handoff."""

from __future__ import annotations

import hashlib
import hmac
import importlib
import os
import secrets
import subprocess
import uuid
from pathlib import Path
from typing import Any, Mapping

from .store import sha256_json
from .supervisor import SupervisorEngine


class AssembledHandoffError(RuntimeError):
    """The assembled transition failed or remains protected for recovery."""


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(os.path.realpath(right))


def _git(repository: Path, *arguments: str, allowed: tuple[int, ...] = (0,)) -> bytes:
    completed = subprocess.run(
        ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
        check=False,
        capture_output=True,
        shell=False,
    )
    if completed.returncode not in allowed:
        raise AssembledHandoffError("Git Handoff reconciliation probe failed")
    return completed.stdout


def _destination_observation(engine: SupervisorEngine, destination: Path) -> dict[str, str]:
    identity = engine.runtime.observe_repository_identity(destination)
    symbolic = _git(destination, "symbolic-ref", "-q", "HEAD", allowed=(0, 1))
    status = _git(destination, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return {
        "repositoryId": identity.repository_id,
        "physicalWorktreeFingerprint": identity.physical_worktree_fingerprint,
        "headSha": _git(destination, "rev-parse", "--verify", "HEAD").decode(
            "ascii", "strict"
        ).strip(),
        "symbolicHead": symbolic.decode("utf-8", "strict").strip(),
        "statusSha256": "sha256:" + hashlib.sha256(status).hexdigest(),
    }


def _registry_entry(engine: SupervisorEngine, workflow_id: str) -> dict[str, Any] | None:
    manager = engine.manager
    with manager.registry.mutex():
        registry = manager._load_registry_unlocked()
        return registry["workflows"].get(workflow_id)


def _evidence_ids(engine: SupervisorEngine, workflow_id: str) -> set[str]:
    root = engine.manager.home.repository / "handoffs" / workflow_id
    if not os.path.lexists(root):
        return set()
    canonical = engine.manager.state_paths.directory(root)
    result: set[str] = set()
    for child in canonical.iterdir():
        directory = engine.manager.state_paths.directory(child)
        try:
            if str(uuid.UUID(directory.name)) != directory.name:
                raise ValueError
        except (TypeError, ValueError, AttributeError) as exc:
            raise AssembledHandoffError("Canonical Handoff evidence contains an invalid identity") from exc
        result.add(directory.name)
    return result


def _context_bundle_path(engine: SupervisorEngine, operation_id: str) -> Path:
    return (
        engine.store.directories["handoff-authorizations"]
        / f"{operation_id}.assembly"
    )


def _context_path(engine: SupervisorEngine, operation_id: str) -> Path:
    return _context_bundle_path(engine, operation_id) / "context.json"


def _read_context_anchor(
    engine: SupervisorEngine,
    *,
    operation_id: str,
    expected_context_digest: str,
) -> dict[str, Any]:
    bundle = engine.store.guard.directory(
        _context_bundle_path(engine, operation_id)
    )
    anchor = engine.store.guard.read_json(
        engine.store.guard.leaf(bundle / "anchor.json", must_exist=True)
    )
    sidecar = engine.store.guard.read_json(
        engine.store.guard.leaf(bundle / "anchor.capability.json", must_exist=True)
    )
    nonce = sidecar.get("nonce")
    required_anchor = {
        "schemaVersion",
        "operationId",
        "contextSha256",
        "contextMacSha256",
        "nonceSha256",
        "status",
    }
    required_sidecar = {
        "schemaVersion",
        "operationId",
        "kind",
        "nonce",
        "nonceSha256",
        "status",
    }
    if (
        set(anchor) != required_anchor
        or set(sidecar) != required_sidecar
        or anchor.get("schemaVersion") != "1.0"
        or sidecar.get("schemaVersion") != "1.0"
        or anchor.get("operationId") != operation_id
        or sidecar.get("operationId") != operation_id
        or anchor.get("contextSha256") != expected_context_digest
        or not isinstance(nonce, str)
        or not hmac.compare_digest(
            str(anchor.get("contextMacSha256")),
            "sha256:"
            + hmac.new(
                nonce.encode("utf-8"),
                expected_context_digest.encode("ascii"),
                hashlib.sha256,
            ).hexdigest(),
        )
        or anchor.get("status") != "active"
        or sidecar.get("kind") != "handoff-recovery-context"
        or sidecar.get("status") != "active"
        or "sha256:" + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        != anchor.get("nonceSha256")
        or sidecar.get("nonceSha256") != anchor.get("nonceSha256")
    ):
        raise AssembledHandoffError(
            "Assembled Handoff recovery context anchor is malformed or mismatched"
        )
    return anchor


def _write_recovery_context(
    engine: SupervisorEngine,
    *,
    operation_id: str,
    workflow_id: str,
    source_fingerprint: str,
    destination_fingerprint: str,
    destination_path: Path,
    expected_paths: list[str],
    prior_evidence_ids: set[str],
    destination_observation: dict[str, str],
) -> dict[str, Any]:
    context = {
        "schemaVersion": "1.0",
        "operationId": operation_id,
        "workflowId": workflow_id,
        "sourceFingerprint": source_fingerprint,
        "destinationFingerprint": destination_fingerprint,
        "destinationPath": os.fspath(destination_path),
        "expectedPaths": list(expected_paths),
        "priorEvidenceIds": sorted(prior_evidence_ids),
        "destinationObservation": dict(destination_observation),
    }
    context_digest = "sha256:" + sha256_json(context)
    bundle = _context_bundle_path(engine, operation_id)
    path = _context_path(engine, operation_id)
    if os.path.lexists(bundle):
        bundle = engine.store.guard.directory(bundle)
        if engine.store.guard.read_json(
            engine.store.guard.leaf(path, must_exist=True)
        ) != context:
            raise AssembledHandoffError("Assembled Handoff recovery context was replayed or changed")
        _read_context_anchor(
            engine,
            operation_id=operation_id,
            expected_context_digest=context_digest,
        )
    else:
        temporary = engine.store.guard.directory(
            bundle.parent / f".{operation_id}.{uuid.uuid4()}.assembly.tmp",
            create=True,
        )
        nonce = secrets.token_urlsafe(48)
        nonce_digest = "sha256:" + hashlib.sha256(
            nonce.encode("utf-8")
        ).hexdigest()
        context_mac = "sha256:" + hmac.new(
            nonce.encode("utf-8"),
            context_digest.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        engine.store.guard.write_json(temporary / "context.json", context)
        engine.store.guard.write_json(
            temporary / "anchor.json",
            {
                "schemaVersion": "1.0",
                "operationId": operation_id,
                "contextSha256": context_digest,
                "contextMacSha256": context_mac,
                "nonceSha256": nonce_digest,
                "status": "active",
            },
        )
        engine.store.guard.write_json(
            temporary / "anchor.capability.json",
            {
                "schemaVersion": "1.0",
                "operationId": operation_id,
                "kind": "handoff-recovery-context",
                "nonce": nonce,
                "nonceSha256": nonce_digest,
                "status": "active",
            },
        )
        os.replace(temporary, bundle)
    return context


def _read_recovery_context(
    engine: SupervisorEngine,
    *,
    operation_id: str,
    authorization: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    path = _context_path(engine, operation_id)
    context = engine.store.guard.read_json(
        engine.store.guard.leaf(path, must_exist=True)
    )
    _read_context_anchor(
        engine,
        operation_id=operation_id,
        expected_context_digest="sha256:" + sha256_json(context),
    )
    required = {
        "schemaVersion",
        "operationId",
        "workflowId",
        "sourceFingerprint",
        "destinationFingerprint",
        "destinationPath",
        "expectedPaths",
        "priorEvidenceIds",
        "destinationObservation",
    }
    if set(context) != required or context.get("schemaVersion") != "1.0":
        raise AssembledHandoffError("Assembled Handoff recovery context is malformed")
    bindings = {
        "operationId": operation_id,
        "workflowId": authorization.get("workflowId"),
        "sourceFingerprint": authorization.get("sourceFingerprint"),
        "destinationFingerprint": authorization.get("destinationFingerprint"),
        "destinationPath": request.get("destinationPath"),
        "expectedPaths": request.get("expectedPaths"),
    }
    if any(context.get(field) != expected for field, expected in bindings.items()):
        raise AssembledHandoffError("Assembled Handoff recovery context binding is mismatched")
    prior = context.get("priorEvidenceIds")
    observation = context.get("destinationObservation")
    if (
        not isinstance(prior, list)
        or prior != sorted(set(prior))
        or not all(isinstance(item, str) for item in prior)
        or not isinstance(observation, dict)
        or set(observation)
        != {
            "repositoryId",
            "physicalWorktreeFingerprint",
            "headSha",
            "symbolicHead",
            "statusSha256",
        }
        or observation.get("repositoryId") != engine.manager.identity.repository_id
        or observation.get("physicalWorktreeFingerprint")
        != authorization.get("destinationFingerprint")
        or observation.get("statusSha256")
        != "sha256:" + hashlib.sha256(b"").hexdigest()
    ):
        raise AssembledHandoffError("Assembled Handoff recovery observation is malformed")
    return context


def _recover_pre_phase_a(
    engine: SupervisorEngine,
    *,
    operation_id: str,
    state: Mapping[str, Any],
    reservations: Mapping[str, Any],
) -> dict[str, Any]:
    """Close a journal when immutable context proves Phase A never committed."""

    evidence = engine.operations.load(operation_id)
    request = evidence["request"]
    context = engine.store.guard.read_json(
        engine.store.guard.leaf(_context_path(engine, operation_id), must_exist=True)
    )
    _read_context_anchor(
        engine,
        operation_id=operation_id,
        expected_context_digest="sha256:" + sha256_json(context),
    )
    required_context = {
        "schemaVersion",
        "operationId",
        "workflowId",
        "sourceFingerprint",
        "destinationFingerprint",
        "destinationPath",
        "expectedPaths",
        "priorEvidenceIds",
        "destinationObservation",
    }
    source = engine.runtime.observe_repository_identity(request.get("sourcePath"))
    destination = engine.runtime.observe_repository_identity(
        request.get("destinationPath")
    )
    record = reservations.get("reservations", {}).get(request.get("reservationId"))
    prior = context.get("priorEvidenceIds")
    observation = context.get("destinationObservation")
    if (
        evidence["journal"].get("operation") != "Handoff"
        or evidence["journal"].get("status") not in {"pending", "failed"}
        or not isinstance(request, dict)
        or request.get("schemaVersion") != "1.0"
        or request.get("operation") != "Handoff"
        or request.get("requestId") != operation_id
        or set(context) != required_context
        or context.get("schemaVersion") != "1.0"
        or context.get("operationId") != operation_id
        or context.get("workflowId") != request.get("workflowId")
        or context.get("sourceFingerprint")
        != source.physical_worktree_fingerprint
        or context.get("destinationFingerprint")
        != destination.physical_worktree_fingerprint
        or not _same_path(context.get("destinationPath", ""), request.get("destinationPath", ""))
        or context.get("expectedPaths") != request.get("expectedPaths")
        or not isinstance(prior, list)
        or prior != sorted(set(prior))
        or not all(isinstance(item, str) for item in prior)
        or not isinstance(observation, dict)
        or set(observation)
        != {
            "repositoryId",
            "physicalWorktreeFingerprint",
            "headSha",
            "symbolicHead",
            "statusSha256",
        }
        or observation.get("repositoryId") != engine.manager.identity.repository_id
        or observation.get("physicalWorktreeFingerprint")
        != destination.physical_worktree_fingerprint
        or observation.get("statusSha256")
        != "sha256:" + hashlib.sha256(b"").hexdigest()
        or state.get("handoffPending") is not None
        or state.get("revision") != request.get("expectedStateRevision")
        or reservations.get("revision") != request.get("expectedReservationsRevision")
        or not isinstance(record, dict)
        or record.get("status") != "live"
        or record.get("revision") != request.get("expectedReservationRevision")
        or record.get("workflowId") != request.get("workflowId")
        or record.get("releaseAuthorizationRef")
        != request.get("reservationControlRef")
        or record.get("physicalWorktreeFingerprint")
        != source.physical_worktree_fingerprint
        or not _same_path(record.get("worktreePath", ""), request.get("sourcePath", ""))
        or _registry_entry(engine, request["workflowId"]) is None
        or _registry_entry(engine, request["workflowId"]).get(
            "physicalWorktreeFingerprint"
        )
        != source.physical_worktree_fingerprint
        or not _no_base_mutation_is_exact(engine, context=context)
    ):
        raise AssembledHandoffError(
            "Pre-Phase-A Handoff recovery evidence is incomplete or mismatched"
        )
    return {
        "schemaVersion": "1.0",
        "status": "restored",
        "operationId": operation_id,
        "workflowId": request["workflowId"],
        "baseHandoff": "not-started",
        "reservation": {
            "status": "unchanged",
            "reservationId": record["reservationId"],
            "reservationRevision": record["revision"],
        },
    }


def _read_operation_request(
    engine: SupervisorEngine,
    *,
    operation_id: str,
    authorization: Mapping[str, Any],
) -> dict[str, Any]:
    request_path = engine.store.guard.leaf(
        engine.store.directories["operations"] / operation_id / "request.json",
        must_exist=True,
    )
    record = engine.store.guard.read_json(request_path)
    required = {"schemaVersion", "operationId", "operation", "requestSha256", "request"}
    request = record.get("request")
    interlock = importlib.import_module(
        f"{engine.runtime.package.__name__}.reservation_interlock"
    )
    source_identity = None
    destination_identity = None
    if isinstance(request, dict):
        try:
            source_identity = engine.runtime.observe_repository_identity(request.get("sourcePath"))
            destination_identity = engine.runtime.observe_repository_identity(
                request.get("destinationPath")
            )
        except Exception:
            pass
    expected_paths = request.get("expectedPaths") if isinstance(request, dict) else None
    expected_digest = (
        "sha256:"
        + hashlib.sha256(
            "\n".join(sorted(expected_paths, key=str.casefold)).encode("utf-8")
        ).hexdigest()
        if isinstance(expected_paths, list)
        and all(isinstance(item, str) for item in expected_paths)
        else None
    )
    expected_request_hash = None
    if source_identity is not None and destination_identity is not None and expected_digest is not None:
        try:
            expected_request_hash = interlock.handoff_request_hash(
                operation_id=operation_id,
                workflow_id=request["workflowId"],
                repository_key=request["repositoryKey"],
                source_fingerprint=source_identity.physical_worktree_fingerprint,
                destination_fingerprint=destination_identity.physical_worktree_fingerprint,
                expected_paths=expected_paths,
                reservation_id=request["reservationId"],
                reservation_revision=authorization["reservationRevision"],
            )
        except Exception:
            pass
    failures = [
        label
        for label, valid in (
            ("shape", set(record) == required),
            ("schema", record.get("schemaVersion") == "1.0"),
            ("operation-id", record.get("operationId") == operation_id),
            ("operation", record.get("operation") == "Handoff"),
            ("request-object", isinstance(request, dict)),
            (
                "request-hash",
                isinstance(request, dict)
                and record.get("requestSha256") == "sha256:" + sha256_json(request),
            ),
            ("request-schema", isinstance(request, dict) and request.get("schemaVersion") == "1.0"),
            ("request-operation", isinstance(request, dict) and request.get("operation") == "Handoff"),
            ("request-id", isinstance(request, dict) and request.get("requestId") == operation_id),
            (
                "workflow-binding",
                isinstance(request, dict)
                and request.get("workflowId") == authorization.get("workflowId"),
            ),
            (
                "repository-binding",
                isinstance(request, dict)
                and request.get("repositoryKey") == authorization.get("repositoryKey"),
            ),
            (
                "reservation-binding",
                isinstance(request, dict)
                and request.get("reservationId") == authorization.get("reservationId")
                and isinstance(request.get("expectedReservationRevision"), int)
                and request.get("expectedReservationRevision") + 1
                == authorization.get("reservationRevision"),
            ),
            (
                "source-binding",
                source_identity is not None
                and source_identity.repository_id == engine.manager.identity.repository_id
                and source_identity.physical_worktree_fingerprint
                == authorization.get("sourceFingerprint"),
            ),
            (
                "destination-binding",
                destination_identity is not None
                and destination_identity.repository_id == engine.manager.identity.repository_id
                and destination_identity.physical_worktree_fingerprint
                == authorization.get("destinationFingerprint"),
            ),
            (
                "path-digest",
                expected_digest is not None
                and expected_digest == authorization.get("expectedPathDigest"),
            ),
            (
                "authorization-request-hash",
                expected_request_hash is not None
                and expected_request_hash == authorization.get("requestHash"),
            ),
        )
        if not valid
    ]
    if failures:
        raise AssembledHandoffError(
            "Pending Handoff request evidence is mismatched (" + ", ".join(failures) + ")"
        )
    return request


def _failure_evidence_is_exact(
    engine: SupervisorEngine,
    *,
    context: Mapping[str, Any],
) -> bool:
    workflow_id = context["workflowId"]
    try:
        new_ids = _evidence_ids(engine, workflow_id) - set(context["priorEvidenceIds"])
        if len(new_ids) != 1:
            return False
        handoff_id = next(iter(new_ids))
        evidence_dir = engine.manager.state_paths.directory(
            engine.manager.home.repository / "handoffs" / workflow_id / handoff_id
        )
        result = engine.manager.state_paths.read_json(
            engine.manager.state_paths.leaf(evidence_dir / "result.json", must_exist=True)
        )
        required = {
            "schemaVersion",
            "status",
            "workflowId",
            "handoffId",
            "originalError",
            "rollbackStatus",
            "rollbackError",
            "destinationReconciliationRequired",
            "sourceRemainsAuthoritative",
            "reservationTransferred",
            "gitMutationPerformed",
        }
        if (
            set(result) != required
            or result.get("schemaVersion") != "1.0"
            or result.get("status") != "failed"
            or result.get("workflowId") != workflow_id
            or result.get("handoffId") != handoff_id
            or not isinstance(result.get("originalError"), str)
            or not result["originalError"]
            or result.get("rollbackStatus") not in {"not-required", "rollback-complete"}
            or result.get("rollbackError") is not None
            or result.get("destinationReconciliationRequired") is not False
            or result.get("sourceRemainsAuthoritative") is not True
            or result.get("reservationTransferred") is not False
            or result.get("gitMutationPerformed") is not False
        ):
            return False
        manifest = evidence_dir / "manifest.json"
        patch = evidence_dir / "patch.diff"
        manifest_exists = os.path.lexists(manifest)
        patch_exists = os.path.lexists(patch)
        if manifest_exists != patch_exists:
            return False
        if result["rollbackStatus"] == "rollback-complete" and not manifest_exists:
            return False
        if manifest_exists:
            manifest_value = engine.manager.state_paths.read_json(
                engine.manager.state_paths.leaf(manifest, must_exist=True)
            )
            engine.manager.registry._validate_handoff_manifest(
                workflow_id, handoff_id, manifest_value
            )
            engine.manager.state_paths.leaf(patch, must_exist=True)
        observed = _destination_observation(engine, Path(context["destinationPath"]))
        return observed == context["destinationObservation"]
    except Exception:
        return False


def _no_base_mutation_is_exact(
    engine: SupervisorEngine,
    *,
    context: Mapping[str, Any],
) -> bool:
    """Prove Phase B made no durable transfer before restoring authority."""

    try:
        if _evidence_ids(engine, context["workflowId"]) != set(
            context["priorEvidenceIds"]
        ):
            return False
        return _destination_observation(
            engine, Path(context["destinationPath"])
        ) == context["destinationObservation"]
    except Exception:
        return False


def _same_transfer_content(source: Path, destination: Path, paths: list[str]) -> bool:
    try:
        for raw in paths:
            relative = Path(raw)
            source_path = source / relative
            destination_path = destination / relative
            if source_path.exists():
                if not source_path.is_file() or not destination_path.is_file():
                    return False
                if source_path.read_bytes() != destination_path.read_bytes():
                    return False
            elif destination_path.exists():
                return False
        return True
    except OSError:
        return False


def _success_evidence_is_exact(
    engine: SupervisorEngine,
    *,
    workflow_id: str,
    source_path: Path,
    destination_path: Path,
    expected_paths: list[str],
    source_fingerprint: str,
    destination_fingerprint: str,
) -> bool:
    try:
        entry = _registry_entry(engine, workflow_id)
        if (
            entry is None
            or entry.get("physicalWorktreeFingerprint") != destination_fingerprint
            or not entry.get("handoffs")
        ):
            return False
        handoff = entry["handoffs"][-1]
        if (
            handoff.get("sourceFingerprint") != source_fingerprint
            or handoff.get("destinationFingerprint") != destination_fingerprint
        ):
            return False
        destination_identity = engine.runtime.observe_repository_identity(destination_path)
        if (
            destination_identity.repository_id != engine.manager.identity.repository_id
            or destination_identity.physical_worktree_fingerprint != destination_fingerprint
        ):
            return False
        artifact = Path(entry["artifactPath"])
        descriptor_relative = artifact.relative_to(destination_path) / "workflow.json"
        expected_changed = set(expected_paths) | {descriptor_relative.as_posix()}
        handoff_module = importlib.import_module(
            f"{engine.runtime.package.__name__}.handoff"
        )
        source_changed = {
            item.as_posix() for item in handoff_module._changed_paths(source_path)
        }
        destination_changed = {
            item.as_posix() for item in handoff_module._changed_paths(destination_path)
        }
        if source_changed != expected_changed or destination_changed != expected_changed:
            return False
        if not _same_transfer_content(source_path, destination_path, expected_paths):
            return False
        evidence_dir = Path(handoff["evidencePath"])
        manifest = engine.manager.state_paths.read_json(
            engine.manager.state_paths.leaf(evidence_dir / "manifest.json", must_exist=True)
        )
        return len(manifest["changes"]) == len(expected_changed)
    except Exception:
        return False


def _protect(engine: SupervisorEngine, operation_id: str) -> None:
    try:
        protected = engine.reservations.finalize_handoff(
            operation_id=operation_id,
            outcome="ambiguous",
        )
        if protected.get("status") == "protected":
            return
    except Exception:
        pass
    try:
        # Phase C may already have cleared the pending barrier while the outer
        # Handoff journal is still pending.  Incomplete finalized evidence must
        # therefore activate the repository recovery barrier explicitly.
        engine.recovery._protect_ambiguity(operation_id)
    except Exception:
        # Protection is best-effort only when canonical state itself cannot be
        # read or committed; callers continue to fail closed.
        pass


def execute_assembled_handoff(
    engine: SupervisorEngine,
    command: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute Phase A/base Phase B/Phase C for one validated Handoff command."""

    request = dict(command)
    manager = engine.manager
    workflow_id = request["workflowId"]
    operation_id = request["requestId"]
    source_path = Path(request["sourcePath"])
    destination_path = Path(request["destinationPath"])
    expected_paths = list(request["expectedPaths"])
    source_identity = engine.runtime.observe_repository_identity(source_path)
    destination_identity = engine.runtime.observe_repository_identity(destination_path)
    if (
        source_identity.repository_id != manager.identity.repository_id
        or destination_identity.repository_id != manager.identity.repository_id
    ):
        raise AssembledHandoffError("Handoff destination belongs to another Git common directory")
    if (
        source_identity.physical_worktree_fingerprint
        == destination_identity.physical_worktree_fingerprint
    ):
        raise AssembledHandoffError("Handoff source and destination must be distinct worktrees")

    prior_evidence = _evidence_ids(engine, workflow_id)
    destination_before = _destination_observation(engine, destination_path)
    if destination_before["statusSha256"] != "sha256:" + hashlib.sha256(b"").hexdigest():
        raise AssembledHandoffError(
            "Handoff destination must be clean before Phase A"
        )
    context = _write_recovery_context(
        engine,
        operation_id=operation_id,
        workflow_id=workflow_id,
        source_fingerprint=source_identity.physical_worktree_fingerprint,
        destination_fingerprint=destination_identity.physical_worktree_fingerprint,
        destination_path=destination_path,
        expected_paths=expected_paths,
        prior_evidence_ids=prior_evidence,
        destination_observation=destination_before,
    )
    authorization = engine.reservations.prepare_handoff_authorization(
        reservation_id=request["reservationId"],
        operation_id=operation_id,
        workflow_id=workflow_id,
        source_fingerprint=source_identity.physical_worktree_fingerprint,
        destination_fingerprint=destination_identity.physical_worktree_fingerprint,
        expected_paths=expected_paths,
        request=request,
        control_authorization_ref=request["reservationControlRef"],
        capability_ref=request["autonomousCapabilityRef"],
        expected_reservation_revision=request["expectedReservationRevision"],
        expected_state_revision=request["expectedStateRevision"],
        expected_reservations_revision=request["expectedReservationsRevision"],
    )
    if authorization.get("operationId") != operation_id:
        raise AssembledHandoffError("Prepared Handoff authorization identity mismatched")
    try:
        nonce = engine.reservations.resolve_handoff_authorization(operation_id)
        interlock = importlib.import_module(
            f"{engine.runtime.package.__name__}.reservation_interlock"
        )
        internal_authorization = interlock.InternalHandoffAuthorization(
            operation_id=operation_id,
            nonce=nonce,
        )
    except Exception as exc:
        _protect(engine, operation_id)
        raise AssembledHandoffError(
            "Assembled Handoff Phase A recovery evidence is incomplete; authority remains protected"
        ) from exc

    try:
        base_result = manager.workflow_managed_handoff(
            workflow_id=workflow_id,
            destination_root=destination_path,
            expected_paths=expected_paths,
            _reservation_authorization=internal_authorization,
            _editing_source_root=source_path,
        )
    except Exception as exc:
        try:
            entry = _registry_entry(engine, workflow_id)
            observed = None if entry is None else entry.get("physicalWorktreeFingerprint")
        except Exception:
            observed = None
        if (
            observed == source_identity.physical_worktree_fingerprint
            and _failure_evidence_is_exact(engine, context=context)
        ):
            restored = engine.reservations.finalize_handoff(
                operation_id=operation_id,
                outcome="proven-failure",
            )
            return {
                "schemaVersion": "1.0",
                "status": "restored",
                "operationId": operation_id,
                "workflowId": workflow_id,
                "baseHandoff": "proven-failure",
                "reservation": restored,
            }
        if (
            observed == destination_identity.physical_worktree_fingerprint
            and _success_evidence_is_exact(
                engine,
                workflow_id=workflow_id,
                source_path=source_path,
                destination_path=destination_path,
                expected_paths=expected_paths,
                source_fingerprint=source_identity.physical_worktree_fingerprint,
                destination_fingerprint=destination_identity.physical_worktree_fingerprint,
            )
        ):
            transferred = engine.reservations.finalize_handoff(
                operation_id=operation_id,
                outcome="succeeded",
                destination_fingerprint=destination_identity.physical_worktree_fingerprint,
                destination_worktree_path=destination_path,
            )
            return {
                "schemaVersion": "1.0",
                "status": "transferred",
                "operationId": operation_id,
                "workflowId": workflow_id,
                "baseHandoff": "completed-before-observed-error",
                "reservation": transferred,
            }
        _protect(engine, operation_id)
        raise AssembledHandoffError(
            "Canonical base Handoff outcome is ambiguous; authority remains protected"
        ) from exc

    if not _success_evidence_is_exact(
        engine,
        workflow_id=workflow_id,
        source_path=source_path,
        destination_path=destination_path,
        expected_paths=expected_paths,
        source_fingerprint=source_identity.physical_worktree_fingerprint,
        destination_fingerprint=destination_identity.physical_worktree_fingerprint,
    ):
        _protect(engine, operation_id)
        raise AssembledHandoffError(
            "Canonical base Handoff success evidence is incomplete; authority remains protected"
        )
    transferred = engine.reservations.finalize_handoff(
        operation_id=operation_id,
        outcome="succeeded",
        destination_fingerprint=destination_identity.physical_worktree_fingerprint,
        destination_worktree_path=destination_path,
    )
    return {
        "schemaVersion": "1.0",
        "status": "transferred",
        "operationId": operation_id,
        "workflowId": workflow_id,
        "baseHandoff": base_result,
        "reservation": transferred,
    }


def recover_assembled_handoff(
    engine: SupervisorEngine,
    operation_id: str,
) -> dict[str, Any]:
    """Reconcile one protected pending Handoff from bound canonical evidence."""

    with engine.store.mutex():
        state, reservations = engine.store.load_pair_unlocked()
        pending = state.get("handoffPending")
        if pending is not None and pending.get("operationId") != operation_id:
            raise AssembledHandoffError("Another assembled Handoff is pending")
    authorization_candidate = engine.store.guard.leaf(
        engine.store.directories["handoff-authorizations"] / f"{operation_id}.json"
    )
    if not authorization_candidate.exists():
        try:
            return _recover_pre_phase_a(
                engine,
                operation_id=operation_id,
                state=state,
                reservations=reservations,
            )
        except Exception as exc:
            _protect(engine, operation_id)
            raise AssembledHandoffError(
                "Pre-Phase-A Handoff recovery evidence is missing or mismatched; authority remains protected"
            ) from exc
    try:
        authorization_path = engine.store.guard.leaf(
            authorization_candidate, must_exist=True
        )
        authorization = engine.store.guard.read_json(authorization_path)
        workflow_id = authorization.get("workflowId")
        request = _read_operation_request(
            engine, operation_id=operation_id, authorization=authorization
        )
        context = _read_recovery_context(
            engine,
            operation_id=operation_id,
            authorization=authorization,
            request=request,
        )
    except Exception as exc:
        _protect(engine, operation_id)
        raise AssembledHandoffError(
            "Assembled Handoff recovery evidence is missing or mismatched; authority remains protected"
        ) from exc
    try:
        entry = _registry_entry(engine, workflow_id)
        observed = None if entry is None else entry.get("physicalWorktreeFingerprint")
    except Exception:
        observed = None
    if pending is None:
        reservation = reservations["reservations"].get(authorization.get("reservationId"))
        if not isinstance(reservation, dict):
            _protect(engine, operation_id)
            return {
                "status": "protected",
                "operationId": operation_id,
                "reason": "Finalized Handoff reservation evidence is absent",
            }
        final_ref = reservation.get("releaseAuthorizationRef")
        try:
            control = engine.reservations._resolve_authorization(
                final_ref, expected_kind="release"
            )
        except Exception:
            control = None
        expected_fingerprint = (
            authorization.get("destinationFingerprint")
            if observed == authorization.get("destinationFingerprint")
            else authorization.get("sourceFingerprint")
        )
        expected_path = (
            request["destinationPath"]
            if expected_fingerprint == authorization.get("destinationFingerprint")
            else request["sourcePath"]
        )
        binding = None if control is None else control.get("binding")
        state_bindings_ok = (
            state.get("handoffPending") is None
            and reservation.get("status") == "live"
            and reservation.get("pendingHandoffOperationId") is None
            and reservation.get("workflowId") == workflow_id
            and reservation.get("physicalWorktreeFingerprint") == expected_fingerprint
            and _same_path(reservation.get("worktreePath", ""), expected_path)
            and isinstance(binding, dict)
            and binding.get("reservationId") == reservation.get("reservationId")
            and binding.get("reservationRevision") == reservation.get("revision")
            and binding.get("stateRevision") == state.get("revision")
            and binding.get("physicalWorktreeFingerprint") == expected_fingerprint
            and binding.get("scope") == "ReservationControl"
        )
        current = state.get("currentWork")
        if current is not None:
            state_bindings_ok = state_bindings_ok and (
                current.get("workflowId") == workflow_id
                and current.get("physicalWorktreeFingerprint") == expected_fingerprint
                and _same_path(current.get("worktreePath", ""), expected_path)
            )
        try:
            engine.reservations._validate_handoff_issue_authority(state, reservation)
        except Exception:
            state_bindings_ok = False
        lease = state.get("lease")
        if lease is not None:
            try:
                sidecar = engine.store.guard.read_json(
                    engine.store.guard.leaf(lease["capabilityRef"], must_exist=True)
                )
            except Exception:
                sidecar = {}
            state_bindings_ok = state_bindings_ok and (
                lease.get("revision") == state.get("revision")
                and sidecar.get("physicalWorktreeFingerprint")
                == engine.manager.identity.physical_worktree_fingerprint
            )
        state_bindings_ok = state_bindings_ok and all(
            capability.get("status") != "issued"
            or (
                capability.get("stateRevision") == state.get("revision")
                and capability.get("physicalWorktreeFingerprint") == expected_fingerprint
                and _same_path(capability.get("worktreePath", ""), expected_path)
            )
            for capability in state.get("capabilities", {}).values()
        )
        success = (
            expected_fingerprint == authorization.get("destinationFingerprint")
            and authorization.get("status") == "consumed"
            and _success_evidence_is_exact(
                engine,
                workflow_id=workflow_id,
                source_path=Path(request["sourcePath"]),
                destination_path=Path(request["destinationPath"]),
                expected_paths=list(request["expectedPaths"]),
                source_fingerprint=authorization["sourceFingerprint"],
                destination_fingerprint=authorization["destinationFingerprint"],
            )
        )
        failure = (
            expected_fingerprint == authorization.get("sourceFingerprint")
            and authorization.get("status") == "revoked"
            and (
                _failure_evidence_is_exact(engine, context=context)
                or _no_base_mutation_is_exact(engine, context=context)
            )
        )
        if state_bindings_ok and success:
            return {
                "schemaVersion": "1.0",
                "status": "transferred",
                "operationId": operation_id,
                "workflowId": workflow_id,
                "baseHandoff": "recovered-after-phase-c",
                "reservation": {
                    "status": "transferred",
                    "operationId": operation_id,
                    "reservationId": reservation["reservationId"],
                    "controlAuthorizationRef": final_ref,
                    "reservationRevision": reservation["revision"],
                },
            }
        if state_bindings_ok and failure:
            return {
                "status": "restored",
                "operationId": operation_id,
                "reservationId": reservation["reservationId"],
                "controlAuthorizationRef": final_ref,
                "reservationRevision": reservation["revision"],
            }
        _protect(engine, operation_id)
        return {
            "status": "protected",
            "operationId": operation_id,
            "reason": "Finalized Handoff evidence is incomplete or mismatched",
        }
    if (
        observed == authorization.get("sourceFingerprint")
        and _failure_evidence_is_exact(engine, context=context)
    ):
        return engine.reservations.recover_handoff(
            operation_id=operation_id,
            proven_outcome="proven-failure",
        )
    if (
        observed == authorization.get("sourceFingerprint")
        and authorization.get("status") in {"prepared", "consumed"}
        and _no_base_mutation_is_exact(engine, context=context)
    ):
        return engine.reservations.recover_handoff(
            operation_id=operation_id,
            proven_outcome="proven-failure",
        )
    if (
        observed == authorization.get("destinationFingerprint")
        and _success_evidence_is_exact(
            engine,
            workflow_id=workflow_id,
            source_path=Path(request["sourcePath"]),
            destination_path=Path(request["destinationPath"]),
            expected_paths=list(request["expectedPaths"]),
            source_fingerprint=authorization["sourceFingerprint"],
            destination_fingerprint=authorization["destinationFingerprint"],
        )
    ):
        return engine.reservations.recover_handoff(
            operation_id=operation_id,
            proven_outcome="succeeded",
            destination_fingerprint=authorization["destinationFingerprint"],
            destination_worktree_path=request["destinationPath"],
        )
    _protect(engine, operation_id)
    return {
        "status": "protected",
        "operationId": operation_id,
        "reason": "Canonical Handoff evidence is incomplete or destination reconciliation failed",
    }
