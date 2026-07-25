# Clarification Policy

A safe assumption is reversible, conservative, dependency-free, behavior-preserving, and supported by repository precedent. Record only assumptions that materially help a later reviewer or run.

A material decision includes authentication or authorization behavior, tenant isolation, privacy, billing, destructive data changes, recurring external cost, vendor lock-in, production operations, materially different UX directions, conflicting requirements, or scope that no longer fits one reviewable goal.

Ask one focused question with two or three options, consequences, and a recommendation.

- Semi-autonomous work may use safe assumptions and asks the user directly for material decisions.
- Manual `Clarify` asks the user and returns control without advancing.
- Autonomous work keeps the issue active, adds the configured human-decision label, posts the structured question in Linear, sends at most one best-effort notification, and stops. A later run may resume only from a newer owner reply matching `DECIDE <ISSUE> <OPTION>`.

Linear is the durable decision record for autonomous work. Conversation text, issue labels alone, and model output do not resolve a material decision. Never put secrets in questions, comments, or notifications.
