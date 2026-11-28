"""Optional OpenAI Responses adapter for the validated intent boundary.

Requires explicit server-side credentials and a model supporting Structured Outputs.
No provider is activated merely by importing this module. No live-model quality,
account availability or cost claim follows from transport tests. Model text remains
untrusted and must pass life_planner.intent.interpret before use.

A new client is closed on every call; no redirects, environment proxies, retries or
tools are enabled. Identity encoding is required so compressed payloads cannot
expand beyond the response bound. Callers should implement account quotas before
exposing this adapter through an API. store=False is not a complete retention policy.
"""

import asyncio
import json
import re

import httpx

from life_planner.intent import (INSTRUCTIONS, MAX_MESSAGE_CHARS, MAX_OUTPUT_BYTES,
                                 MAX_REPLY_CHARS, MAX_REQUEST_BYTES, MAX_TIMEOUT_SECONDS,
                                 ProviderRequest, SCHEMA_VERSION)


_ENDPOINT = "https://api.openai.com/v1/responses"
MAX_RESPONSE_BYTES = 131_072
MAX_OUTPUT_TOKENS = 2_048
_WRAPPER_INSTRUCTION = (
    '\nTransport format: wrap the entire intent object described above in exactly '
    'one outer object with the single key "intent". For example, '
    '{"intent":{"type":"clarification","question":"Which day?"}}. '
    'This wrapper replaces the earlier top-level output format. No extra keys.'
)


class OpenAIIntentError(RuntimeError):
    """Sanitized provider/response failure; contains no request or provider body."""


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("Invalid JSON constant")


def _json(value):
    return json.loads(value, object_pairs_hook=_object, parse_constant=_constant)


def _schema():
    variants = []
    for kind, fields in (("move", ("item_id", "new_start")),
                         ("clarification", ("question",)), ("unsupported", ("reason",))):
        properties = {"type": {"type": "string", "enum": [kind]}}
        properties.update({field: {"type": "string"} for field in fields})
        variants.append({"type": "object", "properties": properties,
                         "required": ["type", *fields], "additionalProperties": False})
    return {"type": "object", "properties": {"intent": {"anyOf": variants}},
            "required": ["intent"], "additionalProperties": False}


def _bounded_text(value, chars):
    if (type(value) is not str or not value.strip() or len(value) > chars or "\x00" in value):
        raise ValueError("Invalid text")
    value.encode("utf-8")
    return value


def _unwrap(data):
    if (type(data) is not dict or data.get("object") != "response"
            or data.get("status") != "completed" or data.get("error") is not None
            or data.get("incomplete_details") is not None):
        raise ValueError("Response did not complete")
    output = data.get("output")
    if type(output) is not list or not 1 <= len(output) <= 128:
        raise ValueError("Invalid response output")
    text = None
    for item in output:
        if type(item) is not dict:
            raise ValueError("Invalid output item")
        if item.get("type") == "reasoning":
            if item.get("status") not in (None, "completed"):
                raise ValueError("Incomplete reasoning")
            continue
        if (item.get("type") != "message" or item.get("role") != "assistant"
                or item.get("status") != "completed" or text is not None):
            raise ValueError("Unexpected output item")
        content = item.get("content")
        if (type(content) is not list or len(content) != 1 or type(content[0]) is not dict
                or content[0].get("type") != "output_text"):
            raise ValueError("Expected a single text result")
        text = _bounded_text(content[0].get("text"), MAX_OUTPUT_BYTES)
        if len(text.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ValueError("Intent text too large")
    if text is None:
        raise ValueError("Missing intent output")
    wrapper = _json(text)
    if type(wrapper) is not dict or set(wrapper) != {"intent"}:
        raise ValueError("Invalid intent wrapper")
    intent = wrapper["intent"]
    if type(intent) is not dict:
        raise ValueError("Invalid intent")
    kind = intent.get("type")
    fields = {"move": {"type", "item_id", "new_start"},
              "clarification": {"type", "question"}, "unsupported": {"type", "reason"}}
    if type(kind) is not str or kind not in fields or set(intent) != fields[kind]:
        raise ValueError("Invalid intent fields")
    for field in fields[kind] - {"type"}:
        _bounded_text(intent[field], 128 if field == "item_id" else 64 if field == "new_start"
                      else MAX_REPLY_CHARS)
    # Semantic IDs/dates/ownership/conflicts remain the interpreter's responsibility.
    return json.dumps(intent, ensure_ascii=False, separators=(",", ":"))


class OpenAIIntentProvider:
    def __init__(self, api_key: str, model: str, *, max_output_tokens: int = 512,
                 transport: httpx.AsyncBaseTransport | None = None):
        """transport is an injection point for offline tests, not endpoint selection."""
        if (type(api_key) is not str or re.fullmatch(r"[\x21-\x7e]{1,4096}", api_key) is None
                or type(model) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", model) is None
                or type(max_output_tokens) is not int or not 64 <= max_output_tokens <= MAX_OUTPUT_TOKENS):
            raise ValueError("Explicit valid provider configuration is required")
        self._api_key = api_key
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._transport = transport

    def __repr__(self):
        return "OpenAIIntentProvider(credentials=<redacted>)"

    def _body(self, request):
        if (type(request) is not ProviderRequest or request.schema_version != SCHEMA_VERSION
                or request.instructions != INSTRUCTIONS):
            raise ValueError("Unsupported intent request")
        _bounded_text(request.message, MAX_MESSAGE_CHARS)
        _bounded_text(request.context_json, MAX_REQUEST_BYTES)
        if len(json.dumps(request.__dict__, ensure_ascii=False).encode("utf-8")) > MAX_REQUEST_BYTES:
            raise ValueError("Request too large")
        context = _json(request.context_json)
        if type(context) is not dict or set(context) != {"timezone", "now", "items"}:
            raise ValueError("Invalid context fields")
        if type(context["items"]) is not list or len(context["items"]) > 500:
            raise ValueError("Invalid context items")
        for item in context["items"]:
            if type(item) is not dict or set(item) != {"id", "title", "kind", "start", "end", "linked_to", "fixed"}:
                raise ValueError("Invalid item fields")
        data = json.dumps({"message": request.message, "context": context}, ensure_ascii=False,
                          separators=(",", ":"))
        return {"model": self._model, "instructions": INSTRUCTIONS + _WRAPPER_INSTRUCTION,
                "input": [{"role": "user", "content": [{"type": "input_text", "text": data}]}],
                "text": {"format": {"type": "json_schema", "name": "planner_intent_v1",
                                    "strict": True, "schema": _schema()}},
                "max_output_tokens": self._max_output_tokens, "store": False, "tools": []}

    async def complete(self, request: ProviderRequest) -> str:
        """One bounded call. Errors are sanitized; caller cancellation propagates."""
        try:
            body = self._body(request)
            async with asyncio.timeout(MAX_TIMEOUT_SECONDS) as deadline:
                async with httpx.AsyncClient(
                    transport=self._transport, timeout=httpx.Timeout(MAX_TIMEOUT_SECONDS),
                    follow_redirects=False, trust_env=False,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
                ) as client:
                    async with client.stream("POST", _ENDPOINT, json=body, headers={
                        "Authorization": f"Bearer {self._api_key}", "Accept": "application/json",
                        "Accept-Encoding": "identity",
                    }) as response:
                        if response.status_code != 200:
                            raise ValueError("Provider request failed")
                        if (response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                                != "application/json"
                                or response.headers.get("content-encoding", "identity").strip().lower() != "identity"):
                            raise ValueError("Unsupported provider encoding")
                        buffer = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(buffer) + len(chunk) > MAX_RESPONSE_BYTES:
                                raise ValueError("Response too large")
                            buffer.extend(chunk)
                        result = _unwrap(_json(bytes(buffer).decode("utf-8")))
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            if deadline.expired():
                raise TimeoutError
            return result
        except (TimeoutError, httpx.TimeoutException):
            raise TimeoutError("Intent provider timed out") from None
        except Exception:
            raise OpenAIIntentError("Intent provider request failed") from None
