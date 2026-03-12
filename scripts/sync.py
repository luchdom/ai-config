from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def run_build() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True)


def sync_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"Copied {src} -> {dest}")


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
        if force or not target.exists():
            sync_file(DIST / "project-templates" / "codex" / "AGENTS.md", target)
        else:
            print(f"Skipped existing {target}")

    if "claude" in tools:
        target = project / "CLAUDE.md"
        if force or not target.exists():
            sync_file(DIST / "project-templates" / "claude" / "CLAUDE.md", target)
        else:
            print(f"Skipped existing {target}")

    if "copilot" in tools:
        target = project / ".github" / "copilot-instructions.md"
        if force or not target.exists():
            sync_file(DIST / "project-templates" / "copilot" / ".github" / "copilot-instructions.md", target)
        else:
            print(f"Skipped existing {target}")

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
        if force or not target.exists():
            sync_file(DIST / "project-templates" / "cursor" / "AGENTS.md", target)
        else:
            print(f"Skipped existing {target}")

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
    parser.add_argument("--force", action="store_true", help="Overwrite existing project-local instruction files.")
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
