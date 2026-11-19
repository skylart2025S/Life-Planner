# Implementation backlog

Order reflects dependencies; estimates and provider choices remain open.

| ID | Task | Acceptance criteria | Depends on |
| --- | --- | --- | --- |
| LP-100 | Foundation | Specs, agent briefs, local demo/tests, CI scaffold | Done locally |
| LP-101 | Persistent plans | PostgreSQL migrations; atomic revision check, durable proposal/apply retry, audit/outbox transaction; concurrency and restart tests | LP-100 |
| LP-102 | Authenticated API | Authentication-derived owner; typed endpoints; cross-user access and conflict tests; bounded requests | LP-101 |
| LP-103 | Calendar web UI | Week view, chat panel, before/after preview, explicit confirmation, loading/error states; accessibility checks | LP-102; frontend decision |
| LP-104 | Chat interpretation | Provider adapter returns validated move/clarification; synthetic evaluation set; timeout and malformed-output tests; cost limits | LP-102; model decision |
| LP-105 | Calendar integration | Start with read-only import; owner-scoped OAuth; encrypted credentials; reconciliation and revoked-token tests | LP-102; provider decision |
| LP-106 | Recurring routines | Local-time recurrence and exceptions; DST and skipped-occurrence tests | LP-101 |
| LP-107 | Meal/clothing suggestions | Explicit preferences, known wardrobe/food context, missing-context questions, explanation tests | LP-104 |
| LP-108 | Confirmed external sync | Outbox worker, idempotent writes, retry limits, user-visible failure, duplicate/out-of-order event tests | LP-105 |
| LP-109 | Undo and history | Undo as fresh validated proposal; audit UI; conflicts with later edits handled | LP-101, LP-103 |
| LP-110 | Launch readiness | Load/cost budgets measured; backup restore, deletion, observability, privacy review, accessibility, deployment runbook | Prior release requirements |

Do not start LP-103 and LP-104 by building independent planner implementations. Both must use the same API and planning contracts.
