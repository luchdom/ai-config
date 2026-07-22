"""Explicit fixture-first composition for SAAS-47 control-plane behavior.

This module is intentionally absent from the public engine command union. Later
integration work may bind its injected ports after attended preflight.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from .control_plane_records import ControlPlaneRecords, stable_id
from .migration import build_migration_report
from .ntfy_transport import NtfyTransport
from .selection import ClaimRolledBack, claim_selected, reconcile_wip, select_candidate
from .tracking import (
    TrackingPreflight,
    TrackingPreflightError,
    resolve_environment,
    validate_tracking_config,
)


class LinearControlPlane:
    __slots__ = ("records", "preflight", "linear", "ntfy")

    def __init__(
        self,
        *,
        records: ControlPlaneRecords,
        preflight: TrackingPreflight,
        linear: Any,
        ntfy: NtfyTransport | None = None,
    ) -> None:
        self.records = records
        self.preflight = preflight
        self.linear = linear
        self.ntfy = ntfy

    def _attest(
        self, attestation: Mapping[str, Any], *, config: Mapping[str, Any],
        repository_key: str, repository_id: str, supervisor_version: str, now: str,
    ) -> dict[str, Any]:
        verified = self.preflight.verify_attestation(
            attestation,
            config=config,
            repository_key=repository_key,
            repository_id=repository_id,
            supervisor_version=supervisor_version,
            now=now,
        )
        if (
            self.linear.endpoint != verified["linearEndpoint"]
            or self.linear.timeout_seconds != verified["linearTimeoutSeconds"]
            or self.linear.max_attempts != verified["linearMaxAttempts"]
        ):
            raise TrackingPreflightError("Injected Linear transport differs from preflight")
        return verified

    def _engine_operation(
        self, verified: Mapping[str, Any], operation: str, **payload: Any,
    ) -> Any:
        return self.preflight._execute_engine_operation(
            verified, operation, payload, linear=self.linear
        )

    def _verified_claim_ports(self, verified: Mapping[str, Any]) -> tuple[Any, Any]:
        control = self

        class ClosedClaimPort:
            transport = control.linear
            adapter_id = verified["linearAdapterId"]
            journal_id = verified["claimJournalId"]

            def reread(self, issue_id: str, operation_id: str) -> Any:
                return control._engine_operation(
                    verified, "claim-reread", issueId=issue_id,
                    operationId=operation_id,
                )

            def claim(self, issue: Mapping[str, Any], operation_id: str) -> Any:
                return control._engine_operation(
                    verified, "claim", issue=issue, operationId=operation_id,
                )

            def readback(self, issue_id: str, operation_id: str) -> Any:
                return control._engine_operation(
                    verified, "claim-readback", issueId=issue_id,
                    operationId=operation_id,
                )

        class ClosedRepositoryAuthority:
            authority_id = verified["claimAuthorityId"]

            def __getattr__(self, name: str) -> Any:
                operations = {
                    "current_execution_lease": "current-execution-lease",
                    "authorize_recovery": "authorize-recovery",
                    "prepare": "prepare", "commit": "commit",
                    "rollback_if_safe": "rollback-if-safe",
                    "protect": "protect", "recover": "recover",
                }
                operation = operations.get(name)
                if operation is None:
                    raise AttributeError(name)
                return lambda **payload: control._engine_operation(
                    verified, operation, **payload
                )

        return ClosedClaimPort(), ClosedRepositoryAuthority()

    def verify(
        self, config: Mapping[str, Any], *, environment: Mapping[str, str],
        repository_key: str, repository_id: str, supervisor_version: str,
        now: str, issue_id: str, failure_link: str,
    ) -> dict[str, Any]:
        try:
            result = self.preflight.run(
                config,
                environment=environment,
                repository_key=repository_key,
                repository_id=repository_id,
                supervisor_version=supervisor_version,
                now=now,
            )
            self._attest(
                result, config=config, repository_key=repository_key,
                repository_id=repository_id, supervisor_version=supervisor_version, now=now,
            )
            return result
        except TrackingPreflightError as exc:
            self.records.record_failure(
                failure_kind="preflight-failure", issue_id=issue_id,
                source_id=hashlib.sha256(str(exc).encode("utf-8")).hexdigest()[:24],
                source_timestamp=now, created_at=now, link=failure_link,
                summary=str(exc), actionable=exc.actionable or exc.ambiguous,
                transient_within_budget=not (exc.actionable or exc.ambiguous),
            )
            raise

    def choose_or_resume(
        self,
        *,
        repository_key: str,
        attestation: Mapping[str, Any],
        config: Mapping[str, Any],
        repository_id: str,
        supervisor_version: str,
        now: str,
        multiple_wip_link: str,
    ) -> dict[str, Any]:
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        observed = self._engine_operation(verified, "observe-selection")
        def decide(state: dict[str, Any]) -> dict[str, Any]:
            required = {
                "issues", "pagination", "reservations", "issueWorktrees", "recovery",
                "autonomousIssueId",
            }
            if not isinstance(observed, Mapping) or set(observed) != required:
                raise TrackingPreflightError("Authoritative selection snapshot is incomplete")
            complete = [copy.deepcopy(dict(issue)) for issue in observed["issues"]]
            reservation_records = [
                copy.deepcopy(dict(item)) for item in observed["reservations"]
            ]
            issue_worktrees = copy.deepcopy(dict(observed["issueWorktrees"]))
            recovery = copy.deepcopy(dict(observed["recovery"]))
            autonomous_issue_id = observed["autonomousIssueId"]
            reservation_issue_ids = {
                str(item["issueId"])
                for item in reservation_records
                if item.get("status") in {"live", "handoff-pending"}
                and item.get("issueId") is not None
            }
            snapshot_payload = {
                "issues": complete,
                "pagination": copy.deepcopy(observed["pagination"]),
                "reservations": reservation_records,
                "issueWorktrees": issue_worktrees,
                "recovery": recovery,
                "autonomousIssueId": autonomous_issue_id,
            }
            snapshot_digest = "sha256:" + hashlib.sha256(
                json.dumps(snapshot_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            protected = []
            for collection in ("decisions", "publicationRequests", "followUps", "selectionClaims"):
                protected.extend(
                    item["id"] for item in state[collection] if item["status"] == "pending"
                )
            live_reservations = [
                item for item in reservation_records if item.get("status") in {"live", "handoff-pending"}
            ]
            if protected or recovery.get("status") != "clean":
                return {
                    "action": "protected-exit", "attention": False,
                    "reason": "authoritative-work-present",
                    "protectedIds": sorted(protected),
                }
            wip = reconcile_wip(
                complete,
                autonomous_issue_id=autonomous_issue_id,
                reservation_issue_ids=reservation_issue_ids,
            )
            if wip["action"] == "resume":
                issue_id = wip["issueId"]
                foreign_reservations = [
                    item for item in live_reservations if item.get("issueId") != issue_id
                ]
                foreign_worktrees = [key for key in issue_worktrees if key != issue_id]
                if foreign_reservations or foreign_worktrees:
                    return {
                        "action": "protected-exit", "attention": False,
                        "reason": "foreign-authority-present",
                    }
                return wip
            if wip["action"] != "select":
                return wip
            if live_reservations or issue_worktrees:
                return {
                    "action": "protected-exit", "attention": False,
                    "reason": "foreign-authority-present",
                }
            selected = select_candidate(complete, repository_key)
            if selected is None:
                return {"action": "empty", "attention": False}
            issue_id = str(selected["identifier"])
            claim_id = self.records._record(
                kind="selection-claim",
                record_id=stable_id(
                    "selection", issue_id, snapshot_digest, verified["configDigest"],
                    verified["repositoryId"]
                ),
                issue_id=issue_id,
                created_at=now,
                source_timestamp=now,
                status="pending",
                link=multiple_wip_link,
                summary=f"Prepared selection for {issue_id}",
                data={
                    "configDigest": verified["configDigest"],
                    "snapshotDigest": snapshot_digest,
                    "repositoryKey": repository_key,
                    "repositoryId": verified["repositoryId"],
                    "ownerId": verified["ownerId"],
                    "operationId": None,
                    "startedAt": None,
                    "executionOwnerId": None,
                    "executionLeaseRevision": None,
                    "executionLeaseExpiresAt": None,
                    "recoveryGeneration": 0,
                    "recoveryOwnerId": None,
                    "recoveryLeaseRevision": None,
                    "recoveryLeaseExpiresAt": None,
                    "recoveryStartedAt": None,
                    "recoveryProof": None,
                    "terminalResult": None,
                },
            )
            state["selectionClaims"].append(claim_id)
            return {
                "action": "selected", "attention": False, "issue": selected,
                "selectionClaimId": claim_id["id"], "snapshotDigest": snapshot_digest,
            }

        _, decision = self.records.store.mutate(decide)
        wip = decision
        if wip["action"] == "fail-closed":
            source_id = "multiple-wip:" + ",".join(wip["issueIds"])
            self.records.record_failure(
                failure_kind="reconciliation-failure",
                issue_id=str(wip["issueIds"][0]),
                source_id=source_id,
                source_timestamp=now,
                created_at=now,
                link=multiple_wip_link,
                summary="Multiple Linear issues are active; selection stopped.",
                actionable=True,
                transient_within_budget=False,
            )
            return wip
        return wip

    def claim(
        self, selected: Mapping[str, Any], *, operation_id: str,
        repository_key: str,
        selection_claim_id: str, attestation: Mapping[str, Any],
        config: Mapping[str, Any], repository_id: str,
        supervisor_version: str, now: str, recovery: bool = False,
    ) -> dict[str, Any]:
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        with self.records.store.operation_fence(operation_id) as fence_token:
            if fence_token is None:
                state = self.records.store.load()
                current = next(
                    (item for item in state["selectionClaims"]
                     if item["id"] == selection_claim_id),
                    None,
                )
                recovering = current is not None and current["status"] == "recovering"
                return {
                    "status": "recovery-in-flight" if recovering else "in-flight",
                    "issueId": selected["identifier"], "operationId": operation_id,
                }
            return self._claim_fenced(
                selected, operation_id=operation_id, repository_key=repository_key,
                selection_claim_id=selection_claim_id, verified=verified, now=now,
                recovery=recovery, fence_token=fence_token,
            )

    def _claim_fenced(
        self, selected: Mapping[str, Any], *, operation_id: str,
        repository_key: str, selection_claim_id: str,
        verified: Mapping[str, Any], now: str, recovery: bool,
        fence_token: str,
    ) -> dict[str, Any]:
        port, authority = self._verified_claim_ports(verified)
        acquisition = self._acquire_selection(
            selection_claim_id, operation_id=operation_id, selected=selected,
            verified=verified, now=now, recovery=recovery, authority=authority,
        )
        if acquisition["mode"] == "replay":
            return copy.deepcopy(acquisition["result"])
        if acquisition["mode"] in {"in-progress", "recovery-required", "recovering"}:
            return {
                "status": {
                    "in-progress": "in-flight",
                    "recovery-required": "recovery-required",
                    "recovering": "recovery-in-flight",
                }[acquisition["mode"]], "issueId": selected["identifier"],
                "operationId": operation_id,
            }
        if acquisition["mode"] == "recovery-acquired":
            try:
                return self._recover_selection(
                    acquisition["record"], selected=selected, operation_id=operation_id,
                    port=port, authority=authority, fence_token=fence_token,
                )
            except Exception:
                self._release_recovery(acquisition["record"], operation_id)
                raise
        try:
            result = claim_selected(
                selected,
                operation_id=operation_id,
                repository_key=repository_key,
                reread=lambda issue_id: port.reread(issue_id, operation_id),
                authority=authority,
                claim=lambda issue, op: port.claim(issue, op),
                readback=lambda issue_id: port.readback(issue_id, operation_id),
            )
        except ClaimRolledBack:
            self._finish_selection(
                selection_claim_id, operation_id, "inert",
                result={
                    "status": "inert", "issueId": selected["identifier"],
                    "operationId": operation_id,
                },
            )
            raise
        except Exception:
            self._finish_selection(selection_claim_id, operation_id, "protected")
            raise
        self._finish_selection(
            selection_claim_id, operation_id, "consumed", result=result
        )
        return result

    def _acquire_selection(
        self, selection_claim_id: str, *, operation_id: str,
        selected: Mapping[str, Any], verified: Mapping[str, Any], now: str,
        recovery: bool, authority: Any,
    ) -> dict[str, Any]:
        def acquire(state: dict[str, Any]) -> dict[str, Any]:
            record = next(
                (item for item in state["selectionClaims"] if item["id"] == selection_claim_id),
                None,
            )
            if (
                record is None or record["issueId"] != selected.get("identifier")
                or record["data"]["configDigest"] != verified["configDigest"]
                or record["data"]["repositoryId"] != verified["repositoryId"]
                or record["data"]["ownerId"] != verified["ownerId"]
            ):
                raise TrackingPreflightError("Selection claim is absent or differently bound")
            bound = record["data"]["operationId"]
            if record["status"] == "pending":
                if recovery:
                    raise TrackingPreflightError("A pending selection has no crashed owner")
                lease = self._execution_lease(authority, operation_id=operation_id, now=now)
                record["status"] = "in-flight"
                record["data"]["operationId"] = operation_id
                record["data"]["startedAt"] = now
                record["data"]["executionOwnerId"] = lease["ownerId"]
                record["data"]["executionLeaseRevision"] = lease["leaseRevision"]
                record["data"]["executionLeaseExpiresAt"] = lease["expiresAt"]
                return {"mode": "acquired", "record": copy.deepcopy(record)}
            if bound != operation_id:
                raise TrackingPreflightError("Selection operation is competing or already terminal")
            if record["status"] == "in-flight":
                if not recovery:
                    return {"mode": "in-progress", "record": copy.deepcopy(record)}
                proof = self._recovery_proof(
                    authority, record=record, now=now,
                    prior_recovery=record["data"]["recoveryGeneration"] > 0,
                )
                if proof is None:
                    return {"mode": "in-progress", "record": copy.deepcopy(record)}
                record["status"] = "recovering"
                record["data"]["recoveryGeneration"] += 1
                record["data"]["recoveryOwnerId"] = proof["recoveryOwnerId"]
                record["data"]["recoveryLeaseRevision"] = proof["recoveryLeaseRevision"]
                record["data"]["recoveryLeaseExpiresAt"] = proof["recoveryLeaseExpiresAt"]
                record["data"]["recoveryStartedAt"] = now
                record["data"]["recoveryProof"] = proof
                return {"mode": "recovery-acquired", "record": copy.deepcopy(record)}
            if record["status"] == "protected":
                if not recovery:
                    return {"mode": "recovery-required", "record": copy.deepcopy(record)}
                proof = self._recovery_proof(
                    authority, record=record, now=now,
                    prior_recovery=record["data"]["recoveryGeneration"] > 0,
                )
                if proof is None:
                    return {"mode": "in-progress", "record": copy.deepcopy(record)}
                record["status"] = "recovering"
                record["data"]["recoveryGeneration"] += 1
                record["data"]["recoveryOwnerId"] = proof["recoveryOwnerId"]
                record["data"]["recoveryLeaseRevision"] = proof["recoveryLeaseRevision"]
                record["data"]["recoveryLeaseExpiresAt"] = proof["recoveryLeaseExpiresAt"]
                record["data"]["recoveryStartedAt"] = now
                record["data"]["recoveryProof"] = proof
                return {"mode": "recovery-acquired", "record": copy.deepcopy(record)}
            if record["status"] == "recovering":
                if not recovery:
                    return {"mode": "recovering", "record": copy.deepcopy(record)}
                proof = self._recovery_proof(
                    authority, record=record, now=now, prior_recovery=True
                )
                if proof is None:
                    return {"mode": "recovering", "record": copy.deepcopy(record)}
                record["data"]["recoveryGeneration"] += 1
                record["data"]["recoveryOwnerId"] = proof["recoveryOwnerId"]
                record["data"]["recoveryLeaseRevision"] = proof["recoveryLeaseRevision"]
                record["data"]["recoveryLeaseExpiresAt"] = proof["recoveryLeaseExpiresAt"]
                record["data"]["recoveryStartedAt"] = now
                record["data"]["recoveryProof"] = proof
                return {"mode": "recovery-acquired", "record": copy.deepcopy(record)}
            if record["status"] in {"consumed", "inert"}:
                result = record["data"]["terminalResult"]
                if not isinstance(result, Mapping):
                    raise TrackingPreflightError("Selection terminal result is unavailable")
                return {"mode": "replay", "result": copy.deepcopy(dict(result))}
            raise TrackingPreflightError("Selection operation is competing or already terminal")

        _, result = self.records.store.mutate(acquire)
        return result

    @staticmethod
    def _execution_lease(authority: Any, *, operation_id: str, now: str) -> dict[str, Any]:
        lease = authority.current_execution_lease(operation_id=operation_id, now=now)
        exact = {"operationId", "ownerId", "leaseRevision", "expiresAt"}
        if (
            not isinstance(lease, Mapping) or set(lease) != exact
            or lease["operationId"] != operation_id
            or not isinstance(lease["ownerId"], str) or not lease["ownerId"]
            or not isinstance(lease["leaseRevision"], int) or lease["leaseRevision"] < 1
            or LinearControlPlane._utc(str(lease["expiresAt"])) <= LinearControlPlane._utc(now)
        ):
            raise TrackingPreflightError("Execution lease is not current and authoritative")
        return copy.deepcopy(dict(lease))

    @staticmethod
    def _recovery_proof(
        authority: Any, *, record: Mapping[str, Any], now: str,
        prior_recovery: bool = False,
    ) -> dict[str, Any] | None:
        data = record["data"]
        previous_owner = data["recoveryOwnerId"] if prior_recovery else data["executionOwnerId"]
        previous_revision = data["recoveryLeaseRevision"] if prior_recovery else data["executionLeaseRevision"]
        previous_expiry = data["recoveryLeaseExpiresAt"] if prior_recovery else data["executionLeaseExpiresAt"]
        proof = authority.authorize_recovery(
            operation_id=data["operationId"],
            previous_owner_id=previous_owner,
            previous_lease_revision=previous_revision,
            previous_lease_expires_at=previous_expiry,
            now=now,
        )
        live_exact = {
            "status", "operationId", "previousOwnerId", "previousLeaseRevision",
            "previousLeaseExpiresAt", "observedAt",
        }
        if (
            isinstance(proof, Mapping) and set(proof) == live_exact
            and proof["status"] == "live"
            and proof["operationId"] == data["operationId"]
            and proof["previousOwnerId"] == previous_owner
            and proof["previousLeaseRevision"] == previous_revision
            and proof["previousLeaseExpiresAt"] == previous_expiry
            and proof["observedAt"] == now
            and LinearControlPlane._utc(str(proof["previousLeaseExpiresAt"]))
            > LinearControlPlane._utc(now)
        ):
            return None
        exact = {
            "status", "proofId", "operationId", "previousOwnerId",
            "previousLeaseRevision", "previousLeaseExpiresAt", "recoveryOwnerId",
            "recoveryLeaseRevision", "recoveryLeaseExpiresAt", "observedAt", "reason",
        }
        if (
            not isinstance(proof, Mapping) or set(proof) != exact
            or proof["status"] != "authorized"
            or proof["operationId"] != data["operationId"]
            or proof["previousOwnerId"] != previous_owner
            or proof["previousLeaseRevision"] != previous_revision
            or proof["previousLeaseExpiresAt"] != previous_expiry
            or proof["observedAt"] != now
            or proof["reason"] not in {"owner-dead", "lease-expired"}
            or not isinstance(proof["proofId"], str) or not proof["proofId"]
            or not isinstance(proof["recoveryOwnerId"], str) or not proof["recoveryOwnerId"]
            or not isinstance(proof["recoveryLeaseRevision"], int)
            or proof["recoveryLeaseRevision"] < 1
            or LinearControlPlane._utc(str(proof["recoveryLeaseExpiresAt"])) <= LinearControlPlane._utc(now)
            or (
                proof["reason"] == "lease-expired"
                and LinearControlPlane._utc(str(proof["previousLeaseExpiresAt"]))
                > LinearControlPlane._utc(now)
            )
        ):
            raise TrackingPreflightError("Recovery lacks durable dead-owner or expired-lease proof")
        return copy.deepcopy(dict(proof))

    @staticmethod
    def _utc(value: str) -> datetime:
        if not value.endswith("Z"):
            raise TrackingPreflightError("Recovery time must be UTC RFC3339")
        try:
            parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise TrackingPreflightError("Recovery time is malformed") from exc
        if parsed.tzinfo != timezone.utc:
            raise TrackingPreflightError("Recovery time must be UTC")
        return parsed

    def _recover_selection(
        self, record: Mapping[str, Any], *, selected: Mapping[str, Any],
        operation_id: str, port: Any, authority: Any, fence_token: str,
    ) -> dict[str, Any]:
        self._require_recovery_owner(record, operation_id, fence_token)
        local = authority.recover(operation_id=operation_id, issue=selected)
        self._require_recovery_owner(record, operation_id, fence_token)
        observed = dict(port.readback(str(selected["identifier"]), operation_id))
        if observed.get("state") == "In Progress":
            self._require_recovery_owner(record, operation_id, fence_token)
            authority.commit(operation_id=operation_id)
            result = {"status": "reconciled", "issueId": selected["identifier"], "operationId": operation_id}
            self._finish_selection(
                record["id"], operation_id, "consumed", result=result,
                recovery_record=record,
            )
            return result
        if not isinstance(local, Mapping) or local.get("status") != "prepared":
            result = {"status": "inert", "issueId": selected["identifier"], "operationId": operation_id}
            self._finish_selection(
                record["id"], operation_id, "inert", result=result,
                recovery_record=record,
            )
            raise TrackingPreflightError("Selection recovery found no prepared local authority")
        self._require_recovery_owner(record, operation_id, fence_token)
        port.claim(selected, operation_id)
        self._require_recovery_owner(record, operation_id, fence_token)
        after = dict(port.readback(str(selected["identifier"]), operation_id))
        if after.get("state") != "In Progress":
            raise TrackingPreflightError("Selection recovery readback remains ambiguous")
        self._require_recovery_owner(record, operation_id, fence_token)
        authority.commit(operation_id=operation_id)
        result = {"status": "recovered", "issueId": selected["identifier"], "operationId": operation_id}
        self._finish_selection(
            record["id"], operation_id, "consumed", result=result,
            recovery_record=record,
        )
        return result

    def _require_recovery_owner(
        self, recovery_record: Mapping[str, Any], operation_id: str,
        fence_token: str,
    ) -> None:
        self.records.store.require_operation_fence(operation_id, fence_token)
        current = self.records.store.load()
        record = next(
            (item for item in current["selectionClaims"]
             if item["id"] == recovery_record["id"]),
            None,
        )
        if (
            record is None or record["status"] != "recovering"
            or record["data"]["operationId"] != operation_id
            or record["data"]["recoveryGeneration"]
            != recovery_record["data"]["recoveryGeneration"]
            or record["data"]["recoveryOwnerId"]
            != recovery_record["data"]["recoveryOwnerId"]
            or record["data"]["recoveryLeaseRevision"]
            != recovery_record["data"]["recoveryLeaseRevision"]
        ):
            raise TrackingPreflightError("Recovery side effect lost its fencing generation")

    def _release_recovery(self, recovery_record: Mapping[str, Any], operation_id: str) -> None:
        def release(state: dict[str, Any]) -> None:
            record = next(item for item in state["selectionClaims"] if item["id"] == recovery_record["id"])
            if (
                record["status"] == "recovering"
                and record["data"]["operationId"] == operation_id
                and record["data"]["recoveryGeneration"] == recovery_record["data"]["recoveryGeneration"]
                and record["data"]["recoveryOwnerId"] == recovery_record["data"]["recoveryOwnerId"]
            ):
                record["status"] = "protected"
        self.records.store.mutate(release)

    def _finish_selection(
        self, selection_claim_id: str, operation_id: str, status: str,
        *, result: Mapping[str, Any] | None = None,
        recovery_record: Mapping[str, Any] | None = None,
    ) -> None:
        def finish(state: dict[str, Any]) -> None:
            record = next(item for item in state["selectionClaims"] if item["id"] == selection_claim_id)
            expected_status = "recovering" if recovery_record is not None else "in-flight"
            owns_recovery = recovery_record is None or (
                record["data"]["recoveryGeneration"] == recovery_record["data"]["recoveryGeneration"]
                and record["data"]["recoveryOwnerId"] == recovery_record["data"]["recoveryOwnerId"]
            )
            if record["status"] != expected_status or record["data"]["operationId"] != operation_id or not owns_recovery:
                raise TrackingPreflightError("Selection terminal CAS does not own the operation")
            record["status"] = status
            if status in {"consumed", "inert"}:
                if not isinstance(result, Mapping):
                    raise TrackingPreflightError("Selection terminal result must be persisted")
                record["data"]["terminalResult"] = copy.deepcopy(dict(result))
        self.records.store.mutate(finish)

    def request_decision(
        self, *, issue_id: str, source_timestamp: str, created_at: str, link: str,
        question: str, options: list[Mapping[str, str]], recommendation: str,
        attestation: Mapping[str, Any], config: Mapping[str, Any],
        repository_key: str, repository_id: str, supervisor_version: str, now: str,
    ) -> dict[str, Any]:
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        return self.records.request_decision(
            issue_id=issue_id, source_timestamp=source_timestamp, created_at=created_at,
            link=link, question=question, options=options, recommendation=recommendation,
            owner_id=verified["ownerId"],
            config_digest=verified["configDigest"],
            repository_id=verified["repositoryId"],
        )

    def publication_refusal(
        self, *, issue_id: str, operation_id: str, head_sha: str,
        source_timestamp: str, created_at: str, link: str, reason: str,
        evidence: Mapping[str, Any], refusal_kind: str,
        attestation: Mapping[str, Any], config: Mapping[str, Any],
        repository_key: str, repository_id: str, supervisor_version: str, now: str,
    ) -> dict[str, Any]:
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        return self.records.publication_refusal(
            issue_id=issue_id, operation_id=operation_id, head_sha=head_sha,
            source_timestamp=source_timestamp, created_at=created_at, link=link,
            reason=reason, evidence=evidence, refusal_kind=refusal_kind,
            owner_id=verified["ownerId"],
            config_digest=verified["configDigest"],
            repository_id=verified["repositoryId"],
        )

    def consume_decision_reply(
        self, *, decision_id: str, actor_id: str, reply_id: str,
        reply_created_at: str, body: str, attestation: Mapping[str, Any],
        config: Mapping[str, Any], repository_key: str, repository_id: str,
        supervisor_version: str, now: str,
    ) -> dict[str, Any] | None:
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        return self.records.consume_decision_reply(
            decision_id=decision_id, actor_id=actor_id, reply_id=reply_id,
            reply_created_at=reply_created_at, body=body,
            owner_id=verified["ownerId"],
            config_digest=verified["configDigest"],
            repository_id=verified["repositoryId"],
        )

    def consume_publication_reply(
        self, *, request_id: str, actor_id: str, reply_id: str,
        reply_created_at: str, body: str, reconciled: bool,
        attestation: Mapping[str, Any], config: Mapping[str, Any],
        repository_key: str, repository_id: str, supervisor_version: str, now: str,
    ) -> dict[str, Any] | None:
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        return self.records.consume_publication_reply(
            request_id=request_id, actor_id=actor_id, reply_id=reply_id,
            reply_created_at=reply_created_at, body=body, reconciled=reconciled,
            owner_id=verified["ownerId"],
            config_digest=verified["configDigest"],
            repository_id=verified["repositoryId"],
        )

    def propose_issue_contract(
        self, *, issue_id: str, source_timestamp: str, created_at: str,
        link: str, summary: str, proposal_kind: str,
        attestation: Mapping[str, Any], config: Mapping[str, Any],
        repository_key: str, repository_id: str, supervisor_version: str, now: str,
    ) -> dict[str, Any]:
        self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        return self.records.propose_issue_contract(
            issue_id=issue_id, source_timestamp=source_timestamp, created_at=created_at,
            link=link, summary=summary, proposal_kind=proposal_kind,
        )

    def record_worker_failure(
        self, *, issue_id: str, source_id: str, source_timestamp: str,
        created_at: str, link: str, summary: str, actionable: bool,
        transient_within_budget: bool, attestation: Mapping[str, Any],
        config: Mapping[str, Any], repository_key: str, repository_id: str,
        supervisor_version: str, now: str,
    ) -> dict[str, Any] | None:
        self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        return self.records.record_failure(
            failure_kind="worker-failure", issue_id=issue_id, source_id=source_id,
            source_timestamp=source_timestamp, created_at=created_at, link=link,
            summary=summary, actionable=actionable,
            transient_within_budget=transient_within_budget,
        )

    def notify(self, event_id: str, *, config_value: Mapping[str, Any],
               environment: Mapping[str, str], now: str,
               attestation: Mapping[str, Any], repository_key: str,
               repository_id: str, supervisor_version: str,
               after_publish: Callable[[], None] | None = None) -> dict[str, Any]:
        config = validate_tracking_config(config_value)
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version, now=now,
        )
        if not config["ntfy"]["enabled"] or self.ntfy is None:
            return {"status": "disabled", "eventId": event_id}
        resolved = resolve_environment(config, environment)
        if (
            resolved["ntfyUrl"] != verified["ntfyEndpoint"]
            or resolved["ntfyTopic"] != verified["ntfyTopic"]
            or self.ntfy.max_attempts != verified["ntfyMaxAttempts"]
        ):
            raise TrackingPreflightError("Resolved ntfy transport differs from preflight")
        acquired = self.records.begin_notification(event_id, now)
        attempt = acquired["record"]
        if not acquired["acquired"] and attempt["data"]["attemptState"] in {"in-flight", "recovery-required"}:
            return {"status": "recovery-required", "eventId": event_id, "recordId": attempt["id"]}
        if not acquired["acquired"] and attempt["data"]["attemptState"] == "terminal":
            return {"status": "already-recorded", "eventId": event_id, "record": attempt}
        state = self.records.store.load()
        event = next(item for item in state["attentionEvents"] if item["id"] == event_id)
        outcome = self.ntfy.publish(
            base_url=str(resolved["ntfyUrl"]),
            topic=str(resolved["ntfyTopic"]),
            allowed_hosts=set(config["ntfy"]["allowedHosts"]),
            title=f"Action needed for {event['issueId']}",
            message=event["summary"],
            click_url=event["link"],
            event_id=attempt["data"]["attemptId"],
            token=resolved["ntfyToken"],
        )
        if after_publish is not None:
            after_publish()
        record = self.records.finish_notification(attempt["id"], outcome, now)
        return {"status": outcome["status"], "eventId": event_id, "recordId": record["id"]}

    def migration_report(
        self, *, repository_key: str, generated_at: str,
        attestation: Mapping[str, Any], config: Mapping[str, Any],
        repository_id: str, supervisor_version: str,
    ) -> dict[str, Any]:
        verified = self._attest(
            attestation, config=config, repository_key=repository_key,
            repository_id=repository_id, supervisor_version=supervisor_version,
            now=generated_at,
        )
        observed = self._engine_operation(verified, "observe-issues")
        return build_migration_report(
            observed, repository_key=repository_key, generated_at=generated_at
        )

    def status(self, supervisor_status: Mapping[str, Any]) -> dict[str, Any]:
        projected = copy.deepcopy(dict(supervisor_status))
        projected["controlPlane"] = self.records.status()
        return projected
