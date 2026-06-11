# Coding Assistant Guide

## Project Workflow
- CCC computes compliance costs through a 7-step workflow:
  - `summary`
  - `regulations`
  - `processes`
  - `case_groups`
  - `process_steps`
  - `effort`
  - `total_cost`
- EA editing is a post-step capability (outside run-all): saves trigger recompute, and no-op updates are rejected.

## Architecture (Active)
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

## Key Endpoints (By Router)
- `sessions`:
  - `POST /sessions`
  - `GET /sessions`
  - `GET /sessions/status`
  - `POST /sessions/undo`
  - `POST /sessions/run-all/start`
  - `POST /sessions/run-all/{run_id}/cancel`
  - `GET /sessions/run-all/{run_id}`
  - `GET /sessions/run-all/{run_id}/events`
  - `GET /sessions/pay-rates`
  - `POST /sessions/pay-rates`
  - `GET /sessions/edit-audit`
  - `GET /sessions/llm-monitor` (dev/debug)
  - `GET /sessions/llm-monitor/events` (dev/debug)
  - `GET /sessions/llm-monitor/stream/{attempt_id}` (dev/debug)
- `tiles`:
  - `GET /tiles`
  - `POST /tiles/rebuild`
- `models`:
  - `GET /models/organized`
- `regulations`:
  - `POST /regulations/summary`
  - `POST /regulations/identify`
- `processes`:
  - `POST /processes/compile`
- `case_groups`:
  - `POST /case-groups/develop`
  - `GET /case-groups/editable`
  - `POST /case-groups/bulk-update`
- `process_steps`:
  - `POST /process-steps/analyze`
  - `GET /process-steps/editable`
  - `POST /process-steps/bulk-update`
- `effort`:
  - `POST /effort/calculate`
- `costs`:
  - `POST /costs/compute`

## Run-All Rules
- Run-all executes steps in the defined 7-step order.
- Run-all is only a sequencer: apart from skipping completed steps, it must have the same effect as the user pressing each step button in order.
- Run-all must not contain step-specific business logic that differs from manual execution; shared step runners/services should own step behavior.
- Completed steps are skipped; steps are re-run only after undo (revert/reset) of the corresponding state.
- Start: `POST /sessions/run-all/start`
- Observe:
  - Polling: `GET /sessions/run-all/{run_id}`
  - SSE: `GET /sessions/run-all/{run_id}/events`
- Cancel: `POST /sessions/run-all/{run_id}/cancel`
- Cancellation is a true abort: in-flight work stops, already completed state remains.

## Session + State Rules
- API-facing identifier is `app_session_id` (string).
- DB-facing key is `session_id` (integer).
- Tiles and links are strictly session-scoped.
- Do not reintroduce fallback behavior for missing session IDs.

## Prompt/LLM Paths
- Prompt templates: `backend/core/prompts.py`
- JSON parsing helpers: `backend/core/llm_json.py`
- LLM provider wrapper: `backend/core/llm_service.py`
- Step 6 (`effort`) issues paired prompt calls in parallel (`cases_calculation` + `effort_calculation`).

## Frontend Integration Points
- Main app state: `frontend/src/contexts/AppContext.tsx`
- API client contract: `frontend/src/lib/api.ts`
- EA editor shell: `frontend/src/components/ea_edit/EaEditDrawerShell.tsx`

## Database + Migrations
- DB setup and in-place migration helpers: `backend/core/db.py`
- Default DB path: `backend/ccc.db`
- Keep integrity checks in DB and avoid duplicating identical guards across routers.
- Keep migration helpers in `db.py` unless they become too numerous/complex.
- Migration helpers must be clearly marked in docstrings/comments as migration-only.

## Layering Pattern
- Routers: request validation and workflow orchestration.
- Core services/modules: prompt rendering, LLM calls/parsing, cross-step orchestration logic.
- DB layer (`core/db.py` and related DB modules): persistence, integrity constraints, transaction boundaries.

## Definition of Done
- API/schema changes include corresponding contract updates:
  - tests
  - API client usage
  - docs where relevant
- Run narrow relevant tests first, then broader suite as needed.
- Minimum checks:
  - Backend: `python3 -m pytest`
  - Frontend tests: `npm --prefix frontend test -- --runInBand`
  - Frontend lint: `npm --prefix frontend run lint -- --max-warnings=0`

## Change Style (Required)
- Implement first, then perform a focused cleanup/refactor pass in the same work item.
- Keep new code aligned with existing style and naming conventions.
- Keep changes minimal and maintainable; avoid unnecessary codebase growth.
- Add docstrings/comments for non-trivial functions and intent-sensitive behavior.
- Prefer small, focused refactors over broad rewrites.

## Anti-Patterns (Avoid)
- Silent fallback paths that hide failures.
- Duplicated validation/guard logic across multiple layers.
- Undocumented compatibility/migration branches.
- Broad rewrites without focused regression tests.
