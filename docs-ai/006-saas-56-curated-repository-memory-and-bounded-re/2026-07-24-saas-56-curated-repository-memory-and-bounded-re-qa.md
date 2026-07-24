# SAAS-56 curated repository memory and bounded retrieval — Runtime QA

## Verdict

**PASS (focused runtime QA): 32 passed, 0 failed, 0 blocked.** No defect was observed in the current uncommitted SAAS-56 implementation. The repository aggregate was intentionally not run by this QA pass because the parent delivery agent was already running that required command; its result is not represented as QA evidence here.

## Target identity

- Verified at `2026-07-24T11:25:01-03:00` in the registered `ai-config` worktree.
- Git base `HEAD`: `1a5190f1815ae25b0a3cba6e81b50ae221c62052` (`main`).
- Target: the dirty, uncommitted working tree containing the SAAS-56 memory sources, schemas, docs, focused fixtures, and related tracked edits. This is a working-tree target, not a clean exact PR-head/SHA gate.
- Runtime: Python `3.12.0`; Git `2.47.1.windows.2`.
- Inputs read: `AGENTS.md`, `README.md`, registered `workflow.json`, plan, tasks, re-audit 3, code-review 3, the repository-memory runbook, and the canonical QA/quality-gate contracts.

## Commands and results

| Command | Result | Duration |
| --- | --- | ---: |
| `python -m unittest discover -s tests\linear_delivery_repository_memory -t . -v` | PASS — 32 tests | 420.469 s |

The suite uses per-test `TemporaryDirectory` repositories/state homes, bounded subprocess timeouts (30–45 seconds), and process cleanup via test completion. It exercises the public direct-script request surface with a distinct disposable request file and state home; no production repository, credential, port, provider, or external service was used.

## Acceptance mapping

| Acceptance criterion | Observed runtime evidence | Result |
| --- | --- | --- |
| Completed workflows can propose candidates only; no unreviewed direct promotion. | `test_current_delivery_source_requires_registry_identity_while_legacy_null_is_explicit`, exact scope/duplicate refusal, and authenticated promotion fixtures reject invalid current provenance before authority consumption. | PASS |
| Approved promotion is idempotent, versioned, repository-scoped, redacted, and preserves superseded history. | Marker-last atomic batch/replay, 32-candidate batch, no-candidate, authority fault, process termination, cross-process contender, forward supersession, invalid-marker/orphan fixtures passed. | PASS |
| Retrieval is deterministic and bounded by scope and provenance. | Repeat filter/rank/provenance test returned stable ordered items; min-budget whole-item omission, source-drift exclusion, and query/rebuild/repair CLI paths passed. | PASS |
| Raw history/chat/Linear/model prose is not implicitly trusted or bulk-loaded. | Public CLI only accepted strict request payloads; context fixture carried malicious text solely in escaped `repository_memory_context` tool data and asserted it cannot close the tool boundary. | PASS |
| Memory never grants workflow, mutation, provider, product, or security authority. | Raw selector mapping was rejected as non-authentication; promotion requires engine-owned authorization; status leaves the operation union unchanged and context only admits supported authenticated stages. | PASS |
| Invalid, secret-like, stale, corrupt, cross-repository, path-alias, and over-budget inputs fail closed or are excluded. | Secret/open-field, source-drift, corrupt/cross-repository index, hard-link/reparse, cross-state assembly, unsupported stage, and wrapper-budget tests passed. | PASS |
| Manual, semi-autonomous, and autonomous entries retain their advancement/clarification policy. | Fixture-backed current/explicit legacy provenance and engine-authenticated selector checks passed; no test evidence shows a memory path broadening the supervisor command union or authority. | PASS |
| Focused fixtures, projections, docs, and aggregate pass at exact PR head and merge SHA. | Focused projection/runtime fixtures passed. Exact clean PR-head, generated-projection/docs, aggregate, merge, and post-merge-SHA evidence were outside this dirty-working-tree QA scope and remain unverified here. | UNVERIFIED |

## Behavioral highlights

- The direct executable script flow invoked `cli.py --repository-memory-request` in isolated subprocesses for `query`, `rebuild`, `repair`, and authenticated `context`; each returned JSON successfully. The ordinary `cli.py --request` Status and AuthorizeMutation dispatch paths also succeeded without relative-import failure.
- Crash/replay evidence covered termination immediately after prepared authority evidence: no record or marker became visible before a subsequent authoritative retry. Concurrent in-process and cross-process contenders converged on one committed result.
- Marker/index recovery, stale/corrupt index observation without status mutation, deterministic ranking/provenance, lifecycle/supersession, accounting digit boundaries, and hard-link/reparse/cross-state isolation all passed.

## Cleanup, blockers, and residual risk

- Cleanup: all exercised data lived under test-owned temporary directories; the suite exited 0 and left no requested production mutation. This QA artifact is the only file created by this pass.
- Blockers: none for focused runtime QA.
- Residual risk: the target is an uncommitted dirty worktree; `python .\scripts\validate.py`, generated `dist/` verification, documentation gate, exact clean provider-head gate, and exact returned merge-SHA gate are not verified by this report. The parent-owned aggregate must be recorded separately before any advancement.
