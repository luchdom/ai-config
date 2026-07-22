"""Fixture-first Linear GraphQL transport with fail-closed reconciliation."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit


class LinearTransportError(RuntimeError):
    """A Linear request could not be proven safe or complete."""


class LinearConfigurationError(LinearTransportError):
    pass


class LinearProtocolError(LinearTransportError):
    pass


class LinearGraphQLError(LinearTransportError):
    pass


class LinearRetryExhausted(LinearTransportError):
    pass


class LinearAmbiguousWrite(LinearTransportError):
    pass


def validate_completed_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate terminal pagination evidence emitted by ``paginate_verified``."""

    if not isinstance(value, Mapping) or set(value) != {"nodes", "pagination"}:
        raise LinearProtocolError("Linear completed observation envelope is malformed")
    nodes = value["nodes"]
    pagination = value["pagination"]
    exact = {
        "status", "pageCount", "nodeCount", "cursorChain",
        "terminalHasNextPage", "terminalEndCursor",
    }
    if (
        not isinstance(nodes, list)
        or any(not isinstance(item, Mapping) for item in nodes)
        or not isinstance(pagination, Mapping)
        or set(pagination) != exact
        or pagination.get("status") != "complete"
        or not isinstance(pagination.get("pageCount"), int)
        or pagination["pageCount"] < 1
        or pagination.get("nodeCount") != len(nodes)
        or pagination.get("terminalHasNextPage") is not False
        or not isinstance(pagination.get("cursorChain"), list)
        or len(pagination["cursorChain"]) != pagination["pageCount"] - 1
        or any(not isinstance(item, str) or not item for item in pagination["cursorChain"])
        or len(set(pagination["cursorChain"])) != len(pagination["cursorChain"])
        or (
            pagination.get("terminalEndCursor") is not None
            and not isinstance(pagination["terminalEndCursor"], str)
        )
    ):
        raise LinearProtocolError("Linear pagination evidence is incomplete or inconsistent")
    return copy.deepcopy({"nodes": [dict(item) for item in nodes], "pagination": dict(pagination)})


def validate_endpoint(endpoint: str, allowed_host: str) -> str:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or parsed.hostname != allowed_host.casefold()
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/graphql"
    ):
        raise LinearConfigurationError("Linear endpoint is outside the configured HTTPS GraphQL host")
    return endpoint


class LinearTransport:
    """Dependency-injected transport. It intentionally has no live requester default."""

    def __init__(
        self,
        *,
        endpoint: str,
        allowed_host: str,
        requester: Callable[..., Mapping[str, Any]],
        sleeper: Callable[[float], None] = lambda _: None,
        timeout_seconds: int = 15,
        max_attempts: int = 3,
    ) -> None:
        self.endpoint = validate_endpoint(endpoint, allowed_host)
        self.allowed_host = allowed_host.casefold()
        self.requester = requester
        self.sleeper = sleeper
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    def _response(self, response: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        if not isinstance(response, Mapping):
            raise LinearProtocolError("Linear response envelope is not an object")
        status = response.get("status")
        final_url = response.get("url", self.endpoint)
        if not isinstance(status, int):
            raise LinearProtocolError("Linear response lacks an HTTP status")
        if final_url != self.endpoint:
            raise LinearProtocolError("Linear redirect or endpoint drift was refused")
        body = response.get("body")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError as exc:
                raise LinearProtocolError("Linear response body is malformed JSON") from exc
        if not isinstance(body, Mapping):
            raise LinearProtocolError("Linear response body is not an object")
        return status, body

    def execute(
        self,
        query: str,
        variables: Mapping[str, Any],
        *,
        api_key: str,
        mutation: bool = False,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        if not api_key:
            raise LinearConfigurationError("LINEAR_API_KEY is unavailable")
        payload = {"query": query, "variables": copy.deepcopy(dict(variables))}
        if mutation:
            if not operation_id:
                raise LinearConfigurationError("Linear mutations require a stable operation ID")
            payload["variables"].setdefault("operationId", operation_id)
        for attempt in range(1, self.max_attempts + 1):
            try:
                raw = self.requester(
                    method="POST",
                    url=self.endpoint,
                    headers={"Authorization": api_key, "Content-Type": "application/json"},
                    body=json.dumps(payload, sort_keys=True),
                    timeout=self.timeout_seconds,
                    follow_redirects=False,
                )
            except Exception as exc:
                if mutation:
                    raise LinearAmbiguousWrite("Linear mutation outcome requires readback") from exc
                if attempt == self.max_attempts:
                    raise LinearRetryExhausted("Linear read retry budget was exhausted") from exc
                self.sleeper(float(2 ** (attempt - 1)))
                continue
            try:
                status, body = self._response(raw)
            except LinearProtocolError as exc:
                if mutation:
                    raise LinearAmbiguousWrite(
                        "Linear mutation returned an ambiguous protocol envelope"
                    ) from exc
                raise
            if status in {301, 302, 303, 307, 308}:
                if mutation:
                    raise LinearAmbiguousWrite(
                        "Linear mutation returned a redirect after dispatch"
                    )
                raise LinearProtocolError("Linear redirects are forbidden")
            if status == 429 or 500 <= status <= 599:
                if mutation:
                    raise LinearAmbiguousWrite("Linear mutation returned an ambiguous retryable status")
                if attempt == self.max_attempts:
                    raise LinearRetryExhausted("Linear retry budget was exhausted")
                self.sleeper(float(2 ** (attempt - 1)))
                continue
            if status != 200:
                if mutation:
                    raise LinearAmbiguousWrite(
                        f"Linear mutation returned HTTP {status} after dispatch"
                    )
                raise LinearProtocolError(f"Linear returned non-retryable HTTP {status}")
            if body.get("errors"):
                if mutation:
                    raise LinearAmbiguousWrite(
                        "Linear mutation returned GraphQL errors and requires readback"
                    )
                raise LinearGraphQLError("Linear GraphQL response contains errors")
            data = body.get("data")
            if not isinstance(data, Mapping):
                if mutation:
                    raise LinearAmbiguousWrite(
                        "Linear mutation response lacks an authoritative data envelope"
                    )
                raise LinearProtocolError("Linear GraphQL response lacks data")
            return copy.deepcopy(dict(data))
        raise LinearRetryExhausted("Linear retry budget was exhausted")

    def paginate(
        self,
        query: str,
        variables: Mapping[str, Any],
        *,
        api_key: str,
        connection: str,
    ) -> list[dict[str, Any]]:
        return self.paginate_verified(
            query, variables, api_key=api_key, connection=connection
        )["nodes"]

    def paginate_verified(
        self,
        query: str,
        variables: Mapping[str, Any],
        *,
        api_key: str,
        connection: str,
    ) -> dict[str, Any]:
        cursor: str | None = None
        seen: set[str] = set()
        nodes: list[dict[str, Any]] = []
        cursor_chain: list[str] = []
        page_count = 0
        while True:
            page_variables = copy.deepcopy(dict(variables))
            page_variables["after"] = cursor
            data = self.execute(query, page_variables, api_key=api_key)
            page = data.get(connection)
            if not isinstance(page, Mapping) or not isinstance(page.get("nodes"), list):
                raise LinearProtocolError("Linear connection page is malformed")
            if not isinstance(page.get("pageInfo"), Mapping):
                raise LinearProtocolError("Linear connection pageInfo is missing")
            if any(not isinstance(item, Mapping) for item in page["nodes"]):
                raise LinearProtocolError("Linear connection contains a malformed node")
            page_count += 1
            nodes.extend(copy.deepcopy(dict(item)) for item in page["nodes"])
            page_info = page["pageInfo"]
            if page_info.get("hasNextPage") is False:
                terminal_cursor = page_info.get("endCursor")
                if terminal_cursor is not None and not isinstance(terminal_cursor, str):
                    raise LinearProtocolError("Linear terminal cursor is malformed")
                return validate_completed_observation({
                    "nodes": nodes,
                    "pagination": {
                        "status": "complete",
                        "pageCount": page_count,
                        "nodeCount": len(nodes),
                        "cursorChain": cursor_chain,
                        "terminalHasNextPage": False,
                        "terminalEndCursor": terminal_cursor,
                    },
                })
            if page_info.get("hasNextPage") is not True:
                raise LinearProtocolError("Linear pagination completion flag is missing")
            next_cursor = page_info.get("endCursor")
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen:
                raise LinearProtocolError("Linear pagination cursor did not progress")
            seen.add(next_cursor)
            cursor_chain.append(next_cursor)
            cursor = next_cursor

    def reconciled_mutation(
        self,
        *,
        operation_id: str,
        observe: Callable[[], Mapping[str, Any]],
        mutate: Callable[[str], Any],
        is_applied: Callable[[Mapping[str, Any]], bool],
    ) -> dict[str, Any]:
        before = dict(observe())
        if is_applied(before):
            return {"status": "already-applied", "operationId": operation_id, "observation": before}
        try:
            mutate(operation_id)
        except LinearAmbiguousWrite as exc:
            try:
                after = dict(observe())
            except Exception as readback_error:
                raise LinearAmbiguousWrite(
                    "Linear mutation and readback outcomes are ambiguous"
                ) from readback_error
            if is_applied(after):
                return {"status": "reconciled", "operationId": operation_id, "observation": after}
            raise exc
        try:
            after = dict(observe())
        except Exception as readback_error:
            raise LinearAmbiguousWrite(
                "Linear mutation succeeded but readback is ambiguous"
            ) from readback_error
        if not is_applied(after):
            raise LinearAmbiguousWrite("Linear mutation readback did not prove the requested state")
        return {"status": "applied", "operationId": operation_id, "observation": after}
