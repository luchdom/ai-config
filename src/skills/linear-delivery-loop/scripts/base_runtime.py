"""Load the exact sibling SAAS-45 base package and reject drift.

This module deliberately contains no repository identity, state-home, mutex,
registry, descriptor, or Handoff implementation.  It only verifies and returns
the canonical sibling package in source and generated/installed skill layouts.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


EXPECTED_BASE_VERSIONS = {
    "BASE_PACKAGE_VERSION": "1.0",
    "IDENTITY_VERSION": "1.0",
    "STATE_HOME_VERSION": "2.0",
    "REGISTRY_VERSION": "1.0",
    "WORK_DESCRIPTOR_VERSION": "2.0",
}

REQUIRED_EXPORTS = frozenset(
    {
        *EXPECTED_BASE_VERSIONS,
        "ProviderObservedWork",
        "RepositoryIdentity",
        "WorkflowManager",
        "WorkflowRegistry",
        "derive_state_home",
        "ensure_state_home",
        "inspect_historical_artifact",
        "observe_repository_identity",
        "validate_descriptor",
    }
)


class BaseRuntimeError(RuntimeError):
    """The canonical base package is absent, ambiguous, or incompatible."""


@dataclass(frozen=True)
class BaseRuntime:
    """Verified references to the canonical base package and supporting modules."""

    package: ModuleType
    scripts_path: Path
    package_version: str
    identity_version: str
    state_home_version: str
    registry_version: str
    work_descriptor_version: str
    WorkflowManager: type[Any]
    WorkflowRegistry: type[Any]
    RepositoryIdentity: type[Any]
    observe_repository_identity: Any
    derive_state_home: Any
    ensure_state_home: Any
    validate_descriptor: Any
    workflow_managed_handoff: Any
    redact_value: Any
    StatePathGuard: type[Any]
    AllocationMutex: type[Any]
    ValidationError: type[Exception]
    UnsafePathError: type[Exception]
    HandoffError: type[Exception]


_PACKAGE_NAME = "_luchdom_goal_to_delivery_base_v1"
_CACHE: dict[str, BaseRuntime] = {}


def _canonical(path: str | Path) -> Path:
    return Path(os.path.realpath(os.path.abspath(os.fspath(path))))


def _scripts_path(anchor: str | Path | None) -> Path:
    current = _canonical(anchor or __file__)
    autonomous_scripts = current if current.is_dir() else current.parent
    expected_name = "scripts"
    if autonomous_scripts.name != expected_name or autonomous_scripts.parent.name != "linear-delivery-loop":
        raise BaseRuntimeError(
            "Base loader must execute from the linear-delivery-loop/scripts layout"
        )
    candidate = _canonical(
        autonomous_scripts.parent.parent / "goal-to-delivery" / "scripts"
    )
    if candidate == autonomous_scripts or candidate.parent.name != "goal-to-delivery":
        raise BaseRuntimeError("Canonical goal-to-delivery sibling path is invalid")
    if not candidate.is_dir() or not (candidate / "__init__.py").is_file():
        raise BaseRuntimeError("Canonical goal-to-delivery sibling package is missing")
    return candidate


def _origin(module: ModuleType) -> Path:
    raw = getattr(module, "__file__", None)
    if not raw:
        raise BaseRuntimeError(f"Loaded module {module.__name__!r} has no file origin")
    return _canonical(raw)


def _contained(scripts_path: Path, origin: Path) -> bool:
    try:
        origin.relative_to(scripts_path)
    except ValueError:
        return False
    return True


def _verify_object_origin(value: Any, scripts_path: Path, export_name: str) -> None:
    module_name = getattr(value, "__module__", None)
    if not module_name or module_name == "builtins":
        raise BaseRuntimeError(f"Base export {export_name} has no verifiable module origin")
    module = sys.modules.get(module_name)
    if module is None or not _contained(scripts_path, _origin(module)):
        raise BaseRuntimeError(f"Base export {export_name} did not originate in the sibling package")


def _load_package(scripts_path: Path, *, force_reload: bool) -> ModuleType:
    cache_key = os.path.normcase(os.fspath(scripts_path))
    module_name = f"{_PACKAGE_NAME}_{abs(hash(cache_key)):x}"
    existing = sys.modules.get(module_name)
    if existing is not None and not force_reload:
        if _origin(existing) != scripts_path / "__init__.py":
            raise BaseRuntimeError("Cached base package origin differs from the canonical sibling")
        return existing
    if force_reload and existing is not None:
        for name in sorted(
            (key for key in sys.modules if key == module_name or key.startswith(module_name + ".")),
            reverse=True,
        ):
            del sys.modules[name]

    init_path = scripts_path / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        module_name,
        init_path,
        submodule_search_locations=[os.fspath(scripts_path)],
    )
    if spec is None or spec.loader is None:
        raise BaseRuntimeError("Cannot construct the canonical base package loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise BaseRuntimeError("Canonical base package failed to load") from exc
    if _origin(module) != init_path:
        raise BaseRuntimeError("Loaded base package origin differs from the canonical sibling")
    return module


def load_base_runtime(
    anchor: str | Path | None = None,
    *,
    force_reload: bool = False,
) -> BaseRuntime:
    """Return the verified canonical base runtime for the current skill layout."""

    scripts_path = _scripts_path(anchor)
    cache_key = os.path.normcase(os.fspath(scripts_path))
    if not force_reload and cache_key in _CACHE:
        return _CACHE[cache_key]

    package = _load_package(scripts_path, force_reload=force_reload)
    missing = REQUIRED_EXPORTS - set(vars(package))
    if missing:
        raise BaseRuntimeError(f"Canonical base package lacks exports: {', '.join(sorted(missing))}")
    for name, expected in EXPECTED_BASE_VERSIONS.items():
        if getattr(package, name) != expected:
            raise BaseRuntimeError(f"Canonical base {name} must equal {expected}")

    for export_name in (
        "WorkflowManager",
        "WorkflowRegistry",
        "RepositoryIdentity",
        "observe_repository_identity",
        "derive_state_home",
        "ensure_state_home",
        "validate_descriptor",
    ):
        _verify_object_origin(getattr(package, export_name), scripts_path, export_name)

    try:
        handoff = importlib.import_module(f"{package.__name__}.handoff")
        redaction = importlib.import_module(f"{package.__name__}.redaction")
        state_paths = importlib.import_module(f"{package.__name__}.state_paths")
        mutex = importlib.import_module(f"{package.__name__}.mutex")
        errors = importlib.import_module(f"{package.__name__}.errors")
    except Exception as exc:
        raise BaseRuntimeError("Canonical Handoff or redaction module failed to load") from exc
    supporting = (handoff, redaction, state_paths, mutex, errors)
    if any(not _contained(scripts_path, _origin(module)) for module in supporting):
        raise BaseRuntimeError("Canonical supporting module origin differs from the sibling package")
    for module, name in ((handoff, "workflow_managed_handoff"), (redaction, "redact_value")):
        if not callable(getattr(module, name, None)):
            raise BaseRuntimeError(f"Canonical supporting export {name} is missing")

    runtime = BaseRuntime(
        package=package,
        scripts_path=scripts_path,
        package_version=package.BASE_PACKAGE_VERSION,
        identity_version=package.IDENTITY_VERSION,
        state_home_version=package.STATE_HOME_VERSION,
        registry_version=package.REGISTRY_VERSION,
        work_descriptor_version=package.WORK_DESCRIPTOR_VERSION,
        WorkflowManager=package.WorkflowManager,
        WorkflowRegistry=package.WorkflowRegistry,
        RepositoryIdentity=package.RepositoryIdentity,
        observe_repository_identity=package.observe_repository_identity,
        derive_state_home=package.derive_state_home,
        ensure_state_home=package.ensure_state_home,
        validate_descriptor=package.validate_descriptor,
        workflow_managed_handoff=handoff.workflow_managed_handoff,
        redact_value=redaction.redact_value,
        StatePathGuard=state_paths.StatePathGuard,
        AllocationMutex=mutex.AllocationMutex,
        ValidationError=errors.ValidationError,
        UnsafePathError=errors.UnsafePathError,
        HandoffError=errors.HandoffError,
    )
    _CACHE[cache_key] = runtime
    return runtime
