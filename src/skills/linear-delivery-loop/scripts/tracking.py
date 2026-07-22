"""Tracking configuration and mutation-free Linear preflight."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import secrets
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from .supervisor import SupervisorEngine
from .store import SupervisorStoreError
from .contracts import ContractValidationError, validate_contract
from .linear_transport import validate_endpoint
from .ntfy_transport import NtfyTransportError, validate_ntfy_policy


class TrackingPreflightError(RuntimeError):
    def __init__(self, message: str, *, actionable: bool = True, ambiguous: bool = False):
        super().__init__(message)
        self.actionable = actionable
        self.ambiguous = ambiguous


def validate_tracking_config(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate identifiers/policy only; credential values are never accepted."""

    config = validate_contract("tracking-config", value)
    validate_endpoint(config["linear"]["endpoint"], config["linear"]["allowedHost"])
    return config


def tracking_config_digest(config: Mapping[str, Any]) -> str:
    validated = validate_tracking_config(config)
    encoded = json.dumps(validated, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _time(value: str) -> datetime:
    if not value.endswith("Z"):
        raise TrackingPreflightError("Preflight time must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TrackingPreflightError("Preflight time is malformed") from exc
    if parsed.tzinfo != timezone.utc:
        raise TrackingPreflightError("Preflight time must be UTC")
    return parsed


def resolve_environment(
    config: Mapping[str, Any], environment: Mapping[str, str]
) -> dict[str, str | None]:
    key_name = config["linear"]["apiKeyEnvironmentVariable"]
    api_key = environment.get(key_name)
    if not api_key:
        raise TrackingPreflightError("Required Linear credential is unavailable")
    ntfy = config["ntfy"]
    resolved: dict[str, str | None] = {"linearApiKey": api_key}
    for output, setting in (
        ("ntfyUrl", "endpointEnvironmentVariable"),
        ("ntfyTopic", "topicEnvironmentVariable"),
        ("ntfyToken", "tokenEnvironmentVariable"),
    ):
        resolved[output] = environment.get(ntfy[setting])
    if ntfy["enabled"] and (not resolved["ntfyUrl"] or not resolved["ntfyTopic"]):
        raise TrackingPreflightError("Enabled ntfy policy is not configured")
    if ntfy["enabled"]:
        try:
            validate_ntfy_policy(
                str(resolved["ntfyUrl"]),
                str(resolved["ntfyTopic"]),
                set(ntfy["allowedHosts"]),
            )
        except NtfyTransportError as exc:
            raise TrackingPreflightError("Resolved ntfy policy is outside the allowlist") from exc
    return resolved


def _identity(observed: Any, expected: Mapping[str, Any], name: str) -> None:
    if not isinstance(observed, Mapping):
        raise TrackingPreflightError(f"{name} observation is missing or ambiguous", ambiguous=True)
    if observed.get("id") != expected["id"]:
        raise TrackingPreflightError(f"{name} identifier differs from configuration")
    expected_name = expected.get("name", expected.get("key"))
    observed_name = observed.get("name", observed.get("key"))
    if observed_name != expected_name:
        raise TrackingPreflightError(f"{name} name differs from configuration")


class TrackingPreflight:
    """Read-only validation. The observer is an injected fixture/provider adapter."""

    __slots__ = (
        "observer", "_issuer_key", "issuer_id", "linear_adapter_id",
        "claim_journal_id", "claim_authority_id", "_claim_binding_id",
        "_supervisor", "_sealed",
    )

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("TrackingPreflight composition is immutable")
        object.__setattr__(self, name, value)

    def __init__(
        self,
        observer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        *,
        issuer_key: bytes | None = None,
        supervisor: SupervisorEngine | None = None,
        engine_registry_reference: str | None = None,
    ):
        object.__setattr__(self, "_sealed", False)
        self.observer = observer
        self._issuer_key = issuer_key or secrets.token_bytes(32)
        if len(self._issuer_key) < 32:
            raise TrackingPreflightError("Preflight issuer key is too short")
        self.issuer_id = "issuer-" + hashlib.sha256(self._issuer_key).hexdigest()[:32]
        if supervisor is not None and type(supervisor) is not SupervisorEngine:
            raise TrackingPreflightError("Supervisor engine type is not authoritative")
        if (supervisor is None) != (engine_registry_reference is None):
            raise TrackingPreflightError("Supervisor engine registry reference is incomplete")
        self._supervisor = supervisor
        try:
            metadata = supervisor.describe_control_plane_reference(
                str(engine_registry_reference)
            ) if supervisor is not None else {
            "reference": "engine-adapters-unavailable",
            "linearAdapterId": "linear-fixture-adapter",
            "claimJournalId": "selection-claim-journal-v1",
            "claimAuthorityId": "repository-authority-v1",
        }
        except SupervisorStoreError as exc:
            raise TrackingPreflightError("Engine adapter reference is unavailable") from exc
        self.linear_adapter_id = metadata["linearAdapterId"]
        self.claim_journal_id = metadata["claimJournalId"]
        self.claim_authority_id = metadata["claimAuthorityId"]
        self._claim_binding_id = metadata["reference"]
        object.__setattr__(self, "_sealed", True)

    def _execute_engine_operation(
        self, attestation: Mapping[str, Any], operation: str,
        payload: Mapping[str, Any], *, linear: Any,
    ) -> Any:
        supervisor = self._supervisor
        if supervisor is None or attestation.get("claimBindingId") != self._claim_binding_id:
            raise TrackingPreflightError("Engine adapter reference is unavailable")
        try:
            return supervisor.execute_control_plane_operation(
                self._claim_binding_id, operation, copy.deepcopy(dict(payload)),
                linear=linear,
            )
        except SupervisorStoreError as exc:
            raise TrackingPreflightError("Engine adapter reference is differently bound") from exc

    @staticmethod
    def _canonical(value: Mapping[str, Any]) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def run(
        self,
        config_value: Mapping[str, Any],
        *,
        environment: Mapping[str, str],
        repository_key: str,
        repository_id: str,
        supervisor_version: str,
        now: str,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        try:
            config = validate_tracking_config(config_value)
        except ContractValidationError as exc:
            raise TrackingPreflightError("Tracking configuration is invalid") from exc
        resolved = resolve_environment(config, environment)
        if config["repositoryKey"] != repository_key:
            raise TrackingPreflightError("Repository key differs from tracking configuration")
        if config["supervisorVersion"] != supervisor_version:
            raise TrackingPreflightError("Supervisor version is incompatible")
        try:
            observation = self.observer(copy.deepcopy(config))
        except Exception as exc:
            raise TrackingPreflightError(
                "Tracking observation failed before mutation", actionable=False
            ) from exc
        if not isinstance(observation, Mapping):
            raise TrackingPreflightError("Tracking observation is malformed", ambiguous=True)
        _identity(observation.get("workspace"), config["workspace"], "workspace")
        _identity(observation.get("team"), config["team"], "team")
        _identity(observation.get("project"), config["project"], "project")
        _identity(observation.get("owner"), config["owner"], "owner")
        for group in ("states", "labels"):
            observed_group = observation.get(group)
            if not isinstance(observed_group, Mapping):
                raise TrackingPreflightError(f"{group} observation is missing", ambiguous=True)
            if set(observed_group) != set(config[group]):
                raise TrackingPreflightError(f"{group} observation is incomplete or unexpected")
            for key, expected in config[group].items():
                _identity(observed_group.get(key), expected, f"{group}.{key}")
        issued = _time(now)
        expires = issued + timedelta(seconds=ttl_seconds)
        digest = tracking_config_digest(config)
        issued = {
            "status": "ready",
            "issuerId": self.issuer_id,
            "configDigest": digest,
            "repositoryKey": repository_key,
            "repositoryId": repository_id,
            "supervisorVersion": supervisor_version,
            "teamKey": config["team"]["key"],
            "workspaceId": config["workspace"]["id"],
            "projectId": config["project"]["id"],
            "ownerId": config["owner"]["id"],
            "linearEndpoint": config["linear"]["endpoint"],
            "linearTimeoutSeconds": config["linear"]["timeoutSeconds"],
            "linearMaxAttempts": config["linear"]["maxAttempts"],
            "linearAdapterId": self.linear_adapter_id,
            "claimJournalId": self.claim_journal_id,
            "claimAuthorityId": self.claim_authority_id,
            "claimBindingId": self._claim_binding_id,
            "ntfyEndpoint": resolved["ntfyUrl"] if config["ntfy"]["enabled"] else None,
            "ntfyTopic": resolved["ntfyTopic"] if config["ntfy"]["enabled"] else None,
            "ntfyMaxAttempts": config["ntfy"]["maxAttempts"],
            "issuedAt": now,
            "expiresAt": expires.isoformat().replace("+00:00", "Z"),
            "providerObserved": True,
            "mutationPerformed": False,
        }
        signature = hmac.new(
            self._issuer_key, self._canonical(issued), hashlib.sha256
        ).hexdigest()
        attestation_id = hashlib.sha256(
            self._canonical(issued) + signature.encode("ascii")
        ).hexdigest()[:32]
        return issued | {
            "attestationId": f"preflight-{attestation_id}",
            "issuerSignature": f"hmac-sha256:{signature}",
        }

    def verify_attestation(
        self,
        attestation: Mapping[str, Any],
        *,
        config: Mapping[str, Any],
        repository_key: str,
        repository_id: str,
        supervisor_version: str,
        now: str,
    ) -> dict[str, Any]:
        exact = {
            "status", "issuerId", "attestationId", "issuerSignature", "configDigest",
            "repositoryKey", "repositoryId", "supervisorVersion", "teamKey",
            "workspaceId", "projectId", "ownerId", "linearEndpoint",
            "linearTimeoutSeconds", "linearMaxAttempts", "linearAdapterId",
            "claimJournalId", "claimAuthorityId",
            "claimBindingId",
            "ntfyEndpoint", "ntfyTopic", "ntfyMaxAttempts", "issuedAt", "expiresAt",
            "providerObserved", "mutationPerformed",
        }
        if not isinstance(attestation, Mapping) or set(attestation) != exact:
            raise TrackingPreflightError("Preflight attestation is not an exact issued contract")
        unsigned = {key: copy.deepcopy(attestation[key]) for key in exact - {"attestationId", "issuerSignature"}}
        expected_signature = hmac.new(
            self._issuer_key, self._canonical(unsigned), hashlib.sha256
        ).hexdigest()
        expected_id = hashlib.sha256(
            self._canonical(unsigned) + expected_signature.encode("ascii")
        ).hexdigest()[:32]
        if (
            attestation["issuerId"] != self.issuer_id
            or not hmac.compare_digest(
                str(attestation["issuerSignature"]), f"hmac-sha256:{expected_signature}"
            )
            or attestation["attestationId"] != f"preflight-{expected_id}"
        ):
            raise TrackingPreflightError("Preflight attestation was not issued by this authority")
        return _validate_attestation_bindings(
            attestation,
            config=config,
            repository_key=repository_key,
            repository_id=repository_id,
            supervisor_version=supervisor_version,
            now=now,
            linear_adapter_id=self.linear_adapter_id,
            claim_journal_id=self.claim_journal_id,
            claim_authority_id=self.claim_authority_id,
            claim_binding_id=self._claim_binding_id,
        )


def _validate_attestation_bindings(
    attestation: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    repository_key: str,
    repository_id: str,
    supervisor_version: str,
    now: str,
    linear_adapter_id: str,
    claim_journal_id: str,
    claim_authority_id: str,
    claim_binding_id: str,
) -> dict[str, Any]:
    required = {
        "status", "issuerId", "attestationId", "issuerSignature", "configDigest", "repositoryKey", "repositoryId",
        "supervisorVersion", "ownerId", "linearEndpoint", "linearTimeoutSeconds",
        "linearMaxAttempts", "linearAdapterId", "claimJournalId", "claimAuthorityId", "claimBindingId", "ntfyEndpoint", "ntfyTopic", "ntfyMaxAttempts",
        "issuedAt", "expiresAt", "providerObserved", "mutationPerformed",
    }
    if not isinstance(attestation, Mapping) or not required.issubset(attestation):
        raise TrackingPreflightError("Preflight attestation is incomplete")
    validated = validate_tracking_config(config)
    expected = {
        "status": "ready",
        "configDigest": tracking_config_digest(validated),
        "repositoryKey": repository_key,
        "repositoryId": repository_id,
        "supervisorVersion": supervisor_version,
        "ownerId": validated["owner"]["id"],
        "linearEndpoint": validated["linear"]["endpoint"],
        "linearTimeoutSeconds": validated["linear"]["timeoutSeconds"],
        "linearMaxAttempts": validated["linear"]["maxAttempts"],
        "linearAdapterId": linear_adapter_id,
        "claimJournalId": claim_journal_id,
        "claimAuthorityId": claim_authority_id,
        "claimBindingId": claim_binding_id,
        "ntfyMaxAttempts": validated["ntfy"]["maxAttempts"],
        "providerObserved": True,
        "mutationPerformed": False,
    }
    if any(attestation.get(key) != value for key, value in expected.items()):
        raise TrackingPreflightError("Preflight attestation binding changed")
    issued = _time(str(attestation["issuedAt"]))
    expires = _time(str(attestation["expiresAt"]))
    observed = _time(now)
    if expires <= issued or observed < issued or observed >= expires:
        raise TrackingPreflightError("Preflight attestation is not currently valid")
    return copy.deepcopy(dict(attestation))
