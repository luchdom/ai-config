from __future__ import annotations

import unittest
import tempfile
import copy
import json
import threading
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from tests.linear_delivery_control_plane.support import (
    fixture_engine_registry, issue, observation, package, raw_issue, tracking_config,
)


selection = __import__(package.__name__ + ".selection", fromlist=["select_candidate"])
linear = __import__(package.__name__ + ".linear_transport", fromlist=["LinearAmbiguousWrite"])
control_module = __import__(package.__name__ + ".control_plane", fromlist=["LinearControlPlane"])
registry_module = __import__(package.__name__ + ".control_plane_registry", fromlist=["EngineRegistryError"])
records_module = __import__(package.__name__ + ".control_plane_records", fromlist=["ControlPlaneStore"])
tracking_module = __import__(package.__name__ + ".tracking", fromlist=["TrackingPreflight"])

NOW = "2026-07-19T12:00:00Z"
REPOSITORY_ID = "repo-" + "a" * 24
LINK = "https://linear.app/issue/SAAS-47"
CONFIG_DIGEST = "sha256:" + "c" * 64


class Authority:
    authority_id = "repository-authority-v1"
    def __init__(self, events, *, rollback=True):
        self.events = events
        self.rollback = rollback
        self.fail_prepare = False
        self.execution_owner_id = "worker-original"
        self.lease_revision = 1
        self.lease_expires_at = "2026-07-19T12:05:00Z"
        self.owner_dead = False
        self.recovery_entered = None
        self.recovery_release = None
        self.recover_entered = None
        self.recover_release = None
        self.commit_entered = None
        self.commit_release = None

    def current_execution_lease(self, *, operation_id, now):
        self.events.append(("execution-lease", operation_id))
        expires = (
            datetime.fromisoformat(now[:-1] + "+00:00") + timedelta(minutes=5)
        ).isoformat().replace("+00:00", "Z")
        return {
            "operationId": operation_id,
            "ownerId": self.execution_owner_id,
            "leaseRevision": self.lease_revision,
            "expiresAt": expires,
        }

    def authorize_recovery(
        self, *, operation_id, previous_owner_id, previous_lease_revision,
        previous_lease_expires_at, now,
    ):
        self.events.append(("authorize-recovery", operation_id))
        if self.recovery_entered is not None:
            self.recovery_entered.set()
        if self.recovery_release is not None:
            self.recovery_release.wait(5)
        if not self.owner_dead and now < previous_lease_expires_at:
            return {
                "status": "live", "operationId": operation_id,
                "previousOwnerId": previous_owner_id,
                "previousLeaseRevision": previous_lease_revision,
                "previousLeaseExpiresAt": previous_lease_expires_at,
                "observedAt": now,
            }
        return {
            "status": "authorized",
            "proofId": "proof-" + operation_id,
            "operationId": operation_id,
            "previousOwnerId": previous_owner_id,
            "previousLeaseRevision": previous_lease_revision,
            "previousLeaseExpiresAt": previous_lease_expires_at,
            "recoveryOwnerId": f"recovery-worker-{previous_lease_revision + 1}",
            "recoveryLeaseRevision": previous_lease_revision + 1,
            "recoveryLeaseExpiresAt": (
                datetime.fromisoformat(now[:-1] + "+00:00") + timedelta(minutes=5)
            ).isoformat().replace("+00:00", "Z"),
            "observedAt": now,
            "reason": "owner-dead" if self.owner_dead else "lease-expired",
        }

    def prepare(self, **kwargs):
        self.events.append("prepare-local-reservation-and-worktree")
        if self.fail_prepare:
            raise RuntimeError("simulated pre-provider crash")
        return {"status": "prepared", "operationId": kwargs["operation_id"]}

    def commit(self, **_):
        self.events.append("commit-local")
        if self.commit_entered is not None:
            self.commit_entered.set()
        if self.commit_release is not None:
            self.commit_release.wait(5)

    def rollback_if_safe(self, **_):
        self.events.append("rollback-check")
        return self.rollback

    def protect(self, **_):
        self.events.append("protect")

    def recover(self, **_):
        self.events.append("recover-local")
        if self.recover_entered is not None:
            self.recover_entered.set()
        if self.recover_release is not None:
            self.recover_release.wait(5)
        return {"status": "prepared"}


class ClaimPort:
    adapter_id = "linear-fixture-adapter"
    journal_id = "selection-claim-journal-v1"

    def __init__(self, transport, events):
        self.transport = transport
        self.events = events
        self.state = "Todo"
        self.entered = None
        self.release = None
        self.readback_failures = 0
        self.claim_error = None
        self.readback_entered = None
        self.readback_release = None

    def reread(self, issue_id, operation_id):
        self.events.append(("reread-port", operation_id))
        return issue(int(issue_id.rsplit("-", 1)[1]))

    def claim(self, selected, operation_id):
        self.events.append(("claim-port", operation_id))
        if self.claim_error is not None:
            raise self.claim_error
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            self.release.wait(5)
        self.state = "In Progress"

    def readback(self, issue_id, operation_id):
        self.events.append(("readback-port", operation_id))
        if self.readback_entered is not None:
            self.readback_entered.set()
        if self.readback_release is not None:
            self.readback_release.wait(5)
        if self.readback_failures:
            self.readback_failures -= 1
            raise RuntimeError("simulated readback crash")
        return issue(int(issue_id.rsplit("-", 1)[1]), state=self.state)


class SelectionTests(unittest.TestCase):
    def test_wip_precedence_and_complete_ordering(self):
        multiple = selection.reconcile_wip(
            [issue(10, state="In Progress"), issue(11, state="In Review")],
            autonomous_issue_id=None,
            reservation_issue_ids=set(),
        )
        self.assertEqual(multiple["action"], "fail-closed")
        self.assertTrue(multiple["attention"])
        manual = selection.reconcile_wip(
            [issue(10, state="In Progress")],
            autonomous_issue_id=None,
            reservation_issue_ids=set(),
        )
        self.assertEqual(manual["action"], "quiet-exit")
        resumed = selection.reconcile_wip(
            [issue(10, state="In Progress")],
            autonomous_issue_id="SAAS-10",
            reservation_issue_ids={"SAAS-10"},
        )
        self.assertEqual(resumed["action"], "resume")
        candidates = [
            issue(13, priority=2, createdAt="2026-07-01T00:00:00Z"),
            issue(12, priority=1, createdAt="2026-07-02T00:00:00Z"),
            issue(11, priority=1, createdAt="2026-07-02T00:00:00Z"),
            issue(9, labels=["autonomous", "stop"]),
        ]
        self.assertEqual(selection.select_candidate(candidates, "ai-config")["identifier"], "SAAS-11")

    def test_rejection_taxonomy_covers_scope_and_labels(self):
        value = issue(
            8, state="Backlog", labels=["external-integration"], parentId="x",
            repositoryKey="saas", scope="epic", goalComplete=False,
            externalDependency=True, title="Platform-wide program",
        )
        reasons = selection.rejection_reasons(value, "ai-config")
        self.assertIn("not-todo", reasons)
        self.assertIn("missing-autonomous-label", reasons)
        self.assertIn("cross-repository", reasons)
        self.assertIn("not-achievable-code-leaf", reasons)
        self.assertIn("incomplete-goal", reasons)
        self.assertIn("external-dependency", reasons)
        self.assertIn("broad-scope", reasons)

    def test_claim_order_is_local_then_remote_then_readback(self):
        events = []
        selected = issue(47)
        result = selection.claim_selected(
            selected,
            operation_id="operation-47",
            repository_key="ai-config",
            reread=lambda _: events.append("reread") or selected,
            authority=Authority(events),
            claim=lambda *_: events.append("claim-remote"),
            readback=lambda _: events.append("readback") or issue(47, state="In Progress"),
        )
        self.assertEqual(result["status"], "claimed")
        self.assertEqual(events, ["reread", "prepare-local-reservation-and-worktree", "claim-remote", "readback", "commit-local"])

    def test_prepare_failure_never_claims_and_ambiguous_readback_protects(self):
        class BrokenAuthority(Authority):
            def prepare(self, **_):
                self.events.append("prepare-failed")
                raise RuntimeError("local failure")

        events = []
        with self.assertRaises(RuntimeError):
            selection.claim_selected(
                issue(47), operation_id="operation-47", repository_key="ai-config",
                reread=lambda _: issue(47), authority=BrokenAuthority(events),
                claim=lambda *_: events.append("claim"), readback=lambda _: issue(47),
            )
        self.assertNotIn("claim", events)
        events = []
        reads = iter([RuntimeError("unknown"), RuntimeError("unknown")])
        with self.assertRaises(selection.ClaimRecoveryRequired):
            selection.claim_selected(
                issue(47), operation_id="operation-47", repository_key="ai-config",
                reread=lambda _: issue(47), authority=Authority(events, rollback=False),
                claim=lambda *_: (_ for _ in ()).throw(linear.LinearAmbiguousWrite("unknown")),
                readback=lambda _: (_ for _ in ()).throw(next(reads)),
            )
        self.assertIn("protect", events)

    def test_manual_label_removal_requires_matching_authority(self):
        calls = []
        with self.assertRaises(selection.SelectionError):
            selection.reconcile_manual_selection(
                issue_id="SAAS-47", matching_issue_id="SAAS-48",
                reservation_live=True, remove_autonomous_label=calls.append,
            )
        self.assertEqual(calls, [])
        self.assertTrue(selection.reconcile_manual_selection(
            issue_id="SAAS-47", matching_issue_id="SAAS-47",
            reservation_live=True, remove_autonomous_label=calls.append,
        ))


class ControlPlaneSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="selection-snapshot-")
        self.addCleanup(self.temporary.cleanup)
        self.store = records_module.ControlPlaneStore(Path(self.temporary.name), fixture_mode=True)
        self.records = records_module.ControlPlaneRecords(self.store)
        self.config = tracking_config()
        self.environment = {"LINEAR_API_KEY": "fixture"}
        self.provider_pages = [[]]
        self.provider_queries = []
        self.pagination_fault = None
        self.local_snapshot = {
            "reservations": [], "issueWorktrees": {},
            "recovery": {"status": "clean"}, "autonomousIssueId": None,
        }
        def requester(**kwargs):
            payload = json.loads(kwargs["body"])
            self.provider_queries.append(payload["query"])
            after = payload["variables"].get("after")
            index = 0 if after is None else int(after.rsplit("-", 1)[1])
            terminal = index == len(self.provider_pages) - 1
            page_info = {
                "hasNextPage": not terminal,
                "endCursor": None if terminal else f"cursor-{index + 1}",
            }
            if self.pagination_fault == "missing-flag":
                page_info.pop("hasNextPage")
            elif self.pagination_fault == "repeated-cursor" and index > 0:
                page_info = {"hasNextPage": True, "endCursor": after}
            return {"status": 200, "body": {"data": {"issues": {
                "nodes": [copy.deepcopy(item) if isinstance(item.get("state"), Mapping) else raw_issue(int(item["identifier"].rsplit("-", 1)[1]), **{
                    key: copy.deepcopy(value) for key, value in item.items()
                    if key not in {"id", "identifier"}
                }) for item in self.provider_pages[index]],
                "pageInfo": page_info,
            }}}}
        self.linear_transport = linear.LinearTransport(
            endpoint="https://api.linear.app/graphql", allowed_host="api.linear.app",
            requester=requester,
        )
        self.claim_events = []
        self.claim_authority = Authority(self.claim_events)
        self.claim_port = ClaimPort(self.linear_transport, self.claim_events)
        engine, registry_reference = fixture_engine_registry(
            linear=self.linear_transport,
            claim_port=self.claim_port, authority=self.claim_authority,
            api_key=lambda: self.environment["LINEAR_API_KEY"],
            local_observer=lambda: copy.deepcopy(self.local_snapshot),
        )
        self.supervisor = engine
        self.registry_reference = registry_reference
        self.preflight = tracking_module.TrackingPreflight(
            lambda value: observation(value), supervisor=engine,
            engine_registry_reference=registry_reference,
        )
        self.control = control_module.LinearControlPlane(
            records=self.records, preflight=self.preflight, linear=self.linear_transport,
        )
        self.attestation = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )

    def choose(self, issues, **overrides):
        self.provider_pages = copy.deepcopy(overrides.pop("pages", [issues]))
        self.pagination_fault = overrides.pop("pagination_fault", None)
        snapshot = dict(
            reservations=[], issueWorktrees={}, recovery={"status": "clean"},
            autonomousIssueId=None,
        )
        aliases = {
            "reservations": "reservations", "issue_worktrees": "issueWorktrees",
            "recovery": "recovery", "autonomous_issue_id": "autonomousIssueId",
        }
        for argument, snapshot_key in aliases.items():
            if argument in overrides:
                snapshot[snapshot_key] = overrides.pop(argument)
        overrides.pop("reservation_issue_ids", None)
        values = dict(
            repository_key="ai-config", attestation=self.attestation,
            config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=NOW, multiple_wip_link=LINK,
        )
        values.update(overrides)
        self.local_snapshot = snapshot
        return self.control.choose_or_resume(**values)

    def test_pending_decision_publication_foreign_authority_and_recovery_block_selection(self):
        self.records.request_decision(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            question="Choose", options=[{"id": "a", "consequence": "A"}, {"id": "b", "consequence": "B"}],
            recommendation="a", owner_id="owner-1",
            config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
        )
        self.assertEqual(self.choose([issue(48)])["action"], "protected-exit")

        with tempfile.TemporaryDirectory(prefix="selection-publication-") as root:
            records = records_module.ControlPlaneRecords(records_module.ControlPlaneStore(Path(root), fixture_mode=True))
            records.publication_refusal(
                issue_id="SAAS-47", operation_id="op-47", head_sha="a" * 40,
                source_timestamp=NOW, created_at=NOW, link=LINK, reason="ambiguous",
                evidence={"issueState": "In Review", "reservationId": "r", "worktreePath": str(Path(root).resolve() / "worktree"), "branch": "b", "prId": "1"},
                owner_id="owner-1",
                config_digest=CONFIG_DIGEST, repository_id=REPOSITORY_ID,
            )
            control = control_module.LinearControlPlane(records=records, preflight=self.preflight, linear=self.linear_transport)
            original = self.control
            self.control = control
            try:
                self.assertEqual(self.choose([issue(48)])["action"], "protected-exit")
            finally:
                self.control = original

        self.assertEqual(self.choose(
            [issue(48)],
            reservations=[{"issueId": "SAAS-47", "status": "live"}],
            reservation_issue_ids={"SAAS-47"},
        )["action"], "protected-exit")
        self.assertEqual(self.choose(
            [issue(48)], recovery={"status": "ambiguous"}
        )["action"], "protected-exit")

    def test_concurrent_selection_creates_one_claim_and_preflight_is_mandatory(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.choose([issue(48)]), range(2)))
        self.assertEqual(sorted(item["action"] for item in results), ["protected-exit", "selected"])
        self.assertEqual(len(self.store.load()["selectionClaims"]), 1)
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.choose([issue(49)], attestation={})
        drifted = tracking_config()
        drifted["owner"]["id"] = "attacker"
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.choose([issue(49)], config=drifted)

    def test_selection_requires_terminal_multi_page_observation(self):
        later_wip = self.choose(
            [], pages=[[issue(48)], [issue(47, state="In Progress")]]
        )
        self.assertEqual(later_wip["action"], "quiet-exit")
        selected = self.choose(
            [], pages=[
                [issue(49, priority=2)],
                [issue(48, priority=1, createdAt="2026-07-01T00:00:00Z")],
            ],
        )
        self.assertEqual(selected["issue"]["identifier"], "SAAS-48")

    def test_selection_refuses_missing_and_repeated_pagination_evidence(self):
        with self.assertRaises(linear.LinearProtocolError):
            self.choose([issue(48)], pagination_fault="missing-flag")
        with self.assertRaises(linear.LinearProtocolError):
            self.choose(
                [], pages=[[issue(49)], [issue(48)], [issue(47)]],
                pagination_fault="repeated-cursor",
            )
        self.assertEqual(self.store.load()["selectionClaims"], [])

    def test_observation_query_is_complete_and_incomplete_nested_nodes_fail(self):
        result = self.choose([issue(48)])
        self.assertEqual(result["issue"]["identifier"], "SAAS-48")
        query = self.provider_queries[-1]
        for field in (
            "identifier", "title", "priority", "createdAt", "repositoryKey",
            "scope", "goalComplete", "externalDependency", "state { name }",
            "labels { nodes { name } }", "parent { id }", "project { id name }",
        ):
            self.assertIn(field, query)
        incomplete = raw_issue(49)
        del incomplete["labels"]
        with self.assertRaises(registry_module.EngineRegistryError):
            self.choose([], pages=[[incomplete]])
        self.assertEqual(len(self.store.load()["selectionClaims"]), 1)

    def test_one_normalized_observation_drives_selection_and_migration(self):
        self.provider_pages = [[issue(49, priority=2), issue(48, priority=1)]]
        completed = self.supervisor.execute_control_plane_operation(
            self.registry_reference, "observe-issues", {},
            linear=self.linear_transport,
        )
        selected = selection.select_candidate(completed["nodes"], "ai-config")
        migration_module = __import__(package.__name__ + ".migration", fromlist=["build_migration_report"])
        report = migration_module.build_migration_report(
            completed, repository_key="ai-config", generated_at=NOW
        )
        self.assertEqual(selected["identifier"], "SAAS-48")
        self.assertEqual(
            {item["issueId"] for item in report["issues"]}, {"SAAS-48", "SAAS-49"}
        )

    def test_actionable_preflight_failure_is_composed_once(self):
        config = tracking_config(ntfy_enabled=True)
        environment = {
            "LINEAR_API_KEY": "fixture", "NTFY_URL": "https://evil.invalid", "NTFY_TOPIC": "topic"
        }
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.control.verify(
                config, environment=environment, repository_key="ai-config",
                repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
                issue_id="SAAS-47", failure_link=LINK,
            )
        state = self.store.load()
        self.assertEqual(len(state["followUps"]), 1)
        self.assertEqual(len(state["attentionEvents"]), 1)

    def test_claim_requires_matching_attestation_and_consumes_selection_claim(self):
        chosen = self.choose([issue(47)])
        arguments = dict(
            operation_id="operation-47", repository_key="ai-config",
            selection_claim_id=chosen["selectionClaimId"], config=self.config,
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.control.claim(chosen["issue"], attestation={}, **arguments)
        result = self.control.claim(chosen["issue"], attestation=self.attestation, **arguments)
        self.assertEqual(result["status"], "claimed")
        state = self.store.load()
        self.assertEqual(state["selectionClaims"][0]["status"], "consumed")

    def test_forged_selection_snapshot_binding_fails_on_load(self):
        self.choose([issue(47)])
        original = self.store.load()
        corrupted = copy.deepcopy(original)
        corrupted["selectionClaims"][0]["data"]["snapshotDigest"] = "sha256:" + "d" * 64
        self.store.path.write_text(json.dumps(corrupted), encoding="utf-8")
        with self.assertRaises(Exception):
            self.store.load()
        self.store.path.write_text(json.dumps(original), encoding="utf-8")

    def test_facade_binds_reply_authority_to_verified_owner_and_config(self):
        request = self.control.request_decision(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            question="Choose tenant policy",
            options=[{"id": "a", "consequence": "A"}, {"id": "b", "consequence": "B"}],
            recommendation="a", attestation=self.attestation, config=self.config,
            repository_key="ai-config", repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=NOW,
        )
        self.assertEqual(request["data"]["ownerId"], "owner-1")
        common = dict(
            decision_id=request["id"], reply_id="reply-1",
            reply_created_at="2026-07-19T12:01:00Z",
            body=f"DECIDE {request['id']} a", attestation=self.attestation,
            config=self.config, repository_key="ai-config", repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=NOW,
        )
        self.assertIsNone(self.control.consume_decision_reply(actor_id="attacker", **common))
        drifted = tracking_config()
        drifted["owner"]["id"] = "attacker"
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.control.consume_decision_reply(actor_id="attacker", **(common | {"config": drifted}))
        consumed = self.control.consume_decision_reply(actor_id="owner-1", **common)
        self.assertEqual(consumed["status"], "consumed")

    def test_fresh_matching_attestation_after_ttl_reuses_and_completes_durable_work(self):
        decision_args = dict(
            issue_id="SAAS-47", source_timestamp=NOW, created_at=NOW, link=LINK,
            question="Choose tenant policy",
            options=[{"id": "a", "consequence": "A"}, {"id": "b", "consequence": "B"}],
            recommendation="a", config=self.config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0",
        )
        decision = self.control.request_decision(
            **decision_args, attestation=self.attestation, now=NOW
        )
        fresh_now = "2026-07-19T12:06:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        replay = self.control.request_decision(
            **decision_args, attestation=fresh, now=fresh_now
        )
        self.assertEqual(replay["id"], decision["id"])
        consumed = self.control.consume_decision_reply(
            decision_id=decision["id"], actor_id="owner-1", reply_id="late-reply",
            reply_created_at=fresh_now, body=f"DECIDE {decision['id']} a",
            attestation=fresh, config=self.config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        self.assertEqual(consumed["status"], "consumed")

        publication_args = dict(
            issue_id="SAAS-48", operation_id="publish-48", head_sha="a" * 40,
            source_timestamp=NOW, created_at=NOW, link=LINK, reason="ambiguous",
            evidence={
                "issueState": "In Review", "reservationId": "r48",
                "worktreePath": str(Path(self.temporary.name).resolve() / "worktree"),
                "branch": "codex/saas-48", "prId": "48",
            }, refusal_kind="ambiguous", config=self.config,
            repository_key="ai-config", repository_id=REPOSITORY_ID,
            supervisor_version="1.0",
        )
        publication = self.control.publication_refusal(
            **publication_args, attestation=fresh, now=fresh_now
        )
        refreshed_again = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0",
            now="2026-07-19T12:07:00Z",
        )
        self.assertEqual(
            self.control.publication_refusal(
                **publication_args, attestation=refreshed_again,
                now="2026-07-19T12:07:00Z",
            )["id"],
            publication["id"],
        )
        authorized = self.control.consume_publication_reply(
            request_id=publication["id"], actor_id="owner-1", reply_id="late-pub",
            reply_created_at="2026-07-19T12:07:00Z",
            body="RETRY-PUBLICATION publish-48 " + "a" * 40, reconciled=True,
            attestation=refreshed_again, config=self.config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0",
            now="2026-07-19T12:07:00Z",
        )
        self.assertEqual(authorized["status"], "authorized")

        chosen = self.choose([issue(49)])
        selection_fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        result = self.control.claim(
            chosen["issue"], operation_id="operation-49", repository_key="ai-config",
            selection_claim_id=chosen["selectionClaimId"], attestation=selection_fresh,
            config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=fresh_now,
        )
        self.assertEqual(result["status"], "claimed")

    def test_claim_operation_cas_blocks_same_and_competing_concurrent_mutations(self):
        chosen = self.choose([issue(47)])
        self.claim_port.entered = threading.Event()
        self.claim_port.release = threading.Event()
        common = dict(
            selected=chosen["issue"], repository_key="ai-config",
            selection_claim_id=chosen["selectionClaimId"], attestation=self.attestation,
            config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=NOW,
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.control.claim, operation_id="op-a", **common)
            self.assertTrue(self.claim_port.entered.wait(2))
            same = self.control.claim(operation_id="op-a", **common)
            self.assertEqual(same["status"], "in-flight")
            live_recovery = self.control.claim(operation_id="op-a", recovery=True, **common)
            self.assertEqual(live_recovery["status"], "in-flight")
            with self.assertRaises(tracking_module.TrackingPreflightError):
                self.control.claim(operation_id="op-b", **common)
            self.claim_port.release.set()
            result = first.result(timeout=2)
        self.assertEqual(result["status"], "claimed")
        self.assertEqual(self.control.claim(operation_id="op-a", **common), result)
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.control.claim(operation_id="op-after-terminal", **common)
        self.assertEqual(
            [event for event in self.claim_events if event == "prepare-local-reservation-and-worktree"],
            ["prepare-local-reservation-and-worktree"],
        )
        self.assertEqual(
            [event for event in self.claim_events if isinstance(event, tuple) and event[0] == "claim-port"],
            [("claim-port", "op-a")],
        )

    def test_claim_recovery_uses_same_operation_and_fresh_attestation(self):
        chosen = self.choose([issue(47)])
        self.claim_port.readback_failures = 2
        common = dict(
            selected=chosen["issue"], operation_id="op-crash",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0",
        )
        with self.assertRaises(Exception):
            self.control.claim(attestation=self.attestation, now=NOW, **common)
        state = self.store.load()
        self.assertEqual(state["selectionClaims"][0]["status"], "protected")
        fresh_now = "2026-07-19T12:06:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        recovered = self.control.claim(
            attestation=fresh, now=fresh_now, recovery=True, **common
        )
        self.assertEqual(recovered["status"], "reconciled")
        self.assertEqual(
            self.control.claim(attestation=fresh, now=fresh_now, recovery=True, **common),
            recovered,
        )
        self.assertEqual(self.store.load()["selectionClaims"][0]["status"], "consumed")

    def test_two_recoverers_have_one_generation_owner_and_one_provider_claim(self):
        chosen = self.choose([issue(47)])
        self.claim_authority.fail_prepare = True
        common = dict(
            selected=chosen["issue"], operation_id="op-two-recoverers",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            config=self.config, repository_id=REPOSITORY_ID, supervisor_version="1.0",
        )
        with self.assertRaises(RuntimeError):
            self.control.claim(attestation=self.attestation, now=NOW, **common)
        self.claim_authority.fail_prepare = False
        fresh_now = "2026-07-19T12:06:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        self.claim_port.entered = threading.Event()
        self.claim_port.release = threading.Event()
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                self.control.claim, attestation=fresh, now=fresh_now,
                recovery=True, **common,
            )
            self.assertTrue(self.claim_port.entered.wait(2))
            second = self.control.claim(
                attestation=fresh, now=fresh_now, recovery=True, **common,
            )
            self.assertEqual(second["status"], "recovery-in-flight")
            self.claim_port.release.set()
            recovered = first.result(timeout=2)
        self.assertEqual(recovered["status"], "recovered")
        record = self.store.load()["selectionClaims"][0]
        self.assertEqual(record["data"]["recoveryGeneration"], 1)
        self.assertEqual(
            [event for event in self.claim_events if event == ("claim-port", "op-two-recoverers")],
            [("claim-port", "op-two-recoverers")],
        )
        self.assertEqual(
            self.control.claim(
                attestation=fresh, now=fresh_now, recovery=True, **common,
            ),
            recovered,
        )

    def test_active_generation_fence_blocks_takeover_at_every_side_effect_boundary(self):
        for boundary in ("before-provider", "during-provider", "before-readback", "before-commit"):
            with self.subTest(boundary=boundary):
                self.setUp()
                chosen = self.choose([issue(47)])
                self.claim_authority.fail_prepare = True
                operation_id = "op-fenced-" + boundary
                common = dict(
                    selected=chosen["issue"], operation_id=operation_id,
                    repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
                    config=self.config, repository_id=REPOSITORY_ID,
                    supervisor_version="1.0",
                )
                with self.assertRaises(RuntimeError):
                    self.control.claim(attestation=self.attestation, now=NOW, **common)
                self.claim_authority.fail_prepare = False
                fresh_now = "2026-07-19T12:06:00Z"
                fresh = self.preflight.run(
                    self.config, environment=self.environment, repository_key="ai-config",
                    repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
                )
                entered, release = threading.Event(), threading.Event()
                if boundary == "before-provider":
                    self.claim_authority.recover_entered = entered
                    self.claim_authority.recover_release = release
                elif boundary == "during-provider":
                    self.claim_port.entered = entered
                    self.claim_port.release = release
                elif boundary == "before-readback":
                    self.claim_port.readback_entered = entered
                    self.claim_port.readback_release = release
                else:
                    self.claim_authority.commit_entered = entered
                    self.claim_authority.commit_release = release
                recovery = common | {
                    "attestation": fresh, "now": fresh_now, "recovery": True,
                }
                with ThreadPoolExecutor(max_workers=2) as pool:
                    active = pool.submit(self.control.claim, **recovery)
                    self.assertTrue(entered.wait(2))
                    takeover_now = "2026-07-19T12:12:00Z"
                    takeover_attestation = self.preflight.run(
                        self.config, environment=self.environment,
                        repository_key="ai-config", repository_id=REPOSITORY_ID,
                        supervisor_version="1.0", now=takeover_now,
                    )
                    contender = self.control.claim(**(
                        recovery | {"now": takeover_now, "attestation": takeover_attestation}
                    ))
                    self.assertEqual(contender["status"], "recovery-in-flight")
                    release.set()
                    self.assertEqual(active.result(timeout=2)["status"], "recovered")
                self.assertEqual(
                    self.claim_events.count(("claim-port", operation_id)), 1
                )
                self.assertEqual(self.claim_events.count("commit-local"), 1)

    def test_inert_terminal_replay_is_stable_and_different_operation_is_rejected(self):
        chosen = self.choose([issue(47)])
        self.claim_port.claim_error = RuntimeError("definitive claim refusal")
        common = dict(
            selected=chosen["issue"], operation_id="op-inert",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            attestation=self.attestation, config=self.config,
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        with self.assertRaises(selection.ClaimRolledBack):
            self.control.claim(**common)
        replay = self.control.claim(**common)
        self.assertEqual(replay, {
            "status": "inert", "issueId": "SAAS-47", "operationId": "op-inert"
        })
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.control.claim(**(common | {"operation_id": "op-other"}))

    def test_copied_id_port_and_fake_authority_cannot_enter_facade(self):
        chosen = self.choose([issue(47)])
        copied = ClaimPort(self.linear_transport, [])
        fake = Authority([])
        with self.assertRaises(TypeError):
            control_module.LinearControlPlane(
                records=self.records, preflight=self.preflight,
                linear=self.linear_transport, claim_port=copied,
                claim_authority=fake,
            )
        with self.assertRaises(AttributeError):
            self.control.claim_port = copied
        with self.assertRaises(AttributeError):
            self.preflight._supervisor = object()
        self.assertFalse(hasattr(registry_module, "_compose_engine_registry"))
        self.assertFalse(hasattr(registry_module, "EngineAdapterRegistry"))
        self.assertFalse(hasattr(self.supervisor, "_install_control_plane_test_fixture"))
        self.assertFalse(hasattr(self.supervisor, "resolve_control_plane_registry"))
        with self.assertRaises(AttributeError):
            self.supervisor._control_plane_registries = {self.registry_reference: object()}
        with self.assertRaises(AttributeError):
            self.supervisor.execute_control_plane_operation = lambda *_args, **_kwargs: fake
        with self.assertRaises(AttributeError):
            object.__setattr__(
                self.supervisor, "execute_control_plane_operation",
                lambda *_args, **_kwargs: fake,
            )
        alternate, _ = fixture_engine_registry(
            linear=self.linear_transport, claim_port=copied, authority=fake,
            api_key=lambda: "fixture", local_observer=lambda: copy.deepcopy(self.local_snapshot),
        )
        # Even bypassing normal immutability cannot replace an attested entry:
        # the alternate engine does not own the opaque reference.
        original = self.preflight._supervisor
        object.__setattr__(self.preflight, "_supervisor", alternate)
        try:
            with self.assertRaises(tracking_module.TrackingPreflightError):
                self.control.claim(
                    chosen["issue"], operation_id="op-forged-registry",
                    repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
                    attestation=self.attestation, config=self.config,
                    repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
                )
        finally:
            object.__setattr__(self.preflight, "_supervisor", original)
        self.assertFalse(hasattr(registry_module, "EngineLinearClaimAdapter"))
        self.assertFalse(hasattr(registry_module, "EngineRepositoryAuthorityAdapter"))
        self.assertNotIn("prepare-local-reservation-and-worktree", self.claim_events)
        self.assertEqual(copied.state, "Todo")

    def test_hard_crashed_in_flight_operation_recovers_one_exclusive_generation(self):
        chosen = self.choose([issue(47)])
        verified = self.control._attest(
            self.attestation, config=self.config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        _, authority = self.control._verified_claim_ports(verified)
        acquired = self.control._acquire_selection(
            chosen["selectionClaimId"], operation_id="op-hard-crash",
            selected=chosen["issue"], verified=verified, now=NOW,
            recovery=False, authority=authority,
        )
        self.assertEqual(acquired["mode"], "acquired")
        self.assertEqual(self.store.load()["selectionClaims"][0]["status"], "in-flight")

        live = self.control.claim(
            chosen["issue"], operation_id="op-hard-crash",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            attestation=self.attestation, config=self.config,
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
            recovery=True,
        )
        self.assertEqual(live["status"], "in-flight")

        fresh_now = "2026-07-19T12:06:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        self.claim_port.entered = threading.Event()
        self.claim_port.release = threading.Event()
        common = dict(
            selected=chosen["issue"], operation_id="op-hard-crash",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            attestation=fresh, config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=fresh_now, recovery=True,
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.control.claim, **common)
            self.assertTrue(self.claim_port.entered.wait(2))
            second = self.control.claim(**common)
            self.assertEqual(second["status"], "recovery-in-flight")
            self.claim_port.release.set()
            recovered = first.result(timeout=2)
        self.assertEqual(recovered["status"], "recovered")
        record = self.store.load()["selectionClaims"][0]
        self.assertEqual(record["data"]["recoveryGeneration"], 1)
        self.assertEqual(
            [event for event in self.claim_events if event == ("claim-port", "op-hard-crash")],
            [("claim-port", "op-hard-crash")],
        )

    def test_hard_crash_after_provider_apply_reconciles_without_second_claim(self):
        chosen = self.choose([issue(47)])
        verified = self.control._attest(
            self.attestation, config=self.config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        _, authority = self.control._verified_claim_ports(verified)
        self.control._acquire_selection(
            chosen["selectionClaimId"], operation_id="op-provider-applied",
            selected=chosen["issue"], verified=verified, now=NOW,
            recovery=False, authority=authority,
        )
        self.claim_port.state = "In Progress"
        fresh_now = "2026-07-19T12:06:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        result = self.control.claim(
            chosen["issue"], operation_id="op-provider-applied",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            attestation=fresh, config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=fresh_now, recovery=True,
        )
        self.assertEqual(result["status"], "reconciled")
        self.assertNotIn(("claim-port", "op-provider-applied"), self.claim_events)

    def test_crashed_recovery_owner_expires_and_one_second_generation_wins(self):
        chosen = self.choose([issue(47)])
        verified = self.control._attest(
            self.attestation, config=self.config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        _, authority = self.control._verified_claim_ports(verified)
        self.control._acquire_selection(
            chosen["selectionClaimId"], operation_id="op-recovery-crash",
            selected=chosen["issue"], verified=verified, now=NOW,
            recovery=False, authority=authority,
        )
        first_recovery = self.control._acquire_selection(
            chosen["selectionClaimId"], operation_id="op-recovery-crash",
            selected=chosen["issue"], verified=verified, now="2026-07-19T12:06:00Z",
            recovery=True, authority=authority,
        )
        self.assertEqual(first_recovery["mode"], "recovery-acquired")
        self.assertEqual(first_recovery["record"]["data"]["recoveryGeneration"], 1)

        live = self.control._acquire_selection(
            chosen["selectionClaimId"], operation_id="op-recovery-crash",
            selected=chosen["issue"], verified=verified, now="2026-07-19T12:07:00Z",
            recovery=True, authority=authority,
        )
        self.assertEqual(live["mode"], "recovering")

        takeover_now = "2026-07-19T12:12:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=takeover_now,
        )
        self.claim_port.entered = threading.Event()
        self.claim_port.release = threading.Event()
        common = dict(
            selected=chosen["issue"], operation_id="op-recovery-crash",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            attestation=fresh, config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=takeover_now, recovery=True,
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            winner = pool.submit(self.control.claim, **common)
            self.assertTrue(self.claim_port.entered.wait(2))
            loser = self.control.claim(**common)
            self.assertEqual(loser["status"], "recovery-in-flight")
            self.claim_port.release.set()
            result = winner.result(timeout=2)
        self.assertEqual(result["status"], "recovered")
        record = self.store.load()["selectionClaims"][0]
        self.assertEqual(record["data"]["recoveryGeneration"], 2)
        self.assertEqual(record["data"]["recoveryLeaseRevision"], 3)
        self.assertEqual(
            [event for event in self.claim_events if event == ("claim-port", "op-recovery-crash")],
            [("claim-port", "op-recovery-crash")],
        )

    def test_second_generation_reconciles_crashes_at_each_recovery_boundary(self):
        chosen = self.choose([issue(47)])
        verified = self.control._attest(
            self.attestation, config=self.config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        _, authority = self.control._verified_claim_ports(verified)
        self.control._acquire_selection(
            chosen["selectionClaimId"], operation_id="op-stage-crash",
            selected=chosen["issue"], verified=verified, now=NOW,
            recovery=False, authority=authority,
        )
        self.control._acquire_selection(
            chosen["selectionClaimId"], operation_id="op-stage-crash",
            selected=chosen["issue"], verified=verified, now="2026-07-19T12:06:00Z",
            recovery=True, authority=authority,
        )
        recovering_state = self.store.load()
        takeover_now = "2026-07-19T12:12:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=takeover_now,
        )
        common = dict(
            selected=chosen["issue"], operation_id="op-stage-crash",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            attestation=fresh, config=self.config, repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=takeover_now, recovery=True,
        )
        for stage in ("local-recover", "provider-claim", "provider-readback"):
            with self.subTest(stage=stage):
                def reset(state):
                    state.clear()
                    state.update(copy.deepcopy(recovering_state))
                self.store.mutate(reset)
                self.claim_events.clear()
                self.claim_port.state = "Todo"
                if stage == "local-recover":
                    self.claim_authority.recover(
                        operation_id="op-stage-crash", issue=chosen["issue"]
                    )
                else:
                    self.claim_port.claim(chosen["issue"], "op-stage-crash")
                    if stage == "provider-readback":
                        self.claim_port.readback("SAAS-47", "op-stage-crash")
                provider_calls_before = len([
                    event for event in self.claim_events
                    if event == ("claim-port", "op-stage-crash")
                ])
                result = self.control.claim(**common)
                provider_calls_after = len([
                    event for event in self.claim_events
                    if event == ("claim-port", "op-stage-crash")
                ])
                self.assertEqual(
                    result["status"],
                    "recovered" if stage == "local-recover" else "reconciled",
                )
                self.assertEqual(
                    provider_calls_after - provider_calls_before,
                    1 if stage == "local-recover" else 0,
                )
                self.assertEqual(
                    self.store.load()["selectionClaims"][0]["data"]["recoveryGeneration"], 2
                )

    def test_pre_provider_crash_is_bound_and_recovered_without_competing_operation(self):
        chosen = self.choose([issue(47)])
        self.claim_authority.fail_prepare = True
        common = dict(
            selected=chosen["issue"], operation_id="op-pre-crash",
            repository_key="ai-config", selection_claim_id=chosen["selectionClaimId"],
            attestation=self.attestation, config=self.config,
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        with self.assertRaises(RuntimeError):
            self.control.claim(**common)
        self.assertFalse(any(
            isinstance(event, tuple) and event[0] == "claim-port"
            for event in self.claim_events
        ))
        self.assertEqual(self.store.load()["selectionClaims"][0]["status"], "protected")
        self.claim_authority.fail_prepare = False
        with self.assertRaises(tracking_module.TrackingPreflightError):
            self.control.claim(**(common | {"operation_id": "op-competing"}))
        fresh_now = "2026-07-19T12:06:00Z"
        fresh = self.preflight.run(
            self.config, environment=self.environment, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=fresh_now,
        )
        recovered = self.control.claim(**(
            common | {"recovery": True, "attestation": fresh, "now": fresh_now}
        ))
        self.assertEqual(recovered["status"], "recovered")


if __name__ == "__main__":
    unittest.main()
