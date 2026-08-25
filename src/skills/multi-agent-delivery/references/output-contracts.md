# Handoff Output Contracts

## Tasking prerequisite

- Concrete plan with exact sources
- Material decisions resolved or explicitly paused
- Frontend/UI classification with exact binding design sources
- Design spec when `design-gates.md` requires one, otherwise a mechanical-change reason tied to a binding source
- Required post-implementation design-conformance path for changed rendered UI or interaction
- Acceptance and local validation strategy

## Implementation prerequisite

- Passing independent audit
- Bounded tasks, likely files/modules, acceptance criteria, tests, docs impact, and dependencies
- Active entry authority and intended repository scope

## Review prerequisite

- Exact target/base identity or well-defined working-tree diff
- Real-file change manifest and implemented tests
- Approved requirement/plan/tasks/design
- For changed rendered UI or interaction, a current product-designer design conformance `PASS` for the reviewed implementation identity

## QA prerequisite

- Review-ready implementation identity
- Current applicable design-review result for the same identity
- Acceptance criteria and runtime paths
- Repository-owned local validation commands and safe disposable test setup

## Completion prerequisite

- Required review, QA, docs, and local gates pass at the declared boundary
- External/Git actions have separate explicit or autonomous-entry authority
- Evidence identifies the exact target and anything still unverified

Every producer uses the descriptor's registered current path. An explicitly supplied historical layout is readable fallback only and remains unchanged.
