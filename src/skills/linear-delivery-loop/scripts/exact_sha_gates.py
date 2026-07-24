"""Clean isolated exact-SHA aggregate gates and bounded evidence convergence."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .publication_records import (
    PublicationRecordError, exact_sha, safe_relative_paths, sha256_json,
    utc_timestamp, validate_attestation,
)

AI_CONFIG_AGGREGATE = (sys.executable, ".\\scripts\\validate.py")
REQUIRED_DRAFT_KINDS = {"plan", "tasks", "audit", "review", "qa", "completion"}


class ExactShaGateError(PublicationRecordError):
    pass


class ExactShaGateRunner:
    """Allocate through an injected worktree manager and run a fixed argv, never a shell."""

    __slots__ = ("repository_id", "workflow_id", "issue_id", "worktrees", "runner", "argv")

    def __init__(self, *, repository_id: str, workflow_id: str, issue_id: str, worktrees: Any, runner: Callable[..., Any] = subprocess.run, argv: Sequence[str] | None = None) -> None:
        self.repository_id = repository_id
        self.workflow_id = workflow_id
        self.issue_id = issue_id
        self.worktrees = worktrees
        self.runner = runner
        self.argv = tuple(argv or AI_CONFIG_AGGREGATE)
        if len(self.argv) != 2 or Path(self.argv[0]).name.casefold() not in {"python", "python.exe"} or self.argv[1] != ".\\scripts\\validate.py":
            raise ExactShaGateError("ai-config aggregate must resolve to fixed Python validate argv")

    def run(self, *, operation_id: str, exact_commit: str, started_at: str, completed_at: str, kind: str = "exact-head-aggregate") -> dict[str, Any]:
        exact_sha(exact_commit)
        utc_timestamp(started_at, "startedAt")
        utc_timestamp(completed_at, "completedAt")
        allocation = self.worktrees.create_gate_worktree(operation_id, exact_sha=exact_commit)
        path = Path(allocation["path"])
        if self._status(path):
            raise ExactShaGateError("gate worktree is dirty before aggregate")
        observed = self._git(path, "rev-parse", "HEAD")
        if observed != exact_commit:
            raise ExactShaGateError("gate worktree is not at the requested exact SHA")
        result = self.runner(list(self.argv), cwd=path, shell=False, capture_output=True, text=True, check=False)
        if self._status(path):
            raise ExactShaGateError("gate worktree is dirty after aggregate")
        fingerprint = allocation["physicalWorktreeFingerprint"]
        attestation = {
            "schemaVersion": "1.0", "attestationId": operation_id,
            "kind": kind, "repositoryId": self.repository_id,
            "workflowId": self.workflow_id, "issueId": self.issue_id,
            "exactSha": exact_commit, "physicalWorktreeFingerprint": fingerprint,
            "evidenceDigest": sha256_json({"argv": list(self.argv), "python": sys.version.split()[0], "exitCode": result.returncode}),
            "startedAt": started_at, "completedAt": completed_at, "exitCode": result.returncode,
        }
        validate_attestation(attestation)
        revision = self.worktrees.store.load_state()["revision"]
        self.worktrees.set_gate_evidence(
            operation_id,
            expected_state_revision=revision,
            operation_status="resolved" if result.returncode == 0 else "failed",
            attestation_status="complete" if result.returncode == 0 else "failed",
        )
        if result.returncode != 0:
            raise ExactShaGateError("exact-SHA aggregate failed")
        return attestation

    @staticmethod
    def _git(path: Path, *arguments: str) -> str:
        result = subprocess.run(["git", "-C", os.fspath(path), *arguments], shell=False, check=False, capture_output=True, text=True)
        if result.returncode:
            raise ExactShaGateError("exact-SHA Git observation failed")
        return result.stdout.strip()

    @classmethod
    def _status(cls, path: Path) -> str:
        return cls._git(path, "status", "--porcelain=v1", "--untracked-files=all")


class EvidenceConvergence:
    """Classify one and only one evidence-only finalization delta."""

    _PATH = re.compile(
        r"^docs-ai/[a-z0-9][a-z0-9-]{2,127}/"
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9][a-z0-9-]{2,160}-"
        r"(?P<role>code-review|qa|completion)\.md$"
    )
    _SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")

    def __init__(self, *, repository_root: str | Path | None = None) -> None:
        self.repository_root = Path(repository_root).resolve() if repository_root else None

    def require_drafts(self, records: Mapping[str, Any], *, design_required: bool,
        read_draft: Callable[[str], bytes] | None = None) -> None:
        expected = REQUIRED_DRAFT_KINDS | {"design"}
        if set(records) != expected:
            raise ExactShaGateError(f"draft evidence inventory is not exact: {sorted(expected - set(records))}")
        if self.repository_root is None:
            raise ExactShaGateError("draft evidence validation requires the registered repository root")
        for kind in REQUIRED_DRAFT_KINDS:
            record = records.get(kind)
            if not isinstance(record, Mapping) or set(record) != {"status", "path", "digest"} or record.get("status") != "draft":
                raise ExactShaGateError(f"{kind} draft evidence record is invalid")
            path = safe_relative_paths([record.get("path")], f"{kind} draft path")[0]
            candidate = self.repository_root / path
            try:
                info = candidate.lstat()
                content = read_draft(path) if read_draft is not None else candidate.read_bytes()
            except OSError as exc:
                raise ExactShaGateError(f"{kind} draft evidence cannot be observed") from exc
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise ExactShaGateError(f"{kind} draft evidence is not a regular file")
            digest = "sha256:" + hashlib.sha256(content).hexdigest()
            if record.get("digest") != digest:
                raise ExactShaGateError(f"{kind} draft evidence digest is stale")
        design = records.get("design")
        if design_required:
            if not isinstance(design, Mapping) or set(design) != {"status", "path", "digest"} or design.get("status") != "draft":
                raise ExactShaGateError("required design evidence is missing")
            path = safe_relative_paths([design.get("path")], "design draft path")[0]
            candidate = self.repository_root / path
            try:
                info = candidate.lstat()
                content = read_draft(path) if read_draft is not None else candidate.read_bytes()
            except OSError as exc:
                raise ExactShaGateError("design draft evidence cannot be observed") from exc
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise ExactShaGateError("design draft evidence is not a regular file")
            digest = "sha256:" + hashlib.sha256(content).hexdigest()
            if design.get("digest") != digest:
                raise ExactShaGateError("design draft evidence digest is stale")
        if not design_required and design != {"status": "not-required", "reason": "no-product-ui"}:
            raise ExactShaGateError("validated design not-required declaration is missing")

    @classmethod
    def _record(cls, path: str, content: str) -> dict[str, str]:
        match = cls._PATH.fullmatch(path)
        if match is None:
            raise ExactShaGateError("final delta is not a role-aware dated evidence artifact")
        fields: dict[str, str] = {}
        for line in content.splitlines():
            if ": " in line and not line.startswith(("#", "-", " ")):
                key, value = line.split(": ", 1)
                if key in fields:
                    raise ExactShaGateError("evidence record contains a duplicate field")
                fields[key] = value
        required = {"Evidence-Role", "Evidence-State", "Exact-SHA"}
        if set(fields) != required:
            raise ExactShaGateError("evidence record field inventory is not exact")
        if fields["Evidence-Role"] != match.group("role"):
            raise ExactShaGateError("evidence role differs from its dated filename")
        if fields["Evidence-State"] not in {"draft", "pass"}:
            raise ExactShaGateError("evidence state is outside the transition vocabulary")
        if cls._SHA.fullmatch(fields["Exact-SHA"]) is None:
            raise ExactShaGateError("evidence record lacks an exact executable SHA")
        if not content.startswith("# ") or "\x00" in content:
            raise ExactShaGateError("evidence record is not canonical UTF-8 Markdown")
        return fields

    @staticmethod
    def _immutable_body(content: str) -> str:
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Evidence-State: "):
                lines.append("Evidence-State: <FINALIZATION-STATE>\n")
            elif line.startswith("Exact-SHA: "):
                lines.append("Exact-SHA: <FINALIZATION-SHA>\n")
            else:
                lines.append(line)
        return "".join(lines)

    def classify(
        self,
        paths: Sequence[str],
        contents: Mapping[str, str],
        *,
        previous_contents: Mapping[str, str],
        file_modes: Mapping[str, int] | None = None,
    ) -> list[str]:
        safe = safe_relative_paths(list(paths), "evidence delta")
        for path in safe:
            content = contents.get(path)
            previous = previous_contents.get(path)
            if not isinstance(content, str) or not isinstance(previous, str):
                raise ExactShaGateError("final evidence content is missing or non-textual")
            current_record = self._record(path, content)
            previous_record = self._record(path, previous)
            if previous_record["Evidence-Role"] != current_record["Evidence-Role"]:
                raise ExactShaGateError("evidence role changed during finalization")
            if previous_record["Evidence-State"] != "draft" or current_record["Evidence-State"] != "pass":
                raise ExactShaGateError("evidence finalization must be exactly draft-to-pass")
            if self._immutable_body(previous) != self._immutable_body(content):
                raise ExactShaGateError(
                    "evidence finalization changed non-enumerated artifact content"
                )
            mode = (file_modes or {}).get(path)
            if mode is None and self.repository_root is not None:
                candidate = self.repository_root / path
                try:
                    info = candidate.lstat()
                except OSError as exc:
                    raise ExactShaGateError("evidence file cannot be observed") from exc
                mode = info.st_mode
            if mode is None or not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                raise ExactShaGateError("evidence artifact must be an observed regular non-symlink file")
        return safe

    def finalize(self, *, paths: Sequence[str], contents: Mapping[str, str], previous_contents: Mapping[str, str], file_modes: Mapping[str, int] | None = None, finalization_count: int, stage: Callable[[Sequence[str]], None], commit: Callable[[str], str]) -> dict[str, Any]:
        if finalization_count != 0:
            raise ExactShaGateError("a second evidence finalization commit is forbidden")
        classified = self.classify(paths, contents, previous_contents=previous_contents, file_modes=file_modes)
        stage(classified)
        head = exact_sha(commit("Finalize delivery evidence"), "final evidence head")
        return {"headSha": head, "stagedPaths": classified, "evidenceFinalizationCount": 1, "deltaDigest": sha256_json({path: contents[path] for path in classified})}

    @staticmethod
    def require_provider_head(local_head: str, provider_head: str) -> None:
        if exact_sha(local_head) != exact_sha(provider_head):
            raise ExactShaGateError("provider-observed final head differs from evidence commit")

    @staticmethod
    def require_final_evidence(*, exact_sha_value: str, attestations: Mapping[str, Mapping[str, Any]], qa_reuse: Mapping[str, Any] | None = None) -> None:
        exact_sha(exact_sha_value)
        for kind in ("exact-head-aggregate", "review", "docs"):
            if attestations.get(kind, {}).get("exactSha") != exact_sha_value:
                raise ExactShaGateError(f"final-head {kind} attestation is missing or stale")
        qa = attestations.get("qa")
        if qa is not None and qa.get("exactSha") == exact_sha_value:
            return
        if not qa_reuse or qa_reuse.get("toSha") != exact_sha_value or not qa_reuse.get("safeNoBehavioralEffect") or not qa_reuse.get("reviewer"):
            raise ExactShaGateError("QA must rerun or carry an explicit safe two-SHA reuse attestation")
