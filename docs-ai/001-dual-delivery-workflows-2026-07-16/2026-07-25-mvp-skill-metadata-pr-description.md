# Overview

Refresh the three delivery skills' UI metadata so explicit invocation describes the current MVP workflows instead of retired adapter behavior.

# Changes

- Describe goal delivery as semi-autonomous and completion-boundary aware.
- Describe spec-driven delivery as a single manually selected stage.
- Describe the Linear loop as one repository-local MVP iteration.

# Security Impact

- No runtime, credential, permission, or network behavior changes.

# Testing

- `quick_validate.py` passed for all three skills.
- `python scripts/build.py` passed.
- `python -m unittest tests.test_delivery_contracts` passed (13 tests).
- Testing in environment: sync Codex, invoke each `$skill-name`, and confirm the displayed prompt matches its workflow and does not use retired adapter terminology.

# Related Work

- SAAS-52
