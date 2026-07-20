from __future__ import annotations

from typing import Awaitable, Callable, TypeVar

from fastapi import Depends, HTTPException, Request

from backend.core import db
from backend.core.auth import ApiKeys, AuthUser, get_current_user
from backend.core.llm_attempts import (
    llm_query_error_to_status_detail,
    mark_llm_answer_apply_failed,
    query_and_stage_llm_answer,
)
from backend.core.llm_service import LlmResult


ApplyResultT = TypeVar("ApplyResultT")


def require_owned_session(app_session_id: str, user: AuthUser) -> dict:
    """Return the session row if it exists and is owned by ``user``, else 404.

    A 404 (rather than 403) is used so the existence of another user's session
    is not revealed.
    """
    session = db.get_session_by_app_id(app_session_id)
    if session is None or session.get("owner_user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def require_session_owner(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """Route dependency: enforce that the request's session is owned by the user.

    Reads ``app_session_id`` from the query string or, failing that, the JSON
    body (Starlette caches the body, so the handler still parses it normally).
    """
    app_session_id = request.query_params.get("app_session_id")
    if not app_session_id and request.method not in {"GET", "HEAD", "DELETE"}:
        try:
            body = await request.json()
        except Exception:
            body = None
        if isinstance(body, dict):
            app_session_id = body.get("app_session_id")
    if not app_session_id:
        raise HTTPException(status_code=422, detail="app_session_id is required")
    require_owned_session(str(app_session_id), user)
    return user


def ensure_session_or_400(
    app_session_id: str,
    model: str | None,
    user: AuthUser,
) -> tuple[int, bool, str]:
    """Resolve or create the session, scoped to ``user`` ownership.

    Creates a new session owned by ``user`` when it does not exist yet (the
    first step of a workflow), resolves it when already owned, and rejects it
    with 404 when it exists but belongs to another user.
    """
    try:
        return db.ensure_session(app_session_id, model, owner_user_id=user.user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def query_and_stage_or_http(
    *,
    session_id: int,
    prompt_id: str,
    prompt: str,
    api_keys: ApiKeys,
    model: str,
    provider: str | None,
    query_fn: Callable[..., Awaitable[str | LlmResult]],
    norm_addressee: str | None = None,
) -> tuple[int, LlmResult]:
    try:
        return await query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id=prompt_id,
            prompt=prompt,
            api_keys=api_keys,
            model=model,
            provider=provider,
            query_fn=query_fn,
            norm_addressee=norm_addressee,
        )
    except Exception as exc:
        status, detail = llm_query_error_to_status_detail(exc)
        raise HTTPException(status_code=status, detail=detail) from exc


def run_with_answer_apply_guard(
    *,
    answer_id: int,
    apply_fn: Callable[[], ApplyResultT],
) -> ApplyResultT:
    try:
        return apply_fn()
    except Exception as exc:
        mark_llm_answer_apply_failed(answer_id=answer_id, exc=exc)
        raise
