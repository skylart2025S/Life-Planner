# Worker boundary — not implemented

Implement external calendar synchronization after persistence and provider selection.
Read committed outbox events, make idempotent provider writes, and record delivery/retry status.
Add bounded retries, backoff, dead-letter handling, and duplicate/out-of-order delivery tests.
Workers cannot bypass user ownership or create unconfirmed planning changes.
