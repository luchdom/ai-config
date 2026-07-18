"""Atomic JSON primitives used by the base registry and descriptors."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import ConcurrentUpdateError, ValidationError


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"Expected a JSON object in {path}")
    return value


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Replace *path* from a same-directory temporary file and read it back."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if path.read_bytes() != content:
            raise ValidationError(f"Atomic readback mismatch for {path}")
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
    *,
    expected_revision: int | None = None,
) -> None:
    """Write deterministic JSON, optionally requiring the current revision."""

    if expected_revision is not None:
        if not path.exists():
            current_revision = 0
        else:
            current_revision = read_json(path).get("revision")
        if current_revision != expected_revision:
            raise ConcurrentUpdateError(
                f"Expected revision {expected_revision} at {path}, observed {current_revision!r}"
            )
    payload = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    atomic_write_bytes(path, payload)
    if read_json(path) != value:
        raise ValidationError(f"JSON readback mismatch for {path}")
