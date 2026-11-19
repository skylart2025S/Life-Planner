# LP-101 persistence delivery — 2026-11-19

Status: **implementation complete; final commit review and remote publication pending**.

## Task and ownership

The user requested continued development after the successful foundation push. The coordinator selected LP-101 from the backlog on branch `agent/LP-101-persistent-plans`, based on published main commit `ddc768e`.

- Backend engineer: `life_planner/storage.py` and `migrations/001_persistent_plans.sql`.
- QA engineer: `tests/test_storage.py` (19 real PostgreSQL tests).
- Independent reviewer: separate review of code, tests, edge cases, and final committed scope.
- Coordinator: dependency pins, local Compose configuration, CI service, specifications, setup instructions, and delivery integration.

## Delivered behavior

Plans and proposals survive process restarts. Apply locks the plan revision and atomically records all item changes, the new revision, immutable history, a durable retry receipt, and pending outbox work. Competing proposals cannot both apply from the same revision. Repeated requests return the first result without duplicating changes. Owner/plan relationships are constrained in PostgreSQL; service operations scope every lookup to the supplied owner and plan.

The adapter reuses deterministic planning rules, validates stored proposals against the current plan, and retains the original standard-library in-memory demo. Versioned migrations have checksum tracking and transactional execution. See [persistence setup](../PERSISTENCE.md).

## Verification evidence

- Python 3.12.3, psycopg 3.3.9, PostgreSQL 16.15.
- QA and independent reviewer each ran `.venv/bin/python -m unittest discover -s tests -v` with `PLAN_TEST_DATABASE_URL` pointing to a disposable local database: **46 tests passed, zero skips** (27 existing domain tests + 19 database tests).
- Coverage includes a fresh child process, owner/plan isolation, conflicting simultaneous writers, simultaneous retry requests, immutable history, repeated migrations, and a deliberately failed outbox insert that rolls back the whole apply.
- Additional independent disposable-schema probes passed for partial creation rollback, before-image mismatch after preview, fixed-item revalidation, and migration checksum mismatch rejection.
- GitHub workflow now installs the pinned dependencies and supplies PostgreSQL so integration tests run in CI. Remote execution has not yet been observed for this change.
- Docker daemon access was unavailable locally. The coordinator extracted PostgreSQL binaries into `/tmp/life-planner-postgres` and ran an isolated localhost test database instead; no system database service was installed or changed.

## Remaining boundaries

This is persistence, not an authenticated product or deployed service. Caller identity and database configuration are trusted. No RLS, pool, configured timeouts, proposal expiration, retention/account deletion, recurrence, undo, or outbox dispatcher is implemented. Migration files currently require the source checkout. History mutation triggers require a deliberate future deletion/retention design.

## Handoff

Obtain independent acceptance of the final commit, push the task branch, open its pull request, and observe remote checks. Do not merge or deploy automatically. After integration, LP-102 should derive owner identity from authentication and expose the validated API contract. M1 is not complete until LP-102 is also verified.
