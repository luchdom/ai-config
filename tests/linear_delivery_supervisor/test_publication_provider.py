from __future__ import annotations

import importlib
import unittest
from tests.linear_delivery_supervisor import load_supervisor_package
from tests.linear_delivery_supervisor.support_state_engine import StateEngineTestCase

package = load_supervisor_package(); module = importlib.import_module(package.__name__ + ".publication_provider")
SHA = "a" * 40

class FixtureProvider:
    def __init__(self): self.ref = None; self.pr = None; self.merge = {"merged": False}; self.calls = []
    def read_remote_ref(self, branch): return self.ref
    def push_ref(self, request): self.calls.append("push"); self.ref = {"headSha": request["headSha"]}; return {"statusCode": 200, "token": "secret"}
    def read_pull_request(self, branch, base_ref): return self.pr
    def create_or_reuse_pull_request(self, request): self.calls.append("pr"); self.pr = {"id": "48", "headSha": request["headSha"], "baseRef": request["baseRef"]}; return self.pr
    def read_merge(self, pull_request_id): return self.merge
    def squash_merge(self, request): self.calls.append("merge"); self.merge = {"merged": True, "mergeSha": "b" * 40}; return {"mergeSha": "b" * 40}

class PublicationProviderTests(unittest.TestCase):
    def test_readback_prevents_duplicate_operations(self):
        port = FixtureProvider(); subject = module.PublicationProviderCoordinator(port)
        subject.push(operation_id="push-1", branch="codex/SAAS-48-x", head_sha=SHA)
        subject.push(operation_id="push-1", branch="codex/SAAS-48-x", head_sha=SHA)
        subject.pull_request(operation_id="pr-1", branch="codex/SAAS-48-x", base_ref="main", head_sha=SHA)
        subject.pull_request(operation_id="pr-1", branch="codex/SAAS-48-x", base_ref="main", head_sha=SHA)
        merged = subject.merge(operation_id="merge-1", pull_request_id="48", base_ref="main", head_sha=SHA)
        subject.merge(operation_id="merge-1", pull_request_id="48", base_ref="main", head_sha=SHA)
        self.assertEqual(["push", "pr", "merge"], port.calls); self.assertEqual("b" * 40, merged["mergeSha"])

    def test_forbidden_provider_capability_is_rejected(self):
        port = FixtureProvider(); port.list_checks = lambda: []
        with self.assertRaises(module.ProviderReconciliationError): module.PublicationProviderCoordinator(port)


class PublicationRefusalPrivacyTests(StateEngineTestCase):
    def test_persisted_refusal_is_closed_allowlisted_and_nested_payload_free(self):
        supervisor = importlib.import_module(package.__name__ + ".supervisor")
        engine = supervisor.SupervisorEngine(manager=self.manager)
        (engine.store.directories["operations"] / "privacy-operation").mkdir()
        secret = "privacy-sentinel-credential"
        digest = engine.publication_operations.record_refusal(
            "privacy-operation",
            {"statusCode": secret, "code": secret, "retryAfterSeconds": secret,
             "ambiguous": secret, "body": secret,
             "diagnostic": {"authorization": secret, "actor": "private-user"}},
            {"applied": secret, "ambiguous": secret, "merged": secret,
             "mergeability": secret, "request": {"cookie": secret},
             "url": "https://private.invalid/path", "headSha": secret,
             "mergeSha": secret, "baseRef": secret, "pullRequestId": secret},
        )
        record = engine.publication_operations.require_refusal("privacy-operation", digest)
        self.assertEqual({"code": "unclassified"}, record["classification"])
        self.assertEqual({}, record["reconciliation"])
        persisted = (engine.store.directories["operations"] / "privacy-operation" / "provider-refusal.json").read_text(encoding="utf-8")
        for sentinel in (secret, "body", "authorization", "actor", "cookie", "private.invalid"):
            self.assertNotIn(sentinel, persisted)

    def test_refusal_fields_require_exact_types_ranges_and_vocabularies(self):
        valid = module.normalized_refusal(
            {"statusCode": 429, "code": "timeout", "retryAfterSeconds": 1800, "ambiguous": True},
            {"applied": False, "ambiguous": False, "merged": False,
             "mergeability": True, "headSha": "a" * 40, "mergeSha": "b" * 40, "baseRef": "main"},
        )
        self.assertEqual(429, valid["classification"]["statusCode"])
        malformed = module.normalized_refusal(
            {"statusCode": True, "retryAfterSeconds": 1801, "ambiguous": 1},
            {"applied": 0, "merged": "false", "mergeability": None},
        )
        self.assertEqual({"classification": {}, "reconciliation": {}}, malformed)
