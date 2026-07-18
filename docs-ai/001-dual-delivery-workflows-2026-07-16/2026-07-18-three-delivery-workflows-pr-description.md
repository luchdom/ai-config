## Overview

Adds a reusable, local-first delivery harness with explicit autonomous, semi-autonomous, and manual spec-driven entry points. The three workflows share one versioned protocol and one deterministic base engine so projects can adopt the same planning, implementation, review, QA, and documentation loop without duplicating policy.

## Changes

- Add the `goal-to-delivery`, `spec-driven-delivery`, and `linear-delivery-loop` entry skills.
- Add repository-scoped workflow identity, safe state storage, atomic allocation and registry handling, exact resume/attachment, and managed Handoff support.
- Add shared planner, auditor, reviewer, QA, and documentation contracts across supported tools.
- Update project templates and repository documentation for the local-first three-workflow model.
- Add generated-source parity checks and a fixed aggregate local validation manifest.

## Security Impact

- State and artifact paths fail closed on traversal, reparse-point, hard-link, identity, and authority mismatches.
- Managed Handoff records immutable, hash-bound evidence and redacts sensitive paths without performing implicit Git or reservation mutations.
- The aggregate local gate rejects arbitrary shell, network, provider, installation, synchronization, CI, and Git-mutation commands.

## Testing

Automated:

- Run `python .\scripts\validate.py` from the repository root.
- Expect the build and marker checks to pass, all 94 tests to pass without skips, and `Local validation gate: PASS`.
- Run `python -m compileall -q scripts validation src/skills/goal-to-delivery/scripts tests` and expect exit code 0.
- Run `git diff --check` and expect no whitespace errors.

Testing in environment:

- From a fresh local checkout at the PR head, run `python .\scripts\validate.py`.
- Confirm exactly three entry skills are accepted by the semantic contracts and generated `dist/manifest.json` matches canonical `src/` content.
- Confirm the working tree remains clean after validation; the validator must not install, sync, publish, or contact external providers.

## Related Work

- Linear: SAAS-45
- Establishes the local base required by the supervisor, notification, SaaS runtime QA, and documentation follow-up issues.
