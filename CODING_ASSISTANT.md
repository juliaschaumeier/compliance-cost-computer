# Coding Assistant Guide

## Project Focus
- CCC computes compliance costs through a 7-step workflow:
  - `summary`
  - `regulations`
  - `processes`
  - `case_groups`
  - `process_steps`
  - `effort`
  - `total_cost`

## Active Architecture (Use This)
- Backend entry point: `backend/main.py`
- Frontend entry point: `frontend/src/app/page.tsx`
- Active backend routers:
  - `backend/routers/sessions.py`
  - `backend/routers/tiles.py`
  - `backend/routers/models.py`
  - `backend/routers/regulations.py`
  - `backend/routers/processes.py`
  - `backend/routers/case_groups.py`
  - `backend/routers/process_steps.py`
  - `backend/routers/effort.py`
  - `backend/routers/costs.py`

## Session Rules (Important)
- API-facing identifier is `app_session_id` (string).
- DB-facing key is `session_id` (integer).
- Tiles and links are strictly session-scoped.
- Do not reintroduce fallback behavior for missing session IDs.

## Run-All Workflow Rules
- Start: `POST /sessions/run-all/start`
- Observe:
  - Polling endpoint: `GET /sessions/run-all/{run_id}`
  - SSE endpoint: `GET /sessions/run-all/{run_id}/events`
- Cancel: `POST /sessions/run-all/{run_id}/cancel`
- Cancellation is a true abort that stops in-flight work and keeps already completed session state.

## Frontend State Notes
- Main state lives in `frontend/src/contexts/AppContext.tsx`.
- Session tab progression derives from `frontend/src/lib/sessionStatus.ts`.
- Session menu orchestration/UI controls live in `frontend/src/components/SessionMenu.tsx`.
- Canvas behavior and tile persistence live in `frontend/src/components/GraphCanvas.tsx`.

## Model + Key Handling
- Frontend uses `GET /models/organized` only.
- API key inputs are in `frontend/src/components/ModelSelector.tsx`.
- Provider model lists are shown only when that provider key looks valid.
- Clearing a key removes it from browser storage.

## LLM Prompt/Parsing Paths
- Prompt templates: `backend/core/prompts.py`
- Unified LLM JSON parsing helpers: `backend/core/llm_json.py`
- LLM service wrapper: `backend/core/llm_service.py`

## Database
- DB setup/migrations-in-place: `backend/core/db.py`
- Default DB path: `backend/ccc.db`
- Keep integrity checks in DB and avoid duplicating the same guard logic in many routers.

## Testing
- Backend: `python3 -m pytest`
- Frontend unit tests: `npm --prefix frontend test -- --runInBand`
- Frontend lint: `npm --prefix frontend run lint -- --max-warnings=0`

## Preferred Change Style
- Keep API contracts stable; update tests with any contract changes.
- Prefer small, focused refactors over broad rewrites.
- For frontend errors:
  - user-facing: concise and actionable
  - developer-facing: lightweight debug logging
