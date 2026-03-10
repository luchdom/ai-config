from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("Agent source must start with YAML-like frontmatter.")

    try:
        _, raw_frontmatter, body = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError("Invalid frontmatter block.") from exc

    meta: dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = json.loads(value)
        meta[key.strip()] = value
    return meta, body.lstrip("\n")


def render_codex_toml(meta: dict[str, str], body: str) -> str:
    return (
        f'model = {json.dumps(meta["codex_model"])}\n'
        f'model_reasoning_effort = {json.dumps(meta["codex_model_reasoning_effort"])}\n'
        f'sandbox_mode = {json.dumps(meta["codex_sandbox_mode"])}\n\n'
        'developer_instructions = """\n'
        f"{body.rstrip()}\n"
        '"""\n'
    )


def render_claude_agent(meta: dict[str, str], body: str) -> str:
    return (
        "---\n"
        f'name: {json.dumps(meta["name"])}\n'
        f'description: {json.dumps(meta["description"])}\n'
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def rebuild_dist() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)

    (DIST / "codex" / "agents").mkdir(parents=True, exist_ok=True)
    (DIST / "codex" / "skills").mkdir(parents=True, exist_ok=True)
    (DIST / "claude" / "agents").mkdir(parents=True, exist_ok=True)
    (DIST / "claude" / "skills").mkdir(parents=True, exist_ok=True)
    (DIST / "project-templates" / "codex").mkdir(parents=True, exist_ok=True)
    (DIST / "project-templates" / "claude").mkdir(parents=True, exist_ok=True)

    for agent_path in sorted((SRC / "agents").glob("*.md")):
        meta, body = parse_frontmatter(agent_path.read_text(encoding="utf-8"))
        codex_text = render_codex_toml(meta, body)
        claude_text = render_claude_agent(meta, body)
        (DIST / "codex" / "agents" / f"{agent_path.stem}.toml").write_text(codex_text, encoding="utf-8")
        (DIST / "claude" / "agents" / f"{agent_path.stem}.md").write_text(claude_text, encoding="utf-8")

    for skill_dir in sorted((SRC / "skills").iterdir()):
        if skill_dir.is_dir():
            shutil.copytree(skill_dir, DIST / "codex" / "skills" / skill_dir.name)
            shutil.copytree(skill_dir, DIST / "claude" / "skills" / skill_dir.name)

    codex_template = SRC / "project-templates" / "codex" / "AGENTS.md"
    claude_template = SRC / "project-templates" / "claude" / "CLAUDE.md"
    if codex_template.exists():
        shutil.copy2(codex_template, DIST / "project-templates" / "codex" / "AGENTS.md")
    if claude_template.exists():
        shutil.copy2(claude_template, DIST / "project-templates" / "claude" / "CLAUDE.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Codex and Claude adapters from canonical AI config sources.")
    parser.parse_args()
    rebuild_dist()
    print("Built adapters into dist/.")


if __name__ == "__main__":
    main()

