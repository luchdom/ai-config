# ai-config

Central AI configuration repo for Codex and Claude Code.

## Goals

- Keep skills as the reusable cross-tool unit.
- Keep agent prompts versioned in one place.
- Generate tool-specific adapters instead of hand-maintaining multiple copies.
- Sync agents, skills, and small project-local instruction files into Codex and Claude environments.

## Layout

- `src/agents/`: canonical agent definitions in Markdown with simple frontmatter
- `src/skills/`: canonical skills copied as reusable cross-tool units
- `src/project-templates/`: small project-local instruction file templates
- `scripts/build.py`: generate Codex and Claude adapters into `dist/`
- `scripts/sync.py`: install generated outputs into user homes and optional project roots
- `scripts/bootstrap_existing.py`: import the current global Codex agents and skills as the starting source set

## Canonical Agent Format

Each file in `src/agents/` uses this shape:

```md
---
name: "planner"
description: "Short agent description"
codex_model: "gpt-5.3-codex"
codex_model_reasoning_effort: "high"
codex_sandbox_mode: "workspace-write"
---
Full instruction body here.
```

The build script generates:

- `dist/codex/agents/*.toml`
- `dist/claude/agents/*.md`

Skills are copied into:

- `dist/codex/skills/*`
- `dist/claude/skills/*`

## Usage

Bootstrap from the current global Codex setup:

```powershell
python .\scripts\bootstrap_existing.py
```

Generate adapters:

```powershell
python .\scripts\build.py
```

Install for Codex and Claude:

```powershell
python .\scripts\sync.py --tool all
```

Install the small project-local instruction files into a repo:

```powershell
python .\scripts\sync.py --tool all --project C:\dev\luchdom\identity
```

## Notes

- `sync.py` only manages the generated agents and skills from this repo. It does not touch unrelated items such as Codex system skills.
- Project-local templates are intentionally small. Put shared workflows in skills and keep repo-specific rules in the project files.

