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
MEMORY_SCHEMA_FILENAMES = {
    "repository-memory-record": "repository-memory-record.schema.json",
    "repository-memory-promotion": "repository-memory-promotion.schema.json",
    "repository-memory-commit": "repository-memory-commit.schema.json",
    "repository-memory-index": "repository-memory-index.schema.json",
    "repository-memory-query": "repository-memory-query.schema.json",
    "repository-memory-result": "repository-memory-result.schema.json",
    "repository-memory-context-envelope": "repository-memory-context-envelope.schema.json",
    "repository-memory-batch-request": "repository-memory-batch-request.schema.json",
    "repository-memory-promotion-result": "repository-memory-promotion-result.schema.json",
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
MEMORY_RUNTIME_CONSTRAINTS = {
    "repository-memory-record": {
        "canonical-digest-projections", "typed-assertion-parity",
        "lifecycle-cross-fields", "sorted-normalized-arrays",
        "safe-repository-paths", "no-secret-like-material",
    },
    "repository-memory-promotion": {
        "manifest-decision-cross-fields", "canonical-candidate-order",
        "distinct-curation-workflow", "canonical-digest-projections",
        "no-authority-fields", "no-secret-like-material",
    },
    "repository-memory-commit": {
        "canonical-digest-projections", "canonical-candidate-order",
        "complete-marker-owned-set", "safe-repository-paths",
        "no-secret-like-material",
    },
    "repository-memory-index": {
        "canonical-index-semantic-projection", "marker-owned-inputs-only",
        "graph-and-conflict-projection", "repository-binding",
        "no-secret-like-material",
    },
    "repository-memory-query": {
        "canonical-query-projection", "normalized-filters",
        "repository-binding", "no-callback-or-authority",
        "no-secret-like-material",
    },
    "repository-memory-result": {
        "whole-item-budgets", "canonical-result-accounting",
        "complete-provenance", "no-authority-fields",
        "no-secret-like-material",
    },
    "repository-memory-context-envelope": {
        "tool-role-untrusted-envelope", "canonical-context-escaping",
        "inclusive-sentinel-accounting", "authenticated-selector-invariance",
        "whole-item-budgets", "no-authority-from-memory",
    },
    "repository-memory-batch-request": {
        "canonical-digest-projections", "exact-authorization-binding",
        "canonical-candidate-order", "safe-repository-paths",
        "no-secret-like-material",
    },
    "repository-memory-promotion-result": {
        "canonical-digest-projections", "complete-marker-owned-set",
        "status-cross-fields", "no-authority-fields",
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
_MEMORY_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_ASSERTION_KEY = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+){0,7}$")
_SECRET_SEMANTIC_KEY = re.compile(r"(?:^|[._-])(?:token|secret|password|passwd|api[_-]?key|private[_-]?key|nonce)(?:$|[._-])", re.IGNORECASE)
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

    filename = SCHEMA_FILENAMES.get(name) or MEMORY_SCHEMA_FILENAMES.get(name)
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


def _validate_native(
    schema: Mapping[str, Any],
    value: Any,
    location: str = "$",
    *,
    root_schema: Mapping[str, Any] | None = None,
    resolving: frozenset[str] = frozenset(),
) -> None:
    root = schema if root_schema is None else root_schema
    reference = schema.get("$ref")
    if reference is not None:
        if not isinstance(reference, str) or not reference.startswith("#/"):
            raise ContractValidationError(
                f"{location} uses an unsupported non-local schema reference"
            )
        if reference in resolving:
            raise ContractValidationError(
                f"{location} contains a cyclic schema reference"
            )
        target: Any = root
        try:
            for token in reference[2:].split("/"):
                key = token.replace("~1", "/").replace("~0", "~")
                target = target[key]
        except (KeyError, TypeError) as exc:
            raise ContractValidationError(
                f"{location} references an unknown local schema definition"
            ) from exc
        if not isinstance(target, Mapping):
            raise ContractValidationError(
                f"{location} schema reference does not resolve to an object"
            )
        _validate_native(
            target, value, location, root_schema=root,
            resolving=resolving | {reference},
        )
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
                _validate_native(
                    item_schema, item, f"{location}[{index}]",
                    root_schema=root, resolving=resolving,
                )
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
                _validate_native(
                    schema["additionalProperties"], value[key], f"{location}.{key}",
                    root_schema=root, resolving=resolving,
                )
        for key, item in value.items():
            property_schema = properties.get(key)
            if isinstance(property_schema, dict):
                _validate_native(
                    property_schema, item, f"{location}.{key}",
                    root_schema=root, resolving=resolving,
                )
    if "oneOf" in schema:
        accepted = 0
        errors: list[Exception] = []
        for option in schema["oneOf"]:
            try:
                _validate_native(
                    option, value, location,
                    root_schema=root, resolving=resolving,
                )
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


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical bytes used by every repository-memory digest projection."""

    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContractValidationError("Value cannot be canonically serialized") from exc
    # JSON permits escaped lone surrogates; the memory contract deliberately does not.
    for _, item in _walk(value):
        if isinstance(item, str) and any(0xD800 <= ord(character) <= 0xDFFF for character in item):
            raise ContractValidationError("Repository memory rejects lone surrogate code points")
    return encoded.encode("utf-8")


def sha256_canonical(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def digest_projection(value: Mapping[str, Any], excluded_field: str) -> dict[str, Any]:
    projected = copy.deepcopy(dict(value))
    if excluded_field not in projected:
        raise ContractValidationError(f"Digest projection lacks {excluded_field}")
    projected.pop(excluded_field)
    return projected


def candidate_intent_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return digest_projection(value, "candidateIntentSha256")


def promotion_manifest_payload_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return digest_projection(value, "promotionManifestPayloadSha256")


def record_payload_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return digest_projection(value, "recordPayloadSha256")


def batch_commit_payload_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return digest_projection(value, "batchCommitPayloadSha256")


def promotion_batch_request_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return digest_projection(value, "promotionBatchRequestSha256")


def retrieval_query_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def retrieval_result_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def context_envelope_payload_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return digest_projection(value, "contextPayloadSha256")


def index_semantic_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    projected = digest_projection(value, "indexSemanticSha256")
    projected.pop("builtAt", None)
    return projected


def context_delivery_accounting_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(dict(value))
    accounting = projected.get("accounting")
    if not isinstance(accounting, dict):
        raise ContractValidationError("Context delivery lacks accounting")
    accounting["charactersUsed"] = "000000"
    accounting["bytesUsed"] = "000000"
    return projected


def _canonical_text(value: str, *, collapsed: bool = False) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ContractValidationError("Repository memory rejects lone surrogate code points")
    normalized = unicodedata.normalize("NFC", value)
    if collapsed:
        normalized = " ".join(normalized.strip().split())
    return normalized


def _memory_relative_path(value: str, location: str) -> None:
    if value != _canonical_text(value) or not value or "\\" in value or value.startswith("/"):
        raise ContractValidationError(f"{location} must be a canonical repository-relative path")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ContractValidationError(f"{location} contains traversal or an empty component")


def _sorted_unique(values: list[Any], key, location: str) -> None:
    keys = [key(item) for item in values]
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise ContractValidationError(f"{location} must be sorted and unique")


def _assert_digest(value: str, location: str) -> None:
    if _MEMORY_DIGEST.fullmatch(value) is None:
        raise ContractValidationError(f"{location} must be a canonical SHA-256 digest")


def _assert_memory_record(value: Mapping[str, Any]) -> None:
    expected_filename = f"{value['recordId']}.v{value['recordVersion']:04d}.json"
    if value["filename"] != expected_filename:
        raise ContractValidationError("Record filename does not match record identity/version")
    _sorted_unique(value["topics"], lambda item: item.casefold(), "topics")
    _sorted_unique(value["paths"], lambda item: item.casefold(), "paths")
    _sorted_unique(value["stages"], lambda item: item.casefold(), "stages")
    for location in ("topics", "stages"):
        if any(item != _canonical_text(item) or item != item.casefold() for item in value[location]):
            raise ContractValidationError(f"{location} must use lowercase NFC values")
    for path in value["paths"]:
        _memory_relative_path(path, "paths")
    work = value["work"]
    if work is not None:
        expected_work = {"workflowId", "workKey", "provider", "externalId"}
        if set(work) != expected_work or not all(isinstance(work[key], str) and work[key] for key in expected_work):
            raise ContractValidationError("Record work binding inventory is not exact")
    if set(value["freshness"]) != {"policy", "reviewAfter"} or value["freshness"]["policy"] != "digest-on-read":
        raise ContractValidationError("Freshness policy must be digest-on-read")
    if value["freshness"]["reviewAfter"] is not None:
        _timestamp(value["freshness"]["reviewAfter"], "freshness.reviewAfter")
    retention = value["retention"]
    if set(retention) != {"class", "reviewAt", "expiresAt"} or retention["class"] not in {"durable", "review-on", "expire-on"}:
        raise ContractValidationError("Retention inventory/class is invalid")
    if retention["class"] == "durable" and (retention["reviewAt"] is not None or retention["expiresAt"] is not None):
        raise ContractValidationError("Durable retention cannot carry dates")
    if retention["class"] == "review-on" and (retention["reviewAt"] is None or retention["expiresAt"] is not None):
        raise ContractValidationError("Review-on retention requires only reviewAt")
    if retention["class"] == "expire-on" and (retention["expiresAt"] is None or retention["reviewAt"] is not None):
        raise ContractValidationError("Expire-on retention requires only expiresAt")
    for key in ("reviewAt", "expiresAt"):
        if retention[key] is not None:
            _timestamp(retention[key], f"retention.{key}")
    provenance = value["provenance"]
    _sorted_unique(provenance, lambda item: item["id"], "provenance")
    provenance_by_id = {item["id"]: item for item in provenance}
    for source in provenance:
        _memory_relative_path(source["path"], "provenance.path")
        _assert_digest(source["sha256"], "provenance.sha256")
        if source["kind"] == "repository-source" and source["path"].startswith("docs-ai/"):
            raise ContractValidationError("Current repository sources cannot be docs-ai artifacts")
        if source["kind"] != "repository-source" and not source["path"].startswith("docs-ai/"):
            raise ContractValidationError("Delivery evidence must remain under docs-ai")
    assertions = value["assertions"]
    _sorted_unique(assertions, lambda item: item["key"], "assertions")
    assertion_classes: list[str] = []
    for assertion in assertions:
        key = assertion["key"]
        if len(key) > 128 or _ASSERTION_KEY.fullmatch(key) is None:
            raise ContractValidationError("Assertion key is not canonical")
        if _SECRET_SEMANTIC_KEY.search(key):
            raise ContractValidationError("Assertion key is secret-like")
        refs = assertion["provenanceRefs"]
        _sorted_unique(refs, lambda item: item, "assertion provenanceRefs")
        if any(ref not in provenance_by_id for ref in refs):
            raise ContractValidationError("Assertion references unknown provenance")
        kind = assertion["valueType"]
        item = assertion["value"]
        if kind == "string":
            if not isinstance(item, str) or item != _canonical_text(item, collapsed=True) or not item:
                raise ContractValidationError("Assertion string is not normalized")
        elif kind == "integer":
            if isinstance(item, bool) or not isinstance(item, int) or abs(item) > 9007199254740991:
                raise ContractValidationError("Assertion integer is outside the safe range")
        elif kind == "boolean":
            if not isinstance(item, bool):
                raise ContractValidationError("Assertion boolean must be native JSON boolean")
        elif kind == "string-set":
            if not isinstance(item, list) or not item:
                raise ContractValidationError("Assertion string-set must be non-empty")
            if any(not isinstance(member, str) or member != _canonical_text(member, collapsed=True) or not member for member in item):
                raise ContractValidationError("Assertion string-set member is not normalized")
            _sorted_unique(item, lambda member: member, "assertion string-set")
        source_kinds = {provenance_by_id[ref]["kind"] for ref in refs}
        if source_kinds == {"repository-source"}:
            assertion_classes.append("current-source-bound")
        elif "repository-source" in source_kinds and any(kind != "repository-source" for kind in source_kinds):
            assertion_classes.append("source-evidence-bound")
        elif source_kinds == {"legacy-delivery-artifact"}:
            assertion_classes.append("legacy-evidence-bound")
        else:
            raise ContractValidationError("Assertion provenance topology is unsupported")
    lifecycle = value["lifecycle"]
    if lifecycle == "active":
        if not value["title"] or not value["summary"] or not assertions:
            raise ContractValidationError("Active memory requires display content and assertions")
        priority = {"current-source-bound": 2, "source-evidence-bound": 1, "legacy-evidence-bound": 0}
        expected_confidence = min(assertion_classes, key=priority.__getitem__)
        if value["confidence"] != expected_confidence:
            raise ContractValidationError("Record confidence is not its weakest assertion topology")
        if value["archiveReason"] is not None or value["redactionReason"] is not None:
            raise ContractValidationError("Active memory contains terminal lifecycle reasons")
    elif lifecycle == "archived":
        if value["summary"] is not None or assertions or not value["archiveReason"] or value["redactionReason"] is not None:
            raise ContractValidationError("Archived memory must be content-free except its safe title/reason")
        if value["confidence"] != "not-applicable":
            raise ContractValidationError("Archived confidence must be not-applicable")
    else:
        if value["title"] is not None or value["summary"] is not None or assertions or not value["redactionReason"] or value["archiveReason"] is not None:
            raise ContractValidationError("Redacted memory must be content-free")
        if value["confidence"] != "not-applicable":
            raise ContractValidationError("Redacted confidence must be not-applicable")
    if value["recordVersion"] == 1 and value["supersedes"] and len(value["supersedes"]) < 2:
        raise ContractValidationError("Version-one consolidation requires two to eight predecessors")
    if value["recordVersion"] > 1:
        expected = [{"recordId": value["recordId"], "recordVersion": value["recordVersion"] - 1}]
        if value["supersedes"] != expected:
            raise ContractValidationError("Later record versions must supersede the immediate predecessor")
    if value["restores"] is not None and value["lifecycle"] != "active":
        raise ContractValidationError("Only an active successor may restore an archive")
    if value["updatedBy"]["promotionManifestPayloadSha256"] != value["promotionManifestPayloadSha256"]:
        raise ContractValidationError("Update evidence differs from manifest binding")
    if value["updatedBy"]["candidatePromotionId"] != value["candidatePromotionId"]:
        raise ContractValidationError("Update identity differs from candidate promotion")
    if value["recordVersion"] == 1 and value["createdBy"] != value["updatedBy"]:
        raise ContractValidationError("Version-one creation/update identities must be equal")
    expected = sha256_canonical(record_payload_projection(value))
    if value["recordPayloadSha256"] != expected:
        raise ContractValidationError("Record payload digest mismatch")


def _assert_memory_promotion(value: Mapping[str, Any]) -> None:
    candidates = value["candidates"]
    if value["decision"] == "no-candidates":
        if candidates or not value["noCandidatesReason"] or value["noCandidatesSummary"] is None:
            raise ContractValidationError("No-candidates decision is incomplete")
    else:
        if not 1 <= len(candidates) <= 32 or value["noCandidatesReason"] is not None or value["noCandidatesSummary"] is not None:
            raise ContractValidationError("Promotion-approved decision requires one to 32 candidates")
    _sorted_unique(candidates, lambda item: item.get("candidateId", ""), "manifest candidates")
    promotion_ids: set[str] = set()
    targets: set[str] = set()
    for candidate in candidates:
        allowed_candidate = {
            "candidateId", "candidatePromotionId", "targetRecordId",
            "targetRecordVersion", "targetPath", "kind", "topics", "paths",
            "stages", "work", "title", "summary", "assertions", "provenance",
            "confidence", "freshness", "lifecycle", "retention", "supersedes",
            "restores", "createdAt", "reviewedAt", "archiveReason",
            "redactionReason", "candidateIntentSha256",
        }
        if set(candidate) != allowed_candidate:
            raise ContractValidationError("Manifest candidate field inventory is not exact")
        required = {"candidateId", "candidatePromotionId", "targetRecordId", "targetRecordVersion", "targetPath", "candidateIntentSha256"}
        if not required <= set(candidate):
            raise ContractValidationError("Manifest candidate identity is incomplete")
        if _UUID.fullmatch(candidate["candidateId"]) is None or _UUID.fullmatch(candidate["candidatePromotionId"]) is None:
            raise ContractValidationError("Manifest candidate IDs must be canonical UUIDs")
        _memory_relative_path(candidate["targetPath"], "candidate.targetPath")
        expected = f"docs/repository-memory/records/{candidate['targetRecordId']}.v{candidate['targetRecordVersion']:04d}.json"
        if candidate["targetPath"] != expected:
            raise ContractValidationError("Manifest target path does not match identity/version")
        if candidate["candidatePromotionId"] in promotion_ids or candidate["targetPath"].casefold() in targets:
            raise ContractValidationError("Manifest candidate promotion IDs/targets must be unique")
        promotion_ids.add(candidate["candidatePromotionId"])
        targets.add(candidate["targetPath"].casefold())
        if candidate["candidateIntentSha256"] != sha256_canonical(candidate_intent_projection(candidate)):
            raise ContractValidationError("Candidate intent digest mismatch")
        # Candidate intent is the record payload source. Validate every nested
        # type, lifecycle field, assertion, and provenance object now rather
        # than deferring shape enforcement until repository preparation.
        from .repository_memory_records import candidate_to_record
        try:
            candidate_to_record(value, candidate)
        except Exception as exc:
            raise ContractValidationError(f"Manifest candidate payload is invalid: {exc}") from exc
    if value["promotionManifestPayloadSha256"] != sha256_canonical(promotion_manifest_payload_projection(value)):
        raise ContractValidationError("Promotion manifest payload digest mismatch")


def _assert_promotion_batch_request(value: Mapping[str, Any]) -> None:
    required = {
        "schemaVersion", "batchPromotionId", "manifestPath",
        "promotionManifestPayloadSha256", "promotionManifestFileSha256",
        "markerTargetPath", "candidates", "expectedPriorIndexSemanticSha256",
        "repositoryId", "repositoryKey", "headSha",
        "physicalWorktreeFingerprint", "authorization",
        "promotionBatchRequestSha256",
    }
    if set(value) != required or value.get("schemaVersion") != "1.0":
        raise ContractValidationError("Promotion batch request inventory is not exact")
    candidate_keys = {"candidateId", "candidatePromotionId", "recordTargetPath", "candidateIntentSha256"}
    if not isinstance(value["candidates"], list) or not 1 <= len(value["candidates"]) <= 32:
        raise ContractValidationError("Promotion batch request candidate cardinality is invalid")
    if any(set(item) != candidate_keys for item in value["candidates"]):
        raise ContractValidationError("Promotion batch request candidate inventory is not exact")
    authorization_keys = {"authorizationId", "operationId", "authorizationSha256", "scope"}
    if set(value["authorization"]) != authorization_keys:
        raise ContractValidationError("Promotion batch authorization inventory is not exact")
    expected_marker = f"docs/repository-memory/commits/{value['batchPromotionId']}.json"
    expected_scope = sorted(
        [item["recordTargetPath"] for item in value["candidates"]] + [expected_marker],
        key=str.casefold,
    )
    if (
        value["markerTargetPath"] != expected_marker
        or value["authorization"]["operationId"] != value["batchPromotionId"]
        or value["authorization"]["scope"] != expected_scope
    ):
        raise ContractValidationError("Promotion batch authorization binding is not exact")
    if value["promotionBatchRequestSha256"] != sha256_canonical(promotion_batch_request_projection(value)):
        raise ContractValidationError("Promotion batch request digest mismatch")
    _check_no_authority_leak(value, engine_command=False)


def validate_promotion_batch_request(value: Mapping[str, Any]) -> dict[str, Any]:
    return validate_contract("repository-memory-batch-request", value)


def _assert_promotion_result(value: Mapping[str, Any]) -> None:
    if value.get("status") == "no-candidates":
        required = {"schemaVersion", "status", "batchPromotionId", "promotionManifestPayloadSha256", "promotionManifestFileSha256", "records"}
        if set(value) != required or value["records"]:
            raise ContractValidationError("No-candidates result inventory is invalid")
    else:
        required = {
            "schemaVersion", "status", "batchPromotionId",
            "promotionBatchRequestSha256", "promotionManifestPayloadSha256",
            "promotionManifestFileSha256", "batchCommitPayloadSha256",
            "batchCommitFileSha256", "records", "indexSemanticSha256",
        }
        if set(value) != required or value["status"] not in {"committed", "index-reconstruction-required"}:
            raise ContractValidationError("Promotion result inventory/status is invalid")
        member_keys = {"candidateId", "candidatePromotionId", "targetPath", "candidateIntentSha256", "recordPayloadSha256", "recordFileSha256", "outcome"}
        if not isinstance(value["records"], list) or not value["records"] or any(set(item) != member_keys or item["outcome"] != "promoted" for item in value["records"]):
            raise ContractValidationError("Promotion result record inventory is invalid")
    _check_no_authority_leak(value, engine_command=False)


def validate_promotion_result(value: Mapping[str, Any]) -> dict[str, Any]:
    return validate_contract("repository-memory-promotion-result", value)


def _assert_memory_commit(value: Mapping[str, Any]) -> None:
    records = value["records"]
    _sorted_unique(records, lambda item: item["candidateId"], "commit records")
    targets = [item["targetPath"].casefold() for item in records]
    promotions = [item["candidatePromotionId"] for item in records]
    if len(targets) != len(set(targets)) or len(promotions) != len(set(promotions)):
        raise ContractValidationError("Commit marker owns duplicate targets or promotions")
    for item in records:
        _memory_relative_path(item["targetPath"], "commit targetPath")
        if not item["targetPath"].startswith("docs/repository-memory/records/"):
            raise ContractValidationError("Commit marker target is outside the fixed record root")
    if value["batchCommitPayloadSha256"] != sha256_canonical(batch_commit_payload_projection(value)):
        raise ContractValidationError("Batch commit payload digest mismatch")


def _assert_memory_index(value: Mapping[str, Any]) -> None:
    if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value["sourceTree"]) is None:
        raise ContractValidationError("Index source-tree identity must be an exact Git SHA")
    _sorted_unique(value["markers"], lambda item: item.get("path", ""), "index markers")
    _sorted_unique(value["entries"], lambda item: (item.get("recordId", ""), item.get("recordVersion", 0), item.get("filename", "")), "index entries")
    marker_keys = {"path", "batchPromotionId", "payloadSha256", "fileSha256"}
    if any(set(item) != marker_keys for item in value["markers"]):
        raise ContractValidationError("Index marker inventory is not exact")
    entry_keys = {
        "recordId", "recordVersion", "filename", "path", "recordFileSha256",
        "recordPayloadSha256", "markerPath", "markerPayloadSha256", "kind",
        "topics", "paths", "stages", "work", "confidence", "lifecycle",
        "superseded", "successor", "invalidGraph", "conflictKeys", "expired",
        "reviewDue", "stale", "staleReasons", "freshnessState",
        "duplicateRepresentative", "duplicateMembers", "provenanceSha256",
        "assertionMapSha256",
    }
    if any(set(item) != entry_keys for item in value["entries"]):
        raise ContractValidationError("Index entry inventory is not exact")
    for mapping_name in ("diagnostics", "counts"):
        if not isinstance(value[mapping_name], dict) or any(
            not isinstance(key, str) or not key or isinstance(item, bool)
            or not isinstance(item, int) or item < 0
            for key, item in value[mapping_name].items()
        ):
            raise ContractValidationError(f"Index {mapping_name} inventory is invalid")
    if value["indexSemanticSha256"] != sha256_canonical(index_semantic_projection(value)):
        raise ContractValidationError("Index semantic digest mismatch")


def _assert_memory_query(value: Mapping[str, Any]) -> None:
    _sorted_unique(value["paths"], lambda item: item.casefold(), "query paths")
    _sorted_unique(value["topics"], lambda item: item.casefold(), "query topics")
    for path in value["paths"]:
        _memory_relative_path(path, "query path")
    if any(item != _canonical_text(item) or item != item.casefold() or not item for item in value["topics"]):
        raise ContractValidationError("Query topics must be lowercase NFC values")
    if value["stage"] is not None and (value["stage"] != value["stage"].casefold() or value["stage"] != _canonical_text(value["stage"])):
        raise ContractValidationError("Query stage must be lowercase NFC")


def _assert_memory_result(value: Mapping[str, Any]) -> None:
    item_keys = {
        "recordId", "recordVersion", "kind", "title", "summary", "assertions",
        "confidence", "provenance", "recordPayloadSha256", "recordFileSha256",
        "rank", "duplicateProvenance",
    }
    if any(set(item) != item_keys for item in value["items"]):
        raise ContractValidationError("Retrieval item inventory is not exact")
    if not isinstance(value["diagnostics"], dict) or any(
        not isinstance(key, str) or isinstance(item, bool) or not isinstance(item, int) or item < 0
        for key, item in value["diagnostics"].items()
    ):
        raise ContractValidationError("Retrieval diagnostics inventory is invalid")
    items_bytes = canonical_json_bytes(value["items"])
    if value["accounting"]["recordsUsed"] != len(value["items"]):
        raise ContractValidationError("Retrieval item accounting mismatch")
    if value["accounting"]["charactersUsed"] != len(items_bytes.decode("utf-8")):
        raise ContractValidationError("Retrieval character accounting mismatch")
    if value["accounting"]["bytesUsed"] != len(canonical_json_bytes(value)):
        raise ContractValidationError("Retrieval byte accounting mismatch")


def _assert_memory_context(value: Mapping[str, Any]) -> None:
    if value["developer"]["role"] != "developer" or value["tool"] != {**value["tool"], "role": "tool", "name": "repository_memory_context"}:
        raise ContractValidationError("Context delivery roles are not fixed")
    projection = context_delivery_accounting_projection(value)
    encoded = canonical_json_bytes(projection)
    characters = len(encoded.decode("utf-8"))
    byte_count = len(encoded)
    expected_characters = f"{characters:06d}"
    expected_bytes = f"{byte_count:06d}"
    if value["accounting"]["charactersUsed"] != expected_characters or value["accounting"]["bytesUsed"] != expected_bytes:
        raise ContractValidationError("Context delivery inclusive accounting invariant failed")
    final = canonical_json_bytes(value)
    if len(final.decode("utf-8")) != characters or len(final) != byte_count:
        raise ContractValidationError("Context sentinel substitution changed serialized length")


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
    if name == "repository-memory-record":
        _assert_memory_record(value)
    if name == "repository-memory-promotion":
        _assert_memory_promotion(value)
    if name == "repository-memory-commit":
        _assert_memory_commit(value)
    if name == "repository-memory-index":
        _assert_memory_index(value)
    if name == "repository-memory-query":
        _assert_memory_query(value)
    if name == "repository-memory-result":
        _assert_memory_result(value)
    if name == "repository-memory-context-envelope":
        _assert_memory_context(value)
    if name == "repository-memory-batch-request":
        _assert_promotion_batch_request(value)
    if name == "repository-memory-promotion-result":
        _assert_promotion_result(value)


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
    schemas = {**SCHEMA_FILENAMES, **MEMORY_SCHEMA_FILENAMES}
    constraints_by_name = {**RUNTIME_CONSTRAINTS, **MEMORY_RUNTIME_CONSTRAINTS}
    expected_files = set(schemas.values())
    if observed_files != expected_files:
        missing = expected_files - observed_files
        extra = observed_files - expected_files
        raise ContractValidationError(
            f"Supervisor schema inventory drift; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if set(constraints_by_name) != set(schemas):
        raise ContractValidationError("Runtime constraint inventory lacks a supervisor schema")
    for name in schemas:
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
        } != constraints_by_name[name]:
            raise ContractValidationError(f"{name} runtime constraint inventory drifted")
    engine = load_schema("engine-command")
    operations = tuple(branch["properties"]["operation"]["const"] for branch in engine["oneOf"])
    if operations != OPERATION_NAMES or len(set(operations)) != 20:
        raise ContractValidationError("EngineCommand must contain the exhaustive ordered 20-operation union")
