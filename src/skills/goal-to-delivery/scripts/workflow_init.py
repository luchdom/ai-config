"""Canonical deterministic workflow init, exact resume, and atomic attachment."""

from __future__ import annotations

import copy
import errno
import hashlib
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .atomic_files import atomic_write_json, read_json
from .descriptor import new_descriptor, read_descriptor, validate_descriptor
from .errors import CollisionError, ResumeError, ValidationError
from .identity import RepositoryIdentity, observe_repository_identity
from .path_safety import (
    ensure_safe_descendant,
    existing_artifact_names,
    iter_safe_artifact_scan_locations,
    normalize_slug,
    reject_case_insensitive_collision,
    validate_provider_key,
    validate_repository_key,
)
from .registry import WorkflowRegistry, validate_descriptor_projection
from .state_home import StateHome, derive_state_home, ensure_state_home
from .state_paths import StatePathGuard

BASE_PACKAGE_VERSION = "1.0"
_replace_path = os.replace


@dataclass(frozen=True)
class ProviderObservedWork:
    """A provider adapter observation; intentionally absent from end-user CLI init."""

    provider: str
    canonical_key: str
    observation_id: str

    def __post_init__(self) -> None:
        validate_provider_key(self.provider, self.canonical_key)
        if not self.observation_id.strip():
            raise ValidationError("Provider-observed work requires a non-empty adapter observation ID")


class WorkflowManager:
    def __init__(
        self,
        repository_root: str | Path,
        *,
        repository_key: str,
        state_home_override: str | Path | None = None,
        environment: dict[str, str] | None = None,
    ):
        self.repository_key = validate_repository_key(repository_key)
        self.identity: RepositoryIdentity = observe_repository_identity(repository_root)
        self.repository_root = Path(self.identity.repository_root)
        self.docs_root = self.repository_root / "docs-ai"
        self.home: StateHome = ensure_state_home(
            derive_state_home(
                self.identity,
                override=state_home_override,
                environment=environment,
            ),
            self.identity,
            repository_key=self.repository_key,
        )
        self.state_paths = StatePathGuard(self.home.repository, base=self.home.base)
        self._bound_repository_key = self.repository_key
        self.registry = WorkflowRegistry(
            self.home.repository,
            self.identity.repository_id,
            repository_key=self.repository_key,
            normalized_common_dir=os.path.normcase(
                os.path.realpath(self.identity.common_dir)
            ).replace("\\", "/"),
            state_paths=self.state_paths,
        )
        self.registry.ensure()
        with self.registry.mutex():
            self._load_registry_unlocked()
        self.recover_incomplete_transactions()

    def recover_incomplete_transactions(self) -> None:
        """Finalize a proven commit or roll a split descriptor/registry pair back."""

        transactions = self.home.repository / "transactions"
        if not os.path.lexists(transactions):
            return
        transactions = self.state_paths.directory(transactions)
        with self.registry.mutex():
            for transaction_path in self.state_paths.glob_files(transactions, "*.json"):
                transaction = self.state_paths.read_json(transaction_path)
                required = {
                    "schemaVersion", "operation", "workflowId", "artifactFolder", "descriptorPath",
                    "beforeDescriptor", "afterDescriptor", "beforeRegistry", "afterRegistry",
                }
                if set(transaction) != required or transaction["schemaVersion"] != "1.0":
                    raise ValidationError(
                        f"Malformed pending workflow transaction requires attended reconciliation: {transaction_path}"
                    )
                self._validate_transaction_bindings(transaction)
                registry_current = self._load_registry_unlocked()
                descriptor_path = Path(transaction["descriptorPath"])
                descriptor_current = read_json(descriptor_path) if descriptor_path.exists() else None
                if (
                    registry_current == transaction["afterRegistry"]
                    and descriptor_current == transaction["afterDescriptor"]
                ):
                    self.state_paths.unlink(transaction_path)
                    continue
                if transaction["beforeDescriptor"] is None:
                    self.state_paths.write_json(self.registry.path, transaction["beforeRegistry"])
                    artifact_folder = Path(transaction["artifactFolder"])
                    if artifact_folder.exists():
                        self._quarantine_partial(
                            artifact_folder,
                            transaction["workflowId"],
                            reason="recovered-incomplete-initialization",
                            docs_root=Path(transaction["afterDescriptor"]["repositoryRoot"]) / "docs-ai",
                        )
                else:
                    atomic_write_json(descriptor_path, transaction["beforeDescriptor"])
                    self.state_paths.write_json(self.registry.path, transaction["beforeRegistry"])
                self.state_paths.unlink(transaction_path)

    def initialize_local(
        self,
        *,
        workflow: str,
        goal: str,
        completion_boundary: str = "working-tree",
        display_title: str | None = None,
        acceptance_criteria: list[str] | None = None,
        non_goals: list[str] | None = None,
        risk_flags: list[str] | None = None,
        design_required: bool = False,
        design_reason: str = "No product UI or interaction change declared.",
        max_attempts: int = 8,
    ) -> dict[str, Any]:
        if workflow not in {"manual", "semi-autonomous"}:
            raise ValidationError("Local init accepts only manual or semi-autonomous policy")
        slug = normalize_slug(display_title or goal)
        return self._allocate(
            workflow=workflow,
            work_source="local",
            provider_observation=None,
            goal=goal,
            slug=slug,
            completion_boundary=completion_boundary,
            acceptance_criteria=acceptance_criteria or [],
            non_goals=non_goals or [],
            risk_flags=risk_flags or [],
            design_required=design_required,
            design_reason=design_reason,
            max_attempts=max_attempts,
        )

    def initialize_provider(
        self,
        *,
        observed_work: ProviderObservedWork,
        workflow: str,
        goal: str,
        completion_boundary: str,
        display_title: str | None = None,
        acceptance_criteria: list[str] | None = None,
        non_goals: list[str] | None = None,
        risk_flags: list[str] | None = None,
        design_required: bool = False,
        design_reason: str = "No product UI or interaction change declared.",
    ) -> dict[str, Any]:
        slug = normalize_slug(display_title or goal)
        return self._allocate(
            workflow=workflow,
            work_source="linear",
            provider_observation=observed_work,
            goal=goal,
            slug=slug,
            completion_boundary=completion_boundary,
            acceptance_criteria=acceptance_criteria or [],
            non_goals=non_goals or [],
            risk_flags=risk_flags or [],
            design_required=design_required,
            design_reason=design_reason,
            max_attempts=1,
        )

    def _allocate(
        self,
        *,
        workflow: str,
        work_source: str,
        provider_observation: ProviderObservedWork | None,
        goal: str,
        slug: str,
        completion_boundary: str,
        acceptance_criteria: list[str],
        non_goals: list[str],
        risk_flags: list[str],
        design_required: bool,
        design_reason: str,
        max_attempts: int,
    ) -> dict[str, Any]:
        self._assert_manager_repository_key()
        if max_attempts < 1:
            raise ValidationError("Allocation retry budget must be positive")
        with self.registry.mutex():
            registry_before = self._load_registry_unlocked()
            for attempt in range(max_attempts):
                if work_source == "local":
                    work_key = self._next_local_key(registry_before)
                    provider = "none"
                    external_id = None
                else:
                    assert provider_observation is not None
                    work_key = provider_observation.canonical_key
                    provider = provider_observation.provider
                    external_id = work_key
                    if any(
                        entry.get("externalId") == external_id
                        for entry in registry_before["workflows"].values()
                    ):
                        raise CollisionError(f"External work {external_id} is already registered")
                folder_name = f"{work_key}-{slug}"
                candidate = self.docs_root / folder_name
                ensure_safe_descendant(self.docs_root, candidate)
                names = existing_artifact_names(
                    self.docs_root,
                    (entry["artifactPath"] for entry in registry_before["workflows"].values()),
                )
                reject_case_insensitive_collision(folder_name, names)
                workflow_id = str(uuid.uuid4())
                descriptor_path = candidate / "workflow.json"
                transaction_path = self._transaction_path(workflow_id)
                descriptor = new_descriptor(
                    workflow_id=workflow_id,
                    workflow=workflow,
                    work_source=work_source,
                    work_key=work_key,
                    slug=slug,
                    repository_key=self.repository_key,
                    repository_root=os.fspath(self.repository_root),
                    goal=goal,
                    acceptance_criteria=acceptance_criteria,
                    non_goals=non_goals,
                    tracking_provider=provider,
                    external_id=external_id,
                    completion_boundary=completion_boundary,
                    physical_worktree_fingerprint=self.identity.physical_worktree_fingerprint,
                    risk_flags=risk_flags,
                    artifact_folder=os.fspath(candidate),
                    design_required=design_required,
                    design_reason=design_reason,
                )
                registry_after = copy.deepcopy(registry_before)
                registry_after["revision"] += 1
                registry_after["workflows"][workflow_id] = self._registry_entry(descriptor)
                transaction = {
                    "schemaVersion": "1.0",
                    "operation": "initialize",
                    "workflowId": workflow_id,
                    "artifactFolder": os.fspath(candidate),
                    "descriptorPath": os.fspath(descriptor_path),
                    "beforeDescriptor": None,
                    "afterDescriptor": descriptor,
                    "beforeRegistry": registry_before,
                    "afterRegistry": registry_after,
                }
                self._validate_transaction_bindings(transaction)
                self.state_paths.write_json(transaction_path, transaction)
                created = False
                try:
                    try:
                        candidate.mkdir(parents=True, exist_ok=False)
                        created = True
                    except FileExistsError:
                        self.state_paths.unlink(transaction_path, missing_ok=True)
                        if work_source == "local" and attempt + 1 < max_attempts:
                            continue
                        raise CollisionError(f"Unable to allocate unique artifact folder {folder_name}")
                    ensure_safe_descendant(self.docs_root, candidate, candidate_may_not_exist=False)
                    atomic_write_json(descriptor_path, descriptor)
                    if read_descriptor(descriptor_path) != descriptor:
                        raise ValidationError("Descriptor readback mismatch")
                    self.registry.write_unlocked(
                        registry_after,
                        expected_revision=registry_before["revision"],
                    )
                    if self._load_registry_unlocked()["workflows"][workflow_id] != self._registry_entry(descriptor):
                        raise ValidationError("Registry allocation readback mismatch")
                    self.state_paths.unlink(transaction_path, missing_ok=True)
                    return descriptor
                except Exception:
                    if created:
                        self._rollback_initialization(
                            candidate=candidate,
                            workflow_id=workflow_id,
                            registry_before=registry_before,
                        )
                    self.state_paths.unlink(transaction_path, missing_ok=True)
                    raise
        raise CollisionError("Local allocation retry budget exhausted")

    def resume(
        self,
        *,
        workflow_id: str | None = None,
        artifact_path: str | Path | None = None,
        external_id: str | None = None,
    ) -> dict[str, Any]:
        self._assert_manager_repository_key()
        supplied = sum(value is not None for value in (workflow_id, artifact_path, external_id))
        if supplied != 1:
            raise ResumeError("Resume requires exactly one workflow ID, artifact path, or external ID")
        self._preflight_authority(
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            external_id=external_id,
        )
        with self.registry.mutex():
            registry = self._load_registry_unlocked()
            entry = copy.deepcopy(
                self.registry._resolve_unlocked_structural(
                    registry,
                    workflow_id=workflow_id,
                    artifact_path=artifact_path,
                    external_id=external_id,
                )
            )
        self._assert_entry_context(entry)
        descriptor = read_descriptor(Path(entry["artifactPath"]) / "workflow.json")
        self._assert_descriptor_registry_projection(entry, descriptor)
        if descriptor["physicalWorktreeFingerprint"] != self.identity.physical_worktree_fingerprint:
            raise ResumeError(self._handoff_mismatch_message(entry))
        return descriptor

    def attach_linear(self, *, workflow_id: str, external_id: str) -> dict[str, Any]:
        self._assert_manager_repository_key()
        validate_provider_key("linear", external_id)
        self._preflight_authority(workflow_id=workflow_id)
        with self.registry.mutex():
            registry_before = self._load_registry_unlocked()
            entry = self.registry._resolve_unlocked_structural(registry_before, workflow_id=workflow_id)
            self._assert_entry_context(entry)
            existing = [
                candidate
                for candidate in registry_before["workflows"].values()
                if candidate.get("externalId") == external_id and candidate["workflowId"] != workflow_id
            ]
            if existing:
                raise CollisionError(f"External ID {external_id} is mapped to another workflow")
            descriptor_path = Path(entry["artifactPath"]) / "workflow.json"
            descriptor_before = read_descriptor(descriptor_path)
            self._assert_descriptor_registry_projection(entry, descriptor_before)
            if descriptor_before["tracking"] == {"provider": "linear", "externalId": external_id}:
                return descriptor_before
            if descriptor_before["tracking"] != {"provider": "none", "externalId": None}:
                raise CollisionError("Workflow is already attached to a different external ID")
            descriptor_after = copy.deepcopy(descriptor_before)
            descriptor_after["revision"] += 1
            descriptor_after["tracking"] = {"provider": "linear", "externalId": external_id}
            validate_descriptor(descriptor_after)
            registry_after = copy.deepcopy(registry_before)
            registry_after["revision"] += 1
            registry_after["workflows"][workflow_id]["externalProvider"] = "linear"
            registry_after["workflows"][workflow_id]["externalId"] = external_id
            registry_after["workflows"][workflow_id]["descriptorRevision"] = descriptor_after["revision"]
            self._paired_commit(
                operation="attach",
                workflow_id=workflow_id,
                descriptor_path=descriptor_path,
                descriptor_before=descriptor_before,
                descriptor_after=descriptor_after,
                registry_before=registry_before,
                registry_after=registry_after,
            )
            return descriptor_after

    def assert_authorized_context(self, workflow_id: str) -> dict[str, Any]:
        return self.resume(workflow_id=workflow_id)

    def workflow_managed_handoff(
        self,
        *,
        workflow_id: str,
        destination_root: str | Path,
        expected_paths: list[str],
    ) -> dict[str, Any]:
        self._assert_manager_repository_key()
        self._preflight_authority(workflow_id=workflow_id)
        from .handoff import workflow_managed_handoff

        return workflow_managed_handoff(
            source=self,
            workflow_id=workflow_id,
            destination_root=destination_root,
            expected_paths=expected_paths,
        )

    def _paired_commit(
        self,
        *,
        operation: str,
        workflow_id: str,
        descriptor_path: Path,
        descriptor_before: dict[str, Any],
        descriptor_after: dict[str, Any],
        registry_before: dict[str, Any],
        registry_after: dict[str, Any],
    ) -> None:
        transaction_path = self._transaction_path(workflow_id)
        transaction = {
            "schemaVersion": "1.0",
            "operation": operation,
            "workflowId": workflow_id,
            "artifactFolder": os.fspath(descriptor_path.parent),
            "descriptorPath": os.fspath(descriptor_path),
            "beforeDescriptor": descriptor_before,
            "afterDescriptor": descriptor_after,
            "beforeRegistry": registry_before,
            "afterRegistry": registry_after,
        }
        self._validate_transaction_bindings(transaction)
        self.state_paths.write_json(transaction_path, transaction)
        try:
            atomic_write_json(
                descriptor_path,
                descriptor_after,
                expected_revision=descriptor_before["revision"],
            )
            self.registry.write_unlocked(
                registry_after,
                expected_revision=registry_before["revision"],
            )
            if read_descriptor(descriptor_path) != descriptor_after:
                raise ValidationError(f"{operation} descriptor readback mismatch")
            if self._load_registry_unlocked() != registry_after:
                raise ValidationError(f"{operation} registry readback mismatch")
            self.state_paths.unlink(transaction_path, missing_ok=True)
        except Exception:
            # Readers use the same mutex, so rollback restores the externally visible pair.
            atomic_write_json(descriptor_path, descriptor_before)
            self.state_paths.write_json(self.registry.path, registry_before)
            self.state_paths.unlink(transaction_path, missing_ok=True)
            raise

    def _rollback_initialization(
        self,
        *,
        candidate: Path,
        workflow_id: str,
        registry_before: dict[str, Any],
    ) -> None:
        current = self._load_registry_unlocked()
        if workflow_id in current["workflows"]:
            self.state_paths.write_json(self.registry.path, registry_before)
        if candidate.exists():
            self._quarantine_partial(candidate, workflow_id, reason="failed-initialization")

    def _quarantine_partial(
        self,
        candidate: Path,
        workflow_id: str,
        *,
        reason: str,
        docs_root: Path | None = None,
    ) -> None:
        quarantine = self.state_paths.directory(self.home.repository / "quarantine", create=True)
        record_path = self.state_paths.leaf(quarantine / f"{time.time_ns()}-{workflow_id}.json")
        try:
            ensure_safe_descendant(docs_root or self.docs_root, candidate, candidate_may_not_exist=False)
        except Exception as exc:
            self.state_paths.write_json(
                record_path,
                {
                    "schemaVersion": "1.0",
                    "workflowId": workflow_id,
                    "status": "quarantine-required",
                    "reason": reason,
                    "path": os.fspath(candidate),
                    "safetyFailure": str(exc),
                },
            )
            return
        destination = candidate.parent / f".quarantine-{workflow_id}-{time.time_ns()}"
        method = "atomic-in-place-rename"
        try:
            _replace_path(candidate, destination)
        except OSError as exc:
            if exc.errno != errno.EXDEV:
                self.state_paths.write_json(
                    record_path,
                    {
                        "schemaVersion": "1.0",
                        "workflowId": workflow_id,
                        "status": "quarantine-required",
                        "reason": reason,
                        "path": os.fspath(candidate),
                        "safetyFailure": str(exc),
                    },
                )
                return
            method = "verified-in-place-copy"
            try:
                shutil.copytree(candidate, destination, copy_function=shutil.copy2)
                if self._tree_digest(candidate) != self._tree_digest(destination):
                    raise ValidationError("Quarantine copy readback mismatch")
                shutil.rmtree(candidate)
            except Exception as copy_error:
                self.state_paths.write_json(
                    record_path,
                    {
                        "schemaVersion": "1.0",
                        "workflowId": workflow_id,
                        "status": "quarantine-required",
                        "reason": reason,
                        "path": os.fspath(candidate),
                        "partialDestination": os.fspath(destination),
                        "safetyFailure": str(copy_error),
                    },
                )
                return
        self.state_paths.write_json(
            record_path,
            {
                "schemaVersion": "1.0",
                "workflowId": workflow_id,
                "status": "quarantined",
                "reason": reason,
                "originalPath": os.fspath(candidate),
                "quarantinePath": os.fspath(destination),
                "method": method,
            },
        )

    @staticmethod
    def _tree_digest(root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if path.is_symlink():
                raise ValidationError(f"Quarantine refuses symlink content: {path}")
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0directory\0" if path.is_dir() else b"\0file\0")
            if path.is_file():
                digest.update(hashlib.sha256(path.read_bytes()).digest())
        return digest.hexdigest()

    def _load_registry_unlocked(self) -> dict[str, Any]:
        registry = self.registry.load_unlocked()
        self._validate_registry_bindings(registry)
        return registry

    def _validate_registry_bindings(self, registry: dict[str, Any]) -> None:
        self.registry.validate_value(registry)

    def _validate_transaction_bindings(self, transaction: dict[str, Any]) -> None:
        after_descriptor = validate_descriptor(transaction["afterDescriptor"])
        before_descriptor = transaction["beforeDescriptor"]
        if before_descriptor is not None:
            validate_descriptor(before_descriptor)
        if after_descriptor["workflowId"] != transaction["workflowId"]:
            raise ValidationError("Transaction workflow identity mismatch")
        artifact_folder = Path(transaction["artifactFolder"])
        descriptor_path = Path(transaction["descriptorPath"])
        if artifact_folder != Path(after_descriptor["artifactFolder"]):
            raise ValidationError("Transaction artifact folder and after-descriptor disagree")
        if descriptor_path != artifact_folder / "workflow.json":
            raise ValidationError("Transaction descriptor path must be the exact workflow.json child")
        repository_root = Path(after_descriptor["repositoryRoot"])
        observed = observe_repository_identity(repository_root)
        if os.path.normcase(os.path.realpath(observed.repository_root)) != os.path.normcase(
            os.path.realpath(repository_root)
        ):
            raise ValidationError("Transaction repositoryRoot must be the exact observed worktree root")
        if observed.repository_id != self.identity.repository_id:
            raise ValidationError("Transaction target belongs to another Git common directory")
        if observed.physical_worktree_fingerprint != after_descriptor["physicalWorktreeFingerprint"]:
            raise ValidationError("Transaction target fingerprint disagrees with its repository root")
        ensure_safe_descendant(repository_root / "docs-ai", artifact_folder)
        self._validate_registry_bindings(transaction["beforeRegistry"])
        self._validate_registry_bindings(transaction["afterRegistry"])
        before_entry = transaction["beforeRegistry"]["workflows"].get(transaction["workflowId"])
        if before_descriptor is not None:
            if before_entry is None:
                raise ValidationError("Transaction before-registry is missing its descriptor projection")
            self._assert_descriptor_registry_projection(before_entry, before_descriptor)
        after_entry = transaction["afterRegistry"]["workflows"].get(transaction["workflowId"])
        if after_entry is None:
            raise ValidationError("Transaction after-registry is missing its descriptor projection")
        self._assert_descriptor_registry_projection(after_entry, after_descriptor)

    def _assert_descriptor_registry_projection(
        self,
        entry: dict[str, Any],
        descriptor: dict[str, Any],
    ) -> None:
        validate_descriptor_projection(entry, descriptor)

    def _next_local_key(self, registry: dict[str, Any]) -> str:
        observed: list[int] = []
        for location in iter_safe_artifact_scan_locations(self.docs_root):
            for child in location.iterdir():
                prefix = child.name.split("-", 1)[0]
                if prefix.isdigit() and len(prefix) >= 3:
                    observed.append(int(prefix))
        for entry in registry["workflows"].values():
            if entry["workKey"].isdigit():
                observed.append(int(entry["workKey"]))
        sequence = max(observed, default=0) + 1
        return f"{sequence:03d}"

    def _assert_entry_context(self, entry: dict[str, Any]) -> None:
        if entry["repositoryKey"] != self.repository_key:
            raise ResumeError("Workflow repositoryKey differs from this manager authority")
        if entry["repositoryId"] != self.identity.repository_id:
            raise ResumeError("Workflow is registered to a different normalized Git common directory")
        if entry["physicalWorktreeFingerprint"] != self.identity.physical_worktree_fingerprint:
            raise ResumeError(self._handoff_mismatch_message(entry))

    def _assert_manager_repository_key(self) -> None:
        if self.repository_key != self._bound_repository_key:
            raise ResumeError("Manager repositoryKey no longer matches state-home authority")

    def _preflight_authority(
        self,
        *,
        workflow_id: str | None = None,
        artifact_path: str | Path | None = None,
        external_id: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Read-only rejection path; every mutation path revalidates under the mutex."""

        registry = self._load_registry_unlocked()
        entry = self.registry._resolve_unlocked_structural(
            registry,
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            external_id=external_id,
        )
        self._assert_entry_context(entry)
        descriptor = read_descriptor(Path(entry["artifactPath"]) / "workflow.json")
        self._assert_descriptor_registry_projection(entry, descriptor)
        return entry, descriptor

    @staticmethod
    def _handoff_mismatch_message(entry: dict[str, Any]) -> str:
        return (
            "Physical-worktree mismatch: native Codex Hand off does not transfer workflow authority. "
            f"Return to registered source {entry['artifactPath']} or run explicit workflow-managed Handoff; "
            "otherwise perform attended recovery/reconciliation."
        )

    def _transaction_path(self, workflow_id: str) -> Path:
        transactions = self.state_paths.directory(
            self.home.repository / "transactions",
            create=True,
        )
        return self.state_paths.leaf(transactions / f"{workflow_id}.json")

    def _registry_entry(self, descriptor: dict[str, Any]) -> dict[str, Any]:
        return {
            "workflowId": descriptor["workflowId"],
            "workKey": descriptor["workKey"],
            "artifactPath": descriptor["artifactFolder"],
            "repositoryId": self.identity.repository_id,
            "repositoryKey": descriptor["repositoryKey"],
            "physicalWorktreeFingerprint": descriptor["physicalWorktreeFingerprint"],
            "externalProvider": descriptor["tracking"]["provider"],
            "externalId": descriptor["tracking"]["externalId"],
            "descriptorRevision": descriptor["revision"],
            "handoffs": [],
        }
