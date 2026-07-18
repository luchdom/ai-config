"""Conservative redaction for machine-local handoff evidence and CLI output."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEY = re.compile(r"(?:token|secret|password|api[_-]?key|authorization|cookie)", re.I)
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(token|secret|password|api[_-]?key|authorization|cookie)(\s*[:=]\s*)([^\s,;]+)"
)
BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")


def redact_text(value: str) -> str:
    value = SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)
    return BEARER.sub("Bearer [REDACTED]", value)


def redact_patch(value: str) -> str:
    """Keep structural diff evidence while removing every content hunk line."""

    output: list[str] = []
    binary_redacted = False
    for line in value.splitlines():
        if line.startswith("diff --git "):
            output.append("diff --git [REDACTED PATHS]")
            binary_redacted = False
        elif binary_redacted:
            continue
        elif line.startswith("index "):
            output.append("index [REDACTED OBJECT IDS]")
        elif line.startswith("--- "):
            output.append("--- [REDACTED PATH]")
        elif line.startswith("+++ "):
            output.append("+++ [REDACTED PATH]")
        elif line.startswith("@@"):
            output.append(line)
        elif line.startswith(("GIT binary patch", "Binary files ")):
            if not binary_redacted:
                output.append("[REDACTED BINARY PATCH]")
                binary_redacted = True
        elif line.startswith(("+", "-", " ")):
            output.append("[REDACTED CONTENT]")
        else:
            output.append("[REDACTED METADATA]")
    return "\n".join(output) + ("\n" if value else "")


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
