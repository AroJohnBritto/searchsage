# SearchSage

SearchSage answers questions by trying three tiers of grounding, in order,
until one succeeds. The public API never reveals which tier or provider
produced an answer, it only reports a generic freshness indicator (`live`
or `general`).

## How answers are produced

1. **Tier 1**: a lightweight local heuristic decides whether the question
   needs live information (skipping obviously definitional or how-to
   questions to save latency). A single call is made either way, with a
   live search grounding tool attached only when needed.
2. **Tier 2**: if tier 1 is not configured or fails, a hosted
   knowledge-only model answers from its training data, no live search.
3. **Tier 3**: last resort. The question is used to search the web, the
   top results are scraped, the scraped text is sanitized against prompt
   injection, and a model answers using only that scraped content as
   reference.

Within each tier, transient failures are retried with backoff. Missing
configuration is never retried, that tier is skipped immediately and the
next tier is tried.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys
```

Run everything locally:

```bash
./run_all.sh
```

This starts the FastAPI backend on `http://localhost:8000` and the
Streamlit UI on its default port, pointed at that local backend.

To run the pieces separately:

```bash
uvicorn backend.main:app --reload
SEARCHSAGE_BACKEND_URL=http://localhost:8000 streamlit run app/ui.py
```

## Environment variables

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Tier 1 credential. |
| `GEMINI_MODEL` | Tier 1 model name. |
| `NVIDIA_API_KEY` | Tier 2 credential. |
| `NVIDIA_MODEL` | Tier 2 model name. |
| `OPENROUTER_API_KEY` | Tier 3 credential. |
| `APP_URL` | Public URL of this backend, sent as an outbound referer header to the tier 3 provider. Not user-facing. |
| `AUTH_ENABLED` | `true` to require `X-API-Key` on protected endpoints. Defaults to `false`. |
| `API_KEYS` | Comma-separated list of accepted API keys, used only when `AUTH_ENABLED=true`. |
| `DB_PATH` | Path to the SQLite file for sessions, history, feedback and cache. |
| `SEARCHSAGE_BACKEND_URL` | Backend URL the Streamlit UI should call. |

A tier with a missing key is simply skipped in favor of the next one. Any
subset of the three keys can be configured.

## API

All responses on `/query` and `/query/stream` are shaped as
`{answer, sources, mode, answer_id}`. `mode` is `live` when the answer
was grounded in a live search or scrape, `general` otherwise. No vendor
or provider name ever appears in a response body.

- `POST /query` — body `{question, session_id?}`. Returns the resolved
  answer.
- `GET /query/stream` — query params `question`, `session_id?`. Server-sent
  events that stream the already-resolved answer out in chunks for a
  typing effect (the tiered fallback resolves the full answer first, so
  this is not token-level provider streaming). The final event carries
  `sources`, `mode` and `answer_id`.
- `POST /session` — creates a session, returns `{session_id}`. Pass this
  back on `/query` calls to keep conversation history.
- `GET /session/{session_id}` — returns that session's message history.
- `GET /answer/{answer_id}` — public read-only share link for a
  previously generated answer, no auth required.
- `POST /feedback` — body `{answer_id, vote}` where `vote` is `up` or
  `down`.
- `GET /status` — `{tier1_configured, tier2_configured, tier3_configured}`,
  booleans only, no provider names.
- `GET /health` — liveness check.

Every response carries an `X-Request-ID` header for correlating with
server logs. Unhandled errors always return a generic message, never
internal exception text.

## Auth and rate limiting

Set `AUTH_ENABLED=true` and `API_KEYS=key1,key2` to require an
`X-API-Key` header on every endpoint except `/health` and
`/answer/{answer_id}`. Rate limiting is always on for `/query` and
`/query/stream`, keyed by API key when one was presented, by client IP
otherwise.

## Caching

Answers to context-free questions (no `session_id`) are cached by question
text in the same SQLite database, so repeated questions do not spend a
tier's quota. Answers within a session are never cached, since they depend
on conversation history and are not safe to key by question text alone.

## Notes and tradeoffs

- The in-memory rate limiter resets on process restart and does not share
  state across multiple backend instances. That is acceptable for this
  project's single-process free-tier deployment target, but would need a
  shared store (Redis or similar) behind a load balancer.
- Tier 3's scrape step is best-effort. Pages that fail to fetch or have no
  extractable paragraph text are skipped rather than surfaced as errors.
