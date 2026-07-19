from __future__ import annotations

import importlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.linear_delivery_supervisor import load_supervisor_package


package = load_supervisor_package()
contracts = package.contracts
store_module = importlib.import_module(package.__name__ + ".store")
operations_module = importlib.import_module(package.__name__ + ".operations")
lease_module = importlib.import_module(package.__name__ + ".lease")
reservations_module = importlib.import_module(package.__name__ + ".reservations")
supervisor_module = importlib.import_module(package.__name__ + ".supervisor")
worktrees_module = importlib.import_module(package.__name__ + ".worktrees")


def git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=False,
    )


def clean_observer(store, worktree, planning_only):
    observed = store.runtime.observe_repository_identity(worktree)
    head = git(Path(observed.repository_root), "rev-parse", "HEAD").stdout.strip()
    branch = git(Path(observed.repository_root), "branch", "--show-current").stdout.strip()
    return {
        "dirty": False,
        "branch": branch,
        "headSha": head,
        "unpushed": False,
        "unmerged": False,
        "prOpen": False,
        "prId": None,
        "prState": "not-applicable",
        "accessible": True,
        "ambiguous": False,
        "planningOnly": planning_only,
    }


class StateEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="linear-supervisor-state-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        git(self.repository, "init", "--initial-branch=main")
        git(self.repository, "config", "user.name", "Test User")
        git(self.repository, "config", "user.email", "test@example.invalid")
        (self.repository / "README.md").write_text("base\n", encoding="utf-8")
        git(self.repository, "add", "README.md")
        git(self.repository, "commit", "-m", "initial")
        runtime = package.base_runtime.load_base_runtime()
        self.manager = runtime.WorkflowManager(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.root / "state",
        )
        descriptor = self.manager.initialize_local(
            workflow="semi-autonomous", goal="State engine test"
        )
        self.descriptor = self.manager.attach_linear(
            workflow_id=descriptor["workflowId"], external_id="SAAS-46"
        )
        self.store = store_module.SupervisorStore(self.manager)

    def linked_worktree(self) -> Path:
        destination = self.root / "destination"
        git(
            self.repository,
            "worktree",
            "add",
            "-b",
            "destination",
            os.fspath(destination),
            "HEAD",
        )
        return destination

    def use_authoritative_issue_worktree(self, issue_id: str = "SAAS-46") -> dict:
        """Bind the fixture workflow to its real persistent issue worktree."""

        worktree_manager = worktrees_module.WorktreeManager(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.root / "state",
        )
        record = worktree_manager.ensure_issue_worktree(issue_id, base_branch="main")
        self.control_repository = self.repository
        self.repository = Path(record["path"])
        fixture_path = Path(self.descriptor["artifactFolder"]) / "fixture.md"
        fixture_path.write_text("fixture handoff evidence\n", encoding="utf-8")
        handoff = self.manager.workflow_managed_handoff(
            workflow_id=self.descriptor["workflowId"],
            destination_root=self.repository,
            expected_paths=[fixture_path.relative_to(self.control_repository).as_posix()],
        )
        self.descriptor = self.manager.registry.resolve(
            workflow_id=self.descriptor["workflowId"]
        )
        self.issue_identity = package.base_runtime.load_base_runtime().observe_repository_identity(
            self.repository
        )
        self.assertEqual(handoff["destinationFingerprint"], record["physicalWorktreeFingerprint"])
        return record
