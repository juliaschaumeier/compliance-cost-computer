from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import inspect
import logging
import time
from typing import Any, Awaitable, Callable, Iterable
import uuid

from backend.core import db
from backend.core.auth import ApiKeys
from backend.core import llm_monitor
from backend.core import llm_trace
from backend.core.config import settings
from backend.core.llm_service import (
    LlmQueryError,
    LlmResult,
    coerce_llm_result,
    query_llm,
)
from backend.core.prompt_audit import append_prompt_audit_entry
from backend.core.prompts import PromptId
from backend.core.request_context import get_request_context

logger = logging.getLogger("uvicorn.error")

# Workflow-Prompts mit struktur-kritischer JSON-Ausgabe. Fuer diese aktivieren wir
# - wo query-Funktion und Provider es unterstuetzen - den JSON-Modus
# (response_format) bereits am Generierungszeitpunkt. Lehnt ein Provider/Modell den
# Parameter ab, faellt query_llm automatisch auf reines Prompting zurueck.
STRUCTURED_JSON_PROMPT_IDS = frozenset(
    {
        PromptId.PROCESS_COMPILATION,
        PromptId.CASE_GROUP_DEVELOPMENT,
        PromptId.PROCESS_STEP_ANALYSIS,
        PromptId.CASES_CALCULATION,
        PromptId.EFFORT_CALCULATION,
    }
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


def _normalize_app_session_id(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text or text == "-":
        return None
    return text


def _resolve_app_session_id(
    session_id: int,
    request_context: dict[str, str | None],
) -> str | None:
    session = db.get_session_by_id(session_id)
    if session:
        resolved = _normalize_app_session_id(str(session.get("app_session_id") or ""))
        if resolved:
            return resolved
    return _normalize_app_session_id(request_context.get("app_session_id"))


async def _publish_monitor_event(
    *,
    app_session_id: str | None,
    event: dict[str, Any],
) -> None:
    if not app_session_id:
        return
    try:
        await llm_monitor.publish_llm_event(
            app_session_id=app_session_id,
            event=event,
        )
    except Exception:
        # Monitoring must never break the execution path.
        return


def _publish_monitor_event_sync(
    *,
    app_session_id: str | None,
    event: dict[str, Any],
) -> None:
    if not app_session_id:
        return
    try:
        llm_monitor.publish_llm_event_from_sync(
            app_session_id=app_session_id,
            event=event,
        )
    except Exception:
        # Monitoring must never break the execution path.
        return


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


def _supports_keyword_argument(
    fn: Callable[..., Any],
    keyword: str,
) -> bool:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return True
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return keyword in signature.parameters


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
    norm_addressee: str | None = None
    result_key: str | None = None


def mark_llm_query_failed(
    *,
    session_id: int,
    prompt_id: str,
    model: str,
    provider: str | None,
    prompt: str,
    exc: Exception,
    elapsed_ms: int | None = None,
    attempt_id: str | None = None,
    request_context: dict[str, str | None] | None = None,
    norm_addressee: str | None = None,
) -> None:
    request_context = request_context or {}
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
        "attempt_id": attempt_id,
        "request_id": request_context.get("request_id"),
        "route_method": request_context.get("route_method"),
        "route_path": request_context.get("route_path"),
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
        norm_addressee=norm_addressee,
        prompt_text=prompt,
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
    attempt_id: str | None = None,
    request_context: dict[str, str | None] | None = None,
    norm_addressee: str | None = None,
) -> int:
    request_context = request_context or {}
    metadata_extra: dict[str, Any] = {
        "attempt_id": attempt_id,
        "request_id": request_context.get("request_id"),
        "route_method": request_context.get("route_method"),
        "route_path": request_context.get("route_path"),
    }
    if elapsed_ms is not None:
        metadata_extra["elapsed_ms"] = elapsed_ms
    return db.create_pending_llm_answer(
        session_id=session_id,
        prompt_id=prompt_id,
        model=model,
        answer_text=llm_result.text,
        metadata=_attempt_metadata(
            provider=provider,
            prompt=prompt,
            extra=metadata_extra or None,
        ),
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        hidden_thinking_tokens=llm_result.hidden_thinking_tokens,
        estimated_cost_usd=llm_result.estimated_cost_usd,
        provider_response_json=llm_result.provider_response_json,
        norm_addressee=norm_addressee,
        prompt_text=prompt,
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
    norm_addressee: str | None = None,
) -> tuple[int, LlmResult]:
    query_impl = query_fn or query_llm
    request_ctx = get_request_context()
    app_session_id = _resolve_app_session_id(session_id, request_ctx)
    attempt_id = uuid.uuid4().hex
    await _publish_monitor_event(
        app_session_id=app_session_id,
        event={
            "event_type": "llm_query_started",
            "attempt_id": attempt_id,
            "session_id": session_id,
            "prompt_id": prompt_id,
            "norm_addressee": norm_addressee,
            "model": model,
            "provider": provider,
            "request_id": request_ctx.get("request_id"),
            "route_method": request_ctx.get("route_method"),
            "route_path": request_ctx.get("route_path"),
            "prompt_chars": len(prompt),
            "stream_mode": "requested",
        },
    )
    if app_session_id:
        append_prompt_audit_entry(
            app_session_id=app_session_id,
            session_id=session_id,
            prompt_id=prompt_id,
            model=model,
            provider=provider,
            attempt_id=attempt_id,
            prompt=prompt,
            route_method=request_ctx.get("route_method"),
            route_path=request_ctx.get("route_path"),
        )

    async def _on_stream_event(stream_event: dict[str, Any]) -> None:
        if not settings.llm_stream_debug_enabled:
            return
        if not isinstance(stream_event, dict):
            return
        event_type = str(stream_event.get("event_type") or "").strip()
        if not event_type:
            return
        await _publish_monitor_event(
            app_session_id=app_session_id,
            event={
                "event_type": event_type,
                "attempt_id": attempt_id,
                "session_id": session_id,
                "prompt_id": prompt_id,
                "norm_addressee": norm_addressee,
                "model": model,
                "provider": provider,
                "request_id": request_ctx.get("request_id"),
                "route_method": request_ctx.get("route_method"),
                "route_path": request_ctx.get("route_path"),
                **stream_event,
            },
        )

    started = time.perf_counter()
    try:
        supports_stream = _supports_keyword_argument(query_impl, "stream")
        supports_on_event = _supports_keyword_argument(query_impl, "on_event")
        query_kwargs: dict[str, Any] = {
            "api_keys": api_keys,
            "model": model,
            "provider": provider,
        }
        if supports_stream:
            query_kwargs["stream"] = True
        else:
            await _publish_monitor_event(
                app_session_id=app_session_id,
                event={
                    "event_type": "llm_stream_fallback",
                    "attempt_id": attempt_id,
                    "session_id": session_id,
                    "prompt_id": prompt_id,
                    "norm_addressee": norm_addressee,
                    "model": model,
                    "provider": provider,
                    "request_id": request_ctx.get("request_id"),
                    "route_method": request_ctx.get("route_method"),
                    "route_path": request_ctx.get("route_path"),
                    "stream_mode": "fallback_non_stream",
                    "reason": "query_fn_no_stream_argument",
                },
            )
        if supports_on_event:
            query_kwargs["on_event"] = _on_stream_event
        if (
            prompt_id in STRUCTURED_JSON_PROMPT_IDS
            and _supports_keyword_argument(query_impl, "response_format")
        ):
            query_kwargs["response_format"] = {"type": "json_object"}
        llm_result = coerce_llm_result(
            await query_impl(
                prompt,
                **query_kwargs,
            )
        )
    except asyncio.CancelledError:
        failure_elapsed_ms = int((time.perf_counter() - started) * 1000)
        exc = LlmQueryError(
            provider=provider or "unknown",
            model=model,
            reason="cancelled",
            message="LLM query was cancelled before completion",
        )
        llm_trace.record_failure(
            prompt_id=prompt_id,
            model=model,
            provider=provider,
            attempt_id=attempt_id,
            prompt=prompt,
            exc=exc,
            elapsed_ms=failure_elapsed_ms,
        )
        mark_llm_query_failed(
            session_id=session_id,
            prompt_id=prompt_id,
            model=model,
            provider=provider,
            prompt=prompt,
            exc=exc,
            elapsed_ms=failure_elapsed_ms,
            attempt_id=attempt_id,
            request_context=request_ctx,
            norm_addressee=norm_addressee,
        )
        await _publish_monitor_event(
            app_session_id=app_session_id,
            event={
                "event_type": "llm_query_failed",
                "attempt_id": attempt_id,
                "session_id": session_id,
                "prompt_id": prompt_id,
                "norm_addressee": norm_addressee,
                "model": model,
                "provider": provider,
                "request_id": request_ctx.get("request_id"),
                "route_method": request_ctx.get("route_method"),
                "route_path": request_ctx.get("route_path"),
                "elapsed_ms": failure_elapsed_ms,
                "error": str(exc),
                "error_kind": exc.reason,
                "error_status_code": exc.status_code,
            },
        )
        raise
    except Exception as exc:
        failure_elapsed_ms = int((time.perf_counter() - started) * 1000)
        llm_trace.record_failure(
            prompt_id=prompt_id,
            model=model,
            provider=provider,
            attempt_id=attempt_id,
            prompt=prompt,
            exc=exc,
            elapsed_ms=failure_elapsed_ms,
        )
        mark_llm_query_failed(
            session_id=session_id,
            prompt_id=prompt_id,
            model=model,
            provider=provider,
            prompt=prompt,
            exc=exc,
            elapsed_ms=failure_elapsed_ms,
            attempt_id=attempt_id,
            request_context=request_ctx,
            norm_addressee=norm_addressee,
        )
        await _publish_monitor_event(
            app_session_id=app_session_id,
            event={
                "event_type": "llm_query_failed",
                "attempt_id": attempt_id,
                "session_id": session_id,
                "prompt_id": prompt_id,
                "norm_addressee": norm_addressee,
                "model": model,
                "provider": provider,
                "request_id": request_ctx.get("request_id"),
                "route_method": request_ctx.get("route_method"),
                "route_path": request_ctx.get("route_path"),
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "error": str(exc),
                "error_kind": getattr(exc, "reason", None),
                "error_status_code": getattr(exc, "status_code", None),
            },
        )
        raise
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    llm_trace.record_success(
        prompt_id=prompt_id,
        model=model,
        provider=provider,
        attempt_id=attempt_id,
        prompt=prompt,
        llm_result=llm_result,
        elapsed_ms=elapsed_ms,
    )
    answer_id = stage_llm_response(
        session_id=session_id,
        prompt_id=prompt_id,
        prompt=prompt,
        model=model,
        provider=provider,
        llm_result=llm_result,
        elapsed_ms=elapsed_ms,
        attempt_id=attempt_id,
        request_context=request_ctx,
        norm_addressee=norm_addressee,
    )
    await _publish_monitor_event(
        app_session_id=app_session_id,
        event={
            "event_type": "llm_query_succeeded",
            "attempt_id": attempt_id,
            "answer_id": answer_id,
            "session_id": session_id,
            "prompt_id": prompt_id,
            "norm_addressee": norm_addressee,
            "model": model,
            "provider": provider,
            "request_id": request_ctx.get("request_id"),
            "route_method": request_ctx.get("route_method"),
            "route_path": request_ctx.get("route_path"),
            "elapsed_ms": elapsed_ms,
            "input_tokens": llm_result.input_tokens,
            "output_tokens": llm_result.output_tokens,
            "hidden_thinking_tokens": llm_result.hidden_thinking_tokens,
            "estimated_cost_usd": llm_result.estimated_cost_usd,
        },
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
                norm_addressee=spec.norm_addressee,
            )
            return spec, answer_id, result, None
        except Exception as exc:
            return spec, None, None, exc

    tasks = [asyncio.create_task(_run_one(spec)) for spec in specs]
    pending_answer_ids: dict[str, int] = {}
    query_results: dict[str, LlmResult] = {}
    query_errors: list[str] = []
    try:
        for task in asyncio.as_completed(tasks):
            spec, answer_id, result, query_error = await task
            if query_error is not None:
                query_errors.append(f"{spec.query_label} query failed: {query_error}")
                continue
            assert answer_id is not None
            assert result is not None
            result_key = spec.result_key or spec.prompt_id
            pending_answer_ids[result_key] = answer_id
            query_results[result_key] = result
    except asyncio.CancelledError:
        for task in tasks:
            if not task.done():
                task.cancel()
        settled = await asyncio.gather(*tasks, return_exceptions=True)
        for item in settled:
            if not isinstance(item, tuple):
                continue
            spec, answer_id, _result, _query_error = item
            if answer_id is None:
                continue
            result_key = spec.result_key or spec.prompt_id
            pending_answer_ids[result_key] = int(answer_id)
        for answer_id in pending_answer_ids.values():
            db.update_llm_answer_state_reason(
                answer_id,
                "waiting_for_paired_retry",
                state=db.LLM_ANSWER_STATE_PENDING,
            )
        raise
    return pending_answer_ids, query_results, query_errors


def mark_llm_answer_applied(
    *,
    answer_id: int,
    session_id: int,
    prompt_id: str,
    publish: bool = True,
) -> None:
    db.activate_llm_answer(
        answer_id=answer_id,
        session_id=session_id,
        prompt_id=prompt_id,
        reason="session_updated",
    )
    if publish:
        publish_llm_answer_applied(answer_id=answer_id, prompt_id=prompt_id)


def publish_llm_answer_applied(
    *,
    answer_id: int,
    prompt_id: str,
) -> None:
    answer = db.get_llm_answer_by_id(answer_id)
    if not answer:
        return
    metadata = answer.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    session = db.get_session_by_id(int(answer["session_id"]))
    app_session_id = None
    if session is not None:
        app_session_id = _normalize_app_session_id(str(session.get("app_session_id") or ""))
    _publish_monitor_event_sync(
        app_session_id=app_session_id,
        event={
            "event_type": "llm_apply_succeeded",
            "attempt_id": metadata.get("attempt_id"),
            "answer_id": int(answer_id),
            "session_id": int(answer["session_id"]),
            "prompt_id": str(answer.get("prompt_id") or prompt_id),
            "norm_addressee": answer.get("norm_addressee"),
            "model": str(answer.get("model") or ""),
            "provider": metadata.get("provider"),
            "request_id": metadata.get("request_id"),
            "route_method": metadata.get("route_method"),
            "route_path": metadata.get("route_path"),
            "answer_state": db.LLM_ANSWER_STATE_ACTIVE,
            "state_reason": "session_updated",
            "elapsed_ms": metadata.get("elapsed_ms"),
            "input_tokens": answer.get("input_tokens"),
            "output_tokens": answer.get("output_tokens"),
            "hidden_thinking_tokens": answer.get("hidden_thinking_tokens"),
            "estimated_cost_usd": answer.get("estimated_cost_usd"),
        },
    )


def mark_llm_answer_apply_failed(
    *,
    answer_id: int,
    exc: Exception,
) -> None:
    answer = db.get_llm_answer_by_id(answer_id)
    db.invalidate_llm_answer(
        answer_id,
        reason=f"session_update_failed: {_error_detail(exc)}",
    )
    if not answer:
        return
    metadata = answer.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    session = db.get_session_by_id(int(answer["session_id"]))
    app_session_id = None
    if session is not None:
        app_session_id = _normalize_app_session_id(str(session.get("app_session_id") or ""))
    _publish_monitor_event_sync(
        app_session_id=app_session_id,
        event={
            "event_type": "llm_apply_failed",
            "attempt_id": metadata.get("attempt_id"),
            "answer_id": int(answer_id),
            "session_id": int(answer["session_id"]),
            "prompt_id": str(answer.get("prompt_id") or ""),
            "norm_addressee": answer.get("norm_addressee"),
            "model": str(answer.get("model") or ""),
            "provider": metadata.get("provider"),
            "request_id": metadata.get("request_id"),
            "route_method": metadata.get("route_method"),
            "route_path": metadata.get("route_path"),
            "answer_state": db.LLM_ANSWER_STATE_INVALID,
            "state_reason": f"session_update_failed: {_error_detail(exc)}",
            "elapsed_ms": metadata.get("elapsed_ms"),
            "error": str(exc),
        },
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


def mark_llm_parse_fallback(
    *,
    session_id: int,
    prompt_id: str,
    fallback_kind: str,
    answer_id: int | None = None,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    answer: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}
    if answer_id is not None:
        answer = db.get_llm_answer_by_id(answer_id)
        raw_metadata = answer.get("metadata") if isinstance(answer, dict) else None
        if isinstance(raw_metadata, dict):
            metadata = raw_metadata
    request_ctx = get_request_context()
    session = db.get_session_by_id(session_id)
    app_session_id = None
    if session is not None:
        app_session_id = _normalize_app_session_id(str(session.get("app_session_id") or ""))

    event: dict[str, Any] = {
        "event_type": "llm_parse_fallback",
        "fallback_kind": fallback_kind,
        "session_id": session_id,
        "prompt_id": prompt_id,
        "attempt_id": metadata.get("attempt_id"),
        "answer_id": answer_id,
        "model": str(answer.get("model") or "") if isinstance(answer, dict) else None,
        "provider": metadata.get("provider"),
        "request_id": metadata.get("request_id") or request_ctx.get("request_id"),
        "route_method": metadata.get("route_method") or request_ctx.get("route_method"),
        "route_path": metadata.get("route_path") or request_ctx.get("route_path"),
    }
    if detail:
        event["detail"] = detail
    if extra:
        event.update(_jsonable(extra))

    logger.warning(
        (
            "LLM parse fallback | session=%s prompt=%s answer=%s attempt=%s "
            "kind=%s detail=%s route=%s %s"
        ),
        session_id,
        prompt_id,
        answer_id if answer_id is not None else "-",
        event.get("attempt_id") or "-",
        fallback_kind,
        detail or "-",
        event.get("route_method") or "-",
        event.get("route_path") or "-",
    )
    _publish_monitor_event_sync(app_session_id=app_session_id, event=event)
    llm_trace.record_fallback(
        prompt_id=prompt_id,
        fallback_kind=fallback_kind,
        attempt_id=event.get("attempt_id"),
        model=event.get("model"),
        provider=event.get("provider"),
        detail=detail,
        extra=_jsonable(extra) if extra else None,
    )
