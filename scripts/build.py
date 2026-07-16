from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"
SKILL_REF_PATTERN = re.compile(r"\$([a-z0-9][a-z0-9-]*)")


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
        f'name = {json.dumps(meta["name"])}\n'
        f'description = {json.dumps(meta["description"])}\n'
        f'model = {json.dumps(meta["codex_model"])}\n'
        f'model_reasoning_effort = {json.dumps(meta["codex_model_reasoning_effort"])}\n'
        f'sandbox_mode = {json.dumps(meta["codex_sandbox_mode"])}\n\n'
        'developer_instructions = """\n'
        f"{body.rstrip()}\n"
        '"""\n'
    )


def render_claude_agent(meta: dict[str, str], body: str) -> str:
    lines = [
        "---",
        f'name: {json.dumps(meta["name"])}',
        f'description: {json.dumps(meta["description"])}',
        f'model: {json.dumps(meta.get("claude_model", "inherit"))}',
    ]
    if meta.get("claude_effort"):
        lines.append(f'effort: {json.dumps(meta["claude_effort"])}')
    if meta.get("claude_disallowed_tools"):
        lines.append(f'disallowedTools: {json.dumps(meta["claude_disallowed_tools"])}')
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.rstrip() + "\n"


def render_copilot_agent(meta: dict[str, str], body: str) -> str:
    return (
        "---\n"
        f'name: {json.dumps(meta["name"])}\n'
        f'description: {json.dumps(meta["description"])}\n'
        "infer: true\n"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def render_cursor_rule(meta: dict[str, str], body: str) -> str:
    return (
        "---\n"
        f'description: {json.dumps(meta["description"])}\n'
        "alwaysApply: false\n"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def validate_project_template_skills() -> None:
    available_skills = {path.name for path in (SRC / "skills").iterdir() if path.is_dir()}
    errors: list[str] = []

    for template_path in sorted((SRC / "project-templates").rglob("*")):
        if not template_path.is_file():
            continue
        for skill_id in sorted(set(SKILL_REF_PATTERN.findall(template_path.read_text(encoding="utf-8")))):
            if skill_id not in available_skills:
                errors.append(f"{template_path}: references unknown skill id ${skill_id}.")

    if errors:
        raise ValueError("Project template skill validation failed:\n" + "\n".join(errors))


def validate_agent_fields() -> None:
    required = ("name", "description", "codex_model", "codex_model_reasoning_effort", "codex_sandbox_mode")
    errors: list[str] = []

    for agent_path in sorted((SRC / "agents").glob("*.md")):
        meta, _ = parse_frontmatter(agent_path.read_text(encoding="utf-8"))
        missing = [field for field in required if not meta.get(field)]
        if missing:
            errors.append(f"{agent_path.name}: missing required frontmatter {', '.join(missing)}.")
        if meta.get("claude_effort") and not meta.get("claude_model"):
            errors.append(f"{agent_path.name}: claude_effort requires claude_model.")

    if errors:
        raise ValueError("Agent frontmatter validation failed:\n" + "\n".join(errors))


def rebuild_dist() -> None:
    validate_project_template_skills()
    validate_agent_fields()

    if DIST.exists():
        shutil.rmtree(DIST)

    (DIST / "codex" / "agents").mkdir(parents=True, exist_ok=True)
    (DIST / "codex" / "skills").mkdir(parents=True, exist_ok=True)
    (DIST / "claude" / "agents").mkdir(parents=True, exist_ok=True)
    (DIST / "claude" / "skills").mkdir(parents=True, exist_ok=True)
    (DIST / "copilot" / "agents").mkdir(parents=True, exist_ok=True)
    (DIST / "copilot" / "skills").mkdir(parents=True, exist_ok=True)
    (DIST / "cursor" / "rules").mkdir(parents=True, exist_ok=True)
    (DIST / "project-templates" / "codex").mkdir(parents=True, exist_ok=True)
    (DIST / "project-templates" / "claude").mkdir(parents=True, exist_ok=True)
    (DIST / "project-templates" / "copilot" / ".github").mkdir(parents=True, exist_ok=True)
    (DIST / "project-templates" / "cursor").mkdir(parents=True, exist_ok=True)

    for agent_path in sorted((SRC / "agents").glob("*.md")):
        meta, body = parse_frontmatter(agent_path.read_text(encoding="utf-8"))
        codex_text = render_codex_toml(meta, body)
        claude_text = render_claude_agent(meta, body)
        copilot_text = render_copilot_agent(meta, body)
        cursor_text = render_cursor_rule(meta, body)
        (DIST / "codex" / "agents" / f"{agent_path.stem}.toml").write_text(codex_text, encoding="utf-8")
        (DIST / "claude" / "agents" / f"{agent_path.stem}.md").write_text(claude_text, encoding="utf-8")
        (DIST / "copilot" / "agents" / f"{agent_path.stem}.agent.md").write_text(copilot_text, encoding="utf-8")
        (DIST / "cursor" / "rules" / f"{agent_path.stem}.mdc").write_text(cursor_text, encoding="utf-8")

    for skill_dir in sorted((SRC / "skills").iterdir()):
        if skill_dir.is_dir():
            shutil.copytree(skill_dir, DIST / "codex" / "skills" / skill_dir.name)
            shutil.copytree(skill_dir, DIST / "claude" / "skills" / skill_dir.name)
            shutil.copytree(skill_dir, DIST / "copilot" / "skills" / skill_dir.name)

    codex_template = SRC / "project-templates" / "codex" / "AGENTS.md"
    claude_template = SRC / "project-templates" / "claude" / "CLAUDE.md"
    copilot_template = SRC / "project-templates" / "copilot" / ".github" / "copilot-instructions.md"
    cursor_template = SRC / "project-templates" / "cursor" / "AGENTS.md"
    if codex_template.exists():
        shutil.copy2(codex_template, DIST / "project-templates" / "codex" / "AGENTS.md")
    if claude_template.exists():
        shutil.copy2(claude_template, DIST / "project-templates" / "claude" / "CLAUDE.md")
    if copilot_template.exists():
        shutil.copy2(copilot_template, DIST / "project-templates" / "copilot" / ".github" / "copilot-instructions.md")
    if cursor_template.exists():
        shutil.copy2(cursor_template, DIST / "project-templates" / "cursor" / "AGENTS.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Codex, Claude, Copilot, and Cursor adapters from canonical AI config sources.")
    parser.parse_args()
    rebuild_dist()
    print("Built adapters into dist/.")


if __name__ == "__main__":
    main()
