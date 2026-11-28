# Authenticated planning API — local foundation

FastAPI exposes the PostgreSQL planner through typed, owner-scoped routes. The API
verifies real signed access tokens against an explicitly configured local public
JWKS file. No identity provider or live account is connected. It never issues
tokens or accepts a user ID supplied in request bodies/alternate identity headers.

## Run locally

Install the repository's dependencies, start PostgreSQL, and run migrations using
the storage instructions first. Startup does **not** migrate the database.

Set `DATABASE_URL`, `AUTH_ISSUER`, `AUTH_AUDIENCE`, and `AUTH_JWKS_PATH` in the process
environment. The last value names a trusted local JSON JWKS file; do not commit
credentials or private signing keys. Missing/invalid configuration or unusable
keys prevent application creation.

```sh
.venv/bin/uvicorn apps.api.main:create_app_from_env --factory --host 127.0.0.1 --no-access-log
```

The environment factory calls `create_app(Settings(database_url, issuer,
audience, jwks_path))`. Dependency-injected settings are trusted startup objects,
never request parameters. The example disables server access logs to avoid
recording user-supplied URL contents. The application itself does not log bodies,
tokens, items, exception text, or database credentials.

## Verified identity contract

- RS256 only with RSA public keys of at least 2048 bits and unique nonempty `kid`.
- Token `typ` must be `at+jwt` or `application/at+jwt`; ID tokens are rejected.
- Required claims: `iss`, `aud`, `sub`, `exp`, `iat`, `client_id`, `jti`.
  Issuer matches exactly; audience is this API's configured value or an array
  containing that value. Subject/client ID/token ID must be nonempty strings.
- Expiration and issuance, plus optional `nbf`, are nonnegative integer NumericDates;
  no clock leeway, future issuance, early use, or expired token is accepted.
- Unknown/duplicate signing key IDs, token-supplied key URLs/keys, unsupported
  critical headers, duplicate JSON members, and unsigned/wrong-algorithm tokens
  are rejected. There is no request-controlled key discovery or network fetch.
- Owner is `oidc:` plus SHA-256 of canonical JSON `[verified issuer, verified sub]`.
  Internal owner IDs are omitted from item responses.

Keys are loaded once per application instance. Rotation requires replacing the
trusted local file and restarting; keep old public keys during the intended overlap.
There is no automatic refresh. Live onboarding still requires a compatible issuer,
registered audience, user-grant/scopes policy and account lifecycle decisions.
Fixtures model a user-only issuer: the generic verifier cannot distinguish a human
token from a machine token when an issuer gives both the same documented claims.

## Routes

Public `GET /health` returns process liveness only. OpenAPI/interactive documentation
are public and contain schemas, not user data. All `/v1` operations require exactly
one `Authorization: Bearer <access token>` header.

| Route | Request | Success |
| --- | --- | --- |
| `GET /v1/plans?limit=20&after=...` | Optional page size and exclusive plan-ID cursor | 200 `{plans:[{plan_id,revision}],next_after}` |
| `POST /v1/plans/{plan_id}` | `{items:[{id,title,kind,start,end,linked_to?,fixed?}]}` | 201 initial revision/items and Location |
| `GET /v1/plans/{plan_id}?from=...&to=...` | Required aware interval, maximum 31 days | 200 revision plus overlapping items |
| `POST /v1/plans/{plan_id}/proposals` | `{type:"move_item",item_id,new_start}` | 201 proposal ID, base revision, before/after changes and explanation |
| `POST /v1/plans/{plan_id}/proposals/{proposal_id}/apply` | `{confirmed:true}` and one `Idempotency-Key` header | 200 original applied revision |

Discovery returns only the authenticated owner's plan IDs and current revisions, never
item content, owner IDs or a global total. `limit` defaults to 20 and accepts canonical
decimal integers 1–100. `after` uses the existing ID format; omit it for the first
page. Unknown or duplicate query parameters fail. Pass a non-null `next_after` as
the next page's `after`. Null means the current page exhausted the matching rows.
The database's plan-ID ordering is used for both comparison and sorting. A cursor
is just an exclusive boundary; it need not refer to a real or owned plan. Discovery
never looks up its existence under another owner. Pages are not a frozen snapshot:
new plans sorting before the cursor require restarting the list. Revisions are
informational until the selected plan is read and a proposal validated. The query
reads at most `limit + 1` metadata rows, without loading items or locking plan rows.
This endpoint enables a future saved-plan picker; the browser is not connected yet.

Item outputs use UTC timestamps. Unknown body fields are rejected. Recreating an
existing owner's plan returns 409 without overwriting it. Proposal creation does
not alter the schedule. Apply requires the actual JSON boolean `true`; strings
or integers cannot confirm. Idempotency is scoped to owner, plan and key. Retry
with the same key after an uncertain response; its original revision is returned
even after subsequent changes. A different key for an already applied proposal
also cannot duplicate schedule/audit/outbox effects.

## Input bounds and errors

- Body maximum 64 KiB, counted while consuming ASGI chunks before side effects,
  even with no/incorrect Content-Length. JSON requests only for POST; duplicate
  JSON members are rejected. A 10-second total body-read deadline returns 408 and
  releases the request's capacity slot. Authorization header maximum 8 KiB.
- IDs use 1–128 ASCII letters/digits/underscore/hyphen. Idempotency keys use 1–128
  visible ASCII characters with no whitespace. Duplicate auth/key headers fail.
- At most 500 items; titles 1–200 characters; kinds 1–32. Strict JSON booleans.
- Input timestamps must be RFC3339 strings with explicit offset, second precision
  (up to six fractional digits), and UTC year 2000–2100. They resolve to instants;
  this interface does not accept unresolved local timezone names.
- Request concurrency is capped at 16 per app instance, returning 503 on saturation.
  Database connections time out after 5 seconds, lock waits after 2 seconds, and
  statements after 5 seconds. Synchronous storage runs in FastAPI worker threads.
- Private responses use `Cache-Control: no-store`; server-generated request IDs
  appear in response headers and sanitized error envelopes. No CORS middleware.

Errors use `{error:{code,message,request_id}}` without echoing submitted private
values: malformed/invalid requests 400, failed auth 401, unknown/inaccessible
resources 404, incomplete-body deadline 408, known scheduling/revision/key conflicts 409, oversized bodies 413,
wrong content type 415, unavailable database/capacity 503, unexpected integrity or
programming failures 500. A 503 apply result can have an uncertain commit outcome;
retry with the original key. Unknown storage errors are never presented as ordinary
user conflicts. OpenAPI describes the same 400 validation contract.

## Deliberate limitations

Window filtering loads a full storage snapshot first; it is not database pagination.
API-created plans are capped; preexisting/imported oversized plans are outside this
slice's supported contract. The concurrency limit is not a distributed/per-user
rate limit. Connection pooling, remote JWKS rotation, RLS, deployment controls,
model interpretation, chat/undo endpoints and calendar synchronization remain
future work. Outbox creation does not mean delivery. This local implementation and
generated-key tests are not evidence that production identity policy is configured.
