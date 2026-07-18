---
name: ui-review-spec
description: Analyze existing product screens and flows, identify UX/UI improvements, and produce an implementer-ready design spec using current repository components first. Use for the design stage after a workflow has a registered artifact folder.
---

# UI Review Spec

Turn current-product evidence into the registered workflow's design artifact. The caller entry controls advancement.

## Workflow

1. Read `AGENTS.md`, the registered plan, and the smallest relevant docs set.
2. Inspect the current screen with an available real-browser tool. Fall back to screenshots/images only when interactive inspection is impossible and state the limitation.
3. Find existing components and design-system patterns before proposing changes.
4. Prefer existing repository components, then approved library primitives, then justified new components.
5. Cover responsive behavior, accessibility, keyboard/focus, loading, empty, error, success, disabled, and validation states where relevant.
6. Write `<date>-<slug>-design.md` to the exact registered `docs-ai/<work-key>-<slug>/` folder using [spec-template.md](./references/spec-template.md).

Do not allocate folders or invent work keys. An explicitly supplied numbered-and-dated folder or flat artifact is historical read fallback only; never rename, rewrite, or add synthetic identity metadata to it.

Do not implement, advance stages, or resolve a material product decision without the caller's clarification policy. Cite exact paths/tools and tie every recommendation to the user goal and observed current behavior.

Read [ui-audit-checklist.md](./references/ui-audit-checklist.md) for review coverage and [component-selection.md](./references/component-selection.md) for component choice.
