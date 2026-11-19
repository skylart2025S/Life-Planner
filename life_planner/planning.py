"""In-memory, single-process reference implementation; no external writes."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("A datetime is required")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An explicit timezone is required")
    instant = value.astimezone(timezone.utc)
    if instant.astimezone(value.tzinfo).replace(tzinfo=None) != value.replace(tzinfo=None):
        raise ValueError("Local time does not exist in its timezone")
    return instant


@dataclass(frozen=True)
class PlanItem:
    id: str
    user_id: str
    title: str
    kind: str
    start: datetime
    end: datetime
    linked_to: str | None = None
    fixed: bool = False

    def __post_init__(self):
        if not self.id or not self.user_id:
            raise ValueError("Item and user IDs are required")
        if utc(self.end) <= utc(self.start):
            raise ValueError("End must be later than start")


@dataclass(frozen=True)
class Change:
    before: PlanItem
    after: PlanItem


@dataclass(frozen=True)
class Proposal:
    id: str
    user_id: str
    base_revision: int
    changes: tuple[Change, ...]
    explanation: str


class Planner:
    """One user's isolated plan. Replace with transactional storage before hosting."""

    def __init__(self, user_id: str, items: list[PlanItem]):
        if not user_id or any(item.user_id != user_id for item in items):
            raise PermissionError("Plan ownership mismatch")
        self._items = {item.id: item for item in items}
        if len(self._items) != len(items):
            raise ValueError("Duplicate item ID")
        for item in items:
            if item.linked_to is not None:
                parent = self._items.get(item.linked_to)
                if parent is None or parent.linked_to is not None:
                    raise ValueError("Dependencies must link directly to a root item")
        self._user_id = user_id
        self._revision = 0
        self._proposals: dict[str, Proposal] = {}
        self._applied: dict[str, int] = {}

    @property
    def revision(self) -> int:
        """Trusted in-process metadata; this property is not an authorized API."""
        return self._revision

    @property
    def items(self) -> tuple[PlanItem, ...]:
        """Trusted in-process snapshot; request boundaries must use read_items."""
        return tuple(sorted(self._items.values(), key=lambda item: utc(item.start)))

    def _authorize(self, user_id: str):
        if user_id != self._user_id:
            raise PermissionError("Plan ownership mismatch")

    def read_items(self, user_id: str) -> tuple[PlanItem, ...]:
        """Return an immutable snapshot after checking the caller's ownership."""
        self._authorize(user_id)
        return self.items

    def _validate_changes(self, changes: tuple[Change, ...]):
        moving = {change.before.id for change in changes}
        unchanged = [item for item in self.items if item.id not in moving]
        moved = [change.after for change in changes]
        for index, item in enumerate(moved):
            for other in unchanged + moved[index + 1:]:
                if utc(item.start) < utc(other.end) and utc(other.start) < utc(item.end):
                    raise ValueError(f"Schedule conflict between {item.id} and {other.id}")

    def propose_move(self, user_id: str, item_id: str, new_start: datetime) -> Proposal:
        self._authorize(user_id)
        item = self._items[item_id]
        if item.linked_to:
            raise ValueError("Move the root item to keep its preparations aligned")
        delta = utc(new_start) - utc(item.start)
        related = [entry for entry in self.items if entry.id == item_id or entry.linked_to == item_id]
        if any(entry.fixed for entry in related):
            raise ValueError("A fixed item cannot be moved")
        changes = tuple(Change(entry, replace(entry, start=utc(entry.start) + delta,
                                              end=utc(entry.end) + delta)) for entry in related)
        self._validate_changes(changes)
        proposal = Proposal(str(uuid4()), user_id, self.revision, changes,
                            "Move the selected event and its linked preparations by the same elapsed time.")
        self._proposals[proposal.id] = proposal
        return proposal

    def apply(self, user_id: str, proposal_id: str, *, confirmed: bool = False) -> int:
        self._authorize(user_id)
        if confirmed is not True:
            raise ValueError("Confirmation is required")
        proposal = self._proposals[proposal_id]
        if proposal_id in self._applied:
            return self._applied[proposal_id]
        if proposal.base_revision != self.revision:
            raise ValueError("Stale proposal; generate a fresh proposal")
        self._validate_changes(proposal.changes)
        updated = dict(self._items)
        for change in proposal.changes:
            updated[change.after.id] = change.after
        self._items = updated
        self._revision += 1
        self._applied[proposal_id] = self.revision
        return self.revision
