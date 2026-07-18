from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from unittest import mock

from tests.goal_to_delivery_base.support import (
    RepositoryTestCase,
    create_windows_junction,
    file_tree_snapshot,
    git,
)
from scripts.errors import HandoffError, ResumeError, UnsafePathError, ValidationError
from scripts import handoff as handoff_module


class WorkflowManagedHandoffTests(RepositoryTestCase):
    def test_different_head_overlapping_transfer_path_fails_before_copy(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Overlapping destination head")
        destination = self.linked_worktree()
        destination_readme = destination / "README.md"
        destination_readme.write_text("destination committed overlap\n", encoding="utf-8")
        git(destination, "add", "README.md")
        git(destination, "commit", "-m", "change overlapping destination path")
        (self.repository / "README.md").write_text("source working edit\n", encoding="utf-8")

        with self.assertRaisesRegex(HandoffError, "Destination HEAD changed a transfer path"):
            source.workflow_managed_handoff(
                workflow_id=descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["README.md"],
            )

        self.assertEqual(
            destination_readme.read_text(encoding="utf-8"),
            "destination committed overlap\n",
        )
        self.assertFalse((destination / Path(descriptor["artifactFolder"]).relative_to(self.repository)).exists())
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_different_head_non_overlapping_commit_is_supported(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Non-overlapping destination head")
        destination = self.linked_worktree()
        destination_only = destination / "destination-only.txt"
        destination_only.write_text("destination-only commit\n", encoding="utf-8")
        git(destination, "add", "destination-only.txt")
        git(destination, "commit", "-m", "add non-overlapping destination path")
        (self.repository / "README.md").write_text("source working edit\n", encoding="utf-8")

        result = source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["README.md"],
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual((destination / "README.md").read_text(encoding="utf-8"), "source working edit\n")
        self.assertEqual(destination_only.read_text(encoding="utf-8"), "destination-only commit\n")
        destination_manager = self.manager(destination)
        resumed = destination_manager.resume(workflow_id=descriptor["workflowId"])
        self.assertEqual(resumed["physicalWorktreeFingerprint"], destination_manager.identity.physical_worktree_fingerprint)
        with self.assertRaisesRegex(ResumeError, "native Codex Hand off"):
            source.resume(workflow_id=descriptor["workflowId"])

    def test_tracked_clean_descriptor_with_feature_edit_and_deletion_handoffs_successfully(self) -> None:
        deleted = self.repository / "delete-me.txt"
        deleted.write_text("tracked deletion baseline\n", encoding="utf-8")
        git(self.repository, "add", "delete-me.txt")
        git(self.repository, "commit", "-m", "add tracked deletion fixture")
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Tracked workflow descriptor")
        git(self.repository, "add", "docs-ai")
        git(self.repository, "commit", "-m", "track workflow artifacts")
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("feature edit\n", encoding="utf-8")
        deleted.unlink()

        result = source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["README.md", "delete-me.txt"],
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual((destination / "README.md").read_text(encoding="utf-8"), "feature edit\n")
        self.assertFalse((destination / "delete-me.txt").exists())
        destination_manager = self.manager(destination)
        destination_descriptor = destination_manager.resume(workflow_id=descriptor["workflowId"])
        self.assertEqual(
            destination_descriptor["physicalWorktreeFingerprint"],
            destination_manager.identity.physical_worktree_fingerprint,
        )
        registry_entry = destination_manager.registry.resolve(workflow_id=descriptor["workflowId"])
        self.assertEqual(registry_entry["artifactPath"], destination_descriptor["artifactFolder"])
        self.assertEqual(registry_entry["descriptorRevision"], destination_descriptor["revision"])
        with self.assertRaisesRegex(ResumeError, "native Codex Hand off"):
            source.resume(workflow_id=descriptor["workflowId"])

    def test_sensitive_filename_and_content_are_absent_from_patch_and_manifest(self) -> None:
        sensitive = self.repository / "api-key.txt"
        sensitive.write_text("placeholder\n", encoding="utf-8")
        git(self.repository, "add", "api-key.txt")
        git(self.repository, "commit", "-m", "add sensitive-name fixture")
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Redaction proof")
        destination = self.linked_worktree()
        sensitive.write_text("api_key=credential-sentinel-value\n", encoding="utf-8")

        result = source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["api-key.txt"],
        )
        evidence = source.home.repository / "handoffs" / descriptor["workflowId"] / result["handoffId"]
        patch = (evidence / "patch.diff").read_text(encoding="utf-8")
        manifest = (evidence / "manifest.json").read_text(encoding="utf-8")
        for forbidden in ("api-key.txt", "credential-sentinel-value", "api_key="):
            self.assertNotIn(forbidden, patch)
            self.assertNotIn(forbidden, manifest)
        self.assertIn("[REDACTED-PATH:", manifest)
        sensitive_sha256 = hashlib.sha256(
            b"api_key=credential-sentinel-value\n"
        ).hexdigest()
        sensitive_git_blob = git(
            self.repository,
            "hash-object",
            "api-key.txt",
        ).stdout.strip()
        all_evidence = "\n".join(path.read_text(encoding="utf-8") for path in evidence.iterdir())
        self.assertNotIn(sensitive_sha256, all_evidence)
        self.assertNotIn(sensitive_git_blob, all_evidence)

    def test_success_remaps_registry_redacts_evidence_and_never_mutates_git_state(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Transfer changes")
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("api_key=super-secret-value\n", encoding="utf-8")
        (self.repository / "feature.txt").write_text("Bearer another-secret\n", encoding="utf-8")
        source_head = git(self.repository, "rev-parse", "HEAD").stdout
        source_branch = git(self.repository, "branch", "--show-current").stdout
        destination_head = git(destination, "rev-parse", "HEAD").stdout
        destination_branch = git(destination, "branch", "--show-current").stdout

        result = source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["README.md", "feature.txt"],
        )

        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["reservationTransferred"])
        self.assertFalse(result["gitMutationPerformed"])
        self.assertEqual(git(self.repository, "rev-parse", "HEAD").stdout, source_head)
        self.assertEqual(git(self.repository, "branch", "--show-current").stdout, source_branch)
        self.assertEqual(git(destination, "rev-parse", "HEAD").stdout, destination_head)
        self.assertEqual(git(destination, "branch", "--show-current").stdout, destination_branch)
        self.assertEqual(git(destination, "diff", "--cached", "--name-only").stdout, "")
        self.assertEqual((destination / "feature.txt").read_text(encoding="utf-8"), "Bearer another-secret\n")

        evidence = source.home.repository / "handoffs" / descriptor["workflowId"] / result["handoffId"]
        all_evidence = "\n".join(path.read_text(encoding="utf-8") for path in evidence.iterdir())
        self.assertNotIn("super-secret-value", all_evidence)
        self.assertNotIn("another-secret", all_evidence)
        manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["reservationTransferred"])
        self.assertFalse(manifest["gitMutationPermitted"])

        with self.assertRaisesRegex(ResumeError, "native Codex Hand off"):
            source.resume(workflow_id=descriptor["workflowId"])
        destination_manager = self.manager(destination)
        resumed = destination_manager.resume(workflow_id=descriptor["workflowId"])
        self.assertEqual(Path(resumed["artifactFolder"]).parent.parent, destination)

    def test_dirty_destination_fails_before_transfer_and_source_stays_authoritative(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Dirty destination")
        destination = self.linked_worktree()
        (destination / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(HandoffError):
            source.workflow_managed_handoff(
                workflow_id=descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["README.md"],
            )
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_concurrent_source_write_fails_and_rolls_destination_back(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Concurrent source")
        destination = self.linked_worktree()
        source_feature = self.repository / "feature.txt"
        source_feature.write_text("initial work\n", encoding="utf-8")
        original_apply = handoff_module._apply_paths

        def apply_then_corrupt_source(*args, **kwargs):
            original_apply(*args, **kwargs)
            source_feature.write_text("concurrent source write\n", encoding="utf-8")

        with mock.patch("scripts.handoff._apply_paths", side_effect=apply_then_corrupt_source):
            with self.assertRaisesRegex(HandoffError, "Source|content"):
                source.workflow_managed_handoff(
                    workflow_id=descriptor["workflowId"],
                    destination_root=destination,
                    expected_paths=["feature.txt"],
                )
        self.assertFalse((destination / "feature.txt").exists())
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_concurrent_destination_write_fails_and_restores_clean_baseline(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Concurrent destination")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("initial work\n", encoding="utf-8")
        destination_feature = destination / "feature.txt"
        original_apply = handoff_module._apply_paths

        def apply_then_corrupt_destination(*args, **kwargs):
            original_apply(*args, **kwargs)
            destination_feature.write_text("concurrent destination write\n", encoding="utf-8")

        with mock.patch("scripts.handoff._apply_paths", side_effect=apply_then_corrupt_destination):
            with self.assertRaisesRegex(HandoffError, "Destination|content"):
                source.workflow_managed_handoff(
                    workflow_id=descriptor["workflowId"],
                    destination_root=destination,
                    expected_paths=["feature.txt"],
                )
        self.assertFalse(destination_feature.exists())
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_concurrent_destination_recreation_of_deleted_file_fails_and_restores_baseline(self) -> None:
        tracked = self.repository / "delete-me.txt"
        tracked.write_text("tracked baseline\n", encoding="utf-8")
        git(self.repository, "add", "delete-me.txt")
        git(self.repository, "commit", "-m", "add deletion fixture")
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Concurrent deletion")
        destination = self.linked_worktree()
        tracked.unlink()
        destination_tracked = destination / "delete-me.txt"
        original_apply = handoff_module._apply_paths

        def apply_then_recreate_destination(*args, **kwargs):
            original_apply(*args, **kwargs)
            destination_tracked.write_text("concurrent recreation\n", encoding="utf-8")

        with mock.patch("scripts.handoff._apply_paths", side_effect=apply_then_recreate_destination):
            with self.assertRaisesRegex(HandoffError, "deletion|content|Destination"):
                source.workflow_managed_handoff(
                    workflow_id=descriptor["workflowId"],
                    destination_root=destination,
                    expected_paths=["delete-me.txt"],
                )
        self.assertEqual(destination_tracked.read_text(encoding="utf-8"), "tracked baseline\n")
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_registry_failure_rolls_back_destination_and_keeps_source_mapping(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Rollback transfer")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("new work\n", encoding="utf-8")

        with mock.patch.object(source.registry, "write_unlocked", side_effect=ValidationError("injected")):
            with self.assertRaises(ValidationError):
                source.workflow_managed_handoff(
                    workflow_id=descriptor["workflowId"],
                    destination_root=destination,
                    expected_paths=["feature.txt"],
                )

        self.assertFalse((destination / "feature.txt").exists())
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_explicit_scope_rejects_unlisted_unrelated_dirty_path_before_copy(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Exact Handoff scope")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("intended\n", encoding="utf-8")
        (self.repository / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")

        with self.assertRaisesRegex(HandoffError, "explicit Handoff scope"):
            source.workflow_managed_handoff(
                workflow_id=descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["feature.txt"],
            )
        self.assertFalse((destination / "feature.txt").exists())
        self.assertFalse((destination / "unrelated.txt").exists())
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_scope_rejects_another_registered_workflow_artifact(self) -> None:
        source = self.manager()
        selected = source.initialize_local(workflow="manual", goal="Selected workflow")
        other = source.initialize_local(workflow="manual", goal="Other workflow")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("intended\n", encoding="utf-8")

        with self.assertRaisesRegex(HandoffError, "another registered workflow"):
            source.workflow_managed_handoff(
                workflow_id=selected["workflowId"],
                destination_root=destination,
                expected_paths=["feature.txt"],
            )
        self.assertFalse((destination / "feature.txt").exists())
        self.assertFalse(
            (destination / Path(selected["artifactFolder"]).relative_to(self.repository)).exists()
        )
        self.assertEqual(source.resume(workflow_id=other["workflowId"]), other)

    def test_destination_bytes_are_rechecked_against_head_immediately_before_apply(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Destination byte recheck")
        destination = self.linked_worktree()
        (self.repository / "README.md").write_text("source change\n", encoding="utf-8")
        original_manifest = handoff_module._manifest

        def manifest_then_mutate_destination(snapshot):
            manifest = original_manifest(snapshot)
            (destination / "README.md").write_text("concurrent destination\n", encoding="utf-8")
            return manifest

        with mock.patch("scripts.handoff._manifest", side_effect=manifest_then_mutate_destination):
            with mock.patch("scripts.handoff._apply_paths", wraps=handoff_module._apply_paths) as apply:
                with self.assertRaisesRegex(HandoffError, "HEAD blob"):
                    source.workflow_managed_handoff(
                        workflow_id=descriptor["workflowId"],
                        destination_root=destination,
                        expected_paths=["README.md"],
                    )
                apply.assert_not_called()
        self.assertEqual((destination / "README.md").read_text(encoding="utf-8"), "concurrent destination\n")
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_snapshot_evidence_and_applied_bytes_remain_consistent_under_source_mutation(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Immutable snapshot")
        destination = self.linked_worktree()
        source_feature = self.repository / "feature.txt"
        source_feature.write_text("captured bytes\n", encoding="utf-8")
        captured_bytes = source_feature.read_bytes()
        original_manifest = handoff_module._manifest

        def manifest_then_mutate_source(snapshot):
            manifest = original_manifest(snapshot)
            source_feature.write_text("concurrent bytes\n", encoding="utf-8")
            return manifest

        with mock.patch("scripts.handoff._manifest", side_effect=manifest_then_mutate_source):
            with self.assertRaisesRegex(HandoffError, "Source|content"):
                source.workflow_managed_handoff(
                    workflow_id=descriptor["workflowId"],
                    destination_root=destination,
                    expected_paths=["feature.txt"],
                )
        self.assertFalse((destination / "feature.txt").exists())
        evidence_root = source.home.repository / "handoffs" / descriptor["workflowId"]
        evidence = next(evidence_root.iterdir())
        manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        feature = next(change for change in manifest["changes"] if change["path"] == "feature.txt")
        self.assertEqual(feature["sha256"], hashlib.sha256(captured_bytes).hexdigest())
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)

    def test_sensitive_failure_diagnostics_and_evidence_never_expose_name_or_content(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Sensitive failure")
        destination = self.linked_worktree()
        sensitive = self.repository / "api-key.txt"
        sensitive.write_text("api_key=failure-secret-sentinel\n", encoding="utf-8")
        destination_sensitive = destination / "api-key.txt"
        original_apply = handoff_module._apply_paths

        def apply_then_corrupt(*args, **kwargs):
            original_apply(*args, **kwargs)
            destination_sensitive.write_text("concurrent\n", encoding="utf-8")

        with mock.patch("scripts.handoff._apply_paths", side_effect=apply_then_corrupt):
            with self.assertRaises(HandoffError) as caught:
                source.workflow_managed_handoff(
                    workflow_id=descriptor["workflowId"],
                    destination_root=destination,
                    expected_paths=["api-key.txt"],
                )
        evidence_root = source.home.repository / "handoffs" / descriptor["workflowId"]
        evidence = next(evidence_root.iterdir())
        all_evidence = "\n".join(path.read_text(encoding="utf-8") for path in evidence.iterdir())
        for forbidden in ("api-key.txt", "failure-secret-sentinel", "api_key="):
            self.assertNotIn(forbidden, str(caught.exception))
            self.assertNotIn(forbidden, all_evidence)
        self.assertIn("[REDACTED-PATH:", all_evidence)
        self.assertFalse(destination_sensitive.exists())

    def test_rollback_failure_reports_reconciliation_required_and_preserves_source_authority(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Rollback failure")
        destination = self.linked_worktree()
        sensitive = self.repository / "api-key.txt"
        sensitive.write_text("api_key=rollback-secret\n", encoding="utf-8")
        destination_sensitive = destination / "api-key.txt"
        original_apply = handoff_module._apply_paths

        def apply_then_corrupt(*args, **kwargs):
            original_apply(*args, **kwargs)
            destination_sensitive.write_text("concurrent\n", encoding="utf-8")

        with mock.patch("scripts.handoff._apply_paths", side_effect=apply_then_corrupt):
            with mock.patch(
                "scripts.handoff._rollback_paths",
                side_effect=OSError("rollback failed for api-key.txt"),
            ):
                with self.assertRaisesRegex(HandoffError, "attended reconciliation") as caught:
                    source.workflow_managed_handoff(
                        workflow_id=descriptor["workflowId"],
                        destination_root=destination,
                        expected_paths=["api-key.txt"],
                    )
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)
        evidence_root = source.home.repository / "handoffs" / descriptor["workflowId"]
        result = json.loads((next(evidence_root.iterdir()) / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["rollbackStatus"], "rollback-required")
        self.assertTrue(result["destinationReconciliationRequired"])
        self.assertNotIn("api-key.txt", str(caught.exception))
        self.assertNotIn("api-key.txt", json.dumps(result))

    def test_failure_result_write_error_raises_attended_reconciliation_without_false_claim(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Failure evidence write")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("work\n", encoding="utf-8")
        destination_feature = destination / "feature.txt"
        original_apply = handoff_module._apply_paths
        original_write_json = source.state_paths.write_json

        def apply_then_corrupt(*args, **kwargs):
            original_apply(*args, **kwargs)
            destination_feature.write_text("concurrent\n", encoding="utf-8")

        def reject_result(path, value, **kwargs):
            if Path(path).name == "result.json":
                raise OSError("injected evidence write failure")
            return original_write_json(path, value, **kwargs)

        with mock.patch("scripts.handoff._apply_paths", side_effect=apply_then_corrupt):
            with mock.patch.object(source.state_paths, "write_json", side_effect=reject_result):
                with self.assertRaisesRegex(HandoffError, "attended reconciliation.*evidence"):
                    source.workflow_managed_handoff(
                        workflow_id=descriptor["workflowId"],
                        destination_root=destination,
                        expected_paths=["feature.txt"],
                    )
        self.assertFalse(destination_feature.exists())
        self.assertEqual(source.resume(workflow_id=descriptor["workflowId"]), descriptor)
        evidence_root = source.home.repository / "handoffs" / descriptor["workflowId"]
        evidence = next(evidence_root.iterdir())
        self.assertFalse((evidence / "result.json").exists())

    def test_handoff_evidence_junction_fails_closed_without_outside_or_destination_write(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Evidence containment")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("work\n", encoding="utf-8")
        outside = self.root / "outside-handoff-evidence"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_text("outside-unchanged", encoding="utf-8")
        create_windows_junction(self, source.home.repository / "handoffs", outside)

        with self.assertRaises(UnsafePathError):
            source.workflow_managed_handoff(
                workflow_id=descriptor["workflowId"],
                destination_root=destination,
                expected_paths=["feature.txt"],
            )
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside-unchanged")
        self.assertFalse((destination / "feature.txt").exists())

    def test_authoritative_evidence_hashes_reject_manifest_patch_and_result_tampering(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Evidence hash binding")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("work\n", encoding="utf-8")
        result = source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["feature.txt"],
        )
        evidence = source.home.repository / "handoffs" / descriptor["workflowId"] / result["handoffId"]
        for name in ("manifest.json", "patch.diff", "result.json"):
            path = evidence / name
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(name=name), self.assertRaises(ValidationError):
                source.registry.load_unlocked()
            path.write_bytes(original)
        source.registry.load_unlocked()

    def test_authoritative_evidence_hardlink_leaf_is_rejected_without_outside_read(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Evidence leaf containment")
        destination = self.linked_worktree()
        (self.repository / "feature.txt").write_text("work\n", encoding="utf-8")
        result = source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["feature.txt"],
        )
        evidence = source.home.repository / "handoffs" / descriptor["workflowId"] / result["handoffId"]
        manifest = evidence / "manifest.json"
        original = manifest.read_bytes()
        manifest.unlink()
        outside = self.root / "outside-manifest.json"
        outside.write_bytes(original)
        os.link(outside, manifest)

        with self.assertRaises(UnsafePathError):
            source.registry.load_unlocked()
        self.assertEqual(outside.read_bytes(), original)

    def test_multi_hop_handoff_history_validates_each_destination_and_evidence_hash(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Multi-hop Handoff")
        destination = self.linked_worktree("destination-one")
        (self.repository / "feature.txt").write_text("work\n", encoding="utf-8")
        first = source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["feature.txt"],
        )
        destination_manager = self.manager(destination)
        third = self.linked_worktree("destination-two")
        second = destination_manager.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=third,
            expected_paths=["feature.txt"],
        )
        third_manager = self.manager(third)
        resumed = third_manager.resume(workflow_id=descriptor["workflowId"])
        entry = third_manager.registry.resolve(workflow_id=descriptor["workflowId"])
        self.assertEqual(len(entry["handoffs"]), 2)
        self.assertEqual(entry["handoffs"][0]["handoffId"], first["handoffId"])
        self.assertEqual(entry["handoffs"][1]["handoffId"], second["handoffId"])
        self.assertEqual(entry["handoffs"][1]["destinationArtifactPath"], resumed["artifactFolder"])

    def test_superseded_source_operations_fail_with_zero_state_or_destination_writes(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Superseded source")
        destination = self.linked_worktree("authority-destination")
        (self.repository / "feature.txt").write_text("work\n", encoding="utf-8")
        source.workflow_managed_handoff(
            workflow_id=descriptor["workflowId"],
            destination_root=destination,
            expected_paths=["feature.txt"],
        )
        third = self.linked_worktree("third-destination")
        state_before = file_tree_snapshot(source.home.repository)
        source_artifacts_before = file_tree_snapshot(self.repository / "docs-ai")
        destination_before = file_tree_snapshot(destination)
        third_before = file_tree_snapshot(third)

        with self.assertRaises(ResumeError):
            source.resume(workflow_id=descriptor["workflowId"])
        with self.assertRaises(ResumeError):
            source.attach_linear(workflow_id=descriptor["workflowId"], external_id="SAAS-999")
        with self.assertRaises(ResumeError):
            source.workflow_managed_handoff(
                workflow_id=descriptor["workflowId"],
                destination_root=third,
                expected_paths=["feature.txt"],
            )
        self.assertEqual(file_tree_snapshot(source.home.repository), state_before)
        self.assertEqual(file_tree_snapshot(self.repository / "docs-ai"), source_artifacts_before)
        self.assertEqual(file_tree_snapshot(destination), destination_before)
        self.assertEqual(file_tree_snapshot(third), third_before)

    def test_different_repository_is_rejected(self) -> None:
        source = self.manager()
        descriptor = source.initialize_local(workflow="manual", goal="Wrong repository")
        other = self.root / "other"
        other.mkdir()
        git(other, "init", "--initial-branch=main")
        git(other, "config", "user.name", "Test User")
        git(other, "config", "user.email", "test@example.invalid")
        (other / "README.md").write_text("other\n", encoding="utf-8")
        git(other, "add", "README.md")
        git(other, "commit", "-m", "initial")
        with self.assertRaises(HandoffError):
            source.workflow_managed_handoff(
                workflow_id=descriptor["workflowId"],
                destination_root=other,
                expected_paths=["README.md"],
            )
