# Discovery Order

## Step 1

Read `AGENTS.md`.

## Step 2

Identify the feature area and likely stack:

- frontend UI
- backend service
- shared library
- infrastructure or configuration

## Step 3

Read the smallest relevant documentation set:

- `/docs` files closest to the task
- top-level `README` when it explains app structure or commands
- nearby feature docs if present

## Step 4

Find the nearest code pattern:

- same feature area first
- same layer second
- shared abstraction third

## Step 5

Find the nearest tests:

- unit tests for logic-heavy work
- component or e2e tests for UI work
- integration tests for service boundaries

## Step 6

Return only the patterns, files, and constraints that matter for the task at hand.
