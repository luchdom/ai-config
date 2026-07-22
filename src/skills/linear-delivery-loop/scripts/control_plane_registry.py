"""Immutable engine-owned adapters for the fixture-first Linear control plane.

The public control-plane facade receives only an opaque registry reference. Raw
provider, journal, repository-authority, and observation callbacks are sealed
inside exact engine adapter types during composition and cannot be rebound.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any


class EngineRegistryError(RuntimeError):
    pass


class _Frozen:
    __slots__ = ("_sealed",)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError(f"{type(self).__name__} is immutable")
        object.__setattr__(self, name, value)

    def _freeze(self) -> None:
        object.__setattr__(self, "_sealed", True)


DEFAULT_ISSUE_OBSERVATION_QUERY = """query ControlPlaneIssues($after: String) {
  issues(after: $after) {
    nodes {
      id identifier title priority createdAt
      repositoryKey scope goalComplete externalDependency
      state { name }
      labels { nodes { name } }
      parent { id }
      project { id name }
    }
    pageInfo { hasNextPage endCursor }
  }
}"""


class _EngineLinearClaimAdapter(_Frozen):
    __slots__ = (
        "transport", "adapter_id", "journal_id", "_reread", "_claim", "_readback"
    )

    def __init__(
        self, *, transport: Any, adapter_id: str, journal_id: str,
        reread: Callable[[str, str], Mapping[str, Any]],
        claim: Callable[[Mapping[str, Any], str], Any],
        readback: Callable[[str, str], Mapping[str, Any]],
    ) -> None:
        object.__setattr__(self, "_sealed", False)
        if not adapter_id or not journal_id or not all(callable(item) for item in (reread, claim, readback)):
            raise EngineRegistryError("Linear claim adapter is incomplete")
        self.transport = transport
        self.adapter_id = adapter_id
        self.journal_id = journal_id
        self._reread = reread
        self._claim = claim
        self._readback = readback
        self._freeze()

    def reread(self, issue_id: str, operation_id: str) -> Mapping[str, Any]:
        return self._reread(issue_id, operation_id)

    def claim(self, issue: Mapping[str, Any], operation_id: str) -> Any:
        return self._claim(issue, operation_id)

    def readback(self, issue_id: str, operation_id: str) -> Mapping[str, Any]:
        return self._readback(issue_id, operation_id)


class _EngineRepositoryAuthorityAdapter(_Frozen):
    __slots__ = ("authority_id", "_operations")

    _NAMES = (
        "current_execution_lease", "authorize_recovery", "prepare", "commit",
        "rollback_if_safe", "protect", "recover",
    )

    def __init__(self, *, authority_id: str, operations: Mapping[str, Callable[..., Any]]) -> None:
        object.__setattr__(self, "_sealed", False)
        if not authority_id or set(operations) != set(self._NAMES) or any(
            not callable(operations[name]) for name in self._NAMES
        ):
            raise EngineRegistryError("Repository authority adapter is incomplete")
        self.authority_id = authority_id
        self._operations = MappingProxyType(dict(operations))
        self._freeze()

    def __getattr__(self, name: str) -> Any:
        if name in self._NAMES:
            return self._operations[name]
        raise AttributeError(name)


class _EngineLinearObservationAdapter(_Frozen):
    __slots__ = (
        "transport", "adapter_id", "_api_key", "_local_observer", "_query", "_variables"
    )

    def __init__(
        self, *, transport: Any, adapter_id: str,
        api_key: Callable[[], str],
        local_observer: Callable[[], Mapping[str, Any]],
        query: str = DEFAULT_ISSUE_OBSERVATION_QUERY,
        variables: Mapping[str, Any] | None = None,
    ) -> None:
        object.__setattr__(self, "_sealed", False)
        if not adapter_id or not callable(api_key) or not callable(local_observer):
            raise EngineRegistryError("Linear observation adapter is incomplete")
        self.transport = transport
        self.adapter_id = adapter_id
        self._api_key = api_key
        self._local_observer = local_observer
        self._query = query
        self._variables = MappingProxyType(copy.deepcopy(dict(variables or {})))
        self._freeze()

    def observe_issues(self) -> dict[str, Any]:
        completed = self.transport.paginate_verified(
            self._query, dict(self._variables), api_key=self._api_key(), connection="issues"
        )
        return {
            "nodes": [_normalize_issue_node(node) for node in completed["nodes"]],
            "pagination": copy.deepcopy(completed["pagination"]),
        }

    def observe_selection(self) -> dict[str, Any]:
        completed = self.observe_issues()
        local = self._local_observer()
        exact = {"reservations", "issueWorktrees", "recovery", "autonomousIssueId"}
        if not isinstance(local, Mapping) or set(local) != exact:
            raise EngineRegistryError("Supervisor selection observation is incomplete")
        return {
            "issues": completed["nodes"],
            "pagination": completed["pagination"],
            **copy.deepcopy(dict(local)),
        }


class _Entry:
    __slots__ = ("claim", "authority", "observation", "_sealed")

    def __init__(
        self, claim: _EngineLinearClaimAdapter,
        authority: _EngineRepositoryAuthorityAdapter,
        observation: _EngineLinearObservationAdapter,
    ) -> None:
        object.__setattr__(self, "claim", claim)
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "observation", observation)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise AttributeError("Engine registry entry is immutable")


def _normalize_issue_node(value: Any) -> dict[str, Any]:
    """Close and normalize the provider node before any policy consumes it."""

    if not isinstance(value, Mapping):
        raise EngineRegistryError("Linear issue observation node is malformed")
    required = {
        "id", "identifier", "title", "priority", "createdAt", "repositoryKey",
        "scope", "goalComplete", "externalDependency", "state", "labels",
        "parent", "project",
    }
    if not required.issubset(value):
        raise EngineRegistryError("Linear issue observation node is incomplete")
    state = value["state"]
    labels = value["labels"]
    parent = value["parent"]
    project = value["project"]
    if (
        not isinstance(state, Mapping) or set(state) != {"name"}
        or not isinstance(state["name"], str) or not state["name"]
        or not isinstance(labels, Mapping) or set(labels) != {"nodes"}
        or not isinstance(labels["nodes"], list)
        or any(not isinstance(item, Mapping) or set(item) != {"name"}
               or not isinstance(item["name"], str) or not item["name"]
               for item in labels["nodes"])
        or (parent is not None and (
            not isinstance(parent, Mapping) or set(parent) != {"id"}
            or not isinstance(parent["id"], str) or not parent["id"]
        ))
        or not isinstance(project, Mapping) or set(project) != {"id", "name"}
        or any(not isinstance(project[key], str) or not project[key]
               for key in ("id", "name"))
        or not all(isinstance(value[key], str) and value[key]
                   for key in ("id", "identifier", "title", "createdAt", "repositoryKey", "scope"))
        or not isinstance(value["goalComplete"], bool)
        or not isinstance(value["externalDependency"], bool)
        or (value["priority"] is not None and (
            not isinstance(value["priority"], int) or isinstance(value["priority"], bool)
        ))
    ):
        raise EngineRegistryError("Linear issue observation node has an invalid closed shape")
    return {
        "id": value["id"], "identifier": value["identifier"],
        "title": value["title"], "priority": value["priority"],
        "createdAt": value["createdAt"], "repositoryKey": value["repositoryKey"],
        "scope": value["scope"], "goalComplete": value["goalComplete"],
        "externalDependency": value["externalDependency"],
        "state": state["name"],
        "labels": [item["name"] for item in labels["nodes"]],
        "parentId": None if parent is None else parent["id"],
        "project": copy.deepcopy(dict(project)),
    }
