# Compliance-Cost Computer (CCC)

CCC is a web app to estimate compliance costs for German legislation across a 7-step workflow, from law comparison to total cost.

## Stack
- Backend: FastAPI + SQLite
- Frontend: Next.js (App Router) + React + React Flow
- LLM providers: OpenAI, DeepInfra, Gemini
- Auth: built-in email + password accounts; sessions are private per user

## Deployment
- Production (Docker + Caddy TLS): see [DEPLOY.md](DEPLOY.md).
- Local run (with or without Docker): see [DEPLOY_LOCAL.md](DEPLOY_LOCAL.md).
- The quick "run without Docker" steps are below.

## Repository Layout
- `backend/main.py`: FastAPI app entry point
- `backend/core/`: DB, config, LLM service, workflow logic
- `backend/routers/`: step endpoints (`regulations`, `processes`, `case_groups`, `process_steps`, `effort`, `costs`) plus `sessions`, `tiles`, `models`
- `frontend/src/`: UI components, context, API client, tests
- `tests/`: backend tests

## Local Setup (without Docker)

The app requires authentication, so the backend needs an auth secret and a
bootstrap admin account to log in with.

### 1) Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Required for auth (login returns 500 without a secret):
export AUTH_SECRET_KEY="$(openssl rand -hex 32)"
export AUTH_COOKIE_SECURE=false          # allow the auth cookie over plain HTTP
export ADMIN_BOOTSTRAP_EMAIL=admin@example.com
export ADMIN_BOOTSTRAP_PASSWORD=changeme123   # 8+ chars

uvicorn backend.main:app --reload --port 5000
```

Backend runs on `http://localhost:5000`. These env vars can also live in a root
`.env` file (read via Pydantic settings) instead of being exported.

### 2) Frontend
From repository root:
```bash
npm run install:frontend
npm run dev
```

Or from `frontend/`:
```bash
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`. Open it and log in with the
`ADMIN_BOOTSTRAP_EMAIL` / `ADMIN_BOOTSTRAP_PASSWORD` above; as an admin you can
provision more users from the header (there is no public self-registration).

The default CORS config already allows `http://localhost:3000` → the backend on
`:5000`, so no reverse proxy is needed for local development.

## Environment
- Backend reads `.env` via Pydantic settings. See [.env.example](.env.example) for the full list.
- LLM provider keys:
  - `OPENAI_API_KEY`
  - `DEEPINFRA_API_KEY`
  - `GEMINI_API_KEY`
- Authentication:
  - `AUTH_SECRET_KEY` (required; signs the auth cookie/JWT)
  - `AUTH_COOKIE_SECURE` (default `false`; set `true` behind TLS)
  - `AUTH_TOKEN_TTL_MINUTES` (default `1440`)
  - `ADMIN_BOOTSTRAP_EMAIL` / `ADMIN_BOOTSTRAP_PASSWORD` (first admin, seeded on startup)
  - `AUTH_ALLOWED_EMAILS` (optional comma-separated allowlist for provisioning)
  - `CORS_ALLOW_ORIGINS` (comma-separated; defaults to localhost dev origins, empty for same-origin prod)
- Optional:
  - `DEFAULT_MODEL`
  - `DB_PATH`
  - `REGULATIONS_PATH`
  - `LLM_CONSOLE_ENABLED` (default: `true`; set to `false` to disable monitor endpoints)
  - `LLM_STREAM_DEBUG_ENABLED` (controls stream debug event capture)

Frontend can override API base URL with:
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_ENABLE_LLM_CONSOLE` (`true`/`false`; default: `true`)

## Testing

The test suites do not need the auth env vars — the backend `tests/conftest.py`
overrides authentication and seeds a test user automatically.

### Backend tests
```bash
python3 -m pytest
```

### Frontend tests
```bash
npm --prefix frontend test -- --runInBand
```

### Frontend lint
```bash
npm --prefix frontend run lint -- --max-warnings=0
```

## Authentication & Ownership
- Accounts are email + password; there is no public self-registration. The
  bootstrap admin (from env) provisions further users via the header UI.
- Requests are authenticated with an httpOnly cookie; every app endpoint requires it.
- Sessions are private per user: `app_session_id` is server-generated, `GET /sessions`
  is scoped to the caller, and accessing another user's session returns 404.

## Core Concepts
- `app_session_id`: user-facing session identifier (server-generated, owned by a user).
- `session_id`: internal integer DB key.
- Tile operations are strictly session-scoped (`app_session_id` is required).
- Workflow state is persisted in DB and mirrored in frontend session state.

## Session Orchestration
- Start full run: `POST /sessions/run-all/start`
- Track run:
  - Poll: `GET /sessions/run-all/{run_id}`
  - Stream (SSE): `GET /sessions/run-all/{run_id}/events`
- Cancel run: `POST /sessions/run-all/{run_id}/cancel`
- Cancellation performs a true abort and reverts to the last completed step baseline.

## Models
- Frontend calls `GET /models/organized`.
- Provider sections are shown only when a valid key is set for that provider.
- API keys entered in the UI are kept in browser storage and removed when fields are cleared.

## Notes
- Fonts are self-hosted via `@fontsource`, so `next build` does not fetch Google Fonts and works offline.
