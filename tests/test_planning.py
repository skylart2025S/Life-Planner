"""Behavior contracts for the isolated, in-memory scheduling foundation."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest
from zoneinfo import ZoneInfo

from life_planner.demo import example_plan
from life_planner.planning import PlanItem, Planner, utc


OWNER = "demo-user"
DESTINATION = datetime.fromisoformat("2026-11-26T18:00:00-05:00")


def block(id, start, end, **kwargs):
    return PlanItem(id, OWNER, id, "event", datetime.fromisoformat(start),
                    datetime.fromisoformat(end), **kwargs)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.planner = example_plan()

    def propose(self, **kwargs):
        return self.planner.propose_move(kwargs.get("user_id", OWNER),
                                         kwargs.get("item_id", "gym"),
                                         kwargs.get("new_start", DESTINATION))

    def test_preview_does_not_mutate_schedule_or_revision(self):
        before = self.planner.read_items(OWNER)
        proposal = self.propose()
        self.assertEqual(before, self.planner.read_items(OWNER))
        self.assertEqual(0, self.planner.revision)
        self.assertEqual(0, proposal.base_revision)
        self.assertEqual(OWNER, proposal.user_id)
        self.assertTrue(proposal.explanation)

    def test_apply_shifts_linked_preparations_and_preserves_unrelated_item(self):
        before = {item.id: item for item in self.planner.read_items(OWNER)}
        proposal = self.propose()
        self.assertEqual({"gym", "meal", "clothes"}, {c.after.id for c in proposal.changes})
        self.assertEqual(1, self.planner.apply(OWNER, proposal.id, confirmed=True))
        after = {item.id: item for item in self.planner.read_items(OWNER)}
        self.assertEqual(before["study"], after["study"])
        for id in ("gym", "meal", "clothes"):
            self.assertEqual(utc(before[id].start) + timedelta(days=1), after[id].start)
            self.assertEqual(utc(before[id].end) + timedelta(days=1), after[id].end)
            self.assertEqual(replace(before[id], start=after[id].start, end=after[id].end), after[id])

    def test_read_snapshot_and_proposal_are_immutable(self):
        snapshot = self.planner.read_items(OWNER)
        proposal = self.propose()
        self.assertIsInstance(snapshot, tuple)
        with self.assertRaises(FrozenInstanceError):
            snapshot[0].title = "changed"
        with self.assertRaises(FrozenInstanceError):
            proposal.changes[0].after.start = DESTINATION
        self.planner.apply(OWNER, proposal.id, confirmed=True)
        self.assertNotEqual(snapshot, self.planner.read_items(OWNER))

    def test_owner_is_checked_before_item_or_proposal_lookup(self):
        for operation in (
            lambda: self.planner.read_items("other-user"),
            lambda: self.propose(user_id="other-user", item_id="missing"),
            lambda: self.planner.apply("other-user", "missing", confirmed=True),
        ):
            with self.subTest(operation=operation), self.assertRaises(PermissionError):
                operation()
        self.assertEqual(0, self.planner.revision)

    def test_other_owner_cannot_apply_known_proposal_or_retry(self):
        proposal = self.propose()
        for already_applied in (False, True):
            if already_applied:
                self.planner.apply(OWNER, proposal.id, confirmed=True)
            with self.subTest(already_applied=already_applied), self.assertRaises(PermissionError):
                self.planner.apply("other-user", proposal.id, confirmed=True)

    def test_constructor_rejects_mixed_ownership(self):
        items = list(self.planner.read_items(OWNER))
        items[0] = replace(items[0], user_id="other-user")
        with self.assertRaises(PermissionError):
            Planner(OWNER, items)
        with self.assertRaises(PermissionError):
            Planner("", [])

    def test_confirmation_requires_actual_true_boolean(self):
        proposal = self.propose()
        before = self.planner.read_items(OWNER)
        for value in (False, None, 0, 1, "false", "true", [], {"confirmed": True}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Confirmation"):
                self.planner.apply(OWNER, proposal.id, confirmed=value)
        self.assertEqual(before, self.planner.read_items(OWNER))
        self.assertEqual(0, self.planner.revision)

    def test_root_collision_rejected_without_mutation(self):
        before = self.planner.read_items(OWNER)
        with self.assertRaisesRegex(ValueError, "Schedule conflict"):
            self.propose(new_start=datetime.fromisoformat("2026-11-26T15:00:00-05:00"))
        self.assertEqual(before, self.planner.read_items(OWNER))
        self.assertEqual(0, self.planner.revision)

    def test_dependent_collision_rejected_even_when_root_is_free(self):
        before = self.planner.read_items(OWNER)
        # Gym is free at 16:30, but its 15:30 meal overlaps study until 16:00.
        with self.assertRaisesRegex(ValueError, "Schedule conflict.*meal.*study"):
            self.propose(new_start=datetime.fromisoformat("2026-11-26T16:30:00-05:00"))
        self.assertEqual(before, self.planner.read_items(OWNER))

    def test_moved_items_cannot_overlap_each_other(self):
        self.planner = Planner(OWNER, [
            block("gym", "2026-11-25T18:00:00Z", "2026-11-25T19:00:00Z"),
            block("meal", "2026-11-25T18:30:00Z", "2026-11-25T19:00:00Z", linked_to="gym"),
        ])
        with self.assertRaisesRegex(ValueError, "Schedule conflict"):
            self.propose()

    def test_adjacent_blocks_are_allowed(self):
        proposal = self.propose(new_start=datetime.fromisoformat("2026-11-26T17:00:00-05:00"))
        self.assertEqual(1, self.planner.apply(OWNER, proposal.id, confirmed=True))

    def test_cannot_move_preparation_independently(self):
        with self.assertRaisesRegex(ValueError, "root item"):
            self.propose(item_id="meal")

    def test_fixed_root_or_dependency_blocks_entire_move(self):
        original = self.planner.read_items(OWNER)
        for fixed_id in ("gym", "meal", "clothes"):
            self.planner = Planner(OWNER, [replace(item, fixed=item.id == fixed_id) for item in original])
            before = self.planner.read_items(OWNER)
            with self.subTest(fixed_id=fixed_id), self.assertRaisesRegex(ValueError, "fixed"):
                self.propose()
            self.assertEqual(before, self.planner.read_items(OWNER))
            self.assertEqual(0, self.planner.revision)

    def test_stale_proposal_is_rejected_without_partial_changes(self):
        first = self.propose()
        stale = self.propose(new_start=DESTINATION + timedelta(days=1))
        self.planner.apply(OWNER, first.id, confirmed=True)
        before = self.planner.read_items(OWNER)
        with self.assertRaisesRegex(ValueError, "Stale proposal"):
            self.planner.apply(OWNER, stale.id, confirmed=True)
        self.assertEqual(before, self.planner.read_items(OWNER))
        self.assertEqual(1, self.planner.revision)

    def test_retry_returns_original_revision_even_after_later_changes(self):
        first = self.propose()
        self.assertEqual(1, self.planner.apply(OWNER, first.id, confirmed=True))
        self.assertEqual(1, self.planner.apply(OWNER, first.id, confirmed=True))
        second = self.propose(new_start=DESTINATION + timedelta(days=1))
        self.assertEqual(2, self.planner.apply(OWNER, second.id, confirmed=True))
        before = self.planner.read_items(OWNER)
        self.assertEqual(1, self.planner.apply(OWNER, first.id, confirmed=True))
        self.assertEqual(2, self.planner.revision)
        self.assertEqual(before, self.planner.read_items(OWNER))

    def test_proposals_are_local_to_their_plan_instance(self):
        proposal = self.propose()
        with self.assertRaises(KeyError):
            example_plan().apply(OWNER, proposal.id, confirmed=True)

    def test_unknown_item_or_proposal_fails_without_changes(self):
        before = self.planner.read_items(OWNER)
        with self.assertRaises(KeyError):
            self.propose(item_id="missing")
        with self.assertRaises(KeyError):
            self.planner.apply(OWNER, "missing", confirmed=True)
        self.assertEqual(before, self.planner.read_items(OWNER))
        self.assertEqual(0, self.planner.revision)

    def test_duplicate_ids_and_invalid_dependency_graphs_are_rejected(self):
        root = block("root", "2026-11-25T10:00:00Z", "2026-11-25T11:00:00Z")
        child = replace(root, id="child", linked_to="root")
        for items in (
            [root, root],
            [replace(root, linked_to="missing")],
            [replace(root, linked_to="root")],
            [root, child, replace(root, id="grandchild", linked_to="child")],
            [replace(root, linked_to="child"), child],
        ):
            with self.subTest(items=items), self.assertRaises(ValueError):
                Planner(OWNER, items)


class TimeValidationTests(unittest.TestCase):
    def test_naive_timestamps_rejected_at_item_and_move_boundaries(self):
        aware = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
        naive = aware.replace(tzinfo=None)
        for start, end in ((naive, aware + timedelta(hours=1)), (aware, naive + timedelta(hours=1))):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                PlanItem("x", OWNER, "x", "event", start, end)
        with self.assertRaises(ValueError):
            example_plan().propose_move(OWNER, "gym", naive)

    def test_invalid_datetime_type_is_rejected(self):
        with self.assertRaises(TypeError):
            utc("2026-11-25T12:00:00Z")

    def test_interval_order_uses_instants_across_offsets(self):
        with self.assertRaises(ValueError):
            block("x", "2026-11-25T10:00:00-05:00", "2026-11-25T14:30:00Z")
        with self.assertRaises(ValueError):
            block("x", "2026-11-25T10:00:00-05:00", "2026-11-25T15:00:00Z")

    def test_empty_item_or_user_id_rejected(self):
        item = example_plan().read_items(OWNER)[0]
        for field in ("id", "user_id"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(item, **{field: ""})

    def test_collision_checks_compare_utc_instants(self):
        planner = Planner(OWNER, [
            block("gym", "2026-11-25T10:00:00Z", "2026-11-25T11:00:00Z"),
            block("other", "2026-11-26T18:30:00+02:00", "2026-11-26T19:30:00+02:00"),
        ])
        with self.assertRaisesRegex(ValueError, "Schedule conflict"):
            planner.propose_move(OWNER, "gym", datetime.fromisoformat("2026-11-26T11:00:00-05:00"))

    def test_snapshot_is_sorted_by_utc_instant(self):
        later = block("later", "2026-11-25T10:00:00-05:00", "2026-11-25T11:00:00-05:00")
        earlier = block("earlier", "2026-11-25T14:00:00Z", "2026-11-25T14:30:00Z")
        self.assertEqual((earlier, later), Planner(OWNER, [later, earlier]).read_items(OWNER))

    def test_nonexistent_dst_local_time_rejected(self):
        nonexistent = datetime(2026, 3, 8, 2, 30, tzinfo=ZoneInfo("America/New_York"))
        for fold in (0, 1):
            with self.subTest(fold=fold), self.assertRaisesRegex(ValueError, "does not exist"):
                utc(nonexistent.replace(fold=fold))
        with self.assertRaises(ValueError):
            example_plan().propose_move(OWNER, "gym", nonexistent)

    def test_explicit_dst_fold_resolves_to_distinct_instants(self):
        first = datetime(2026, 11, 1, 1, 30, fold=0, tzinfo=ZoneInfo("America/New_York"))
        second = first.replace(fold=1)
        self.assertEqual(timedelta(hours=1), utc(second) - utc(first))
        item = PlanItem("x", OWNER, "x", "event", first, second)
        self.assertEqual(timedelta(hours=1), utc(item.end) - utc(item.start))

    def test_dst_shift_uses_elapsed_duration_for_all_items(self):
        zone = ZoneInfo("America/New_York")
        root = PlanItem("gym", OWNER, "Gym", "workout", datetime(2026, 3, 7, 12, tzinfo=zone),
                        datetime(2026, 3, 7, 13, tzinfo=zone))
        child = replace(root, id="meal", kind="meal", start=datetime(2026, 3, 7, 11, tzinfo=zone),
                        end=datetime(2026, 3, 7, 11, 30, tzinfo=zone), linked_to="gym")
        planner = Planner(OWNER, [root, child])
        proposal = planner.propose_move(OWNER, "gym", datetime(2026, 3, 8, 12, tzinfo=zone))
        for change in proposal.changes:
            self.assertEqual(timedelta(hours=23), change.after.start - utc(change.before.start))
            self.assertEqual(utc(change.before.end) - utc(change.before.start),
                             change.after.end - change.after.start)
            self.assertIs(timezone.utc, change.after.start.tzinfo)


if __name__ == "__main__":
    unittest.main()
