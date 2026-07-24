from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
import subprocess
import uuid
from pathlib import Path

from tests.linear_delivery_supervisor import load_supervisor_package

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "skills" / "linear-delivery-loop"
runtime_package = load_supervisor_package()
contracts = importlib.import_module(runtime_package.__name__ + ".contracts")
base_runtime = importlib.import_module(runtime_package.__name__ + ".base_runtime")
supervisor_module = importlib.import_module(runtime_package.__name__ + ".supervisor")
repository_memory_module = importlib.import_module(runtime_package.__name__ + ".repository_memory")
repository_memory_records_module = importlib.import_module(runtime_package.__name__ + ".repository_memory_records")
repository_memory_index_module = importlib.import_module(runtime_package.__name__ + ".repository_memory_index")

canonical_json_bytes = contracts.canonical_json_bytes
sha256_canonical = contracts.sha256_canonical
validate_contract = contracts.validate_contract
assert_runtime_parity = contracts.assert_runtime_parity
ContractValidationError = contracts.ContractValidationError
load_schema = contracts.load_schema
validate_native = contracts._validate_native
candidate_intent_projection = contracts.candidate_intent_projection
promotion_manifest_payload_projection = contracts.promotion_manifest_payload_projection
record_payload_projection = contracts.record_payload_projection
promotion_batch_request_projection = contracts.promotion_batch_request_projection
batch_commit_payload_projection = contracts.batch_commit_payload_projection
index_semantic_projection = contracts.index_semantic_projection
retrieval_query_projection = contracts.retrieval_query_projection
retrieval_result_projection = contracts.retrieval_result_projection
context_envelope_payload_projection = contracts.context_envelope_payload_projection
context_delivery_accounting_projection = contracts.context_delivery_accounting_projection
SupervisorEngine = supervisor_module.SupervisorEngine
RepositoryMemory = repository_memory_module.RepositoryMemory
RepositoryMemoryError = repository_memory_module.RepositoryMemoryError
compose_context = repository_memory_module.compose_context
memory_status_snapshot = repository_memory_module.memory_status_snapshot
query_with_defaults = repository_memory_module.query_with_defaults
candidate_to_record = repository_memory_records_module.candidate_to_record
safe_repository_path = repository_memory_records_module.safe_repository_path
RepositoryMemoryRecordError = repository_memory_records_module.RepositoryMemoryRecordError
graph_projection = repository_memory_index_module._graph_projection


ZERO = "sha256:" + "0" * 64
NOW = "2026-07-24T12:00:00Z"
HEAD = "1" * 40
FINGERPRINT = "sha256:" + "2" * 64
REPOSITORY_KEY = "ai-config"
_FIXTURES = {}


def write_canonical(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def initialize_repository(root: Path) -> Path:
    subprocess.run(["git", "init", "--initial-branch=main", os.fspath(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", os.fspath(root), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", os.fspath(root), "config", "user.email", "test@example.invalid"], check=True)
    (root / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", os.fspath(root), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", os.fspath(root), "commit", "-m", "base"], check=True, capture_output=True)
    runtime = base_runtime.load_base_runtime()
    manager = runtime.WorkflowManager(root, repository_key=REPOSITORY_KEY, state_home_override=root.parent / "state")
    source_descriptor = manager.initialize_local(workflow="semi-autonomous", goal="source")
    curation_descriptor = manager.initialize_local(workflow="semi-autonomous", goal="curation")
    engine = SupervisorEngine(manager=manager, local_observer=lambda *_args, **_kwargs: {"dirty": False, "branch": "main", "headSha": head(root), "unpushed": False, "unmerged": False, "prOpen": False, "prId": None, "prState": "not-applicable", "accessible": True, "ambiguous": False, "planningOnly": False})
    memory = RepositoryMemory(manager, store=engine.store, reservations=engine.reservations)
    _FIXTURES[root.resolve()] = {"manager": manager, "engine": engine, "memory": memory, "source": source_descriptor, "curation": curation_descriptor, "reservation": None}
    source = root / "docs" / "guide.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Guide\n\nCanonical repository guidance.\n", encoding="utf-8")
    (root / "docs" / "repository-memory" / "records").mkdir(parents=True)
    (root / "docs" / "repository-memory" / "commits").mkdir(parents=True)
    completed = Path(source_descriptor["artifactFolder"]) / "2026-07-24-source-completion.md"
    completed.parent.mkdir(parents=True, exist_ok=True)
    completed.write_text("# Completion\n\nValidated source evidence.\n", encoding="utf-8")
    descriptor = json.loads((completed.parent / "workflow.json").read_text(encoding="utf-8"))
    descriptor.update({"currentArtifactStage": "completion", "artifactInventory": ["workflow.json", completed.name]})
    write_canonical(completed.parent / "workflow.json", descriptor)
    return source


def binding(root: Path):
    return _FIXTURES[root.resolve()]


def head(root: Path) -> str:
    return subprocess.run(["git", "-C", os.fspath(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def memory_engine(root: Path):
    return binding(root)["memory"]


def set_curation_stage(root: Path, stage: str) -> None:
    descriptor_path = Path(binding(root)["curation"]["artifactFolder"]) / "workflow.json"
    value = json.loads(descriptor_path.read_text(encoding="utf-8"))
    value["currentArtifactStage"] = stage
    write_canonical(descriptor_path, value)


def candidate(
    source: Path,
    root: Path,
    *,
    record_id: str = "runtime-python",
    version: int = 1,
    assertion_key: str = "runtime.python",
    assertion_value: object = "3.13",
    value_type: str = "string",
    title: str = "Python runtime",
    summary: str = "Use the repository-selected Python runtime.",
    candidate_number: int = 10,
    promotion_number: int = 20,
    supersedes: list[dict] | None = None,
) -> dict:
    candidate_id = f"00000000-0000-4000-8000-{candidate_number:012x}"
    promotion_id = f"00000000-0000-4000-8000-{promotion_number:012x}"
    value = {
        "candidateId": candidate_id,
        "candidatePromotionId": promotion_id,
        "targetRecordId": record_id,
        "targetRecordVersion": version,
        "targetPath": f"docs/repository-memory/records/{record_id}.v{version:04d}.json",
        "kind": "constraint",
        "topics": ["python"],
        "paths": ["src"],
        "stages": ["implementer", "planner"],
        "work": None,
        "title": title,
        "summary": summary,
        "assertions": [{"key": assertion_key, "valueType": value_type, "comparison": "equals", "value": assertion_value, "provenanceRefs": ["guide"]}],
        "provenance": [{"id": "guide", "kind": "repository-source", "path": source.relative_to(root).as_posix(), "sha256": digest(source), "workflowId": None, "workKey": None, "stage": None, "anchor": "guide"}],
        "confidence": "current-source-bound",
        "freshness": {"policy": "digest-on-read", "reviewAfter": None},
        "lifecycle": "active",
        "retention": {"class": "durable", "reviewAt": None, "expiresAt": None},
        "supersedes": supersedes or [],
        "restores": None,
        "createdAt": NOW,
        "reviewedAt": NOW,
        "archiveReason": None,
        "redactionReason": None,
        "candidateIntentSha256": ZERO,
    }
    value["candidateIntentSha256"] = sha256_canonical({key: item for key, item in value.items() if key != "candidateIntentSha256"})
    return value


def manifest(root: Path, candidates: list[dict], *, batch_number: int = 30, no_candidates: bool = False) -> tuple[str, dict]:
    fixture = binding(root)
    batch_id = f"00000000-0000-4000-8000-{batch_number:012x}"
    name = f"2026-07-24-memory-{batch_number}-memory-promotion.json"
    curation_folder = Path(fixture["curation"]["artifactFolder"])
    relative = (curation_folder / name).relative_to(root).as_posix()
    source = Path(fixture["source"]["artifactFolder"]) / "2026-07-24-source-completion.md"
    repository_source = root / "docs" / "guide.md"
    value = {
        "schemaVersion": "1.0", "repositoryId": fixture["manager"].identity.repository_id,
        "repositoryKey": REPOSITORY_KEY, "curationWorkflowId": fixture["curation"]["workflowId"],
        "headSha": head(root), "physicalWorktreeFingerprint": fixture["manager"].identity.physical_worktree_fingerprint,
        "producer": "docs-as-code", "createdAt": NOW,
        "compatibilityClass": "current-completion-v2", "batchPromotionId": batch_id,
        "decision": "no-candidates" if no_candidates else "promotion-approved",
        "sourceArtifacts": [
            {"workflowId": None, "workKey": None, "path": "docs/guide.md", "stage": "repository", "sha256": digest(repository_source), "completed": True},
            {"workflowId": fixture["source"]["workflowId"], "workKey": fixture["source"]["workKey"], "path": source.relative_to(root).as_posix(), "stage": "completion", "sha256": digest(source), "completed": True}
        ],
        "candidates": sorted(copy.deepcopy(candidates), key=lambda item: item["candidateId"]),
        "noCandidatesReason": "no-reusable-knowledge" if no_candidates else None,
        "noCandidatesSummary": "Reviewed; nothing reusable." if no_candidates else None,
        "docsAttestationRef": None,
        "promotionManifestPayloadSha256": ZERO,
    }
    value["promotionManifestPayloadSha256"] = sha256_canonical({key: item for key, item in value.items() if key != "promotionManifestPayloadSha256"})
    write_canonical(root / relative, value)
    descriptor_path = curation_folder / "workflow.json"
    inventory = []
    if descriptor_path.exists():
        inventory = json.loads(descriptor_path.read_text(encoding="utf-8")).get("artifactInventory", [])
    descriptor = {
        **json.loads(descriptor_path.read_text(encoding="utf-8")),
        "currentArtifactStage": "docs", "artifactInventory": sorted(set(inventory + ["workflow.json", name])),
    }
    write_canonical(descriptor_path, descriptor)
    return relative, value


def authorization(value: dict) -> dict:
    marker = f"docs/repository-memory/commits/{value['batchPromotionId']}.json"
    scope = sorted([item["targetPath"] for item in value["candidates"]] + [marker], key=str.casefold)
    return {"authorizationId": "00000000-0000-4000-8000-000000000040", "operationId": value["batchPromotionId"], "authorizationSha256": "sha256:" + "3" * 64, "scope": scope}


def issue_authority(root: Path, value: dict, *, scope=None):
    fixture = binding(root)
    engine = fixture["engine"]
    reservation = fixture["reservation"]
    if reservation is None:
        state, reservations = engine.store.load_state(), engine.store.load_reservations()
        reservation = engine.reservations.reserve(
            workflow_id=fixture["curation"]["workflowId"], issue_id=None,
            worktree_path=root, physical_worktree_fingerprint=fixture["manager"].identity.physical_worktree_fingerprint,
            policy="semi-autonomous", owner_id="memory-test", run_id=None,
            expected_state_revision=state["revision"], expected_reservations_revision=reservations["revision"],
        )
    state, reservations = engine.store.load_state(), engine.store.load_reservations()
    marker = f"docs/repository-memory/commits/{value['batchPromotionId']}.json"
    exact_scope = sorted([item["targetPath"] for item in value["candidates"]] + [marker], key=str.casefold)
    grant = engine.reservations.authorize_mutation(
        reservation_id=reservation["reservationId"], authorization_id=str(uuid.uuid4()),
        target_operation_id=value["batchPromotionId"], scope=scope or exact_scope,
        expected_record_revision=reservation["revision"], expected_state_revision=state["revision"],
        expected_reservations_revision=reservations["revision"],
        control_authorization_ref=reservation["releaseAuthorizationRef"], capability_ref=None,
    )
    fixture["reservation"] = {**reservation, "revision": grant["reservationRevision"], "releaseAuthorizationRef": grant["controlAuthorizationRef"]}
    return {
        "reservation_id": reservation["reservationId"], "authorization_ref": grant["authorizationRef"],
        "expected_record_revision": grant["reservationRevision"], "expected_state_revision": engine.store.load_state()["revision"],
        "expected_reservations_revision": engine.store.load_reservations()["revision"],
        "physical_worktree_fingerprint": fixture["manager"].identity.physical_worktree_fingerprint,
    }


def promote(root: Path, path: str, value: dict, *, expected=ZERO, scope=None):
    return memory_engine(root).promote(
        manifest_path=path, expected_prior_index_digest=expected,
        **issue_authority(root, value, scope=scope),
    )
