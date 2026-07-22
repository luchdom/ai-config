"""Injectable ntfy attention transport; Linear remains the durable source."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import quote, urlsplit


class NtfyTransportError(RuntimeError):
    pass


def validate_ntfy_policy(base_url: str, topic: str, allowed_hosts: set[str]) -> str:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.hostname.casefold() not in {host.casefold() for host in allowed_hosts}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not topic
    ):
        raise NtfyTransportError("ntfy endpoint or topic is outside configured policy")
    return f"{base_url.rstrip('/')}/{quote(topic, safe='')}"


class NtfyTransport:
    def __init__(
        self,
        *,
        requester: Callable[..., Mapping[str, Any]],
        sleeper: Callable[[float], None] = lambda _: None,
        max_attempts: int = 3,
    ) -> None:
        self.requester = requester
        self.sleeper = sleeper
        self.max_attempts = max_attempts

    def publish(
        self,
        *,
        base_url: str,
        topic: str,
        allowed_hosts: set[str],
        title: str,
        message: str,
        click_url: str,
        event_id: str,
        token: str | None = None,
    ) -> dict[str, Any]:
        url = validate_ntfy_policy(base_url, topic, allowed_hosts)
        payload = {
            "title": title[:120],
            "message": message[:500],
            "click": click_url,
            "tags": ["robot_face"],
        }
        headers = {"Content-Type": "application/json", "Idempotency-Key": event_id}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.requester(
                    method="POST",
                    url=url,
                    headers=headers,
                    body=json.dumps(payload, sort_keys=True),
                    timeout=10,
                    follow_redirects=False,
                )
            except Exception:
                response = {"status": 599, "url": url}
            status = response.get("status")
            if response.get("url", url) != url or status in {301, 302, 303, 307, 308}:
                return {"status": "failed", "eventId": event_id, "reason": "endpoint-drift"}
            if isinstance(status, int) and 200 <= status <= 299:
                return {"status": "delivered", "eventId": event_id, "attempts": attempt}
            if status != 429 and not (isinstance(status, int) and 500 <= status <= 599):
                return {"status": "failed", "eventId": event_id, "reason": "non-retryable"}
            if attempt < self.max_attempts:
                self.sleeper(float(2 ** (attempt - 1)))
        return {"status": "failed", "eventId": event_id, "reason": "retry-exhausted"}
