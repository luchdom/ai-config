# Three Delivery Workflows Plan (Revised)

## 0. Revision Status

This document is the forward-looking source of truth for the delivery-workflow program. It revises the architecture from two workflows to three:

1. autonomous Linear delivery through `$linear-delivery-loop`;
2. semi-autonomous goal delivery through `$goal-to-delivery`;
3. manually advanced spec-driven delivery through `$spec-driven-delivery`.

The following artifacts remain unchanged as historical records of the earlier two-workflow design and its independent audits:

- `2026-07-16-dual-delivery-workflows-plan.md`
- `2026-07-16-dual-delivery-workflows-audit.md`
- `2026-07-17-dual-delivery-workflows-tasks.md`
- `2026-07-17-dual-delivery-workflows-task-audit.md`

The earlier task audit passed for the earlier plan. It does not certify this revision. The current three-workflow task breakdown and Linear hierarchy `SAAS-44` through `SAAS-55` remain provisional until this plan and the corresponding tasks pass a repeated independent audit. Preserve those Linear IDs and revise their descriptions and dependencies later; do not create duplicate program issues.

This document authorizes planning only. It does not authorize code changes, build/sync installation, Linear mutations, Git/GitHub mutations, pilot execution, or schedule enablement.

No product UI is changed by this program. A product-design spec is not required for the program itself. Individual product work routed through these workflows still requires `product-designer` and a `*-design.md` artifact when it materially changes a screen, interaction, usability, or accessibility behavior.

### 0.1 Audit-resolution revision

This in-place revision resolves all findings from `2026-07-17-three-delivery-workflows-audit.md`. The audit remains unchanged as the independent record that caused the revision. The following ledger is normative for the repeated audit:

| Finding | Locked resolution | Normative plan sections | Required proof |
|---|---|---|---|
| `P1.1` | Scheduled worktrees are ephemeral control surfaces; one machine-stable per-repository state home owns the versioned base allocation mutex/registry plus autonomous lease, state, journal, reservations, and persistent issue worktrees. | 2, 7.2, 7.5, 8.2, 8.3, 11 | Two distinct scheduled worktrees, scheduled-worktree cleanup, crash recovery, same status from any linked worktree, and no duplicate Linear/GitHub mutation tests in 10.3. |
| `P1.2` | A deterministic repository-scoped active-work reservation protects autonomous, semi-autonomous, and manual implementation in the same repository in addition to Linear's global tracked WIP. | 2, 3, 5.3, 6.2, 7.4, 7.5, 8.2 | Manual-planning race, local SaaS implementation, reservation renewal/staleness, dirty-work fail-closed, Release/workflow-managed Handoff, and different-repository tests in 10.1 and 10.3. |
| `P1.3` | Scheduled delivery uses a least-privilege unattended profile plus a mutation-free permissions/connectivity preflight before claim. | 2, 7.3, 8.4, 9 phases 2/5/7 | Denied network/state/engine/loopback/Git mutation cases and one approved-profile proof in 10.3/10.4. |
| `P2.1` | Draft tracked evidence is committed before the final gated head; final exact-SHA attestations are stored externally without another branch mutation, with deterministic evidence-only reuse rules. | 7.7, 7.8, 8.2, 11 | Evidence-only versus executable delta, clean exact-final-head local validation/review, QA reuse, merge identity, and no post-merge repo-mutation tests in 10.3. |
| `P2.2` | `src/skills/goal-to-delivery/references/` becomes the intentional canonical cross-tool protocol; repo guidance remains canonical for repo-specific and stricter rules, with explicit precedence and parity validation. | 3.1, 4.2, 5.5, 8.4, 9 phases 1/3 | Source-to-dist-to-installed version/hash/reference parity and duplicate-norm rejection in 10.2. |
| `P2.3` | One deterministic workflow-init helper atomically allocates and registers local work and allows only exact, compatible resume or explicit workflow-managed Handoff. | 5.1, 5.2, 5.4, 8.1, 8.2 | Simultaneous allocation, same-goal distinct IDs, explicit resume, cross-worktree rejection/workflow-managed Handoff, later Linear attachment, and history fallback tests in 10.1/10.2. |

No implementation, migration, or rollout may proceed until the revised plan/task pair passes its repeated independent audit.

### 0.2 Plan-and-task audit resolution — 2026-07-18

This in-place planning revision resolves every finding from `2026-07-18-three-delivery-workflows-task-audit.md` plus the user's clarification that phase 1 must work locally and requires no hosted CI pipeline. The failed audit remains unchanged as the independent record that caused this revision.

| Finding / clarification | Locked resolution | Normative plan sections | Required proof |
|---|---|---|---|
| `P1.1` plus user clarification | Phase 1 uses deterministic repository-specific local gates only. No hosted check is required for `ai-config` or SaaS, no pipeline is added, and the existing SaaS GitHub Actions workflow is non-authoritative and out of scope. | 2, 6.4, 7.7, 7.8, 8.2, 8.4, 9, 10, 13–15 | Exact PR-head and exact merge-SHA local attestations from clean isolated worktrees using the matrix in 6.4; no check discovery/polling/budget dependency. |
| `P1.2` | `SAAS-45` solely owns versioned base local-work primitives; `SAAS-46` consumes them without reimplementation and adds autonomous supervisor/reservation functionality plus assembled reservation-aware transfer. | 5, 7.2, 7.6, 8.1, 8.2, 8.4, 9 phases 1/2, 12 | Base-module ownership/import checks, registry-only transfer tests in `SAAS-45`, and live-reservation authority-transfer tests in `SAAS-46`. |
| `P2.1` | Work keys are provider-observed or allocator-generated only, and slug/folder allocation is Windows-safe, case-insensitive, containment-checked, and reparse-point-safe. | 5.1, 5.2, 5.4, 8.1, 9 phase 1, 10.1/10.2, 14 | Invalid-character/device-name/traversal/case-collision/containment/reparse tests on Windows. |
| `P3.1` | The custom transfer is named **workflow-managed Handoff** and is explicitly distinct from Codex desktop's native **Hand off** action. Native **Hand off** alone never transfers workflow authority. | 5.2, 5.3, 6.2, 8.1, 9, 10, 11, 14, 15 | Native-action mismatch fails closed with deterministic recovery; successful workflow-managed transfer revokes the source's later writes. |
| Re-audit `P2.1` | Hosted-check results remain outside the phase-1 quality/authority model, while provider-enforced push/merge refusal is handled as a real deterministic transport/policy failure without bypass or settings mutation. | 2, 6.3/6.4, 7.7–7.9, 9 phases 2/5/6, 10.3/10.4, 12–15 | `SAAS-48` fixtures cover push and merge refusal, transient versus paused classification, retry exhaustion, exact attended retry, idempotency/redaction, protected-state preservation, and zero check query/settings bypass. |

The task breakdown must now be revised to match this plan and the combined plan/task pair must pass another independent audit. No implementation, Linear mutation, Git/GitHub mutation, installation, notification publishing, pilot, or schedule action is authorized by this revision.

## 1. Overview

### 1.1 Direction

Create three reusable workflow entry skills rather than three copies of the agent stack. Each entry skill selects an advancement, clarification, authority, tracking, and completion policy. All three route work through the same planner, product designer, tasker, auditor, implementers, code reviewer, QA verifier, and documentation policy.

The distinction is policy, not capability:

- `$linear-delivery-loop` owns unattended queue execution for one deterministically prepared Linear issue.
- `$goal-to-delivery` owns one user-selected goal or issue and advances it automatically to a declared completion boundary.
- `$spec-driven-delivery` owns one user-selected goal or issue but advances only the stage the user explicitly requests.

Skills are the reusable user-facing entry points because Codex skills can be invoked explicitly with `$skill-name`, can also be selected by description, and user-level skills are available across repositories. Repository `AGENTS.md` files remain the durable place for repo-specific commands, conventions, definitions of done, and safety rules. A recurring Codex task must explicitly invoke `$linear-delivery-loop` rather than relying on implicit skill selection.

Prompt orchestration does not own durable autonomous correctness. Linear selection, the global WIP check, leases, state revisions, retry counters, issue transitions, notifications, Git/GitHub mutations, and exact-SHA gates remain deterministic adapter responsibilities.

### 1.2 Goals

- Offer explicit autonomous, semi-autonomous, and manual spec-driven workflows without duplicating specialist agents.
- Make a local goal with no Linear issue a first-class work source in any repository where the shared skills are installed.
- Let a local workflow later attach to Linear without recreating or losing its artifacts.
- Preserve deliberate manual planning and approval while also supporting one-command goal-to-working-implementation delivery.
- Keep `$goal-to-delivery` useful for code, documentation, configuration, research, and other artifact-producing work.
- Keep workflow artifacts in the repository and durable product/technical guidance in a searchable docs-as-code wiki.
- Keep Linear optional for semi-autonomous and manual work, but authoritative for autonomous queue work.
- Preserve one bounded issue, one target repository, and one primary PR for autonomous code-bearing work.
- Define completion separately from publication: working tree, artifact, commit, PR, and merge are distinct boundaries.
- Require real review and runtime acceptance QA before autonomous merge, not only plan validation or compilation.
- Keep current SaaS work locally runnable before prioritizing AWS, PostHog, hosted pipelines, and other external integrations.
- Keep reusable workflow policy and engine code in `ai-config`; keep project-specific commands and identifiers in thin repo adapters.

### 1.3 Non-goals

- Do not create separate planner, designer, tasker, auditor, implementer, reviewer, QA, or docs agents for each workflow.
- Do not require Linear for a local goal or for use in another repository.
- Do not let `$goal-to-delivery` select backlog work or grant itself autonomous authority.
- Do not let `$spec-driven-delivery` advance to another stage merely because the current stage succeeded.
- Do not make conversation memory authoritative for locks, checkpoints, retries, external state, or completion.
- Do not add parallel autonomous issue execution in phase 1.
- Do not add Telegram or Slack to the notification design.
- Do not add Windows Task Scheduler in phase 1; Codex Scheduled is the chosen heartbeat surface.
- Do not autonomously provision cloud resources, incur recurring spend, alter production secrets, delete data, revert `main`, or perform other destructive operations.
- Do not extract a separate workflow-engine repository until a real second-project requirement cannot be represented by the shared configuration schema.
- Do not rewrite historical `LUC-*`, flat `docs-ai`, or audited v1 artifacts.

## 2. Assumptions and Constraints

- `ai-config/src/` is canonical. `dist/` and installed tool adapters are generated output.
- Shared skills must build and sync to Codex, Claude, and Copilot; Cursor continues to consume project-local generated instructions/rules.
- User-level skills provide cross-repository entry points. Repo-local `AGENTS.md` and docs provide the exact commands and constraints for the current repository.
- The SaaS Linear team key and issue prefix are `SAAS`; the project remains `SaaS Boilerplate`.
- Linear uses ordinary states: `Backlog`, `Todo`, `In Progress`, `In Review`, `Done`, `Canceled`, and `Duplicate`.
- `Ready for Codex` must not remain as a workflow state or operational concept. Readiness is expressed through ordinary states, issue quality, dependencies, and labels.
- Autonomous eligibility is `Todo + autonomous`, excluding stop/defer labels.
- `blocked`, `needs-human`, `needs-refinement`, and `external-integration` remain the exception/sequencing labels. A `manual` label is not required.
- One global SaaS Linear WIP slot spans tracked issues in `In Progress` and `In Review`. In addition, every active delivery that can edit the SaaS repository uses the repository-scoped reservation in the machine-stable supervisor home. Local work in another repository does not block SaaS.
- A user-selected SaaS issue is manual ownership. Entry/reservation immediately reconciles any autonomous lease and removes `autonomous` before `Plan`; it fails closed instead of racing an active autonomous owner.
- Autonomous code-bearing `Done` means the latest issue PR/repair is squash-merged to `main` and the exact merge SHA passes the repository-specific clean local post-merge gate.
- A manual or semi-autonomous workflow can finish successfully at an earlier requested boundary without moving a linked issue to `Done`.
- Linear's direct GraphQL API is the deterministic transport. It uses only the `LINEAR_API_KEY` process environment variable and never writes the key to repositories, commands, logs, state, comments, artifacts, or notifications.
- Linear is the durable unattended decision record; ntfy attracts attention; the Codex Scheduled inbox provides run visibility. Native Linear notifications are useful but not the sole attention guarantee while the API actor and owner are the same user.
- The autonomous schedule runs every five minutes from one dedicated Codex task rooted at SaaS in Worktree mode. That scheduled worktree is an ephemeral control surface, never authoritative state or issue work. Persistent supervisor state and adapter-owned issue worktrees live outside every checkout. The computer, Codex desktop app, and repository must remain available.
- The heartbeat cadence is recovery/wake-up frequency, not a one-stage throttle. One run works on at most one issue but may continue that issue through all routine stages.
- Phase 1 is local-only for delivery authorization. No hosted CI/check is required for `ai-config` or SaaS, and this program adds no pipeline.
- The existing SaaS `.github/workflows/validate.yml` may remain, but its check status is non-authoritative and out of scope: phase 1 never requires, queries, polls, waits on, or accepts it as quality evidence or authorization. Separately, GitHub can physically refuse push, PR, or merge because of transport/provider availability, permissions, branch protection, rulesets, required-check enforcement, merge queues, or other repository policy; the adapter handles that refusal under section 7.8.1 and never bypasses or weakens the control.
- SaaS local validation remains `pwsh ./scripts/validate-all.ps1`; real HTTP/Playwright acceptance is an additional exact-PR-head gate where behavior is affected.
- Optional hosted CI/provider integration is explicitly deferred beyond phase 1 and requires a separately planned and approved capability. The phase-1 engine contains no required check discovery, polling, timeout, or failed-head budget.
- The locked repository-owned tool pins remain `mkdocs==1.6.1` and direct exact dev dependency `@playwright/test` `1.61.1` unless a separately reviewed dependency-update decision supersedes them.
- The program builds its own deterministic adapter. Until the SaaS adapter is merged, installed, and verified, implementation children use the documented interactive bootstrap exception after explicit user approval.
- The scheduled profile is `workspace-write` with `approval_policy = "never"`, explicitly configured writable roots and network proxy allowlists, and fixed command rules. Full access is not the default or fallback.
- The scheduled shell inherits only required core process variables, `PATH`/Git/`gh` needs, `LOCALAPPDATA` or the explicit state-home override, `LINEAR_API_KEY`, and configured ntfy variables. Unrelated cloud/provider credentials are excluded.

## 3. Workflow Policy Matrix

| Policy | Autonomous | Semi-autonomous | Manual spec-driven |
|---|---|---|---|
| Entry | `$linear-delivery-loop` from the versioned Codex Scheduled prompt or explicit attended pilot | `$goal-to-delivery <goal-or-issue>` | `$spec-driven-delivery <stage> <goal-or-issue>` |
| Work source | Required eligible Linear issue prepared by the deterministic adapter | Local goal by default; optional explicitly supplied issue | Local goal by default; optional explicitly supplied issue |
| Queue selection | Deterministic adapter only | Never | Never |
| Stage advancement | Automatic while the adapter's prepared capability remains valid | Automatic through the declared completion boundary | Exactly one explicitly requested stage; never auto-advance |
| Clarification | Auto-resolve safe assumptions; pause high-risk ambiguity in Linear and notify | Auto-resolve safe assumptions; ask only when ambiguity materially changes outcome or safety | Never auto-resolve a material ambiguity; ask the user, one focused question at a time |
| Implementation authority | Narrow `autonomous` issue authorization, enforced by adapter | User's goal request authorizes scoped working-tree implementation | Only an explicit `Implement` stage authorizes scoped working-tree implementation |
| Git authority | Adapter may branch, stage, commit, push, create/update PR, and gated squash-merge only for the prepared issue | Default is no Git mutation; commit/PR/merge only when included in the declared boundary or separately granted | Each `Commit`, `PR`, or `Merge` action is separately invoked/approved |
| Linear use | Required and authoritative | Optional; a supplied issue enables linked tracking under repo policy | Optional; tracking changes happen only in the explicitly invoked stage/action |
| SaaS global WIP | Always | Only when attached to and claiming a SaaS issue | Only after the explicit `Implement`/tracking action claims a SaaS issue |
| Repository reservation | Required before autonomous selection/claim | Required before automatic delivery can edit the target repo; isolated planning evidence in its uniquely allocated `docs-ai` folder may defer it | Required before `Implement` or any other stage that mutates repository deliverables, or earlier through explicit `Reserve`; retained until deterministic Release/workflow-managed Handoff/terminal reconciliation |
| Default completion boundary | Merge plus exact-SHA post-merge validation | Working tree | The requested stage/artifact only |
| Non-code work | Not eligible in phase 1; use manual-operational evidence | Supported with `artifact` completion | Supported with `artifact` completion |
| Failure behavior | Retry within budget; pause/escalate deterministically | Fix/retry automatically when safe; otherwise ask user and preserve artifacts | Report the stage result and wait for the next user instruction |
| May become autonomous | Already entered through the only autonomous gate | Never self-elevates | Never self-elevates |

### 3.1 Mode detection and precedence

Workflow selection is explicit and stable for the life of the work item:

1. A valid deterministic `PreparedIteration` capability supplied by `$linear-delivery-loop` selects autonomous policy.
2. An explicit `$goal-to-delivery` invocation selects semi-autonomous policy.
3. An explicit `$spec-driven-delivery` invocation selects manual policy.
4. Without one of these entries, repo-local `AGENTS.md` defines the default; the shared project template defaults non-trivial work to manual spec-driven delivery.

Issue labels do not silently switch an active conversation into autonomous mode. The `autonomous` label authorizes only the deterministic adapter after it has acquired the lease, reconciled WIP, re-read eligibility, and produced a capability for that issue.

`$goal-to-delivery` and `$spec-driven-delivery` reject an attempt to pass `mode: autonomous` directly. They can consume autonomous policy only when called by `$linear-delivery-loop` with the adapter-prepared capability. Even then, specialists propose work; the adapter independently validates every mutation.

Normative precedence is: user/system instructions and repository-specific stricter safety constraints, then the invoked entry policy, then the canonical shared delivery contract. Repo guidance cannot weaken user/system or shared safety floors; entry skills cannot weaken repository-specific stricter safety. Any unresolved conflict fails closed before implementation or external mutation and is reported as a clarification/blocker.

### 3.2 Workflow examples

```text
$goal-to-delivery create an authorization flow with PKCE
  -> local work key
  -> automatic artifacts and implementation
  -> review + runtime QA + docs
  -> stop with tested changes in the working tree
```

```text
$goal-to-delivery SAAS-123 --completion pr
  -> verify/claim the selected issue under manual ownership
  -> automatic delivery stages
  -> commit, push, and open PR because that boundary was explicitly requested
  -> stop in In Review; user owns merge unless merge was explicitly granted
```

```text
$spec-driven-delivery Plan add tenant-scoped API keys
$spec-driven-delivery Clarify
$spec-driven-delivery Task
$spec-driven-delivery Audit
$spec-driven-delivery Implement
$spec-driven-delivery QA
$spec-driven-delivery PR
  -> each invocation performs only that stage and returns control
```

## 4. Shared Delivery Core

### 4.1 Canonical stages and owners

| Stage | Primary owner | Required output or gate |
|---|---|---|
| `discover` | active orchestrator using `$repo-discovery` | Exact repo instructions, source docs, relevant patterns, tests, and conflicts |
| `plan` | `planner` | Goal, non-goals, architecture/contracts, risks, tests, rollout, sources |
| `clarify` | `planner` or entry skill policy | Recorded assumptions and resolved/paused material decisions |
| `design` | `product-designer` when needed | Implementer-ready `*-design.md`; otherwise explicit `design: not required` |
| `task` | `tasker` | Concrete ordered tasks with acceptance criteria, likely files, tests, and dependencies |
| `audit` | independent `auditor` | Adversarial verdict against requirement, plan, design, tasks, and repo sources |
| `implement` | matching implementer(s) | Scoped implementation, tests, and change manifest |
| `review` | `code-reviewer` | Exact-diff findings against acceptance, security/tenant boundaries, and repo conventions |
| `qa` | `qa` using `$qa-verification` | Real behavior evidence mapped to every acceptance criterion |
| `docs` | `$docs-as-code`, with `$luchdom-docs` policy where applicable | Nearest durable docs updated or explicit no-impact reason |
| `publish` | authorized root/adapter | Requested commit/PR boundary with exact identities |
| `merge` | user or authorized deterministic adapter | Squash merge after exact-head gates |
| `post_merge` | deterministic adapter or explicit manual stage | Clean validation of the exact merge SHA and completion record |

The auditor is pre-implementation and does not replace code review. Code review inspects what was implemented and does not replace runtime QA. QA exercises actual HTTP/browser/behavior paths where acceptance criteria require them and does not fix production code by default.

### 4.2 Shared references

As an intentional migration from the current project-template doctrine, `src/skills/goal-to-delivery/references/` becomes the canonical cross-tool reusable delivery protocol:

```text
src/skills/goal-to-delivery/
  SKILL.md
  references/
    delivery-stages.md
    artifact-contract.md
    clarification-policy.md
    quality-gates.md
    completion-boundaries.md
    work-descriptor.schema.json
```

`$spec-driven-delivery` and `$linear-delivery-loop` consume those references instead of copying them. Their own `SKILL.md` files define only entry-specific advancement, authority, tracking, and stop policy. Build validation must fail when these references drift, disappear, or are duplicated as competing policy.

Every Codex, Claude, Copilot, and Cursor project template and the canonical `ai-config` docs must adopt the same ownership and precedence statement in the same change. Generated `dist/` and installed copies carry a version/hash manifest and references back to canonical `src`; they are generated projections, not independently editable doctrine. The old sentence that skill references are “portable summaries, not the source of truth” is removed everywhere operational.

Repository `AGENTS.md` and curated repo docs remain canonical for repository-specific commands, domain rules, safety constraints, definitions of done, and stricter requirements. They do not copy the cross-tool protocol. Precedence follows section 3.1; an unresolved conflict or an attempted weakening fails closed.

`$goal-to-delivery` owning the shared references does not make semi-autonomous advancement the default for consumers. The caller policy remains authoritative:

- `$goal-to-delivery` uses automatic advancement;
- `$spec-driven-delivery` uses manual advancement;
- `$linear-delivery-loop` uses automatic advancement plus deterministic autonomous checkpoints.

### 4.3 Specialist agent architecture

Use one shared set of specialists:

```text
entry skill
  -> planner
  -> product-designer when required
  -> tasker
  -> independent auditor
  -> dotnet / nextjs-mui / react / jekyll-site-builder
  -> code-reviewer
  -> qa
  -> docs skills
```

No specialist mutates Linear independently. In autonomous work, no specialist performs state-changing Git/GitHub operations. It returns structured proposals and a real-file change manifest to the deterministic adapter. In semi/manual work, Git authority follows the explicit completion boundary and the active conversation.

`feature-driver` becomes a one-migration-cycle compatibility router to `$goal-to-delivery`. It must not retain its own orchestration doctrine and must never route to autonomous execution. Remove it after generated/installed references and documentation use the three skills.

`multi-agent-delivery` remains a specialist handoff primitive. It must understand all three policies but must not choose a workflow, select Linear work, or override the caller's advancement/authority policy.

### 4.4 Stage advancement contracts

Semi-autonomous advancement:

- Start from one user-provided goal or selected issue.
- Continue through every applicable stage without asking for routine approval.
- Return to planning/tasking when audit exposes a safe fixable gap.
- Return to implementation when review or QA finds a scoped defect, within the retry budget.
- Ask the user only when a material decision cannot be resolved safely from requirements, repo evidence, or conservative precedent.
- Stop exactly at the declared completion boundary.
- Never select a second work item.

Manual advancement:

- Validate that the requested stage's prerequisites exist.
- Execute only the named stage and write/update only its permitted artifact or implementation output.
- Report the next available stages without invoking them.
- `Clarify` never silently resolves a material ambiguity. Ask one focused question at a time. If no ambiguity remains, ask the user to confirm that the current plan/assumptions may be locked.
- `Implement` does not imply `Review`, `QA`, `Commit`, `PR`, or `Merge`.
- `QA` does not imply fixes; a later explicit `Implement` action handles defects.
- Planning/artifact-only stages need no repository editing reservation unless the user explicitly invokes `Reserve`; `Implement` requires it and preserves it through the chosen deterministic release boundary.

Autonomous advancement:

- Accept only one adapter-prepared issue and capability.
- Continue routine stages in the same heartbeat while the lease/capability remains valid.
- Apply every checkpoint through the deterministic adapter.
- Stop for external wait, completion, pause, retry exhaustion, non-retryable failure, lease/capability loss, or Codex interruption.
- Never run selection again after the prepared issue completes or pauses.

## 5. Work Source, Tracking, and Artifact Contracts

### 5.1 Work descriptor

Every workflow starts through the shared deterministic `workflow-init` helper and receives a schema-validated work descriptor:

```json
{
  "schemaVersion": "2.0",
  "workflowId": "uuid",
  "workflow": "autonomous|semi-autonomous|manual",
  "workSource": "linear|local",
  "workKey": "SAAS-123",
  "slug": "pkce-authorization",
  "repositoryKey": "saas",
  "repositoryRoot": "absolute-path-observed-by-runtime",
  "goal": "observable outcome",
  "acceptanceCriteria": [],
  "nonGoals": [],
  "tracking": {
    "provider": "linear|none",
    "externalId": "SAAS-123|null"
  },
  "completionBoundary": "artifact|working-tree|commit|pr|merge",
  "physicalWorktreeFingerprint": "runtime-observed-repository-and-worktree-identity",
  "riskFlags": []
}
```

The `workKey` example above is one provider-observed external issue key. A local workflow instead receives the allocator-generated zero-padded sequence such as `001`; these are alternatives, never a literal combined value. The helper accepts only a canonical key returned by the configured provider or its own next local sequence. A model, goal, prompt, or user-authored slug can never supply or override `workKey`.

The runtime derives repository identity from normalized `git rev-parse --git-common-dir`, derives the exact physical worktree fingerprint from Git-observed paths/identity, and observes absolute paths; model output cannot grant itself access to another repository or path. `workflowId` is immutable and is the primary resume identity even when two people/tasks independently use the same goal text.

Resume is never inferred fuzzily from chat memory, goal similarity, slug, or “latest folder.” The caller must supply exactly one registered workflow ID, exact artifact path, or unique external issue ID. The helper resolves it through the per-repository registry and requires an exact compatible physical worktree before any write.

### 5.2 Local work is first class

For `workSource: local`:

- Linear preflight is skipped.
- No Linear issue is created or required.
- Under the `SAAS-45` base allocation mutex in the shared state home, `workflow-init` scans current `docs-ai/`, `docs-ai/history/`, and the registry case-insensitively; selects the next zero-padded sequence; validates the key/slug and resolved path under section 5.4; atomically reserves the directory with create-new semantics; writes and schema-validates `workflow.json`; registers the workflow ID/work key/path/fingerprint; and releases the mutex only after readback succeeds.
- Directory or registry collision causes a bounded rescan/retry; a partial allocation is quarantined for reconciliation and is never silently reused.
- The artifact folder is `docs-ai/001-pkce-authorization/`.
- The workflow does not consume the SaaS global Linear WIP slot.
- The workflow writes no state, labels, comments, or notifications to Linear.
- Repo-local instructions and validation commands still apply.
- A semi-autonomous local workflow that will edit SaaS acquires the SaaS repository reservation before automatic delivery begins. Manual Plan/Clarify/Task/Audit stages may remain unreserved only while they write inside their uniquely allocated workflow folder. `Implement` and any non-code/artifact stage that changes curated docs, configuration, product files, or another repository deliverable cannot start without explicit `Reserve` or an automatically acquired reservation authorized by that invoked stage.
- A local workflow may be attached to Linear later through one atomic registry/`workflow.json` transaction that first proves the external ID is not mapped elsewhere. Do not rename the folder or recreate its evidence; preserving the stable workflow ID and path is more important than changing the prefix.
- Local work in another repository uses that repository's separate supervisor home and reservation and therefore cannot block SaaS.

Cross-context resume with uncommitted changes fails closed and directs the user/worker to the registered original worktree. The only alternative is an explicit user-authorized **workflow-managed Handoff**. The `SAAS-45` base helper writes a redacted patch plus change manifest into the state home, proves the destination is the same repository and has no overlapping/dirty paths, applies the transfer without staging, committing, pushing, or changing branches, validates the result, updates the registry's physical-worktree mapping atomically, and records both endpoints. This base transition is registry-only: it does not claim or prove transfer of a live editing reservation. A failed or ambiguous transition leaves the original mapping authoritative.

Codex desktop's native **Hand off** action is a separate Git/chat movement feature. Invoking native **Hand off** alone does not call the workflow helper and therefore does not update the workflow registry, lease, or reservation and never transfers workflow authority. A later command from a natively moved context deterministically detects the physical-worktree mismatch, rejects writes/checkpoints, points to the registered source, and offers either explicit workflow-managed Handoff or attended recovery/reconciliation. `SAAS-46` assembles the base registry transition with live reservation/lease checks and owns the proof that successful workflow-managed Handoff transfers all authority and rejects every later workflow-managed source write.

### 5.3 Linear-linked manual and semi-autonomous work

When the user explicitly supplies an issue and the repo has a configured tracking adapter:

- Read the issue and validate that it maps to the current repository and achievable goal.
- Entry/`Reserve` immediately checks the shared registry/reservation and reconciles any autonomous lease for that exact issue. If safe, it removes `autonomous` before `Plan`; if an autonomous owner, other workflow, or ambiguous stale record exists, it fails closed before artifacts or labels are mutated.
- Plan/Clarify/Task/Audit may remain `Backlog` or `Todo` and do not consume the Linear global WIP slot, but the issue-to-workflow reservation prevents autonomous selection of that same issue. Semi-autonomous work that will automatically reach implementation also acquires the repository editing reservation at entry.
- `Implement` requires the repository reservation, checks the global tracked WIP slot, and moves the linked issue to `In Progress`. If another tracked SaaS issue consumes the slot, fail closed and ask the user to finish/release it.
- A PR boundary moves a linked code issue to `In Review`.
- Working-tree and commit boundaries for code remain `In Progress` and keep the repository reservation until the user explicitly invokes `Release` or workflow-managed Handoff, opens a PR, merges, or abandons/reconciles the work. `Release` moves the issue to `Todo` or `Backlog`, records the incomplete boundary, and never restores `autonomous` unless the user explicitly requests it and the issue contract is revalidated.
- A fully accepted non-code artifact may move directly to `Done` under its repository completion rule. A code issue reaches `Done` only after merge plus required post-merge validation; for SaaS that is squash merge plus exact-merge-SHA validation.
- Workflow-managed Handoff transfers the reservation only through the assembled deterministic `SAAS-46` contract. Native Codex **Hand off** never does. Abandonment requires reconciliation of artifacts, dirty files, branch/PR, external issue, and reservation before release.
- A PR-linked issue keeps repository/Linear WIP ownership through `In Review`; merge or deterministic release/abandon reconciliation clears it.

Linear is an adapter for these workflows, not their execution engine. A repo without Linear configuration can use the same local path unchanged.

### 5.4 Artifact layout and transition

New work uses:

```text
docs-ai/<work-key>-<slug>/
  workflow.json
  <date>-<slug>-plan.md
  <date>-<slug>-design.md       # only when required
  <date>-<slug>-tasks.md
  <date>-<slug>-audit.md
  <date>-<slug>-code-review.md
  <date>-<slug>-qa.md
  <date>-<slug>-completion.md
```

`<work-key>` is either the provider-observed canonical issue key when one exists at creation time or the allocator-generated local zero-padded sequence matching `^[0-9]{3,}$`. Provider adapters validate their canonical key grammar before allocation; for Linear `SAAS` work that is `^SAAS-[1-9][0-9]*$`. No model-controlled value is accepted. Dated filenames preserve chronology; immutable workflow ID plus stable folder preserves later links.

`<slug>` is a deterministic normalization of display text followed by validation; the normalized result is lowercase ASCII, 1–48 characters, and matches `^[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?$`. Allocation rejects separators, `.`/`..` segments, control characters, Windows-invalid characters (`< > : " / \\ | ? *`), trailing dots/spaces, and case-insensitive Windows device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`). Normalization never turns an invalid explicit path-like value into a trusted path; the helper rejects unsafe input before deriving a safe display slug.

Before create-new allocation, the helper compares the proposed folder name case-insensitively against current `docs-ai/`, `docs-ai/history/`, and registry paths. It resolves the repository's intended `docs-ai` root and proposed parent/final path, verifies the final path remains a strict descendant of that root, and rejects any existing ancestor/component that is a symlink, junction, mount point, or other reparse point. The same containment and reparse checks run again after atomic creation/readback. Any collision, traversal, alias, containment ambiguity, or reparse escape fails closed or uses the bounded allocator rescan for a generated local sequence; it never overwrites or follows the path.

`workflow.json` contains no secrets. It records immutable workflow ID, work source, workflow policy, repository key, physical worktree fingerprint, artifact paths, declared completion boundary, current artifact stage, external tracking IDs, and superseded artifact names. It is schema-validated evidence/navigation metadata, not the autonomous lease, reservation, or authority source. The registry in the shared supervisor home maps workflow ID, work key, optional external ID, exact artifact path, and physical worktree; tracked metadata and registry updates use compare-and-swap/atomic readback.

Existing `docs-ai/<NNN>-<slug>-<YYYY-MM-DD>/` and flat historical artifacts remain valid. During implementation, update `planner`, `tasker`, `auditor`, `qa`, `multi-agent-delivery`, `task-audit-breakdown`, project templates, and tests together so every producer/consumer recognizes the new convention plus explicit historical fallback. Do not partially migrate only one producer.

### 5.5 Documentation contract

- Per-work evidence stays under `docs-ai/`.
- Durable how-to, concept, reference, ADR, runbook, and troubleshooting content stays under the repository's curated `docs/` tree.
- Curated docs form the searchable/explanatory wiki and link to canonical shared contracts plus repository-specific rules. They do not restate a second normative copy of the shared protocol.
- Every task records docs impact as an exact page/update or `none` with a reason.
- A setting such as “how to configure X” becomes a task-oriented how-to with prerequisites, steps, verification, rollback, and troubleshooting.
- MkDocs provides local navigation and search; noisy run evidence is linked when useful but not added wholesale to primary navigation.
- Linear receives concise links and transition evidence, not copies of full documents.
- Once pushed, links use immutable blob SHAs or merged `main` paths.
- Non-code artifact work can complete at the `artifact` boundary after its acceptance criteria and documentation checks pass; it must not create an empty PR.

## 6. Clarification, Authority, and Completion Contracts

### 6.1 Clarification classification

Safe assumptions are reversible, supported by repo/docs precedent, conservative, dependency-free, behavior-preserving, or aligned with an existing architecture/design pattern. Semi-autonomous and autonomous workflows may resolve them and must record them.

Material/high-risk ambiguity includes:

- authentication, authorization, security, privacy, tenant isolation, or secrets;
- billing, entitlement, money, or product rules that change observable behavior;
- destructive data/schema operations or irreversible migration;
- recurring cost, vendor lock-in, cloud resources, or production operations;
- materially different UX directions without precedent;
- conflicting requirements or source-of-truth docs;
- a scope that no longer fits one bounded goal/reviewable change.

For high-risk ambiguity:

- autonomous delivery pauses the issue as `Backlog + needs-human`, writes one structured decision request, reconciles/releases the repository reservation and Linear WIP only when protected changes are durably recoverable, and sends ntfy;
- semi-autonomous delivery preserves work/artifacts and its reservation when dirty/unmerged changes exist, then asks one focused question in the active task;
- manual delivery asks the user during `Clarify` and does not advance until explicitly told; a planning-only issue reservation may remain, while an editing reservation is retained if work is dirty/unmerged.

### 6.2 Completion boundaries

| Boundary | Meaning |
|---|---|
| `artifact` | The requested non-code/document/spec output exists and its acceptance checks pass. |
| `working-tree` | Scoped implementation, tests, review, QA, and docs are complete in the current working tree; no Git mutation is implied. |
| `commit` | `working-tree` gates pass and an explicitly authorized scoped commit exists locally. |
| `pr` | `commit` gates pass, branch is pushed, one PR exists, and linked tracking may move to `In Review`. |
| `merge` | PR exact-head local gates pass, authorized squash merge occurs, and the exact merge SHA passes the repository-specific clean local post-merge gate. |

`$goal-to-delivery` defaults to `working-tree`. A user can declare a higher boundary in the original invocation or grant it later. A later grant resumes the same work descriptor and artifacts; it does not rerun selection or recreate planning.

Manual workflow stages are not inferred from the boundary. The user explicitly invokes `Commit`, `PR`, or `Merge`.

An autonomous code-bearing issue always targets `merge`. A manual-operational issue uses its evidence contract instead of an artificial branch or PR.

Completion boundary and tracking/reservation behavior is deterministic:

| Outcome | Linear state when linked | Repository reservation |
|---|---|---|
| Plan/Clarify/Task/Audit only | Preserve `Backlog`/`Todo`; `autonomous` remains removed | Issue reservation retained; editing reservation optional until `Reserve`/`Implement` |
| Accepted non-code `artifact` | `Done` when repository acceptance rule is complete; otherwise `Todo`/`Backlog` | Release only after artifact/registry readback |
| Code `working-tree` or `commit` | `In Progress` | Retain until explicit `Release`, valid workflow-managed Handoff, PR/merge progression, or reconciled abandon |
| `pr` | `In Review` | Retain through PR-linked WIP |
| Validated `merge` | `Done` | Release after exact merge/post-merge state is durably recorded |
| Explicit `Release` before completion | `Todo` or `Backlog`, never automatically `autonomous` | Release only after dirty/unmerged state is absent or durably handed off and verified |

Reservations are renewable records with workflow/issue ID, repository ID, physical worktree, owner/run, revision, heartbeat, expiry, and dirty/branch/PR summary. A heartbeat renews only after matching ownership and physical state are observed. Expiry never means automatic release: stale clean planning-only reservations may be reclaimed after registry/external reconciliation; dirty files, unmerged commits, an open PR, uncertain worktree access, or ambiguous owner always fail closed and require original-worktree recovery or explicit user-authorized workflow-managed Handoff/Release. Time alone can never discard protected work.

### 6.3 Git/GitHub authority

- Read-only Git inspection is allowed in every workflow.
- Semi-autonomous implementation may edit and validate within the current worktree, but the default boundary grants no branch/stage/commit/push/PR/merge action.
- Manual `Implement` grants edit/validate authority only. Each Git publication action remains separately requested.
- Autonomous Git/GitHub mutation belongs only to the deterministic adapter and only while the prepared issue still carries `autonomous`, matches the run/lease, has no stop label/decision, and passes manifest/path checks.
- Autonomous authority is limited to `codex/SAAS-N-<slug>`, one PR to `main`, and numbered `codex/SAAS-N-repair-<attempt>` branches when post-merge repair is required.
- Force-push, rebase/history rewrite, direct `main` push, unrelated file changes, tags/releases, repo settings, secret changes, auto-revert, and destructive cleanup are never implied.
- Publication authority never includes repository/ruleset/branch-protection mutation, admin/bypass merge, merge-queue configuration, required-check weakening, or check-status queries. A provider refusal is state-machine input, not permission to circumvent external enforcement.
- The human user can always perform their own Git/GitHub actions; “sole mutator” applies to automated components.

### 6.4 Bootstrap exception and phase-1 local gate matrix

This program cannot use the deterministic adapter before that adapter exists. After the user explicitly approves implementation, `SAAS-45` through `SAAS-52` use manual/semi-autonomous delivery with root-task or human-controlled Git/PR actions explicitly authorized in the active conversation. Specialist subagents remain non-mutating. Each code issue still uses one target repository, one primary PR, independent review, applicable runtime QA, docs, squash merge, and exact-SHA local validation. The exception ends after the shared engine and SaaS thin adapter are merged, synced, installed, and verified.

Hosted CI is not a phase-1 quality gate in either repository. The existing SaaS workflow is neither removed nor repaired by this program; the engine does not discover, query, poll, wait for, budget, or accept hosted checks as evidence or authorization. GitHub may nevertheless enforce repository policy by refusing push/PR/merge. Such a refusal follows section 7.8.1 and never causes settings mutation, bypass, or a false local-gate success. Optional hosted-CI evidence integration remains a deferred, separately approved extension.

The repository-specific authoritative local gate matrix is:

| Repository / children | Exact PR/final head gate | Exact merge-SHA gate |
|---|---|---|
| `ai-config` / `SAAS-45`–`SAAS-49` | From a fresh isolated worktree checked out at the exact observed PR head, require a clean worktree, run `python .\scripts\validate.py`, pass independent review and applicable docs checks, then prove the worktree remains clean. `SAAS-45` introduces this aggregate command; each later child extends its manifest so the command includes every applicable build, marker, semantic, schema/module, contract, and temporary sync test available at that version. | From a separate fresh isolated worktree checked out at the exact squash-merge SHA returned by GitHub, require clean-before/after and rerun `python .\scripts\validate.py` successfully. |
| `saas` / `SAAS-50`–`SAAS-52` | From a fresh isolated worktree checked out at the exact observed PR head, require clean-before/after, run `pwsh ./scripts/validate-all.ps1`, pass independent review/docs checks, and run repository-pinned real HTTP/Playwright acceptance for every affected behavior with isolated disposable resources and cleanup evidence. | From a separate fresh isolated worktree checked out at the exact squash-merge SHA returned by GitHub, require clean-before/after and rerun `pwsh ./scripts/validate-all.ps1` successfully. |

Every attestation records the SHA observed by `git rev-parse HEAD`, the expected PR or merge identity independently read from GitHub, physical isolated-worktree identity, clean status before/after, exact command and arguments, exit code, relevant tool versions, timestamp, and redacted evidence location. A SHA mismatch, dirty worktree, missing aggregate member, failed command, incomplete required runtime QA, or ambiguous identity fails closed. Draft/final evidence handling follows section 7.8 without turning tracked reports into self-authorizing evidence.

## 7. Autonomous Control Plane

### 7.1 Responsibilities and boundary

`$linear-delivery-loop` has two layers:

1. a skill that explains the unattended policy, calls the deterministic command surface, and delegates the prepared goal through the shared delivery stages;
2. a deterministic engine under `src/skills/linear-delivery-loop/scripts/` that owns durable state and all external mutations.

SaaS owns only a versioned config, rendered heartbeat prompt, fixtures, docs, runtime-QA hooks, and a thin wrapper. It must not duplicate GraphQL, state-machine, lease, notification, Git, GitHub, or recovery logic.

Representative deterministic commands remain:

```powershell
pwsh ./scripts/agent-worker.ps1 -Action PrepareIteration -RunId <uuid>
pwsh ./scripts/agent-worker.ps1 -Action ApplyCheckpoint -InputPath <absolute-json-path>
pwsh ./scripts/agent-worker.ps1 -Action Status
pwsh ./scripts/agent-worker.ps1 -Action ReleaseLease -RunId <uuid>
```

The wrapper never launches nested `codex exec`. Structured payloads use files, not issue text or secrets in command arguments.

### 7.2 Runtime topology and machine-stable supervisor home

The Codex Scheduled Worktree run is ephemeral control only. It may be archived or cleaned without losing authority, work, or recovery state, and it is never reused as the authoritative issue worktree.

On every command, the engine consumes the exact versioned `SAAS-45` base modules; it must not rederive or reimplement repository identity, stable state-home selection, the allocation mutex, workflow registry, physical-worktree binding, or local allocation/resume/attach behavior. Those base modules:

1. executes `git rev-parse --git-common-dir`, resolves/normalizes the result without trusting the current working-directory spelling, and combines that stable Git identity with the configured repository key;
2. derives a collision-resistant `<repo-id>` and verifies the stored repository identity before opening state;
3. selects the supervisor base from explicit `LUCHDOM_DELIVERY_STATE_HOME`, otherwise `%LOCALAPPDATA%\Luchdom\ai-delivery`; the final authoritative home is `<base>\<repo-id>`;
4. rejects a base that is relative, inside any checkout/worktree, aliased to a different repository, inaccessible, or not writable; if neither override nor `LOCALAPPDATA` is usable, fail closed before mutation and never fall back under the scheduled worktree;
5. acquires the per-repository mutex and reads the same registry/state regardless of which linked worktree or scheduled run invoked it.

The authoritative layout is:

```text
<state-home>/
  repository.json
  mutex/
  supervisor-state.json
  reservations.json
  registry.json
  operations/<operation-id>/
  runs/<run-id>/
  handoffs/<workflow-id>/<handoff-id>/
  worktrees/<issue-id>/
  validation-worktrees/<operation-id>/
```

The base allocation mutex and workflow registry plus the autonomous renewable lease, repository reservations, state revision, operation journal, final attestations, and notification state live only here. Adapter-owned persistent issue worktrees live under `<state-home>\worktrees\<issue-id>` and survive cleanup of any scheduled-run worktree. Clean isolated local-gate worktrees live temporarily under `<state-home>\validation-worktrees\<operation-id>` and are bound to one observed commit SHA. One issue maps to one registered persistent worktree; creation/reuse is idempotent and containment-checked. The engine rejects implementation, staging, commit, or QA checkpoints whose observed worktree is the scheduled control worktree rather than the registered persistent issue worktree.

The deterministic engine alone owns autonomous terminal reconciliation, retention, and cleanup. It never deletes a worktree with dirty/unmerged/unpushed work, a live reservation, open PR, unresolved operation, or ambiguous external state. Gate-worktree cleanup additionally requires the recorded SHA, clean status, completed attestation, and verified containment. Cleanup is path-contained under the verified state home, recorded before/after, and never delegates recursive deletion through another shell. `Status`, recovery, reservation, and cleanup commands derive the same state root from any linked worktree.

### 7.3 Scheduled least-privilege permissions and mutation-free preflight

The unattended Codex task uses `sandbox_mode = "workspace-write"` and `approval_policy = "never"`. Setup grants read/execute access to the installed engine and explicitly grants writable roots only for the scheduled workspace/repository, the derived machine state home, and its persistent issue-worktree root. It does not grant write access to installed canonical engine files and does not use `danger-full-access` or full-access fallback.

Network is enabled through `sandbox_workspace_write.network_access = true` and a proxy allowlist limited to Linear GraphQL, GitHub APIs/`gh`, the configured Git remote hosts, the exact configured ntfy host, and exact loopback host/ports required by repository QA. QA may bind/request only declared loopback targets; broad LAN/local binding is not enabled. DNS/redirects to unapproved hosts fail closed.

The scheduled shell environment is minimal: required operating-system/core variables, `PATH` and explicit Git/`gh` needs, `LOCALAPPDATA` or `LUCHDOM_DELIVERY_STATE_HOME`, `LINEAR_API_KEY`, and configured ntfy variable names. Unrelated AWS, Azure, GCP, deployment, analytics, production, or other provider secrets are not inherited. Values are never echoed and redaction/sentinel checks cover process output and state.

Only fixed wrapper, local-validation, Git, and `gh` command shapes declared by the versioned project configuration are permitted. Because unattended `approval_policy = "never"` cannot repair a blocked protected `.git` operation, fixed rules explicitly cover the exact branch/worktree/status/diff/add/commit/fetch/push/merge and allowed `gh` PR/merge operations required by the state machine; arbitrary shell, arbitrary Git flags, hosted-check commands, force/history rewrite, and issue-derived commands remain denied.

Before selection, claim, label/state change, branch creation, or any other mutation, `PermissionPreflight` is mutation-free with respect to repositories and external systems and proves:

- installed engine/schema/config version is readable/executable and matches the wrapper;
- the stable state root resolves correctly, a disposable sentinel can be create/read/removed, and the per-repo mutex can be acquired/released;
- a disposable sentinel worktree directory can be create/read/removed under the persistent issue-worktree root without touching Git;
- fixed Git/`gh` commands have required read/auth access and protected `.git` commit/worktree capability is permitted for the later declared operations, using a disposable preflight fixture rather than the target repository history;
- Linear credentials exist/redact correctly and a read-only workspace/team/project query succeeds;
- Git remote/GitHub read/auth and exact repository identity succeed without write;
- ntfy variables/host are valid and connectivity succeeds without publishing; attended setup separately proves one redacted test publish;
- the exact configured loopback bind/request probe succeeds and cleanup completes;
- the repository-specific aggregate local gate command and isolated gate-worktree root are present, version-compatible, executable, and path-contained without running the gate or mutating repository history;
- required secrets exist, unrelated provider secrets are absent from the child environment, and sentinel values never appear in emitted evidence.

Any failed or ambiguous probe exits before claim/mutation, writes redacted actionable evidence to the Scheduled inbox and authoritative run journal, and sends ntfy only when connectivity and configuration were already proven safe. It cannot request an approval mid-run.

### 7.4 Heartbeat behavior

```text
five-minute Codex task heartbeat
  -> explicitly invoke $linear-delivery-loop
  -> acquire/renew invocation lease
  -> derive stable supervisor home and run mutation-free permission preflight
  -> preflight and reconcile Linear, Git/GitHub, reservations, and local state
  -> reconcile pending human decisions before queue selection
  -> inspect global In Progress/In Review WIP
  -> resume the matching autonomous issue
  -> or exit cleanly when manual WIP owns the slot
  -> or select one eligible Todo + autonomous issue
  -> re-read and claim it
  -> create adapter-owned PreparedIteration capability
  -> call shared delivery stages for that one goal
  -> validate/apply checkpoints and mutations deterministically
  -> stop on completion, pause, external wait, exhausted retry, unsafe failure, or interruption
  -> never select a second issue in the run
```

The dedicated Codex task uses Worktree mode only as the heartbeat control surface. Conversation context may help reasoning but every run derives the machine-stable home and reconciles durable state first. A healthy overlapping lease exits without noise. An expired lease is reclaimed only after repository reservation, persistent issue worktree, registry, journal, Linear, and GitHub reconciliation shows it is safe; ambiguity fails closed.

### 7.5 Selection, Linear WIP, and repository reservations

Before claim, acquire the per-repository mutex and inspect the shared repository reservation registry, then paginate every SaaS issue in `In Progress` and `In Review`:

- Any live SaaS repository reservation, including a planning-only reservation for a manually selected Linear issue, blocks new autonomous selection unless it belongs to the exact autonomous issue being resumed. It need not consume the Linear WIP slot to protect manual ownership.
- A manual local planning workflow has no reservation while it is confined to its uniquely allocated workflow folder; once reserved it blocks new autonomous selection. A clean unreserved planning-only workflow does not authorize other repository edits and must acquire the reservation before implementation or any stage that mutates a repository deliverable outside that folder.
- A stale/expired reservation is reconciled under section 6.2; dirty/unmerged/inaccessible/ambiguous work fails closed and is never released by time alone.
- Reservations derived from another normalized repository identity do not block SaaS.

- More than one active issue is a reconciliation failure; notify once and mutate nothing further.
- One manual issue consumes the global slot; exit successfully.
- One matching autonomous issue is resumed before any queue read.
- Only zero active issues permits selection.

An eligible candidate must satisfy:

```text
project = SaaS Boilerplate
team key = SAAS
state = Todo
labels contains autonomous
labels exclude blocked, needs-human, needs-refinement
labels exclude external-integration during local-first milestone
issue kind = code-bearing executable leaf
repository key = saas for the SaaS worker
exactly one observable, bounded goal
acceptance, non-goals, dependencies, validation, docs impact, and risk flags are complete
dependencies are satisfied
```

After complete pagination/filtering, order by Linear priority (Urgent, High, Normal, Low, None), then `createdAt` ascending, then numeric issue identifier ascending. Persist considered/rejected candidates in dry-run evidence and re-read the winner immediately before claim.

An incomplete/broad issue becomes `Backlog + needs-refinement` with a bounded split proposal. A deferred external issue becomes `Backlog + external-integration`. The worker does not invent product intent. The winning candidate is re-read, then its repository reservation and persistent issue-worktree mapping are created atomically before Linear claim; failure rolls back/reconciles the prepared local operation and performs no claim.

### 7.6 Lease, checkpoint, reservation, and state integrity

`SAAS-46` imports the versioned `SAAS-45` repository identity, state-home, allocation-mutex, registry, physical-worktree-binding, and local workflow modules by their canonical paths/schema versions. Import/version tests fail if a duplicate implementation appears under the autonomous engine. On top of those base modules, `SAAS-46` owns:

- short OS mutex per command invocation;
- renewable durable lease with run ID, heartbeat, expiry, and prepared capability nonce;
- atomic state writes;
- monotonically increasing state revision;
- expected previous stage and replay-safe transition ID;
- idempotent external-operation journal;
- repository-scoped active-work reservation and exact issue/workflow-to-persistent-worktree registry;
- independently observed Linear state, labels, branch, worktree, PR, base/head SHA, local-gate worktree/attestation, merge SHA, and retry counters.

`PreparedIteration` identifies one run, issue, repository, state revision, stage, and capability nonce. `$goal-to-delivery` can propose autonomous work only while that capability is current. `ApplyCheckpoint` independently re-reads external authorization and rejects stale or fabricated identity, stage, revision, capability, SHA, PR, local-gate attestation, or attempt data.

The engine persists state before or with an idempotent operation record. Lease and reservation are separate: the short-lived renewable run lease prevents concurrent autonomous mutations; the reservation protects the repository/work item across runs and interactive contexts. The assembled reservation-aware workflow-managed Handoff first validates the base registry-only transfer, then compare-and-swap transfers the matching live reservation/capability and revokes the source before exposing success. Native Codex **Hand off** never enters this transition; its resulting mismatch follows deterministic rejection/recovery. After a crash at a local or remote mutation boundary, the next heartbeat reopens the same supervisor home and persistent issue worktree, re-reads Git/Linear/GitHub, and reconciles rather than repeating blindly.

### 7.7 Durable stage policy

Autonomous stages remain:

```text
idle -> claimed -> planning -> design? -> tasking -> audit
  -> implementation -> local_validation -> draft_evidence -> publish
  -> exact_head_local_gate -> code_review -> runtime_qa
  -> evidence_finalize -> final_head_validation
  -> merge_ready -> merge
  -> post_merge -> done
```

Allowed repair/wait loops:

- audit may return to planning/tasking;
- local validation, code review, and runtime QA may return to implementation;
- a demonstrably transient GitHub push/PR refusal remains `In Progress + autonomous`; a demonstrably transient merge refusal remains `In Review + autonomous`; both retain branch/PR when present, reservation, and persistent worktree, release only the run lease, and follow section 7.8.1's bounded retry;
- base drift returns to base sync/local validation and invalidates affected gates;
- any executable delta after a gate returns to affected implementation/local-validation/review/QA stages;
- an evidence-only delta enters deterministic evidence reconciliation and final-head validation under section 7.8;
- failed post-merge validation enters same-issue numbered repair PRs;
- ordinary scope/decision pause maps to `Backlog` plus the applicable stop label; provider-publication pause is the explicit exception and preserves `In Progress` before PR or `In Review` after PR under section 7.8.1;
- `done` is terminal.

Default behavioral repair budget is three per stage. Local gate failures are behavioral failures on the same issue; there is no hosted-check wait/deadline/failed-head counter. Publication transport retries use only section 7.8.1's operation-specific budget. Every accepted transition uses compare-and-swap revision/stage validation.

### 7.8 GitHub publication and exact-SHA local evidence gates

1. Snapshot base SHA and pre-existing worktree state.
2. Reconcile the specialist change manifest with the real diff; reject unexpected paths, unrelated changes, or conflict markers.
3. Run the repository-specific aggregate local command from section 6.4 in the issue worktree before staging as an early feedback check; this does not replace the later clean isolated exact-head gate.
4. Before declaring a final gated head, stage/commit the implementation plus plan, design when required, tasks, audit, and draft `code-review`, `qa`, and `completion` artifacts. Draft artifacts contain planned checks/acceptance mappings and clearly identify that final SHA-bound attestations are pending.
5. Push without force, create/reuse one primary PR to `main`, and persist PR/head/base identity. A refused or ambiguous push/PR operation enters section 7.8.1 before another operation is attempted.
6. Re-read the PR head from GitHub, require it to match the local observed commit, create a fresh contained isolated validation worktree at that exact executable SHA, and run the repository-specific exact-head local matrix from section 6.4 with clean-before/after proof. No hosted check is queried or accepted as authority.
7. Run independent code review and, for SaaS behavior changes, repository-pinned real HTTP/Playwright runtime QA against that exact executable head. Record observed head SHA, isolated physical worktree, commands, behavior evidence, cleanup, and findings in the tracked reports.
8. Before staging final report changes, calculate their worktree delta from the executable head. A deterministic allowlist/content classifier must prove every change is evidence-only: only planned workflow/docs evidence paths, no source/config/dependency/build/runtime/test fixture/schema/migration/command changes, and no generated executable effect. Ambiguity is executable. Only after proof may the adapter stage those exact evidence files, create an issue-prefixed evidence commit, push without force, and record the new head.
9. For that proven evidence-only final head, re-read the PR head, create another fresh isolated validation worktree at the exact observed SHA, rerun the section 6.4 local aggregate/docs gate with clean-before/after proof, and obtain a final exact-head code-review attestation covering both the original executable diff and evidence-only delta. Runtime QA either reruns on the final head or the QA attestation explicitly reuses prior runtime evidence, names both observed SHAs, and proves the evidence-only delta cannot affect behavior.
10. Any executable or ambiguous delta invalidates every affected gate and reruns local validation, the clean exact-head aggregate, independent code review, runtime QA, docs, and evidence finalization as applicable. Repeated evidence finalization must converge; a non-converging head fails closed.
11. Store the final PR/head/base, exact-head local-gate attestation, final code-review attestation, runtime-QA run/reuse attestation, docs identity, and later merge/post-merge identity in authoritative supervisor state and concise Linear evidence without committing another branch change. Tracked completion evidence points to this durable final record and does not claim a future merge result.
12. Immediately before merge, re-read Linear authorization, reservation/lease, stop labels, decision state, PR/head/base, mergeability, and final review/QA/docs/exact-head local attestations; independently verify every attestation SHA equals the current PR head.
13. If `origin/main` advanced, merge it into the issue branch without rebase/force and rerun invalidated local, QA, review, evidence, and clean exact-head gates.
14. Squash-merge through GitHub. A refused or ambiguous merge enters section 7.8.1 and never reaches `post_merge`; otherwise verify the returned merge SHA against GitHub readback, then create a new clean isolated worktree at that exact merge commit and run the repository-specific merge-SHA local gate from section 6.4.
15. Persist merge/post-merge identities in authoritative state and Linear, release the reservation only after reconciliation, and move Linear to `Done`. No post-merge repository mutation or follow-up “completion commit” is required or allowed.

If post-merge validation fails, keep the original issue in `In Review`, record the exact failing merge SHA, and create `codex/SAAS-N-repair-<attempt>` from current `main`. Rerun every gate for at most three repair attempts. Never auto-revert. Exhaustion or an unsafe/ambiguous remedy becomes `Backlog + needs-human` with ordered repair evidence and ntfy notification.

#### 7.8.1 Provider-enforced publication refusal

This reusable contract applies whether or not either current repository has branch protection, a ruleset, required checks, or a merge queue. Phase 1 never queries hosted-check status. It classifies only the redacted response/transport result from the requested push, PR, or merge operation plus idempotent readback of remote ref, PR/head/base, merge state, and the operation journal.

1. A refusal is demonstrably transient only when the provider/transport explicitly identifies a retryable condition such as `429` with bounded `Retry-After`, `5xx`/unavailable service, or temporary mergeability calculation, and readback proves the requested mutation did not already succeed. Preserve the current ordinary state (`In Progress` before a PR exists; `In Review` after a PR exists), keep `autonomous`, repository reservation, branch, PR when present, and persistent worktree, release only the run lease, and record the redacted response plus idempotent operation identity. Retry at most three times for that exact operation/head across heartbeats, honoring `Retry-After` capped at 30 minutes or otherwise backing off 5, 15, then 30 minutes. Reconcile remote state before every attempt; never duplicate a push, PR, or merge.
2. A stable, exhausted, ambiguous, policy, permission, required-check, branch/ruleset, merge-queue, or unclassified refusal fails closed. Preserve the same ordinary state and `autonomous`, add both `blocked` and `needs-human`, retain the protected reservation/worktree/branch/PR, release only the run lease, and never move to `Done`. Persist the exact redacted provider response, operation/head/PR/local-attestation identities, attempts, and required attended reconciliation. Write one deduplicated Linear operational request and send ntfy. The request uses exact owner-only syntax `RETRY-PUBLICATION <operation-id> <head-sha>` after the user has reconciled the external policy/permission/provider condition. Do not create a speculative child by default.
3. Malformed, stale, duplicate, unauthorized, or pre-reconciliation replies do nothing. One exact new authorized reply is consumed once, re-reads the issue state/labels/authorization, repository reservation and physical worktree, operation journal, branch/PR/head/base/mergeability, all local SHA-bound attestations, and the latest provider response, then performs at most one idempotent push/PR/merge operation. It never queries check status. Success clears `blocked`/`needs-human` and continues from the preserved stage; any unresolved, changed-head, or ambiguous result remains paused and updates the same request rather than creating another operation/request.
4. The adapter never changes GitHub settings, branch protection, rulesets, required checks, permissions, or merge queues; never uses admin/bypass merge; never weakens a control; and never adds/repairs a pipeline as recovery. Any attended external reconciliation is outside the automated operation and must be complete before the exact retry reply.

### 7.9 Decisions and notifications

Linear stores the decision request, authorized reply, and consumed outcome. A decision includes a unique ID, one focused question, offered options/consequences, recommendation, exact reply syntax, and artifact links.

Before ordinary queue selection, the engine scans persisted pending decisions on `Backlog + needs-human + autonomous` and publication requests on preserved `In Progress`/`In Review + autonomous + blocked + needs-human`. Only an exact, new, unconsumed reply by the configured owner resumes the same issue as preferred work. Publication replies additionally obey section 7.8.1 and authorize only one idempotent retry after attended external reconciliation. Malformed, duplicate, stale, or unauthorized replies do nothing.

ntfy is required for unattended actionable alerts: `needs-human`, external blocker, publication-policy/permission/ambiguous/refusal exhaustion, multiple active issues, and worker/preflight failure. Secrets remain environment-only. The alert links to Linear. Empty queues, held leases, manual WIP, demonstrably transient publication attempts still inside budget, and routine stages do not notify. Codex Scheduled provides run visibility but is not the decision source of truth.

### 7.10 Backlog and custom-state migration

Before schedule enablement:

1. Fully paginate every `Backlog`/`Todo` issue carrying `autonomous` and every issue currently in `Ready for Codex`.
2. Include parents, children, blockers, repository contract, local/external classification, and proposed state/label mapping.
3. Remove `autonomous` from parents, broad goals, cross-repository work, incomplete contracts, and deferred external integrations.
4. Split/reuse bounded local leaves idempotently; only complete unattended leaves become `Todo + autonomous`.
5. Map every custom-state issue to an ordinary state and appropriate labels.
6. Preserve unrelated metadata and record authoritative redacted before/after evidence in the machine-stable operation journal plus concise Linear readback. A best-effort redacted diagnostic export may also be written under ignored `.artifacts/harness/operations/`, but it is never required for authority or recovery.
7. Verify zero issues and zero operational references remain for `Ready for Codex`.
8. Only then delete the custom status manually in Linear.
9. Re-run inventories and verify there is no `Backlog + autonomous` residue.

Operations-only migration work creates no fake PR.

### 7.11 Failure and follow-up issue contract

- A transient tool/network failure stays on the original issue and consumes only a bounded transport retry; it does not create ticket noise.
- An implementation, review, local-validation, QA, merge, or post-merge defect is repaired on the original issue within the applicable budget.
- GitHub push/PR/merge refusal follows section 7.8.1. It preserves current WIP/protected work and uses one deduplicated operational request; it does not create a child merely to represent provider enforcement.
- When progress is impossible because of a separately actionable external prerequisite, deduplicate against existing work, create one linked child issue with its own observable outcome and acceptance criteria, move the original issue to `Backlog + blocked`, attach the attempted-work evidence, release Linear WIP, reconcile/release the repository reservation only when protected work is durably recoverable, and notify through Linear plus ntfy.
- When the missing input is a product/security/cost decision rather than independently executable work, do not create a speculative implementation ticket. Use `Backlog + needs-human` and the structured decision contract.
- When the original goal is oversized or incomplete, use `Backlog + needs-refinement` and propose bounded leaf issues; never create generic “investigate” or “fix tests” work without an achievable completion condition.
- Repeated non-progress records commands, errors, attempted remedies, current artifact/branch/PR identities, and the recommended next action before pausing.
- Follow-up creation is a deterministic, read-before-write/read-after-write Linear adapter operation with an idempotency key. Specialist prose can propose a follow-up but cannot create one directly.
- Semi-autonomous work that reaches the same condition preserves its artifacts and asks the user before creating or linking external tracking. Manual work reports the blocker in the current stage and waits for an explicit tracking/task instruction.

## 8. Data Model and Storage

### 8.1 Tracked workflow metadata

Each work folder's `workflow.json` tracks navigation and handoff metadata:

- schema version;
- immutable workflow UUID;
- stable local work key;
- optional external issue provider/ID;
- selected workflow policy;
- repository key;
- exact physical worktree fingerprint at last authorized write;
- goal and artifact folder;
- artifact inventory and latest completed artifact stage;
- declared completion boundary;
- assumptions/decisions references;
- design required/not-required reason;
- current non-authoritative delivery summary.

This file is tracked with the workflow artifacts and contains no secrets, lease, capability nonce, or authority proof.

Creation/update is performed only by `workflow-init` or its deterministic attach and workflow-managed Handoff subcommands. The helper schema-validates keys/slugs/containment, atomically writes with expected revision, updates the machine registry, reads both back, and rolls back/quarantines partial state on mismatch. The registry is authoritative for lookup and maps immutable workflow ID, work key, optional unique external ID, exact artifact path, repository identity, and physical worktree fingerprint; it never grants Git or external-mutation authority.

### 8.2 Authoritative machine-local supervisor state

```text
%LOCALAPPDATA%/Luchdom/ai-delivery/<repo-id>/
  repository.json
  supervisor-state.json
  reservations.json
  registry.json
  runs/<run-id>/
    request.json
    events.jsonl
    result.json
    validation.md
    stdout.log
    stderr.log
  operations/<operation-id>/
  handoffs/<workflow-id>/<handoff-id>/
  worktrees/<issue-id>/
  validation-worktrees/<operation-id>/
```

`LUCHDOM_DELIVERY_STATE_HOME` may replace the base only when it resolves to an approved absolute machine-stable directory outside every checkout; `<repo-id>` is still derived and appended/verified by the `SAAS-45` base module. Runtime state includes normalized Git/repository identity, base-module/config/state schema versions, run lease/capability, repository reservations, registry mappings, issue/workflow UUID/ID, state revision/stage, external observations, pending decisions/publication requests, persistent issue worktree, isolated gate-worktree identities, primary/repair PR and merge history, gate-bound SHAs, final local-validation/review/QA/reuse attestations, publication operation/refusal/retry identities, attempt/backoff counters, operation journal, heartbeat/result, workflow-managed handoffs, and notification state. It contains no hosted-check timer/history or queried check result in phase 1.

State is atomic, redacted, outside Git, retention-bounded by the engine, and always reconciled against physical worktrees and external state before resume. Engine cleanup occurs only after terminal reconciliation and the safety conditions in section 7.2. Scheduled-worktree archive/cleanup cannot remove it.

### 8.3 Optional repository diagnostic export

Repositories may ignore `.artifacts/harness/operations/` and receive a best-effort redacted export for local debugging. This directory contains no live lease, reservation, registry, capability, authoritative journal, or sole copy of recovery evidence. Its absence, divergence between linked worktrees, or cleanup has no control-plane effect. Manual operational work can link a concise export to Linear only after redaction/readback.

### 8.4 Shared/project configuration and permission boundary

The versioned `SAAS-45` base local-work package solely owns the work-descriptor schema, normalized repository identity, stable state-home derivation, allocation mutex, workflow registry, exact physical-worktree binding, Windows-safe atomic allocation/resume/attach, and registry-only workflow-managed Handoff. `SAAS-46` and later autonomous modules import these exact canonical module paths and schema versions; build validation rejects copied identity/state-home/mutex/registry implementations.

The `SAAS-46` autonomous supervisor layer adds supervisor/checkpoint/config schemas, state transitions, lease/capability, editing reservations, persistent issue/gate worktrees, operation journal, permission preflight, status, recovery/cleanup, and assembled reservation-aware workflow-managed Handoff. Later engine layers add Linear transport/selection/decisions, Git/GitHub PR/merge and provider-refusal handling, ntfy, retry, redaction, logs, health, fixtures, and exact-SHA local-gate orchestration. Neither project wrappers nor later engine tasks reimplement the base primitives.

SaaS configuration owns only:

- `repositoryKey: saas` and base `main`;
- team/project/state/label names or stable IDs;
- branch templates and artifact/docs paths;
- fixed aggregate local-validation and runtime-QA commands;
- allowed writable roots, fixed wrapper/Git/`gh` command shapes, network hosts, Git remotes, and exact loopback QA targets;
- GitHub repository/PR/merge identity only; no required hosted workflow/check identity;
- local-first flags;
- environment-variable names, never values;
- engine/config version compatibility.

No project command is built from Linear issue text. The SaaS wrapper fails closed when the installed engine is missing or incompatible; it never downloads or copies a fallback at runtime.

Canonical policy ownership is also enforced at this boundary: `src/skills/goal-to-delivery/references/` owns the cross-tool contract; repo `AGENTS.md`/docs own repo-specific commands and stricter constraints. Every generated `dist` and installed Codex/Claude/Copilot/Cursor projection records the canonical contract version/hash and resolved references. Build/sync rejects missing parity, broken references, a competing normative policy copy, or a template that restores the retired ownership doctrine.

## 9. Implementation Plan

### Phase 0: Re-audit and re-task without duplicating Linear work

1. Repeat the independent audit of this in-place revision against the user requirements, repo sources, v1 safeguards, current Codex behavior, and the section 0.1 resolution ledger.
2. Resolve any remaining material finding in this file while preserving the audit and historical v1 artifacts; repeat until PASS.
3. Create a new revised task document for the three-workflow architecture and mark the prior task document historical/provisional without editing it.
4. Independently audit the revised plan and revised tasks together.
5. After that audit passes, update existing Linear `SAAS-44` through `SAAS-55` descriptions/titles/dependencies in place. Preserve parentage, stable IDs, Backlog state, and absence of `autonomous`; create a new child only if the audited task graph proves an existing issue cannot safely absorb a distinct goal.
6. Wait for explicit `Implement` approval before any code, sync/install, workflow migration, pilot, or schedule action.

### Phase 1: Shared entry skills and specialist doctrine (`ai-config`)

1. Add user-facing `goal-to-delivery`, `spec-driven-delivery`, and `linear-delivery-loop` skills.
2. Intentionally migrate canonical cross-tool ownership to the delivery-stage, artifact, clarification, quality-gate, completion-boundary, and work-descriptor references under `goal-to-delivery`; remove the conflicting “portable summaries” doctrine.
3. Implement explicit policy composition so manual and autonomous entry skills reuse the references without inheriting semi-autonomous advancement/authority.
4. Convert `feature-driver` to a short deprecated compatibility router to `$goal-to-delivery`; remove duplicate policy and any autonomous route.
5. Add `code-reviewer`; strengthen `qa` and `$qa-verification` into real acceptance verification with localhost/Development isolation, unique resources, disposable data, bounded readiness, production-secret rejection, and cleanup evidence.
6. Add reusable `$docs-as-code`; keep `$luchdom-docs` as the Luchdom source-of-truth routing layer rather than a permanent separate docs agent.
7. Add the sole versioned base local-work package: normalized repository identity, stable state-home derivation, per-repo allocation mutex, workflow registry, exact physical-worktree binding, and deterministic `workflow-init` allocation/resume/attach/registry-only workflow-managed Handoff. Enforce the Windows-safe work-key/slug/containment/reparse contract and historical fallback.
8. Update planner, tasker, auditor, multi-agent delivery, task-audit breakdown, QA, every Codex/Claude/Copilot/Cursor project template, canonical docs, and artifact references atomically for the new modes/layout, ownership precedence, and historical fallback.
9. Make the default project-template workflow manual spec-driven. Document explicit semi-autonomous and autonomous entries.
10. Introduce `python .\scripts\validate.py` as the authoritative `ai-config` local aggregate gate and include every applicable phase-1 shared test available in this first PR; later `ai-config` tasks extend the same manifest rather than introducing another gate.

### Phase 2: Deterministic autonomous engine (`ai-config`)

1. Import and version-check the exact `SAAS-45` base identity/state-home/mutex/registry/workflow modules; add only autonomous config, prepared-iteration, checkpoint, supervisor-state, reservation, and operation-journal schemas.
2. Implement persistent issue/gate-worktree mapping, durable lease/capability, active editing reservations, atomic supervisor state, compare-and-swap transitions, replay-safe operations, status, recovery, safe terminal retention/cleanup, and assembled reservation-aware workflow-managed Handoff. Do not reimplement identity, state-home derivation, allocation mutex, workflow registry, or base transfer.
3. Implement mutation-free permission preflight, minimal child environment, allowlisted network/loopback targets, fixed wrapper/Git/`gh` rules, and actionable redacted failure evidence.
4. Implement direct Linear GraphQL preflight, pagination, errors/rate limits, stable selection, combined repository-reservation/Linear-WIP claim/resume, issue contracts, decisions, follow-ups, and migration dry-run.
5. Implement ntfy delivery and complete secret redaction.
6. Implement worktree/manifest containment, fixed local gate/QA commands, Git/PR/merge, base drift, draft/final evidence sequencing, clean-isolated exact-SHA local attestations, evidence-only reuse classification, provider push/merge refusal classification and attended retry, and bounded post-merge repair. Add no hosted-check discovery/query/polling/budget logic and no settings/bypass capability.
7. Add dependency-free fixture adapters and comprehensive contract tests. The engine never launches nested Codex.

### Phase 3: Build, sync, and shared documentation (`ai-config`)

1. Extend `scripts/build.py` to validate unique names, skill references, canonical shared-reference integrity/ownership, mode policies, schemas, engine modules, prompt restrictions, and compatibility routing.
2. Add semantic tests proving the three entry behaviors and authority boundaries.
3. Extend sync tests to temporary homes/projects and verify source-to-`dist`-to-installed contract version/hash/reference parity for Codex, Claude, Copilot, and Cursor; reject duplicate competing normative policy.
4. Extend the existing `python .\scripts\validate.py` aggregate manifest with all completed engine/build/sync tests. Do not create hosted `ai-config` CI in this program.
5. Update `README.md`, root `AGENTS.md`, canonical docs, and every tool project template with the three workflows, normative precedence, and shared-engine/project-config boundary; docs remain searchable explanations/links, not a second protocol copy.
6. Build and sync only after the relevant code PR is merged and the user authorizes installation; verify installed files exist.

### Phase 4: SaaS local quality and workflow documentation

1. Preserve `pwsh ./scripts/validate-all.ps1` as the authoritative SaaS local aggregate and keep hosted `.github/workflows/validate.yml` non-authoritative/out of scope; do not add or repair a pipeline in phase 1.
2. Pin repository-owned Playwright and add safe real HTTP/browser acceptance paths with isolated disposable resources to the local gate surface.
3. Update `AGENTS.md`, `README.md`, and workflow/Linear/decisions/quality/tooling docs for Autonomous, Semi-autonomous, and Manual Spec-driven Delivery, including the distinction between non-authoritative hosted-check status and provider-enforced publication refusal/recovery.
4. Remove operational `Ready for Codex`, Slack, Telegram, current `LUC-*`, and old two-mode guidance while preserving clearly marked history.
5. Add `docs/AUTOMATION.md`, MkDocs navigation/search, exact MkDocs pin, docs templates, and drift checks.
6. Document local goals, optional Linear attachment, completion boundaries, and how manual stage invocation affects tracking.

### Phase 5: SaaS thin adapter

1. Add versioned project config with identifiers, ordinary states/labels, branch templates, artifact/docs paths, repository key, state-home policy, writable roots, fixed wrapper/Git/`gh` commands, network/remote/loopback allowlists, exact local aggregate/QA hooks, local-first policy, and environment-variable names only. It carries no required hosted-check identity.
2. Add a thin PowerShell wrapper that resolves the installed engine, validates versions, forwards structured file arguments, and contains no generic control-plane logic.
3. Add SaaS fixtures and assembled project-boundary contract tests, including propagation of the shared push/merge refusal states without any check query, settings mutation, or bypass.
4. Add the versioned Codex Scheduled prompt that explicitly invokes `$linear-delivery-loop` and processes at most one issue while continuing routine stages.
5. Add kill switch, pause/archive/removal, stable-home status/recovery, permission preflight, minimal environment, and disabled-by-default setup.

### Phase 6: Linear migration and attended pilot

1. Create/verify exception labels without duplication.
2. Run fully paginated mutation-free inventories for autonomous Backlog/Todo and every `Ready for Codex` issue.
3. Review and apply the idempotent migration; verify zero custom-state and Backlog-autonomous residue; delete the status manually only after proof.
4. Configure private authenticated ntfy environment values, verify connectivity/redaction, and prove one attended test publish before unattended use.
5. Before live publication, pass the complete fixture-only provider-refusal suite and one attended exact `RETRY-PUBLICATION` recovery simulation without changing repository settings or querying checks.
6. Select one safe bounded local-first SaaS leaf and run an attended end-to-end pilot from the dedicated Codex task.
7. Exercise a structured decision round trip, global WIP/no-op behavior, one PR, clean isolated exact-head local gate, code review, real runtime QA, squash merge, and clean exact-merge-SHA local validation. If the real provider refuses publication, use section 7.8.1 rather than weakening controls or expanding scope.

### Phase 7: Scheduled rollout and product sequencing

1. From the same dedicated SaaS Codex task, create one five-minute recurring task using the merged prompt.
2. Verify ephemeral Worktree mode, stable supervisor home, configured `workspace-write`/`never` profile, minimal environment, writable-root/command/network/loopback allowlists, explicit skill invocation, app/computer prerequisites, Scheduled inbox, lease/reservation no-op, manual-WIP no-op, publication-pause no-op without an authorized retry, kill switch, scheduled-worktree cleanup survival, and missed-heartbeat recovery.
3. Observe the first several runs before broadening eligibility.
4. Refine backlog order: authentication, tenant isolation, organizations/users, roles/permissions, primary features, billing domain/plans/entitlements/local fake or sandbox adapters; then deterministic local setup/tests/docs; only then live billing providers, hosted CI/CD, PostHog, AWS, production secrets, monitoring, and deployment infrastructure.

## 10. Testing Strategy

### 10.1 Three-workflow semantic tests

- Exactly three user-facing entry skills exist with unambiguous descriptions and explicit invocation examples.
- `$goal-to-delivery` defaults to local source and `working-tree`, selects no queue work, and cannot accept user-forged autonomous mode.
- `$goal-to-delivery` automatically advances applicable stages, records safe assumptions, and asks only for material ambiguity.
- `$spec-driven-delivery` performs only the requested stage and never triggers the next stage.
- Manual `Clarify` never silently resolves a material question and asks for plan confirmation when no ambiguity remains.
- Manual `Implement` cannot imply QA, commit, PR, or merge.
- Local work skips Linear preflight/mutations and Linear WIP while still honoring repo validation and same-repository reservations; a different-repository reservation does not block SaaS.
- Two simultaneous local initializations allocate distinct allocator-generated keys/folders/UUIDs atomically, including identical goal text; collisions/partial writes retry or quarantine without interleaving evidence, and no model-controlled work key is accepted.
- Resume accepts only registered workflow ID, exact path, or unique external ID and compatible physical worktree; fuzzy chat/latest-goal inference is rejected.
- Work-key/slug validation covers one provider-observed `SAAS-123` key versus one allocator-generated `001` key, 1/48/49-character slugs, separators, dot segments, controls, Windows-invalid characters, trailing dot/space, every reserved device-name family, case-insensitive collisions, traversal, containment, and symlink/junction/mount/reparse escapes.
- Cross-worktree resume with uncommitted work fails closed; explicit workflow-managed Handoff proves clean/non-overlapping destination, preserves a redacted patch/manifest, updates registry atomically, and performs no implicit Git mutation. `SAAS-45` proves registry-only transfer and never claims live-reservation acceptance.
- Native Codex **Hand off** without the custom helper produces a deterministic physical-worktree mismatch, rejects writes/checkpoints, and directs recovery; `SAAS-46` separately proves assembled live-reservation transfer and rejection of all later source writes.
- Attaching a local workflow to Linear updates metadata/registry atomically without duplicate external mapping or artifact rename; history-path fallback remains readable.
- Linked semi/manual entry reconciles autonomous lease and removes autonomous ownership before Plan; Plan/Clarify/Task/Audit state, Implement-to-In-Progress, PR-to-In-Review, Done, Release, workflow-managed Handoff, and abandon transitions match section 6.2.
- Semi-autonomous local SaaS work reserves before automatic repository edits; manual local SaaS work reserves at `Implement`, before any other repository-deliverable mutation, or through explicit `Reserve`; an autonomous preflight racing either cannot claim.
- Reservation expiry with dirty/unmerged/open-PR/inaccessible state fails closed, clean planning-only staleness reconciles safely, and time alone never releases protected work.
- Completion boundaries grant only their documented Git scope.
- `feature-driver` routes only to `$goal-to-delivery` and contains no copied policy.
- All three modes reuse the same specialist agents and shared references.
- Project templates default to manual spec-driven delivery and document explicit alternatives.

### 10.2 Artifact, docs, build, and sync tests

- New local and issue-linked artifact folders use the stable work-key layout and dated filenames.
- Folder allocation is Windows-safe, case-insensitive, strict-descendant-contained beneath the resolved `docs-ai` root, and refuses every symlink/junction/mount/reparse escape before and after create-new readback.
- Every artifact producer/consumer recognizes the new layout and historical fallback.
- `workflow.json` validates, contains immutable workflow ID and physical-worktree fingerprint but no secrets/authority, and preserves later issue attachment.
- Build rejects missing/duplicated shared references, competing normative policy, retired ownership language, precedence drift, and unresolved skill/agent routing.
- Temporary sync tests verify Codex/Claude/Copilot outputs and Cursor project routing without touching real user homes.
- Canonical source, generated `dist`, and every installed contract/engine/schema version, hash, and reference graph match; tampering or partial sync fails.
- Docs drift rejects operational `Ready for Codex`, Slack, Telegram, and current `LUC-*` examples while permitting marked history.
- `requirements-docs.txt` pins `mkdocs==1.6.1`; MkDocs strict build/search/navigation pass.

### 10.3 Autonomous contract tests

Retain all v1 autonomous test coverage, including:

- missing/invalid/wrong-workspace `LINEAR_API_KEY` fails before mutation and never leaks;
- GraphQL HTTP/errors/pagination/rate limits/retries and idempotent mutation reconciliation;
- empty queue, manual WIP, autonomous resume, multiple-WIP fail-close, candidate filtering/order, and contract rejection;
- pending-decision reconciliation before selection and exact authorized one-time reply consumption;
- concurrent/expired/ambiguous leases, interruptions, state revisions, replay, crash-boundary recovery, and one-issue-per-heartbeat;
- two separate scheduled control worktrees derive one repository ID/state home/mutex, resume one persistent issue worktree, and cannot duplicate a Linear/GitHub operation;
- cleanup/archive of either scheduled worktree preserves lease/reservation/journal/registry/issue worktree; engine terminal cleanup refuses dirty/live/ambiguous state and status/recovery is identical from any linked worktree;
- repository-reservation races between manual planning, local SaaS implementation, autonomous preflight, and claim; explicit Release/workflow-managed Handoff; stale clean versus dirty work; and local work in a different repository;
- state-home override/default derivation, relative/checkout/alias/collision/inaccessible roots, sentinel/mutex/worktree-root denial, and fail-closed no-relative fallback;
- scheduled `workspace-write` plus `approval_policy=never` succeeds only with exact writable roots, installed-engine access, fixed wrapper/Git/`gh` rules, protected `.git` commit/worktree capability, and network/loopback allowlists;
- default-denied Linear/GitHub/Git-remote/ntfy network, blocked redirect/host, denied shared-state write, inaccessible engine, blocked exact loopback bind/request, missing secrets, and unrelated provider-secret inheritance all fail before claim without leakage;
- approved least-privilege permission profile passes every mutation-free preflight probe; attended setup separately proves ntfy publishing;
- stop-label/authorization/head changes preventing the next mutation;
- worktree containment, unexpected diff rejection, no force/direct-main/revert, and specialist mutation prohibition;
- exact repository/PR/head/base/local-gate-worktree/merge identity, clean-before/after evidence, aggregate-command failure, SHA mismatch, and base drift;
- draft tracked evidence committed before the final gated head; review/runtime-QA bind to executable SHA; deterministic evidence-only diff classification versus executable/ambiguous delta;
- evidence-only delta reruns docs and the clean isolated exact-final-head local aggregate, obtains final-head code-review attestation, and records either rerun QA or explicit safe reuse across named SHAs; executable delta invalidates/reruns all affected gates;
- final attestations, merge SHA, and post-merge identity persist in authoritative state/Linear without another branch or post-merge repository mutation;
- squash merge, exact returned merge SHA, same-issue repair PRs from current `main`, max three, and no auto-revert;
- `SAAS-48` provider fixtures separately cover push and merge refusals for pending/failing required-check enforcement, branch protection/rulesets, required merge queue, permission denial, `429`, `5xx`/unavailable provider, and ambiguous responses; no fixture asserts that these controls currently exist in either repository;
- provider-refusal fixtures prove transient bounded backoff versus stable/exhausted/ambiguous pause, `In Progress` before PR versus `In Review` after PR, preservation of `autonomous`/WIP/reservation/worktree/branch/PR, run-lease-only release, redacted/idempotent journal/Linear/ntfy evidence, no speculative child, no settings/bypass/check query, and no duplicate push/PR/merge;
- exact `RETRY-PUBLICATION <operation-id> <head-sha>` tests reject unauthorized/stale/duplicate replies, perform at most one reconciled operation for a new authorized reply, keep unresolved refusal paused, and prove successful attended resume clears stop labels and continues from the preserved stage;
- ntfy required in unattended mode, idempotent delivery, quiet routine/no-work behavior, and Linear durability;
- deterministic backlog/custom-state migration without duplicate splits or label loss;
- transient failures staying on the original issue, independently actionable blockers creating at most one achievable linked child, and product decisions creating no speculative implementation ticket;
- shared engine/project wrapper version and ownership boundary.
- no phase-1 code path discovers, queries, polls, waits for, budgets, or accepts a hosted check as quality evidence/authorization; a provider-enforced publication refusal follows section 7.8.1 and never triggers bypass or settings mutation.

### 10.4 SaaS behavior and repository gates

- `pwsh ./scripts/check-doc-drift.ps1`
- `pwsh ./scripts/validate-all.ps1`
- `mkdocs build --strict` in a repo-managed environment
- repository-pinned Playwright acceptance tests
- real localhost/Development API requests verifying response, persistence, auth, and tenant boundaries where relevant
- browser flows verifying visible outcome, keyboard/focus behavior, and obvious accessibility failures where relevant
- unique ports/resources, disposable data, bounded readiness, production-secret rejection, and cleanup proof
- configured loopback targets only, with broad LAN binding denied and cleanup verified
- live Linear only through read-only/permission dry run before the attended pilot
- one attended autonomous pilot and then observed scheduled no-op/resume/terminal cases
- two scheduled worktree runs plus control-worktree cleanup and crash/resume prove the stable supervisor topology before unattended rollout
- exact SaaS PR head and exact merge SHA each run the required local matrix from clean isolated worktrees; the PR head also runs applicable real HTTP/Playwright QA
- assembled SaaS fixtures propagate both push- and merge-refusal states, preserve protected work/WIP, and resume only through the exact attended retry contract without querying checks or changing GitHub settings

## 11. Observability and Debuggability

- Generate a unique run ID for every autonomous claim/resume and immutable workflow ID plus stable work key for every local workflow.
- Emit authoritative redacted JSONL events under the machine-stable state home for permission preflight, allocation/resume/workflow-managed Handoff, reservation, selection, claim, stage, checkpoint, validation, publication request/refusal/retry, mutation, notification, and cleanup.
- Record durations, exit codes, attempts/backoff, workflow/issue/work key, normalized repository ID, stage, persistent and physical worktree fingerprints, branch/PR, exact SHAs, evidence/reuse attestations, redacted provider response/operation identity, reservation state, and final boundary/outcome.
- Provide `Status` and recovery commands that derive the same state root from any linked worktree and show active lease/run/reservation, registry mapping, issue/stage, last heartbeat, retry, pending decision/publication request/notification, protected dirty/branch/PR state, and last result.
- Provide mutation-free dry-run reports with complete candidate/rejection reasons and migration proposals.
- Keep concise Linear comments only for claim, decision/blocker, review handoff, and completion.
- Keep semi/manual local progress in artifacts; do not create an external notification dependency for local work.
- Include workflow ID, exact registry path, `workflow.json`, and completion records in handoffs so a later task can resume explicitly without chat inference; uncommitted cross-worktree work still requires workflow-managed Handoff. Native Codex **Hand off** alone records no workflow authority transfer and follows mismatch recovery.
- Bound authoritative runtime-log and persistent-worktree retention only after terminal reconciliation; optional ignored repository diagnostics can be cleaned independently and never affect recovery.

## 12. Migration from the Existing Plan, Tasks, and Linear Hierarchy

### 12.1 Artifact supersession

- Keep the v1 plan, audit, task breakdown, and passing task audit unchanged.
- Mark this file as the current plan in the next revised task/audit artifacts.
- Do not claim that the v1 PASS applies to the three-workflow revision.
- Do not move or rename the existing workflow folder during this revision.

### 12.2 Existing Linear issue preservation

Preserve the current records:

| Linear | Existing stable role | Revised intent after audit/re-task |
|---|---|---|
| `SAAS-44` | Program parent | Rename/reframe as the three-delivery-workflows program parent |
| `SAAS-45` | Shared doctrine | Sole owner of three entry skills, canonical protocol/precedence, normalized repo identity, stable state-home derivation, allocation mutex, workflow registry, exact worktree binding, Windows-safe local workflow init/attach, registry-only workflow-managed Handoff, specialist boundaries, compatibility routing, and initial `ai-config` aggregate local gate |
| `SAAS-46` | Durable supervisor core | Consume the exact `SAAS-45` base modules; add supervisor state, lease/capability, editing reservations, persistent issue/gate worktrees, operation journal, permission preflight, recovery/cleanup, and assembled reservation-aware workflow-managed Handoff without reimplementing identity/mutex/registry |
| `SAAS-47` | Linear/decisions/ntfy | Retain deterministic tracking, queue, decision, notification scope |
| `SAAS-48` | GitHub publication/local gates/repair | Own deterministic PR/merge publication, exact-SHA local evidence ordering/attestations, push/merge provider-refusal classification, bounded transient retry, stable pause/exact attended resume, and repair; no hosted-check query/integration or settings bypass |
| `SAAS-49` | Build/sync harness | Add three-mode semantic validation and source/dist/installed contract hash/reference parity |
| `SAAS-50` | SaaS local validation/runtime QA | Retain authoritative local aggregate validation and isolated real runtime QA; hosted check status remains outside quality authority while provider publication refusal is allowed to pause safely |
| `SAAS-51` | SaaS docs/wiki | Revise docs from two modes to three and add local-work/completion-boundary plus provider-publication pause/recovery guidance |
| `SAAS-52` | SaaS thin adapter | Retain adapter/config/prompt boundary and add prepared capability, stable-home, least-privilege permission/environment, reservation, persistent-worktree composition, and shared provider-refusal state propagation |
| `SAAS-53` | Linear migration | Retain regular-state/label/custom-status migration |
| `SAAS-54` | Notifications/pilot | Retain attended pilot/decision/ntfy proof |
| `SAAS-55` | Scheduled heartbeat | Retain five-minute Codex task rollout/observation |

Do not mutate these records during planning. After revised task audit passes, update them idempotently in Backlog, preserve parent/child relationships where still valid, adjust blockers to the audited graph, and confirm none carries `autonomous`.

### 12.3 Compatibility transition

- Keep `feature-driver` as a semi-autonomous alias for one generated/synced migration cycle.
- Add deprecation guidance pointing users to `$goal-to-delivery`.
- Never make the alias an autonomous entry.
- Remove it only after repo templates, docs, installed adapters, and tests contain no active dependency.
- Keep old artifact path readers until the historical set no longer needs direct tooling support; do not rewrite historical files.

## 13. Rollout and Rollback

### Rollout

1. Repeat the independent audit of this revised plan and require PASS against the section 0.1 ledger.
2. Revise tasks and re-audit plan/tasks.
3. Update existing Linear program records in place.
4. Obtain explicit implementation approval.
5. Land shared skills/doctrine, engine, and build/sync support in ordered `ai-config` PRs.
6. Build/sync the merged shared version with explicit installation authority.
7. Repair SaaS validation/runtime QA and land the revised docs/wiki.
8. Land the disabled SaaS thin adapter and pass fixture, permission, stable-state-root, reservation, provider-refusal/retry, and read-only dry-run checks.
9. Migrate Linear state/labels/custom status with redacted before/after evidence.
10. Configure ntfy, prove one attended publish, pass the exact attended publication-retry simulation, and pass one attended autonomous issue under the exact least-privilege scheduled profile and repository-specific local-only gate matrix without querying hosted checks or changing GitHub settings.
11. Enable one five-minute Codex task, prove two-run/scheduled-worktree-cleanup recovery, and observe early runs.
12. Expand `Todo + autonomous` only to audited local-first leaves.

### Rollback

- Pause/remove the Codex recurring task and archive its dedicated task.
- Set the repo kill switch and remove `autonomous` from eligible issues.
- Preserve ordinary states, manual/semi workflows, work artifacts, machine-stable supervisor state, reservations, registry, persistent issue worktrees, and runtime evidence until attended reconciliation proves cleanup is safe.
- Preserve any publication-paused issue's current `In Progress`/`In Review` WIP, reservation, branch/PR, worktree, operation/request identity, and redacted provider evidence until attended reconciliation; rollback never retries or weakens the external control implicitly.
- Restore issue classification from the redacted pre-migration export where safe; do not assume a deleted custom status can be recreated automatically.
- Revert source changes through normal reviewed PRs, rebuild from canonical `src`, and sync only after explicit authorization.
- Retain the local workflow path even when Linear/ntfy/GitHub integrations are unavailable.
- Do not manually delete the state home or persistent issue worktrees as rollback. Use engine status/reconcile/cleanup after dirty/unmerged/open-PR and external operations are resolved.

## 14. Risks and Mitigations

- **Mode ambiguity causes the wrong authority policy.** Use three explicit entry skills, stable work descriptors, precedence rules, and semantic tests; labels alone never switch modes.
- **Semi-autonomous mode accidentally becomes unattended queue execution.** Prohibit selection and user-forged autonomous mode; require adapter-prepared capability plus external revalidation for every autonomous mutation.
- **Manual mode silently advances.** Make each invocation stage-scoped, return next-stage options only, and test that success never triggers another stage.
- **Shared references inherit the wrong advancement policy.** Keep stage/artifact/quality contracts separate from caller advancement/authority and validate composition in build tests.
- **Local work becomes second-class or pollutes Linear WIP.** Use `workSource: local`, atomically allocated workflow IDs/keys, no Linear preflight/mutation, no Linear WIP participation, and a separate same-repository reservation before any stage can mutate repository deliverables outside its isolated workflow folder.
- **Concurrent local allocations collide or same-goal chats cross wires.** Serialize allocation under the per-repo mutex, use create-new folder semantics plus immutable UUID/registry mapping, and require explicit exact resume identity rather than fuzzy inference.
- **Uncommitted work is resumed from the wrong Codex worktree.** Bind workflow metadata to the physical worktree, fail closed on cross-context resume, and require explicit validated workflow-managed Handoff with a redacted patch/manifest and no implicit Git mutation. Native Codex **Hand off** alone triggers mismatch recovery and never authority transfer.
- **A model-controlled key or slug escapes/collides on Windows.** Accept only provider-observed or allocator-generated work keys; enforce the bounded lowercase slug grammar, reserved-name/invalid-character rejection, case-insensitive collision scan, strict resolved containment, and symlink/junction/mount/reparse rejection before and after atomic allocation.
- **Later Linear attachment duplicates history.** Keep the original stable folder/workflow ID, atomically enforce one external-ID mapping, update metadata only, and link existing artifacts from the issue.
- **Three workflows triple agent maintenance.** Reuse one specialist pipeline and retire copied feature-driver policy.
- **A vague Linear issue reaches implementation.** Enforce the executable issue contract, leaf/repository/dependency checks, and `needs-refinement` split policy.
- **Interactive and autonomous workers race.** Check both global Linear WIP and the repository-scoped reservation; reserve/remove autonomous ownership before manual Plan, require editing reservation at Implement, and fail closed on dirty/ambiguous staleness.
- **Overlapping scheduled worktrees use separate local state.** Derive one machine-stable supervisor home from normalized Git common-dir identity plus repository key; scheduled worktrees are disposable control surfaces and issue worktrees persist under the state home.
- **Overlapping scheduled runs mutate concurrently.** Use the per-repo mutex plus renewable durable lease/capability and repository reservation; fail closed on ambiguous expiry and never time-release dirty/unmerged work.
- **Unattended sandbox blocks a mid-run Git/network/state operation.** Use the locked least-privilege profile, minimal environment, fixed protected `.git`/wrapper/`gh` rules, exact writable/network/loopback allowlists, and mutation-free preflight before claim; no approval or full-access fallback exists.
- **Conversation or model output forges state/authority.** Treat all control-plane identity as adapter-observed and require state revision, capability, issue, lease, and fresh external authorization at checkpoints.
- **Tracked reports change the head after the behavior they attest.** Commit draft evidence before gates; classify final report deltas deterministically; rerun docs and the clean isolated exact-final-head local aggregate plus final review; rerun QA or record explicit safe evidence-only reuse; store terminal attestations externally without another branch mutation.
- **Autonomous merge lands untested behavior.** Require the repository-specific clean isolated exact-final-head local gate, independent final-head code review, real HTTP/Playwright QA or explicitly proven evidence-only reuse, docs, base-drift handling, squash merge, and clean exact-merge-SHA local validation.
- **Post-merge recovery makes matters worse.** Keep the same issue, use numbered repair PRs, rerun every gate, cap at three, and never auto-revert.
- **Hosted provider status is absent, delayed, or misleading.** Phase 1 never queries or treats hosted CI/check state as quality evidence or authority. The adapter enforces exact-SHA clean local gates and keeps optional hosted-check integration deferred.
- **GitHub physically refuses push or merge.** Classify only operation responses/readback, bound demonstrably transient retries, and otherwise preserve `In Progress`/`In Review`, `autonomous`, WIP, reservation, worktree, branch/PR, and local attestations under `blocked + needs-human`. Resume only from one exact authorized retry after attended reconciliation; never query checks, duplicate operations, mutate settings, use bypass/admin merge, weaken controls, or mark `Done`.
- **Scheduled QA damages developer/production data.** Require loopback/Development assertions, unique resources, disposable data, production-secret rejection, bounded readiness, and cleanup evidence.
- **Secrets leak into evidence.** Environment-only credentials, structured redaction, sentinel tests, no secret command arguments, and fail-closed preflight.
- **Notifications are missed or noisy.** Linear remains durable, ntfy alerts only actionable unattended states, Codex Scheduled shows runs, and routine/no-work paths stay quiet.
- **Canonical policy ownership conflicts across tools/repositories.** Make `goal-to-delivery/references` the intentional shared protocol owner, preserve repo-specific stricter authority, publish explicit precedence in every template, and fail on competing normative copies.
- **Docs and installed skills drift.** Source-first version/hash/reference parity from canonical skill references through `dist` and every installed projection, doc drift checks, pinned tooling, and one local aggregate validation command.
- **Historical evidence becomes misleading.** Preserve it unchanged but mark the new plan as forward source of truth and update only current operational guidance.
- **Existing Linear planning records are duplicated.** Preserve `SAAS-44` through `SAAS-55`, revise in place only after a new passing audit, and require idempotent readback.
- **Workflow artifacts become noisy.** Separate per-work evidence from curated searchable docs and link rather than copy full documents into Linear.

## 15. Open Questions / Locked Decisions

No blocking planning question remains. The following decisions are locked for tasking and independent audit:

1. There are three user-facing workflow skills: `$linear-delivery-loop`, `$goal-to-delivery`, and `$spec-driven-delivery`.
2. Workflows are policy layers over one shared specialist agent set; no per-workflow specialist duplication.
3. `$goal-to-delivery` is the preferred semi-autonomous name because it supports code and non-code delivery; it defaults to local source and `working-tree` completion.
4. `$spec-driven-delivery` performs only explicitly invoked stages; manual clarification never silently resolves material ambiguity.
5. `$linear-delivery-loop` is the only autonomous entry and requires a deterministic prepared capability for one eligible Linear issue.
6. Neither semi-autonomous nor manual work can self-elevate to autonomous mode.
7. Linear is optional for local/semi/manual work and required for autonomous work.
8. Local work bypasses Linear WIP but not same-repository safety: deterministic workflow init atomically assigns immutable workflow ID/key/folder/registry/worktree identity, editing work holds a repository reservation, and later Linear attachment is atomic without recreating/renaming artifacts.
9. New evidence uses `docs-ai/<work-key>-<slug>/` and dated filenames; historical layouts remain untouched and readable.
10. `feature-driver` becomes a temporary semi-autonomous compatibility router, then is removed.
11. As an intentional ownership migration, canonical cross-tool shared delivery references live under `src/skills/goal-to-delivery/references`; repo guidance owns repository-specific and stricter constraints, and precedence is user/system plus repo-specific stricter safety, then entry policy, then shared contract, with unresolved conflict fail-closed.
12. Code review and real runtime QA are distinct required gates for autonomous delivery.
13. Autonomous code always uses one primary PR, squash merge, repository-specific clean isolated exact-head local gates, and clean exact-merge-SHA local validation before `Done`; hosted CI is neither required nor authoritative in phase 1.
14. Post-merge repair stays on the same issue, permits three numbered repair PRs, and never auto-reverts.
15. SaaS has one global tracked Linear WIP slot across `In Progress` and `In Review`, plus one deterministic repository-scoped active-work reservation system covering autonomous and interactive editing; another repository never blocks SaaS.
16. The heartbeat is one five-minute recurring Codex task in Worktree mode, explicitly invoking `$linear-delivery-loop`; its worktree is ephemeral control only, while stable supervisor state and persistent issue worktrees live outside every checkout. No Windows scheduler is used in phase 1.
17. Linear + ntfy + Codex Scheduled are the chosen durable/attention/visibility surfaces; Telegram and Slack are excluded.
18. `LINEAR_API_KEY` and ntfy values remain environment-only and redacted.
19. `Ready for Codex` is fully inventoried/migrated and manually deleted only after zero-count/reference proof.
20. Locally runnable SaaS product capability precedes live providers, PostHog, AWS, hosted deployment, and other external integrations.
21. Reusable engine/policy stays in `ai-config`; SaaS remains a thin project configuration/wrapper.
22. Preserve and later revise existing Linear `SAAS-44` through `SAAS-55`; do not create a replacement hierarchy by default.
23. The existing v1 task audit remains historical; this revision requires a new independent audit and re-task before implementation.
24. No program-level UI design spec is required.
25. The authoritative state root is `%LOCALAPPDATA%\Luchdom\ai-delivery\<repo-id>` or an approved absolute `LUCHDOM_DELIVERY_STATE_HOME` base plus verified repo ID; no relative/check-out fallback is allowed.
26. Repository reservations are not released by expiry alone when dirty/unmerged/open-PR/inaccessible/ambiguous work exists; working-tree/commit code boundaries remain `In Progress` until explicit Release/workflow-managed Handoff/PR/merge/abandon reconciliation.
27. Scheduled delivery uses `workspace-write`, `approval_policy=never`, exact writable roots, minimal shell environment, fixed wrapper/Git/`gh` rules, and allowlisted external/loopback network; no full-access fallback.
28. Mutation-free permission preflight must pass before claim, and attended setup proves ntfy publishing.
29. Draft tracked evidence precedes the final gated head; final SHA-bound attestations live in authoritative state/Linear, and report-only deltas use deterministic evidence-only validation/reuse rules with no post-merge repository mutation.
30. Resume requires exact workflow ID/path/unique external ID and compatible physical worktree; cross-worktree uncommitted work requires explicit validated workflow-managed Handoff. Native Codex **Hand off** alone never updates registry/reservation or transfers authority.
31. `SAAS-45` solely owns normalized repository identity, stable state-home derivation, allocation mutex, registry, exact worktree binding, path-safe allocation/resume/attach, and registry-only workflow-managed Handoff; `SAAS-46` consumes those versioned modules and owns supervisor state, lease/capability, editing reservations, persistent issue/gate worktrees, operation journal, permission preflight, recovery/cleanup, and assembled reservation-aware transfer.
32. Work keys are provider-observed external keys or allocator-generated zero-padded sequences only. Slugs use the bounded Windows-safe grammar and every allocation is case-insensitive, strict-descendant-contained under `docs-ai`, and reparse-point-safe.
33. Phase 1 adds no hosted CI pipeline and requires no hosted check in either repository. `ai-config` uses `python .\scripts\validate.py`; SaaS uses `pwsh ./scripts/validate-all.ps1` plus applicable exact-head real HTTP/Playwright QA; both rerun their aggregate from a fresh worktree at the exact merge SHA.
34. Hosted-check status is never required, queried/polled/waited on, or accepted as quality evidence/authorization in phase 1, but GitHub can physically refuse publication. `SAAS-48` handles push/merge refusal through bounded transient retry or preserved-state `blocked + needs-human` pause and one exact attended idempotent retry; no settings mutation, bypass, duplicate operation, speculative child, or `Done` is allowed.

## 16. Sources Consulted

### Current and historical `ai-config` sources

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\planner.md`
- `C:\dev\luchdom\ai-config\src\agents\tasker.md`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\references\handoff-order.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\references\output-contracts.md`
- `C:\dev\luchdom\ai-config\src\skills\task-audit-breakdown\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\SKILL.md`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-16-dual-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-16-dual-delivery-workflows-audit.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-dual-delivery-workflows-tasks.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-dual-delivery-workflows-task-audit.md`

### SaaS sources carried forward from the audited v1 plan

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
- `C:\dev\luchdom\saas\apps\web\package.json`
- `C:\dev\luchdom\saas\apps\web\package-lock.json`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`

### Official product and integration documentation

- [Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [Codex scheduled tasks and recurring automations](https://learn.chatgpt.com/docs/automations)
- [Codex sandboxing and permissions](https://learn.chatgpt.com/docs/sandboxing)
- [Codex Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
- [Codex `AGENTS.md` project guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- `C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md` (fresh local Codex manual cache consulted 2026-07-17)
- [Linear GraphQL API](https://linear.app/developers/graphql)
- [Linear API pagination](https://linear.app/developers/pagination)
- [Linear API rate limiting](https://linear.app/developers/rate-limiting)
- [Linear notifications](https://linear.app/docs/notifications)
- [ntfy publishing and actions](https://docs.ntfy.sh/publish/)
- [MkDocs configuration and search](https://www.mkdocs.org/user-guide/configuration/#search)
- [MkDocs GitHub Pages deployment](https://www.mkdocs.org/user-guide/deploying-your-docs/#github-pages)
