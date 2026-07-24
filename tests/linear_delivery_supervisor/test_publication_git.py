from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from unittest import mock
from tests.linear_delivery_supervisor.support_state_engine import StateEngineTestCase, package, git

module = importlib.import_module(package.__name__ + ".publication_git")

class PublicationGitTests(StateEngineTestCase):
    def test_status_paths_normalize_windows_separators(self):
        with mock.patch.object(module, "_run_git_raw", return_value=" M docs-ai\\work\\review.md\0"):
            paths, conflicted = module._status_paths(self.repository)
        self.assertEqual(["docs-ai/work/review.md"], paths)
        self.assertFalse(conflicted)

    def test_status_paths_parse_rename_copy_in_either_column_with_two_nul_paths(self):
        raw = (
            "R  docs-ai\\new name.md\0docs-ai\\old name.md\0"
            " R work\\new two.md\0work\\old two.md\0"
            " C copy\\new three.md\0copy\\old three.md\0"
        )
        with mock.patch.object(module, "_run_git_raw", return_value=raw):
            paths, conflicted = module._status_paths(self.repository)
        self.assertEqual(sorted([
            "docs-ai/new name.md", "docs-ai/old name.md",
            "work/new two.md", "work/old two.md",
            "copy/new three.md", "copy/old three.md",
        ]), paths)
        self.assertFalse(conflicted)
        with mock.patch.object(module, "_run_git_raw", return_value=" R only\\new.md\0"):
            with self.assertRaises(module.PublicationGitError):
                module._status_paths(self.repository)

    def test_primary_and_finalization_commits_reconcile_after_commit_crash(self):
        crashes = {"prepare-committed", "finalization-committed"}
        def fault(stage, _operation):
            if stage in crashes:
                crashes.remove(stage); raise RuntimeError(stage)
        subject = module.PublicationGit(self.repository, aggregate_runner=lambda _: {"exitCode": 0}, fault_injector=fault)
        path = "docs-ai/saas-48-publication/2026-07-23-saas-48-code-review.md"
        target = self.repository / path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Review\nEvidence-Role: code-review\nEvidence-State: draft\nExact-SHA: " + "a" * 40 + "\n", encoding="utf-8")
        with self.assertRaises(module.PublicationGitCommittedInterruption):
            subject.prepare_primary(issue_id="SAAS-48", branch="codex/SAAS-48-publication", manifest=[path], preexisting_paths=[], operation_id="prepare-replay")
        prepared = subject.prepare_primary(issue_id="SAAS-48", branch="codex/SAAS-48-publication", manifest=[path], preexisting_paths=[], operation_id="prepare-replay")
        self.assertEqual(prepared["headSha"], subject.branch_head(prepared["branch"]))
        target.write_text("# Review\nEvidence-Role: code-review\nEvidence-State: pass\nExact-SHA: " + prepared["headSha"] + "\n", encoding="utf-8")
        with self.assertRaises(module.PublicationGitCommittedInterruption):
            subject.finalize_evidence([path], operation_id="finalize-replay")
        finalized = subject.finalize_evidence([path], operation_id="finalize-replay")
        self.assertEqual(git(self.repository, "rev-list", "--count", "main..HEAD").stdout.strip(), "2")
        self.assertEqual(finalized["headSha"], git(self.repository, "rev-parse", "HEAD").stdout.strip())

    def test_manifest_aggregate_then_scoped_stage(self):
        calls = []
        subject = module.PublicationGit(self.repository, aggregate_runner=lambda path: calls.append(path) or {"exitCode": 0})
        target = self.repository / "feature.txt"; target.write_text("work\n", encoding="utf-8")
        result = subject.pre_stage_and_stage(["feature.txt"])
        self.assertEqual([self.repository.resolve()], calls)
        self.assertEqual("feature.txt", git(self.repository, "diff", "--cached", "--name-only").stdout.strip())
        self.assertEqual(["feature.txt"], result["paths"])

    def test_repair_preparation_owns_aggregate_stage_commit_and_readback(self):
        calls = []
        subject = module.PublicationGit(self.repository, aggregate_runner=lambda path: calls.append(path) or {"exitCode": 0})
        main_sha = git(self.repository, "rev-parse", "main").stdout.strip()
        branch = subject.create_repair_branch(issue_id="SAAS-48", attempt=1, current_main_sha=main_sha)
        target = self.repository / "repair.txt"
        target.write_text("repair\n", encoding="utf-8")
        result = subject.prepare_repair(
            issue_id="SAAS-48", attempt=1, manifest=["repair.txt"],
            preexisting_paths=[], operation_id="repair-owned",
        )
        self.assertEqual(branch, result["branch"])
        self.assertEqual([self.repository.resolve()], calls)
        self.assertEqual(result["headSha"], subject.branch_head(branch))
        self.assertEqual("repair.txt", git(self.repository, "show", "--pretty=", "--name-only", "HEAD").stdout.strip())
        self.assertIn("Publication-Operation: repair-owned", git(self.repository, "show", "-s", "--format=%B", "HEAD").stdout)

    def test_unexpected_diff_and_failed_aggregate_refuse_staging(self):
        subject = module.PublicationGit(self.repository, aggregate_runner=lambda _: {"exitCode": 1})
        (self.repository / "one.txt").write_text("one", encoding="utf-8")
        with self.assertRaises(module.PublicationGitError): subject.pre_stage_and_stage(["two.txt"])
        with self.assertRaises(module.PublicationGitError): subject.pre_stage_and_stage(["one.txt"])
        self.assertEqual("", git(self.repository, "diff", "--cached", "--name-only").stdout)

    def test_branch_names_are_closed(self):
        self.assertEqual("codex/SAAS-48-feature", module.PublicationGit.validate_primary_branch("SAAS-48", "codex/SAAS-48-feature"))
        for branch in ("main", "codex/SAAS-48-repair-1", "codex/OTHER-1-x"):
            with self.assertRaises(module.PublicationGitError): module.PublicationGit.validate_primary_branch("SAAS-48", branch)
