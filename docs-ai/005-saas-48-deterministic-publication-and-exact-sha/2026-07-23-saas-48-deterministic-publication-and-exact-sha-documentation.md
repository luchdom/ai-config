# SAAS-48 deterministic publication and exact-SHA gates — Documentation

## Verdict

**PASS** — the durable Linear control-plane reference documents the strict state `1.0` to `1.1` migration and fail-closed tamper boundary, generated projections are current, and every narrow documentation, schema, migration, parity, link, and whitespace check passes.

This is a documentation-stage verdict only. It is not code review or runtime QA.

## Durable documentation impact

The nearest durable sources are:

- `README.md` — links the fixture-first publication engine from repository orientation and keeps live activation explicitly deferred.
- `src/skills/goal-to-delivery/references/completion-boundaries.md` — states that a failed exact returned-merge-SHA gate is not completion and routes bounded same-work repair without auto-revert.
- `src/skills/goal-to-delivery/references/quality-gates.md` — owns cross-tool pre-staging, exact-head, conditional design, one-commit evidence convergence, and terminal-identity requirements.
- `src/skills/linear-delivery-loop/references/linear-control-plane.md` — owns preserved Linear state/labels, the exact attended reply, the control-plane/publication-engine boundary, and the strict persisted-state migration/tamper contract.
- `src/skills/linear-delivery-loop/references/supervisor-core.md` — records publication state in `Status`, links the dedicated publication reference, and lists the complete 20-command public engine surface.
- `src/skills/linear-delivery-loop/references/publication.md` — owns fixture-first contained Git preparation, injected provider readback, refusal/recovery, exact-SHA evidence convergence, base drift, squash merge, bounded repair, rollback, and troubleshooting behavior.

No competing protocol page was added. Shared quality/completion policy remains under `goal-to-delivery`; transport-specific behavior remains under `linear-delivery-loop`.

## Sources checked

- `workflow.json`, approved plan, execution tasks, and passing re-audit 2 in this registered work folder.
- The exact implementation record through its SAAS-48 correction history.
- `2026-07-23-saas-48-deterministic-publication-and-exact-sha-code-review-10.md` with verdict **PASS**.
- The public operation inventory in `scripts/contracts.py`, dispatch/status surface in `scripts/supervisor.py`, control-plane migration in `scripts/control_plane_records.py`, and the five changed control-plane/publication/supervisor JSON schemas.

## Documentation and schema checks

### PASS — local Markdown links

Command: a repository-root PowerShell link resolver over exactly the six durable pages above, matching Markdown targets with `\[[^\]]+\]\(([^)]+)\)`, resolving each non-HTTP target relative to its containing page, and requiring `Test-Path -LiteralPath`.

Result: **PASS** — all local targets resolve across 6 pages.

### PASS — changed schema parse

Command:

```powershell
$schemaFiles = @(
  'src/skills/linear-delivery-loop/references/control-plane-state.schema.json',
  'src/skills/linear-delivery-loop/references/engine-command.schema.json',
  'src/skills/linear-delivery-loop/references/operation-journal.schema.json',
  'src/skills/linear-delivery-loop/references/supervisor-state.schema.json',
  'src/skills/linear-delivery-loop/references/publication-state.schema.json'
)
foreach ($schema in $schemaFiles) { Get-Content -Raw -LiteralPath $schema | ConvertFrom-Json | Out-Null }
```

Result: **PASS** — 5 schemas parse, including `control-plane-state.schema.json` version `1.1`.

### PASS — runtime/schema inventory parity

Command:

```powershell
python -m unittest tests.linear_delivery_supervisor.test_contracts.SupervisorContractTests.test_runtime_parity_inventory_and_every_valid_contract
```

Result: **PASS** — 1 test in 0.038 seconds.

### PASS — strict control-plane state migration fixture

Command:

```powershell
python -m unittest tests.linear_delivery_control_plane.test_migration_status.MigrationStatusTests.test_control_plane_store_migrates_publication_reply_lower_bounds_once -v
```

Result: **PASS** — 1 test in 0.137 seconds. The fixture proves one-time `1.0` to `1.1` migration, revision advancement, deterministic reply lower-bound backfill, idempotent reread, and refusal to rewrite a tampered current `1.1` record.

### PASS — scoped documentation whitespace

Commands:

```powershell
git diff --check -- README.md src/skills/goal-to-delivery/references/completion-boundaries.md src/skills/goal-to-delivery/references/quality-gates.md src/skills/linear-delivery-loop/references/linear-control-plane.md src/skills/linear-delivery-loop/references/supervisor-core.md
git diff --no-index --check -- NUL src/skills/linear-delivery-loop/references/publication.md
```

Result: **PASS** — no whitespace errors; Git reported line-ending conversion notices only. The second command's normal exit `1` denotes the expected new-file diff, not a whitespace error.

### PASS — repository delivery-contract documentation/drift gate

Command:

```powershell
python -m unittest tests.test_delivery_contracts -v
```

Result: **PASS** — 22 tests in 0.757 seconds, including repository delivery-contract, supervisor-core completeness, and generated-projection drift checks.

## Residual gaps

None within the authorized documentation scope. The durable migration guidance and generated projections agree with the current `1.1` schema/runtime boundary.

Per the assigned narrow-check boundary, `python .\scripts\validate.py` and other full aggregates were not run. No Git, Linear, GitHub, ntfy, provider, hosted-check, or network mutation was performed.
