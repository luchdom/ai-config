# Deterministic publication and exact-SHA gates

## Overview

Make local delivery publication deterministic and fail closed across branch preparation, GitHub provider operations, exact-SHA validation, attended recovery, and bounded post-merge repair.

## Changes

- Add a durable publication state machine and public supervisor commands for preparation, push, PR, evidence finalization, merge, recovery, and repair.
- Bind every mutation and attestation to the workflow, issue, reservation, worktree, operation, revision, and exact Git SHA.
- Add injected Git/provider adapters with idempotent readback and no live-provider authority in fixtures.
- Add strict control-plane reply watermarks with a one-time `1.0` to `1.1` migration.
- Document publication behavior, recovery boundaries, exact-SHA gates, and harness coverage.

## Security Impact

- Provider refusal, stale authority, ambiguous readback, base drift, replay, and mismatched evidence fail closed.
- The implementation exposes no hosted-check, provider-settings, bypass, direct-main, force, rebase, tag, release, auto-revert, arbitrary-shell, or live-provider authority.
- Tests use disposable repositories and injected local fixtures; they do not mutate live GitHub, Linear, or ntfy state.

## Testing

- Automated: `python -u .\scripts\validate.py` passed build generation, marker-sync regressions, and all 308 tests in 6174.872 seconds.
- Testing in environment: from the repository root, run `python -u .\scripts\validate.py` and expect exit code `0` with the complete fixture-backed publication, recovery, exact-SHA, merge, and repair suite reporting `OK`.
- No feature flag or live credential is required; the supported verification path is local and transport-free.

## Related Work

- Linear: SAAS-48
- Completion boundary: squash-merged to `main`, followed by validation of the exact returned merge SHA.
