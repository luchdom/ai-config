from __future__ import annotations

import uuid

from tests.linear_delivery_supervisor.support_state_engine import (
    StateEngineTestCase,
    contracts,
    operations_module,
    store_module,
    supervisor_module,
)


class OperationTests(StateEngineTestCase):
    def test_exact_replay_returns_result_and_changed_request_rejects(self) -> None:
        journal = operations_module.OperationJournal(self.store)
        operation_id = str(uuid.uuid4())
        request = {"workflowId": self.descriptor["workflowId"]}
        self.assertEqual("created", journal.begin(operation_id=operation_id, operation="Status", request=request)["status"])
        result = journal.complete(
            operation_id=operation_id,
            operation="Status",
            request=request,
            result={"status": "ready"},
        )
        self.assertEqual("ready", result["status"])
        replay = journal.begin(operation_id=operation_id, operation="Status", request=request)
        self.assertEqual("replayed", replay["status"])
        evidence = journal.load(operation_id)
        contracts.validate_contract("operation-journal", evidence["journal"])
        self.assertEqual(1, evidence["journal"]["attemptCount"])
        self.assertIsNotNone(evidence["journal"]["afterStateHash"])
        self.assertTrue(evidence["journal"]["resultRef"].endswith("result.json"))
        with self.assertRaises(Exception):
            journal.begin(operation_id=operation_id, operation="Status", request={"workflowId": "changed"})
        contracts.validate_contract("supervisor-state", self.store.load_state())

    def test_result_written_before_journal_completion_recovers_exactly(self) -> None:
        journal = operations_module.OperationJournal(self.store)
        operation_id = str(uuid.uuid4())
        request = {"workflowId": self.descriptor["workflowId"]}
        begun = journal.begin(
            operation_id=operation_id, operation="Status", request=request
        )
        result = {"status": "ready"}
        operation_dir = self.store.guard.directory(
            self.store.directories["operations"] / operation_id
        )
        self.store.guard.write_json(
            self.store.guard.leaf(operation_dir / "result.json"),
            {
                "schemaVersion": "1.0",
                "operationId": operation_id,
                "operation": "Status",
                "requestHash": begun["requestSha256"],
                "status": "completed",
                "resultHash": "sha256:" + store_module.sha256_json(result),
                "result": result,
            },
        )
        engine = supervisor_module.SupervisorEngine(manager=self.manager)
        recovered = engine.recovery.recover()
        self.assertEqual([operation_id], recovered["recoveredOperations"])
        evidence = engine.operations.load(operation_id)
        self.assertEqual("completed", evidence["journal"]["status"])
        self.assertEqual(result, evidence["result"])

    def test_request_only_pre_action_crash_repairs_as_failed(self) -> None:
        operation_id = str(uuid.uuid4())
        request = {"workflowId": self.descriptor["workflowId"]}
        operation_dir = self.store.guard.directory(
            self.store.directories["operations"] / operation_id, create=True
        )
        self.store.guard.write_json(
            self.store.guard.leaf(operation_dir / "request.json"),
            {
                "schemaVersion": "1.0",
                "operationId": operation_id,
                "operation": "Status",
                "requestSha256": "sha256:" + store_module.sha256_json(request),
                "request": request,
            },
        )
        engine = supervisor_module.SupervisorEngine(manager=self.manager)
        recovered = engine.recovery.recover()
        self.assertEqual([operation_id], recovered["repairedPreActionOperations"])
        self.assertEqual([operation_id], recovered["failedOperations"])
        self.assertEqual("failed", engine.operations.load(operation_id)["journal"]["status"])
