from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
MARKER_START = "<!-- AI-TOOLKIT-LUCHDOM:START -->"
MARKER_END = "<!-- AI-TOOLKIT-LUCHDOM:END -->"
LEGACY_MARKER_PAIRS = (("<!-- AI-CONFIG-LUCHDOM:START -->", "<!-- AI-CONFIG-LUCHDOM:END -->"),)


def run_build() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True)


def sync_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"Copied {src} -> {dest}")


def resolve_docs_root() -> str:
    override = os.environ.get("LUCHDOM_AI_TOOLKIT_DOCS") or os.environ.get("LUCHDOM_AI_CONFIG_DOCS")
    if override:
        return Path(override).expanduser().resolve().as_posix()
    return (ROOT / "docs").resolve().as_posix()


def render_template_text(src: Path) -> str:
    docs_root = resolve_docs_root()
    with open(src, "r", encoding="utf-8", newline="") as file:
        return (
            file.read()
            .replace("{{LUCHDOM_AI_TOOLKIT_DOCS}}", docs_root)
            .replace("{{LUCHDOM_AI_CONFIG_DOCS}}", docs_root)
        )


def consume_newline(text: str, position: int) -> int:
    if text[position:position + 2] == "\r\n":
        return position + 2
    if text[position:position + 1] == "\n":
        return position + 1
    return position


def write_or_splice_template(src: Path, dest: Path, force: bool) -> str:
    """Render a new managed file or refresh only its marker-owned content."""
    rendered = render_template_text(src)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        with open(dest, "w", encoding="utf-8", newline="") as file:
            file.write(rendered)
        print(f"Rendered {dest} (new)")
        return "new"

    if force:
        with open(dest, "w", encoding="utf-8", newline="") as file:
            file.write(rendered)
        print(f"Overwrote {dest} (--force; now marker-managed)")
        return "overwrote"

    with open(dest, "r", encoding="utf-8", newline="") as file:
        existing = file.read()

    marker_spans: list[tuple[int, int, int, int]] = []
    for start_marker, end_marker in ((MARKER_START, MARKER_END), *LEGACY_MARKER_PAIRS):
        start_positions = [match.start() for match in re.finditer(re.escape(start_marker), existing)]
        end_positions = [match.start() for match in re.finditer(re.escape(end_marker), existing)]
        if not start_positions and not end_positions:
            continue
        if not start_positions or not end_positions:
            print(f"Warning: malformed markers in {dest} (start/end mismatch), skipped")
            return "warning"

        first_start = min(start_positions)
        last_end = max(end_positions)
        if first_start >= last_end:
            print(f"Warning: malformed markers in {dest} (markers out of order), skipped")
            return "warning"
        marker_spans.append((first_start, last_end + len(end_marker), len(start_positions), len(end_positions)))

    if not marker_spans:
        print(f"Skipped existing {dest} (no markers; re-run with --force to adopt)")
        return "skipped"

    first_start = min(span[0] for span in marker_spans)
    last_end = max(span[1] for span in marker_spans)
    if len(marker_spans) > 1 or any(starts > 1 or ends > 1 for _, _, starts, ends in marker_spans):
        print(f"Warning: multiple marker pairs found in {dest}, using outermost")

    prefix = existing[:first_start]
    suffix = existing[consume_newline(existing, last_end):]
    with open(dest, "w", encoding="utf-8", newline="") as file:
        file.write(prefix + rendered + suffix)
    print(f"Spliced {dest} (preserved external content)")
    return "spliced"


def sync_skill_dirs(src_root: Path, dest_root: Path) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    for skill_dir in sorted(src_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        target = dest_root / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        print(f"Synced skill {skill_dir.name} -> {target}")


def sync_codex() -> None:
    codex_home = Path.home() / ".codex"
    for agent_file in sorted((DIST / "codex" / "agents").glob("*.toml")):
        sync_file(agent_file, codex_home / "agents" / agent_file.name)
    sync_skill_dirs(DIST / "codex" / "skills", codex_home / "skills")


def sync_claude() -> None:
    claude_home = Path.home() / ".claude"
    for agent_file in sorted((DIST / "claude" / "agents").glob("*.md")):
        sync_file(agent_file, claude_home / "agents" / agent_file.name)
    sync_skill_dirs(DIST / "claude" / "skills", claude_home / "skills")


def sync_copilot() -> None:
    copilot_home = Path.home() / ".copilot"
    for agent_file in sorted((DIST / "copilot" / "agents").glob("*.agent.md")):
        sync_file(agent_file, copilot_home / "agents" / agent_file.name)
    sync_skill_dirs(DIST / "copilot" / "skills", copilot_home / "skills")


def sync_project_templates(project: Path, tools: set[str], force: bool) -> None:
    project.mkdir(parents=True, exist_ok=True)

    if "codex" in tools:
        target = project / "AGENTS.md"
        write_or_splice_template(DIST / "project-templates" / "codex" / "AGENTS.md", target, force)

    if "claude" in tools:
        target = project / "CLAUDE.md"
        write_or_splice_template(DIST / "project-templates" / "claude" / "CLAUDE.md", target, force)

    if "copilot" in tools:
        target = project / ".github" / "copilot-instructions.md"
        write_or_splice_template(DIST / "project-templates" / "copilot" / ".github" / "copilot-instructions.md", target, force)

        agents_root = project / ".github" / "agents"
        for agent_file in sorted((DIST / "copilot" / "agents").glob("*.agent.md")):
            target = agents_root / agent_file.name
            if force or not target.exists():
                sync_file(agent_file, target)
            else:
                print(f"Skipped existing {target}")

        skills_root = project / ".github" / "skills"
        for skill_dir in sorted((DIST / "copilot" / "skills").iterdir()):
            if not skill_dir.is_dir():
                continue
            target = skills_root / skill_dir.name
            if target.exists():
                if force:
                    shutil.rmtree(target)
                else:
                    print(f"Skipped existing {target}")
                    continue
            shutil.copytree(skill_dir, target)
            print(f"Synced skill {skill_dir.name} -> {target}")

    if "cursor" in tools:
        target = project / "AGENTS.md"
        write_or_splice_template(DIST / "project-templates" / "cursor" / "AGENTS.md", target, force)

        rules_root = project / ".cursor" / "rules"
        for rule_file in sorted((DIST / "cursor" / "rules").glob("*.mdc")):
            target = rules_root / rule_file.name
            if force or not target.exists():
                sync_file(rule_file, target)
            else:
                print(f"Skipped existing {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install generated Codex, Claude, Copilot, and Cursor adapters, skills, and project templates.")
    parser.add_argument("--tool", choices=["codex", "claude", "copilot", "cursor", "all"], default="all")
    parser.add_argument("--project", action="append", default=[], help="Project root to receive local instruction files.")
    parser.add_argument("--no-build", action="store_true", help="Skip rebuilding dist before sync.")
    parser.add_argument("--force", action="store_true", help="Hard-overwrite project instruction files and adopt unmarked legacy files.")
    args = parser.parse_args()

    if not args.no_build:
        run_build()

    tools = {"codex", "claude", "copilot", "cursor"} if args.tool == "all" else {args.tool}

    if "codex" in tools:
        sync_codex()
    if "claude" in tools:
        sync_claude()
    if "copilot" in tools:
        sync_copilot()

    for project in args.project:
        sync_project_templates(Path(project), tools, args.force)


if __name__ == "__main__":
    main()
