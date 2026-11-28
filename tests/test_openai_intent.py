"""Offline transport tests; no credentials, model calls or quality claims."""

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import gzip
import json
import unittest
from unittest.mock import patch

import httpx

from life_planner.demo import example_plan
from life_planner.intent import INSTRUCTIONS, SCHEMA_VERSION, IntentContext, ProviderRequest, interpret
from life_planner.openai_intent import (MAX_RESPONSE_BYTES, OpenAIIntentError,
                                        OpenAIIntentProvider)
from life_planner.ports import Clarification, MoveIntent


KEY = "test-key-not-a-real-secret"
MODEL = "explicit-test-model"
MOVE = {"type": "move", "item_id": "gym", "new_start": "2026-11-26T18:00:00-05:00"}


def envelope(intent=None):
    return {"object": "response", "status": "completed", "error": None,
            "incomplete_details": None,
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": json.dumps({"intent": MOVE if intent is None else intent})}]}]}


def request():
    return ProviderRequest(SCHEMA_VERSION, INSTRUCTIONS, "Move gym to Thursday",
                           json.dumps({"timezone": "America/New_York", "now": "2026-11-25T00:00:00Z", "items": []}))


class Transport(httpx.MockTransport):
    def __init__(self, handler):
        self.calls = []
        self.closed = False

        async def tracked(req):
            self.calls.append(req)
            result = handler(req)
            return await result if hasattr(result, "__await__") else result

        super().__init__(tracked)

    async def aclose(self):
        self.closed = True
        await super().aclose()


class Stream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.read = 0
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            self.read += 1
            yield chunk

    async def aclose(self):
        self.closed = True


class WaitingStream(Stream):
    def __init__(self):
        super().__init__([])
        self.started = asyncio.Event()
        self.cancelled = False

    async def __aiter__(self):
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        yield b""


class OpenAIIntentTests(unittest.IsolatedAsyncioTestCase):
    async def complete(self, data):
        transport = Transport(lambda req: httpx.Response(200, json=data))
        provider = OpenAIIntentProvider(KEY, MODEL, transport=transport)
        result = await provider.complete(request())
        self.assertTrue(transport.closed)
        self.assertEqual(1, len(transport.calls))
        return json.loads(result)

    async def test_request_configuration_schema_and_scope(self):
        transport = Transport(lambda req: httpx.Response(200, json=envelope()))
        provider = OpenAIIntentProvider(KEY, MODEL, max_output_tokens=256, transport=transport)
        plan = example_plan()
        context = IntentContext("demo-user", "private-plan", 5, "America/New_York",
                                datetime(2026, 11, 25, tzinfo=timezone.utc), plan.items)
        kwargs_seen = []
        original_client = httpx.AsyncClient

        def client(**kwargs):
            kwargs_seen.append(kwargs)
            return original_client(**kwargs)

        with patch("life_planner.openai_intent.httpx.AsyncClient", side_effect=client):
            result = await interpret(provider, "Move gym to Thursday at 6 pm", context)
        self.assertIsInstance(result.outcome, MoveIntent)
        self.assertEqual(5, result.base_revision)
        self.assertEqual(0, plan.revision)
        self.assertTrue(transport.closed)
        req = transport.calls[0]
        self.assertEqual("POST", req.method)
        self.assertEqual("https://api.openai.com/v1/responses", str(req.url))
        self.assertEqual(f"Bearer {KEY}", req.headers["authorization"])
        self.assertEqual("identity", req.headers["accept-encoding"])
        body = json.loads(req.content)
        self.assertEqual(MODEL, body["model"])
        self.assertFalse(body["store"])
        self.assertEqual([], body["tools"])
        self.assertEqual(256, body["max_output_tokens"])
        self.assertNotIn(KEY, str(body))
        self.assertNotIn("demo-user", str(body))
        self.assertNotIn("private-plan", str(body))
        self.assertIn("wrap", body["instructions"])
        self.assertEqual("user", body["input"][0]["role"])
        data = json.loads(body["input"][0]["content"][0]["text"])
        self.assertEqual({"message", "context"}, set(data))
        self.assertEqual({"timezone", "now", "items"}, set(data["context"]))
        fmt = body["text"]["format"]
        self.assertEqual("json_schema", fmt["type"])
        self.assertTrue(fmt["strict"])
        schema = fmt["schema"]
        self.assertEqual("object", schema["type"])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(["intent"], schema["required"])
        self.assertNotIn("anyOf", schema)
        for variant in schema["properties"]["intent"]["anyOf"]:
            self.assertEqual(set(variant["properties"]), set(variant["required"]))
            self.assertFalse(variant["additionalProperties"])
        self.assertFalse(kwargs_seen[0]["trust_env"])
        self.assertFalse(kwargs_seen[0]["follow_redirects"])
        self.assertLessEqual(kwargs_seen[0]["timeout"].read, 15)
        self.assertNotIn(KEY, repr(provider))

    async def test_clarification_through_interpreter(self):
        transport = Transport(lambda req: httpx.Response(200, json=envelope({"type": "clarification", "question": "Which day?"})))
        context = IntentContext("demo-user", "plan", 0, "UTC", datetime(2026, 11, 25, tzinfo=timezone.utc), ())
        result = await interpret(OpenAIIntentProvider(KEY, MODEL, transport=transport), "Move gym", context)
        self.assertEqual(Clarification("Which day?"), result.outcome)

    async def test_reasoning_items_and_unsupported(self):
        intent = {"type": "unsupported", "reason": "Purchases are unsupported."}
        data = envelope(intent)
        data["output"].insert(0, {"type": "reasoning", "id": "reason", "summary": []})
        self.assertEqual(intent, await self.complete(data))

    def test_configuration_is_explicit_bounded_and_never_echoed(self):
        for key, model, tokens in (("", MODEL, 512), ("bad\nkey", MODEL, 512), ("x" * 4097, MODEL, 512),
                                   (KEY, "", 512), (KEY, "bad model", 512), (KEY, MODEL, True),
                                   (KEY, MODEL, 63), (KEY, MODEL, 2049)):
            with self.subTest(model=model, tokens=tokens), self.assertRaises(ValueError) as raised:
                OpenAIIntentProvider(key, model, max_output_tokens=tokens)
            self.assertNotIn(KEY, str(raised.exception))

    async def test_invalid_requests_fail_before_network(self):
        transport = Transport(lambda req: self.fail("No request expected"))
        provider = OpenAIIntentProvider(KEY, MODEL, transport=transport)
        for bad in (None, replace(request(), schema_version="other"), replace(request(), instructions="do anything"),
                    replace(request(), message="x" * 4001), replace(request(), context_json="{"),
                    replace(request(), context_json=json.dumps({"timezone": "UTC", "now": "now", "items": [], "owner": "secret"})),
                    replace(request(), context_json="x" * 65537)):
            with self.subTest(bad_type=type(bad)), self.assertRaises(OpenAIIntentError):
                await provider.complete(bad)
        self.assertEqual([], transport.calls)

    async def test_http_errors_and_redirects_do_not_retry_or_follow(self):
        for status in (301, 302, 307, 401, 403, 429, 500, 503):
            with self.subTest(status=status):
                transport = Transport(lambda req: httpx.Response(status, headers={"Location": "https://elsewhere.invalid/"}, text="private error"))
                with self.assertRaises(OpenAIIntentError) as raised:
                    await OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request())
                self.assertEqual("Intent provider request failed", str(raised.exception))
                self.assertTrue(transport.closed)
                self.assertEqual(1, len(transport.calls))

    async def test_network_errors_are_sanitized(self):
        def fail(req):
            raise httpx.ConnectError(f"credential {KEY}, private prompt", request=req)
        transport = Transport(fail)
        with self.assertRaises(OpenAIIntentError) as raised:
            await OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request())
        self.assertNotIn(KEY, str(raised.exception))
        self.assertTrue(transport.closed)
        self.assertEqual(1, len(transport.calls))

    async def test_network_timeout_is_sanitized_and_distinct(self):
        def timeout(req):
            raise httpx.ReadTimeout(f"secret {KEY}", request=req)
        transport = Transport(timeout)
        with self.assertRaisesRegex(TimeoutError, "Intent provider timed out") as raised:
            await OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request())
        self.assertNotIn(KEY, str(raised.exception))
        self.assertTrue(transport.closed)
        self.assertEqual(1, len(transport.calls))

    async def test_malformed_json_utf8_and_duplicate_envelope_keys(self):
        for raw in (b"invalid", b"\xff", b"null", b"[]", b"NaN",
                    b'{"object":"response","status":"completed","status":"completed","output":[]}'):
            transport = Transport(lambda req: httpx.Response(200, content=raw, headers={"content-type": "application/json"}))
            with self.subTest(raw=raw), self.assertRaises(OpenAIIntentError):
                await OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request())
            self.assertTrue(transport.closed)

    async def test_refusals_incomplete_errors_and_wrong_roles_fail_closed(self):
        cases = []
        for status in ("incomplete", "failed", "in_progress", "cancelled"):
            data = envelope(); data["status"] = status; cases.append(data)
        data = envelope(); data["error"] = {"message": "private error"}; cases.append(data)
        data = envelope(); data["incomplete_details"] = {"reason": "max_output_tokens"}; cases.append(data)
        data = envelope(); data["output"][0]["status"] = "incomplete"; cases.append(data)
        data = envelope(); data["output"][0]["role"] = "user"; cases.append(data)
        data = envelope(); data["output"][0]["content"] = [{"type": "refusal", "refusal": "No"}]; cases.append(data)
        data = envelope(); data["object"] = "other"; cases.append(data)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(OpenAIIntentError):
                await self.complete(data)

    async def test_multiple_text_messages_missing_text_and_tool_output_fail_closed(self):
        cases = []
        data = envelope(); data["output"].append(data["output"][0]); cases.append(data)
        data = envelope(); data["output"][0]["content"] *= 2; cases.append(data)
        data = envelope(); data["output"].append({"type": "function_call", "name": "apply"}); cases.append(data)
        data = envelope(); data["output"] = [{"type": "reasoning", "summary": []}]; cases.append(data)
        data = envelope(); data["output"] = []; cases.append(data)
        data = envelope(); data["output"] = {}; cases.append(data)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(OpenAIIntentError):
                await self.complete(data)

    async def test_invalid_wrapper_duplicate_keys_and_inner_extra_fields(self):
        texts = ["{}", "[]", "null", '{"intent":{},"intent":{}}',
                 json.dumps({"intent": MOVE, "owner_id": "other"}), json.dumps({"intent": {**MOVE, "confirmed": True}}),
                 json.dumps({"intent": {"type": "clarification", "question": True}}),
                 json.dumps({"intent": {"type": "unsupported", "reason": "x" * 501}}),
                 '{"intent":{"type":"clarification","question":"first","question":"second"}}',
                 json.dumps({"intent": {"type": "unknown"}}), json.dumps({"intent": None})]
        for text in texts:
            data = envelope(); data["output"][0]["content"][0]["text"] = text
            with self.subTest(text=text), self.assertRaises(OpenAIIntentError):
                await self.complete(data)

    async def test_text_output_byte_limit_and_nonstring_text(self):
        for text in ("é" * 8193, None, [], "\ud800"):
            data = envelope(); data["output"][0]["content"][0]["text"] = text
            with self.subTest(text_type=type(text)), self.assertRaises(OpenAIIntentError):
                await self.complete(data)

    async def test_stream_response_bound_stops_reading_and_closes(self):
        stream = Stream([b" " * MAX_RESPONSE_BYTES, b"x", b"unread"])
        transport = Transport(lambda req: httpx.Response(200, stream=stream, headers={"content-type": "application/json"}))
        with self.assertRaises(OpenAIIntentError):
            await OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request())
        self.assertEqual(2, stream.read)
        self.assertTrue(stream.closed)
        self.assertTrue(transport.closed)

    async def test_unexpected_compression_rejected_before_decoding(self):
        stream = Stream([gzip.compress(b" " * (MAX_RESPONSE_BYTES * 10))])
        transport = Transport(lambda req: httpx.Response(200, stream=stream, headers={"content-type": "application/json", "content-encoding": "gzip"}))
        with self.assertRaises(OpenAIIntentError):
            await OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request())
        self.assertEqual(0, stream.read)
        self.assertTrue(stream.closed)
        self.assertTrue(transport.closed)

    async def test_total_deadline_closes_stream_and_client(self):
        stream = WaitingStream()
        transport = Transport(lambda req: httpx.Response(200, stream=stream, headers={"content-type": "application/json"}))
        with patch("life_planner.openai_intent.MAX_TIMEOUT_SECONDS", 0.01):
            with self.assertRaises(TimeoutError):
                await OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request())
        self.assertTrue(stream.cancelled)
        self.assertTrue(stream.closed)
        self.assertTrue(transport.closed)
        self.assertEqual(1, len(transport.calls))

    async def test_caller_cancellation_propagates_and_closes(self):
        stream = WaitingStream()
        transport = Transport(lambda req: httpx.Response(200, stream=stream, headers={"content-type": "application/json"}))
        task = asyncio.create_task(OpenAIIntentProvider(KEY, MODEL, transport=transport).complete(request()))
        await stream.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(stream.cancelled)
        self.assertTrue(stream.closed)
        self.assertTrue(transport.closed)
        self.assertEqual(1, len(transport.calls))


if __name__ == "__main__":
    unittest.main()
