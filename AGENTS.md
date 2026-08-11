# AI Toolkit Repo Instructions

Use this repo as the source of truth for shared AI agents, skills, project-local workflow templates, and generated tool adapters.

Read [docs/external-tools.md](C:/dev/luchdom/ai-toolkit/docs/external-tools.md) when the user asks to install recommended external skills, MCP servers, agents, or supporting CLIs from the links tracked by this repo.

## Delivery workflow ownership

- Exactly three user-facing delivery entries exist: `$goal-to-delivery`, `$spec-driven-delivery`, and `$linear-delivery-loop`.
- For non-trivial work without an explicit entry, default to manual `$spec-driven-delivery`; execute only the requested stage and never infer implementation or publication authority.
- The sole canonical cross-tool protocol is under `src/skills/goal-to-delivery/references/`. Other entry skills and project templates link to it rather than copying it.
- Repositories own their project-specific commands, domain rules, definitions of done, and stricter safety constraints.
- Precedence is user/system requirements and repository-specific stricter safety, then the explicitly invoked entry policy, then the canonical shared contract. Unresolved conflict fails closed before implementation or external mutation.
- New work may use `docs-ai/<work-key>-<slug>/` for concise durable evidence. The helper is optional; existing historical artifacts must not be rewritten.
- `feature-driver` is a deprecated one-migration-cycle semi-autonomous alias only. It never routes autonomous work.
- The MVP autonomous entry uses Linear as its durable queue and `.ai/loop.json` as project configuration; it does not require a separate supervisor or memory service.

## When asked to install or sync the AI toolkit

1. Run `python .\scripts\build.py` from the repo root.
2. Run `python .\scripts\sync.py --tool <codex|claude|copilot|cursor|all>`.
3. If the user wants project-local instruction files, add `--project <path>`.
4. `scripts\sync.py` resolves `{{LUCHDOM_AI_TOOLKIT_DOCS}}` in project templates from `LUCHDOM_AI_TOOLKIT_DOCS` when it is set, otherwise from the legacy `LUCHDOM_AI_CONFIG_DOCS` name or this repo's local `docs` folder.
5. `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` are marker-managed: normal sync emits `<!-- AI-TOOLKIT-LUCHDOM:START -->` and `:END`, accepts and migrates the legacy `AI-CONFIG-LUCHDOM` markers, and preserves content outside them. Existing unmarked files remain untouched unless `--force` explicitly adopts them. Generated agents, skills, and Cursor rules remain skip-unless-`--force`.
6. Verify the installed files exist after sync.

## Preferred behavior

- Prefer the scripts in this repo over manual copying.
- Treat `src/` as canonical and `dist/` as generated output.
- When the user says "install for me" without specifying a tool, default to `python .\scripts\sync.py --tool all`.
- If changing shared agents or skills, update `src/` and regenerate `dist/` instead of editing generated files directly.
- If changing shared project-local guidance, update the relevant files under `src/project-templates/`.
- Project-local templates route the three explicit entries into the canonical shared protocol and default unspecified non-trivial work to manual stage control.
- When asked to install external tools referenced by this repo, follow `docs/external-tools.md` in the listed order and prefer official install commands from the linked sources.
- Copilot support in this repo uses user-level `~/.copilot/agents` and `~/.copilot/skills`, plus project-level `.github/agents`, `.github/skills`, and `.github/copilot-instructions.md`.
- Cursor support in this repo is project-level only. Generate `AGENTS.md` plus `.cursor/rules/*.mdc` into the target repo when the user asks for Cursor support.
