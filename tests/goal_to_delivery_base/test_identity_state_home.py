from __future__ import annotations

import json
import os
from pathlib import Path

from tests.goal_to_delivery_base.support import RepositoryTestCase, create_windows_junction
from scripts.errors import ResumeError, StateHomeError, UnsafePathError, ValidationError
from scripts.identity import observe_repository_identity
from scripts.registry import WorkflowRegistry
from scripts.state_home import derive_state_home, ensure_state_home


class IdentityAndStateHomeTests(RepositoryTestCase):
    def test_nested_subdirectory_observes_the_same_repository_and_worktree_identity(self) -> None:
        nested = self.repository / "src" / "nested"
        nested.mkdir(parents=True)
        root_identity = observe_repository_identity(self.repository)
        nested_identity = observe_repository_identity(nested)
        self.assertEqual(root_identity.repository_id, nested_identity.repository_id)
        self.assertEqual(root_identity.common_dir, nested_identity.common_dir)
        self.assertEqual(
            root_identity.physical_worktree_fingerprint,
            nested_identity.physical_worktree_fingerprint,
        )

    def test_linked_worktrees_share_repository_id_and_home_but_not_fingerprint(self) -> None:
        destination = self.linked_worktree()
        source_identity = observe_repository_identity(self.repository)
        destination_identity = observe_repository_identity(destination)

        self.assertEqual(source_identity.repository_id, destination_identity.repository_id)
        self.assertEqual(Path(source_identity.common_dir), Path(destination_identity.common_dir))
        self.assertNotEqual(
            source_identity.physical_worktree_fingerprint,
            destination_identity.physical_worktree_fingerprint,
        )
        source_home = derive_state_home(source_identity, override=self.state_base)
        destination_home = derive_state_home(destination_identity, override=self.state_base)
        self.assertEqual(source_home.repository, destination_home.repository)

    def test_override_must_be_absolute_and_outside_checkout(self) -> None:
        identity = observe_repository_identity(self.repository)
        with self.assertRaises(StateHomeError):
            derive_state_home(identity, override="relative-state")
        with self.assertRaises(StateHomeError):
            derive_state_home(identity, override=self.repository / ".state")

    def test_state_home_base_parent_junction_is_rejected_without_outside_write(self) -> None:
        identity = observe_repository_identity(self.repository)
        outside = self.root / "outside-state-base"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_text("outside-unchanged", encoding="utf-8")
        alias = self.root / "state-base-alias"
        create_windows_junction(self, alias, outside)
        with self.assertRaises(StateHomeError):
            derive_state_home(identity, override=alias / "nested")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside-unchanged")

    def test_state_home_sentinel_rejects_another_repository_identity(self) -> None:
        identity = observe_repository_identity(self.repository)
        home = ensure_state_home(
            derive_state_home(identity, override=self.state_base),
            identity,
            repository_key="test-repository",
        )
        home.sentinel.write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "repositoryId": "repo-wrong",
                    "normalizedCommonDir": "wrong",
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(StateHomeError):
            ensure_state_home(home, identity, repository_key="test-repository")

    def test_native_handoff_mismatch_is_explicit_and_fail_closed(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Native handoff mismatch")
        destination = self.linked_worktree()
        destination_manager = self.manager(destination)

        with self.assertRaisesRegex(ResumeError, "native Codex Hand off"):
            destination_manager.resume(workflow_id=descriptor["workflowId"])
        self.assertEqual(
            source.resume(workflow_id=descriptor["workflowId"])["workflowId"],
            descriptor["workflowId"],
        )

    def test_repository_key_is_bound_on_first_initialization_and_reopen(self) -> None:
        first = self.manager()
        descriptor = first.initialize_local(workflow="manual", goal="Repository key binding")
        reopened = self.manager()
        self.assertEqual(reopened.resume(workflow_id=descriptor["workflowId"]), descriptor)

        state_before = {
            path.relative_to(first.home.repository).as_posix(): path.read_bytes()
            for path in first.home.repository.rglob("*")
            if path.is_file()
        }
        with self.assertRaises(StateHomeError):
            type(first)(
                self.repository,
                repository_key="different-repository",
                state_home_override=self.state_base,
            )
        state_after = {
            path.relative_to(first.home.repository).as_posix(): path.read_bytes()
            for path in first.home.repository.rglob("*")
            if path.is_file()
        }
        self.assertEqual(state_after, state_before)

    def test_repository_sentinel_hardlink_is_rejected_without_outside_write(self) -> None:
        identity = observe_repository_identity(self.repository)
        home = derive_state_home(identity, override=self.state_base)
        home.repository.mkdir(parents=True)
        outside = self.root / "outside-repository-sentinel.json"
        outside.write_text("outside-unchanged", encoding="utf-8")
        os.link(outside, home.sentinel)

        with self.assertRaises(UnsafePathError):
            ensure_state_home(home, identity, repository_key="test-repository")
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside-unchanged")

    def test_repository_init_lock_hardlink_is_rejected_before_mutex_write(self) -> None:
        identity = observe_repository_identity(self.repository)
        home = derive_state_home(identity, override=self.state_base)
        home.repository.mkdir(parents=True)
        outside = self.root / "outside-init-lock.json"
        outside.write_text("outside-unchanged", encoding="utf-8")
        os.link(outside, home.repository / "repository-init.lock")

        with self.assertRaises(UnsafePathError):
            ensure_state_home(home, identity, repository_key="test-repository")
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside-unchanged")

    def test_registry_hardlink_leaf_is_rejected_without_outside_write(self) -> None:
        manager = self.manager()
        manager.registry.path.unlink()
        outside = self.root / "outside-registry.json"
        outside.write_text("outside-unchanged", encoding="utf-8")
        os.link(outside, manager.registry.path)

        with self.assertRaises(UnsafePathError):
            self.manager()
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside-unchanged")

    def test_public_registry_api_cannot_bypass_repository_key_authority(self) -> None:
        manager = self.manager()
        self.assertEqual(manager.registry.load_unlocked()["workflows"], {})
        before = {
            path.relative_to(manager.home.repository).as_posix(): path.read_bytes()
            for path in manager.home.repository.rglob("*")
            if path.is_file()
        }
        forged = WorkflowRegistry(
            manager.home.repository,
            manager.identity.repository_id,
            repository_key="wrong-repository",
            normalized_common_dir=json.loads(
                manager.home.sentinel.read_text(encoding="utf-8")
            )["normalizedCommonDir"],
        )
        with self.assertRaises(ValidationError):
            forged.ensure()
        after = {
            path.relative_to(manager.home.repository).as_posix(): path.read_bytes()
            for path in manager.home.repository.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_public_registry_rejects_normalized_common_dir_sentinel_tamper(self) -> None:
        manager = self.manager()
        pristine = json.loads(manager.home.sentinel.read_text(encoding="utf-8"))
        tampered = dict(pristine)
        tampered["normalizedCommonDir"] = "C:/tampered-common-dir"
        manager.home.sentinel.write_text(json.dumps(tampered), encoding="utf-8")
        with self.assertRaises(ValidationError):
            manager.registry.load_unlocked()
        manager.home.sentinel.write_text(json.dumps(pristine), encoding="utf-8")
        self.assertEqual(manager.registry.load_unlocked()["workflows"], {})
