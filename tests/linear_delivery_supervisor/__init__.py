"""Focused fixtures for the SAAS-46 deterministic supervisor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPOSITORY_ROOT / "src" / "skills" / "linear-delivery-loop" / "scripts"
PACKAGE_NAME = "tests_linear_delivery_supervisor_runtime"


def load_supervisor_package():
    existing = sys.modules.get(PACKAGE_NAME)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        SCRIPTS_ROOT / "__init__.py",
        submodule_search_locations=[str(SCRIPTS_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load supervisor package for tests")
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)
    return module
