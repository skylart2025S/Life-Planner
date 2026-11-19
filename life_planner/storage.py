"""Transactional PostgreSQL planner. Caller identity must come from authentication.

Each operation opens a fresh connection and transaction. All service access to a
plan takes its row lock, ensuring consistent snapshots and serial application.
The database role and DSN are trusted deployment configuration, not user input.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from life_planner.planning import Change, PlanItem, Planner, Proposal, utc


@dataclass(frozen=True)
class PlanSnapshot:
    revision: int
    items: tuple[PlanItem, ...]


def _required(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")


def migrate(dsn: str) -> None:
    """Apply checked-in SQL once, atomically, in the DSN's current schema.

    Existing migration checksums must match. An advisory transaction lock also
    serializes concurrent first-time bootstraps, before a migration table exists.
    """
    directory = Path(__file__).resolve().parent.parent / "migrations"
    migration_paths = sorted(directory.glob("*.sql"))
    if not migration_paths:
        raise ValueError("Migration SQL files are missing")
    with psycopg.connect(dsn) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(672901800101)")
        connection.execute("""CREATE TABLE IF NOT EXISTS lp_schema_migrations (
            version text PRIMARY KEY, checksum text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        for path in migration_paths:
            script = path.read_text(encoding="utf-8")
            checksum = sha256(script.encode("utf-8")).hexdigest()
            existing = connection.execute(
                "SELECT checksum FROM lp_schema_migrations WHERE version = %s", (path.name,)
            ).fetchone()
            if existing:
                if existing[0] != checksum:
                    raise ValueError(f"Migration checksum mismatch: {path.name}")
                continue
            connection.execute(script)
            connection.execute("INSERT INTO lp_schema_migrations (version, checksum) VALUES (%s, %s)",
                               (path.name, checksum))


def _encode_item(item: PlanItem) -> dict:
    return {"id": item.id, "user_id": item.user_id, "title": item.title, "kind": item.kind,
            "start": utc(item.start).isoformat(), "end": utc(item.end).isoformat(),
            "linked_to": item.linked_to, "fixed": item.fixed}


def _encode_changes(changes: tuple[Change, ...]) -> list[dict]:
    return [{"before": _encode_item(change.before), "after": _encode_item(change.after)}
            for change in changes]


def _decode_item(value: dict) -> PlanItem:
    return PlanItem(**{**value, "start": datetime.fromisoformat(value["start"]),
                       "end": datetime.fromisoformat(value["end"])})


def _decode_proposal(row: dict) -> Proposal:
    try:
        changes = tuple(Change(_decode_item(value["before"]), _decode_item(value["after"]))
                        for value in row["changes"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Invalid persisted proposal") from error
    return Proposal(row["proposal_id"], row["user_id"], row["base_revision"], changes,
                    row["explanation"])


class PostgresPlanner:
    """Owner-scoped storage, not an authentication or external-sync service."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    def _connect(self):
        return psycopg.connect(self._dsn, row_factory=dict_row)

    @staticmethod
    def _scope(user_id: str, plan_id: str) -> tuple[str, str]:
        _required(user_id, "User ID")
        _required(plan_id, "Plan ID")
        return user_id, plan_id

    @staticmethod
    def _lock(connection, scope: tuple[str, str]) -> int:
        row = connection.execute(
            "SELECT revision FROM lp_plans WHERE user_id = %s AND plan_id = %s FOR UPDATE", scope
        ).fetchone()
        if row is None:
            raise KeyError("Plan not found")
        return row["revision"]

    @staticmethod
    def _items(connection, scope: tuple[str, str]) -> tuple[PlanItem, ...]:
        rows = connection.execute("""SELECT item_id AS id, user_id, title, kind,
            start_at AS start, end_at AS end, linked_to, fixed FROM lp_items
            WHERE user_id = %s AND plan_id = %s ORDER BY start_at, item_id""", scope).fetchall()
        return tuple(PlanItem(**row) for row in rows)

    def create_plan(self, user_id: str, plan_id: str, items: list[PlanItem]) -> None:
        scope = self._scope(user_id, plan_id)
        if any(item.user_id != user_id for item in items):
            raise ValueError("Plan ownership mismatch")
        planner = Planner(user_id, list(items))
        try:
            with self._connect() as connection:
                connection.execute("INSERT INTO lp_plans (user_id, plan_id) VALUES (%s, %s)", scope)
                for item in planner.read_items(user_id):
                    connection.execute("""INSERT INTO lp_items
                        (user_id, plan_id, item_id, title, kind, start_at, end_at, linked_to, fixed)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (*scope, item.id, item.title, item.kind, utc(item.start), utc(item.end),
                         item.linked_to, item.fixed))
        except psycopg.errors.UniqueViolation as error:
            raise ValueError("Plan already exists") from error

    def read_plan(self, user_id: str, plan_id: str) -> PlanSnapshot:
        scope = self._scope(user_id, plan_id)
        with self._connect() as connection:
            revision = self._lock(connection, scope)
            return PlanSnapshot(revision, self._items(connection, scope))

    def propose_move(self, user_id: str, plan_id: str, item_id: str,
                     new_start: datetime) -> Proposal:
        scope = self._scope(user_id, plan_id)
        with self._connect() as connection:
            revision = self._lock(connection, scope)
            planner = Planner(user_id, list(self._items(connection, scope)))
            proposal = replace(planner.propose_move(user_id, item_id, new_start),
                               base_revision=revision)
            connection.execute("""INSERT INTO lp_proposals
                (user_id, plan_id, proposal_id, base_revision, changes, explanation)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (*scope, proposal.id, proposal.base_revision, Jsonb(_encode_changes(proposal.changes)),
                 proposal.explanation))
            return proposal

    def apply(self, user_id: str, plan_id: str, proposal_id: str, *,
              idempotency_key: str, confirmed: bool = False) -> int:
        scope = self._scope(user_id, plan_id)
        if confirmed is not True:
            raise ValueError("Confirmation is required")
        _required(idempotency_key, "Idempotency key")
        with self._connect() as connection:
            revision = self._lock(connection, scope)
            row = connection.execute("""SELECT * FROM lp_proposals
                WHERE user_id = %s AND plan_id = %s AND proposal_id = %s""",
                (*scope, proposal_id)).fetchone()
            if row is None:
                raise KeyError("Proposal not found")
            receipt = connection.execute("""SELECT proposal_id, applied_revision FROM lp_receipts
                WHERE user_id = %s AND plan_id = %s AND idempotency_key = %s""",
                (*scope, idempotency_key)).fetchone()
            if receipt is not None:
                if receipt["proposal_id"] != proposal_id:
                    raise ValueError("Idempotency key is already bound to another proposal")
                return receipt["applied_revision"]
            applied = connection.execute("""SELECT applied_revision FROM lp_changes
                WHERE user_id = %s AND plan_id = %s AND proposal_id = %s""",
                (*scope, proposal_id)).fetchone()
            if applied is not None:
                self._record_receipt(connection, scope, idempotency_key, proposal_id,
                                     applied["applied_revision"])
                return applied["applied_revision"]
            proposal = _decode_proposal(row)
            if proposal.base_revision != revision:
                raise ValueError("Stale proposal; generate a fresh proposal")
            # Rebuild from current state: persisted JSON is never mutation authority.
            roots = [change for change in proposal.changes if change.before.linked_to is None]
            if len(roots) != 1:
                raise ValueError("Invalid persisted proposal")
            planner = Planner(user_id, list(self._items(connection, scope)))
            try:
                validated = planner.propose_move(user_id, roots[0].before.id, roots[0].after.start)
            except KeyError as error:
                raise ValueError("Proposal no longer matches the plan") from error
            if validated.changes != proposal.changes:
                raise ValueError("Proposal no longer matches the plan")
            for change in validated.changes:
                connection.execute("""UPDATE lp_items SET start_at = %s, end_at = %s
                    WHERE user_id = %s AND plan_id = %s AND item_id = %s""",
                    (utc(change.after.start), utc(change.after.end), *scope, change.after.id))
            applied_revision = revision + 1
            connection.execute("UPDATE lp_plans SET revision = %s WHERE user_id = %s AND plan_id = %s",
                               (applied_revision, *scope))
            connection.execute("""INSERT INTO lp_changes
                (user_id, plan_id, proposal_id, applied_revision, changes, idempotency_key)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (*scope, proposal_id, applied_revision, Jsonb(_encode_changes(validated.changes)),
                 idempotency_key))
            self._record_receipt(connection, scope, idempotency_key, proposal_id, applied_revision)
            connection.execute("""INSERT INTO lp_outbox
                (user_id, plan_id, proposal_id, event_id, event_type, payload)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (*scope, proposal_id, str(uuid4()), "plan.changed",
                 Jsonb({"proposal_id": proposal_id, "revision": applied_revision})))
            return applied_revision

    @staticmethod
    def _record_receipt(connection, scope, key, proposal_id, revision):
        connection.execute("""INSERT INTO lp_receipts
            (user_id, plan_id, idempotency_key, proposal_id, applied_revision)
            VALUES (%s, %s, %s, %s, %s)""", (*scope, key, proposal_id, revision))
