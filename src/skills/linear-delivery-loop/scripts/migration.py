"""Mutation-free migration reporting for fully observed Linear issues."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from .contracts import validate_contract
from .linear_transport import validate_completed_observation
from .selection import rejection_reasons


def build_migration_report(
    completed_observation: Mapping[str, Any],
    *,
    repository_key: str,
    generated_at: str,
) -> dict[str, Any]:
    observed = validate_completed_observation(completed_observation)
    records: list[dict[str, Any]] = []
    for issue in observed["nodes"]:
        issue_id = str(issue["identifier"])
        reasons = rejection_reasons(issue, repository_key)
        current_labels = sorted(
            str(item.get("name") if isinstance(item, Mapping) else item)
            for item in issue.get("labels", [])
        )
        proposed_labels = list(current_labels)
        proposed_state: str | None = None
        if issue.get("goalComplete") is not True:
            proposed_state = "Backlog"
            if "needs-refinement" not in proposed_labels:
                proposed_labels.append("needs-refinement")
        elif issue.get("externalDependency") is True:
            proposed_state = "Backlog"
            if "external-integration" not in proposed_labels:
                proposed_labels.append("external-integration")
        elif not reasons:
            proposed_state = "Todo"
            if "autonomous" not in proposed_labels:
                proposed_labels.append("autonomous")
        records.append(
            {
                "issueId": issue_id,
                "eligible": not reasons,
                "rejectionReasons": sorted(set(reasons)),
                "currentState": str(issue.get("state", "unknown")),
                "currentLabels": current_labels,
                "proposedState": proposed_state,
                "proposedLabels": sorted(set(proposed_labels)),
            }
        )
    records.sort(key=lambda item: int(item["issueId"].rsplit("-", 1)[1]))
    report = {
        "schemaVersion": "1.0",
        "generatedAt": generated_at,
        "mutationFree": True,
        "issues": records,
    }
    return validate_contract("migration-report", copy.deepcopy(report))
