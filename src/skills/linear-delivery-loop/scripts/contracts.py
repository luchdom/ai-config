"""Dependency-free runtime validation for the versioned supervisor contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .base_runtime import EXPECTED_BASE_VERSIONS, load_base_runtime


CONTRACT_VERSION = "1.0"
CONTRACT_VERSIONS = {"control-plane-state": "1.1"}
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
    "PreparePublication",
    "PublicationProvider",
    "PublicationGate",
    "RecordPublicationAttestation",
    "PublicationRepair",
    "RecoverPublication",
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
    "tracking-config": "tracking-config.schema.json",
    "control-plane-state": "control-plane-state.schema.json",
    "migration-report": "migration-report.schema.json",
    "publication-state": "publication-state.schema.json",
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
    "tracking-config": {
        "tracking-identifier-only-configuration",
        "no-secret-like-material",
    },
    "control-plane-state": {
        "canonical-record-identities",
        "no-raw-capability-or-nonce",
        "no-secret-like-material",
    },
    "migration-report": {
        "mutation-free-report-shape",
        "no-secret-like-material",
    },
    "publication-state": {
        "immutable-operation-and-head",
        "initial-plus-three-retries",
        "complete-preserved-state",
        "redacted-provider-evidence",
        "bounded-evidence-and-repair",
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
    "publicationStateRef",
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


def _stable_record_id(kind: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{kind}-{digest}"


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
    if "publicationStateRef" in paths and not (
        _contains(repository_root, paths["publicationStateRef"])
        or _contains(state_home, paths["publicationStateRef"])
    ):
        raise ContractValidationError(
            "publicationStateRef must stay beneath the repository or state home"
        )
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
    if name == "tracking-config":
        expected_top = {
            "schemaVersion", "controlPlaneVersion", "supervisorVersion",
            "repositoryKey", "workspace", "team", "project", "owner",
            "states", "labels", "linear", "ntfy",
        }
        if set(value) != expected_top:
            raise ContractValidationError("Tracking configuration inventory is not exact")
        for key in ("workspace", "project", "owner"):
            if set(value[key]) != {"id", "name"} or not all(
                isinstance(item, str) and item for item in value[key].values()
            ):
                raise ContractValidationError(f"Tracking {key} identity is malformed")
        if set(value["team"]) != {"id", "key"}:
            raise ContractValidationError("Tracking team identity is malformed")
        expected_states = {"backlog", "todo", "inProgress", "inReview", "done"}
        expected_labels = {
            "autonomous", "needsRefinement", "needsHuman", "externalIntegration", "stop"
        }
        if set(value["states"]) != expected_states or set(value["labels"]) != expected_labels:
            raise ContractValidationError("Tracking state/label inventory is not exact")
        observed_ids: list[str] = []
        for group in ("states", "labels"):
            for identity in value[group].values():
                if set(identity) != {"id", "name"} or not all(
                    isinstance(item, str) and item for item in identity.values()
                ):
                    raise ContractValidationError(f"Tracking {group} identity is malformed")
                observed_ids.append(identity["id"])
        observed_ids.extend(
            [value["workspace"]["id"], value["team"]["id"], value["project"]["id"], value["owner"]["id"]]
        )
        if len(observed_ids) != len(set(observed_ids)):
            raise ContractValidationError("Tracking provider identifiers must be unique")
        if value["team"]["key"] != "SAAS":
            raise ContractValidationError("Tracking configuration must bind the SAAS team")
        if value["linear"]["apiKeyEnvironmentVariable"] != "LINEAR_API_KEY":
            raise ContractValidationError("Linear credentials must resolve from LINEAR_API_KEY")
        serialized = json.dumps(value, sort_keys=True).casefold()
        if any(token in serialized for token in ('"token":', '"apikey":', '"secret":')):
            raise ContractValidationError("Tracking configuration contains credential material")
    if name == "control-plane-state":
        all_ids: list[str] = []
        for collection in (
            "decisions",
            "publicationRequests",
            "followUps",
            "attentionEvents",
            "notifications",
            "selectionClaims",
        ):
            records = value[collection]
            identities = [record["id"] for record in records]
            if len(identities) != len(set(identities)):
                raise ContractValidationError(f"{collection} contains duplicate record IDs")
            all_ids.extend(identities)
            for record in records:
                if _timestamp(record["createdAt"], "createdAt") < _timestamp(
                    record["sourceTimestamp"], "sourceTimestamp"
                ):
                    raise ContractValidationError("Control-plane record predates its source")
        if len(all_ids) != len(set(all_ids)):
            raise ContractValidationError("Control-plane record IDs collide across collections")
        for record in value["decisions"]:
            data = record["data"]
            expected_id = _stable_record_id(
                "decision", record["issueId"], record["sourceTimestamp"],
                record["summary"], data["ownerId"], data["configDigest"],
                data["repositoryId"]
            )
            option_ids = [item["id"] for item in data["options"]]
            if record["id"] != expected_id or len(option_ids) != len(set(option_ids)):
                raise ContractValidationError("Decision identity or options are non-canonical")
            if data["recommendation"] not in option_ids:
                raise ContractValidationError("Decision recommendation is not an option")
            expected_syntax = f"DECIDE {record['id']} <{'|'.join(option_ids)}>"
            if data["replySyntax"] != expected_syntax:
                raise ContractValidationError("Decision reply syntax is non-canonical")
            consumed = data["consumedReplyId"] is not None
            if consumed != (data["consumedReplyTimestamp"] is not None):
                raise ContractValidationError("Decision consumption evidence is incomplete")
            if (record["status"] == "consumed") != consumed:
                raise ContractValidationError("Decision consumption marker/status mismatch")
            if consumed and data.get("selectedOption") not in option_ids:
                raise ContractValidationError("Consumed decision lacks a valid selected option")
            if not consumed and "selectedOption" in data:
                raise ContractValidationError("Pending decision contains a selected option")
            if consumed and _timestamp(
                data["consumedReplyTimestamp"], "consumedReplyTimestamp"
            ) <= _timestamp(record["sourceTimestamp"], "sourceTimestamp"):
                raise ContractValidationError("Decision reply does not follow its source")
        for record in value["publicationRequests"]:
            data = record["data"]
            expected_id = _stable_record_id(
                "publication", record["issueId"], data["operationId"],
                data["headSha"], data["ownerId"], data["configDigest"],
                data["repositoryId"]
            )
            if record["id"] != expected_id:
                raise ContractValidationError("Publication request identity is non-canonical")
            expected_syntax = f"RETRY-PUBLICATION {data['operationId']} {data['headSha']}"
            if data["replySyntax"] != expected_syntax:
                raise ContractValidationError("Publication reply syntax is non-canonical")
            consumed = data["consumedReplyId"] is not None
            if consumed != (data["consumedReplyTimestamp"] is not None):
                raise ContractValidationError("Publication consumption evidence is incomplete")
            if (record["status"] == "authorized") != consumed:
                raise ContractValidationError("Publication consumption marker/status mismatch")
            lower_bound = _timestamp(
                data["lastConsumedReplyTimestamp"], "lastConsumedReplyTimestamp"
            )
            if lower_bound < _timestamp(record["sourceTimestamp"], "sourceTimestamp"):
                raise ContractValidationError("Publication reply lower bound predates its source")
            if consumed and _timestamp(
                data["consumedReplyTimestamp"], "consumedReplyTimestamp"
            ) <= _timestamp(record["sourceTimestamp"], "sourceTimestamp"):
                raise ContractValidationError("Publication reply does not follow its source")
            if consumed and data["consumedReplyTimestamp"] != data["lastConsumedReplyTimestamp"]:
                raise ContractValidationError("Publication active reply differs from its durable lower bound")
            evidence_keys = {"issueState", "reservationId", "worktreePath", "branch", "prId"}
            if set(data["evidence"]) != evidence_keys:
                raise ContractValidationError("Publication evidence inventory is incomplete")
        source_records: dict[str, Mapping[str, Any]] = {}
        for collection in ("decisions", "publicationRequests", "followUps"):
            source_records.update({item["id"]: item for item in value[collection]})
        for record in value["followUps"]:
            data = record["data"]
            if record["kind"] in {"needs-refinement", "external-integration"}:
                if data["proposalType"] == "external-prerequisite":
                    expected_id = _stable_record_id(
                        "followup", record["issueId"], record["sourceTimestamp"], record["summary"]
                    )
                    if record["kind"] != "external-integration":
                        raise ContractValidationError("External prerequisite has the wrong kind")
                else:
                    expected_id = _stable_record_id(
                        "proposal", record["issueId"], record["sourceTimestamp"],
                        record["summary"], record["kind"]
                    )
                if data["proposedState"] != "Backlog" or data["proposedLabel"] != record["kind"]:
                    raise ContractValidationError("Follow-up proposal fields are inconsistent")
            else:
                expected_id = _stable_record_id(
                    "failure", record["issueId"], record["kind"], data["sourceId"]
                )
            if record["id"] != expected_id:
                raise ContractValidationError("Follow-up/failure identity is non-canonical")
        expected_attention: dict[str, str | None] = {
            record["id"]: "needs-human" for record in value["decisions"]
        }
        expected_attention.update(
            {record["id"]: "publication-refusal" for record in value["publicationRequests"]}
        )
        for record in value["followUps"]:
            if record["kind"] == "external-integration":
                expected_attention[record["id"]] = (
                    "external-blocker"
                    if record["data"]["proposalType"] == "external-prerequisite"
                    else None
                )
            elif record["kind"] == "needs-refinement":
                expected_attention[record["id"]] = None
            elif record["kind"] == "reconciliation-failure":
                expected_attention[record["id"]] = "multiple-wip"
            else:
                expected_attention[record["id"]] = record["kind"]
        attention_by_source: dict[str, list[Mapping[str, Any]]] = {}
        for record in value["attentionEvents"]:
            source_id = record["data"]["sourceId"]
            attention_by_source.setdefault(source_id, []).append(record)
            source = source_records.get(source_id)
            required_kind = expected_attention.get(source_id)
            if source is None or required_kind is None or record["kind"] != required_kind:
                raise ContractValidationError("Attention event has an invalid source taxonomy")
            expected_id = _stable_record_id(
                "attention", source["issueId"], required_kind, source_id
            )
            if record["id"] != expected_id or any(
                record[key] != source[key]
                for key in ("issueId", "sourceTimestamp", "link", "summary")
            ):
                raise ContractValidationError("Attention event metadata differs from its source")
        for source_id, required_kind in expected_attention.items():
            count = len(attention_by_source.get(source_id, []))
            if count != (1 if required_kind is not None else 0):
                raise ContractValidationError("Source attention cardinality violates its taxonomy")
        attention = {item["id"]: item for item in value["attentionEvents"]}
        for record in value["notifications"]:
            data = record["data"]
            if data["eventId"] not in attention:
                raise ContractValidationError("Notification lacks its attention event")
            event = attention[data["eventId"]]
            if any(
                record[key] != event[key]
                for key in ("issueId", "sourceTimestamp", "link", "summary")
            ):
                raise ContractValidationError("Notification metadata differs from its attention source")
            if record["id"] != _stable_record_id("notification", data["eventId"]):
                raise ContractValidationError("Notification identity is non-canonical")
            if data["attemptId"] != _stable_record_id("attempt", data["eventId"]):
                raise ContractValidationError("Notification attempt identity is non-canonical")
            terminal = data["attemptState"] == "terminal"
            if terminal != (record["status"] in {"delivered", "failed"}):
                raise ContractValidationError("Notification attempt/status mismatch")
            if terminal != (data["completedAt"] is not None and data["outcome"] is not None):
                raise ContractValidationError("Notification completion evidence mismatch")
            if data["completedAt"] is not None and _timestamp(
                data["completedAt"], "completedAt"
            ) < _timestamp(record["createdAt"], "createdAt"):
                raise ContractValidationError("Notification completed before its attempt")
            if terminal and data["outcome"].get("status") != record["status"]:
                raise ContractValidationError("Notification outcome/status mismatch")
        for record in value["selectionClaims"]:
            data = record["data"]
            expected_id = _stable_record_id(
                "selection", record["issueId"], data["snapshotDigest"],
                data["configDigest"], data["repositoryId"]
            )
            if record["id"] != expected_id:
                raise ContractValidationError("Selection claim identity is non-canonical")
            bound = record["status"] in {
                "in-flight", "protected", "recovering", "consumed", "inert"
            }
            lease_bound = all(
                data[key] is not None for key in (
                    "operationId", "startedAt", "executionOwnerId",
                    "executionLeaseRevision", "executionLeaseExpiresAt",
                )
            )
            if bound != lease_bound:
                raise ContractValidationError("Selection operation binding/status mismatch")
            if data["startedAt"] is not None and _timestamp(
                data["startedAt"], "startedAt"
            ) < _timestamp(record["createdAt"], "createdAt"):
                raise ContractValidationError("Selection operation predates its claim")
            recovering = record["status"] == "recovering"
            recovery_bound = all(
                data[key] is not None for key in (
                    "recoveryOwnerId", "recoveryLeaseRevision",
                    "recoveryLeaseExpiresAt", "recoveryStartedAt", "recoveryProof"
                )
            )
            if recovering and not recovery_bound:
                raise ContractValidationError("Recovering selection lacks exclusive proof")
            if data["recoveryGeneration"] == 0 and recovery_bound:
                raise ContractValidationError("Selection recovery proof lacks a generation")
            if data["recoveryGeneration"] > 0 and data["recoveryProof"] is None:
                raise ContractValidationError("Selection recovery generation lacks durable proof")
            proof = data["recoveryProof"]
            if proof is not None:
                if (
                    proof["operationId"] != data["operationId"]
                    or proof["recoveryOwnerId"] != data["recoveryOwnerId"]
                    or proof["recoveryLeaseRevision"] != data["recoveryLeaseRevision"]
                    or proof["recoveryLeaseExpiresAt"] != data["recoveryLeaseExpiresAt"]
                    or proof["observedAt"] != data["recoveryStartedAt"]
                ):
                    raise ContractValidationError("Selection recovery proof is differently bound")
                if data["recoveryGeneration"] == 1 and (
                    proof["previousOwnerId"] != data["executionOwnerId"]
                    or proof["previousLeaseRevision"] != data["executionLeaseRevision"]
                    or proof["previousLeaseExpiresAt"] != data["executionLeaseExpiresAt"]
                ):
                    raise ContractValidationError("First recovery proof lacks execution binding")
                if proof["reason"] == "lease-expired" and _timestamp(
                    proof["previousLeaseExpiresAt"], "previousLeaseExpiresAt"
                ) > _timestamp(proof["observedAt"], "observedAt"):
                    raise ContractValidationError("Recovery lease had not expired")
            terminal = record["status"] in {"consumed", "inert"}
            if terminal != (data["terminalResult"] is not None):
                raise ContractValidationError("Selection terminal result/status mismatch")
            result = data["terminalResult"]
            if result is not None and (
                result["operationId"] != data["operationId"]
                or result["issueId"] != record["issueId"]
                or (record["status"] == "inert") != (result["status"] == "inert")
            ):
                raise ContractValidationError("Selection terminal result is differently bound")
    if name == "migration-report":
        identities = [record["issueId"] for record in value["issues"]]
        if len(identities) != len(set(identities)):
            raise ContractValidationError("Migration report contains duplicate issues")
    if name == "publication-state":
        from .publication_records import validate_publication_state

        validate_publication_state(value)


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
        expected_version = CONTRACT_VERSIONS.get(name, CONTRACT_VERSION)
        if schema.get("properties", {}).get("schemaVersion", {}).get("const") != expected_version and name != "engine-command":
            raise ContractValidationError(f"{name} does not bind schemaVersion {expected_version}")
        extension = schema.get("x-luchdom-runtimeParity")
        if not isinstance(extension, dict) or extension.get("version") != expected_version:
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
    if operations != OPERATION_NAMES or len(set(operations)) != 20:
        raise ContractValidationError("EngineCommand must contain the exhaustive ordered 20-operation union")
