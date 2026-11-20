# LP-103 — calendar app layout refinement

- Base: `2e27bd4d9382dca6c0c774a476a244311b01158f`, integrated PR #2 with observed passing main checks.
- Branch: `agent/LP-103-app-layout`.
- Owner: app_layout agent, `apps/web/` only. Coordinator owns docs, integration and browser QA. Independent reviewer: api_ui_review, read-only implementation review and its own report.
- User request: make the visible product more like Acloset and less like an AI-generated dashboard; retain the exact Warm Neutral Tones palette.
- State: implemented and pushed in PR #3; browser and remote checks passed on the implementation head; independent review accepted the exact implementation head. Final report-head checks and merge verification remain the integration gate.
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

## Publication evidence

- Implementation: `2642d71ed5a7656986fda66cf7e1f4e01a9127a3`, pushed to `agent/LP-103-app-layout`.
- Pull request: [PR #3](https://github.com/skylart2025S/Life-Planner/pull/3).
- Implementation-head checks observed successful: [pull request run](https://github.com/skylart2025S/Life-Planner/actions/runs/44666182046) and [branch run](https://github.com/skylart2025S/Life-Planner/actions/runs/44666143933). The pull request log reports 76 tests, OK, with PostgreSQL enabled.
- On continuation, the local preview was restarted and verified HTTP 200 at `http://127.0.0.1:8765/`. This is a local preview, not a deployment.

- Independent review accepted implementation `2642d71ed5a7656986fda66cf7e1f4e01a9127a3`; see [review report](2026-11-20-app-layout-review.md). The reviewer independently verified all 76 CI tests passed; the local database had stopped, so the local retry is not reported as a pass. The following commit contains reports/status only, with unchanged implementation.
