from __future__ import annotations

import copy
import hashlib
import importlib
import json
import uuid

from tests.linear_delivery_supervisor.support_state_engine import StateEngineTestCase, clean_observer, git, package, store_module

records = importlib.import_module(package.__name__ + ".publication_records")
operations = importlib.import_module(package.__name__ + ".operations")
supervisor = importlib.import_module(package.__name__ + ".supervisor")
cli = importlib.import_module(package.__name__ + ".cli")
publication_git = importlib.import_module(package.__name__ + ".publication_git")


class PublicationContractTests(StateEngineTestCase):
    def _write_composed_draft_inventory(self):
        inventory = {}
        for kind in ("plan", "tasks", "audit", "review", "qa", "completion"):
            path = f"docs-ai/005-saas-48/{kind}.md"
            target = self.repository / path; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {kind}\n", encoding="utf-8")
            inventory[kind] = {"status": "draft", "path": path,
                "digest": "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()}
        inventory["design"] = {"status": "not-required", "reason": "no-product-ui"}
        return inventory

    def publication(self, head_sha="a" * 40):
        return {
            "schemaVersion": "1.0", "repositoryId": "repo-test", "repositoryKey": "ai-config",
            "workflowId": self.descriptor["workflowId"], "issueId": "SAAS-48",
            "operationId": "publish-1", "idempotencyKey": "publish-1", "operation": "push",
            "status": "prepared", "branch": "codex/SAAS-48-publication", "baseRef": "main",
            "baseSha": head_sha, "headSha": head_sha, "mergeSha": None, "pullRequest": None,
            "attemptCount": 0, "retryCount": 0, "nextRetryAt": None, "refusalKind": None,
            "providerEvidenceRef": None,
            "preservedState": {"issueState": "In Progress", "autonomous": True, "globalWip": True,
                "reservationId": "reservation-1", "worktreePath": str(self.repository.resolve()),
                "physicalWorktreeFingerprint": "sha256:" + "b" * 64,
                "branch": "codex/SAAS-48-publication", "pullRequest": None, "evidenceRefs": []},
            "attestations": {}, "providerOperationIds": {"push": None, "pull-request": None, "squash-merge": None}, "evidenceFinalizationCount": 0, "repairAttempt": 0,
            "activeProviderOperation": None, "authorityReadback": None,
            "preparation": None, "evidenceFinalization": None,
            "consumedReplyId": None,
            "createdAt": "2026-07-22T00:00:00Z", "updatedAt": "2026-07-22T00:00:00Z",
        }

    def test_strict_state_retry_and_unknown_fields(self):
        value = self.publication()
        self.assertEqual(value, records.validate_publication_state(value))
        changed = copy.deepcopy(value); changed["unknown"] = True
        with self.assertRaises(records.PublicationRecordError): records.validate_publication_state(changed)
        self.assertEqual([5, 15, 30], [records.retry_delay_minutes(i) for i in (1, 2, 3)])
        self.assertEqual(30, records.retry_delay_minutes(2, 3600))

    def test_legacy_store_migration_is_deterministic_and_idempotent(self):
        legacy = self.store.load_state(); legacy.pop("publication")
        self.store.guard.write_json(self.store.state_path, legacy, expected_revision=legacy["revision"])
        migrated = store_module.SupervisorStore(self.manager).load_state()
        self.assertIsNone(migrated["publication"])
        self.assertEqual(migrated, store_module.SupervisorStore(self.manager).load_state())

    def test_legacy_store_with_pending_transaction_fails_closed(self):
        legacy = self.store.load_state(); legacy.pop("publication")
        self.store.guard.write_json(self.store.state_path, legacy, expected_revision=legacy["revision"])
        (self.store.transaction_dir / "pending.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(store_module.SupervisorRecoveryError): self.store.load_state()

    def test_publication_journal_replay_is_immutable_and_head_bound(self):
        journal = operations.PublicationJournal(self.store)
        value = self.publication()
        self.assertEqual(value, journal.save(value))
        self.assertEqual(value, journal.save(value))
        changed = copy.deepcopy(value); changed["headSha"] = "e" * 40
        with self.assertRaises(store_module.SupervisorConflictError): journal.save(changed)

    def test_authoritative_binding_recovers_only_after_supervisor_cas(self):
        interruptions = []
        def fault(stage, operation_id):
            if not interruptions:
                interruptions.append((stage, operation_id)); raise RuntimeError("crash")
        journal = operations.PublicationJournal(self.store, fault_injector=fault)
        value = self.publication()
        with self.assertRaises(RuntimeError): journal.save_authoritative(value)
        self.assertEqual(value["operationId"], self.store.load_state()["publication"]["operationId"])
        journal.fault_injector = None
        journal.reconcile_authoritative(value["operationId"])
        self.assertEqual(value["operationId"], self.store.load_state()["publication"]["operationId"])

    def test_stale_cas_proposal_is_never_reconcilable(self):
        journal = operations.PublicationJournal(self.store)
        value = self.publication()
        with self.assertRaises(store_module.SupervisorConflictError):
            journal.save_authoritative(value, expected_state_revision=999)
        with self.assertRaises(store_module.SupervisorConflictError):
            journal.reconcile_authoritative(value["operationId"])

    def test_composed_publication_provider_gate_merge_and_replay(self):
        issue_record = self.use_authoritative_issue_worktree("SAAS-48")
        head = git(self.repository, "rev-parse", "HEAD").stdout.strip()
        tree = git(self.repository, "rev-parse", "HEAD^{tree}").stdout.strip()
        merge_sha = git(self.repository, "commit-tree", tree, "-p", head, "-m", "merge fixture").stdout.strip()

        class Provider:
            def __init__(self): self.ref = None; self.pr = None; self.merged = {"merged": False}; self.calls = []
            def read_remote_ref(self, branch): return self.ref
            def push_ref(self, request): self.calls.append("push"); self.ref = {"headSha": request["headSha"]}; return {"statusCode": 200}
            def read_pull_request(self, branch, base_ref): return self.pr
            def create_or_reuse_pull_request(self, request): self.calls.append("pr"); self.pr = {"id": "48", "headSha": request["headSha"], "baseRef": request["baseRef"]}; return self.pr
            def read_merge(self, pull_request_id): return self.merged
            def squash_merge(self, request): self.calls.append("merge"); self.merged = {"merged": True, "mergeSha": merge_sha}; return {"mergeSha": merge_sha}
            def read_publication_authority(self, issue_id, branch, base_ref):
                return {"issueId": issue_id, "labels": ["autonomous"],
                    "pullRequestId": self.pr.get("id") if self.pr else None,
                    "baseRef": base_ref, "baseSha": head, "headSha": head, "mergeability": True}
        repository_path = self.repository
        class GitBoundary:
            physical_fingerprint = issue_record["physicalWorktreeFingerprint"]
            def prepare_primary(self, *, issue_id, branch, manifest, preexisting_paths, operation_id):
                git(repository_path, "switch", "-c", branch, "main")
                return {"branch": branch, "baseSha": head, "headSha": head,
                    "paths": list(manifest), "manifestDigest": "sha256:" + "1" * 64,
                    "aggregateDigest": "sha256:" + "2" * 64}
            def finalize_evidence(self, paths, *, operation_id):
                return {"headSha": head, "stagedPaths": list(paths),
                    "evidenceFinalizationCount": 1, "deltaDigest": "sha256:" + "3" * 64}
            def read_head_bytes(self, path): return (repository_path / path).read_bytes()
            def branch_head(self, branch): return head
        class Result: returncode = 0
        port = Provider()
        engine = supervisor.SupervisorEngine(
            manager=self.manager, publication_provider=port,
            publication_git=GitBoundary(),
            publication_gate_runner=lambda *args, **kwargs: Result(),
            local_observer=clean_observer,
        )
        run_id = str(uuid.uuid4())
        lease = engine.acquire_lease(
            run_id=run_id, owner_id="owner",
            expected_revision=engine.store.load_state()["revision"],
        )
        source_ids = {}
        def prepare_stage(stage):
            return engine.prepare_iteration(
                run_id=run_id, owner_id="owner", workflow_id=self.descriptor["workflowId"],
                issue_id="SAAS-48", worktree_path=self.repository,
                physical_worktree_fingerprint=issue_record["physicalWorktreeFingerprint"],
                expected_revision=engine.store.load_state()["revision"],
                lease_capability_ref=lease["capabilityRef"], stage=stage,
            )
        def apply_stage(prepared_stage, stage, next_stage, evidence_name):
            transition_id = str(uuid.uuid4())
            worker = {
                "schemaVersion": "1.0", "preparedIterationId": prepared_stage["preparedIterationId"],
                "runId": run_id, "workflowId": self.descriptor["workflowId"], "issueId": "SAAS-48",
                "transitionId": transition_id, "outcome": "completed" if next_stage == "completion" else "advanced",
                "completedStage": stage, "proposedNextStage": next_stage,
                "artifactManifest": [], "changedPaths": engine.leases._observe_worktree(self.repository)["changedPaths"], "summary": f"{stage} passed",
                "proposedExternalTransitions": [], "pause": None,
                "observed": {"repositoryId": self.manager.identity.repository_id,
                    "physicalWorktreeFingerprint": issue_record["physicalWorktreeFingerprint"], "headSha": head},
            }
            worker_path = self.manager.home.repository / f"worker-{evidence_name}.json"
            worker_path.write_text(json.dumps(worker), encoding="utf-8")
            prepared_ref = engine.store.directories["runs"] / run_id / f"{prepared_stage['preparedIterationId']}.prepared-iteration.json"
            source_id = str(uuid.uuid4())
            command = {
                "schemaVersion": "1.0", "operation": "ApplyCheckpoint", "requestId": source_id,
                "repositoryKey": self.manager.repository_key, "repositoryRoot": str(self.control_repository.resolve()),
                "stateHome": str(self.manager.home.repository), "requestedAt": "2026-07-22T00:00:00Z",
                "runId": run_id, "preparedIterationRef": str(prepared_ref), "workerResultPath": str(worker_path),
                "transitionId": transition_id, "expectedStateRevision": engine.store.load_state()["revision"],
                "expectedStage": stage,
            }
            command_path = self.manager.home.repository / f"apply-{evidence_name}.json"
            command_path.write_text(json.dumps(command), encoding="utf-8")
            cli.run_request(command_path.resolve())
            source_ids[evidence_name] = source_id
        prepared_stage = prepare_stage("review")
        for stage, next_stage, evidence_name in (("review", "qa", "review"), ("qa", "docs", "qa"), ("docs", "publication", "docs")):
            apply_stage(prepared_stage, stage, next_stage, evidence_name)
            prepared_stage = prepare_stage(next_stage)
        prepared = prepared_stage
        pair = (engine.store.load_state(), engine.store.load_reservations())
        reservation = engine.reserve(
            workflow_id=self.descriptor["workflowId"], issue_id="SAAS-48",
            worktree_path=self.repository,
            physical_worktree_fingerprint=issue_record["physicalWorktreeFingerprint"],
            policy="autonomous", owner_id="owner", run_id=run_id,
            expected_state_revision=pair[0]["revision"],
            expected_reservations_revision=pair[1]["revision"],
            capability_ref=prepared["capabilityRef"],
        )
        def authorize(mutation_id, kind):
            pair = (engine.store.load_state(), engine.store.load_reservations())
            live = pair[1]["reservations"][reservation["reservationId"]]
            return engine.authorize_mutation(
                reservation_id=reservation["reservationId"], authorization_id=str(uuid.uuid4()),
                target_operation_id=mutation_id,
                scope=[f"publication/publish-1/{kind}/{mutation_id}.json"],
                expected_record_revision=live["revision"], expected_state_revision=pair[0]["revision"],
                expected_reservations_revision=pair[1]["revision"],
                control_authorization_ref=live["releaseAuthorizationRef"],
                capability_ref=prepared["capabilityRef"],
            )
        def auth_args(mutation_id, kind):
            grant = authorize(mutation_id, kind)
            return {
                "reservation_id": reservation["reservationId"],
                "authorization_ref": grant["authorizationRef"],
                "expected_record_revision": grant["reservationRevision"],
                "expected_reservations_revision": engine.store.load_reservations()["revision"],
                "physical_worktree_fingerprint": issue_record["physicalWorktreeFingerprint"],
            }
        cli.register_fixture_assembly(self.manager.home.repository, cli.FixtureAssembly(
            publication_provider=port, publication_recovery=None,
            publication_git=GitBoundary(),
            publication_gate_runner=lambda *args, **kwargs: Result(),
        ))
        self.addCleanup(cli.unregister_fixture_assembly, self.manager.home.repository)
        def run_public(operation, fields, authorization):
            command = {
                "schemaVersion": "1.0", "operation": operation, "requestId": str(uuid.uuid4()),
                "repositoryKey": self.manager.repository_key, "repositoryRoot": str(self.control_repository.resolve()),
                "stateHome": str(self.manager.home.repository), "requestedAt": "2026-07-22T00:01:00Z",
                "expectedStateRevision": engine.store.load_state()["revision"],
                "reservationId": authorization["reservation_id"], "authorizationRef": authorization["authorization_ref"],
                "expectedRecordRevision": authorization["expected_record_revision"],
                "expectedReservationsRevision": authorization["expected_reservations_revision"],
                "physicalWorktreeFingerprint": authorization["physical_worktree_fingerprint"],
                **fields,
            }
            path = self.manager.home.repository / f"public-{operation}-{command['requestId']}.json"
            path.write_text(json.dumps(command), encoding="utf-8")
            return cli.run_request(path.resolve())
        def provider(name, identity):
            args = auth_args(identity, f"provider-{name}")
            return run_public("PublicationProvider", {
                "publicationOperationId": "publish-1", "providerOperation": name,
                "providerOperationId": identity,
            }, args)
        def trusted(name):
            args = auth_args(name + "-48", "evidence")
            return run_public("RecordPublicationAttestation", {
                "publicationOperationId": "publish-1", "attestationId": name + "-48",
                "sourceOperationId": source_ids[name],
            }, args)
        def gate(kind, identity, exact_sha, started, completed):
            return run_public("PublicationGate", {
                "publicationOperationId": "publish-1", "gateOperationId": identity,
                "exactSha": exact_sha, "gateKind": kind,
                "startedAt": started, "completedAt": completed,
            }, auth_args(identity, f"gate-{kind}"))
        value = self.publication(head)
        value["repositoryId"] = self.manager.identity.repository_id
        value["repositoryKey"] = self.manager.repository_key
        value["preservedState"].update({
            "reservationId": reservation["reservationId"],
            "worktreePath": str(self.repository.resolve()),
            "physicalWorktreeFingerprint": issue_record["physicalWorktreeFingerprint"],
        })
        prepare_args = auth_args("publish-1", "prepare")
        engine.dispatch("PreparePublication", {"publication_state": value,
            "artifact_manifest": ["src/fixture.py"], "preexisting_paths": [],
            "preparation_operation_id": "publish-1",
            "expected_state_revision": engine.store.load_state()["revision"], **prepare_args})
        authoritative_publication = engine.publication_operations.load("publish-1")
        for mutate in (
            lambda item: item.update(issueId="SAAS-999"),
            lambda item: item.update(workflowId=str(uuid.uuid4())),
            lambda item: item["preservedState"].update(worktreePath=str(self.control_repository)),
            lambda item: item["preservedState"].update(physicalWorktreeFingerprint="sha256:" + "f" * 64),
        ):
            foreign = copy.deepcopy(authoritative_publication); mutate(foreign)
            with self.assertRaises(store_module.SupervisorStoreError):
                engine.publication_operations.resolve_checkpoint_result(
                    publication=foreign, source_operation_id=source_ids["review"]
                )
        with self.assertRaises(store_module.SupervisorStoreError):
            engine.dispatch("RecordPublicationAttestation", {"operation_id": value["operationId"], "attestation_id": "stale-review", "source_operation_id": "arbitrary-unissued", "expected_state_revision": engine.store.load_state()["revision"], **auth_args("stale-review", "evidence")})
        self.assertEqual(value["operationId"], engine.status()["publication"]["operationId"])
        with self.assertRaises(store_module.SupervisorStoreError):
            provider("pull-request", "pr-too-early")
        with self.assertRaises(store_module.SupervisorStoreError):
            engine.dispatch("PublicationProvider", {"operation_id": value["operationId"], "provider_operation": "push", "provider_operation_id": "push-stale", "expected_state_revision": engine.store.load_state()["revision"] - 1, **auth_args("push-stale", "provider-push")})
        provider("push", "push-48")
        provider("push", "push-48")
        provider("pull-request", "pr-48")
        finalize_id = "finalize-48"
        finalize_args = auth_args(finalize_id, "finalize-evidence")
        engine.finalize_publication_evidence(
            operation_id=value["operationId"], finalization_operation_id=finalize_id,
            evidence_paths=["docs-ai/005-saas-48/review.md"],
            draft_inventory=self._write_composed_draft_inventory(), design_required=False,
            expected_state_revision=engine.store.load_state()["revision"],
            **finalize_args,
        )
        provider("push", "push-final-48")
        provider("pull-request", "pr-final-48")
        for kind in ("plan", "tasks", "audit", "review", "qa", "completion"):
            (self.repository / f"docs-ai/005-saas-48/{kind}.md").unlink()
        with self.assertRaises(store_module.SupervisorStoreError):
            bad_gate = str(uuid.uuid4()); engine.dispatch("PublicationGate", {"operation_id": value["operationId"], "gate_operation_id": bad_gate, "exact_sha": head, "kind": "exact-merge-aggregate", "started_at": "2026-07-22T00:00:00Z", "completed_at": "2026-07-22T00:01:00Z", "expected_state_revision": engine.store.load_state()["revision"], **auth_args(bad_gate, "gate-exact-merge-aggregate")})
        pre_stage_gate = str(uuid.uuid4())
        gate("pre-staging-aggregate", pre_stage_gate, head, "2026-07-22T00:00:00Z", "2026-07-22T00:01:00Z")
        head_gate = str(uuid.uuid4())
        gate("exact-head-aggregate", head_gate, head, "2026-07-22T00:00:00Z", "2026-07-22T00:01:00Z")
        self.assertEqual("complete", engine.store.load_state()["gateWorktrees"][head_gate]["attestationStatus"])
        with self.assertRaises(store_module.SupervisorStoreError):
            provider("squash-merge", "merge-missing-evidence")
        trusted("review")
        for name in ("qa", "docs"):
            trusted(name)
        apply_stage(prepared, "publication", "completion", "evidence-convergence")
        trusted("evidence-convergence")
        provider("squash-merge", "merge-48")
        merge_gate = str(uuid.uuid4())
        gate("exact-merge-aggregate", merge_gate, merge_sha, "2026-07-22T00:02:00Z", "2026-07-22T00:03:00Z")
        self.assertEqual("completed", engine.status()["publication"]["status"])
        self.assertEqual(["push", "pr", "merge"], port.calls)
        self.assertEqual(
            {"push": "push-final-48", "pull-request": "pr-final-48", "squash-merge": "merge-48"},
            engine.publication_operations.load("publish-1")["providerOperationIds"],
        )
