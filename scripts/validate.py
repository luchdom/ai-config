"""Run the authoritative, dependency-free local validation gate.

The manifest is deliberately repository-local and only supports fixed command and
unittest-discovery steps.  It never installs or syncs generated output into a
real user or project home.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation" / "manifest.json"
SUPPORTED_STEP_TYPES = {"command", "unittest-discovery"}
ALLOWED_COMMAND_ARGV = {
    ("{python}", "scripts/build.py"),
    ("{python}", "scripts/test_sync_markers.py"),
}
ALLOWED_UNITTEST_DISCOVERY = {("tests", "test*.py")}
TOP_LEVEL_FIELDS = {"schemaVersion", "steps"}
STEP_FIELDS = {
    "command": {"name", "type", "argv"},
    "unittest-discovery": {"name", "type", "startDirectory", "pattern"},
}


class ManifestError(ValueError):
    """Raised when the local gate manifest is unsafe or malformed."""


def _repo_path(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ManifestError(f"Manifest path escapes the repository: {relative}") from exc
    return candidate


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    if not path.is_file():
        raise ManifestError(f"Validation manifest is missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != TOP_LEVEL_FIELDS:
        raise ManifestError("Validation manifest contains unknown or missing top-level fields.")
    if data.get("schemaVersion") != 1:
        raise ManifestError("validation/manifest.json must use schemaVersion 1.")

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ManifestError("Validation manifest must contain at least one step.")

    names: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            raise ManifestError("Every validation step must be an object.")
        name = step.get("name")
        kind = step.get("type")
        if not isinstance(name, str) or not name.strip():
            raise ManifestError("Every validation step needs a non-empty name.")
        if name in names:
            raise ManifestError(f"Duplicate validation step name: {name}")
        names.add(name)
        if kind not in SUPPORTED_STEP_TYPES:
            raise ManifestError(f"Unsupported validation step type for {name}: {kind}")
        if set(step) != STEP_FIELDS[kind]:
            raise ManifestError(f"Validation step {name} contains unknown or missing fields.")
        if kind == "command":
            argv = step.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and arg for arg in argv):
                raise ManifestError(f"Command step {name} needs a non-empty string argv list.")
            command_shape = tuple(argv)
            if command_shape not in ALLOWED_COMMAND_ARGV:
                raise ManifestError(
                    f"Command step {name} is not allowlisted. Sync/install, shell wrappers, "
                    "network/provider/CI commands, inline code, and extra arguments are prohibited."
                )
            script = _repo_path(argv[1])
            if not script.is_file():
                raise ManifestError(f"Command step {name} references a missing script: {argv[1]}")
        else:
            start = step.get("startDirectory")
            pattern = step.get("pattern")
            if not isinstance(start, str) or not isinstance(pattern, str):
                raise ManifestError(f"Unittest step {name} needs string startDirectory and pattern fields.")
            if (start, pattern) not in ALLOWED_UNITTEST_DISCOVERY:
                raise ManifestError(
                    f"Unittest step {name} must use the fixed repository-local tests/test*.py discovery shape."
                )
            if not _repo_path(start).is_dir():
                raise ManifestError(f"Unittest step {name} has a missing startDirectory: {start}")
    return data


def command_for(step: dict[str, Any]) -> list[str]:
    if step["type"] == "command":
        return [sys.executable if value == "{python}" else value for value in step["argv"]]
    return [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(_repo_path(step["startDirectory"])),
        "-t",
        str(ROOT),
        "-p",
        step["pattern"],
        "-v",
    ]


def main() -> int:
    try:
        manifest = load_manifest()
    except (ManifestError, json.JSONDecodeError) as exc:
        print(f"VALIDATION MANIFEST ERROR: {exc}", file=sys.stderr)
        return 2

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for step in manifest["steps"]:
        command = command_for(step)
        print(f"\n==> {step['name']}: {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
        if result.returncode:
            print(f"\nFAILED: {step['name']} (exit {result.returncode})", file=sys.stderr)
            return result.returncode

    print("\nLocal validation gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
