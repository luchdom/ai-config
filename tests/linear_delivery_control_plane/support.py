from __future__ import annotations

import copy
import importlib.util
import secrets
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "src" / "skills" / "linear-delivery-loop" / "scripts"
PACKAGE = "tests_linear_delivery_control_plane_runtime"


def load_package():
    existing = sys.modules.get(PACKAGE)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        PACKAGE, SCRIPTS / "__init__.py", submodule_search_locations=[str(SCRIPTS)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    spec.loader.exec_module(module)
    return module


package = load_package()

_FIXTURE_ENGINES = {}
_FIXTURE_PATCHED = False


def _install_fixture_surface(supervisor_module):
    """Patch the isolated test package with closed-operation fixture routing.

    Raw callbacks stay in this test module.  The production SupervisorEngine
    exposes neither fixture installation nor authority-entry resolution.
    """

    global _FIXTURE_PATCHED
    if _FIXTURE_PATCHED:
        return

    def describe(engine, reference):
        fixture = _FIXTURE_ENGINES.get(reference)
        if fixture is None or fixture["engine"] is not engine:
            raise supervisor_module.SupervisorStoreError(
                "Fixture control-plane reference is absent"
            )
        return copy.deepcopy(fixture["metadata"])

    def execute(engine, reference, operation, payload, *, linear):
        fixture = _FIXTURE_ENGINES.get(reference)
        if (
            fixture is None or fixture["engine"] is not engine
            or fixture["linear"] is not linear
        ):
            raise supervisor_module.SupervisorStoreError(
                "Fixture control-plane reference is differently bound"
            )
        claim_port = fixture["claim_port"]
        authority = fixture["authority"]
        if operation == "observe-issues":
            return fixture["observation"].observe_issues()
        if operation == "observe-selection":
            return fixture["observation"].observe_selection()
        if operation == "claim-reread":
            return claim_port.reread(payload["issueId"], payload["operationId"])
        if operation == "claim":
            return claim_port.claim(payload["issue"], payload["operationId"])
        if operation == "claim-readback":
            return claim_port.readback(payload["issueId"], payload["operationId"])
        authority_names = {
            "current-execution-lease": "current_execution_lease",
            "authorize-recovery": "authorize_recovery",
            "prepare": "prepare", "commit": "commit",
            "rollback-if-safe": "rollback_if_safe", "protect": "protect",
            "recover": "recover",
        }
        name = authority_names.get(operation)
        if name is None:
            raise supervisor_module.SupervisorStoreError(
                "Fixture control-plane operation is unknown"
            )
        return getattr(authority, name)(**dict(payload))

    supervisor_module.SupervisorEngine.describe_control_plane_reference = describe
    supervisor_module.SupervisorEngine.execute_control_plane_operation = execute
    _FIXTURE_PATCHED = True


def fixture_engine_registry(
    *, linear, claim_port, authority, api_key, local_observer, query=None,
):
    """Compose raw adapters only in the isolated test package."""

    supervisor_module = __import__(
        package.__name__ + ".supervisor", fromlist=["SupervisorEngine"]
    )
    registry_module = __import__(
        package.__name__ + ".control_plane_registry", fromlist=["_Entry"]
    )
    _install_fixture_surface(supervisor_module)
    engine = object.__new__(supervisor_module.SupervisorEngine)
    reference = "fixture-engine-adapters-" + secrets.token_hex(16)
    observation_adapter = registry_module._EngineLinearObservationAdapter(
        transport=linear, adapter_id=claim_port.adapter_id, api_key=api_key,
        local_observer=local_observer,
        query=query or registry_module.DEFAULT_ISSUE_OBSERVATION_QUERY,
    )
    _FIXTURE_ENGINES[reference] = {
        "engine": engine, "linear": linear, "claim_port": claim_port,
        "authority": authority, "observation": observation_adapter,
        "metadata": {
            "reference": reference,
            "linearAdapterId": claim_port.adapter_id,
            "claimJournalId": claim_port.journal_id,
            "claimAuthorityId": authority.authority_id,
        },
    }
    return engine, reference


def tracking_config(*, ntfy_enabled: bool = False) -> dict:
    def named(identity: str, name: str) -> dict:
        return {"id": identity, "name": name}

    return {
        "schemaVersion": "1.0",
        "controlPlaneVersion": "1.0",
        "supervisorVersion": "1.0",
        "repositoryKey": "ai-config",
        "workspace": named("workspace-1", "Luchdom"),
        "team": {"id": "team-1", "key": "SAAS"},
        "project": named("project-1", "SaaS"),
        "owner": named("owner-1", "Lucas"),
        "states": {
            "backlog": named("state-backlog", "Backlog"),
            "todo": named("state-todo", "Todo"),
            "inProgress": named("state-progress", "In Progress"),
            "inReview": named("state-review", "In Review"),
            "done": named("state-done", "Done"),
        },
        "labels": {
            "autonomous": named("label-auto", "autonomous"),
            "needsRefinement": named("label-refine", "needs-refinement"),
            "needsHuman": named("label-human", "needs-human"),
            "externalIntegration": named("label-external", "external-integration"),
            "stop": named("label-stop", "stop"),
        },
        "linear": {
            "endpoint": "https://api.linear.app/graphql",
            "allowedHost": "api.linear.app",
            "apiKeyEnvironmentVariable": "LINEAR_API_KEY",
            "timeoutSeconds": 15,
            "maxAttempts": 3,
        },
        "ntfy": {
            "enabled": ntfy_enabled,
            "endpointEnvironmentVariable": "NTFY_URL",
            "topicEnvironmentVariable": "NTFY_TOPIC",
            "tokenEnvironmentVariable": "NTFY_TOKEN",
            "allowedHosts": ["ntfy.sh"],
            "maxAttempts": 3,
        },
    }


def observation(config: dict) -> dict:
    return {
        key: copy.deepcopy(config[key])
        for key in ("workspace", "team", "project", "owner", "states", "labels")
    }


def issue(number: int, **overrides) -> dict:
    value = {
        "id": f"linear-{number}",
        "identifier": f"SAAS-{number}",
        "title": f"Implement local feature {number}",
        "state": "Todo",
        "labels": ["autonomous"],
        "parentId": None,
        "repositoryKey": "ai-config",
        "scope": "code-leaf",
        "goalComplete": True,
        "externalDependency": False,
        "priority": 2,
        "createdAt": f"2026-07-{number:02d}T00:00:00Z",
    }
    value.update(overrides)
    return value


def raw_issue(number: int, **overrides) -> dict:
    """Query-shaped Linear node that normalizes to ``issue``."""

    normalized = issue(number, **overrides)
    return {
        "id": normalized["id"], "identifier": normalized["identifier"],
        "title": normalized["title"], "priority": normalized["priority"],
        "createdAt": normalized["createdAt"],
        "repositoryKey": normalized["repositoryKey"], "scope": normalized["scope"],
        "goalComplete": normalized["goalComplete"],
        "externalDependency": normalized["externalDependency"],
        "state": {"name": normalized["state"]},
        "labels": {"nodes": [{"name": label} for label in normalized["labels"]]},
        "parent": None if normalized["parentId"] is None else {"id": normalized["parentId"]},
        "project": {"id": "project-1", "name": "SaaS"},
    }
