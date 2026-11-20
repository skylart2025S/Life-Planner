# LP-103 — calendar app layout refinement

- Base: `2e27bd4d9382dca6c0c774a476a244311b01158f`, integrated PR #2 with observed passing main checks.
- Branch: `agent/LP-103-app-layout`.
- Owner: app_layout agent, `apps/web/` only. Coordinator owns docs, integration and browser QA. Independent reviewer: api_ui_review, read-only implementation review and its own report.
- User request: make the visible product more like Acloset and less like an AI-generated dashboard; retain the exact Warm Neutral Tones palette.
- State: implemented; browser checks passed; independent final review and remote checks pending.
- Authorization: commit/push/PR and merge after independent acceptance plus passing current-head checks. No deployment.

## Acceptance

Use a compact month calendar and selected-day agenda, practical controls, restrained sans-serif type and the supplied warm palette. Remove the decorative hero, slogans, sparkles and summary cards. Dates must align correctly for November 2026. Day selection and empty days must behave consistently. All existing sample interactions remain explicit: preview three linked moves, confirm/cancel/reset, and clarify unsupported input without changing the plan. The calendar and agenda must agree before and after confirmation. Support keyboard controls and narrow screens. Clearly disclose that the sample does not call live AI or the authenticated API and resets on reload.

## Reference and scope

The coordinator inspected [Acloset’s official calendar screenshot](https://media.acloset.app/homepage/app/main/app_style_calendar_en_540x1119.webp), linked from [its official site](https://www.acloset.app/). The reference informed the sparse calendar, selected-day treatment and content-first organization. Life Planner retains original branding, icons and sample activities. No Acloset assets, photos or integration are included.

This is a user-requested interface refinement. It does not add live identity, language-model interpretation, persistence in the browser or a deployment. The authenticated API remains unchanged.

## Verification and delivery

Coordinator browser checks passed in the actual in-app browser:

- Correct November2026 grid with30 selectable dates; empty dates show a clear empty state.
- Wednesday25 initially shows4 agenda items. Preview selects Thursday26 and shows4 items, including3 marked proposed and3 corresponding change entries.
- Cancel restores Wednesday’s4 items. Confirm leaves4 on Thursday without proposed markers and only the unrelated focus item on Wednesday. Reset restores the fixture.
- Negated, reversed and time-qualified requests do not open a proposal. The supported phrase previews and confirms on mobile.
- ArrowRight from25 selects26 and preserves focus on the newly rendered day button.
- Desktop and390/320-pixel viewport screenshots inspected. Document content stayed within the viewport (375/375 and305/305 CSS pixels excluding scrollbar). Temporary viewport override reset; user preview refreshed.
- JavaScript syntax and diff whitespace checks passed. Full repository integration results and independent acceptance are recorded by the reviewer.

No browser/API connection or backend behavior was changed. Required remote CI is observed separately before merge. The previous API/preview delivery is merged; its exact review is preserved in `2026-11-19-api-preview-review.md` and its integration evidence in `2026-11-19-api-and-preview.md`.

Next: connect the accepted visible journey to the durable API with loading/error handling and a selected authentication-provider flow. Do not claim M2 complete while the sample is disconnected from live planning.
