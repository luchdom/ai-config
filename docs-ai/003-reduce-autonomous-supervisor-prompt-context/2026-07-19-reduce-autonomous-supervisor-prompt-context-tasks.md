# Reduce Autonomous Supervisor Prompt Context — Execution Tasks

## Status and authority

Plan is available and design is not required: this is a policy, validation, generated-projection, and documentation change with no product UI or interaction change. The active workflow is `c8804502-5267-4415-85f6-5db6b86d1a34`, targets `C:\dev\luchdom\ai-config`, and stops at the `working-tree` boundary. Implementation must acquire the repository editing reservation before changing repository deliverables. No commit, PR, merge, Linear mutation, scheduled-automation change, or installation/sync action is authorized.

## Audit notes

The independent auditor must verify that the compact contract preserves the essential autonomous semantics (prepared capability only, authority remains adapter-owned, fail-closed behavior, stage/quality ownership, structured pause for material decisions, one-issue limit, checkpoints, and merge completion) without reintroducing the detailed protocol by copy. It must also check that the byte-budget measurement is deterministic, correctly follows only mandatory direct local Markdown references, and cannot be bypassed by indirect links, renamed policy copies, schema links, or script links. Confirm the existing supervisor contract suites still prove that schemas, all 14 operations, reservation, authorization, recovery, and Handoff behavior were untouched.

## Dependency graph

`CTX-01` is the sole code-bearing task. It depends on the approved plan and the existing canonical protocol and supervisor contract tests. Its generated projections and README update follow the canonical-source and validation changes in the same task.

### CTX-01 — Route healthy autonomous iterations through a compact, tested runtime contract

- Goal: Reduce routine `$linear-delivery-loop` entry-plus-direct-reference context to no more than 8,192 bytes while retaining deterministic enforcement and the detailed protocol for semi-autonomous and manual entries.
- Target repository: `C:\dev\luchdom\ai-config`
- Likely files/modules:
  - Add `src/skills/goal-to-delivery/references/autonomous-runtime-contract.md` as the sole compact canonical protocol reference for healthy autonomous iterations.
  - Update `src/skills/linear-delivery-loop/SKILL.md` to link only that compact contract and retain concise invocation, authority, advancement, stopping, and output policy.
  - Update `validation/delivery_contracts.py` and `tests/test_delivery_contracts.py` for entry-specific canonical-link expectations, direct prompt-surface closure/byte-budget validation, and negative fixtures for forbidden detailed, schema, and script links.
  - Preserve `src/skills/goal-to-delivery/SKILL.md`, `src/skills/spec-driven-delivery/SKILL.md`, `src/skills/linear-delivery-loop/references/supervisor-core.md`, all 11 supervisor schemas, and `src/skills/linear-delivery-loop/scripts/` as detailed, diagnostic, or deterministic assets unless a test-only adjustment is strictly needed.
  - Update `README.md`; regenerate affected `dist/` skill projections and `dist/manifest.json` through `scripts/build.py`.
- Acceptance criteria:
  - A healthy autonomous entry directly loads exactly the new compact canonical runtime contract; its measured entry-plus-direct-reference surface is at most 8,192 UTF-8 bytes.
  - The autonomous entry has no direct local link to `supervisor-core.md`, any JSON schema, a script, or the six detailed cross-entry protocol references; its compact contract is canonical rather than a competing copied doctrine.
  - The compact contract carries the semantic anchors needed for a safe autonomous iteration: adapter-prepared single capability, fail-closed authority, bounded staged delivery and quality gates, structured material-decision pause, adapter-only checkpoint/external authority, stop conditions, and exact merge completion expectations.
  - Goal-to-delivery and spec-driven-delivery continue to directly link all six detailed canonical references, including `work-descriptor.schema.json`.
  - Existing supervisor runtime/schema parity and state, reservation, authorization, Handoff, and recovery behavior are not changed; the focused contract suites pass.
  - Generated `dist/` projections exactly match `src/`, and README guidance distinguishes routine prompt policy from deterministic and diagnostic assets.
- Local test and runtime QA notes:
  - Run `python -m unittest tests.test_delivery_contracts -v` and extend it with positive and negative tests for the entry-specific links, compact-contract semantic anchors, forbidden prompt links, and exact byte budget.
  - Run `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` to retain the 11-schema and 14-operation runtime contract evidence.
  - Run `python .\scripts\build.py`, inspect generated autonomous skill projections and manifest for the compact-only direct link, then run `python .\scripts\validate.py`.
  - Record the measured UTF-8 byte total, commands, exit codes, and source/generated paths in later review and QA evidence; do not treat hosted-provider status as evidence.
- Documentation impact: Update the README’s canonical-protocol/supervisor guidance to explain progressive disclosure: healthy autonomous iterations load the compact runtime contract, while the supervisor core and schemas stay diagnostic/runtime assets.
- Dependencies / blocks: Requires the approved plan and no design artifact. Implementation is blocked if preserving essential autonomous semantics needs a policy choice outside the plan, or if the current worktree/reservation cannot safely authorize repository edits.
- Risks and non-goals: Avoid policy omission, hidden prompt-surface growth, competing doctrine, and generated-copy drift. Do not alter runtime supervisor behavior, schemas, engine operations, leases, reservations, worktrees, preflight, Handoff, recovery, cleanup, Linear/GitHub/notification integrations, scheduled automation, or large runtime module structure.
- Completion/publication boundary: Complete all scoped source, generated, test, validation, and documentation work in the current working tree. Do not commit, push, create a PR, merge, mutate Linear, or run installation/sync.

## Sources consulted (paths)

- `AGENTS.md`
- `docs-ai/003-reduce-autonomous-supervisor-prompt-context/workflow.json`
- `docs-ai/003-reduce-autonomous-supervisor-prompt-context/2026-07-19-reduce-autonomous-supervisor-prompt-context-plan.md`
- `src/skills/linear-delivery-loop/SKILL.md`
- `src/skills/spec-driven-delivery/SKILL.md`
- `src/skills/goal-to-delivery/references/`
- `src/skills/linear-delivery-loop/references/supervisor-core.md`
- `src/skills/linear-delivery-loop/scripts/`
- `validation/delivery_contracts.py`
- `tests/test_delivery_contracts.py`
- `tests/linear_delivery_supervisor/test_contracts.py`
- `README.md`
