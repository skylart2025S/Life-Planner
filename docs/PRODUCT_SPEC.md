# Product specification — draft 0.1

## Evidence and assumptions

Confirmed from the user's earlier messages in “AI Life Planner Concept”: a calendar controlled through chat; routine planning such as gym Monday/Wednesday/Friday and studying on other days; schedule changes should affect related meals, clothing, and plans; eventual publication and growth; development with agents, frequent commits, and documentation.

The detailed earlier assistant design was not readable. The supplied repository, https://github.com/skylart2025S/Life-Planner, was cloned on 2026-11-19 and contained no commits or files. The architecture below is a new proposal, not a recovered or approved historical design.

Provisional choices: web-first product, Python planning core, later PostgreSQL storage and a web UI; changes preview before confirmation; Google Calendar as a possible first calendar provider. No provider, frontend framework, hosting vendor, or AI model is selected yet.

## First user journey

1. User sees their week, including routines and related preparations.
2. User says, “I can't go to the gym on Wednesday.”
3. If no replacement time is given, the assistant asks a targeted question or proposes available alternatives. It does not invent a commitment.
4. Once the destination is resolved, the planner checks conflicts and creates one proposal containing all affected items.
5. The UI immediately previews the calendar, meal, and clothing changes together.
6. Confirmation applies the proposal once; an outdated proposal must be regenerated.

## Requirements and acceptance criteria

| ID | Requirement | Acceptance |
| --- | --- | --- |
| LP-01 | Calendar and routines | Week view supports timezone-aware one-off events; recurring rules and exceptions follow in a later slice. |
| LP-02 | Chat intent | Supported requests produce validated commands; unclear event, date, or time yields clarification. |
| LP-03 | Coordinated updates | Moving a root event also moves directly linked meal/clothing preparations; unrelated events remain unchanged. |
| LP-04 | Constraints | No new overlapping scheduled items; fixed commitments cannot be moved. |
| LP-05 | Preview and apply | Preview has no mutation; apply requires explicit confirmation and matching plan revision. |
| LP-06 | Retry safety | Reapplying the same confirmed proposal does not duplicate changes or advance revision again. |
| LP-07 | Account isolation | Every read/write is scoped to the authenticated owner; a different user cannot access a plan. |
| LP-08 | Explainability | Each proposal states affected items and the reason; recommendations distinguish provided facts from missing context. |
| LP-09 | Preferences | Meal/clothing recommendations respect explicitly provided preferences; missing allergy, weather, or wardrobe context is not fabricated. |
| LP-10 | Recovery | Production includes persisted change history, undo proposals, and visible external synchronization failures. |

Implemented now: the in-memory mechanics behind LP-03 through LP-06, explicit owner checks on commands and `read_items(user_id)`, and PostgreSQL persistence with owner-scoped storage operations, durable retries, revision checks, audit history, and pending outbox records. The FastAPI boundary verifies signed access tokens and derives owner identity before storage calls. Internal snapshots and direct-library owner parameters remain trusted access, not authentication or database row-level security. A visible sample-only UI now demonstrates the week and linked-change confirmation journey following user feedback on 2026-11-19. Its Warm Neutral Tones palette follows the user’s supplied colors. Recommendation generation, real chat interpretation, recurring schedules, undo, external syncing and connected browser login remain backlog items.

## Scope boundaries

The first release should plan a week, interpret a narrow set of calendar commands, preview downstream effects, and confirm changes. It will not book travel, buy meals/clothing, send messages, or provide medical treatment advice. Domain “agents” should be simple modules until independent reasoning or tool access is demonstrably necessary.

## Open decisions

- Frontend framework, mobile needs, sign-in provider, and initial calendar integration.
- Whether users can opt into automatic application after trust is established.
- Meal/wardrobe data sources and what users want to enter manually.
- Product targets for latency, per-user AI cost, retention, and expected active users.
- Semantics for recurrence, daylight saving changes, meal windows, and unschedulable requests.
