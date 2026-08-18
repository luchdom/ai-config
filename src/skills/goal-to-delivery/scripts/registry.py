"""Atomic, repository-scoped workflow registry and exact selector resolution."""

from __future__ import annotations

import copy
import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Any, Callable

from .descriptor import read_descriptor, validate_descriptor
from .errors import (
    CollisionError,
    RepositoryIdentityError,
    ResumeError,
    UnsafePathError,
    ValidationError,
)
from .identity import observe_repository_identity
from .mutex import AllocationMutex
from .path_safety import (
    ensure_safe_relative_path,
    registered_artifact_root,
    repository_root_from_registered_artifact,
    validate_current_artifact_folder_name,
)
from .state_paths import StatePathGuard

REGISTRY_VERSION = "1.0"
FINGERPRINT_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


def empty_registry(repository_id: str) -> dict[str, Any]:
    return {
        "schemaVersion": REGISTRY_VERSION,
        "revision": 1,
        "repositoryId": repository_id,
        "workflows": {},
    }


def _normalized_path(value: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(value))))


def _lexical_path(value: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(value))))


def _artifact_selector(value: str | Path) -> str:
    raw = os.fspath(value)
    if not os.path.isabs(raw):
        raise ResumeError("Artifact-path selector must be absolute")
    _, tail = os.path.splitdrive(raw)
    normalized_tail = tail.replace("\\", "/")
    body = normalized_tail[1:] if normalized_tail.startswith("/") else normalized_tail
    if "//" in body:
        raise ResumeError("Artifact-path selector cannot contain duplicate separators")
    parts = body.split("/") if body else []
    if any(part in {".", ".."} for part in parts):
        raise ResumeError("Artifact-path selector cannot contain dot segments or traversal")
    if raw.endswith(("/", "\\")):
        raise ResumeError("Artifact-path selector must name the exact artifact folder")
    return _lexical_path(raw)


def validate_descriptor_projection(entry: dict[str, Any], descriptor: dict[str, Any]) -> None:
    """Validate the complete registry projection before lookup success or mutation."""

    validate_descriptor(descriptor)
    descriptor_root = Path(descriptor["repositoryRoot"])
    try:
        canonical_descriptor_root = _artifact_selector(descriptor["repositoryRoot"])
        canonical_descriptor_artifact = _artifact_selector(descriptor["artifactFolder"])
        canonical_entry_artifact = _artifact_selector(entry["artifactPath"])
    except ResumeError as exc:
        raise ValidationError("Descriptor/registry paths are not exact canonical selectors") from exc
    observed = observe_repository_identity(descriptor_root)
    if _lexical_path(observed.repository_root) != canonical_descriptor_root:
        raise ValidationError("Descriptor repositoryRoot is not the exact observed worktree root")
    expected = {
        "workflowId": descriptor["workflowId"],
        "workKey": descriptor["workKey"],
        "artifactPath": canonical_descriptor_artifact,
        "repositoryId": observed.repository_id,
        "repositoryKey": descriptor["repositoryKey"],
        "physicalWorktreeFingerprint": descriptor["physicalWorktreeFingerprint"],
        "externalProvider": descriptor["tracking"]["provider"],
        "externalId": descriptor["tracking"]["externalId"],
        "descriptorRevision": descriptor["revision"],
    }
    actual = {
        "workflowId": entry["workflowId"],
        "workKey": entry["workKey"],
        "artifactPath": canonical_entry_artifact,
        "repositoryId": entry["repositoryId"],
        "repositoryKey": entry["repositoryKey"],
        "physicalWorktreeFingerprint": entry["physicalWorktreeFingerprint"],
        "externalProvider": entry["externalProvider"],
        "externalId": entry["externalId"],
        "descriptorRevision": entry["descriptorRevision"],
    }
    if actual != expected or observed.physical_worktree_fingerprint != descriptor[
        "physicalWorktreeFingerprint"
    ]:
        raise ValidationError("Registry and descriptor authoritative projections differ")
    try:
        artifact_kind, _ = registered_artifact_root(
            descriptor_root,
            Path(descriptor["artifactFolder"]),
            candidate_may_not_exist=False,
        )
    except UnsafePathError as exc:
        raise ValidationError("Descriptor artifact folder is outside the managed roots") from exc
    if artifact_kind == "current":
        validate_current_artifact_folder_name(
            Path(descriptor["artifactFolder"]).name,
            work_source=descriptor["workSource"],
            work_key=descriptor["workKey"],
            slug=descriptor["slug"],
        )


class WorkflowRegistry:
    def __init__(
        self,
        state_home: Path,
        repository_id: str,
        *,
        repository_key: str,
        normalized_common_dir: str,
        state_paths: StatePathGuard | None = None,
    ):
        self.state_home = Path(state_home)
        self.repository_id = repository_id
        self.repository_key = repository_key
        self.normalized_common_dir = normalized_common_dir
        self.state_paths = state_paths or StatePathGuard(self.state_home)
        self.path = self.state_home / "registry.json"
        self.mutex_path = self.state_home / "allocation.lock"

    def mutex(self, *, timeout_seconds: float = 30.0) -> AllocationMutex:
        return AllocationMutex(
            self.mutex_path,
            timeout_seconds=timeout_seconds,
            state_paths=self.state_paths,
        )

    def ensure(self) -> None:
        self._validate_state_authority()
        with self.mutex():
            if not self.path.exists():
                self.state_paths.write_json(self.path, empty_registry(self.repository_id))
            self.load_unlocked()

    def load_unlocked(self) -> dict[str, Any]:
        self._validate_state_authority()
        if not self.path.exists():
            return empty_registry(self.repository_id)
        value = self.state_paths.read_json(self.path)
        self.validate_value(value)
        return value

    def validate_value(self, value: dict[str, Any]) -> None:
        if set(value) != {"schemaVersion", "revision", "repositoryId", "workflows"}:
            raise ValidationError("Registry contains unknown or missing top-level fields")
        if value["schemaVersion"] != REGISTRY_VERSION or value["repositoryId"] != self.repository_id:
            raise ValidationError("Registry version or repository identity mismatch")
        if not isinstance(value["revision"], int) or value["revision"] < 1:
            raise ValidationError("Registry revision must be a positive integer")
        if not isinstance(value["workflows"], dict):
            raise ValidationError("Registry workflows must be an object")
        identity_cache: dict[str, Any] = {}
        for workflow_id, entry in value["workflows"].items():
            self._validate_entry(workflow_id, entry, identity_cache)
        self._validate_unique_mappings(value)

    def write_unlocked(self, value: dict[str, Any], *, expected_revision: int) -> None:
        self._validate_state_authority()
        self.validate_value(value)
        self.state_paths.write_json(self.path, value, expected_revision=expected_revision)
        if self.load_unlocked() != value:
            raise ValidationError("Registry atomic readback mismatch")

    def update(self, mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        self._validate_state_authority()
        with self.mutex():
            current = self.load_unlocked()
            updated = copy.deepcopy(current)
            mutator(updated)
            updated["revision"] = current["revision"] + 1
            self.write_unlocked(updated, expected_revision=current["revision"])
            return updated

    def resolve(
        self,
        *,
        workflow_id: str | None = None,
        artifact_path: str | Path | None = None,
        external_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_state_authority()
        supplied = sum(value is not None for value in (workflow_id, artifact_path, external_id))
        if supplied != 1:
            raise ResumeError("Resume requires exactly one workflow ID, artifact path, or external ID")
        with self.mutex():
            registry = self.load_unlocked()
            entry = self._resolve_unlocked_structural(
                registry,
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                external_id=external_id,
            )
            descriptor = read_descriptor(Path(entry["artifactPath"]) / "workflow.json")
            validate_descriptor_projection(entry, descriptor)
            return copy.deepcopy(entry)

    def _validate_state_authority(self) -> None:
        sentinel = self.state_paths.read_json(self.state_home / "repository.json")
        if sentinel != {
            "schemaVersion": "2.0",
            "repositoryId": self.repository_id,
            "normalizedCommonDir": self.normalized_common_dir,
            "repositoryKey": self.repository_key,
        }:
            raise ValidationError("Registry repositoryId/repositoryKey state authority mismatch")

    def _resolve_unlocked_structural(
        self,
        registry: dict[str, Any],
        *,
        workflow_id: str | None = None,
        artifact_path: str | Path | None = None,
        external_id: str | None = None,
    ) -> dict[str, Any]:
        if workflow_id is not None:
            entry = registry["workflows"].get(workflow_id)
            if entry is None:
                raise ResumeError(f"No registered workflow ID {workflow_id}")
            return entry
        if artifact_path is not None:
            expected = _artifact_selector(artifact_path)
            matches = [
                entry
                for entry in registry["workflows"].values()
                if _lexical_path(entry["artifactPath"]) == expected
            ]
        else:
            matches = [
                entry for entry in registry["workflows"].values() if entry.get("externalId") == external_id
            ]
        if not matches:
            raise ResumeError("No workflow matches the exact selector")
        if len(matches) != 1:
            raise ResumeError("Exact selector is ambiguous; attended registry reconciliation is required")
        return matches[0]

    def _validate_entry(
        self,
        workflow_id: str,
        entry: Any,
        identity_cache: dict[str, Any],
    ) -> None:
        required = {
            "workflowId", "workKey", "artifactPath", "repositoryId", "physicalWorktreeFingerprint",
            "repositoryKey", "externalProvider", "externalId", "descriptorRevision", "handoffs",
        }
        if not isinstance(entry, dict) or set(entry) != required:
            raise ValidationError(f"Registry entry {workflow_id} has invalid fields")
        if entry["workflowId"] != workflow_id:
            raise ValidationError("Registry workflow key/identity mismatch")
        try:
            if str(uuid.UUID(workflow_id)) != workflow_id:
                raise ValueError
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValidationError("Registry workflow ID must be a canonical UUID") from exc
        if not isinstance(entry["workKey"], str) or not entry["workKey"]:
            raise ValidationError("Registry work key must be non-empty")
        if not isinstance(entry["repositoryKey"], str) or not entry["repositoryKey"]:
            raise ValidationError("Registry repository key must be non-empty")
        if entry["repositoryKey"] != self.repository_key:
            raise ValidationError("Registry workflow repositoryKey differs from the state-home authority")
        if entry["externalProvider"] not in {"none", "linear"}:
            raise ValidationError("Registry external provider is invalid")
        if entry["externalProvider"] == "none" and entry["externalId"] is not None:
            raise ValidationError("Untracked registry entry cannot carry an external ID")
        if entry["externalProvider"] == "linear" and not isinstance(entry["externalId"], str):
            raise ValidationError("Linear registry entry requires an external ID")
        if not isinstance(entry["descriptorRevision"], int) or entry["descriptorRevision"] < 1:
            raise ValidationError("Registry descriptor revision must be positive")
        if not os.path.isabs(entry["artifactPath"]):
            raise ValidationError("Registry artifact path must be absolute")
        try:
            _artifact_selector(entry["artifactPath"])
        except ResumeError as exc:
            raise ValidationError("Registry artifact path must be an exact canonical selector") from exc
        if not isinstance(entry["handoffs"], list):
            raise ValidationError("Registry handoffs must be an array")
        artifact_folder = Path(entry["artifactPath"])
        try:
            repository_root = repository_root_from_registered_artifact(artifact_folder)
            registered_artifact_root(
                repository_root,
                artifact_folder,
                candidate_may_not_exist=False,
            )
        except UnsafePathError as exc:
            raise ValidationError("Registry artifact path is outside the managed roots") from exc
        root_key = _normalized_path(repository_root)
        observed = identity_cache.get(root_key)
        if observed is None:
            try:
                observed = observe_repository_identity(repository_root)
            except RepositoryIdentityError as exc:
                raise ValidationError("Registry artifact path is not an observed Git worktree") from exc
            identity_cache[root_key] = observed
        if _normalized_path(observed.repository_root) != _normalized_path(repository_root):
            raise ValidationError("Registry artifact path is not rooted at the observed worktree root")
        if observed.repository_id != self.repository_id or entry["repositoryId"] != self.repository_id:
            raise ValidationError("Registry entry belongs to another Git common directory")
        if entry["physicalWorktreeFingerprint"] != observed.physical_worktree_fingerprint:
            raise ValidationError("Registry artifact path and physical-worktree fingerprint disagree")
        self._validate_handoffs(workflow_id, entry)

    def _validate_handoffs(self, workflow_id: str, entry: dict[str, Any]) -> None:
        previous_destination: str | None = None
        seen: set[str] = set()
        for handoff in entry["handoffs"]:
            required = {
                "handoffId", "sourceFingerprint", "destinationFingerprint", "evidencePath",
                "destinationArtifactPath", "manifestSha256", "patchSha256", "resultSha256",
                "reservationTransferred",
            }
            if not isinstance(handoff, dict) or set(handoff) != required:
                raise ValidationError("Registry handoff record has invalid fields")
            handoff_id = handoff["handoffId"]
            try:
                if str(uuid.UUID(handoff_id)) != handoff_id:
                    raise ValueError
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValidationError("Registry handoff ID must be a canonical UUID") from exc
            if handoff_id in seen:
                raise ValidationError("Registry contains a duplicate handoff ID")
            seen.add(handoff_id)
            source_fingerprint = handoff["sourceFingerprint"]
            destination_fingerprint = handoff["destinationFingerprint"]
            if (
                not isinstance(source_fingerprint, str)
                or not FINGERPRINT_PATTERN.fullmatch(source_fingerprint)
                or not isinstance(destination_fingerprint, str)
                or not FINGERPRINT_PATTERN.fullmatch(destination_fingerprint)
            ):
                raise ValidationError("Registry handoff fingerprints are invalid")
            if previous_destination is not None and source_fingerprint != previous_destination:
                raise ValidationError("Registry handoff fingerprint chain is discontinuous")
            previous_destination = destination_fingerprint
            if handoff["reservationTransferred"] is not False:
                raise ValidationError("Base registry handoff cannot claim reservation transfer")
            for field in ("manifestSha256", "patchSha256", "resultSha256"):
                digest = handoff[field]
                if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                    raise ValidationError("Registry handoff evidence digest is invalid")
            destination_artifact = handoff["destinationArtifactPath"]
            if not isinstance(destination_artifact, str) or not os.path.isabs(destination_artifact):
                raise ValidationError("Registry handoff destination artifact path is invalid")
            try:
                destination_root = repository_root_from_registered_artifact(
                    Path(destination_artifact)
                )
                registered_artifact_root(
                    destination_root,
                    Path(destination_artifact),
                    candidate_may_not_exist=True,
                )
            except UnsafePathError as exc:
                raise ValidationError(
                    "Registry handoff destination artifact path is outside the managed roots"
                ) from exc
            evidence_path = Path(handoff["evidencePath"])
            expected = self.state_home / "handoffs" / workflow_id / handoff_id
            if _lexical_path(evidence_path) != _lexical_path(expected):
                raise ValidationError("Registry handoff evidence path is not canonical")
            self.state_paths.directory(evidence_path)
            manifest_path = self.state_paths.leaf(evidence_path / "manifest.json", must_exist=True)
            patch_path = self.state_paths.leaf(evidence_path / "patch.diff", must_exist=True)
            result_path = self.state_paths.leaf(evidence_path / "result.json", must_exist=True)
            manifest_bytes = self.state_paths.read_bytes(manifest_path)
            patch_bytes = self.state_paths.read_bytes(patch_path)
            result_bytes = self.state_paths.read_bytes(result_path)
            if hashlib.sha256(manifest_bytes).hexdigest() != handoff["manifestSha256"]:
                raise ValidationError("Registry handoff manifest hash differs from authoritative record")
            if hashlib.sha256(patch_bytes).hexdigest() != handoff["patchSha256"]:
                raise ValidationError("Registry handoff patch hash differs from authoritative record")
            if hashlib.sha256(result_bytes).hexdigest() != handoff["resultSha256"]:
                raise ValidationError("Registry handoff result hash differs from authoritative record")
            manifest = self.state_paths.read_json(manifest_path)
            result = self.state_paths.read_json(result_path)
            self._validate_handoff_manifest(workflow_id, handoff_id, manifest)
            self._validate_handoff_result(workflow_id, handoff, result)
        if previous_destination is not None and previous_destination != entry["physicalWorktreeFingerprint"]:
            raise ValidationError("Registry final handoff fingerprint does not match current worktree binding")

    @staticmethod
    def _validate_handoff_manifest(
        workflow_id: str,
        handoff_id: str,
        manifest: dict[str, Any],
    ) -> None:
        required = {
            "schemaVersion", "workflowId", "handoffId", "changes",
            "reservationTransferred", "gitMutationPermitted",
        }
        if set(manifest) != required or manifest["schemaVersion"] != "1.0":
            raise ValidationError("Registry handoff manifest shape is invalid")
        if (
            manifest["workflowId"] != workflow_id
            or manifest["handoffId"] != handoff_id
            or manifest["reservationTransferred"] is not False
            or manifest["gitMutationPermitted"] is not False
            or not isinstance(manifest["changes"], list)
        ):
            raise ValidationError("Registry handoff manifest identity or policy is invalid")
        seen: set[str] = set()
        for change in manifest["changes"]:
            if not isinstance(change, dict):
                raise ValidationError("Registry handoff change record must be an object")
            path = change.get("path")
            operation = change.get("operation")
            if not isinstance(path, str) or not path or path.casefold() in seen:
                raise ValidationError("Registry handoff change path is invalid or duplicated")
            redacted_path = bool(re.fullmatch(r"\[REDACTED-PATH:[a-f0-9]{12}\]", path))
            if not redacted_path:
                try:
                    if ensure_safe_relative_path(path).as_posix() != path:
                        raise ValueError
                except (UnsafePathError, ValueError) as exc:
                    raise ValidationError("Registry handoff change path is not canonical") from exc
            seen.add(path.casefold())
            if operation == "delete":
                valid = set(change) == {"path", "operation"}
            elif operation == "write" and change.get("contentEvidence") in {
                "redacted-sensitive-path",
                "redacted-sensitive-content",
            }:
                valid = (
                    (
                        redacted_path
                        if change["contentEvidence"] == "redacted-sensitive-path"
                        else not redacted_path
                    )
                    and set(change) == {"path", "operation", "contentEvidence"}
                )
            elif operation == "write":
                size = change.get("size")
                digest = change.get("sha256")
                valid = (
                    set(change) == {"path", "operation", "size", "sha256"}
                    and isinstance(size, int)
                    and not isinstance(size, bool)
                    and size >= 0
                    and isinstance(digest, str)
                    and bool(re.fullmatch(r"[a-f0-9]{64}", digest))
                )
            else:
                valid = False
            if not valid:
                raise ValidationError("Registry handoff change record shape is invalid")

    @staticmethod
    def _validate_handoff_result(
        workflow_id: str,
        handoff: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        required = {
            "schemaVersion", "status", "workflowId", "handoffId", "sourceFingerprint",
            "destinationFingerprint", "artifactPath", "reservationTransferred",
            "gitMutationPerformed", "authority",
        }
        if set(result) != required or result["schemaVersion"] != "1.0":
            raise ValidationError("Registry handoff result shape is invalid")
        expected = {
            "status": "completed",
            "workflowId": workflow_id,
            "handoffId": handoff["handoffId"],
            "sourceFingerprint": handoff["sourceFingerprint"],
            "destinationFingerprint": handoff["destinationFingerprint"],
            "artifactPath": handoff["destinationArtifactPath"],
            "reservationTransferred": False,
            "gitMutationPerformed": False,
            "authority": "authoritative-only-when-registry-hash-referenced",
        }
        if {key: result[key] for key in expected} != expected:
            raise ValidationError("Registry handoff result differs from authoritative record")

    @staticmethod
    def _validate_unique_mappings(registry: dict[str, Any]) -> None:
        paths: set[str] = set()
        work_keys: set[str] = set()
        external_ids: set[str] = set()
        for entry in registry.get("workflows", {}).values():
            path = _normalized_path(entry["artifactPath"])
            work_key = entry["workKey"].casefold()
            external_id = entry.get("externalId")
            if path in paths:
                raise CollisionError("Registry contains a case-insensitive artifact-path collision")
            if work_key in work_keys:
                raise CollisionError("Registry contains a case-insensitive work-key collision")
            if external_id is not None and external_id.casefold() in external_ids:
                raise CollisionError("Registry contains a duplicate external-ID mapping")
            paths.add(path)
            work_keys.add(work_key)
            if external_id is not None:
                external_ids.add(external_id.casefold())
