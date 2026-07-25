# ai-config

Central AI configuration for Codex, Claude Code, GitHub Copilot CLI, and Cursor.

## Purpose

- Keep reusable workflow policy and specialist skills in one canonical `src/` tree.
- Reuse one agent set across autonomous, semi-autonomous, and manual delivery.
- Generate tool-specific adapters instead of maintaining divergent copies.
- Sync shared agents, skills, and small project-local routing instructions.
- Keep delivery evidence local and repository-specific guidance close to the code it governs.

## Three delivery entries

These are the only user-facing workflow entries:

- `$goal-to-delivery <goal-or-selected-issue>` delivers one user-selected goal semi-autonomously. It defaults to local work and tested `working-tree` output, never selects backlog work, and stops at the declared boundary.
- `$spec-driven-delivery <stage> <goal-or-selector>` performs exactly one requested stage and returns control. It is the default for non-trivial work when no entry was explicitly chosen.
- `$linear-delivery-loop <adapter-prepared-iteration>` applies autonomous policy to one capability prepared by deterministic adapter code. It does not accept a raw goal or implement queue selection in model instructions.

`feature-driver` remains only as a deprecated one-migration-cycle alias to `$goal-to-delivery`; it never routes autonomous work.

The entries reuse the same planner, optional product designer, tasker, independent auditor, implementers, code reviewer, runtime QA verifier, and documentation skills. Their difference is advancement and authority policy, not separate agent stacks.

## Canonical protocol

The sole cross-tool delivery protocol lives in [`src/skills/goal-to-delivery/references/`](src/skills/goal-to-delivery/references/):

- delivery stages and role ownership;
- artifact identity/layout and historical fallback;
- clarification policy;
- distinct quality gates;
- completion/publication boundaries;
- the work-descriptor schema.

Other workflow skills and project templates link to these files instead of copying the protocol. Repository `AGENTS.md` files and curated docs continue to own repository-specific commands, domain rules, definitions of done, and stricter safety requirements.

Precedence is user/system requirements and repository-specific stricter safety, then the explicitly invoked entry policy, then the canonical shared contract. An unresolved conflict fails closed before implementation or external mutation.

## Work artifacts

New work is initialized by the deterministic helper into:

```text
docs-ai/<work-key>-<slug>/
  workflow.json
  <date>-<slug>-plan.md
  ...dated delivery evidence...
```

Work resumes only through an exact registered selector. Older numbered-and-dated workflow folders and flat `docs-ai/*` files remain readable historical evidence; current producers never rewrite or migrate them.

Per-work evidence belongs in `docs-ai/`. Reusable how-tos, concepts, references, ADRs, runbooks, and troubleshooting belong in the repository's curated docs tree and may link to the shared protocol.

The base helper binds `repositoryKey` to the normalized repository's state home; legacy unbound state requires attended reconciliation. Workflow-managed Handoff requires an exact repeated `--expected-path` scope, preserves the registry as authority, writes redacted hash-bound evidence, and transfers no reservation. See the canonical [artifact contract](src/skills/goal-to-delivery/references/artifact-contract.md) for the complete boundary and its distinction from native Codex **Hand off**.

## Layout

- `src/agents/`: canonical specialist agent definitions
- `src/skills/`: canonical reusable skills and references
- `src/project-templates/`: small project-local routing templates
- `scripts/build.py`: generate tool adapters into `dist/`
- `scripts/sync.py`: install generated output into user homes and optional project roots
- `scripts/validate.py`: authoritative aggregate local validation
- `dist/`: generated projections; never edit directly

Agent frontmatter defines tool-specific model and sandbox metadata. The build generates Codex TOML agents, Claude and Copilot Markdown agents, Cursor rules, copied skills, and rendered project templates.

Each canonical agent uses YAML-like frontmatter:

```md
---
name: "planner"
description: "Short agent description"
codex_model: "gpt-5.6"
codex_model_reasoning_effort: "high"
codex_sandbox_mode: "workspace-write"
claude_model: "opus"
claude_effort: "high"
---
```

Planner, auditor, and code-reviewer use the deeper review profile. Product design, tasking, implementation, and QA use the repository's balanced profiles declared in their canonical files.

Generated output includes:

- `dist/codex/agents/*.toml` and `dist/codex/skills/*`
- `dist/claude/agents/*.md` and `dist/claude/skills/*`
- `dist/copilot/agents/*.agent.md` and `dist/copilot/skills/*`
- `dist/cursor/rules/*.mdc`
- tool-specific project templates under `dist/project-templates/`

## Local workflow

Validate all canonical sources and generated behavior:

```powershell
python .\scripts\validate.py
```

Generate adapters:

```powershell
python .\scripts\build.py
```

Bootstrap canonical sources from an existing global setup only when intentionally importing it:

```powershell
python .\scripts\bootstrap_existing.py
```

Install global outputs:

```powershell
python .\scripts\sync.py --tool all
```

Install project-local instruction files as well:

```powershell
python .\scripts\sync.py --tool all --project C:\path\to\repo
```

Limit installation to one tool when needed:

```powershell
python .\scripts\sync.py --tool codex
python .\scripts\sync.py --tool claude
python .\scripts\sync.py --tool copilot
python .\scripts\sync.py --tool cursor --project C:\path\to\repo
```

Set `LUCHDOM_AI_CONFIG_DOCS` before sync to override the shared curated-docs path rendered into project templates.

Normal sync refreshes only marker-managed content in existing `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md`, preserving content outside the markers. Existing unmarked files remain untouched unless `--force` explicitly adopts them. Generated agents, skills, and Cursor rules remain skip-unless-`--force` where the sync contract says so.

## Maintenance rules

- Change `src/`, regenerate `dist/`, and validate; do not edit generated output.
- Keep project templates concise routers, not copies of the canonical delivery protocol.
- Use [`docs/external-tools.md`](docs/external-tools.md) for optional external tooling setup.
- Preserve unrelated user changes and historical `docs-ai` evidence.
