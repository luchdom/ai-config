"""Registry-only workflow-managed Handoff with no Git state mutation."""

from __future__ import annotations

import copy
import hashlib
import os
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .atomic_files import atomic_write_bytes, atomic_write_json
from .descriptor import read_descriptor, validate_descriptor
from .errors import HandoffError, ResumeError, UnsafePathError, ValidationError
from .identity import observe_repository_identity
from .path_safety import (
    ensure_safe_descendant,
    ensure_safe_relative_path,
    is_reparse_point,
    validate_expected_path_scope,
)
from .redaction import SENSITIVE_KEY, redact_patch, redact_text, redact_value

if TYPE_CHECKING:
    from .reservation_interlock import InternalHandoffAuthorization
    from .workflow_init import WorkflowManager


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
            check=False,
            capture_output=True,
            shell=False,
        )
    except OSError as exc:
        raise HandoffError("Git handoff executable is unavailable") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip() or "unknown Git error"
        raise HandoffError(f"Read-only Git handoff probe failed: {detail}")
    return completed.stdout


def _git_text(repository: Path, *arguments: str) -> str:
    try:
        return _git_bytes(repository, *arguments).decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise HandoffError("Git handoff output is not valid UTF-8") from exc


def _index_digest(repository: Path) -> str:
    raw = _git_text(repository, "rev-parse", "--git-path", "index")
    path = Path(raw)
    if not path.is_absolute():
        path = repository / path
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_immutability_snapshot(repository: Path) -> dict[str, str]:
    return {
        "head": _git_text(repository, "rev-parse", "HEAD"),
        "branch": _git_text(repository, "rev-parse", "--abbrev-ref", "HEAD"),
        "indexSha256": _index_digest(repository),
    }


def _changed_paths(repository: Path) -> list[Path]:
    raw = _git_bytes(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    fields = raw.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 4 or field[2:3] != b" ":
            raise HandoffError("Cannot parse source Git status safely")
        status = field[:2].decode("ascii", "strict")
        current = field[3:].decode("utf-8", "surrogateescape")
        paths.add(os.fspath(ensure_safe_relative_path(current)))
        if "R" in status or "C" in status:
            if index >= len(fields) or not fields[index]:
                raise HandoffError("Rename/copy status is incomplete")
            original = fields[index].decode("utf-8", "surrogateescape")
            index += 1
            paths.add(os.fspath(ensure_safe_relative_path(original)))
    return [Path(value) for value in sorted(paths, key=str.casefold)]


def _head_entry(repository: Path, relative: Path) -> tuple[str, str, str] | None:
    raw = _git_bytes(repository, "ls-tree", "-z", "HEAD", "--", relative.as_posix())
    records = [record for record in raw.split(b"\0") if record]
    if not records:
        return None
    if len(records) != 1 or b"\t" not in records[0]:
        raise HandoffError("Cannot resolve an unambiguous HEAD baseline for a transfer path")
    metadata, observed_path = records[0].split(b"\t", 1)
    fields = metadata.decode("ascii", "strict").split()
    if len(fields) != 3:
        raise HandoffError("Cannot parse HEAD baseline metadata for a transfer path")
    if observed_path.decode("utf-8", "surrogateescape") != relative.as_posix():
        raise HandoffError("HEAD baseline path identity differs from the transfer path")
    mode, object_type, object_id = fields
    return mode, object_type, object_id


def _worktree_blob_id(repository: Path, relative: Path, path: Path) -> str:
    return _git_text(
        repository,
        "hash-object",
        f"--path={relative.as_posix()}",
        os.fspath(path),
    )


def _validate_destination_baseline_compatibility(
    source_root: Path,
    destination_root: Path,
    transfer_paths: list[Path],
) -> None:
    """Reject overlapping destination commits before any destination worktree write."""

    for relative in transfer_paths:
        source_entry = _head_entry(source_root, relative)
        destination_entry = _head_entry(destination_root, relative)
        if source_entry != destination_entry:
            raise HandoffError(
                "Destination HEAD changed a transfer path relative to the source baseline; "
                "source remains authoritative"
            )
        destination_path = ensure_safe_descendant(destination_root, destination_root / relative)
        if source_entry is None:
            if destination_path.exists():
                raise HandoffError(
                    "Destination contains an untracked or ignored transfer-path overlap; "
                    "source remains authoritative"
                )
            continue
        _, object_type, object_id = source_entry
        if object_type != "blob" or not destination_path.is_file() or is_reparse_point(destination_path):
            raise HandoffError(
                "Destination transfer-path baseline is not a compatible regular file; "
                "source remains authoritative"
            )
        if _worktree_blob_id(destination_root, relative, destination_path) != object_id:
            raise HandoffError(
                "Destination transfer-path bytes differ from its matching HEAD blob; "
                "source remains authoritative"
            )


def _safe_evidence_path(path: Path) -> str:
    value = path.as_posix()
    if SENSITIVE_KEY.search(value):
        digest = hashlib.sha256(value.encode("utf-8", "surrogateescape")).hexdigest()[:12]
        return f"[REDACTED-PATH:{digest}]"
    return value


def _redact_diagnostic(value: str, relative_paths: list[Path]) -> str:
    result = redact_text(value)
    for relative in sorted(relative_paths, key=lambda item: len(item.as_posix()), reverse=True):
        replacement = _safe_evidence_path(relative)
        if replacement == relative.as_posix():
            continue
        result = result.replace(relative.as_posix(), replacement)
        result = result.replace(os.fspath(relative), replacement)
        result = result.replace(relative.as_posix().replace("/", "\\"), replacement)
    return result


def _manifest(snapshot: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw_relative, entry in snapshot.items():
        relative = Path(raw_relative)
        evidence_path = _safe_evidence_path(relative)
        if entry["operation"] == "write" and SENSITIVE_KEY.search(relative.as_posix()):
            result.append(
                {
                    "path": evidence_path,
                    "operation": "write",
                    "contentEvidence": "redacted-sensitive-path",
                }
            )
        elif entry["operation"] == "write":
            result.append(
                {
                    "path": evidence_path,
                    "operation": "write",
                    "size": entry["size"],
                    "sha256": entry["sha256"],
                }
            )
        else:
            result.append({"path": evidence_path, "operation": "delete"})
    return result


def _content_snapshot(source_root: Path, relative_paths: list[Path]) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for relative in relative_paths:
        source_path = ensure_safe_descendant(source_root, source_root / relative)
        key = relative.as_posix()
        if source_path.exists():
            if source_path.is_dir() or is_reparse_point(source_path):
                raise UnsafePathError(
                    f"Handoff refuses directory/reparse content: {_safe_evidence_path(relative)}"
                )
            content = source_path.read_bytes()
            snapshot[key] = {
                "operation": "write",
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "content": content,
            }
        else:
            snapshot[key] = {"operation": "delete"}
    return snapshot


def _validate_transfer_content(
    source_root: Path,
    destination_root: Path,
    snapshot: dict[str, dict[str, Any]],
    expected_git_paths: set[str],
) -> None:
    source_changed = {path.as_posix() for path in _changed_paths(source_root)}
    destination_changed = {path.as_posix() for path in _changed_paths(destination_root)}
    if source_changed != expected_git_paths:
        raise HandoffError(
            "Source change set changed during workflow-managed Handoff "
            f"(expected={len(expected_git_paths)}:{_path_set_digest(expected_git_paths)}, "
            f"observed={len(source_changed)}:{_path_set_digest(source_changed)})"
        )
    clean_transfer_only = set(snapshot) - expected_git_paths
    effective_destination_changes = destination_changed - clean_transfer_only
    if effective_destination_changes != expected_git_paths:
        raise HandoffError(
            "Destination change set changed during workflow-managed Handoff "
            f"(expected={len(expected_git_paths)}:{_path_set_digest(expected_git_paths)}, "
            f"observed={len(effective_destination_changes)}:{_path_set_digest(effective_destination_changes)})"
        )
    for raw_relative, expected in snapshot.items():
        relative = Path(raw_relative)
        source_path = ensure_safe_descendant(source_root, source_root / relative)
        destination_path = ensure_safe_descendant(destination_root, destination_root / relative)
        if expected["operation"] == "delete":
            if source_path.exists() or destination_path.exists():
                raise HandoffError(
                    "Handoff deletion changed before authority commit: "
                    f"{_safe_evidence_path(relative)}"
                )
            continue
        if not source_path.is_file() or not destination_path.is_file():
            raise HandoffError(
                "Handoff write disappeared before authority commit: "
                f"{_safe_evidence_path(relative)}"
            )
        source_content = source_path.read_bytes()
        destination_content = destination_path.read_bytes()
        if (
            len(source_content) != expected["size"]
            or len(destination_content) != expected["size"]
            or hashlib.sha256(source_content).hexdigest() != expected["sha256"]
            or hashlib.sha256(destination_content).hexdigest() != expected["sha256"]
        ):
            raise HandoffError(
                "Handoff content changed before authority commit: "
                f"{_safe_evidence_path(relative)}"
            )


def _path_set_digest(paths: set[str]) -> str:
    return hashlib.sha256("\0".join(sorted(paths, key=str.casefold)).encode("utf-8")).hexdigest()[:12]


def _apply_paths(
    destination_root: Path,
    snapshot: dict[str, dict[str, Any]],
    backups: dict[Path, tuple[bool, bytes | None, int | None]],
    created_directories: list[Path],
) -> None:
    for raw_relative, captured in snapshot.items():
        relative = Path(raw_relative)
        destination_path = ensure_safe_descendant(destination_root, destination_root / relative)
        if destination_path.exists() and is_reparse_point(destination_path):
            raise UnsafePathError(
                f"Destination reparse target rejected: {_safe_evidence_path(relative)}"
            )
        if destination_path.exists():
            if destination_path.is_dir():
                raise UnsafePathError(
                    f"Destination file path is a directory: {_safe_evidence_path(relative)}"
                )
            backups[destination_path] = (
                True,
                destination_path.read_bytes(),
                destination_path.stat().st_mode,
            )
        else:
            backups[destination_path] = (False, None, None)

        if captured["operation"] == "write":
            parent = destination_path.parent
            missing: list[Path] = []
            current = parent
            while current != destination_root and not current.exists():
                missing.append(current)
                current = current.parent
            if current != destination_root and is_reparse_point(current):
                raise UnsafePathError(
                    "Destination parent reparse component rejected: "
                    f"{_safe_evidence_path(relative)}"
                )
            parent.mkdir(parents=True, exist_ok=True)
            created_directories.extend(reversed(missing))
            ensure_safe_descendant(destination_root, destination_path)
            atomic_write_bytes(destination_path, captured["content"])
        else:
            destination_path.unlink(missing_ok=True)


def _rollback_paths(
    backups: dict[Path, tuple[bool, bytes | None, int | None]],
    created_directories: list[Path],
) -> None:
    for path, (existed, content, mode) in reversed(list(backups.items())):
        if existed:
            assert content is not None
            atomic_write_bytes(path, content)
            if mode is not None:
                os.chmod(path, mode)
        else:
            path.unlink(missing_ok=True)
    for directory in reversed(created_directories):
        try:
            directory.rmdir()
        except OSError:
            pass


def _is_at_or_below(path: Path, parent: Path) -> bool:
    path_parts = tuple(part.casefold() for part in path.parts)
    parent_parts = tuple(part.casefold() for part in parent.parts)
    return len(path_parts) >= len(parent_parts) and path_parts[: len(parent_parts)] == parent_parts


def _validate_workflow_scope_isolation(
    *,
    source_root: Path,
    registry: dict[str, Any],
    workflow_id: str,
    paths: set[str],
) -> None:
    candidates = [Path(value) for value in paths]
    for other_id, other in registry["workflows"].items():
        if other_id == workflow_id:
            continue
        artifact = Path(other["artifactPath"])
        try:
            relative_folder = artifact.relative_to(source_root)
        except ValueError:
            continue
        if any(_is_at_or_below(candidate, relative_folder) for candidate in candidates):
            raise HandoffError(
                "Handoff scope intersects another registered workflow artifact folder; "
                "source remains authoritative"
            )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def workflow_managed_handoff(
    *,
    source: "WorkflowManager",
    workflow_id: str,
    destination_root: str | Path,
    expected_paths: list[str],
    reservation_authorization: "InternalHandoffAuthorization | None" = None,
    editing_source_root: str | Path | None = None,
) -> dict[str, Any]:
    """Transfer working files and registry binding; never transfer a live reservation."""

    expected_scope = validate_expected_path_scope(expected_paths)
    expected_scope_set = {path.as_posix() for path in expected_scope}
    if editing_source_root is not None:
        from .reservation_interlock import InternalHandoffAuthorization

        if type(reservation_authorization) is not InternalHandoffAuthorization:
            raise HandoffError(
                "An editing-source override requires exact internal Handoff authorization"
            )
        source_identity = observe_repository_identity(editing_source_root)
        if source_identity.repository_id != source.identity.repository_id:
            raise HandoffError(
                "Editing source belongs to another normalized Git common directory"
            )
    else:
        source_identity = source.identity
    effective_source_root = Path(source_identity.repository_root)
    destination_identity = observe_repository_identity(destination_root)
    destination = Path(destination_identity.repository_root)
    if destination_identity.repository_id != source.identity.repository_id:
        raise HandoffError("workflow-managed Handoff requires the same normalized Git common directory")
    if destination_identity.physical_worktree_fingerprint == source_identity.physical_worktree_fingerprint:
        raise HandoffError("Source and destination physical worktrees must be distinct")
    if _git_bytes(destination, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise HandoffError("Destination worktree is dirty; no workflow authority was transferred")

    source_before = _git_immutability_snapshot(effective_source_root)
    destination_before = _git_immutability_snapshot(destination)

    with source.registry.mutex():
        registry_before = source._load_registry_unlocked()
        entry = source.registry._resolve_unlocked_structural(registry_before, workflow_id=workflow_id)
        if (
            entry["repositoryKey"] != source.repository_key
            or entry["repositoryId"] != source.identity.repository_id
            or entry["physicalWorktreeFingerprint"]
            != source_identity.physical_worktree_fingerprint
        ):
            raise HandoffError(
                "Workflow registry authority differs from the effective editing source"
            )
        descriptor_source_path = Path(entry["artifactPath"]) / "workflow.json"
        descriptor_before = read_descriptor(descriptor_source_path)
        source._assert_descriptor_registry_projection(entry, descriptor_before)
        if descriptor_before["repositoryKey"] != source.repository_key:
            raise HandoffError("Workflow repositoryKey differs from source manager authority")

        # This check must remain inside the base mutex.  It is the only safe
        # serialization point for a first Reserve racing registry-only Handoff.
        from .reservation_interlock import validate_and_consume_handoff_authorization_unlocked

        validate_and_consume_handoff_authorization_unlocked(
            source=source,
            workflow_id=workflow_id,
            editing_source_path=effective_source_root,
            editing_source_fingerprint=source_identity.physical_worktree_fingerprint,
            destination_fingerprint=destination_identity.physical_worktree_fingerprint,
            expected_paths=[path.as_posix() for path in expected_scope],
            authorization=reservation_authorization,
        )

        # No state or destination write occurs before exact source authority is proven above.
        handoff_id = str(uuid.uuid4())
        evidence_root = source.state_paths.directory(
            source.home.repository / "handoffs",
            create=True,
        )
        workflow_evidence = source.state_paths.directory(evidence_root / workflow_id, create=True)
        evidence_dir = source.state_paths.directory(workflow_evidence / handoff_id, create=True)
        backups: dict[Path, tuple[bool, bytes | None, int | None]] = {}
        created_directories: list[Path] = []
        transfer_paths: list[Path] = []
        try:
            if _git_bytes(destination, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
                raise HandoffError("Destination became dirty before transfer; source remains authoritative")
            changed_paths = _changed_paths(effective_source_root)
            try:
                artifact_relative = Path(entry["artifactPath"]).relative_to(
                    effective_source_root
                )
            except ValueError as exc:
                raise HandoffError(
                    "Registered workflow artifact is outside the effective editing source"
                ) from exc
            descriptor_relative = artifact_relative / "workflow.json"
            observed_git_paths = {path.as_posix() for path in changed_paths}
            _validate_workflow_scope_isolation(
                source_root=effective_source_root,
                registry=registry_before,
                workflow_id=workflow_id,
                paths=observed_git_paths | expected_scope_set,
            )
            observed_user_paths = observed_git_paths - {descriptor_relative.as_posix()}
            if observed_user_paths != expected_scope_set:
                raise HandoffError(
                    "Observed Git change set differs from explicit Handoff scope "
                    f"(expected={len(expected_scope_set)}:{_path_set_digest(expected_scope_set)}, "
                    f"observed={len(observed_user_paths)}:{_path_set_digest(observed_user_paths)}); "
                    "source remains authoritative"
                )
            expected_git_paths = observed_git_paths
            transfer_paths = list(changed_paths)
            if descriptor_relative not in transfer_paths:
                transfer_paths.append(descriptor_relative)
                transfer_paths.sort(key=lambda item: item.as_posix().casefold())
            _validate_destination_baseline_compatibility(
                effective_source_root,
                destination,
                transfer_paths,
            )
            content_snapshot = _content_snapshot(effective_source_root, transfer_paths)
            manifest = _manifest(content_snapshot)
            raw_patch = _git_bytes(
                effective_source_root,
                "diff",
                "--binary",
                "--no-ext-diff",
                "HEAD",
                "--",
            ).decode("utf-8", "replace")
            source.state_paths.write_json(
                evidence_dir / "manifest.json",
                {
                    "schemaVersion": "1.0",
                    "workflowId": workflow_id,
                    "handoffId": handoff_id,
                    "changes": manifest,
                    "reservationTransferred": False,
                    "gitMutationPermitted": False,
                },
            )
            source.state_paths.write_bytes(
                evidence_dir / "patch.diff",
                redact_patch(raw_patch).encode("utf-8"),
            )

            # Re-run immediately before apply and compare current destination bytes to HEAD.
            _validate_destination_baseline_compatibility(
                effective_source_root,
                destination,
                transfer_paths,
            )
            _apply_paths(
                destination,
                content_snapshot,
                backups,
                created_directories,
            )
            destination_descriptor_path = destination / descriptor_relative
            descriptor_destination_before = read_descriptor(destination_descriptor_path)
            if descriptor_destination_before != descriptor_before:
                raise HandoffError("Destination descriptor did not reproduce the registered source")
            descriptor_after = copy.deepcopy(descriptor_before)
            descriptor_after["revision"] += 1
            descriptor_after["repositoryRoot"] = os.fspath(destination)
            descriptor_after["artifactFolder"] = os.fspath(destination / artifact_relative)
            descriptor_after["physicalWorktreeFingerprint"] = (
                destination_identity.physical_worktree_fingerprint
            )
            validate_descriptor(descriptor_after)

            _validate_transfer_content(
                effective_source_root,
                destination,
                content_snapshot,
                expected_git_paths,
            )
            if _git_immutability_snapshot(effective_source_root) != source_before:
                raise HandoffError("Source Git HEAD, branch, or index changed during Handoff")
            if _git_immutability_snapshot(destination) != destination_before:
                raise HandoffError("Destination Git HEAD, branch, or index changed during Handoff")
            result = {
                "schemaVersion": "1.0",
                "status": "completed",
                "workflowId": workflow_id,
                "handoffId": handoff_id,
                "sourceFingerprint": source_identity.physical_worktree_fingerprint,
                "destinationFingerprint": destination_identity.physical_worktree_fingerprint,
                "artifactPath": descriptor_after["artifactFolder"],
                "reservationTransferred": False,
                "gitMutationPerformed": False,
                "authority": "authoritative-only-when-registry-hash-referenced",
            }
            source.state_paths.write_json(evidence_dir / "result.json", redact_value(result))
            # This is the final check immediately before the authority pair is committed.
            _validate_transfer_content(
                effective_source_root,
                destination,
                content_snapshot,
                expected_git_paths,
            )
            if _git_immutability_snapshot(effective_source_root) != source_before:
                raise HandoffError("Source Git HEAD, branch, or index changed before authority commit")
            if _git_immutability_snapshot(destination) != destination_before:
                raise HandoffError("Destination Git HEAD, branch, or index changed before authority commit")

            manifest_sha256 = _sha256(source.state_paths.read_bytes(evidence_dir / "manifest.json"))
            patch_sha256 = _sha256(source.state_paths.read_bytes(evidence_dir / "patch.diff"))
            result_sha256 = _sha256(source.state_paths.read_bytes(evidence_dir / "result.json"))
            registry_after = copy.deepcopy(registry_before)
            registry_after["revision"] += 1
            updated_entry = registry_after["workflows"][workflow_id]
            updated_entry["artifactPath"] = descriptor_after["artifactFolder"]
            updated_entry["physicalWorktreeFingerprint"] = descriptor_after[
                "physicalWorktreeFingerprint"
            ]
            updated_entry["descriptorRevision"] = descriptor_after["revision"]
            updated_entry["handoffs"].append(
                {
                    "handoffId": handoff_id,
                    "sourceFingerprint": source_identity.physical_worktree_fingerprint,
                    "destinationFingerprint": destination_identity.physical_worktree_fingerprint,
                    "destinationArtifactPath": descriptor_after["artifactFolder"],
                    "evidencePath": os.fspath(evidence_dir),
                    "manifestSha256": manifest_sha256,
                    "patchSha256": patch_sha256,
                    "resultSha256": result_sha256,
                    "reservationTransferred": False,
                }
            )
            source._paired_commit(
                operation="handoff",
                workflow_id=workflow_id,
                descriptor_path=destination_descriptor_path,
                descriptor_before=descriptor_destination_before,
                descriptor_after=descriptor_after,
                registry_before=registry_before,
                registry_after=registry_after,
            )
            return result
        except Exception as exc:
            original_reason = _redact_diagnostic(str(exc), transfer_paths)
            rollback_error: str | None = None
            rollback_status = "not-required"
            if backups:
                try:
                    _rollback_paths(backups, created_directories)
                    rollback_status = "rollback-complete"
                except Exception as rollback_exc:
                    rollback_status = "rollback-required"
                    rollback_error = _redact_diagnostic(str(rollback_exc), transfer_paths)
            failure = {
                "schemaVersion": "1.0",
                "status": "failed",
                "workflowId": workflow_id,
                "handoffId": handoff_id,
                "originalError": original_reason,
                "rollbackStatus": rollback_status,
                "rollbackError": rollback_error,
                "destinationReconciliationRequired": rollback_error is not None,
                "sourceRemainsAuthoritative": True,
                "reservationTransferred": False,
                "gitMutationPerformed": False,
            }
            evidence_error: str | None = None
            try:
                source.state_paths.write_json(evidence_dir / "result.json", redact_value(failure))
            except Exception as evidence_exc:
                evidence_error = _redact_diagnostic(str(evidence_exc), transfer_paths)
            if rollback_error is not None or evidence_error is not None:
                raise HandoffError(
                    "workflow-managed Handoff requires attended reconciliation; "
                    f"original={original_reason}; rollback={rollback_error or rollback_status}; "
                    f"evidence={evidence_error or 'recorded'}"
                ) from exc
            if isinstance(exc, (HandoffError, ResumeError, UnsafePathError, ValidationError)):
                raise type(exc)(original_reason) from exc
            raise HandoffError(f"workflow-managed Handoff failed closed: {original_reason}") from exc
