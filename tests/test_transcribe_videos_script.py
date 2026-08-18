import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "skills" / "transcribe-videos" / "scripts" / "transcribe_media.py"
SPEC = importlib.util.spec_from_file_location("transcribe_media", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TranscribeVideosScriptTests(unittest.TestCase):
    def test_http_url_detection_does_not_treat_urls_as_windows_paths(self) -> None:
        self.assertTrue(MODULE.is_http_url("https://example.test/watch?v=123"))
        self.assertFalse(MODULE.is_http_url(r"C:\videos\sample.mp4"))

    def test_slugify_normalizes_accented_titles(self) -> None:
        self.assertEqual(
            MODULE.slugify("Lesson 04 — Café, Sleep & Timing"),
            "lesson-04-cafe-sleep-timing",
        )

    def test_load_manifest_accepts_items_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "slug": "aula-01",
                                "title": "Lesson 01",
                                "input": "https://example.test/media.m3u8",
                                "direct_media": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            jobs = MODULE.load_manifest(manifest)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].slug, "aula-01")
        self.assertTrue(jobs[0].direct_media)

    def test_load_manifest_rejects_duplicate_slugs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    [
                        {"slug": "same", "input": "https://example.test/one"},
                        {"slug": "same", "input": "https://example.test/two"},
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate slugs"):
                MODULE.load_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
