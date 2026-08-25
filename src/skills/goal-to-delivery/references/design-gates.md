# Frontend And UI Design Gates

Use these gates for work that changes a rendered screen, user flow, navigation, layout, component choice, interaction, responsive behavior, accessibility behavior, UI state presentation, visual styling, design token, or content hierarchy.

## Binding design sources

Before making a UI decision, identify the applicable repository sources in this order:

1. repository instructions and product-specific design rules;
2. an issue-tied approved design spec or frozen visual reference;
3. the repository design system, theme, tokens, component catalog, and established feature patterns;
4. approved framework or component-library primitives.

Record the exact paths or tools consulted. A stricter repository rule wins. If binding sources conflict and repository precedent does not resolve the conflict, stop for clarification. Do not silently replace an existing design system with personal preference or a new visual direction.

A frozen reference is an acceptance oracle, not inspiration. Compare the implementation at the same viewport, state, content, and theme. Record any unavoidable deviation instead of redesigning it.

## Before implementation

The planner records whether the work changes rendered UI and whether a design specification is required.

A product-designer design specification is required when any of these conditions apply:

- a screen, flow, navigation path, layout, component composition, interaction, responsive rule, accessibility behavior, state presentation, visual style, or content hierarchy is added or changed;
- the implementer would need to choose between plausible UI behaviors or visual treatments;
- a new component, primitive, token, pattern, or exception to the existing design system is proposed;
- the available product/design sources are missing, ambiguous, conflicting, or do not cover the requested state;
- the user explicitly requests UI/UX design, review, redesign, fidelity, or design-system alignment.

A new design specification may be marked not required only for a mechanical change whose UI decisions are fully dictated by a binding source. Examples are an exact copy correction inside unchanged structure, a test-selector change, or restoring already documented behavior without changing component choice, layout, styling, interaction, responsiveness, state presentation, or accessibility. Record the exact binding source and reason; the absence of a design spec is not itself a reason.

Tasking, audit, and implementation must stop when a required design specification is missing or a material design decision remains unresolved.

## During implementation

The implementer reads the recorded design-gate decision, binding design sources, and approved design specification before editing UI code. Implement the specified components and tokens. Do not add one-off styling, a new primitive, or a visual/interaction deviation that the approved artifacts do not authorize.

When implementation exposes an uncovered UI decision or makes the approved direction impractical, return it to product-designer or planner clarification. Do not redesign in code.

Exercise the affected UI in a real browser during implementation when the environment permits it. Return the exact routes, states, themes, and representative viewports needed for conformance review. Keep optional screenshots in disposable evidence storage unless the user or registered workflow explicitly requires another destination.

## After implementation

A product-designer design conformance review is required for every change to rendered UI or interaction, including mechanical changes that did not need a new design specification.

The product-designer inspects the exact implementation identity in a real browser and compares the affected routes, states, themes, and representative mobile and desktop viewports against the binding design sources and approved specification. The result is a dated `*-design-review.md` with `PASS` or `FAIL`, exact evidence, deviations, and required corrections.

The review cannot pass from source code, compilation, unit tests, or screenshots alone when the affected UI can be run. If real rendering is unavailable, record the limitation and leave visual or interaction conformance unverified. Any unresolved mismatch with a binding design source or approved acceptance criterion produces `FAIL`; optional improvements remain advisory and do not fail conforming work.

An implementation change that affects rendered output invalidates the previous design-review result. Route a failed result to the implementer, then rerun the affected conformance review. This gate does not replace code review, accessibility/runtime QA, or repository validation.
