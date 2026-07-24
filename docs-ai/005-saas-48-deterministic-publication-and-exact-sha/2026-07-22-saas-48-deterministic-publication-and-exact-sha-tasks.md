# SAAS-48 deterministic publication and exact-SHA gates — Execution Tasks

## Status and authority

- Workflow: `semi-autonomous`; repository: `ai-config`; completion boundary: merge.
- Product design is not required: this is a transport-free engine and operator-contract change with no product UI or interaction.
- This breakdown authorizes neither implementation nor build/sync, Git/GitHub/Linear/ntfy mutation, provider access, or a change to `workflow.json`. The six tasks are ordered implementation slices within **one** `ai-config` primary PR against `main` when implementation is separately authorized; they are not six PRs.
- Publication behavior is fixture-only. The engine must expose injected ports and must not acquire a raw provider client, hosted-check authority, or a live autonomous activation path.

## Audit notes

Light completeness check only; this is not independent audit sign-off.

- The registered plan supplies the material policy decisions: `main` base, squash-only merge, the exact `ai-config` aggregate command, bounded retries, one attended retry, and three same-issue repair attempts. No unresolved UI, product, billing, tenancy, cost, or destructive-data decision was found.
- Implementation depends on usable SAAS-46 supervisor/reservation/journal seams and SAAS-47 control-plane publication-request/reply seams. The independent auditor must verify their actual merged contract versions and reject invented compatibility shims or authority expansion.
- The exact schema/version migration strategy, record field names, module filenames, and test-module filenames remain implementation choices; they must be settled in the first task by extending existing closed schemas and runtime validators together.
- Rollout is deliberately disabled/fixture-only. Rollback is a reviewed code change that preserves journals, reservations, worktrees, and protected publication state; no recovery path may delete state to escape ambiguity.
- The independent auditor must verify all negative authority tests, complete provider-refusal classification, exact-SHA evidence ordering/convergence, replay/crash paths, and post-merge repair bound rather than treating this task document as proof.

## Dependency graph

```text
SAAS-46 + SAAS-47 handoff
  -> SAAS48-01 contracts and durable records
  -> SAAS48-02 Git containment and manifest reconciliation
  -> SAAS48-03 injected GitHub publication/idempotent readback
  -> SAAS48-04 exact-SHA local gates and evidence convergence
  -> SAAS48-05 refusal recovery, merge, and bounded repair
  -> SAAS48-06 engine composition, docs, and aggregate integration
  -> SAAS-49
```

### SAAS48-01 — Define closed publication, attestation, and repair contracts

- Goal: Add versioned, fail-closed runtime/schema records for publication requests/readbacks, operation identity, refusal/retry state, exact-SHA attestations, evidence deltas, merge result, repair state, and preserved control-plane state.
- Target repository: `ai-config`.
- Likely files/modules: `src/skills/linear-delivery-loop/scripts/contracts.py`, `supervisor.py`, `operations.py`, `control_plane_records.py`, `references/{engine-command,operation-journal,supervisor-state}.schema.json`; new publication/evidence record modules under `src/skills/linear-delivery-loop/scripts/`; `tests/linear_delivery_supervisor/test_contracts.py`, `test_operations.py`, `tests/linear_delivery_control_plane/test_records_notifications.py`, and focused new contract tests.
- Acceptance criteria:
  - Records bind normalized repository/workflow/issue, physical-worktree fingerprint, branch, base/head/merge SHA, immutable operation ID/idempotency key, timestamps, redacted provider evidence, and a full preserved-state snapshot: ordinary issue state (`In Progress` before PR / `In Review` after PR), `autonomous`, global WIP, reservation, persistent worktree, branch, optional PR, and evidence references.
  - The retry model persists the initial attempt separately from `retryCount`: the initial operation plus at most three retries, with retry indexes 1/2/3 mapped to 5/15/30 minutes (or capped `Retry-After`), and an explicit exhausted transition after retry count 3.
  - Schemas and `contracts.validate_contract` have strict unknown-field rejection and runtime/schema inventory parity; migration/default fixtures fail closed on unsupported versions or malformed prior state.
  - State and journal transitions cannot represent an unbound operation, raw capability/secret/provider credential, mutable operation identity, or a terminal success without a matching readback/attestation reference.
- Local test and runtime QA notes: Add focused unittest fixtures for schema/runtime parity, version migration, unknown fields, redaction sentinels, immutable replay, preserved-state completeness, and state/journal recovery. Prove initial attempt plus retries 1/2/3, the 5/15/30 indexes, crash/replay without double-advancement, and the first refused operation after exhaustion. Run `python -m unittest discover -s tests -t . -p "test*.py" -v` and `python .\scripts\validate.py`; no live provider calls.
- Documentation impact: Update the nearest engine/reference contract documentation only if it is the source of truth for the new record semantics; defer user-facing publication runbook wording to SAAS48-06.
- Dependencies / blocks: Requires SAAS-46 durable state/journal interfaces and SAAS-47 publication-request record boundary. Blocks all later SAAS-48 tasks.
- Risks and non-goals: Avoid a parallel state store or permissive compatibility decoder. Does not implement Git subprocess execution, provider transport, gate execution, or control-plane mutation.
- Completion/publication boundary: Code complete only after focused and aggregate local tests; it creates no branch, PR, or provider mutation in this task stage.

### SAAS48-02 — Enforce Git containment and specialist-manifest reconciliation

- Goal: Implement injected Git operations that reconcile only the authorized specialist manifest to the actual diff and prepare the scoped publication branch safely.
- Target repository: `ai-config`.
- Likely files/modules: new Git/manifest module(s) under `src/skills/linear-delivery-loop/scripts/`, integration points in `worktrees.py`, `operations.py`, and `supervisor.py`; focused disposable-repository fixtures under `tests/linear_delivery_supervisor/` such as `test_publication_git.py` and support helpers.
- Acceptance criteria:
  - Snapshot base and pre-existing changes; verify the registered physical worktree and normalized repository; reject dirty/unrelated/conflicting/unexpected paths and manifest-to-diff disagreement.
  - After manifest reconciliation and before any staging, run the trusted repository aggregate in the registered issue worktree as an early feedback gate; a failure blocks staging. This check never replaces the later fresh, clean isolated exact-PR-head gate.
  - Create only `codex/SAAS-<N>-<slug>` branches and stage only reconciled scope. Repair naming is reserved for `codex/SAAS-<N>-repair-<attempt>` and must originate from current `main` later in SAAS48-05.
  - Deny direct `main` delivery, force push, rebase, tags/releases, settings/secrets operations, arbitrary shell execution, and auto-revert at the public/runtime surface.
  - Specialist output stays proposal/manifest-only; it cannot independently stage, commit, push, create/update a PR, merge, or mutate Linear.
- Local test and runtime QA notes: Use disposable local repositories/remotes to prove containment, physical-worktree mismatch, dirty-worktree refusal, issue-worktree aggregate-before-staging ordering and failure refusal, scoped staging, branch naming, base drift preparation, prohibited-action denial, and crash/replay safety. Run the focused module plus `python .\scripts\validate.py`.
- Documentation impact: None beyond module-level operator/reference comments unless a canonical Git containment reference exists and requires a source-of-truth update.
- Dependencies / blocks: Depends on SAAS48-01; blocks publication orchestration and exact-head gates.
- Risks and non-goals: Never use the developer worktree as a disposable gate worktree. Does not contact GitHub or decide retries.
- Completion/publication boundary: Fixture-backed local Git only; no remote/provider mutation authority.

### SAAS48-03 — Add injected, readback-reconciled GitHub publication operations

- Goal: Provide a closed injected provider port for push, primary PR create/reuse/readback, and squash merge request/readback, with immutable operation/head binding and no duplicate publication on replay.
- Target repository: `ai-config`.
- Likely files/modules: new provider/publication orchestration module(s) under `src/skills/linear-delivery-loop/scripts/`; `operations.py`, `supervisor.py`, `control_plane_records.py`; fixture ports/support in `tests/linear_delivery_supervisor/` and `tests/linear_delivery_control_plane/`, including new `test_publication_provider.py`.
- Acceptance criteria:
  - The only provider methods are narrow injected push/ref readback, PR create-or-reuse/readback, merge request/readback operations; requests are operation-ID and exact-head bound.
  - Before and after every attempted mutation, remote ref/PR/base/head/merge readback reconciles the journal so a crash, timeout, or ambiguous response cannot cause a duplicate push, PR, or merge.
  - The production surface contains no raw provider client, hosted-check discover/query/poll/wait/budget method, repository-settings/permissions/protection/ruleset/queue mutation, or bypass/admin merge method.
  - Primary PR targets `main`; provider evidence is redacted and persisted by reference, not as raw response secrets.
- Local test and runtime QA notes: Fixture provider responses must prove push, PR create/update/reuse, and merge success; timeout/readback success; ambiguous response/readback; duplicate replay prevention; base/head mismatch; and public-surface negative capability checks. Run focused suites, existing supervisor/control-plane suites, and `python .\scripts\validate.py`.
- Documentation impact: None yet; final operator-facing publication contract is documented in SAAS48-06.
- Dependencies / blocks: Depends on SAAS48-01 and SAAS48-02; blocks gates and recovery orchestration.
- Risks and non-goals: Provider fixtures model GitHub semantics only; no SDK/client, live GitHub request, hosted status check, or provider-control modification is introduced.
- Completion/publication boundary: No provider mutation occurs outside injected fixtures.

### SAAS48-04 — Execute clean isolated exact-SHA gates and converge evidence

- Goal: Execute the trusted repository aggregate at observed exact PR/merge SHAs in fresh gate worktrees and make review/QA/docs evidence converge deterministically.
- Target repository: `ai-config`.
- Likely files/modules: new local-gate/attestation/evidence-classifier module(s) under `src/skills/linear-delivery-loop/scripts/`; `worktrees.py`, `supervisor.py`, `operations.py`; trusted aggregate configuration/allowlist in existing repository-owned configuration; new focused tests such as `tests/linear_delivery_supervisor/test_exact_sha_gates.py` and `test_evidence_convergence.py`.
- Acceptance criteria:
  - For `ai-config`, resolve only fixed argv `python .\scripts\validate.py` from trusted configuration; execute without a shell in a fresh contained worktree at the provider-observed PR head or returned merge SHA.
  - Prove gate-worktree cleanliness before and after; record redacted argv digest, tool/version evidence, timestamps, exit code, normalized repository and physical-worktree identity, and exact SHA. Missing member/configuration, command failure, SHA/identity drift, or dirtiness fails closed.
  - Require implementation plus draft plan, tasks, audit, review, QA, and completion evidence, together with draft design evidence when the canonical design stage is required or an explicit validated not-required design record when it is not, before final gating. Missing required design evidence, a missing not-required declaration, or an invalid declaration fails closed. Review and applicable QA attest to the executable SHA.
  - Classify final deltas through a strict path/content allowlist. For a proven evidence-only delta, stage only the classifier-returned evidence files and create exactly one finalization commit; reread the provider-observed final PR head and require it to equal that commit before final-head docs, aggregate, and review reruns plus QA rerun or explicit named two-SHA safe-reuse attestation.
  - A second evidence-finalization commit, non-convergent delta, provider-final-head mismatch, executable/ambiguous change, or missing final-head rerun fails closed and invalidates the affected gates. After convergence, persist terminal supervisor and concise Linear evidence with final PR/base/head, gate/review/QA/docs identities, and merge-ready identity; no later branch mutation or completion commit is permitted.
  - No hosted check result is discovered, queried, waited on, or accepted as gate evidence.
- Local test and runtime QA notes: Fixtures prove fixed-command resolution, no-shell invocation, exact-SHA mismatch, clean-before/after, command failure, tool/evidence redaction, draft ordering, required-design and validated-not-required design members, missing/invalid-member refusal, and positive/negative evidence convergence: classifier-only staging, exactly one finalization commit, provider-final-head reread, final-head reruns, QA reuse bounds, second-commit/non-convergence/head-mismatch refusal, terminal supervisor/Linear identities, and no later branch mutation. Run focused suites and `python .\scripts\validate.py`.
- Documentation impact: Add the canonical evidence/gate ordering reference in SAAS48-06; this task may add only code-adjacent contract documentation required for maintainability.
- Dependencies / blocks: Depends on SAAS48-01 through SAAS48-03; blocks merge/repair finalization.
- Risks and non-goals: The configured aggregate is a trust boundary, not an implementation-selected command. This task does not add SaaS commands or real browser QA.
- Completion/publication boundary: Local disposable gate worktrees only; no live PR/merge or post-merge commit.

### SAAS48-05 — Recover provider refusals, squash merge safely, and bound repair

- Goal: Orchestrate refusal classification, exact authorized attended recovery, merge verification, and same-issue post-merge repair while preserving protected work fail closed.
- Target repository: `ai-config`.
- Likely files/modules: new publication-recovery/repair orchestration module(s); `operations.py`, `supervisor.py`, `control_plane.py`, `control_plane_records.py`, `reservations.py`, `lease.py`, `recovery.py`; focused new tests such as `test_publication_recovery.py`, `test_publication_merge_repair.py`, and control-plane reply fixtures.
- Acceptance criteria:
  - Classify transient only for explicit retryable 429, provider 5xx/unavailable, or temporary mergeability when readback proves non-application. Persist the initial attempt separately from `retryCount`; permit at most three retries after it for the same operation/head, indexed 1/2/3 to capped `Retry-After` or 5/15/30-minute backoff. The first refusal after retry count 3 is exhausted pause.
  - Every retry independently reconciles journal and remote readback. Transient wait and stable/exhausted/ambiguous/permission/policy/required-check/protection/ruleset/merge-queue refusal preserve the complete snapshot: `In Progress` before a PR and `In Review` after one, `autonomous`, global WIP, reservation, persistent worktree, branch, optional PR, and all evidence; release only the run lease.
  - Stable, exhausted, ambiguous, permission, policy, required-check, protection/ruleset, merge-queue, and unclassified refusal add `blocked + needs-human`, create/update one deduplicated Linear operational request through SAAS-47, and emit one idempotent redacted ntfy attention event. No automatic retry occurs while paused.
  - Pause uses exactly `RETRY-PUBLICATION <operation-id> <head-sha>`. Before consuming one fresh authorized reply and granting at most one idempotent operation, reread issue ordinary state, labels, and authorization; reservation and physical worktree; operation journal; branch, PR, head, base, and mergeability; every SHA-bound local/review/QA/docs attestation; and the latest provider requested-operation response and readback. Malformed, stale, duplicate, unauthorized, changed-head, unresolved, or ambiguous cases remain paused and update the same request; success clears `blocked` and `needs-human` and resumes the preserved stage.
  - Immediately before squash merge, re-read stop/authority/reservation/lease, PR/base/head/mergeability, and exact-head attestations. Base drift merges `origin/main` normally, never rebases/forces, and invalidates affected gates.
  - Verify returned merge identity by provider readback; rerun the clean aggregate at the returned merge SHA before success/release. A failed post-merge gate stays on the same issue in `In Review`, preserves `autonomous` and all protected state, and uses at most three numbered repair branches from current `main`. Every repair attempt re-enters the complete pipeline: repair-head issue-worktree aggregate before staging, isolated exact-repair-head aggregate, independent review, applicable QA, docs/evidence convergence, merge readback, and a clean aggregate at the exact returned repair-merge SHA. Missing, stale, or wrong-repair-head gate evidence blocks merge and completion. It never auto-reverts, and exhaustion transitions to `Backlog + needs-human`, updates the same durable request/evidence, and emits idempotent redacted ntfy without creating a speculative issue.
- Local test and runtime QA notes: Fixture each push/PR/merge refusal separately: required-check enforcement, protection/ruleset, merge queue, permission, 429, 5xx/unavailable, temporary mergeability, ambiguity, and exhaustion. Prove initial attempt plus three retries, 5/15/30 indexes, crash/replay and first-after-exhaustion boundaries; full pre-/post-PR ordinary-state plus `autonomous`/WIP/reservation/worktree/branch/PR/evidence preservation; stop-label add/clear; one deduplicated Linear request and idempotent ntfy; complete attended rereads and exact reply consumption; base drift invalidation, returned merge identity, no post-merge mutation, and repair-exhaustion request/ntfy. For each repair, prove the complete re-entry pipeline and that missing/stale/wrong-head pre-staging aggregate, exact-head aggregate, review, QA, docs/evidence convergence, merge readback, or returned-merge-SHA aggregate blocks merge/completion. Run new focused suites, existing supervisor/control-plane suites, and `python .\scripts\validate.py`.
- Documentation impact: Requires the canonical operator-facing provider-refusal/retry/pause, merge identity, base-drift, and repair reference updates in SAAS48-06.
- Dependencies / blocks: Depends on SAAS48-01 through SAAS48-04 and the actual SAAS-47 retry-reply contract. Blocks SAAS48-06 and SAAS-49.
- Risks and non-goals: No retry can infer authorization, weaken provider policy, inspect hosted checks, create a ticket to evade a refusal, or release protected state to recover from ambiguity.
- Completion/publication boundary: Fixture-only provider behavior; live merge, Linear, and ntfy mutation remain out of scope.

### SAAS48-06 — Compose the deterministic engine, document the contract, and register tests

- Goal: Integrate the completed publication subsystem into deterministic engine/control-plane composition, update canonical documentation, and make all fixture suites part of the repository aggregate.
- Target repository: `ai-config`.
- Likely files/modules: `src/skills/linear-delivery-loop/scripts/{agent-worker-engine.ps1,cli.py,operations.py,supervisor.py}`, relevant `references/` documentation, canonical protocol references under `src/skills/goal-to-delivery/references/` where ownership requires it, `validation/manifest.json` only if fixed aggregate registration needs it, `scripts/validate.py`, and the SAAS48 test modules.
- Acceptance criteria:
  - The composed runtime can invoke only the closed publication operations and preserves existing specialist non-mutation, authority, reservation, lease, full refusal snapshot, and one-primary-PR boundaries. It invokes and verifies, rather than redesigns, SAAS-47's deduplicated Linear request/exact-reply/idempotent ntfy seams, including repair exhaustion.
  - Public/runtime negative tests prove absence of hosted-check controls, raw provider client, arbitrary command/shell execution, direct-main/force/rebase/tag/release/auto-revert, provider-setting mutation, bypass, and live activation paths.
  - Canonical docs describe issue-worktree aggregate-before-staging plus later isolated exact-SHA gates, conditional design evidence, evidence ordering/convergence, refusal classification/initial-plus-three-retry backoff/pause, state and label preservation, exact reply syntax, returned squash merge identity, base drift, bounded repair and exhaustion notification, fixture-only rollout, and rollback preservation. They do not duplicate cross-tool protocol ownership.
  - `python .\scripts\validate.py` discovers/runs all new focused suites through the existing fixed aggregate without adding a second aggregate, network step, hosted gate, or real-user-home sync.
- Local test and runtime QA notes: Run every new focused suite, existing `tests/linear_delivery_supervisor/` and `tests/linear_delivery_control_plane/` suites, `python .\scripts\build.py`, `git diff --check`, and `python .\scripts\validate.py`. Intended later PR evidence runs the aggregate from clean isolated exact PR-head and returned merge-SHA worktrees; those provider actions are not performed by this task stage.
- Documentation impact: Required canonical/reference updates as above. Build generated projections only when separately authorized by the implementation workflow; never hand-edit `dist/`.
- Dependencies / blocks: Depends on SAAS48-01 through SAAS48-05. Blocks SAAS-49 distribution/parity work.
- Risks and non-goals: Do not silently make the fixture engine live or add SaaS-specific adapter configuration. Documentation must link to canonical policy rather than copy it.
- Completion/publication boundary: One implementation PR only after separate authority; no install/sync, Git/provider/Linear/ntfy action is authorized by this artifact.

## Sources consulted (paths)

- `C:\dev\luchdom\ai-config\AGENTS.md`
- `C:\dev\luchdom\ai-config\docs-ai\005-saas-48-deterministic-publication-and-exact-sha\workflow.json`
- `C:\dev\luchdom\ai-config\docs-ai\005-saas-48-deterministic-publication-and-exact-sha\2026-07-22-saas-48-deterministic-publication-and-exact-sha-plan.md`
- `C:\dev\luchdom\ai-config\docs-ai\001-dual-delivery-workflows-2026-07-16\2026-07-17-three-delivery-workflows-tasks.md` (historical read fallback; `DDW-AIC-004`)
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\SKILL.md`
- `C:\Users\lucas\.codex\skills\task-audit-breakdown\references\task-template.md`
- `C:\dev\luchdom\ai-config\src\skills\goal-to-delivery\references\artifact-contract.md`
- `C:\dev\luchdom\ai-config\src\skills\linear-delivery-loop\scripts\{contracts.py,operations.py,control_plane_records.py,supervisor.py,worktrees.py,reservations.py,recovery.py}`
- `C:\dev\luchdom\ai-config\src\skills\linear-delivery-loop\references\{engine-command,operation-journal,supervisor-state}.schema.json`
- `C:\dev\luchdom\ai-config\tests\linear_delivery_supervisor\` and `C:\dev\luchdom\ai-config\tests\linear_delivery_control_plane\`
- `C:\dev\luchdom\ai-config\scripts\validate.py`
