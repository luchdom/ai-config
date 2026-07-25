# Quality Gates

Use repository-owned local commands and the smallest evidence that proves the acceptance criteria. CI is optional and hosted status never replaces required local validation.

## Proportional gates

1. Run focused tests for the changed area first.
2. Run one standard repository-owned local validation command before code reaches `merge`.
3. Perform one independent code review of the implemented diff.
4. Run real HTTP, browser, CLI, or other runtime QA only when acceptance criteria are behavioral.
5. Update the nearest durable documentation when behavior, architecture, setup, or operations changed.

Use a separate pre-implementation auditor for high-risk, ambiguous, security-sensitive, tenancy-sensitive, billing, migration, or unusually large work. Routine small changes do not require a formal plan audit or an artifact for every gate.

## Budgets and failures

Respect repository or `.ai/loop.json` budgets. For the MVP autonomous loop, focused checks should normally finish within five minutes and all validation within fifteen. Stop, checkpoint, and report the slow command when the budget is exceeded; do not keep retrying indefinitely.

Record exact commands, outcomes, and any unverified criterion in the Linear comment, pull request, or concise delivery note. Full raw logs, repeated aggregate runs, separate clean worktrees, and duplicate post-merge suites are unnecessary unless repository-specific rules demand them.

Never expose secrets in commands, logs, artifacts, comments, commits, or notifications. Do not claim completion when a required local check, review, or applicable behavior path remains unverified.
