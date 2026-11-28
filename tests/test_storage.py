"""Real PostgreSQL transaction contracts; each test owns a disposable schema.

Set PLAN_TEST_DATABASE_URL to a disposable PostgreSQL database. Missing DSN skips
these tests; an explicitly configured but broken database/driver fails them.
No existing schemas or application data are truncated or dropped.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier
import unittest
from uuid import uuid4

from life_planner.demo import example_plan
from life_planner.planning import utc


TEST_DSN = os.environ.get("PLAN_TEST_DATABASE_URL")
OWNER = "demo-user"
PLAN = "weekly-plan"
DESTINATION = datetime.fromisoformat("2026-11-26T18:00:00-05:00")


@unittest.skipUnless(TEST_DSN, "PostgreSQL integration: set PLAN_TEST_DATABASE_URL")
class PostgresStorageTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        from life_planner.storage import PostgresPlanner, migrate

        self.psycopg = psycopg
        self.sql = sql
        self.Planner = PostgresPlanner
        self.migrate = migrate
        self.schema = "lp_test_" + uuid4().hex
        # Exclude public from search_path: neither migrations nor fixtures can
        # accidentally resolve a same-named application table outside our schema.
        with psycopg.connect(TEST_DSN) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)
        options = conninfo_to_dict(TEST_DSN).get("options", "")
        self.dsn = make_conninfo(TEST_DSN, options=options + f" -c search_path={self.schema} -c statement_timeout=15000 -c lock_timeout=10000")
        migrate(self.dsn)
        self.planner = PostgresPlanner(self.dsn)
        self.original = example_plan().read_items(OWNER)
        self.planner.create_plan(OWNER, PLAN, list(self.original))

    def drop_schema(self):
        with self.psycopg.connect(TEST_DSN) as conn:
            conn.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(self.sql.Identifier(self.schema)))

    def propose(self, start=DESTINATION, *, owner=OWNER, plan=PLAN):
        return self.planner.propose_move(owner, plan, "gym", start)

    def apply(self, proposal, key="request-one", *, planner=None, owner=OWNER, plan=PLAN, confirmed=True):
        return (planner or self.planner).apply(owner, plan, proposal.id, idempotency_key=key, confirmed=confirmed)

    def rows(self, table):
        with self.psycopg.connect(self.dsn) as conn:
            return sorted(conn.execute(self.sql.SQL("SELECT * FROM {}").format(self.sql.Identifier(table))).fetchall(), key=repr)

    def counts(self):
        return {table: len(self.rows(table)) for table in ("lp_changes", "lp_outbox")}

    def assert_effect_counts(self, count):
        self.assertEqual({"lp_changes": count, "lp_outbox": count}, self.counts())

    def test_plan_discovery_empty_single_exact_and_multiple_pages(self):
        from life_planner.storage import PlanPage, PlanSummary
        self.assertEqual(PlanPage((), None), self.planner.list_plans("empty-owner"))
        single = self.planner.list_plans(OWNER, limit=1)
        self.assertEqual(PlanPage((PlanSummary(PLAN, 0),), None), single)
        for plan_id in ("A", "a", "a-1", "a_1", "z", "Z"):
            self.planner.create_plan(OWNER, plan_id, [])
        with self.psycopg.connect(self.dsn) as conn:
            expected = [row[0] for row in conn.execute(
                "SELECT plan_id FROM lp_plans WHERE user_id = %s ORDER BY plan_id", (OWNER,))]
        found, cursor = [], None
        while True:
            page = self.planner.list_plans(OWNER, limit=2, after=cursor)
            found.extend(plan.plan_id for plan in page.plans)
            if page.next_after is None:
                break
            self.assertEqual(page.plans[-1].plan_id, page.next_after)
            cursor = page.next_after
        self.assertEqual(expected, found)
        self.assertIsNone(self.planner.list_plans(OWNER, limit=len(expected)).next_after)
        self.assertEqual(100, len(self._discovery_large_page().plans))

    def _discovery_large_page(self):
        for index in range(101):
            self.planner.create_plan("many", f"plan-{index:03}", [])
        default = self.planner.list_plans("many")
        self.assertEqual(20, len(default.plans))
        self.assertEqual("plan-019", default.next_after)
        page = self.planner.list_plans("many", limit=100)
        self.assertEqual("plan-099", page.next_after)
        self.assertEqual(["plan-100"], [plan.plan_id for plan in
                         self.planner.list_plans("many", limit=100, after=page.next_after).plans])
        return page

    def test_plan_discovery_is_owner_scoped_with_arbitrary_cursors(self):
        for owner, plan_ids in (("alice", ("a", "c", "e")), ("bob", ("a", "b", "e"))):
            for plan_id in plan_ids:
                self.planner.create_plan(owner, plan_id, [])
        for cursor in ("b", "bb"):
            page = self.planner.list_plans("alice", after=cursor, limit=1)
            self.assertEqual(["c"], [plan.plan_id for plan in page.plans])
            self.assertEqual("c", page.next_after)
        self.assertEqual(["a", "b", "e"],
                         [plan.plan_id for plan in self.planner.list_plans("bob").plans])
        self.assertEqual((), self.planner.list_plans("alice", after="z").plans)

    def test_plan_discovery_revision_survives_apply_and_restart(self):
        self.assertEqual(0, self.planner.list_plans(OWNER).plans[0].revision)
        self.apply(self.propose())
        restarted = self.Planner(self.dsn)
        self.assertEqual(1, restarted.list_plans(OWNER).plans[0].revision)
        self.assert_effect_counts(1)

    def test_plan_discovery_does_not_wait_for_plan_row_lock(self):
        # A held row lock must not block this metadata-only SELECT.
        with self.psycopg.connect(self.dsn) as conn:
            conn.execute("SELECT * FROM lp_plans WHERE user_id = %s AND plan_id = %s FOR UPDATE",
                         (OWNER, PLAN))
            from psycopg.conninfo import make_conninfo
            fast = self.Planner(make_conninfo(self.dsn, options=f"-c search_path={self.schema} -c lock_timeout=100"))
            self.assertEqual(PLAN, fast.list_plans(OWNER).plans[0].plan_id)

    def test_migration_can_repeat_without_losing_existing_plan(self):
        before = self.planner.read_plan(OWNER, PLAN)
        self.migrate(self.dsn)
        self.migrate(self.dsn)
        self.assertEqual(before, self.Planner(self.dsn).read_plan(OWNER, PLAN))
        self.assert_effect_counts(0)

    def test_snapshot_is_frozen_and_preview_is_durable_without_mutation(self):
        before = self.planner.read_plan(OWNER, PLAN)
        self.assertEqual(0, before.revision)
        self.assertEqual(self.original, before.items)
        self.assertIsInstance(before.items, tuple)
        with self.assertRaises(FrozenInstanceError):
            before.revision = 99
        proposal = self.propose()
        self.assertEqual(0, proposal.base_revision)
        self.assertEqual(before, self.Planner(self.dsn).read_plan(OWNER, PLAN))
        self.assert_effect_counts(0)
        self.assertEqual(1, self.apply(proposal, planner=self.Planner(self.dsn)))

    def test_fresh_process_can_apply_persisted_proposal_and_replay(self):
        proposal = self.propose()
        environment = dict(os.environ)
        environment["LP_TEST_PROCESS_DSN"] = self.dsn
        environment["LP_TEST_PROCESS_PROPOSAL"] = proposal.id
        script = """
import json, os
from life_planner.storage import PostgresPlanner
p = PostgresPlanner(os.environ['LP_TEST_PROCESS_DSN'])
revision = p.apply('demo-user', 'weekly-plan', os.environ['LP_TEST_PROCESS_PROPOSAL'], idempotency_key='process-retry', confirmed=True)
print(json.dumps({'result': revision, 'stored': p.read_plan('demo-user', 'weekly-plan').revision}))
"""
        for attempt in range(2):
            result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual({"result": 1, "stored": 1}, json.loads(result.stdout))
        self.assert_effect_counts(1)

    def test_apply_moves_dependencies_and_atomically_records_effects(self):
        proposal = self.propose()
        self.assertEqual(1, self.apply(proposal))
        snapshot = self.Planner(self.dsn).read_plan(OWNER, PLAN)
        self.assertEqual(1, snapshot.revision)
        before = {item.id: item for item in self.original}
        after = {item.id: item for item in snapshot.items}
        self.assertEqual(before["study"], after["study"])
        for item_id in ("gym", "meal", "clothes"):
            self.assertEqual(utc(before[item_id].start) + timedelta(days=1), after[item_id].start)
            self.assertEqual(utc(before[item_id].end) + timedelta(days=1), after[item_id].end)
        self.assert_effect_counts(1)
        from psycopg.rows import dict_row
        with self.psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            audit = conn.execute("SELECT * FROM lp_changes").fetchone()
            outbox = conn.execute("SELECT * FROM lp_outbox").fetchone()
            receipt = conn.execute("SELECT * FROM lp_receipts").fetchone()
        for record in (audit, outbox, receipt):
            self.assertEqual((OWNER, PLAN, proposal.id), (record["user_id"], record["plan_id"], record["proposal_id"]))
        self.assertEqual(1, audit["applied_revision"])
        self.assertEqual(1, receipt["applied_revision"])
        self.assertEqual("request-one", receipt["idempotency_key"])
        self.assertEqual({"gym", "meal", "clothes"}, {change["after"]["id"] for change in audit["changes"]})
        self.assertEqual({"proposal_id": proposal.id, "revision": 1}, outbox["payload"])
        self.assertEqual("pending", outbox["status"])
        self.assertEqual("plan.changed", outbox["event_type"])

    def test_other_owner_and_missing_plan_return_not_found(self):
        proposal = self.propose()
        before = self.planner.read_plan(OWNER, PLAN)
        for owner, plan in (("intruder", PLAN), (OWNER, "missing-plan")):
            operations = (
                lambda: self.planner.read_plan(owner, plan),
                lambda: self.propose(owner=owner, plan=plan),
                lambda: self.apply(proposal, owner=owner, plan=plan),
            )
            for operation in operations:
                with self.subTest(owner=owner, plan=plan, operation=operation), self.assertRaises(KeyError):
                    operation()
        self.assertEqual(before, self.planner.read_plan(OWNER, PLAN))
        self.assert_effect_counts(0)

    def test_identical_plan_and_item_ids_are_isolated_by_owner(self):
        other_items = [replace(item, user_id="other-owner") for item in self.original]
        self.planner.create_plan("other-owner", PLAN, other_items)
        other_before = self.planner.read_plan("other-owner", PLAN)
        proposal = self.propose()
        with self.assertRaises(KeyError):
            self.apply(proposal, owner="other-owner")
        self.assertEqual(1, self.apply(proposal))
        self.assertEqual(other_before, self.planner.read_plan("other-owner", PLAN))
        other_proposal = self.propose(owner="other-owner")
        # Idempotency keys are scoped to owner/plan, not globally reserved.
        self.assertEqual(1, self.apply(other_proposal, owner="other-owner"))
        with self.assertRaises(KeyError):
            self.apply(proposal, owner="other-owner", key="other-replay")
        self.assert_effect_counts(2)

    def test_proposal_cannot_cross_plans_of_same_owner(self):
        self.planner.create_plan(OWNER, "second-plan", list(self.original))
        proposal = self.propose()
        with self.assertRaises(KeyError):
            self.apply(proposal, plan="second-plan")
        self.assertEqual(0, self.planner.read_plan(OWNER, "second-plan").revision)
        self.assert_effect_counts(0)

    def test_two_plans_of_same_owner_can_reuse_item_ids_and_request_key(self):
        self.planner.create_plan(OWNER, "second-plan", list(self.original))
        second_before = self.planner.read_plan(OWNER, "second-plan")
        first = self.propose()
        second = self.propose(DESTINATION + timedelta(days=1), plan="second-plan")
        self.assertEqual(1, self.apply(first))
        self.assertEqual(second_before, self.planner.read_plan(OWNER, "second-plan"))
        self.assertEqual(1, self.apply(second, plan="second-plan"))
        first_items = {item.id: item for item in self.planner.read_plan(OWNER, PLAN).items}
        second_items = {item.id: item for item in self.planner.read_plan(OWNER, "second-plan").items}
        self.assertEqual(timedelta(days=1), second_items["gym"].start - first_items["gym"].start)
        self.assert_effect_counts(2)

    def test_database_rejects_item_without_matching_owner_and_plan(self):
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation):
            with self.psycopg.connect(self.dsn) as conn:
                conn.execute("UPDATE lp_items SET user_id = 'unrelated-owner' WHERE item_id = 'study'")
        self.assertEqual(self.original, self.planner.read_plan(OWNER, PLAN).items)

    def test_invalid_keys_and_missing_items_or_proposals_have_no_effects(self):
        proposal = self.propose()
        for key in ("", None):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.apply(proposal, key=key)
        with self.assertRaises(KeyError):
            self.planner.propose_move(OWNER, PLAN, "missing-item", DESTINATION)
        with self.assertRaises(KeyError):
            self.planner.apply(OWNER, PLAN, "missing-proposal", idempotency_key="missing-key", confirmed=True)
        self.assertEqual(0, self.planner.read_plan(OWNER, PLAN).revision)
        self.assert_effect_counts(0)

    def test_confirmation_requires_true_boolean_even_for_retry(self):
        proposal = self.propose()
        before = self.planner.read_plan(OWNER, PLAN)
        for confirmed in (False, None, 0, 1, "true", "false", [], {"confirmed": True}):
            with self.subTest(confirmed=confirmed), self.assertRaises(ValueError):
                self.apply(proposal, confirmed=confirmed)
        self.assertEqual(before, self.planner.read_plan(OWNER, PLAN))
        self.assert_effect_counts(0)
        self.apply(proposal)
        with self.assertRaises(ValueError):
            self.apply(proposal, confirmed=False)
        self.assert_effect_counts(1)

    def test_retry_after_reconnect_and_later_change_returns_original_revision(self):
        first = self.propose()
        self.assertEqual(1, self.apply(first))
        second = self.propose(DESTINATION + timedelta(days=1))
        self.assertEqual(2, self.apply(second, key="request-two"))
        before_retry = self.planner.read_plan(OWNER, PLAN)
        self.assertEqual(1, self.apply(first, planner=self.Planner(self.dsn)))
        self.assertEqual(before_retry, self.Planner(self.dsn).read_plan(OWNER, PLAN))
        self.assert_effect_counts(2)

    def test_reusing_key_for_another_proposal_is_rejected(self):
        first = self.propose()
        self.apply(first)
        second = self.propose(DESTINATION + timedelta(days=1))
        before = self.planner.read_plan(OWNER, PLAN)
        with self.assertRaises(ValueError):
            self.apply(second)
        self.assertEqual(before, self.planner.read_plan(OWNER, PLAN))
        self.assert_effect_counts(1)

    def test_reapplying_proposal_with_new_key_does_not_duplicate_effects(self):
        proposal = self.propose()
        self.assertEqual(1, self.apply(proposal))
        self.assertEqual(1, self.apply(proposal, key="another-key", planner=self.Planner(self.dsn)))
        self.assertEqual(1, self.planner.read_plan(OWNER, PLAN).revision)
        self.assert_effect_counts(1)

    def test_stale_proposal_is_rejected_without_changes(self):
        first = self.propose()
        stale = self.propose(DESTINATION + timedelta(days=1))
        self.apply(first)
        before = self.planner.read_plan(OWNER, PLAN)
        with self.assertRaises(ValueError):
            self.apply(stale, key="stale-key")
        self.assertEqual(before, self.planner.read_plan(OWNER, PLAN))
        self.assert_effect_counts(1)

    def concurrent_apply(self, proposals, keys):
        barrier = Barrier(len(proposals))
        def run(proposal, key):
            planner = self.Planner(self.dsn)
            barrier.wait(timeout=10)
            try:
                return ("applied", self.apply(proposal, key=key, planner=planner))
            except ValueError as error:
                return ("rejected", str(error))
        with ThreadPoolExecutor(max_workers=len(proposals)) as pool:
            futures = [pool.submit(run, proposal, key) for proposal, key in zip(proposals, keys)]
            return [future.result(timeout=25) for future in futures]

    def test_competing_concurrent_proposals_apply_exactly_one(self):
        first = self.propose()
        second = self.propose(DESTINATION + timedelta(days=1))
        results = self.concurrent_apply([first, second], ["race-one", "race-two"])
        self.assertEqual(1, sum(kind == "applied" for kind, _ in results), results)
        self.assertEqual(1, sum(kind == "rejected" for kind, _ in results), results)
        self.assertEqual(1, self.planner.read_plan(OWNER, PLAN).revision)
        self.assert_effect_counts(1)

    def test_simultaneous_same_key_retries_record_effects_once(self):
        proposal = self.propose()
        results = self.concurrent_apply([proposal] * 4, ["same-race-key"] * 4)
        self.assertEqual([("applied", 1)] * 4, results)
        self.assertEqual(1, self.planner.read_plan(OWNER, PLAN).revision)
        self.assert_effect_counts(1)


    def test_audit_receipts_and_proposals_are_immutable(self):
        proposal = self.propose()
        self.apply(proposal)
        for table in ("lp_changes", "lp_receipts", "lp_proposals"):
            before = self.rows(table)
            for action in ("UPDATE {} SET user_id = user_id", "DELETE FROM {}"):
                with self.subTest(table=table, action=action), self.assertRaisesRegex(self.psycopg.Error, "immutable"):
                    with self.psycopg.connect(self.dsn) as conn:
                        conn.execute(self.sql.SQL(action).format(self.sql.Identifier(table)))
                self.assertEqual(before, self.rows(table))

    def test_outbox_failure_after_updates_rolls_back_entire_apply(self):
        proposal = self.propose()
        before = self.planner.read_plan(OWNER, PLAN)
        tables = ("lp_plans", "lp_items", "lp_proposals", "lp_changes", "lp_receipts", "lp_outbox")
        before_rows = {table: self.rows(table) for table in tables}
        # This is a real database exception late in apply, not a mocked adapter.
        # The trigger proves item/revision/audit/receipt writes already happened
        # inside this transaction before forcing the outbox insert to fail.
        with self.psycopg.connect(self.dsn) as conn:
            conn.execute("""
                CREATE FUNCTION fail_test_outbox() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF (SELECT revision FROM lp_plans
                        WHERE user_id = NEW.user_id AND plan_id = NEW.plan_id) <> 1 THEN
                        RAISE EXCEPTION 'Test precondition: revision was not updated';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM lp_items
                        WHERE user_id = NEW.user_id AND plan_id = NEW.plan_id
                        AND item_id = 'gym' AND start_at = '2026-11-26 23:00:00+00'::timestamptz) THEN
                        RAISE EXCEPTION 'Test precondition: item was not updated';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM lp_changes
                        WHERE user_id = NEW.user_id AND plan_id = NEW.plan_id) THEN
                        RAISE EXCEPTION 'Test precondition: audit was not written';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM lp_receipts
                        WHERE user_id = NEW.user_id AND plan_id = NEW.plan_id) THEN
                        RAISE EXCEPTION 'Test precondition: receipt was not written';
                    END IF;
                    RAISE EXCEPTION 'injected outbox failure after prior writes';
                END;
                $$
            """)
            conn.execute("CREATE TRIGGER fail_test_outbox BEFORE INSERT ON lp_outbox FOR EACH ROW EXECUTE FUNCTION fail_test_outbox()")
        with self.assertRaisesRegex(self.psycopg.Error, "injected outbox failure after prior writes"):
            self.apply(proposal, key="rollback-key")
        self.assertEqual(before, self.Planner(self.dsn).read_plan(OWNER, PLAN))
        self.assertEqual(before_rows, {table: self.rows(table) for table in tables})
        with self.psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TRIGGER fail_test_outbox ON lp_outbox")
            conn.execute("DROP FUNCTION fail_test_outbox()")
        self.assertEqual(1, self.apply(proposal, key="rollback-key", planner=self.Planner(self.dsn)))
        self.assert_effect_counts(1)


if __name__ == "__main__":
    unittest.main()
