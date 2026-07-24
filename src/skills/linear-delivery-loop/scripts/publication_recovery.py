"""Provider-refusal, attended retry, merge, and bounded same-issue repair policy."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from .publication_records import (
    PublicationRecordError, exact_sha, retry_delay_minutes, validate_preserved_state,
)

TRANSIENT = {"rate-limit", "provider-unavailable", "temporary-mergeability"}
STABLE = {
    "permission", "required-check", "branch-protection", "ruleset", "merge-queue",
    "policy", "ambiguous", "unclassified",
}
REQUIRED_ATTENDED_REREADS = {
    "issue", "authorization", "reservation", "worktree", "journal", "branch",
    "pullRequest", "head", "base", "mergeability", "attestations", "provider",
}
REPAIR_GATES = {
    "pre-staging-aggregate", "exact-head-aggregate", "review", "qa", "docs",
    "evidence-convergence", "merge-readback", "exact-merge-aggregate",
}
REPAIR_PREMERGE_GATES = REPAIR_GATES - {"merge-readback", "exact-merge-aggregate"}


class PublicationRecoveryError(PublicationRecordError):
    pass


def classify_refusal(response: Mapping[str, Any], readback: Mapping[str, Any]) -> str:
    """Classify only redacted operation response plus authoritative readback."""

    if readback.get("applied") is True:
        return "applied"
    status = response.get("statusCode")
    code = str(response.get("code", "")).casefold()
    if status == 429:
        return "rate-limit"
    if isinstance(status, int) and 500 <= status <= 599 or code in {"unavailable", "timeout"}:
        return "provider-unavailable"
    if code in {"mergeability-pending", "mergeability-unknown"}:
        return "temporary-mergeability"
    mapping = {
        "permission-denied": "permission", "required-check": "required-check",
        "branch-protection": "branch-protection", "ruleset": "ruleset",
        "merge-queue": "merge-queue", "policy": "policy",
    }
    if code in mapping:
        return mapping[code]
    if readback.get("ambiguous") or response.get("ambiguous"):
        return "ambiguous"
    return "unclassified"


class PublicationRecovery:
    """Pure policy coordinator around injected durable control-plane effects."""

    __slots__ = ("requests", "release_lease", "set_labels", "set_issue_state", "notify")

    def __init__(
        self,
        *,
        requests: Any,
        release_lease: Callable[[], None],
        set_labels: Callable[[set[str]], None],
        set_issue_state: Callable[[str], None],
        notify: Callable[[Mapping[str, Any]], None],
    ) -> None:
        self.requests = requests
        self.release_lease = release_lease
        self.set_labels = set_labels
        self.set_issue_state = set_issue_state
        self.notify = notify

    def refusal(
        self,
        *,
        publication: Mapping[str, Any],
        response: Mapping[str, Any],
        readback: Mapping[str, Any],
        now: str,
        request_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        result = copy.deepcopy(dict(publication))
        validate_preserved_state(result["preservedState"])
        kind = classify_refusal(response, readback)
        if kind == "applied":
            result.update({"status": "succeeded", "refusalKind": None, "nextRetryAt": None})
            return result
        result["refusalKind"] = kind
        if kind in TRANSIENT and result["retryCount"] < 3:
            result["retryCount"] += 1
            minutes = retry_delay_minutes(result["retryCount"], response.get("retryAfterSeconds"))
            instant = datetime.fromisoformat(now.replace("Z", "+00:00"))
            result.update({"status": "retry-wait", "nextRetryAt": (instant + timedelta(minutes=minutes)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")})
            self.release_lease()
            return result
        result.update({"status": "paused", "nextRetryAt": None})
        self.set_issue_state(result["preservedState"]["issueState"])
        self.set_labels({"autonomous", "blocked", "needs-human"})
        request_method = getattr(self.requests, "publication_refusal", None)
        if not callable(request_method):
            raise PublicationRecoveryError("durable publication-request boundary is unavailable")
        request = request_method(**dict(request_context))
        self.notify({"kind": "publication-refusal", "requestId": request["id"], "operationId": result["operationId"], "headSha": result["headSha"]})
        self.release_lease()
        return result

    def attended_retry(
        self,
        *,
        publication: Mapping[str, Any],
        consume_reply: Callable[[], Mapping[str, Any] | None],
        rereads: Mapping[str, Any],
        persist_consumption: Callable[[Mapping[str, Any]], None],
        attempt: Callable[[], Mapping[str, Any]],
        authorize_attempt: Callable[[], None] = lambda: None,
        reconcile_application: Callable[[], Mapping[str, Any]] = lambda: {"applied": False, "ambiguous": True},
        reopen_request: Callable[[str], Any] = lambda _reply_id: None,
    ) -> dict[str, Any]:
        result = copy.deepcopy(dict(publication))
        if result.get("status") != "paused":
            raise PublicationRecoveryError("publication is not paused for attended retry")
        if set(rereads) != REQUIRED_ATTENDED_REREADS:
            raise PublicationRecoveryError("attended retry did not perform every independent reread")
        if any(value is not True for value in rereads.values()):
            unresolved = sorted(name for name, value in rereads.items() if value is not True)
            raise PublicationRecoveryError(
                f"attended retry reconciliation is unresolved: {', '.join(unresolved)}"
            )
        # SAAS-47 atomically changes the durable request from pending to
        # authorized and records the unique reply identity. A replay returns
        # None, so mutation authority cannot be distributed twice.
        reply = consume_reply()
        if reply is None or reply.get("status") != "authorized":
            raise PublicationRecoveryError("publication reply is absent, stale, or already consumed")
        if reply.get("operationId") != result["operationId"] or reply.get("headSha") != result["headSha"]:
            raise PublicationRecoveryError("attended retry reply is stale")
        reply_id = reply.get("consumedReplyId")
        if not isinstance(reply_id, str) or not reply_id:
            raise PublicationRecoveryError("attended retry lacks durable reply consumption identity")
        result["consumedReplyId"] = reply_id
        result["status"] = "attempting"
        # Consume the exact one-shot mutation grant after durable reply
        # consumption but before publication CAS changes its state binding.
        authorize_attempt()
        # Persist consumption before attempting. A crash here leaves a
        # consumed, reconcile-only operation rather than reusable authority.
        persist_consumption(copy.deepcopy(result))
        self.set_labels({"autonomous"})
        try:
            outcome = dict(attempt())
        except Exception:
            observed = dict(reconcile_application())
            if observed.get("applied") is True:
                pull_request = observed.get("pullRequest")
                merge_sha = observed.get("mergeSha")
                if isinstance(pull_request, Mapping) and pull_request.get("id"):
                    result["status"] = "pr-open"
                    result["pullRequest"] = copy.deepcopy(dict(pull_request))
                elif isinstance(merge_sha, str):
                    result["status"] = "merged"
                    result["mergeSha"] = merge_sha
                    if isinstance(observed.get("mergeReadback"), Mapping):
                        result["attestations"]["merge-readback"] = copy.deepcopy(dict(observed["mergeReadback"]))
                elif isinstance(observed.get("headSha"), str):
                    result["status"] = "pushed"
                else:
                    raise PublicationRecoveryError("applied provider reconciliation lacks an exact phase identity")
                result.update({"refusalKind": None, "nextRetryAt": None,
                    "activeProviderOperation": None,
                    "providerEvidenceRef": observed.get("evidenceRef")})
            elif observed.get("applied") is False and observed.get("ambiguous") is not True:
                # The provider proved non-application. Preserve the stable
                # refusal classification and consumed reply identity while
                # reopening the same request for a strictly newer reply.
                result.update({"status": "paused", "nextRetryAt": None})
            else:
                result.update({"status": "paused", "refusalKind": "ambiguous", "nextRetryAt": None})
            persist_consumption(copy.deepcopy(result))
            if observed.get("applied") is False and observed.get("ambiguous") is not True:
                reopened = reopen_request(reply_id)
                if not isinstance(reopened, Mapping) or reopened.get("status") != "pending":
                    raise PublicationRecoveryError("proven non-application request was not safely reopened")
            self.set_labels({"autonomous"} if observed.get("applied") is True else {"autonomous", "blocked", "needs-human"})
            if observed.get("applied") is True:
                self.set_issue_state(result["preservedState"]["issueState"])
            raise
        if outcome.get("applied") is not True:
            result["status"] = "paused"
            self.set_labels({"autonomous", "blocked", "needs-human"})
            return result
        authoritative = outcome.get("publication")
        if not isinstance(authoritative, Mapping):
            raise PublicationRecoveryError("attended success lacks authoritative provider phase state")
        result = copy.deepcopy(dict(authoritative))
        if result.get("consumedReplyId") != reply_id:
            raise PublicationRecoveryError("attended success lost its consumed reply identity")
        self.set_labels({"autonomous"})
        self.set_issue_state(result["preservedState"]["issueState"])
        return result

    def repair_exhausted(
        self, *, publication: Mapping[str, Any], request_context: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Pause the same issue after repair 3 and notify through existing seams."""

        result = copy.deepcopy(dict(publication))
        if result.get("repairAttempt") != 3:
            raise PublicationRecoveryError("repair exhaustion requires exactly three attempts")
        validate_preserved_state(result["preservedState"])
        result.update({"status": "paused", "refusalKind": "policy", "nextRetryAt": None})
        self.set_issue_state("Backlog")
        self.set_labels({"autonomous", "needs-human"})
        request = self.requests.publication_refusal(**dict(request_context))
        self.notify({"kind": "repair-exhausted", "requestId": request["id"], "operationId": result["operationId"], "headSha": result["headSha"]})
        self.release_lease()
        return result


class MergeRepairPolicy:
    """Require exact-head merge evidence and complete gates for up to three repairs."""

    @staticmethod
    def premerge(*, head_sha: str, base_ref: str, authority: Mapping[str, bool], attestations: Mapping[str, Mapping[str, Any]]) -> None:
        exact_sha(head_sha)
        if base_ref != "main" or not authority or any(value is not True for value in authority.values()):
            raise PublicationRecoveryError("pre-merge authority or base is unresolved")
        for name in ("exact-head-aggregate", "review", "qa", "docs"):
            if attestations.get(name, {}).get("exactSha") != head_sha:
                raise PublicationRecoveryError(f"pre-merge {name} evidence is missing or stale")

    @staticmethod
    def base_drift(*, observed_base_sha: str, attested_base_sha: str, merge_origin_main: Callable[[], str]) -> dict[str, Any]:
        exact_sha(observed_base_sha, "observed base SHA")
        exact_sha(attested_base_sha, "attested base SHA")
        if observed_base_sha == attested_base_sha:
            return {"drifted": False, "invalidated": []}
        new_head = exact_sha(merge_origin_main(), "base-drift merge head")
        return {"drifted": True, "headSha": new_head, "invalidated": ["aggregate", "review", "qa", "docs", "evidence"]}

    @staticmethod
    def require_repair_pipeline(*, repair_head: str, gates: Mapping[str, Mapping[str, Any]], phase: str = "complete") -> None:
        exact_sha(repair_head, "repair head")
        required = REPAIR_PREMERGE_GATES if phase == "pre-merge" else REPAIR_GATES
        if phase not in {"pre-merge", "complete"} or set(gates) != required:
            raise PublicationRecoveryError("repair did not re-enter the complete publication pipeline")
        for name, record in gates.items():
            bound = record.get("exactSha") if name not in {"merge-readback", "exact-merge-aggregate"} else record.get("repairHeadSha")
            if bound != repair_head or record.get("passed") is not True:
                raise PublicationRecoveryError(f"repair gate {name} is missing, failed, or wrong-head")

    @staticmethod
    def next_repair(*, issue_id: str, previous_attempt: int, current_main_sha: str) -> dict[str, Any]:
        exact_sha(current_main_sha, "current main SHA")
        attempt = previous_attempt + 1
        if attempt > 3:
            return {"status": "exhausted", "issueState": "Backlog", "labels": ["autonomous", "needs-human"], "notify": True}
        return {"status": "repairing", "issueState": "In Review", "attempt": attempt, "branch": f"codex/{issue_id}-repair-{attempt}", "baseSha": current_main_sha}
