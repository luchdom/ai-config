from __future__ import annotations

import importlib
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from tests.linear_delivery_supervisor.support_state_engine import clean_observer, git, package


cli = importlib.import_module(package.__name__ + ".cli")
control_plane = importlib.import_module(package.__name__ + ".control_plane_records")
publication_git_module = importlib.import_module(package.__name__ + ".publication_git")
publication_recovery_module = importlib.import_module(package.__name__ + ".publication_recovery")
supervisor = importlib.import_module(package.__name__ + ".supervisor")
lease_module = importlib.import_module(package.__name__ + ".lease")


NOW = "2026-07-23T00:00:00Z"


class FixtureProvider:
    """Closed in-process provider with explicit non-application scripts."""

    def __init__(self, scenario: "PublicPublicationScenario") -> None:
        self.scenario = scenario
        self.remote_refs: dict[str, dict] = {}
        self.pull_requests: dict[tuple[str, str], dict] = {}
        self.merges: dict[str, dict] = {}
        self.refusals: dict[str, list[dict]] = {name: [] for name in ("push", "pull-request", "squash-merge")}
        self.calls: list[tuple[str, str]] = []
        self.crash_operation: str | None = None
        self.crash_after_apply_operation: str | None = None

    def refuse(self, operation: str, *responses: dict) -> None:
        self.refusals[operation].extend(dict(item) for item in responses)

    def _response(self, operation: str, operation_id: str) -> dict | None:
        self.calls.append((operation, operation_id))
        if self.crash_operation == operation:
            self.crash_operation = None
            raise RuntimeError("fixture crash after durable reply consumption")
        return self.refusals[operation].pop(0) if self.refusals[operation] else None

    def read_remote_ref(self, branch: str):
        return self.remote_refs.get(branch)

    def push_ref(self, request: dict):
        refused = self._response("push", request["operationId"])
        if refused is not None:
            return refused
        self.remote_refs[request["branch"]] = {"headSha": request["headSha"]}
        for (branch, _base), pull_request in self.pull_requests.items():
            if branch == request["branch"]:
                pull_request["headSha"] = request["headSha"]
        if self.crash_after_apply_operation == "push":
            self.crash_after_apply_operation = None
            raise RuntimeError("fixture crash after applied push")
        return {"statusCode": 200}

    def read_pull_request(self, branch: str, base_ref: str):
        return self.pull_requests.get((branch, base_ref))

    def create_or_reuse_pull_request(self, request: dict):
        refused = self._response("pull-request", request["operationId"])
        if refused is not None:
            return refused
        value = {"id": f"pr-{len(self.pull_requests) + 1}", "headSha": request["headSha"], "baseRef": request["baseRef"]}
        self.pull_requests[(request["branch"], request["baseRef"])] = value
        if self.crash_after_apply_operation == "pull-request":
            self.crash_after_apply_operation = None
            raise RuntimeError("fixture crash after applied pull request")
        return value

    def read_merge(self, pull_request_id: str):
        return self.merges.get(pull_request_id, {"merged": False})

    def squash_merge(self, request: dict):
        refused = self._response("squash-merge", request["operationId"])
        if refused is not None:
            return refused
        merge_sha = self.scenario.real_commit(f"merge {request['operationId']}")
        self.merges[request["pullRequestId"]] = {"merged": True, "mergeSha": merge_sha}
        git(self.scenario.repository, "update-ref", "refs/heads/main", merge_sha)
        if self.crash_after_apply_operation == "squash-merge":
            self.crash_after_apply_operation = None
            raise RuntimeError("fixture crash after applied merge")
        return {"mergeSha": merge_sha}

    def read_publication_authority(self, issue_id: str, branch: str, base_ref: str):
        pr = self.pull_requests.get((branch, base_ref))
        remote = self.remote_refs.get(branch)
        provider_head = (pr or remote or {}).get("headSha")
        if provider_head is None:
            provider_head = git(self.scenario.repository, "rev-parse", "main").stdout.strip()
        return {
            "issueId": issue_id,
            "labels": sorted(self.scenario.labels),
            "pullRequestId": pr["id"] if pr else None,
            "baseRef": base_ref,
            "baseSha": git(self.scenario.repository, "rev-parse", "main").stdout.strip(),
            "headSha": provider_head,
            "mergeability": True,
        }


class PublicPublicationScenario:
    """Reusable fixture assembly whose commands all cross ``cli.run_request``."""

    def __init__(self, case, *, finalize: bool = True, prepare: bool = True,
        git_fault_injector=None) -> None:
        self.case = case
        record = case.use_authoritative_issue_worktree("SAAS-48")
        self.repository: Path = case.repository
        self.control_repository: Path = case.control_repository
        self.manager = case.manager
        self.fingerprint = record["physicalWorktreeFingerprint"]
        self.workflow_id = case.descriptor["workflowId"]
        self.operation_id = str(uuid.uuid4())
        self.owner = "owner"
        self.labels = {"autonomous"}
        self.issue_states: list[str] = []
        self.notifications: list[dict] = []
        self.lease_releases = 0
        self.gate_failures = 0
        self.clock = lease_module.ManualClock(time.time_ns())
        self.provider = FixtureProvider(self)
        self.requests = control_plane.ControlPlaneRecords(
            control_plane.ControlPlaneStore(case.root / "publication-control", fixture_mode=True)
        )
        self.recovery = publication_recovery_module.PublicationRecovery(
            requests=self.requests,
            release_lease=lambda: setattr(self, "lease_releases", self.lease_releases + 1),
            set_labels=self._set_labels,
            set_issue_state=self.issue_states.append,
            notify=lambda value: self.notifications.append(dict(value)),
        )
        self.git_boundary = publication_git_module.PublicationGit(
            self.repository, expected_repository=self.repository,
            aggregate_runner=lambda _path: {"exitCode": 0},
            fault_injector=git_fault_injector,
        )
        cli.register_fixture_assembly(
            self.manager.home.repository,
            cli.FixtureAssembly(
                publication_provider=self.provider,
                publication_recovery=self.recovery,
                publication_git=self.git_boundary,
                publication_gate_runner=self._gate_runner,
                clock=self.clock, reservation_clock=self.clock.now_ns,
            ),
        )
        case.addCleanup(cli.unregister_fixture_assembly, self.manager.home.repository)
        self.run_id = str(uuid.uuid4())
        self.lease = self.command("AcquireLease", {"requestId": self.run_id, "ownerId": self.owner})
        self.prepared = self.command("PrepareIteration", {
            "runId": self.run_id, "issueId": "SAAS-48", "workflowId": self.workflow_id,
            "worktreePath": str(self.repository), "leaseCapabilityRef": self.lease["capabilityRef"],
            "expectedStage": "review",
        })
        self.sources: dict[tuple[int, str], str] = {}
        self._evidence_suffix = ""
        self.reservation = self.command("Reserve", {
            "workflowId": self.workflow_id, "issueId": "SAAS-48", "worktreePath": str(self.repository),
            "policy": "autonomous", "ownerId": self.owner, "runId": self.run_id,
            "autonomousCapabilityRef": self.prepared["capabilityRef"],
        })
        root = "docs-ai/005-saas-48-deterministic-publication-and-exact-sha"
        self.draft_paths = {
            "plan": f"{root}/2026-07-23-saas-48-plan.md", "tasks": f"{root}/2026-07-23-saas-48-tasks.md",
            "audit": f"{root}/2026-07-23-saas-48-audit.md",
            "review": f"{root}/2026-07-23-saas-48-code-review.md",
            "qa": f"{root}/2026-07-23-saas-48-qa.md",
            "completion": f"{root}/2026-07-23-saas-48-completion.md",
        }
        self.evidence_path = self.draft_paths["review"]
        for kind, path in self.draft_paths.items():
            target = self.repository / path; target.parent.mkdir(parents=True, exist_ok=True)
            role = {"review": "code-review", "qa": "qa", "completion": "completion"}.get(kind)
            content = (f"# {kind.title()}\nEvidence-Role: {role}\nEvidence-State: draft\nExact-SHA: " + "0" * 40 + "\n") if role else f"# {kind.title()}\n\nDraft evidence.\n"
            target.write_text(content, encoding="utf-8")
        self.head = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        if prepare:
            self.prepare_publication()
            self.refresh_publication_capability("review")
        self.auto_finalize = finalize

    def _set_labels(self, labels: set[str]) -> None:
        self.labels = set(labels)

    def _gate_runner(self, *args, **kwargs):
        if self.gate_failures:
            self.gate_failures -= 1
            return SimpleNamespace(returncode=1, stdout="", stderr="fixture failure")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    @property
    def engine(self):
        return supervisor.SupervisorEngine(
            manager=self.manager, publication_provider=self.provider,
            publication_recovery=self.recovery, publication_git=self.git_boundary,
            publication_gate_runner=self._gate_runner, local_observer=clean_observer,
            clock=self.clock, reservation_clock=self.clock.now_ns,
        )

    def state(self):
        return self.engine.store.load_state()

    def publication(self):
        state = self.state()
        if state.get("publication") is None:
            return None
        return self.engine.publication_operations.load(self.operation_id)

    def real_commit(self, message: str) -> str:
        parent = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        tree = git(self.repository, "rev-parse", f"{parent}^{{tree}}").stdout.strip()
        return git(self.repository, "commit-tree", tree, "-p", parent, "-m", message).stdout.strip()

    def command(self, operation: str, fields: dict, *, requested_at: str = NOW):
        state = self.engine.store.load_state()
        reservations = self.engine.store.load_reservations()
        value = {
            "schemaVersion": "1.0", "operation": operation,
            "requestId": fields.get("requestId", str(uuid.uuid4())),
            "repositoryKey": self.manager.repository_key,
            "repositoryRoot": str(self.control_repository.resolve()),
            "stateHome": str(self.manager.home.repository), "requestedAt": requested_at,
            "expectedStateRevision": state["revision"], **fields,
        }
        if operation in {
            "Reserve", "RenewReservation", "AuthorizeMutation", "Release", "Cleanup",
            "PreparePublication", "PublicationProvider", "PublicationGate",
            "RecordPublicationAttestation", "PublicationRepair", "RecoverPublication",
        }:
            value.setdefault("expectedReservationsRevision", reservations["revision"])
        path = self.manager.home.repository / f"public-{operation}-{value['requestId']}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        self.last_command_path = path.resolve()
        return cli.run_request(path.resolve())

    def authorize(self, mutation_id: str, kind: str) -> dict:
        reservations = self.engine.store.load_reservations()
        record = reservations["reservations"][self.reservation["reservationId"]]
        return self.command("AuthorizeMutation", {
            "requestId": mutation_id, "reservationId": record["reservationId"],
            "workflowId": self.workflow_id, "targetOperationId": mutation_id,
            "operationScope": [f"publication/{self.operation_id}/{kind}/{mutation_id}.json"],
            "reservationControlRef": record["releaseAuthorizationRef"],
            "autonomousCapabilityRef": self.prepared["capabilityRef"],
            "expectedReservationRevision": record["revision"],
        })

    def mutation(self, operation: str, fields: dict, kind: str, *, mutation_id: str | None = None, requested_at: str = NOW):
        mutation_id = mutation_id or str(uuid.uuid4())
        grant = self.authorize(mutation_id, kind)
        return self.command(operation, {
            "reservationId": self.reservation["reservationId"],
            "authorizationRef": grant["authorizationRef"],
            "expectedRecordRevision": grant["reservationRevision"],
            "physicalWorktreeFingerprint": self.fingerprint,
            **fields,
        }, requested_at=requested_at)

    def _advance_checkpoint(self, stage: str, next_stage: str, kind: str, attempt: int) -> str:
        transition_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        observed_head = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        worker = {
            "schemaVersion": "1.0", "preparedIterationId": self.prepared["preparedIterationId"],
            "runId": self.run_id, "workflowId": self.workflow_id, "issueId": "SAAS-48",
            "transitionId": transition_id, "outcome": "completed" if next_stage == "completion" else "advanced",
            "completedStage": stage, "proposedNextStage": next_stage, "artifactManifest": [],
            "changedPaths": self.engine.leases._observe_worktree(self.repository)["changedPaths"],
            "summary": f"{kind} passed", "proposedExternalTransitions": [], "pause": None,
            "observed": {"repositoryId": self.manager.identity.repository_id,
                "physicalWorktreeFingerprint": self.fingerprint, "headSha": observed_head},
        }
        worker_path = self.manager.home.repository / f"worker-{source_id}.json"
        worker_path.write_text(json.dumps(worker), encoding="utf-8")
        prepared_ref = self.engine.store.directories["runs"] / self.run_id / f"{self.prepared['preparedIterationId']}.prepared-iteration.json"
        self.command("ApplyCheckpoint", {
            "requestId": source_id, "runId": self.run_id, "preparedIterationRef": str(prepared_ref),
            "workerResultPath": str(worker_path), "transitionId": transition_id, "expectedStage": stage,
        })
        self.sources[(attempt, kind)] = source_id
        if next_stage != "completion":
            self.prepared = self.command("PrepareIteration", {
                "runId": self.run_id, "issueId": "SAAS-48", "workflowId": self.workflow_id,
                "worktreePath": str(self.repository), "leaseCapabilityRef": self.lease["capabilityRef"],
                "expectedStage": next_stage,
            })
        return source_id

    def prepare_publication(self) -> None:
        base_sha = git(self.repository, "rev-parse", "main").stdout.strip()
        value = {
            "schemaVersion": "1.0", "repositoryId": self.manager.identity.repository_id,
            "repositoryKey": self.manager.repository_key, "workflowId": self.workflow_id,
            "issueId": "SAAS-48", "operationId": self.operation_id, "idempotencyKey": self.operation_id,
            "operation": "push", "status": "prepared", "branch": "codex/SAAS-48-publication",
            "baseRef": "main", "baseSha": base_sha, "headSha": self.head, "mergeSha": None, "pullRequest": None,
            "attemptCount": 0, "retryCount": 0, "nextRetryAt": None, "refusalKind": None,
            "providerEvidenceRef": None,
            "preservedState": {"issueState": "In Progress", "autonomous": True, "globalWip": True,
                "reservationId": self.reservation["reservationId"], "worktreePath": str(self.repository.resolve()),
                "physicalWorktreeFingerprint": self.fingerprint, "branch": "codex/SAAS-48-publication",
                "pullRequest": None, "evidenceRefs": []},
            "attestations": {}, "providerOperationIds": {"push": None, "pull-request": None, "squash-merge": None},
            "evidenceFinalizationCount": 0, "repairAttempt": 0, "activeProviderOperation": None,
            "authorityReadback": None, "preparation": None, "evidenceFinalization": None, "consumedReplyId": None,
            "createdAt": NOW, "updatedAt": NOW,
        }
        ref = self.manager.home.repository / f"publication-{self.operation_id}.json"
        ref.write_text(json.dumps(value), encoding="utf-8")
        self.mutation("PreparePublication", {
            "publicationStateRef": str(ref), "preparationOperationId": self.operation_id,
            "artifactManifest": sorted(self.draft_paths.values()),
            "preexistingPaths": [],
        }, "prepare", mutation_id=self.operation_id)
        self.head = self.publication()["headSha"]

    def reprepare_after_base_drift(self) -> None:
        self._evidence_suffix = "Base-drift revalidation.\n"
        evidence_paths = [self.draft_paths[name] for name in ("review", "qa", "completion")]
        git(self.repository, "update-index", "--no-assume-unchanged", "--", *evidence_paths)
        git(self.repository, "update-index", "--no-skip-worktree", "--", *evidence_paths)
        for kind, role in (("review", "code-review"), ("qa", "qa"), ("completion", "completion")):
            (self.repository / self.draft_paths[kind]).write_text(
                f"# {kind.title()}\nEvidence-Role: {role}\nEvidence-State: draft\nExact-SHA: {self.head}\n{self._evidence_suffix}",
                encoding="utf-8",
            )
        observed, conflicted = publication_git_module._status_paths(self.repository)
        self.case.assertFalse(conflicted)
        expected = {self.draft_paths[name] for name in ("review", "qa", "completion")}
        self.case.assertTrue(expected.issubset(set(observed)))
        manifest = sorted(expected)
        preexisting = sorted(set(observed) - set(manifest))
        identity = str(uuid.uuid4())
        ref = self.manager.home.repository / f"publication-{self.operation_id}.json"
        self.mutation("PreparePublication", {
            "publicationStateRef": str(ref), "preparationOperationId": identity,
            "artifactManifest": manifest,
            "preexistingPaths": preexisting,
        }, "prepare", mutation_id=identity)
        self.head = self.publication()["headSha"]
        for key in [key for key in self.sources if key[0] == 0]: self.sources.pop(key)

    def _write_final_evidence(self) -> None:
        for kind, role in (("review", "code-review"), ("qa", "qa"), ("completion", "completion")):
            (self.repository / self.draft_paths[kind]).write_text(
                f"# {kind.title()}\nEvidence-Role: {role}\nEvidence-State: pass\nExact-SHA: {self.head}\n{self._evidence_suffix}",
                encoding="utf-8",
            )

    def draft_inventory(self) -> dict:
        value = {}
        for kind, path in self.draft_paths.items():
            content = self.git_boundary.read_head_bytes(path)
            value[kind] = {"status": "draft", "path": path,
                "digest": "sha256:" + hashlib.sha256(content).hexdigest()}
        value["design"] = {"status": "not-required", "reason": "no-product-ui"}
        return value

    def finalize_evidence(self) -> None:
        identity = str(uuid.uuid4())
        self.mutation("RecordPublicationAttestation", {
            "publicationOperationId": self.operation_id, "attestationId": identity,
            "sourceOperationId": identity, "evidencePaths": [self.draft_paths[name] for name in ("review", "qa", "completion")],
            "draftInventory": self._draft_inventory, "designRequired": False,
        }, "finalize-evidence", mutation_id=identity)
        self.head = self.publication()["headSha"]

    def provider_operation(self, name: str, *, operation_id: str | None = None):
        identity = operation_id or str(uuid.uuid4())
        return self.mutation("PublicationProvider", {
            "publicationOperationId": self.operation_id, "providerOperation": name,
            "providerOperationId": identity,
        }, f"provider-{name}", mutation_id=identity)

    def recover(self, *, requested_at: str, attended: dict | None = None):
        identity = str(uuid.uuid4())
        return self.mutation("RecoverPublication", {
            "publicationOperationId": self.operation_id, "recoveryOperationId": identity,
            **({"attended": attended} if attended is not None else {}),
        }, f"provider-{self.publication()['activeProviderOperation']}", mutation_id=identity, requested_at=requested_at)

    def gate(self, kind: str, exact_sha: str):
        identity = str(uuid.uuid4())
        return self.mutation("PublicationGate", {
            "publicationOperationId": self.operation_id, "gateOperationId": identity,
            "exactSha": exact_sha, "gateKind": kind,
            "startedAt": NOW, "completedAt": "2026-07-23T00:01:00Z",
        }, f"gate-{kind}", mutation_id=identity)

    def attest(self, kind: str, attempt: int):
        identity = str(uuid.uuid4())
        return self.mutation("RecordPublicationAttestation", {
            "publicationOperationId": self.operation_id, "attestationId": identity,
            "sourceOperationId": self.sources[(attempt, kind)],
        }, "evidence", mutation_id=identity)

    def repair(self, current_main: str, artifact_manifest: list[str] | None = None):
        identity = str(uuid.uuid4())
        fields = {"publicationOperationId": self.operation_id, "repairOperationId": identity,
            "currentMainSha": current_main}
        if artifact_manifest is not None:
            fields["artifactManifest"] = artifact_manifest
            fields["preexistingPaths"] = []
        return self.mutation("PublicationRepair", fields, "repair", mutation_id=identity)

    def request_record(self) -> dict:
        records = self.requests.store.load()["publicationRequests"]
        return records[-1]

    def attended(self, *, body: str, reply_id: str | None = None, actor: str = "owner") -> dict:
        request = self.request_record()
        return {
            "request_id": request["id"], "actor_id": actor,
            "reply_id": reply_id or str(uuid.uuid4()), "reply_created_at": "2026-07-23T00:02:00Z",
            "body": body, "owner_id": "owner", "config_digest": "sha256:" + "0" * 64,
            "repository_id": self.manager.identity.repository_id,
        }

    def prepare_cycle_evidence(self, attempt: int) -> None:
        self._advance_checkpoint("publication", "completion", "evidence-convergence", attempt)

    def prepare_repair_specialists(self, attempt: int) -> None:
        self.prepared = self.command("PrepareIteration", {
            "runId": self.run_id, "issueId": "SAAS-48", "workflowId": self.workflow_id,
            "worktreePath": str(self.repository), "leaseCapabilityRef": self.lease["capabilityRef"],
            "expectedStage": "review",
        })
        self._advance_checkpoint("review", "qa", "review", attempt)
        self._advance_checkpoint("qa", "docs", "qa", attempt)
        self._advance_checkpoint("docs", "publication", "docs", attempt)

    def refresh_publication_capability(self, stage: str = "publication") -> None:
        self.prepared = self.command("PrepareIteration", {
            "runId": self.run_id, "issueId": "SAAS-48", "workflowId": self.workflow_id,
            "worktreePath": str(self.repository), "leaseCapabilityRef": self.lease["capabilityRef"],
            "expectedStage": stage,
        })

    def run_premerge(self, attempt: int) -> None:
        status = self.publication()["status"]
        if status == "prepared":
            self.provider_operation("push")
            stage = (self.state().get("currentWork") or {})["stage"]
            if stage != "completion": self.refresh_publication_capability(stage)
        if self.publication()["status"] == "pushed":
            self.provider_operation("pull-request")
            stage = (self.state().get("currentWork") or {})["stage"]
            if stage != "completion": self.refresh_publication_capability(stage)
        if self.publication()["evidenceFinalization"] is None:
            self._draft_inventory = self.draft_inventory()
            self._write_final_evidence(); self.finalize_evidence()
            current_stage = (self.state().get("currentWork") or {})["stage"]
            if current_stage != "completion": self.refresh_publication_capability(current_stage)
        if self.publication()["status"] == "prepared":
            self.provider_operation("push")
            current_stage = (self.state().get("currentWork") or {})["stage"]
            if current_stage != "completion": self.refresh_publication_capability(current_stage)
        if self.publication()["status"] == "pushed":
            self.provider_operation("pull-request")
            current_stage = (self.state().get("currentWork") or {})["stage"]
            if current_stage != "completion": self.refresh_publication_capability(current_stage)
        if (attempt, "review") not in self.sources:
            if attempt or (self.state().get("currentWork") or {}).get("stage") == "completion": self.prepare_repair_specialists(attempt)
            else:
                self._advance_checkpoint("review", "qa", "review", 0)
                self._advance_checkpoint("qa", "docs", "qa", 0)
                self._advance_checkpoint("docs", "publication", "docs", 0)
        self.gate("pre-staging-aggregate", self.head)
        self.gate("exact-head-aggregate", self.head)
        for kind in ("review", "qa", "docs"):
            self.attest(kind, attempt)
        self.prepare_cycle_evidence(attempt)
        self.attest("evidence-convergence", attempt)

    def merge_and_fail_exact_gate(self) -> str:
        self.provider_operation("squash-merge")
        merge_sha = self.publication()["mergeSha"]
        self.gate_failures = 1
        try:
            self.gate("exact-merge-aggregate", merge_sha)
        except Exception:
            if self.publication()["status"] != "post-merge-validating":
                raise
        return merge_sha

    def begin_repair(self, current_main: str) -> str:
        result = self.repair(current_main)
        if result["status"] != "repairing":
            return current_main
        for kind, role in (("review", "code-review"), ("qa", "qa"), ("completion", "completion")):
            (self.repository / self.draft_paths[kind]).write_text(
                f"# {kind.title()}\nEvidence-Role: {role}\nEvidence-State: draft\nExact-SHA: {self.head}\n",
                encoding="utf-8",
            )
        prepared = self.repair(current_main, [self.draft_paths[name] for name in ("review", "qa", "completion")])
        self.head = prepared["headSha"]
        return self.head
