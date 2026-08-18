from __future__ import annotations

import inspect
import json
import copy
import errno
import os
import uuid
from datetime import date
from pathlib import Path
from unittest import mock

from tests.goal_to_delivery_base.support import (
    RepositoryTestCase,
    create_windows_junction,
    file_tree_snapshot,
    git,
)
from scripts.descriptor import inspect_historical_artifact, validate_descriptor
from scripts.atomic_files import atomic_write_json
from scripts.errors import (
    CollisionError,
    ResumeError,
    StateHomeError,
    UnsafePathError,
    ValidationError,
)
from scripts.workflow_init import ProviderObservedWork, WorkflowManager


class WorkflowLifecycleTests(RepositoryTestCase):
    def test_local_init_allocates_schema_valid_identity_and_exact_resume(self) -> None:
        manager = self.manager()
        first = manager.initialize_local(workflow="semi-autonomous", goal="Build PKCE", display_title="PKCE")
        second = manager.initialize_local(workflow="manual", goal="Build PKCE", display_title="PKCE")

        self.assertEqual(first["workKey"], "001")
        self.assertEqual(second["workKey"], "002")
        self.assertEqual(Path(first["artifactFolder"]).parent, self.repository / ".ai" / "work")
        self.assertEqual(
            Path(first["artifactFolder"]).name,
            f"{date.today().isoformat()}--local-001--pkce",
        )
        self.assertNotEqual(first["workflowId"], second["workflowId"])
        self.assertNotEqual(first["artifactFolder"], second["artifactFolder"])
        self.assertEqual(first["completionBoundary"], "working-tree")
        self.assertEqual(validate_descriptor(first), first)
        self.assertEqual(manager.resume(workflow_id=first["workflowId"]), first)
        self.assertEqual(manager.resume(artifact_path=first["artifactFolder"]), first)
        with self.assertRaises(ResumeError):
            manager.resume()
        with self.assertRaises(ResumeError):
            manager.resume(workflow_id=first["workflowId"], artifact_path=first["artifactFolder"])

    def test_local_api_exposes_no_model_controlled_work_key_and_rejects_autonomous(self) -> None:
        parameters = inspect.signature(WorkflowManager.initialize_local).parameters
        self.assertNotIn("work_key", parameters)
        with self.assertRaises(ValidationError):
            self.manager().initialize_local(workflow="autonomous", goal="Forged authority")

    def test_provider_observation_accepts_canonical_key_only(self) -> None:
        observed = ProviderObservedWork("linear", "SAAS-123", "linear-read-1")
        descriptor = self.manager().initialize_provider(
            observed_work=observed,
            workflow="manual",
            goal="Issue-backed work",
            completion_boundary="artifact",
        )
        self.assertEqual(descriptor["workKey"], "SAAS-123")
        self.assertEqual(
            Path(descriptor["artifactFolder"]).name,
            f"{date.today().isoformat()}--SAAS-123--issue-backed-work",
        )
        with self.assertRaises(ValidationError):
            ProviderObservedWork("linear", "001", "linear-read-2")

    def test_exact_registered_legacy_workflow_resumes_and_advances_in_place(self) -> None:
        manager = self.manager()
        current = manager.initialize_local(workflow="manual", goal="Legacy resume")
        legacy = self.move_workflow_to_legacy(manager, current)
        legacy_folder = Path(legacy["artifactFolder"])

        self.assertEqual(legacy_folder.parent, self.repository / "docs-ai")
        self.assertEqual(manager.resume(artifact_path=legacy_folder), legacy)
        attached = manager.attach_linear(
            workflow_id=legacy["workflowId"],
            external_id="SAAS-123",
        )
        self.assertEqual(Path(attached["artifactFolder"]), legacy_folder)
        self.assertFalse(Path(current["artifactFolder"]).exists())

    def test_exact_collision_uses_deterministic_sequence_without_changing_work_key(self) -> None:
        base = (
            self.repository
            / ".ai"
            / "work"
            / f"{date.today().isoformat()}--local-001--collision"
        )
        base.mkdir(parents=True)
        (base.parent / f"{base.name}--02").mkdir()

        descriptor = self.manager().initialize_local(
            workflow="manual",
            goal="Collision",
        )

        self.assertEqual(descriptor["workKey"], "001")
        self.assertEqual(Path(descriptor["artifactFolder"]).name, f"{base.name}--03")

    def test_missing_ignore_or_ignored_loop_config_fails_before_artifact_creation(self) -> None:
        cases = {
            "missing-work-rule": "",
            "loop-hidden": "/.ai/\n",
        }
        for label, content in cases.items():
            with self.subTest(label=label):
                self.global_excludes.write_text(content, encoding="utf-8")
                manager = self.manager()
                with self.assertRaisesRegex(ValidationError, "ignored|visible"):
                    manager.initialize_local(workflow="manual", goal=f"Ignore {label}")
                self.assertFalse((self.repository / ".ai" / "work").exists())
        self.global_excludes.write_text("/.ai/work/\n/.ai/worktrees/\n", encoding="utf-8")

    def test_tracked_current_artifact_root_fails_before_new_folder_creation(self) -> None:
        tracked = self.repository / ".ai" / "work" / "tracked.txt"
        tracked.parent.mkdir(parents=True)
        tracked.write_text("tracked\n", encoding="utf-8")
        git(self.repository, "add", "-f", ".ai/work/tracked.txt")
        git(self.repository, "commit", "-m", "track invalid artifact root")

        with self.assertRaisesRegex(ValidationError, "tracked paths"):
            self.manager().initialize_local(workflow="manual", goal="Tracked root")
        self.assertEqual(list(tracked.parent.iterdir()), [tracked])

    def test_attach_is_atomic_preserves_folder_and_resumes_by_external_id(self) -> None:
        manager = self.manager()
        before = manager.initialize_local(workflow="manual", goal="Attach later")
        after = manager.attach_linear(workflow_id=before["workflowId"], external_id="SAAS-123")

        self.assertEqual(after["workflowId"], before["workflowId"])
        self.assertEqual(after["workKey"], "001")
        self.assertEqual(after["artifactFolder"], before["artifactFolder"])
        self.assertEqual(after["tracking"], {"provider": "linear", "externalId": "SAAS-123"})
        self.assertEqual(manager.resume(external_id="SAAS-123"), after)

        other = manager.initialize_local(workflow="manual", goal="Other")
        with self.assertRaises(CollisionError):
            manager.attach_linear(workflow_id=other["workflowId"], external_id="SAAS-123")

    def test_forged_registry_projection_cannot_resume_or_mutate_descriptor(self) -> None:
        manager = self.manager()
        descriptor = manager.initialize_local(workflow="manual", goal="Projection authority")
        descriptor = manager.attach_linear(
            workflow_id=descriptor["workflowId"],
            external_id="SAAS-123",
        )
        pristine_registry = manager.registry.load_unlocked()
        mutations = {
            "work-key": lambda entry: entry.update(workKey="999"),
            "external-id": lambda entry: entry.update(externalId="SAAS-999"),
            "provider": lambda entry: entry.update(externalProvider="none", externalId=None),
            "revision": lambda entry: entry.update(descriptorRevision=descriptor["revision"] + 1),
            "repository-key": lambda entry: entry.update(repositoryKey="forged-repository"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                forged = copy.deepcopy(pristine_registry)
                mutate(forged["workflows"][descriptor["workflowId"]])
                atomic_write_json(manager.registry.path, forged)
                with self.assertRaises(ValidationError):
                    manager.resume(workflow_id=descriptor["workflowId"])
                with self.assertRaises(ValidationError):
                    manager.attach_linear(
                        workflow_id=descriptor["workflowId"],
                        external_id="SAAS-123",
                    )
                atomic_write_json(manager.registry.path, pristine_registry)

        forged_external = copy.deepcopy(pristine_registry)
        forged_external["workflows"][descriptor["workflowId"]]["externalId"] = "SAAS-999"
        atomic_write_json(manager.registry.path, forged_external)
        with self.assertRaises(ValidationError):
            manager.resume(external_id="SAAS-999")
        with self.assertRaises(ValidationError):
            manager.registry.resolve(external_id="SAAS-999")
        atomic_write_json(manager.registry.path, pristine_registry)

    def test_attach_failure_rolls_back_descriptor_and_registry(self) -> None:
        manager = self.manager()
        before = manager.initialize_local(workflow="manual", goal="Atomic attach")
        original_write = manager.registry.write_unlocked
        with mock.patch.object(manager.registry, "write_unlocked", side_effect=ValidationError("injected")):
            with self.assertRaises(ValidationError):
                manager.attach_linear(workflow_id=before["workflowId"], external_id="SAAS-456")
        self.assertEqual(manager.resume(workflow_id=before["workflowId"]), before)
        with self.assertRaises(ResumeError):
            manager.resume(external_id="SAAS-456")

    def test_crash_marker_recovers_a_split_attach_transaction(self) -> None:
        manager = self.manager()
        before = manager.initialize_local(workflow="manual", goal="Crash recovery")
        registry_before = manager.registry.load_unlocked()
        descriptor_after = copy.deepcopy(before)
        descriptor_after["revision"] += 1
        descriptor_after["tracking"] = {"provider": "linear", "externalId": "SAAS-789"}
        registry_after = copy.deepcopy(registry_before)
        registry_after["revision"] += 1
        entry = registry_after["workflows"][before["workflowId"]]
        entry["externalProvider"] = "linear"
        entry["externalId"] = "SAAS-789"
        entry["descriptorRevision"] = descriptor_after["revision"]
        descriptor_path = Path(before["artifactFolder"]) / "workflow.json"
        transaction_path = manager._transaction_path(before["workflowId"])
        atomic_write_json(
            transaction_path,
            {
                "schemaVersion": "1.0",
                "operation": "attach",
                "workflowId": before["workflowId"],
                "artifactFolder": before["artifactFolder"],
                "descriptorPath": str(descriptor_path),
                "beforeDescriptor": before,
                "afterDescriptor": descriptor_after,
                "beforeRegistry": registry_before,
                "afterRegistry": registry_after,
            },
        )
        atomic_write_json(descriptor_path, descriptor_after)

        recovered = self.manager()
        self.assertFalse(transaction_path.exists())
        self.assertEqual(recovered.resume(workflow_id=before["workflowId"]), before)
        with self.assertRaises(ResumeError):
            recovered.resume(external_id="SAAS-789")

    def test_partial_initialization_is_quarantined(self) -> None:
        manager = self.manager()
        with mock.patch.object(manager.registry, "write_unlocked", side_effect=ValidationError("injected")):
            with self.assertRaises(ValidationError):
                manager.initialize_local(workflow="manual", goal="Partial allocation")
        quarantine = manager.home.repository / "quarantine"
        self.assertTrue(quarantine.exists())
        self.assertEqual(len(list(quarantine.iterdir())), 1)
        in_place = list((self.repository / ".ai" / "work").glob(".quarantine-*"))
        self.assertEqual(len(in_place), 1)
        self.assertTrue((in_place[0] / "workflow.json").exists())

    def test_invalid_initialization_is_rejected_before_journal_or_folder_creation(self) -> None:
        manager = self.manager()
        with self.assertRaises(ValidationError):
            manager.initialize_local(
                workflow="manual",
                goal="api_key=must-not-be-written",
                display_title="Invalid descriptor",
            )
        artifacts_root = self.repository / ".ai" / "work"
        self.assertFalse(artifacts_root.exists() and any(artifacts_root.iterdir()))
        transactions = manager.home.repository / "transactions"
        self.assertFalse(transactions.exists() and any(transactions.glob("*.json")))

    def test_cross_device_quarantine_falls_back_to_verified_in_place_copy(self) -> None:
        manager = self.manager()
        with mock.patch.object(manager.registry, "write_unlocked", side_effect=ValidationError("injected")):
            with mock.patch("scripts.workflow_init._replace_path", side_effect=OSError(errno.EXDEV, "cross-device")):
                with self.assertRaises(ValidationError):
                    manager.initialize_local(workflow="manual", goal="Cross volume quarantine")
        records = list((manager.home.repository / "quarantine").glob("*.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "quarantined")
        self.assertEqual(record["method"], "verified-in-place-copy")
        quarantined = Path(record["quarantinePath"])
        self.assertTrue((quarantined / "workflow.json").exists())
        self.assertFalse(Path(record["originalPath"]).exists())

    def test_post_create_path_revalidation_failure_quarantines(self) -> None:
        manager = self.manager()
        from scripts import workflow_init as module

        original = module.ensure_safe_descendant
        failed = False

        def fail_second(root: Path, candidate: Path, **kwargs):
            nonlocal failed
            if (
                not failed
                and kwargs.get("candidate_may_not_exist") is False
                and candidate.exists()
                and candidate.name.endswith("post-check")
            ):
                failed = True
                raise UnsafePathError("injected post-create reparse")
            return original(root, candidate, **kwargs)

        with mock.patch("scripts.workflow_init.ensure_safe_descendant", side_effect=fail_second):
            with self.assertRaises(UnsafePathError):
                manager.initialize_local(workflow="manual", goal="Post check")
        self.assertEqual(len(list((manager.home.repository / "quarantine").iterdir())), 1)

    def test_history_layout_is_read_only_and_advances_allocator(self) -> None:
        history = self.repository / "docs-ai" / "history"
        history.mkdir(parents=True)
        legacy = history / "009-old-layout-2025-01-01"
        legacy.mkdir()
        artifact = legacy / "2025-01-01-plan.md"
        artifact.write_text("historical\n", encoding="utf-8")
        inspected = inspect_historical_artifact(self.repository, artifact)
        self.assertTrue(inspected.historical)
        descriptor = self.manager().initialize_local(workflow="manual", goal="New layout")
        self.assertEqual(descriptor["workKey"], "010")
        self.assertEqual(Path(descriptor["artifactFolder"]).parent, self.repository / ".ai" / "work")
        self.assertEqual(artifact.read_text(encoding="utf-8"), "historical\n")

    def test_history_junction_scan_fails_closed_without_outside_write(self) -> None:
        docs_root = self.repository / "docs-ai"
        docs_root.mkdir()
        outside = self.root / "outside-history"
        outside.mkdir()
        sentinel = outside / "009-outside.txt"
        sentinel.write_text("outside-unchanged", encoding="utf-8")
        create_windows_junction(self, docs_root / "history", outside)

        with self.assertRaises(UnsafePathError):
            self.manager().initialize_local(workflow="manual", goal="Unsafe history")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside-unchanged")

    def test_transaction_junction_fails_closed_without_outside_read_or_delete(self) -> None:
        manager = self.manager()
        outside = self.root / "outside-transactions"
        outside.mkdir()
        sentinel = outside / "pending.json"
        sentinel.write_text("outside-unchanged", encoding="utf-8")
        create_windows_junction(self, manager.home.repository / "transactions", outside)

        with self.assertRaises((UnsafePathError, ValidationError)):
            self.manager()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside-unchanged")

    def test_transaction_hardlink_leaf_is_rejected_without_outside_read_or_delete(self) -> None:
        manager = self.manager()
        transactions = manager.state_paths.directory(
            manager.home.repository / "transactions",
            create=True,
        )
        outside = self.root / "outside-pending-transaction.json"
        outside.write_text("outside-unchanged", encoding="utf-8")
        os.link(outside, transactions / "pending.json")

        with self.assertRaises(UnsafePathError):
            self.manager()
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside-unchanged")

    def test_quarantine_junction_fails_closed_without_outside_write(self) -> None:
        manager = self.manager()
        outside = self.root / "outside-quarantine"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_text("outside-unchanged", encoding="utf-8")
        create_windows_junction(self, manager.home.repository / "quarantine", outside)

        with mock.patch.object(manager.registry, "write_unlocked", side_effect=ValidationError("injected")):
            with self.assertRaises((StateHomeError, UnsafePathError)):
                manager.initialize_local(workflow="manual", goal="Unsafe quarantine")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside-unchanged")

    def test_quarantine_record_hardlink_is_rejected_without_outside_write(self) -> None:
        manager = self.manager()
        quarantine = manager.state_paths.directory(
            manager.home.repository / "quarantine",
            create=True,
        )
        fixed_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
        fixed_time = 123456789
        outside = self.root / "outside-quarantine-record.json"
        outside.write_text("outside-unchanged", encoding="utf-8")
        os.link(outside, quarantine / f"{fixed_time}-{fixed_uuid}.json")

        with mock.patch("scripts.workflow_init.uuid.uuid4", return_value=fixed_uuid):
            with mock.patch("scripts.workflow_init.time.time_ns", return_value=fixed_time):
                with mock.patch.object(
                    manager.registry,
                    "write_unlocked",
                    side_effect=ValidationError("injected"),
                ):
                    with self.assertRaises(UnsafePathError):
                        manager.initialize_local(workflow="manual", goal="Unsafe quarantine record")
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside-unchanged")

    def test_exact_artifact_selector_rejects_relative_dot_and_junction_aliases(self) -> None:
        manager = self.manager()
        descriptor = manager.initialize_local(workflow="manual", goal="Exact selector")
        exact = Path(descriptor["artifactFolder"])
        self.assertEqual(manager.resume(artifact_path=exact), descriptor)
        with self.assertRaises(ResumeError):
            manager.resume(artifact_path=exact.name)
        dotted = f"{exact.parent}{os.sep}.{os.sep}{exact.name}"
        with self.assertRaises(ResumeError):
            manager.resume(artifact_path=dotted)

        alias = self.repository / "docs-alias"
        create_windows_junction(self, alias, exact.parent)
        with self.assertRaises(ResumeError):
            manager.resume(artifact_path=alias / exact.name)

    def test_descriptor_projection_rejects_dot_trailing_and_junction_path_aliases(self) -> None:
        manager = self.manager()
        descriptor = manager.initialize_local(workflow="manual", goal="Projection path canonicality")
        descriptor_path = Path(descriptor["artifactFolder"]) / "workflow.json"
        exact_folder = Path(descriptor["artifactFolder"])
        alias_root = self.repository / "docs-projection-alias"
        create_windows_junction(self, alias_root, exact_folder.parent)
        mutations = {
            "repository-dot": (
                "repositoryRoot",
                f"{self.repository.parent}{os.sep}.{os.sep}{self.repository.name}",
            ),
            "artifact-dot": (
                "artifactFolder",
                f"{exact_folder.parent}{os.sep}.{os.sep}{exact_folder.name}",
            ),
            "artifact-trailing": ("artifactFolder", f"{exact_folder}{os.sep}"),
            "artifact-junction": ("artifactFolder", str(alias_root / exact_folder.name)),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label):
                tampered = copy.deepcopy(descriptor)
                tampered[field] = value
                atomic_write_json(descriptor_path, tampered)
                with self.assertRaises(ValidationError):
                    manager.resume(workflow_id=descriptor["workflowId"])
                atomic_write_json(descriptor_path, descriptor)

    def test_wrong_manager_key_cannot_resume_attach_or_handoff(self) -> None:
        manager = self.manager()
        descriptor = manager.initialize_local(workflow="manual", goal="Operation key authority")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("work\n", encoding="utf-8")
        state_before = file_tree_snapshot(manager.home.repository)
        destination_before = file_tree_snapshot(destination)

        manager.repository_key = "wrong-repository"
        with self.assertRaises(ResumeError):
            manager.resume(workflow_id=descriptor["workflowId"])
        with self.assertRaises(ResumeError):
            manager.attach_linear(workflow_id=descriptor["workflowId"], external_id="SAAS-123")
        with self.assertRaises((ResumeError, ValidationError)):
            manager.workflow_managed_handoff(
                workflow_id=descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["feature.txt"],
            )
        self.assertEqual(file_tree_snapshot(manager.home.repository), state_before)
        self.assertEqual(file_tree_snapshot(destination), destination_before)

        manager.repository_key = "test-repository"
        self.assertEqual(manager.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_descriptor_rejects_secret_like_material(self) -> None:
        descriptor = self.manager().initialize_local(workflow="manual", goal="Safe goal")
        descriptor["goal"] = "authorization=Bearer abc.def"
        with self.assertRaises(ValidationError):
            validate_descriptor(descriptor)

    def test_tampered_registry_path_fails_before_outside_descriptor_read(self) -> None:
        manager = self.manager()
        descriptor = manager.initialize_local(workflow="manual", goal="Registry containment")
        outside = self.root / "outside" / "docs-ai" / "evil"
        outside.mkdir(parents=True)
        sentinel = outside / "workflow.json"
        sentinel.write_text("do-not-read-or-change", encoding="utf-8")
        registry = manager.registry.load_unlocked()
        registry["workflows"][descriptor["workflowId"]]["artifactPath"] = str(outside)
        atomic_write_json(manager.registry.path, registry)

        with self.assertRaises(ValidationError):
            self.manager()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do-not-read-or-change")

    def test_malformed_registry_update_never_changes_live_bytes_or_revision(self) -> None:
        manager = self.manager()
        descriptor = manager.initialize_local(workflow="manual", goal="Registry update atomicity")
        before_bytes = manager.registry.path.read_bytes()
        before_revision = manager.registry.load_unlocked()["revision"]

        def corrupt(registry):
            registry["workflows"][descriptor["workflowId"]]["artifactPath"] = str(
                self.root / "outside" / "docs-ai" / "evil"
            )

        with self.assertRaises(ValidationError):
            manager.registry.update(corrupt)
        self.assertEqual(manager.registry.path.read_bytes(), before_bytes)
        self.assertEqual(manager.registry.load_unlocked()["revision"], before_revision)

    def test_tampered_transaction_path_fails_before_outside_read_or_write(self) -> None:
        manager = self.manager()
        descriptor = manager.initialize_local(workflow="manual", goal="Transaction containment")
        registry = manager.registry.load_unlocked()
        outside = self.root / "outside-transaction"
        outside.mkdir()
        sentinel = outside / "workflow.json"
        sentinel.write_text("do-not-read-or-change", encoding="utf-8")
        after = copy.deepcopy(descriptor)
        after["revision"] += 1
        after["artifactFolder"] = str(outside)
        transaction = {
            "schemaVersion": "1.0",
            "operation": "attach",
            "workflowId": descriptor["workflowId"],
            "artifactFolder": str(outside),
            "descriptorPath": str(sentinel),
            "beforeDescriptor": descriptor,
            "afterDescriptor": after,
            "beforeRegistry": registry,
            "afterRegistry": registry,
        }
        atomic_write_json(manager._transaction_path(descriptor["workflowId"]), transaction)

        with self.assertRaises(UnsafePathError):
            self.manager()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do-not-read-or-change")
