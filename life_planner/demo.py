"""Run with python3 -m life_planner.demo from the repository root."""

from datetime import datetime

from life_planner.planning import PlanItem, Planner, utc


def example_plan() -> Planner:
    def item(id, title, kind, start, end, linked=None):
        return PlanItem(id, "demo-user", title, kind, datetime.fromisoformat(start),
                        datetime.fromisoformat(end), linked)

    return Planner("demo-user", [
        item("gym", "Gym", "workout", "2026-11-25T18:00:00-05:00", "2026-11-25T19:00:00-05:00"),
        item("meal", "Pre-workout meal", "meal", "2026-11-25T17:00:00-05:00", "2026-11-25T17:30:00-05:00", "gym"),
        item("clothes", "Prepare gym clothes", "clothing", "2026-11-25T17:45:00-05:00", "2026-11-25T18:00:00-05:00", "gym"),
        item("study", "Study", "study", "2026-11-26T14:00:00-05:00", "2026-11-26T16:00:00-05:00"),
    ])


def main():
    planner = example_plan()
    proposal = planner.propose_move("demo-user", "gym", datetime.fromisoformat("2026-11-26T18:00:00-05:00"))
    print("DEMO: move Wednesday gym to Thursday; timestamps below are UTC.")
    for change in proposal.changes:
        print(f"{change.before.title}: {utc(change.before.start).isoformat()} -> {change.after.start.isoformat()}")
    print(f"Preview only: revision remains {planner.revision}.")
    print(f"Demo confirms proposal: revision {planner.apply('demo-user', proposal.id, confirmed=True)}.")
    print("No live calendar, model, or database was used.")


if __name__ == "__main__":
    main()
