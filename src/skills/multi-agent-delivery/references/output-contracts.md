# Handoff Output Contracts

## Tasking prerequisite

- Concrete plan with exact sources
- Material decisions resolved or explicitly paused
- Design spec for material UI/UX work, otherwise a not-required reason
- Acceptance and local validation strategy

## Implementation prerequisite

- Passing independent audit
- Bounded tasks, likely files/modules, acceptance criteria, tests, docs impact, and dependencies
- Active entry authority and required repository reservation

## Review prerequisite

- Exact target/base identity or well-defined working-tree diff
- Real-file change manifest and implemented tests
- Approved requirement/plan/tasks/design

## QA prerequisite

- Review-ready implementation identity
- Acceptance criteria and runtime paths
- Repository-owned local validation commands and safe disposable test setup

## Completion prerequisite

- Required review, QA, docs, and local gates pass at the declared boundary
- External/Git actions have separate explicit or deterministic authority
- Evidence identifies the exact target and anything still unverified

Every producer uses the descriptor's registered current path. An explicitly supplied historical layout is readable fallback only and remains unchanged.
