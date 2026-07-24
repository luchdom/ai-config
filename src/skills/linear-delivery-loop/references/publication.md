# Deterministic publication and exact-SHA recovery

This reference owns the fixture-first Git/GitHub publication engine used by `$linear-delivery-loop`. Cross-tool gate and completion policy remains canonical in the sibling [`goal-to-delivery` references](../../goal-to-delivery/references/quality-gates.md). Live provider activation is not part of this package.

## Contained Git preparation

The engine snapshots the registered physical issue worktree and pre-existing changes. A specialist supplies only a proposed real-file manifest. The engine rejects conflict state, overlap with pre-existing work, unexpected or unrelated paths, and any manifest-to-diff disagreement. It runs the trusted repository aggregate in the issue worktree before staging, then stages only the reconciled paths. This early check does not replace the later clean isolated exact-head gate.

`PreparePublication` is the sole public preparation transition. Its manifest and pre-existing-path inventory are inputs to reconciliation, never proof of success. The engine creates and reads back the primary branch and commit, persists exact base/head SHAs plus manifest and aggregate digests, and issues the pre-staging attestation. Merge rejects a publication without this engine-owned record.

Primary branches are `codex/SAAS-<N>-<slug>` and target `main`. Post-merge repair alone may use `codex/SAAS-<N>-repair-<attempt>`, numbered 1 through 3 and created from current `main`. Direct-main push, force, rebase, tag/release, arbitrary shell, settings or secret mutation, bypass/admin merge, and auto-revert have no engine capability.

## Provider operations and refusal

The injected provider port contains only remote-ref read/push, pull-request create-or-reuse/readback, and squash-merge request/readback. Every mutation is bound to an immutable operation ID/idempotency key and exact head. Readback occurs before and after the mutation, so replay, timeout, or response ambiguity cannot duplicate a push, PR, or merge. Raw provider responses and credentials are never persisted; durable evidence uses redacted digests.

Refusal persistence is a closed typed record. HTTP status is an integer from 100 through 599, retry delay is an integer from 0 through 1800 seconds, reconciliation flags are booleans, codes use the fixed refusal vocabulary, SHAs are exact lowercase full identities, and base ref is exactly `main`. Every mismatch is omitted or canonicalized to `unclassified`. Bodies, nested diagnostics, actor/request metadata, URLs, credentials, cookies, arbitrary provider strings, and out-of-range values are discarded before any sidecar write.

A refusal is transient only for an explicit `429`, provider `5xx`/unavailable result, or temporary mergeability response when readback proves non-application. The initial attempt is separate from retries 1, 2, and 3. Those retries wait 5, 15, and 30 minutes respectively, or a provider `Retry-After` capped at 30 minutes. Reconciliation precedes every retry. The first refusal after retry 3 becomes a stable pause.

Transient wait and pause preserve the ordinary state (`In Progress` before a PR, `In Review` after), `autonomous`, global WIP, reservation, persistent worktree, branch, optional PR, and evidence. Only the run lease is released. Stable, exhausted, ambiguous, permission, policy, required-check, protection/ruleset, merge-queue, and unclassified refusal add `blocked + needs-human`, update one durable Linear request, and emit one idempotent redacted ntfy event.

Paused publication never retries automatically. The configured owner must reply exactly:

```text
RETRY-PUBLICATION <operation-id> <head-sha>
```

Before consuming that reply once, the engine independently rereads issue state/labels/authorization, reservation and physical worktree, operation journal, branch/PR/head/base/mergeability, all SHA-bound attestations, and the latest provider response/readback. At most one idempotent operation follows. Changed or ambiguous evidence remains paused on the same request. Success clears `blocked` and `needs-human` and resumes the preserved stage.

If the attended provider call crashes, the engine independently reconciles whether it applied and durably reconstructs the exact continuation phase: `pushed`, `pr-open` plus PR identity, or `merged` plus merge SHA/readback. Proven non-application remains protected `paused + ambiguous`. A consumed attended reply cannot enter generic automatic recovery, so a later recovery command cannot cause a second provider call.

## Exact-SHA evidence and convergence

Plan, tasks, audit, review, QA, and completion drafts must exist before final gating. Design is also required when the canonical stage requires it; otherwise an explicit validated not-required record is mandatory. Review and applicable QA bind to the executable SHA.

The provider-observed PR head is validated in a fresh contained worktree. For `ai-config`, the fixed no-shell aggregate is `python .\scripts\validate.py`. The attestation records repository/worktree identity, exact SHA, redacted argv digest, tool version, timestamps, exit code, and clean-before/after observations. Missing configuration/evidence, identity or SHA drift, dirtiness, or command failure fails closed. Hosted checks are never discovered, queried, polled, waited on, budgeted, or accepted as authority.

Only a strict path-and-text classifier may authorize one evidence-only finalization commit, and only classifier-returned files are staged. Finalization is post-PR: the engine first validates a complete digest-bound draft inventory for plan, tasks, audit, review, QA, completion, and the required design record (or an exact not-required declaration) from the prepared Git head. The local finalization commit is persisted before provider binding; the provider is expected to remain on the prior head until a fresh push. Publication then re-enters push and PR readback under fresh immutable operation identities, binds the provider-observed final head, and only then permits final-head gates. The engine reruns final-head docs, aggregate, and review. QA reruns or supplies a named two-SHA reuse attestation proving no behavioral effect. A second finalization commit, non-convergent delta, executable/ambiguous delta, or head mismatch fails closed. Terminal supervisor/Linear identities are then recorded without another branch mutation.

Evidence finalization is a closed mode of `RecordPublicationAttestation`: callers provide candidate evidence paths, not pass fields. The engine reads current and prior Git content, proves the exact draft-to-pass-only delta, stages the classifier result, commits once, reads back the new head, and persists the finalization identity. Convergence can be attested only after this record exists.

## Merge and repair

Immediately before squash merge, the engine rereads stop/authority/reservation/lease, PR/base/head/mergeability, and every exact-head attestation. Base drift is incorporated with a normal merge of `origin/main`; rebase and force are forbidden, and affected gates rerun. The exact returned squash-merge SHA must equal provider readback. A separate fresh worktree validates that SHA cleanly before completion or reservation release. No post-merge repository mutation or completion commit is allowed.

The readback includes the full base SHA, not only `main`. It is compared with the preparation-attested base immediately before merge. Drift enters an explicit resumable `base-drift` phase and returns without calling squash merge. A later public preparation operation performs only the contained `git merge --no-ff --no-edit origin/main`, commits and reads back the reconciled manifest under a new immutable operation identity, clears old provider operation identities and affected aggregate/review/QA/docs/convergence/finalization evidence, then requires push, PR readback, and every final-head gate to be rebound before merge.

A failed post-merge aggregate keeps the same issue in `In Review`. Each numbered repair re-enters the complete pipeline. The public repair command accepts only the manifest and pre-existing-path inventory; the engine owns reconciliation, pre-staging aggregate, scoped staging, commit, and readback. It then requires isolated exact repair-head aggregate, independent review, applicable QA, docs/evidence convergence, merge readback, and clean exact returned repair-merge-SHA aggregate. Missing, stale, or wrong-head evidence blocks merge/completion. After three attempts, the issue moves to `Backlog + needs-human`, preserves evidence, updates the same request, and emits idempotent ntfy. The engine never auto-reverts or creates a speculative issue.

Primary preparation, evidence finalization, base-drift preparation, and repair preparation commits carry immutable operation trailers. If the process stops after Git commits but before supervisor state is written, schema-valid replay of the exact pending command proves the original consumed authorization, reconciles current supervisor/reservation revisions, verifies exact commit paths/trailers/readback, and converges state without a second Git mutation.

Git status reconciliation consumes raw NUL porcelain without stripping its semantic leading status column. Rename/copy records are recognized in either index or worktree status column; both NUL path fields are validated, and Windows separators are normalized before manifest comparison.

Rollback is a reviewed code change. Preserve supervisor state, journals, reservations, worktrees, branches/PRs, and provider-paused evidence; never delete protected state to escape ambiguity.
