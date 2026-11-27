# Delivery plan — complete planning journey

Agreed by the coordinator after the 2026-11-20 agent planning meeting, following the user's request for real AI, outfits and a professional scalable product. This is the team's implementation plan, not a claim that the product is complete. See PRODUCT_SPEC.md for confirmed user requirements and BACKLOG.md for the delivery ledger.

## Outcome and completion gates

A person can enter their own routines, preferences and wardrobe, ask for a schedule change in natural language, clarify missing information, review coordinated calendar/meal/outfit proposals, confirm, and reopen their saved plan. The product keeps the warm neutral visual direction. No fabricated clothes, pantry contents, preferences or weather may be presented as known facts.

| Stage | Required working journey | Evidence needed to close |
| --- | --- | --- |
| A — owned data and saved plans | Create/edit garments and availability; build an outfit from owned items; create/reopen real calendar items; connect account-scoped persistence | CRUD and refresh tests; valid garment references; account isolation for cloud storage; loading/error/mobile/keyboard checks. Any device-only interim slice is clearly labeled and does not close the cloud gate. |
| B — real AI planning | Varied requests produce typed moves or useful clarification from actual plan context; proposals require confirmation | Live provider tested with configured credentials; versioned held-out evaluations; malformed output, unknown IDs, injection, ambiguity, DST, timeout and quota tests; zero unconfirmed mutations. Fake adapters alone cannot close this gate. |
| C — grounded outfits and meals | Recommendations draw from owned available garments and explicit preferences; meal suggestions respect recorded restrictions and distinguish unknown pantry/ingredient data; accepted outfit stays associated with the event when moved | Owned-ID validation, availability/revision checks, user swaps and acceptance, missing-context questions, preference violations rejected, truthful weather provenance. Manual outfits or clothing time blocks alone cannot close this gate. |
| D — routine and recovery | Recurrence, undo/history, account export/deletion, recovery and calendar import/sync with an authorized provider | DST/exception tests, undo conflicts, deletion/retention design and tests, restore drill, revoked-token and idempotent synchronization/reconciliation tests. Import precedes external writes. An unconfigured provider leaves this gate pending unless the user explicitly approves release scope excluding external integration. |
| E — professional release | Accessible responsive journey, secure account lifecycle, operations runbook and measured capacity/cost | Browser journey checks, accessibility review, isolation review, load/contention evidence, AI cost/latency measurements, backup restoration, monitoring and readiness checks. Separate user authorization remains necessary for deployment. |

## Immediate assignment: LP-107A

Manual wardrobe capture and outfit building is independent of model credentials. First deliver a usable browser screen with bounded, versioned device storage: add/edit/delete clothes, record availability, select a valid outfit, preview and explicitly save, reopen and remove outfits. Start empty rather than inventing user possessions. Explain device-only saving and the absence of calendar association/live AI. Handle invalid/corrupt/unavailable storage, stale tabs and missing/deleted/unavailable garment references visibly. This is a limited first implementation slice, not the final persistence architecture.

Ownership: wardrobe_builder owns new apps/web/wardrobe* files and tests/web/wardrobe.test.js. Coordinator owns navigation, CI, docs, integration and browser checks. A separate reviewer owns the final review report and reads the entire implementation diff. Future account persistence must migrate/import device data only with the user choosing the destination account; local data must not silently appear in whichever account signs in.

## Next sequence and contracts

1. LP-107A manual capture/outfit builder is integrated. User-requested practical functionality adds LP-103A personal device calendar with preview/confirmation; it does not close account-backed gates. Then LP-103B account-backed calendar journey, loading/errors and refresh-safe state; LP-107B owns wardrobe persistence and its connected UI. Sign-in registration is a dependency of live account activation, not of every implementation task.
2. LP-104A typed intent service, provider boundary, synthetic fixtures and evaluation runner; LP-104B configured live provider, measured quality/cost, clarification UI and confirmation journey. Do not let a test interpreter appear as live AI.
3. LP-107B persisted preferences and event/outfit association; LP-107C constrained recommendation candidate selection plus model ranking and grounded meal recommendations. Validate ownership, IDs and current availability after model output; model prose never writes a plan.
4. LP-106/109 recurrence and undo/history; LP-105/108 authorized provider import/sync; LP-110 measured release gates. Include release testing during feature development, not only at the end.

Use authenticated owner identity, bounded plan/wardrobe context, IANA timezone and server time. AI results distinguish a move, clarification, unsupported request and provider failure. Clothing records have stable IDs and explicit user-entered attributes; outfit assignments are separate from preparation time blocks. Weather requires a source/location/time, and absence stays unknown. Provider calls must happen outside database locks.

## Architecture and scale

Keep a modular API and PostgreSQL, with a bounded worker when asynchronous work is introduced. The review found new connections per storage call, write locks even on reads, date filtering after full-plan loading, a concurrency cap per process rather than per account, and no retention/deletion/key-rotation lifecycle. Address these with measured pooling/query/fairness work and dedicated lifecycle tests. Do not claim scalability from the existence of PostgreSQL or introduce microservices without evidence.

Proposed initial benchmark targets below are engineering hypotheses, not measured capacity, purchases, user-approved SLAs or guaranteed pricing. Confirm environment and budgets before closing the release gate:

- 1,000 synthetic accounts with up to 500 plan items, 50 concurrent sessions, 20 requests/second for 30 minutes.
- p95 reads at most 300 ms and deterministic proposal/apply at most 750 ms; report contention and intentional overload responses separately.
- Zero cross-user disclosures, lost updates or duplicate applications; less than 1% unexpected server errors.
- At least 95% supported-intent/clarification accuracy on a reviewed held-out set and 100% of critical safety/isolation fixtures passing.
- Proposed AI p95 at most 8 seconds and hard timeout 15 seconds. Measure actual provider costs and enforce configurable per-account quotas before enabling paid usage.
- Proposed recovery objectives: at most 24-hour data loss window and 4-hour recovery time, demonstrated by a restore drill.

## Decisions and scheduling

Pending: sign-in method/provider configuration, live model credentials and spending limit, external-calendar provider, hosting/operational budget, privacy/retention policy and approved capacity targets. Do not request secrets in chat. Make reversible implementation decisions locally, record assumptions, and raise only decisions that block the next dependent step.

The existing hourly task ai-life-planner-development-team was updated, not duplicated. Each run starts with a short coordination review and delivers one bounded reviewed slice. Scheduled status does not guarantee a run has executed or remove access/usage limits. Notify on delivery, significant failure or required user input, not unchanged polling. Stop expanding scope at the documented release gate and ask for the next milestone. No deployment or purchase is authorized.
