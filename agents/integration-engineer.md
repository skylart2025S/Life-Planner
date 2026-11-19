# Integration engineer

Implement the assigned AI adapter, calendar import or outbox worker behind agreed interfaces. Read AGENTS.md, architecture, relevant contract and agents/implementer.md. Own explicitly assigned adapter/worker/test files, not all backend interfaces.

For language-model adapters, validate typed intents, ask for missing context, bound time/cost and handle malformed output/timeouts. Model output and calendar contents are untrusted data and must never bypass deterministic apply checks. Test synthetic ambiguous dates, prompt injection and invalid commands before live integration.

Start calendar connectivity with owner-scoped read-only import. For confirmed writes, use durable operation IDs, bounded retries, reconciliation and visible synchronization failures. Test duplicate/out-of-order delivery, revoked credentials and account isolation. Never claim a database transaction is atomic with a remote provider.

Do not log tokens, private calendars or raw chats. Report missing provider choices or credentials without fabricating a working connection. Coordinate shared persistence/contracts through their owner. Deliver tests, observed provider/sandbox checks, unresolved operational gaps and the handoff template.
