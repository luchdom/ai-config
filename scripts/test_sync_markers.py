"""Dependency-free regression tests for marker-managed tool instructions."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bootstrap_existing  # noqa: E402
import sync  # noqa: E402


BODY = "<!-- AI-TOOLKIT-LUCHDOM:START -->\r\n# Template\r\n<!-- AI-TOOLKIT-LUCHDOM:END -->\r\n"
LEGACY_BODY = "<!-- AI-CONFIG-LUCHDOM:START -->\r\n# Legacy\r\n<!-- AI-CONFIG-LUCHDOM:END -->\r\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(content)


def read(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as file:
        return file.read()


def source(root: Path, content: str = BODY) -> Path:
    path = root / "template.md"
    write(path, content)
    return path


def test_fresh_write_and_splice() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src, dest = source(root), root / "target.md"
        assert sync.write_or_splice_template(src, dest, False) == "new"
        external = "\r\n@RTK.md\r\n<!-- CODEGRAPH_START -->\r\n<!-- CODEGRAPH_END -->\r\n"
        write(dest, read(dest).rstrip("\r\n") + external)
        write(src, BODY.replace("# Template", "# Updated"))
        assert sync.write_or_splice_template(src, dest, False) == "spliced"
        result = read(dest)
        assert "# Updated" in result and result.endswith(external)


def test_legacy_and_force() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src, dest = source(root), root / "target.md"
        write(dest, "# Hand-written\n")
        assert sync.write_or_splice_template(src, dest, False) == "skipped"
        assert sync.write_or_splice_template(src, dest, True) == "overwrote"

        write(dest, LEGACY_BODY.rstrip("\r\n") + "\r\n@RTK.md\r\n")
        assert sync.write_or_splice_template(src, dest, False) == "spliced"
        result = read(dest)
        assert sync.MARKER_START in result
        assert "AI-CONFIG-LUCHDOM" not in result
        assert result.endswith("\r\n@RTK.md\r\n")


def test_malformed_and_newline_preservation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src, dest = source(root), root / "target.md"
        write(dest, "<!-- AI-TOOLKIT-LUCHDOM:START -->\n")
        assert sync.write_or_splice_template(src, dest, False) == "warning"
        write(dest, BODY.rstrip("\r\n") + "\n@RTK.md\n")
        assert sync.write_or_splice_template(src, dest, False) == "spliced"
        assert read(dest).endswith("\n@RTK.md\n")


def test_docs_override_prefers_toolkit_and_supports_legacy() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src = source(root, "{{LUCHDOM_AI_TOOLKIT_DOCS}}|{{LUCHDOM_AI_CONFIG_DOCS}}")
        toolkit_docs = root / "toolkit-docs"
        legacy_docs = root / "legacy-docs"

        with mock.patch.dict(
            "os.environ",
            {
                "LUCHDOM_AI_TOOLKIT_DOCS": str(toolkit_docs),
                "LUCHDOM_AI_CONFIG_DOCS": str(legacy_docs),
            },
            clear=True,
        ):
            rendered = sync.render_template_text(src)
            expected = toolkit_docs.resolve().as_posix()
            assert rendered == f"{expected}|{expected}"

        with mock.patch.dict("os.environ", {"LUCHDOM_AI_CONFIG_DOCS": str(legacy_docs)}, clear=True):
            rendered = sync.render_template_text(src)
            expected = legacy_docs.resolve().as_posix()
            assert rendered == f"{expected}|{expected}"


def test_project_help_names_tool_instruction_destination() -> None:
    result = subprocess.run(
        [sys.executable, str(Path(sync.__file__)), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Destination project root to receive tool instructions." in result.stdout


def test_sync_tool_instructions_reads_renamed_dist_root() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        dist = root / "dist"
        instruction = dist / "tool-instructions" / "codex" / "AGENTS.md"
        write(instruction, BODY)
        project = root / "project"
        with mock.patch.object(sync, "DIST", dist):
            sync.sync_tool_instructions(project, {"codex"}, False)
        assert read(project / "AGENTS.md") == BODY


def test_cursor_project_receives_design_support_rules() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        dist = root / "dist"
        write(dist / "tool-instructions" / "cursor" / "AGENTS.md", BODY)
        rule_names = (
            "product-designer.mdc",
            "ui-design-gates.mdc",
            "ui-review-spec.mdc",
            "ui-design-spec-template.mdc",
            "ui-design-review-template.mdc",
            "ui-audit-checklist.mdc",
            "ui-component-selection.mdc",
        )
        for rule_name in rule_names:
            write(dist / "cursor" / "rules" / rule_name, f"# {rule_name}\n")

        project = root / "project"
        with mock.patch.object(sync, "DIST", dist):
            sync.sync_tool_instructions(project, {"cursor"}, False)

        assert read(project / "AGENTS.md") == BODY
        assert all((project / ".cursor" / "rules" / rule_name).is_file() for rule_name in rule_names)


def test_bootstrap_writes_tool_instruction_source_tree() -> None:
    with tempfile.TemporaryDirectory() as directory:
        source_root = Path(directory) / "src" / "tool-instructions"
        with mock.patch.object(bootstrap_existing, "SRC_TOOL_INSTRUCTIONS", source_root):
            bootstrap_existing.write_tool_instructions()
        expected = (
            source_root / "codex" / "AGENTS.md",
            source_root / "claude" / "CLAUDE.md",
            source_root / "copilot" / ".github" / "copilot-instructions.md",
            source_root / "cursor" / "AGENTS.md",
        )
        assert all(path.is_file() for path in expected)


def main() -> int:
    tests = (
        test_fresh_write_and_splice,
        test_legacy_and_force,
        test_malformed_and_newline_preservation,
        test_docs_override_prefers_toolkit_and_supports_legacy,
        test_project_help_names_tool_instruction_destination,
        test_sync_tool_instructions_reads_renamed_dist_root,
        test_cursor_project_receives_design_support_rules,
        test_bootstrap_writes_tool_instruction_source_tree,
    )
    for test in tests:
        test()
        print(f"{test.__name__}: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
