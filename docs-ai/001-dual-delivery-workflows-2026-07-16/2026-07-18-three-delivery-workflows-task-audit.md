# Three Delivery Workflows — Independent Plan and Task Audit

## Verdict

**FAIL — proceed only after plan/task corrections. Return to Task it out, then repeat this independent audit.**

The revised plan and task graph preserve the user's three-workflow direction and most locked safeguards, but they are not yet safe or execution-ready. Two P1 ownership/gate contradictions and one P2 filesystem-contract gap remain. No user product clarification is required if the recommended corrections below are adopted.

No new Linear child is required. Preserve `SAAS-44` through `SAAS-55`; correct the affected `SAAS-45`/`SAAS-46` scopes and shared delivery gate before updating those records in Linear.

This audit created only this report. It did not implement or revise source, build/sync, install tools, mutate Linear/Git/GitHub, configure or publish ntfy, run a pilot, or create/enable a schedule.

## Findings by severity

### P0 — Critical

None.

### P1 — High

#### P1.1 — The bootstrap contract requires an exact-head CI gate that does not exist in `ai-config` and is simultaneously forbidden by scope

**Evidence**

- The bootstrap exception says every code issue from `SAAS-45` through `SAAS-52` still requires exact-head CI (`2026-07-17-three-delivery-workflows-plan.md:437-439`).
- The same plan explicitly forbids creating hosted `ai-config` CI in this program (`2026-07-17-three-delivery-workflows-plan.md:778-785`, especially `:783`).
- The task breakdown repeats the no-hosted-CI constraint for `DDW-AIC-005` (`2026-07-17-three-delivery-workflows-tasks.md:253-278`, especially `:271`) while its common code-child contract ambiguously requires CI for every code child (`2026-07-17-three-delivery-workflows-tasks.md:456-473`, especially `:470-471`).
- The current `ai-config` repository has no `.github` directory and no tracked GitHub Actions workflow; `Test-Path .github` is false and `git ls-files .github` returns no files. Its current validation surfaces are local `scripts/build.py` and `scripts/test_sync_markers.py` (`C:\dev\luchdom\ai-config\scripts\build.py:118-172`; `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py:32-74`).
- By contrast, SaaS already has the exact named hosted gate: workflow `Validate`, job `validate`, on Ubuntu (`C:\dev\luchdom\saas\.github\workflows\validate.yml:1-9`, `:30-32`).

**Impact**

The five `ai-config` PRs cannot satisfy their universal bootstrap definition of done. An implementer must either violate the exact-head-CI rule or violate the locked no-hosted-`ai-config`-CI rule. This blocks the critical path before the shared engine can be installed.

**Required correction**

Add one explicit repository-specific bootstrap gate matrix to the plan and task document:

- `DDW-AIC-001` through `DDW-AIC-005`: require the complete local aggregate suite, independent review, docs checks, and evidence to be rerun from the exact PR head, followed by the same clean exact-merge-SHA validation. Record an exact-SHA local-validation attestation; do not require a nonexistent hosted check.
- `DDW-SAS-001` through `DDW-SAS-003`: require the exact current PR-head `Validate / validate` GitHub Actions check in addition to local/review/QA gates.
- Keep the locked decision not to add hosted `ai-config` CI.

Update plan section 6.4 and the per-code-child task contract so “CI where applicable” cannot be read as either universal or optional at implementer discretion.

#### P1.2 — `SAAS-45` and `SAAS-46` have circular acceptance and duplicate ownership of repository identity, mutex, and registry primitives

**Evidence**

- The plan assigns functional workflow-init/Handoff to phase 1 and assigns normalized repository identity, stable state home, mutex, and registry again to phase 2 (`2026-07-17-three-delivery-workflows-plan.md:756-776`, especially `:764`, `:770-772`). The Linear mapping similarly gives deterministic workflow-init/Handoff to `SAAS-45` and stable identity/mutex/registry to `SAAS-46` (`2026-07-17-three-delivery-workflows-plan.md:922-928`).
- `DDW-AIC-001` says it will implement repository identity, allocation, registry, attach, and Handoff (`2026-07-17-three-delivery-workflows-tasks.md:120-130`), and its acceptance requires the per-repository mutex, registry, exact worktree identity, and functional Handoff (`:140-144`).
- The same `DDW-AIC-001` acceptance says Handoff composes with a reservation interface supplied by `DDW-AIC-002` (`:143`), even though `DDW-AIC-001` has no dependency and blocks `DDW-AIC-002` (`:152-155`).
- `DDW-AIC-002` then claims repository identity/state home, mutex, registry, reservations, and Handoff integration as its own likely modules and acceptance (`2026-07-17-three-delivery-workflows-tasks.md:157-180`) while depending on `DDW-AIC-001` (`:189`).
- The task-level live-reservation Handoff test correctly belongs to `DDW-AIC-002` (`:181-186`), demonstrating that `DDW-AIC-001` cannot independently satisfy the reservation-aware form of its current acceptance.

**Impact**

The first PR either has to invent duplicate temporary state primitives that the second PR replaces, or it cannot pass its own functional acceptance until its dependent successor exists. That violates the stated independently actionable, one-primary-PR task contract and makes schema/module ownership unsafe for later build/hash parity work.

**Required correction**

Preserve both Linear IDs but assign each primitive exactly once. The least disruptive split is:

- `SAAS-45`: own the three entry policies, canonical protocol, specialist doctrine, and the canonical base modules/contracts required for local workflow-init—repository identity, stable state-home derivation, allocation mutex, workflow registry, exact worktree binding, atomic local allocation/resume/attach, and registry-only Handoff. It must publish the sole module paths and schema versions consumed later.
- `SAAS-46`: consume and extend those base modules with autonomous supervisor state, lease/capability, repository reservations, persistent issue worktrees, operation journal, permission preflight, recovery/cleanup, and the assembled reservation-aware Handoff transition. It owns the successful live-reservation authority-transfer proof and superseded-source rejection.

Remove the duplicated identity/mutex/registry implementation wording from `SAAS-46`, and remove live reservation-aware Handoff from `SAAS-45` acceptance. Alternatively, move all functional workflow-init/Handoff implementation to `SAAS-46` and make `SAAS-45` contract-only, but then revise the plan mapping/dependency explicitly. Do not leave a later task as an unstated prerequisite of an earlier task's acceptance.

### P2 — Medium

#### P2.1 — The work descriptor and artifact allocation contract is not path-safe or unambiguous on Windows

**Evidence**

- The JSON example gives the literal value `"workKey": "SAAS-123|001"` (`2026-07-17-three-delivery-workflows-plan.md:281-301`, especially `:287`). `|` is not valid in a Windows filename.
- Later prose shows that `SAAS-123` and `001` are intended as alternatives and embeds the selected value in an artifact directory (`2026-07-17-three-delivery-workflows-plan.md:308-324`, especially `:316`; `:342-360`, especially `:358`).
- `DDW-AIC-001` assigns the schema and atomic folder allocation but does not require a path-safe grammar for observed work keys or slugs, containment below `docs-ai`, or Windows reserved-name/case/reparse-point handling (`2026-07-17-three-delivery-workflows-tasks.md:124-148`).
- The actual shared and target repositories are being developed on Windows under `C:\dev\luchdom\...`, so this is an active platform constraint rather than a theoretical portability note.

**Impact**

An implementer could treat the example literally, accept model-controlled separators/dot segments in a slug, collide case-insensitively, or allocate outside the intended artifact root. That weakens deterministic initialization and can make the first workflow unusable on the user's machine.

**Required correction**

- Replace the example with one concrete value and document the alternatives separately, such as `"workKey": "SAAS-123"` or `"workKey": "001"`.
- Make the schema/helper enforce provider-observed issue keys or allocator-generated numeric keys; never accept arbitrary model text as a work key.
- Define a bounded, path-safe slug grammar and length, reject separators, dot segments, control/invalid characters, Windows device names, trailing dots/spaces, symlink/junction/reparse escapes, and case-insensitive collisions.
- Resolve and verify the final directory remains beneath the intended `docs-ai` root before create-new allocation.
- Add Windows-focused invalid-character, reserved-name, traversal, case-collision, and containment tests to `DDW-AIC-001`.

### P3 — Low / precision

#### P3.1 — Distinguish workflow-managed `Handoff` from the native Codex **Hand off** action

The plan's deterministic Handoff intentionally transfers a registered patch/manifest and performs no implicit Git action (`2026-07-17-three-delivery-workflows-plan.md:324`). Current Codex documentation uses **Hand off** for a desktop action that moves a chat and code between Local and Worktree through Git operations (`C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md:7574-7578`, `:7628-7640`). Exact-worktree validation will fail closed, but the shared and SaaS docs tasks do not explicitly distinguish these similarly named operations.

Assign this note to `DDW-AIC-001`, `DDW-SAS-001`, and `DDW-SAS-003`: name commands as “workflow-managed Handoff,” state that the native Codex button alone does not update the workflow registry/reservation, and provide deterministic mismatch/recovery instructions. This does not require another Linear issue.

## Requirements and traceability readback

| Requirement / locked decision | Task owner(s) | Audit result |
|---|---|---|
| Three entries: autonomous, semi-autonomous, manual spec-driven | `DDW-AIC-001`, `DDW-AIC-005`, `DDW-SAS-001` | Covered; semantic/no-self-elevation/no-auto-advance criteria are explicit. |
| One shared specialist pipeline, distinct audit/review/QA/docs roles | `DDW-AIC-001`, `DDW-AIC-005` | Covered; no per-mode specialist duplication. |
| Local goal without Linear, later atomic attachment, exact resume | `DDW-AIC-001` | Behavior covered; filesystem grammar/containment needs P2.1. |
| Ordinary states plus labels; no operational `Ready for Codex` | `DDW-AIC-003`, `DDW-SAS-001`, `DDW-OPS-001` | Covered, including zero-count/reference proof before manual status deletion. |
| One global SaaS tracked WIP plus same-repository reservation | `DDW-AIC-002`, `DDW-AIC-003`, `DDW-SAS-003` | Behavior/tests covered; primitive ownership needs P1.2. |
| Stable supervisor home and persistent issue worktrees outside scheduled checkouts | `DDW-AIC-002`, `DDW-SAS-003`, `DDW-OPS-003` | Covered with two-worktree, cleanup, crash/resume, and different-repository tests. |
| Least-privilege unattended Codex configuration | `DDW-AIC-002`, `DDW-SAS-003`, `DDW-OPS-003` | Covered; established sandbox settings and beta named profiles are explicitly not mixed. |
| Linear durable decision record, ntfy attention, Scheduled inbox visibility | `DDW-AIC-003`, `DDW-OPS-002`, `DDW-OPS-003` | Covered; Telegram and Slack excluded; routine/no-work paths quiet. |
| One issue/one repo/one primary PR, squash, exact-SHA completion/repair | `DDW-AIC-004`, assembled adapter/pilot | Exact-SHA evidence ordering and no post-merge repo mutation are covered; bootstrap CI applicability needs P1.1. |
| Real HTTP and Playwright usability/behavior QA | `DDW-SAS-002`, `DDW-SAS-003`, `DDW-OPS-002` | Covered with loopback/Development isolation, unique resources, bounded readiness, and cleanup. |
| Searchable docs/wiki and per-task documentation | `DDW-AIC-001`, `DDW-SAS-001` | Covered through docs-as-code, pinned MkDocs, strict build, navigation/search, and drift rules. |
| Local product capability before AWS/PostHog/hosted providers | `DDW-AIC-003`, `DDW-SAS-001`, `DDW-OPS-001/002/003` | Covered in eligibility, migration, pilot selection, and rollout sequencing. |
| Five-minute Codex Scheduled loop, not Windows Task Scheduler | `DDW-SAS-003`, `DDW-OPS-003` | Covered; current Codex supports recurring local-project worktree tasks and explicit skill invocation. |
| Explicit bootstrap and later implementation/install/mutation gates | Document status, per-code contract, operations dependencies | Covered except for the impossible universal CI clause in P1.1. |
| Preserve historical artifacts and `SAAS-44`–`SAAS-55` | Every mapped task | Covered; no duplicate child is justified. |

## Task-boundary and dependency audit

- The declared dependency graph is acyclic on paper (`2026-07-17-three-delivery-workflows-tasks.md:77-93`).
- The functional acceptance relationship between `DDW-AIC-001` and `DDW-AIC-002` is nevertheless circular/overlapping as described in P1.2.
- Every code-bearing child names one target repository and one primary PR; no task requires a mixed-repository PR (`2026-07-17-three-delivery-workflows-tasks.md:20-27`, `:456-475`).
- Operational children correctly use authoritative external/state-home evidence and forbid fake PRs (`2026-07-17-three-delivery-workflows-tasks.md:368-430`).
- `DDW-AIC-005` correctly separates source/build validation from later explicitly authorized installation, and `DDW-SAS-003` waits for the exact installed shared version (`2026-07-17-three-delivery-workflows-tasks.md:253-278`, `:338-366`).
- After P1.2 is corrected, the existing eleven children remain cohesive enough for one primary PR or one operations outcome each. A new Linear child is not required by this audit.

## Test, risk, migration, and rollout ownership

The earlier re-audit's two P3 notes are now well assigned:

- Permission tests explicitly forbid mixing established sandbox settings with beta named permission profiles and separately validate host policy, loopback targets, commands, roots, environment, and redaction (`2026-07-17-three-delivery-workflows-tasks.md:29-32`, `:177-188`, `:349-361`, `:447-454`). This matches current Codex documentation that the models do not compose (`codex-manual.md:14367-14385`).
- Handoff tests cover both failed transfer and successful superseded-source rejection, including a live reservation (`2026-07-17-three-delivery-workflows-tasks.md:143-148`, `:181-186`, `:447-450`). P1.2 changes only which child owns the assembled proof.

Other ownership checks passed:

- `DDW-AIC-004` owns draft evidence ordering, executable/final SHA distinctions, exact-head review/CI/QA reuse, merge identity, no post-merge mutation, and bounded same-issue repair (`2026-07-17-three-delivery-workflows-tasks.md:222-251`).
- `DDW-SAS-002` owns the current Ubuntu/PowerShell break, local Playwright pin, real HTTP/browser behavior, isolation, and cleanup (`2026-07-17-three-delivery-workflows-tasks.md:282-308`).
- `DDW-SAS-001` owns migration of current two-mode/Slack/custom-state docs plus MkDocs and drift checks (`2026-07-17-three-delivery-workflows-tasks.md:310-336`).
- `DDW-OPS-001/002/003` own state/label migration, attended ntfy/decision/pilot evidence, scheduled rollout observation, and reversible rollback (`2026-07-17-three-delivery-workflows-tasks.md:370-430`).
- State retention, cleanup, recovery, secret redaction, follow-up deduplication, rollback, and observability each have primary and assembled owners in the cross-task matrix (`2026-07-17-three-delivery-workflows-tasks.md:432-454`).

The missing proof obligations are limited to P1.1's repository-specific head-gate definition and P2.1's path-safety tests.

## Repository truth checks

### `ai-config`

- `src/` is canonical and `dist/` is generated (`C:\dev\luchdom\ai-config\AGENTS.md:16-19`); `dist/` is ignored (`C:\dev\luchdom\ai-config\.gitignore:1`). The tasks correctly target `src/` and build/sync tests rather than hand-editing generated output.
- The current project templates still state that skill references are not source of truth (`C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md:4-15`, especially `:6`). The plan/task ownership migration is therefore a real, correctly scoped change rather than current truth.
- `feature-driver` currently owns duplicated one-shot orchestration (`C:\dev\luchdom\ai-config\src\agents\feature-driver.md:10-34`, `:43-54`, `:97-99`); its compatibility-router conversion is correctly assigned.
- Current QA is report-only and discovers repo gates (`C:\dev\luchdom\ai-config\src\agents\qa.md:11-29`; `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md:10-35`), so the planned runtime acceptance strengthening is correctly placed.
- Current build/sync generation covers Codex, Claude, Copilot, and Cursor projections (`C:\dev\luchdom\ai-config\scripts\build.py:118-165`; `C:\dev\luchdom\ai-config\scripts\sync.py:105-197`), making `DDW-AIC-005` feasible after the P1/P2 corrections.
- No current `ai-config` hosted CI exists, confirming P1.1.

### `saas`

- Current repo guidance still has two modes, a `Build it all` autonomous trigger, old flat artifact names, and a `LUC-*` branch example (`C:\dev\luchdom\saas\AGENTS.md:138-227`). These are migration targets owned by `DDW-SAS-001`, not blockers.
- Current docs still require `Ready for Codex` and Slack (`C:\dev\luchdom\saas\docs\LINEAR.md:5-17`; `C:\dev\luchdom\saas\docs\SLACK-APPROVALS.md:1-35`), and current drift checks enforce the old terms (`C:\dev\luchdom\saas\scripts\check-doc-drift.ps1:23-30`). The documentation/migration tasks explicitly replace them.
- The current CI identity already matches `Validate / validate`, but `push` is unrestricted (`C:\dev\luchdom\saas\.github\workflows\validate.yml:1-9`). The task correctly changes it to PR plus main-only push.
- Current `validate-all.ps1` invokes Windows `cmd /c` for web typecheck/build (`C:\dev\luchdom\saas\scripts\validate-all.ps1:44-67`), confirming the Ubuntu repair scope.
- Current web dependencies contain no Playwright package (`C:\dev\luchdom\saas\apps\web\package.json:21-26`), while smoke downloads a floating CLI through `npx --yes --package` (`C:\dev\luchdom\saas\scripts\smoke.ps1:370-410`). The exact repository pin and local Playwright surface are necessary and correctly assigned.

### Current Codex behavior

- Scheduled tasks can run local Git projects in isolated worktrees, require the computer/app/project to remain available, can invoke explicit skills, and expose results in the Scheduled inbox (`C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md:7012-7018`, `:7055-7071`, `:7073-7101`).
- Minute-based recurring chat tasks and creation/update from Codex chats are documented (`codex-manual.md:7103-7117`, `:7119-7145`), so the five-minute Codex Scheduled choice is feasible.
- Scheduled tasks are unattended, use default sandbox settings, and normally use approval policy `never`; workspace-write can use rules for selected commands (`codex-manual.md:7167-7196`).
- The manual confirms that old sandbox settings and beta named permission profiles must not be combined (`codex-manual.md:14367-14385`), matching the task safeguards.

## Linear mapping decision

The task map matches the revised plan's preserved intent for `SAAS-44` through `SAAS-55` (`2026-07-17-three-delivery-workflows-plan.md:918-937`; `2026-07-17-three-delivery-workflows-tasks.md:49-75`). The graph needs scope correction, not another child:

- keep `SAAS-44` as the non-executable parent;
- keep `SAAS-45` through `SAAS-52` as the eight code-bearing children in their assigned repositories;
- keep `SAAS-53` through `SAAS-55` as manual-operational outcomes;
- leave every program-building issue in `Backlog` without `autonomous`;
- do not mutate Linear until the corrected plan/task pair passes another independent audit.

## Gate and next actions

1. Revise the plan and task document for P1.1, P1.2, P2.1, and the P3 naming precision note.
2. Repeat an independent plan-plus-task audit. PASS requires no actionable P0/P1/P2 finding.
3. Only after PASS, update `SAAS-44` through `SAAS-55` in place and verify titles/descriptions/dependencies by readback; do not create duplicates.
4. Obtain the user's later explicit `Implement` approval before code, build/sync installation, Linear workflow migration, Git/GitHub mutation, ntfy configuration/publishing, pilot execution, or schedule enablement.

The preferred corrections are deterministic and do not require a product decision from the user. Implementation is not authorized by this audit.

## Sources consulted (paths)

### User requirement and workflow artifacts

- User requirements and clarifications in the current conversation
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-re-audit.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-tasks.md`

### Audit policy and `ai-config` truth

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\README.md`
- `C:\dev\luchdom\ai-config\.gitignore`
- `C:\dev\luchdom\ai-config\src\agents\auditor.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\SKILL.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\audit-checklist.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\task-template.md`
- `C:\dev\luchdom\ai-config\src\project-templates\codex\AGENTS.md`
- `C:\dev\luchdom\ai-config\src\project-templates\claude\CLAUDE.md`
- `C:\dev\luchdom\ai-config\src\project-templates\copilot\.github\copilot-instructions.md`
- `C:\dev\luchdom\ai-config\src\project-templates\cursor\AGENTS.md`
- `C:\dev\luchdom\ai-config\src\agents\feature-driver.md`
- `C:\dev\luchdom\ai-config\src\agents\qa.md`
- `C:\dev\luchdom\ai-config\src\skills\multi-agent-delivery\SKILL.md`
- `C:\dev\luchdom\ai-config\src\skills\qa-verification\SKILL.md`
- `C:\dev\luchdom\ai-config\scripts\build.py`
- `C:\dev\luchdom\ai-config\scripts\sync.py`
- `C:\dev\luchdom\ai-config\scripts\test_sync_markers.py`

### SaaS repository truth

- `C:\dev\luchdom\saas\AGENTS.md`
- `C:\dev\luchdom\saas\README.md`
- `C:\dev\luchdom\saas\docs\HARNESS.md`
- `C:\dev\luchdom\saas\docs\WORKFLOW.md`
- `C:\dev\luchdom\saas\docs\LINEAR.md`
- `C:\dev\luchdom\saas\docs\DECISIONS.md`
- `C:\dev\luchdom\saas\docs\QUALITY.md`
- `C:\dev\luchdom\saas\docs\AI-TOOLING.md`
- `C:\dev\luchdom\saas\docs\LOCAL-DEVELOPMENT.md`
- `C:\dev\luchdom\saas\docs\SLACK-APPROVALS.md`
- `C:\dev\luchdom\saas\.github\workflows\validate.yml`
- `C:\dev\luchdom\saas\apps\web\package.json`
- `C:\dev\luchdom\saas\scripts\check-doc-drift.ps1`
- `C:\dev\luchdom\saas\scripts\check-tools.ps1`
- `C:\dev\luchdom\saas\scripts\smoke.ps1`
- `C:\dev\luchdom\saas\scripts\test-all.ps1`
- `C:\dev\luchdom\saas\scripts\validate-all.ps1`

### Current Codex documentation

- `C:\Users\lucas\.codex\skills\.system\openai-docs\SKILL.md`
- `C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.md` (helper confirmed current on 2026-07-18)
- `C:\Users\lucas\AppData\Local\Temp\openai-docs-cache\codex-manual.outline.md`
