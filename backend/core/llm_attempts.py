from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import time
from typing import Awaitable, Callable, Iterable

from backend.core import db
from backend.core.auth import ApiKeys
from backend.core.llm_service import (
    LlmQueryError,
    LlmResult,
    coerce_llm_result,
    query_llm,
)


def _provider_metadata(provider: str | None) -> dict[str, str | None]:
    return {"provider": provider}


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _attempt_metadata(
    *,
    provider: str | None,
    prompt: str,
    extra: dict | None = None,
) -> dict:
    metadata: dict = {
        **_provider_metadata(provider),
        "prompt_sha256": prompt_sha256(prompt),
    }
    if extra:
        metadata.update(extra)
    return metadata


def _error_detail(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str) and detail.strip():
        return detail
    return str(exc)


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def llm_query_error_to_status_detail(exc: Exception) -> tuple[int, str]:
    if not isinstance(exc, LlmQueryError):
        return 502, f"LLM query failed: {exc}"

    reason = exc.reason
    if reason == "rate_limit":
        status = 429
    elif reason == "provider_timeout":
        status = 504
    elif reason == "provider_connection_error":
        status = 503
    elif reason == "provider_http_error":
        status = (
            exc.status_code
            if isinstance(exc.status_code, int) and 400 <= exc.status_code <= 599
            else 502
        )
    else:
        status = 502

    detail = (
        f"LLM query failed ({reason}) for provider={exc.provider}, model={exc.model}: "
        f"{exc.args[0]}"
    )
    return status, detail


@dataclass(frozen=True)
class LlmPromptSpec:
    prompt_id: str
    query_label: str
    prompt: str


def mark_llm_query_failed(
    *,
    session_id: int,
    prompt_id: str,
    model: str,
    provider: str | None,
    prompt: str,
    exc: Exception,
    elapsed_ms: int | None = None,
) -> None:
    error_kind = getattr(exc, "reason", None)
    error_status_code = getattr(exc, "status_code", None)
    error_details = _jsonable(getattr(exc, "details", None))
    metadata_extra = {
        "error": str(exc),
        "error_kind": error_kind,
        "error_status_code": error_status_code,
        "error_type": exc.__class__.__name__,
        "error_module": exc.__class__.__module__,
        "error_details": error_details,
    }
    if elapsed_ms is not None:
        metadata_extra["elapsed_ms"] = elapsed_ms
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=prompt_id,
        model=model,
        answer_text="",
        metadata=_attempt_metadata(
            provider=provider,
            prompt=prompt,
            extra=metadata_extra,
        ),
        answer_state=db.LLM_ANSWER_STATE_INVALID,
        state_reason="query_failed",
    )


def stage_llm_response(
    *,
    session_id: int,
    prompt_id: str,
    prompt: str,
    model: str,
    provider: str | None,
    llm_result: LlmResult,
    elapsed_ms: int | None = None,
) -> int:
    metadata_extra = {"elapsed_ms": elapsed_ms} if elapsed_ms is not None else None
    return db.create_pending_llm_answer(
        session_id=session_id,
        prompt_id=prompt_id,
        model=model,
        answer_text=llm_result.text,
        metadata=_attempt_metadata(
            provider=provider,
            prompt=prompt,
            extra=metadata_extra,
        ),
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        hidden_thinking_tokens=llm_result.hidden_thinking_tokens,
        estimated_cost_usd=llm_result.estimated_cost_usd,
        provider_response_json=llm_result.provider_response_json,
    )


async def query_and_stage_llm_answer(
    *,
    session_id: int,
    prompt_id: str,
    prompt: str,
    api_keys: ApiKeys,
    model: str,
    provider: str | None,
    query_fn: Callable[..., Awaitable[str | LlmResult]] | None = None,
) -> tuple[int, LlmResult]:
    query_impl = query_fn or query_llm
    started = time.perf_counter()
    try:
        llm_result = coerce_llm_result(
            await query_impl(
                prompt,
                api_keys=api_keys,
                model=model,
                provider=provider,
            )
        )
    except Exception as exc:
        mark_llm_query_failed(
            session_id=session_id,
            prompt_id=prompt_id,
            model=model,
            provider=provider,
            prompt=prompt,
            exc=exc,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        raise
    answer_id = stage_llm_response(
        session_id=session_id,
        prompt_id=prompt_id,
        prompt=prompt,
        model=model,
        provider=provider,
        llm_result=llm_result,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
    return answer_id, llm_result


async def query_and_stage_llm_answers_parallel(
    *,
    session_id: int,
    specs: Iterable[LlmPromptSpec],
    api_keys: ApiKeys,
    model: str,
    provider: str | None,
    query_fn: Callable[..., Awaitable[str | LlmResult]] | None = None,
) -> tuple[dict[str, int], dict[str, LlmResult], list[str]]:
    async def _run_one(
        spec: LlmPromptSpec,
    ) -> tuple[LlmPromptSpec, int | None, LlmResult | None, Exception | None]:
        try:
            answer_id, result = await query_and_stage_llm_answer(
                session_id=session_id,
                prompt_id=spec.prompt_id,
                prompt=spec.prompt,
                api_keys=api_keys,
                model=model,
                provider=provider,
                query_fn=query_fn,
            )
            return spec, answer_id, result, None
        except Exception as exc:
            return spec, None, None, exc

    tasks = [asyncio.create_task(_run_one(spec)) for spec in specs]
    pending_answer_ids: dict[str, int] = {}
    query_results: dict[str, LlmResult] = {}
    query_errors: list[str] = []
    for task in asyncio.as_completed(tasks):
        spec, answer_id, result, query_error = await task
        if query_error is not None:
            query_errors.append(f"{spec.query_label} query failed: {query_error}")
            continue
        assert answer_id is not None
        assert result is not None
        pending_answer_ids[spec.prompt_id] = answer_id
        query_results[spec.prompt_id] = result
    return pending_answer_ids, query_results, query_errors


def mark_llm_answer_applied(
    *,
    answer_id: int,
    session_id: int,
    prompt_id: str,
) -> None:
    db.activate_llm_answer(
        answer_id=answer_id,
        session_id=session_id,
        prompt_id=prompt_id,
        reason="session_updated",
    )


def mark_llm_answer_apply_failed(
    *,
    answer_id: int,
    exc: Exception,
) -> None:
    db.invalidate_llm_answer(
        answer_id,
        reason=f"session_update_failed: {_error_detail(exc)}",
    )


def invalidate_staged_llm_answer(
    *,
    answer_id: int,
    reason: str,
) -> None:
    db.invalidate_llm_answer(answer_id, reason=reason)


def invalidate_staged_llm_answers(
    *,
    answer_ids: Iterable[int],
    reason: str,
) -> None:
    for answer_id in answer_ids:
        invalidate_staged_llm_answer(answer_id=answer_id, reason=reason)


def mark_llm_answers_apply_failed(
    *,
    answer_ids: Iterable[int],
    exc: Exception,
) -> None:
    for answer_id in answer_ids:
        mark_llm_answer_apply_failed(answer_id=answer_id, exc=exc)
