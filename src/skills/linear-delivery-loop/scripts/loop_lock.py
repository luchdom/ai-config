"""Acquire and release the cross-run lease for one autonomous repository queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCK_SCHEMA_VERSION = 1
LEASE_GRACE_MINUTES = 15
BUSY_EXIT = 3
ERROR_EXIT = 4
LOCK_FIELDS = {
    "schemaVersion",
    "token",
    "lockKey",
    "repositoryKey",
    "team",
    "project",
    "pid",
    "host",
    "acquiredAt",
    "acquiredAtEpoch",
    "expiresAt",
    "expiresAtEpoch",
}


class LockError(ValueError):
    """Raised when lock configuration or state is unsafe or malformed."""


@dataclass(frozen=True)
class LoopIdentity:
    repository_key: str
    team: str
    project: str
    lease_minutes: int

    @property
    def lock_key(self) -> str:
        encoded = json.dumps(
            [self.repository_key, self.team, self.project],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:32]


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LockError(f"{field} must be a non-empty string")
    return value.strip()


def load_identity(repository_root: Path) -> LoopIdentity:
    config_path = repository_root.resolve() / ".ai" / "loop.json"
    if not config_path.is_file():
        raise LockError(f"Loop configuration is missing: {config_path}")

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LockError(f"Loop configuration is unreadable: {config_path}") from exc

    if not isinstance(config, dict) or config.get("schemaVersion") != 1:
        raise LockError("Loop configuration must use schemaVersion 1")
    if config.get("enabled") is not True:
        raise LockError("Loop configuration must set enabled to true before acquiring a lease")

    linear = config.get("linear")
    limits = config.get("limits")
    if not isinstance(linear, dict) or not isinstance(limits, dict):
        raise LockError("Loop configuration requires linear and limits objects")

    max_run_minutes = limits.get("maxRunMinutes")
    if (
        not isinstance(max_run_minutes, int)
        or isinstance(max_run_minutes, bool)
        or max_run_minutes < 1
        or max_run_minutes > 1_425
    ):
        raise LockError("limits.maxRunMinutes must be an integer from 1 through 1425")

    return LoopIdentity(
        repository_key=_required_string(config.get("repositoryKey"), "repositoryKey"),
        team=_required_string(linear.get("team"), "linear.team"),
        project=_required_string(linear.get("project"), "linear.project"),
        lease_minutes=max_run_minutes + LEASE_GRACE_MINUTES,
    )


def state_root() -> Path:
    configured = os.environ.get("LUCHDOM_AI_STATE_HOME")
    if configured:
        return Path(configured).expanduser().resolve()

    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return (Path(os.environ["LOCALAPPDATA"]) / "Luchdom" / "ai-config").resolve()

    if os.environ.get("XDG_STATE_HOME"):
        return (Path(os.environ["XDG_STATE_HOME"]) / "luchdom-ai").resolve()

    return (Path.home() / ".local" / "state" / "luchdom-ai").resolve()


def lock_path(identity: LoopIdentity) -> Path:
    root = state_root() / "linear-delivery-loop" / "locks"
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise LockError(f"Lock directory cannot be a symbolic link: {root}")
    return root / f"{identity.lock_key}.json"


def _utc(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_lock(value: Any, expected_key: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != LOCK_FIELDS:
        raise LockError("Existing loop lock has an invalid shape")
    if value.get("schemaVersion") != LOCK_SCHEMA_VERSION or value.get("lockKey") != expected_key:
        raise LockError("Existing loop lock has an invalid identity")
    for field in ("token", "repositoryKey", "team", "project", "host", "acquiredAt", "expiresAt"):
        _required_string(value.get(field), f"lock.{field}")
    for field in ("pid", "acquiredAtEpoch", "expiresAtEpoch"):
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or item < 1:
            raise LockError(f"lock.{field} must be a positive integer")
    if value["expiresAtEpoch"] <= value["acquiredAtEpoch"]:
        raise LockError("Existing loop lock expires before it was acquired")
    return value


def _read_lock(path: Path, expected_key: str) -> dict[str, Any]:
    if path.is_symlink():
        raise LockError(f"Loop lock cannot be a symbolic link: {path}")
    try:
        return _validate_lock(json.loads(path.read_text(encoding="utf-8")), expected_key)
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise LockError(f"Existing loop lock is unreadable: {path}") from exc


def _write_new_lock(path: Path, value: dict[str, Any]) -> bool:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        return False

    try:
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        finally:
            os.close(descriptor)
        raise
    else:
        os.close(descriptor)
    return True


def _move_if_token_matches(path: Path, expected_key: str, token: str, suffix: str) -> Path:
    current = _read_lock(path, expected_key)
    if current["token"] != token:
        raise LockError("Loop lock ownership changed; refusing mutation")

    destination = path.with_name(f".{path.name}.{uuid.uuid4().hex}.{suffix}")
    try:
        os.replace(path, destination)
    except FileNotFoundError as exc:
        raise LockError("Loop lock disappeared during mutation") from exc

    moved = _read_lock(destination, expected_key)
    if moved["token"] != token:
        if not path.exists():
            os.replace(destination, path)
        raise LockError("Loop lock ownership changed during mutation")
    return destination


def acquire(repository_root: Path) -> tuple[int, dict[str, Any]]:
    identity = load_identity(repository_root)
    path = lock_path(identity)

    for _ in range(4):
        now = int(time.time())
        expires = now + identity.lease_minutes * 60
        token = uuid.uuid4().hex
        value = {
            "schemaVersion": LOCK_SCHEMA_VERSION,
            "token": token,
            "lockKey": identity.lock_key,
            "repositoryKey": identity.repository_key,
            "team": identity.team,
            "project": identity.project,
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "acquiredAt": _utc(now),
            "acquiredAtEpoch": now,
            "expiresAt": _utc(expires),
            "expiresAtEpoch": expires,
        }
        if _write_new_lock(path, value):
            return 0, {
                "status": "acquired",
                "token": token,
                "lockKey": identity.lock_key,
                "expiresAt": value["expiresAt"],
                "leaseMinutes": identity.lease_minutes,
            }

        try:
            existing = _read_lock(path, identity.lock_key)
        except FileNotFoundError:
            continue
        if existing["expiresAtEpoch"] > now:
            return BUSY_EXIT, {
                "status": "busy",
                "lockKey": identity.lock_key,
                "expiresAt": existing["expiresAt"],
            }

        stale = _move_if_token_matches(path, identity.lock_key, existing["token"], "stale")
        stale.unlink(missing_ok=True)

    raise LockError("Loop lock changed repeatedly; refusing acquisition")


def release(repository_root: Path, token: str) -> tuple[int, dict[str, Any]]:
    identity = load_identity(repository_root)
    path = lock_path(identity)
    try:
        released = _move_if_token_matches(path, identity.lock_key, token, "released")
    except FileNotFoundError as exc:
        raise LockError("Loop lock is already absent") from exc
    released.unlink(missing_ok=True)
    return 0, {"status": "released", "lockKey": identity.lock_key}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    acquire_parser = subparsers.add_parser("acquire", help="Acquire the repository queue lease.")
    acquire_parser.add_argument("--repo-root", required=True, type=Path)
    release_parser = subparsers.add_parser("release", help="Release an owned repository queue lease.")
    release_parser.add_argument("--repo-root", required=True, type=Path)
    release_parser.add_argument("--token", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "acquire":
            code, result = acquire(args.repo_root)
        else:
            code, result = release(args.repo_root, _required_string(args.token, "token"))
    except LockError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, separators=(",", ":")))
        return ERROR_EXIT

    print(json.dumps(result, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
