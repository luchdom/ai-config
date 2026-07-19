# SAAS-46 supervisor core — independent code rereview 4

## Target identity

- Review scope: the exact current working tree, focused on expiry lifecycle reauthorization and pre-Phase-A Handoff recovery ordering/idempotency. No implementation, tests, workflow registry, Linear state, Git/provider state, or ignored output was mutated by this reviewer.
- Repository: `C:\dev\luchdom\ai-config`.
- Base and checked-out `HEAD`: `e1f44b9dd3f4d281d104b4df06a94267c36eacee`.
- Target: every tracked diff against the base plus every non-ignored untracked file present before this report was added. This report is excluded from its own identity.
- Target manifest: 64 files.
- Manifest algorithm: sort repository-relative `/` paths; hash each file's exact bytes with SHA-256; hash the UTF-8 concatenation of `path + NUL + "sha256:" + file-hash + LF`.
- Target digest: `sha256:86137fe6f78e79986cd29fd13576f26dea392078f3b7921b668bfd1e2bb6a718`.

## Verdict

**FAIL — 1 P1 finding.** The expiry-lifecycle P1 from rereview 3 is resolved, but the Handoff recovery repair moves the unrecoverable kill window to immediately before Phase A. This target must not advance to QA, publication, or merge; PASS requires zero actionable P1/P2 findings.

## Finding

### P1-1 — Context-first Handoff still cannot recover a kill before the Phase A state commit

`execute_assembled_handoff` now writes the exact destination/evidence recovery context before calling `prepare_handoff_authorization` (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:500-526`). This fixes the previously reported kill after Phase A returns, but introduces an earlier durable boundary: the process can stop after the context write and before Phase A creates its authorization or commits `handoffPending`. It can also stop inside Phase A after the authorization files are written but before the paired state/reservation commit (`src/skills/linear-delivery-loop/scripts/reservations.py:1126-1205`).

Recovery still requires an authorization record before it reads or uses the precommitted context (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:640-665`). If that record is absent, `_protect` cannot finalize a nonexistent pending Handoff and instead activates the repository ambiguity barrier (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:453-470`). The exception escapes before the CLI can terminalize the original Handoff journal (`src/skills/linear-delivery-loop/scripts/cli.py:424-441`). If an authorization exists but the pair commit did not occur, the `pending is None` recovery branch requires a revoked authorization to classify source restoration; a still-`prepared` orphan cannot satisfy its failure predicate (`src/skills/linear-delivery-loop/scripts/assembled_handoff.py:671-794`).

A disposable-repository probe began the exact Handoff journal, allowed `_write_recovery_context` to complete, injected `SystemExit` before `prepare_handoff_authorization`, and then invoked Recover twice. Evidence after the kill was `context=True`, `authorization=False`, `handoffPending=None`, `recovery.status=clean`, and original journal `pending`. Both recovery attempts raised `AssembledHandoffError: Assembled Handoff recovery evidence is missing or mismatched`; final state was `recovery.status=ambiguous` with the original Handoff journal still `pending`. The new regression test injects its crash only after `prepare_handoff_authorization` has fully returned, so it does not cover either context-to-authorization or authorization-to-pair-commit (`tests/linear_delivery_supervisor/test_assembled_handoff.py:301-357`).

This is a normal process-kill boundary with provable no-transfer evidence, yet it permanently blocks replay and subsequent authority-bearing work. The recovery contract must classify all context-first Phase A sub-boundaries:

- context exists, no authorization, no `handoffPending`, original reservation/control and source registry still exactly match the journal request;
- context and prepared authorization exist, but no `handoffPending`/reservation transition exists;
- Phase A pair commit exists and the old control is either still active or already revoked.

For each case, recovery may terminalize as failed-before-Phase-B only when the immutable journal request, context bindings, unchanged destination observation, unchanged base-evidence identity set, source registry, reservation revision/control binding, and absence of a conflicting pending operation all agree. It must revoke/quarantine any orphan authorization, preserve or rotate the exact source lifecycle authority as required, close the original journal idempotently, and leave the repository recovery barrier clean. Any mismatch must remain protected. Add kill-point tests immediately after context creation, after each authorization file, after the pair commit, and after old-control revocation; repeat Recover for every terminal classification.

## Repair disposition

| Rereview-3 P1 | Disposition |
|---|---|
| Expired implementation reservation has no lifecycle route | **Resolved.** `RenewLease` accepts only the exact still-active opaque lease sidecar through the `expired-lease` barrier and rotates it; `RenewReservation` accepts the exact current expired control, rotates it, and does not make an expired prepared capability valid for mutation. Semi-autonomous reauthorization/release and autonomous lease-plus-reservation reauthorization/fresh-prepare/release tests pass. |
| Kill after Phase A but before context persistence is unrecoverable | **Partially resolved.** Context now precedes Phase A and the post-Phase-A test recovers idempotently, but kills between context creation and the Phase A pair commit remain unrecoverable (P1-1). |

## Focused verification

- `test_expired_semi_autonomous_reservation_can_reauthorize_then_release`: **PASS**.
- `test_expired_autonomous_authority_can_reauthorize_lifecycle_without_mutation`: **PASS**; stale prepared authority remained unable to mint mutation authority, then fresh prepared authority allowed safe release.
- `test_crash_after_phase_a_recovers_from_precommitted_context_idempotently`: **PASS**.
- Reviewer context-before-Phase-A kill probe: **confirmed P1-1** across two repeated recovery attempts.
- `git diff --check`: **PASS** (line-ending conversion warnings only).
- No full-suite rerun was necessary for this focused rereview; no live provider/Linear operation or real external adapter was exercised.

## Exact target manifest

```text
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-audit.md sha256:9798cc1c0dc6109692d499456dcf9e967284b84fe9f1958ae1aa21e98dbf8828
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-code-review.md sha256:239764425a2952fb8191f998b544e2dfb92b5e0f784bd120636717ae5af41a06
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-plan.md sha256:a8840d5b1252cc88abd3a41ca64dc0a6d9955c354f0d7bf102857a5acb728eae
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit-2.md sha256:7af0adaae462c23d4f1318794a06bd3216bc2c54edb60b3f428f8057e67e932c
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-re-audit.md sha256:1b6d8f53d09ad53e29f874cc58bafe9d38981d1eb2cdab821ecf0d946d7d3c27
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-18-saas-46-supervisor-core-tasks.md sha256:dce9376bbdfe165e8334e597e44558b4c01b5b49675a689718cff0accf86dbc1
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-19-saas-46-supervisor-core-code-re-review-2.md sha256:5a23d6c93a41bbb7904c6389322048a8fc404c2812ba62c3b35d129cf3869a77
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-19-saas-46-supervisor-core-code-re-review-3.md sha256:7005aaa3f5654abe7be6c6c1eec0dee3f4cba898ee82f103ef4b9fd37e82511b
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/2026-07-19-saas-46-supervisor-core-code-re-review.md sha256:fc12e146275763fccee58f2184094bc911a76112915d2ba0826b14f591c549df
docs-ai/002-saas-46-supervisor-reservation-permissions-recov/workflow.json sha256:41bda53814d9afa91eb232138c45918ee9c86bfb355ed4d8865fdb39dd7ced2a
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
src/skills/linear-delivery-loop/references/supervisor-core.md sha256:ac57e7e1413ea0c0979682191db1cf0f685ad7700416a58016302b2d86f0e804
src/skills/linear-delivery-loop/references/supervisor-state.schema.json sha256:40bbf181b7d779c318013595b471c8c512fcb8edbc33e85476fb62b404a6e737
src/skills/linear-delivery-loop/references/trusted-observation.schema.json sha256:197f599704e3154ac643fda15a05e4f611e95403b2e73d28d3742e84a1736f64
src/skills/linear-delivery-loop/references/worker-result.schema.json sha256:f6e7b2f5adfb32ded82661cfd6caf6f23ceedd923d82b5b5bb6983c34efdf3d4
src/skills/linear-delivery-loop/scripts/__init__.py sha256:cd04adadb1f50ad19b1d4954930155838e9568940c276cac293a740ebcf03b03
src/skills/linear-delivery-loop/scripts/agent-worker-engine.ps1 sha256:875f70730e2b77b796ab09e6b65a15b798a15aa7b336696aa624e5a9367dde40
src/skills/linear-delivery-loop/scripts/assembled_handoff.py sha256:314b25f1d23abde4c9fb654fd7409673a6b61c7cfc131455243a58789f3f2d22
src/skills/linear-delivery-loop/scripts/base_runtime.py sha256:1951925a17174cb39e7fa969edbba66fdb280e66e6843c7825f87e8e72cda7e4
src/skills/linear-delivery-loop/scripts/cli.py sha256:a06fba5ca87343154b475646ef143b3a057765b9cb7911cc74864017612d104e
src/skills/linear-delivery-loop/scripts/contracts.py sha256:4fcfbaa809e3e8785dfecf6e971105f5e64cc6250587d6a3dea901b5677e68f9
src/skills/linear-delivery-loop/scripts/lease.py sha256:87f5ef1db33c2fcb02d8fcd1caef44102abd183ed352f4e6f36c4e7f043434ec
src/skills/linear-delivery-loop/scripts/operations.py sha256:60cb289776c44428bc5bd9a1d2d70b3f8109da112b6a8e8797e7e6aff8d8a1cd
src/skills/linear-delivery-loop/scripts/preflight.py sha256:c7fa9dfe9b0df31220f2a0a35bf9bbc6e7564f5b228237d9019912ee5b5f57a3
src/skills/linear-delivery-loop/scripts/recovery.py sha256:02f4eaf8a07380f4607282e49610734bdb81b0b23ee45c30a23611c220070f4b
src/skills/linear-delivery-loop/scripts/reservations.py sha256:906509a79633331ae52e0c690b525ce3f477af431cfc652cc50ada47d1b3702f
src/skills/linear-delivery-loop/scripts/store.py sha256:cce720d315b9bd8effa4aadbcea46c50c60138e16f087464390eee4c8423233c
src/skills/linear-delivery-loop/scripts/supervisor.py sha256:aacb02e65ab0dd07f9dce83faa9b2d943e959f013a121e15869bd1fd27c591f3
src/skills/linear-delivery-loop/scripts/worktrees.py sha256:fb969ef493adb9d98708245624668f08eb3d5673e13183ff42bfb6c238293492
src/skills/linear-delivery-loop/SKILL.md sha256:b29ec903fe168442aad2df66adb70707ccb5a8e70285de4782e3543e77cc028b
src/skills/spec-driven-delivery/SKILL.md sha256:1d9cf186217a34d6daf0d0f6c854cc520a4349a353a48ad56c2216d26d3a0eba
tests/linear_delivery_supervisor/__init__.py sha256:03944f753a49f7a34f4eca8369f14e56ff68e880bb9a7385a4da8c09ff67b226
tests/linear_delivery_supervisor/fixtures/preflight/passing-probe.template.json sha256:381c3719d341f3ceef0cb268215a3b53860dbccc1efd5105ea721587ff4d94a1
tests/linear_delivery_supervisor/support_state_engine.py sha256:6b4b1447a4d8353daae11cfd7538f584615aa5b046a93f3db21c4c5637af5f7c
tests/linear_delivery_supervisor/test_assembled_handoff.py sha256:576f512958dd0d9ea15aa2d5f1ac7d7fcabeb0e1c36787ee7fa84c3e950f3e95
tests/linear_delivery_supervisor/test_base_runtime.py sha256:c485085760d83f5592b9bee1a1bbbac1cd37750c260020cd549ffce53d901eac
tests/linear_delivery_supervisor/test_checkpoints.py sha256:7ee019123ce5294b7dc6c4e7ba1892eacef080daf64dda210b4ce80dc9410941
tests/linear_delivery_supervisor/test_cli_wrapper.py sha256:1b4caf877da68c28fd5485823d5dc77035a635b6556d5abe5445987630eff477
tests/linear_delivery_supervisor/test_contracts.py sha256:c9e2ac6eaa66e15bd01cfe0dbb9a3192c9473182ec2323289033f10602400067
tests/linear_delivery_supervisor/test_lease_capability.py sha256:8ca21db1bf9fd36077c70f516b6fdad8bd568b52d3c43166ab29d7469f4de05b
tests/linear_delivery_supervisor/test_operations.py sha256:744fc3beb42416f0ca135564e205bbc432e04455f02c4f5b8dca49858e7cca20
tests/linear_delivery_supervisor/test_preflight.py sha256:01e55df4dbf37c45fe151df000aad34c31e2e3e7bd53a9abb27d56174c891f03
tests/linear_delivery_supervisor/test_recovery_reconciliation.py sha256:2f0a8d8df96737d0fdf6872b90103c364b0337ded9df2f624041ef540e10337f
tests/linear_delivery_supervisor/test_reservations.py sha256:2758f7065d0f51210b975746549a0e76f3d75808e290f42f6cdf1811f1484de6
tests/linear_delivery_supervisor/test_status_cleanup.py sha256:fa846808bda3cf3bb11ef7c97a8d230a8424e7a450d594bd7868481165f5f2e9
tests/linear_delivery_supervisor/test_store_recovery.py sha256:e3f98f3ff462961034ee5605df69fe3f4320f8608cfd42d2280a6f75eb84ae97
tests/linear_delivery_supervisor/test_worktrees.py sha256:359cc1f67bf67421335dcb5ad7ad1de2165f5f63b01d674e9a413f6b9b34ad39
tests/test_delivery_contracts.py sha256:4e9f9130e900c029c6a294fd621ba5956bed8afcdd91f7551666388a1310ccb8
validation/delivery_contracts.py sha256:79a2daa68b32794630a6ac6abd173c46fa335f5063f458e0c33b19d69f51b79a
```

Overall target digest: `sha256:86137fe6f78e79986cd29fd13576f26dea392078f3b7921b668bfd1e2bb6a718`.
