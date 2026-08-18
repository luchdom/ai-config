from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPOSITORY_ROOT / "src" / "skills" / "goal-to-delivery"
if os.fspath(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, os.fspath(SKILL_ROOT))

from scripts.workflow_init import WorkflowManager


def git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=False,
    )


def create_windows_junction(testcase: unittest.TestCase, link: Path, target: Path) -> None:
    if os.name != "nt":
        testcase.skipTest("Windows junction coverage applies only on Windows")
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=False,
    )
    if completed.returncode != 0:
        testcase.skipTest(f"Windows denied junction creation: {completed.stderr or completed.stdout}")


def file_tree_snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class RepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="goal-delivery-base-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        git(self.repository, "init", "--initial-branch=main")
        git(self.repository, "config", "user.name", "Test User")
        git(self.repository, "config", "user.email", "test@example.invalid")
        self.global_excludes = self.root / "global-excludes"
        self.global_excludes.write_text(
            "/.ai/work/\n/.ai/worktrees/\n",
            encoding="utf-8",
        )
        git(
            self.repository,
            "config",
            "core.excludesFile",
            os.fspath(self.global_excludes),
        )
        (self.repository / "README.md").write_text("base\n", encoding="utf-8")
        git(self.repository, "add", "README.md")
        git(self.repository, "commit", "-m", "initial")
        self.state_base = self.root / "state"

    def manager(self, repository: Path | None = None) -> WorkflowManager:
        return WorkflowManager(
            repository or self.repository,
            repository_key="test-repository",
            state_home_override=self.state_base,
        )

    def linked_worktree(self, name: str = "destination") -> Path:
        destination = self.root / name
        git(self.repository, "worktree", "add", "-b", name, os.fspath(destination), "HEAD")
        return destination

    def move_workflow_to_legacy(self, manager: WorkflowManager, descriptor: dict) -> dict:
        """Build an exact old-runtime registry fixture without adding adoption behavior."""

        source = Path(descriptor["artifactFolder"])
        destination = self.repository / "docs-ai" / f"{descriptor['workKey']}-{descriptor['slug']}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(os.fspath(source), os.fspath(destination))
        updated = copy.deepcopy(descriptor)
        updated["artifactFolder"] = os.fspath(destination)
        (destination / "workflow.json").write_text(
            json.dumps(updated, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        registry = manager.registry.load_unlocked()
        expected_revision = registry["revision"]
        registry["revision"] += 1
        registry["workflows"][descriptor["workflowId"]]["artifactPath"] = os.fspath(
            destination
        )
        manager.registry.write_unlocked(registry, expected_revision=expected_revision)
        return manager.resume(workflow_id=descriptor["workflowId"])
