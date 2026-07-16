---
name: qa-verification
description: Verify implemented work by discovering and running the repo's own build, tests, lint, and type checks, then confirming acceptance criteria against real behavior. Use after implementation to check that a change actually works, not just that it compiles or that tests are green.
---

# QA Verification

Verify that implemented work does what it should. Discover the repo's own tooling, run it, and check behavior against acceptance criteria. Report what is verified, what is not, and residual risk.

## Discover, never hardcode

- Read `AGENTS.md`/`README`, then manifests and CI scripts to find the real build, test, lint, and type-check commands.
- Derive commands from the repo, not memory. Never hardcode absolute paths, machine names, ports, dev URLs, tokens, or environment identifiers.
- Stay shell-agnostic.

## Run meaningful verification

- Run the smallest relevant subset first, then the full relevant suite before declaring done.
- Prefer behavioral or integration coverage: keep business logic real and mock only boundaries.
- For async work, wait on explicit readiness predicates within a bounded window; do not use fixed sleeps.

## Verify intent, not just green output

- Map every acceptance criterion to a concrete observed check.
- Use non-default values when defaults could hide broken wiring.
- Do not commit failing or skipped tests. Document an unpassable scenario as a discovery-failure and route it to an implementer.

## Respect the repo's gates

- Honor existing warnings, analyzers, coverage, lint, and type-check requirements.
- Keep test setup and cleanup clean; treat cleanup failures as diagnostics.

## Report

Write `<YYYY-MM-DD>-<slug>-qa.md` in the active workflow folder with commands and results, pass/fail counts and quality gates, acceptance criteria verified/not verified, and residual risk.

Read [references/qa-checklist.md](./references/qa-checklist.md) before reporting.
