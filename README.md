# ai-toolkit

Reusable AI agents, skills, and project-local tool instructions for Codex, Claude Code, GitHub Copilot CLI, and Cursor.

## Delivery workflows

There are exactly three user-facing entries:

- `$linear-delivery-loop`: autonomous. A Codex scheduled task resumes or claims one eligible Linear issue, delivers it within configurable local budgets, and merges or checkpoints it.
- `$goal-to-delivery <goal-or-selected-issue>`: semi-autonomous. The user chooses one goal; Codex advances applicable stages and stops at the declared boundary.
- `$spec-driven-delivery <stage> <goal-or-selector>`: manual. Codex performs exactly one requested stage and returns control.

For non-trivial work without an explicit entry, use manual `$spec-driven-delivery`. All entries share the canonical cross-tool protocol under [`src/skills/goal-to-delivery/references/`](src/skills/goal-to-delivery/references/), including the [linked-worktree policy](src/skills/goal-to-delivery/references/worktree-policy.md), while repositories own their commands, domain rules, and stricter safety requirements. Unresolved conflicts fail closed before implementation or external mutation.

The workflows reuse the same specialist skills, but they do not require every specialist for every issue. Routine work plans inline; risky work can add design, tasking, audit, runtime QA, or documentation stages as needed.

## MVP autonomous loop

The MVP deliberately uses existing systems instead of a separate orchestration service:

- Linear stores queue state, checkpoints, decisions, and completion.
- `.ai/loop.json` stores the repository-specific team, labels, states, Git policy, and budgets.
- A deterministic user-local lease prevents overlapping invocations from working the same Linear queue.
- A Codex scheduled task invokes `$linear-delivery-loop` every 15 minutes from one dedicated chat/project context.
- Git branches and pull requests store implementation history and review.
- Linear comments are the authoritative human-decision channel; listed choices and explicit custom suggestions are supported, while ntfy is optional best-effort attention that links directly to the issue.

The loop handles one issue at a time. It resumes eligible autonomous work, does nothing while attended work is active, and selects a new labeled backlog issue only when no work is active. Quiet standalone scheduled runs archive their own chat when native task archiving is available; decision requests, checkpoints, errors, and runs with mutations remain visible. When configured size limits expose a larger remainder, the loop may create one linked, bounded continuation issue without selecting it in the same run. Code is Done only after required local checks, one review, applicable QA, and merge into the default branch.

Linear labels have separate responsibilities:

- `autonomous` grants the scheduled loop permission to select a refined backlog issue.
- `needs-decision` marks backlog work that needs one owner choice before it can be refined or made autonomous. It is a lightweight curation label, not another delivery workflow.
- `needs-human` pauses an issue that is already active in the autonomous loop.

Unlabeled backlog issues may be reviewed and refined collaboratively without starting a full delivery workflow. Record any material owner decision in Linear, remove `needs-decision` when resolved, and add `autonomous` only after the goal and acceptance criteria are bounded and locally testable.

See [MVP Linear delivery loop](docs/mvp-linear-delivery-loop.md) for setup and operation.

## Harness coverage

A useful engineering harness needs seven capabilities. The MVP covers all seven without turning each one into a service:

| Component | MVP coverage |
|---|---|
| System prompt | Repository instructions plus the three explicit entry skills define behavior and authority. |
| Tools | Codex local tools, Linear, Git/GitHub, and optional browser/HTTP checks provide only the needed capabilities. |
| Context management | Skills load progressively; `.ai/loop.json`, the selected issue, repository instructions, and relevant code form the working set. |
| Verification | Focused tests, one local project gate, one code review, and acceptance-driven runtime QA check the work. |
| Memory | Linear comments/issues, Git/PR history, curated docs, and optional concise notes in the exact registered `artifactFolder` persist useful knowledge. |
| Sandboxes | Codex repository/worktree isolation and repository-owned disposable test data constrain execution. |
| Human hooks | `needs-decision` marks pre-work owner choices; `needs-human`, a structured Linear choice or custom suggestion, the Codex task inbox, and an optional issue-linked ntfy notification pause active work safely. |

Memory curation and observability are intentionally modest: persist decisions and useful documentation, and rely on scheduled-task history plus Linear/Git records. Add more machinery only after the MVP exposes a concrete gap.

## Repository layout

- `src/agents/`: canonical specialist agent definitions
- `src/skills/`: canonical reusable skills and references
- `src/tool-instructions/`: project-local routing instructions for each supported tool
- `scripts/build.py`: generate tool adapters into `dist/`
- `scripts/sync.py`: install generated output into user homes and optional projects
- `scripts/validate.py`: local repository validation
- `dist/tool-instructions/`: generated project-local projections for each supported tool
- `dist/`: generated projections; never edit directly

Per-work evidence uses the workflow descriptor's exact registered `artifactFolder`. New/current workflows use `.ai/work`; an exact registered legacy workflow may continue at its exact `docs-ai` path, while unregistered or tracked historical `docs-ai` evidence remains read-only. Durable reusable guidance belongs in the repository's curated docs. The optional workflow helper and descriptor remain available for multi-session work but are not required by the autonomous MVP.

## Build, validate, and install

```powershell
python .\scripts\build.py
python .\scripts\validate.py
python .\scripts\sync.py --tool all
```

Install project-local tool instructions too:

```powershell
python .\scripts\sync.py --tool all --project C:\path\to\repo
```

Use `--tool codex`, `claude`, `copilot`, or `cursor` to limit installation. `LUCHDOM_AI_TOOLKIT_DOCS` can override the shared curated-docs path rendered into tool instructions; the legacy `LUCHDOM_AI_CONFIG_DOCS` name remains supported.

Normal sync updates only marker-managed blocks in existing instruction files and preserves content outside them. Existing unmarked instruction files and generated skills remain untouched unless `--force` explicitly adopts or refreshes them.

## Maintenance

- Change `src/`, regenerate `dist/`, and validate; do not edit generated output.
- Keep tool instructions as concise routers rather than copies of the canonical protocol.
- Keep legacy artifact-root literals limited to the validator's reviewed path-and-purpose allowlist.
- Keep credentials in environment variables, never repository files.
- Use [external tools](EXTERNAL-TOOLS.md) only when optional tooling is requested.
- Preserve unrelated user changes and historical artifact evidence.
