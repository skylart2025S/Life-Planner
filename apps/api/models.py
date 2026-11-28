"""Strict transport schemas. Scheduling rules remain in life_planner."""

from datetime import datetime
import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, field_validator, model_validator

from life_planner.planning import utc


ID_PATTERN = r"^[A-Za-z0-9_-]{1,128}$"
Identifier = Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=ID_PATTERN)]


def parse_time(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value
    ):
        raise ValueError("An RFC3339 timestamp with offset is required")
    local = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not 2000 <= local.year <= 2100:
        raise ValueError("Timestamp outside supported range")
    result = utc(local)
    if not 2000 <= result.year <= 2100:
        raise ValueError("Timestamp outside supported range")
    return result


Timestamp = Annotated[datetime, BeforeValidator(parse_time)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ItemInput(StrictModel):
    id: Identifier
    title: Annotated[str, Field(strict=True, min_length=1, max_length=200)]
    kind: Annotated[str, Field(strict=True, min_length=1, max_length=32)]
    start: Timestamp
    end: Timestamp
    linked_to: Identifier | None = None
    fixed: StrictBool = False

    @field_validator("title", "kind")
    @classmethod
    def database_text(cls, value):
        if "\x00" in value:
            raise ValueError("Text cannot contain NUL")
        return value

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("End must follow start")
        return self


class CreatePlan(StrictModel):
    items: Annotated[list[ItemInput], Field(max_length=500)]


class MoveRequest(StrictModel):
    type: Literal["move_item"]
    item_id: Identifier
    new_start: Timestamp


class ApplyRequest(StrictModel):
    confirmed: StrictBool

    @field_validator("confirmed")
    @classmethod
    def explicitly_confirmed(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation is required")
        return value


class ItemResponse(StrictModel):
    id: str
    title: str
    kind: str
    start: datetime
    end: datetime
    linked_to: str | None
    fixed: bool


class PlanResponse(StrictModel):
    plan_id: str
    revision: int
    items: list[ItemResponse]


class PlanSummaryResponse(StrictModel):
    plan_id: Identifier
    revision: Annotated[int, Field(strict=True, ge=0)]


class PlanListResponse(StrictModel):
    plans: Annotated[list[PlanSummaryResponse], Field(max_length=100)]
    next_after: Identifier | None


class ChangeResponse(StrictModel):
    before: ItemResponse
    after: ItemResponse


class ProposalResponse(StrictModel):
    plan_id: str
    proposal_id: str
    base_revision: int
    changes: list[ChangeResponse]
    explanation: str


class ApplyResponse(StrictModel):
    plan_id: str
    proposal_id: str
    applied_revision: int


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail
