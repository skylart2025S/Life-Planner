"""Application factory. No database migrations or external identity discovery."""

from datetime import timedelta
import re
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer
from starlette.exceptions import HTTPException

from apps.api.auth import InvalidToken, TokenVerifier
from apps.api.config import Settings
from apps.api.errors import APIError, error_response, storage_call
from apps.api.middleware import RequestBoundsMiddleware
from apps.api.models import (ApplyRequest, ApplyResponse, CreatePlan, ErrorResponse, ID_PATTERN,
                             MoveRequest, PlanResponse, ProposalResponse, parse_time)
from life_planner.planning import PlanItem, utc
from life_planner.storage import PostgresPlanner


ResourceID = Annotated[str, Path(min_length=1, max_length=128, pattern=ID_PATTERN)]


def _item_response(item):
    return {"id": item.id, "title": item.title, "kind": item.kind,
            "start": utc(item.start), "end": utc(item.end), "linked_to": item.linked_to,
            "fixed": item.fixed}


def create_app(settings: Settings) -> FastAPI:
    verifier = TokenVerifier(settings)
    storage = PostgresPlanner(settings.service_dsn())
    app = FastAPI(title="AI Life Planner API", version="0.2.0",
                  responses={status: {"model": ErrorResponse} for status in
                             (400, 401, 404, 408, 409, 413, 415, 500, 503)})
    app.state.planner = storage
    app.add_middleware(RequestBoundsMiddleware)
    bearer = HTTPBearer(auto_error=False)

    @app.exception_handler(APIError)
    async def api_error(request, error):
        return error_response(error.status, error.code, error.message, request.state.request_id)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return error_response(400, "invalid_request", "Invalid request", request.state.request_id)

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return error_response(error.status_code, "not_found" if error.status_code == 404 else "invalid_request",
                              "Resource not found" if error.status_code == 404 else "Invalid request",
                              request.state.request_id)

    def owner(request: Request, _=Depends(bearer)):
        values = request.headers.getlist("authorization")
        if len(values) != 1 or len(values[0]) > 8192:
            raise APIError(401, "invalid_token", "A valid bearer access token is required")
        parts = values[0].split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
            raise APIError(401, "invalid_token", "A valid bearer access token is required")
        try:
            return verifier.verify(parts[1])
        except InvalidToken:
            raise APIError(401, "invalid_token", "A valid bearer access token is required") from None

    def key(request: Request, documented_key: Annotated[str, Header(
            alias="Idempotency-Key", description="Stable request key: 1–128 visible ASCII characters",
            min_length=1, max_length=128)]):
        values = request.headers.getlist("idempotency-key")
        if len(values) != 1 or re.fullmatch(r"[\x21-\x7e]{1,128}", values[0]) is None:
            raise APIError(400, "invalid_request", "One valid Idempotency-Key header is required")
        return values[0]

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/plans/{plan_id}", status_code=201, response_model=PlanResponse)
    def create_plan(plan_id: ResourceID, body: CreatePlan, response: Response,
                    user_id: str = Depends(owner)):
        items = [PlanItem(user_id=user_id, **item.model_dump()) for item in body.items]
        storage_call("create", storage.create_plan, user_id, plan_id, items)
        response.headers["Location"] = f"/v1/plans/{plan_id}"
        return {"plan_id": plan_id, "revision": 0,
                "items": [_item_response(item) for item in sorted(items, key=lambda item: item.start)]}

    @app.get("/v1/plans/{plan_id}", response_model=PlanResponse)
    def read_plan(plan_id: ResourceID, request: Request,
                  start: Annotated[str, Query(alias="from")], end: Annotated[str, Query(alias="to")],
                  user_id: str = Depends(owner)):
        if (set(request.query_params.keys()) != {"from", "to"}
                or len(request.query_params.getlist("from")) != 1
                or len(request.query_params.getlist("to")) != 1):
            raise APIError(400, "invalid_request", "Provide one from and one to timestamp")
        try:
            beginning, ending = parse_time(start), parse_time(end)
            if not timedelta(0) < ending - beginning <= timedelta(days=31):
                raise ValueError("Invalid window")
        except ValueError:
            raise APIError(400, "invalid_request", "Provide an aware interval of at most 31 days") from None
        snapshot = storage_call("read", storage.read_plan, user_id, plan_id)
        return {"plan_id": plan_id, "revision": snapshot.revision,
                "items": [_item_response(item) for item in snapshot.items
                          if utc(item.start) < ending and utc(item.end) > beginning]}

    @app.post("/v1/plans/{plan_id}/proposals", status_code=201, response_model=ProposalResponse)
    def propose_move(plan_id: ResourceID, body: MoveRequest, user_id: str = Depends(owner)):
        proposal = storage_call("propose", storage.propose_move, user_id, plan_id,
                                body.item_id, body.new_start)
        return {"plan_id": plan_id, "proposal_id": proposal.id, "base_revision": proposal.base_revision,
                "changes": [{"before": _item_response(change.before), "after": _item_response(change.after)}
                            for change in proposal.changes], "explanation": proposal.explanation}

    @app.post("/v1/plans/{plan_id}/proposals/{proposal_id}/apply", response_model=ApplyResponse)
    def apply(plan_id: ResourceID, proposal_id: ResourceID, body: ApplyRequest,
              user_id: str = Depends(owner), idempotency_key: str = Depends(key)):
        revision = storage_call("apply", storage.apply, user_id, plan_id, proposal_id,
                                idempotency_key=idempotency_key, confirmed=body.confirmed)
        return {"plan_id": plan_id, "proposal_id": proposal_id, "applied_revision": revision}

    # Validation is uniformly 400; remove FastAPI's auto-generated 422 promise.
    original_openapi = app.openapi

    def openapi():
        schema = original_openapi()
        for path in schema["paths"].values():
            for operation in path.values():
                if isinstance(operation, dict):
                    operation.get("responses", {}).pop("422", None)
        return schema

    app.openapi = openapi
    return app
