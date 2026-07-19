"""Semantic regression tests for the three delivery workflows."""
from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_aggregate_validation():
    spec = importlib.util.spec_from_file_location("ai_config_aggregate_validation", ROOT / "scripts" / "validate.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scripts/validate.py for contract tests.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aggregate_validation = load_aggregate_validation()

from validation.delivery_contracts import (
    AUTONOMOUS_PROMPT_BUDGET_BYTES,
    AUTONOMOUS_RUNTIME_REFERENCE,
    CANONICAL_REFERENCES,
    check_autonomous_prompt_surface,
    check_artifact_layout,
    check_canonical_references,
    check_entry_policies,
    check_forbidden_operational_terms,
    check_projection_manifest,
    check_shared_specialists_and_routing,
    check_supervisor_core,
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
    write(
        root,
        f"{references}/{AUTONOMOUS_RUNTIME_REFERENCE}",
        "adapter-prepared exactly one issue fail closed repository rules planner product designer tasker "
        "independent auditor implementer independent code reviewer runtime QA documentation structured pause "
        "material decision adapter owns checkpoint external mutation stop merge SHA",
    )
    for skill in ("goal-to-delivery", "spec-driven-delivery"):
        if skill == "goal-to-delivery":
            prefix = "references"
        else:
            prefix = "../goal-to-delivery/references"
        links = "\n".join(f"- [{name}]({prefix}/{name})" for name in CANONICAL_REFERENCES)
        write(root, f"src/skills/{skill}/SKILL.md", links)
    write(
        root,
        "src/skills/linear-delivery-loop/SKILL.md",
        f"[{AUTONOMOUS_RUNTIME_REFERENCE}]"
        f"(../goal-to-delivery/references/{AUTONOMOUS_RUNTIME_REFERENCE})",
    )


class DeliveryContractTests(unittest.TestCase):
    def test_repository_autonomous_prompt_surface_is_compact(self) -> None:
        self.assertEqual([], check_autonomous_prompt_surface(ROOT))
        entry = ROOT / "src/skills/linear-delivery-loop/SKILL.md"
        contract = (
            ROOT
            / "src/skills/goal-to-delivery/references"
            / AUTONOMOUS_RUNTIME_REFERENCE
        )
        self.assertLessEqual(
            len(entry.read_bytes()) + len(contract.read_bytes()),
            AUTONOMOUS_PROMPT_BUDGET_BYTES,
        )

    def test_repository_supervisor_core_contract_is_complete(self) -> None:
        self.assertEqual([], check_supervisor_core(ROOT))

    def test_repository_satisfies_delivery_contracts(self) -> None:
        self.assertEqual([], validate_repository(ROOT))

    def test_historical_docs_ai_is_not_operational_doctrine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root, "docs-ai/history/old.md", "Ready for Codex used Slack for LUC-42")
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
            (root / "src/skills/goal-to-delivery/references/quality-gates.md").unlink()
            write(root, "src/skills/spec-driven-delivery/references/delivery-stages.md", "competing copy")
            findings = check_canonical_references(root)
            self.assertTrue(any("Missing canonical" in finding for finding in findings))
            self.assertTrue(any("Competing delivery reference" in finding for finding in findings))
            self.assertTrue(any("broken local reference" in finding for finding in findings))

    def test_entry_specific_canonical_links_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical_fixture(root)
            self.assertEqual([], check_canonical_references(root))
            goal = root / "src/skills/goal-to-delivery/SKILL.md"
            goal.write_text(
                goal.read_text(encoding="utf-8").replace(
                    "- [quality-gates.md](references/quality-gates.md)\n", ""
                ),
                encoding="utf-8",
            )
            findings = check_canonical_references(root)
            self.assertTrue(any("quality-gates.md" in finding for finding in findings))

    def test_autonomous_entry_rejects_detailed_schema_script_and_renamed_links(self) -> None:
        cases = (
            "../goal-to-delivery/references/delivery-stages.md",
            "../goal-to-delivery/references/work-descriptor.schema.json",
            "./scripts/cli.py",
            "./references/supervisor-core.md",
            "./references/renamed-policy.md",
        )
        for target in cases:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                canonical_fixture(root)
                skill = root / "src/skills/linear-delivery-loop/SKILL.md"
                destination = (skill.parent / target).resolve()
                if not destination.exists():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text("diagnostic", encoding="utf-8")
                skill.write_text(
                    skill.read_text(encoding="utf-8") + f"\n[extra]({target})\n",
                    encoding="utf-8",
                )
                findings = check_autonomous_prompt_surface(root)
                self.assertTrue(any("must link directly only" in finding for finding in findings))

    def test_supported_local_reference_forms_resolve_the_same_compact_contract(self) -> None:
        target = f"../goal-to-delivery/references/{AUTONOMOUS_RUNTIME_REFERENCE}"
        forms = (
            f"[runtime][contract]\n\n[contract]: {target}\n",
            f'[runtime][contract]\n\n[contract]:\n  {target}\n  "runtime title"\n',
            f"[runtime][contract]\n\n[contract]:\n  <{target}>\n  'runtime title'\n",
            f"[runtime][contract]\n\n[contract]: <{target}> (runtime title)\n",
            f"[runtime][]\n\n[runtime]: {target}\n",
            f"[runtime]\n\n[runtime]: {target}\n",
            f"[runtime](<{target}>)\n",
            f'<a href="{target}">runtime</a>\n',
        )
        for content in forms:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                canonical_fixture(root)
                write(root, "src/skills/linear-delivery-loop/SKILL.md", content)
                self.assertEqual([], check_autonomous_prompt_surface(root))

    def test_external_and_fragment_references_are_excluded_from_local_closure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical_fixture(root)
            skill = root / "src/skills/linear-delivery-loop/SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8")
                + "\n[web][external]\n[external]:\n  <https://example.invalid/policy>\n"
                + "[section](#policy)\n<a href='mailto:owner@example.invalid'>owner</a>\n",
                encoding="utf-8",
            )
            self.assertEqual([], check_autonomous_prompt_surface(root))

    def test_alternate_local_reference_forms_cannot_bypass_entry_closure(self) -> None:
        target = "../goal-to-delivery/references/delivery-stages.md"
        forms = (
            f"[details][protocol]\n\n[protocol]: {target}\n",
            f'[details][protocol]\n\n[protocol]:\n  {target}\n  "protocol title"\n',
            f"[details][protocol]\n\n[protocol]:\n  <{target}>\n  'protocol title'\n",
            f"[details][protocol]\n\n[protocol]: <{target}> (protocol title)\n",
            f"[details][]\n\n[details]: {target}\n",
            f"[details]\n\n[details]: {target}\n",
            f"[details](<{target}>)\n",
            f"<a href='{target}'>details</a>\n",
        )
        for extra in forms:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                canonical_fixture(root)
                skill = root / "src/skills/linear-delivery-loop/SKILL.md"
                skill.write_text(skill.read_text(encoding="utf-8") + "\n" + extra, encoding="utf-8")
                findings = check_autonomous_prompt_surface(root)
                self.assertTrue(any("must link directly only" in finding for finding in findings))

    def test_autonomous_compact_contract_rejects_indirect_local_links(self) -> None:
        forms = (
            "[details](delivery-stages.md)",
            "[details][protocol]\n\n[protocol]: <delivery-stages.md>",
            '[details][protocol]\n\n[protocol]:\n  delivery-stages.md\n  "protocol title"',
            "[details][protocol]\n\n[protocol]:\n  <delivery-stages.md>\n  'protocol title'",
            "[details][protocol]\n\n[protocol]: <delivery-stages.md> (protocol title)",
            "[details][]\n\n[details]: delivery-stages.md",
            "[details]\n\n[details]: delivery-stages.md",
            "[details](<delivery-stages.md>)",
            '<a href="delivery-stages.md">details</a>',
        )
        for extra in forms:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                canonical_fixture(root)
                contract = (
                    root
                    / "src/skills/goal-to-delivery/references"
                    / AUTONOMOUS_RUNTIME_REFERENCE
                )
                contract.write_text(
                    contract.read_text(encoding="utf-8") + "\n" + extra + "\n",
                    encoding="utf-8",
                )
                findings = check_autonomous_prompt_surface(root)
                self.assertTrue(any("indirect local prompt references" in finding for finding in findings))

    def test_autonomous_prompt_budget_and_semantic_anchors_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical_fixture(root)
            contract = (
                root
                / "src/skills/goal-to-delivery/references"
                / AUTONOMOUS_RUNTIME_REFERENCE
            )
            contract.write_text("# Compact\n", encoding="utf-8")
            findings = check_autonomous_prompt_surface(root)
            self.assertTrue(any("missing semantic anchors" in finding for finding in findings))

            contract.write_text(
                contract.read_text(encoding="utf-8")
                + ("x" * (AUTONOMOUS_PROMPT_BUDGET_BYTES + 1)),
                encoding="utf-8",
            )
            findings = check_autonomous_prompt_surface(root)
            self.assertTrue(any("exceeds 8192 UTF-8 bytes" in finding for finding in findings))

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
            write(
                root,
                "src/skills/goal-to-delivery/references/artifact-contract.md",
                "docs-ai/<work-key>-<slug>/ docs-ai/history historical read fallback never rename, rewrite",
            )
            write(root, "src/agents/planner.md", "Use docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/")
            findings = check_artifact_layout(root)
            self.assertTrue(any("active producer/consumer" in finding for finding in findings))

    def test_entry_policy_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(
                root,
                "src/skills/goal-to-delivery/SKILL.md",
                "semi-autonomous automatic working-tree queue selection never mode: autonomous",
            )
            write(
                root,
                "src/skills/spec-driven-delivery/SKILL.md",
                "manual exactly one without automatic advancement one focused question reject mode: autonomous",
            )
            linear = write(
                root,
                "src/skills/linear-delivery-loop/SKILL.md",
                "autonomous PreparedIteration capability deterministic adapter queue-selection "
                "does not implement selection or mutation",
            )
            self.assertEqual([], check_entry_policies(root))
            linear.write_text("autonomous helper", encoding="utf-8")
            self.assertTrue(check_entry_policies(root))

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
                "planner product-designer tasker auditor matching implementer code-reviewer qa docs-as-code",
            )
            for agent in specialists:
                anchors = ""
                if agent == "auditor":
                    anchors = "independent pre-implementation read-only"
                elif agent == "code-reviewer":
                    anchors = "exact diff review qa"
                elif agent == "qa":
                    anchors = "real behavior do not fix defects"
                write(root, f"src/agents/{agent}.md", anchors)
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
                "do not choose a policy; do not select work",
            )
            self.assertEqual([], check_shared_specialists_and_routing(root))
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
            (root / "src/project-templates").mkdir(parents=True)

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
