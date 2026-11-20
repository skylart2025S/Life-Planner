# Implementation backlog

Order reflects dependencies; estimates and provider choices remain open.

| ID | Task | Acceptance criteria | Depends on |
| --- | --- | --- | --- |
| LP-100 | Foundation — integrated | Specs, agent briefs, local demo/tests, CI scaffold; published main with passing checks | Complete |
| LP-101 | Persistent plans — integrated in PR #1 | PostgreSQL migrations; atomic revision check, durable proposal/apply retry, audit/outbox transaction; 46 local tests passed with real PostgreSQL; independent review accepted and remote CI passed | Complete; main `46d840d` |
| LP-102 | Authenticated API — integrated in PR #2 | Authentication-derived owner; typed endpoints; cross-user access and conflict tests; bounded requests | LP-101 |
| LP-103 | Calendar web UI — month/day sample refined | Week view, chat panel, before/after preview, explicit confirmation, loading/error states; accessibility checks | Sample prototype now; authenticated connection depends on LP-102 and sign-in |
| LP-104 | Chat interpretation | Provider adapter returns validated move/clarification; synthetic evaluation set; timeout and malformed-output tests; cost limits | LP-102; model decision |
| LP-105 | Calendar integration | Start with read-only import; owner-scoped OAuth; encrypted credentials; reconciliation and revoked-token tests | LP-102; provider decision |
| LP-106 | Recurring routines | Local-time recurrence and exceptions; DST and skipped-occurrence tests | LP-101 |
| LP-107 | Meal/clothing suggestions | Explicit preferences, known wardrobe/food context, missing-context questions, explanation tests | LP-104 |
| LP-108 | Confirmed external sync | Outbox worker, idempotent writes, retry limits, user-visible failure, duplicate/out-of-order event tests | LP-105 |
| LP-109 | Undo and history | Undo as fresh validated proposal; audit UI; conflicts with later edits handled | LP-101, LP-103 |
| LP-110 | Launch readiness | Load/cost budgets measured; backup restore, deletion, observability, privacy review, accessibility, deployment runbook | Prior release requirements |

User feedback on 2026-11-19 prioritizes a visible, usable calendar alongside API work. LP-103 begins with a clearly labeled sample-only browser prototype; it does not claim live AI, durable saving, or authenticated integration. The connected product and LP-104 must use the same API and deterministic planning contracts.
