# AI Life Planner — foundation

A chat-driven calendar that keeps routines, meals, and clothing plans aligned when life changes.

This is a **project foundation**, not a deployed application. It includes a runnable planning core, project specifications, a coordinated development team workflow, and GitHub CI/templates. The repository is https://github.com/skylart2025S/Life-Planner. No AI provider for the product, calendar account, or database is connected yet.

## Start here

1. Read [product spec](docs/PRODUCT_SPEC.md) and [architecture](docs/ARCHITECTURE.md).
2. Read [team charter](docs/TEAM_CHARTER.md) and [agent workflow](docs/AGENT_WORKFLOW.md) before assigning development work.
3. Select the next task in [backlog](docs/BACKLOG.md).
4. Run the demo and tests from this directory with Python 3.12 or newer:

```sh
python3 -m life_planner.demo
python3 -m unittest discover -s tests -v
python3 scripts/review_context.py
```

The demo moves a Wednesday gym session and its linked meal/clothing preparations to Thursday, previews the changes, then explicitly applies them. It uses fixtures and deterministic rules, not a language model. Context reports are written to `reports/` and work even before Git initialization.

## Layout

| Path | Purpose |
| --- | --- |
| `life_planner/` | Working domain core and integration interfaces |
| `tests/` | Behavior tests for rescheduling, conflicts, ownership, and retries |
| `agents/` | Role briefs and review/handoff templates for coding agents |
| `docs/` | Requirements, architecture, API draft, roadmap, decisions, progress |
| `apps/web/`, `apps/api/`, `workers/` | Documented boundaries for future implementation |
| `scripts/review_context.py` | Local repository/spec context packet for a review agent |
| `.github/` | CI workflow, issue template, pull request checklist |

## Team and GitHub

The supplied repository was empty when cloned. The initial foundation passed independent review. Bootstrap publication was attempted but is blocked by local GitHub authentication; the commits are saved locally. See [GitHub setup](docs/GITHUB_SETUP.md) for branch, pull request, and repository settings. Dated evidence belongs in [delivery reports](docs/reports/).

An hourly Codex task continuation is active for the coordinated development team. It works on a bounded milestone slice, with implementation, independent review, tests, commits, and reports. It does not authorize automatic merging or deployment. Scheduling is managed by the Codex app, not a service installed in this repository.

The parent project mirror and its `sources/` remain untouched. See [status](docs/STATUS.md) and the latest report for observed commit, push, and check results.
