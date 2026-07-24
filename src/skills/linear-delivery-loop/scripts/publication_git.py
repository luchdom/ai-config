"""Contained Git manifest reconciliation and scoped staging."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .publication_records import PublicationRecordError, safe_relative_paths, sha256_json

PRIMARY_BRANCH = re.compile(r"^codex/(?P<issue>[A-Z][A-Z0-9]+-[1-9][0-9]*)-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")
REPAIR_BRANCH = re.compile(r"^codex/(?P<issue>[A-Z][A-Z0-9]+-[1-9][0-9]*)-repair-(?P<attempt>[1-3])$")


class PublicationGitError(PublicationRecordError):
    pass


class PublicationGitCommittedInterruption(PublicationGitError):
    """Fixture-visible process interruption after an immutable Git commit."""


def _normalized(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path)))).replace("\\", "/")


def _run_git(repository: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(repository), *arguments],
        text=True, capture_output=True, shell=False, check=False,
    )
    if result.returncode:
        raise PublicationGitError(f"Git observation failed: {' '.join(arguments[:2])}")
    return result.stdout.strip()


def _run_git_raw(repository: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(repository), *arguments],
        text=True, capture_output=True, shell=False, check=False,
    )
    if result.returncode:
        raise PublicationGitError(f"Git observation failed: {' '.join(arguments[:2])}")
    return result.stdout


def _status_paths(repository: Path) -> tuple[list[str], bool]:
    # Porcelain's leading status column is semantic (for example `` M``).
    # Never route it through the ordinary stripped Git observer.
    raw = _run_git_raw(repository, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if not raw:
        return [], False
    fields = raw.split("\0")
    paths: list[str] = []
    conflict = False
    index = 0
    while index < len(fields) and fields[index]:
        item = fields[index]
        status, path = item[:2], item[3:].replace("\\", "/")
        conflict = conflict or "U" in status or status in {"AA", "DD"}
        if any(column in {"R", "C"} for column in status):
            index += 1
            if index >= len(fields) or not fields[index]:
                raise PublicationGitError("Git rename record is incomplete")
            paths.extend([path, fields[index].replace("\\", "/")])
        else:
            paths.append(path)
        index += 1
    return sorted(set(paths)), conflict


class PublicationGit:
    """Observe and stage only a reconciled specialist manifest."""

    __slots__ = ("repository", "expected_repository", "aggregate_runner", "fault_injector", "_common_dir", "_initial_paths")

    def __init__(
        self,
        repository: str | Path,
        *,
        expected_repository: str | Path | None = None,
        aggregate_runner: Callable[[Path], Mapping[str, Any]] | None = None,
        fault_injector: Callable[[str, str], None] | None = None,
    ) -> None:
        self.repository = Path(repository).resolve()
        self.expected_repository = Path(expected_repository or repository).resolve()
        self.aggregate_runner = aggregate_runner
        self.fault_injector = fault_injector
        if _normalized(self.repository) != _normalized(self.expected_repository):
            raise PublicationGitError("physical issue worktree does not match its registration")
        common = _run_git(self.repository, ["rev-parse", "--git-common-dir"])
        physical = _run_git(self.repository, ["rev-parse", "--show-toplevel"])
        if _normalized(physical) != _normalized(self.repository):
            raise PublicationGitError("registered issue worktree is not the physical Git worktree")
        self._common_dir = _normalized(self.repository / common)
        self._initial_paths = frozenset(_status_paths(self.repository)[0])

    @property
    def physical_fingerprint(self) -> str:
        payload = f"{_normalized(self.repository)}\0{self._common_dir}".encode()
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        paths, conflicted = _status_paths(self.repository)
        return {
            "headSha": _run_git(self.repository, ["rev-parse", "HEAD"]),
            "branch": _run_git(self.repository, ["branch", "--show-current"]),
            "changedPaths": paths,
            "conflicted": conflicted,
            "physicalWorktreeFingerprint": self.physical_fingerprint,
        }

    def reconcile_manifest(
        self,
        manifest: Sequence[str],
        *,
        preexisting_paths: Sequence[str] = (),
    ) -> list[str]:
        requested = safe_relative_paths(list(manifest), "specialist manifest")
        existing = set(safe_relative_paths(list(preexisting_paths), "pre-existing paths")) if preexisting_paths else set(self._initial_paths)
        observed, conflicted = _status_paths(self.repository)
        if conflicted:
            raise PublicationGitError("conflicted Git state cannot be published")
        observed_set = set(observed)
        if set(requested) & existing:
            raise PublicationGitError("specialist manifest overlaps pre-existing changes")
        if observed_set - existing != set(requested):
            raise PublicationGitError("specialist manifest does not equal the real Git diff")
        return requested

    def pre_stage_and_stage(
        self,
        manifest: Sequence[str],
        *,
        preexisting_paths: Sequence[str] = (),
    ) -> dict[str, Any]:
        paths = self.reconcile_manifest(manifest, preexisting_paths=preexisting_paths)
        if self.aggregate_runner is None:
            raise PublicationGitError("trusted issue-worktree aggregate is not configured")
        aggregate = dict(self.aggregate_runner(self.repository))
        if aggregate.get("exitCode") != 0:
            raise PublicationGitError("issue-worktree aggregate failed before staging")
        subprocess.run(
            ["git", "-C", os.fspath(self.repository), "add", "--", *paths],
            shell=False, check=True, capture_output=True, text=True,
        )
        staged = _run_git(self.repository, ["diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB"]).splitlines()
        if sorted(staged) != paths:
            raise PublicationGitError("Git staged scope differs from reconciled manifest")
        return {"paths": paths, "aggregate": aggregate, "fingerprint": self.physical_fingerprint}

    @staticmethod
    def validate_primary_branch(issue_id: str, branch: str) -> str:
        match = PRIMARY_BRANCH.fullmatch(branch)
        if match is None or match.group("issue") != issue_id or REPAIR_BRANCH.fullmatch(branch):
            raise PublicationGitError("primary branch must use codex/<issue>-<slug>")
        return branch

    @staticmethod
    def validate_repair_branch(issue_id: str, branch: str, attempt: int) -> str:
        match = REPAIR_BRANCH.fullmatch(branch)
        if match is None or match.group("issue") != issue_id or int(match.group("attempt")) != attempt:
            raise PublicationGitError("repair branch identity is invalid")
        return branch

    def create_branch(self, *, issue_id: str, branch: str, base_ref: str = "main") -> None:
        self.validate_primary_branch(issue_id, branch)
        if base_ref != "main":
            raise PublicationGitError("primary branch must originate from main")
        subprocess.run(["git", "-C", os.fspath(self.repository), "switch", "-c", branch, base_ref], shell=False, check=True, capture_output=True, text=True)

    def create_repair_branch(self, *, issue_id: str, attempt: int, current_main_sha: str) -> str:
        branch = f"codex/{issue_id}-repair-{attempt}"
        self.validate_repair_branch(issue_id, branch, attempt)
        if _run_git(self.repository, ["rev-parse", "main"]) != current_main_sha:
            raise PublicationGitError("repair must originate from current main")
        subprocess.run(["git", "-C", os.fspath(self.repository), "switch", "-c", branch, current_main_sha], shell=False, check=True, capture_output=True, text=True)
        return branch

    def branch_head(self, branch: str) -> str:
        """Read the real full head for an existing local numbered branch."""
        return _run_git(self.repository, ["rev-parse", "--verify", f"refs/heads/{branch}"])

    def read_head_bytes(self, path: str) -> bytes:
        safe = safe_relative_paths([path], "draft evidence path")[0]
        result = subprocess.run(
            ["git", "-C", os.fspath(self.repository), "show", f"HEAD:{safe}"],
            shell=False, check=False, capture_output=True,
        )
        if result.returncode:
            raise PublicationGitError("draft evidence is absent from the exact pre-finalization head")
        return result.stdout

    def prepare_primary(
        self, *, issue_id: str, branch: str, manifest: Sequence[str],
        preexisting_paths: Sequence[str] = (), operation_id: str,
    ) -> dict[str, Any]:
        """Create/read back the primary branch after aggregate-first scoped staging."""

        self.validate_primary_branch(issue_id, branch)
        base_sha = _run_git(self.repository, ["rev-parse", "main"])
        current = _run_git(self.repository, ["branch", "--show-current"])
        if current == branch:
            replay = self.reconcile_committed_operation(
                operation_id=operation_id, paths=manifest,
                trailer="Publication-Operation", preexisting_paths=preexisting_paths,
            )
            if replay is not None:
                return {"branch": branch, "baseSha": replay["baseSha"], "headSha": replay["headSha"],
                    "paths": replay["paths"], "manifestDigest": replay["manifestDigest"],
                    "aggregateDigest": replay["aggregateDigest"]}
        if current != branch:
            self.create_branch(issue_id=issue_id, branch=branch)
        staged = self.pre_stage_and_stage(manifest, preexisting_paths=preexisting_paths)
        manifest_digest = "sha256:" + hashlib.sha256("\0".join(staged["paths"]).encode()).hexdigest()
        aggregate_digest = "sha256:" + hashlib.sha256(repr(sorted(staged["aggregate"].items())).encode()).hexdigest()
        subprocess.run(
            ["git", "-C", os.fspath(self.repository), "commit", "-m", "Prepare publication",
             "-m", f"Publication-Operation: {operation_id}\nManifest-Digest: {manifest_digest}\nAggregate-Digest: {aggregate_digest}\nBase-SHA: {base_sha}"],
            shell=False, check=True, capture_output=True, text=True,
        )
        head_sha = self.branch_head(branch)
        if self.fault_injector is not None:
            try: self.fault_injector("prepare-committed", operation_id)
            except Exception as exc: raise PublicationGitCommittedInterruption("interrupted after preparation commit") from exc
        if set(_status_paths(self.repository)[0]) - set(self._initial_paths):
            raise PublicationGitError("publication worktree is dirty after primary commit")
        return {
            "branch": branch, "baseSha": base_sha, "headSha": head_sha,
            "paths": staged["paths"],
            "manifestDigest": manifest_digest, "aggregateDigest": aggregate_digest,
        }

    def finalize_evidence(self, paths: Sequence[str], *, operation_id: str) -> dict[str, Any]:
        """Read draft/current evidence from Git and create the sole scoped commit."""

        from .exact_sha_gates import EvidenceConvergence

        safe = safe_relative_paths(list(paths), "evidence paths")
        replay = self._replay_commit(operation_id, safe, "Evidence-Finalization-Operation")
        if replay is not None:
            return {"headSha": replay["headSha"], "stagedPaths": replay["paths"],
                "evidenceFinalizationCount": 1, "deltaDigest": replay["deltaDigest"]}
        contents = {path: (self.repository / path).read_text(encoding="utf-8") for path in safe}
        previous = {path: _run_git(self.repository, ["show", f"HEAD:{path}"]) + "\n" for path in safe}
        modes = {path: (self.repository / path).lstat().st_mode for path in safe}
        result = EvidenceConvergence(repository_root=self.repository).finalize(
            paths=safe, contents=contents, previous_contents=previous, file_modes=modes,
            finalization_count=0,
            stage=lambda selected: subprocess.run(
                ["git", "-C", os.fspath(self.repository), "add", "--", *selected],
                shell=False, check=True, capture_output=True, text=True,
            ),
            commit=lambda message: self._commit(
                message + "\n\n" + f"Evidence-Finalization-Operation: {operation_id}",
                operation_id=operation_id,
            ),
        )
        if set(_status_paths(self.repository)[0]) - set(self._initial_paths):
            raise PublicationGitError("publication worktree is dirty after evidence finalization")
        return result

    def _commit(self, message: str, *, operation_id: str | None = None) -> str:
        subprocess.run(
            ["git", "-C", os.fspath(self.repository), "commit", "-m", message],
            shell=False, check=True, capture_output=True, text=True,
        )
        head = _run_git(self.repository, ["rev-parse", "HEAD"])
        if self.fault_injector is not None and operation_id is not None:
            try: self.fault_injector("finalization-committed", operation_id)
            except Exception as exc: raise PublicationGitCommittedInterruption("interrupted after finalization commit") from exc
        return head

    def _replay_commit(self, operation_id: str, expected_paths: Sequence[str], trailer: str) -> dict[str, Any] | None:
        message = _run_git(self.repository, ["show", "-s", "--format=%B", "HEAD"])
        if f"{trailer}: {operation_id}" not in message:
            return None
        paths = sorted(_run_git(self.repository, ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"]).splitlines())
        if paths != safe_relative_paths(list(expected_paths), "replay paths"):
            raise PublicationGitError("replayed publication commit path identity differs")
        def trailer_value(name: str) -> str | None:
            prefix = name + ": "
            return next((line[len(prefix):] for line in message.splitlines() if line.startswith(prefix)), None)
        if trailer == "Publication-Operation":
            manifest_digest = trailer_value("Manifest-Digest")
            aggregate_digest = trailer_value("Aggregate-Digest")
            base_sha = trailer_value("Base-SHA")
            if not manifest_digest or not aggregate_digest or not base_sha:
                raise PublicationGitError("replayed preparation commit lacks immutable trailers")
            return {"headSha": self.branch_head(_run_git(self.repository, ["branch", "--show-current"])),
                "baseSha": base_sha, "paths": paths, "manifestDigest": manifest_digest,
                "aggregateDigest": aggregate_digest}
        contents = {path: (self.repository / path).read_text(encoding="utf-8") for path in paths}
        return {"headSha": _run_git(self.repository, ["rev-parse", "HEAD"]), "paths": paths,
            "deltaDigest": sha256_json(contents)}

    def reconcile_committed_operation(
        self, *, operation_id: str, paths: Sequence[str], trailer: str,
        preexisting_paths: Sequence[str] = (),
    ) -> dict[str, Any] | None:
        """Read an exact already-committed operation without mutating Git."""

        allowed = set(safe_relative_paths(list(preexisting_paths), "pre-existing replay paths")) if preexisting_paths else set(self._initial_paths)
        observed, conflicted = _status_paths(self.repository)
        if conflicted:
            raise PublicationGitError("committed publication replay worktree is conflicted")
        if set(observed) - allowed:
            return None
        return self._replay_commit(operation_id, paths, trailer)

    def prepare_repair(
        self, *, issue_id: str, attempt: int, manifest: Sequence[str],
        preexisting_paths: Sequence[str], operation_id: str,
    ) -> dict[str, Any]:
        branch = f"codex/{issue_id}-repair-{attempt}"
        self.validate_repair_branch(issue_id, branch, attempt)
        if _run_git(self.repository, ["branch", "--show-current"]) != branch:
            raise PublicationGitError("repair preparation is not on its engine-created branch")
        replay = self.reconcile_committed_operation(
            operation_id=operation_id, paths=manifest,
            trailer="Publication-Operation", preexisting_paths=preexisting_paths,
        )
        if replay is not None:
            return {"branch": branch, **replay}
        staged = self.pre_stage_and_stage(manifest, preexisting_paths=preexisting_paths)
        base_sha = _run_git(self.repository, ["rev-parse", "main"])
        manifest_digest = "sha256:" + hashlib.sha256("\0".join(staged["paths"]).encode()).hexdigest()
        aggregate_digest = "sha256:" + hashlib.sha256(repr(sorted(staged["aggregate"].items())).encode()).hexdigest()
        subprocess.run(
            ["git", "-C", os.fspath(self.repository), "commit", "-m", f"Prepare repair {attempt}",
             "-m", f"Publication-Operation: {operation_id}\nManifest-Digest: {manifest_digest}\nAggregate-Digest: {aggregate_digest}\nBase-SHA: {base_sha}"],
            shell=False, check=True, capture_output=True, text=True,
        )
        if self.fault_injector is not None:
            try: self.fault_injector("repair-committed", operation_id)
            except Exception as exc: raise PublicationGitCommittedInterruption("interrupted after repair commit") from exc
        return {"branch": branch, "baseSha": base_sha, "headSha": self.branch_head(branch),
            "paths": staged["paths"], "manifestDigest": manifest_digest,
            "aggregateDigest": aggregate_digest}

    def reprepare_committed_head(self, *, branch: str, manifest: Sequence[str],
        preexisting_paths: Sequence[str], operation_id: str) -> dict[str, Any]:
        paths = safe_relative_paths(list(manifest), "drift preparation manifest")
        if _run_git(self.repository, ["branch", "--show-current"]) != branch:
            raise PublicationGitError("drift preparation branch is mismatched")
        replay = self.reconcile_committed_operation(
            operation_id=operation_id, paths=paths,
            trailer="Publication-Operation", preexisting_paths=preexisting_paths,
        )
        if replay is not None:
            return {"branch": branch, **replay}
        staged = self.pre_stage_and_stage(paths, preexisting_paths=preexisting_paths)
        base_sha = _run_git(self.repository, ["rev-parse", "origin/main"])
        manifest_digest = "sha256:" + hashlib.sha256("\0".join(paths).encode()).hexdigest()
        aggregate_digest = "sha256:" + hashlib.sha256(repr(sorted(staged["aggregate"].items())).encode()).hexdigest()
        subprocess.run(
            ["git", "-C", os.fspath(self.repository), "commit", "-m", "Prepare base-drift head",
             "-m", f"Publication-Operation: {operation_id}\nManifest-Digest: {manifest_digest}\nAggregate-Digest: {aggregate_digest}\nBase-SHA: {base_sha}"],
            shell=False, check=True, capture_output=True, text=True,
        )
        if self.fault_injector is not None:
            try: self.fault_injector("prepare-committed", operation_id)
            except Exception as exc: raise PublicationGitCommittedInterruption("interrupted after drift preparation commit") from exc
        return {"branch": branch, "baseSha": base_sha, "headSha": self.branch_head(branch),
            "paths": paths, "manifestDigest": manifest_digest, "aggregateDigest": aggregate_digest}

    def merge_origin_main(self, observed_base_sha: str) -> str:
        """Apply only the authorized ordinary no-ff merge of origin/main."""

        if _run_git(self.repository, ["branch", "--show-current"]) == "main":
            raise PublicationGitError("base drift cannot mutate main directly")
        if set(_status_paths(self.repository)[0]) - set(self._initial_paths):
            raise PublicationGitError("base drift merge requires a clean worktree")
        if _run_git(self.repository, ["rev-parse", "origin/main"]) != observed_base_sha:
            raise PublicationGitError("origin/main differs from provider-observed base SHA")
        subprocess.run(
            ["git", "-C", os.fspath(self.repository), "merge", "--no-ff", "--no-edit", "origin/main"],
            shell=False, check=True, capture_output=True, text=True,
        )
        return _run_git(self.repository, ["rev-parse", "HEAD"])
