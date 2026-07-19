from __future__ import annotations

import ast
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.linear_delivery_supervisor import REPOSITORY_ROOT, SCRIPTS_ROOT, load_supervisor_package


runtime_package = load_supervisor_package()
base_runtime = runtime_package.base_runtime


class BaseRuntimeTests(unittest.TestCase):
    def copied_layout(self, temporary: str) -> tuple[Path, Path]:
        skills = Path(temporary) / "skills"
        autonomous = skills / "linear-delivery-loop" / "scripts"
        base = skills / "goal-to-delivery" / "scripts"
        autonomous.mkdir(parents=True)
        shutil.copytree(REPOSITORY_ROOT / "src/skills/goal-to-delivery/scripts", base)
        return autonomous, base

    def test_loads_exact_canonical_base_versions_and_origins(self) -> None:
        runtime = base_runtime.load_base_runtime(force_reload=True)
        self.assertEqual(runtime.package_version, "1.0")
        self.assertEqual(runtime.identity_version, "1.0")
        self.assertEqual(runtime.state_home_version, "2.0")
        self.assertEqual(runtime.registry_version, "1.0")
        self.assertEqual(runtime.work_descriptor_version, "2.0")
        self.assertEqual(runtime.scripts_path, (REPOSITORY_ROOT / "src/skills/goal-to-delivery/scripts").resolve())
        for value in (
            runtime.WorkflowManager,
            runtime.WorkflowRegistry,
            runtime.RepositoryIdentity,
            runtime.StatePathGuard,
            runtime.AllocationMutex,
            runtime.workflow_managed_handoff,
        ):
            module = __import__(value.__module__, fromlist=["__file__"])
            Path(module.__file__).resolve().relative_to(runtime.scripts_path)

    def test_rejects_missing_or_wrong_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="supervisor-loader-") as temporary:
            scripts = Path(temporary) / "linear-delivery-loop" / "scripts"
            scripts.mkdir(parents=True)
            with self.assertRaises(base_runtime.BaseRuntimeError):
                base_runtime.load_base_runtime(scripts, force_reload=True)
            wrong = Path(temporary) / "not-the-skill" / "scripts"
            wrong.mkdir(parents=True)
            with self.assertRaises(base_runtime.BaseRuntimeError):
                base_runtime.load_base_runtime(wrong, force_reload=True)

    def test_rejects_wrong_base_version_before_returning_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="supervisor-loader-version-") as temporary:
            autonomous, base = self.copied_layout(temporary)
            workflow = base / "workflow_init.py"
            workflow.write_text(
                workflow.read_text(encoding="utf-8").replace('BASE_PACKAGE_VERSION = "1.0"', 'BASE_PACKAGE_VERSION = "9.9"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(base_runtime.BaseRuntimeError, "BASE_PACKAGE_VERSION"):
                base_runtime.load_base_runtime(autonomous, force_reload=True)

    def test_rejects_missing_or_wrong_origin_export(self) -> None:
        for suffix, addition, pattern in (
            ("missing", "\ndel WorkflowManager\n", "lacks exports"),
            ("origin", "\nWorkflowManager = dict\n", "no verifiable module origin"),
        ):
            with self.subTest(case=suffix), tempfile.TemporaryDirectory(prefix=f"supervisor-loader-{suffix}-") as temporary:
                autonomous, base = self.copied_layout(temporary)
                init = base / "__init__.py"
                init.write_text(init.read_text(encoding="utf-8") + addition, encoding="utf-8")
                with self.assertRaisesRegex(base_runtime.BaseRuntimeError, pattern):
                    base_runtime.load_base_runtime(autonomous, force_reload=True)

    def test_autonomous_package_contains_no_copied_base_primitive(self) -> None:
        forbidden_files = {
            "atomic_files.py", "descriptor.py", "handoff.py", "identity.py", "mutex.py",
            "path_safety.py", "registry.py", "state_home.py", "state_paths.py", "workflow_init.py",
        }
        self.assertFalse(forbidden_files & {path.name for path in SCRIPTS_ROOT.glob("*.py")})
        forbidden_definitions = {
            "WorkflowManager", "WorkflowRegistry", "RepositoryIdentity", "StatePathGuard",
            "AllocationMutex", "workflow_managed_handoff", "observe_repository_identity",
            "derive_state_home", "ensure_state_home", "validate_descriptor",
        }
        defined: set[str] = set()
        for path in SCRIPTS_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            defined.update(
                node.name for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            )
        self.assertFalse(forbidden_definitions & defined)


if __name__ == "__main__":
    unittest.main()
