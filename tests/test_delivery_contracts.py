"""Semantic regression tests for the three delivery workflows."""
from __future__ import annotations

import json
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_aggregate_validation():
    spec = importlib.util.spec_from_file_location("ai_toolkit_aggregate_validation", ROOT / "scripts" / "validate.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scripts/validate.py for contract tests.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aggregate_validation = load_aggregate_validation()

from validation.delivery_contracts import (
    CANONICAL_REFERENCES,
    DOCS_AI_ALLOWLIST,
    check_artifact_layout,
    check_canonical_references,
    check_docs_ai_allowlist,
    check_entry_policies,
    check_forbidden_operational_terms,
    check_projection_manifest,
    check_shared_specialists_and_routing,
    check_tool_instruction_cutover,
    check_worktree_policy,
    validate_repository,
)


def write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def valid_schema() -> str:
    names = {
        "schemaVersion",
        "workflowId",
        "workflow",
        "workSource",
        "workKey",
        "slug",
        "repositoryKey",
        "repositoryRoot",
        "goal",
        "acceptanceCriteria",
        "nonGoals",
        "tracking",
        "completionBoundary",
        "physicalWorktreeFingerprint",
        "riskFlags",
    }
    return json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                **{name: {} for name in sorted(names)},
                "schemaVersion": {"const": "2.0"},
                "workflow": {"enum": ["autonomous", "semi-autonomous", "manual"]},
                "workSource": {"enum": ["linear", "local"]},
                "completionBoundary": {"enum": ["artifact", "working-tree", "commit", "pr", "merge"]},
            },
            "required": sorted(names),
        }
    )


def canonical_fixture(root: Path) -> None:
    references = "src/skills/goal-to-delivery/references"
    for name in CANONICAL_REFERENCES:
        content = valid_schema() if name.endswith(".json") else f"# {name}\n"
        write(root, f"{references}/{name}", content)
    for skill in ("goal-to-delivery", "spec-driven-delivery", "linear-delivery-loop"):
        if skill == "goal-to-delivery":
            prefix = "references"
        else:
            prefix = "../goal-to-delivery/references"
        links = "\n".join(f"- [{name}]({prefix}/{name})" for name in CANONICAL_REFERENCES)
        write(root, f"src/skills/{skill}/SKILL.md", links)


class DeliveryContractTests(unittest.TestCase):
    def test_repository_satisfies_delivery_contracts(self) -> None:
        self.assertEqual([], validate_repository(ROOT))

    def test_historical_docs_ai_is_not_operational_doctrine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_root = "docs" + "-ai"
            write(root, f"{legacy_root}/history/old.md", "Ready for Codex used Slack for LUC-42")
            self.assertEqual([], check_forbidden_operational_terms(root))

    def test_retired_operational_terms_fail(self) -> None:
        cases = (
            "Ready for Codex",
            "Send the approval through Slack",
            "Send the approval through Telegram",
            "Use LUC-42 for the current SaaS issue",
            "Skill references are portable summaries, not the source of truth",
        )
        for index, content in enumerate(cases):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write(root, f"docs/current-{index}.md", content)
                self.assertTrue(check_forbidden_operational_terms(root))

    def test_missing_and_competing_canonical_references_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical_fixture(root)
            self.assertEqual([], check_canonical_references(root))
            (root / "src/skills/goal-to-delivery/references/design-gates.md").unlink()
            write(root, "src/skills/spec-driven-delivery/references/design-gates.md", "competing copy")
            findings = check_canonical_references(root)
            self.assertTrue(any("Missing canonical" in finding for finding in findings))
            self.assertTrue(any("Competing delivery reference" in finding for finding in findings))
            self.assertTrue(any("broken local reference" in finding for finding in findings))

    def test_renamed_normative_protocol_copy_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical_fixture(root)
            first_block = (
                "The canonical stage owner must produce independently reviewable evidence, preserve the active "
                "entry authority boundary, and return deterministic output to the caller without selecting work."
            )
            second_block = (
                "A completed stage never substitutes for independent audit, exact-diff code review, runtime "
                "acceptance verification, or durable documentation when those gates apply to the requested goal."
            )
            write(
                root,
                "src/skills/goal-to-delivery/references/delivery-stages.md",
                f"# Delivery Stages\n\n{first_block}\n\n{second_block}\n",
            )
            write(
                root,
                "src/skills/spec-driven-delivery/references/renamed-policy.md",
                f"# Locally Renamed Policy\n\n{first_block}\n\n{second_block}\n",
            )
            findings = check_canonical_references(root)
            self.assertTrue(any("Competing renamed delivery doctrine" in finding for finding in findings))

    def test_historical_layout_is_read_only_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_root = "docs" + "-ai"
            write(
                root,
                "src/skills/goal-to-delivery/references/artifact-contract.md",
                f".ai/work/ artifactFolder exact registered legacy {legacy_root} historical read-only",
            )
            write(root, "src/agents/planner.md", f"Use {legacy_root}/<NNN>-<slug>-<YYYY-MM-DD>/")
            findings = check_artifact_layout(root)
            self.assertTrue(any("active producer/consumer" in finding for finding in findings))

    def test_legacy_literal_allowlist_is_path_and_purpose_specific(self) -> None:
        literal = "docs" + "-ai"
        readme_line = next(line for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if literal in line)
        runtime_line = next(
            line
            for line in (
                ROOT / "src/skills/goal-to-delivery/scripts/descriptor.py"
            ).read_text(encoding="utf-8").splitlines()
            if literal in line
        )
        tool_line = next(
            line
            for line in (ROOT / "src/tool-instructions/codex/AGENTS.md").read_text(encoding="utf-8").splitlines()
            if literal in line
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root, "README.md", readme_line)
            write(root, "dist/tool-instructions/codex/AGENTS.md", tool_line)
            self.assertEqual([], check_docs_ai_allowlist(root))

            write(root, "README.md", readme_line + f"\nCreate current work in {literal}/new-work.\n")
            self.assertTrue(check_docs_ai_allowlist(root), "stale current doctrine must fail in an allowlisted path")

            write(root, "README.md", runtime_line)
            self.assertTrue(check_docs_ai_allowlist(root), "an allowed line must fail under the wrong path/purpose")

        for relative in (
            "src/agents/unlisted.md",
            "tests/unreviewed.py",
            "dist/codex/agents/unlisted.toml",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write(root, relative, runtime_line)
                self.assertTrue(check_docs_ai_allowlist(root), "active source, tests, and dist must all be scanned")

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(
                DOCS_AI_ALLOWLIST,
                {"README.md": {"unsupported purpose": frozenset()}},
                clear=True,
            ):
                self.assertTrue(check_docs_ai_allowlist(Path(directory)))

    def test_tool_instruction_cutover_rejects_retired_path_and_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src/tool-instructions").mkdir(parents=True)
            self.assertEqual([], check_tool_instruction_cutover(root))

            retired_leaf = "project" + "-templates"
            (root / "src" / retired_leaf).mkdir()
            self.assertTrue(check_tool_instruction_cutover(root))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src/tool-instructions").mkdir(parents=True)
            retired_name = "Project" + " templates"
            write(root, "README.md", f"Keep {retired_name} here.")
            self.assertTrue(check_tool_instruction_cutover(root))

    def test_tool_instruction_paths_and_identifiers_are_canonical(self) -> None:
        expected = (
            "src/tool-instructions/codex/AGENTS.md",
            "src/tool-instructions/claude/CLAUDE.md",
            "src/tool-instructions/copilot/.github/copilot-instructions.md",
            "src/tool-instructions/cursor/AGENTS.md",
        )
        self.assertTrue(all((ROOT / relative).is_file() for relative in expected))
        self.assertFalse((ROOT / "src" / ("project" + "-templates")).exists())
        for relative in expected:
            instruction = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("canonical design-gate and UI-review contracts", instruction)
            self.assertNotIn("goal-to-delivery/references/design-gates.md", instruction)
            self.assertNotIn(".cursor/rules/ui-design-gates.mdc", instruction)
            self.assertIn("applicable UI design conformance", instruction)

        self.assertEqual(
            (ROOT / "src/tool-instructions/codex/AGENTS.md").read_text(encoding="utf-8"),
            (ROOT / "src/tool-instructions/cursor/AGENTS.md").read_text(encoding="utf-8"),
        )

        cursor_rules = ROOT / "dist" / "cursor" / "rules"
        expected_cursor_support = (
            "ui-design-gates.mdc",
            "ui-review-spec.mdc",
            "ui-design-spec-template.mdc",
            "ui-design-review-template.mdc",
            "ui-audit-checklist.mdc",
            "ui-component-selection.mdc",
        )
        self.assertTrue(all((cursor_rules / name).is_file() for name in expected_cursor_support))
        self.assertIn(
            ".cursor/rules/ui-design-gates.mdc",
            (cursor_rules / "product-designer.mdc").read_text(encoding="utf-8"),
        )
        for specialist in ("planner.mdc", "auditor.mdc"):
            rule = (cursor_rules / specialist).read_text(encoding="utf-8")
            self.assertIn(".cursor/rules/ui-design-gates.mdc", rule)
            self.assertNotIn("`design-gates.md`", rule)
        self.assertIn(
            "./ui-design-review-template.mdc",
            (cursor_rules / "ui-review-spec.mdc").read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "./references/",
            (cursor_rules / "ui-review-spec.mdc").read_text(encoding="utf-8"),
        )

        build = (ROOT / "scripts/build.py").read_text(encoding="utf-8")
        sync = (ROOT / "scripts/sync.py").read_text(encoding="utf-8")
        bootstrap = (ROOT / "scripts/bootstrap_existing.py").read_text(encoding="utf-8")
        self.assertIn("def validate_tool_instruction_skills", build)
        self.assertIn("def sync_tool_instructions", sync)
        self.assertIn("SRC_TOOL_INSTRUCTIONS", bootstrap)
        self.assertIn("def write_tool_instructions", bootstrap)

    def test_worktree_policy_and_all_tool_routes_are_enforced(self) -> None:
        self.assertEqual([], check_worktree_policy(ROOT))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative_paths = (
                "src/skills/goal-to-delivery/references/worktree-policy.md",
                "src/tool-instructions/codex/AGENTS.md",
                "src/tool-instructions/claude/CLAUDE.md",
                "src/tool-instructions/copilot/.github/copilot-instructions.md",
                "src/tool-instructions/cursor/AGENTS.md",
            )
            for relative in relative_paths:
                write(root, relative, (ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual([], check_worktree_policy(root))

            codex = root / "src/tool-instructions/codex/AGENTS.md"
            canonical_codex = codex.read_text(encoding="utf-8")
            codex.write_text(
                canonical_codex.replace(
                    "goal-to-delivery/references/worktree-policy.md",
                    "missing-worktree-policy.md",
                ),
                encoding="utf-8",
            )
            self.assertTrue(check_worktree_policy(root))

            codex.write_text(canonical_codex, encoding="utf-8")
            policy = root / "src/skills/goal-to-delivery/references/worktree-policy.md"
            resolved_command = "git worktree add -b <branch> <exact-path> <resolved-base-commit>"
            movable_command = "git worktree add -b <branch> <exact-path> <remote-ref>"
            policy.write_text(
                policy.read_text(encoding="utf-8").replace(resolved_command, movable_command),
                encoding="utf-8",
            )
            findings = check_worktree_policy(root)
            self.assertTrue(
                any("never a movable remote ref" in finding for finding in findings),
                "the policy validator must reject a movable-ref execution command",
            )

    def test_worktree_creation_pins_authorized_commit_when_remote_ref_moves(self) -> None:
        def git(cwd: Path, *args: str) -> str:
            return subprocess.run(
                ["git", *args],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            repository.mkdir()
            git(repository, "init")
            git(repository, "config", "user.name", "Worktree Policy Fixture")
            git(repository, "config", "user.email", "worktree-policy@example.invalid")

            tracked = repository / "tracked.txt"
            tracked.write_text("authorized\n", encoding="utf-8")
            git(repository, "add", "tracked.txt")
            git(repository, "commit", "-m", "authorized base")
            authorized_commit = git(repository, "rev-parse", "HEAD")
            git(repository, "update-ref", "refs/remotes/origin/main", authorized_commit)

            tracked.write_text("advanced\n", encoding="utf-8")
            git(repository, "commit", "-am", "advance movable ref")
            advanced_commit = git(repository, "rev-parse", "HEAD")
            git(repository, "update-ref", "refs/remotes/origin/main", advanced_commit)
            self.assertNotEqual(authorized_commit, advanced_commit)
            self.assertEqual(advanced_commit, git(repository, "rev-parse", "refs/remotes/origin/main"))

            worktrees = root / "worktrees"
            worktrees.mkdir()
            destination = worktrees / "authorized"
            git(
                repository,
                "worktree",
                "add",
                "-b",
                "fixture-authorized",
                str(destination),
                authorized_commit,
            )

            self.assertEqual(authorized_commit, git(destination, "rev-parse", "HEAD"))
            self.assertNotEqual(advanced_commit, git(destination, "rev-parse", "HEAD"))

    def test_entry_policy_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(
                root,
                "src/skills/goal-to-delivery/SKILL.md",
                "semi-autonomous automatic working-tree queue selection never mode: autonomous "
                "registered `artifactFolder`",
            )
            write(
                root,
                "src/skills/spec-driven-delivery/SKILL.md",
                "manual exactly one without automatic advancement one focused question reject mode: autonomous "
                "registered `artifactFolder`",
            )
            linear = write(
                root,
                "src/skills/linear-delivery-loop/SKILL.md",
                "autonomous .ai/loop.json autonomous label human-decision label at most one "
                "In Progress Backlog Done continuation issue "
                "DECIDE <ISSUE> CUSTOM <SUGGESTION> notification click target "
                "quiet standalone scheduled run set_thread_archived raw archive directive "
                "applicable UI design conformance registered `artifactFolder`",
            )
            self.assertEqual([], check_entry_policies(root))
            linear.write_text("autonomous helper", encoding="utf-8")
            self.assertTrue(check_entry_policies(root))

    def test_linear_loop_archives_only_quiet_standalone_runs(self) -> None:
        skill = (ROOT / "src/skills/linear-delivery-loop/SKILL.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs/mvp-linear-delivery-loop.md").read_text(encoding="utf-8")

        for fragment in (
            "quiet standalone scheduled run",
            "set_thread_archived",
            "After releasing any acquired lease",
            "Never archive an attended pilot",
            "no newer valid owner decision",
            "If native archiving is unavailable",
        ):
            self.assertIn(fragment, skill)
        self.assertIn("Quiet-run cleanup", guide)
        self.assertIn("Do not archive attended pilots", guide)

    def test_linear_loop_recommends_larger_implementation_budgets(self) -> None:
        config = json.loads(
            (ROOT / "src/skills/linear-delivery-loop/references/project-config.example.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            {
                "maxRunMinutes": 90,
                "maxFiles": 30,
                "maxChangedLines": 5000,
                "maxTestMinutes": 30,
            },
            config["limits"],
        )

    def test_feature_driver_routing_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specialists = (
                "planner",
                "product-designer",
                "tasker",
                "auditor",
                "dotnet",
                "nextjs-mui",
                "react",
                "jekyll-site-builder",
                "code-reviewer",
                "qa",
            )
            write(
                root,
                "src/skills/goal-to-delivery/references/delivery-stages.md",
                "planner product-designer tasker auditor matching implementer design_review "
                "code-reviewer qa docs-as-code proven not to affect rendered UI or interaction",
            )
            write(
                root,
                "src/skills/goal-to-delivery/references/completion-boundaries.md",
                "merge applicable UI design conformance one code review applicable QA",
            )
            design_gates = write(
                root,
                "src/skills/goal-to-delivery/references/design-gates.md",
                "binding design sources design specification mechanical change design conformance review "
                "every change to rendered UI or interaction real browser PASS FAIL registered `artifactFolder` "
                "reviewed state `--02`",
            )
            for agent in specialists:
                anchors = ""
                if agent == "auditor":
                    anchors = "independent pre-implementation read-only"
                elif agent == "product-designer":
                    anchors = (
                        "two product-design operations binding design sources design specification "
                        "design conformance review real-browser PASS FAIL stale reviewed state `--02`"
                    )
                elif agent == "planner":
                    anchors = "design-gates.md binding design sources post-implementation design conformance review"
                elif agent == "tasker":
                    anchors = (
                        "design-gates.md binding design-source paths product-designer conformance-review task"
                    )
                elif agent in ("react", "nextjs-mui", "jekyll-site-builder"):
                    anchors = (
                        "design-gates.md binding design sources required design spec design conformance review"
                    )
                elif agent == "code-reviewer":
                    anchors = (
                        "exact diff review qa product-designer design conformance missing stale failed"
                    )
                elif agent == "qa":
                    anchors = (
                        "real behavior do not fix defects product-designer design conformance missing stale failed"
                    )
                write(root, f"src/agents/{agent}.md", anchors)
            write(
                root,
                "src/skills/ui-review-spec/SKILL.md",
                "binding design sources exact implementation identity design-review-template.md "
                "real rendered evidence `--02`",
            )
            feature = write(
                root,
                "src/agents/feature-driver.md",
                "---\nname: feature-driver\n---\ncompatibility alias to $goal-to-delivery; never autonomous",
            )
            write(root, "src/skills/docs-as-code/SKILL.md", "durable documentation")
            write(
                root,
                "src/skills/multi-agent-delivery/SKILL.md",
                "$goal-to-delivery $spec-driven-delivery $linear-delivery-loop; "
                "do not choose a policy; do not select work; design conformance review",
            )
            self.assertEqual([], check_shared_specialists_and_routing(root))

            original_gates = design_gates.read_text(encoding="utf-8")
            design_gates.write_text("binding design sources", encoding="utf-8")
            self.assertTrue(
                any("frontend/UI design gate contract" in item for item in check_shared_specialists_and_routing(root))
            )
            design_gates.write_text(original_gates, encoding="utf-8")

            designer = root / "src/agents/product-designer.md"
            original_designer = designer.read_text(encoding="utf-8")
            designer.write_text("design specification only", encoding="utf-8")
            self.assertTrue(
                any(
                    "product-designer design gate ownership" in item
                    for item in check_shared_specialists_and_routing(root)
                )
            )
            designer.write_text(original_designer, encoding="utf-8")

            feature.write_text(
                "---\nname: feature-driver\n---\ncompatibility $goal-to-delivery never autonomous\n"
                "Required workflow: copied orchestration",
                encoding="utf-8",
            )
            self.assertTrue(
                any("retired orchestration doctrine" in item for item in check_shared_specialists_and_routing(root))
            )

    def test_projection_manifest_detects_source_and_generated_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write(root, "src/agents/example.md", "canonical")
            output = write(root, "dist/codex/agents/example.toml", "generated")
            (root / "src/skills").mkdir(parents=True)
            (root / "src/tool-instructions").mkdir(parents=True)

            import hashlib

            manifest = {
                "schemaVersion": 1,
                "canonicalRoot": "src",
                "generatedRoot": "dist",
                "entries": [
                    {
                        "source": "src/agents/example.md",
                        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "projections": [
                            {
                                "path": "dist/codex/agents/example.toml",
                                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                            }
                        ],
                    }
                ],
            }
            write(root, "dist/manifest.json", json.dumps(manifest))
            self.assertEqual([], check_projection_manifest(root))
            output.write_text("drift", encoding="utf-8")
            self.assertTrue(any("projection drift" in item for item in check_projection_manifest(root)))

    def test_aggregate_manifest_is_local_and_complete(self) -> None:
        manifest = json.loads((ROOT / "validation/manifest.json").read_text(encoding="utf-8"))
        names = [step["name"] for step in manifest["steps"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            ["command", "command", "unittest-discovery"],
            [step["type"] for step in manifest["steps"]],
        )
        rendered = json.dumps(manifest).casefold()
        self.assertIn("scripts/build.py", rendered)
        self.assertIn("scripts/test_sync_markers.py", rendered)
        self.assertIn('"startdirectory": "tests"', rendered)
        self.assertNotIn("sync.py --tool", rendered)

    def test_aggregate_manifest_accepts_only_fixed_local_shapes(self) -> None:
        safe = {
            "schemaVersion": 1,
            "steps": [
                {
                    "name": "build",
                    "type": "command",
                    "argv": ["{python}", "scripts/build.py"],
                },
                {
                    "name": "tests",
                    "type": "unittest-discovery",
                    "startDirectory": "tests",
                    "pattern": "test*.py",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            manifest = write(Path(directory), "manifest.json", json.dumps(safe))
            self.assertEqual(safe, aggregate_validation.load_manifest(manifest))

    def test_aggregate_manifest_rejects_mutating_or_external_commands(self) -> None:
        unsafe_argv = (
            ["{python}", "scripts/sync.py", "--tool", "all"],
            ["{python}", "scripts/build.py", "scripts/sync.py"],
            ["{python}", "scripts/build.py && scripts/sync.py"],
            ["{python}", "-c", "import scripts.sync"],
            ["{python}", "-m", "pip", "install", "package"],
            ["pwsh", "-File", "scripts/build.py"],
            ["cmd", "/c", "python scripts/build.py"],
            ["bash", "-c", "python scripts/build.py"],
            ["curl", "https://example.invalid"],
            ["gh", "pr", "checks"],
            ["git", "push"],
            ["linear", "issue", "update"],
        )
        for index, argv in enumerate(unsafe_argv):
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as directory:
                data = {
                    "schemaVersion": 1,
                    "steps": [{"name": f"unsafe-{index}", "type": "command", "argv": argv}],
                }
                manifest = write(Path(directory), "manifest.json", json.dumps(data))
                with self.assertRaisesRegex(aggregate_validation.ManifestError, "not allowlisted"):
                    aggregate_validation.load_manifest(manifest)

    def test_aggregate_manifest_rejects_shell_fields_and_discovery_drift(self) -> None:
        unsafe_steps = (
            {
                "name": "shell-field",
                "type": "command",
                "argv": ["{python}", "scripts/build.py"],
                "shell": True,
            },
            {
                "name": "external-tests",
                "type": "unittest-discovery",
                "startDirectory": "../tests",
                "pattern": "test*.py",
            },
            {
                "name": "arbitrary-pattern",
                "type": "unittest-discovery",
                "startDirectory": "tests",
                "pattern": "*.py",
            },
        )
        for step in unsafe_steps:
            with self.subTest(step=step["name"]), tempfile.TemporaryDirectory() as directory:
                data = {"schemaVersion": 1, "steps": [step]}
                manifest = write(Path(directory), "manifest.json", json.dumps(data))
                with self.assertRaises(aggregate_validation.ManifestError):
                    aggregate_validation.load_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
