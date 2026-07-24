from __future__ import annotations

import importlib
import tempfile
import unittest
from tests.linear_delivery_supervisor import load_supervisor_package

package = load_supervisor_package(); module = importlib.import_module(package.__name__ + ".publication_recovery")
control_records = importlib.import_module(package.__name__ + ".control_plane_records")
supervisor_module = importlib.import_module(package.__name__ + ".supervisor")
SHA = "a" * 40
REPOSITORY_ID = "repo-" + "a" * 24

class Requests:
    def publication_refusal(self, **kwargs): self.kwargs = kwargs; return {"id": "request-1"}

class OneShotReply:
    def __init__(self, operation_id, head_sha):
        self.value = {"status": "authorized", "operationId": operation_id, "headSha": head_sha, "consumedReplyId": "reply-1"}
    def consume(self):
        value, self.value = self.value, None
        return value

class PublicationRecoveryTests(unittest.TestCase):
    def test_supervisor_publication_context_uses_schema_valid_linear_issue_link(self):
        self.assertEqual(
            "https://linear.app/issue/SAAS-48",
            supervisor_module._linear_issue_link("SAAS-48"),
        )

    def setUp(self):
        self.releases = 0; self.labels = []; self.states = []; self.notifications = []; self.requests = Requests()
        self.subject = module.PublicationRecovery(requests=self.requests, release_lease=lambda: setattr(self, "releases", self.releases + 1), set_labels=self.labels.append, set_issue_state=self.states.append, notify=self.notifications.append)
        self.state = {"operationId": "push-1", "headSha": SHA, "status": "attempting", "attemptCount": 1, "retryCount": 0,
            "preservedState": {"issueState": "In Progress", "autonomous": True, "globalWip": True, "reservationId": "r", "worktreePath": "C:/work", "physicalWorktreeFingerprint": "sha256:" + "b" * 64, "branch": "codex/SAAS-48-x", "pullRequest": None, "evidenceRefs": []}}
        self.context = {"issue_id": "SAAS-48", "operation_id": "push-1", "head_sha": SHA, "source_timestamp": "2026-07-22T00:00:00Z", "created_at": "2026-07-22T00:01:00Z", "link": "https://example.invalid/48", "reason": "refused", "evidence": {"issueState": "In Progress", "reservationId": "r", "worktreePath": "C:/work", "branch": "codex/SAAS-48-x", "prId": "none"}, "owner_id": "owner", "config_digest": "sha256:" + "c" * 64, "repository_id": REPOSITORY_ID, "refusal_kind": "stable"}

    def test_transient_backoff_then_stable_pause_preserves_work(self):
        transient = self.subject.refusal(publication=self.state, response={"statusCode": 429}, readback={"applied": False}, now="2026-07-22T00:00:00Z", request_context=self.context)
        self.assertEqual("retry-wait", transient["status"]); self.assertEqual(1, transient["retryCount"]); self.assertEqual(1, self.releases)
        stable = self.subject.refusal(publication=self.state, response={"code": "permission-denied"}, readback={"applied": False}, now="2026-07-22T00:00:00Z", request_context=self.context)
        self.assertEqual("paused", stable["status"]); self.assertEqual({"autonomous", "blocked", "needs-human"}, self.labels[-1]); self.assertEqual(1, len(self.notifications))

    def test_attended_retry_requires_all_rereads_and_exact_reply(self):
        paused = dict(self.state, status="paused")
        rereads = {name: True for name in module.REQUIRED_ATTENDED_REREADS}
        reply = OneShotReply("push-1", SHA); persisted = []; attempts = []
        def applied():
            attempts.append("attempt"); return {"applied": True, "publication": dict(persisted[-1], status="pushed", activeProviderOperation=None, refusalKind=None)}
        result = self.subject.attended_retry(publication=paused, consume_reply=reply.consume, rereads=rereads, persist_consumption=persisted.append, attempt=applied)
        self.assertEqual("pushed", result["status"]); self.assertEqual({"autonomous"}, self.labels[-1])
        self.assertEqual("reply-1", persisted[0]["consumedReplyId"]); self.assertEqual(["attempt"], attempts)
        with self.assertRaises(module.PublicationRecoveryError):
            self.subject.attended_retry(publication=paused, consume_reply=reply.consume, rereads=rereads, persist_consumption=persisted.append, attempt=lambda: attempts.append("duplicate") or {"applied": True})
        self.assertEqual(["attempt"], attempts)
        rereads.pop("provider")
        with self.assertRaises(module.PublicationRecoveryError): self.subject.attended_retry(publication=paused, consume_reply=lambda: None, rereads=rereads, persist_consumption=persisted.append, attempt=lambda: {"applied": True})

    def test_consumption_is_persisted_before_attempt_crash_and_cannot_replay(self):
        paused = dict(self.state, status="paused")
        rereads = {name: True for name in module.REQUIRED_ATTENDED_REREADS}
        reply = OneShotReply("push-1", SHA); persisted = []
        def crash(): raise RuntimeError("crash after durable consumption")
        with self.assertRaises(RuntimeError):
            self.subject.attended_retry(publication=paused, consume_reply=reply.consume, rereads=rereads, persist_consumption=persisted.append, attempt=crash)
        self.assertEqual("reply-1", persisted[0]["consumedReplyId"])
        with self.assertRaises(module.PublicationRecoveryError):
            self.subject.attended_retry(publication=paused, consume_reply=reply.consume, rereads=rereads, persist_consumption=persisted.append, attempt=lambda: {"applied": True})

    def test_proven_nonapplication_reopens_request_without_losing_publication_reply(self):
        paused = dict(self.state, status="paused", refusalKind="permission")
        rereads = {name: True for name in module.REQUIRED_ATTENDED_REREADS}
        reply = OneShotReply("push-1", SHA); persisted = []; reopened = []
        with self.assertRaises(RuntimeError):
            self.subject.attended_retry(
                publication=paused, consume_reply=reply.consume, rereads=rereads,
                persist_consumption=persisted.append,
                attempt=lambda: (_ for _ in ()).throw(RuntimeError("provider crash")),
                reconcile_application=lambda: {"applied": False, "ambiguous": False},
                reopen_request=lambda reply_id: reopened.append(reply_id) or {"status": "pending"},
            )
        self.assertEqual("reply-1", persisted[-1]["consumedReplyId"])
        self.assertEqual("permission", persisted[-1]["refusalKind"])
        self.assertEqual(["reply-1"], reopened)
        self.assertEqual({"autonomous", "blocked", "needs-human"}, self.labels[-1])

    def test_real_control_plane_reply_record_is_consumed_once_before_attempt(self):
        with tempfile.TemporaryDirectory() as root:
            records = control_records.ControlPlaneRecords(
                control_records.ControlPlaneStore(root, fixture_mode=True)
            )
            request = records.publication_refusal(
                issue_id="SAAS-48", operation_id="push-1", head_sha=SHA,
                source_timestamp="2026-07-22T00:00:00Z",
                created_at="2026-07-22T00:01:00Z", link="https://example.invalid/48",
                reason="stable refusal", evidence={"issueState": "In Progress", "reservationId": "r", "worktreePath": "C:/work", "branch": "codex/SAAS-48-x", "prId": "none"},
                owner_id="owner", config_digest="sha256:" + "c" * 64,
                repository_id=REPOSITORY_ID, refusal_kind="stable",
            )
            def consume():
                return records.consume_publication_reply(
                    request_id=request["id"], actor_id="owner", reply_id="reply-real-1",
                    reply_created_at="2026-07-22T00:02:00Z",
                    body=f"RETRY-PUBLICATION push-1 {SHA}", reconciled=True,
                    owner_id="owner", config_digest="sha256:" + "c" * 64,
                    repository_id=REPOSITORY_ID,
                )
            paused = dict(self.state, status="paused"); persisted = []; attempts = []
            rereads = {name: True for name in module.REQUIRED_ATTENDED_REREADS}
            self.subject.attended_retry(
                publication=paused, consume_reply=consume, rereads=rereads,
                persist_consumption=persisted.append,
                attempt=lambda: attempts.append("attempt") or {"applied": True, "publication": dict(persisted[-1], status="pushed", activeProviderOperation=None, refusalKind=None)},
            )
            self.assertEqual("reply-real-1", persisted[0]["consumedReplyId"])
            with self.assertRaises(module.PublicationRecoveryError):
                self.subject.attended_retry(
                    publication=paused, consume_reply=consume, rereads=rereads,
                    persist_consumption=persisted.append,
                    attempt=lambda: attempts.append("duplicate") or {"applied": True},
                )
            self.assertEqual(["attempt"], attempts)

    def test_first_refusal_after_three_retries_pauses(self):
        exhausted = dict(self.state, retryCount=3, attemptCount=4)
        result = self.subject.refusal(publication=exhausted, response={"statusCode": 503}, readback={"applied": False}, now="2026-07-22T00:00:00Z", request_context=self.context)
        self.assertEqual("paused", result["status"])

    def test_transient_retry_matrix_uses_5_15_30_and_capped_retry_after(self):
        current = dict(self.state)
        expected = ("2026-07-22T00:05:00Z", "2026-07-22T00:15:00Z", "2026-07-22T00:30:00Z")
        for index, timestamp in enumerate(expected, 1):
            current["attemptCount"] = index
            current = self.subject.refusal(
                publication=current, response={"statusCode": 429},
                readback={"applied": False}, now="2026-07-22T00:00:00Z",
                request_context=self.context,
            )
            self.assertEqual(index, current["retryCount"])
            self.assertEqual(timestamp, current["nextRetryAt"])
        capped = self.subject.refusal(
            publication=dict(self.state),
            response={"statusCode": 503, "retryAfterSeconds": 9999},
            readback={"applied": False}, now="2026-07-22T00:00:00Z",
            request_context=self.context,
        )
        self.assertEqual("2026-07-22T00:30:00Z", capped["nextRetryAt"])

    def test_attended_malformed_stale_duplicate_and_failed_attempt_restore_pause_labels(self):
        paused = dict(self.state, status="paused")
        rereads = {name: True for name in module.REQUIRED_ATTENDED_REREADS}
        persisted = []
        for reply in (
            None,
            {"status": "authorized", "operationId": "wrong", "headSha": SHA, "consumedReplyId": "bad"},
            {"status": "authorized", "operationId": "push-1", "headSha": "b" * 40, "consumedReplyId": "bad"},
        ):
            with self.assertRaises(module.PublicationRecoveryError):
                self.subject.attended_retry(
                    publication=paused, consume_reply=lambda reply=reply: reply,
                    rereads=rereads, persist_consumption=persisted.append,
                    attempt=lambda: {"applied": True},
                )
        reply = OneShotReply("push-1", SHA)
        with self.assertRaises(RuntimeError):
            self.subject.attended_retry(
                publication=paused, consume_reply=reply.consume, rereads=rereads,
                persist_consumption=persisted.append,
                attempt=lambda: (_ for _ in ()).throw(RuntimeError("crash")),
            )
        self.assertEqual("reply-1", persisted[-1]["consumedReplyId"])
        self.assertEqual({"autonomous", "blocked", "needs-human"}, self.labels[-1])
        with self.assertRaises(module.PublicationRecoveryError):
            self.subject.attended_retry(
                publication=paused, consume_reply=reply.consume, rereads=rereads,
                persist_consumption=persisted.append, attempt=lambda: {"applied": True},
            )

    def test_repair_exhaustion_updates_same_request_and_notifies(self):
        exhausted = dict(self.state, repairAttempt=3)
        result = self.subject.repair_exhausted(publication=exhausted, request_context=self.context)
        self.assertEqual("paused", result["status"]); self.assertEqual("Backlog", self.states[-1])
        self.assertEqual("repair-exhausted", self.notifications[-1]["kind"])
