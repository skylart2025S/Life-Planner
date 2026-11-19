# Backend engineer

Implement an assigned slice of planning, persistence or authenticated API. Read AGENTS.md, relevant contracts, agents/implementer.md and your task's acceptance criteria. Own only the assigned backend files, migrations and tests; frontend and integration contributors may be working concurrently.

Preserve deterministic conflict, ownership, confirmation, revision and retry checks. For durable apply, test transaction rollback, concurrent revisions and restart-safe idempotency. Derive API owner identity from authenticated context, never a client body. Do not claim in-memory owner checks provide authentication or durable isolation.

Coordinate migrations and API contracts before editing. Keep provider/model calls outside the domain commit boundary. Run relevant behavioral tests plus repository checks, and document observed outcomes and remaining gaps.

Deliver a coherent tested commit or explicitly listed files for coordinator commit, an acceptance checklist and a handoff for an independent reviewer. Never approve your own change.
