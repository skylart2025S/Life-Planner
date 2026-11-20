"""Safe public errors; never expose untrusted input or database exception text."""

import psycopg
from starlette.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def error_response(status, code, message, request_id):
    headers = {"Cache-Control": "no-store", "X-Request-ID": request_id}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if status == 503:
        headers["Retry-After"] = "1"
    return JSONResponse({"error": {"code": code, "message": message, "request_id": request_id}},
                        status_code=status, headers=headers)


def storage_call(operation, function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except KeyError:
        raise APIError(404, "not_found", "Resource not found") from None
    except psycopg.OperationalError:
        raise APIError(503, "temporarily_unavailable",
                       "Service temporarily unavailable; retry an apply with the same idempotency key") from None
    except ValueError as error:
        # Only known domain failures are client errors. Corrupt stored proposals,
        # mismatched before-images, and unknown failures remain internal errors.
        message = str(error)
        if operation == "create" and message == "Plan already exists":
            raise APIError(409, "plan_exists", "Plan already exists") from None
        if operation == "create" and message in (
            "Duplicate item ID", "Dependencies must link directly to a root item"
        ):
            raise APIError(400, "invalid_request", "Invalid plan items or dependencies") from None
        conflict = message in (
            "Move the root item to keep its preparations aligned", "A fixed item cannot be moved",
            "Stale proposal; generate a fresh proposal",
            "Idempotency key is already bound to another proposal",
        ) or message.startswith("Schedule conflict between ")
        if operation in ("propose", "apply") and conflict:
            raise APIError(409, "plan_conflict", "Requested change conflicts with the current plan") from None
        raise
