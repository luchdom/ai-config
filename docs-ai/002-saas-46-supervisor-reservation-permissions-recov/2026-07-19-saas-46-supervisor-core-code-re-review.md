# SAAS-46 supervisor core — independent code rereview

## Target identity

- Review role: fresh independent `code-reviewer`; no production code, Linear state, or Git/provider state was mutated.
- Repository: `C:\dev\luchdom\ai-config`.
- Base and checked-out `HEAD`: `e1f44b9dd3f4d281d104b4df06a94267c36eacee`.
- Target: all 61 tracked-diff and non-ignored untracked files present before this rereview artifact was added, including the registered plan/tasks/audits and prior failed review.
- Manifest algorithm: sort repository-relative `/` paths; hash each file's exact bytes with SHA-256; hash the UTF-8 concatenation of `path + NUL + "sha256:" + file-hash + LF`.
- Target digest: `sha256:611394b169b64e269bb51bf792fdcdbbf979d5b2539d5bb28e7c7cd6f64923a5`.

## Verdict

**FAIL — 6 P1 findings and 2 P2 findings.** The target must not advance to QA or publication. PASS requires zero P1/P2.

## Findings

### P1-1 — Public identifiers can renew or mint mutation/Handoff authority, and autonomous capability expiry/revision is not enforced

The public `RenewReservation`, `AuthorizeMutation`, and `Handoff` variants contain no contained reservation/capability authorization reference (`src/skills/linear-delivery-loop/references/engine-command.schema.json:89-106`, `src/skills/linear-delivery-loop/references/engine-command.schema.json:146-154`). Renewal accepts owner text and revisions (`src/skills/linear-delivery-loop/scripts/reservations.py:276-345`); semi/manual mutation authorization accepts the reservation ID/revision and immediately mints a grant (`src/skills/linear-delivery-loop/scripts/reservations.py:347-412`); Phase A Handoff does the same from reservation/workflow identifiers (`src/skills/linear-delivery-loop/scripts/reservations.py:750-857`). None references the one-workflow opaque authorization created by `Reserve`, contrary to the registered plan's authority rule.

For autonomous policy, `_validate_current_capability` checks only `issued`, run/workflow/issue, and a readable matching nonce (`src/skills/linear-delivery-loop/scripts/reservations.py:1390-1418`). It does not check capability expiry, capability `stateRevision`, stage, physical-worktree fingerprint, or exact capability reference. A focused probe advanced the injected clock beyond both the prepared capability and lease expiry and `authorize_mutation` still returned an active authorization. Thus time-expired/stale autonomous authority can create fresh mutation authority without recovery.

Require the exact engine-owned reservation authorization for semi/manual renewal, mutation issuance, and Handoff; require the exact current capability for autonomous commands and enforce expiry, state revision, stage, repository, physical fingerprint, and reservation binding before issuing any new authority.

### P1-2 — Recovery reclaims implementation reservations by rewriting them as planning-only and ignores a still-live run

Only clean **planning-only** reservations may be reclaimed. Instead, `reclaim_expired` always calls the observer with `planning_only=True` (`src/skills/linear-delivery-loop/scripts/reservations.py:689-729`), never checks the stored `protectedWork.planningOnly`, and never rejects a still-live lease/current run before committing `reclaimed` (`src/skills/linear-delivery-loop/scripts/reservations.py:730-747`). `RecoveryManager` invokes this automatically for every expired active record (`src/skills/linear-delivery-loop/scripts/recovery.py:344-380`).

A focused probe reserved an implementation workflow with `planningOnly: false`, expired it while the worktree was momentarily clean, and `Recover` changed it to `reclaimed` with `planningOnly: true`. This is a time-only authority release and can admit a second repository editor while the original goal/run remains live or resumable. Preserve the original classification and require exact lease/current-work/registry/worktree/operation/provider reconciliation; non-planning work must remain protected.

### P1-3 — Prepared/checkpoint authority is not bound to the authoritative issue-worktree mapping

`WorktreeManager` now persists `issueWorktrees`, but the lease/checkpoint path never consumes that authority. `PrepareIteration` merely observes the caller's `worktreePath` and compares the caller-supplied fingerprint (`src/skills/linear-delivery-loop/scripts/lease.py:423-430`); its workflow check validates only repository ID/key (`src/skills/linear-delivery-loop/scripts/lease.py:704-712`). It never requires `state.issueWorktrees[issueId]`, never rejects the scheduled control worktree, and never requires the current manager to equal the registered issue worktree. The public CLI passes this directly (`src/skills/linear-delivery-loop/scripts/cli.py:296-311`).

The public wrapper checkpoint test itself creates no issue mapping, prepares against the control repository, and successfully applies the checkpoint (`tests/linear_delivery_supervisor/test_cli_wrapper.py:81-162`). This violates the explicit S46-05 rule that implementation/checkpoint reject scheduled-control and unregistered linked worktrees. Before preparing or checkpointing, resolve the one authoritative issue mapping under the mutex and bind manager, workflow registry, capability sidecar, worker observation, and actual physical worktree to it.

### P1-4 — A crash after successful supervisor Handoff finalization is falsely made permanently ambiguous

Phase C clears `handoffPending` and transfers the reservation/capability before the outer operation journal is completed (`src/skills/linear-delivery-loop/scripts/reservations.py:1001-1019`, then `src/skills/linear-delivery-loop/scripts/cli.py:431-436`). If the process is killed in that interval, the registry, destination reservation, and capabilities already prove success, but the Handoff journal remains pending.

Public `Recover` calls assembled recovery only when `handoffPending` is still non-null (`src/skills/linear-delivery-loop/scripts/cli.py:380-389`). Generic recovery has no authoritative Handoff-success case and classifies every remaining pending Handoff as ambiguous (`src/skills/linear-delivery-loop/scripts/recovery.py:112-142`, `src/skills/linear-delivery-loop/scripts/recovery.py:286-289`). A focused exact probe produced `transferred`, observed `handoffPending: null`, then recovered the pending journal as `protected`/`ambiguous-operation:*`.

Recovery must recognize the exact post-Phase-C destination registry/reservation/capability/context evidence and complete the original journal idempotently. This is part of the required “crash after supervisor transfer” boundary, not attended ambiguity.

### P1-5 — Cleanup's safety condition is inverted: it requires and runs during a live reservation

The registered task and durable runbook require Cleanup to refuse a live reservation (`docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-tasks.md:142`, `src/skills/linear-delivery-loop/references/supervisor-core.md:88`). The implementation instead rejects anything except a live/pending reservation (`src/skills/linear-delivery-loop/scripts/cli.py:152-166`), derives cleanup authority from it, and removes the gate while it is live (`src/skills/linear-delivery-loop/scripts/cli.py:167-204`, `src/skills/linear-delivery-loop/scripts/worktrees.py:544-568`). The public positive test codifies that inverted behavior (`tests/linear_delivery_supervisor/test_status_cleanup.py:91-158`).

This makes post-release cleanup impossible and permits destructive Git worktree mutation while repository editing authority is active. Define a separate exact cleanup authority derived from resolved operation/attestation evidence after no active reservation/lease/Handoff exists; keep exact path/revision/scope binding and the current ambiguous-removal protection.

### P1-6 — Worktree allocation has an unrecoverable Git-before-state crash window

Issue allocation executes `git worktree add` before committing the mapping (`src/skills/linear-delivery-loop/scripts/worktrees.py:325-363`); gate allocation has the same ordering (`src/skills/linear-delivery-loop/scripts/worktrees.py:422-474`). A kill after Git succeeds but before the paired state commit leaves a valid contained worktree with no authoritative record. The next issue call explicitly refuses that shape (`src/skills/linear-delivery-loop/scripts/worktrees.py:304-308`), gate allocation refuses the existing path (`src/skills/linear-delivery-loop/scripts/worktrees.py:428-433`), and `RecoveryManager` has no issue/gate allocation reconciliation path.

The five-minute loop is then permanently wedged despite an unambiguous Git worktree that can be matched by exact issue/branch or operation/SHA/common-dir/path evidence. Journal allocation intent before Git, record before/after observations, and make `Recover` either adopt the exact expected mapping or protect genuinely ambiguous shapes. Add real interruption tests on both sides of Git mutation and state commit.

### P2-1 — Schema-valid WorkerResult identity and HEAD claims are accepted without binding or observation

The repaired public WorkerResult field names now reach `ApplyCheckpoint`, but `_validate_checkpoint_bindings` omits required `preparedIterationId` and ignores `observed.headSha` (`src/skills/linear-delivery-loop/scripts/lease.py:727-754`). No runtime Git HEAD observation occurs at checkpoint. A focused probe supplied a different schema-valid prepared UUID and `ffffffffffffffffffffffffffffffffffffffff` instead of the actual HEAD; the checkpoint returned `applied`.

Bind every required WorkerResult identity to the selected prepared file and compare the reported HEAD/change evidence with fresh engine observations. Add negative wrapper tests for wrong prepared ID, actual HEAD, issue mapping, artifact/change manifest, and any applicable gate/provider facts.

### P2-2 — Public/crash tests still omit most security boundaries and encode unsafe behavior

The repaired tests add public wrapper coverage only for Status, ApplyCheckpoint, and Recover (`tests/linear_delivery_supervisor/test_cli_wrapper.py:29-209`), plus direct public Cleanup. Acquire/Renew/Prepare/Reserve/RenewReservation/AuthorizeMutation/Release/Handoff/ReleaseLease lack end-to-end wrapper success and negative authority tests. Handoff tests call internal assembly/functions and cover rollback evidence, but do not kill a process after Phase C and before journal completion (`tests/linear_delivery_supervisor/test_assembled_handoff.py:124-326`). Worktree tests do not interrupt allocation between Git and state commit, recovery tests affirm reclaiming a non-planning reservation (`tests/linear_delivery_supervisor/test_recovery_reconciliation.py:64-85`), and cleanup tests affirm deletion during a live reservation.

Add public file/wrapper tests for all 14 variants and real subprocess interruption coverage for every external-mutation/state/journal boundary. Tests must assert the registered safety rules rather than normalize the defects above.

## Prior-finding disposition

| Prior finding | Disposition | Evidence |
|---|---|---|
| P1-1 pinned preflight and non-configurable secret denial | **Resolved** | Adapter is pinned to the installed Python and exact engine script/argv (`preflight.py:383-397`); child environment is core-only (`preflight.py:284-292`); malicious adapter/config-declared unrelated-secret tests pass. |
| P1-2 public schema-valid WorkerResult / expectedStage | **Partially resolved** | Valid WorkerResult reaches the public wrapper and `expectedStage` is consumed, but prepared ID and HEAD are not bound (new P2-1), and issue-worktree authority is absent (new P1-3). |
| P1-3 repository-wide foreign/multiple reservation interlock | **Resolved** | Base interlock enumerates every active repository record before workflow matching (`reservation_interlock.py:98-151`); foreign/multiple tests pass. |
| P1-4 positive failure/success and partial-destination ambiguity | **Partially resolved** | Exact rollback readback and partial-destination protection are implemented/tested, but post-Phase-C/pre-journal crash recovery is broken (new P1-4). |
| P1-5 killed/expired lease and pending journal recovery | **Partially resolved** | Expired leases and pending local journals can reconcile, but automatic reservation reclaim is unsafe (new P1-2), and several crash windows remain unhandled. |
| P1-6 persistent mappings and exact cleanup authority | **Partially resolved** | Mappings and scoped cleanup state are persisted, but allocation is not crash-recoverable (new P1-6) and live-reservation cleanup is inverted (new P1-5). |
| P2-1 runtime/schema-valid journal evidence | **Resolved** | `journal.json` conforms to and is validated against `operation-journal`; request/result companions are hash-bound and validated on read (`operations.py:42-243`). |
| P2-2 expiry/operation/revision/fingerprint/scope authorization binding | **Partially resolved** | Mutation/release consumption enforces detailed bindings, but authority issuance/renewal/Handoff and autonomous capability freshness remain bypassable (new P1-1). |
| P2-3 public negative/crash adequacy | **Not resolved** | See new P2-2. |

## Checks run

- `python -m unittest tests.linear_delivery_supervisor.test_preflight tests.linear_delivery_supervisor.test_cli_wrapper tests.linear_delivery_supervisor.test_assembled_handoff tests.linear_delivery_supervisor.test_recovery_reconciliation tests.linear_delivery_supervisor.test_reservations tests.linear_delivery_supervisor.test_status_cleanup tests.linear_delivery_supervisor.test_worktrees -v` — PASS, 39 tests, 525.414 s. These green tests expose coverage/expectation gaps; they do not clear the findings.
- Exact Handoff finalization interruption probe — base/supervisor returned `transferred`; pending journal recovery returned `protected` with the operation in `ambiguousOperations` and set the recovery barrier to `ambiguous`.
- Expired autonomous-capability probe — clock advanced beyond prepared capability and lease expiry; `authorize_mutation` still returned `active`.
- Non-planning reservation recovery probe — initial `planningOnly: false`; Recover returned it under `reclaimedReservations` and persisted `planningOnly: true`.
- WorkerResult binding probe — wrong schema-valid `preparedIterationId` and fabricated HEAD; `ApplyCheckpoint` returned `applied`.
- Static inspection covered all 61 manifest files, all supervisor/base-interlock scripts, all schemas, all focused tests, registered plan/tasks, and the prior failed review.

## Residual risks

- Live Linear, ntfy, GitHub mutation transports and exact-SHA publication orchestration remain intentional SAAS-47/48 non-goals and are not findings.
- No real credential or raw capability was used or emitted. Preflight's repaired redaction/minimized-environment boundary passed focused checks.
- The reviewer did not treat any aggregate status as evidence for or against these semantic authority/crash defects.

## Exact target manifest

```text
sha256:2a7e580003ce67103413d94f1850bcbfd61460014727ea1aee307eaaad890ce4  README.md
sha256:9798cc1c0dc6109692d499456dcf9e967284b84fe9f1958ae1aa21e98dbf8828  docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-audit.md
sha256:239764425a2952fb8191f998b544e2dfb92b5e0f784bd120636717ae5af41a06  docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-code-review.md
sha256:a8840d5b1252cc88abd3a41ca64dc0a6d9955c354f0d7bf102857a5acb728eae  docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-plan.md
sha256:7af0adaae462c23d4f1318794a06bd3216bc5c54edb60b3f428f8057e67e932c  docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit-2.md
sha256:1b6d8f53d09ad53e29f874cc58bafe9d38981d1eb2cdab821ecf0d946d7d3c27  docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit.md
sha256:dce9376bbdfe165e8334e597e44558b4c01b5b49675a689718cff0accf86dbc1  docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-tasks.md
sha256:42c0d6570fb0a4d712671881126aa2ec50fa89582d44c65d0d7f30a4ec447df6  docs-ai/002-saas-46-supervisor-reservation-permissions-recov/workflow.json
sha256:32d3ac0b97db4f62d2acc14ce6d1ef53d832e41bbd0d35124434bce6af824cd9  src/project-templates/claude/CLAUDE.md
sha256:32d3ac0b97db4f62d2acc14ce6d1ef53d832e41bbd0d35124434bce6af824cd9  src/project-templates/codex/AGENTS.md
sha256:32d3ac0b97db4f62d2acc14ce6d1ef53d832e41bbd0d35124434bce6af824cd9  src/project-templates/cursor/AGENTS.md
sha256:f20e665da0f67a45913c26281b872bcdedafb3d076da0a8116edacfb312a422e  src/skills/goal-to-delivery/SKILL.md
sha256:a0c6326c0c39dcb27fb40ceeea49d1faaf7ac518582f9fd95646dba0931238fa  src/skills/goal-to-delivery/scripts/handoff.py
sha256:c25dee0c65209e7917dc076432b182b2c7e85c8c3d3e02b0c763ec2281a5935d  src/skills/goal-to-delivery/scripts/reservation_interlock.py
sha256:fa4ef230d06c5aaa637c3afebc4288d490db34c3e0b795e4c1cd5b655251f86c  src/skills/goal-to-delivery/scripts/workflow_init.py
sha256:b29ec903fe168442aad2df66adb70707ccb5a8e70285de4782e3543e77cc028b  src/skills/linear-delivery-loop/SKILL.md
sha256:cde041778cfa6053b03ffbbfcff1dc0f70d1336f2c7642f9aceb7047adfdb5ec  src/skills/linear-delivery-loop/references/checkpoint.schema.json
sha256:b0eb750fa2cc0d7971af8b0862b4faa199c45c88114d57270882efbf2b37c0c1  src/skills/linear-delivery-loop/references/editing-reservation.schema.json
sha256:3a4a83c4619122aaa116b0ff96abeacf202b1090ccd09d1dd5225b8c94bfc2fe  src/skills/linear-delivery-loop/references/engine-command.schema.json
sha256:03eec0bf5687dbc933aad88ccc96f83f52cc7162bf525b948a38ceb41baf2813  src/skills/linear-delivery-loop/references/handoff-authorization.schema.json
sha256:5f7112ac42159383cbcd530ba009e4d2f5733853828d69240f2269ad9d421563  src/skills/linear-delivery-loop/references/operation-journal.schema.json
sha256:78ff1823faac9dd7d9cf68f340a4a044f9a6052cf219c49bff5c06a169ab414b  src/skills/linear-delivery-loop/references/prepared-iteration.schema.json
sha256:9c5f5bd58614cd0db53579e130533ad4560dad3fadc948326bf0450f3e6cc16f  src/skills/linear-delivery-loop/references/project-config.schema.json
sha256:52207279c9e5fbd612a924e753d9c818e45ceb878e8561447b55237af4659a13  src/skills/linear-delivery-loop/references/release-authorization.schema.json
sha256:cf8c02560262f43539ec439bae51628aafaf2bd92e1f4a664ba703de7d7da049  src/skills/linear-delivery-loop/references/supervisor-core.md
sha256:9ea8cde74e8226b8f46d096d8d8da1c2d47bcd7a827764a7d43c767350a6b209  src/skills/linear-delivery-loop/references/supervisor-state.schema.json
sha256:197f599704e3154ac643fda15a05e4f611e95403b2e73d28d3742e84a1736f64  src/skills/linear-delivery-loop/references/trusted-observation.schema.json
sha256:f6e7b2f5adfb32ded82661cfd6caf6f23ceedd923d82b5b5bb6983c34efdf3d4  src/skills/linear-delivery-loop/references/worker-result.schema.json
sha256:cd04adadb1f50ad19b1d4954930155838e9568940c276cac293a740ebcf03b03  src/skills/linear-delivery-loop/scripts/__init__.py
sha256:875f70730e2b77b796ab09e6b65a15b798a15aa7b336696aa624e5a9367dde40  src/skills/linear-delivery-loop/scripts/agent-worker-engine.ps1
sha256:81325e5c5bb1ffb5845fed5ba96550d80897fb7a2046a5432b81c3648d1bf2cc  src/skills/linear-delivery-loop/scripts/assembled_handoff.py
sha256:1951925a17174cb39e7fa969edbba66fdb280e66e6843c7825f87e8e72cda7e4  src/skills/linear-delivery-loop/scripts/base_runtime.py
sha256:9ec6f7d9ee3733119d6969f1246119e0afaf8c411eff3b414f7f9e2fce1e048a  src/skills/linear-delivery-loop/scripts/cli.py
sha256:cf3c78e15c0b3e612a50464b2a0a4ed09b147def1d1858fed40f54a9fb53dc44  src/skills/linear-delivery-loop/scripts/contracts.py
sha256:ba07571d3398b295a56b922317bd1da6c1c31e8c7df2170cd402ff2aadbc686b  src/skills/linear-delivery-loop/scripts/lease.py
sha256:60cb289776c44428bc5bd9a1d2d70b3f8109da112b6a8e8797e7e6aff8d8a1cd  src/skills/linear-delivery-loop/scripts/operations.py
sha256:c7fa9dfe9b0df31220f2a0a35bf9bbc6e7564f5b228237d9019912ee5b5f57a3  src/skills/linear-delivery-loop/scripts/preflight.py
sha256:67a382a84ae1f3b80a99e68580660774730a843c6785ef6e58c6f80652ce6a49  src/skills/linear-delivery-loop/scripts/recovery.py
sha256:b08fc203c5b365266ef5988c8fddc61ddd4fdd349e777cab068162c53d821c8e  src/skills/linear-delivery-loop/scripts/reservations.py
sha256:42a041fcf13e9a6c34b7783f569493ba2ef42fde72f7e4edaa978b86b94293f6  src/skills/linear-delivery-loop/scripts/store.py
sha256:f771e12827aa6cf96a0a83d72272ae309296d8816ef32a2264b7b4fcafadd389  src/skills/linear-delivery-loop/scripts/supervisor.py
sha256:aed66a2bb0dc6e8a0877065bf90c99dfa17e41ea37d881bbf3352b85101319eb  src/skills/linear-delivery-loop/scripts/worktrees.py
sha256:5587d46f611294d91f12fab4af54b5b91dbc654f24315c4be8016fef3094735d  src/skills/spec-driven-delivery/SKILL.md
sha256:03944f753a49f7a34f4eca8369f14e56ff68e880bb9a7385a4da8c09ff67b226  tests/linear_delivery_supervisor/__init__.py
sha256:381c3719d341f3ceef0cb268215a3b53860dbccc1efd5105ea721587ff4d94a1  tests/linear_delivery_supervisor/fixtures/preflight/passing-probe.template.json
sha256:a6a91737cbaf442e63cdcb6e1021b6aefa8d3c2bc5bf9c9dff49b411baa7119  tests/linear_delivery_supervisor/support_state_engine.py
sha256:74a2dddc5bba822d825c412af533706ddce78f1d516959acc1feafd154fd7318  tests/linear_delivery_supervisor/test_assembled_handoff.py
sha256:c485085760d83f5592b9bee1a1bbbac1cd37750c260020cd549ffce53d901eac  tests/linear_delivery_supervisor/test_base_runtime.py
sha256:c0202dd6be10244d147579015b7ea2ec2a4369f004eeff037e298b7c47d3ba9f  tests/linear_delivery_supervisor/test_checkpoints.py
sha256:2f9cdd81a1993d32acab356ea6eb05353436bf81910a57efc97930acf0489e1b  tests/linear_delivery_supervisor/test_cli_wrapper.py
sha256:88989d0febbbfb61a842c086b2998446134428d5c42df1e9e3e5df23ad927c20  tests/linear_delivery_supervisor/test_contracts.py
sha256:8a878fe3224a2a5c404203a1009a71dc518dd62cc59c59a7ff75337f131b4a78  tests/linear_delivery_supervisor/test_lease_capability.py
sha256:744fc3beb42416f0ca135564e205bbc432e04455f02c4f5b8dca49858e7cca20  tests/linear_delivery_supervisor/test_operations.py
sha256:6ffc202d26b01edc4e4972d0a1eace17c61150ba3585ad331f971464499d6b4d  tests/linear_delivery_supervisor/test_preflight.py
sha256:afbee741ae6a6441cf849c656d92d1da0328d1fe946f19d0ab7d9faa91da0d44  tests/linear_delivery_supervisor/test_recovery_reconciliation.py
sha256:92eed76a8fe604927820dfb4a50667097b4f4ccf1e4d438ed6c15fcd641b4e6f  tests/linear_delivery_supervisor/test_reservations.py
sha256:6abbd0605bf1726a048146f84e261a8731ef3d7d7a853df376df9349e20b29c9  tests/linear_delivery_supervisor/test_status_cleanup.py
sha256:8501d5f4c9b5c214dcbc0e2879d76f5dcbac50cc0390fb66d94d6324edaf5cc6  tests/linear_delivery_supervisor/test_store_recovery.py
sha256:f612844e621190a1cc793ef3ef1df9b477dd2f7f913d8b62d06e8dbbdbc749d5  tests/linear_delivery_supervisor/test_worktrees.py
sha256:4e9f9130e900c029c6a294fd621ba5956bed8afcdd91f7551666388a1310ccb8  tests/test_delivery_contracts.py
sha256:79a2daa68b32794630a6ac6abd173c46fa335f5063f458e0c33b19d69f51b79a  validation/delivery_contracts.py
```
