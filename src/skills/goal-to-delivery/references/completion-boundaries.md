# Completion Boundaries

Protocol version: `2.0`

Completion and publication are separate. Stop exactly at the active entry's declared boundary.

| Boundary | Required outcome |
|---|---|
| `artifact` | The accepted non-code/spec/document output exists and its acceptance checks pass. |
| `working-tree` | Scoped implementation, tests, review, applicable QA, and docs are complete in the current worktree; no Git mutation is implied. |
| `commit` | Working-tree gates pass and an explicitly authorized scoped local commit exists. |
| `pr` | Commit gates pass, the branch is pushed, one PR exists, and linked tracking may enter review. |
| `merge` | Exact-head gates pass, authorized squash merge occurs, and the exact returned merge SHA passes the repository clean local post-merge gate. |

A failed exact returned-merge-SHA gate is not completion. Keep the same work identity and protected publication state, and follow the repository's bounded repair policy. Every repair reruns all applicable exact-head, review, QA, docs/evidence, merge-readback, and exact-merge-SHA gates; repair exhaustion requires attended recovery and never authorizes auto-revert.

`$goal-to-delivery` defaults to `working-tree`; a later explicit grant resumes the same work rather than recreating it. `$spec-driven-delivery` never infers stages from a boundary: `Commit`, `PR`, and `Merge` remain separate invocations. Autonomous code always targets `merge`; manual operational evidence never creates an artificial branch or PR.

## Authority

Read-only Git inspection is allowed unless repository guidance is stricter. Repository edits require the active entry/stage and a valid editing reservation. Branch, stage, commit, push, PR, merge, provider settings, or tracking mutations are not implied by implementation.

Semi-autonomous publication requires an explicit boundary or later grant. Manual publication requires each named action. Autonomous Git/provider mutation belongs only to deterministic adapter code while its prepared capability remains valid; specialists return proposals and manifests.

Never infer force-push, history rewrite, direct default-branch push, unrelated changes, tags/releases, provider-setting changes, bypass/admin merge, destructive cleanup, or automatic revert.

## Linked tracking and reservation

- Planning-only stages preserve backlog/todo tracking and may defer an editing reservation while writing only isolated workflow artifacts.
- Working-tree or commit code remains active and retains its repository reservation until explicit Release, valid workflow-managed Handoff, publication/merge progression, or reconciled abandon.
- A PR-linked issue remains in review and retains repository/tracking WIP through merge or deterministic release.
- Validated merge may complete linked code only after exact-merge-SHA evidence is durably recorded.
- Explicit Release never discards dirty, unmerged, open-PR, inaccessible, or ambiguous work and never silently restores autonomous eligibility.

Reservation expiry alone never releases protected work. Native Codex **Hand off** does not transfer a reservation or workflow authority.
