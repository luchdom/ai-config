# Reduce Autonomous Supervisor Prompt Context — Plan

## Goal

Reduce the routine `$linear-delivery-loop` prompt surface from 40,821 bytes to at most 8,192 bytes while preserving the deterministic supervisor schemas, validation, recovery, reservation, and authorization behavior.

## Current evidence

- `src/skills/linear-delivery-loop/SKILL.md` directly exposes the detailed `supervisor-core.md` reference and requires six canonical protocol files, including the 9,232-byte work-descriptor schema.
- The routine prompt-reachable surface is 40,821 bytes: the entry skill, six canonical references, and `supervisor-core.md`.
- The supervisor JSON schemas and Python runtime are already deterministic assets; `contracts.py`, `cli.py`, `store.py`, and `recovery.py` enforce them without requiring model context.
- `validation/delivery_contracts.py` currently forces all three entries to link all six canonical references and forces the exhaustive operation inventory into the prompt-facing autonomous skill.

## Approach

1. Add one concise canonical autonomous runtime contract under `src/skills/goal-to-delivery/references/`. It will be the sole prompt-loaded protocol reference for a healthy autonomous iteration, not a duplicate of the long-form protocol.
2. Slim `src/skills/linear-delivery-loop/SKILL.md` to invocation, authority, advancement, stopping, and output rules. It will direct healthy runs only to the compact contract and explicitly keep scripts, schemas, and diagnostic architecture out of routine context.
3. Keep `supervisor-core.md`, all supervisor schemas, and all runtime/recovery code unchanged as diagnostic and deterministic assets.
4. Make canonical link validation entry-specific: goal and manual entries retain their existing detailed references; the autonomous entry must link only the compact canonical runtime contract.
5. Add an autonomous prompt-surface regression that rejects detailed/schema/script links and enforces an 8,192-byte combined entry-plus-direct-reference budget.
6. Regenerate `dist/`, run focused delivery-contract and supervisor contract tests, then run the repository aggregate.

## Acceptance criteria

- A healthy `$linear-delivery-loop` invocation has at most 8,192 bytes of mandatory skill/reference context, measured deterministically by repository validation.
- The autonomous entry directly loads one compact canonical runtime contract and does not directly load `supervisor-core.md`, JSON schemas, scripts, or the detailed cross-entry reference set.
- `$goal-to-delivery` and `$spec-driven-delivery` retain their detailed canonical protocol links.
- All 11 supervisor schemas, all 14 engine operations, runtime schema parity, persisted-state validation, reservations, authorizations, Handoff, and recovery remain enforced by deterministic code and existing tests.
- Generated projections match canonical `src/` and the aggregate local validation passes.
- Durable README guidance distinguishes prompt-facing policy from deterministic/diagnostic assets.

## Non-goals

- No behavioral change to supervisor state, leases, reservations, worktrees, preflight, Handoff, cleanup, or recovery.
- No schema format, engine command, notification, Linear, GitHub, or scheduled automation change.
- No refactor of large runtime modules in this goal.
- No commit, PR, merge, or Linear mutation at the `working-tree` boundary.

## Risks and mitigations

- **Policy omission:** protect essential autonomous semantics with explicit semantic-anchor tests in the compact contract.
- **Competing doctrine:** place the compact contract inside the sole canonical protocol directory and prohibit renamed copies elsewhere.
- **Hidden prompt growth:** validate the exact direct-link closure and byte budget.
- **Runtime weakening:** do not edit runtime modules or schemas; retain existing parity and recovery suites.
- **Installed-copy drift:** regenerate `dist/`; installation/sync remains outside this boundary and will be reported separately.

## Validation strategy

- `python -m unittest tests.test_delivery_contracts -v`
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v`
- `python .\scripts\build.py`
- `python .\scripts\validate.py`
- Verify the measured autonomous prompt surface and inspect the real generated skill projections.

## Documentation impact

Update `README.md` to describe progressive disclosure: healthy autonomous iterations load the compact contract, while supervisor architecture and schemas remain diagnostic/runtime assets.

## Rollback

Revert the compact-contract routing, entry-specific validation, prompt-budget test, README update, and generated projections together. Runtime state and schemas require no migration.

## Assumptions

- A healthy prepared iteration does not require model inspection of engine schemas or supervisor internals because the deterministic adapter validates and owns those concerns.
- An 8,192-byte prompt budget is conservative and leaves room for future essential policy without returning to the current 40,821-byte footprint.

## Sources consulted

- `AGENTS.md`
- `README.md`
- `src/skills/linear-delivery-loop/SKILL.md`
- `src/skills/linear-delivery-loop/references/supervisor-core.md`
- `src/skills/linear-delivery-loop/scripts/contracts.py`
- `src/skills/linear-delivery-loop/scripts/cli.py`
- `src/skills/linear-delivery-loop/scripts/store.py`
- `src/skills/linear-delivery-loop/scripts/recovery.py`
- `src/skills/goal-to-delivery/references/`
- `validation/delivery_contracts.py`
- `tests/test_delivery_contracts.py`
- `tests/linear_delivery_supervisor/test_contracts.py`
