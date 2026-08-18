from __future__ import annotations

from pathlib import Path
import os
import subprocess
from unittest import mock

from tests.goal_to_delivery_base.support import RepositoryTestCase
from scripts.errors import CollisionError, UnsafePathError, ValidationError
from scripts.path_safety import (
    ensure_safe_descendant,
    normalize_slug,
    reject_case_insensitive_collision,
    validate_current_artifact_folder_name,
    validate_local_key,
    validate_provider_key,
    validate_slug,
)


class PathSafetyTests(RepositoryTestCase):
    def test_canonical_provider_and_allocator_keys_are_distinct(self) -> None:
        self.assertEqual(validate_provider_key("linear", "SAAS-123"), "SAAS-123")
        self.assertEqual(validate_local_key("001"), "001")
        for invalid in ("SAAS-0", "saas-1", "001", "SAAS-01"):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                validate_provider_key("linear", invalid)
        for invalid in ("1", "01", "SAAS-123", "001x"):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                validate_local_key(invalid)

    def test_slug_boundaries_and_normalization(self) -> None:
        self.assertEqual(validate_slug("a"), "a")
        self.assertEqual(validate_slug("a" * 48), "a" * 48)
        with self.assertRaises(ValidationError):
            validate_slug("a" * 49)
        self.assertEqual(normalize_slug("PKCE Authorization Flow"), "pkce-authorization-flow")

    def test_unsafe_explicit_values_never_become_paths(self) -> None:
        invalid = [
            ".", "..", "folder/name", "folder\\name", "bad<name", "bad>name", "bad:name",
            'bad"name', "bad|name", "bad?name", "bad*name", "trailing.", "trailing ", "line\nfeed",
        ]
        invalid.extend(["CON", "prn", "AUX", "nul"])
        invalid.extend([f"COM{number}" for number in range(1, 10)])
        invalid.extend([f"lpt{number}" for number in range(1, 10)])
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                normalize_slug(value)

    def test_case_insensitive_collision_is_rejected(self) -> None:
        with self.assertRaises(CollisionError):
            reject_case_insensitive_collision("001-pkce", {"001-PKCE"})

    def test_current_folder_name_is_bound_to_descriptor_identity(self) -> None:
        validate_current_artifact_folder_name(
            "2026-08-18--local-001--pkce--02",
            work_source="local",
            work_key="001",
            slug="pkce",
        )
        invalid = (
            "2026-08-18--local-002--pkce",
            "2026-02-30--local-001--pkce",
            "2026-08-18--local-001--pkce--01",
        )
        for folder in invalid:
            with self.subTest(folder=folder), self.assertRaises(ValidationError):
                validate_current_artifact_folder_name(
                    folder,
                    work_source="local",
                    work_key="001",
                    slug="pkce",
                )

    def test_strict_containment_rejects_traversal(self) -> None:
        docs_root = self.repository / "artifact-root"
        docs_root.mkdir()
        with self.assertRaises(UnsafePathError):
            ensure_safe_descendant(docs_root, docs_root / ".." / "escape")
        with self.assertRaises(UnsafePathError):
            ensure_safe_descendant(docs_root, docs_root)

    def test_reparse_component_is_rejected_before_or_after_creation(self) -> None:
        docs_root = self.repository / "artifact-root"
        docs_root.mkdir()
        candidate = docs_root / "001-safe"
        candidate.mkdir()
        with mock.patch("scripts.path_safety.is_reparse_point", side_effect=lambda path: path == candidate):
            with self.assertRaises(UnsafePathError):
                ensure_safe_descendant(docs_root, candidate, candidate_may_not_exist=False)

    def test_actual_windows_junction_escape_is_rejected_when_os_permits_creation(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows junction coverage applies only on Windows")
        docs_root = self.repository / "artifact-root"
        docs_root.mkdir()
        outside = self.root / "junction-target"
        outside.mkdir()
        junction = docs_root / "escape"
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=False,
        )
        if completed.returncode != 0:
            self.skipTest(f"Windows denied junction creation: {completed.stderr or completed.stdout}")
        with self.assertRaises(UnsafePathError):
            ensure_safe_descendant(docs_root, junction / "001-escape")
