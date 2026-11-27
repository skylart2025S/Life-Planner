# LP-103A — personal device calendar independent review

- Reviewer: api_ui_review; independent from calendar_domain, calendar_ui and coordinator authors.
- Date: 2026-11-26 UTC.
- Base: `149990205eb79088663e7b170afcffdf9f861b41`.
- Reviewed source: current uncommitted working tree on `agent/LP-103B-personal-calendar`; exact final implementation commit remains pending.
- Scope: calendar-domain.js, app.js, index.html, calendar.css, calendar tests, navigation, CI and affected documentation; criteria from LP-103A and DELIVERY_PLAN.md.
- Verdict: source review provisionally accepted after one verified fix; final acceptance/integration pending browser evidence, complete tests and stable commit binding.

## Acceptance coverage

- Empty user calendar, current month, month/day keyboard navigation and Today; no fixture plans or pretend AI calls.
- Create/update/delete preview includes before and after values. Domain proposals clone/freeze snapshots and recompute on apply, checking revision, conflicts and fixed-event restrictions.
- Fixed events require an explicit separate unlock before interval changes or deletion. UI preserves exact instants while unlocking.
- Local timestamps resolve to UTC; source rejects nonexistent/ambiguous times, including half-hour daylight-saving transitions. Coordinator now reports passing timezone tests as described below.
- Device saving uses a separate key, Web Lock and raw-token/revision checks. Stale-tab notifications disable mutation; explicit reload is confirmed. Error states preserve data rather than silently replacing corrupt records.
- Modal previews use labeled HTML dialog, default Cancel, Escape cancellation, captured state/token and focus restoration. All submitted titles render through textContent.
- UI/docs explain device-only storage, absence of account/API/AI integration, and absence of automatic linked meal/clothing moves. This does not close the account-backed or live-AI gates.

## Finding and verified resolution

| ID | Severity | Trigger and impact | Resolution / evidence |
| --- | --- | --- | --- |
| R1 | Medium; previously blocking | Store.save accepted domain-valid state whose JSON exceeded500000 characters, wrote it, then its own load rejected it as unreadable. Reproduction:500 nonoverlapping events with200 lone-surrogate title characters each serialized664927 characters. The saved key changed despite the error asserting otherwise. | calendar-domain.js:101 serializes once and rejects oversized data before setItem. Added regression independently passes and verifies prior raw token/state remains unchanged. |

No additional blocking source defect found in reviewed scope. The previous write/read-size mismatch is resolved in the current working tree.

## Verification actually performed

- Independently ran calendar tests before and after the fix. Reviewer-local result: **12 passed;2 could not execute because child-process spawn returned EPERM**. This earlier reviewer-local run is not a fully passing suite. The blocked cases exercise New York gap/fold conversion and Lord Howe/UTC conversion in subprocesses.
- Independently reproduced R1, inspected its repair and passed the new prior-data-preservation regression.
- JavaScript syntax check for app.js and whitespace diff check passed.
- Read the new/changed UI, domain/tests, CI and docs. No implementation edits made by reviewer.
- Coordinator later reran all JavaScript tests successfully: **24 passed**, including all daylight-saving subprocess cases. This is coordinator-observed evidence, not a new reviewer-local full-suite run. Coordinator Python result:76 discovered,39 passed,37 skipped because no local PostgreSQL test service was configured. Complete remote database regression evidence remains pending.
- Coordinator browser evidence so far: create/confirm, successful save, reload persistence, move before/after preview and Escape cancellation. Remaining browser checks are in progress. Reviewer has not independently run a browser session or observed remote CI for this delivery.

## Handoff

Await remaining browser delete/conflict/fixed/stale/mobile evidence, complete remote database regression checks, and an exact final implementation commit before final acceptance. Coordinator reports that the previously blocked JavaScript timezone tests now pass. Review coverage must be rebound to that commit; subsequent fixes require review. Standing user authorization allows reviewed passing merges, with no protection bypass or deployments. No merge-ready claim is made by this provisional report.
