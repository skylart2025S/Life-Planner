"""Transport bounds without database or external services."""

import asyncio
import json
from threading import BoundedSemaphore
import unittest
from unittest.mock import patch

from apps.api.middleware import RequestBoundsMiddleware
from apps.api.models import parse_time


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
