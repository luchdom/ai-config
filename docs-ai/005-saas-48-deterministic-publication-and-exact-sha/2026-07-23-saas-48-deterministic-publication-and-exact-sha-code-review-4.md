# SAAS-48 deterministic publication and exact-SHA gates — Code review 4

## Verdict

**FAIL** — four P1 findings remain. The latest changes reject preloaded publication evidence, read the real lease/reservation state, type attestation sidecars, classify refusals in the provider handler, expose repair in dispatch, and preserve the ordered happy path. However, the public engine still accepts caller-authored pass evidence, does not consume scoped mutation authority, persists publication changes before its CAS check, and does not compose refusal/attended recovery or the complete repair pipeline.

## Findings

### P1 — “Engine-issued” review/QA/docs attestations are still caller assertions, and one unrelated mutation grant authorizes the whole publication

`RecordPublicationAttestation` accepts `attestationId`, `kind`, `exactSha`, `provenanceRef`, timestamp, and `result` directly from the public command (`engine-command.schema.json:207-218`; `cli.py:477-486`). `record_publication_attestation()` merely assigns the configured producer string and writes the supplied claim to an “issued” sidecar (`supervisor.py:375-403`). It never resolves `provenanceRef` to an authoritative specialist result, verifies that the named producer actually ran, or derives pass/fail from engine-owned evidence. The main integration test demonstrates the bypass by supplying the same arbitrary hash and `result="passed"` for review, QA, docs, and evidence convergence, then merging (`test_publication_contracts.py:166-175`). Rejecting attestations preloaded in `PreparePublication` therefore does not close the original evidence-authority defect; it only moves fabrication to a later public command.

Publication mutation authority is similarly not bounded to each mutation. `_publication_local_authority()` scans durable authorization records for an active record whose operation ID equals the publication operation (`supervisor.py:308-322`), but it does not validate or consume the authorization reference, require the authorization's path/operation scope, bind it to the current state and reservation revisions/run/repository, or issue a fresh grant per push, PR, merge, gate, and evidence mutation. The test authorizes `publish-1` over only `README.md` once (`test_publication_contracts.py:124-133`) and reuses it for the entire provider/gate/attestation/merge sequence. This bypasses the canonical “AuthorizeMutation before each bounded deliverable mutation” boundary and allows a caller-chosen digest plus a reusable unrelated path grant to reach merge.

Required correction: consume exact operation/scope/revision-bound authorization through the reservation manager for every bounded mutation, and derive typed specialist attestations from validated engine-owned result records rather than accepting `result` and an opaque digest from the command. Add negative integration fixtures proving a README-only or already-consumed grant cannot authorize provider/gate/evidence operations and an arbitrary hash cannot become passing review/QA/docs evidence.

### P1 — Publication journal state is written before the authoritative CAS and authority check

`PublicationJournal.save_authoritative()` calls `self.save(value)` before acquiring the paired-state mutex, checking `expected_state_revision`, or running `authority_check` (`operations.py:497-516`). A stale or concurrently invalidated request can therefore overwrite `publication-state.json`, then fail its supervisor CAS. `reconcile_authoritative()` subsequently loads that already-written record and binds it without an expected revision or authority check (`operations.py:540-543`). Several public paths rely on this method after a separate authority check (`supervisor.py:400-401`, `455-456`, `508-518`, `552-571`, `586-587`, `633-653`), leaving a deterministic crash/concurrency path that converts rejected state into authoritative state.

Required correction: validate CAS and authority under the mutex before publication journal mutation, or journal an immutable proposed transition and atomically commit an authority-bound reference that recovery can prove. Recovery must never bind a proposal whose originating CAS/authorization was not committed. Add a fault fixture for journal write followed by stale-CAS/authority failure and prove reconciliation refuses it.

### P1 — Provider refusal and attended recovery remain disconnected from the public runnable flow

The provider handler duplicates only the retry counter/status portion of `PublicationRecovery.refusal()` (`supervisor.py:489-511`). It never invokes the composed recovery policy, releases the run lease for transient wait, or, for stable/exhausted refusal, restores the ordinary issue state, adds `blocked + needs-human`, creates/updates the durable SAAS-47 request, emits ntfy, and releases only the lease. The complete side effects exist only in the standalone policy (`publication_recovery.py:77-109`) and are not called by provider execution.

Attended recovery also cannot run through public dispatch. `recover_publication()` has an internal `attended` argument (`supervisor.py:574-605`), but the `RecoverPublication` command schema contains only the publication ID and expected revision (`engine-command.schema.json:231-239`), and CLI dispatch passes only `operation_id` and `now` (`cli.py:495-500`). Moreover, normal CLI construction installs neither a publication provider nor a `PublicationRecovery` instance. The unit tests validate the standalone policy with injected callbacks, not the assembled command path. Thus a stable refusal produced by the engine cannot create its required request and cannot consume an exact attended reply to resume.

Required correction: route every provider refusal through the durable policy transaction and expose a closed, schema-valid attended-recovery command that performs the authoritative rereads and consumes the SAAS-47 reply internally. Test transient retries 1/2/3, first refusal after exhaustion, stable pause side effects, crash/replay, malformed/stale/duplicate reply, and successful attended resume through `run_request`/dispatch rather than the standalone class.

### P1 — Public repair records a branch name but cannot execute or enforce the complete bounded repair pipeline

`PublicationRepair` is now public, but `next_publication_repair()` only changes the record to `prepared`, assigns `codex/SAAS-48-repair-N`, sets `headSha` to current `main`, and clears evidence (`supervisor.py:608-654`). It neither creates the physical branch nor provides an authority-bound transition from the base SHA to the resulting repair commit. `PublicationJournal.save()` permits a head change only in the same `post-merge-validating -> prepared` transition that increments the repair attempt (`operations.py:483-490`), so the later repair implementation head cannot be recorded through this state machine.

More importantly, `MergeRepairPolicy.require_repair_pipeline()`—the only check requiring pre-staging aggregate, exact repair-head aggregate, review, QA, docs, evidence convergence, merge readback, and exact repair-merge aggregate—is never called by production code (`publication_recovery.py:192-200`; its only caller is the isolated unit test). The ordinary premerge check omits pre-staging and merge-readback evidence. Consequently the public flow neither runs a real repair nor proves the required full re-entry before the next merge; the three-attempt/exhaustion counter wraps an unenforced pipeline.

Required correction: implement a journaled repair-head preparation/commit transition with physical Git readback, invalidate and regenerate all exact-head evidence, enforce `require_repair_pipeline()` in the assembled path, and make each attempt plus final exhaustion recoverable through dispatch. Add integration fixtures that fail independently when every required repair member is missing/stale/wrong-SHA and that drive attempts 1–3 plus exhaustion through the public engine.

## Prior-finding closure assessment

- Real live lease/reservation/current-stage lookup: **partially closed**; records are read, but mutation grants are neither scoped nor consumed and CAS is not atomic with publication persistence.
- Durable provider authority facts: **partially closed**; a strict readback shape is persisted, but refusal side effects and attended recovery are not composed.
- Preloaded evidence rejection: **closed at preparation**, but passing evidence remains publicly forgeable through `RecordPublicationAttestation`.
- Typed, provenance-bound attestations: **not closed**; type/producer fields are fixed, while provenance and result remain unverified caller input.
- Provider retry/backoff/pause and attended resume through dispatch: **not closed**.
- Public bounded repair through attempts/exhaustion: **not closed**.
- Ordered push/PR/head-gate/merge/merge-gate phases, distinct provider operation IDs, provider-readback merge SHA, and full-body evidence-delta rejection: **remain closed**.

## Verification evidence

- Reviewed the full current working tree against `main`, including all untracked SAAS-48 implementation/tests and excluding only `.codex-remote-attachments/`, plus all prior SAAS-48 audit/review artifacts.
- Focused publication contract/provider/recovery/repair/exact-SHA suites: **24 tests passed** in 54.167 seconds. The passing integration fixture itself supplies the caller-authored evidence and unrelated reusable scope described above.
- `engine-command.schema.json` parses successfully.
- `git diff --check`: **PASS** (line-ending warnings only).
