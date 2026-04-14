from __future__ import annotations

from typing import Awaitable, Callable, TypeVar

from fastapi import HTTPException

from backend.core import db
from backend.core.auth import ApiKeys
from backend.core.llm_attempts import (
    llm_query_error_to_status_detail,
    mark_llm_answer_apply_failed,
    query_and_stage_llm_answer,
)
from backend.core.llm_service import LlmResult


ApplyResultT = TypeVar("ApplyResultT")


def ensure_session_or_400(
    app_session_id: str,
    model: str | None,
) -> tuple[int, bool, str]:
    try:
        return db.ensure_session(app_session_id, model)
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
