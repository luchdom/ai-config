# SAAS-56 curated repository memory and bounded retrieval — Documentation verification

## Verdict

**PASS** — the four durable documentation pages match the final repository-memory implementation and its rebuilt Claude, Codex, and Copilot projections. Canonical and generated navigation resolves, schema/runtime inventories and named digest projections agree, commands are valid, and the pages keep shared delivery protocol ownership in the canonical `$goal-to-delivery` references.

This is documentation verification only. It does not replace independent code review, runtime QA, the repository aggregate, publication, merge, or exact returned-merge-SHA validation.

## Pages verified

- `src/skills/linear-delivery-loop/references/repository-memory.md`
- `docs/repository-memory/README.md`
- `README.md`
- `src/skills/luchdom-docs/references/doc-targets.md`

## Content consistency

PASS. The durable pages accurately describe the final implementation:

- repository records and marker files are the portable tier; state-home index, journals, prepared data, and results are derived/reconstructable;
- one valid marker created after all no-clobber record writes is the sole durable batch commit point; pre-marker orphans remain invisible and post-marker index failure is `index-reconstruction-required`;
- promotion remains a 1–32 candidate ordered batch under the repository mutex and existing exact mutation authority rather than a new public supervisor authority operation;
- the nine strict schemas, acyclic named projections, canonical JSON hashing, typed assertions, complete-map duplicate boundary, structural conflicts, provenance-topology confidence, append-only lifecycle, freshness, retention, archive/restoration, redaction, and marker-based state-home recovery are represented without relying on prose/model judgment;
- deterministic query defaults/minima/maxima are records `8/1/32`, characters `12000/1000/48000`, and bytes `24576/4096/98304`; rank priorities, whole-item omission, source reread, and count-only diagnostics match runtime;
- planner, implementer, code reviewer, and QA context is opt-in tool-role untrusted data with authenticated selector invariance and inclusive six-digit final accounting;
- the public memory CLI accepts only `query`, `rebuild`, `repair`, and `context`; version-1 repair is derived-only rebuild; supervisor status is observation-only and never performs implicit repair;
- setup prerequisites, explicit opt-in posture, verification, rollback, state-home loss, orphan, invalid-marker, stale-source, conflict/graph, unsafe-path, secret-like, and context-budget troubleshooting are present and do not advise destructive source repair.

Implementation evidence checked included:

- `src/skills/linear-delivery-loop/scripts/repository_memory.py` constants and behavior at lines 40–49, 314–337, 731–749, 817–874, 983–1051, and 1053–1094;
- `src/skills/linear-delivery-loop/scripts/cli.py` strict memory surface at lines 669–722;
- `src/skills/linear-delivery-loop/scripts/contracts.py` schema/runtime inventory at lines 59–69, 166–210, and 1317–1360;
- all nine `src/skills/linear-delivery-loop/references/repository-memory-*.schema.json` contracts and the final marker/index/record modules.

## Navigation and ownership

PASS. A PowerShell Markdown check examined the four canonical pages plus the generated repository-memory and `luchdom-docs` pages under all three tool trees. It resolved **67 local links and one anchor** across four canonical and six generated files and found no trailing whitespace.

The earlier projection-only broken link from the shared runbook to the repository root was corrected before this final verification. The rebuilt runbook now contains projection-safe wording, and every local link resolves from:

- `dist/claude/skills/linear-delivery-loop/references/repository-memory.md`
- `dist/codex/skills/linear-delivery-loop/references/repository-memory.md`
- `dist/copilot/skills/linear-delivery-loop/references/repository-memory.md`

`README.md` provides orientation and links to both durable memory pages. `doc-targets.md` assigns repository curation/lifecycle/recovery to `docs/repository-memory/README.md` and shared contracts/runtime/troubleshooting to the module reference. No workflow evidence folder was added to primary navigation.

## Source-to-dist projection verification

PASS. `dist/manifest.json` was parsed after the repair rebuild. For the repository-memory references, schemas, runtime modules, and documentation ownership map, every current source SHA-256 equaled the manifest `sourceSha256` and every declared projection existed and equaled both its manifest hash and source hash:

- **14 selected canonical sources**;
- **42 generated projections** — one each for Claude, Codex, and Copilot;
- repository-memory runbook source SHA-256: `7e4921372c12b1b358782a9ef7ee83976ea9baf1ae560c0143f7aea3c4d62948`;
- documentation ownership source SHA-256: `aca6f8333df8ffa4afd4e8fda7bb761f58408ae020c41cc5000f4c1ea42a1cf0`.

The selected set comprised the nine repository-memory schemas, the shared runbook, three repository-memory Python modules, and `luchdom-docs/references/doc-targets.md`.

## Exact commands and results

1. Manifest/source/projection SHA verification: PowerShell parsed `dist/manifest.json`, selected sources matching `repository-memory`, `repository_memory`, or `luchdom-docs/references/doc-targets`, and compared `Get-FileHash -Algorithm SHA256` for each source and projection. **Exit 0**: 14 sources and 42 projections matched.
2. Canonical/generated Markdown verification: PowerShell parsed Markdown links in the four canonical pages and six generated runbook/ownership pages, resolved relative paths and headings, and checked trailing whitespace. **Exit 0**: 67 local links, one anchor, no missing target, no trailing whitespace.
3. `git diff --check -- README.md src/skills/luchdom-docs/references/doc-targets.md`. **Exit 0**; only PowerShell's expected LF-to-CRLF working-copy warnings were emitted.
4. `python .\src\skills\linear-delivery-loop\scripts\cli.py --help`. **Exit 0**; usage exposes mutually exclusive `--request` and `--repository-memory-request`, matching the documented source command.
5. `python -m unittest tests.linear_delivery_repository_memory.test_contracts.ContractTests.test_schema_runtime_parity_and_acyclic_known_answers tests.linear_delivery_repository_memory.test_contracts.ContractTests.test_real_layer_projection_bytes_digests_and_included_excluded_boundaries -v`. **Exit 0**: two tests passed in 12.376 seconds. This proves registered schema/runtime parity, canonical known answers, and included/excluded digest boundaries against real contract objects.

An earlier verifier invocation of `python .\scripts\validate.py` was terminated by the command timeout after 304.1 seconds without a completed result or reported test failure. It is therefore **not claimed as passing evidence here**. The repository aggregate remains a distinct RM-06/exact-head gate owned outside this documentation-only verdict.

## Canonical protocol boundary

PASS. The memory pages link the canonical artifact and quality contracts instead of copying their normative stage, clarification, quality, completion, publication, or Handoff definitions. Local text is limited to repository-memory-specific storage, authority restrictions, promotion mechanics, commands, lifecycle, recovery, and stricter safety. `README.md` remains orientation, while `docs-ai/` remains per-work evidence rather than reusable guidance.

## Residual gaps

None within documentation scope. Seed curation and implicit live autonomous loading remain intentionally disabled and are stated as rollout boundaries, not documentation omissions. The incomplete aggregate attempt above remains separate validation work and does not weaken the verified documentation/link/projection result.
