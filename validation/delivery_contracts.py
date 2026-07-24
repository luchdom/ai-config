"""Semantic checks for the shared delivery protocol and its projections."""
from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


CANONICAL_REFERENCES = (
    "delivery-stages.md",
    "artifact-contract.md",
    "clarification-policy.md",
    "quality-gates.md",
    "completion-boundaries.md",
    "work-descriptor.schema.json",
)
AUTONOMOUS_RUNTIME_REFERENCE = "autonomous-runtime-contract.md"
AUTONOMOUS_PROMPT_BUDGET_BYTES = 8192
ENTRY_SKILLS = ("goal-to-delivery", "spec-driven-delivery", "linear-delivery-loop")
SUPERVISOR_SCHEMAS = (
    "project-config.schema.json",
    "prepared-iteration.schema.json",
    "checkpoint.schema.json",
    "supervisor-state.schema.json",
    "editing-reservation.schema.json",
    "operation-journal.schema.json",
    "worker-result.schema.json",
    "engine-command.schema.json",
    "release-authorization.schema.json",
    "handoff-authorization.schema.json",
    "trusted-observation.schema.json",
)
SUPERVISOR_OPERATIONS = (
    "Preflight",
    "AcquireLease",
    "RenewLease",
    "PrepareIteration",
    "ApplyCheckpoint",
    "Status",
    "Reserve",
    "RenewReservation",
    "AuthorizeMutation",
    "Release",
    "Recover",
    "Cleanup",
    "Handoff",
    "ReleaseLease",
    "PreparePublication",
    "PublicationProvider",
    "PublicationGate",
    "RecordPublicationAttestation",
    "PublicationRepair",
    "RecoverPublication",
)
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
    "src/project-templates/codex/AGENTS.md",
    "src/project-templates/claude/CLAUDE.md",
    "src/project-templates/copilot/.github/copilot-instructions.md",
    "src/project-templates/cursor/AGENTS.md",
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
    r"docs-ai/<(?:NNN|[Nn]{3})>-<(?:short-feature-name|slug)>-<YYYY-MM-DD>",
    re.IGNORECASE,
)
INLINE_MARKDOWN_LINK_PATTERN = re.compile(
    r"!?\[[^\]]*\]\(\s*(?:<(?P<angle>[^>\r\n]+)>|(?P<plain>[^\s)]+))"
)
REFERENCE_DEFINITION_PATTERN = re.compile(
    r"^[ \t]{0,3}\[(?P<label>[^\]]+)\]:[ \t]*"
    r"(?:\r?\n[ \t]{0,3})?"
    r"(?:<(?P<angle>[^>\r\n]+)>|(?P<plain>[^\s<>]+))",
    re.MULTILINE,
)
FULL_REFERENCE_LINK_PATTERN = re.compile(r"!?\[(?P<label>[^\]]+)\]\[(?P<reference>[^\]]*)\]")
SHORTCUT_REFERENCE_LINK_PATTERN = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\](?![ \t]*(?:[\[(]|:))")
URI_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
DOCTRINE_BLOCK_MIN_LENGTH = 120


class _HrefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.casefold() == "href" and value is not None:
                self.targets.append(value)


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
    """Return current operational doctrine, intentionally excluding docs-ai history."""
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


def _local_target(raw_target: str) -> str | None:
    target = unescape(raw_target).strip()
    if not target or target.startswith("#") or target.startswith("//"):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not target or URI_SCHEME_PATTERN.match(target):
        return None
    return target


def _markdown_and_html_targets(text: str) -> set[str]:
    targets: set[str] = set()
    for match in INLINE_MARKDOWN_LINK_PATTERN.finditer(text):
        targets.add(match.group("angle") or match.group("plain"))

    definitions = {
        re.sub(r"\s+", " ", match.group("label").strip()).casefold(): (
            match.group("angle") or match.group("plain")
        )
        for match in REFERENCE_DEFINITION_PATTERN.finditer(text)
    }
    for match in FULL_REFERENCE_LINK_PATTERN.finditer(text):
        label = match.group("reference") or match.group("label")
        target = definitions.get(re.sub(r"\s+", " ", label.strip()).casefold())
        if target:
            targets.add(target)
    for match in SHORTCUT_REFERENCE_LINK_PATTERN.finditer(text):
        label = re.sub(r"\s+", " ", match.group("label").strip()).casefold()
        target = definitions.get(label)
        if target:
            targets.add(target)

    parser = _HrefCollector()
    parser.feed(text)
    targets.update(parser.targets)
    return targets


def _resolved_local_links(path: Path) -> set[Path]:
    resolved: set[Path] = set()
    for raw_target in _markdown_and_html_targets(_read(path)):
        target = _local_target(raw_target)
        if target is not None:
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
    detailed_paths = {canonical / name for name in CANONICAL_REFERENCES}
    autonomous_path = canonical / AUTONOMOUS_RUNTIME_REFERENCE
    expected_paths = detailed_paths | {autonomous_path}
    for path in sorted(expected_paths):
        if not path.is_file():
            findings.append(f"Missing canonical delivery reference: {_relative(root, path)}")

    for name in (*CANONICAL_REFERENCES, AUTONOMOUS_RUNTIME_REFERENCE):
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
        required_links = {autonomous_path} if skill_name == "linear-delivery-loop" else detailed_paths
        missing_links = sorted(required_links - links)
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


def check_autonomous_prompt_surface(root: Path) -> list[str]:
    """Validate the complete mandatory Markdown surface for a healthy autonomous run."""
    skill = root / "src" / "skills" / "linear-delivery-loop" / "SKILL.md"
    contract = (
        root
        / "src"
        / "skills"
        / "goal-to-delivery"
        / "references"
        / AUTONOMOUS_RUNTIME_REFERENCE
    )
    if not skill.is_file() or not contract.is_file():
        missing = skill if not skill.is_file() else contract
        return [f"Missing autonomous prompt asset: {_relative(root, missing)}"]

    findings: list[str] = []
    skill_links = _resolved_local_links(skill)
    if skill_links != {contract.resolve()}:
        observed = ", ".join(
            _relative(root, link) if root.resolve() in link.parents else str(link)
            for link in sorted(skill_links)
        ) or "none"
        findings.append(
            "src/skills/linear-delivery-loop/SKILL.md: healthy autonomous prompt must link directly "
            f"only {AUTONOMOUS_RUNTIME_REFERENCE}; observed: {observed}"
        )

    contract_links = _resolved_local_links(contract)
    if contract_links:
        observed = ", ".join(
            _relative(root, link) if root.resolve() in link.parents else str(link)
            for link in sorted(contract_links)
        )
        findings.append(
            f"{_relative(root, contract)}: compact contract must not add indirect local prompt references: "
            + observed
        )

    prompt_bytes = len(skill.read_bytes()) + len(contract.read_bytes())
    if prompt_bytes > AUTONOMOUS_PROMPT_BUDGET_BYTES:
        findings.append(
            "Autonomous prompt surface exceeds "
            f"{AUTONOMOUS_PROMPT_BUDGET_BYTES} UTF-8 bytes: observed {prompt_bytes}."
        )

    findings.extend(
        _require_fragments(
            root,
            contract,
            (
                "adapter-prepared",
                "exactly one issue",
                "fail closed",
                "repository rules",
                "planner",
                "product designer",
                "tasker",
                "independent auditor",
                "implementer",
                "independent code reviewer",
                "runtime QA",
                "documentation",
                "structured pause",
                "material decision",
                "adapter owns",
                "checkpoint",
                "external mutation",
                "stop",
                "merge SHA",
            ),
            "compact autonomous runtime contract",
        )
    )
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
            ("semi-autonomous", "automatic", "working-tree", "queue selection", "mode: autonomous"),
            "semi-autonomous entry policy",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            skills / "spec-driven-delivery" / "SKILL.md",
            ("manual", "exactly one", "automatic advancement", "one focused question", "mode: autonomous"),
            "manual entry policy",
        )
    )
    findings.extend(
        _require_fragments(
            root,
            skills / "linear-delivery-loop" / "SKILL.md",
            ("autonomous", "PreparedIteration", "capability", "deterministic adapter", "queue-selection"),
            "autonomous entry policy",
        )
    )

    if (skills / "linear-delivery-loop" / "SKILL.md").is_file():
        linear_text = _read(skills / "linear-delivery-loop" / "SKILL.md").casefold()
        if not any(
            phrase in linear_text
            for phrase in ("does not implement", "does not contain", "must not implement", "never implements")
        ):
            findings.append(
                "src/skills/linear-delivery-loop/SKILL.md: must deny independent selection/mutation implementation."
            )
    return findings


def check_shared_specialists_and_routing(root: Path) -> list[str]:
    findings: list[str] = []
    stages = root / "src" / "skills" / "goal-to-delivery" / "references" / "delivery-stages.md"
    findings.extend(
        _require_fragments(
            root,
            stages,
            ("planner", "product-designer", "tasker", "auditor", "matching implementer", "code-reviewer", "qa"),
            "shared specialist contract",
        )
    )
    findings.extend(_require_fragments(root, stages, ("docs-as-code",), "shared documentation owner"))
    for agent in SPECIALIST_AGENTS:
        path = root / "src" / "agents" / f"{agent}.md"
        if not path.is_file():
            findings.append(f"Missing shared specialist agent: {_relative(root, path)}")

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
            ("$goal-to-delivery", "$spec-driven-delivery", "$linear-delivery-loop", "do not choose", "do not select"),
            "policy-neutral specialist handoff primitive",
        )
    )
    return findings


def check_artifact_layout(root: Path) -> list[str]:
    findings: list[str] = []
    contract = root / "src" / "skills" / "goal-to-delivery" / "references" / "artifact-contract.md"
    findings.extend(
        _require_fragments(
            root,
            contract,
            (
                "docs-ai/<work-key>-<slug>/",
                "docs-ai/history",
                "historical",
                "read fallback",
                "never rename, rewrite",
            ),
            "artifact layout and historical fallback contract",
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
        for area in (root / "src" / "agents", root / "src" / "skills", root / "src" / "project-templates")
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


def check_supervisor_core(root: Path) -> list[str]:
    findings: list[str] = []
    skill = root / "src" / "skills" / "linear-delivery-loop"
    references = skill / "references"
    scripts = skill / "scripts"
    for name in SUPERVISOR_SCHEMAS:
        path = references / name
        if not path.is_file():
            findings.append(f"Missing supervisor schema: {_relative(root, path)}")
    command_schema = references / "engine-command.schema.json"
    if command_schema.is_file():
        try:
            schema = json.loads(_read(command_schema))
            observed = tuple(
                branch.get("properties", {}).get("operation", {}).get("const")
                for branch in schema.get("oneOf", [])
            )
        except (json.JSONDecodeError, AttributeError):
            observed = ()
        if observed != SUPERVISOR_OPERATIONS:
            findings.append(
                "engine-command.schema.json operation inventory drift; expected "
                + ", ".join(SUPERVISOR_OPERATIONS)
            )
    required_scripts = {
        "base_runtime.py",
        "contracts.py",
        "store.py",
        "operations.py",
        "lease.py",
        "reservations.py",
        "worktrees.py",
        "preflight.py",
        "recovery.py",
        "assembled_handoff.py",
        "supervisor.py",
        "cli.py",
        "agent-worker-engine.ps1",
    }
    for name in sorted(required_scripts):
        if not (scripts / name).is_file():
            findings.append(f"Missing supervisor runtime file: src/skills/linear-delivery-loop/scripts/{name}")
    copied_base_names = {"identity.py", "state_home.py", "mutex.py", "registry.py", "descriptor.py"}
    for name in sorted(copied_base_names):
        if (scripts / name).exists():
            findings.append(f"Supervisor package copies base-owned primitive: {name}")
    for path in sorted(scripts.glob("*")):
        if not path.is_file() or path.suffix not in {".py", ".ps1"}:
            continue
        text = _read(path).casefold().replace(" ", "")
        if "codexexec" in text or "shell=true" in text or "os.system(" in text:
            findings.append(f"{_relative(root, path)}: contains forbidden nested/arbitrary execution")
    fragments = {
        "goal-to-delivery": ("Reserve", "RenewReservation", "AuthorizeMutation", "assembled"),
        "spec-driven-delivery": ("Reserve", "RenewReservation", "AuthorizeMutation", "Handoff"),
    }
    for name, required in fragments.items():
        findings.extend(
            _require_fragments(
                root,
                root / "src" / "skills" / name / "SKILL.md",
                required,
                f"{name} supervisor integration",
            )
        )
    reference = references / "supervisor-core.md"
    if not reference.is_file():
        findings.append("Missing durable supervisor-core technical reference")
    return findings


def validate_repository(root: Path) -> list[str]:
    checks = (
        check_forbidden_operational_terms,
        check_canonical_references,
        check_autonomous_prompt_surface,
        check_entry_policies,
        check_shared_specialists_and_routing,
        check_artifact_layout,
        check_guidance_alignment,
        check_supervisor_core,
        check_projection_manifest,
    )
    findings: list[str] = []
    for check in checks:
        findings.extend(check(root))
    return findings
