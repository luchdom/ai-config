from __future__ import annotations

import importlib
import unittest
from unittest import mock
from tests.linear_delivery_supervisor import load_supervisor_package

package = load_supervisor_package(); module = importlib.import_module(package.__name__ + ".publication_recovery")
supervisor = importlib.import_module(package.__name__ + ".supervisor")
SHA = "a" * 40; MERGE = "b" * 40

class MergeRepairTests(unittest.TestCase):
    def test_premerge_and_every_repair_gate_bind_exact_head(self):
        attestations = {name: {"exactSha": SHA} for name in ("exact-head-aggregate", "review", "qa", "docs")}
        module.MergeRepairPolicy.premerge(head_sha=SHA, base_ref="main", authority={"lease": True, "reservation": True, "labels": True, "mergeability": True}, attestations=attestations)
        gates = {name: {"exactSha": SHA, "repairHeadSha": SHA, "passed": True} for name in module.REPAIR_GATES}
        module.MergeRepairPolicy.require_repair_pipeline(repair_head=SHA, gates=gates)
        gates["review"]["exactSha"] = MERGE
        with self.assertRaises(module.PublicationRecoveryError): module.MergeRepairPolicy.require_repair_pipeline(repair_head=SHA, gates=gates)

    def test_every_premerge_member_is_mandatory_and_exact_head_bound(self):
        valid = {name: {"exactSha": SHA, "passed": True} for name in module.REPAIR_PREMERGE_GATES}
        module.MergeRepairPolicy.require_repair_pipeline(
            repair_head=SHA, gates=valid, phase="pre-merge"
        )
        for name in module.REPAIR_PREMERGE_GATES:
            missing = dict(valid); missing.pop(name)
            with self.assertRaises(module.PublicationRecoveryError, msg=name):
                module.MergeRepairPolicy.require_repair_pipeline(repair_head=SHA, gates=missing, phase="pre-merge")
            failed = {key: dict(value) for key, value in valid.items()}; failed[name]["passed"] = False
            with self.assertRaises(module.PublicationRecoveryError, msg=name):
                module.MergeRepairPolicy.require_repair_pipeline(repair_head=SHA, gates=failed, phase="pre-merge")
            stale = {key: dict(value) for key, value in valid.items()}; stale[name]["exactSha"] = MERGE
            with self.assertRaises(module.PublicationRecoveryError, msg=name):
                module.MergeRepairPolicy.require_repair_pipeline(repair_head=SHA, gates=stale, phase="pre-merge")

    def test_merge_readback_and_exact_merge_are_postmerge_mandatory(self):
        gates = {name: {"exactSha": SHA, "repairHeadSha": SHA, "passed": True} for name in module.REPAIR_GATES}
        for name in ("merge-readback", "exact-merge-aggregate"):
            missing = dict(gates); missing.pop(name)
            with self.assertRaises(module.PublicationRecoveryError):
                module.MergeRepairPolicy.require_repair_pipeline(repair_head=SHA, gates=missing)
            wrong = {key: dict(value) for key, value in gates.items()}; wrong[name]["repairHeadSha"] = MERGE
            with self.assertRaises(module.PublicationRecoveryError):
                module.MergeRepairPolicy.require_repair_pipeline(repair_head=SHA, gates=wrong)

    def test_base_drift_invalidates_gates_without_rebase(self):
        result = module.MergeRepairPolicy.base_drift(observed_base_sha=MERGE, attested_base_sha=SHA, merge_origin_main=lambda: "c" * 40)
        self.assertTrue(result["drifted"]); self.assertIn("review", result["invalidated"])

    def test_three_numbered_repairs_then_attended_exhaustion(self):
        for previous in range(3):
            result = module.MergeRepairPolicy.next_repair(issue_id="SAAS-48", previous_attempt=previous, current_main_sha=MERGE)
            self.assertEqual(f"codex/SAAS-48-repair-{previous + 1}", result["branch"])
        exhausted = module.MergeRepairPolicy.next_repair(issue_id="SAAS-48", previous_attempt=3, current_main_sha=MERGE)
        self.assertEqual("Backlog", exhausted["issueState"]); self.assertTrue(exhausted["notify"])

    def test_fourth_repair_returns_the_persisted_paused_readback(self):
        publication = {
            "operationId": "publication-1", "issueId": "SAAS-48",
            "repositoryId": "repo", "headSha": SHA, "status": "post-merge-validating",
            "branch": "codex/SAAS-48-repair-3",
            "repairAttempt": 3, "updatedAt": "2026-07-23T00:00:00Z",
            "pullRequest": {"id": "pr-3"},
            "preservedState": {"issueState": "In Review", "reservationId": "reservation-1",
                "worktreePath": "C:/worktree", "branch": "codex/SAAS-48-repair-3"},
        }
        class Journal:
            def __init__(self): self.value = publication
            def load(self, _operation_id): return dict(self.value)
            def save_authoritative(self, value, **_kwargs): self.value = dict(value); return dict(value)
        class Recovery:
            def repair_exhausted(self, *, publication, request_context):
                self.context = request_context
                return {**publication, "status": "paused", "refusalKind": "policy"}
        engine = supervisor.SupervisorEngine.__new__(supervisor.SupervisorEngine)
        engine.publication_operations = Journal()
        engine.publication_recovery = Recovery()
        with mock.patch.object(supervisor.SupervisorEngine, "_publication_authority"), mock.patch.object(
            supervisor.SupervisorEngine, "_consume_publication_authorization"
        ):
            result = engine.next_publication_repair(
                operation_id="publication-1", repair_operation_id="repair-4",
                current_main_sha=MERGE, expected_state_revision=1,
                reservation_id="reservation-1", authorization_ref="fixture",
                expected_record_revision=1, expected_reservations_revision=1,
                physical_worktree_fingerprint="sha256:" + "c" * 64,
            )
        self.assertEqual("paused", result["status"])
        self.assertEqual(result, engine.publication_operations.load("publication-1"))
        self.assertEqual("exhausted", engine.publication_recovery.context["refusal_kind"])
