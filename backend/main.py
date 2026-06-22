from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any
import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from backend.core import auth as auth_core
from backend.core import db
from backend.core import llm_trace
from backend.core.config import settings
from backend.core.request_context import bind_request_context, reset_request_context
from backend.routers import (
    auth,
    models,
    regulations,
    tiles,
    sessions,
    processes,
    case_groups,
    process_steps,
    effort,
    costs,
)


app = FastAPI()
logger = logging.getLogger("uvicorn.error")

_MAX_JSON_LOG_BYTES = 65_536
_QUIET_PATHS = {"/health"}

_cors_allow_origins = [
    origin.strip()
    for origin in (settings.cors_allow_origins or "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


def _safe_str(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text if text else "-"


async def _extract_json_dict(request: Request) -> dict[str, Any] | None:
    if request.method not in {"POST", "PUT", "PATCH"}:
        return None
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return None

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > _MAX_JSON_LOG_BYTES:
                return None
        except ValueError:
            pass

    try:
        raw = await request.body()
    except Exception:
        return None

    if not raw or len(raw) > _MAX_JSON_LOG_BYTES:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


@app.middleware("http")
async def log_backend_communication(request: Request, call_next):
    started = perf_counter()
    path = request.url.path
    request_id = uuid.uuid4().hex[:12]
    payload = await _extract_json_dict(request)
    payload_keys = ",".join(sorted(payload.keys())) if payload else "-"
    app_session_id = request.query_params.get("app_session_id")
    if not app_session_id and payload:
        app_session_id = payload.get("app_session_id")
    model = request.query_params.get("model")
    if not model and payload:
        model = payload.get("model")
    token = bind_request_context(
        request_id=request_id,
        route_method=request.method,
        route_path=path,
        app_session_id=(str(app_session_id).strip() if app_session_id else None),
    )

    trace_header = request.headers.get("x-llm-trace", "").strip().lower()
    trace_enabled = llm_trace.trace_enabled_by_env() or trace_header in {"1", "true", "yes", "on"}
    trace_token = None
    if trace_enabled:
        trace_token = llm_trace.start_run(
            request_id=request_id,
            route_method=request.method,
            route_path=path,
            app_session_id=(str(app_session_id).strip() if app_session_id else None),
        )

    response = None
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (perf_counter() - started) * 1000
        logger.exception(
            "API %s %s -> 500 %.1fms | req=%s client=%s session=%s model=%s body_keys=%s",
            request.method,
            path,
            elapsed_ms,
            request_id,
            _safe_str(request.client.host if request.client else None),
            _safe_str(app_session_id),
            _safe_str(model),
            payload_keys,
        )
        raise
    finally:
        if trace_token is not None:
            try:
                llm_trace.flush_run(
                    trace_token,
                    status_code=(response.status_code if response is not None else 500),
                )
            except Exception:
                logger.exception("Failed to flush LLM trace for req=%s", request_id)
        reset_request_context(token)

    elapsed_ms = (perf_counter() - started) * 1000
    log_fn = logger.debug if path in _QUIET_PATHS else logger.info
    log_fn(
        "API %s %s -> %s %.1fms | req=%s client=%s session=%s model=%s body_keys=%s",
        request.method,
        path,
        response.status_code,
        elapsed_ms,
        request_id,
        _safe_str(request.client.host if request.client else None),
        _safe_str(app_session_id),
        _safe_str(model),
        payload_keys,
    )
    response.headers["x-request-id"] = request_id
    return response


@app.on_event("startup")
def startup() -> None:
    db.ensure_db()
    auth_core.ensure_bootstrap_admin()
    db.clear_all_session_activities()


# Authentication is required on every application router; session-scoped routers
# additionally enforce per-user ownership. `require_session_owner` itself depends
# on `get_current_user`, so the owner gate also covers authentication.
from fastapi import Depends  # noqa: E402
from backend.core.auth import get_current_user  # noqa: E402
from backend.routers._llm_router_utils import require_session_owner  # noqa: E402

_auth_only = [Depends(get_current_user)]
_owner_gate = [Depends(require_session_owner)]

app.include_router(auth.router)
# tiles and costs only ever operate on an existing session, so the owner gate
# (which requires the session to already exist and be owned) fits the whole router.
app.include_router(tiles.router, dependencies=_owner_gate)
app.include_router(costs.router, dependencies=_owner_gate)
app.include_router(models.router, dependencies=_auth_only)
# The remaining routers expose workflow-step endpoints that create the session on
# first use (owned by the caller via ensure_session_or_400) alongside read/edit
# endpoints; ownership is enforced inside each handler / per-endpoint dependency.
app.include_router(regulations.router, dependencies=_auth_only)
app.include_router(processes.router, dependencies=_auth_only)
app.include_router(case_groups.router, dependencies=_auth_only)
app.include_router(process_steps.router, dependencies=_auth_only)
app.include_router(effort.router, dependencies=_auth_only)
app.include_router(sessions.router, dependencies=_auth_only)


@app.get("/")
async def root() -> dict:
    return {"message": "CCC backend API"}


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy"}
