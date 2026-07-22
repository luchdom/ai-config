# Add Linear selection and notification control plane

## Summary

- add the fixture-first SAAS-47 Linear selection, WIP reconciliation, claim recovery, decision/follow-up, and migration control plane
- add durable ntfy attention delivery records with redaction, idempotency, and attended recovery semantics
- add strict schemas, operator documentation, and focused tests while keeping live provider activation deferred

## Validation

- `python -m unittest discover -s tests\linear_delivery_control_plane -v` — 53 passed
- supervisor contract subset — 6 passed
- `python scripts\validate.py` — 248 passed; local validation gate PASS
- independent code review — PASS, no findings
- documentation gate — PASS

## Operational notes

- No live Linear backlog migration or ntfy publish was performed.
- Credentials remain environment-only (`LINEAR_API_KEY`; optional `NTFY_URL`, `NTFY_TOPIC`, `NTFY_TOKEN`).
- SAAS-49/52/54 remain responsible for runtime integration and attended activation.

Closes SAAS-47.
