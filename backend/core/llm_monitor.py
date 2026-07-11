from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


_MAX_EVENTS_PER_SESSION = 300
_MAX_ATTEMPTS_PER_SESSION = 120
_MAX_STREAM_CHUNKS_PER_ATTEMPT = 400
_MAX_STREAM_TEXT_CHARS_PER_ATTEMPT = 500_000
_MAX_STREAM_DELTA_CHARS = 4_000


@dataclass
class _SessionMonitorState:
    events: deque[dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=_MAX_EVENTS_PER_SESSION)
    )
    pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    stream_attempts: dict[str, dict[str, Any]] = field(default_factory=dict)
    stream_attempt_order: deque[str] = field(
        default_factory=lambda: deque(maxlen=_MAX_ATTEMPTS_PER_SESSION)
    )
    subscribers: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)
    sequence: int = 0


_STATE_BY_APP_SESSION: dict[str, _SessionMonitorState] = {}
_STATE_LOCK = asyncio.Lock()


def _get_or_create_state(app_session_id: str) -> _SessionMonitorState:
    state = _STATE_BY_APP_SESSION.get(app_session_id)
    if state is None:
        state = _SessionMonitorState()
        _STATE_BY_APP_SESSION[app_session_id] = state
    return state


def _sorted_pending(pending: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        pending.values(),
        key=lambda item: (
            int(item.get("started_at_ms") or 0),
            str(item.get("attempt_id") or ""),
        ),
        reverse=True,
    )


def _pending_from_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt_id": event.get("attempt_id"),
        "app_session_id": event.get("app_session_id"),
        "session_id": event.get("session_id"),
        "prompt_id": event.get("prompt_id"),
        "norm_addressee": event.get("norm_addressee"),
        "model": event.get("model"),
        "provider": event.get("provider"),
        "request_id": event.get("request_id"),
        "route_method": event.get("route_method"),
        "route_path": event.get("route_path"),
        "started_at_ms": event.get("timestamp_ms"),
        "status": "querying",
        "answer_id": None,
        "elapsed_ms": None,
    }


def _copy_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    copied = {
        key: value
        for key, value in attempt.items()
        if key not in {"chunks"}
    }
    chunks = attempt.get("chunks")
    copied["chunks"] = list(chunks) if isinstance(chunks, list) else []
    return copied


def _attempt_base_from_event(event: dict[str, Any]) -> dict[str, Any]:
    now_ms = int(event.get("timestamp_ms") or 0)
    return {
        "attempt_id": event.get("attempt_id"),
        "app_session_id": event.get("app_session_id"),
        "session_id": event.get("session_id"),
        "prompt_id": event.get("prompt_id"),
        "norm_addressee": event.get("norm_addressee"),
        "model": event.get("model"),
        "provider": event.get("provider"),
        "request_id": event.get("request_id"),
        "route_method": event.get("route_method"),
        "route_path": event.get("route_path"),
        "started_at_ms": now_ms,
        "updated_at_ms": now_ms,
        "completed_at_ms": None,
        "status": "querying",
        "answer_id": None,
        "elapsed_ms": None,
        "streaming": False,
        "stream_mode": event.get("stream_mode") or "requested",
        "stream_fallback_reason": None,
        "chunks": [],
        "chunk_count": 0,
        "text": "",
        "text_chars": 0,
        "error": None,
        "error_kind": None,
        "error_status_code": None,
        "answer_state": None,
        "state_reason": None,
        "input_tokens": None,
        "output_tokens": None,
        "hidden_thinking_tokens": None,
        "estimated_cost_usd": None,
    }


def _stream_attempts_list(state: _SessionMonitorState, limit: int = 80) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 500))
    items: list[dict[str, Any]] = []
    for attempt_id in reversed(state.stream_attempt_order):
        attempt = state.stream_attempts.get(attempt_id)
        if attempt is None:
            continue
        items.append(_copy_attempt(attempt))
        if len(items) >= safe_limit:
            break
    return items


def _get_or_create_attempt(
    state: _SessionMonitorState,
    event: dict[str, Any],
) -> dict[str, Any] | None:
    attempt_id = str(event.get("attempt_id") or "").strip()
    if not attempt_id:
        return None
    attempt = state.stream_attempts.get(attempt_id)
    if attempt is not None:
        return attempt

    while len(state.stream_attempt_order) >= _MAX_ATTEMPTS_PER_SESSION:
        oldest = state.stream_attempt_order.popleft()
        state.stream_attempts.pop(oldest, None)
    attempt = _attempt_base_from_event(event)
    state.stream_attempts[attempt_id] = attempt
    state.stream_attempt_order.append(attempt_id)
    return attempt


def _trim_chunks(chunks: list[dict[str, Any]]) -> None:
    if len(chunks) <= _MAX_STREAM_CHUNKS_PER_ATTEMPT:
        return
    overflow = len(chunks) - _MAX_STREAM_CHUNKS_PER_ATTEMPT
    del chunks[:overflow]


def _update_stream_attempt_from_event(
    *,
    state: _SessionMonitorState,
    event_type: str,
    event: dict[str, Any],
) -> dict[str, Any] | None:
    attempt = _get_or_create_attempt(state, event)
    if attempt is None:
        return None
    attempt_id = str(event.get("attempt_id") or "").strip()
    if attempt_id:
        try:
            state.stream_attempt_order.remove(attempt_id)
        except ValueError:
            pass
        state.stream_attempt_order.append(attempt_id)

    now_ms = int(event.get("timestamp_ms") or 0)
    attempt["updated_at_ms"] = now_ms
    for key in [
        "answer_id",
        "norm_addressee",
        "elapsed_ms",
        "input_tokens",
        "output_tokens",
        "hidden_thinking_tokens",
        "estimated_cost_usd",
        "answer_state",
        "state_reason",
        "error",
        "error_kind",
        "error_status_code",
        "response_format_requested",
        "response_format_used",
        "response_format_downgraded",
    ]:
        if key in event and event.get(key) is not None:
            attempt[key] = event.get(key)

    if event_type == "llm_query_started":
        attempt["status"] = "querying"
        attempt["stream_mode"] = event.get("stream_mode") or "requested"
        attempt["streaming"] = False
    elif event_type == "llm_stream_started":
        attempt["status"] = "streaming"
        attempt["stream_mode"] = event.get("stream_mode") or attempt.get("stream_mode")
        attempt["streaming"] = True
    elif event_type == "llm_stream_fallback":
        attempt["status"] = "fallback_non_stream"
        attempt["stream_mode"] = "fallback_non_stream"
        attempt["streaming"] = False
        attempt["stream_fallback_reason"] = event.get("reason")
    elif event_type == "llm_stream_delta":
        attempt["status"] = "streaming"
        attempt["streaming"] = True
        delta_text = str(event.get("delta_text") or "")
        if len(delta_text) > _MAX_STREAM_DELTA_CHARS:
            delta_text = f"{delta_text[:_MAX_STREAM_DELTA_CHARS]}..."
        chunk = {
            "sequence": event.get("chunk_index"),
            "timestamp_ms": now_ms,
            "delta_text": delta_text,
            "delta_chars": len(delta_text),
            "cumulative_chars": event.get("cumulative_chars"),
        }
        chunks = attempt.get("chunks")
        if not isinstance(chunks, list):
            chunks = []
            attempt["chunks"] = chunks
        chunks.append(chunk)
        _trim_chunks(chunks)
        text_now = str(attempt.get("text") or "")
        if delta_text and len(text_now) < _MAX_STREAM_TEXT_CHARS_PER_ATTEMPT:
            remaining = _MAX_STREAM_TEXT_CHARS_PER_ATTEMPT - len(text_now)
            text_now = f"{text_now}{delta_text[:remaining]}"
            attempt["text"] = text_now
            attempt["text_chars"] = len(text_now)
        attempt["chunk_count"] = int(attempt.get("chunk_count") or 0) + 1
    elif event_type == "llm_stream_completed":
        attempt["status"] = "stream_completed"
        attempt["streaming"] = False
        attempt["elapsed_ms"] = event.get("elapsed_ms") or attempt.get("elapsed_ms")
    elif event_type == "llm_stream_failed":
        attempt["status"] = "stream_failed"
        attempt["streaming"] = False
        attempt["error"] = event.get("error")
    elif event_type == "llm_query_succeeded":
        attempt["status"] = "staged_pending_apply"
        attempt["streaming"] = False
        attempt["completed_at_ms"] = now_ms
    elif event_type == "llm_query_failed":
        attempt["status"] = "query_failed"
        attempt["streaming"] = False
        attempt["completed_at_ms"] = now_ms
    elif event_type == "llm_apply_succeeded":
        attempt["status"] = "applied"
        attempt["streaming"] = False
        attempt["completed_at_ms"] = now_ms
    elif event_type == "llm_apply_failed":
        attempt["status"] = "apply_failed"
        attempt["streaming"] = False
        attempt["completed_at_ms"] = now_ms

    return attempt


def _update_pending_from_event(
    *,
    state: _SessionMonitorState,
    event_type: str,
    event: dict[str, Any],
) -> None:
    attempt_id = str(event.get("attempt_id") or "").strip()
    if not attempt_id:
        return

    if event_type == "llm_query_started":
        state.pending[attempt_id] = _pending_from_event(event)
        return

    existing = state.pending.get(attempt_id)
    if event_type in {"llm_stream_started", "llm_stream_delta"}:
        if existing is None:
            existing = _pending_from_event(event)
        existing["status"] = "streaming"
        state.pending[attempt_id] = existing
        return
    if event_type == "llm_stream_fallback":
        if existing is None:
            existing = _pending_from_event(event)
        existing["status"] = "fallback_non_stream"
        state.pending[attempt_id] = existing
        return
    if event_type == "llm_query_succeeded":
        if existing is None:
            existing = _pending_from_event(event)
        existing["status"] = "staged_pending_apply"
        existing["answer_id"] = event.get("answer_id")
        existing["elapsed_ms"] = event.get("elapsed_ms")
        state.pending[attempt_id] = existing
        return

    if event_type in {
        "llm_query_failed",
        "llm_apply_succeeded",
        "llm_apply_failed",
    }:
        state.pending.pop(attempt_id, None)


async def publish_llm_event(
    *,
    app_session_id: str,
    event: dict[str, Any],
) -> dict[str, Any]:
    subscribers: list[asyncio.Queue[dict[str, Any]]] = []
    outbound: dict[str, Any]
    async with _STATE_LOCK:
        state = _get_or_create_state(app_session_id)
        state.sequence += 1
        event_record = {
            **event,
            "app_session_id": app_session_id,
            "sequence": state.sequence,
            "timestamp_ms": int(time.time() * 1000),
        }
        event_type = str(event_record.get("event_type") or "").strip()
        _update_pending_from_event(
            state=state,
            event_type=event_type,
            event=event_record,
        )
        attempt_snapshot = _update_stream_attempt_from_event(
            state=state,
            event_type=event_type,
            event=event_record,
        )
        state.events.appendleft(event_record)
        pending_snapshot = _sorted_pending(state.pending)
        subscribers = list(state.subscribers)
        outbound = {
            "event": event_record,
            "pending": pending_snapshot,
            "stream_attempt": _copy_attempt(attempt_snapshot) if attempt_snapshot else None,
        }

    for queue in subscribers:
        try:
            queue.put_nowait(outbound)
        except asyncio.QueueFull:
            continue
    return outbound


def publish_llm_event_from_sync(
    *,
    app_session_id: str,
    event: dict[str, Any],
) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(publish_llm_event(app_session_id=app_session_id, event=event))


async def get_pending(app_session_id: str) -> list[dict[str, Any]]:
    async with _STATE_LOCK:
        state = _STATE_BY_APP_SESSION.get(app_session_id)
        if state is None:
            return []
        return _sorted_pending(state.pending)


async def get_recent_events(
    app_session_id: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 500))
    async with _STATE_LOCK:
        state = _STATE_BY_APP_SESSION.get(app_session_id)
        if state is None:
            return []
        return list(state.events)[:safe_limit]


async def subscribe(
    app_session_id: str,
    *,
    queue_size: int = 128,
) -> tuple[asyncio.Queue[dict[str, Any]], dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=queue_size)
    async with _STATE_LOCK:
        state = _get_or_create_state(app_session_id)
        state.subscribers.add(queue)
        snapshot = {
            "pending": _sorted_pending(state.pending),
            "events": list(state.events)[:100],
            "stream_attempts": _stream_attempts_list(state, limit=100),
        }
    return queue, snapshot


async def unsubscribe(app_session_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
    async with _STATE_LOCK:
        state = _STATE_BY_APP_SESSION.get(app_session_id)
        if state is None:
            return
        state.subscribers.discard(queue)


async def get_stream_attempts(
    app_session_id: str,
    *,
    limit: int = 80,
) -> list[dict[str, Any]]:
    async with _STATE_LOCK:
        state = _STATE_BY_APP_SESSION.get(app_session_id)
        if state is None:
            return []
        return _stream_attempts_list(state, limit=limit)


async def get_stream_attempt(
    app_session_id: str,
    attempt_id: str,
) -> dict[str, Any] | None:
    target = str(attempt_id or "").strip()
    if not target:
        return None
    async with _STATE_LOCK:
        state = _STATE_BY_APP_SESSION.get(app_session_id)
        if state is None:
            return None
        attempt = state.stream_attempts.get(target)
        if attempt is None:
            return None
        return _copy_attempt(attempt)
