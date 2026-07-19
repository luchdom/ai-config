from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "src" / "skills" / "linear-delivery-loop" / "scripts"
PACKAGE = "_linear_delivery_loop_worktree_tests"
if PACKAGE not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        PACKAGE,
        SCRIPTS / "__init__.py",
        submodule_search_locations=[os.fspath(SCRIPTS)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    spec.loader.exec_module(module)

worktrees = __import__(f"{PACKAGE}.worktrees", fromlist=["WorktreeManager"])
WorktreeManager = worktrees.WorktreeManager
WorktreeError = worktrees.WorktreeError


class SimulatedAllocationCrash(RuntimeError):
    pass


def git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=False,
    )


class WorktreeManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="supervisor-worktrees-")
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
        self.state = self.root / "state"
        self.manager = WorktreeManager(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.state,
        )

    def linked_control(self, name: str) -> Path:
        path = self.root / name
        git(self.repository, "worktree", "add", "--detach", os.fspath(path), "HEAD")
        return path

    def crashing_manager(self, crash_stage: str) -> WorktreeManager:
        def inject(stage: str, allocation_id: str) -> None:
            if stage == crash_stage:
                raise SimulatedAllocationCrash(f"{stage}:{allocation_id}")

        return WorktreeManager(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.state,
            allocation_fault_injector=inject,
        )

    def test_issue_mapping_is_contained_exact_and_idempotent(self) -> None:
        record = self.manager.ensure_issue_worktree("SAAS-46", base_branch="main")
        issue_path = Path(record["path"])
        self.assertEqual(issue_path.parent, self.manager.issue_root)
        self.assertEqual(record["branch"], "delivery/saas-46")
        self.assertFalse(git(issue_path, "status", "--porcelain").stdout)

        observed = self.manager.ensure_issue_worktree(
            "SAAS-46", base_branch="main", existing_record=record
        )
        self.assertEqual(observed, record)

        stale = dict(record, headSha="0" * 40)
        with self.assertRaisesRegex(WorktreeError, "headSha"):
            self.manager.ensure_issue_worktree(
                "SAAS-46", base_branch="main", existing_record=stale
            )

    def test_two_controls_share_mapping_after_first_control_is_removed(self) -> None:
        first = self.linked_control("control-one")
        second = self.linked_control("control-two")
        from_first = WorktreeManager(
            first,
            repository_key="test-repository",
            state_home_override=self.state,
        )
        record = from_first.ensure_issue_worktree("SAAS-47", base_branch="main")
        git(self.repository, "worktree", "remove", os.fspath(first))

        from_second = WorktreeManager(
            second,
            repository_key="test-repository",
            state_home_override=self.state,
        )
        self.assertEqual(
            from_second.ensure_issue_worktree(
                "SAAS-47", base_branch="main", existing_record=record
            ),
            record,
        )

    def test_issue_allocation_recovers_from_crash_after_persisted_intent(self) -> None:
        crashed = self.crashing_manager("after-intent")
        with self.assertRaisesRegex(
            SimulatedAllocationCrash, "after-intent:issue:SAAS-51"
        ):
            crashed.ensure_issue_worktree("SAAS-51", base_branch="main")

        allocation_id = "issue:SAAS-51"
        state = self.manager.store.load_state()
        intent = state["worktreeAllocations"][allocation_id]
        self.assertEqual("prepared", intent["status"])
        self.assertFalse(Path(intent["worktreePath"]).exists())
        self.assertNotIn("SAAS-51", state["issueWorktrees"])

        recovery = self.manager.reconcile_worktree_allocations(allocation_id)
        self.assertEqual("recovered", recovery["status"])
        record = recovery["allocations"][0]
        self.assertEqual("SAAS-51", record["issueId"])
        self.assertEqual(intent["worktreePath"], record["path"])
        state = self.manager.store.load_state()
        self.assertEqual("completed", state["worktreeAllocations"][allocation_id]["status"])
        self.assertEqual("active", state["issueWorktrees"]["SAAS-51"]["status"])
        self.assertTrue(Path(record["path"]).exists())

    def test_gate_allocation_adopts_exact_worktree_after_git_crash(self) -> None:
        operation_id = str(uuid.uuid4())
        allocation_id = f"gate:{operation_id}"
        head = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        crashed = self.crashing_manager("after-git")
        with self.assertRaisesRegex(
            SimulatedAllocationCrash, f"after-git:{allocation_id}"
        ):
            crashed.create_gate_worktree(operation_id, exact_sha=head)

        state = self.manager.store.load_state()
        intent = state["worktreeAllocations"][allocation_id]
        gate_path = Path(intent["worktreePath"])
        self.assertEqual("prepared", intent["status"])
        self.assertTrue(gate_path.exists())
        self.assertNotIn(operation_id, state["gateWorktrees"])
        self.assertEqual(head, git(gate_path, "rev-parse", "HEAD").stdout.strip())

        recovery = self.manager.reconcile_worktree_allocations(allocation_id)
        self.assertEqual("recovered", recovery["status"])
        record = recovery["allocations"][0]
        self.assertEqual(operation_id, record["operationId"])
        self.assertEqual(intent["worktreePath"], record["path"])
        state = self.manager.store.load_state()
        self.assertEqual("completed", state["worktreeAllocations"][allocation_id]["status"])
        self.assertEqual("active", state["gateWorktrees"][operation_id]["status"])
        self.manager.validate_gate_worktree(record)

    def test_control_unregistered_dirty_and_different_repository_are_rejected(self) -> None:
        record = self.manager.ensure_issue_worktree("SAAS-48", base_branch="main")
        with self.assertRaises(WorktreeError):
            self.manager.validate_issue_worktree(
                self.repository, record, control_worktree=self.repository
            )
        issue_path = Path(record["path"])
        (issue_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(WorktreeError, "dirty"):
            self.manager.validate_issue_worktree(
                issue_path, record, control_worktree=self.repository
            )

        other = self.root / "other-repository"
        other.mkdir()
        git(other, "init", "--initial-branch=main")
        git(other, "config", "user.name", "Test User")
        git(other, "config", "user.email", "test@example.invalid")
        (other / "README.md").write_text("other\n", encoding="utf-8")
        git(other, "add", "README.md")
        git(other, "commit", "-m", "initial")
        other_manager = WorktreeManager(
            other,
            repository_key="other-repository",
            state_home_override=self.root / "other-state",
        )
        with self.assertRaises(WorktreeError):
            other_manager.ensure_issue_worktree(
                "SAAS-48", base_branch="main", existing_record=record
            )

    def test_traversal_case_alias_and_reparse_mapping_fail_closed(self) -> None:
        for issue_id in ("../SAAS-46", "saas-46", "SAAS-0", "SAAS-46/other"):
            with self.subTest(issue_id=issue_id), self.assertRaises(WorktreeError):
                self.manager.ensure_issue_worktree(issue_id, base_branch="main")

        alias = self.manager.issue_root / "saas-49"
        alias.mkdir()
        with self.assertRaisesRegex(WorktreeError, "Case-insensitive"):
            self.manager.ensure_issue_worktree("SAAS-49", base_branch="main")

        outside = self.root / "outside"
        outside.mkdir()
        link = self.manager.issue_root / "SAAS-50"
        creation_errors: list[str] = []
        link_created = False
        if hasattr(os, "symlink"):
            try:
                os.symlink(outside, link, target_is_directory=True)
                link_created = True
            except OSError as exc:
                creation_errors.append(f"directory symlink: {exc}")

        # Windows commonly denies directory symlinks without Developer Mode or an
        # elevated token. A directory junction exercises the same reparse-point
        # containment boundary and normally requires neither.
        if not link_created and os.name == "nt":
            completed = subprocess.run(
                [
                    os.environ.get("COMSPEC", "cmd.exe"),
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    os.fspath(link),
                    os.fspath(outside),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                shell=False,
            )
            link_created = completed.returncode == 0 and os.path.lexists(link)
            if not link_created:
                detail = completed.stderr.strip() or completed.stdout.strip()
                creation_errors.append(
                    f"directory junction exited {completed.returncode}: {detail}"
                )

        if not link_created:
            self.skipTest(
                "Host cannot construct a directory symlink or Windows junction: "
                + "; ".join(creation_errors)
            )

        fake = {
            "issueId": "SAAS-50",
            "schemaVersion": "1.0",
            "kind": "issue",
        }
        with self.assertRaisesRegex(
            WorktreeError, "containment or reparse validation"
        ):
            self.manager.ensure_issue_worktree(
                "SAAS-50", base_branch="main", existing_record=fake
            )

    def test_gate_record_is_exact_sha_and_cleanup_is_guarded(self) -> None:
        head = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        operation_id = str(uuid.uuid4())
        record = self.manager.create_gate_worktree(operation_id, exact_sha=head)
        gate_path = Path(record["path"])
        self.assertEqual(git(gate_path, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotEqual(git(gate_path, "symbolic-ref", "-q", "HEAD", check=False).returncode, 0)

        state = self.manager.store.load_state()
        with self.assertRaisesRegex(WorktreeError, "resolved operation"):
            self.manager._cleanup_gate_worktree_authorized(
                operation_id, mutable_state=state
            )
        ready = self.manager.set_gate_evidence(
            operation_id,
            expected_state_revision=state["revision"],
            operation_status="resolved",
            attestation_status="complete",
        )
        self.assertEqual(ready["operationStatus"], "resolved")
        state = self.manager.store.load_state()
        (gate_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(WorktreeError, "clean"):
            self.manager._cleanup_gate_worktree_authorized(
                operation_id, mutable_state=state
            )
        (gate_path / "dirty.txt").unlink()
        cleaned = self.manager._cleanup_gate_worktree_authorized(
            operation_id, mutable_state=state
        )
        self.assertTrue(cleaned["cleanAfter"])
        self.assertEqual(state["gateWorktrees"][operation_id]["status"], "cleaned")
        self.assertFalse(gate_path.exists())

    def test_git_invocation_is_fixed_argv_and_never_shell(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
        with mock.patch.object(worktrees.subprocess, "run", return_value=completed) as run:
            self.manager._git(self.repository, ["status", "--porcelain=v1"])
        positional, keyword = run.call_args
        self.assertIsInstance(positional[0], list)
        self.assertEqual(positional[0][:4], ["git", "--no-optional-locks", "-C", os.fspath(self.repository)])
        self.assertIs(keyword["shell"], False)


if __name__ == "__main__":
    unittest.main()
