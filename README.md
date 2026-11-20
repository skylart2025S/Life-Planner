# AI Life Planner

A chat-driven calendar that keeps routines, meals, and clothing plans aligned when life changes.

This is an **early local prototype**, not a deployed application. It includes an interactive month calendar and daily agenda, an authenticated planning API, PostgreSQL persistence, a deterministic planning core, and a coordinated development team workflow. The repository is https://github.com/skylart2025S/Life-Planner. No live AI provider, calendar account, or hosted production database is connected.

## Try the visible prototype

From the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory apps/web
```

Open [Life Planner locally](http://127.0.0.1:8765). Select a day in November’s sample calendar to view its agenda. Open “Change a plan” to move Wednesday gym to Thursday, preview all three linked changes, then confirm or cancel. The screen uses sample data and a predefined interaction; it does not yet call the authenticated API or live AI. Reloading resets its state. See [browser prototype](apps/web/README.md) and [API setup](apps/api/README.md).

## Start here

1. Read [product spec](docs/PRODUCT_SPEC.md) and [architecture](docs/ARCHITECTURE.md).
2. Read [team charter](docs/TEAM_CHARTER.md) and [agent workflow](docs/AGENT_WORKFLOW.md) before assigning development work.
3. Select the next task in [backlog](docs/BACKLOG.md).
4. Run the demo and tests from this directory with Python 3.12 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m life_planner.demo
.venv/bin/python -m unittest discover -s tests -v
python3 scripts/review_context.py
```

The demo moves a Wednesday gym session and its linked meal/clothing preparations to Thursday, previews the changes, then explicitly applies them. It uses fixtures and deterministic rules, not a language model. Context reports are written to `reports/` and work even before Git initialization.

For durable plans and the PostgreSQL integration tests, follow [persistence setup](docs/PERSISTENCE.md). The commands above run the domain tests; database tests skip unless the test database is configured. CI configures PostgreSQL and runs both suites.

## Layout

| Path | Purpose |
| --- | --- |
| `life_planner/` | Working domain core, PostgreSQL storage, and integration interfaces |
| `migrations/` | Versioned PostgreSQL schema with checksum tracking |
| `tests/` | Behavior tests for rescheduling, conflicts, ownership, and retries |
| `agents/` | Role briefs and review/handoff templates for coding agents |
| `docs/` | Requirements, architecture, API draft, roadmap, decisions, progress |
| `apps/web/` | Interactive month calendar, daily agenda, linked-change preview and confirmation |
| `apps/api/` | Authenticated typed planning API; trusted local public keys |
| `workers/` | Future external-calendar synchronization boundary |
| `scripts/review_context.py` | Local repository/spec context packet for a review agent |
| `.github/` | CI workflow, issue template, pull request checklist |

## Team and GitHub

The supplied repository was empty when cloned. The initial foundation passed independent review. The reviewed foundation has been pushed to `main`, and its GitHub checks passed. GitHub CLI authentication is working for future branch pushes and review operations. See [GitHub setup](docs/GITHUB_SETUP.md) for branch, pull request, and repository settings. Dated evidence belongs in [delivery reports](docs/reports/).

An hourly Codex task continuation is active for the coordinated development team. It works on a bounded milestone slice, with implementation, independent review, tests, commits, and reports. The user authorized merging independently reviewed PRs once all automated checks pass on 2026-11-19. Deployments remain unauthorized. Scheduling is managed by the Codex app, not a service installed in this repository.

The parent project mirror and its `sources/` remain untouched. See [status](docs/STATUS.md) and the latest report for observed commit, push, and check results.
