"""Durable, redacted Linear control-plane records and reply reconciliation."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .base_runtime import load_base_runtime
from .contracts import validate_contract


class ControlPlaneRecordError(RuntimeError):
    pass


_FENCE_MAP_LOCK = threading.Lock()
_FENCE_LOCKS: dict[str, threading.Lock] = {}
CONTROL_PLANE_STATE_VERSION = "1.1"
LEGACY_CONTROL_PLANE_STATE_VERSION = "1.0"


def _process_alive(process_id: int) -> bool:
    if process_id < 1:
        return False
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _timestamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ControlPlaneRecordError("Record timestamp must be UTC RFC3339")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ControlPlaneRecordError("Record timestamp is invalid") from exc


def stable_id(kind: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{kind}-{digest}"


def _redact(value: Any) -> Any:
    return load_base_runtime().redact_value(value)


class ControlPlaneStore:
    """Atomic state file below the supervisor-owned state home.

    A supervisor mutex factory may be supplied for cross-process serialization.
    The internal lock keeps fixture/in-process use deterministic.
    """

    def __init__(
        self,
        state_home: str | Path,
        *,
        mutex: Callable[[], Any] | None = None,
        fixture_mode: bool = False,
    ):
        if mutex is None and not fixture_mode:
            raise ControlPlaneRecordError(
                "Control-plane state requires the shared supervisor mutex outside fixtures"
            )
        self.root = Path(os.path.realpath(os.path.abspath(state_home))) / "control-plane"
        self.path = self.root / "control-plane-state.json"
        self._external_mutex = mutex
        self._lock = threading.RLock()

    @contextmanager
    def _guard(self):
        with self._lock:
            if self._external_mutex is None:
                yield
            else:
                with self._external_mutex():
                    yield

    @staticmethod
    def empty() -> dict[str, Any]:
        return {
            "schemaVersion": CONTROL_PLANE_STATE_VERSION,
            "revision": 0,
            "decisions": [],
            "publicationRequests": [],
            "followUps": [],
            "attentionEvents": [],
            "notifications": [],
            "selectionClaims": [],
        }

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ControlPlaneRecordError("Control-plane state cannot be read safely") from exc
        migrated = (
            isinstance(value, dict)
            and value.get("schemaVersion") == LEGACY_CONTROL_PLANE_STATE_VERSION
        )
        if migrated and isinstance(value.get("publicationRequests"), list):
            for record in value["publicationRequests"]:
                data = record.get("data") if isinstance(record, dict) else None
                if isinstance(data, dict) and "lastConsumedReplyTimestamp" not in data:
                    active = data.get("consumedReplyTimestamp")
                    data["lastConsumedReplyTimestamp"] = (
                        active if isinstance(active, str) else record.get("sourceTimestamp")
                    )
        if migrated:
            if not isinstance(value.get("revision"), int) or value["revision"] < 0:
                raise ControlPlaneRecordError("Legacy control-plane revision is invalid")
            value["schemaVersion"] = CONTROL_PLANE_STATE_VERSION
            value["revision"] += 1
        validated = validate_contract("control-plane-state", value)
        if migrated:
            self._write_unlocked(validated)
        return validated

    def _write_unlocked(self, value: Mapping[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / f".{self.path.name}.{uuid.uuid4()}.tmp"
        try:
            temporary.write_text(
                json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def load(self) -> dict[str, Any]:
        with self._guard():
            return self._read_unlocked()

    def mutate(self, callback: Callable[[dict[str, Any]], Any]) -> tuple[dict[str, Any], Any]:
        with self._guard():
            before = self._read_unlocked()
            after = copy.deepcopy(before)
            result = callback(after)
            after["revision"] = before["revision"] + 1
            validated = validate_contract("control-plane-state", after)
            self._write_unlocked(validated)
            return copy.deepcopy(validated), copy.deepcopy(result)

    @contextmanager
    def operation_fence(self, operation_id: str):
        """Acquire a process/thread fence for every operation side effect.

        An active worker owns the fence even if its logical lease expires.  A
        crashed process releases ownership through its dead PID evidence, so a
        successor can safely take over without overlapping provider/local work.
        """

        if not isinstance(operation_id, str) or not operation_id:
            raise ControlPlaneRecordError("Operation fence requires an operation id")
        digest = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
        key = os.fspath(self.root / "operation-fences" / f"{digest}.lock")
        with _FENCE_MAP_LOCK:
            local_lock = _FENCE_LOCKS.setdefault(key, threading.Lock())
        if not local_lock.acquire(blocking=False):
            yield None
            return
        token = uuid.uuid4().hex
        path = Path(key)
        acquired = False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            for _ in range(2):
                try:
                    descriptor = os.open(
                        path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                    )
                except FileExistsError:
                    try:
                        existing = json.loads(path.read_text(encoding="utf-8"))
                        owner_pid = int(existing.get("processId", 0))
                    except (ValueError, TypeError, json.JSONDecodeError):
                        # A process may die after O_EXCL creation but before its
                        # owner document is complete. Never steal a fresh file;
                        # a later caller can reap an abandoned partial write.
                        try:
                            stale_partial = time.time() - path.stat().st_mtime > 5
                        except OSError:
                            stale_partial = False
                        if not stale_partial:
                            yield None
                            return
                        try:
                            path.unlink()
                        except FileNotFoundError:
                            pass
                        continue
                    except OSError:
                        yield None
                        return
                    if _process_alive(owner_pid):
                        yield None
                        return
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    json.dump(
                        {"operationId": operation_id, "processId": os.getpid(), "token": token},
                        stream, sort_keys=True,
                    )
                acquired = True
                break
            if not acquired:
                yield None
                return
            yield token
        finally:
            if acquired:
                try:
                    existing = json.loads(path.read_text(encoding="utf-8"))
                    if existing.get("token") == token:
                        path.unlink()
                except (FileNotFoundError, OSError, json.JSONDecodeError):
                    pass
            local_lock.release()

    def require_operation_fence(self, operation_id: str, token: str) -> None:
        digest = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
        path = self.root / "operation-fences" / f"{digest}.lock"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ControlPlaneRecordError("Operation side effect lacks its fence") from exc
        if (
            record.get("operationId") != operation_id
            or record.get("processId") != os.getpid()
            or record.get("token") != token
        ):
            raise ControlPlaneRecordError("Operation side effect fence was superseded")


class ControlPlaneRecords:
    def __init__(self, store: ControlPlaneStore):
        self.store = store

    @staticmethod
    def _record(
        *, kind: str, record_id: str, issue_id: str, created_at: str,
        source_timestamp: str, status: str, link: str, summary: str,
        data: Mapping[str, Any],
    ) -> dict[str, Any]:
        _timestamp(created_at)
        _timestamp(source_timestamp)
        return {
            "id": record_id,
            "kind": kind,
            "issueId": issue_id,
            "createdAt": created_at,
            "sourceTimestamp": source_timestamp,
            "status": status,
            "link": link,
            "summary": str(_redact(summary))[:500],
            "data": _redact(copy.deepcopy(dict(data))),
        }

    def _add_once(self, collection: str, record: Mapping[str, Any]) -> dict[str, Any]:
        def add(state: dict[str, Any]) -> dict[str, Any]:
            existing = next((item for item in state[collection] if item["id"] == record["id"]), None)
            if existing is not None:
                return existing
            state[collection].append(copy.deepcopy(dict(record)))
            return dict(record)

        _, result = self.store.mutate(add)
        return result

    def _add_composed(
        self,
        source_collection: str,
        source: Mapping[str, Any],
        attention: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        def add(state: dict[str, Any]) -> dict[str, Any]:
            existing = next(
                (item for item in state[source_collection] if item["id"] == source["id"]),
                None,
            )
            if existing is None:
                state[source_collection].append(copy.deepcopy(dict(source)))
                existing = state[source_collection][-1]
            if attention is not None and not any(
                item["id"] == attention["id"] for item in state["attentionEvents"]
            ):
                state["attentionEvents"].append(copy.deepcopy(dict(attention)))
            return existing

        _, result = self.store.mutate(add)
        return result

    def _attention_record(
        self, *, event_kind: str, issue_id: str, source_id: str,
        source_timestamp: str, created_at: str, link: str, summary: str,
    ) -> dict[str, Any]:
        return self._record(
            kind=event_kind,
            record_id=stable_id("attention", issue_id, event_kind, source_id),
            issue_id=issue_id,
            created_at=created_at,
            source_timestamp=source_timestamp,
            status="pending",
            link=link,
            summary=summary,
            data={"sourceId": source_id},
        )

    def request_decision(
        self, *, issue_id: str, source_timestamp: str, created_at: str, link: str,
        question: str, options: list[Mapping[str, str]], recommendation: str,
        owner_id: str, config_digest: str, repository_id: str,
    ) -> dict[str, Any]:
        if len(options) < 2:
            raise ControlPlaneRecordError("A material decision requires at least two options")
        safe_question = str(_redact(question))[:500]
        record_id = stable_id(
            "decision", issue_id, source_timestamp, safe_question, owner_id,
            config_digest, repository_id,
        )
        option_ids = [str(option["id"]) for option in options]
        record = self._record(
            kind="needs-human", record_id=record_id, issue_id=issue_id,
            created_at=created_at, source_timestamp=source_timestamp, status="pending",
            link=link, summary=safe_question,
            data={
                "options": [dict(option) for option in options],
                "recommendation": recommendation,
                "ownerId": owner_id,
                "configDigest": config_digest,
                "repositoryId": repository_id,
                "replySyntax": f"DECIDE {record_id} <{'|'.join(option_ids)}>",
                "consumedReplyId": None,
                "consumedReplyTimestamp": None,
            },
        )
        attention = self._attention_record(
            event_kind="needs-human", issue_id=issue_id, source_id=record_id,
            source_timestamp=source_timestamp, created_at=created_at, link=link,
            summary=safe_question,
        )
        return self._add_composed("decisions", record, attention)

    def consume_decision_reply(
        self, *, decision_id: str, actor_id: str, reply_id: str,
        reply_created_at: str, body: str,
        owner_id: str, config_digest: str, repository_id: str,
    ) -> dict[str, Any] | None:
        result: dict[str, Any] | None = None

        def consume(state: dict[str, Any]) -> None:
            nonlocal result
            record = next((item for item in state["decisions"] if item["id"] == decision_id), None)
            if (
                record is None or record["status"] != "pending"
                or actor_id != record["data"]["ownerId"]
                or owner_id != record["data"]["ownerId"]
                or config_digest != record["data"]["configDigest"]
                or repository_id != record["data"]["repositoryId"]
            ):
                return
            if _timestamp(reply_created_at) <= _timestamp(record["sourceTimestamp"]):
                return
            match = re.fullmatch(rf"DECIDE {re.escape(decision_id)} ([a-z0-9-]+)", body)
            allowed = {str(item["id"]) for item in record["data"]["options"]}
            if match is None or match.group(1) not in allowed:
                return
            record["status"] = "consumed"
            record["data"]["selectedOption"] = match.group(1)
            record["data"]["consumedReplyId"] = reply_id
            record["data"]["consumedReplyTimestamp"] = reply_created_at
            result = copy.deepcopy(record)

        self.store.mutate(consume)
        return result

    def publication_refusal(
        self, *, issue_id: str, operation_id: str, head_sha: str,
        source_timestamp: str, created_at: str, link: str, reason: str,
        evidence: Mapping[str, Any], owner_id: str,
        config_digest: str, repository_id: str,
        refusal_kind: str = "ambiguous",
    ) -> dict[str, Any]:
        required_evidence = {"issueState", "reservationId", "worktreePath", "branch", "prId"}
        if set(evidence) != required_evidence or any(not isinstance(evidence[key], str) or not evidence[key] for key in required_evidence):
            raise ControlPlaneRecordError("Publication evidence is incomplete or unexpected")
        record_id = stable_id(
            "publication", issue_id, operation_id, head_sha, owner_id,
            config_digest, repository_id,
        )
        record = self._record(
            kind="publication-refusal", record_id=record_id, issue_id=issue_id,
            created_at=created_at, source_timestamp=source_timestamp, status="pending",
            link=link, summary=reason,
            data={
                "operationId": operation_id,
                "headSha": head_sha,
                "evidence": dict(evidence),
                "ownerId": owner_id,
                "configDigest": config_digest,
                "repositoryId": repository_id,
                "refusalKind": refusal_kind,
                "replySyntax": f"RETRY-PUBLICATION {operation_id} {head_sha}",
                "consumedReplyId": None,
                "consumedReplyTimestamp": None,
                "lastConsumedReplyTimestamp": source_timestamp,
            },
        )
        if refusal_kind not in {"stable", "exhausted", "ambiguous"}:
            raise ControlPlaneRecordError("Publication refusal kind is not actionable")
        attention = self._attention_record(
            event_kind="publication-refusal", issue_id=issue_id, source_id=record_id,
            source_timestamp=source_timestamp, created_at=created_at, link=link,
            summary=reason,
        )
        return self._add_composed("publicationRequests", record, attention)

    def consume_publication_reply(
        self, *, request_id: str, actor_id: str, reply_id: str,
        reply_created_at: str, body: str, reconciled: bool,
        owner_id: str, config_digest: str, repository_id: str,
    ) -> dict[str, Any] | None:
        result: dict[str, Any] | None = None

        def consume(state: dict[str, Any]) -> None:
            nonlocal result
            record = next((item for item in state["publicationRequests"] if item["id"] == request_id), None)
            if (
                record is None or record["status"] != "pending"
                or actor_id != (record or {}).get("data", {}).get("ownerId")
                or owner_id != (record or {}).get("data", {}).get("ownerId")
                or config_digest != (record or {}).get("data", {}).get("configDigest")
                or repository_id != (record or {}).get("data", {}).get("repositoryId")
                or not reconciled
                or _timestamp(reply_created_at) <= max(
                    _timestamp(record["sourceTimestamp"]),
                    _timestamp(
                        record["data"]["lastConsumedReplyTimestamp"],
                    ),
                )
                or reply_id == (record or {}).get("data", {}).get("consumedReplyId")
            ):
                return
            data = record["data"]
            expected = f"RETRY-PUBLICATION {data['operationId']} {data['headSha']}"
            if body != expected:
                return
            record["status"] = "authorized"
            record["data"]["consumedReplyId"] = reply_id
            record["data"]["consumedReplyTimestamp"] = reply_created_at
            record["data"]["lastConsumedReplyTimestamp"] = reply_created_at
            result = {
                "status": "authorized",
                "requestId": record["id"],
                "operationId": data["operationId"],
                "headSha": data["headSha"],
                "consumedReplyId": reply_id,
                "consumedReplyTimestamp": reply_created_at,
                "evidence": copy.deepcopy(data["evidence"]),
            }

        self.store.mutate(consume)
        return result

    def reopen_publication_request(
        self, *, request_id: str, consumed_reply_id: str,
    ) -> dict[str, Any] | None:
        """Reopen one request while retaining its durable reply-time lower bound."""

        result: dict[str, Any] | None = None

        def reopen(state: dict[str, Any]) -> None:
            nonlocal result
            record = next(
                (item for item in state["publicationRequests"] if item["id"] == request_id),
                None,
            )
            if (
                record is None or record["status"] != "authorized"
                or record.get("data", {}).get("consumedReplyId") != consumed_reply_id
            ):
                return
            record["status"] = "pending"
            # Pending requests have no active consumption marker. The durable
            # lower bound survives so delayed alternate replies cannot regain
            # one-shot mutation authority.
            record["data"]["consumedReplyId"] = None
            record["data"]["consumedReplyTimestamp"] = None
            result = copy.deepcopy(record)

        self.store.mutate(reopen)
        return result

    def propose_follow_up(
        self, *, issue_id: str, source_timestamp: str, created_at: str, link: str,
        title: str, independently_actionable: bool, achievable: bool,
    ) -> dict[str, Any] | None:
        if not independently_actionable or not achievable:
            return None
        safe_title = str(_redact(title))[:500]
        record_id = stable_id("followup", issue_id, source_timestamp, safe_title)
        record = self._record(
            kind="external-integration", record_id=record_id, issue_id=issue_id,
            created_at=created_at, source_timestamp=source_timestamp, status="pending",
            link=link, summary=safe_title,
            data={
                "proposalType": "external-prerequisite",
                "proposedState": "Backlog",
                "proposedLabel": "external-integration",
            },
        )
        attention = self._attention_record(
            event_kind="external-blocker", issue_id=issue_id, source_id=record_id,
            source_timestamp=source_timestamp, created_at=created_at, link=link,
            summary=safe_title,
        )
        return self._add_composed("followUps", record, attention)

    def propose_issue_contract(
        self, *, issue_id: str, source_timestamp: str, created_at: str,
        link: str, summary: str, proposal_kind: str,
    ) -> dict[str, Any]:
        if proposal_kind not in {"needs-refinement", "external-integration"}:
            raise ControlPlaneRecordError("Issue proposal kind is unsupported")
        safe_summary = str(_redact(summary))[:500]
        record_id = stable_id("proposal", issue_id, source_timestamp, safe_summary, proposal_kind)
        record = self._record(
            kind=proposal_kind, record_id=record_id, issue_id=issue_id,
            created_at=created_at, source_timestamp=source_timestamp, status="pending",
            link=link, summary=safe_summary,
            data={
                "proposalType": "issue-contract",
                "proposedState": "Backlog",
                "proposedLabel": proposal_kind,
            },
        )
        return self._add_composed("followUps", record, None)

    def record_failure(
        self, *, failure_kind: str, issue_id: str, source_id: str,
        source_timestamp: str, created_at: str, link: str, summary: str,
        actionable: bool, transient_within_budget: bool,
    ) -> dict[str, Any] | None:
        if failure_kind not in {"worker-failure", "preflight-failure", "reconciliation-failure"}:
            raise ControlPlaneRecordError("Failure kind is unsupported")
        if not actionable or transient_within_budget:
            return None
        record_id = stable_id("failure", issue_id, failure_kind, source_id)
        record = self._record(
            kind=failure_kind, record_id=record_id, issue_id=issue_id,
            created_at=created_at, source_timestamp=source_timestamp, status="pending",
            link=link, summary=summary, data={"sourceId": source_id},
        )
        attention_kind = "multiple-wip" if failure_kind == "reconciliation-failure" else failure_kind
        attention = self._attention_record(
            event_kind=attention_kind, issue_id=issue_id, source_id=record_id,
            source_timestamp=source_timestamp, created_at=created_at, link=link,
            summary=summary,
        )
        return self._add_composed("followUps", record, attention)

    def attention(
        self, *, event_kind: str, issue_id: str, source_id: str,
        source_timestamp: str, created_at: str, link: str, summary: str,
        actionable: bool = True, transient_within_budget: bool = False,
    ) -> dict[str, Any] | None:
        allowed = {
            "needs-human", "external-blocker", "multiple-wip",
            "publication-refusal", "worker-failure", "preflight-failure",
        }
        if event_kind not in allowed or not actionable or transient_within_budget:
            return None
        record = self._attention_record(
            event_kind=event_kind, issue_id=issue_id, source_id=source_id,
            source_timestamp=source_timestamp, created_at=created_at, link=link,
            summary=summary,
        )
        return self._add_once("attentionEvents", record)

    def begin_notification(self, event_id: str, now: str) -> dict[str, Any]:
        def begin(state: dict[str, Any]) -> dict[str, Any]:
            event = next((item for item in state["attentionEvents"] if item["id"] == event_id), None)
            if event is None:
                raise ControlPlaneRecordError("Notification source event is absent")
            record_id = stable_id("notification", event_id)
            existing = next((item for item in state["notifications"] if item["id"] == record_id), None)
            if existing is not None:
                return {"record": existing, "acquired": False}
            record = self._record(
                kind="ntfy", record_id=record_id, issue_id=event["issueId"],
                created_at=now, source_timestamp=event["sourceTimestamp"], status="pending",
                link=event["link"], summary=event["summary"],
                data={
                    "eventId": event_id,
                    "attemptId": stable_id("attempt", event_id),
                    "attemptState": "in-flight",
                    "completedAt": None,
                    "outcome": None,
                },
            )
            state["notifications"].append(record)
            return {"record": record, "acquired": True}

        _, result = self.store.mutate(begin)
        return result

    def finish_notification(
        self, notification_id: str, outcome: Mapping[str, Any], now: str
    ) -> dict[str, Any]:
        def finish(state: dict[str, Any]) -> dict[str, Any]:
            record = next((item for item in state["notifications"] if item["id"] == notification_id), None)
            if record is None or record["data"]["attemptState"] != "in-flight":
                raise ControlPlaneRecordError("Notification attempt is absent or terminal")
            record["status"] = "delivered" if outcome.get("status") == "delivered" else "failed"
            record["data"]["attemptState"] = "terminal"
            record["data"]["completedAt"] = now
            record["data"]["outcome"] = _redact(dict(outcome))
            return record

        _, record = self.store.mutate(finish)
        return record

    def require_notification_recovery(self, notification_id: str) -> dict[str, Any]:
        """Persist attended recovery without authorizing another notification send."""

        def require(state: dict[str, Any]) -> dict[str, Any]:
            record = next(
                (item for item in state["notifications"] if item["id"] == notification_id),
                None,
            )
            if record is None:
                raise ControlPlaneRecordError("Notification attempt is absent")
            if record["data"]["attemptState"] != "terminal":
                record["data"]["attemptState"] = "recovery-required"
            return record

        _, record = self.store.mutate(require)
        return record

    def status(self) -> dict[str, Any]:
        state = self.store.load()
        def pending(collection: str) -> list[dict[str, Any]]:
            return [
                {"id": item["id"], "issueId": item["issueId"], "kind": item["kind"], "status": item["status"], "link": item["link"], "summary": item["summary"]}
                for item in state[collection]
                if item["status"] in {"pending", "failed"}
            ]
        return {
            "schemaVersion": "1.0",
            "revision": state["revision"],
            "pendingDecisions": pending("decisions"),
            "pendingPublicationRequests": pending("publicationRequests"),
            "pendingFollowUps": pending("followUps"),
            "attention": pending("attentionEvents"),
            "notificationFailures": pending("notifications"),
        }
