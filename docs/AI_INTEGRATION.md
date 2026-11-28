# AI interpretation integration — LP-104A1

The provider-neutral service in `life_planner/intent.py` interprets one request against an immutable, authorized plan snapshot. An optional OpenAI Responses adapter implements the provider protocol; browser chat and live configuration remain disconnected. Controlled providers in tests validate the integration contract; they do not demonstrate language understanding, prompt-injection resistance of a model, or recommendation quality.

## Caller and provider contract

A trusted caller constructs `IntentContext(owner_id, plan_id, revision, timezone, now, items)` after authenticating and reading the complete authorized plan. Context validates ownership, IDs, revision, timezone, intervals and dependency structure. `interpret(provider, message, context)` calls the asynchronous `IntentProvider.complete(request)` once. No database connection or mutation capability is passed to the provider.

`ProviderRequest` contains the versioned `intent-v1` instructions, user message and serialized calendar context. Context includes event IDs, titles, kinds, intervals, fixed flags and dependencies, plus timezone and current time. Internal owner ID, plan ID and revision are omitted from model context and bound to the returned `IntentResult` by trusted code. Event titles and user messages may themselves contain private information; a future live adapter must honor the approved data-sharing and retention policy.

The adapter returns exactly one JSON object:

```json
{"type":"move","item_id":"gym","new_start":"2026-11-28T18:00:00-05:00"}
```

Or `{"type":"clarification","question":"What time should I move it to?"}` or `{"type":"unsupported","reason":"This request is not supported yet."}`. Unknown fields, duplicate JSON keys, unknown IDs, invalid dates and malformed output fail closed. The service uses a disposable deterministic planner to reject conflicting, fixed or dependent-item moves. A valid move is a typed intent, not a persisted proposal or permission to apply it. Questions and reasons remain untrusted text: render as text, never HTML or instructions.

## Bounds and failures

Initial engineering limits: 4,000 message characters, 500 items, 64 KiB serialized request, 16 KiB provider output, 500-character clarification/reason and at most 15 seconds per call. Oversized or invalid caller input fails before the provider runs. Provider errors are sanitized; failure codes distinguish timeout, provider error, invalid output and invalid move. Caller cancellation propagates, and there are no automatic retries or fallback answers disguised as AI.

The async deadline is cooperative. A real adapter must use cancellable I/O, set transport deadlines and cap response bytes while reading. This layer cannot forcibly stop an adapter that blocks the event loop or suppresses cancellation. No token spending, distributed rate limiting or measured cost budget is implemented here.

## Required before connecting live AI

1. Configure and live-test the optional OpenAI adapter (or implement another provider) with credentials outside source control/chat and an approved spending limit. The user chose to build the integration before selecting a provider; no model or paid usage is activated by this code.
2. Add atomic expected-revision checking when converting the intent to a stored proposal. Existing storage proposal creation does not accept that revision yet; a separate read/check followed by propose is race-prone and is not sufficient.
3. Connect authenticated chat and clarification state to the UI, render before/after changes, and preserve explicit user confirmation before apply. Refresh/session recovery and cancellation must not apply a stale result.
4. Run reviewed, held-out model evaluations for ambiguous events/dates, missing times, DST, malicious event titles, malformed outputs, unsupported requests, ownership, latency and cost. Contract tests do not close this gate.
5. Add grounded outfit/meal context and recommendation validation in their own slices; this service supports calendar moves only.

## Optional OpenAI adapter

`life_planner/openai_intent.py` supplies `OpenAIIntentProvider(api_key, model, max_output_tokens=512)`. Both the server-side key and model are explicit configuration; there is no default model, automatic activation or credential discovery. The provider protocol remains replaceable. The adapter uses the [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create) with a strict [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses) schema. The nested `intent` object is unwrapped before the provider-neutral validation runs.

It targets only the official HTTPS endpoint, requests `store: false`, enables no tools and follows no redirects. It makes one request with a 15-second cooperative/transport deadline; no retry. A fresh async client closes on success, failure or cancellation. The streamed response envelope is limited to 128 KiB and text to 16 KiB. Identity encoding is requested and compressed responses are rejected before decoding. Output tokens are bounded to an explicitly configured value between 64 and 2,048. These limits do not substitute for a per-account spending budget or verified provider retention policy.

Refusals, incomplete responses, unexpected tool output, malformed JSON, duplicate keys and multiple text results fail closed. Errors never return raw provider bodies or credentials. Offline transport tests verify these behaviors; no request has been sent to a live model. Model availability, schema acceptance for the selected model, quality, latency and cost require live evaluation.

A trusted server integration can construct the adapter from securely configured environment values and call `interpret` with an authorized context:

```python
import os
from life_planner.intent import interpret
from life_planner.openai_intent import OpenAIIntentProvider

provider = OpenAIIntentProvider(
    api_key=os.environ["OPENAI_API_KEY"],
    model=os.environ["PLANNER_AI_MODEL"],
)
# Call only after live use and spending are approved.
# context must be an authorized complete IntentContext, not browser-supplied ownership.
result = await interpret(provider, message, context)
```

This is an integration example, not a public endpoint. Keep keys server-side. Do not paste them into chat, browser forms or repository files. Connecting this to the planner still requires the revision, session, quota and UI gates above.
