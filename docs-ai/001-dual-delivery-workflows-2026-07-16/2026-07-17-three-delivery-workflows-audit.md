# Three Delivery Workflows Plan — Independent Audit

## Verdict

**FAIL — return the plan for targeted clarification/revision, then repeat the independent plan audit before re-tasking.**

The three-workflow direction is sound, but the plan cannot proceed to tasking as-is. Three P1 gaps leave the unattended loop either unsafe across worktrees or unable to run under Codex Scheduled's unattended permission model. The remaining P2 findings weaken exact-SHA evidence integrity and cross-repository workflow durability.

No P0 finding was identified. No product UI is changed by this program, so a program-level design spec is not required.

## Findings by severity

### P1 — High

#### P1.1 — The durable lease/state is relative to a scheduled worktree, so it is not a proven global coordination point

The plan requires the recurring task to run in Worktree mode and treats `.artifacts/harness/worker-state.json` as the durable lease, operation journal, and recovery source (`three-delivery-workflows-plan.md:85`, `:415-435`, `:466-480`, `:576-594`). It never defines a machine-stable supervisor home shared by every scheduled run, background worktree, validation worktree, and attended recovery command.

That is unsafe because worktrees have independent file copies, ignored `.artifacts/` content is not propagated through Git, and Codex documents that scheduled worktree use can create multiple worktrees that require cleanup (`codex-manual.md:7059-7064`, `:7088-7094`, `:7161-7165`, `:7565-7572`). Two run worktrees can therefore each observe no relative lease/state, and a later heartbeat may be unable to find the prior issue worktree or operation journal. The short per-command mutex does not repair a durable-state path that differs by worktree.

Required plan adjustment:

- Select one explicit runtime topology: either a stable local supervisor checkout that creates persistent issue worktrees, or Worktree-mode heartbeats backed by a machine-stable shared supervisor-state root.
- Define the canonical state-root derivation from repository identity, global mutex scope, issue-worktree mapping, permissions, retention/cleanup owner, and recovery behavior.
- Add tests with two distinct worktree paths proving one lease owner, one issue worktree, crash recovery, archive/cleanup safety, and no duplicate Linear/GitHub mutation.

#### P1.2 — Manual and local work are not durably reserved against the autonomous scheduler

The plan says local work bypasses Linear preflight, Linear mutation, and the SaaS global WIP slot (`three-delivery-workflows-plan.md:79`, `:279-290`). Autonomous selection consults only Linear `In Progress`/`In Review` before claiming another issue (`:437-464`). A local semi-autonomous or manual implementation in the SaaS repository is therefore invisible to the scheduler, which may concurrently claim and edit a second SaaS issue in another worktree.

There is a second form of the same race for an explicitly selected Linear issue. Manual Plan/Clarify/Task/Audit is declared read-only until `Implement` (`:292-304`), while removal of `autonomous` is described only around claiming (`:297-300`). A `Todo + autonomous` issue can be manually planned in one task and claimed by the five-minute loop in another before the user reaches `Implement`. This fails the user's requirement that the system reliably know when non-autonomous work owns the item.

Required plan adjustment:

- Add a deterministic repository-scoped active-work reservation that every SaaS autonomous preflight checks, including work with `workSource: local`; local work in another repository must not block SaaS.
- Define how a manually selected `Todo + autonomous` issue is reserved before planning: immediate safe label/ownership reconciliation, an explicit `Reserve/Claim` action, or an equivalent adapter-owned record visible to the scheduler.
- Define expiry, release, stale-reservation reconciliation, and exact Linear state/label behavior at `artifact`, `working-tree`, `commit`, and `pr` boundaries. “Appropriate non-terminal state” (`:302`) is not deterministic enough because `In Progress` and `In Review` consume the global slot.
- Test simultaneous manual planning, local SaaS implementation, autonomous preflight, stale reservation, and different-repository local work.

#### P1.3 — The unattended sandbox/network/filesystem permission contract is missing

The loop requires direct Linear GraphQL, GitHub/`gh`, ntfy, localhost runtime QA, an installed shared engine, and durable state/worktrees that may sit outside the scheduled run's current directory (`three-delivery-workflows-plan.md:83-90`, `:505-519`, `:521-527`, `:596-611`, `:670-683`). The rollout checks environment inheritance, but it does not select or preflight a Codex permission profile, network access, writable roots, command rules, or local-network access.

Codex Scheduled runs unattended with the user's default sandbox settings. The official manual states that scheduled runs use those defaults, `workspace-write` blocks network and writes outside the workspace unless explicitly enabled/allowed, and scheduled tasks normally use `approval_policy = "never"` (`codex-manual.md:7069-7071`, `:7167-7196`; general network default at `:2327-2358`). An unattended run cannot pause for a permission approval and continue safely.

Required plan adjustment:

- Specify the least-privilege scheduled permission profile and setup for the installed engine, shared state root, issue worktrees, Git/GitHub, `api.linear.app`, the configured ntfy host, and loopback QA.
- Add a mutation-free permission preflight that fails before claim and reports a precise actionable error without leaking credentials.
- Test default-denied network, denied shared-state write, inaccessible installed engine, blocked loopback, and the approved least-privilege configuration.

### P2 — Medium

#### P2.1 — Tracked review/QA evidence can change the PR head after the gate it claims to attest

The artifact contract tracks `*-code-review.md` and `*-qa.md` (`three-delivery-workflows-plan.md:308-328`), but the autonomous stage order publishes and passes exact-head CI before code review and runtime QA (`:482-503`). Those stages then write tracked reports. If the reports are committed, the PR head changes; if they are not committed, the promised repository evidence is absent from the merged result. The revised plan only says executable changes invalidate gates (`:505-519`, `:724-729`) and dropped v1's explicit evidence-only delta and final-head attestation rule (`2026-07-16-dual-delivery-workflows-plan.md:503-527`, `:876`, `:978-979`, `:1018`).

Required plan adjustment: restore an exact evidence-ordering contract. Commit draft evidence before the final gated head or keep final attestations in durable external state/Linear; require final-head CI and code-review attestation, and permit QA reuse only after a deterministic evidence-only diff check explicitly records that behavior is unaffected.

#### P2.2 — Canonical policy ownership conflicts with the current project-template doctrine

The plan makes `src/skills/goal-to-delivery/references/` the canonical source for delivery stages, artifacts, clarification, quality gates, and completion boundaries (`three-delivery-workflows-plan.md:175-197`). The current canonical project template says long-form doctrine belongs in repo-local docs or the configured canonical docs path and that skill references are portable summaries, not the source of truth (`src/project-templates/codex/AGENTS.md:4-15`).

Phase 1 says templates will be updated, but the plan does not identify this as an intentional ownership migration or define the replacement source-of-truth rule (`three-delivery-workflows-plan.md:624-633`). Without one, repo docs, installed skill references, and project templates can disagree about which policy wins.

Required plan adjustment: choose and state one model. Either keep canonical delivery doctrine under `ai-config/docs/` and generate/validate portable skill summaries, or explicitly revise every template/tool contract to make the canonical `src` skill references authoritative. Add source-to-generated-to-installed drift tests for the selected model.

#### P2.3 — Local work-key allocation and cross-context resume are not concurrency-safe

Local work chooses the “next collision-free” numeric key by scanning `docs-ai/` and `docs-ai/history/` (`three-delivery-workflows-plan.md:279-290`), while local workflows deliberately do not share Linear WIP and may run concurrently. Two tasks can scan the same state and both choose `001`, corrupting or interleaving artifacts. `workflow.json` is navigation metadata, explicitly not a lease (`:308-328`, `:558-575`), and the plan also claims a later task can resume without chat memory (`:747-756`) without defining how an uncommitted working-tree artifact is discovered from another Codex worktree/context.

Required plan adjustment: define atomic folder/key reservation with collision retry, stable descriptor lookup/reuse, and a handoff rule for uncommitted working-tree artifacts across Local/Worktree contexts. Test simultaneous allocation, same-goal resume, later Linear attachment, and historical-folder fallback.

## Consistency checks that passed

- The plan cleanly defines three explicit entries and reuses one specialist pipeline rather than duplicating agents (`three-delivery-workflows-plan.md:24-38`, `:93-123`, `:199-219`).
- Manual spec-driven delivery performs one named stage and never auto-advances; `Implement` does not imply review, QA, or Git publication (`:221-249`).
- `$goal-to-delivery` cannot select queue work or self-elevate; autonomous authority requires an adapter-prepared capability and fresh deterministic validation (`:111-123`, `:466-480`).
- Local goals and optional later Linear attachment are first-class, and Linear remains optional outside autonomous delivery (`:250-340`).
- Completion boundaries distinguish artifact, working tree, commit, PR, and merge, with explicit Git authority (`:341-391`).
- V1 autonomous safety locks are materially preserved: ordinary Linear states/labels, `SAAS`, global tracked WIP, direct GraphQL, environment-only secrets, Linear + ntfy + Scheduled visibility, deterministic mutation ownership, PR/squash/exact-SHA gates, bounded repair without auto-revert, `Ready for Codex` migration, and bootstrap exception (`:69-91`, `:393-554`).
- Real HTTP/Playwright QA, code review, docs-as-code/MkDocs, cross-platform SaaS validation repair, and local-first product sequencing are covered (`:613-684`, `:686-745`).
- The migration preserves `SAAS-44` through `SAAS-55` and defers Linear mutation until a revised task graph passes audit (`:759-795`).
- The implementation phases can be split cleanly across shared doctrine, deterministic engine, build/sync, SaaS validation/docs, SaaS adapter, Linear migration/pilot, and schedule rollout after the findings above are resolved.

## Required disposition

Revise the plan to resolve P1.1–P1.3 and P2.1–P2.3. Then repeat this independent plan audit. Only after it passes should the provisional task document be replaced and the existing `SAAS-44` through `SAAS-55` records be updated in place.

No task breakdown, Linear mutation, Git mutation, build/sync, implementation, pilot, or schedule action is authorized by this audit.

## Sources consulted (paths)

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-16-dual-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-16-dual-delivery-workflows-audit.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-dual-delivery-workflows-tasks.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-dual-delivery-workflows-task-audit.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\planner.md`
- `C:\dev\luchdom\ai-config\src\agents\product-designer.md`
- `C:\dev\luchdom\ai-config\src\agents\tasker.md`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\references\handoff-order.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\references\output-contracts.md`
- `C:\dev\luchdom\ai-config\src\skills\task-audit-breakdown\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\task-audit-breakdown\references\audit-checklist.md`
- `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\SKILL.md`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py`
- `C:\dev\luchdom\saas\AGENTS.md`
- `C:\dev\luchdom\saas\README.md`
- `C:\dev\luchdom\saas\docs\HARNESS.md`
- `C:\dev\luchdom\saas\docs\WORKFLOW.md`
- `C:\dev\luchdom\saas\docs\LINEAR.md`
- `C:\dev\luchdom\saas\docs\DECISIONS.md`
- `C:\dev\luchdom\saas\docs\QUALITY.md`
- `C:\dev\luchdom\saas\docs\AI-TOOLING.md`
- `C:\dev\luchdom\saas\docs\SLACK-APPROVALS.md`
- `C:\dev\luchdom\saas\.github\workflows\validate.yml`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\apps\web\package.json`
- `C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md`

Official pages represented in the refreshed Codex manual cache:

- [Codex scheduled tasks](https://learn.chatgpt.com/docs/automations)
- [Codex worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
- [Codex sandboxing and permissions](https://learn.chatgpt.com/docs/sandboxing)
