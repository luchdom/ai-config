"""Narrow, injected and readback-reconciled publication provider boundary."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, Protocol

from .publication_records import PublicationRecordError, exact_sha, sha256_json


class PublicationProvider(Protocol):
    """The complete provider capability surface; hosted-check APIs are absent."""

    def read_remote_ref(self, branch: str) -> Mapping[str, Any] | None: ...
    def push_ref(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def read_pull_request(self, branch: str, base_ref: str) -> Mapping[str, Any] | None: ...
    def create_or_reuse_pull_request(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def read_merge(self, pull_request_id: str) -> Mapping[str, Any]: ...
    def squash_merge(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


class ProviderReconciliationError(PublicationRecordError):
    pass


class ProviderOperationRefused(ProviderReconciliationError):
    """A provider mutation was not applied and has authoritative readback."""

    def __init__(self, message: str, *, response: Mapping[str, Any], readback: Mapping[str, Any]):
        super().__init__(message)
        self.response = copy.deepcopy(dict(response))
        self.readback = copy.deepcopy(dict(readback))


_RESPONSE_FIELDS = {"statusCode", "code", "retryAfterSeconds", "ambiguous"}
_READBACK_FIELDS = {
    "applied", "ambiguous", "merged", "mergeSha", "headSha", "baseRef",
    "mergeability",
}
_CODES = {
    "unavailable", "timeout", "mergeability-pending", "mergeability-unknown",
    "permission-denied", "required-check", "branch-protection", "ruleset",
    "merge-queue", "policy",
}


def _closed_fields(value: Mapping[str, Any] | None, allowed: set[str]) -> dict[str, Any]:
    """Return only fields whose values satisfy their exact durable type."""

    safe: dict[str, Any] = {}
    for key, item in dict(value or {}).items():
        if key not in allowed:
            continue
        if key == "statusCode" and type(item) is int and 100 <= item <= 599:
            safe[key] = item
        elif key == "retryAfterSeconds" and type(item) is int and 0 <= item <= 1800:
            safe[key] = item
        elif key in {"ambiguous", "applied", "merged", "mergeability"} and type(item) is bool:
            safe[key] = item
        elif key in {"code", "headSha", "mergeSha", "baseRef"} and isinstance(item, str):
            safe[key] = item
    return safe


def normalized_refusal(
    response: Mapping[str, Any] | None, readback: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    classification = _closed_fields(response, _RESPONSE_FIELDS)
    code = classification.get("code")
    if code is not None:
        classification["code"] = code if code in _CODES else "unclassified"
    reconciliation = _closed_fields(readback, _READBACK_FIELDS)
    for name in ("headSha", "mergeSha"):
        value = reconciliation.get(name)
        if value is not None:
            try:
                exact_sha(value, name)
            except PublicationRecordError:
                reconciliation.pop(name, None)
    if reconciliation.get("baseRef") != "main":
        reconciliation.pop("baseRef", None)
    return {"classification": classification, "reconciliation": reconciliation}


def _redacted_evidence(response: Mapping[str, Any] | None) -> str:
    value = dict(response or {})
    if set(value).issubset({"response", "readback"}):
        return sha256_json(normalized_refusal(value.get("response"), value.get("readback")))
    return sha256_json(_closed_fields(value, _RESPONSE_FIELDS | _READBACK_FIELDS))


class PublicationProviderCoordinator:
    """Reconcile before and after each idempotent provider mutation."""

    __slots__ = ("_provider",)

    def __init__(self, provider: PublicationProvider) -> None:
        required = {
            "read_remote_ref", "push_ref", "read_pull_request",
            "create_or_reuse_pull_request", "read_merge", "squash_merge",
        }
        if any(not callable(getattr(provider, name, None)) for name in required):
            raise ProviderReconciliationError("provider lacks the closed publication surface")
        forbidden = {
            "list_checks", "get_checks", "wait_for_checks", "update_settings",
            "update_branch_protection", "update_ruleset", "update_permissions",
            "update_merge_queue", "admin_merge", "bypass_merge",
        }
        if any(callable(getattr(provider, name, None)) for name in forbidden):
            raise ProviderReconciliationError("provider exposes a forbidden capability")
        self._provider = provider

    def push(self, *, operation_id: str, branch: str, head_sha: str) -> dict[str, Any]:
        exact_sha(head_sha)
        before = self._provider.read_remote_ref(branch)
        if before and before.get("headSha") == head_sha:
            return {"status": "reconciled", "applied": True, "evidenceRef": _redacted_evidence(before)}
        request = {"operationId": operation_id, "idempotencyKey": operation_id, "branch": branch, "headSha": head_sha}
        response = self._provider.push_ref(copy.deepcopy(request))
        after = self._provider.read_remote_ref(branch)
        if not after or after.get("headSha") != head_sha:
            raise ProviderOperationRefused(
                "push was not applied after readback", response=response,
                readback=dict(after or {}, applied=False),
            )
        return {"status": "succeeded", "applied": True, "evidenceRef": _redacted_evidence({"response": response, "readback": after})}

    def pull_request(self, *, operation_id: str, branch: str, base_ref: str, head_sha: str) -> dict[str, Any]:
        if base_ref != "main":
            raise ProviderReconciliationError("primary pull request must target main")
        exact_sha(head_sha)
        before = self._provider.read_pull_request(branch, base_ref)
        if before is not None:
            self._require_pr(before, base_ref, head_sha)
            return {"status": "reconciled", "pullRequest": copy.deepcopy(dict(before)), "evidenceRef": _redacted_evidence(before)}
        request = {"operationId": operation_id, "idempotencyKey": operation_id, "branch": branch, "baseRef": base_ref, "headSha": head_sha}
        response = self._provider.create_or_reuse_pull_request(copy.deepcopy(request))
        after = self._provider.read_pull_request(branch, base_ref)
        if after is None:
            raise ProviderOperationRefused(
                "pull request was not applied after readback", response=response,
                readback={"applied": False},
            )
        self._require_pr(after, base_ref, head_sha)
        return {"status": "succeeded", "pullRequest": copy.deepcopy(dict(after)), "evidenceRef": _redacted_evidence({"response": response, "readback": after})}

    def merge(self, *, operation_id: str, pull_request_id: str, base_ref: str, head_sha: str) -> dict[str, Any]:
        if base_ref != "main":
            raise ProviderReconciliationError("squash merge must target main")
        exact_sha(head_sha)
        before = self._provider.read_merge(pull_request_id)
        if before.get("merged") is True:
            merge_sha = exact_sha(before.get("mergeSha"), "mergeSha")
            return {"status": "reconciled", "mergeSha": merge_sha, "evidenceRef": _redacted_evidence(before)}
        request = {"operationId": operation_id, "idempotencyKey": operation_id, "pullRequestId": pull_request_id, "baseRef": base_ref, "headSha": head_sha, "method": "squash", "admin": False}
        response = self._provider.squash_merge(copy.deepcopy(request))
        after = self._provider.read_merge(pull_request_id)
        if not response.get("mergeSha") or after.get("merged") is not True:
            raise ProviderOperationRefused(
                "squash merge was not applied after readback", response=response,
                readback=dict(after, applied=False),
            )
        returned_sha = exact_sha(response.get("mergeSha"), "returned mergeSha")
        if after.get("merged") is not True or after.get("mergeSha") != returned_sha:
            raise ProviderReconciliationError("returned merge identity does not match provider readback")
        return {"status": "succeeded", "mergeSha": returned_sha, "evidenceRef": _redacted_evidence({"response": response, "readback": after})}

    def authority_readback(
        self, *, issue_id: str, branch: str, base_ref: str, head_sha: str,
    ) -> dict[str, Any]:
        """Read the closed issue/PR authority surface; callers cannot inject it."""

        reader = getattr(self._provider, "read_publication_authority", None)
        if not callable(reader):
            raise ProviderReconciliationError("provider lacks publication-authority readback")
        observed = reader(issue_id, branch, base_ref)
        required = {"issueId", "labels", "pullRequestId", "baseRef", "baseSha", "headSha", "mergeability"}
        if not isinstance(observed, Mapping) or set(observed) != required:
            raise ProviderReconciliationError("publication-authority readback is incomplete")
        if observed["issueId"] != issue_id or observed["baseRef"] != base_ref:
            raise ProviderReconciliationError("publication-authority readback identity drifted")
        labels = observed["labels"]
        if not isinstance(labels, list) or any(not isinstance(item, str) for item in labels):
            raise ProviderReconciliationError("publication labels readback is invalid")
        return {
            **copy.deepcopy(dict(observed)),
            "evidenceRef": _redacted_evidence(observed),
            "expectedHeadSha": exact_sha(head_sha),
        }

    def reconcile_application(
        self, *, provider_operation: str, branch: str, base_ref: str,
        head_sha: str, pull_request_id: str | None,
    ) -> dict[str, Any]:
        """Independently determine whether an interrupted mutation was applied."""

        if provider_operation == "push":
            observed = self._provider.read_remote_ref(branch)
            applied = bool(observed) and observed.get("headSha") == head_sha
            return {"applied": applied, "headSha": head_sha if applied else None,
                "evidenceRef": _redacted_evidence(observed)}
        if provider_operation == "pull-request":
            observed = self._provider.read_pull_request(branch, base_ref)
            applied = bool(observed) and observed.get("headSha") == head_sha
            return {"applied": applied,
                "pullRequest": copy.deepcopy(dict(observed)) if applied else None,
                "evidenceRef": _redacted_evidence(observed)}
        if provider_operation == "squash-merge" and pull_request_id:
            observed = self._provider.read_merge(pull_request_id)
            applied = observed.get("merged") is True
            merge_sha = exact_sha(observed.get("mergeSha"), "mergeSha") if applied else None
            return {"applied": applied, "ambiguous": False, "mergeSha": merge_sha,
                "evidenceRef": _redacted_evidence(observed)}
        return {"applied": False, "ambiguous": True}

    @staticmethod
    def _require_pr(value: Mapping[str, Any], base_ref: str, head_sha: str) -> None:
        if value.get("baseRef") != base_ref or value.get("headSha") != head_sha:
            raise ProviderReconciliationError("provider pull-request identity drifted")
        if not value.get("id"):
            raise ProviderReconciliationError("provider pull request lacks an identity")
