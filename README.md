# Codewatch - AI Code Reviewer

A rebuilt version of the original Streamlit + single-file FastAPI project.
Same core idea — OpenAI → Ollama → offline fallback — but the backend is now
structured like a real service, and the frontend is a proper Next.js app
instead of Streamlit.

## What changed and why

**Backend**
- **Package structure.** `main.py` + 6 flat files → `app/{core,schemas,services,prompts,api}`.
  Each module has one job (config, logging, caching, circuit breaking, providers, orchestration).
- **Structured findings instead of four string lists.** The old `CodeReviewResponse` had
  `bugs: list[str]`, `security_risks: list[str]`, etc. — the frontend could never sort,
  filter, or link a finding to a line. Now every finding is a `Finding` object with
  `category`, `severity`, `title`, `description`, and an optional `line`.
- **A real fallback, not a demo trick.** The original fallback special-cased one example
  function (`calculate_total`) to fake a "forced improvement" and otherwise left code
  untouched while claiming it had been improved. The new `static_analyzer.py` does real
  `ast`-based analysis for Python (bare `except`, mutable default args, `eval`/`exec`,
  `== None`, `range(len(...))` loops, credentials passed to `print`) and only applies
  changes it can justify as unambiguously safe.
- **Circuit breaker per provider.** If OpenAI has failed 3 times in a row, requests skip
  straight to Ollama for a cooldown window instead of paying its full timeout every time.
- **Caching.** Identical `(code, language)` requests are served from an in-memory TTL/LRU
  cache instead of re-spending an LLM call — useful since people iterate on the same
  snippet in the UI.
- **Rate limiting + request IDs + structured JSON logs.** Every log line and API response
  carries a request ID; logs are single-line JSON so they're greppable/ingestible as-is.
- **Real tests.** `tests/test_api.py` covers the API surface, the static analyzer's actual
  detections, the cache, and the circuit breaker — 9 tests, all passing.

**Frontend**
- Replaced Streamlit with a Next.js 15 + TypeScript + Tailwind app: a Monaco code editor,
  a findings panel grouped and colored by severity with line-jump buttons, a real diff
  viewer, and a "provider chain" strip that visualizes which provider actually answered
  the request (and which were skipped/failed) — surfacing the system's own resilience
  instead of hiding it behind a single "used_model" string.

## Running it

### Backend
```bash
cd backend
cp .env.example .env   # fill in OPENAI_API_KEY if you have one
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs
Tests: `pytest tests/ -v`

### Frontend
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```
App: http://localhost:3000

### Or both, with Docker
```bash
docker compose up --build
```
This also starts a local Ollama container. Pull a model into it once with:
```bash
docker compose exec ollama ollama pull llama3
```

## Architecture

```
Next.js UI  ──POST /review──>  FastAPI
                                  │
                          ReviewOrchestrator
                    (cache check → provider chain → cache write)
                                  │
                ┌─────────────────┼─────────────────┐
          OpenAIProvider    OllamaProvider    StaticAnalysisProvider
          (circuit-breaker) (circuit-breaker)   (always succeeds)
```

Each provider implements the same `review(code, language) -> CodeReviewResponse`
interface, so the orchestrator doesn't know or care which one it's calling —
adding a fourth provider (say, Anthropic) means writing one new class and adding
one line to `ReviewOrchestrator._providers`.

## Notable trade-offs / next steps
- The in-memory cache, breaker, and rate limiter are process-local by design (no Redis
  dependency) — fine for a single instance; swap `TTLCache`/`CircuitBreaker` internals for
  a Redis-backed version if you need this to work across multiple API replicas.
- The static-analysis fallback is intentionally conservative: it will never claim to have
  fixed something it can't safely prove is a fix. That's a deliberate trust decision, not
  a missing feature.
