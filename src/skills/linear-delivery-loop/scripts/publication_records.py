"""Strict records for deterministic publication and exact-SHA evidence.

The records in this module deliberately contain identities and redacted evidence only.
Provider clients, credentials, callbacks, and raw responses are never durable state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

PUBLICATION_VERSION = "1.0"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
ISSUE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,15}-[1-9][0-9]*$")
OPERATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
PUBLICATION_OPERATIONS = ("push", "pull-request", "squash-merge")
PUBLICATION_STATUSES = (
    "prepared", "attempting", "retry-wait", "paused", "pushed", "pr-open",
    "head-gated", "merge-ready", "succeeded", "merged",
    "post-merge-validating", "repairing", "base-drift", "completed",
)
REFUSAL_KINDS = (
    "rate-limit", "provider-unavailable", "temporary-mergeability", "permission",
    "required-check", "branch-protection", "ruleset", "merge-queue", "policy",
    "ambiguous", "unclassified",
)
EVIDENCE_KINDS = (
    "pre-staging-aggregate", "exact-head-aggregate", "review", "qa", "qa-reuse",
    "docs", "evidence-convergence", "merge-readback", "exact-merge-aggregate",
)
ATTESTATION_PRODUCERS = {
    "pre-staging-aggregate": "gate-runner",
    "exact-head-aggregate": "gate-runner", "exact-merge-aggregate": "gate-runner",
    "review": "code-reviewer", "qa": "qa", "qa-reuse": "qa",
    "docs": "docs", "evidence-convergence": "evidence-classifier",
    "merge-readback": "provider-readback",
}
BACKOFF_MINUTES = (5, 15, 30)


class PublicationRecordError(ValueError):
    """A publication record is incomplete, unsafe, or ambiguously bound."""


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def utc_timestamp(value: str, label: str = "timestamp") -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PublicationRecordError(f"{label} must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PublicationRecordError(f"{label} is invalid") from exc
    if parsed.tzinfo != timezone.utc:
        raise PublicationRecordError(f"{label} must be UTC")
    return value


def exact_sha(value: str, label: str = "SHA") -> str:
    if not isinstance(value, str) or SHA_PATTERN.fullmatch(value) is None:
        raise PublicationRecordError(f"{label} must be a lowercase full Git SHA")
    return value


def safe_relative_paths(values: list[str], label: str = "paths") -> list[str]:
    if not isinstance(values, list) or not values:
        raise PublicationRecordError(f"{label} must be a non-empty list")
    seen: set[str] = set()
    for value in values:
        if (
            not isinstance(value, str) or not value or value != value.strip()
            or "\\" in value or value.startswith("/") or "//" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
        ):
            raise PublicationRecordError(f"{label} contains an unsafe path")
        folded = value.casefold()
        if folded in seen:
            raise PublicationRecordError(f"{label} contains a duplicate path")
        seen.add(folded)
    return sorted(values)


def _exact_keys(value: Mapping[str, Any], required: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != required:
        raise PublicationRecordError(f"{label} field inventory is not exact")


def validate_preserved_state(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "issueState", "autonomous", "globalWip", "reservationId", "worktreePath",
        "physicalWorktreeFingerprint", "branch", "pullRequest", "evidenceRefs",
    }
    _exact_keys(value, required, "preserved state")
    if value["issueState"] not in {"In Progress", "In Review"}:
        raise PublicationRecordError("preserved issue state is not ordinary publication state")
    if value["issueState"] == "In Progress" and value["pullRequest"] is not None:
        raise PublicationRecordError("pre-PR state cannot preserve a pull request")
    if value["issueState"] == "In Review" and not isinstance(value["pullRequest"], Mapping):
        raise PublicationRecordError("post-PR state must preserve a pull request")
    if value["autonomous"] is not True or value["globalWip"] is not True:
        raise PublicationRecordError("publication recovery must preserve autonomous WIP")
    if not HASH_PATTERN.fullmatch(str(value["physicalWorktreeFingerprint"])):
        raise PublicationRecordError("physical worktree fingerprint is invalid")
    if not isinstance(value["evidenceRefs"], list):
        raise PublicationRecordError("evidence references must be a list")
    return copy.deepcopy(dict(value))


def validate_publication_state(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schemaVersion", "repositoryId", "repositoryKey", "workflowId", "issueId",
        "operationId", "idempotencyKey", "operation", "status", "branch", "baseRef",
        "headSha", "mergeSha", "pullRequest", "attemptCount", "retryCount",
        "nextRetryAt", "refusalKind", "providerEvidenceRef", "preservedState",
        "attestations", "evidenceFinalizationCount", "repairAttempt", "createdAt", "updatedAt",
        "consumedReplyId",
        "providerOperationIds",
        "activeProviderOperation", "authorityReadback", "baseSha",
        "preparation", "evidenceFinalization",
    }
    _exact_keys(value, required, "publication state")
    if value["schemaVersion"] != PUBLICATION_VERSION:
        raise PublicationRecordError("unsupported publication state version")
    if not ISSUE_PATTERN.fullmatch(str(value["issueId"])):
        raise PublicationRecordError("publication issue identity is invalid")
    if not OPERATION_PATTERN.fullmatch(str(value["operationId"])):
        raise PublicationRecordError("publication operation identity is invalid")
    if value["idempotencyKey"] != value["operationId"]:
        raise PublicationRecordError("idempotency key must equal immutable operation identity")
    if value["operation"] not in PUBLICATION_OPERATIONS or value["status"] not in PUBLICATION_STATUSES:
        raise PublicationRecordError("publication operation or status is invalid")
    exact_sha(value["headSha"], "headSha")
    exact_sha(value["baseSha"], "baseSha")
    if value["mergeSha"] is not None:
        exact_sha(value["mergeSha"], "mergeSha")
    if not isinstance(value["attemptCount"], int) or value["attemptCount"] < 0:
        raise PublicationRecordError("attemptCount is invalid")
    if not isinstance(value["retryCount"], int) or not 0 <= value["retryCount"] <= 3:
        raise PublicationRecordError("retryCount is invalid")
    allowed_attempts = {0} if value["status"] in {"prepared", "base-drift"} else {value["retryCount"] + 1}
    if value["status"] == "retry-wait":
        allowed_attempts.add(value["retryCount"])
    if value["attemptCount"] not in allowed_attempts:
        raise PublicationRecordError("initial attempt and retry accounting disagree")
    if value["status"] == "retry-wait" and value["nextRetryAt"] is None:
        raise PublicationRecordError("retry wait lacks its next timestamp")
    if value["status"] == "paused" and value["refusalKind"] is None:
        raise PublicationRecordError("paused publication lacks refusal evidence")
    if value["refusalKind"] is not None and value["refusalKind"] not in REFUSAL_KINDS:
        raise PublicationRecordError("refusal kind is invalid")
    if value["providerEvidenceRef"] is not None and not HASH_PATTERN.fullmatch(str(value["providerEvidenceRef"])):
        raise PublicationRecordError("provider evidence must be a redacted digest reference")
    validate_preserved_state(value["preservedState"])
    if not isinstance(value["attestations"], dict):
        raise PublicationRecordError("attestations must be an exact identity map")
    for kind, attestation in value["attestations"].items():
        if kind != attestation.get("kind"):
            raise PublicationRecordError("attestation identity map is mismatched")
        validate_publication_attestation(attestation)
    expected_provider_ids = {"push", "pull-request", "squash-merge"}
    if set(value["providerOperationIds"]) != expected_provider_ids:
        raise PublicationRecordError("provider operation identity inventory is incomplete")
    assigned = [item for item in value["providerOperationIds"].values() if item is not None]
    if any(not isinstance(item, str) or not item for item in assigned) or len(assigned) != len(set(assigned)):
        raise PublicationRecordError("provider mutation identities must be unique and immutable")
    if value["activeProviderOperation"] is not None and value["activeProviderOperation"] not in PUBLICATION_OPERATIONS:
        raise PublicationRecordError("active provider operation is invalid")
    readback = value["authorityReadback"]
    if readback is not None:
        required_readback = {
            "issueId", "labels", "pullRequestId", "baseRef", "headSha",
            "baseSha", "mergeability", "evidenceRef", "expectedHeadSha",
        }
        _exact_keys(readback, required_readback, "authority readback")
        if readback["issueId"] != value["issueId"] or readback["baseRef"] != value["baseRef"]:
            raise PublicationRecordError("authority readback identity is mismatched")
        exact_sha(readback["expectedHeadSha"], "authority expected head")
        exact_sha(readback["baseSha"], "authority base SHA")
        if not HASH_PATTERN.fullmatch(str(readback["evidenceRef"])):
            raise PublicationRecordError("authority readback evidence is invalid")
    if value["evidenceFinalizationCount"] not in {0, 1}:
        raise PublicationRecordError("at most one evidence finalization is permitted")
    preparation = value["preparation"]
    if preparation is not None:
        _exact_keys(preparation, {"branch", "baseSha", "headSha", "paths", "manifestDigest", "aggregateDigest"}, "publication preparation")
        exact_sha(preparation["baseSha"], "preparation base SHA")
        exact_sha(preparation["headSha"], "preparation head SHA")
        safe_relative_paths(preparation["paths"], "prepared paths")
        for name in ("manifestDigest", "aggregateDigest"):
            if not HASH_PATTERN.fullmatch(str(preparation[name])):
                raise PublicationRecordError("publication preparation digest is invalid")
        if preparation["branch"] != value["branch"] or preparation["baseSha"] != value["baseSha"]:
            raise PublicationRecordError("publication preparation identity is stale")
    finalization = value["evidenceFinalization"]
    if finalization is not None:
        _exact_keys(finalization, {"headSha", "stagedPaths", "deltaDigest", "providerEvidenceRef"}, "evidence finalization")
        exact_sha(finalization["headSha"], "finalization head SHA")
        safe_relative_paths(finalization["stagedPaths"], "finalized evidence paths")
        for name in ("deltaDigest", "providerEvidenceRef"):
            if not HASH_PATTERN.fullmatch(str(finalization[name])):
                raise PublicationRecordError("evidence finalization digest is invalid")
        if value["evidenceFinalizationCount"] != 1 or finalization["headSha"] != value["headSha"]:
            raise PublicationRecordError("evidence finalization identity is stale")
    if not isinstance(value["repairAttempt"], int) or not 0 <= value["repairAttempt"] <= 3:
        raise PublicationRecordError("repair attempt is outside the bound")
    if value["consumedReplyId"] is not None and (
        not isinstance(value["consumedReplyId"], str) or not value["consumedReplyId"]
    ):
        raise PublicationRecordError("consumed reply identity is invalid")
    utc_timestamp(value["createdAt"], "createdAt")
    utc_timestamp(value["updatedAt"], "updatedAt")
    return copy.deepcopy(dict(value))


def retry_delay_minutes(retry_count: int, retry_after_seconds: int | None = None) -> int:
    """Return the delay for retry indexes 1/2/3, capped at thirty minutes."""

    if retry_count not in {1, 2, 3}:
        raise PublicationRecordError("retry index must be 1, 2, or 3")
    if retry_after_seconds is None:
        return BACKOFF_MINUTES[retry_count - 1]
    if not isinstance(retry_after_seconds, int) or retry_after_seconds < 0:
        raise PublicationRecordError("Retry-After must be a non-negative integer")
    return min(30, (retry_after_seconds + 59) // 60)


def validate_attestation(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schemaVersion", "attestationId", "kind", "repositoryId", "workflowId",
        "issueId", "exactSha", "physicalWorktreeFingerprint", "evidenceDigest",
        "startedAt", "completedAt", "exitCode",
    }
    _exact_keys(value, required, "attestation")
    if value["schemaVersion"] != PUBLICATION_VERSION or value["kind"] not in EVIDENCE_KINDS:
        raise PublicationRecordError("attestation version or kind is invalid")
    exact_sha(value["exactSha"], "attestation exactSha")
    for name in ("physicalWorktreeFingerprint", "evidenceDigest"):
        if not HASH_PATTERN.fullmatch(str(value[name])):
            raise PublicationRecordError(f"attestation {name} is invalid")
    utc_timestamp(value["startedAt"], "startedAt")
    utc_timestamp(value["completedAt"], "completedAt")
    if not isinstance(value["exitCode"], int):
        raise PublicationRecordError("attestation exit code is invalid")
    return copy.deepcopy(dict(value))


def validate_publication_attestation(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schemaVersion", "attestationId", "publicationOperationId", "kind",
        "producer", "stage", "result", "provenanceRef", "exactSha",
        "issuedStateRevision", "recordedAt",
    }
    _exact_keys(value, required, "publication attestation")
    kind = value["kind"]
    if value["schemaVersion"] != PUBLICATION_VERSION or kind not in ATTESTATION_PRODUCERS:
        raise PublicationRecordError("publication attestation kind is invalid")
    if value["producer"] != ATTESTATION_PRODUCERS[kind]:
        raise PublicationRecordError("publication attestation producer is invalid")
    expected_stage = "post-merge" if kind in {"merge-readback", "exact-merge-aggregate"} else "pre-merge"
    if value["stage"] != expected_stage or value["result"] not in {"passed", "failed"}:
        raise PublicationRecordError("publication attestation stage or result is invalid")
    if not OPERATION_PATTERN.fullmatch(str(value["attestationId"])) or not OPERATION_PATTERN.fullmatch(str(value["publicationOperationId"])):
        raise PublicationRecordError("publication attestation identity is invalid")
    if not HASH_PATTERN.fullmatch(str(value["provenanceRef"])):
        raise PublicationRecordError("publication attestation provenance is invalid")
    exact_sha(value["exactSha"], "publication attestation SHA")
    if not isinstance(value["issuedStateRevision"], int) or value["issuedStateRevision"] < 0:
        raise PublicationRecordError("publication attestation revision is invalid")
    utc_timestamp(value["recordedAt"], "recordedAt")
    return copy.deepcopy(dict(value))


def validate_publication_result(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one immutable engine-owned specialist/trusted result."""
    required = {
        "schemaVersion", "resultId", "publicationOperationId", "kind",
        "producer", "stage", "exactSha", "outcome", "recordedAt",
        "sourceOperationId", "sourceRecordDigest",
    }
    _exact_keys(value, required, "publication result")
    kind = value["kind"]
    if value["schemaVersion"] != PUBLICATION_VERSION or kind not in ATTESTATION_PRODUCERS:
        raise PublicationRecordError("publication result kind is invalid")
    if value["producer"] != ATTESTATION_PRODUCERS[kind]:
        raise PublicationRecordError("publication result producer is invalid")
    expected_stage = "post-merge" if kind in {"merge-readback", "exact-merge-aggregate"} else "pre-merge"
    if value["stage"] != expected_stage or value["outcome"] not in {"passed", "failed"}:
        raise PublicationRecordError("publication result stage or outcome is invalid")
    for name in ("resultId", "publicationOperationId", "sourceOperationId"):
        if not OPERATION_PATTERN.fullmatch(str(value[name])):
            raise PublicationRecordError(f"publication result {name} is invalid")
    exact_sha(value["exactSha"], "publication result SHA")
    if not HASH_PATTERN.fullmatch(str(value["sourceRecordDigest"])):
        raise PublicationRecordError("publication result provenance digest is invalid")
    utc_timestamp(value["recordedAt"], "recordedAt")
    return copy.deepcopy(dict(value))
