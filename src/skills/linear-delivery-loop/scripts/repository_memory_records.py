"""Immutable repository-memory record construction and structural topology."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .contracts import (
    ContractValidationError,
    canonical_json_bytes,
    sha256_canonical,
    validate_contract,
)


RECORD_ROOT = PurePosixPath("docs/repository-memory/records")
COMMIT_ROOT = PurePosixPath("docs/repository-memory/commits")


class RepositoryMemoryRecordError(ValueError):
    """A curated memory file is malformed, unsafe, or differently bound."""


def file_sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def file_sha256(path: Path) -> str:
    try:
        return file_sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise RepositoryMemoryRecordError("Cannot read repository-memory input") from exc


def safe_repository_path(repository_root: Path, relative: str, *, must_exist: bool = False) -> Path:
    if not relative or "\\" in relative or relative.startswith("/"):
        raise RepositoryMemoryRecordError("Repository-memory path is not canonical")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise RepositoryMemoryRecordError("Repository-memory path escapes its repository")
    root = repository_root.resolve(strict=True)
    candidate = root.joinpath(*pure.parts)
    # Walk every existing component. The first promotion may legitimately lack
    # repository-memory/records and commits, but every existing ancestor must
    # remain a real directory beneath the physical repository root.
    cursor = root
    for part in pure.parts[:-1]:
        cursor = cursor / part
        if not cursor.exists():
            break
        if cursor.is_symlink() or not cursor.is_dir():
            raise RepositoryMemoryRecordError(
                "Repository-memory parent is not a safe directory"
            )
        try:
            observed = cursor.resolve(strict=True)
        except OSError as exc:
            raise RepositoryMemoryRecordError(
                "Repository-memory parent cannot be resolved safely"
            ) from exc
        if os.path.commonpath([os.fspath(root), os.fspath(observed)]) != os.fspath(root):
            raise RepositoryMemoryRecordError(
                "Repository-memory path resolves outside its repository"
            )
    if candidate.exists():
        try:
            observed_candidate = candidate.resolve(strict=True)
        except OSError as exc:
            raise RepositoryMemoryRecordError(
                "Repository-memory target cannot be resolved safely"
            ) from exc
        if os.path.commonpath([os.fspath(root), os.fspath(observed_candidate)]) != os.fspath(root):
            raise RepositoryMemoryRecordError("Repository-memory path resolves outside its repository")
    if must_exist and not candidate.is_file():
        raise RepositoryMemoryRecordError("Repository-memory file is missing")
    if candidate.exists() and candidate.is_symlink():
        raise RepositoryMemoryRecordError("Repository-memory files cannot be symlinks")
    if candidate.exists() and candidate.stat().st_nlink != 1:
        raise RepositoryMemoryRecordError("Repository-memory files cannot be hard-linked")
    return candidate


def read_canonical_json(path: Path) -> dict[str, Any]:
    try:
        content = path.read_bytes()
        value = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryMemoryRecordError("Repository-memory JSON is unreadable") from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != content:
        raise RepositoryMemoryRecordError("Repository-memory JSON is not canonical")
    return value


def write_create_new(
    path: Path, content: bytes, *, repository_root: Path | None = None
) -> None:
    if repository_root is None:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        root = repository_root.resolve(strict=True)
        try:
            relative_parent = path.parent.relative_to(root)
        except ValueError as exc:
            raise RepositoryMemoryRecordError(
                "Repository-memory create parent escapes its repository"
            ) from exc
        cursor = root
        for part in relative_parent.parts:
            cursor = cursor / part
            try:
                cursor.mkdir()
            except FileExistsError:
                pass
            if cursor.is_symlink() or not cursor.is_dir():
                raise RepositoryMemoryRecordError(
                    "Repository-memory create parent is not a safe directory"
                )
            observed = cursor.resolve(strict=True)
            if os.path.commonpath([os.fspath(root), os.fspath(observed)]) != os.fspath(root):
                raise RepositoryMemoryRecordError(
                    "Repository-memory create parent resolves outside its repository"
                )
        safe_repository_path(
            root, path.relative_to(root).as_posix(), must_exist=False
        )
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o600)
        if os.fstat(descriptor).st_nlink != 1:
            raise RepositoryMemoryRecordError("Repository-memory create is hard-linked")
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise RepositoryMemoryRecordError("Repository-memory target already exists") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if path.read_bytes() != content:
        raise RepositoryMemoryRecordError("Repository-memory create readback differs")


def candidate_to_record(
    manifest: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    created_by: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct RecordPayloadV1 after the manifest payload digest is known."""

    identity = {
        "workflowId": manifest["curationWorkflowId"],
        "candidatePromotionId": candidate["candidatePromotionId"],
        "promotionManifestPayloadSha256": manifest["promotionManifestPayloadSha256"],
        "producer": "docs-as-code",
        "repositoryId": manifest["repositoryId"],
        "headSha": manifest["headSha"],
        "physicalWorktreeFingerprint": manifest["physicalWorktreeFingerprint"],
        "observedAt": manifest["createdAt"],
    }
    source = copy.deepcopy(dict(candidate))
    candidate_digest = source.pop("candidateIntentSha256")
    record_id = source.pop("targetRecordId")
    version = source.pop("targetRecordVersion")
    target = source.pop("targetPath")
    source.pop("candidateId", None)
    source.pop("candidatePromotionId", None)
    expected_fields = {
        "kind", "topics", "paths", "stages", "work", "title", "summary",
        "assertions", "provenance", "confidence", "freshness", "lifecycle",
        "retention", "supersedes", "restores", "createdAt", "reviewedAt",
        "archiveReason", "redactionReason",
    }
    if set(source) != expected_fields:
        raise RepositoryMemoryRecordError("Candidate intent field inventory is not exact")
    record = {
        "schemaVersion": "1.0",
        "recordId": record_id,
        "recordVersion": version,
        "candidateId": candidate["candidateId"],
        "candidatePromotionId": candidate["candidatePromotionId"],
        "repositoryId": manifest["repositoryId"],
        "repositoryKey": manifest["repositoryKey"],
        "filename": PurePosixPath(target).name,
        "candidateIntentSha256": candidate_digest,
        "promotionManifestPayloadSha256": manifest["promotionManifestPayloadSha256"],
        **source,
        "createdBy": copy.deepcopy(dict(created_by or identity)),
        "updatedBy": identity,
        "recordPayloadSha256": "sha256:" + "0" * 64,
    }
    record["recordPayloadSha256"] = sha256_canonical(
        {key: item for key, item in record.items() if key != "recordPayloadSha256"}
    )
    try:
        return validate_contract("repository-memory-record", record)
    except ContractValidationError as exc:
        raise RepositoryMemoryRecordError(str(exc)) from exc


def validate_record(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_contract("repository-memory-record", value)
    except ContractValidationError as exc:
        raise RepositoryMemoryRecordError(str(exc)) from exc


def normalized_scope(record: Mapping[str, Any]) -> dict[str, Any]:
    work = record.get("work")
    normalized_work = None
    if isinstance(work, Mapping):
        normalized_work = tuple(
            (key, unicodedata.normalize("NFC", str(work[key])).casefold())
            for key in sorted(work)
        )
    return {
        "repositoryId": record["repositoryId"],
        "work": normalized_work,
        "stages": tuple(item.casefold() for item in record["stages"]),
        "paths": tuple(item.casefold() for item in record["paths"]),
        "topics": tuple(item.casefold() for item in record["topics"]),
    }


def assertion_map(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        item["key"]: {
            "valueType": item["valueType"],
            "comparison": "equals",
            "value": copy.deepcopy(item["value"]),
        }
        for item in record["assertions"]
    }


def _paths_intersect(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    if not left or not right:
        return True
    for first in left:
        for second in right:
            if first == second or first.startswith(second + "/") or second.startswith(first + "/"):
                return True
    return False


def scopes_intersect(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    a = normalized_scope(left)
    b = normalized_scope(right)
    if a["repositoryId"] != b["repositoryId"]:
        return False
    if a["work"] is not None and b["work"] is not None and a["work"] != b["work"]:
        return False
    if a["stages"] and b["stages"] and not set(a["stages"]) & set(b["stages"]):
        return False
    if not _paths_intersect(a["paths"], b["paths"]):
        return False
    if a["topics"] and b["topics"] and not set(a["topics"]) & set(b["topics"]):
        return False
    return True


def duplicate_records(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        canonical_json_bytes(normalized_scope(left)) == canonical_json_bytes(normalized_scope(right))
        and canonical_json_bytes(assertion_map(left)) == canonical_json_bytes(assertion_map(right))
    )


def conflicting_keys(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
    if not scopes_intersect(left, right):
        return []
    a = assertion_map(left)
    b = assertion_map(right)
    return sorted(key for key in set(a) & set(b) if a[key] != b[key])


def record_ref(record: Mapping[str, Any]) -> tuple[str, int]:
    return record["recordId"], record["recordVersion"]


def predecessor_refs(record: Mapping[str, Any]) -> list[tuple[str, int]]:
    return [(item["recordId"], item["recordVersion"]) for item in record["supersedes"]]
