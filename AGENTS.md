# AI Config Repo Instructions

Use this repo as the source of truth for shared AI agents, skills, project-local workflow templates, and generated tool adapters.

Read [docs/external-tools.md](C:/dev/luchdom/ai-config/docs/external-tools.md) when the user asks to install recommended external skills, MCP servers, agents, or supporting CLIs from the links tracked by this repo.

## When asked to install or sync AI config

1. Run `python .\scripts\build.py` from the repo root.
2. Run `python .\scripts\sync.py --tool <codex|claude|copilot|cursor|all>`.
3. If the user wants project-local instruction files, add `--project <path>`.
4. `scripts\sync.py` resolves `{{LUCHDOM_AI_CONFIG_DOCS}}` in project templates from `LUCHDOM_AI_CONFIG_DOCS` when it is set, otherwise from this repo's local `docs` folder.
5. `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` are marker-managed: normal sync refreshes only the content between `<!-- AI-CONFIG-LUCHDOM:START -->` and `:END`, preserving content outside the markers. Existing unmarked files remain untouched unless `--force` explicitly adopts them. Generated agents, skills, and Cursor rules remain skip-unless-`--force`.
6. Verify the installed files exist after sync.

## Preferred behavior

- Prefer the scripts in this repo over manual copying.
- Treat `src/` as canonical and `dist/` as generated output.
- When the user says "install for me" without specifying a tool, default to `python .\scripts\sync.py --tool all`.
- If changing shared agents or skills, update `src/` and regenerate `dist/` instead of editing generated files directly.
- If changing shared project-local guidance, update the relevant files under `src/project-templates/`.
- Project-local templates define the shared docs-ai workflow: plan, clarify, task, independent audit, implement after explicit user approval, then QA verification.
- When asked to install external tools referenced by this repo, follow `docs/external-tools.md` in the listed order and prefer official install commands from the linked sources.
- Copilot support in this repo uses user-level `~/.copilot/agents` and `~/.copilot/skills`, plus project-level `.github/agents`, `.github/skills`, and `.github/copilot-instructions.md`.
- Cursor support in this repo is project-level only. Generate `AGENTS.md` plus `.cursor/rules/*.mdc` into the target repo when the user asks for Cursor support.
