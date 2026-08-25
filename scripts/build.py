from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"
SKILL_REF_PATTERN = re.compile(r"\$([a-z0-9][a-z0-9-]*)")
MANIFEST_VERSION = 1
CURSOR_RULE_PATH_REPLACEMENTS = (
    ("`$ui-review-spec`", "the `.cursor/rules/ui-review-spec.mdc` rule"),
    ("../goal-to-delivery/references/design-gates.md", "./ui-design-gates.mdc"),
    ("./references/design-review-template.md", "./ui-design-review-template.mdc"),
    ("./references/spec-template.md", "./ui-design-spec-template.mdc"),
    ("./references/ui-audit-checklist.md", "./ui-audit-checklist.mdc"),
    ("./references/component-selection.md", "./ui-component-selection.mdc"),
    ("goal-to-delivery/references/design-gates.md", ".cursor/rules/ui-design-gates.mdc"),
    ("`design-gates.md`", "`.cursor/rules/ui-design-gates.mdc`"),
)


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
    for source, destination in CURSOR_RULE_PATH_REPLACEMENTS:
        body = body.replace(source, destination)
    return (
        "---\n"
        f'description: {json.dumps(meta["description"])}\n'
        "alwaysApply: false\n"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def validate_tool_instruction_skills() -> None:
    available_skills = {path.name for path in (SRC / "skills").iterdir() if path.is_dir()}
    errors: list[str] = []

    for instruction_path in sorted((SRC / "tool-instructions").rglob("*")):
        if not instruction_path.is_file():
            continue
        for skill_id in sorted(set(SKILL_REF_PATTERN.findall(instruction_path.read_text(encoding="utf-8")))):
            if skill_id not in available_skills:
                errors.append(f"{instruction_path}: references unknown skill id ${skill_id}.")

    if errors:
        raise ValueError("Tool instruction skill validation failed:\n" + "\n".join(errors))


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def write_projection_manifest(projections: dict[Path, list[Path]]) -> None:
    """Record exactly which canonical source produced each generated file."""
    entries: list[dict[str, object]] = []
    for source in sorted(projections, key=lambda path: path.as_posix()):
        outputs = sorted(projections[source], key=lambda path: path.as_posix())
        entries.append(
            {
                "source": source.relative_to(ROOT).as_posix(),
                "sourceSha256": file_sha256(source),
                "projections": [
                    {
                        "path": output.relative_to(ROOT).as_posix(),
                        "sha256": file_sha256(output),
                    }
                    for output in outputs
                ],
            }
        )
    manifest = {
        "schemaVersion": MANIFEST_VERSION,
        "canonicalRoot": "src",
        "generatedRoot": "dist",
        "entries": entries,
    }
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def rebuild_dist() -> None:
    validate_tool_instruction_skills()
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
    (DIST / "tool-instructions" / "codex").mkdir(parents=True, exist_ok=True)
    (DIST / "tool-instructions" / "claude").mkdir(parents=True, exist_ok=True)
    (DIST / "tool-instructions" / "copilot" / ".github").mkdir(parents=True, exist_ok=True)
    (DIST / "tool-instructions" / "cursor").mkdir(parents=True, exist_ok=True)

    projections: dict[Path, list[Path]] = {}

    for agent_path in sorted((SRC / "agents").glob("*.md")):
        meta, body = parse_frontmatter(agent_path.read_text(encoding="utf-8"))
        codex_text = render_codex_toml(meta, body)
        claude_text = render_claude_agent(meta, body)
        copilot_text = render_copilot_agent(meta, body)
        cursor_text = render_cursor_rule(meta, body)
        outputs = [
            DIST / "codex" / "agents" / f"{agent_path.stem}.toml",
            DIST / "claude" / "agents" / f"{agent_path.stem}.md",
            DIST / "copilot" / "agents" / f"{agent_path.stem}.agent.md",
            DIST / "cursor" / "rules" / f"{agent_path.stem}.mdc",
        ]
        for output, content in zip(outputs, (codex_text, claude_text, copilot_text, cursor_text), strict=True):
            output.write_text(content, encoding="utf-8")
        projections[agent_path] = outputs

    for skill_dir in sorted((SRC / "skills").iterdir()):
        if skill_dir.is_dir():
            destinations = [
                DIST / "codex" / "skills" / skill_dir.name,
                DIST / "claude" / "skills" / skill_dir.name,
                DIST / "copilot" / "skills" / skill_dir.name,
            ]
            for destination in destinations:
                shutil.copytree(skill_dir, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for source in sorted(
                path
                for path in skill_dir.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
            ):
                relative = source.relative_to(skill_dir)
                projections[source] = [destination / relative for destination in destinations]

    cursor_support_rules = (
        (
            SRC / "skills" / "goal-to-delivery" / "references" / "design-gates.md",
            "ui-design-gates.mdc",
            "Binding frontend/UI design gates for planning, implementation, and rendered conformance review.",
            False,
        ),
        (
            SRC / "skills" / "ui-review-spec" / "SKILL.md",
            "ui-review-spec.mdc",
            "Produce a pre-build UI design specification or post-build rendered design-conformance review.",
            True,
        ),
        (
            SRC / "skills" / "ui-review-spec" / "references" / "spec-template.md",
            "ui-design-spec-template.mdc",
            "Output template for an implementer-ready UI design specification.",
            False,
        ),
        (
            SRC / "skills" / "ui-review-spec" / "references" / "design-review-template.md",
            "ui-design-review-template.mdc",
            "Output template for a rendered UI design-conformance verdict.",
            False,
        ),
        (
            SRC / "skills" / "ui-review-spec" / "references" / "ui-audit-checklist.md",
            "ui-audit-checklist.mdc",
            "Checklist for UI hierarchy, states, accessibility, responsiveness, and conformance evidence.",
            False,
        ),
        (
            SRC / "skills" / "ui-review-spec" / "references" / "component-selection.md",
            "ui-component-selection.mdc",
            "Repository-first component and design-system selection rules.",
            False,
        ),
    )
    for source, output_name, description, has_frontmatter in cursor_support_rules:
        source_text = source.read_text(encoding="utf-8")
        if has_frontmatter:
            source_meta, body = parse_frontmatter(source_text)
            description = source_meta["description"]
        else:
            body = source_text
        output = DIST / "cursor" / "rules" / output_name
        output.write_text(render_cursor_rule({"description": description}, body), encoding="utf-8")
        projections.setdefault(source, []).append(output)

    codex_instruction = SRC / "tool-instructions" / "codex" / "AGENTS.md"
    claude_instruction = SRC / "tool-instructions" / "claude" / "CLAUDE.md"
    copilot_instruction = SRC / "tool-instructions" / "copilot" / ".github" / "copilot-instructions.md"
    cursor_instruction = SRC / "tool-instructions" / "cursor" / "AGENTS.md"
    if codex_instruction.exists():
        output = DIST / "tool-instructions" / "codex" / "AGENTS.md"
        shutil.copy2(codex_instruction, output)
        projections[codex_instruction] = [output]
    if claude_instruction.exists():
        output = DIST / "tool-instructions" / "claude" / "CLAUDE.md"
        shutil.copy2(claude_instruction, output)
        projections[claude_instruction] = [output]
    if copilot_instruction.exists():
        output = DIST / "tool-instructions" / "copilot" / ".github" / "copilot-instructions.md"
        shutil.copy2(copilot_instruction, output)
        projections[copilot_instruction] = [output]
    if cursor_instruction.exists():
        output = DIST / "tool-instructions" / "cursor" / "AGENTS.md"
        shutil.copy2(cursor_instruction, output)
        projections[cursor_instruction] = [output]

    write_projection_manifest(projections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Codex, Claude, Copilot, and Cursor adapters from canonical AI config sources.")
    parser.parse_args()
    rebuild_dist()
    print("Built adapters into dist/.")


if __name__ == "__main__":
    main()
