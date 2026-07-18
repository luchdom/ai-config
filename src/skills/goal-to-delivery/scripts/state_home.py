"""Machine-stable, repository-scoped state-home derivation and verification."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import StateHomeError
from .identity import RepositoryIdentity
from .mutex import AllocationMutex
from .path_safety import is_reparse_point, validate_repository_key
from .state_paths import StatePathGuard

STATE_HOME_VERSION = "2.0"
STATE_HOME_ENVIRONMENT = "LUCHDOM_DELIVERY_STATE_HOME"


def _resolved(path: str | Path) -> Path:
    return Path(os.path.realpath(os.path.abspath(os.fspath(path))))


def _contains(parent: Path, child: Path) -> bool:
    try:
        return os.path.commonpath([os.fspath(parent), os.fspath(child)]) == os.fspath(parent)
    except ValueError:
        return False


def _reject_reparse_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    anchor = Path(absolute.anchor)
    current = anchor
    for part in absolute.parts[1:]:
        current = current / part
        if os.path.lexists(current) and is_reparse_point(current):
            raise StateHomeError(
                "State-home base path contains a junction, symlink, mount, or reparse component"
            )


@dataclass(frozen=True)
class StateHome:
    base: Path
    repository: Path
    sentinel: Path


def derive_state_home(
    identity: RepositoryIdentity,
    *,
    override: str | Path | None = None,
    environment: dict[str, str] | None = None,
) -> StateHome:
    environment = os.environ if environment is None else environment
    configured = override if override is not None else environment.get(STATE_HOME_ENVIRONMENT)
    if configured:
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            raise StateHomeError(f"{STATE_HOME_ENVIRONMENT} must be an absolute machine-stable base")
        _reject_reparse_components(configured_path)
        base = _resolved(configured_path)
    else:
        local_app_data = environment.get("LOCALAPPDATA")
        if not local_app_data:
            raise StateHomeError("LOCALAPPDATA is required when no state-home override is configured")
        configured_path = Path(local_app_data) / "Luchdom" / "ai-delivery"
        _reject_reparse_components(configured_path)
        base = _resolved(configured_path)

    repository_root = _resolved(identity.repository_root)
    common_dir = _resolved(identity.common_dir)
    if _contains(repository_root, base) or _contains(base, repository_root):
        raise StateHomeError("State-home base must be outside the repository checkout")
    if _contains(common_dir, base) or _contains(base, common_dir):
        raise StateHomeError("State-home base must be outside the Git common directory")

    repository = _resolved(base / identity.repository_id)
    if (
        os.path.normcase(os.path.realpath(repository.parent))
        != os.path.normcase(os.path.realpath(base))
        or repository.name.casefold() != identity.repository_id.casefold()
    ):
        raise StateHomeError("Repository-scoped state home failed repo-id append verification")
    return StateHome(base=base, repository=repository, sentinel=repository / "repository.json")


def ensure_state_home(home: StateHome, identity: RepositoryIdentity, *, repository_key: str) -> StateHome:
    repository_key = validate_repository_key(repository_key)
    paths = StatePathGuard(home.repository, base=home.base)
    paths.prepare_root()
    expected = {
        "schemaVersion": STATE_HOME_VERSION,
        "repositoryId": identity.repository_id,
        "normalizedCommonDir": os.path.normcase(os.path.realpath(identity.common_dir)).replace("\\", "/"),
        "repositoryKey": repository_key,
    }

    def validate_observed(observed: dict) -> None:
        if observed.get("schemaVersion") == "1.0" and "repositoryKey" not in observed:
            raise StateHomeError(
                "Legacy state-home sentinel lacks repositoryKey authority; "
                "attended migration is required"
            )
        if observed != expected:
            raise StateHomeError(
                "State-home sentinel does not match repository identity and repositoryKey binding"
            )

    # A mismatched existing authority is rejected before even lock metadata is changed.
    sentinel = paths.leaf(home.sentinel)
    if sentinel.exists():
        validate_observed(paths.read_json(sentinel))
    # WorkflowManager instances can start simultaneously before registry.json exists.
    # Serialize the create/readback so Windows never races two os.replace calls.
    with AllocationMutex(
        paths.leaf(home.repository / "repository-init.lock"),
        state_paths=paths,
    ):
        sentinel = paths.leaf(home.sentinel)
        if sentinel.exists():
            observed = paths.read_json(sentinel)
            validate_observed(observed)
        else:
            paths.write_json(sentinel, expected)
        if paths.read_json(sentinel) != expected:
            raise StateHomeError("State-home sentinel readback failed")
    return home
