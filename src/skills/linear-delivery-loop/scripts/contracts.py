"""Dependency-free runtime validation for the versioned supervisor contracts."""

from __future__ import annotations

import copy
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .base_runtime import EXPECTED_BASE_VERSIONS, load_base_runtime


CONTRACT_VERSION = "1.0"
OPERATION_NAMES = (
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
)
SCHEMA_FILENAMES = {
    "project-config": "project-config.schema.json",
    "prepared-iteration": "prepared-iteration.schema.json",
    "checkpoint": "checkpoint.schema.json",
    "supervisor-state": "supervisor-state.schema.json",
    "editing-reservation": "editing-reservation.schema.json",
    "operation-journal": "operation-journal.schema.json",
    "worker-result": "worker-result.schema.json",
    "engine-command": "engine-command.schema.json",
    "release-authorization": "release-authorization.schema.json",
    "handoff-authorization": "handoff-authorization.schema.json",
    "trusted-observation": "trusted-observation.schema.json",
}
RUNTIME_CONSTRAINTS = {
    "project-config": {
        "canonical-absolute-paths",
        "exact-base-version-bindings",
        "scheduled-policy-vocabulary",
        "no-secret-like-material",
    },
    "prepared-iteration": {
        "canonical-absolute-paths",
        "engine-owned-capability-reference",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "checkpoint": {
        "canonical-absolute-paths",
        "safe-relative-paths",
        "stage-transition-changes-stage",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "supervisor-state": {
        "canonical-absolute-paths",
        "repository-version-bindings",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "editing-reservation": {
        "canonical-absolute-paths",
        "unique-reservation-identities",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "operation-journal": {
        "canonical-absolute-paths",
        "operation-inventory-parity",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "worker-result": {
        "safe-relative-paths",
        "proposal-only-no-authority",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "engine-command": {
        "canonical-absolute-paths",
        "command-path-trust-boundaries",
        "operation-inventory-parity",
        "no-caller-output-path",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "release-authorization": {
        "canonical-absolute-paths",
        "authorization-time-order",
        "one-shot-authorization-state",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "handoff-authorization": {
        "source-destination-fingerprints-differ",
        "one-shot-authorization-state",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "trusted-observation": {
        "canonical-absolute-paths",
        "observation-time-order",
        "one-shot-observation-state",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
}

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_RAW_AUTHORITY_KEYS = {
    "capability",
    "capabilitynonce",
    "nonce",
    "rawcapability",
    "rawnonce",
}
_CALLER_OUTPUT_KEYS = {"outputpath", "resultpath"}
_PATH_KEYS = {
    "repositoryRoot",
    "stateHome",
    "configPath",
    "worktreePath",
    "workerResultPath",
    "preparedIterationRef",
    "capabilityRef",
    "leaseCapabilityRef",
    "autonomousCapabilityRef",
    "reservationControlRef",
    "cleanupAuthorizationRef",
    "releaseAuthorizationRef",
    "mutationAuthorizationRef",
    "trustedObservationRef",
    "sourcePath",
    "destinationPath",
    "authorizationRef",
    "observationRef",
    "resultRef",
    "normalizedCommonDir",
    "executable",
    "pythonExecutable",
    "powerShellExecutable",
    "gitExecutable",
    "ghExecutable",
    "workerWrapper",
}


class ContractValidationError(ValueError):
    """A schema or runtime-only contract rule was violated."""


def _references_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "references"


def load_schema(name: str) -> dict[str, Any]:
    """Read one canonical schema by contract name."""

    filename = SCHEMA_FILENAMES.get(name)
    if filename is None:
        raise ContractValidationError(f"Unknown supervisor contract: {name}")
    path = _references_dir() / filename
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractValidationError(f"Cannot read supervisor schema: {filename}") from exc
    if not isinstance(value, dict):
        raise ContractValidationError(f"Supervisor schema is not an object: {filename}")
    return value


def _type_matches(expected: str, value: Any) -> bool:
    return {
        "array": isinstance(value, list),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "null": value is None,
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
    }[expected]


def _validate_native(schema: Mapping[str, Any], value: Any, location: str = "$") -> None:
    expected = schema.get("type")
    if isinstance(expected, str) and not _type_matches(expected, value):
        raise ContractValidationError(f"{location} must be {expected}")
    if isinstance(expected, list) and not any(_type_matches(item, value) for item in expected):
        raise ContractValidationError(f"{location} has an invalid type")
    if "const" in schema and value != schema["const"]:
        raise ContractValidationError(f"{location} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractValidationError(f"{location} is outside the allowed vocabulary")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ContractValidationError(f"{location} is below the minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ContractValidationError(f"{location} is above the maximum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ContractValidationError(f"{location} is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ContractValidationError(f"{location} is too long")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ContractValidationError(f"{location} does not match its required pattern")
        if schema.get("format") == "uuid" and _UUID.fullmatch(value) is None:
            raise ContractValidationError(f"{location} must be a lowercase canonical UUID")
        if schema.get("format") == "date-time":
            _timestamp(value, location)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ContractValidationError(f"{location} contains too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ContractValidationError(f"{location} contains too many items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(encoded) != len(set(encoded)):
                raise ContractValidationError(f"{location} must contain unique items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_native(item_schema, item, f"{location}[{index}]")
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        missing = required - set(value)
        if missing:
            raise ContractValidationError(f"{location} lacks required fields: {', '.join(sorted(missing))}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ContractValidationError(f"{location} contains unknown fields: {', '.join(sorted(unknown))}")
        elif isinstance(schema.get("additionalProperties"), dict):
            for key in set(value) - set(properties):
                _validate_native(schema["additionalProperties"], value[key], f"{location}.{key}")
        for key, item in value.items():
            property_schema = properties.get(key)
            if isinstance(property_schema, dict):
                _validate_native(property_schema, item, f"{location}.{key}")
    if "oneOf" in schema:
        accepted = 0
        errors: list[Exception] = []
        for option in schema["oneOf"]:
            try:
                _validate_native(option, value, location)
                accepted += 1
            except ContractValidationError as exc:
                errors.append(exc)
        if accepted != 1:
            raise ContractValidationError(f"{location} must match exactly one contract variant") from (errors[0] if errors else None)


def _timestamp(value: str, location: str) -> datetime:
    if not value.endswith("Z"):
        raise ContractValidationError(f"{location} must be a UTC RFC3339 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractValidationError(f"{location} is not a valid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ContractValidationError(f"{location} must be UTC")
    return parsed


def _key_token(key: str) -> str:
    return re.sub(r"[^a-z]", "", key.casefold())


def _walk(value: Any, *, key: str | None = None):
    yield key, value
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _walk(child, key=child_key)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _canonical_absolute_path(value: str, location: str) -> Path:
    if not value or value != unicodedata.normalize("NFC", value):
        raise ContractValidationError(f"{location} must be a non-empty NFC path")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ContractValidationError(f"{location} contains a control character")
    normalized = os.path.normpath(value)
    # Authoritative state uses portable forward-slash absolute paths for
    # physical-worktree bindings, while public Windows commands commonly use
    # the native backslash spelling. Accept exactly either canonical spelling;
    # mixed separators, dot segments, duplicate separators, and traversal still
    # fail because neither representation equals the input.
    portable = normalized.replace("\\", "/")
    if not os.path.isabs(value) or value not in {normalized, portable}:
        raise ContractValidationError(f"{location} must be a canonical absolute path")
    return Path(os.path.realpath(os.path.abspath(value)))


def _contains(parent: Path, child: Path) -> bool:
    try:
        return os.path.commonpath([os.fspath(parent), os.fspath(child)]) == os.fspath(parent)
    except ValueError:
        return False


def _safe_relative_paths(values: Any, location: str) -> None:
    if not isinstance(values, list):
        raise ContractValidationError(f"{location} must be a list")
    casefolded: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value or value != value.strip():
            raise ContractValidationError(f"{location} contains an invalid path")
        if value != unicodedata.normalize("NFC", value) or "\\" in value or value.startswith("/"):
            raise ContractValidationError(f"{location} contains a non-canonical relative path")
        parts = value.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ContractValidationError(f"{location} contains traversal or an empty component")
        folded = value.casefold()
        if folded in casefolded:
            raise ContractValidationError(f"{location} contains a case-insensitive duplicate")
        casefolded.add(folded)


def _check_no_authority_leak(value: Mapping[str, Any], *, engine_command: bool) -> None:
    runtime = load_base_runtime()
    for key, item in _walk(value):
        if key is not None:
            token = _key_token(key)
            if token in _RAW_AUTHORITY_KEYS:
                raise ContractValidationError(f"Raw authority material is forbidden: {key}")
            if engine_command and token in _CALLER_OUTPUT_KEYS:
                raise ContractValidationError(f"Caller-selected output paths are forbidden: {key}")
        if isinstance(item, str) and runtime.redact_value(item) != item:
            raise ContractValidationError("Secret-like material is forbidden by the supervisor contract")


def _check_paths(value: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key, item in _walk(value):
        if key == "stateHome" and item == EXPECTED_BASE_VERSIONS["STATE_HOME_VERSION"]:
            continue
        if key in _PATH_KEYS and isinstance(item, str):
            paths[key] = _canonical_absolute_path(item, key)
        if key in {"writableRoots"} and isinstance(item, list):
            for index, child in enumerate(item):
                _canonical_absolute_path(child, f"{key}[{index}]")
    return paths


def _check_engine_command(value: Mapping[str, Any], paths: Mapping[str, Path]) -> None:
    if tuple(OPERATION_NAMES) != tuple(option["properties"]["operation"]["const"] for option in load_schema("engine-command")["oneOf"]):
        raise ContractValidationError("Engine command schema operation inventory drifted")
    repository_root = paths["repositoryRoot"]
    state_home = paths["stateHome"]
    if _contains(repository_root, state_home) or _contains(state_home, repository_root):
        raise ContractValidationError("State home and repository checkout must be disjoint")
    if "configPath" in paths and not _contains(repository_root, paths["configPath"]):
        raise ContractValidationError("configPath must stay beneath the verified repository root")
    if "workerResultPath" in paths and not (
        _contains(repository_root, paths["workerResultPath"])
        or _contains(state_home, paths["workerResultPath"])
    ):
        raise ContractValidationError(
            "workerResultPath must stay beneath the controller or contained issue worktree"
        )
    for key in (
        "preparedIterationRef",
        "leaseCapabilityRef",
        "autonomousCapabilityRef",
        "reservationControlRef",
        "cleanupAuthorizationRef",
        "releaseAuthorizationRef",
        "mutationAuthorizationRef",
        "trustedObservationRef",
    ):
        if key in paths and not _contains(state_home, paths[key]):
            raise ContractValidationError(f"{key} must stay beneath the verified state home")
    if "worktreePath" in paths and (
        paths["worktreePath"] != repository_root
        and not _contains(state_home, paths["worktreePath"])
    ):
        raise ContractValidationError(
            "worktreePath is outside the controller or contained issue-worktree roots"
        )
    # Handoff.sourcePath is a proposed editing source, not the controller
    # checkout. Execution binds it to the live reservation, workflow registry,
    # and (when present) persistent issue mapping under the shared mutex.
    # destinationPath is observed at execution time and must be a distinct
    # linked checkout of the same common Git repository. It is intentionally
    # allowed outside both controller and state roots so a canonical Handoff
    # can transfer to an ordinary sibling worktree.
    if "expectedPaths" in value:
        _safe_relative_paths(value["expectedPaths"], "expectedPaths")


def _check_runtime(name: str, value: Mapping[str, Any]) -> None:
    _check_no_authority_leak(value, engine_command=name == "engine-command")
    paths = _check_paths(value)
    if name == "engine-command":
        _check_engine_command(value, paths)
    if name in {"prepared-iteration", "release-authorization", "trusted-observation"}:
        state_home = paths["stateHome"]
        reference_keys = {
            "prepared-iteration": ("capabilityRef",),
            "release-authorization": ("authorizationRef",),
            "trusted-observation": ("observationRef",),
        }[name]
        for key in reference_keys:
            if not _contains(state_home, paths[key]):
                raise ContractValidationError(f"{key} must be engine-owned beneath stateHome")
    if name == "project-config":
        expected = {
            "basePackage": EXPECTED_BASE_VERSIONS["BASE_PACKAGE_VERSION"],
            "identity": EXPECTED_BASE_VERSIONS["IDENTITY_VERSION"],
            "stateHome": EXPECTED_BASE_VERSIONS["STATE_HOME_VERSION"],
            "registry": EXPECTED_BASE_VERSIONS["REGISTRY_VERSION"],
            "workDescriptor": EXPECTED_BASE_VERSIONS["WORK_DESCRIPTOR_VERSION"],
        }
        if value["baseVersions"] != expected:
            raise ContractValidationError("Project config base version bindings do not match SAAS-45")
        policy = value["scheduledPolicy"]
        if policy != {
            "sandboxMode": "workspace-write",
            "networkAccess": True,
            "approvalPolicy": "never",
            "profileComposition": "none",
        }:
            raise ContractValidationError("Scheduled policy must use the exact supported profile")
        vocabulary = json.dumps(value, sort_keys=True).casefold()
        if any(word in vocabulary for word in ("danger-full-access", "full-access", "beta-profile")):
            raise ContractValidationError("Danger/full/beta scheduled profiles are forbidden")
    if name in {"checkpoint", "worker-result"}:
        for key in ("artifactManifest", "changedPaths", "expectedPaths"):
            if key in value:
                _safe_relative_paths(value[key], key)
    if name == "checkpoint" and value["expectedPreviousStage"] == value["nextStage"]:
        raise ContractValidationError("Checkpoint must advance to a different stage")
    if name == "editing-reservation":
        identities = [item["reservationId"] for item in value["reservations"].values()]
        if len(identities) != len(set(identities)):
            raise ContractValidationError("Reservation IDs must be unique")
        if set(value["reservations"]) != set(identities):
            raise ContractValidationError("Reservation map keys must equal their reservationId")
    if name == "supervisor-state":
        repository = value["repository"]
        expected = {
            "basePackageVersion": EXPECTED_BASE_VERSIONS["BASE_PACKAGE_VERSION"],
            "identityVersion": EXPECTED_BASE_VERSIONS["IDENTITY_VERSION"],
            "stateHomeVersion": EXPECTED_BASE_VERSIONS["STATE_HOME_VERSION"],
            "registryVersion": EXPECTED_BASE_VERSIONS["REGISTRY_VERSION"],
            "workDescriptorVersion": EXPECTED_BASE_VERSIONS["WORK_DESCRIPTOR_VERSION"],
        }
        if any(repository[key] != expected_value for key, expected_value in expected.items()):
            raise ContractValidationError("Supervisor state base version bindings do not match SAAS-45")
        if any(
            operation_id != record.get("operationId")
            for operation_id, record in value["gateWorktrees"].items()
        ):
            raise ContractValidationError("Gate worktree keys must equal operationId")
    if name == "handoff-authorization":
        if value["sourceFingerprint"] == value["destinationFingerprint"]:
            raise ContractValidationError("Handoff source and destination fingerprints must differ")
    if name == "release-authorization":
        created = _timestamp(value["createdAt"], "createdAt")
        expires = _timestamp(value["expiresAt"], "expiresAt")
        if expires <= created:
            raise ContractValidationError("Authorization expiry must follow creation")
        consumed = value.get("consumedAt")
        if consumed is not None and _timestamp(consumed, "consumedAt") < created:
            raise ContractValidationError("Authorization consumption predates creation")
        if (value["status"] == "consumed") != (consumed is not None):
            raise ContractValidationError("Consumed authorization status/timestamp mismatch")
    if name == "trusted-observation":
        observed = _timestamp(value["observedAt"], "observedAt")
        expires = _timestamp(value["expiresAt"], "expiresAt")
        if expires <= observed:
            raise ContractValidationError("Trusted observation expiry must follow observation")
        consumed = value.get("consumedAt")
        if consumed is not None and _timestamp(consumed, "consumedAt") < observed:
            raise ContractValidationError("Observation consumption predates observation")
        if (value["status"] == "consumed") != (consumed is not None):
            raise ContractValidationError("Consumed observation status/timestamp mismatch")


def validate_contract(name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate native schema rules plus the complete runtime-parity inventory."""

    if not isinstance(value, Mapping):
        raise ContractValidationError("Supervisor contract value must be an object")
    schema = load_schema(name)
    _validate_native(schema, value)
    _check_runtime(name, value)
    return copy.deepcopy(dict(value))


def validate_engine_command(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return one exhaustive public EngineCommand request."""

    return validate_contract("engine-command", value)


def assert_runtime_parity() -> None:
    """Fail when schemas, runtime inventory, or public operation variants drift."""

    reference_dir = _references_dir()
    observed_files = {path.name for path in reference_dir.glob("*.schema.json")}
    expected_files = set(SCHEMA_FILENAMES.values())
    if observed_files != expected_files:
        missing = expected_files - observed_files
        extra = observed_files - expected_files
        raise ContractValidationError(
            f"Supervisor schema inventory drift; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if set(RUNTIME_CONSTRAINTS) != set(SCHEMA_FILENAMES):
        raise ContractValidationError("Runtime constraint inventory lacks a supervisor schema")
    for name in SCHEMA_FILENAMES:
        schema = load_schema(name)
        if schema.get("properties", {}).get("schemaVersion", {}).get("const") != CONTRACT_VERSION and name != "engine-command":
            raise ContractValidationError(f"{name} does not bind schemaVersion {CONTRACT_VERSION}")
        extension = schema.get("x-luchdom-runtimeParity")
        if not isinstance(extension, dict) or extension.get("version") != CONTRACT_VERSION:
            raise ContractValidationError(f"{name} lacks runtime parity metadata")
        if extension.get("runtimeValidator") != "scripts.contracts.validate_contract":
            raise ContractValidationError(f"{name} names the wrong runtime validator")
        constraints = extension.get("constraints")
        if not isinstance(constraints, list) or {
            item.get("id") for item in constraints if isinstance(item, dict)
        } != RUNTIME_CONSTRAINTS[name]:
            raise ContractValidationError(f"{name} runtime constraint inventory drifted")
    engine = load_schema("engine-command")
    operations = tuple(branch["properties"]["operation"]["const"] for branch in engine["oneOf"])
    if operations != OPERATION_NAMES or len(set(operations)) != 14:
        raise ContractValidationError("EngineCommand must contain the exhaustive ordered 14-operation union")
