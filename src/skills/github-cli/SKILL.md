---
name: github-cli
description: Use GitHub CLI safely for repository, pull request, issue, check, and Actions inspection. Use when Codex needs `gh` setup guidance, auth checks, read-first GitHub lookups, PR descriptions, CI/check logs, or explicitly approved GitHub mutations from the terminal.
---

# GitHub CLI

Use `gh` as a local GitHub interface when connector data is unavailable, incomplete, or when CLI output is the clearest source of truth.

## Default Workflow

1. Verify the current repo and branch with read-only Git commands.
2. Check auth with `gh auth status` before any GitHub lookup.
3. Prefer read-only commands first: `gh repo view`, `gh pr view`, `gh pr diff`, `gh pr checks`, `gh run list`, `gh run view`, `gh issue view`, and `gh api` GET requests.
4. Use `$pr-description` before drafting or updating PR titles or bodies.
5. Summarize the command purpose and important output instead of pasting noisy logs.

## Safety Rules

- Do not create, edit, close, reopen, label, assign, merge, or comment on GitHub objects unless the user explicitly approves that exact action in the current conversation.
- Do not push branches, create PRs, trigger workflows, rerun jobs, or change repository settings without explicit approval.
- Preserve unrelated local changes. Read `git status --short` before any workflow that might depend on local state.
- Treat `gh api` non-GET requests as mutating actions that require explicit approval.
- Never expose tokens or secrets from `gh auth token`, environment variables, workflow logs, or API responses.

## Useful Reads

- Auth and account: `gh auth status`
- Current repository: `gh repo view --json nameWithOwner,url,defaultBranchRef`
- Pull request: `gh pr view <number> --json title,body,state,author,headRefName,baseRefName,files,reviews,comments`
- Pull request checks: `gh pr checks <number>`
- Failed workflow logs: `gh run view <run-id> --log-failed`
- Issue: `gh issue view <number> --json title,body,state,author,labels,comments`

## Setup

If `gh` is missing or unauthenticated, use `docs/external-tools.md` for install and login guidance. Do not invent install commands when the repo docs already define the supported path.
