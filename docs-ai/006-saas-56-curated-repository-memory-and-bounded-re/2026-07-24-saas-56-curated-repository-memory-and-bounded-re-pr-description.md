# feat: add curated repository memory

## Overview

Adds deterministic, repository-local curated memory so delivery workflows can promote reviewed knowledge and retrieve only a bounded, provenance-rich subset without granting authority.

## Changes

- Adds strict schemas and canonical digest projections for records, promotion batches, commit markers, indexes, queries, results, and context envelopes.
- Adds marker-last atomic promotion, crash/replay recovery, marker-derived rebuild/repair, lifecycle/conflict handling, and bounded deterministic retrieval.
- Adds opt-in escaped tool-role context, observation-only status, direct CLI operations, durable documentation, and generated projection parity.

## Security Impact

- Promotion consumes engine-owned reservation authorization and validates registered workflow, repository, head, worktree, source, and attestation bindings.
- Memory cannot grant workflow, provider, product, security, or mutation authority; secret-like content, path aliases, malformed records, stale sources, and cross-repository state fail closed.
- No network service, embeddings, or external vector database is introduced.

## Testing

- Automated: `python .\scripts\validate.py` — PASS; generated adapters, sync regressions, and 340 tests.
- Focused runtime QA: 32 repository-memory tests PASS.
- Testing in environment:
  1. Run `python src\skills\linear-delivery-loop\scripts\cli.py --memory-request <absolute-query-json>` with a valid repository-bound query and expect stable ordered items plus provenance within the requested caps.
  2. Run the same command with `repository-memory-rebuild`, then repeat the query and expect byte-identical semantic results.
  3. Request `repository-memory-context` for planner, implementer, reviewer, or QA and expect one fixed developer message plus one escaped tool-role envelope; spoofed selectors or undersized wrapper budgets must fail closed.

## Related Work

- Linear: SAAS-56
- Parent program: SAAS-44
