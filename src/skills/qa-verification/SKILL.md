---
name: qa-verification
description: Independently verify implemented work with repository-owned local commands and real runtime behavior mapped to acceptance criteria. Use after implementation for QA evidence; report defects and unverified work without fixing production code or substituting for code review.
---

# QA Verification

Verify the exact implementation target against observable acceptance criteria.

## Discover the local gate

- Read `AGENTS.md`, `README`, relevant docs, and manifests/scripts to discover the repository's real build, test, lint, type, documentation, and aggregate validation commands.
- Derive commands from the repository. Never hardcode machine paths, ports, URLs, tokens, or environment identifiers.
- Identify the exact working tree or SHA under test and fail on ambiguity.

## Exercise behavior

1. Run the smallest relevant checks first, then the full repository-required local aggregate.
2. Map every acceptance criterion to a concrete observed result.
3. Use real HTTP/browser/CLI/user flows for behavioral criteria. Mock only true boundaries.
4. Use environment guards, non-default values, isolated disposable data, bounded readiness predicates, and verified cleanup. Avoid fixed sleeps.
5. Treat skipped required checks, cleanup failures, identity mismatch, or an unexercised behavior path as incomplete verification.

## Report, do not fix

Write the dated `*-qa.md` in the exact registered `docs-ai/<work-key>-<slug>/` folder with target identity, commands/results, pass/fail counts, acceptance mapping, cleanup evidence, blockers, and residual risk. A historical numbered-and-dated folder or flat artifact may be read when explicitly selected, but must not be rewritten or migrated.

QA does not implement fixes, perform the pre-implementation audit, or replace exact-diff code review. Route defects to the caller for a separately authorized implementation pass. Do not mutate Linear or perform Git/provider actions.

Read [qa-checklist.md](./references/qa-checklist.md) before reporting and the canonical quality contract in `../goal-to-delivery/references/quality-gates.md`.
