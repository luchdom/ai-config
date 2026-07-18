# Dual Interactive and Autonomous Delivery Workflows Audit

## Verdict

**Proceed after fixes; return to Clarify, then Task it out, then repeat the independent audit.**

The product direction is sound and covers the user's two workflows, local-first priority, achievable Linear issues, PR-based completion, runtime QA, documentation, and Linear + ntfy notifications. The plan is not implementation-ready until the High findings below have explicit contracts.

This is a **plan-only audit**. The expected task document `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-16-dual-delivery-workflows-tasks.md` is absent. Therefore task ordering, file-level ownership, dependencies, and independently executable acceptance criteria could not be audited. No design spec is required because this work changes delivery tooling rather than product UI.

## Findings by severity

### High

1. **The deterministic supervisor has no concrete Linear transport or authentication contract.**
   - The supervisor owns selection and mutation before Codex is invoked (`plan.md:115-130`, `:514-525`), but the current repo documents only Linear MCP through Codex OAuth (`C:\dev\luchdom\saas\docs\AI-TOOLING.md:22-24`). A PowerShell process cannot be assumed to call that connector directly.
   - Specify one transport, credential source, rate-limit/retry behavior, and fixture boundary. If selection uses a direct Linear API adapter, keep issue selection and mutations outside the LLM. If Codex/MCP is used, revise the claim that the supervisor is deterministic and define how returned mutations are independently validated.
   - Separate the automation actor, issue assignee, and human decision owner. The workspace currently has only Lucas, so `assign the worker` (`plan.md:329`) and `assign/@mention the owner` (`:347`) cannot describe two distinct users. Make the Linear self-notification test a rollout gate and require ntfy for decisions if self-authored mentions do not alert.

2. **Paused decisions have no reachable reconciliation path.**
   - A decision pauses the issue as `Backlog + needs-human` (`plan.md:340`), while the main loop queries active WIP and then `Todo + autonomous` (`:117-130`, `:313-332`). The resume predicate only covers `In Progress`/`In Review` (`:184-192`). Nothing explicitly scans paused issues for a valid `Decision <id>` reply.
   - Add a pre-selection reconciliation stage for `Backlog + needs-human` issues with persisted pending decision IDs. A valid answer must restore the same run/worktree as `resume-pending` before normal queue selection; it must not merely move the issue to `Todo` where another candidate may win (`:363-370`). Add tests for accepted, malformed, duplicate, stale, and unauthorized replies.

3. **Autonomous Git authorization conflicts with the current canonical safety rule.**
   - The plan treats `autonomous` as authorization to create and merge a PR (`plan.md:50`, `:141-143`, `:695`), while the canonical project template forbids branch, commit, push, PR, and merge mutations without exact approval in the current conversation (`C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md:45-50`). The SaaS repo currently authorizes autonomous branch/commit/push, but not PR creation or merge (`C:\dev\luchdom\saas\AGENTS.md:146-167`, `:224-230`).
   - Define a narrow durable exception in canonical and SaaS instructions: an eligible `Todo + autonomous` issue authorizes only its issue branch, commits, push, PR create/update, and merge after gates. Explicitly forbid force-push, history rewrite, direct push to `main`, repository-setting changes, unrelated files, and all existing high-risk stop conditions. Add semantic tests proving interactive work retains the per-action gate.

4. **Automatic merge integrity is underspecified for an unprotected private repository.**
   - Live read-only GitHub checks confirm `main` is default, all three merge methods are enabled, and branch protection/rulesets return `403` on the current private plan. The plan records base/head SHAs (`plan.md:430-445`) but does not require the reviewed/tested head to equal the merged head or require the base SHA to remain unchanged.
   - Select one merge method, require a clean/mergeable PR, bind code review and QA to the exact PR head SHA, rebase/update and rerun gates when `main` changes, and merge only that SHA. Because GitHub cannot enforce checks here, the supervisor must fail closed and enforce every gate itself. Define post-merge failure recovery; leaving broken code on `main` in `In Review` (`:603`) is a status, not a remediation policy.

5. **The model result currently contains control-plane facts that the supervisor must own.**
   - The result schema asks the model to return run ID, issue ID, session ID, branch, head SHA, and attempt (`plan.md:288-311`), conflicting with the non-goal that the LLM not own scheduler state (`:31`). The actual Codex thread ID is emitted by `thread.started`, not established by model prose.
   - Treat those fields as supervisor inputs or independently observed values. Parse the Codex thread ID from JSONL, obtain branch/head/PR state from Git/GitHub, and reject any result whose echoed issue/run identity differs. Restrict model-owned output to proposed outcome, assumptions, validation claims, blocker, and next action.

### Medium

1. **Linear migration covers `Todo`, but the real risk is the autonomous Backlog.**
   - Phase 5 audits current `Todo` issues only (`plan.md:532-540`). Live Linear inspection found no `Todo`, `In Progress`, or `In Review` issues; `Ready for Codex` still exists; only `autonomous`, `Feature`, `Improvement`, and `Bug` labels exist; and broad parents plus AWS, CI/CD, New Relic, and PostHog backlog items already carry `autonomous`.
   - Audit every non-terminal issue carrying `autonomous`, not only `Todo`: remove eligibility from broad parents, add `needs-refinement` to oversized goals, add `external-integration` to deferred work, verify dependencies, and promote only bounded local leaf issues to `Todo`. Record an inventory before removing `Ready for Codex`.

2. **The missing task artifact blocks the canonical pre-implementation gate.**
   - Canonical order requires tasker before auditor and auditor validation of both plan and tasks (`C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md:10-17`; `C:\dev\luchdom\ai-config\src\agents\auditor.md:15-19`).
   - After resolving High findings, create tasks split across shared `ai-config`, SaaS adapter/docs, Linear migration, and pilot/rollout, with acceptance criteria and dependencies. Re-audit before implementation.

3. **Runtime QA needs an isolated local-environment safety contract.**
   - Real HTTP/Playwright checks and deterministic setup are strong (`plan.md:610-620`), but the plan does not require Development-only endpoints, disposable databases, per-run Docker project names/ports, or a bounded cleanup/reset target.
   - Require localhost/Development assertions, unique per-run resource names, no production credentials, disposable test data, bounded readiness timeouts, and cleanup evidence. Never let scheduled QA reset the user's normal development database implicitly.

4. **Workflow reports can invalidate the SHA they claim to approve.**
   - Code review and QA reports are committed PR artifacts (`plan.md:389-409`), so writing/pushing them changes the PR head after a gate may have approved the prior SHA.
   - Define evidence ordering and SHA binding. Either batch evidence-only commits and perform a final diff/gate check, or store immutable gate evidence outside the reviewed branch. Linear links should target immutable blob SHAs or merged `main`, not a deletable branch ref.

5. **The non-interactive invocation contract is not executable as written.**
   - The PowerShell sample uses backslash continuation (`plan.md:261-268`), which is not PowerShell syntax. The installed `codex exec` supports prompts, JSONL, schemas, and resume, but no direct custom-agent selector.
   - Replace the sample with valid PowerShell splatting or a single line. Define the root prompt that explicitly delegates to `autonomous-driver`, how required subagents are requested, and a contract test proving this works in non-interactive mode before live Linear mutation.

6. **New-issue selection is not deterministic.**
   - The predicate says which issues qualify but not which one wins (`plan.md:168-182`, `:321`).
   - Specify stable ordering, for example: Linear priority, project rank, creation time, then identifier. Persist the considered candidate set and rejection reasons in dry-run evidence.

7. **Hosted CI is scheduled before the stated local-first boundary.**
   - The plan adds an `ai-config` CI workflow in Phase 2 (`plan.md:472-485`) although the user explicitly placed pipelines after locally runnable product capability, and Phase 7 repeats that order (`:553-561`).
   - Keep local build/test validation in the initial implementation and move hosted CI creation to the later external-integration milestone unless the user explicitly promotes it as a harness prerequisite.

### Low

1. **Two artifact-format details drift from canonical sources.**
   - The required section is `11. Open Questions`, but the plan uses `11. Decisions and Defaults` (`C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md:132-146`; `plan.md:689`). Rename it to `Open Questions / Decisions and Defaults` and state `None` if resolved.
   - The plan names UI artifacts `*-design-spec.md` (`plan.md:394`), while canonical skills and agents use `*-design.md` (`C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md:31-38`). Preserve `*-design.md`, or explicitly migrate every producer, consumer, template, and test.

## Consistency checks that passed

- Two entry workflows share specialist agents while preserving a hard interactive implementation gate (`plan.md:3-12`, `:61-100`).
- Normal Linear states plus labels replace `Ready for Codex`; the obsolete status is explicitly a manual administration step (`plan.md:145-206`, `:532-540`).
- Global WIP is one across `In Progress` and `In Review`; autonomous work resumes and manual work makes the scheduler idle (`plan.md:46-48`, `:313-332`).
- `Done` requires merge to `main` plus post-merge validation (`plan.md:50-51`, `:141-143`, `:693-695`).
- The executable issue contract is bounded, observable, locally testable, dependency-aware, risk-aware, and documentation-aware (`plan.md:196-206`).
- Auditor, code reviewer, and runtime QA have distinct pre- and post-implementation responsibilities; HTTP and Playwright behavior checks are included (`plan.md:61-74`, `:457-467`, `:610-620`).
- Reusable policy belongs in `ai-config`; project-specific scheduling, commands, and Linear configuration remain in SaaS (`plan.md:208-237`). This matches `C:\dev\luchdom\ai-config\AGENTS.md`.
- Local-first product sequencing, deferred external integrations, docs-as-code/MkDocs, repository evidence, and concise Linear links directly cover the user's priorities (`plan.md:385-409`, `:488-510`, `:553-561`).
- Retry, locking, stale-state reconciliation, redaction, observability, dry-run, rollout, kill switch, and rollback are materially addressed (`plan.md:334-343`, `:411-453`, `:622-687`).
- Current operational identifiers use `SAAS-*`, while the clean legacy branch `codex/LUC-43-conflict-resolution` and historical artifacts are intentionally preserved (`plan.md:20`, `:55-56`, `:703`).

## Sources consulted (paths)

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-16-dual-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\planner.md`
- `C:\dev\luchdom\ai-config\src\agents\tasker.md`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\references\handoff-order.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\references\output-contracts.md`
- `C:\dev\luchdom\ai-config\src\skills\task-audit-breakdown\references\audit-checklist.md`
- `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\SKILL.md`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md`
- `C:\dev\luchdom\saas\AGENTS.md`
- `C:\dev\luchdom\saas\README.md`
- `C:\dev\luchdom\saas\docs\HARNESS.md`
- `C:\dev\luchdom\saas\docs\WORKFLOW.md`
- `C:\dev\luchdom\saas\docs\LINEAR.md`
- `C:\dev\luchdom\saas\docs\DECISIONS.md`
- `C:\dev\luchdom\saas\docs\QUALITY.md`
- `C:\dev\luchdom\saas\docs\AI-TOOLING.md`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`
- Read-only live checks on 2026-07-16: Linear statuses, labels, users, and issue queues; `git status`; `codex exec --help`; `gh auth status`; GitHub repository merge settings, branch protection, and rulesets.
