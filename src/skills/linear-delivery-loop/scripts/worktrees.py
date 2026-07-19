"""Contained persistent issue worktrees and disposable exact-SHA gate worktrees."""

from __future__ import annotations

import copy
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from .base_runtime import load_base_runtime
from .store import SupervisorConflictError, SupervisorStore


WORKTREE_MANAGER_VERSION = "1.0"
ISSUE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,15}-[1-9][0-9]*$")
OPERATION_PATTERN = re.compile(
    r"^(?:[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}|"
    r"[a-z0-9][a-z0-9-]{0,62}[a-z0-9])$"
)
COMMIT_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,126}[A-Za-z0-9]$")


class WorktreeError(RuntimeError):
    """A worktree request could not be proven safe and exact."""


class _AllocationAmbiguous(WorktreeError):
    """Persisted allocation evidence cannot be reconciled automatically."""


def _normalized(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path)))).replace("\\", "/")


def _validate_ref(value: str, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not REF_PATTERN.fullmatch(value)
        or value.startswith("-")
        or ".." in value
        or "//" in value
        or "@{" in value
        or value.endswith(("/", ".", ".lock"))
    ):
        raise WorktreeError(f"{label} is not a safe fixed Git ref")
    return value


def _field(record: Mapping[str, Any], name: str, expected: Any) -> None:
    if record.get(name) != expected:
        raise WorktreeError(f"Worktree record {name} does not match the observed context")


class WorktreeManager:
    """Allocate and verify worktrees without accepting command fragments or cleanup paths."""

    def __init__(
        self,
        repository: str | Path,
        *,
        repository_key: str,
        state_home_override: str | Path | None = None,
        environment: Mapping[str, str] | None = None,
        store: SupervisorStore | None = None,
        allocation_fault_injector: Callable[[str, str], None] | None = None,
    ) -> None:
        runtime = load_base_runtime()
        self._runtime = runtime
        self.workflow_manager = runtime.WorkflowManager(
            repository,
            repository_key=repository_key,
            state_home_override=state_home_override,
            environment=dict(environment) if environment is not None else None,
        )
        self.identity = self.workflow_manager.identity
        self.repository = Path(self.identity.repository_root)
        self.state_root = self.workflow_manager.home.repository
        self.paths = self.workflow_manager.state_paths
        if store is not None:
            if store.manager.identity.repository_id != self.identity.repository_id:
                raise WorktreeError("Supervisor store belongs to a different repository")
            self.store = store
        else:
            self.store = SupervisorStore(self.workflow_manager, runtime=runtime)
        self.allocation_fault_injector = allocation_fault_injector
        self.issue_root = self.paths.directory(self.state_root / "worktrees", create=True)
        self.gate_root = self.paths.directory(
            self.state_root / "validation-worktrees", create=True
        )

    def _commit_state_unlocked(
        self,
        state: dict[str, Any],
        reservations: dict[str, Any],
        *,
        operation: str,
        mutate: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        after = copy.deepcopy(state)
        mutate(after)
        after["revision"] = state["revision"] + 1
        committed, _ = self.store.commit_pair_unlocked(
            before_state=state,
            after_state=after,
            before_reservations=reservations,
            after_reservations=reservations,
            operation=operation,
        )
        return committed

    @staticmethod
    def _issue_state_record(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "issueId": record["issueId"],
            "workflowId": record.get("workflowId"),
            "repositoryId": record["repositoryId"],
            "repositoryKey": record["repositoryKey"],
            "normalizedCommonDir": record["commonDir"],
            "worktreePath": record["path"],
            "physicalWorktreeFingerprint": record["physicalWorktreeFingerprint"],
            "branch": record["branch"],
            "headSha": record["headSha"],
            "handoffOperationId": record.get("handoffOperationId"),
            "status": "active",
        }

    def _allocation_fault(self, stage: str, allocation_id: str) -> None:
        if self.allocation_fault_injector is not None:
            self.allocation_fault_injector(stage, allocation_id)

    def _allocation_state_record(
        self,
        *,
        allocation_id: str,
        kind: str,
        subject_id: str,
        target: Path,
        branch: str | None,
        exact_sha: str,
    ) -> dict[str, Any]:
        return {
            "allocationId": allocation_id,
            "kind": kind,
            "subjectId": subject_id,
            "repositoryId": self.identity.repository_id,
            "repositoryKey": self.workflow_manager.repository_key,
            "normalizedCommonDir": _normalized(self.identity.common_dir),
            "worktreePath": _normalized(target),
            "branch": branch,
            "exactSha": exact_sha,
            "physicalWorktreeFingerprint": None,
            "handoffOperationId": None,
            "status": "prepared",
        }

    @staticmethod
    def _gate_state_record(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "operationId": record["operationId"],
            "worktreePath": record["path"],
            "physicalWorktreeFingerprint": record["physicalWorktreeFingerprint"],
            "exactSha": record["exactSha"],
            "status": "active",
            "operationStatus": "pending",
            "attestationStatus": "pending",
        }

    def _issue_public_record(
        self, record: Mapping[str, Any], observed: Mapping[str, Any]
    ) -> dict[str, Any]:
        return {
            "schemaVersion": WORKTREE_MANAGER_VERSION,
            "kind": "issue",
            "issueId": record["issueId"],
            "workflowId": record.get("workflowId"),
            "repositoryKey": record["repositoryKey"],
            "repositoryId": observed["repositoryId"],
            "commonDir": observed["commonDir"],
            "path": record["worktreePath"],
            "physicalWorktreeFingerprint": record["physicalWorktreeFingerprint"],
            "branch": record["branch"],
            "headSha": record["headSha"],
            "handoffOperationId": record.get("handoffOperationId"),
        }

    def _issue_target_from_mapping(
        self, issue_id: str, record: Mapping[str, Any]
    ) -> Path:
        operation_id = record.get("handoffOperationId")
        if operation_id is None:
            return self._direct_child(self.issue_root, issue_id, may_not_exist=False)
        try:
            if str(uuid.UUID(operation_id)) != operation_id:
                raise ValueError
        except (TypeError, ValueError, AttributeError) as exc:
            raise WorktreeError("Transferred issue mapping has an invalid Handoff identity") from exc
        raw_path = record.get("worktreePath")
        if not isinstance(raw_path, str):
            raise WorktreeError("Transferred issue mapping has no exact destination path")
        expected = self._direct_child(
            self.issue_root, Path(raw_path).name, may_not_exist=False
        )
        if _normalized(expected) != _normalized(raw_path):
            raise WorktreeError(
                "Transferred issue mapping is not a direct child of the issue-worktree root"
            )
        return expected

    def _validate_issue_allocation_mapping(
        self,
        state: Mapping[str, Any],
        issue_id: str,
        mapping: Mapping[str, Any],
    ) -> None:
        allocation_id = f"issue:{issue_id}"
        allocation = state.get("worktreeAllocations", {}).get(allocation_id)
        if not isinstance(allocation, dict):
            raise WorktreeError("Issue mapping lacks its authoritative allocation")
        self._validate_allocation_intent(allocation_id, allocation)
        operation_id = mapping.get("handoffOperationId")
        expected_status = "completed" if operation_id is None else "transferred"
        bindings = {
            "handoffOperationId": operation_id,
            "status": expected_status,
            "worktreePath": mapping.get("worktreePath"),
            "physicalWorktreeFingerprint": mapping.get(
                "physicalWorktreeFingerprint"
            ),
            "branch": mapping.get("branch"),
            "exactSha": mapping.get("headSha"),
        }
        if any(allocation.get(name) != value for name, value in bindings.items()):
            raise WorktreeError(
                "Issue mapping differs from its exact worktree allocation authority"
            )

    def _gate_public_record(
        self, record: Mapping[str, Any], observed: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "schemaVersion": WORKTREE_MANAGER_VERSION,
            "kind": "gate",
            "operationId": record["operationId"],
            "repositoryId": self.identity.repository_id,
            "commonDir": _normalized(self.identity.common_dir),
            "path": record["worktreePath"],
            "physicalWorktreeFingerprint": record["physicalWorktreeFingerprint"],
            "exactSha": record["exactSha"],
            "cleanBefore": True,
            "cleanAfter": record["status"] == "cleaned",
            "attestationStatus": record["attestationStatus"],
            "operationStatus": record["operationStatus"],
        }

    @staticmethod
    def _require_exact_public_record(
        supplied: Mapping[str, Any], authoritative: Mapping[str, Any], *, label: str
    ) -> None:
        for name in set(supplied) | set(authoritative):
            if supplied.get(name) != authoritative.get(name):
                raise WorktreeError(
                    f"Caller {label} record {name} differs from authoritative state"
                )

    @staticmethod
    def issue_branch(issue_id: str) -> str:
        issue_id = WorktreeManager._validate_issue_id(issue_id)
        return f"delivery/{issue_id.casefold()}"

    @staticmethod
    def _validate_issue_id(issue_id: str) -> str:
        if not isinstance(issue_id, str) or not ISSUE_PATTERN.fullmatch(issue_id):
            raise WorktreeError("issueId must be a canonical uppercase issue key")
        return issue_id

    @staticmethod
    def _validate_operation_id(operation_id: str) -> str:
        if not isinstance(operation_id, str) or not OPERATION_PATTERN.fullmatch(operation_id):
            raise WorktreeError("operationId must be an engine-generated canonical identifier")
        return operation_id

    def _direct_child(self, root: Path, name: str, *, may_not_exist: bool) -> Path:
        if not name or name in {".", ".."} or Path(name).name != name:
            raise WorktreeError("Worktree path component is not a direct child name")
        candidate = Path(os.path.abspath(root / name))
        if candidate.parent != root:
            raise WorktreeError("Worktree mapping must be a direct child of its authoritative root")
        if os.path.lexists(candidate) or not may_not_exist:
            try:
                return self.paths.directory(candidate)
            except Exception as exc:
                raise WorktreeError("Worktree path failed containment or reparse validation") from exc
        # The canonical root is already guarded; a strict single safe component cannot
        # escape it before Git creates the child. Readback revalidates the new directory.
        return candidate

    def _reject_case_alias(self, root: Path, expected_name: str) -> None:
        if not root.exists():
            return
        aliases = [
            child.name
            for child in root.iterdir()
            if child.name.casefold() == expected_name.casefold() and child.name != expected_name
        ]
        if aliases:
            raise WorktreeError("Case-insensitive worktree path collision requires reconciliation")

    def _git(
        self,
        repository: Path,
        arguments: list[str],
        *,
        allowed_returncodes: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "git",
            "--no-optional-locks",
            "-C",
            os.fspath(repository),
            *arguments,
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                shell=False,
            )
        except (OSError, UnicodeError) as exc:
            raise WorktreeError("Git worktree executable or UTF-8 output is unavailable") from exc
        if completed.returncode not in allowed_returncodes:
            raise WorktreeError("Fixed Git worktree command failed")
        return completed

    def _git_value(self, repository: Path, arguments: list[str]) -> str:
        value = self._git(repository, arguments).stdout.strip()
        if not value:
            raise WorktreeError("Fixed Git worktree observation returned no value")
        return value

    def _resolve_commit(self, repository: Path, ref: str) -> str:
        ref = _validate_ref(ref, label="Git ref")
        value = self._git_value(repository, ["rev-parse", "--verify", f"{ref}^{{commit}}"])
        if not COMMIT_PATTERN.fullmatch(value):
            raise WorktreeError("Git ref did not resolve to an exact commit object")
        return value

    def _observe(self, worktree: Path) -> dict[str, Any]:
        identity = self._runtime.observe_repository_identity(worktree)
        if identity.repository_id != self.identity.repository_id or _normalized(
            identity.common_dir
        ) != _normalized(self.identity.common_dir):
            raise WorktreeError("Worktree belongs to a different common Git repository")
        head = self._git_value(worktree, ["rev-parse", "HEAD"])
        if not COMMIT_PATTERN.fullmatch(head):
            raise WorktreeError("Worktree HEAD is not an exact commit")
        branch_result = self._git(
            worktree,
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
            allowed_returncodes=(0, 1),
        )
        branch = branch_result.stdout.strip() or None
        dirty = bool(self._git(worktree, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout)
        return {
            "repositoryId": identity.repository_id,
            "commonDir": _normalized(identity.common_dir),
            "path": _normalized(identity.repository_root),
            "physicalWorktreeFingerprint": identity.physical_worktree_fingerprint,
            "headSha": head,
            "branch": branch,
            "dirty": dirty,
        }

    def _validate_allocation_intent(
        self, allocation_id: str, record: Mapping[str, Any]
    ) -> tuple[Path, str]:
        required = {
            "allocationId",
            "kind",
            "subjectId",
            "repositoryId",
            "repositoryKey",
            "normalizedCommonDir",
            "worktreePath",
            "branch",
            "exactSha",
            "physicalWorktreeFingerprint",
            "handoffOperationId",
            "status",
        }
        if set(record) != required or record.get("allocationId") != allocation_id:
            raise _AllocationAmbiguous("Worktree allocation intent shape is invalid")
        kind = record.get("kind")
        subject_id = record.get("subjectId")
        if kind == "issue":
            self._validate_issue_id(subject_id)
            expected_id = f"issue:{subject_id}"
            root = self.issue_root
            operation_id = record.get("handoffOperationId")
            if operation_id is None:
                expected_branch = self.issue_branch(subject_id)
                if record.get("branch") != expected_branch:
                    raise _AllocationAmbiguous("Issue allocation branch binding is mismatched")
            else:
                try:
                    if str(uuid.UUID(operation_id)) != operation_id:
                        raise ValueError
                except (TypeError, ValueError, AttributeError) as exc:
                    raise _AllocationAmbiguous(
                        "Transferred allocation Handoff identity is invalid"
                    ) from exc
                try:
                    _validate_ref(record.get("branch"), label="Transferred issue branch")
                except WorktreeError as exc:
                    raise _AllocationAmbiguous(str(exc)) from exc
        elif kind == "gate":
            self._validate_operation_id(subject_id)
            expected_id = f"gate:{subject_id}"
            root = self.gate_root
            if record.get("branch") is not None:
                raise _AllocationAmbiguous("Gate allocation must remain detached")
        else:
            raise _AllocationAmbiguous("Worktree allocation kind is invalid")
        if allocation_id != expected_id:
            raise _AllocationAmbiguous("Worktree allocation identity is mismatched")
        exact_sha = record.get("exactSha")
        if not isinstance(exact_sha, str) or not COMMIT_PATTERN.fullmatch(exact_sha):
            raise _AllocationAmbiguous("Worktree allocation exact SHA is invalid")
        target_name = (
            subject_id
            if record.get("handoffOperationId") is None
            else Path(str(record.get("worktreePath", ""))).name
        )
        target = self._direct_child(
            root,
            target_name,
            may_not_exist=not os.path.lexists(root / target_name),
        )
        bindings = {
            "repositoryId": self.identity.repository_id,
            "repositoryKey": self.workflow_manager.repository_key,
            "normalizedCommonDir": _normalized(self.identity.common_dir),
            "worktreePath": _normalized(target),
        }
        if any(record.get(name) != value for name, value in bindings.items()):
            raise _AllocationAmbiguous("Worktree allocation repository/path binding is mismatched")
        status = record.get("status")
        fingerprint = record.get("physicalWorktreeFingerprint")
        if status not in {"prepared", "completed", "transferred", "ambiguous"}:
            raise _AllocationAmbiguous("Worktree allocation status is invalid")
        if status in {"completed", "transferred"} and not isinstance(fingerprint, str):
            raise _AllocationAmbiguous("Completed allocation lacks a physical-worktree binding")
        if status == "prepared" and fingerprint is not None:
            raise _AllocationAmbiguous("Prepared allocation cannot pre-claim a worktree fingerprint")
        if status == "transferred" and record.get("handoffOperationId") is None:
            raise _AllocationAmbiguous("Transferred allocation lacks its Handoff identity")
        if status != "transferred" and record.get("handoffOperationId") is not None:
            raise _AllocationAmbiguous("Initial allocation cannot claim Handoff transfer authority")
        return target, kind

    def _set_allocation_ambiguous_unlocked(
        self,
        allocation_id: str,
        state: dict[str, Any],
        reservations: dict[str, Any],
        *,
        reason: str,
    ) -> dict[str, Any]:
        after = copy.deepcopy(state)
        record = after["worktreeAllocations"].get(allocation_id)
        if isinstance(record, dict):
            record["status"] = "ambiguous"
        after["recovery"] = {
            "status": "ambiguous",
            "reason": f"worktree-allocation:{allocation_id}:{reason}"[:512],
            "updatedAtNs": 0,
        }
        after["revision"] = state["revision"] + 1
        committed, _ = self.store.commit_pair_unlocked(
            before_state=state,
            after_state=after,
            before_reservations=reservations,
            after_reservations=reservations,
            operation=f"WorktreeAllocation:{allocation_id}:ambiguous",
        )
        return committed

    def _reconcile_allocation_unlocked(
        self,
        allocation_id: str,
        state: dict[str, Any],
        reservations: dict[str, Any],
    ) -> dict[str, Any]:
        record = state["worktreeAllocations"].get(allocation_id)
        if not isinstance(record, dict):
            raise WorktreeError("Worktree allocation intent is absent")
        target, kind = self._validate_allocation_intent(allocation_id, record)
        if record["status"] == "ambiguous":
            raise _AllocationAmbiguous("Worktree allocation is already protected as ambiguous")

        subject_id = record["subjectId"]
        if not os.path.lexists(target):
            if record["status"] == "completed":
                raise _AllocationAmbiguous("Completed worktree allocation path is missing")
            resolved = self._git_value(
                self.repository,
                ["rev-parse", "--verify", f"{record['exactSha']}^{{commit}}"],
            )
            if resolved != record["exactSha"]:
                raise _AllocationAmbiguous("Allocation commit object no longer resolves exactly")
            if kind == "issue":
                branch = record["branch"]
                branch_exists = self._git(
                    self.repository,
                    ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                    allowed_returncodes=(0, 1),
                ).returncode == 0
                if branch_exists:
                    branch_sha = self._resolve_commit(self.repository, branch)
                    if branch_sha != record["exactSha"]:
                        raise _AllocationAmbiguous(
                            "Issue allocation branch advanced before worktree adoption"
                        )
                    arguments = ["worktree", "add", os.fspath(target), branch]
                else:
                    arguments = [
                        "worktree",
                        "add",
                        "-b",
                        branch,
                        os.fspath(target),
                        record["exactSha"],
                    ]
            else:
                arguments = [
                    "worktree",
                    "add",
                    "--detach",
                    os.fspath(target),
                    record["exactSha"],
                ]
            self._git(self.repository, arguments)
            self._allocation_fault("after-git", allocation_id)

        target = self._direct_child(
            self.issue_root if kind == "issue" else self.gate_root,
            subject_id,
            may_not_exist=False,
        )
        observed = self._observe(target)
        if (
            observed["path"] != record["worktreePath"]
            or observed["repositoryId"] != record["repositoryId"]
            or observed["commonDir"] != record["normalizedCommonDir"]
            or observed["headSha"] != record["exactSha"]
            or observed["dirty"]
            or (kind == "issue" and observed["branch"] != record["branch"])
            or (kind == "gate" and observed["branch"] is not None)
        ):
            raise _AllocationAmbiguous(
                "Worktree allocation Git evidence differs from the persisted intent"
            )

        after = copy.deepcopy(state)
        updated_intent = after["worktreeAllocations"][allocation_id]
        updated_intent["physicalWorktreeFingerprint"] = observed[
            "physicalWorktreeFingerprint"
        ]
        updated_intent["status"] = "completed"
        if kind == "issue":
            existing = after["issueWorktrees"].get(subject_id)
            public = {
                "schemaVersion": WORKTREE_MANAGER_VERSION,
                "kind": "issue",
                "issueId": subject_id,
                "workflowId": existing.get("workflowId") if isinstance(existing, dict) else None,
                "repositoryId": observed["repositoryId"],
                "repositoryKey": self.workflow_manager.repository_key,
                "commonDir": observed["commonDir"],
                "path": observed["path"],
                "physicalWorktreeFingerprint": observed["physicalWorktreeFingerprint"],
                "branch": record["branch"],
                "headSha": observed["headSha"],
            }
            state_record = self._issue_state_record(public)
            if existing is not None and existing != state_record:
                raise _AllocationAmbiguous(
                    "Issue mapping differs from the exact completed allocation"
                )
            after["issueWorktrees"][subject_id] = state_record
        else:
            public = {
                "schemaVersion": WORKTREE_MANAGER_VERSION,
                "kind": "gate",
                "operationId": subject_id,
                "repositoryId": observed["repositoryId"],
                "commonDir": observed["commonDir"],
                "path": observed["path"],
                "physicalWorktreeFingerprint": observed["physicalWorktreeFingerprint"],
                "exactSha": record["exactSha"],
                "cleanBefore": True,
                "cleanAfter": False,
                "attestationStatus": "pending",
                "operationStatus": "pending",
            }
            state_record = self._gate_state_record(public)
            existing = after["gateWorktrees"].get(subject_id)
            if existing is not None and existing != state_record:
                raise _AllocationAmbiguous(
                    "Gate mapping differs from the exact completed allocation"
                )
            after["gateWorktrees"][subject_id] = state_record
        if after != state:
            after["revision"] = state["revision"] + 1
            committed, _ = self.store.commit_pair_unlocked(
                before_state=state,
                after_state=after,
                before_reservations=reservations,
                after_reservations=reservations,
                operation=f"WorktreeAllocation:{allocation_id}:complete",
            )
            state = committed
        self._allocation_fault("after-state-commit", allocation_id)
        if kind == "issue":
            authoritative = state["issueWorktrees"][subject_id]
            return self._issue_public_record(authoritative, observed)
        return self._gate_public_record(state["gateWorktrees"][subject_id], observed)

    def reconcile_worktree_allocations(
        self, allocation_id: str | None = None
    ) -> dict[str, Any]:
        """Deterministically resume/adopt exact persisted allocation intents for Recover."""

        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            selected = (
                [allocation_id]
                if allocation_id is not None
                else sorted(
                    key
                    for key, value in state["worktreeAllocations"].items()
                    if value.get("status") == "prepared"
                )
            )
            recovered: list[dict[str, Any]] = []
            for selected_id in selected:
                if selected_id not in state["worktreeAllocations"]:
                    raise WorktreeError("Requested worktree allocation intent is absent")
                try:
                    recovered.append(
                        self._reconcile_allocation_unlocked(
                            selected_id, state, reservations
                        )
                    )
                    state, reservations = self.store.load_pair_unlocked()
                except _AllocationAmbiguous as exc:
                    state, reservations = self.store.load_pair_unlocked()
                    self._set_allocation_ambiguous_unlocked(
                        selected_id,
                        state,
                        reservations,
                        reason="evidence-mismatch",
                    )
                    return {
                        "schemaVersion": WORKTREE_MANAGER_VERSION,
                        "status": "protected",
                        "allocationId": selected_id,
                        "reason": str(exc),
                    }
            return {
                "schemaVersion": WORKTREE_MANAGER_VERSION,
                "status": "recovered" if recovered else "ready",
                "allocations": recovered,
            }

    def ensure_issue_worktree(
        self,
        issue_id: str,
        *,
        base_branch: str,
        existing_record: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create once or strictly validate an existing issue mapping."""

        issue_id = self._validate_issue_id(issue_id)
        base_branch = _validate_ref(base_branch, label="baseBranch")
        branch = self.issue_branch(issue_id)
        allocation_id = f"issue:{issue_id}"
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            authoritative = state["issueWorktrees"].get(issue_id)
            self._reject_case_alias(self.issue_root, issue_id)
            target = self._direct_child(self.issue_root, issue_id, may_not_exist=True)

            if isinstance(authoritative, dict) and authoritative.get("status") == "active":
                self._validate_issue_allocation_mapping(state, issue_id, authoritative)
                target = self._issue_target_from_mapping(issue_id, authoritative)
                if not os.path.lexists(target):
                    raise WorktreeError("Authoritative issue mapping points to a missing worktree")
                observed = self._observe(target)
                public = self._issue_public_record(authoritative, observed)
                if existing_record is not None:
                    self._require_exact_public_record(
                        existing_record, public, label="issue"
                    )
                return self._validate_issue_observation(
                    target,
                    authoritative,
                    observed,
                    control_worktree=self.repository,
                    require_clean=False,
                )
            if authoritative is not None:
                raise WorktreeError("Issue worktree mapping is not active")
            if allocation_id in state["worktreeAllocations"]:
                try:
                    return self._reconcile_allocation_unlocked(
                        allocation_id, state, reservations
                    )
                except _AllocationAmbiguous:
                    state, reservations = self.store.load_pair_unlocked()
                    self._set_allocation_ambiguous_unlocked(
                        allocation_id,
                        state,
                        reservations,
                        reason="evidence-mismatch",
                    )
                    raise
            if os.path.lexists(target):
                raise WorktreeError(
                    "Existing issue worktree lacks its authoritative allocation intent"
                )
            if existing_record is not None:
                raise WorktreeError("Authoritative issue mapping points to a missing worktree")

            base_sha = self._resolve_commit(self.repository, base_branch)
            branch_exists = self._git(
                self.repository,
                ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                allowed_returncodes=(0, 1),
            ).returncode == 0
            if branch_exists and self._resolve_commit(self.repository, branch) != base_sha:
                raise WorktreeError("Existing issue branch differs from the exact allocation base")
            intent = self._allocation_state_record(
                allocation_id=allocation_id,
                kind="issue",
                subject_id=issue_id,
                target=target,
                branch=branch,
                exact_sha=base_sha,
            )
            committed = self._commit_state_unlocked(
                state,
                reservations,
                operation=f"WorktreeAllocation:{allocation_id}:prepare",
                mutate=lambda after: after["worktreeAllocations"].__setitem__(
                    allocation_id, intent
                ),
            )
            self._allocation_fault("after-intent", allocation_id)
            return self._reconcile_allocation_unlocked(
                allocation_id, committed, reservations
            )

    def validate_issue_worktree(
        self,
        candidate: str | Path,
        record: Mapping[str, Any],
        *,
        control_worktree: str | Path,
        require_clean: bool = True,
    ) -> dict[str, Any]:
        issue_id = self._validate_issue_id(record.get("issueId"))
        with self.store.mutex():
            state, _ = self.store.load_pair_unlocked()
            authoritative = state["issueWorktrees"].get(issue_id)
            if not isinstance(authoritative, dict) or authoritative.get("status") != "active":
                raise WorktreeError("Issue worktree is not active in authoritative state")
            self._validate_issue_allocation_mapping(state, issue_id, authoritative)
            expected = self._issue_target_from_mapping(issue_id, authoritative)
            observed = self._observe(expected)
            public = self._issue_public_record(authoritative, observed)
            self._require_exact_public_record(record, public, label="issue")
            return self._validate_issue_observation(
                candidate,
                authoritative,
                observed,
                control_worktree=control_worktree,
                require_clean=require_clean,
            )

    def _validate_issue_observation(
        self,
        candidate: str | Path,
        record: Mapping[str, Any],
        observed: Mapping[str, Any],
        *,
        control_worktree: str | Path,
        require_clean: bool,
    ) -> dict[str, Any]:
        issue_id = self._validate_issue_id(record.get("issueId"))
        expected = self._issue_target_from_mapping(issue_id, record)
        if _normalized(candidate) != _normalized(expected):
            raise WorktreeError("Candidate is not the registered persistent issue worktree")
        if _normalized(candidate) == _normalized(control_worktree):
            raise WorktreeError("Scheduled control worktree cannot authorize implementation")
        expected_branch = (
            self.issue_branch(issue_id)
            if record.get("handoffOperationId") is None
            else record.get("branch")
        )
        for name, value in {
            "repositoryId": self.identity.repository_id,
            "repositoryKey": self.workflow_manager.repository_key,
            "normalizedCommonDir": observed["commonDir"],
            "worktreePath": _normalized(expected),
            "physicalWorktreeFingerprint": observed["physicalWorktreeFingerprint"],
            "branch": expected_branch,
            "headSha": observed["headSha"],
            "status": "active",
        }.items():
            _field(record, name, value)
        if observed["branch"] != expected_branch:
            raise WorktreeError("Issue worktree branch differs from its canonical mapping")
        if require_clean and observed["dirty"]:
            raise WorktreeError("Issue worktree contains unexpected dirty state")
        return self._issue_public_record(record, observed)

    def create_gate_worktree(self, operation_id: str, *, exact_sha: str) -> dict[str, Any]:
        operation_id = self._validate_operation_id(operation_id)
        if not isinstance(exact_sha, str) or not COMMIT_PATTERN.fullmatch(exact_sha):
            raise WorktreeError("Gate exactSha must be a full lowercase commit object ID")
        allocation_id = f"gate:{operation_id}"
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            authoritative = state["gateWorktrees"].get(operation_id)
            if isinstance(authoritative, dict) and authoritative.get("status") == "active":
                if authoritative.get("exactSha") != exact_sha:
                    raise WorktreeError("Gate operation replay changed its exact SHA")
                return self._validate_gate_observation(authoritative)
            if authoritative is not None:
                raise WorktreeError("Gate operation is not in an allocatable active state")
            self._reject_case_alias(self.gate_root, operation_id)
            target = self._direct_child(self.gate_root, operation_id, may_not_exist=True)
            if allocation_id in state["worktreeAllocations"]:
                intent = state["worktreeAllocations"][allocation_id]
                if intent.get("exactSha") != exact_sha:
                    raise WorktreeError("Gate allocation replay changed its exact SHA")
                try:
                    return self._reconcile_allocation_unlocked(
                        allocation_id, state, reservations
                    )
                except _AllocationAmbiguous:
                    state, reservations = self.store.load_pair_unlocked()
                    self._set_allocation_ambiguous_unlocked(
                        allocation_id,
                        state,
                        reservations,
                        reason="evidence-mismatch",
                    )
                    raise
            if os.path.lexists(target):
                raise WorktreeError("Gate worktree path lacks an authoritative allocation intent")
            resolved = self._git_value(
                self.repository, ["rev-parse", "--verify", f"{exact_sha}^{{commit}}"]
            )
            if resolved != exact_sha:
                raise WorktreeError("Gate exactSha does not identify the requested commit exactly")
            intent = self._allocation_state_record(
                allocation_id=allocation_id,
                kind="gate",
                subject_id=operation_id,
                target=target,
                branch=None,
                exact_sha=exact_sha,
            )
            committed = self._commit_state_unlocked(
                state,
                reservations,
                operation=f"WorktreeAllocation:{allocation_id}:prepare",
                mutate=lambda after: after["worktreeAllocations"].__setitem__(
                    allocation_id, intent
                ),
            )
            self._allocation_fault("after-intent", allocation_id)
            return self._reconcile_allocation_unlocked(
                allocation_id, committed, reservations
            )

    def validate_gate_worktree(self, record: Mapping[str, Any]) -> dict[str, Any]:
        operation_id = self._validate_operation_id(record.get("operationId"))
        with self.store.mutex():
            state, _ = self.store.load_pair_unlocked()
            authoritative = state["gateWorktrees"].get(operation_id)
            if not isinstance(authoritative, dict) or authoritative["status"] not in {
                "active",
                "cleanup-pending",
            }:
                raise WorktreeError("Gate worktree is not active in authoritative state")
            public = self._gate_public_record(authoritative)
            self._require_exact_public_record(record, public, label="gate")
            return self._validate_gate_observation(authoritative)

    def _validate_gate_observation(self, record: Mapping[str, Any]) -> dict[str, Any]:
        operation_id = self._validate_operation_id(record.get("operationId"))
        exact_sha = record.get("exactSha")
        if not isinstance(exact_sha, str) or not COMMIT_PATTERN.fullmatch(exact_sha):
            raise WorktreeError("Gate record contains an invalid exactSha")
        expected = self._direct_child(self.gate_root, operation_id, may_not_exist=False)
        observed = self._observe(expected)
        for name, value in {
            "worktreePath": _normalized(expected),
            "physicalWorktreeFingerprint": observed["physicalWorktreeFingerprint"],
            "exactSha": observed["headSha"],
        }.items():
            _field(record, name, value)
        if observed["branch"] is not None or observed["dirty"]:
            raise WorktreeError("Gate worktree is not detached and clean")
        return self._gate_public_record(record, observed)

    def set_gate_evidence(
        self,
        operation_id: str,
        *,
        expected_state_revision: int,
        operation_status: str,
        attestation_status: str,
    ) -> dict[str, Any]:
        """Record engine-observed gate results in the authoritative state document."""

        operation_id = self._validate_operation_id(operation_id)
        if operation_status not in {"resolved", "failed", "ambiguous"}:
            raise WorktreeError("Gate operation status is invalid")
        if attestation_status not in {"complete", "failed"}:
            raise WorktreeError("Gate attestation status is invalid")
        with self.store.mutex():
            state, reservations = self.store.load_pair_unlocked()
            if state["revision"] != expected_state_revision:
                raise SupervisorConflictError("Gate evidence state revision is stale")
            record = state["gateWorktrees"].get(operation_id)
            if not isinstance(record, dict) or record.get("status") != "active":
                raise WorktreeError("Gate evidence has no active authoritative mapping")
            self._validate_gate_observation(record)

            def mutate(after: dict[str, Any]) -> None:
                updated = after["gateWorktrees"][operation_id]
                updated["operationStatus"] = operation_status
                updated["attestationStatus"] = attestation_status

            committed = self._commit_state_unlocked(
                state,
                reservations,
                operation=f"GateEvidence:{operation_id}",
                mutate=mutate,
            )
            return self._gate_public_record(committed["gateWorktrees"][operation_id])

    def _cleanup_gate_worktree_authorized(
        self,
        operation_id: str,
        *,
        mutable_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Remove one authoritative contained gate inside an authorized mutex callback."""

        operation_id = self._validate_operation_id(operation_id)
        record = mutable_state.get("gateWorktrees", {}).get(operation_id)
        if not isinstance(record, dict) or record.get("status") != "active":
            raise WorktreeError("Gate cleanup has no active authoritative mapping")
        if record.get("operationStatus") != "resolved":
            raise WorktreeError("Gate cleanup record does not prove a resolved operation")
        if record.get("attestationStatus") != "complete":
            raise WorktreeError("Gate cleanup refuses incomplete attestation evidence")
        self._validate_gate_observation(record)
        target = self._direct_child(
            self.gate_root, operation_id, may_not_exist=False
        )
        record["status"] = "cleanup-pending"
        self._git(self.repository, ["worktree", "remove", os.fspath(target)])
        if os.path.lexists(target):
            raise WorktreeError("Git gate cleanup did not remove the contained worktree")
        record["status"] = "cleaned"
        return self._gate_public_record(record)
