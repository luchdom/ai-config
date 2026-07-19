from __future__ import annotations

import json
import uuid

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    contracts,
    lease_module,
)


class LeaseCapabilityTests(StateEngineTestCase):
    def test_lease_prepared_contract_and_nonce_sidecar_boundary(self) -> None:
        issue_record = self.use_authoritative_issue_worktree()
        clock = lease_module.ManualClock(1_000_000_000)
        leases = lease_module.LeaseManager(self.store, clock=clock)
        run_id = str(uuid.uuid4())
        lease = leases.acquire(
            run_id=run_id,
            owner_id="owner",
            expected_revision=self.store.load_state()["revision"],
        )
        prepared = leases.prepare_iteration(
            run_id=run_id,
            owner_id="owner",
            workflow_id=self.descriptor["workflowId"],
            issue_id="SAAS-46",
            worktree_path=self.repository,
            physical_worktree_fingerprint=issue_record["physicalWorktreeFingerprint"],
            expected_revision=self.store.load_state()["revision"],
            lease_capability_ref=lease["capabilityRef"],
            stage="implement",
        )
        contracts.validate_contract("prepared-iteration", prepared)
        contracts.validate_contract("supervisor-state", self.store.load_state())
        public = json.dumps({"state": self.store.load_state(), "prepared": prepared})
        sidecar = self.store.guard.read_json(prepared["capabilityRef"])
        self.assertEqual(
            issue_record["physicalWorktreeFingerprint"],
            sidecar["physicalWorktreeFingerprint"],
        )
        self.assertNotEqual(
            self.manager.identity.physical_worktree_fingerprint,
            sidecar["physicalWorktreeFingerprint"],
        )
        self.assertNotIn(sidecar["nonce"], public)
        self.assertNotIn("nonce", prepared)

    def test_backward_clock_marks_protected_discontinuity(self) -> None:
        clock = lease_module.ManualClock(100)
        leases = lease_module.LeaseManager(self.store, clock=clock, max_forward_step_ns=1000)
        run_id = str(uuid.uuid4())
        lease = leases.acquire(run_id=run_id, owner_id="owner", expected_revision=1)
        clock.set(99)
        with self.assertRaises(lease_module.LeaseError):
            leases.renew(
                run_id=run_id,
                owner_id="owner",
                expected_revision=2,
                capability_ref=lease["capabilityRef"],
            )
        state = self.store.load_state()
        self.assertEqual("clock-discontinuity", state["clockEvidence"]["status"])
        self.assertEqual("required", state["recovery"]["status"])
