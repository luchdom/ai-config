"""Deterministic marker-owned repository-memory index projection."""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from .contracts import canonical_json_bytes, sha256_canonical, validate_contract
from .repository_memory_records import (
    COMMIT_ROOT,
    RECORD_ROOT,
    assertion_map,
    conflicting_keys,
    duplicate_records,
    file_sha256_bytes,
    predecessor_refs,
    read_canonical_json,
    record_ref,
    safe_repository_path,
    validate_record,
)


BUILDER_VERSION = "1.0"


class RepositoryMemoryIndexError(ValueError):
    """The marker projection cannot be safely built or persisted."""


def _utc(value: datetime | None) -> datetime:
    observed = value or datetime.now(timezone.utc)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return observed.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _marker_path(batch_id: str) -> str:
    return f"{COMMIT_ROOT.as_posix()}/{batch_id}.json"


def scan_committed_records(
    repository_root: Path,
    *,
    repository_id: str,
    repository_key: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    """Read only complete, valid marker-bound record sets."""

    diagnostics: Counter[str] = Counter()
    marker_root = repository_root / COMMIT_ROOT
    marker_paths = sorted(marker_root.glob("*.json"), key=lambda path: path.name.casefold()) if marker_root.is_dir() else []
    candidates: list[tuple[dict[str, Any], bytes, list[tuple[dict[str, Any], str, bytes]]]] = []
    target_owners: defaultdict[str, list[int]] = defaultdict(list)
    for path in marker_paths:
        try:
            marker_bytes = path.read_bytes()
            marker = read_canonical_json(path)
            validate_contract("repository-memory-commit", marker)
            if marker["repositoryId"] != repository_id or marker["repositoryKey"] != repository_key:
                raise RepositoryMemoryIndexError("cross-repository-marker")
            if path.name != f"{marker['batchPromotionId']}.json":
                raise RepositoryMemoryIndexError("marker-filename-mismatch")
            bound: list[tuple[dict[str, Any], str, bytes]] = []
            for member in marker["records"]:
                record_path = safe_repository_path(repository_root, member["targetPath"], must_exist=True)
                record_bytes = record_path.read_bytes()
                if file_sha256_bytes(record_bytes) != member["recordFileSha256"]:
                    raise RepositoryMemoryIndexError("record-file-digest-mismatch")
                record = read_canonical_json(record_path)
                validate_record(record)
                expected_target = f"{RECORD_ROOT.as_posix()}/{record['filename']}"
                if member["targetPath"] != expected_target:
                    raise RepositoryMemoryIndexError("record-target-mismatch")
                for field in ("candidateId", "candidatePromotionId", "candidateIntentSha256", "recordPayloadSha256"):
                    if member[field] != record[field]:
                        raise RepositoryMemoryIndexError("marker-record-binding-mismatch")
                if record["repositoryId"] != repository_id or record["repositoryKey"] != repository_key:
                    raise RepositoryMemoryIndexError("cross-repository-record")
                bound.append((record, member["targetPath"], record_bytes))
            marker_index = len(candidates)
            for member in marker["records"]:
                target_owners[member["targetPath"].casefold()].append(marker_index)
            candidates.append((marker, marker_bytes, bound))
        except Exception:
            diagnostics["invalid-marker-batch"] += 1
    invalid_owners = {owner for owners in target_owners.values() if len(owners) > 1 for owner in owners}
    markers: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for index, (marker, marker_bytes, bound) in enumerate(candidates):
        if index in invalid_owners:
            diagnostics["duplicate-marker-ownership"] += 1
            continue
        marker_path = _marker_path(marker["batchPromotionId"])
        markers.append({
            "path": marker_path,
            "batchPromotionId": marker["batchPromotionId"],
            "payloadSha256": marker["batchCommitPayloadSha256"],
            "fileSha256": file_sha256_bytes(marker_bytes),
        })
        for record, target, record_bytes in bound:
            records.append({
                "record": record,
                "path": target,
                "fileSha256": file_sha256_bytes(record_bytes),
                "markerPath": marker_path,
                "markerPayloadSha256": marker["batchCommitPayloadSha256"],
            })
    # Unmarked records are visible only as a bounded diagnostic count.
    record_root = repository_root / RECORD_ROOT
    observed_records = len(list(record_root.glob("*.json"))) if record_root.is_dir() else 0
    committed_paths = {item["path"].casefold() for item in records}
    diagnostics["uncommitted-orphan"] += max(0, observed_records - len(committed_paths))
    return markers, records, diagnostics


def _graph_projection(records: list[dict[str, Any]], diagnostics: Counter[str]) -> tuple[dict[tuple[str, int], tuple[str, int]], set[tuple[str, int]]]:
    by_ref = {record_ref(item["record"]): item["record"] for item in records}
    successors: dict[tuple[str, int], tuple[str, int]] = {}
    descendants: defaultdict[tuple[str, int], set[tuple[str, int]]] = defaultdict(set)
    invalid: set[tuple[str, int]] = set()
    for item in records:
        record = item["record"]
        current = record_ref(record)
        predecessors = predecessor_refs(record)
        if record.get("restores") is not None:
            restore = (record["restores"].get("recordId"), record["restores"].get("recordVersion"))
            if len(predecessors) != 1 or restore != predecessors[0] or restore not in by_ref or by_ref[restore]["lifecycle"] != "archived":
                invalid.add(current)
                diagnostics["invalid-restoration"] += 1
        if any(predecessor in by_ref and by_ref[predecessor]["lifecycle"] == "redacted" for predecessor in predecessors) and record["lifecycle"] == "active":
            invalid.add(current)
            diagnostics["redacted-chain-revival"] += 1
        for predecessor in predecessors:
            if predecessor not in by_ref or predecessor == current:
                invalid.add(current)
                diagnostics["invalid-supersession"] += 1
                continue
            descendants[predecessor].add(current)
            if predecessor in successors and successors[predecessor] != current:
                invalid.update({current, successors[predecessor]})
                diagnostics["supersession-branch"] += 1
            else:
                successors[predecessor] = current
    # Detect cycles over all forward edges, although version rules normally preclude them.
    for start in by_ref:
        seen: set[tuple[str, int]] = set()
        cursor = start
        while cursor in successors:
            if cursor in seen:
                invalid.update(seen)
                diagnostics["supersession-cycle"] += 1
                break
            seen.add(cursor)
            cursor = successors[cursor]
    # Invalid ancestry is contagious. A syntactically valid descendant cannot
    # become a terminal record when any path to it crosses a missing, branched,
    # cyclic, restoration-invalid, or redacted predecessor.
    pending = list(invalid)
    while pending:
        ancestor = pending.pop()
        for descendant in descendants.get(ancestor, set()):
            if descendant not in invalid:
                invalid.add(descendant)
                diagnostics["invalid-ancestry"] += 1
                pending.append(descendant)
    for predecessor, successor in list(successors.items()):
        if predecessor in invalid or successor in invalid:
            successors.pop(predecessor, None)
    return successors, invalid


def build_index(
    repository_root: str | Path,
    *,
    repository_id: str,
    repository_key: str,
    source_tree: str,
    now: datetime | None = None,
    prepared_marker: Mapping[str, Any] | None = None,
    prepared_records: list[tuple[Mapping[str, Any], str, bytes]] | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve(strict=True)
    markers, committed, diagnostics = scan_committed_records(
        root, repository_id=repository_id, repository_key=repository_key
    )
    if prepared_marker is not None:
        validate_contract("repository-memory-commit", prepared_marker)
        if prepared_marker["repositoryId"] != repository_id or prepared_marker["repositoryKey"] != repository_key:
            raise RepositoryMemoryIndexError("Prepared marker repository binding differs")
        supplied = prepared_records or []
        by_target = {target: (record, content) for record, target, content in supplied}
        if set(by_target) != {item["targetPath"] for item in prepared_marker["records"]}:
            raise RepositoryMemoryIndexError("Prepared index record set is incomplete")
        marker_path = _marker_path(prepared_marker["batchPromotionId"])
        marker_bytes = canonical_json_bytes(prepared_marker)
        markers.append({
            "path": marker_path, "batchPromotionId": prepared_marker["batchPromotionId"],
            "payloadSha256": prepared_marker["batchCommitPayloadSha256"],
            "fileSha256": file_sha256_bytes(marker_bytes),
        })
        for member in prepared_marker["records"]:
            record, content = by_target[member["targetPath"]]
            validate_record(record)
            if file_sha256_bytes(content) != member["recordFileSha256"]:
                raise RepositoryMemoryIndexError("Prepared index record digest differs")
            committed.append({
                "record": copy.deepcopy(dict(record)), "path": member["targetPath"],
                "fileSha256": member["recordFileSha256"], "markerPath": marker_path,
                "markerPayloadSha256": prepared_marker["batchCommitPayloadSha256"],
            })
    successors, invalid_graph = _graph_projection(committed, diagnostics)
    entries: list[dict[str, Any]] = []
    by_ref = {record_ref(item["record"]): item for item in committed}
    terminal_records = [item for item in committed if record_ref(item["record"]) not in successors and record_ref(item["record"]) not in invalid_graph]
    conflicts: defaultdict[tuple[str, int], set[str]] = defaultdict(set)
    duplicate_groups: list[list[tuple[str, int]]] = []
    grouped: set[tuple[str, int]] = set()
    for index, left in enumerate(terminal_records):
        for right in terminal_records[index + 1:]:
            left_record, right_record = left["record"], right["record"]
            keys = conflicting_keys(left_record, right_record)
            if keys:
                conflicts[record_ref(left_record)].update(keys)
                conflicts[record_ref(right_record)].update(keys)
            elif duplicate_records(left_record, right_record):
                a, b = record_ref(left_record), record_ref(right_record)
                existing = next((group for group in duplicate_groups if a in group or b in group), None)
                if existing is None:
                    duplicate_groups.append([a, b])
                else:
                    if a not in existing:
                        existing.append(a)
                    if b not in existing:
                        existing.append(b)
                grouped.update({a, b})
    duplicate_representatives: dict[tuple[str, int], tuple[str, int]] = {}
    duplicate_members: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for group in duplicate_groups:
        ordered = sorted(group, key=lambda ref: (-ref[1], ref[0].casefold(), by_ref[ref]["record"]["filename"]))
        representative = ordered[0]
        duplicate_members[representative] = [
            {
                "recordId": ref[0], "recordVersion": ref[1],
                "provenance": copy.deepcopy(by_ref[ref]["record"]["provenance"]),
            }
            for ref in ordered[1:]
        ]
        for ref in ordered:
            duplicate_representatives[ref] = representative
    current = _utc(now)
    for item in committed:
        record = item["record"]
        ref = record_ref(record)
        superseded = ref in successors
        expiry = record["retention"].get("expiresAt") if isinstance(record["retention"], Mapping) else None
        expired = False
        if isinstance(expiry, str):
            expired = datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= current
        review_date = record["retention"].get("reviewAt") or record["freshness"].get("reviewAfter")
        review_due = bool(
            isinstance(review_date, str)
            and datetime.fromisoformat(review_date.replace("Z", "+00:00")) <= current
        )
        stale_reasons: set[str] = set()
        for source in record["provenance"]:
            try:
                source_path = safe_repository_path(root, source["path"], must_exist=True)
                if file_sha256_bytes(source_path.read_bytes()) != source["sha256"]:
                    stale_reasons.add("source-digest-drift")
            except Exception as exc:
                message = str(exc).casefold()
                stale_reasons.add("source-missing" if "missing" in message else "source-unsafe")
        representative = duplicate_representatives.get(ref, ref)
        entry = {
            "recordId": ref[0], "recordVersion": ref[1], "filename": record["filename"],
            "path": item["path"], "recordFileSha256": item["fileSha256"],
            "recordPayloadSha256": record["recordPayloadSha256"],
            "markerPath": item["markerPath"], "markerPayloadSha256": item["markerPayloadSha256"],
            "kind": record["kind"], "topics": record["topics"], "paths": record["paths"],
            "stages": record["stages"], "work": record["work"], "confidence": record["confidence"],
            "lifecycle": record["lifecycle"], "superseded": superseded,
            "successor": ({"recordId": successors[ref][0], "recordVersion": successors[ref][1]} if superseded else None),
            "invalidGraph": ref in invalid_graph, "conflictKeys": sorted(conflicts.get(ref, set())),
            "expired": expired, "reviewDue": review_due,
            "stale": bool(stale_reasons), "staleReasons": sorted(stale_reasons),
            "freshnessState": "stale" if stale_reasons else "expired" if expired else "review-due" if review_due else "fresh",
            "duplicateRepresentative": {"recordId": representative[0], "recordVersion": representative[1]},
            "duplicateMembers": duplicate_members.get(ref, []),
            "provenanceSha256": sha256_canonical(record["provenance"]),
            "assertionMapSha256": sha256_canonical(assertion_map(record)),
        }
        entries.append(entry)
    entries.sort(key=lambda item: (item["recordId"].casefold(), item["recordVersion"], item["filename"]))
    markers.sort(key=lambda item: item["path"])
    counts = Counter()
    for entry in entries:
        counts[entry["lifecycle"]] += 1
        for name, active in (("superseded", entry["superseded"]), ("conflict", bool(entry["conflictKeys"])), ("expired", entry["expired"]), ("stale", entry["stale"]), ("review-due", entry["reviewDue"]), ("legacy-evidence-bound", entry["confidence"] == "legacy-evidence-bound")):
            counts[name] += int(active)
    counts["quarantined"] = sum(diagnostics.values())
    index = {
        "schemaVersion": "1.0", "builderVersion": BUILDER_VERSION,
        "repositoryId": repository_id, "repositoryKey": repository_key,
        "sourceTree": source_tree, "builtAt": _timestamp(current),
        "markers": markers, "entries": entries,
        "diagnostics": dict(sorted(diagnostics.items())),
        "counts": dict(sorted(counts.items())),
        "indexSemanticSha256": "sha256:" + "0" * 64,
    }
    semantic = {key: value for key, value in index.items() if key not in {"builtAt", "indexSemanticSha256"}}
    index["indexSemanticSha256"] = sha256_canonical(semantic)
    return validate_contract("repository-memory-index", index)


def marker_set_sha256(index: Mapping[str, Any]) -> str:
    return sha256_canonical(index["markers"])


def persist_index(index: Mapping[str, Any], *, state_guard: Any, state_root: Path) -> Path:
    directory = state_guard.directory(state_root / "repository-memory", create=True)
    path = state_guard.leaf(directory / "index.json")
    state_guard.write_json(path, copy.deepcopy(dict(index)))
    if state_guard.read_json(path) != index:
        raise RepositoryMemoryIndexError("Index atomic replacement readback differs")
    return path


def load_index(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepositoryMemoryIndexError("Derived index is unreadable") from exc
    if not isinstance(value, dict):
        raise RepositoryMemoryIndexError("Derived index must be an object")
    return validate_contract("repository-memory-index", value)
