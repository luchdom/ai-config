from __future__ import annotations

import copy
import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from tests.linear_delivery_control_plane.support import (
    fixture_engine_registry, issue, observation, package, raw_issue,
)


migration = __import__(package.__name__ + ".migration", fromlist=["build_migration_report"])
records_module = __import__(package.__name__ + ".control_plane_records", fromlist=["ControlPlaneStore"])
control_module = __import__(package.__name__ + ".control_plane", fromlist=["LinearControlPlane"])
tracking_module = __import__(package.__name__ + ".tracking", fromlist=["TrackingPreflight"])
linear_module = __import__(package.__name__ + ".linear_transport", fromlist=["LinearTransport"])


def completed(nodes):
    return {
        "nodes": copy.deepcopy(nodes),
        "pagination": {
            "status": "complete", "pageCount": 1, "nodeCount": len(nodes),
            "cursorChain": [], "terminalHasNextPage": False,
            "terminalEndCursor": None,
        },
    }


class MigrationStatusTests(unittest.TestCase):
    def test_report_lists_every_issue_preserves_unrelated_labels_and_never_mutates(self):
        observed = [
            issue(3, goalComplete=False, labels=["customer-important"]),
            issue(1, externalDependency=True, labels=["keep-me", "autonomous"]),
            issue(2),
        ]
        before = repr(observed)
        report = migration.build_migration_report(
            completed(observed), repository_key="ai-config",
            generated_at="2026-07-19T12:00:00Z"
        )
        self.assertTrue(report["mutationFree"])
        self.assertEqual([item["issueId"] for item in report["issues"]], ["SAAS-1", "SAAS-2", "SAAS-3"])
        self.assertIn("keep-me", report["issues"][0]["proposedLabels"])
        self.assertIn("external-integration", report["issues"][0]["proposedLabels"])
        self.assertIn("needs-refinement", report["issues"][2]["proposedLabels"])
        self.assertEqual(repr(observed), before)

    def test_control_plane_migration_uses_verified_pages_and_never_mutates(self):
        pages = [[issue(3, labels=["keep-3"])], [issue(1), issue(2)]]
        requests = []
        def requester(**kwargs):
            payload = json.loads(kwargs["body"])
            requests.append(payload)
            after = payload["variables"].get("after")
            index = 0 if after is None else int(after.rsplit("-", 1)[1])
            terminal = index == len(pages) - 1
            return {"status": 200, "body": {"data": {"issues": {
                "nodes": [raw_issue(int(item["identifier"].rsplit("-", 1)[1]), **{
                    key: copy.deepcopy(value) for key, value in item.items()
                    if key not in {"id", "identifier"}
                }) for item in pages[index]],
                "pageInfo": {
                    "hasNextPage": not terminal,
                    "endCursor": None if terminal else f"cursor-{index + 1}",
                },
            }}}}
        transport = linear_module.LinearTransport(
            endpoint="https://api.linear.app/graphql", allowed_host="api.linear.app",
            requester=requester,
        )
        noop = lambda **_: None
        claim_port = SimpleNamespace(
            adapter_id="linear-fixture-adapter", journal_id="selection-claim-journal-v1",
            reread=lambda issue_id, operation_id: {},
            claim=lambda selected, operation_id: None,
            readback=lambda issue_id, operation_id: {},
        )
        authority = SimpleNamespace(
            authority_id="repository-authority-v1",
            **{name: noop for name in (
                "current_execution_lease", "authorize_recovery", "prepare", "commit",
                "rollback_if_safe", "protect", "recover",
            )},
        )
        engine, registry_reference = fixture_engine_registry(
            linear=transport, claim_port=claim_port, authority=authority,
            api_key=lambda: "fixture",
            local_observer=lambda: {
                "reservations": [], "issueWorktrees": {},
                "recovery": {"status": "clean"}, "autonomousIssueId": None,
            },
        )
        preflight = tracking_module.TrackingPreflight(
            lambda config: observation(config), supervisor=engine,
            engine_registry_reference=registry_reference,
        )
        config = __import__(
            "tests.linear_delivery_control_plane.support", fromlist=["tracking_config"]
        ).tracking_config()
        now = "2026-07-19T12:00:00Z"
        attestation = preflight.run(
            config, environment={"LINEAR_API_KEY": "fixture"},
            repository_key="ai-config", repository_id="repo-" + "a" * 24,
            supervisor_version="1.0", now=now,
        )
        with tempfile.TemporaryDirectory(prefix="migration-pages-") as root:
            control = control_module.LinearControlPlane(
                records=records_module.ControlPlaneRecords(
                    records_module.ControlPlaneStore(Path(root), fixture_mode=True)
                ),
                preflight=preflight, linear=transport,
            )
            report = control.migration_report(
                repository_key="ai-config", generated_at=now,
                attestation=attestation, config=config,
                repository_id="repo-" + "a" * 24, supervisor_version="1.0",
            )
        self.assertEqual([item["issueId"] for item in report["issues"]], ["SAAS-1", "SAAS-2", "SAAS-3"])
        self.assertEqual(len(requests), 2)
        self.assertTrue(all("mutation" not in item["query"].casefold() for item in requests))

    def test_migration_refuses_incomplete_or_repeated_pagination_evidence(self):
        incomplete = completed([issue(1)])
        incomplete["pagination"]["terminalHasNextPage"] = True
        with self.assertRaises(linear_module.LinearProtocolError):
            migration.build_migration_report(
                incomplete, repository_key="ai-config",
                generated_at="2026-07-19T12:00:00Z",
            )
        repeated = completed([issue(1), issue(2)])
        repeated["pagination"].update(
            pageCount=3, cursorChain=["cursor-1", "cursor-1"]
        )
        with self.assertRaises(linear_module.LinearProtocolError):
            migration.build_migration_report(
                repeated, repository_key="ai-config",
                generated_at="2026-07-19T12:00:00Z",
            )

    def test_status_projection_contains_summaries_not_record_data(self):
        with tempfile.TemporaryDirectory(prefix="control-plane-status-") as root:
            records = records_module.ControlPlaneRecords(records_module.ControlPlaneStore(Path(root), fixture_mode=True))
            decision = records.request_decision(
                issue_id="SAAS-47", source_timestamp="2026-07-19T12:00:00Z",
                created_at="2026-07-19T12:00:00Z", link="https://linear.app/issue/SAAS-47",
                question="Choose an approach",
                options=[{"id": "a", "consequence": "A"}, {"id": "b", "consequence": "B"}],
                recommendation="a",
                owner_id="owner-1",
                config_digest="sha256:" + "c" * 64,
                repository_id="repo-" + "a" * 24,
            )
            control = control_module.LinearControlPlane(
                records=records,
                preflight=tracking_module.TrackingPreflight(lambda config: observation(config)),
                linear=linear_module.LinearTransport(
                    endpoint="https://api.linear.app/graphql", allowed_host="api.linear.app",
                    requester=lambda **_: {},
                ),
            )
            status = control.status({"schemaVersion": "1.0", "reservationControlRef": "must-not-copy"})
            projected = status["controlPlane"]["pendingDecisions"][0]
            self.assertEqual(projected["id"], decision["id"])
            self.assertNotIn("data", projected)
            self.assertNotIn("must-not-copy", repr(status["controlPlane"]))


if __name__ == "__main__":
    unittest.main()
