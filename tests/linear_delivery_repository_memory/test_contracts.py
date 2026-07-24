from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from .support import *


class ContractTests(unittest.TestCase):
    def test_native_schema_validator_enforces_nested_local_refs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root)
            _, promotion = manifest(root, [item])
            record = candidate_to_record(promotion, item)
            schema = load_schema("repository-memory-record")
            extra = copy.deepcopy(record)
            extra["provenance"][0]["unexpected"] = True
            with self.assertRaisesRegex(ContractValidationError, "unknown fields"):
                validate_native(schema, extra)
            invalid_enum = copy.deepcopy(record)
            invalid_enum["provenance"][0]["kind"] = "unreviewed-source"
            with self.assertRaisesRegex(ContractValidationError, "allowed vocabulary"):
                validate_native(schema, invalid_enum)

    def test_schema_runtime_parity_and_acyclic_known_answers(self):
        assert_runtime_parity()
        self.assertEqual(canonical_json_bytes({"z": "é", "a": 1}), b'{"a":1,"z":"\\u00e9"}')
        self.assertEqual(sha256_canonical({"a": 1}), "sha256:015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862")
        answers = [
            ({"candidateId":"c","candidateIntentSha256":"x"}, candidate_intent_projection, b'{"candidateId":"c"}', "sha256:831c81edfd022bfb051c8e37270dce412a9bcfb461322e427d887c4984e8cacf"),
            ({"schemaVersion":"1.0","promotionManifestPayloadSha256":"x"}, promotion_manifest_payload_projection, b'{"schemaVersion":"1.0"}', "sha256:25dfef627915c779ee2feba03c09a85e7fffaf498a7a8cf19b0c70637c715f8e"),
            ({"recordId":"r","recordPayloadSha256":"x"}, record_payload_projection, b'{"recordId":"r"}', "sha256:685ab4de86ee612d355c91451f3796704963bf4a9fd1a2b24b3fe4e6cc14ac7f"),
            ({"batchPromotionId":"b","promotionBatchRequestSha256":"x"}, promotion_batch_request_projection, b'{"batchPromotionId":"b"}', "sha256:345c3a5e29fb64518d0cbc96be2333018cc8dc4aa9b1c04f090d254192a1c77d"),
            ({"batchPromotionId":"b","batchCommitPayloadSha256":"x"}, batch_commit_payload_projection, b'{"batchPromotionId":"b"}', "sha256:345c3a5e29fb64518d0cbc96be2333018cc8dc4aa9b1c04f090d254192a1c77d"),
            ({"builtAt":"t","entries":[],"indexSemanticSha256":"x"}, index_semantic_projection, b'{"entries":[]}', "sha256:d801aa1fb7ddcc330a5e3173372ea6af4a3d08ec58074478e85aa5603e926658"),
            ({"schemaVersion":"1.0","topics":[]}, retrieval_query_projection, b'{"schemaVersion":"1.0","topics":[]}', "sha256:f8e380510aaccd25397a18b2906f0a45adbf7c0564e697f0a70c3c7d7e3e4eef"),
            ({"schemaVersion":"1.0","items":[]}, retrieval_result_projection, b'{"items":[],"schemaVersion":"1.0"}', "sha256:ba8568df0d89d850a1f9b9374f811b3ac2b4d05a6cf31812faca9e9148b5b731"),
            ({"trust":"untrusted-data","contextPayloadSha256":"x"}, context_envelope_payload_projection, b'{"trust":"untrusted-data"}', "sha256:274e7d6d6b1e62a5aefd6b0a07d6eca6114f957077c1158e97a7322cd1ea9320"),
        ]
        for value, projection, expected_bytes, expected_hash in answers:
            projected = projection(value)
            self.assertEqual(canonical_json_bytes(projected), expected_bytes)
            self.assertEqual(sha256_canonical(projected), expected_hash)
            changed = {**projected, "tamper": True}
            self.assertNotEqual(sha256_canonical(changed), expected_hash)

    def test_record_typed_assertions_and_payload_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root)
            _, promotion = manifest(root, [item])
            record = candidate_to_record(promotion, item)
            validate_contract("repository-memory-record", record)
            tampered = copy.deepcopy(record)
            tampered["assertions"][0]["value"] = "3.12"
            with self.assertRaises(ContractValidationError):
                validate_contract("repository-memory-record", tampered)

    def test_manifest_rejects_changed_intent_and_unsorted_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            first = candidate(source, root, candidate_number=10)
            second = candidate(source, root, record_id="build-command", assertion_key="build.command", assertion_value="python scripts/build.py", candidate_number=9, promotion_number=21)
            _, promotion = manifest(root, [first, second])
            validate_contract("repository-memory-promotion", promotion)
            broken = copy.deepcopy(promotion)
            broken["candidates"].reverse()
            with self.assertRaises(ContractValidationError):
                validate_contract("repository-memory-promotion", broken)

    def test_secret_like_assertion_key_and_open_candidate_field_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root, assertion_key="api_key")
            _, promotion = manifest(root, [item])
            with self.assertRaisesRegex(Exception, "secret-like"):
                validate_contract("repository-memory-record", candidate_to_record(promotion, item))
            normal = candidate(source, root)
            normal["unexpected"] = True
            normal["candidateIntentSha256"] = sha256_canonical({key: value for key, value in normal.items() if key != "candidateIntentSha256"})
            _, open_manifest = manifest(root, [normal], batch_number=31)
            with self.assertRaisesRegex(ContractValidationError, "inventory|unknown fields"):
                validate_contract("repository-memory-promotion", open_manifest)

    def test_real_layer_projection_bytes_digests_and_included_excluded_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            item = candidate(source, root)
            manifest_path, promotion = manifest(root, [item], batch_number=160)
            committed = promote(root, manifest_path, promotion)
            fixture = binding(root)
            promotion_dir = fixture["engine"].store.root / "repository-memory" / "promotions" / promotion["batchPromotionId"]
            request = fixture["engine"].store.guard.read_json(promotion_dir / "journal.json")["promotionBatchRequest"]
            record = json.loads((root / item["targetPath"]).read_text(encoding="utf-8"))
            marker = json.loads((root / request["markerTargetPath"]).read_text(encoding="utf-8"))
            index = memory_engine(root).rebuild(persist=False)
            query = query_with_defaults({"repositoryId": fixture["manager"].identity.repository_id, "repositoryKey": REPOSITORY_KEY})
            retrieval = memory_engine(root).query(query)
            set_curation_stage(root, "plan")
            selectors = memory_engine(root).context_selectors(
                workflow_id=fixture["curation"]["workflowId"], issue_id=None,
                stage="planner", query=query,
            )
            delivery = compose_context(
                retrieval, authenticated=selectors, max_records=8,
                max_characters=12000, max_bytes=24576,
            )
            envelope = json.loads(delivery["tool"]["content"])

            validate_contract("repository-memory-batch-request", request)
            validate_contract("repository-memory-promotion-result", committed)
            layers = (
                (item, candidate_intent_projection, "candidateIntentSha256"),
                (promotion, promotion_manifest_payload_projection, "promotionManifestPayloadSha256"),
                (record, record_payload_projection, "recordPayloadSha256"),
                (request, promotion_batch_request_projection, "promotionBatchRequestSha256"),
                (marker, batch_commit_payload_projection, "batchCommitPayloadSha256"),
                (index, index_semantic_projection, "indexSemanticSha256"),
                (envelope, context_envelope_payload_projection, "contextPayloadSha256"),
            )
            for value, projection, digest_field in layers:
                projected = projection(value)
                expected_bytes = canonical_json_bytes(projected)
                self.assertEqual(expected_bytes, canonical_json_bytes(projection(copy.deepcopy(value))))
                self.assertEqual(value[digest_field], sha256_canonical(projected))
                excluded_tamper = copy.deepcopy(value)
                excluded_tamper[digest_field] = ZERO
                self.assertEqual(canonical_json_bytes(projection(excluded_tamper)), expected_bytes)
                included_tamper = copy.deepcopy(value)
                included_tamper["schemaVersion"] = "1.1"
                self.assertNotEqual(canonical_json_bytes(projection(included_tamper)), expected_bytes)

            self.assertEqual(retrieval["querySha256"], sha256_canonical(retrieval_query_projection(query)))
            self.assertNotEqual(
                canonical_json_bytes(retrieval_result_projection({**retrieval, "schemaVersion": "1.1"})),
                canonical_json_bytes(retrieval_result_projection(retrieval)),
            )
            accounting_bytes = canonical_json_bytes(context_delivery_accounting_projection(delivery))
            excluded_accounting = copy.deepcopy(delivery)
            excluded_accounting["accounting"]["charactersUsed"] = "999999"
            excluded_accounting["accounting"]["bytesUsed"] = "999999"
            self.assertEqual(canonical_json_bytes(context_delivery_accounting_projection(excluded_accounting)), accounting_bytes)
            included_accounting = copy.deepcopy(delivery)
            included_accounting["accounting"]["recordsUsed"] += 1
            self.assertNotEqual(canonical_json_bytes(context_delivery_accounting_projection(included_accounting)), accounting_bytes)

    def test_hard_link_reparse_alias_and_cross_state_assembly_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            first_root = parent / "first"
            second_root = parent / "second"
            initialize_repository(first_root)
            initialize_repository(second_root)
            external = parent / "external.json"
            external.write_text("{}", encoding="utf-8")
            linked = first_root / "docs" / "repository-memory" / "records" / "hard-linked.json"
            os.link(external, linked)
            with self.assertRaisesRegex(RepositoryMemoryRecordError, "hard-linked"):
                safe_repository_path(first_root, linked.relative_to(first_root).as_posix(), must_exist=True)

            symlinked = first_root / "docs" / "repository-memory" / "records" / "reparse.json"
            try:
                os.symlink(external, symlinked)
            except OSError:
                pass  # Windows without Developer Mode cannot create this fixture.
            else:
                with self.assertRaisesRegex(RepositoryMemoryRecordError, "symlink|escapes"):
                    safe_repository_path(first_root, symlinked.relative_to(first_root).as_posix(), must_exist=True)

            first = binding(first_root)
            second = binding(second_root)
            with self.assertRaisesRegex(RepositoryMemoryError, "canonical engine assembly"):
                RepositoryMemory(
                    first["manager"], store=second["engine"].store,
                    reservations=second["engine"].reservations,
                )


if __name__ == "__main__":
    unittest.main()
