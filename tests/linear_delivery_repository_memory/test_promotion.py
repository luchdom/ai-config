from __future__ import annotations

import copy
import tempfile
import threading
import subprocess
import json
import shutil
import sys
import unittest
from pathlib import Path

from .support import *


class PromotionTests(unittest.TestCase):
    def engine(self, root: Path) -> RepositoryMemory:
        return memory_engine(root)

    def test_atomic_marker_last_promotion_and_exact_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            items = [
                candidate(source, root, candidate_number=10),
                candidate(source, root, record_id="build-command", assertion_key="build.command", assertion_value="python scripts/build.py", candidate_number=11, promotion_number=21),
            ]
            path, value = manifest(root, items)
            engine = self.engine(root)
            authority = issue_authority(root, value)
            result = engine.promote(manifest_path=path, **authority)
            self.assertEqual(result["status"], "committed")
            self.assertEqual(len(result["records"]), 2)
            marker = root / "docs" / "repository-memory" / "commits" / f"{value['batchPromotionId']}.json"
            self.assertTrue(marker.is_file())
            replay = engine.promote(manifest_path=path, **authority)
            self.assertEqual(replay, result)

    def test_first_promotion_creates_missing_fixed_roots_safely(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            memory_root = root / "docs" / "repository-memory"
            (memory_root / "records").rmdir()
            (memory_root / "commits").rmdir()
            memory_root.rmdir()
            path, value = manifest(root, [candidate(source, root)], batch_number=41)
            result = promote(root, path, value)
            self.assertEqual(result["status"], "committed")
            self.assertTrue((root / value["candidates"][0]["targetPath"]).is_file())
            self.assertTrue((root / "docs" / "repository-memory" / "commits" / f"{value['batchPromotionId']}.json").is_file())

    def test_corrupt_cached_result_and_journal_are_reconstructed_from_valid_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            path, value = manifest(root, [candidate(source, root)], batch_number=42)
            authority = issue_authority(root, value)
            expected = memory_engine(root).promote(manifest_path=path, **authority)
            promotion_dir = binding(root)["engine"].store.root / "repository-memory" / "promotions" / value["batchPromotionId"]
            result_path = promotion_dir / "result.json"
            result_path.write_bytes(b'{"schemaVersion":"1.0","status":"committed"}')
            (promotion_dir / "journal.json").write_bytes(b"{not-json")
            replay = memory_engine(root).promote(manifest_path=path, **authority)
            self.assertEqual(replay, expected)
            self.assertEqual(
                validate_contract("repository-memory-promotion-result", json.loads(result_path.read_text(encoding="utf-8"))),
                expected,
            )

    def test_marker_recovers_after_complete_promotion_state_loss_and_consumed_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            path, value = manifest(root, [candidate(source, root)], batch_number=43)
            authority = issue_authority(root, value)
            expected = memory_engine(root).promote(manifest_path=path, **authority)
            fixture = binding(root)
            authorization_id = fixture["engine"].store.guard.read_json(
                authority["authorization_ref"]
            )["authorizationId"]
            self.assertIn(
                authorization_id,
                fixture["engine"].store.load_reservations()["consumedAuthorizationIds"],
            )
            promotion_dir = fixture["engine"].store.root / "repository-memory" / "promotions" / value["batchPromotionId"]
            shutil.rmtree(promotion_dir)
            replay = memory_engine(root).promote(manifest_path=path, **authority)
            self.assertEqual(replay, expected)
            self.assertTrue((promotion_dir / "result.json").is_file())
            self.assertFalse((promotion_dir / "journal.json").exists())

    def test_requested_valid_marker_recovers_beside_unrelated_malformed_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root)
            path, value = manifest(root, [item], batch_number=44)
            authority = issue_authority(root, value)
            memory_engine(root).promote(manifest_path=path, **authority)
            marker_root = root / "docs" / "repository-memory" / "commits"
            (marker_root / "unrelated-malformed.json").write_bytes(b"{not-json")
            promotion_dir = binding(root)["engine"].store.root / "repository-memory" / "promotions" / value["batchPromotionId"]
            (promotion_dir / "result.json").write_bytes(b"{not-json")
            (promotion_dir / "journal.json").write_bytes(b"{not-json")

            replay = memory_engine(root).promote(manifest_path=path, **authority)
            self.assertEqual(replay["status"], "committed")
            self.assertEqual(len(replay["records"]), 1)
            self.assertTrue((root / item["targetPath"]).is_file())
            index = memory_engine(root).rebuild(persist=False)
            self.assertEqual(len(index["entries"]), 1)
            self.assertEqual(index["diagnostics"]["invalid-marker-batch"], 1)
            self.assertEqual(index["diagnostics"].get("uncommitted-orphan", 0), 0)

    def test_marker_first_rejects_self_consistent_member_projection_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root)
            path, value = manifest(root, [item], batch_number=45)
            authority = issue_authority(root, value)
            memory_engine(root).promote(manifest_path=path, **authority)

            record_path = root / item["targetPath"]
            record = json.loads(record_path.read_text(encoding="utf-8"))
            replacement_id = "00000000-0000-4000-8000-000000000299"
            record["candidateId"] = replacement_id
            record["recordPayloadSha256"] = ZERO
            record["recordPayloadSha256"] = sha256_canonical(
                record_payload_projection(record)
            )
            write_canonical(record_path, record)

            marker_path = root / "docs" / "repository-memory" / "commits" / f"{value['batchPromotionId']}.json"
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["records"][0]["candidateId"] = replacement_id
            marker["records"][0]["recordPayloadSha256"] = record["recordPayloadSha256"]
            marker["records"][0]["recordFileSha256"] = digest(record_path)
            marker["batchCommitPayloadSha256"] = ZERO
            marker["batchCommitPayloadSha256"] = sha256_canonical(
                batch_commit_payload_projection(marker)
            )
            write_canonical(marker_path, marker)
            rebuilt = memory_engine(root).rebuild(persist=False)
            self.assertEqual(len(rebuilt["markers"]), 1)
            self.assertEqual(rebuilt["diagnostics"].get("invalid-marker-batch", 0), 0)

            promotion_dir = binding(root)["engine"].store.root / "repository-memory" / "promotions" / value["batchPromotionId"]
            (promotion_dir / "result.json").write_bytes(b"{not-json")
            with self.assertRaisesRegex(RepositoryMemoryError, "member projection"):
                memory_engine(root).promote(manifest_path=path, **authority)

    def test_valid_cached_result_cannot_commit_without_valid_marker_truth(self):
        for damage in ("missing", "corrupt"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = initialize_repository(root)
                item = candidate(source, root)
                path, value = manifest(
                    root, [item], batch_number=46 if damage == "missing" else 47
                )
                authority = issue_authority(root, value)
                committed = memory_engine(root).promote(manifest_path=path, **authority)
                promotion_dir = binding(root)["engine"].store.root / "repository-memory" / "promotions" / value["batchPromotionId"]
                cached = validate_contract(
                    "repository-memory-promotion-result",
                    json.loads((promotion_dir / "result.json").read_text(encoding="utf-8")),
                )
                self.assertEqual(cached, committed)
                marker_path = root / "docs" / "repository-memory" / "commits" / f"{value['batchPromotionId']}.json"
                if damage == "missing":
                    marker_path.unlink()
                else:
                    marker_path.write_bytes(b"{not-json")
                with self.assertRaises(Exception):
                    memory_engine(root).promote(manifest_path=path, **authority)
                self.assertTrue((root / item["targetPath"]).is_file())
                self.assertEqual(
                    validate_contract(
                        "repository-memory-promotion-result",
                        json.loads((promotion_dir / "result.json").read_text(encoding="utf-8")),
                    ),
                    committed,
                )

    def test_exact_scope_and_batch_duplicate_fail_before_consumption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            first = candidate(source, root, candidate_number=10)
            second = candidate(source, root, record_id="runtime-python-copy", candidate_number=11, promotion_number=21)
            path, value = manifest(root, [first, second])
            engine = self.engine(root)
            with self.assertRaisesRegex(RepositoryMemoryError, "scope"):
                engine.promote(manifest_path=path, **issue_authority(root, value, scope=[first["targetPath"]]))
            with self.assertRaisesRegex(RepositoryMemoryError, "duplicate-or-conflict"):
                engine.promote(manifest_path=path, **issue_authority(root, value))
            self.assertFalse(any((root / "docs" / "repository-memory" / "records").iterdir()))

    def test_current_delivery_source_requires_registry_identity_while_legacy_null_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root)
            path, current = manifest(root, [item], batch_number=70)
            current["sourceArtifacts"][1]["workflowId"] = None
            current["sourceArtifacts"][1]["workKey"] = None
            current["promotionManifestPayloadSha256"] = sha256_canonical(
                {key: value for key, value in current.items() if key != "promotionManifestPayloadSha256"}
            )
            write_canonical(root / path, current)
            authority = issue_authority(root, current)
            with self.assertRaisesRegex(RepositoryMemoryError, "registered completed workflow"):
                memory_engine(root).promote(manifest_path=path, **authority)
            authorization_id = binding(root)["engine"].store.guard.read_json(authority["authorization_ref"])["authorizationId"]
            self.assertNotIn(authorization_id, binding(root)["engine"].store.load_reservations()["consumedAuthorizationIds"])

            legacy_item = candidate(source, root, record_id="legacy-explicit", assertion_key="legacy.explicit", candidate_number=72, promotion_number=73)
            legacy_path, legacy = manifest(root, [legacy_item], batch_number=71)
            legacy["compatibilityClass"] = "legacy-completion-v1"
            legacy["sourceArtifacts"][1]["workflowId"] = None
            legacy["sourceArtifacts"][1]["workKey"] = None
            legacy["promotionManifestPayloadSha256"] = sha256_canonical(
                {key: value for key, value in legacy.items() if key != "promotionManifestPayloadSha256"}
            )
            write_canonical(root / legacy_path, legacy)
            result = memory_engine(root).promote(manifest_path=legacy_path, **issue_authority(root, legacy))
            self.assertEqual(result["status"], "committed")

    def test_prospective_graph_accepts_ordered_chain_and_rejects_double_successor_before_consumption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            first = candidate(source, root, record_id="chain", assertion_key="chain.value", assertion_value=1, value_type="integer", candidate_number=80, promotion_number=90)
            second = candidate(source, root, record_id="chain", version=2, assertion_key="chain.value", assertion_value=2, value_type="integer", candidate_number=81, promotion_number=91, supersedes=[{"recordId": "chain", "recordVersion": 1}])
            path, value = manifest(root, [first, second], batch_number=80)
            committed = memory_engine(root).promote(manifest_path=path, **issue_authority(root, value))
            self.assertEqual(len(committed["records"]), 2)
            index = memory_engine(root).rebuild(persist=False)
            entries = {(item["recordId"], item["recordVersion"]): item for item in index["entries"]}
            self.assertTrue(entries[("chain", 1)]["superseded"])
            self.assertFalse(entries[("chain", 2)]["invalidGraph"])

            bases = [
                candidate(source, root, record_id=f"fan-{offset}", assertion_key=f"fan.{offset}", assertion_value=offset, value_type="integer", candidate_number=100 + offset, promotion_number=110 + offset)
                for offset in range(3)
            ]
            base_path, base_value = manifest(root, bases, batch_number=81)
            prior = index["indexSemanticSha256"]
            memory_engine(root).promote(manifest_path=base_path, expected_prior_index_digest=prior, **issue_authority(root, base_value))
            branch_a = candidate(source, root, record_id="branch-a", assertion_key="branch.a", candidate_number=120, promotion_number=130, supersedes=[{"recordId": "fan-0", "recordVersion": 1}, {"recordId": "fan-1", "recordVersion": 1}])
            branch_b = candidate(source, root, record_id="branch-b", assertion_key="branch.b", candidate_number=121, promotion_number=131, supersedes=[{"recordId": "fan-0", "recordVersion": 1}, {"recordId": "fan-2", "recordVersion": 1}])
            branch_path, branch_value = manifest(root, [branch_a, branch_b], batch_number=82)
            prior = memory_engine(root).rebuild(persist=False)["indexSemanticSha256"]
            authority = issue_authority(root, branch_value)
            with self.assertRaisesRegex(RepositoryMemoryError, "nonterminal"):
                memory_engine(root).promote(manifest_path=branch_path, expected_prior_index_digest=prior, **authority)
            self.assertFalse((root / branch_a["targetPath"]).exists())
            authorization_id = binding(root)["engine"].store.guard.read_json(authority["authorization_ref"])["authorizationId"]
            self.assertNotIn(authorization_id, binding(root)["engine"].store.load_reservations()["consumedAuthorizationIds"])

    def test_manifest_and_source_replacement_at_mutex_boundary_fail_before_consumption(self):
        for replacement in ("manifest", "source"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = initialize_repository(root)
                path, value = manifest(root, [candidate(source, root)], batch_number=85)
                authority = issue_authority(root, value)
                fired = []
                def replace(phase):
                    if phase != "before-locked-manifest-reread" or fired:
                        return
                    fired.append(phase)
                    target = root / path if replacement == "manifest" else source
                    target.write_bytes(target.read_bytes() + b"\n")
                fixture = binding(root)
                subject = RepositoryMemory(
                    fixture["manager"], store=fixture["engine"].store,
                    reservations=fixture["engine"].reservations,
                    fault_injector=replace,
                )
                with self.assertRaisesRegex(RepositoryMemoryError, "changed while waiting|source digest is stale"):
                    subject.promote(manifest_path=path, **authority)
                authorization_id = fixture["engine"].store.guard.read_json(authority["authorization_ref"])["authorizationId"]
                self.assertNotIn(authorization_id, fixture["engine"].store.load_reservations()["consumedAuthorizationIds"])

    def test_no_candidates_is_durable_noop_without_authority_or_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_repository(root)
            path, value = manifest(root, [], no_candidates=True)
            engine = self.engine(root)
            result = engine.promote(manifest_path=path)
            self.assertEqual(result["status"], "no-candidates")
            self.assertEqual(result["records"], [])
            self.assertFalse((root / ".state" / "repository-memory" / "promotions" / value["batchPromotionId"] / "journal.json").exists())

    def test_concurrent_exact_replay_has_one_authority_consumer_and_one_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            path, value = manifest(root, [candidate(source, root)])
            engine = self.engine(root)
            barrier = threading.Barrier(2)
            results, errors = [], []
            authority = issue_authority(root, value)
            def run():
                try:
                    barrier.wait()
                    results.append(engine.promote(manifest_path=path, **authority))
                except Exception as exc:
                    errors.append(exc)
            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertEqual(errors, [])
            self.assertEqual(results[0], results[1])

    def test_maximum_32_candidate_batch_commits_as_one_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            items = [
                candidate(
                    source, root, record_id=f"record-{index:02d}",
                    assertion_key=f"item.{index}", assertion_value=index,
                    value_type="integer", candidate_number=100 + index,
                    promotion_number=200 + index,
                )
                for index in range(32)
            ]
            path, value = manifest(root, items)
            engine = self.engine(root)
            result = promote(root, path, value)
            self.assertEqual(len(result["records"]), 32)
            self.assertEqual(len(list((root / "docs" / "repository-memory" / "commits").glob("*.json"))), 1)

    def test_replay_recovers_representative_prepared_record_marker_index_result_boundaries(self):
        for phase in ("after-prepared", "after-record", "after-marker", "after-index", "before-result"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = initialize_repository(root)
                path, value = manifest(root, [candidate(source, root)])
                authority = issue_authority(root, value)
                fired = []
                def inject(observed):
                    if not fired and (observed == phase or (phase == "after-record" and observed.startswith("after-record:"))):
                        fired.append(observed)
                        raise RuntimeError("simulated process death")
                fixture = binding(root)
                crashing = RepositoryMemory(
                    fixture["manager"], store=fixture["engine"].store,
                    reservations=fixture["engine"].reservations,
                    fault_injector=inject,
                )
                with self.assertRaisesRegex(RuntimeError, "process death"):
                    crashing.promote(manifest_path=path, **authority)
                recovered = memory_engine(root).promote(manifest_path=path, **authority)
                self.assertIn(recovered["status"], {"committed", "index-reconstruction-required"})
                self.assertEqual(len(recovered["records"]), 1)

    def test_authority_transition_faults_never_make_journal_itself_authoritative(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            fixture = binding(root)
            phases = (
                ("transfer", "before-prepared-evidence", False),
                ("transfer", "after-prepared-evidence", False),
                ("transfer", "before-consumed-commit", False),
                ("store", "after-journal", False),
                ("store", "after-second-write", True),
                ("transfer", "before-opaque-cleanup", True),
            )
            for offset, (owner, phase, consumed_before_recovery) in enumerate(phases):
                with self.subTest(phase=phase):
                    item = candidate(
                        source, root, record_id=f"authority-fault-{offset}",
                        assertion_key=f"authority.fault.{offset}", assertion_value=offset,
                        value_type="integer", candidate_number=500 + offset,
                        promotion_number=600 + offset,
                    )
                    path, value = manifest(root, [item], batch_number=100 + offset)
                    authority = issue_authority(root, value)
                    current = fixture["memory"].rebuild(persist=False)
                    prior = current["indexSemanticSha256"] if current["markers"] else ZERO
                    fired = []
                    if owner == "transfer":
                        def transfer(observed, _operation):
                            if observed == phase and not fired:
                                fired.append(observed)
                                raise RuntimeError("authority transition fault")
                        fixture["engine"].reservations.transfer_fault_injector = transfer
                    else:
                        def store_fault(observed, _transaction):
                            if observed == phase and not fired:
                                fired.append(observed)
                                raise RuntimeError("authority transition fault")
                        fixture["engine"].store.fault_injector = store_fault
                    with self.assertRaisesRegex(RuntimeError, "authority transition fault"):
                        fixture["memory"].promote(
                            manifest_path=path, expected_prior_index_digest=prior,
                            **authority,
                        )
                    target = root / item["targetPath"]
                    marker = root / "docs" / "repository-memory" / "commits" / f"{value['batchPromotionId']}.json"
                    self.assertFalse(target.exists())
                    self.assertFalse(marker.exists())
                    raw_consumed = authority["authorization_ref"]
                    observed_ids = fixture["engine"].store.guard.read_json(
                        fixture["engine"].store.reservations_path
                    )["consumedAuthorizationIds"]
                    authorization_id = fixture["engine"].store.guard.read_json(raw_consumed)["authorizationId"]
                    self.assertEqual(authorization_id in observed_ids, consumed_before_recovery)
                    fixture["engine"].reservations.transfer_fault_injector = None
                    fixture["engine"].store.fault_injector = None
                    recovered = fixture["memory"].promote(
                        manifest_path=path, expected_prior_index_digest=prior,
                        **authority,
                    )
                    self.assertEqual(recovered["status"], "committed")

    def test_actual_process_termination_after_prepared_journal_requires_authoritative_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root, record_id="terminated-authority", assertion_key="authority.terminated")
            path, value = manifest(root, [item], batch_number=140)
            authority = issue_authority(root, value)
            arguments = {key: str(item) if isinstance(item, Path) else item for key, item in authority.items()}
            code = r'''
import importlib,importlib.util,json,os,sys
from pathlib import Path
scripts_root=Path(sys.argv[1])/"scripts"; package_name="repository_memory_child_runtime"
spec=importlib.util.spec_from_file_location(package_name,scripts_root/"__init__.py",submodule_search_locations=[str(scripts_root)])
package=importlib.util.module_from_spec(spec); sys.modules[package_name]=package; spec.loader.exec_module(package)
load_base_runtime=importlib.import_module(package_name+".base_runtime").load_base_runtime
SupervisorEngine=importlib.import_module(package_name+".supervisor").SupervisorEngine
RepositoryMemory=importlib.import_module(package_name+".repository_memory").RepositoryMemory
root=Path(sys.argv[2]); args=json.loads(sys.argv[4])
manager=load_base_runtime().WorkflowManager(root,repository_key="ai-config",state_home_override=root.parent/"state")
engine=SupervisorEngine(manager=manager)
engine.reservations.transfer_fault_injector=lambda stage,_operation: os._exit(91) if stage=="after-prepared-evidence" else None
RepositoryMemory(manager,store=engine.store,reservations=engine.reservations).promote(manifest_path=sys.argv[3],**args)
'''
            process = subprocess.run(
                [sys.executable, "-c", code, str(PACKAGE), str(root), path, json.dumps(arguments)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(process.returncode, 91, (process.stdout, process.stderr))
            self.assertFalse((root / item["targetPath"]).exists())
            consumed = binding(root)["engine"].store.load_reservations()["consumedAuthorizationIds"]
            authorization_id = binding(root)["engine"].store.guard.read_json(authority["authorization_ref"])["authorizationId"]
            self.assertNotIn(authorization_id, consumed)
            recovered = memory_engine(root).promote(manifest_path=path, **authority)
            self.assertEqual(recovered["status"], "committed")

    def test_cross_process_contenders_converge_on_one_committed_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            path, value = manifest(root, [candidate(source, root)])
            authority = issue_authority(root, value)
            arguments = {key: str(item) if isinstance(item, Path) else item for key, item in authority.items()}
            code = r'''
import importlib,importlib.util,json,sys
from pathlib import Path
scripts_root=Path(sys.argv[1])/"scripts"; package_name="repository_memory_contender_runtime"
spec=importlib.util.spec_from_file_location(package_name,scripts_root/"__init__.py",submodule_search_locations=[str(scripts_root)])
package=importlib.util.module_from_spec(spec); sys.modules[package_name]=package; spec.loader.exec_module(package)
load_base_runtime=importlib.import_module(package_name+".base_runtime").load_base_runtime
SupervisorEngine=importlib.import_module(package_name+".supervisor").SupervisorEngine
RepositoryMemory=importlib.import_module(package_name+".repository_memory").RepositoryMemory
root=Path(sys.argv[2]); args=json.loads(sys.argv[4])
manager=load_base_runtime().WorkflowManager(root,repository_key="ai-config",state_home_override=root.parent/"state")
engine=SupervisorEngine(manager=manager)
result=RepositoryMemory(manager,store=engine.store,reservations=engine.reservations).promote(manifest_path=sys.argv[3],**args)
print(json.dumps(result,sort_keys=True))
'''
            command = [sys.executable, "-c", code, str(PACKAGE), str(root), path, json.dumps(arguments)]
            processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
            outputs = [process.communicate(timeout=45) for process in processes]
            self.assertEqual([process.returncode for process in processes], [0, 0], outputs)
            results = [json.loads(stdout) for stdout, _stderr in outputs]
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0]["status"], "committed")


if __name__ == "__main__":
    unittest.main()
