from __future__ import annotations

import copy
import unittest

from tests.linear_delivery_supervisor.support_publication import PublicPublicationScenario, cli
from tests.linear_delivery_supervisor.support_state_engine import StateEngineTestCase, git, store_module


class PublicationPublicCliTests(StateEngineTestCase):
    def test_public_primary_commit_crash_replays_same_command_without_duplicate_commit(self):
        crashes = {"prepare-committed"}
        def fault(stage, _operation):
            if stage in crashes:
                crashes.remove(stage)
                raise RuntimeError(stage)
        scenario = PublicPublicationScenario(self, prepare=False, git_fault_injector=fault)
        with self.assertRaises(Exception):
            scenario.prepare_publication()
        command = scenario.last_command_path
        count = git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip()
        replay = cli.run_request(command)
        self.assertEqual("prepared", replay["status"])
        self.assertEqual(count, git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip())

    def test_public_finalization_commit_crash_replays_same_command_before_provider_push(self):
        scenario = PublicPublicationScenario(self)
        scenario.provider_operation("push"); scenario.refresh_publication_capability("review")
        scenario.provider_operation("pull-request"); scenario.refresh_publication_capability("review")
        scenario._draft_inventory = scenario.draft_inventory()
        scenario._write_final_evidence()
        crashes = {"finalization-committed"}
        def fault(stage, _operation):
            if stage in crashes:
                crashes.remove(stage)
                raise RuntimeError(stage)
        scenario.git_boundary.fault_injector = fault
        with self.assertRaises(Exception):
            scenario.finalize_evidence()
        command = scenario.last_command_path
        count = git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip()
        cli.run_request(command)
        self.assertEqual(1, scenario.publication()["evidenceFinalizationCount"])
        self.assertEqual("prepared", scenario.publication()["status"])
        self.assertIsNone(scenario.publication()["authorityReadback"])
        self.assertEqual(count, git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip())

    def test_public_drift_commit_crash_replays_same_command_without_duplicate_commit(self):
        scenario = PublicPublicationScenario(self)
        scenario.run_premerge(0)
        drift_sha = scenario.real_commit("advance main for crash replay")
        git(scenario.repository, "update-ref", "refs/heads/main", drift_sha)
        git(scenario.repository, "update-ref", "refs/remotes/origin/main", drift_sha)
        self.assertEqual("base-drift", scenario.provider_operation("squash-merge")["status"])
        crashes = {"prepare-committed"}
        def fault(stage, _operation):
            if stage in crashes:
                crashes.remove(stage)
                raise RuntimeError(stage)
        scenario.git_boundary.fault_injector = fault
        with self.assertRaises(Exception):
            scenario.reprepare_after_base_drift()
        command = scenario.last_command_path
        count = git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip()
        replay = cli.run_request(command)
        self.assertEqual("prepared", replay["status"])
        self.assertEqual(count, git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip())

    def test_public_repair_commit_crash_replays_same_command_without_duplicate_commit(self):
        scenario = PublicPublicationScenario(self)
        scenario.run_premerge(0)
        scenario.merge_and_fail_exact_gate()
        current_main = git(scenario.repository, "rev-parse", "main").stdout.strip()
        self.assertEqual("repairing", scenario.repair(current_main)["status"])
        manifest = [scenario.draft_paths[name] for name in ("review", "qa", "completion")]
        for kind, role in (("review", "code-review"), ("qa", "qa"), ("completion", "completion")):
            (scenario.repository / scenario.draft_paths[kind]).write_text(
                f"# {kind.title()}\nEvidence-Role: {role}\nEvidence-State: draft\nExact-SHA: {scenario.head}\n",
                encoding="utf-8",
            )
        crashes = {"repair-committed"}
        def fault(stage, _operation):
            if stage in crashes:
                crashes.remove(stage)
                raise RuntimeError(stage)
        scenario.git_boundary.fault_injector = fault
        with self.assertRaises(Exception):
            scenario.repair(current_main, manifest)
        command = scenario.last_command_path
        count = git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip()
        replay = cli.run_request(command)
        self.assertEqual("repair-head", replay["status"])
        self.assertEqual(count, git(scenario.repository, "rev-list", "--count", "main..HEAD").stdout.strip())

    def test_public_preparation_and_finalization_are_engine_owned_and_cannot_be_skipped(self):
        scenario = PublicPublicationScenario(self, finalize=False)
        publication = scenario.publication()
        self.assertEqual(scenario.git_boundary.branch_head(publication["branch"]), publication["headSha"])
        self.assertEqual(publication["headSha"], publication["preparation"]["headSha"])
        self.assertIn("pre-staging-aggregate", publication["attestations"])
        with self.assertRaises(Exception):
            scenario.finalize_evidence()
        scenario.provider_operation("push")
        scenario.provider_operation("pull-request")
        scenario._draft_inventory = {"design": {"status": "not-required", "reason": "no-product-ui"}}
        scenario._write_final_evidence()
        with self.assertRaises(Exception):
            scenario.finalize_evidence()
        with self.assertRaises(Exception):
            scenario.provider_operation("squash-merge")
        self.assertEqual(0, scenario.publication()["evidenceFinalizationCount"])
        self.assertIsNone(scenario.publication()["evidenceFinalization"])

    def test_public_premerge_base_drift_merges_only_origin_main_and_invalidates_evidence(self):
        scenario = PublicPublicationScenario(self)
        scenario.run_premerge(0)
        drift_sha = scenario.real_commit("advance main")
        git(scenario.repository, "update-ref", "refs/heads/main", drift_sha)
        git(scenario.repository, "update-ref", "refs/remotes/origin/main", drift_sha)
        before_calls = list(scenario.provider.calls)
        result = scenario.provider_operation("squash-merge")
        self.assertEqual("base-drift", result["status"])
        self.assertEqual(before_calls, scenario.provider.calls)
        publication = scenario.publication()
        self.assertEqual("base-drift", publication["status"])
        self.assertEqual(drift_sha, publication["baseSha"])
        self.assertEqual({}, publication["attestations"])
        self.assertEqual(0, publication["evidenceFinalizationCount"])
        scenario.reprepare_after_base_drift()
        scenario.run_premerge(0)
        scenario.provider_operation("squash-merge")
        scenario.gate("exact-merge-aggregate", scenario.publication()["mergeSha"])
        self.assertEqual("completed", scenario.publication()["status"])
    def test_transient_retry_matrix_and_first_refusal_after_exhaustion(self):
        scenario = PublicPublicationScenario(self)
        scenario.provider.refuse(
            "push",
            {"statusCode": 429},
            {"statusCode": 503},
            {"statusCode": 429, "retryAfterSeconds": 9999},
            {"statusCode": 503},
        )
        identity = "11111111-1111-4111-8111-111111111111"
        result = scenario.provider_operation("push", operation_id=identity)
        self.assertEqual(("retry-wait", 1, "2026-07-23T00:05:00Z"), (result["status"], result["retryCount"], result["nextRetryAt"]))
        result = scenario.recover(requested_at="2026-07-23T00:05:00Z")
        self.assertEqual(("retry-wait", 2, "2026-07-23T00:15:00Z"), (result["status"], result["retryCount"], result["nextRetryAt"]))
        result = scenario.recover(requested_at="2026-07-23T00:15:00Z")
        self.assertEqual(("retry-wait", 3, "2026-07-23T00:30:00Z"), (result["status"], result["retryCount"], result["nextRetryAt"]))
        result = scenario.recover(requested_at="2026-07-23T00:30:00Z")
        self.assertEqual("paused", result["status"])
        self.assertEqual(4, result["attemptCount"])
        self.assertEqual(4, scenario.lease_releases)
        self.assertEqual({"autonomous", "blocked", "needs-human"}, scenario.labels)
        self.assertEqual(1, len(scenario.requests.store.load()["publicationRequests"]))
        self.assertEqual(1, len(scenario.notifications))
        self.assertEqual([("push", identity)] * 4, scenario.provider.calls)

    def test_stable_pause_is_durable_deduplicated_and_attended_resume_is_one_shot(self):
        scenario = PublicPublicationScenario(self)
        before = copy.deepcopy(scenario.publication()["preservedState"])
        scenario.provider.refuse("push", {"code": "permission-denied"})
        identity = "22222222-2222-4222-8222-222222222222"
        paused = scenario.provider_operation("push", operation_id=identity)
        self.assertEqual("paused", paused["status"])
        self.assertEqual(before, paused["preservedState"])
        self.assertEqual("In Progress", scenario.issue_states[-1])
        self.assertEqual(1, scenario.lease_releases)
        request = scenario.request_record()
        self.assertEqual(f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}", request["data"]["replySyntax"])

        for body in (
            "retry publication",
            f"RETRY-PUBLICATION wrong {scenario.head}",
            f"RETRY-PUBLICATION {scenario.operation_id} {'f' * 40}",
        ):
            with self.assertRaises(Exception):
                scenario.recover(requested_at="2026-07-23T00:03:00Z", attended=scenario.attended(body=body))
        self.assertEqual(1, len(scenario.requests.store.load()["publicationRequests"]))
        self.assertEqual(1, len(scenario.notifications))
        self.assertEqual([("push", identity)], scenario.provider.calls)

        scenario.refresh_publication_capability("review")
        body = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        resumed = scenario.recover(requested_at="2026-07-23T00:04:00Z", attended=scenario.attended(body=body, reply_id="reply-success"))
        resume_command = scenario.last_command_path
        self.assertEqual("pushed", resumed["status"])
        self.assertEqual("reply-success", resumed["consumedReplyId"])
        self.assertEqual({"autonomous"}, scenario.labels)
        self.assertEqual([("push", identity), ("push", identity)], scenario.provider.calls)
        duplicate = cli.run_request(resume_command)
        self.assertEqual("pushed", duplicate["status"])
        self.assertEqual(2, len(scenario.provider.calls))

    def test_attended_pr_success_retains_pr_identity_and_continues(self):
        scenario = PublicPublicationScenario(self)
        scenario.provider_operation("push")
        scenario.refresh_publication_capability("review")
        scenario.provider.refuse("pull-request", {"code": "permission-denied"})
        scenario.provider_operation("pull-request", operation_id="55555555-5555-4555-8555-555555555555")
        scenario.refresh_publication_capability("review")
        retry = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        resumed = scenario.recover(requested_at="2026-07-23T00:04:00Z", attended=scenario.attended(body=retry, reply_id="reply-pr"))
        self.assertEqual("pr-open", resumed["status"])
        self.assertEqual("pr-1", resumed["pullRequest"]["id"])
        scenario.refresh_publication_capability("review")
        scenario.run_premerge(0)
        self.assertEqual("head-gated", scenario.publication()["status"])

    def test_attended_merge_success_retains_merge_identity_and_completes(self):
        scenario = PublicPublicationScenario(self)
        scenario.run_premerge(0)
        scenario.provider.refuse("squash-merge", {"code": "permission-denied"})
        scenario.provider_operation("squash-merge", operation_id="66666666-6666-4666-8666-666666666666")
        retry = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        resumed = scenario.recover(requested_at="2026-07-23T00:04:00Z", attended=scenario.attended(body=retry, reply_id="reply-merge"))
        self.assertEqual("merged", resumed["status"])
        self.assertEqual(resumed["mergeSha"], scenario.publication()["mergeSha"])
        scenario.gate("exact-merge-aggregate", resumed["mergeSha"])
        self.assertEqual("completed", scenario.publication()["status"])

    def test_attended_push_applied_then_exception_persists_exact_pushed_phase(self):
        scenario = PublicPublicationScenario(self)
        scenario.provider.refuse("push", {"code": "permission-denied"})
        scenario.provider_operation("push", operation_id="77777777-7777-4777-8777-777777777777")
        scenario.refresh_publication_capability("review")
        scenario.provider.crash_after_apply_operation = "push"
        retry = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        with self.assertRaises(RuntimeError):
            scenario.recover(requested_at="2026-07-23T00:04:00Z", attended=scenario.attended(body=retry, reply_id="reply-push-applied"))
        publication = scenario.publication()
        self.assertEqual("pushed", publication["status"])
        self.assertEqual("reply-push-applied", publication["consumedReplyId"])
        self.assertEqual({"autonomous"}, scenario.labels)

    def test_attended_pr_applied_then_exception_persists_exact_pr_phase(self):
        scenario = PublicPublicationScenario(self)
        scenario.provider_operation("push"); scenario.refresh_publication_capability("review")
        scenario.provider.refuse("pull-request", {"code": "permission-denied"})
        scenario.provider_operation("pull-request", operation_id="88888888-8888-4888-8888-888888888888")
        scenario.refresh_publication_capability("review")
        scenario.provider.crash_after_apply_operation = "pull-request"
        retry = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        with self.assertRaises(RuntimeError):
            scenario.recover(requested_at="2026-07-23T00:04:00Z", attended=scenario.attended(body=retry, reply_id="reply-pr-applied"))
        publication = scenario.publication()
        self.assertEqual("pr-open", publication["status"])
        self.assertEqual("pr-1", publication["pullRequest"]["id"])
        self.assertEqual("reply-pr-applied", publication["consumedReplyId"])

    def test_attended_merge_applied_then_exception_persists_exact_merge_phase(self):
        scenario = PublicPublicationScenario(self)
        scenario.run_premerge(0)
        scenario.provider.refuse("squash-merge", {"code": "permission-denied"})
        scenario.provider_operation("squash-merge", operation_id="99999999-9999-4999-8999-999999999999")
        scenario.provider.crash_after_apply_operation = "squash-merge"
        retry = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        with self.assertRaises(RuntimeError):
            scenario.recover(requested_at="2026-07-23T00:04:00Z", attended=scenario.attended(body=retry, reply_id="reply-merge-applied"))
        publication = scenario.publication()
        self.assertEqual("merged", publication["status"])
        self.assertEqual(scenario.provider.merges[publication["pullRequest"]["id"]]["mergeSha"], publication["mergeSha"])
        self.assertIn("merge-readback", publication["attestations"])
        scenario.gate("exact-merge-aggregate", publication["mergeSha"])
        self.assertEqual("completed", scenario.publication()["status"])

    def test_attended_consumption_precedes_crash_and_nonapplication_restores_labels(self):
        scenario = PublicPublicationScenario(self)
        scenario.provider.refuse("push", {"code": "permission-denied"})
        identity = "33333333-3333-4333-8333-333333333333"
        scenario.provider_operation("push", operation_id=identity)
        body = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        scenario.provider.crash_operation = "push"
        first = scenario.attended(body=body, reply_id="reply-crash")
        first["reply_created_at"] = "2026-07-23T00:10:00Z"
        with self.assertRaises(RuntimeError):
            scenario.recover(requested_at="2026-07-23T00:10:01Z", attended=first)
        self.assertEqual("pending", scenario.request_record()["status"])
        self.assertEqual(
            "2026-07-23T00:10:00Z",
            scenario.request_record()["data"]["lastConsumedReplyTimestamp"],
        )
        self.assertEqual("paused", scenario.publication()["status"])
        self.assertEqual("permission", scenario.publication()["refusalKind"])
        self.assertEqual("reply-crash", scenario.publication()["consumedReplyId"])
        self.assertEqual({"autonomous", "blocked", "needs-human"}, scenario.labels)
        calls = list(scenario.provider.calls)
        with self.assertRaises(Exception):
            scenario.recover(requested_at="2026-07-23T00:10:02Z")
        self.assertEqual(calls, scenario.provider.calls)
        for reply_id, timestamp in (
            ("reply-crash", "2026-07-23T00:12:00Z"),
            ("reply-older-different", "2026-07-23T00:05:00Z"),
            ("reply-equal-time-different", "2026-07-23T00:10:00Z"),
        ):
            rejected = scenario.attended(body=body, reply_id=reply_id)
            rejected["reply_created_at"] = timestamp
            with self.assertRaises(Exception):
                scenario.recover(
                    requested_at="2026-07-23T00:10:03Z", attended=rejected,
                )
            self.assertEqual(calls, scenario.provider.calls)
        newer = scenario.attended(body=body, reply_id="reply-newer-different")
        newer["reply_created_at"] = "2026-07-23T00:11:00Z"
        resumed = scenario.recover(
            requested_at="2026-07-23T00:11:01Z", attended=newer,
        )
        self.assertEqual("pushed", resumed["status"])
        self.assertEqual("reply-newer-different", resumed["consumedReplyId"])
        self.assertEqual(len(calls) + 1, len(scenario.provider.calls))

    def test_attended_nonapplication_restores_pause_labels(self):
        scenario = PublicPublicationScenario(self)
        scenario.provider.refuse("push", {"code": "permission-denied"}, {"code": "permission-denied"})
        scenario.provider_operation("push", operation_id="44444444-4444-4444-8444-444444444444")
        retry = f"RETRY-PUBLICATION {scenario.operation_id} {scenario.head}"
        result = scenario.recover(requested_at="2026-07-23T00:04:00Z", attended=scenario.attended(body=retry, reply_id="reply-refused"))
        self.assertEqual("paused", result["status"])
        self.assertEqual({"autonomous", "blocked", "needs-human"}, scenario.labels)
        self.assertEqual("authorized", scenario.requests.store.load()["publicationRequests"][0]["status"])

    def test_three_complete_numbered_repair_cycles_then_fourth_exhausts(self):
        scenario = PublicPublicationScenario(self)
        scenario.run_premerge(0)
        merge_sha = scenario.merge_and_fail_exact_gate()
        self.assertEqual("post-merge-validating", scenario.publication()["status"])

        for attempt in range(1, 4):
            previous_head = scenario.head
            repair_head = scenario.begin_repair(merge_sha)
            publication = scenario.publication()
            self.assertEqual(attempt, publication["repairAttempt"])
            self.assertEqual(f"codex/SAAS-48-repair-{attempt}", publication["branch"])
            self.assertEqual(repair_head, git_head := scenario.git_boundary.branch_head(publication["branch"]))
            self.assertNotEqual(merge_sha, git_head)

            if attempt == 1:
                # Independently absent, wrong-SHA, and stale members fail closed.
                with self.assertRaises(Exception):
                    scenario.provider_operation("squash-merge")
                scenario.refresh_publication_capability()
                with self.assertRaises(Exception):
                    scenario.gate("pre-staging-aggregate", previous_head)
                scenario.refresh_publication_capability()
                stale_id = str(__import__("uuid").uuid4())
                with self.assertRaises(Exception):
                    scenario.mutation("RecordPublicationAttestation", {
                        "publicationOperationId": scenario.operation_id, "attestationId": stale_id,
                        "sourceOperationId": scenario.sources[(0, "review")],
                    }, "evidence", mutation_id=stale_id)
                scenario.refresh_publication_capability()

            scenario.run_premerge(attempt)
            self.assertEqual(
                {"pre-staging-aggregate", "exact-head-aggregate", "review", "qa", "docs", "evidence-convergence"},
                set(scenario.publication()["attestations"]),
            )
            merge_sha = scenario.merge_and_fail_exact_gate()
            self.assertEqual("post-merge-validating", scenario.publication()["status"])

        before_exhaustion = copy.deepcopy(scenario.publication())
        branches_before = scenario.git_boundary.branch_head("codex/SAAS-48-repair-3")
        exhausted = scenario.repair(merge_sha)
        exhaustion_command = scenario.last_command_path
        self.assertEqual("paused", exhausted["status"])
        self.assertEqual(3, exhausted["repairAttempt"])
        self.assertEqual("Backlog", scenario.issue_states[-1])
        self.assertEqual({"autonomous", "needs-human"}, scenario.labels)
        self.assertEqual("repair-exhausted", scenario.notifications[-1]["kind"])
        self.assertEqual(1, len(scenario.requests.store.load()["publicationRequests"]))
        self.assertEqual(before_exhaustion["attestations"], exhausted["attestations"])
        self.assertEqual(branches_before, scenario.git_boundary.branch_head("codex/SAAS-48-repair-3"))
        self.assertEqual("", __import__("subprocess").run(
            ["git", "-C", str(scenario.repository), "branch", "--list", "codex/SAAS-48-repair-4"],
            capture_output=True, text=True, check=True,
        ).stdout.strip())
        replay = cli.run_request(exhaustion_command)
        self.assertEqual("paused", replay["status"])
        self.assertEqual(1, len(scenario.notifications))
        self.assertEqual(1, len(scenario.requests.store.load()["publicationRequests"]))


if __name__ == "__main__":
    unittest.main()
