# LP-102 API / LP-103 sample UI — independent review

- Reviewer: `api_ui_review` agent, independent of all implementation authors; no implementation edits made.
- Authors: planning_engineer, team_operations, api_regression_fixes, frontend contributor, coordinator; see delivery report for ownership.
- Date: 2026-11-19 UTC.
- Acceptance source: AGENTS.md, PRODUCT_SPEC.md, BACKLOG.md, API_DRAFT.md, TEAM_CHARTER.md and user direction prioritizing a visible product.
- Base: `46d840d0568082523a5d76585f1ea3a57625c561`.
- Final reviewed head: **`0b469062a08ae2bf502c7c84286f449a9b53b45a`**.
- Implementation commits: API `420248c`, browser sample `d24d0db`; final documentation `0b46906`.
- Verdict: **accepted** for LP-102 and the explicitly sample-only LP-103 first slice. No remaining blocking finding in reviewed scope.
- Remote context: GitHub checks for this delivery have not been observed by this reviewer; passing current-head checks remain required before integration.

## Acceptance coverage

| Criterion | Evidence | Verification / result |
| --- | --- | --- |
| Authentication-derived owner | apps/api/auth.py; app.py owner dependency | Real RSA signatures, algorithm/profile/claim checks, issuer/subject namespace and cross-identity tests pass. |
| Durable create/read/preview/apply | apps/api/app.py; existing storage adapter | Real PostgreSQL HTTP journey, preview immutability, explicit confirmation, stale proposals and scoped retry tests pass. |
| Bounded safe requests | apps/api/middleware.py; models.py | Byte caps, malformed input, extreme dates, NUL text, stalled/dripping body, disconnect and saturation regressions pass; private errors sanitized. |
| Honest visible journey | apps/web/index.html; app.js | Sample-only scope, browser-memory state, no live AI/account/calendar claims; explicit preview/confirm/cancel/reset; actual matcher rejects unsupported/negated/reversed/time-qualified inputs. |
| User visual direction | apps/web/styles.css | Requested warm-neutral tokens and readable darker supporting text present; responsive layout and keyboard focus styles inspected. Actual browser checks are coordinator evidence. |
| Handoff and authority | README; API/spec/backlog/status/team docs; delivery report | Local run instructions, current limits and next connected-UI work recorded; reviewed passing merges authorized, deployments excluded. |

## Findings and resolution

| ID | Original severity | Location / trigger | Fix and reviewer verification | Disposition |
| --- | --- | --- | --- | --- |
| R1 | Medium; blocked acceptance | apps/api/models.py:39–40 accepted NUL in title/kind, causing PostgreSQL DataError and HTTP500. | API commit `420248c`: validator at models.py:46 rejects NUL. HTTP regression verifies400, no private input echo and no persisted plan; passes against real DB. | Resolved |
| R2 | Medium; blocked acceptance | apps/web/app.js:89 accepted “never move gym to Thursday,” reversed direction, or morning requests but previewed the same Thursday18:00 move. | UI commit `d24d0db`: anchored narrow phrase grammar. Evaluated actual source expression: six unsupported examples reject, four supported demo variants accept. | Resolved |

Prior timestamp-overflow and indefinite-body-read defects are also fixed: local-year validation precedes UTC conversion; a total10-second deadline releases request capacity. Dedicated regressions verify both.

The earlier API documentation note is resolved: API_DRAFT.md:29 documents the total body-read deadline and :42 documents HTTP408. No documentation blocker remains.

## Verification actually performed

- Independently ran `.venv/bin/python -m unittest discover -s tests -v` with `PLAN_TEST_DATABASE_URL` pointing to the isolated temporary local PostgreSQL database: **76 tests passed, zero skips**,6.075seconds. This supersedes an earlier attempt while the database server was stopped.
- Inspected all API/auth/bounds test code and the committed implementation, UI, dependency/CI changes and final documentation against the base. Final working tree was clean at the reviewed head.
- Independently checked actual UI matcher with six negative and four positive phrases; all expected outcomes passed.
- `node --check apps/web/app.js` and `git diff --check` passed; final committed diff whitespace check also passed.
- Standalone ASGI checks confirmed timeout408 prevents downstream invocation, returns capacity for a subsequent200, and saturation returns503.
- Coordinator separately reports desktop/mobile browser journeys, visual screenshot inspection and visible palette refresh. Those are author/coordinator observations, not independent browser execution by this reviewer.
- Existing testclient emits a nonblocking deprecation warning about its httpx backend. Pinned dependencies pass the suite.

## Remaining limits and integration eligibility

This accepts an authenticated resource-server foundation and an isolated visual sample, not a finished connected product. Browser/API connection, live login policy/provider, live AI, recurrence, external calendar delivery, undo, distributed quotas, production capacity and accessibility certification remain outside this slice. No deployment is authorized.

The exact reviewed head is **`0b469062a08ae2bf502c7c84286f449a9b53b45a`**. Review acceptance is complete; merge eligibility remains conditional on observing all automated checks passing for the current PR head and confirming any subsequent changes are report-only or reviewed. Do not bypass protection or force-push.
