from __future__ import annotations

import unittest

from tests.linear_delivery_control_plane.support import package


linear = __import__(package.__name__ + ".linear_transport", fromlist=["LinearTransport"])
ntfy_module = __import__(package.__name__ + ".ntfy_transport", fromlist=["NtfyTransport"])


class LinearTransportTests(unittest.TestCase):
    def transport(self, requester, *, sleeps=None, attempts=3):
        return linear.LinearTransport(
            endpoint="https://api.linear.app/graphql",
            allowed_host="api.linear.app",
            requester=requester,
            sleeper=(sleeps if sleeps is not None else []).append,
            max_attempts=attempts,
        )

    def test_endpoint_redirect_and_graphql_errors_fail_closed(self):
        with self.assertRaises(linear.LinearConfigurationError):
            linear.validate_endpoint("https://evil.invalid/graphql", "api.linear.app")
        redirect = self.transport(lambda **_: {"status": 302, "body": {}, "url": "https://evil.invalid"})
        with self.assertRaises(linear.LinearProtocolError):
            redirect.execute("query X {x}", {}, api_key="sentinel-key")
        graphql = self.transport(lambda **_: {"status": 200, "body": {"errors": [{"message": "no"}]}})
        with self.assertRaises(linear.LinearGraphQLError) as raised:
            graphql.execute("query X {x}", {}, api_key="sentinel-key")
        self.assertNotIn("sentinel-key", str(raised.exception))

    def test_reads_retry_with_bounded_backoff(self):
        calls = []
        sleeps = []
        responses = iter([
            {"status": 429, "body": {}},
            {"status": 503, "body": {}},
            {"status": 200, "body": {"data": {"ok": True}}},
        ])
        result = self.transport(lambda **kwargs: calls.append(kwargs["body"]) or next(responses), sleeps=sleeps).execute(
            "query X($id: ID!) {x(id: $id)}", {"id": "one"}, api_key="sentinel-key"
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(sleeps, [1.0, 2.0])
        self.assertTrue(all("sentinel-key" not in body for body in calls))

    def test_pagination_requires_progress_and_completes_all_pages(self):
        responses = iter([
            {"status": 200, "body": {"data": {"issues": {"nodes": [{"id": "1"}], "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"}}}}},
            {"status": 200, "body": {"data": {"issues": {"nodes": [{"id": "2"}], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}},
        ])
        result = self.transport(lambda **_: next(responses)).paginate(
            "query Issues($after: String) {issues {nodes {id}}}", {}, api_key="key", connection="issues"
        )
        self.assertEqual([item["id"] for item in result], ["1", "2"])
        stuck = self.transport(lambda **_: {"status": 200, "body": {"data": {"issues": {"nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": ""}}}}})
        with self.assertRaises(linear.LinearProtocolError):
            stuck.paginate("query X {issues}", {}, api_key="key", connection="issues")

    def test_mutation_ambiguity_uses_readback_without_duplicate_write(self):
        observations = iter([{"state": "Todo"}, {"state": "In Progress"}])
        writes = []
        result = self.transport(lambda **_: {}).reconciled_mutation(
            operation_id="op-1",
            observe=lambda: next(observations),
            mutate=lambda operation_id: writes.append(operation_id) or (_ for _ in ()).throw(linear.LinearAmbiguousWrite("ambiguous")),
            is_applied=lambda value: value["state"] == "In Progress",
        )
        self.assertEqual(result["status"], "reconciled")
        self.assertEqual(writes, ["op-1"])

    def test_graphql_mutation_errors_always_enter_readback_reconciliation(self):
        for body in (
            {"errors": [{"message": "partial"}], "data": {"issueUpdate": {"success": True}}},
            {"errors": [{"message": "unknown"}]},
        ):
            observations = iter([{"state": "Todo"}, {"state": "In Progress"}])
            transport = self.transport(
                lambda **_: {"status": 200, "body": body}, attempts=1
            )
            result = transport.reconciled_mutation(
                operation_id="op-graphql",
                observe=lambda: next(observations),
                mutate=lambda operation_id: transport.execute(
                    "mutation X($operationId: String!) {issueUpdate {success}}",
                    {}, api_key="key", mutation=True, operation_id=operation_id,
                ),
                is_applied=lambda value: value["state"] == "In Progress",
            )
            self.assertEqual(result["status"], "reconciled")

        observations = iter([{"state": "Todo"}, {"state": "Todo"}])
        transport = self.transport(
            lambda **_: {"status": 200, "body": {"errors": [{"message": "unknown"}]}},
            attempts=1,
        )
        with self.assertRaises(linear.LinearAmbiguousWrite):
            transport.reconciled_mutation(
                operation_id="op-not-applied",
                observe=lambda: next(observations),
                mutate=lambda operation_id: transport.execute(
                    "mutation X {issueUpdate {success}}", {}, api_key="key",
                    mutation=True, operation_id=operation_id,
                ),
                is_applied=lambda value: value["state"] == "In Progress",
            )

    def test_every_post_dispatch_protocol_ambiguity_enters_readback(self):
        responses = (
            {"status": 200, "body": "{not-json"},
            {"status": 200, "body": {"extensions": {}}},
            ["not", "an", "envelope"],
        )
        for index, response in enumerate(responses):
            writes = []
            transport = self.transport(
                lambda **_: writes.append(index) or response, attempts=1
            )
            observations = iter([{"state": "Todo"}, {"state": "In Progress"}])
            result = transport.reconciled_mutation(
                operation_id=f"op-applied-{index}",
                observe=lambda: next(observations),
                mutate=lambda operation_id: transport.execute(
                    "mutation X {issueUpdate {success}}", {}, api_key="key",
                    mutation=True, operation_id=operation_id,
                ),
                is_applied=lambda value: value["state"] == "In Progress",
            )
            self.assertEqual(result["status"], "reconciled")
            self.assertEqual(writes, [index])

            observations = iter([{"state": "Todo"}, {"state": "Todo"}])
            with self.assertRaises(linear.LinearAmbiguousWrite):
                transport.reconciled_mutation(
                    operation_id=f"op-not-applied-{index}",
                    observe=lambda: next(observations),
                    mutate=lambda operation_id: transport.execute(
                        "mutation X {issueUpdate {success}}", {}, api_key="key",
                        mutation=True, operation_id=operation_id,
                    ),
                    is_applied=lambda value: value["state"] == "In Progress",
                )

            reads = 0
            def ambiguous_observe():
                nonlocal reads
                reads += 1
                if reads == 1:
                    return {"state": "Todo"}
                raise RuntimeError("readback unavailable")
            with self.assertRaises(linear.LinearAmbiguousWrite):
                transport.reconciled_mutation(
                    operation_id=f"op-ambiguous-{index}",
                    observe=ambiguous_observe,
                    mutate=lambda operation_id: transport.execute(
                        "mutation X {issueUpdate {success}}", {}, api_key="key",
                        mutation=True, operation_id=operation_id,
                    ),
                    is_applied=lambda value: value["state"] == "In Progress",
                )

        with self.assertRaises(linear.LinearConfigurationError):
            self.transport(lambda **_: self.fail("must not dispatch")).execute(
                "mutation X {issueUpdate {success}}", {}, api_key="",
                mutation=True, operation_id="op-config",
            )
        with self.assertRaises(linear.LinearProtocolError):
            self.transport(lambda **_: {"status": 200, "body": "{bad"}).execute(
                "query X {issues {id}}", {}, api_key="key",
            )
        calls = 0

        def ambiguous_observe():
            nonlocal calls
            calls += 1
            if calls == 1:
                return {"state": "Todo"}
            raise RuntimeError("readback unavailable")

        with self.assertRaises(linear.LinearAmbiguousWrite):
            transport.reconciled_mutation(
                operation_id="op-readback-ambiguous",
                observe=ambiguous_observe,
                mutate=lambda operation_id: transport.execute(
                    "mutation X {issueUpdate {success}}", {}, api_key="key",
                    mutation=True, operation_id=operation_id,
                ),
                is_applied=lambda value: value["state"] == "In Progress",
            )


class NtfyTransportTests(unittest.TestCase):
    def test_retry_outcome_is_redacted_and_stable(self):
        responses = iter([{"status": 503}, {"status": 204}])
        sleeps = []
        transport = ntfy_module.NtfyTransport(requester=lambda **_: next(responses), sleeper=sleeps.append)
        result = transport.publish(
            base_url="https://ntfy.sh", topic="private-topic", allowed_hosts={"ntfy.sh"},
            title="Action", message="See Linear", click_url="https://linear.app/x",
            event_id="attention-1", token="sentinel-token",
        )
        self.assertEqual(result, {"status": "delivered", "eventId": "attention-1", "attempts": 2})
        self.assertEqual(sleeps, [1.0])
        self.assertNotIn("sentinel-token", repr(result))

    def test_redirect_is_not_followed(self):
        transport = ntfy_module.NtfyTransport(
            requester=lambda **_: {"status": 302, "url": "https://evil.invalid"}
        )
        result = transport.publish(
            base_url="https://ntfy.sh", topic="topic", allowed_hosts={"ntfy.sh"},
            title="A", message="B", click_url="https://linear.app/x", event_id="event-1"
        )
        self.assertEqual(result["reason"], "endpoint-drift")


if __name__ == "__main__":
    unittest.main()
