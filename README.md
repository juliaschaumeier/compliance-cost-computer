# Compliance-Cost Computer (CCC)

CCC is a web app to estimate compliance costs for German legislation across a 7-step workflow, from law comparison to total cost.

## Stack
- Backend: FastAPI + SQLite
- Frontend: Next.js (App Router) + React + React Flow
- LLM providers: OpenAI, DeepInfra, Gemini

## Repository Layout
- `backend/main.py`: FastAPI app entry point
- `backend/core/`: DB, config, LLM service, workflow logic
- `backend/routers/`: step endpoints (`regulations`, `processes`, `case_groups`, `process_steps`, `effort`, `costs`) plus `sessions`, `tiles`, `models`
- `frontend/src/`: UI components, context, API client, tests
- `tests/`: backend tests

## Local Setup

### 1) Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 5000
```

Backend runs on `http://localhost:5000`.

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

Frontend runs on `http://localhost:3000`.

## Environment
- Backend reads `.env` via Pydantic settings.
- Supported keys:
  - `OPENAI_API_KEY`
  - `DEEPINFRA_API_KEY`
  - `GEMINI_API_KEY`
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

## Core Concepts
- `app_session_id`: user-facing session identifier (used by frontend and API).
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
- Legacy modules are kept under `backend/legacy/` for reference/testing, but current app flow uses `backend/main.py` + `backend/routers/*`.
- If `next build` fails offline due to Google Fonts fetch, run development server or provide network access for font fetch at build time.
