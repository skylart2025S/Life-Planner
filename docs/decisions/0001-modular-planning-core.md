# ADR 0001: Keep planning rules separate from AI interpretation

Status: proposed baseline; reassess against original detailed specs when available.

Context: chat must update several related items consistently. The user expects eventual growth, but current repository has no implementation or traffic measurements.

Decision: start with a modular application, a deterministic Python planning core, typed integration interfaces, and later transactional PostgreSQL storage. Use an AI adapter for intent interpretation and constrained recommendations. Keep provider writes in a retryable worker.

Consequences: scheduling invariants can be tested without model calls; API and UI can evolve independently. The prototype needs production persistence, concurrency, and timezone/recurrence work before release. No frontend, model, or hosting vendor is selected by this decision.

Alternatives: a service per domain agent adds coordination and consistency costs now; a model writing directly to calendars cannot reliably enforce the shared planning rules. Revisit service extraction only with measured load or team boundaries.
