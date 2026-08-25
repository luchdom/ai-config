# Completion Boundaries

Stop at the boundary authorized by the active entry.

| Boundary | Required outcome |
|---|---|
| `artifact` | The requested non-code artifact exists and its acceptance checks pass. |
| `working-tree` | Scoped changes and required local checks are complete; no Git publication is implied. |
| `commit` | Working-tree requirements pass and an authorized scoped commit exists. |
| `pr` | The branch is pushed and one pull request exists. |
| `merge` | Required local checks, applicable UI design conformance, one code review, and applicable QA pass; the authorized PR is merged into the configured default branch. |

`$goal-to-delivery` defaults to `working-tree`. `$spec-driven-delivery` requires a separate named stage for Commit, PR, and Merge. `$linear-delivery-loop` targets `merge` for code and `artifact` for non-code work.

Read-only Git inspection is allowed unless repository guidance is stricter. Implementation authority does not imply commit, push, PR, merge, provider settings, force-push, history rewrite, direct default-branch push, unrelated changes, or destructive cleanup.

For `merge`, validate the PR head locally before merging and verify the provider reports the PR merged into the configured default branch. A second full validation in a clean post-merge worktree is not required unless repository-specific rules explicitly require it.

A linked issue remains active through implementation and in review while its PR is open. Move it to Done only after its actual completion boundary is observed. A checkpoint, notification, or passing hosted check is not completion.
