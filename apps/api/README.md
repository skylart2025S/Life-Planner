# API boundary — not implemented

Implement the endpoints in docs/API_DRAFT.md after transactional persistence (LP-101).
The API owns authentication, input validation, owner scoping, rate limits, and error mapping.
It calls life_planner rather than duplicating planning rules. Keep provider/model calls behind adapters.

Framework and authentication selection remain open. Do not expose the in-memory prototype as a multi-user service.
