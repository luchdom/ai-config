# Quality Gates

Protocol version: `2.0`

Use repository-owned local commands and acceptance paths. Do not invent a generic remote quality requirement or treat provider status as evidence.

## Distinct gates

### Independent plan audit

The `auditor` rereads the requirement and repository sources, then challenges the plan, design, and task breakdown before implementation. It writes only the audit artifact. It does not implement, review code, run acceptance QA as a substitute, or produce the tasks it judges.

### Code review

The `code-reviewer` examines the exact implemented diff/head against acceptance criteria, repository conventions, security/tenant boundaries, failure behavior, and test adequacy. It writes findings and a verdict. It does not fix code or replace the plan audit or runtime QA.

### Runtime QA

The `qa` verifier maps every acceptance criterion to observed behavior. Run the smallest relevant repository checks first, then the full required local aggregate. Exercise real HTTP/browser/CLI behavior when the criterion is behavioral, with isolated disposable data and cleanup. QA reports defects and does not fix production code by default.

### Documentation

`$docs-as-code` updates the nearest durable docs or records an explicit no-impact reason. Verify commands, links, navigation, and the repository's local docs gate. Documentation does not substitute for review or QA.

## Evidence

Record the observed source/head identity, exact commands and arguments, exit codes, relevant tool versions, clean status when required, timestamps, redacted evidence locations, and acceptance-to-evidence mapping. A missing command, dirty or mismatched target, incomplete behavioral path, or ambiguous identity fails the relevant gate.

For a `merge` boundary, run exact-head local validation/review/applicable QA before squash merge and rerun the repository aggregate from a separate clean worktree at the exact returned merge SHA. Repository guidance owns the actual commands and any stricter requirements.

Before staging a publication manifest, run the trusted aggregate in the registered issue worktree as early feedback. After provider readback, the later exact-head gate remains mandatory in a fresh clean worktree. Required delivery drafts include conditional design evidence or an explicit validated not-required record. Only a proven evidence-only delta may receive one classifier-scoped finalization commit; reread the provider head and rerun final-head docs, aggregate, and review, plus QA or an explicit named safe two-SHA reuse attestation. Persist terminal identities externally without another branch commit.

Secrets never appear in artifacts, command arguments, logs, patches, manifests, comments, or notifications. State what remains unverified and why when a gate cannot run; do not report completion.
