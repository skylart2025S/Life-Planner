# Implementation backlog

Order reflects dependencies; estimates and provider choices remain open.

| ID | Task | Acceptance criteria | Depends on |
| --- | --- | --- | --- |
| LP-100 | Foundation — integrated | Specs, agent briefs, local demo/tests, CI scaffold; published main with passing checks | Complete |
| LP-101 | Persistent plans — integrated in PR #1 | PostgreSQL migrations; atomic revision check, durable proposal/apply retry, audit/outbox transaction; 46 local tests passed with real PostgreSQL; independent review accepted and remote CI passed | Complete; main `46d840d` |
| LP-102 | Authenticated API — integrated in PR #2 | Authentication-derived owner; typed endpoints; cross-user access and conflict tests; bounded requests | LP-101 |
| LP-103 | Calendar web UI — month/day sample integrated in PR #3 | Week view, chat panel, before/after preview, explicit confirmation, loading/error states; accessibility checks | Sample prototype now; authenticated connection depends on LP-102 and sign-in |
| LP-103A | Personal calendar on this device — independently accepted in PR #5; integration pending | Empty initial calendar, real dates/month navigation, user event create/edit/remove, preview/confirm, conflicts/fixed-event safeguards, refresh saving and visible storage errors; device-only gate | Independent of identity configuration; does not close LP-103B |
| LP-103B | Connected calendar journey | API-backed creation/read/preview/confirmation, loading/errors, refresh-safe state and session recovery | LP-102 for implementation; identity configuration for live acceptance |
| LP-104A | Typed intent pipeline and evaluation harness | Provider-independent result validation, clarification/unsupported/error distinctions; versioned synthetic fixtures, timeout/invalid-output tests | LP-102; live credentials not required for boundary tests |
| LP-104B | Live AI interpretation | Real provider acceptance/evaluation run, held-out quality, cost/quota controls, connected clarification/preview UI | LP-104A; provider credentials and spending approval for live acceptance |
| LP-105 | Calendar integration | Start with read-only import; owner-scoped OAuth; encrypted credentials; reconciliation and revoked-token tests | LP-102; provider decision |
| LP-106 | Recurring routines | Local-time recurrence and exceptions; DST and skipped-occurrence tests | LP-101 |
| LP-107A | Manual wardrobe and outfit builder — integrated in PR #4 | User-owned garment entry/edit/removal, availability, valid explicit outfit selection, bounded device saving with visible errors and refresh; no AI/cloud claims | Independent of live sign-in/model; first slice only |
| LP-107B | Account-backed wardrobe, preferences and event outfits | Owner-scoped durable records, isolation/revision tests, explicit migration from device data, outfit stays linked when event moves | LP-102 for implementation; live account activation only for end-to-end acceptance |
| LP-107C | Grounded meal/outfit recommendations | Known wardrobe/food context, preference enforcement, missing-context questions, provenance and live provider evaluation | LP-104B, LP-107B |
| LP-108 | Confirmed external sync | Outbox worker, idempotent writes, retry limits, user-visible failure, duplicate/out-of-order event tests | LP-105 |
| LP-109 | Undo and history | Undo as fresh validated proposal; audit UI; conflicts with later edits handled | LP-101, LP-103 |
| LP-110 | Launch readiness | Load/cost budgets measured; backup restore, deletion, observability, privacy review, accessibility, deployment runbook | Prior release requirements |

User feedback on 2026-11-19 prioritizes a visible, usable calendar alongside API work. LP-103 begins with a clearly labeled sample-only browser prototype; it does not claim live AI, durable saving, or authenticated integration. The connected product and LP-104 must use the same API and deterministic planning contracts.

See [delivery plan](DELIVERY_PLAN.md) for full user-journey completion gates and proposed load/AI/recovery benchmarks. Local storage, test adapters and fixtures never close live account/AI/release gates.
