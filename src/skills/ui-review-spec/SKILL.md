---
name: ui-review-spec
description: Produce an implementer-ready UI design spec or a post-build rendered design-conformance review using binding repository design sources. Use for frontend/UI design gates after a workflow has a registered artifact folder.
---

# UI Review Spec

Turn current-product evidence into the registered workflow's design specification or design-conformance review. The caller entry selects the operation and controls advancement.

## Workflow

1. Read `AGENTS.md`, the registered plan, approved design, implementation manifest when present, `../goal-to-delivery/references/design-gates.md`, and the smallest relevant product/design docs set.
2. Identify binding design sources: issue-tied design artifacts or frozen references, then repository design-system docs, theme/tokens, component catalog, and established feature patterns.
3. Inspect the affected screen with an available real-browser tool. Fall back to screenshots/images only when interactive inspection is impossible and state the limitation.
4. For an initial or implementation-time design specification, find existing components and design-system patterns before proposing changes. Prefer repository components, then approved library primitives, then justified new components. Write a new dated artifact with supersession notes instead of overwriting prior design evidence.
5. For a design conformance review, inspect the exact implementation identity and compare representative routes, states, themes, content, and mobile/desktop viewports with every binding source. Do not pass runnable UI without real rendered evidence.
6. Cover responsive behavior, accessibility, keyboard/focus, loading, empty, error, success, disabled, and validation states where relevant.
7. Write `<date>-<slug>-design.md` using [spec-template.md](./references/spec-template.md), or `<date>-<slug>-design-review.md` using [design-review-template.md](./references/design-review-template.md), in the exact `artifactFolder` recorded by the active work descriptor/registry.

Do not allocate or reconstruct an artifact folder, invent a work key, or select a folder by recency or a similar slug. New/current registered work resolves under `.ai/work`; an exactly registered legacy workflow continues in its exact registered folder. Explicitly supplied unregistered or tracked historical artifacts are read-only fallback; never adopt, rename, rewrite, or add synthetic identity metadata to them.

Do not implement, perform code review, replace runtime QA, advance stages, or resolve a material product decision without the caller's clarification policy. Cite exact paths/tools and tie every recommendation or finding to the user goal, binding design sources, and observed rendered behavior.

Read [ui-audit-checklist.md](./references/ui-audit-checklist.md) for review coverage and [component-selection.md](./references/component-selection.md) for component choice.
