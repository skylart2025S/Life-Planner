"""Integration contracts only; no model or calendar implementation is connected."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from life_planner.planning import PlanItem


@dataclass(frozen=True)
class MoveIntent:
    item_id: str
    new_start: datetime


@dataclass(frozen=True)
class Clarification:
    question: str


class IntentInterpreter(Protocol):
    def interpret(self, message: str, *, timezone: str, now: datetime,
                  items: tuple[PlanItem, ...]) -> MoveIntent | Clarification:
        """Extract a command or ask a question; no persistence or side effects."""
        ...


class CalendarReader(Protocol):
    def read(self, *, user_id: str, start: datetime, end: datetime) -> tuple[PlanItem, ...]:
        """Read one authorized user's external events through a provider adapter."""
        ...
