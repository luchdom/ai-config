from __future__ import annotations

import tempfile
import threading
import unittest
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tests.linear_delivery_control_plane.support import (
    CONTROL_PLANE_STATE_VERSION, observation, package, tracking_config,
)


records_module = __import__(package.__name__ + ".control_plane_records", fromlist=["ControlPlaneStore"])
control_module = __import__(package.__name__ + ".control_plane", fromlist=["LinearControlPlane"])
tracking_module = __import__(package.__name__ + ".tracking", fromlist=["TrackingPreflight"])
ntfy_module = __import__(package.__name__ + ".ntfy_transport", fromlist=["NtfyTransport"])
linear_module = __import__(package.__name__ + ".linear_transport", fromlist=["LinearTransport"])


NOW = "2026-07-19T12:00:00Z"
LATER = "2026-07-19T12:01:00Z"
MUCH_LATER = "2026-07-19T12:10:00Z"
NEWER = "2026-07-19T12:11:00Z"
LINK = "https://linear.app/luchdom/issue/SAAS-47/example"
REPOSITORY_ID = "repo-" + "a" * 24
CONFIG_DIGEST = "sha256:" + "c" * 64


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="control-plane-records-")
        self.addCleanup(self.temporary.cleanup)
        self.store = records_module.ControlPlaneStore(Path(self.temporary.name), fixture_mode=True)
        self.records = records_module.ControlPlaneRecords(self.store)

    def test_new_control_plane_state_uses_current_schema_boundary(self):
        self.assertEqual(CONTROL_PLANE_STATE_VERSION, self.store.load()["schemaVersion"])

    def test_decision_is_deduplicated_and_only_exact_new_owner_reply_is_consumed(self):
        kwargs = dict(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            question="Choose the tenant isolation policy",
            options=[{"id": "row", "consequence": "shared database"}, {"id": "schema", "consequence": "more isolation"}],
            recommendation="row",
            owner_id="owner-1",
            config_digest=CONFIG_DIGEST,
            repository_id=REPOSITORY_ID,
        )
        first = self.records.request_decision(**kwargs)
        second = self.records.request_decision(**kwargs)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.load()["decisions"]), 1)
        self.assertIsNone(self.records.consume_decision_reply(
            decision_id=first["id"], actor_id="other",
            reply_id="reply-1", reply_created_at=LATER,
            body=f"DECIDE {first['id']} row",
            owner_id="owner-1", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        ))
        other = self.records.request_decision(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            question="Choose another boundary",
            options=[{"id": "x", "consequence": "X"}, {"id": "y", "consequence": "Y"}],
            recommendation="x", owner_id="owner-1",
            config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        )
        self.assertIsNone(self.records.consume_decision_reply(
            decision_id=other["id"], actor_id="owner-1", reply_id="cross",
            reply_created_at=LATER, body=f"DECIDE {first['id']} row",
            owner_id="owner-1", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        ))
        self.assertIsNone(self.records.consume_decision_reply(
            decision_id=other["id"], actor_id="owner-1", reply_id="drift",
            reply_created_at=LATER, body=f"DECIDE {other['id']} x",
            owner_id="attacker", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        ))
        consumed = self.records.consume_decision_reply(
            decision_id=first["id"], actor_id="owner-1",
            reply_id="reply-2", reply_created_at=LATER,
            body=f"DECIDE {first['id']} row",
            owner_id="owner-1", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        )
        self.assertEqual(consumed["data"]["selectedOption"], "row")
        self.assertIsNone(self.records.consume_decision_reply(
            decision_id=first["id"], actor_id="owner-1",
            reply_id="reply-3", reply_created_at=LATER,
            body=f"DECIDE {first['id']} schema",
            owner_id="owner-1", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        ))

    def test_publication_retry_reopen_retains_monotonic_reply_lower_bound(self):
        request = self.records.publication_refusal(
            issue_id="SAAS-47", operation_id="operation-47",
            head_sha="a" * 40, source_timestamp=NOW, created_at=NOW,
            link=LINK, reason="Publication outcome is ambiguous",
            evidence={
                "issueState": "In Review", "reservationId": "reservation-47",
                "worktreePath": str(Path(self.temporary.name).resolve() / "issue-worktree"), "branch": "codex/saas-47", "prId": "17",
            },
            owner_id="owner-1",
            config_digest=CONFIG_DIGEST,
            repository_id=REPOSITORY_ID,
        )
        exact = "RETRY-PUBLICATION operation-47 " + "a" * 40
        self.assertIsNone(self.records.consume_publication_reply(
            request_id=request["id"], actor_id="owner-1",
            reply_id="r1", reply_created_at=LATER, body=exact, reconciled=False,
            owner_id="owner-1", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        ))
        result = self.records.consume_publication_reply(
            request_id=request["id"], actor_id="owner-1",
            reply_id="r2", reply_created_at=MUCH_LATER, body=exact, reconciled=True,
            owner_id="owner-1", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        )
        self.assertEqual(result["status"], "authorized")
        self.assertEqual(result["evidence"]["branch"], "codex/saas-47")
        reopened = self.records.reopen_publication_request(
            request_id=request["id"], consumed_reply_id="r2",
        )
        self.assertEqual(reopened["status"], "pending")
        self.assertIsNone(reopened["data"]["consumedReplyTimestamp"])
        self.assertEqual(MUCH_LATER, reopened["data"]["lastConsumedReplyTimestamp"])
        for reply_id, timestamp in (
            ("r2", MUCH_LATER),
            ("older-different", LATER),
            ("equal-time-different", MUCH_LATER),
        ):
            self.assertIsNone(self.records.consume_publication_reply(
                request_id=request["id"], actor_id="owner-1",
                reply_id=reply_id, reply_created_at=timestamp, body=exact, reconciled=True,
                owner_id="owner-1", config_digest=CONFIG_DIGEST,
                repository_id=REPOSITORY_ID,
            ))
        newer = self.records.consume_publication_reply(
            request_id=request["id"], actor_id="owner-1",
            reply_id="newer-different", reply_created_at=NEWER,
            body=exact, reconciled=True, owner_id="owner-1",
            config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        )
        self.assertEqual("newer-different", newer["consumedReplyId"])
        self.assertEqual(NEWER, newer["consumedReplyTimestamp"])
        valid = self.store.load()
        corrupted = copy.deepcopy(valid)
        corrupted["publicationRequests"][0]["data"]["lastConsumedReplyTimestamp"] = NOW
        self.store.path.write_text(json.dumps(corrupted), encoding="utf-8")
        with self.assertRaises(Exception):
            self.store.load()
        self.store.path.write_text(json.dumps(valid), encoding="utf-8")
        self.assertIsNone(self.records.consume_publication_reply(
            request_id=request["id"], actor_id="owner-1",
            reply_id="r3", reply_created_at=NEWER, body=exact, reconciled=True,
            owner_id="owner-1", config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        ))

    def test_follow_up_is_only_for_achievable_external_prerequisite(self):
        base = dict(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW,
            link=LINK, title="Provision an external provider sandbox",
        )
        self.assertIsNone(self.records.propose_follow_up(
            **base, independently_actionable=False, achievable=True
        ))
        first = self.records.propose_follow_up(
            **base, independently_actionable=True, achievable=True
        )
        second = self.records.propose_follow_up(
            **base, independently_actionable=True, achievable=True
        )
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.load()["followUps"]), 1)

    def test_composed_proposals_failures_and_quiet_states(self):
        self.records.propose_issue_contract(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            summary="Goal needs refinement", proposal_kind="needs-refinement",
        )
        self.records.propose_issue_contract(
            issue_id="SAAS-48", source_timestamp=NOW, created_at=NOW, link=LINK,
            summary="Provider work deferred", proposal_kind="external-integration",
        )
        for number, kind in enumerate(("worker-failure", "preflight-failure", "reconciliation-failure"), 49):
            self.assertIsNotNone(self.records.record_failure(
                failure_kind=kind, issue_id=f"SAAS-{number}", source_id=kind,
                source_timestamp=NOW, created_at=NOW, link=LINK, summary=kind,
                actionable=True, transient_within_budget=False,
            ))
        self.assertIsNone(self.records.record_failure(
            failure_kind="worker-failure", issue_id="SAAS-55", source_id="transient",
            source_timestamp=NOW, created_at=NOW, link=LINK, summary="retrying",
            actionable=True, transient_within_budget=True,
        ))
        state = self.store.load()
        self.assertEqual(len(state["followUps"]), 5)
        self.assertEqual(len(state["attentionEvents"]), 3)
        quiet_sources = {
            item["id"] for item in state["followUps"]
            if item["data"].get("proposalType") == "issue-contract"
        }
        self.assertTrue(quiet_sources)
        self.assertTrue(all(
            event["data"]["sourceId"] not in quiet_sources
            for event in state["attentionEvents"]
        ))

    def test_ntfy_notifies_once_and_failure_is_status_visible(self):
        decision = self.records.request_decision(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            question="Product decision needed; token=sentinel-secret",
            options=[{"id": "a", "consequence": "A"}, {"id": "b", "consequence": "B"}],
            recommendation="a", owner_id="owner-1",
            config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        )
        event = self.store.load()["attentionEvents"][0]
        calls = []
        transport = ntfy_module.NtfyTransport(
            requester=lambda **kwargs: calls.append(kwargs) or {"status": 503},
            max_attempts=1,
        )
        config = tracking_config(ntfy_enabled=True)
        config["ntfy"]["maxAttempts"] = 1
        preflight = tracking_module.TrackingPreflight(lambda value: observation(value))
        linear = linear_module.LinearTransport(
            endpoint="https://api.linear.app/graphql", allowed_host="api.linear.app",
            requester=lambda **_: (_ for _ in ()).throw(AssertionError("no Linear request")),
        )
        control = control_module.LinearControlPlane(records=self.records, preflight=preflight, linear=linear, ntfy=transport)
        environment = {
            "LINEAR_API_KEY": "linear-secret", "NTFY_URL": "https://ntfy.sh",
            "NTFY_TOPIC": "topic", "NTFY_TOKEN": "ntfy-secret",
        }
        attestation = preflight.run(
            config, environment=environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        notify = dict(
            config_value=config, environment=environment, now=LATER,
            attestation=attestation, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0",
        )
        first = control.notify(event["id"], **notify)
        second = control.notify(event["id"], **notify)
        self.assertEqual(first["status"], "failed")
        self.assertEqual(second["status"], "already-recorded")
        self.assertEqual(len(calls), 1)
        status = control.status({"schemaVersion": "1.0", "reservations": {}})
        self.assertEqual(len(status["controlPlane"]["notificationFailures"]), 1)
        self.assertNotIn("sentinel-secret", repr(status))
        self.assertNotIn("ntfy-secret", repr(status))

    def test_publish_crash_and_concurrent_replay_never_send_twice(self):
        self.records.record_failure(
            failure_kind="worker-failure", issue_id="SAAS-47", source_id="worker-1",
            source_timestamp=NOW, created_at=NOW, link=LINK, summary="Worker stopped",
            actionable=True, transient_within_budget=False,
        )
        event = self.store.load()["attentionEvents"][0]
        calls = []
        transport = ntfy_module.NtfyTransport(
            requester=lambda **kwargs: calls.append(kwargs) or {"status": 204}
        )
        config = tracking_config(ntfy_enabled=True)
        environment = {"LINEAR_API_KEY": "x", "NTFY_URL": "https://ntfy.sh", "NTFY_TOPIC": "topic"}
        preflight = tracking_module.TrackingPreflight(lambda value: observation(value))
        linear = linear_module.LinearTransport(
            endpoint="https://api.linear.app/graphql", allowed_host="api.linear.app",
            requester=lambda **_: {},
        )
        control = control_module.LinearControlPlane(
            records=self.records, preflight=preflight, linear=linear, ntfy=transport
        )
        attestation = preflight.run(
            config, environment=environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        args = dict(
            config_value=config, environment=environment, now=LATER,
            attestation=attestation, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0",
        )
        with self.assertRaises(RuntimeError):
            control.notify(event["id"], after_publish=lambda: (_ for _ in ()).throw(RuntimeError("crash")), **args)
        notification = self.store.load()["notifications"][0]
        recovery = self.records.require_notification_recovery(notification["id"])
        self.assertEqual(recovery["data"]["attemptState"], "recovery-required")
        replay = control.notify(event["id"], **args)
        self.assertEqual(replay["status"], "recovery-required")
        self.assertEqual(len(calls), 1)

    def test_concurrent_notification_callers_have_one_sender(self):
        self.records.record_failure(
            failure_kind="worker-failure", issue_id="SAAS-47", source_id="worker-race",
            source_timestamp=NOW, created_at=NOW, link=LINK, summary="Worker stopped",
            actionable=True, transient_within_budget=False,
        )
        event = self.store.load()["attentionEvents"][0]
        entered = threading.Event()
        release = threading.Event()
        calls = []

        def requester(**kwargs):
            calls.append(kwargs)
            entered.set()
            release.wait(5)
            return {"status": 204}

        config = tracking_config(ntfy_enabled=True)
        environment = {"LINEAR_API_KEY": "x", "NTFY_URL": "https://ntfy.sh", "NTFY_TOPIC": "topic"}
        preflight = tracking_module.TrackingPreflight(lambda value: observation(value))
        linear = linear_module.LinearTransport(
            endpoint="https://api.linear.app/graphql", allowed_host="api.linear.app",
            requester=lambda **_: {},
        )
        control = control_module.LinearControlPlane(
            records=self.records, preflight=preflight, linear=linear,
            ntfy=ntfy_module.NtfyTransport(requester=requester),
        )
        attestation = preflight.run(
            config, environment=environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        args = dict(
            config_value=config, environment=environment, now=LATER,
            attestation=attestation, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0",
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(control.notify, event["id"], **args)
            self.assertTrue(entered.wait(2))
            second = pool.submit(control.notify, event["id"], **args)
            second_result = second.result(timeout=2)
            release.set()
            first_result = first.result(timeout=2)
        self.assertEqual(first_result["status"], "delivered")
        self.assertEqual(second_result["status"], "recovery-required")
        self.assertEqual(len(calls), 1)

    def test_corrupted_persisted_authority_records_fail_closed(self):
        self.records.request_decision(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            question="Choose", options=[{"id": "a", "consequence": "A"}, {"id": "b", "consequence": "B"}],
            recommendation="a", owner_id="owner-1",
            config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        )
        event_id = self.store.load()["attentionEvents"][0]["id"]
        self.records.begin_notification(event_id, LATER)
        quiet = self.records.propose_issue_contract(
            issue_id="SAAS-48", source_timestamp=NOW, created_at=NOW, link=LINK,
            summary="Deferred provider work", proposal_kind="external-integration",
        )
        original = self.store.load()

        def changed_owner(value):
            value["decisions"][0]["data"]["ownerId"] = "attacker"

        def consumed_without_marker(value):
            value["decisions"][0]["status"] = "consumed"

        def forged_source(value):
            value["attentionEvents"][0]["data"]["sourceId"] = "decision-" + "0" * 24

        def terminal_without_evidence(value):
            value["notifications"][0]["status"] = "delivered"

        def changed_config_binding(value):
            value["decisions"][0]["data"]["configDigest"] = "sha256:" + "d" * 64

        def changed_attention_taxonomy(value):
            event = value["attentionEvents"][0]
            event["kind"] = "worker-failure"
            event["id"] = records_module.stable_id(
                "attention", event["issueId"], event["kind"], event["data"]["sourceId"]
            )

        def missing_required_attention(value):
            value["attentionEvents"] = []

        def extra_quiet_attention(value):
            event = copy.deepcopy(value["attentionEvents"][0])
            event.update({
                "kind": "external-blocker", "issueId": quiet["issueId"],
                "sourceTimestamp": quiet["sourceTimestamp"], "link": quiet["link"],
                "summary": quiet["summary"], "data": {"sourceId": quiet["id"]},
            })
            event["id"] = records_module.stable_id(
                "attention", event["issueId"], event["kind"], quiet["id"]
            )
            value["attentionEvents"].append(event)

        def mismatched_notification_metadata(value):
            value["notifications"][0]["summary"] = "forged summary"

        for mutation in (
            changed_owner, consumed_without_marker, forged_source,
            terminal_without_evidence, changed_config_binding,
            changed_attention_taxonomy, missing_required_attention,
            extra_quiet_attention, mismatched_notification_metadata,
        ):
            corrupted = copy.deepcopy(original)
            mutation(corrupted)
            self.store.path.write_text(json.dumps(corrupted), encoding="utf-8")
            with self.assertRaises(Exception):
                self.store.load()
        self.store.path.write_text(json.dumps(original), encoding="utf-8")
        self.assertEqual(self.store.load(), original)


if __name__ == "__main__":
    unittest.main()
