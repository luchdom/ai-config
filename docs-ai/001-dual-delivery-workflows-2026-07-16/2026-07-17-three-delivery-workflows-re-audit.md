# Three Delivery Workflows Plan — Independent Re-audit

## Verdict

**PASS.** No remaining actionable P0, P1, or P2 finding was identified. The revised plan resolves every blocker from `2026-07-17-three-delivery-workflows-audit.md` with a coherent contract and matching proof obligations.

The plan is ready for a **new revised task breakdown** and then an independent plan-plus-task audit. It is **not ready for implementation**: code, build/sync, Linear mutation, Git/GitHub mutation, pilot execution, and schedule enablement remain gated.

No product UI is changed by this program, so no program-level design spec is required.

## Findings by severity

### P0 — Critical

None.

### P1 — High

None.

### P2 — Medium

None.

### P3 — Low / implementation precision notes

No plan revision is required for these notes, but the revised task breakdown should preserve them explicitly:

1. **Keep the scheduled permission mechanism internally consistent.** The plan locks the established `sandbox_mode = "workspace-write"` path with `sandbox_workspace_write`, `approval_policy = "never"`, and tested exec-policy rules (`three-delivery-workflows-plan.md:107-108`, `:494-516`). Current Codex documentation says beta named permission profiles do not compose with those older sandbox settings (`codex-manual.md:14367-14385`). Implementation tasks should not silently mix the two configuration models. They should also keep network domain enforcement, exact loopback target/port validation, and deterministic wrapper validation as distinct controls; Codex network domain rules are host-oriented (`codex-manual.md:2351-2426`, `:14534-14567`).
2. **Make the successful Handoff postcondition visible in tests.** The plan already makes the registry mapping authoritative, rejects an incompatible physical worktree before writes, records both endpoints, and updates the mapping atomically (`three-delivery-workflows-plan.md:304-306`, `:324`, `:360`, `:695`). The task-level test should explicitly prove that the superseded source worktree cannot continue writing after a successful Handoff, in addition to proving that failure leaves the source authoritative.

These are task-writing precision notes, not unresolved design gaps.

## Resolution readback

| Prior finding | Independent readback | Result |
|---|---|---|
| `P1.1` — worktree-relative lease/state | Scheduled worktrees are now disposable control surfaces. Normalized Git common-dir identity plus repository key derives one machine-stable supervisor home outside every checkout. That home owns mutex, lease, reservations, registry, journal, final attestations, and persistent issue worktrees. Cleanup and recovery are adapter-owned and fail closed on protected or ambiguous work (`three-delivery-workflows-plan.md:100`, `:463-492`, `:697-723`). Two-worktree, cleanup, crash/recovery, and duplicate-mutation tests are explicit (`:863-866`, `:895`). | **Resolved** |
| `P1.2` — manual/local work invisible to autonomous selection | The plan now separates Linear global tracked WIP from a repository-scoped active-work reservation. A selected Linear issue is reconciled and stripped of `autonomous` before Plan; local planning may remain unreserved only inside its atomically unique workflow folder; any implementation or curated docs/config/product mutation requires the same-repository reservation. Expiry alone never discards dirty, unmerged, open-PR, inaccessible, or ambiguous work (`:94-95`, `:123`, `:314-324`, `:328-338`, `:414-425`, `:541-573`). Race, state-transition, staleness, Release/Handoff, and different-repository tests are explicit (`:830-837`, `:865`). | **Resolved** |
| `P1.3` — unattended permission contract absent | The scheduled run now has a concrete least-privilege contract: workspace-write, never-prompt approval, explicit writable roots, constrained network/loopback targets, minimal child environment, fixed deterministic command shapes, no full-access fallback, and a pre-claim preflight. The preflight proves engine/config compatibility, state/mutex/worktree-root access, Git/`gh` capability, read-only Linear/GitHub/ntfy connectivity, loopback behavior, environment minimization, and redaction before any claim or external mutation (`:107-108`, `:494-516`, `:725-743`). Default-denied and approved-profile tests cover the affected boundaries (`:866-869`, `:891-895`). This is compatible with current Scheduled behavior: runs are unattended under default sandbox settings, workspace-write blocks out-of-bound writes/network unless configured, rules can allow specific commands outside the sandbox, and scheduled tasks normally use `approval_policy = "never"` (`codex-manual.md:7069-7071`, `:7167-7196`, `:2491-2507`, `:9981-10115`). | **Resolved** |
| `P2.1` — evidence changes PR head after its gate | The autonomous stage model now commits draft tracked reports before publication, binds review/runtime QA to the executable head, classifies the resulting report delta, commits only a proven evidence-only delta, and reruns docs/local validation/exact-final-head CI plus final-head review. QA either reruns or records a deterministic two-SHA reuse attestation. Final SHA-bound attestations live in authoritative state and Linear, so no further branch or post-merge repository mutation is needed (`three-delivery-workflows-plan.md:592-634`). Evidence ordering, convergence, reuse/invalidation, and merge-identity tests are explicit (`:872-876`). | **Resolved** |
| `P2.2` — conflicting canonical policy ownership | The revision makes the ownership change explicit: `src/skills/goal-to-delivery/references/` owns the reusable cross-tool protocol; repository guidance owns repo-specific commands and stricter constraints; user/system instructions and stricter repo safety take precedence; unresolved conflicts fail closed. Every Codex, Claude, Copilot, and Cursor template/projection must migrate in the same change, carry version/hash/reference identity, and reject competing normative copies or retired doctrine (`:129-142`, `:195-221`, `:364-374`, `:743`, `:756-785`). Build/sync parity and drift tests cover source, generated, temporary-installed, and Cursor project projections (`:843-852`). This intentionally replaces, rather than silently conflicts with, the current project-template sentence in `src/project-templates/codex/AGENTS.md`. | **Resolved** |
| `P2.3` — unsafe local allocation and resume | One deterministic `workflow-init` helper now creates an immutable workflow UUID, serializes per-repository allocation, scans folders/history/registry, uses create-new directory semantics, writes and validates `workflow.json`, registers exact work key/path/worktree identity, retries collisions, and quarantines partial allocation. Resume requires exact registered identity and a compatible physical worktree. Cross-worktree uncommitted work rejects by default; explicit Handoff validates repository/destination/diff, records both endpoints, and atomically changes the registry only after successful application/readback. Later Linear attachment is atomic and does not rename/recreate artifacts (`:277-324`, `:342-362`, `:675-719`). Allocation, exact resume, cross-worktree rejection/Handoff, attachment, and history fallback tests are explicit (`:831-834`, `:845-850`). | **Resolved** |

## New-contradiction checks

The audit also checked the revision independently rather than relying on its resolution ledger:

- **Repository reservation transitions:** planning-only, artifact, working-tree, commit, PR, merge, Release, Handoff, abandon, expiry, and stale/dirty reconciliation now have deterministic state/reservation behavior (`three-delivery-workflows-plan.md:326-338`, `:398-425`).
- **Local non-code edits:** isolated workflow evidence may defer reservation, but curated documentation, configuration, product files, and other repository deliverables require it before mutation (`:320`, `:374`).
- **Persistent topology:** authoritative state is outside Git and every checkout; optional `.artifacts` exports are explicitly non-authoritative (`:463-492`, `:697-723`). This is compatible with Codex worktrees having separate file copies, ignored-file handoff limitations, and managed-worktree cleanup (`codex-manual.md:7561-7658`, `:7691-7731`).
- **Permission feasibility:** the plan acknowledges protected Git operations, fixed wrapper/rule shapes, a disposable preflight fixture, minimal environment, and fail-closed no-approval behavior. It does not depend on an unattended approval prompt (`three-delivery-workflows-plan.md:494-516`).
- **Evidence convergence:** draft/final evidence stages, evidence-only classification, final-head reruns, external final attestations, and non-convergence failure are ordered consistently (`:592-634`).
- **Cursor/cross-tool migration:** Cursor remains project-local, but the plan requires its generated project projection to carry the same canonical protocol identity/precedence and tests it with the other tool outputs (`:87`, `:213-215`, `:743`, `:780-785`, `:848-850`).
- **Atomic Handoff:** exact worktree binding and compare-and-swap registry updates prevent two contexts from becoming authoritative; failed/ambiguous transfer preserves the source mapping (`:304-306`, `:324`, `:360`, `:695`).
- **Historical and Linear migration:** the v1 artifacts remain unchanged; `SAAS-44` through `SAAS-55` are preserved and may be revised only after the new task graph passes its independent audit (`:911-945`).

## Other consistency checks that passed

- The three entries are policy layers over one specialist pipeline; no duplicate per-workflow agent stack is introduced (`three-delivery-workflows-plan.md:39-53`, `:223-243`).
- `$goal-to-delivery` and `$spec-driven-delivery` cannot forge or self-elevate into autonomous authority; only a current adapter-prepared capability enables autonomous checkpoints (`:129-142`, `:267-273`, `:575-590`).
- Manual mode executes one named stage only; `Implement` does not imply review, QA, or Git publication (`:257-265`, `:398-435`).
- Linear is optional outside autonomous delivery, while autonomous selection remains deterministic and uses ordinary states plus labels—never `Ready for Codex` (`:84-106`, `:110-127`, `:541-571`, `:646-660`).
- Autonomous completion retains PR/squash/exact-SHA gates, bounded same-issue repair, and no auto-revert (`:618-636`).
- Linear remains the durable unattended decision record, ntfy remains the actionable attention channel, and Scheduled remains run visibility (`:98-100`, `:638-644`).
- Real HTTP/Playwright QA, isolated resources, cross-platform validation repair, docs-as-code, and locally runnable SaaS capability before external integrations remain in scope (`:613-636`, `:747-895`).
- Implementation phases can be retasked cleanly across shared doctrine/workflow-init, supervisor core, Linear/notifications, GitHub gates, build/sync, SaaS quality/docs, SaaS adapter, migration/pilot, and scheduled rollout (`:745-818`, `:918-937`).

## Gate

Authorized next steps:

1. Create a new three-workflow task breakdown from this revised plan.
2. Preserve the earlier v1 task document and both prior audits unchanged as historical evidence.
3. Independently audit the revised plan and revised task breakdown together.
4. Only after that task audit passes, update `SAAS-44` through `SAAS-55` in place without duplicate program issues.

Not authorized by this re-audit: implementation, build/sync, installation, Linear mutation, Git/GitHub mutation, pilot execution, ntfy configuration/publishing, custom-state migration, or schedule creation/enablement.

## Sources consulted (paths)

### Current and historical `ai-config`

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-audit.md`
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
- `C:\dev\luchdom\ai-config\src\skills\task-audit-breakdown\references\audit-checklist.md`
- `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\luchdom-docs\SKILL.md`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md`
- `C:\dev\luchdom\ai-config\src\project-templates\claude\CLAUDE.md`
- `C:\dev\luchdom\ai-config\src\project-templates\cursor\AGENTS.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py`

### SaaS workflow and quality boundary

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

### Current Codex product behavior

- `C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md` (refreshed 2026-07-17 for this re-audit)
- [Scheduled tasks](https://learn.chatgpt.com/docs/automations)
- [Sandboxing and permissions](https://learn.chatgpt.com/docs/sandboxing)
- [Command rules](https://learn.chatgpt.com/docs/agent-configuration/rules)
- [Permission profiles](https://learn.chatgpt.com/docs/permissions)
- [Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
