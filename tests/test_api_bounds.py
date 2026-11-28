"""Transport bounds without database or external services."""

import asyncio
import json
from threading import BoundedSemaphore
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import psycopg

from test_auth import SignedIdentityFixture
from life_planner.storage import PlanPage, PlanSummary, PostgresPlanner

from apps.api.middleware import RequestBoundsMiddleware
from apps.api.models import parse_time


class PlanDiscoveryBoundsTests(SignedIdentityFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from apps.api.app import create_app
        self.app = create_app(self.settings())
        self.client = self.enterContext(TestClient(self.app, raise_server_exceptions=False))
        self.headers = {"Authorization": "Bearer " + self.token()}
        self.storage = self.enterContext(patch.object(self.app.state.planner, "list_plans",
                                                      return_value=PlanPage((), None)))

    def test_canonical_query_bounds_and_unknown_or_duplicate_fields(self):
        cases = [[("limit", value)] for value in
                 ("", "0", "101", "01", "1.0", "1e1", "+1", "-1", " 1", "1 ", "true", "١", "1\n")]
        cases += [[("after", value)] for value in ("", "x" * 129, "a/b", "a b", "é", "a\n")]
        cases += [[("limit", "1"), ("limit", "2")], [("after", "a"), ("after", "a")],
                  [("user_id", "bob")], [("owner", "bob")], [("offset", "2")], [("extra", "private")]]
        for params in cases:
            with self.subTest(params=params):
                response = self.client.get("/v1/plans", headers=self.headers, params=params)
                self.assertEqual(400, response.status_code, response.text)
                self.assertEqual("invalid_request", response.json()["error"]["code"])
                self.assertEqual("no-store", response.headers.get("cache-control"))
                self.assertNotIn("private", response.text)
        self.storage.assert_not_called()

    def test_defaults_and_valid_query_use_verified_owner(self):
        from apps.api.auth import derive_owner
        from test_auth import ISSUER
        owner = derive_owner(ISSUER, "alice")
        response = self.client.get("/v1/plans", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.storage.assert_called_once_with(owner, limit=20, after=None)
        for limit in ("1", "100"):
            self.storage.reset_mock()
            response = self.client.get("/v1/plans", headers={**self.headers, "X-User-ID": "bob"},
                                       params={"limit": limit, "after": "A_1-"})
            self.assertEqual(200, response.status_code)
            self.storage.assert_called_once_with(owner, limit=int(limit), after="A_1-")

    def test_authentication_required_before_discovery(self):
        for headers in ({}, {"Authorization": "Bearer not-a-token"},
                        {"Authorization": "Bearer " + self.token(key=self.wrong_key)},
                        [("Authorization", self.headers["Authorization"])] * 2):
            response = self.client.get("/v1/plans", headers=headers)
            self.assertEqual(401, response.status_code)
            self.assertEqual("Bearer", response.headers["www-authenticate"])
            self.assertEqual("no-store", response.headers["cache-control"])
        self.storage.assert_not_called()

    def test_discovery_errors_are_sanitized_and_not_cached(self):
        for error, expected in ((psycopg.OperationalError("PRIVATE DATABASE URI"), 503),
                                (ValueError("PRIVATE ROW VALUE"), 500)):
            self.storage.side_effect = error
            response = self.client.get("/v1/plans", headers=self.headers)
            self.assertEqual(expected, response.status_code, response.text)
            self.assertNotIn("PRIVATE", response.text)
            self.assertEqual("no-store", response.headers["cache-control"])
            self.assertEqual({"error"}, set(response.json()))

    def test_public_schema_exposes_only_summary_fields_and_authenticated_operation(self):
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/v1/plans"]["get"]
        self.assertEqual([{"HTTPBearer": []}], operation["security"])
        self.assertEqual({"limit", "after"}, {param["name"] for param in operation["parameters"]})
        self.assertNotIn("422", operation["responses"])
        models = schema["components"]["schemas"]
        self.assertEqual({"plans", "next_after"}, set(models["PlanListResponse"]["properties"]))
        self.assertEqual({"plan_id", "revision"}, set(models["PlanSummaryResponse"]["properties"]))
        self.storage.return_value = PlanPage((PlanSummary("a", 2),), None)
        response = self.client.get("/v1/plans", headers=self.headers)
        self.assertEqual({"plans": [{"plan_id": "a", "revision": 2}], "next_after": None}, response.json())

    def test_storage_internal_bounds_fail_before_database_access(self):
        planner = PostgresPlanner("unused")
        with patch.object(planner, "_connect") as connect:
            for limit in (True, False, 0, 101, 1.0, "20", None):
                with self.subTest(limit=limit), self.assertRaises(ValueError):
                    planner.list_plans("alice", limit=limit)
            for after in (True, 1, "", "x" * 129, "a/b", "a\n"):
                with self.subTest(after=after), self.assertRaises(ValueError):
                    planner.list_plans("alice", after=after)
            for owner in (None, "", " ", 1):
                with self.subTest(owner=owner), self.assertRaises(ValueError):
                    planner.list_plans(owner)
            connect.assert_not_called()


class TimestampBoundsTests(unittest.TestCase):
    def test_unsupported_dates_and_offsets_fail_with_value_error(self):
        for value in ("0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00",
                      "2026-11-25T18:00:00+24:00", "2026-11-25T18:00:00+00:60",
                      "2000-01-01T00:00:00+01:00", "2100-12-31T23:59:59-01:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_time(value)


class RequestBoundsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = 0

        async def app(scope, receive, send):
            self.calls += 1
            await receive()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        self.middleware = RequestBoundsMiddleware(app)

    async def request(self, receive):
        events = []

        async def send(event):
            events.append(event)

        await self.middleware({"type": "http", "method": "GET", "headers": []}, receive, send)
        return events

    async def complete(self):
        return {"type": "http.request", "body": b"", "more_body": False}

    def assert_error(self, events, status, code):
        self.assertEqual(status, events[0]["status"])
        self.assertEqual(code, json.loads(events[1]["body"])["error"]["code"])
        self.assertIn((b"cache-control", b"no-store"), events[0]["headers"])

    async def test_stalled_body_times_out_and_releases_slot(self):
        self.middleware._slots = BoundedSemaphore(1)

        async def stalled():
            await asyncio.Event().wait()

        with patch.object(RequestBoundsMiddleware, "BODY_TIMEOUT", 0.03):
            events = await asyncio.wait_for(self.request(stalled), timeout=1)
        self.assert_error(events, 408, "request_timeout")
        self.assertEqual(0, self.calls)
        self.assertEqual(200, (await self.request(self.complete))[0]["status"])

    async def test_dripping_body_cannot_extend_total_deadline(self):
        received = 0

        async def dripping():
            nonlocal received
            received += 1
            await asyncio.sleep(0.001)
            return {"type": "http.request", "body": b"", "more_body": True}

        with patch.object(RequestBoundsMiddleware, "BODY_TIMEOUT", 0.03):
            events = await asyncio.wait_for(self.request(dripping), timeout=1)
        self.assert_error(events, 408, "request_timeout")
        self.assertGreater(received, 1)
        self.assertEqual(0, self.calls)

    async def test_disconnect_releases_slot_without_invoking_application(self):
        self.middleware._slots = BoundedSemaphore(1)

        async def disconnected():
            return {"type": "http.disconnect"}

        self.assertEqual([], await self.request(disconnected))
        self.assertEqual(0, self.calls)
        self.assertEqual(200, (await self.request(self.complete))[0]["status"])

    async def test_saturation_rejects_extra_request_and_recovers(self):
        entered = 0
        full = asyncio.Event()
        release = asyncio.Event()

        async def held():
            nonlocal entered
            entered += 1
            if entered == 16:
                full.set()
            await release.wait()
            return await self.complete()

        tasks = [asyncio.create_task(self.request(held)) for _ in range(16)]
        try:
            await asyncio.wait_for(full.wait(), timeout=1)
            events = await self.request(self.complete)
            self.assert_error(events, 503, "temporarily_unavailable")
            self.assertIn((b"retry-after", b"1"), events[0]["headers"])
            self.assertEqual(0, self.calls)
        finally:
            release.set()
            results = await asyncio.gather(*tasks)
        self.assertTrue(all(result[0]["status"] == 200 for result in results))
        self.assertEqual(200, (await self.request(self.complete))[0]["status"])


if __name__ == "__main__":
    unittest.main()
