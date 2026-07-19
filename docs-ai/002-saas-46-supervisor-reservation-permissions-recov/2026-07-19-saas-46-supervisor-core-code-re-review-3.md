# SAAS-46 supervisor core — independent code rereview 3

## Target identity

- Review role: fresh independent post-implementation `code-reviewer`; no production code, tests, workflow registry, Linear state, Git/provider state, or ignored generated output was mutated.
- Repository: `C:\dev\luchdom\ai-config`.
- Base and checked-out `HEAD`: `e1f44b9dd3f4d281d104b4df06a94267c36eacee`.
- Target: every tracked diff against the base plus every non-ignored untracked file present before this report was added. This report is excluded from its own identity.
- Target manifest: 63 files.
- Manifest algorithm: sort repository-relative `/` paths; hash each file's exact bytes with SHA-256; hash the UTF-8 concatenation of `path + NUL + "sha256:" + file-hash + LF`.
- Target digest: `sha256:2a76210113362aa5c282224703cb81249b775852a4f100559d79adda165000c7`.

## Verdict

**FAIL — 2 P1 findings.** This exact target must not advance to QA, publication, or merge. PASS requires zero actionable P1/P2 findings.

## Findings

### P1-1 — An expired implementation reservation cannot be renewed, released, or reclaimed

Every implemented lifecycle route closes at the same expiry boundary. `renew` resolves the active record and then validates the current control authorization (`src/skills/linear-delivery-loop/scripts/reservations.py:313-320`). `release` accepts `live`, `protected`, and `expired` records, but performs the same validation before considering trusted work evidence (`src/skills/linear-delivery-loop/scripts/reservations.py:713-729`). That validator rejects whenever either the authorization or reservation has expired (`src/skills/linear-delivery-loop/scripts/reservations.py:1666-1701`). The only authority-free expiry route, `reclaim_expired`, explicitly rejects every non-planning reservation (`src/skills/linear-delivery-loop/scripts/reservations.py:955-970`). Recovery just attempts that reclaim and reports the exception as a protected reservation (`src/skills/linear-delivery-loop/scripts/recovery.py:521-549`).

A disposable-repository probe created a semi-autonomous non-planning reservation, advanced the injected clock one nanosecond beyond expiry, and exercised every route. `RenewReservation` and `Release` both failed with `ReservationError: Release authorization contract is invalid`; `ReclaimReservation` failed with `Expired implementation reservations remain protected until explicit release`; `Recover` returned the reservation under `protectedReservations` while its persisted status remained `live`. Because `live`/`expired`/`protected` remain exclusion blockers, no new Reserve or base Handoff can make progress. Autonomous expiry is stricter still: the recovery barrier can coexist with the blocking reservation, while the expired reservation control and capability cannot be refreshed.

This is a permanent repository-authority wedge after an ordinary timeout, contrary to the durable runbook's instruction that expired reservations use an explicit Release/Reclaim/reconciliation route (`src/skills/linear-delivery-loop/references/supervisor-core.md:104-113`). Minimum safe repair constraints:

- expiry must revoke editing/mutation authority without destroying the separately scoped lifecycle authority needed to reconcile or safely terminate the reservation;
- any post-expiry rebind/rotation must be manager-authenticated, operation-journaled, and CAS-bound to the exact reservation, state revision, reservation revision, repository identity, worktree fingerprint, and observed clock state;
- non-planning work must never be rewritten as planning-only or silently reclaimed; terminal reclaim/release requires exact trusted evidence that the protected work is safe, otherwise an explicit attended route must be able to rotate recovery control while preserving exclusion;
- autonomous lease recovery and reservation reconciliation must preserve the barrier until the exact reservation is terminal or explicitly reauthorized, and must not mint mutation authority as a side effect.

Add public-path tests that expire both semi-autonomous and autonomous implementation reservations, prove stale editing credentials remain rejected, and prove an authorized recovery/release sequence reaches a terminal reservation without weakening repository exclusion.

### P1-2 — A kill after Handoff Phase A commits but before recovery-context persistence creates a permanent pending barrier

`prepare_handoff_authorization` writes the authorization/nonce, commits `handoffPending`, changes the reservation to `handoff-pending`, clears its release reference, and revokes the old control authorization before it returns (`src/skills/linear-delivery-loop/scripts/reservations.py:1113-1192`). Only after that return does `execute_assembled_handoff` observe the destination and write the assembly recovery context (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:481-510`). Process termination between those operations therefore leaves a valid pending outer journal and Phase A state but no context.

Recovery requires that context and routes any missing/mismatched read through `_protect` and an exception (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:621-646`). `_protect`, however, calls `finalize_handoff(outcome="ambiguous")`; that branch merely returns a `protected` result without changing state (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:434-452`, `src/skills/linear-delivery-loop/scripts/reservations.py:1222-1258`).

A disposable-repository probe journaled Handoff, completed only `prepare_handoff_authorization`, confirmed the context did not exist, and invoked `recover_assembled_handoff` twice. Both attempts raised `AssembledHandoffError: Assembled Handoff recovery evidence is missing or mismatched`; afterward `handoffPending.status` was still `prepared`, the reservation was still `handoff-pending`, and the repository recovery status was still `clean`. The existing crash helper always writes context immediately after Phase A and therefore does not exercise this boundary (`tests/linear_delivery_supervisor/test_assembled_handoff.py:66-100`).

This is a deterministic pre-Phase-B kill point, not an unknowable transfer outcome. It permanently consumes source control authority and blocks all other authority-bearing commands. Minimum safe repair constraints:

- persist the exact recovery context before, or atomically with, the Phase A state/reservation transition; the durable Phase A record itself must be sufficient to classify every kill point;
- recovery must distinguish authorization not consumed, authorization consumed with proven no destination mutation, proven base failure/rollback, proven transfer, and genuinely ambiguous evidence without trusting absence as proof;
- a proven pre-Phase-B/no-transfer recovery must rotate fresh source lifecycle authority and terminalize the abandoned operation; if authorization was consumed, a retry must use a newly prepared operation/authorization rather than replaying the spent capability;
- recovery must idempotently close or deliberately protect the outer journal and repository barrier. It must not leave `handoff-pending` with `recovery.status == clean` or depend on manual state editing.

Add kill-point tests immediately after the authorization files, pair commit, old-control revocation, context write, interlock consumption, base evidence creation, and Phase C commit, including repeated Recover calls.

## Prior-finding disposition

The three pre-implementation audits were reread. The final pre-implementation re-audit remained a valid PASS for the plan/task specification; both findings above are implementation/recovery defects rather than missing plan authority.

### First failed review (`2026-07-18-saas-46-supervisor-core-code-review.md`)

| Prior finding | Disposition in this target |
|---|---|
| P1-1 repository-selected preflight executable/secrets | **Resolved.** Adapter identity, bytes, argv, and restricted environment are pinned and adversarially tested. |
| P1-2 schema-valid WorkerResult incompatible with ApplyCheckpoint | **Resolved.** Public WorkerResult identity, prepared iteration, mapping, HEAD, and path scope are bound. |
| P1-3 foreign workflow reservation bypasses base Handoff | **Resolved for exclusion.** All blocking and unknown statuses now fail closed. Expiry now exposes the distinct unrecoverable-lifecycle defect in P1-1. |
| P1-4 partial destination treated as restored | **Resolved for reviewed shapes.** Recovery requires exact base evidence and destination/rollback readback. |
| P1-5 killed/expired runs and pending journals lack recovery | **Partially resolved.** Lease and ordinary operation recovery exist, but reservation expiry and the Phase-A Handoff kill point remain permanently wedged (P1-1/P1-2). |
| P1-6 mappings absent and cleanup trusts assertions | **Resolved.** Authoritative allocations and operation/scope/revision-bound cleanup gates are present. |
| P2-1 operation evidence violates schema | **Resolved.** Request/result journal contracts and recovery validation are aligned for the reviewed routes. |
| P2-2 authorization freshness/scope gaps | **Resolved for active authority.** Opaque references, revision/scope binding, rotation, and one-shot checks are enforced; expiry recovery is separately defective (P1-1). |
| P2-3 tests bypass public security boundaries | **Substantially resolved.** Public/adversarial coverage is broad; the two confirmed kill/expiry gaps above remain missing. |

### Second failed review (`2026-07-19-saas-46-supervisor-core-code-re-review.md`)

| Prior finding | Disposition in this target |
|---|---|
| P1-1 identifiers mint renewal/mutation/Handoff authority | **Resolved.** Non-derivable opaque authority is required, rotated, and not exposed by Status. |
| P1-2 recovery rewrites implementation work as planning-only | **Partially resolved.** The unsafe rewrite is gone, but rejecting every safe lifecycle route after expiry causes P1-1. |
| P1-3 prepared/checkpoint authority not bound to issue mapping | **Resolved.** Persistent mapping and exact fingerprint/path bindings are enforced. |
| P1-4 finalized successful Handoff becomes ambiguous | **Resolved for post-Phase-C evidence.** The newly confirmed earlier Phase-A/context boundary remains P1-2. |
| P1-5 Cleanup runs during live reservation | **Resolved.** Cleanup requires terminal reservation and exact cleanup authorization. |
| P1-6 Git-before-state allocation crash window | **Resolved.** Allocation intent/evidence supports reconciliation. |
| P2-1 WorkerResult identity/HEAD accepted without binding | **Resolved.** Identity, HEAD, changed paths, and prepared capability are bound and observed. |
| P2-2 public/crash tests omit security boundaries | **Substantially resolved.** The two exact recovery boundaries in this review still lack regression tests. |

### Third failed review (`2026-07-19-saas-46-supervisor-core-code-re-review-2.md`)

| Prior finding | Disposition in this target |
|---|---|
| P1-1 Status distributes lease authority | **Resolved.** Status removes capability reference/digest; the sidecar name is non-derivable and mutation requires the opaque reference. |
| P1-2 protected/expired reservations do not block | **Resolved for blocking and validation.** These statuses block Reserve/base Handoff and unknown persisted statuses fail closed; the terminal recovery route is nevertheless absent (new P1-1). |
| P1-3 Reserve lacks reservation CAS | **Resolved.** `expectedReservationsRevision` is public, preserved, and rejected when stale. |
| P1-4 autonomous Handoff source/mapping transfer is incoherent | **Resolved for successful execution.** Controller and editing source are separated; complete issue authority/mapping transfers and destination follow-up commands pass. |
| P2-1 RenewLease recovery false-positive after checkpoint | **Resolved.** Request-specific lease sidecar evidence is required and the unrelated-checkpoint regression passes. |
| P2-2 tests/docs omit actual boundaries | **Partially resolved.** Prior missing cases and Windows junction fallback are covered; docs and tests still claim recovery without the expiry and Phase-A kill-point routes above. |

## Verification evidence

- Implementer-reported full supervisor suite: **PASS**, 87 tests in 892.289 seconds.
- Implementer-reported sequential build: **PASS**.
- Implementer-reported delivery-contract suite: **PASS**, 14 tests.
- Reviewer focused regression selection: five correctly selected tests passed (lease authority negatives, stale Reserve CAS, request-specific RenewLease recovery, autonomous Handoff plus destination authority, and Windows reparse fallback); one stale selector failed discovery only. The corrected protected/expired exclusion test then passed: 1 test in 16.651 seconds.
- Reviewer disposable expiry probe: **confirmed P1-1** across RenewReservation, Release, ReclaimReservation, and Recover.
- Reviewer disposable Phase-A kill probe: **confirmed P1-2** across two repeated recovery attempts.
- `git diff --check`: **PASS** (line-ending conversion warnings only).
- No live Linear/provider operation, real external adapter, real process kill, hosted CI, or publication was performed. The probes used temporary local Git repositories and injected boundaries.

## Exact target manifest

```text
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-audit.md sha256:9798cc1c0dc6109692d499456dcf9e967284b84fe9f1958ae1aa21e98dbf8828
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-code-review.md sha256:239764425a2952fb8191f998b544e2dfb92b5e0f784bd120636717ae5af41a06
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-plan.md sha256:a8840d5b1252cc88abd3a41ca64dc0a6d9955c354f0d7bf102857a5acb728eae
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit-2.md sha256:7af0adaae462c23d4f1318794a06bd3216bc2c54edb60b3f428f8057e67e932c
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit.md sha256:1b6d8f53d09ad53e29f874cc58bafe9d38981d1eb2cdab821ecf0d946d7d3c27
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-tasks.md sha256:dce9376bbdfe165e8334e597e44558b4c01b5b49675a689718cff0accf86dbc1
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-19-saas-46-supervisor-core-code-re-review-2.md sha256:5a23d6c93a41bbb7904c6389322048a8fc404c2812ba62c3b35d129cf3869a77
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-19-saas-46-supervisor-core-code-re-review.md sha256:fc12e146275763fccee58f2184094bc911a76112915d2ba0826b14f591c549df
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/workflow.json sha256:e9a5fb2d006474fca507b7f8333f1cfc0189670d106c49553e9d26f8f70dab00
README.md sha256:2a7e580003ce67103413d94f1850bcbfd61460014727ea1aee307eaaad890ce4
src/project-templates/claude/CLAUDE.md sha256:f33411318e0010358b1f55e3b432dea0aff68d731bf85e51683503f442fa2630
src/project-templates/codex/AGENTS.md sha256:f33411318e0010358b1f55e3b432dea0aff68d731bf85e51683503f442fa2630
src/project-templates/cursor/AGENTS.md sha256:f33411318e0010358b1f55e3b432dea0aff68d731bf85e51683503f442fa2630
src/skills/goal-to-delivery/scripts/handoff.py sha256:e5656ca91414ce2a7828b7a1a8f982b3b40d6fa093045a074e47ea7c0a78afa4
src/skills/goal-to-delivery/scripts/reservation_interlock.py sha256:9c1ea6f25eb6b1c46348dcbce0e931dd288dee684486cf17de9ca288303f5a49
src/skills/goal-to-delivery/scripts/workflow_init.py sha256:3c4f3b1d9f374538f52e14656b5bc58d894434c6c236664e46c85dd472d09ae8
src/skills/goal-to-delivery/SKILL.md sha256:ff05e0cbefd2269ff1c13176d312db361a5e4266f23216bdd8290021e2e856e2
src/skills/linear-delivery-loop/references/checkpoint.schema.json sha256:cde041778cfa6053b03ffbbfcff1dc0f70d1336f2c7642f9aceb7047adfdb5ec
src/skills/linear-delivery-loop/references/editing-reservation.schema.json sha256:e4261e3820ebb2942c124f031fbffd05d0e2aea0291b2a59546bcd06ae50685a
src/skills/linear-delivery-loop/references/engine-command.schema.json sha256:9956cd15dc9661d4613da903dbb066c7429efb6e60bf2de30522b5692ee319b4
src/skills/linear-delivery-loop/references/handoff-authorization.schema.json sha256:03eec0bf5687dbc933aad88ccc96f83f52cc7162bf525b948a38ceb41baf2813
src/skills/linear-delivery-loop/references/operation-journal.schema.json sha256:5f7112ac42159383cbcd530ba009e4d2f5733853828d69240f2269ad9d421563
src/skills/linear-delivery-loop/references/prepared-iteration.schema.json sha256:78ff1823faac9dd7d9cf68f340a4a044f9a6052cf219c49bff5c06a169ab414b
src/skills/linear-delivery-loop/references/project-config.schema.json sha256:9c5f5bd58614cd0db53579e130533ad4560dad3fadc948326bf0450f3e6cc16f
src/skills/linear-delivery-loop/references/release-authorization.schema.json sha256:edbccac164eb26197e30310883ae7cfebef9523d0dfb0008796d61fa7f12c711
src/skills/linear-delivery-loop/references/supervisor-core.md sha256:7bb6971cd5660cd9fca7b0697cefd19e4532f995c76edbb1efb796b1acf2d62b
src/skills/linear-delivery-loop/references/supervisor-state.schema.json sha256:40bbf181b7d779c318013595b471c8c512fcb8edbc33e85476fb62b404a6e737
src/skills/linear-delivery-loop/references/trusted-observation.schema.json sha256:197f599704e3154ac643fda15a05e4f611e95403b2e73d28d3742e84a1736f64
src/skills/linear-delivery-loop/references/worker-result.schema.json sha256:f6e7b2f5adfb32ded82661cfd6caf6f23ceedd923d82b5b5bb6983c34efdf3d4
src/skills/linear-delivery-loop/scripts/__init__.py sha256:cd04adadb1f50ad19b1d4954930155838e9568940c276cac293a740ebcf03b03
src/skills/linear-delivery-loop/scripts/agent-worker-engine.ps1 sha256:875f70730e2b77b796ab09e6b65a15b798a15aa7b336696aa624e5a9367dde40
src/skills/linear-delivery-loop/scripts/assembled_handoff.py sha256:b88c1dff98156a3c5a2d06c602161524ccc5e5329f1a3e076ee4044215a55db3
src/skills/linear-delivery-loop/scripts/base_runtime.py sha256:1951925a17174cb39e7fa969edbba66fdb280e66e6843c7825f87e8e72cda7e4
src/skills/linear-delivery-loop/scripts/cli.py sha256:a06fba5ca87343154b475646ef143b3a057765b9cb7911cc74864017612d104e
src/skills/linear-delivery-loop/scripts/contracts.py sha256:4fcfbaa809e3e8785dfecf6e971105f5e64cc6250587d6a3dea901b5677e68f9
src/skills/linear-delivery-loop/scripts/lease.py sha256:e51113bbc595654d3daaafe6f25f27813f3e71b3d8c49279a9be3c975333d29c
src/skills/linear-delivery-loop/scripts/operations.py sha256:60cb289776c44428bc5bd9a1d2d70b3f8109da112b6a8e8797e7e6aff8d8a1cd
src/skills/linear-delivery-loop/scripts/preflight.py sha256:c7fa9dfe9b0df31220f2a0a35bf9bbc6e7564f5b228237d9019912ee5b5f57a3
src/skills/linear-delivery-loop/scripts/recovery.py sha256:02f4eaf8a07380f4607282e49610734bdb81b0b23ee45c30a23611c220070f4b
src/skills/linear-delivery-loop/scripts/reservations.py sha256:5142f37a6856c3f006fe3b31f523b52abd3db1191353bc36110810fa50fa5c78
src/skills/linear-delivery-loop/scripts/store.py sha256:cce720d315b9bd8effa4aadbcea46c50c60138e16f087464390eee4c8423233c
src/skills/linear-delivery-loop/scripts/supervisor.py sha256:aacb02e65ab0dd07f9dce83faa9b2d943e959f013a121e15869bd1fd27c591f3
src/skills/linear-delivery-loop/scripts/worktrees.py sha256:fb969ef493adb9d98708245624668f08eb3d5673e13183ff42bfb6c238293492
src/skills/linear-delivery-loop/SKILL.md sha256:b29ec903fe168442aad2df66adb70707ccb5a8e70285de4782e3543e77cc028b
src/skills/spec-driven-delivery/SKILL.md sha256:1d9cf186217a34d6daf0d0f6c854cc520a4349a353a48ad56c2216d26d3a0eba
tests/linear_delivery_supervisor/__init__.py sha256:03944f753a49f7a34f4eca8369f14e56ff68e880bb9a7385a4da8c09ff67b226
tests/linear_delivery_supervisor/fixtures/preflight/passing-probe.template.json sha256:381c3719d341f3ceef0cb268215a3b53860dbccc1efd5105ea721587ff4d94a1
tests/linear_delivery_supervisor/support_state_engine.py sha256:6b4b1447a4d8353daae11cfd7538f584615aa5b046a93f3db21c4c5637af5f7c
tests/linear_delivery_supervisor/test_assembled_handoff.py sha256:535cef90f37487a658a63d22702fec6a4208f6bec58373e8d054e8c0aa15fce5
tests/linear_delivery_supervisor/test_base_runtime.py sha256:c485085760d83f5592b9bee1a1bbbac1cd37750c260020cd549ffce53d901eac
tests/linear_delivery_supervisor/test_checkpoints.py sha256:7ee019123ce5294b7dc6c4e7ba1892eacef080daf64dda210b4ce80dc9410941
tests/linear_delivery_supervisor/test_cli_wrapper.py sha256:1b4caf877da68c28fd5485823d5dc77035a635b6556d5abe5445987630eff477
tests/linear_delivery_supervisor/test_contracts.py sha256:c9e2ac6eaa66e15bd01cfe0dbb9a3192c9473182ec2323289033f10602400067
tests/linear_delivery_supervisor/test_lease_capability.py sha256:8ca21db1bf9fd36077c70f516b6fdad8bd568b52d3c43166ab29d7469f4de05b
tests/linear_delivery_supervisor/test_operations.py sha256:744fc3beb42416f0ca135564e205bbc432e04455f02c4f5b8dca49858e7cca20
tests/linear_delivery_supervisor/test_preflight.py sha256:01e55df4dbf37c45fe151df000aad34c31e2e3e7bd53a9abb27d56174c891f03
tests/linear_delivery_supervisor/test_recovery_reconciliation.py sha256:2f0a8d8df96737d0fdf6872b90103c364b0337ded9df2f624041ef540e10337f
tests/linear_delivery_supervisor/test_reservations.py sha256:9dba8df654e64c978c47fbb2d1a9fbe7e9791eca2b26e5f640db46d8f3270a41
tests/linear_delivery_supervisor/test_status_cleanup.py sha256:fa846808bda3cf3bb11ef7c97a8d230a8424e7a450d594bd7868481165f5f2e9
tests/linear_delivery_supervisor/test_store_recovery.py sha256:e3f98f3ff462961034ee5605df69fe3f4320f8608cfd42d2280a6f75eb84ae97
tests/linear_delivery_supervisor/test_worktrees.py sha256:359cc1f67bf67421335dcb5ad7ad1de2165f5f63b01d674e9a413f6b9b34ad39
tests/test_delivery_contracts.py sha256:4e9f9130e900c029c6a294fd621ba5956bed8afcdd91f7551666388a1310ccb8
validation/delivery_contracts.py sha256:79a2daa68b32794630a6ac6abd173c46fa335f5063f458e0c33b19d69f51b79a
```

Overall target digest: `sha256:2a76210113362aa5c282224703cb81249b775852a4f100559d79adda165000c7`.
