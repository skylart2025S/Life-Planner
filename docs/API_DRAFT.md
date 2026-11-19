# API contract — design only

No HTTP server or authentication exists yet. These routes define the intended next boundary.

| Route | Input | Result |
| --- | --- | --- |
| `GET /v1/plan?from=...&to=...` | Bounded date interval | Owner's plan items, timezone, revision |
| `POST /v1/chat` | Message and conversation ID | Clarification or proposal preview |
| `POST /v1/proposals` | `move_item` command with item ID and aware new start | Proposal ID, base revision, changes, explanation |
| `POST /v1/proposals/{id}/apply` | Explicit confirmation and idempotency key | Applied revision and sync status |
| `POST /v1/changes/{id}/undo-proposal` | Change ID | New proposal, validated against the current plan |

Derive owner identity from authentication, never body fields. Validate request size, time ranges, allowed commands, and timestamps before domain execution. Map malformed commands to 400, missing authentication to 401, inaccessible/missing resources to 404, conflicts/stale proposals to 409, quotas to 429, and temporary dependency failures to 503. Do not leak other users' IDs or event titles in errors.

Example command:

```json
{"type":"move_item","item_id":"gym","new_start":"2026-11-26T18:00:00-05:00"}
```

The PostgreSQL storage layer now provides durable retry receipts scoped to owner/plan/key, transactional apply, audit history, and rollback tests. An apply retry returns the original applied revision even if subsequent changes have occurred. Before hosting, implement authentication, HTTP request validation/error mapping, proposal expiration, connection limits/timeouts, and retention/deletion policy.
