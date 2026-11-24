# Lyftr AI

Lyftr AI is a single-session-at-a-time chat workspace with a FastAPI service, LiteLLM Router deployments, SQLite conversation storage, exact-match in-process LiteLLM caching, and a React/Vite interface. It uses one backend worker so the local cache stays consistent. The browser creates a fresh session ID each page load; history is never restored automatically.

## 1. Live URLs

No public deployment has been created. Frontend and backend URLs are pending deployment and external credentials.

## 2. Run locally: with Docker and without

### Prerequisites

- Docker Desktop and Docker Compose for the container workflow.
- Python 3.12 and Node.js 22 for the non-Docker workflow.
- Two valid provider API keys supported by the selected LiteLLM model.

Copy `.env.example` to `.env`, replace both placeholder credentials, and set `LLM_MODEL` to a LiteLLM model identifier supported by that provider. Never commit `.env`.

### Docker

From the repository root:

```sh
make up
```

Open the frontend at http://localhost:3000 and the backend at http://localhost:8000. SQLite lives in the named `lyftr-data` volume mounted at `/data`. Stop the services with `make down`.

### Without Docker

Backend (from `backend/`):

```sh
python -m venv .venv
# Activate .venv, then:
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (from `frontend/`):

```sh
npm install
npm run dev -- --port 3000
```

The Vite development server uses `VITE_API_BASE_URL` from the environment or defaults to `http://localhost:8000`.

### Repository structure

```text
backend/app/             FastAPI application, config, SQLAlchemy models and routes
backend/app/services/    LiteLLM calls, Router deployments and response cache
backend/tests/           Deterministic mocked API tests
frontend/src/             React workspace, typed API client and UI
frontend/src/components/  Shared UI components
docker-compose.yml        Local full-stack services and persistent SQLite volume
```

## 3. Design decisions: key fallback, caching, SQLite session storage

- Two independently configured API keys are mapped to distinct LiteLLM Router deployments. A request tries them in order; if one errors, the next configured deployment gets its own Router call. The optional failure simulation skips a deployment for that request only.
- LiteLLM's in-process `Cache(type="local")` stores response objects. Its lookup key is a SHA-256 digest of the configured model and the complete ordered message list, which includes system prompt, history and latest message, and excludes session ID. This allows identical first turns in separate sessions to hit the same response while preserving conversational context.
- Cache hits replay the cached output and usage, label the response `LLM_CACHE`, and report no provider key or fallback attempts. Cache entries share one process and are lost when the backend restarts; deploy one worker initially.
- SQLAlchemy uses SQLite and creates the `sessions` and `messages` tables on application startup. Only successful user/assistant exchanges are committed. The public history route omits system prompts and returns assistant metadata.
- The screenshot and `prompt-bond-source.txt` named in the implementation brief were not present in the supplied workspace/attachments. The chat is implemented in a custom ambient scene wrapper; the original Prompt Bond component, its MIT notice, and exact screenshot match remain dependent on providing those reference files.

## 4. Verification: how to see failover, cache hits and per-message token usage

Start Docker with configured keys and check:

```sh
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"session_id":"demo-a","message":"Explain API caching in one sentence."}'
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"session_id":"demo-b","message":"Explain API caching in one sentence."}'
curl http://localhost:8000/sessions/demo-a/messages
```

The second identical first turn is eligible for an `LLM_CACHE` response. To demonstrate fallback, use a new prompt to avoid a prior cache hit:

```sh
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=429" -d '{"session_id":"fallback-demo","message":"Give a fresh random color name."}'
```

It should report `key_2` and one fallback attempt. Simulate all deployments failing with `X-Simulate-Failure: *=429`; the endpoint should return JSON `detail` with HTTP 503 and should not save that exchange. This hook is enabled by default in `.env.example`; disable it in production if desired.

Each assistant message renders its own source, model, latency, input tokens, output tokens, key ID and fallback count. Token values come from LiteLLM's provider response; tests mock them deterministically. No real provider test has been run in this workspace.

### Tests

From `backend/`, run:

```sh
pytest
```

The tests use mocked provider results and cover health fields/key count, schema validation, history isolation, assistant metadata, simulated fallback and all-key failure. They do not prove real credentials work or validate a live LiteLLM response cache.

### Demo recording checklist (2-3 minutes)

1. Open the dashboard and send a real prompt.
2. Point out per-message metadata.
3. Start a fresh session and resend the same first prompt to show cache behavior.
4. Ask a follow-up that relies on previous context.
5. Send the fallback request header using a new prompt and show `key_2`.
6. Send `*=429` and show the 503 JSON response.
7. Open `/health` and the session message history endpoint.

## 5. Setup Used: your editor and AI tools

Implementation prepared in the Lyftr AI workspace with Codex. Repository setup and code are local; no live deployment or real-key validation has been performed.

## 6. Bonus features (if any): what you added beyond the requirements and why

- Theme toggle and a per-session system-prompt editor for workspace customization.
- Animated status indicators, reduced-motion handling, mobile infrastructure summary and helpful starter prompts.
- A named SQLite Docker volume so conversation data survives container recreation.

## API examples

```sh
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"session_id":"s-demo","message":"What is the capital of France?"}'
curl http://localhost:8000/sessions/s-demo/messages
```

The application has exactly three API routes: `GET /health`, `POST /chat`, and `GET /sessions/{session_id}/messages`. FastAPI docs and OpenAPI routes are disabled.

## Deployment

Build the frontend static image with the public API URL in `VITE_API_BASE_URL` (or `VITE_API_BASE_URL` build arg) and configure `ALLOWED_ORIGINS` to the frontend origin. Deploy the backend with a persistent disk mounted at `/data`, `DATABASE_URL=sqlite:////data/app.db`, both real provider credentials, and one worker. Keep public deployment URLs marked pending until deployment and endpoint checks succeed.

For Render, connect the public Git repository containing this project and create a Blueprint from `render.yaml`. Enter `LLM_API_KEYS` and `LLM_MODEL` in the prompted secret fields. After the service deploys, copy its assigned `onrender.com` origin into the frontend's `VITE_API_BASE_URL` build setting and into the backend's `ALLOWED_ORIGINS`, then redeploy both tiers. The Render disk uses the Starter plan and persists SQLite at `/data`.
