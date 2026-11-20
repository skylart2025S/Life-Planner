# PostgreSQL persistence

LP-101 adds durable storage while keeping the deterministic planning rules in `planning.py`. The original in-memory demo remains available. `PostgresPlanner` opens a new connection/transaction for each operation; plans and proposal results survive Python process restarts.

## Local setup

Run from the repository root with Python 3.12 and Docker Compose available:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
docker compose up -d --wait postgres
export DATABASE_URL='postgresql://planner:planner_local_only@localhost:55432/life_planner_test'
export PLAN_TEST_DATABASE_URL="$DATABASE_URL"
.venv/bin/python -c 'import os; from life_planner.storage import migrate; migrate(os.environ["DATABASE_URL"])'
.venv/bin/python -m unittest discover -s tests -v
```

Compose binds only to localhost and uses development-only credentials. Its named volume preserves local data across container restarts. `docker compose stop` stops the database without removing its volume. `.env.example` documents the variables; Python does not automatically load that file.

An existing disposable PostgreSQL database works too: set the two variables to its connection string and skip Compose. The DSN and schema/search path are trusted application configuration, never values accepted from a chat message or API request.

Tests create and remove their own randomly named schemas; they do not truncate shared tables. The test role needs permission to create schemas, tables, and functions. Without `PLAN_TEST_DATABASE_URL`, integration tests explicitly skip; that is not persistence verification. CI supplies the variable and a real PostgreSQL service, so those tests must run. A supplied but unusable DSN or missing driver fails the integration suite.

## Storage interface

```python
import os
from datetime import datetime
from life_planner.demo import example_plan
from life_planner.storage import PostgresPlanner

store = PostgresPlanner(os.environ["DATABASE_URL"])
store.create_plan("demo-user", "week-1", list(example_plan().items))
proposal = store.propose_move(
    "demo-user", "week-1", "gym",
    datetime.fromisoformat("2026-11-26T18:00:00-05:00"),
)
revision = store.apply(
    "demo-user", "week-1", proposal.id,
    idempotency_key="move-gym-1", confirmed=True,
)
snapshot = store.read_plan("demo-user", "week-1")
assert snapshot.revision == revision
```

Run this example against a fresh plan ID; duplicate creation is rejected. This direct-library example uses a fixture owner; the HTTP API derives it from verified token identity. Passing an owner string is not sign-in or authorization against someone who has the database credentials.

## Transaction guarantees

Every read, proposal, and apply locks the plan row before reading its revision/items. This serializes operations for one plan while other plans can progress independently. Competing proposals created from one revision cannot both apply: the first commit advances the revision, and the other fails as stale. PostgreSQL holds the row lock through transaction completion. [PostgreSQL locking documentation](https://www.postgresql.org/docs/16/explicit-locking.html).

Apply stores changed items, the incremented revision, immutable change history, the retry receipt, and one pending outbox event in the same transaction. A failure in any step rolls all of them back. Psycopg connection contexts commit on normal exit and roll back on exceptions. [Psycopg transaction documentation](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).

The idempotency key is scoped to **owner + plan + key**. Repeating the same proposal/key returns its original applied revision, including after reconnecting or later plan changes. Reusing that key for a different proposal is rejected. Reapplying an already applied proposal with a new key records a receipt for its original result without generating another revision, history record, or outbox event.

Stored proposal JSON is revalidated against the current plan through the deterministic planner before mutation. Missing or inaccessible plan/proposal IDs raise `KeyError`; invalid confirmation, conflicting/stale proposals, and reused keys raise `ValueError`. The authenticated API maps known domain failures into the public error contract; unknown or corrupt persisted state remains an internal error.

## Tables and migrations

| Table | Purpose |
| --- | --- |
| `lp_plans` | Owner/plan identity and revision |
| `lp_items` | Scheduled items with owner/plan-scoped dependency foreign keys |
| `lp_proposals` | Immutable proposed before/after changes |
| `lp_changes` | Immutable applied change history and original revision |
| `lp_receipts` | Immutable idempotency key/result associations |
| `lp_outbox` | One pending notification per applied proposal; no delivery worker yet |
| `lp_schema_migrations` | Applied migration filenames and checksums |

`migrate(dsn)` applies SQL from the source checkout's `migrations/` directory. Migration execution is transactional and serialized by an advisory lock; rerunning unchanged migrations is safe. Editing an already applied migration causes a checksum error. Add a new numbered migration for later changes. A packaged distribution must include migration resources before deployment; source-checkout usage is the supported path today.

## Current limits

- Owner scoping and composite constraints protect service operations and relationships. The API verifies signed access tokens and derives owner identity. There is no database row-level security; the configured database role is trusted.
- Reads take the same plan lock as writes. The API adds bounded connection/statement/lock timeouts. Direct library clients configure their own. No connection pool or contention benchmark exists yet.
- Outbox records do not send calendar updates; provider delivery is LP-108.
- Proposal expiration, history retention/deletion, account lifecycle, undo, and production backup/restore remain future work. History mutation triggers intentionally reject ordinary update/delete operations.
- Persistence preserves UTC instants; recurrence and stored IANA user timezone remain later work.
