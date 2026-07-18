"""Canonical containment and reparse guards for repository-scoped state."""

from __future__ import annotations

import os
import json
import stat
from pathlib import Path
from typing import Iterator

from .atomic_files import atomic_write_bytes
from .errors import ConcurrentUpdateError, StateHomeError, UnsafePathError, ValidationError
from .path_safety import ensure_safe_descendant, is_reparse_point


class StatePathGuard:
    """Prove every repository-state path before and after state I/O."""

    def __init__(self, repository_root: str | Path, *, base: str | Path | None = None):
        root = Path(os.path.abspath(os.fspath(repository_root)))
        self.root = root
        self.base = Path(os.path.abspath(os.fspath(base))) if base is not None else root.parent

    def prepare_root(self) -> Path:
        """Create the root without accepting a reparse base or repository leaf."""

        try:
            self.base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StateHomeError("Cannot create state-home base safely") from exc
        self._validate_directory(self.base, label="state-home base")
        ensure_safe_descendant(self.base, self.root)
        try:
            self.root.mkdir(parents=False, exist_ok=True)
        except OSError as exc:
            raise StateHomeError("Cannot create repository state root safely") from exc
        ensure_safe_descendant(self.base, self.root, candidate_may_not_exist=False)
        self._validate_directory(self.root, label="repository state root")
        return self.root

    def validate_root(self) -> Path:
        self._validate_directory(self.root, label="repository state root")
        return self.root

    def directory(self, candidate: str | Path, *, create: bool = False) -> Path:
        path = self._contained(candidate, may_not_exist=create)
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise StateHomeError("Cannot create repository state directory safely") from exc
            path = self._contained(path, may_not_exist=False)
        self._validate_directory(path, label="repository state directory")
        return path

    def leaf(self, candidate: str | Path, *, must_exist: bool = False) -> Path:
        path = self._contained(candidate, may_not_exist=not must_exist)
        if os.path.lexists(path):
            if is_reparse_point(path) or not path.is_file():
                raise UnsafePathError("Repository state leaf must be a non-reparse regular file")
            if path.stat().st_nlink != 1:
                raise UnsafePathError("Repository state leaf must not have multiple hard links")
        elif must_exist:
            raise ValidationError("Required repository state leaf does not exist")
        self._validate_directory(path.parent, label="repository state parent")
        return path

    def read_bytes(self, candidate: str | Path) -> bytes:
        path = self.leaf(candidate, must_exist=True)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise ValidationError("Cannot open repository state leaf safely") from exc
        try:
            self.validate_open_file(path, descriptor)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            content = b"".join(chunks)
        except OSError as exc:
            raise ValidationError("Cannot read repository state leaf safely") from exc
        finally:
            os.close(descriptor)
        self.leaf(path, must_exist=True)
        return content

    def read_json(self, candidate: str | Path) -> dict:
        try:
            value = json.loads(self.read_bytes(candidate).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValidationError("Repository state leaf does not contain valid UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise ValidationError("Repository state JSON must be an object")
        return value

    def write_bytes(self, candidate: str | Path, content: bytes) -> None:
        path = self.leaf(candidate)
        try:
            atomic_write_bytes(path, content)
        except OSError as exc:
            raise ValidationError("Cannot write repository state leaf safely") from exc
        self.leaf(path, must_exist=True)

    def write_json(
        self,
        candidate: str | Path,
        value: dict,
        *,
        expected_revision: int | None = None,
    ) -> None:
        path = self.leaf(candidate)
        if expected_revision is not None:
            current_revision = self.read_json(path).get("revision") if path.exists() else 0
            if current_revision != expected_revision:
                raise ConcurrentUpdateError(
                    f"Expected repository state revision {expected_revision}, "
                    f"observed {current_revision!r}"
                )
        payload = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
        self.write_bytes(path, payload)
        if self.read_json(path) != value:
            raise ValidationError("Repository state JSON readback mismatch")

    def unlink(self, candidate: str | Path, *, missing_ok: bool = False) -> None:
        path = self.leaf(candidate, must_exist=not missing_ok)
        if not path.exists() and missing_ok:
            return
        try:
            path.unlink()
        except OSError as exc:
            raise ValidationError("Cannot remove repository state leaf safely") from exc
        self._contained(path, may_not_exist=True)

    def glob_files(self, directory: str | Path, pattern: str) -> Iterator[Path]:
        safe_directory = self.directory(directory)
        observed = list(safe_directory.glob(pattern))
        for path in sorted(observed, key=lambda item: item.name.casefold()):
            yield self.leaf(path, must_exist=True)

    def validate_open_file(self, candidate: str | Path, descriptor: int) -> None:
        path = self.leaf(candidate, must_exist=True)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise UnsafePathError("Opened repository state leaf is not a regular file")
        observed = path.stat()
        if opened.st_nlink != 1 or observed.st_nlink != 1:
            raise UnsafePathError("Repository state leaf must not have multiple hard links")
        if (opened.st_dev, opened.st_ino) != (observed.st_dev, observed.st_ino):
            raise UnsafePathError("Repository state leaf identity changed during open")
        self.leaf(path, must_exist=True)

    def _contained(self, candidate: str | Path, *, may_not_exist: bool) -> Path:
        self.validate_root()
        return ensure_safe_descendant(
            self.root,
            Path(candidate),
            candidate_may_not_exist=may_not_exist,
        )

    @staticmethod
    def _validate_directory(path: Path, *, label: str) -> None:
        if not path.exists() or not path.is_dir() or is_reparse_point(path):
            raise StateHomeError(f"{label} must be an existing non-reparse directory")
