# Component Selection

Use this order of preference:

1. Existing repo component
2. Existing repo pattern composed from current primitives
3. MUI or shadcn primitive already approved in the stack
4. New component, only with explicit justification

## Reuse Criteria

- Prefer the closest existing component in the same feature area.
- Prefer a shared component when the same interaction appears across multiple screens.
- Prefer composition over inventing a new abstraction when the behavior is straightforward.

## New Component Criteria

Propose a new component only when at least one of these is true:

- The interaction is repeated and not represented cleanly today.
- Existing primitives create inconsistent UX or excessive one-off code.
- Accessibility or responsiveness would be materially worse with forced reuse.

## Spec Requirement

When naming a component choice, include:

- Preferred component or primitive
- Relevant repo path when it exists
- Reason the choice is better than nearby alternatives
