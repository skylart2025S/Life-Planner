# ADR 0002: Serialize per-plan PostgreSQL transactions

Status: implemented in LP-101; awaiting integration through its pull request.

Context: the foundation's in-memory plans and retry receipts disappear on process restart and cannot coordinate competing writers. LP-101 requires durable proposals, revision checks, and atomic audit/outbox recording.

Decision: use PostgreSQL through psycopg3, with one fresh transaction per storage call. Lock the owner/plan row before reading its items or revision. Store items, revision, audit history, idempotency receipt, and outbox event atomically on apply. Composite keys preserve owner/plan relationships; deterministic planner revalidation remains the authority for permitted mutations.

Idempotency keys are scoped to owner + plan. A retry returns the first result even after newer revisions. A key cannot be reused for a different proposal. Applying one proposal with another key returns the original result without repeating side effects.

Consequences: correctness is explicit and independently testable across connections/processes, at the cost of serializing reads and writes for one plan. Database access is trusted; API authentication and potential RLS remain separate work. Pooling, timeout policy, history deletion, proposal expiration, outbox delivery and production migration packaging are not solved here.

Validation gate: real PostgreSQL tests for restart durability, concurrent competing writes/retries, owner isolation, migration repeatability, and rollback when a late outbox write fails. Local skips or mocked connections cannot satisfy this gate.
