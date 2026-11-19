# LP-102 / LP-103 first slice — authenticated API and visible calendar

- Date: 2026-11-19 UTC.
- State: implemented and locally verified; independent stable-revision review and remote checks are recorded below/by the linked review and PR.
- Owners: planning_engineer authored `apps/api/`; team_operations authored initial API/auth tests; api_regression_fixes authored NUL/date/transport regressions; independent_review (reassigned frontend role) authored `apps/web/`; coordinator integrated docs/dependencies and the requested visual palette. api_ui_review independently reviewed the final implementation and fixes without authoring it.
- Base: main `46d840d0568082523a5d76585f1ea3a57625c561`; branch `agent/LP-102-authenticated-api`.
- Implementation: `420248c` API/dependencies/tests; `d24d0db` sample calendar and warm-neutral theme. Documentation/review commits may follow.
- Authorization: commit/push/PR and merge independently reviewed PRs when all automated checks pass; no deployments or repository-permission changes.

## Visible outcome

The browser now displays a weekly calendar and planning panel. A supported Wednesday-to-Thursday gym request previews the gym, meal and clothes preparations together; cancellation preserves the original schedule, confirmation applies the local sample, and reset restores it. Responsive layout provides a scrollable calendar on narrow screens. The user-requested palette uses Azure Mist #ecf8f8, Alabaster Grey #eee4e1, Almond Cream #e7d8c9, Almond Silk #e6beae and Camel #b2967d, with creamy surfaces and darker soft brown text.

This screen intentionally labels its sample data, predefined request and browser-memory state. It does not call the API, a model or an external calendar. That connection remains the next product slice. The user asked for something visible after the infrastructure-heavy start; this delivery adjusts sequencing accordingly.

## Backend outcome

A FastAPI resource server verifies real signed RS256 access tokens from configured public keys and derives an opaque issuer/subject owner. Typed create/read/propose/apply endpoints call the existing PostgreSQL planner. Strict confirmation, bounded bodies/date windows/items, duplicate-header/JSON handling, safe errors, request deadlines, database timeouts and a per-process concurrency cap are covered. Local keys require restart for rotation. No login service/provider or live-user policy is configured.

## Acceptance evidence

- Coordinator and independent reviewer each ran the full suite against real PostgreSQL16.15: **76 tests passed, zero skips** (27 domain,19 persistence,7 authentication,18 HTTP and5 boundary tests).
- Command: `PLAN_TEST_DATABASE_URL=<isolated-local-test-DSN> .venv/bin/python -m unittest discover -s tests -q`.
- Core fixture demo, local review-context generation, JavaScript syntax and `git diff --check` passed.
- Browser QA at1500×1000 and390×844: initial11 events; preview3 proposed and3 original ghost events; cancel leaves Wednesday intact; confirm moves exactly3 items to Thursday; reset restores; unsupported input clarifies; supported phrase previews; mobile confirmation works. No JavaScript page errors or page-width overflow. Coordinator inspected desktop/mobile screenshots and refreshed the user’s in-app preview to verify the palette.
- Independent source review rejected NUL database text returning500 and overly broad sample-language matching. Fixes now return400/no writes and reject negated/reversed/time-qualified requests. Prior extreme-date overflow and incomplete-body exhaustion fixes are regression-tested.
- Existing test-client dependency emits a nonblocking deprecation warning; tests pass with pinned dependencies.
- Browser checks are coordinator evidence, not a claim of accessibility certification or automated remote browser CI. Python/API/database tests run in GitHub CI.

## Publication and continuation

Remote push, PR and observed check evidence are added after publication; local checks alone do not establish remote success. See the independent review report for final accepted revision. No deployment has been performed.

Next: complete authorized integration, then connect the visible UI to durable authenticated plans with loading/errors and refresh-safe state. A live sign-in provider and compatible access-token policy remain product decisions before real accounts. Live AI, recurring routines, recommendations, calendar import/sync and undo remain backlog items. The hourly continuation remains active and should finish existing work before creating a new slice.
