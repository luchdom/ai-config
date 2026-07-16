# QA Checklist

Repo-agnostic. Discover specifics from the target repo; do not assume tools or paths.

## Pre-run

- [ ] Read `AGENTS.md`, `README`, manifests, and CI scripts to find build, test, lint, and type-check commands.
- [ ] Identify the changed area, its relevant suites, quality gates, and acceptance criteria.

## Run

- [ ] Build succeeds.
- [ ] Type-check and lint pass when provided by the repo.
- [ ] Run the focused subset first, then the full relevant suite.
- [ ] Prefer real behavior with mocked boundaries; avoid fixed sleeps for async work.

## Verify intent

- [ ] Each acceptance criterion maps to a concrete observed result.
- [ ] Tests exercise changed behavior rather than only producing green output.
- [ ] Document and route discovery failures instead of relaxing assertions.

## Report

- [ ] Commands and results.
- [ ] Pass/fail counts and quality gates.
- [ ] Acceptance criteria verified vs. not verified.
- [ ] Residual risk and unverified work.
