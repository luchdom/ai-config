from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

from .support import *


class IndexTests(unittest.TestCase):
    def engine(self, root: Path) -> RepositoryMemory:
        return memory_engine(root)

    def test_invalid_ancestry_quarantines_every_descendant(self):
        def wrapped(record_id, version, predecessors):
            return {"record": {
                "recordId": record_id, "recordVersion": version,
                "supersedes": [
                    {"recordId": predecessor_id, "recordVersion": predecessor_version}
                    for predecessor_id, predecessor_version in predecessors
                ],
                "restores": None, "lifecycle": "active",
            }}

        records = [
            wrapped("broken", 1, [("missing", 1)]),
            wrapped("child", 1, [("broken", 1)]),
            wrapped("grandchild", 1, [("child", 1)]),
        ]
        diagnostics = Counter()
        successors, invalid = graph_projection(records, diagnostics)
        self.assertEqual(
            invalid,
            {("broken", 1), ("child", 1), ("grandchild", 1)},
        )
        self.assertEqual(successors, {})
        self.assertEqual(diagnostics["invalid-ancestry"], 2)

    def promote(self, engine, root, items, batch):
        path, value = manifest(root, items, batch_number=batch)
        prior = engine.rebuild(persist=False)
        expected = prior["indexSemanticSha256"] if prior["markers"] else ZERO
        return promote(root, path, value, expected=expected)

    def test_forward_supersession_derives_terminal_and_reverse_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            engine = self.engine(root)
            self.promote(engine, root, [candidate(source, root)], 30)
            successor = candidate(source, root, version=2, assertion_value="3.14", candidate_number=12, promotion_number=22, supersedes=[{"recordId": "runtime-python", "recordVersion": 1}])
            self.promote(engine, root, [successor], 31)
            index = engine.rebuild(persist=False)
            entries = {(item["recordId"], item["recordVersion"]): item for item in index["entries"]}
            self.assertTrue(entries[("runtime-python", 1)]["superseded"])
            self.assertEqual(entries[("runtime-python", 1)]["successor"], {"recordId": "runtime-python", "recordVersion": 2})
            self.assertFalse(entries[("runtime-python", 2)]["superseded"])

    def test_same_scope_assertion_superset_is_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            engine = self.engine(root)
            first = candidate(source, root)
            second = candidate(source, root, record_id="runtime-and-build", candidate_number=11, promotion_number=21)
            second["assertions"].append({"key": "validation.command", "valueType": "string", "comparison": "equals", "value": "python scripts/validate.py", "provenanceRefs": ["guide"]})
            second["assertions"].sort(key=lambda item: item["key"])
            second["candidateIntentSha256"] = sha256_canonical({key: item for key, item in second.items() if key != "candidateIntentSha256"})
            self.promote(engine, root, [first, second], 30)
            index = engine.rebuild(persist=False)
            terminal = [item for item in index["entries"] if not item["superseded"]]
            self.assertEqual(len(terminal), 2)
            self.assertTrue(all(not item["duplicateMembers"] for item in terminal))

    def test_invalid_marker_excludes_whole_batch_and_orphan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = initialize_repository(root)
            engine = self.engine(root)
            result = self.promote(engine, root, [candidate(source, root)], 30)
            marker = root / "docs" / "repository-memory" / "commits" / "00000000-0000-4000-8000-00000000001e.json"
            marker.write_bytes(marker.read_bytes().replace(b'"recordFileSha256":"sha256:', b'"recordFileSha256":"sha256:f'))
            index = engine.rebuild(persist=False)
            self.assertEqual(index["entries"], [])
            self.assertEqual(index["diagnostics"]["invalid-marker-batch"], 1)
            self.assertEqual(index["diagnostics"]["uncommitted-orphan"], 1)


if __name__ == "__main__":
    unittest.main()
