# Worktree Policy

This is the canonical cross-tool policy for creating, resuming, and removing linked Git worktrees. Repository-local instructions may prohibit worktrees or impose stricter checks; those rules win. This policy does not grant authority by itself.

## Establish creation authority before mutation

A persistent worktree and its branch may be created only when one of these sources unambiguously authorizes creation for the current work:

- a direct owner instruction for the current request that explicitly requires or permits a worktree in the named repository and scope; or
- an explicitly invoked delivery entry or stricter repository policy that expressly grants automatic worktree creation for the current work item.

A plan, task file, proposed branch, `working-tree` completion boundary, available directory, or implementer convenience is not authority. Before creating a branch, directory, or registration, record and reconcile all of:

- the canonical repository root and Git common directory;
- the work key or task identity;
- the fetched remote ref as provenance and the exact resolved base commit as a full object ID;
- the branch name;
- the normalized worktree leaf and derived absolute target; and
- the permitted `git worktree add` operation.

Missing, stale, or mismatched creation authority fails closed before `git worktree add`, branch creation, or target mutation. Continue in the canonical checkout only when its instructions and state permit that; otherwise request an owner decision.

## Resolve and validate the target

1. Resolve the Git common directory and confirm the main worktree through `git worktree list --porcelain -z`. An invocation from a linked worktree must still select the main worktree root.
2. Derive exactly `<main-worktree-root>/.ai/worktrees/<safe-worktree-name>`. Never place the target beneath the invoking linked worktree.
3. Use one normalized work-key or branch slug as the leaf. Reject absolute input, traversal, path separators, empty or dot names, Windows reserved names, trailing dots or spaces, and any value that does not remain one child after normalization.
4. Resolve every existing ancestor without following a reparse-point escape. Reject a reparse traversal or any target whose resolved parent is not the exact main-root `.ai/worktrees` directory.
5. Verify the effective ignore rule before creation with `git check-ignore -v --no-index` against a probe below the exact target. The expected global rule is `/.ai/worktrees/`; `.ai/loop.json` must remain unignored.
6. Fetch the intended remote ref, retain that ref and fetch observation as provenance, and resolve the authorized base to a full immutable object ID. The remote ref is provenance only: never use it as the final `git worktree add` operand. Refuse an existing target, branch, or worktree registration unless all recorded path, branch, common-directory, work-identity, and base expectations describe the same resumable worktree.

Stricter repository-local no-worktree rules take precedence at every step.

## Create or resume

Immediately before execution, reconcile the current repository, common directory, work identity, exact resolved base commit, branch, derived path, and command with the authority record. Bind the recorded full commit SHA into the imminent command; do not re-resolve or substitute the movable remote ref during mutation. Create only with a non-forcing operation equivalent to:

```text
git worktree add -b <branch> <exact-path> <resolved-base-commit>
```

If the fetched remote ref advances after authority is recorded, that movement must never change the command operand: create from the already authorized resolved commit, or, when stricter repository policy requires a fresh tip, invalidate authority and refuse before branch, path, or worktree mutation.

Never use `--force` to bypass branch, path, or registration safety. After creation, verify the registered path and branch, exact HEAD, Git common directory, containment below the main root, effective ignore, and parent repository status.

When the exact target is already registered, resume it only if every bound identity, path, branch, and common-directory check matches. Do not allocate a sibling or silently repurpose a collision; fail closed on any mismatch.

## Removal and cleanup

Creation authority never implies removal authority. Outside a disposable QA fixture whose test contract explicitly owns both its creation and exact cleanup, removal requires a separate direct owner instruction or explicitly invoked repository/workflow policy that names the exact registered worktree and grants its removal.

Immediately before `git worktree remove`, reconcile that removal authority and verify:

- the exact registered path, branch, and Git common directory;
- clean tracked and untracked state;
- merged status or an explicit disposition for unmerged work;
- no open process is using the worktree; and
- the resolved path is still the exact authorized target.

Missing, stale, or mismatched removal authority preserves the worktree and reports cleanup pending. Use `git worktree remove <exact-path>` only after all checks pass; never recursively delete `.ai/worktrees` or a registered worktree. A disposable fixture's cleanup authority cannot authorize a user or production worktree.

Parent-level `git clean -x` includes ignored paths and can destroy nested worktrees. Shared automation must warn about this hazard and must never run a destructive parent clean as worktree cleanup.
