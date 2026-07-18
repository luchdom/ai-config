"""Git-observed repository identity and exact physical worktree binding."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .errors import RepositoryIdentityError

IDENTITY_VERSION = "1.0"


def _canonical_path(value: str | Path) -> Path:
    return Path(os.path.realpath(os.path.abspath(os.fspath(value))))


def _normalized_path(value: str | Path) -> str:
    return os.path.normcase(os.fspath(_canonical_path(value))).replace("\\", "/")


def _git(repository: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", os.fspath(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            shell=False,
        )
    except (OSError, UnicodeError) as exc:
        raise RepositoryIdentityError("Git identity executable or output is unavailable") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown Git error"
        raise RepositoryIdentityError(f"Git identity probe failed: {detail}")
    value = completed.stdout.strip()
    if not value:
        raise RepositoryIdentityError(f"Git identity probe returned no value: {' '.join(arguments)}")
    return value


@dataclass(frozen=True)
class RepositoryIdentity:
    identity_version: str
    repository_id: str
    repository_root: str
    common_dir: str
    git_dir: str
    physical_worktree_fingerprint: str

    def to_json(self) -> dict[str, str]:
        return asdict(self)


def observe_repository_identity(repository: str | Path) -> RepositoryIdentity:
    requested = _canonical_path(repository)
    root = _canonical_path(_git(requested, "rev-parse", "--show-toplevel"))

    common_raw = _git(requested, "rev-parse", "--git-common-dir")
    common_candidate = Path(common_raw)
    if not common_candidate.is_absolute():
        # Git documents relative path output against the invocation working directory.
        common_candidate = requested / common_candidate
    common_dir = _canonical_path(common_candidate)

    git_raw = _git(requested, "rev-parse", "--absolute-git-dir")
    git_dir = _canonical_path(git_raw)

    common_norm = _normalized_path(common_dir)
    root_norm = _normalized_path(root)
    git_norm = _normalized_path(git_dir)
    repository_digest = hashlib.sha256(f"git-common-dir\0{common_norm}".encode()).hexdigest()
    fingerprint_digest = hashlib.sha256(
        f"repository\0{repository_digest}\0worktree\0{root_norm}\0git-dir\0{git_norm}".encode()
    ).hexdigest()
    return RepositoryIdentity(
        identity_version=IDENTITY_VERSION,
        repository_id=f"repo-{repository_digest[:24]}",
        repository_root=os.fspath(root),
        common_dir=os.fspath(common_dir),
        git_dir=os.fspath(git_dir),
        physical_worktree_fingerprint=f"sha256:{fingerprint_digest}",
    )


def identity_fingerprint_payload(identity: RepositoryIdentity) -> str:
    """Return deterministic non-secret identity evidence for diagnostics/tests."""

    return json.dumps(identity.to_json(), sort_keys=True, separators=(",", ":"))
