"""Windows-safe work-key, slug, collision, containment, and reparse checks."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import unicodedata
from datetime import date
from pathlib import Path
from typing import Iterable

from .errors import CollisionError, UnsafePathError, ValidationError

LINEAR_KEY_PATTERN = re.compile(r"^SAAS-[1-9][0-9]*$")
LOCAL_KEY_PATTERN = re.compile(r"^[0-9]{3,}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?$")
REPOSITORY_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
WINDOWS_INVALID_CHARACTERS = set('<>:"/\\|?*')
WINDOWS_DEVICE_PATTERN = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.I)
CURRENT_ARTIFACT_ROOT = Path(".ai") / "work"
LEGACY_ARTIFACT_ROOT = Path("docs-ai")
CURRENT_ARTIFACT_SEQUENCE_PATTERN = re.compile(r"^(?:0[2-9]|[1-9][0-9]+)$")


def validate_provider_key(provider: str, key: str) -> str:
    if not isinstance(provider, str) or provider.casefold() != "linear":
        raise ValidationError(f"Unsupported provider for canonical work-key validation: {provider}")
    if not isinstance(key, str) or not LINEAR_KEY_PATTERN.fullmatch(key):
        raise ValidationError("Linear work key must match ^SAAS-[1-9][0-9]*$")
    return key


def validate_local_key(key: str) -> str:
    if not LOCAL_KEY_PATTERN.fullmatch(key):
        raise ValidationError("Local work key must be an allocator-generated zero-padded sequence")
    return key


def validate_repository_key(key: str) -> str:
    if not isinstance(key, str) or not REPOSITORY_KEY_PATTERN.fullmatch(key):
        raise ValidationError("repositoryKey must be lowercase ASCII and match the canonical grammar")
    return key


def _reject_unsafe_explicit_display(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValidationError("Display text must be a non-empty string")
    if value in {".", ".."} or any(character in WINDOWS_INVALID_CHARACTERS for character in value):
        raise ValidationError("Unsafe path-like display text is rejected before slug normalization")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValidationError("Control characters are not allowed in display text")
    if value.endswith((".", " ")):
        raise ValidationError("Display text may not end with a dot or space")
    if WINDOWS_DEVICE_PATTERN.fullmatch(value.strip()):
        raise ValidationError("Windows device names are not valid display text for workflow paths")


def normalize_slug(display_text: str) -> str:
    _reject_unsafe_explicit_display(display_text)
    ascii_text = unicodedata.normalize("NFKD", display_text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-").lower()
    slug = re.sub(r"-+", "-", slug)
    if len(slug) > 48:
        slug = slug[:48].rstrip("-")
    return validate_slug(slug)


def validate_slug(slug: str) -> str:
    if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
        raise ValidationError(
            "Slug must be lowercase ASCII, 1-48 characters, and match the canonical slug grammar"
        )
    if WINDOWS_DEVICE_PATTERN.fullmatch(slug):
        raise ValidationError("Windows device names are not valid slugs")
    return slug


def is_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse_attribute) or os.path.ismount(path)


def ensure_safe_descendant(root: Path, candidate: Path, *, candidate_may_not_exist: bool = True) -> Path:
    """Prove strict lexical and physical containment and reject reparse components."""

    root_absolute = Path(os.path.abspath(root))
    candidate_absolute = Path(os.path.abspath(candidate))
    try:
        lexical_common = Path(os.path.commonpath([root_absolute, candidate_absolute]))
    except ValueError as exc:
        raise UnsafePathError("Candidate and artifact root are on incompatible path roots") from exc
    if os.path.normcase(os.fspath(lexical_common)) != os.path.normcase(os.fspath(root_absolute)):
        raise UnsafePathError("Candidate escapes the intended managed root")
    if os.path.normcase(os.fspath(candidate_absolute)) == os.path.normcase(os.fspath(root_absolute)):
        raise UnsafePathError("Candidate must be a strict descendant of the managed root")

    root_resolved = Path(os.path.realpath(root_absolute))
    candidate_resolved = Path(os.path.realpath(candidate_absolute))
    try:
        physical_common = Path(os.path.commonpath([root_resolved, candidate_resolved]))
    except ValueError as exc:
        raise UnsafePathError("Resolved candidate and artifact root are incompatible") from exc
    if os.path.normcase(os.fspath(physical_common)) != os.path.normcase(os.fspath(root_resolved)):
        raise UnsafePathError("Resolved candidate escapes the intended managed root")
    if os.path.normcase(os.fspath(candidate_resolved)) == os.path.normcase(os.fspath(root_resolved)):
        raise UnsafePathError("Resolved artifact folder is not a strict descendant")

    components = [root_absolute]
    relative = candidate_absolute.relative_to(root_absolute)
    current = root_absolute
    for component in relative.parts:
        current = current / component
        components.append(current)
    for index, component in enumerate(components):
        if not component.exists():
            if index < len(components) - 1 or not candidate_may_not_exist:
                continue
            continue
        if is_reparse_point(component):
            raise UnsafePathError(f"Reparse, junction, symlink, or mount component rejected: {component}")
    return candidate_absolute


def current_artifact_root(repository_root: Path) -> Path:
    return Path(os.path.abspath(repository_root)) / CURRENT_ARTIFACT_ROOT


def legacy_artifact_root(repository_root: Path) -> Path:
    return Path(os.path.abspath(repository_root)) / LEGACY_ARTIFACT_ROOT


def registered_artifact_root(
    repository_root: Path,
    artifact_folder: Path,
    *,
    candidate_may_not_exist: bool = True,
) -> tuple[str, Path]:
    """Classify an exact direct child of the current or registered legacy root."""

    repository = Path(os.path.abspath(repository_root))
    artifact = Path(os.path.abspath(artifact_folder))
    current = current_artifact_root(repository)
    legacy = legacy_artifact_root(repository)
    artifact_parent = os.path.normcase(os.fspath(artifact.parent))
    current_key = os.path.normcase(os.fspath(current))
    legacy_key = os.path.normcase(os.fspath(legacy))
    if artifact_parent == current_key:
        ensure_safe_descendant(repository, current)
        ensure_safe_descendant(
            current,
            artifact,
            candidate_may_not_exist=candidate_may_not_exist,
        )
        return "current", current
    if artifact_parent == legacy_key:
        ensure_safe_descendant(repository, legacy)
        ensure_safe_descendant(
            legacy,
            artifact,
            candidate_may_not_exist=candidate_may_not_exist,
        )
        return "legacy", legacy
    raise UnsafePathError(
        "Registered artifact folder must be a direct child of .ai/work or the exact legacy docs-ai root"
    )


def repository_root_from_registered_artifact(artifact_folder: Path) -> Path:
    """Derive the only possible worktree root without following an arbitrary parent."""

    artifact = Path(os.path.abspath(artifact_folder))
    parent = artifact.parent
    if parent.name.casefold() == LEGACY_ARTIFACT_ROOT.name.casefold():
        return parent.parent
    if (
        parent.name.casefold() == CURRENT_ARTIFACT_ROOT.name.casefold()
        and parent.parent.name.casefold() == CURRENT_ARTIFACT_ROOT.parent.name.casefold()
    ):
        return parent.parent.parent
    raise UnsafePathError("Registry artifact path is outside every managed artifact root")


def validate_current_artifact_folder_name(
    folder_name: str,
    *,
    work_source: str,
    work_key: str,
    slug: str,
) -> None:
    token = f"local-{work_key}" if work_source == "local" else work_key
    match = re.fullmatch(
        rf"(?P<date>[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})--{re.escape(token)}--"
        rf"{re.escape(slug)}(?:--(?P<sequence>[0-9]+))?",
        folder_name,
    )
    if match is None:
        raise ValidationError("Current artifact folder does not match its descriptor identity")
    try:
        date.fromisoformat(match.group("date"))
    except ValueError as exc:
        raise ValidationError("Current artifact folder date is invalid") from exc
    sequence = match.group("sequence")
    if sequence is not None and not CURRENT_ARTIFACT_SEQUENCE_PATTERN.fullmatch(sequence):
        raise ValidationError("Current artifact collision sequence must start at --02")


def assert_effective_artifact_ignore(repository_root: Path, artifact_folder: Path) -> None:
    """Fail before creation unless the exact current root is ignored and untracked."""

    repository = Path(os.path.abspath(repository_root))
    artifact = Path(os.path.abspath(artifact_folder))
    kind, _ = registered_artifact_root(repository, artifact)
    if kind != "current":
        return

    probe = (artifact / "workflow.json").relative_to(repository).as_posix()
    commands = (
        ("check-ignore", "--quiet", "--no-index", "--", probe),
        ("check-ignore", "--quiet", "--no-index", "--", ".ai/loop.json"),
        ("ls-files", "-z", "--", CURRENT_ARTIFACT_ROOT.as_posix()),
    )
    results: list[subprocess.CompletedProcess[bytes]] = []
    for arguments in commands:
        try:
            results.append(
                subprocess.run(
                    [
                        "git",
                        "--no-optional-locks",
                        "-C",
                        os.fspath(repository),
                        *arguments,
                    ],
                    check=False,
                    capture_output=True,
                    shell=False,
                )
            )
        except OSError as exc:
            raise ValidationError("Git is unavailable for the artifact ignore preflight") from exc

    artifact_ignore, loop_ignore, tracked = results
    if artifact_ignore.returncode != 0:
        raise ValidationError(".ai/work is not effectively ignored for the managed artifact")
    if loop_ignore.returncode == 0:
        raise ValidationError(".ai/loop.json must remain visible to Git")
    if loop_ignore.returncode != 1:
        raise ValidationError("Git could not verify .ai/loop.json visibility")
    if tracked.returncode != 0:
        raise ValidationError("Git could not verify the .ai/work tracked-path boundary")
    if tracked.stdout:
        raise ValidationError(".ai/work contains tracked paths and cannot receive managed artifacts")


def reject_case_insensitive_collision(candidate_name: str, names: Iterable[str]) -> None:
    folded = candidate_name.casefold()
    if any(name.casefold() == folded for name in names):
        raise CollisionError(f"Case-insensitive artifact collision for {candidate_name}")


def existing_artifact_names(artifact_root: Path, registry_paths: Iterable[str]) -> set[str]:
    names: set[str] = set()
    root = Path(os.path.abspath(artifact_root))
    for location in iter_safe_artifact_scan_locations(root, include_history=False):
        names.update(child.name for child in location.iterdir())
    for raw in registry_paths:
        path = Path(os.path.abspath(raw))
        if os.path.normcase(os.fspath(path.parent)) == os.path.normcase(os.fspath(root)):
            names.add(path.name)
    return names


def iter_safe_artifact_scan_locations(
    artifact_root: Path,
    *,
    include_history: bool = True,
) -> Iterable[Path]:
    """Yield current/history scan roots only after containment and reparse proof."""

    root = Path(os.path.abspath(artifact_root))
    if not os.path.lexists(root):
        return
    if not root.is_dir() or is_reparse_point(root):
        raise UnsafePathError("Artifact scan root must be a non-reparse directory")
    yield root
    if not include_history:
        return
    history = root / "history"
    if not os.path.lexists(history):
        return
    safe_history = ensure_safe_descendant(root, history, candidate_may_not_exist=False)
    if not safe_history.is_dir() or is_reparse_point(safe_history):
        raise UnsafePathError("Artifact history must be a contained non-reparse directory")
    yield safe_history


def ensure_safe_relative_path(value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise UnsafePathError("Change path must be a non-empty canonical forward-slash path")
    if value.startswith(("/", "//")) or re.match(r"^[A-Za-z]:", value):
        raise UnsafePathError(f"Unsafe relative path in change manifest: {value}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise UnsafePathError(f"Unsafe relative path in change manifest: {value}")
    for part in parts:
        if (
            any(character in WINDOWS_INVALID_CHARACTERS for character in part)
            or any(ord(character) < 32 or ord(character) == 127 for character in part)
            or part.endswith((".", " "))
            or WINDOWS_DEVICE_PATTERN.fullmatch(part)
        ):
            raise UnsafePathError(f"Windows-invalid change path: {value}")
    return Path(*parts)


def validate_expected_path_scope(values: Iterable[str]) -> list[Path]:
    if isinstance(values, (str, bytes)):
        raise ValidationError("Expected changed-path scope must be an array")
    result: list[Path] = []
    seen: set[str] = set()
    for value in values:
        path = ensure_safe_relative_path(value)
        canonical = path.as_posix()
        folded = canonical.casefold()
        if folded in seen:
            raise ValidationError("Expected changed-path scope contains a duplicate or case alias")
        seen.add(folded)
        result.append(path)
    if not result:
        raise ValidationError("Expected changed-path scope must contain at least one path")
    return sorted(result, key=lambda item: item.as_posix().casefold())
