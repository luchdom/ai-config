from __future__ import annotations

import copy
import uuid
from pathlib import Path

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    contracts,
    git,
    lease_module,
)


class CheckpointTests(StateEngineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.issue_record = self.use_authoritative_issue_worktree()

    def _acquire_and_prepare(self) -> tuple[lease_module.LeaseManager, str, dict]:
        clock = lease_module.ManualClock(1_000_000_000)
        leases = lease_module.LeaseManager(self.store, clock=clock)
        run_id = str(uuid.uuid4())
        revision = self.store.load_state()["revision"]
        lease = leases.acquire(
            run_id=run_id,
            owner_id="owner",
            expected_revision=revision,
        )
        prepared = leases.prepare_iteration(
            run_id=run_id,
            owner_id="owner",
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=self.repository,
            physical_worktree_fingerprint=self.issue_record["physicalWorktreeFingerprint"],
            expected_revision=self.store.load_state()["revision"],
            lease_capability_ref=lease["capabilityRef"],
            stage="implement",
        )
        return leases, run_id, prepared

    def _worker_result(self, prepared: dict, run_id: str, transition_id: str) -> dict:
        (self.repository / "docs-ai").mkdir(exist_ok=True)
        (self.repository / "docs-ai" / "review.md").write_text(
            "review evidence\n", encoding="utf-8"
        )
        (self.repository / "README.md").write_text(
            "implemented\n", encoding="utf-8"
        )
        changed_paths = set(
            filter(
                None,
                git(self.repository, "diff", "--name-only", "-z", "HEAD", "--").stdout.split("\0"),
            )
        )
        changed_paths.update(
            filter(
                None,
                git(
                    self.repository,
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "-z",
                ).stdout.split("\0"),
            )
        )
        self.assertTrue(changed_paths)
        head = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        return {
            "schemaVersion": "1.0",
            "preparedIterationId": prepared["preparedIterationId"],
            "runId": run_id,
            "workflowId": self.descriptor["workflowId"],
            "issueId": "SAAS-46",
            "transitionId": transition_id,
            "outcome": "advanced",
            "completedStage": "implement",
            "proposedNextStage": "review",
            "artifactManifest": ["docs-ai/review.md"],
            "changedPaths": sorted(changed_paths, key=str.casefold),
            "summary": "Implementation is ready for independent review.",
            "proposedExternalTransitions": [],
            "pause": None,
            "observed": {
                "repositoryId": self.manager.identity.repository_id,
                "physicalWorktreeFingerprint": self.issue_record["physicalWorktreeFingerprint"],
                "headSha": head,
            },
        }

    def test_checkpoint_is_single_use_bound_and_exactly_replayable(self) -> None:
        leases, run_id, prepared = self._acquire_and_prepare()
        transition_id = str(uuid.uuid4())
        result = self._worker_result(prepared, run_id, transition_id)
        prepared_ref = self.store.root / "runs" / run_id / f"{prepared['preparedIterationId']}.prepared-iteration.json"
        revision = self.store.load_state()["revision"]
        first = leases.apply_checkpoint(
            prepared_ref=prepared_ref,
            transition_id=transition_id,
            expected_revision=revision,
            expected_stage="implement",
            worker_result=result,
        )
        replay = leases.apply_checkpoint(
            prepared_ref=prepared_ref,
            transition_id=transition_id,
            expected_revision=revision,
            expected_stage="implement",
            worker_result=result,
        )
        self.assertEqual(first, replay)
        changed = dict(result, summary="Changed replay")
        with self.assertRaises(lease_module.LeaseError):
            leases.apply_checkpoint(
                prepared_ref=prepared_ref,
                transition_id=transition_id,
                expected_revision=revision + 1,
                expected_stage="implement",
                worker_result=changed,
            )
        contracts.validate_contract("supervisor-state", self.store.load_state())

    def test_prepare_rejects_control_and_unregistered_worktrees(self) -> None:
        clock = lease_module.ManualClock(1_000_000_000)
        leases = lease_module.LeaseManager(self.store, clock=clock)
        run_id = str(uuid.uuid4())
        lease = leases.acquire(
            run_id=run_id,
            owner_id="owner",
            expected_revision=self.store.load_state()["revision"],
        )
        unregistered = self.linked_worktree()
        for candidate in (self.control_repository, unregistered):
            with self.subTest(candidate=candidate), self.assertRaisesRegex(
                lease_module.LeaseError, "authoritative issue mapping"
            ):
                leases.prepare_iteration(
                    run_id=run_id,
                    owner_id="owner",
                    workflow_id=self.descriptor["workflowId"],
                    issue_id="SAAS-46",
                    worktree_path=candidate,
                    physical_worktree_fingerprint=self.issue_record["physicalWorktreeFingerprint"],
                    expected_revision=self.store.load_state()["revision"],
                    lease_capability_ref=lease["capabilityRef"],
                    stage="implement",
                )

    def test_checkpoint_rejects_fabricated_bindings_and_git_evidence(self) -> None:
        leases, run_id, prepared = self._acquire_and_prepare()
        transition_id = str(uuid.uuid4())
        result = self._worker_result(prepared, run_id, transition_id)
        prepared_ref = self.store.root / "runs" / run_id / f"{prepared['preparedIterationId']}.prepared-iteration.json"
        revision = self.store.load_state()["revision"]
        mutations = (
            ("prepared iteration", lambda value: value.__setitem__("preparedIterationId", str(uuid.uuid4()))),
            ("HEAD", lambda value: value["observed"].__setitem__("headSha", "f" * 40)),
            ("changed paths", lambda value: value["changedPaths"].pop()),
        )
        for label, mutate in mutations:
            forged = copy.deepcopy(result)
            mutate(forged)
            with self.subTest(binding=label), self.assertRaises(lease_module.LeaseError):
                leases.apply_checkpoint(
                    prepared_ref=prepared_ref,
                    transition_id=transition_id,
                    expected_revision=revision,
                    expected_stage="implement",
                    worker_result=forged,
                )
