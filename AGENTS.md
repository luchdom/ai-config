# AI Config Repo Instructions

Use this repo as the source of truth for shared AI agents, skills, and generated tool adapters.

Read [docs/external-tools.md](C:/dev/luchdom/ai-config/docs/external-tools.md) when the user asks to install recommended external skills, MCP servers, agents, or supporting CLIs from the links tracked by this repo.

## When asked to install or sync AI config

1. Run `python .\scripts\build.py` from the repo root.
2. Run `python .\scripts\sync.py --tool <codex|claude|all>`.
3. If the user wants project-local instruction files, add `--project <path>`.
4. Do not overwrite existing project-local `AGENTS.md` or `CLAUDE.md` unless the user explicitly asks for it or `--force` is intended.
5. Verify the installed files exist after sync.

## Preferred behavior

- Prefer the scripts in this repo over manual copying.
- Treat `src/` as canonical and `dist/` as generated output.
- When the user says "install for me" without specifying a tool, default to `python .\scripts\sync.py --tool all`.
- If changing shared agents or skills, update `src/` and regenerate `dist/` instead of editing generated files directly.
- When asked to install external tools referenced by this repo, follow `docs/external-tools.md` in the listed order and prefer official install commands from the linked sources.
