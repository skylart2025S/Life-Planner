# LP-103A — personal device calendar independent review

- Reviewer: api_ui_review; independent from calendar_domain, calendar_ui and coordinator authors.
- Final review date: 2026-11-27 UTC.
- Base: `149990205eb79088663e7b170afcffdf9f861b41`.
- Accepted implementation and delivery documentation: `6832583bfc4a28c32bb601cb2ce66611f2f715d1`.
- Scope: calendar-domain.js, app.js, index.html, calendar.css, calendar tests, navigation, CI and affected documentation; criteria from LP-103A and DELIVERY_PLAN.md.
- Verdict: **Accepted.** One blocking finding was fixed and verified; no remaining blocking source finding in this scope. This verdict binds to the exact implementation commit above. Merge still requires passing checks on the final report-bearing head.

## Acceptance coverage

- Empty user calendar, current month, month/day keyboard navigation and Today; no fixture plans or pretend AI calls.
- Create/update/delete preview includes before and after values. Domain proposals clone/freeze snapshots and recompute on apply, checking revision, conflicts and fixed-event restrictions.
- Fixed events require an explicit separate unlock before interval changes or deletion. UI preserves exact instants while unlocking.
- Local timestamps resolve to UTC; source rejects nonexistent/ambiguous times, including half-hour daylight-saving transitions.
- Device saving uses a separate key, Web Lock and raw-token/revision checks. Stale-tab notifications disable mutation; explicit reload is confirmed. Error states preserve data rather than silently replacing corrupt records.
- Modal previews use labeled HTML dialog, default Cancel, Escape cancellation, captured state/token and focus restoration. All submitted titles render through textContent.
- UI/docs explain device-only storage, absence of account/API/AI integration, and absence of automatic linked meal/clothing moves. This does not close the account-backed or live-AI gates.

## Finding and verified resolution

| ID | Severity | Trigger and impact | Resolution / evidence |
| --- | --- | --- | --- |
| R1 | Medium; previously blocking | Store.save accepted domain-valid state whose JSON exceeded 500000 characters, wrote it, then its own load rejected it as unreadable. Reproduction: 500 nonoverlapping events with 200 lone-surrogate title characters each serialized 664927 characters. The saved key changed despite the error asserting otherwise. | calendar-domain.js:101 serializes once and rejects oversized data before setItem. Added regression independently passes and verifies prior raw token/state remains unchanged. |

No additional blocking source defect found in reviewed scope. The write/read-size mismatch is resolved in the accepted commit.

## Verification and attribution

- Independently read the UI, domain/tests, CI and docs, then refreshed the final diff through the accepted commit. No implementation edits made by reviewer. Final whitespace diff check passed.
- Independently ran calendar tests before and after the fix. Reviewer-local result: **12 passed; 2 could not execute because child-process spawn returned EPERM**. That earlier reviewer-local run is not a fully passing suite. The blocked cases exercise New York gap/fold conversion and Lord Howe/UTC conversion in subprocesses.
- Independently reproduced R1, inspected its repair and passed the new prior-data-preservation regression. JavaScript syntax check for app.js passed.
- Coordinator subsequently observed **24 JavaScript tests passed**, including all daylight-saving subprocess cases. Local Python result was 76 discovered, 39 passed and 37 skipped because no local PostgreSQL test service was configured.
- Coordinator observed remote push CI run **45937728265** on the accepted commit succeed: **76 Python tests OK with no skips, and 24 JavaScript tests passed with no failures or skips**. This remote evidence is attributed to the coordinator; reviewer did not independently fetch the run logs.
- Coordinator browser QA: create/confirm/save and refresh persistence; move before/after preview and Escape cancellation; confirmed move persisted on November 27 at 11:00–12:00; overlapping 11:30–12:30 creation blocked; delete preview showed removal and cancellation preserved the event; fixed flag saved and edit time inputs became read-only; separate unlock saved; second tab detected stale data and disabled saving, with explicit reload restoring current state and enabled controls; ArrowRight, PageDown and Today worked; 390px and 320px screenshots inspected without horizontal overflow.
- Reviewer did not independently run a browser session. The final destructive delete action was covered by domain tests, not completed in coordinator browser QA. Storage failure/corruption handling was reviewed in source/domain tests rather than browser injection. No formal accessibility audit was performed.

## Handoff

Source acceptance is complete for `6832583bfc4a28c32bb601cb2ce66611f2f715d1`. This review report may be committed separately without changing the accepted implementation. Verify that the resulting head changes only review evidence and observe passing automated checks on that final head before merging PR #5. Any subsequent implementation change requires renewed review. Standing user authorization allows reviewed passing merges, with no protection bypass or deployments.
