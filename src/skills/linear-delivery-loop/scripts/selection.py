"""Pure WIP/eligibility rules and local-before-remote claim coordination."""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from .linear_transport import LinearAmbiguousWrite


ACTIVE_STATES = frozenset({"In Progress", "In Review"})
STOP_LABELS = frozenset({"stop", "external-integration", "needs-refinement", "needs-human"})
_BROAD_WORDS = re.compile(r"\b(epic|program|all repositories|platform-wide)\b", re.IGNORECASE)


class SelectionError(RuntimeError):
    pass


class ClaimRecoveryRequired(SelectionError):
    pass


class ClaimRolledBack(SelectionError):
    pass


def _labels(issue: Mapping[str, Any]) -> set[str]:
    raw = issue.get("labels", [])
    return {str(item.get("name") if isinstance(item, Mapping) else item) for item in raw}


def rejection_reasons(issue: Mapping[str, Any], repository_key: str) -> list[str]:
    reasons: list[str] = []
    labels = _labels(issue)
    if issue.get("state") != "Todo":
        reasons.append("not-todo")
    if "autonomous" not in labels:
        reasons.append("missing-autonomous-label")
    reasons.extend(f"blocked-label:{label}" for label in sorted(labels & STOP_LABELS))
    if issue.get("parentId"):
        reasons.append("has-parent")
    if issue.get("repositoryKey") != repository_key:
        reasons.append("cross-repository")
    if issue.get("scope") != "code-leaf":
        reasons.append("not-achievable-code-leaf")
    if issue.get("goalComplete") is not True:
        reasons.append("incomplete-goal")
    if issue.get("externalDependency") is True:
        reasons.append("external-dependency")
    if _BROAD_WORDS.search(str(issue.get("title", ""))):
        reasons.append("broad-scope")
    return reasons


def _number(issue: Mapping[str, Any]) -> int:
    identifier = str(issue.get("identifier", ""))
    try:
        return int(identifier.rsplit("-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise SelectionError("Issue identifier lacks a numeric suffix") from exc


def select_candidate(issues: Iterable[Mapping[str, Any]], repository_key: str) -> dict[str, Any] | None:
    eligible = [copy.deepcopy(dict(issue)) for issue in issues if not rejection_reasons(issue, repository_key)]
    if not eligible:
        return None
    eligible.sort(
        key=lambda issue: (
            int(issue.get("priority") or 999),
            str(issue.get("createdAt", "")),
            _number(issue),
        )
    )
    return eligible[0]


def reconcile_wip(
    issues: Iterable[Mapping[str, Any]],
    *,
    autonomous_issue_id: str | None,
    reservation_issue_ids: set[str],
) -> dict[str, Any]:
    active = [copy.deepcopy(dict(issue)) for issue in issues if issue.get("state") in ACTIVE_STATES]
    if len(active) > 1:
        return {
            "action": "fail-closed",
            "reason": "multiple-active-issues",
            "attention": True,
            "issueIds": sorted(str(issue["identifier"]) for issue in active),
        }
    if not active:
        return {"action": "select", "attention": False}
    issue_id = str(active[0]["identifier"])
    if issue_id == autonomous_issue_id and issue_id in reservation_issue_ids:
        return {"action": "resume", "attention": False, "issueId": issue_id}
    return {"action": "quiet-exit", "reason": "manual-or-semi-wip", "attention": False, "issueId": issue_id}


def claim_selected(
    selected: Mapping[str, Any],
    *,
    operation_id: str,
    repository_key: str,
    reread: Callable[[str], Mapping[str, Any]],
    authority: Any,
    claim: Callable[[Mapping[str, Any], str], Any],
    readback: Callable[[str], Mapping[str, Any]],
) -> dict[str, Any]:
    """Prepare repository authority first, claim second, then prove readback."""

    issue_id = str(selected["identifier"])
    current = dict(reread(issue_id))
    if rejection_reasons(current, repository_key):
        raise SelectionError("Selected issue changed eligibility before claim")
    prepared: Mapping[str, Any] | None = None
    claim_attempted = False
    try:
        prepared = authority.prepare(operation_id=operation_id, issue=current)
        if not isinstance(prepared, Mapping) or prepared.get("status") != "prepared":
            raise SelectionError("Repository reservation/worktree preparation was not proven")
        claim_attempted = True
        try:
            claim(current, operation_id)
        except LinearAmbiguousWrite:
            observed = dict(readback(issue_id))
            if observed.get("state") == "In Progress":
                authority.commit(operation_id=operation_id)
                return {"status": "reconciled", "issueId": issue_id, "operationId": operation_id}
            raise
        observed = dict(readback(issue_id))
        if observed.get("state") != "In Progress":
            raise LinearAmbiguousWrite("Claim readback is not authoritative")
        authority.commit(operation_id=operation_id)
        return {"status": "claimed", "issueId": issue_id, "operationId": operation_id}
    except Exception as exc:
        if prepared is None:
            raise
        if claim_attempted:
            try:
                observed = dict(readback(issue_id))
            except Exception:
                authority.protect(operation_id=operation_id, reason="provider-readback-ambiguous")
                raise ClaimRecoveryRequired("Claim outcome is protected for recovery") from exc
            if observed.get("state") == "In Progress":
                authority.protect(operation_id=operation_id, reason="remote-claim-present")
                raise ClaimRecoveryRequired("Remote WIP is protected for recovery") from exc
        if authority.rollback_if_safe(operation_id=operation_id):
            raise ClaimRolledBack("Claim failed; proven-safe local preparation was rolled back") from exc
        authority.protect(operation_id=operation_id, reason="rollback-not-proven-safe")
        raise ClaimRecoveryRequired("Prepared work is protected for recovery") from exc


def reconcile_manual_selection(
    *,
    issue_id: str,
    matching_issue_id: str | None,
    reservation_live: bool,
    remove_autonomous_label: Callable[[str], Any],
) -> bool:
    if matching_issue_id != issue_id or not reservation_live:
        raise SelectionError("Manual selection conflicts with autonomous authority")
    remove_autonomous_label(issue_id)
    return True
