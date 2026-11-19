"""ASGI request caps apply before parsing or any authenticated side effects."""

import asyncio
import json
from threading import BoundedSemaphore
from uuid import uuid4

from apps.api.auth import _unique_object
from apps.api.errors import error_response


class RequestBoundsMiddleware:
    MAX_BODY = 64 * 1024
    BODY_TIMEOUT = 10.0

    def __init__(self, app):
        self.app = app
        self._slots = BoundedSemaphore(16)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def reject(status, code, message):
            await error_response(status, code, message, request_id)(scope, receive, send)

        if not self._slots.acquire(blocking=False):
            return await reject(503, "temporarily_unavailable", "Service temporarily unavailable")
        response_started = False
        try:
            headers = scope.get("headers", [])
            lengths = [value for name, value in headers if name.lower() == b"content-length"]
            if len(lengths) > 1 or lengths and (not lengths[0].isdigit() or len(lengths[0]) > 12):
                return await reject(400, "invalid_request", "Invalid request headers")
            if lengths and int(lengths[0]) > self.MAX_BODY:
                return await reject(413, "request_too_large", "Request body exceeds 64 KiB")
            body = bytearray()
            try:
                async with asyncio.timeout(self.BODY_TIMEOUT):
                    while True:
                        event = await receive()
                        if event["type"] == "http.disconnect":
                            return
                        body.extend(event.get("body", b""))
                        if len(body) > self.MAX_BODY:
                            return await reject(413, "request_too_large", "Request body exceeds 64 KiB")
                        if not event.get("more_body", False):
                            break
            except TimeoutError:
                return await reject(408, "request_timeout", "Request body was not received in time")
            if scope["method"] == "POST":
                types = [value for name, value in headers if name.lower() == b"content-type"]
                if len(types) != 1 or types[0].split(b";", 1)[0].strip().lower() != b"application/json":
                    return await reject(415, "unsupported_media_type", "Use application/json")
                try:
                    json.loads(body, object_pairs_hook=_unique_object,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                except (ValueError, UnicodeError, RecursionError):
                    return await reject(400, "invalid_request", "Malformed JSON request")
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            async def private_send(message):
                nonlocal response_started
                if message["type"] == "http.response.start":
                    response_started = True
                    response_headers = [(name, value) for name, value in message.get("headers", [])
                                        if name.lower() not in (b"cache-control", b"x-request-id")]
                    message = {**message, "headers": response_headers + [
                        (b"cache-control", b"no-store"), (b"x-request-id", request_id.encode("ascii"))]}
                await send(message)

            await self.app(scope, bounded_receive, private_send)
        except Exception:
            if response_started:
                raise
            # Never serialize/log exception text: it can contain private SQL values.
            await reject(500, "internal_error", "An internal error occurred")
        finally:
            self._slots.release()
