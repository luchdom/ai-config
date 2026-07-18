---
name: pr-description
description: Draft or review pull request titles and descriptions. Use when Codex is asked to create, update, audit, or prepare PR text, especially when the repo has a .github/pull_request_template.md file, PR titles must stay concise, or reviewer-ready Testing in environment steps are required.
---

# PR Description

Draft PR text that is easy for reviewers to scan and test.

## Workflow

1. Inspect `.github/pull_request_template.md` in the target repo before drafting.
2. Use the repo template's headings and order exactly. Do not add extra sections.
3. If the repo has no PR template, use: Overview, Changes, Security Impact, Testing, Related Work.
4. Keep the PR title under 70 characters.
5. Write `<date>-<slug>-pr-description.md` to the exact registered `docs-ai/<work-key>-<slug>/` workflow folder.

Do not allocate a workflow folder or infer one from the latest directory. Accept an explicitly supplied numbered-and-dated folder or flat artifact only as historical read fallback and never rewrite or migrate it.

## Writing Rules

- Keep bullets short and concrete.
- Lead with what changed and why.
- Do not restate the diff line by line.
- Omit internal narration, including audits, stash experiments, plan history, task history, and `docs-ai/` workflow artifacts.
- Mention pre-existing or unrelated test failures in one line.

## Testing Section

- Include concrete `Testing in environment` steps a reviewer or tester can follow in Dev.
- Name flags or configuration switches to toggle when relevant.
- Name the upstream API or workflow to call.
- Include the exact request shape when an API call is part of validation.
- State expected behavior and previous behavior when the comparison matters.
- Include automated test results separately from manual Dev verification when the template has room for both.
