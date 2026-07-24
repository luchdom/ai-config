from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .support import *


class QueryTests(unittest.TestCase):
    def setup_memory(self, root: Path):
        source = initialize_repository(root)
        engine = memory_engine(root)
        items = [
            candidate(source, root, title="Python é runtime", summary="Use Python é safely.", candidate_number=10),
            candidate(source, root, record_id="build-command", assertion_key="build.command", assertion_value="python scripts/build.py", title="Build", summary="Canonical build command.", candidate_number=11, promotion_number=21),
        ]
        path, value = manifest(root, items)
        promote(root, path, value)
        return engine, source

    def query(self, root):
        return {"repositoryId": binding(root)["manager"].identity.repository_id, "repositoryKey": REPOSITORY_KEY, "work": None, "stage": "implementer", "paths": ["src/tools"], "topics": ["python"], "maxRecords": 8, "maxCharacters": 12000, "maxBytes": 24576, "includeLegacy": False}

    def test_filter_rank_provenance_and_repeat_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine, _ = self.setup_memory(root)
            first = engine.query(self.query(root))
            second = engine.query(self.query(root))
            self.assertEqual(first, second)
            self.assertEqual([item["recordId"] for item in first["items"]], ["build-command", "runtime-python"])
            self.assertEqual(first["accounting"]["recordsUsed"], 2)
            self.assertEqual(first["accounting"]["bytesUsed"], len(canonical_json_bytes(first)))
            self.assertTrue(all(item["provenance"] for item in first["items"]))

    def test_source_digest_drift_excludes_without_leaking_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine, source = self.setup_memory(root)
            source.write_text("changed", encoding="utf-8")
            result = engine.query(self.query(root))
            self.assertEqual(result["items"], [])
            self.assertEqual(result["diagnostics"]["stale"], 2)

    def test_minimum_budget_omits_whole_items_without_truncation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine, _ = self.setup_memory(root)
            query = self.query(root)
            query.update({"maxRecords": 1, "maxCharacters": 1000, "maxBytes": 4096})
            result = engine.query(query)
            self.assertLessEqual(len(result["items"]), 1)
            self.assertLessEqual(result["accounting"]["charactersUsed"], 1000)
            self.assertLessEqual(result["accounting"]["bytesUsed"], 4096)


if __name__ == "__main__":
    unittest.main()
