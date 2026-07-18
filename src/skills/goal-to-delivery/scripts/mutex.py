"""Crash-safe cross-process allocation/registry mutex."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from .errors import MutexTimeoutError, ValidationError
from .state_paths import StatePathGuard


class AllocationMutex:
    """Use an OS advisory lock; the kernel releases it when a process exits."""

    def __init__(
        self,
        path: Path,
        *,
        timeout_seconds: float = 10.0,
        poll_seconds: float = 0.025,
        state_paths: StatePathGuard | None = None,
    ):
        self.path = Path(path)
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds
        self.state_paths = state_paths
        self._token: str | None = None
        self._descriptor: int | None = None
        self._active_paths: StatePathGuard | None = None

    def acquire(self) -> "AllocationMutex":
        if self._descriptor is not None:
            raise ValidationError("AllocationMutex instances are not re-entrant")
        if not self.path.parent.exists() or not self.path.parent.is_dir():
            raise ValidationError("Allocation mutex parent must already be a safe directory")
        paths = self.state_paths or StatePathGuard(self.path.parent)
        paths.validate_root()
        lock_path = paths.leaf(self.path)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise ValidationError("Cannot open allocation mutex safely") from exc
        deadline = time.monotonic() + self.timeout_seconds
        try:
            paths.validate_open_file(lock_path, descriptor)
            while True:
                try:
                    _try_lock(descriptor)
                    break
                except (BlockingIOError, OSError) as exc:
                    if not _is_lock_contention(exc):
                        raise
                    if time.monotonic() >= deadline:
                        raise MutexTimeoutError(f"Timed out acquiring allocation mutex {self.path}") from exc
                    time.sleep(self.poll_seconds)

            previous = _read_metadata(descriptor)
            if previous and previous.get("released") is not True:
                pid = previous.get("pid")
                token = previous.get("token")
                if isinstance(pid, int) and isinstance(token, str) and not _process_is_alive(pid):
                    stale = paths.directory(self.path.parent / "stale-locks", create=True)
                    evidence = stale / f"{time.time_ns()}-{uuid.uuid4()}.json"
                    paths.write_json(evidence, previous)

            token = str(uuid.uuid4())
            metadata = {
                "token": token,
                "pid": os.getpid(),
                "createdNs": time.time_ns(),
                "released": False,
            }
            _write_metadata(descriptor, metadata)
            paths.validate_open_file(lock_path, descriptor)
            self._token = token
            self._descriptor = descriptor
            self._active_paths = paths
            return self
        except Exception:
            try:
                _unlock(descriptor)
            except Exception:
                pass
            os.close(descriptor)
            raise

    def release(self) -> None:
        if self._descriptor is None:
            return
        descriptor = self._descriptor
        try:
            assert self._active_paths is not None
            self._active_paths.validate_open_file(self.path, descriptor)
            value = _read_metadata(descriptor)
            if not value or value.get("token") != self._token:
                raise ValidationError("Allocation mutex ownership changed; refusing release")
            value["released"] = True
            value["releasedNs"] = time.time_ns()
            _write_metadata(descriptor, value)
            self._active_paths.validate_open_file(self.path, descriptor)
            _unlock(descriptor)
        finally:
            os.close(descriptor)
            self._descriptor = None
            self._token = None
            self._active_paths = None

    def __enter__(self) -> "AllocationMutex":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


def _read_metadata(descriptor: int) -> dict[str, object] | None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    raw = os.read(descriptor, 65536).rstrip(b"\0\r\n ")
    if not raw:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("Allocation mutex metadata is malformed") from exc
    if not isinstance(value, dict):
        raise ValidationError("Allocation mutex metadata must be a JSON object")
    _validate_metadata(value)
    return value


def _validate_metadata(value: dict[str, object]) -> None:
    released = value.get("released")
    expected = {"token", "pid", "createdNs", "released"}
    if released is True:
        expected.add("releasedNs")
    if set(value) != expected or not isinstance(released, bool):
        raise ValidationError("Allocation mutex metadata fields are invalid")
    token = value["token"]
    try:
        if not isinstance(token, str) or str(uuid.UUID(token)) != token:
            raise ValueError
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError("Allocation mutex token must be a canonical UUID") from exc
    for field in ("pid", "createdNs"):
        item = value[field]
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise ValidationError(f"Allocation mutex {field} must be a positive integer")
    if released is True:
        released_ns = value["releasedNs"]
        if not isinstance(released_ns, int) or isinstance(released_ns, bool) or released_ns <= 0:
            raise ValidationError("Allocation mutex releasedNs must be a positive integer")


def _write_metadata(descriptor: int, value: dict[str, object]) -> None:
    payload = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.ftruncate(descriptor, 0)
    os.write(descriptor, payload)
    os.fsync(descriptor)


def _try_lock(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        if os.fstat(descriptor).st_size == 0:
            os.write(descriptor, b"\0")
            os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _is_lock_contention(error: OSError) -> bool:
    if isinstance(error, BlockingIOError):
        return True
    return getattr(error, "winerror", None) in {33, 36} or error.errno in {11, 13}


def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        process = ctypes.windll.kernel32.OpenProcess(0x100000, False, wintypes.DWORD(pid))
        if not process:
            return ctypes.GetLastError() == 5
        try:
            exit_code = wintypes.DWORD()
            if not ctypes.windll.kernel32.GetExitCodeProcess(process, ctypes.byref(exit_code)):
                return True
            return exit_code.value == 259
        finally:
            ctypes.windll.kernel32.CloseHandle(process)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
