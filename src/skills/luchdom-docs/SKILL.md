---
name: luchdom-docs
description: Apply Luchdom repository-specific documentation ownership when architecture, workflow, setup, tooling, validation, tracking, or operations change. Use with docs-as-code to update the nearest durable source without duplicating the canonical shared delivery protocol.
---

# Luchdom Docs

Apply `$docs-as-code` with the Luchdom documentation ownership map.

1. Read repository `AGENTS.md`, `README.md`, and the smallest relevant curated docs set.
2. Inspect the implemented change and approved artifacts from the exact registered `docs-ai/<work-key>-<slug>/` folder. Accept an explicitly supplied numbered-and-dated folder or flat artifact only as historical read fallback and never rewrite it.
3. Use [doc-targets.md](./references/doc-targets.md) to select the existing source of truth.
4. Update that source and remove contradictions instead of adding another explanation.
5. Link the canonical `$goal-to-delivery` protocol when shared workflow behavior must be referenced; keep only repository-specific commands, domain rules, definitions of done, and stricter constraints locally.
6. Run the available local docs/drift checks and report exact pages, checks, and gaps.

Do not put reusable guidance only in `docs-ai/`; that tree is per-work evidence. Do not add full workflow records to curated navigation. Prefer concise task-oriented how-tos with prerequisites, steps, verification, rollback, and troubleshooting.

If documentation and implementation disagree and the correct source cannot be proven, report the conflict and fail the docs stage rather than choosing silently.
