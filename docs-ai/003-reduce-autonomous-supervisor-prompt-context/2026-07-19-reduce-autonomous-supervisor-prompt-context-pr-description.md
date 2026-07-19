# Reduce autonomous supervisor prompt context

## Overview

Reduce routine `$linear-delivery-loop` prompt loading while preserving deterministic supervisor validation, authority, and recovery behavior.

## Changes

- Add one compact canonical autonomous runtime contract.
- Route healthy autonomous iterations through only that contract.
- Enforce an 8,192-byte prompt-context budget and exact local-link closure.
- Detect inline, reference-style, multiline, angle-bracket, and HTML local links so alternate syntax cannot bypass the budget.
- Keep detailed architecture, schemas, and runtime scripts as diagnostic or deterministic assets.
- Document the progressive-disclosure behavior in the repository README.

## Security Impact

No supervisor runtime, schema, authorization, reservation, Handoff, or recovery implementation changed. Existing deterministic parity checks continue to cover all 11 schemas and 14 engine operations.

## Testing

- `python -m unittest tests.test_delivery_contracts -v` — 22/22 passed.
- `python -m unittest tests.linear_delivery_supervisor.test_contracts -v` — 6/6 passed.
- `python .\scripts\validate.py` — 195/195 passed.
- Prompt surface: 5,968 bytes against an 8,192-byte maximum, reduced from 40,821 bytes.
- Independent final code review: PASS with zero findings.

Testing in environment:

1. Run `python .\scripts\validate.py` from a clean checkout of the PR head.
2. Confirm `src/skills/linear-delivery-loop/SKILL.md` has exactly one direct local reference.
3. Confirm the referenced compact contract has no indirect local links.
4. Confirm validation reports the combined prompt surface below 8,192 bytes.

## Related Work

Local workflow `c8804502-5267-4415-85f6-5db6b86d1a34`. No Linear issue is attached.
