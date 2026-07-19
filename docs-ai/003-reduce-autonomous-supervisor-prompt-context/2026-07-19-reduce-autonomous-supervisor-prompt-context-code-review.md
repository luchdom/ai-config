# Reduce Autonomous Supervisor Prompt Context — Code Review

## Verdict

**CHANGES REQUESTED.** One P2 finding prevents the prompt-surface regression from proving the approved no-bypass acceptance criterion. No P1 or P3 findings were identified.

## Reviewed target

- Baseline and current HEAD: `c1a421cc0e1966f0cde53a1e40c5519c588cc466` (`main`)
- Workflow: `c8804502-5267-4415-85f6-5db6b86d1a34`
- Exact working-tree scope: `README.md`, `src/skills/goal-to-delivery/references/autonomous-runtime-contract.md`, `src/skills/linear-delivery-loop/SKILL.md`, `tests/test_delivery_contracts.py`, and `validation/delivery_contracts.py`, plus this workflow's evidence
- Review date: 2026-07-19

## Findings

### P2 — Prompt-link closure can be bypassed with valid Markdown link forms

`validation/delivery_contracts.py:84` and `validation/delivery_contracts.py:144-151` recognize only inline links shaped like `[label](target)`. `check_autonomous_prompt_surface` then treats that incomplete result as the complete link closure at lines 306-328. A valid reference-style local link such as `[details][policy]` with `[policy]: ../goal-to-delivery/references/quality-gates.md`, an HTML link, or an angle-bracket destination is invisible to the validator. The linked detailed policy can therefore become mandatory prompt context without being rejected or included in the 8,192-byte budget.

The new negative tests at `tests/test_delivery_contracts.py:176-214` exercise only inline-link syntax, so they pass while leaving the same bypass untested. This contradicts CTX-01's requirement that direct/indirect detailed, schema, script, and renamed-policy dependencies cannot bypass the measured prompt surface.

Required repair: make local-reference discovery cover every supported Markdown reference form (or fail closed on unsupported link-bearing syntax), apply the same canonical resolution to both the entry and compact contract, and add negative fixtures for reference-style and other supported non-inline local links. The byte budget must be computed only after the validator has proved that no additional local prompt asset is reachable.

## Non-regression and scope observations

- The implementation does not edit supervisor scripts or schemas; the deterministic operation/schema inventory remains in validation.
- The compact entry and contract currently total 5,968 bytes, below the 8,192-byte ceiling.
- The generated manifest contains projections for both the compact contract and updated autonomous entry. Generated files are ignored build output in this repository rather than Git-tracked source.
- The earlier focused delivery-contract and supervisor-contract suites passed, but the missing syntax variants mean that result does not close the P2 finding.

## Evidence inspected

- `git status --short`
- `git diff --stat c1a421cc0e1966f0cde53a1e40c5519c588cc466`
- Exact source diff against `c1a421cc0e1966f0cde53a1e40c5519c588cc466`
- Approved plan, tasks, and independent audit
- Canonical delivery contract and generated `dist/manifest.json` projections
