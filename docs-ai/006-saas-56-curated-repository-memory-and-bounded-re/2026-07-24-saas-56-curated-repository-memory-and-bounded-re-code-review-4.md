# SAAS-56 curated repository memory and bounded retrieval — Code review 4

## Verdict

**PASS** — zero P1 findings, zero P2 findings, and zero P3 findings in the post-review-3 delta. The direct-script conditional import fix restores ordinary `cli.py --request` compatibility for both read-only Status and mutation authorization dispatch, and the final schema/documentation-link adjustments do not regress the RM-01–RM-05 PASS.

## Review boundary and evidence

- Reviewed base identity remains `main` / `1a5190f1815ae25b0a3cba6e81b50ae221c62052`; reviewed target is the exact current uncommitted working tree on 2026-07-24.
- Delta focus: direct-script imports in `src/skills/linear-delivery-loop/scripts/cli.py`, registered memory schemas/runtime parity, the canonical artifact ownership text, and new repository-memory README/runbook links.
- `python -m unittest tests.linear_delivery_repository_memory.test_context.ContextTests.test_direct_script_supervisor_status_executes_dispatch_path tests.linear_delivery_repository_memory.test_contracts.ContractTests.test_schema_runtime_parity_and_acyclic_known_answers tests.linear_delivery_repository_memory.test_contracts.ContractTests.test_real_layer_projection_bytes_digests_and_included_excluded_boundaries -v` — **exit 0**, three tests, 24.182 seconds.
- Review-3 evidence remains applicable to unchanged authority, recovery, graph, retrieval, context, path, secret, CLI-memory, and status behavior: 13 targeted tests passed across its three bounded commands.

## Delta validation

### PASS — Direct `cli.py --request` Status and AuthorizeMutation compatibility

- Direct-script mode imports repository-memory support through `scripts.repository_memory`; package mode retains relative imports (`cli.py:16-37`). This preserves both invocation forms without changing the supervisor operation union.
- The exception path now conditionally imports `PublicationGitCommittedInterruption` through `scripts.publication_git` in direct-script mode and relatively in package mode (`cli.py:605-614`). There is no remaining unconditional relative import in the exercised dispatch/error boundary.
- `test_direct_script_supervisor_status_executes_dispatch_path` launches the real script twice with `--request`: first with `Status`, then with an issued reservation and `AuthorizeMutation` (`tests/linear_delivery_repository_memory/test_context.py:175-237`). Both subprocesses exit 0; Status returns the exact repository identity and AuthorizeMutation returns `status: active`. Output contains neither a traceback nor “attempted relative import.”
- The direct path still validates the same EngineCommand schema, canonical state home, revisions, reservation control reference, workflow binding, and exact mutation scope before dispatch. The fix changes import selection only; it does not add a new authority surface.

### PASS — Final schema adjustment preserves strict runtime parity

- The nine repository-memory schemas, including batch request and promotion result, remain registered in `MEMORY_SCHEMA_FILENAMES` with matching runtime-constraint inventories (`contracts.py:59-69`, `165-210`).
- `assert_runtime_parity()` still compares the complete reference schema inventory, schema versions, validator metadata, and constraint IDs. The targeted parity test exits 0.
- The real-layer projection test continues to validate canonical bytes/digests and included/excluded boundaries for the manifest, record, request, marker, committed result, index, envelope, and final accounting objects. No digest or schema regression was observed.

### PASS — Documentation and link adjustment

- `README.md` links to the existing shared module runbook and repository curation guide.
- `src/skills/luchdom-docs/references/doc-targets.md` assigns the repository-owned curation guide to `$docs-as-code` and separately identifies the shared runtime/reference page.
- `docs/repository-memory/README.md` links to the existing shared reference, canonical artifact contract, and the `#setup-cli-and-status` heading present in that reference.
- `src/skills/linear-delivery-loop/references/repository-memory.md` links to all nine existing memory schema files and the canonical goal-to-delivery artifact/quality references using correct relative paths.
- The canonical artifact contract records the optional `*-memory-promotion.json` file and its docs-as-code ownership without granting reservation, mutation, publication, provider, or completion authority.

## Prior PASS regression check

No reviewed delta changes the review-3 guarantees:

- journal presence alone is not authority; paired-store recovery and consumed-authorization proof still precede repository creation;
- manifest/source reread, current versus legacy provenance, and prospective in-batch graph validation remain under the canonical mutex;
- marker-last commitment, state-loss rebuild, lifecycle/freshness, deterministic retrieval, and final context accounting are unchanged;
- path/state/secret isolation, observation-only status, and the unchanged supervisor operation union remain intact.

## Remaining delivery gates

This PASS is an independent final-delta code review. Repository aggregate/build projection evidence, runtime QA, docs verification, exact clean PR-head gates, publication/merge authority, and exact returned-merge-SHA validation remain separate workflow stages. This review grants none of that authority.
