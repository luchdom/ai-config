---
name: repo-discovery
description: Build repo context quickly by reading AGENTS.md, docs, and existing code patterns before planning or implementation. Use when Codex needs to discover relevant files, conventions, component patterns, architecture paths, tests, or source-of-truth docs and cite the exact paths consulted.
---

# Repo Discovery

Build only the context needed for the current task. Find the governing docs, the nearest implementation pattern, and the exact files that matter before planning or coding.

## Discovery Workflow

1. Read `AGENTS.md` first.
2. Identify the task area: frontend, backend, shared, infrastructure, or mixed.
3. Read the smallest relevant subset of `/docs`, `README`, and nearby feature docs.
4. Find the closest existing implementation pattern in code.
5. Find the tests nearest to that pattern.
6. Return a concise summary with exact source paths and open questions.

## Discovery Rules

- Prefer nearest-neighbor patterns over broad repo surveys.
- Do not summarize the whole repo when only one area matters.
- Do not claim a convention without citing a file path.
- Distinguish documented rules from inferred patterns.
- Stop and surface conflicts when docs and code disagree.

## Deliverable

Summarize:

- Relevant docs and why they matter
- Existing code paths to copy or extend
- Tests or fixtures that show the expected style
- Open questions or conflicting conventions
- Sources consulted (paths)

Read [references/discovery-order.md](./references/discovery-order.md) for the step order and search priorities. Read [references/discovery-summary-template.md](./references/discovery-summary-template.md) when writing the final context summary.
