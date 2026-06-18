# Project AI Instructions

Use this file as the repo-local bootstrap and router into the target repo's docs and any shared doctrine configured for the machine or team.

Long-form doctrine should live in repo-local docs or in the canonical docs path referenced by this file. Skill `references/` are portable summaries, not the source of truth.

## Canonical Docs

- Canonical docs path: `{{LUCHDOM_AI_CONFIG_DOCS}}`
- This path is rendered by `scripts/sync.py --project <path>` from `LUCHDOM_AI_CONFIG_DOCS` when it is set, otherwise from this repo's local `docs/` folder.
- Read the repo's local `AGENTS.md` and the docs it references first.
- Read the smallest relevant subset of docs for the task at hand instead of scanning everything.
- Repo-local docs win when they define a more specific rule for the target project.
- When repo-local guidance is silent, use the canonical docs path referenced by this file.

## Project Type Detection

- Start with the repo's local `AGENTS.md`, README, solution files, manifests, and nearest docs before choosing a workflow path.
- Backend or service work usually shows solution or project files, service hosts, API entry points, persistence boundaries, or repo docs that define service behavior.
- Frontend work usually shows `package.json`, framework config, React app structure, or repo docs focused on UI flows, components, and browser behavior.
- Jekyll/GitHub Pages work usually shows `_config.yml`, `Gemfile`, `_layouts`, `_includes`, `_data`, `_sass`, `assets`, `.github/workflows/`, or Pages deployment docs.
- Mixed or unclear repos should follow repo-local docs and nearest patterns first. If the boundary is still ambiguous after inspection, stop and clarify.
- Repo-local docs and explicit project guidance override these heuristics.

## Preferred Behavior

- If requirements are unclear or docs conflict, stop and clarify instead of guessing.
- Keep AI-written docs concise. Short, simple, high-signal writing is required because overly long text is less likely to be read.
- Prefer existing components, abstractions, and tests over inventing new patterns.
- Update relevant docs when behavior, workflow, setup, or architecture changes.

## Pull Request Descriptions

- Use `$pr-description` when drafting or reviewing a PR title or description.
- Always inspect and follow the repo's PR template at `.github/pull_request_template.md` first. Match its section headings and order exactly, and do not invent extra sections.
- If the repo has no PR template, use this fallback section order: Overview, Changes, Security Impact, Testing, Related Work.
- Keep the PR title under 70 characters; put detail in the body, not the title.
- Keep the body simple and concise: short bullet points, no long prose, and no restating the diff line by line. Lead with what changed and why.
- Omit internal narration, including audits, stash experiments, plan history, task history, and `docs-ai/` workflow artifacts.
- The Testing section must include concrete `Testing in environment` steps a reviewer or tester can follow in Dev when manual validation is relevant.
- Note pre-existing or unrelated test failures explicitly, but in one line.
- Write PR descriptions to `docs-ai/<NNN>-<short-feature-name>-<YYYY-MM-DD>/<YYYY-MM-DD>-<short-feature-name>-pr-description.md`.

## Git Safety

- Read-only Git inspection is allowed: `git status`, `git diff`, `git log`, `git show`, and branch inspection.
- Drafting commit messages or PR descriptions is allowed.
- Do not stage files, create or switch branches, commit, push, create PRs, merge PRs, or rewrite Git history unless the user explicitly approves that exact Git action in the current conversation.
- Before any approved Git action, summarize the intended files and action, and preserve unrelated user changes.

## MCP And Tool Routing

- Prefer local repo inspection first, then use the smallest external tool needed to remove uncertainty.
- Use Context7 MCP for current framework or library docs and API details when repo docs are not enough.
- Use GitHub MCP or `$github-cli` for PRs, issues, remote code references, checks, or repository context that local checkout inspection does not provide cleanly.
- Use MUI MCP only when the repo already uses MUI and current component, theming, or accessibility guidance is needed.
- Use Playwright CLI as the default browser and UI workflow when it is available and interactive verification is needed. Treat Playwright MCP as optional and only use it when it is separately installed and specifically helpful.

## Agents And Skills

- Use `$repo-discovery` when the relevant docs, modules, or conventions are not already obvious.
- Use `$pr-description` when drafting or reviewing a PR title or description.
- Use `$github-cli` when the task needs GitHub CLI setup, auth checks, PR or issue inspection, check logs, or explicitly approved GitHub mutations.
- Use `$jekyll-github-pages` when creating, customizing, debugging, or deploying Jekyll sites for GitHub Pages.
- Backend and service flow: `planner` -> `tasker` -> `dotnet`.
- Frontend flow: `feature-driver`, `product-designer`, `nextjs-mui`, and `react`.
- Jekyll/GitHub Pages flow: `planner` or `feature-driver` -> `product-designer` when visual direction changes materially -> `tasker` when decomposition is useful -> `jekyll-site-builder`.
- Repo-managed shared skills: `$repo-discovery`, `$pr-description`, `$github-cli`, `$jekyll-github-pages`, `$task-audit-breakdown`, `$multi-agent-delivery`, `$ui-review-spec`, `$luchdom-docs`.
- Optional machine-local skills may also exist, but they are not guaranteed across developers or machines. Do not assume optional skills are available unless the environment exposes them.

## Mandatory Workflow

When the user asks for a non-trivial feature, behavior change, endpoint, refactor with functional impact, or any request larger than a trivial edit, use this workflow and do not start implementation until the user explicitly chooses `Implement`.

### Workflow artifact folder

- Create or reuse one workflow folder for all related AI artifacts.
- Folder format: `docs-ai/<NNN>-<short-feature-name>-<YYYY-MM-DD>/`
- Choose `<NNN>` by scanning folders under `docs-ai/` and `docs-ai/history/`, then using the next highest three-digit number.
- If multiple active folders could match the current work, ask which one to use instead of creating a duplicate.
- Keep every related plan, clarification update, task breakdown, audit, design spec, and AI workflow note in that folder.
- New workflow artifacts must use the folder format. Older flat `docs-ai/*` artifacts may be read as legacy fallback only.

### 1. Plan first

- Create a detailed plan in the workflow artifact folder.
- Filename format: `docs-ai/<NNN>-<short-feature-name>-<YYYY-MM-DD>/<YYYY-MM-DD>-<short-feature-name>-plan.md`
- Use the required planning format below.

After writing the plan, summarize it briefly and ask:

`Do you want to Clarify (resolve open questions) or Task it out (produce executable task breakdown)?`

### 2. Clarify

- Ask one question at a time.
- Offer 2-5 clear options.
- Update the plan file after each answer.
- Continue until no blocking gaps remain.

### 3. Task it out

- Create an executable task breakdown in the workflow artifact folder.
- Filename format: `docs-ai/<NNN>-<short-feature-name>-<YYYY-MM-DD>/<YYYY-MM-DD>-<short-feature-name>-tasks.md`
- Include ordered steps, files to touch, acceptance criteria, tests, and rollout/risk notes when relevant.

After writing the tasks file, ask:

`Do you want to Audit or Implement?`

### 4. Audit

- Validate the request, plan, clarification decisions, and tasks for consistency.
- Call out mismatches, gaps, weak sections, and recommended adjustments.
- Write the audit under `docs-ai/<NNN>-<short-feature-name>-<YYYY-MM-DD>/<YYYY-MM-DD>-<short-feature-name>-audit.md`.

After auditing, ask:

`Proceed to Implement or go back to Clarify/Task it out to address findings?`

### 5. Implement

- Start coding only after the user explicitly says `Implement`.
- After implementation, ask: `Do you want me to move this workflow folder to docs-ai/history?`

## Required Planning Format

Every plan must include:

1. Overview
2. Assumptions & Constraints
3. Architecture / Approach
4. API / Contracts
5. Data Model & Storage
6. Implementation Steps
7. Testing Strategy
8. Observability / Debuggability
9. Rollout Plan
10. Risks & Mitigations
11. Open Questions
