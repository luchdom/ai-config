from __future__ import annotations

import copy
import json
import os
import re
import unittest
import unicodedata
import uuid
from pathlib import Path

from tests.goal_to_delivery_base.support import REPOSITORY_ROOT
from scripts.descriptor import validate_descriptor
from scripts.errors import ValidationError
from scripts.redaction import redact_value


SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "src"
    / "skills"
    / "goal-to-delivery"
    / "references"
    / "work-descriptor.schema.json"
)


def _base_descriptor() -> dict:
    return {
        "schemaVersion": "2.0",
        "revision": 1,
        "workflowId": str(uuid.uuid4()),
        "workflow": "manual",
        "workSource": "local",
        "workKey": "001",
        "slug": "schema-parity",
        "repositoryKey": "test-repository",
        "repositoryRoot": str(Path(REPOSITORY_ROOT).resolve()),
        "goal": "Exercise schema and runtime parity",
        "acceptanceCriteria": [],
        "nonGoals": [],
        "tracking": {"provider": "none", "externalId": None},
        "completionBoundary": "working-tree",
        "physicalWorktreeFingerprint": "sha256:" + "a" * 64,
        "riskFlags": [],
        "artifactFolder": str(
            (
                REPOSITORY_ROOT
                / ".ai"
                / "work"
                / "2026-08-18--local-001--schema-parity"
            ).resolve()
        ),
        "artifactInventory": ["workflow.json"],
        "currentArtifactStage": "initialized",
        "assumptionsDecisionRefs": [],
        "design": {"required": False, "reason": "No UI change."},
        "deliverySummary": {},
        "supersededArtifactNames": [],
    }


def _json_type_matches(expected: str, value: object) -> bool:
    return {
        "array": isinstance(value, list),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "null": value is None,
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
    }[expected]


def _native_schema_accepts(schema: dict, value: object) -> bool:
    expected_types = schema.get("type")
    if isinstance(expected_types, str) and not _json_type_matches(expected_types, value):
        return False
    if isinstance(expected_types, list) and not any(_json_type_matches(item, value) for item in expected_types):
        return False
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if isinstance(value, int) and not isinstance(value, bool) and value < schema.get("minimum", value):
        return False
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            return False
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            return False
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            return False
        if "items" in schema and any(not _native_schema_accepts(schema["items"], item) for item in value):
            return False
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        if not required.issubset(value):
            return False
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            return False
        for name, property_schema in properties.items():
            if name in value and not _native_schema_accepts(property_schema, value[name]):
                return False
    if "oneOf" in schema and sum(_native_schema_accepts(option, value) for option in schema["oneOf"]) != 1:
        return False
    for condition in schema.get("allOf", []):
        if _native_schema_accepts(condition.get("if", {}), value):
            if not _native_schema_accepts(condition.get("then", {}), value):
                return False
    return True


WINDOWS_INVALID = set('<>:"/\\|?*')
WINDOWS_DEVICE = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.I)


def _safe_component(component: str) -> bool:
    return bool(
        component
        and component not in {".", ".."}
        and component == unicodedata.normalize("NFC", component)
        and not any(unicodedata.category(character) == "Cc" for character in component)
        and not any(character in WINDOWS_INVALID for character in component)
        and not component.endswith((".", " "))
        and not WINDOWS_DEVICE.fullmatch(component)
    )


def _safe_relative_paths(values: object) -> bool:
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        return False
    if len({unicodedata.normalize("NFC", value).casefold() for value in values}) != len(values):
        return False
    return all(
        value
        and value == value.strip()
        and "\\" not in value
        and not value.startswith("/")
        and all(_safe_component(component) for component in value.split("/"))
        for value in values
    )


def _safe_single_names(values: object) -> bool:
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        return False
    if len({unicodedata.normalize("NFC", value).casefold() for value in values}) != len(values):
        return False
    return all(value == value.strip() and "/" not in value and "\\" not in value and _safe_component(value) for value in values)


def _pointer(value: dict, pointer: str) -> object:
    current: object = value
    for part in pointer.strip("/").split("/") if pointer else ():
        if not isinstance(current, dict) or part not in current:
            return object()
        current = current[part]
    return current


def _runtime_extension_accepts(extension: dict, descriptor: dict) -> bool:
    for constraint in extension["constraints"]:
        applies = constraint.get("appliesWhen")
        if applies and _pointer(descriptor, applies["jsonPointer"]) != applies["value"]:
            continue
        operator = constraint["operator"]
        if operator == "equals":
            accepted = _pointer(descriptor, constraint["leftJsonPointer"]) == _pointer(
                descriptor, constraint["rightJsonPointer"]
            )
        elif operator == "os-path-is-absolute":
            candidate = _pointer(descriptor, constraint["jsonPointer"])
            accepted = isinstance(candidate, str) and os.path.isabs(candidate)
        elif operator == "not-windows-device-name":
            candidate = _pointer(descriptor, constraint["jsonPointer"])
            accepted = isinstance(candidate, str) and WINDOWS_DEVICE.fullmatch(candidate) is None
        elif operator == "redaction-is-identity":
            accepted = redact_value(descriptor) == descriptor
        elif operator == "unique-safe-relative-file-paths-windows-casefold":
            accepted = _safe_relative_paths(_pointer(descriptor, constraint["jsonPointer"]))
        elif operator == "unique-safe-single-names-windows-casefold":
            accepted = _safe_single_names(_pointer(descriptor, constraint["jsonPointer"]))
        else:
            raise AssertionError(f"Unrecognized runtime parity operator: {operator}")
        if not accepted:
            return False
    return True


def _schema_contract_accepts(schema: dict, descriptor: dict) -> bool:
    return _native_schema_accepts(schema, descriptor) and _runtime_extension_accepts(
        schema["x-luchdom-runtimeParity"], descriptor
    )


def _runtime_accepts(descriptor: dict) -> bool:
    try:
        validate_descriptor(descriptor)
        return True
    except ValidationError:
        return False


class WorkDescriptorSchemaParityTests(unittest.TestCase):
    def test_schema_inventories_every_runtime_only_descriptor_constraint(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        extension = schema["x-luchdom-runtimeParity"]
        self.assertEqual(extension["version"], "2.0")
        self.assertEqual(extension["runtimeValidator"], "scripts.descriptor.validate_descriptor")
        constraints = {item["id"]: item for item in extension["constraints"]}
        self.assertEqual(
            set(constraints),
            {
                "linear-work-key-equals-external-id",
                "repository-root-observed-absolute-path",
                "artifact-folder-absolute-path",
                "slug-not-windows-reserved-device",
                "descriptor-contains-no-secret-like-material",
                "artifact-inventory-canonical-safe-relative-paths",
                "superseded-artifact-names-canonical-safe-single-names",
            },
        )
        equality = constraints["linear-work-key-equals-external-id"]
        self.assertEqual(equality["operator"], "equals")
        self.assertEqual(equality["leftJsonPointer"], "/workKey")
        self.assertEqual(equality["rightJsonPointer"], "/tracking/externalId")
        self.assertEqual(equality["runtimeValidator"], "scripts.descriptor.validate_descriptor")

    def test_schema_extension_and_runtime_match_every_policy_source_key_tracking_combination(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        keys = ("001", "SAAS-123")
        trackings = (
            {"provider": "none", "externalId": None},
            {"provider": "linear", "externalId": "SAAS-123"},
            {"provider": "linear", "externalId": "SAAS-999"},
        )
        for workflow in ("manual", "semi-autonomous", "autonomous"):
            for source in ("local", "linear"):
                for key in keys:
                    for tracking in trackings:
                        descriptor = _base_descriptor()
                        descriptor["workflow"] = workflow
                        descriptor["workSource"] = source
                        descriptor["workKey"] = key
                        descriptor["tracking"] = copy.deepcopy(tracking)
                        schema_accepts = _schema_contract_accepts(schema, descriptor)
                        runtime_accepts = _runtime_accepts(descriptor)
                        with self.subTest(
                            workflow=workflow,
                            source=source,
                            key=key,
                            tracking=tracking,
                        ):
                            self.assertEqual(schema_accepts, runtime_accepts)

    def test_native_and_runtime_constraints_match_representative_matrix(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cases = {
            "baseline": (lambda value: None, True),
            "whitespace-goal": (lambda value: value.__setitem__("goal", " \t "), False),
            "whitespace-design-reason": (
                lambda value: value.__setitem__("design", {"required": False, "reason": "  "}),
                False,
            ),
            "relative-repository-root": (lambda value: value.__setitem__("repositoryRoot", "relative/repo"), False),
            "relative-artifact-folder": (
                lambda value: value.__setitem__("artifactFolder", ".ai/work/schema-parity"),
                False,
            ),
            "design-review-stage": (
                lambda value: value.__setitem__("currentArtifactStage", "design_review"),
                True,
            ),
            "unknown-artifact-stage": (
                lambda value: value.__setitem__("currentArtifactStage", "visual_review"),
                False,
            ),
            "uppercase-uuid": (lambda value: value.__setitem__("workflowId", str(uuid.uuid4()).upper()), False),
            "windows-reserved-slug": (lambda value: value.__setitem__("slug", "con"), False),
            "secret-like-material": (
                lambda value: value.__setitem__("goal", "authorization=Bearer abc.def"),
                False,
            ),
            "safe-artifact-inventory": (
                lambda value: value.__setitem__(
                    "artifactInventory", ["workflow.json", "src/API/File.cs", ".ai/work/plan.md"]
                ),
                True,
            ),
            "safe-superseded-names": (
                lambda value: value.__setitem__("supersededArtifactNames", ["old-plan.md", "README"]),
                True,
            ),
        }
        for name, (mutate, expected) in cases.items():
            descriptor = _base_descriptor()
            mutate(descriptor)
            with self.subTest(case=name):
                self.assertEqual(expected, _schema_contract_accepts(schema, descriptor))
                self.assertEqual(expected, _runtime_accepts(descriptor))

    def test_artifact_inventory_schema_runtime_matrix(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cases = (
            (["workflow.json"], True),
            (["workflow.json", "src/Feature/File.cs", ".ai/work/qa.md"], True),
            (["/absolute/file.md"], False),
            (["C:/absolute/file.md"], False),
            (["../escape.md"], False),
            (["folder/../escape.md"], False),
            (["./file.md"], False),
            (["folder//file.md"], False),
            ([r"folder\file.md"], False),
            (["folder/file?.md"], False),
            (["folder/name\u0085.md"], False),
            (["CON/file.md"], False),
            (["folder/NUL.txt"], False),
            (["folder/name."], False),
            (["folder/name "], False),
            (["README.md", "readme.md"], False),
            (["workflow.json", "workflow.json"], False),
        )
        for inventory, expected in cases:
            descriptor = _base_descriptor()
            descriptor["artifactInventory"] = inventory
            with self.subTest(inventory=inventory):
                self.assertEqual(expected, _schema_contract_accepts(schema, descriptor))
                self.assertEqual(expected, _runtime_accepts(descriptor))

    def test_superseded_artifact_names_schema_runtime_matrix(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cases = (
            ([], True),
            (["old-plan.md", "README"], True),
            (["/absolute.md"], False),
            ([r"folder\old.md"], False),
            (["folder/old.md"], False),
            (["."], False),
            ([".."], False),
            (["CON"], False),
            (["nul.txt"], False),
            (["bad?.md"], False),
            (["name\u0085.md"], False),
            (["name."], False),
            (["name "], False),
            (["Old.md", "old.md"], False),
            (["old.md", "old.md"], False),
        )
        for names, expected in cases:
            descriptor = _base_descriptor()
            descriptor["supersededArtifactNames"] = names
            with self.subTest(names=names):
                self.assertEqual(expected, _schema_contract_accepts(schema, descriptor))
                self.assertEqual(expected, _runtime_accepts(descriptor))
