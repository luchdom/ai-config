# ai-config

Central AI configuration repo for Codex, Claude Code, GitHub Copilot CLI, and Cursor.

## Goals

- Keep skills as the reusable cross-tool unit.
- Keep agent prompts versioned in one place.
- Generate tool-specific adapters instead of hand-maintaining multiple copies.
- Sync agents, skills, and small project-local instruction files into Codex, Claude, Copilot CLI, and Cursor workflows.

## Layout

- `src/agents/`: canonical agent definitions in Markdown with simple frontmatter
- `src/skills/`: canonical skills copied as reusable cross-tool units
- `src/project-templates/`: small project-local instruction file templates
- `scripts/build.py`: generate Codex, Claude, Copilot, and Cursor adapters into `dist/`
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
- `dist/copilot/agents/*.agent.md`
- `dist/cursor/rules/*.mdc`

Skills are copied into:

- `dist/codex/skills/*`
- `dist/claude/skills/*`
- `dist/copilot/skills/*`

## Usage

Bootstrap from the current global Codex setup:

```powershell
python .\scripts\bootstrap_existing.py
```

Generate adapters:

```powershell
python .\scripts\build.py
```

Install global outputs for Codex, Claude, Copilot, and project-capable Cursor adapters:

```powershell
python .\scripts\sync.py --tool all
```

Install the small project-local instruction files into a repo:

```powershell
python .\scripts\sync.py --tool all --project C:\dev\luchdom\identity
```

Install only Copilot or Cursor adapters:

```powershell
python .\scripts\sync.py --tool copilot
python .\scripts\sync.py --tool cursor --project C:\dev\luchdom\identity
```

## If an AI agent is asked to install this repo

Preferred flow:

```powershell
python .\scripts\build.py
python .\scripts\sync.py --tool all
```

If a specific tool is requested:

```powershell
python .\scripts\sync.py --tool codex
python .\scripts\sync.py --tool claude
python .\scripts\sync.py --tool copilot
python .\scripts\sync.py --tool cursor --project C:\path\to\repo
```

If project-local instruction files are also needed:

```powershell
python .\scripts\sync.py --tool all --project C:\path\to\repo
```

Guidance:

- Prefer the repo scripts over manual copying.
- Treat `src/` as the source of truth and `dist/` as generated output.
- Do not overwrite existing project-local `AGENTS.md` or `CLAUDE.md` unless explicitly asked or `--force` is intended.
- Verify the installed files after sync.
- Copilot supports global user-level agents and skills via `~/.copilot`.
- Cursor support in this repo is project-level: generated `AGENTS.md` and `.cursor/rules/*.mdc`.

## Notes

- `sync.py` only manages the generated agents and skills from this repo. It does not touch unrelated items such as Codex system skills.
- Project-local templates are intentionally small. Put shared workflows in skills and keep repo-specific rules in the project files.
- For recommended external skills, MCPs, and supporting CLIs, see [docs/external-tools.md](C:/dev/luchdom/ai-config/docs/external-tools.md).
