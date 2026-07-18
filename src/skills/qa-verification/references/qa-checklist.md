# Runtime QA Checklist

## Target and safety

- [ ] Read repository instructions, acceptance criteria, manifest, and review result.
- [ ] Record exact target identity and repository-owned local commands.
- [ ] Reject production credentials/data and unsafe non-local targets where repository policy requires isolation.
- [ ] Prepare unique disposable resources and cleanup verification.

## Local gates

- [ ] Run focused build/test/lint/type/docs checks that apply.
- [ ] Run the repository's full required local aggregate.
- [ ] Record commands, versions, exit codes, and relevant clean status.

## Real behavior

- [ ] Map every acceptance criterion to observed evidence.
- [ ] Exercise affected HTTP/browser/CLI/user paths with non-default values.
- [ ] Use bounded readiness predicates rather than fixed sleeps.
- [ ] Verify failure, validation, authorization/tenant, and accessibility paths when applicable.
- [ ] Complete and verify cleanup.

## Report

- [ ] Distinguish passed, failed, blocked, and unverified criteria.
- [ ] State residual risk and exact defect handoff.
- [ ] Do not claim code-review coverage or fix production code.
