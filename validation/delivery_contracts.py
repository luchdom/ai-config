"""Semantic checks for the shared delivery protocol and its projections."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


CANONICAL_REFERENCES = (
    "delivery-stages.md",
    "design-gates.md",
    "artifact-contract.md",
    "clarification-policy.md",
    "quality-gates.md",
    "completion-boundaries.md",
    "worktree-policy.md",
    "work-descriptor.schema.json",
)
ENTRY_SKILLS = ("goal-to-delivery", "spec-driven-delivery", "linear-delivery-loop")
SPECIALIST_AGENTS = (
    "planner",
    "product-designer",
    "tasker",
    "auditor",
    "dotnet",
    "nextjs-mui",
    "react",
    "jekyll-site-builder",
    "code-reviewer",
    "qa",
)
GUIDANCE_FILES = (
    "AGENTS.md",
    "README.md",
    "src/tool-instructions/codex/AGENTS.md",
    "src/tool-instructions/claude/CLAUDE.md",
    "src/tool-instructions/copilot/.github/copilot-instructions.md",
    "src/tool-instructions/cursor/AGENTS.md",
)
FORBIDDEN_OPERATIONAL_PATTERNS = (
    ("retired state name", re.compile(r"\bReady for Codex\b", re.IGNORECASE)),
    ("retired notification channel", re.compile(r"\b(?:Slack|Telegram)\b", re.IGNORECASE)),
    ("retired SaaS issue prefix", re.compile(r"\bLUC-(?:[1-9][0-9]*|\*)", re.IGNORECASE)),
    (
        "retired protocol ownership wording",
        re.compile(r"portable summaries,?\s+not the source of truth", re.IGNORECASE),
    ),
)
OLD_LAYOUT_PATTERN = re.compile(
    r"docs" + r"-ai/<(?:NNN|[Nn]{3})>-<(?:short-feature-name|slug)>-<YYYY-MM-DD>",
    re.IGNORECASE,
)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DOCTRINE_BLOCK_MIN_LENGTH = 120
TEXT_SUFFIXES = {".json", ".md", ".mdc", ".py", ".toml", ".txt", ".yaml", ".yml"}

# Each digest identifies one exact stripped source line and its reviewed purpose.
# Generated projections are mapped back to their canonical source before lookup.
# Keep this narrow: adding or changing a legacy literal requires an explicit review here.
DOCS_AI_ALLOWED_PURPOSES = frozenset(
    ("legacy runtime compatibility", "intentional legacy test", "classified history")
)
DOCS_AI_ALLOWLIST: dict[str, dict[str, frozenset[str]]] = {
    "AGENTS.md": {
        "legacy runtime compatibility": frozenset(
            {"e300897cfebba5099aec32422a44cff0e182353f3fc4caefa93978296ef36ceb"}
        )
    },
    "README.md": {
        "legacy runtime compatibility": frozenset(
            {"c3024d51ad95cc2b6810d47eb0e85924f0e72da18ea53d2c4a8ce6f59a0cb68b"}
        )
    },
    "src/skills/goal-to-delivery/references/artifact-contract.md": {
        "legacy runtime compatibility": frozenset(
            {"60b8e0b7d2829676c3a3f873556df074d82d9846fc55f663047b6a47adadf71d"}
        ),
        "classified history": frozenset(
            {"0969aa7926b8f14f63757838691918d124f7535c55b4b88a39db1a4c17490b8b"}
        ),
    },
    "src/skills/goal-to-delivery/scripts/descriptor.py": {
        "classified history": frozenset(
            {
                "56481291618293162e3dbd91dcb66c0b447b3e468ecc31f77916d428ce54f37c",
                "fd769173d8485ec017aaf25b1636ee4eacaa8c758ec6c4d9949d72599f4fd8ea",
            }
        )
    },
    "src/skills/goal-to-delivery/scripts/path_safety.py": {
        "legacy runtime compatibility": frozenset(
            {
                "45375bba04c3d99ef61a3f54e35767ecf4b14d5e183b5d3a85f1f006dfa19854",
                "ffda759438c1e0bed28f8e7b20abd0f9af285a31ca3d0934f294ebb3498ef19d",
            }
        )
    },
    "src/tool-instructions/codex/AGENTS.md": {
        "legacy runtime compatibility": frozenset(
            {"e300897cfebba5099aec32422a44cff0e182353f3fc4caefa93978296ef36ceb"}
        )
    },
    "src/tool-instructions/claude/CLAUDE.md": {
        "legacy runtime compatibility": frozenset(
            {"e300897cfebba5099aec32422a44cff0e182353f3fc4caefa93978296ef36ceb"}
        )
    },
    "src/tool-instructions/copilot/.github/copilot-instructions.md": {
        "legacy runtime compatibility": frozenset(
            {"e300897cfebba5099aec32422a44cff0e182353f3fc4caefa93978296ef36ceb"}
        )
    },
    "src/tool-instructions/cursor/AGENTS.md": {
        "legacy runtime compatibility": frozenset(
            {"e300897cfebba5099aec32422a44cff0e182353f3fc4caefa93978296ef36ceb"}
        )
    },
    "tests/goal_to_delivery_base/support.py": {
        "intentional legacy test": frozenset(
            {"5725b27b2810f1e6b917d5def3a9688aa0e6cde46090b424fc9f807a85738eef"}
        )
    },
    "tests/goal_to_delivery_base/test_handoff.py": {
        "intentional legacy test": frozenset(
            {"f92233d0e872d0fd248317a6138ff4ca6b2dc2226c13884b593395c6340415b4"}
        )
    },
    "tests/goal_to_delivery_base/test_workflow_lifecycle.py": {
        "intentional legacy test": frozenset(
            {
                "0519abfbbeb17553767ec1dad639c2f75c459c074bd600c26fbc72dfd2c4f0cd",
                "1d57e38d741202f07f761b8d3670ab6e3421faa23bde4230d382932ecf2e472d",
                "33a78043fc1f82d300b3e62d9a97ebe9aad9cf83ebb6410804cb3375d85e345f",
                "41c71090db3af355a55cc361d9e3f8f090d235357cd28dddcb5747e2907362cd",
                "50e1d320827e3cc11f469152bbaaba196bf6dab57afbbc80e01a618d186a3624",
            }
        )
    },
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_doctrine(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _doctrine_blocks(text: str) -> dict[str, str]:
    """Return long normalized blocks suitable for copy/signature detection."""
    blocks: dict[str, str] = {}
    for raw_block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        normalized = _normalized_doctrine(raw_block)
        if len(normalized) < DOCTRINE_BLOCK_MIN_LENGTH:
            continue
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        blocks[digest] = normalized
    return blocks


def _normalized_json(path: Path) -> str | None:
    try:
        value = json.loads(_read(path))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def operational_markdown(root: Path) -> list[Path]:
    """Return current operational doctrine, intentionally excluding legacy evidence history."""
    paths = [root / "AGENTS.md", root / "README.md"]
    paths.extend((root / "docs").rglob("*.md"))
    paths.extend((root / "src").rglob("*.md"))
    return sorted({path for path in paths if path.is_file()})


def check_forbidden_operational_terms(root: Path) -> list[str]:
    findings: list[str] = []
    for path in operational_markdown(root):
        text = _read(path)
        for label, pattern in FORBIDDEN_OPERATIONAL_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{_relative(root, path)}:{line}: contains {label}: {match.group(0)!r}")
    return findings


def _resolved_local_links(path: Path) -> set[Path]:
    resolved: set[Path] = set()
    for raw_target in MARKDOWN_LINK_PATTERN.findall(_read(path)):
        target = raw_target.split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("#"):
            continue
        resolved.add((path.parent / target).resolve())
    return resolved


def _schema_findings(root: Path, schema_path: Path) -> list[str]:
    try:
        schema = json.loads(_read(schema_path))
    except json.JSONDecodeError as exc:
        return [f"{_relative(root, schema_path)}: invalid JSON: {exc}"]

    findings: list[str] = []
    expected = {
        "schemaVersion",
        "workflowId",
        "workflow",
        "workSource",
        "workKey",
        "slug",
        "repositoryKey",
        "repositoryRoot",
        "goal",
        "acceptanceCriteria",
        "nonGoals",
        "tracking",
        "completionBoundary",
        "physicalWorktreeFingerprint",
        "riskFlags",
    }
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    if schema.get("type") != "object":
        findings.append(f"{_relative(root, schema_path)}: root schema type must be object.")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        findings.append(f"{_relative(root, schema_path)}: must declare JSON Schema draft 2020-12.")
    if schema.get("additionalProperties") is not False:
        findings.append(f"{_relative(root, schema_path)}: root schema must fail closed on additional properties.")
    missing_properties = sorted(expected - set(properties))
    if missing_properties:
        findings.append(f"{_relative(root, schema_path)}: missing properties: {', '.join(missing_properties)}")
    missing_required = sorted(expected - required)
    if missing_required:
        findings.append(f"{_relative(root, schema_path)}: missing required fields: {', '.join(missing_required)}")
    expected_enums = {
        "workflow": {"autonomous", "semi-autonomous", "manual"},
        "workSource": {"linear", "local"},
        "completionBoundary": {"artifact", "working-tree", "commit", "pr", "merge"},
    }
    if properties.get("schemaVersion", {}).get("const") != "2.0":
        findings.append(f"{_relative(root, schema_path)}: schemaVersion must be fixed at 2.0.")
    for name, expected_values in expected_enums.items():
        actual = set(properties.get(name, {}).get("enum", []))
        if actual != expected_values:
            findings.append(
                f"{_relative(root, schema_path)}: {name} enum drift; expected {sorted(expected_values)}."
            )
    return findings


def check_canonical_references(root: Path) -> list[str]:
    findings: list[str] = []
    skills_root = root / "src" / "skills"
    canonical = skills_root / "goal-to-delivery" / "references"
    expected_paths = {canonical / name for name in CANONICAL_REFERENCES}
    for path in sorted(expected_paths):
        if not path.is_file():
            findings.append(f"Missing canonical delivery reference: {_relative(root, path)}")

    for name in CANONICAL_REFERENCES:
        copies = [path for path in skills_root.rglob(name) if path.parent != canonical]
        for copy in copies:
            findings.append(
                f"Competing delivery reference {_relative(root, copy)} duplicates canonical filename {name}."
            )

    canonical_markdown = [path for path in expected_paths if path.suffix == ".md" and path.is_file()]
    canonical_full_hashes = {
        hashlib.sha256(_normalized_doctrine(_read(path)).encode("utf-8")).hexdigest(): path
        for path in canonical_markdown
    }
    canonical_block_hashes = {path: _doctrine_blocks(_read(path)) for path in canonical_markdown}
    for candidate in operational_markdown(root):
        if candidate.parent == canonical:
            continue
        candidate_text = _read(candidate)
        full_hash = hashlib.sha256(_normalized_doctrine(candidate_text).encode("utf-8")).hexdigest()
        exact_source = canonical_full_hashes.get(full_hash)
        if exact_source is not None:
            findings.append(
                f"Competing renamed delivery doctrine {_relative(root, candidate)} copies "
                f"{_relative(root, exact_source)}."
            )
            continue

        candidate_blocks = _doctrine_blocks(candidate_text)
        for source, source_blocks in canonical_block_hashes.items():
            shared = set(candidate_blocks) & set(source_blocks)
            contains_large_block = any(len(source_blocks[digest]) >= 300 for digest in shared)
            if len(shared) >= 2 or contains_large_block:
                findings.append(
                    f"Competing renamed delivery doctrine {_relative(root, candidate)} contains normative "
                    f"content from {_relative(root, source)}."
                )
                break

    schema_path = canonical / "work-descriptor.schema.json"
    canonical_schema = _normalized_json(schema_path) if schema_path.is_file() else None
    if canonical_schema is not None:
        for candidate in (root / "src").rglob("*.json"):
            if candidate == schema_path:
                continue
            if _normalized_json(candidate) == canonical_schema:
                findings.append(
                    f"Competing renamed delivery schema {_relative(root, candidate)} copies "
                    f"{_relative(root, schema_path)}."
                )

    for skill_name in ENTRY_SKILLS:
        skill_path = skills_root / skill_name / "SKILL.md"
        if not skill_path.is_file():
            findings.append(f"Missing workflow entry skill: {_relative(root, skill_path)}")
            continue
        links = _resolved_local_links(skill_path)
        missing_links = sorted(expected_paths - links)
        if missing_links:
            findings.append(
                f"{_relative(root, skill_path)}: missing canonical reference links: "
                + ", ".join(path.name for path in missing_links)
            )
        broken = [link for link in links if not link.is_file() and root.resolve() in link.parents]
        for link in sorted(broken):
            findings.append(f"{_relative(root, skill_path)}: broken local reference {_relative(root, link)}")

    if schema_path.is_file():
        findings.extend(_schema_findings(root, schema_path))
    return findings


def _require_fragments(root: Path, path: Path, fragments: Iterable[str], label: str) -> list[str]:
    if not path.is_file():
        return [f"Missing {label}: {_relative(root, path)}"]
    folded = _read(path).casefold()
    missing = [fragment for fragment in fragments if fragment.casefold() not in folded]
    if not missing:
        return []
    return [f"{_relative(root, path)}: {label} is missing semantic anchors: {', '.join(missing)}"]


def check_entry_policies(root: Path) -> list[str]:
    skills = root / "src" / "skills"
    findings: list[str] = []
    findings.extend(
        _require_fragments(
            root,
            skills / "goal-to-delivery" / "SKILL.md",
            (
                "semi-autonomous",
                "automatic",
                "working-tree",
                "queue selection",
                "mode: autonomous",
                "registered `artifactFolder`",
            ),
            "semi-autonomous entry policy",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            skills / "spec-driven-delivery" / "SKILL.md",
            (
                "manual",
                "exactly one",
                "automatic advancement",
                "one focused question",
                "mode: autonomous",
                "registered `artifactFolder`",
            ),
            "manual entry policy",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            skills / "linear-delivery-loop" / "SKILL.md",
            (
                "autonomous",
                ".ai/loop.json",
                "autonomous label",
                "human-decision label",
                "at most one",
                "In Progress",
                "Backlog",
                "Done",
                "continuation issue",
                "DECIDE <ISSUE> CUSTOM <SUGGESTION>",
                "notification click target",
                "quiet standalone scheduled run",
                "set_thread_archived",
                "raw archive directive",
                "applicable UI design conformance",
                "registered `artifactFolder`",
            ),
            "autonomous entry policy",
        )
    )
    return findings


def check_shared_specialists_and_routing(root: Path) -> list[str]:
    findings: list[str] = []
    stages = root / "src" / "skills" / "goal-to-delivery" / "references" / "delivery-stages.md"
    findings.extend(
        _require_fragments(
            root,
            stages,
            (
                "planner",
                "product-designer",
                "tasker",
                "auditor",
                "matching implementer",
                "design_review",
                "code-reviewer",
                "qa",
                "proven not to affect rendered UI or interaction",
            ),
            "shared specialist contract",
        )
    )
    findings.extend(_require_fragments(root, stages, ("docs-as-code",), "shared documentation owner"))
    findings.extend(
        _require_fragments(
            root,
            root / "src" / "skills" / "goal-to-delivery" / "references" / "completion-boundaries.md",
            ("applicable UI design conformance", "one code review", "applicable QA"),
            "merge UI design gate",
        )
    )
    for agent in SPECIALIST_AGENTS:
        path = root / "src" / "agents" / f"{agent}.md"
        if not path.is_file():
            findings.append(f"Missing shared specialist agent: {_relative(root, path)}")

    design_gates = root / "src" / "skills" / "goal-to-delivery" / "references" / "design-gates.md"
    findings.extend(
        _require_fragments(
            root,
            design_gates,
            (
                "binding design sources",
                "design specification",
                "mechanical change",
                "design conformance review",
                "every change to rendered UI or interaction",
                "real browser",
                "PASS",
                "FAIL",
                "registered `artifactFolder`",
                "reviewed state",
                "`--02`",
            ),
            "frontend/UI design gate contract",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            root / "src" / "agents" / "product-designer.md",
            (
                "two product-design operations",
                "binding design sources",
                "design specification",
                "design conformance review",
                "real-browser",
                "PASS",
                "FAIL",
                "stale",
                "reviewed state",
                "`--02`",
            ),
            "product-designer design gate ownership",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            root / "src" / "agents" / "planner.md",
            ("design-gates.md", "binding design sources", "post-implementation design conformance review"),
            "planner UI design routing",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            root / "src" / "agents" / "tasker.md",
            ("design-gates.md", "binding design-source paths", "product-designer conformance-review task"),
            "tasker UI design routing",
        )
    )
    for implementer in ("react", "nextjs-mui", "jekyll-site-builder"):
        findings.extend(
            _require_fragments(
                root,
                root / "src" / "agents" / f"{implementer}.md",
                ("design-gates.md", "binding design sources", "required design spec", "design conformance review"),
                f"{implementer} UI design gate",
            )
        )
    for verifier in ("code-reviewer", "qa"):
        findings.extend(
            _require_fragments(
                root,
                root / "src" / "agents" / f"{verifier}.md",
                ("product-designer", "design conformance", "missing", "stale", "failed"),
                f"{verifier} design-review prerequisite",
            )
        )

    ui_review = root / "src" / "skills" / "ui-review-spec" / "SKILL.md"
    findings.extend(
        _require_fragments(
            root,
            ui_review,
            (
                "binding design sources",
                "exact implementation identity",
                "design-review-template.md",
                "real rendered evidence",
                "`--02`",
            ),
            "UI review design-conformance operation",
        )
    )

    findings.extend(
        _require_fragments(
            root,
            root / "src" / "agents" / "auditor.md",
            ("independent", "pre-implementation", "read-only"),
            "auditor authority contract",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            root / "src" / "agents" / "code-reviewer.md",
            ("exact diff", "review", "qa"),
            "code-review authority contract",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            root / "src" / "agents" / "qa.md",
            ("real behavior", "fix defects"),
            "runtime QA authority contract",
        )
    )
    docs_skill = root / "src" / "skills" / "docs-as-code" / "SKILL.md"
    findings.extend(
        _require_fragments(root, docs_skill, ("durable", "documentation"), "documentation authority contract")
    )

    feature_driver = root / "src" / "agents" / "feature-driver.md"
    findings.extend(
        _require_fragments(
            root,
            feature_driver,
            ("compatibility", "$goal-to-delivery", "autonomous", "never"),
            "feature-driver compatibility router",
        )
    )
    if feature_driver.is_file():
        body = _read(feature_driver).split("---", 2)[-1]
        retired_markers = ("Required workflow:", "Select the correct implementation specialist", "Primary goals:")
        for marker in retired_markers:
            if marker.casefold() in body.casefold():
                findings.append(f"{_relative(root, feature_driver)}: retains retired orchestration doctrine: {marker}")
        if len(body) > 1800:
            findings.append(f"{_relative(root, feature_driver)}: compatibility router is too large to be a thin alias.")

    multi_agent = root / "src" / "skills" / "multi-agent-delivery" / "SKILL.md"
    findings.extend(
        _require_fragments(
            root,
            multi_agent,
            (
                "$goal-to-delivery",
                "$spec-driven-delivery",
                "$linear-delivery-loop",
                "do not choose",
                "do not select",
                "design conformance review",
            ),
            "policy-neutral specialist handoff primitive",
        )
    )
    return findings


def check_artifact_layout(root: Path) -> list[str]:
    findings: list[str] = []
    contract = root / "src" / "skills" / "goal-to-delivery" / "references" / "artifact-contract.md"
    legacy_root = "docs" + "-ai"
    findings.extend(
        _require_fragments(
            root,
            contract,
            (
                ".ai/work/",
                "artifactFolder",
                "registered legacy",
                legacy_root,
                "historical",
                "read-only",
            ),
            "artifact layout, registered legacy compatibility, and historical read-only contract",
        )
    )

    for path in (root / "src").rglob("*.md"):
        if path == contract:
            continue
        match = OLD_LAYOUT_PATTERN.search(_read(path))
        if match:
            findings.append(
                f"{_relative(root, path)}: active producer/consumer retains historical folder layout: {match.group(0)}"
            )
    return findings


def _active_text_files(root: Path) -> list[Path]:
    candidates = list(root.glob("*.md"))
    for relative in ("docs", "src", "scripts", "validation", "tests", "dist"):
        area = root / relative
        if area.is_dir():
            candidates.extend(area.rglob("*"))
    return sorted(
        {
            path
            for path in candidates
            if path.is_file()
            and path.suffix.casefold() in TEXT_SUFFIXES
            and "__pycache__" not in path.parts
            and path.suffix.casefold() != ".pyc"
        }
    )


def _canonical_projection_source(relative: str) -> str:
    parts = relative.split("/")
    if len(parts) >= 3 and parts[0] == "dist" and parts[1] == "tool-instructions":
        return "/".join(("src", "tool-instructions", *parts[2:]))

    if len(parts) >= 5 and parts[0] == "dist" and parts[2] == "skills":
        return "/".join(("src", "skills", *parts[3:]))

    if len(parts) == 4 and parts[0] == "dist" and parts[2] == "agents":
        name = parts[3]
        if parts[1] == "codex" and name.endswith(".toml"):
            stem = name.removesuffix(".toml")
        elif parts[1] == "claude" and name.endswith(".md"):
            stem = name.removesuffix(".md")
        elif parts[1] == "copilot" and name.endswith(".agent.md"):
            stem = name.removesuffix(".agent.md")
        else:
            return relative
        return f"src/agents/{stem}.md"

    if len(parts) == 4 and parts[:3] == ["dist", "cursor", "rules"] and parts[3].endswith(".mdc"):
        support_sources = {
            "ui-design-gates.mdc": "src/skills/goal-to-delivery/references/design-gates.md",
            "ui-review-spec.mdc": "src/skills/ui-review-spec/SKILL.md",
            "ui-design-spec-template.mdc": "src/skills/ui-review-spec/references/spec-template.md",
            "ui-design-review-template.mdc": "src/skills/ui-review-spec/references/design-review-template.md",
            "ui-audit-checklist.mdc": "src/skills/ui-review-spec/references/ui-audit-checklist.md",
            "ui-component-selection.mdc": "src/skills/ui-review-spec/references/component-selection.md",
        }
        return support_sources.get(parts[3], f"src/agents/{parts[3].removesuffix('.mdc')}.md")

    return relative


def _line_sha256(line: str) -> str:
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


def check_docs_ai_allowlist(root: Path) -> list[str]:
    """Reject every unreviewed legacy-root literal in active source and projections."""
    literal = "docs" + "-ai"
    findings: list[str] = []
    for source_relative, purpose_digests in DOCS_AI_ALLOWLIST.items():
        unexpected = sorted(set(purpose_digests) - DOCS_AI_ALLOWED_PURPOSES)
        if unexpected:
            findings.append(
                f"Legacy literal allowlist for {source_relative!r} has unsupported purposes: "
                + ", ".join(unexpected)
            )
        for purpose, digests in purpose_digests.items():
            invalid = sorted(digest for digest in digests if re.fullmatch(r"[0-9a-f]{64}", digest) is None)
            if invalid:
                findings.append(
                    f"Legacy literal allowlist for {source_relative!r} purpose {purpose!r} "
                    "contains an invalid line digest."
                )
    for path in _active_text_files(root):
        relative = _relative(root, path)
        source_relative = _canonical_projection_source(relative)
        purpose_digests = DOCS_AI_ALLOWLIST.get(source_relative, {})
        for line_number, line in enumerate(_read(path).splitlines(), start=1):
            if literal.casefold() not in line.casefold():
                continue
            digest = _line_sha256(line)
            purposes = sorted(purpose for purpose, digests in purpose_digests.items() if digest in digests)
            if purposes:
                continue
            expected = ", ".join(sorted(purpose_digests)) or "no allowed purpose"
            findings.append(
                f"{relative}:{line_number}: unallowlisted legacy artifact-root literal; "
                f"canonical source {source_relative!r} permits {expected}."
            )
    return findings


def check_tool_instruction_cutover(root: Path) -> list[str]:
    findings: list[str] = []
    current_source = root / "src" / "tool-instructions"
    retired_leaf = "project" + "-templates"
    retired_source = root / "src" / retired_leaf
    retired_generated = root / "dist" / retired_leaf
    if not current_source.is_dir():
        findings.append("Missing canonical tool-instructions directory: src/tool-instructions")
    if retired_source.exists():
        findings.append("Retired canonical instruction directory still exists under src/.")
    if retired_generated.exists():
        findings.append("Retired generated instruction directory still exists under dist/.")

    retired_path_pattern = re.compile(re.escape(retired_leaf), re.IGNORECASE)
    retired_name_pattern = re.compile(r"\bproject\s+templates?\b", re.IGNORECASE)
    for path in _active_text_files(root):
        text = _read(path)
        match = retired_path_pattern.search(text) or retired_name_pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{_relative(root, path)}:{line}: retains retired tool-instruction terminology.")
    return findings


def check_worktree_policy(root: Path) -> list[str]:
    policy = root / "src" / "skills" / "goal-to-delivery" / "references" / "worktree-policy.md"
    resolved_command = "git worktree add -b <branch> <exact-path> <resolved-base-commit>"
    findings = _require_fragments(
        root,
        policy,
        (
            "direct owner instruction",
            "explicitly invoked delivery entry",
            "is not authority",
            "git worktree list --porcelain -z",
            ".ai/worktrees/<safe-worktree-name>",
            "windows reserved names",
            "reparse traversal",
            "git check-ignore -v --no-index",
            "remote ref is provenance only",
            "bind the recorded full commit sha into the imminent command",
            resolved_command,
            "must never change the command operand",
            "creation authority never implies removal authority",
            "git worktree remove",
            "git clean -x",
            "never recursively delete",
            "stricter repository-local",
        ),
        "canonical worktree authority and safety contract",
    )

    if policy.is_file():
        command_lines = [
            line.strip()
            for line in _read(policy).splitlines()
            if line.strip().casefold().startswith("git worktree add -b")
        ]
        unexpected_commands = [command for command in command_lines if command != resolved_command]
        if unexpected_commands:
            findings.append(
                f"{_relative(root, policy)}: worktree creation must execute against the reconciled "
                "resolved base commit, never a movable remote ref."
            )

    for relative in GUIDANCE_FILES[2:]:
        findings.extend(
            _require_fragments(
                root,
                root / relative,
                (
                    "goal-to-delivery/references/worktree-policy.md",
                    "artifactFolder",
                    ".ai/work",
                    "exact registered legacy",
                    "read-only",
                ),
                "tool-instruction artifact and worktree routing contract",
            )
        )
    return findings


def check_guidance_alignment(root: Path) -> list[str]:
    findings: list[str] = []
    for relative in GUIDANCE_FILES:
        path = root / relative
        findings.extend(
            _require_fragments(
                root,
                path,
                (
                    "goal-to-delivery/references",
                    "cross-tool",
                    "repository-specific",
                    "stricter",
                    "closed before implementation",
                    "$spec-driven-delivery",
                ),
                "canonical ownership, precedence, and default-entry guidance",
            )
        )
        if path.is_file():
            text = _read(path)
            if "### 1. Plan first" in text or "## Required Planning Format" in text:
                findings.append(f"{relative}: duplicates the canonical stage protocol instead of referencing it.")
    return findings


def check_projection_manifest(root: Path) -> list[str]:
    manifest_path = root / "dist" / "manifest.json"
    if not manifest_path.is_file():
        return ["dist/manifest.json: missing generated source/projection manifest; run the build first."]
    try:
        manifest = json.loads(_read(manifest_path))
    except json.JSONDecodeError as exc:
        return [f"dist/manifest.json: invalid JSON: {exc}"]

    findings: list[str] = []
    if manifest.get("schemaVersion") != 1 or manifest.get("canonicalRoot") != "src":
        findings.append("dist/manifest.json: unsupported schemaVersion or canonicalRoot.")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        return findings + ["dist/manifest.json: entries must be a non-empty array."]

    expected_sources = {
        path.relative_to(root).as_posix()
        for area in (root / "src" / "agents", root / "src" / "skills", root / "src" / "tool-instructions")
        for path in area.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    observed_sources: set[str] = set()
    observed_outputs: set[str] = set()
    for entry in entries:
        source_name = entry.get("source")
        if not isinstance(source_name, str):
            findings.append("dist/manifest.json: entry has no source path.")
            continue
        if source_name in observed_sources:
            findings.append(f"dist/manifest.json: duplicate source entry: {source_name}")
        observed_sources.add(source_name)
        source = root / source_name
        if not source.is_file():
            findings.append(f"dist/manifest.json: source is missing: {source_name}")
        elif entry.get("sourceSha256") != _sha256(source):
            findings.append(f"dist/manifest.json: stale source hash: {source_name}")
        projections = entry.get("projections")
        if not isinstance(projections, list) or not projections:
            findings.append(f"dist/manifest.json: source has no projections: {source_name}")
            continue
        for projection in projections:
            output_name = projection.get("path") if isinstance(projection, dict) else None
            if not isinstance(output_name, str):
                findings.append(f"dist/manifest.json: malformed projection for {source_name}")
                continue
            if output_name in observed_outputs:
                findings.append(f"dist/manifest.json: duplicate projection path: {output_name}")
            observed_outputs.add(output_name)
            output = root / output_name
            if not output.is_file():
                findings.append(f"dist/manifest.json: generated projection is missing: {output_name}")
            elif projection.get("sha256") != _sha256(output):
                findings.append(f"dist/manifest.json: generated projection drift: {output_name}")

    for source_name in sorted(expected_sources - observed_sources):
        findings.append(f"dist/manifest.json: canonical source is not projected: {source_name}")
    for source_name in sorted(observed_sources - expected_sources):
        findings.append(f"dist/manifest.json: manifest includes a non-canonical source: {source_name}")
    return findings


def validate_repository(root: Path) -> list[str]:
    checks = (
        check_forbidden_operational_terms,
        check_canonical_references,
        check_entry_policies,
        check_shared_specialists_and_routing,
        check_artifact_layout,
        check_docs_ai_allowlist,
        check_tool_instruction_cutover,
        check_worktree_policy,
        check_guidance_alignment,
        check_projection_manifest,
    )
    findings: list[str] = []
    for check in checks:
        findings.extend(check(root))
    return findings
