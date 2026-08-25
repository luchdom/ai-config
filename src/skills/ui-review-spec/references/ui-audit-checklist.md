# UI Audit Checklist

## User Goal

- State the primary user task.
- State the secondary tasks on the same screen.
- Note any critical business or technical constraints already documented.

## Binding Design Sources

- Identify issue-tied design specs or frozen references.
- Identify repository design-system docs, theme, tokens, component catalog, and closest feature patterns.
- Record source precedence and stop when binding sources conflict.

## Information Hierarchy

- Check whether the page title, primary action, and supporting context are obvious.
- Check whether visual weight matches task importance.
- Check whether related controls and content are grouped clearly.

## Layout And Density

- Check spacing consistency.
- Check alignment and scanability.
- Check whether dense tables or forms still preserve readability.
- Check whether the default viewport shows the most important content without unnecessary scrolling.

## Components And States

- Map every changed element to an existing component and token when available.
- Flag one-off styling, duplicated primitives, and unauthorized design-system exceptions.
- Check default, hover, focus, active, disabled, loading, empty, error, and success states.
- Check whether status feedback is timely and understandable.
- Check whether forms show validation close to the affected field.

## Accessibility

- Check semantics, labels, and focus order.
- Check keyboard reachability for all important actions.
- Check contrast and readable type sizes.
- Check whether screen-reader names are likely to be clear.

## Responsive Behavior

- Check mobile and desktop layouts.
- Check overflow, truncation, and long-text handling.
- Check whether actions stay discoverable when space shrinks.

## Conformance Evidence

- Inspect the exact implementation identity when reviewing built work.
- Compare the same route, state, theme, content, and viewport required by a frozen reference.
- Treat source-only or screenshot-only evidence as a limitation when runnable UI is available.
- Separate required corrections from optional improvements.

## Decision Rule

Recommend only changes that clearly improve comprehension, efficiency, accessibility, or confidence for the user.
