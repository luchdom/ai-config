from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"
SRC_AGENTS = ROOT / "src" / "agents"
SRC_SKILLS = ROOT / "src" / "skills"
SRC_TEMPLATES = ROOT / "src" / "project-templates"


def ensure_clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_agent_descriptions() -> dict[str, str]:
    config_path = CODEX_HOME / "config.toml"
    if not config_path.exists():
        return {}

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    descriptions: dict[str, str] = {}
    for _, value in data.get("agents", {}).items():
        if isinstance(value, dict) and "config_file" in value:
            stem = Path(value["config_file"]).stem
            descriptions[stem] = value.get("description", "")
    return descriptions


def write_agent_sources() -> None:
    ensure_clean_dir(SRC_AGENTS)
    descriptions = load_agent_descriptions()

    for toml_path in sorted((CODEX_HOME / "agents").glob("*.toml")):
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        body = data["developer_instructions"].rstrip() + "\n"
        description = descriptions.get(toml_path.stem, f"{toml_path.stem} agent")
        frontmatter = "\n".join(
            [
                "---",
                f'name: {json.dumps(toml_path.stem)}',
                f'description: {json.dumps(description)}',
                f'codex_model: {json.dumps(data["model"])}',
                f'codex_model_reasoning_effort: {json.dumps(data["model_reasoning_effort"])}',
                f'codex_sandbox_mode: {json.dumps(data["sandbox_mode"])}',
                "---",
                "",
            ]
        )
        (SRC_AGENTS / f"{toml_path.stem}.md").write_text(frontmatter + body, encoding="utf-8")


def write_skill_sources() -> None:
    ensure_clean_dir(SRC_SKILLS)
    for skill_dir in sorted((CODEX_HOME / "skills").iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        target = SRC_SKILLS / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)


def write_project_templates() -> None:
    codex_dir = SRC_TEMPLATES / "codex"
    claude_dir = SRC_TEMPLATES / "claude"
    codex_dir.mkdir(parents=True, exist_ok=True)
    claude_dir.mkdir(parents=True, exist_ok=True)

    (codex_dir / "AGENTS.md").write_text(
        "# Project AI Instructions\n\n"
        "- Keep project-specific rules here.\n"
        "- Keep reusable workflows in the shared ai-config skills.\n"
        "- Follow this repo's docs, architecture notes, and established patterns before coding.\n"
        "- Prefer existing components, abstractions, and tests over new ones.\n",
        encoding="utf-8",
    )

    (claude_dir / "CLAUDE.md").write_text(
        "# Project AI Instructions\n\n"
        "- Keep project-specific rules here.\n"
        "- Keep reusable workflows in the shared ai-config skills.\n"
        "- Read this repo's docs, architecture notes, and established patterns before coding.\n"
        "- Prefer existing components, abstractions, and tests over new ones.\n",
        encoding="utf-8",
    )


def main() -> None:
    write_agent_sources()
    write_skill_sources()
    write_project_templates()
    print("Bootstrapped existing Codex agents, skills, and project templates into src/.")


if __name__ == "__main__":
    main()

