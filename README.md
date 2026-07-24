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

Autonomous delivery uses progressive disclosure. A healthy `$linear-delivery-loop` iteration loads only its thin entry policy and the compact canonical `autonomous-runtime-contract.md`; deterministic code validates capabilities, schemas, authority, state, and engine operations without placing those implementation assets in model context. The detailed protocol remains directly available to `$goal-to-delivery` and `$spec-driven-delivery`.

Precedence is user/system requirements and repository-specific stricter safety, then the explicitly invoked entry policy, then the canonical shared contract. An unresolved conflict fails closed before implementation or external mutation.

## Harness engineering coverage

A dependable engineering harness needs more than a prompt that asks an agent to keep working. It needs bounded behavior, controlled capabilities and context, independent evidence, durable state, safe execution, and explicit points for human intervention. The seven components below are complementary: no single component substitutes for another, and fixture-backed design is not the same as live operational readiness.

| Component | Why it matters | How this repository covers it | Current maturity |
|---|---|---|---|
| System prompt | Establishes role, behavior, constraints, precedence, and stopping conditions. | The three entry skills route into one canonical protocol; repository instructions add local rules; specialist agent definitions keep stage ownership distinct. | Shared policy is implemented. |
| Tools | Gives each role the capabilities it needs without exposing every possible mutation surface. | Reusable skills and specialist agents provide narrow responsibilities; generated adapters carry tool-specific metadata; deterministic wrappers and provider boundaries use fixed, schema-validated operations. | Shared surfaces exist; complete least-privilege SaaS integration remains pending. |
| Context management | Controls what the agent knows now so relevant evidence is available without loading the whole harness. | Autonomous work uses progressive disclosure and a compact runtime contract; detailed schemas and diagnostics stay out of healthy-run context; repository discovery and stage artifacts load only the nearest relevant sources. | Implemented by design; context size and token efficiency still require measurement and tuning. |
| Verification mechanisms | Prevents model confidence from being treated as proof that work is correct. | Plan audit, exact-diff code review, runtime QA, documentation checks, repository-owned local aggregates, and clean exact-head/exact-merge-SHA validation are separate gates. | Shared gates are implemented; repository-specific real HTTP/browser QA must be supplied by each project. |
| Memory | Preserves the state and knowledge needed to resume safely across sessions. | Linear stores durable work and decisions; `workflow.json` and `docs-ai/` retain delivery identity and evidence; the supervisor state home retains leases, reservations, journals, recovery state, and persistent worktrees; curated repository docs retain reusable knowledge. | Operational memory is implemented; compact curated knowledge, retrieval, retention, and promotion from run evidence need further work. |
| Sandboxes | Limits the damage of commands, tools, network access, and concurrent edits. | Agent metadata declares sandbox expectations; repository reservations and scoped mutation authorization constrain writes; preflight checks environment and permissions; persistent issue worktrees and disposable validation worktrees isolate execution. | Core controls are implemented and fixture-tested; the scheduled SaaS configuration and attended pilot must prove them live without a full-access fallback. |
| Hooks | Provides explicit human intervention when product judgment, external reconciliation, or unsafe failure blocks automation. | Structured `needs-human` decisions use exact authorized Linear replies; ntfy is an attention channel; pause, kill-switch, retry, recovery, and publication-refusal paths preserve protected work instead of guessing. | Decision and attention behavior is fixture-backed; live notification configuration and an attended pilot remain pending. |

The compact [autonomous runtime contract](src/skills/goal-to-delivery/references/autonomous-runtime-contract.md) owns healthy-run policy. The [supervisor core](src/skills/linear-delivery-loop/references/supervisor-core.md) documents local authority, state, isolation, and recovery. The [Linear control plane](src/skills/linear-delivery-loop/references/linear-control-plane.md) documents selection, decisions, durable requests, and attention behavior. The canonical [quality gates](src/skills/goal-to-delivery/references/quality-gates.md) define the evidence required before completion.

### Additional success factors

The seven components are a useful harness model, but a successful unattended engineering loop also depends on:

- **Determinism, idempotency, and recovery:** every issue, mutation, retry, checkpoint, and publication operation needs a stable identity, compare-and-set state, bounded retry policy, and safe crash recovery.
- **Observability and engineering economics:** status and evidence should make stage, owner, lease, retry, duration, tool-call volume, context size, token use, and failure cause understandable without exposing secrets. The current harness has structured status and evidence, but aggregate cost and efficiency reporting remain a gap.
- **Input and rollout quality:** autonomous candidates must be achievable, bounded, locally verifiable issue leaves. Enablement should progress through fixture tests, an attended pilot, a kill switch, and observed scheduled heartbeats before eligibility expands.

The goal is therefore not to maximize autonomy. It is to make each autonomous action bounded, observable, recoverable, independently verifiable, and interruptible by its owner.

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

The shared [supervisor core](src/skills/linear-delivery-loop/references/supervisor-core.md) is a diagnostic and operator reference, not mandatory healthy-run prompt context. Its deterministic runtime layers machine-stable leases, repository editing reservations, mutation authorization, persistent issue/gate worktrees, permission preflight, recovery/cleanup, and reservation-aware assembled Handoff on that base. The fixture-first [Linear control plane](src/skills/linear-delivery-loop/references/linear-control-plane.md) adds fully paginated selection, decision and publication-retry reconciliation, migration reporting, and ntfy attention behind injected ports. The fixture-first [publication engine](src/skills/linear-delivery-loop/references/publication.md) adds contained manifest staging, idempotent GitHub-style readback, exact-SHA gates, evidence convergence, squash-merge identity, and bounded repair. Both remain disabled from live autonomous use until later integration and attended pilot tasks. Semi-autonomous and manual implementation use the same reservation namespace as autonomous work, so one workflow cannot silently edit through another workflow's active authority.

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
