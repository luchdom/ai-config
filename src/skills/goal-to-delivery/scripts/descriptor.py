"""Versioned work-descriptor creation, validation, and read-only history fallback."""

from __future__ import annotations

import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .atomic_files import read_json
from .errors import UnsafePathError, ValidationError
from .path_safety import (
    ensure_safe_descendant,
    validate_local_key,
    validate_provider_key,
    validate_repository_key,
    validate_slug,
    WINDOWS_DEVICE_PATTERN,
    WINDOWS_INVALID_CHARACTERS,
)
from .redaction import redact_value

WORK_DESCRIPTOR_VERSION = "2.0"
WORKFLOWS = {"autonomous", "semi-autonomous", "manual"}
WORK_SOURCES = {"linear", "local"}
COMPLETION_BOUNDARIES = {"artifact", "working-tree", "commit", "pr", "merge"}
ARTIFACT_STAGES = {
    "initialized",
    "plan",
    "clarify",
    "design",
    "task",
    "audit",
    "implement",
    "design_review",
    "review",
    "qa",
    "docs",
    "completion",
}
FINGERPRINT_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


def new_descriptor(
    *,
    workflow_id: str,
    workflow: str,
    work_source: str,
    work_key: str,
    slug: str,
    repository_key: str,
    repository_root: str,
    goal: str,
    acceptance_criteria: list[str],
    non_goals: list[str],
    tracking_provider: str,
    external_id: str | None,
    completion_boundary: str,
    physical_worktree_fingerprint: str,
    risk_flags: list[str],
    artifact_folder: str,
    design_required: bool = False,
    design_reason: str = "No product UI or interaction change declared.",
) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "schemaVersion": WORK_DESCRIPTOR_VERSION,
        "revision": 1,
        "workflowId": workflow_id,
        "workflow": workflow,
        "workSource": work_source,
        "workKey": work_key,
        "slug": slug,
        "repositoryKey": repository_key,
        "repositoryRoot": repository_root,
        "goal": goal,
        "acceptanceCriteria": acceptance_criteria,
        "nonGoals": non_goals,
        "tracking": {"provider": tracking_provider, "externalId": external_id},
        "completionBoundary": completion_boundary,
        "physicalWorktreeFingerprint": physical_worktree_fingerprint,
        "riskFlags": risk_flags,
        "artifactFolder": artifact_folder,
        "artifactInventory": ["workflow.json"],
        "currentArtifactStage": "initialized",
        "assumptionsDecisionRefs": [],
        "design": {"required": design_required, "reason": design_reason},
        "deliverySummary": {},
        "supersededArtifactNames": [],
    }
    validate_descriptor(descriptor)
    return descriptor


def _string_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationError(f"{field} must be an array of strings")


def _validate_windows_safe_component(component: str, field: str) -> None:
    if not component or component in {".", ".."}:
        raise ValidationError(f"{field} contains an empty or dot path segment")
    if component != unicodedata.normalize("NFC", component):
        raise ValidationError(f"{field} must use canonical NFC path text")
    if any(unicodedata.category(character) == "Cc" for character in component):
        raise ValidationError(f"{field} contains a control character")
    if any(character in WINDOWS_INVALID_CHARACTERS for character in component):
        raise ValidationError(f"{field} contains a Windows-invalid character")
    if component.endswith((".", " ")):
        raise ValidationError(f"{field} contains a name ending in dot or space")
    if WINDOWS_DEVICE_PATTERN.fullmatch(component):
        raise ValidationError(f"{field} contains a Windows reserved device name")


def _reject_case_aliases(values: list[str], field: str) -> None:
    canonical = [unicodedata.normalize("NFC", value).casefold() for value in values]
    if len(canonical) != len(set(canonical)):
        raise ValidationError(f"{field} must not contain duplicate or case-aliased names")


def _validate_artifact_inventory(values: list[str]) -> None:
    for value in values:
        if not value or value != value.strip() or "\\" in value or value.startswith("/"):
            raise ValidationError("artifactInventory entries must be canonical relative file paths")
        components = value.split("/")
        for component in components:
            _validate_windows_safe_component(component, "artifactInventory")
    _reject_case_aliases(values, "artifactInventory")


def _validate_superseded_artifact_names(values: list[str]) -> None:
    for value in values:
        if not value or value != value.strip() or "/" in value or "\\" in value:
            raise ValidationError("supersededArtifactNames entries must be safe single names")
        _validate_windows_safe_component(value, "supersededArtifactNames")
    _reject_case_aliases(values, "supersededArtifactNames")


def validate_descriptor(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("Work descriptor must be a JSON object")
    required = {
        "schemaVersion", "revision", "workflowId", "workflow", "workSource", "workKey", "slug",
        "repositoryKey", "repositoryRoot", "goal", "acceptanceCriteria", "nonGoals", "tracking",
        "completionBoundary", "physicalWorktreeFingerprint", "riskFlags", "artifactFolder",
        "artifactInventory", "currentArtifactStage", "assumptionsDecisionRefs", "design",
        "deliverySummary", "supersededArtifactNames",
    }
    extra = set(value) - required
    missing = required - set(value)
    if missing or extra:
        raise ValidationError(f"Descriptor fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
    if value["schemaVersion"] != WORK_DESCRIPTOR_VERSION:
        raise ValidationError(f"Unsupported work descriptor schema: {value['schemaVersion']!r}")
    if not isinstance(value["revision"], int) or isinstance(value["revision"], bool) or value["revision"] < 1:
        raise ValidationError("Descriptor revision must be a positive integer")
    try:
        parsed_uuid = uuid.UUID(value["workflowId"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("workflowId must be a canonical UUID") from exc
    if str(parsed_uuid) != value["workflowId"]:
        raise ValidationError("workflowId must use canonical lowercase UUID formatting")
    if value["workflow"] not in WORKFLOWS:
        raise ValidationError("Unknown workflow policy")
    if value["workSource"] not in WORK_SOURCES:
        raise ValidationError("Unknown work source")
    validate_slug(value["slug"])
    validate_repository_key(value["repositoryKey"])
    if not isinstance(value["repositoryRoot"], str) or not os.path.isabs(value["repositoryRoot"]):
        raise ValidationError("repositoryRoot must be an observed absolute path")
    if not isinstance(value["goal"], str) or not value["goal"].strip():
        raise ValidationError("goal must be non-empty")
    for field in (
        "acceptanceCriteria", "nonGoals", "riskFlags", "artifactInventory",
        "assumptionsDecisionRefs", "supersededArtifactNames",
    ):
        _string_list(value[field], field)
    _validate_artifact_inventory(value["artifactInventory"])
    _validate_superseded_artifact_names(value["supersededArtifactNames"])
    if value["completionBoundary"] not in COMPLETION_BOUNDARIES:
        raise ValidationError("Unknown completion boundary")
    if value["currentArtifactStage"] not in ARTIFACT_STAGES:
        raise ValidationError("Unknown artifact stage")
    if not isinstance(value["artifactFolder"], str) or not os.path.isabs(value["artifactFolder"]):
        raise ValidationError("artifactFolder must be an absolute path")
    if not isinstance(value["physicalWorktreeFingerprint"], str) or not FINGERPRINT_PATTERN.fullmatch(
        value["physicalWorktreeFingerprint"]
    ):
        raise ValidationError("physicalWorktreeFingerprint must be a sha256 identity")
    tracking = value["tracking"]
    if not isinstance(tracking, dict) or set(tracking) != {"provider", "externalId"}:
        raise ValidationError("tracking must contain only provider and externalId")
    if value["workSource"] == "local":
        validate_local_key(value["workKey"])
        if tracking != {"provider": "none", "externalId": None}:
            validate_provider_key(tracking.get("provider"), tracking.get("externalId"))
        if value["workflow"] == "autonomous":
            raise ValidationError("A local/user request cannot forge autonomous workflow mode")
    else:
        validate_provider_key(tracking.get("provider"), value["workKey"])
        if tracking.get("externalId") != value["workKey"]:
            raise ValidationError("Linear external ID and provider-observed work key must match")
    design = value["design"]
    if (
        not isinstance(design, dict)
        or set(design) != {"required", "reason"}
        or not isinstance(design["required"], bool)
        or not isinstance(design["reason"], str)
        or not design["reason"].strip()
    ):
        raise ValidationError("design must record a boolean requirement and non-empty reason")
    if not isinstance(value["deliverySummary"], dict):
        raise ValidationError("deliverySummary must be an object")
    if redact_value(value) != value:
        raise ValidationError("Work descriptor contains secret-like material and cannot be persisted")
    return value


def read_descriptor(path: Path) -> dict[str, Any]:
    return validate_descriptor(read_json(path))


@dataclass(frozen=True)
class HistoricalArtifact:
    path: Path
    historical: bool = True


def inspect_historical_artifact(repository_root: Path, path: Path) -> HistoricalArtifact:
    """Allow exact read-only navigation of legacy docs-ai layouts without adopting them."""

    docs_root = Path(repository_root) / "docs-ai"
    candidate = ensure_safe_descendant(docs_root, Path(path), candidate_may_not_exist=False)
    if not candidate.exists():
        raise UnsafePathError(f"Historical artifact does not exist: {candidate}")
    return HistoricalArtifact(path=candidate)
