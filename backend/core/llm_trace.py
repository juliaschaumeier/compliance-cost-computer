from __future__ import annotations

import json
import os
import re
import threading
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.llm_service import LlmResult


TRACE_DIR = Path("tmp/traces")


def _env_flag(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def trace_enabled_by_env() -> bool:
    return _env_flag("LLM_TRACE")


@dataclass
class _Step:
    index: int
    kind: str  # "success" | "failure" | "fallback"
    prompt_id: str
    model: str
    provider: str | None
    attempt_id: str | None
    prompt: str | None = None
    response_text: str | None = None
    elapsed_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    hidden_thinking_tokens: int | None = None
    estimated_cost_usd: float | None = None
    error: str | None = None
    error_kind: str | None = None
    fallback_kind: str | None = None
    fallback_detail: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Run:
    request_id: str
    route_method: str
    route_path: str
    started_at: datetime
    app_session_id: str | None
    steps: list[_Step] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


_CURRENT_RUN: ContextVar[_Run | None] = ContextVar("llm_trace_run", default=None)


def start_run(
    *,
    request_id: str,
    route_method: str,
    route_path: str,
    app_session_id: str | None,
) -> Token[_Run | None]:
    run = _Run(
        request_id=request_id,
        route_method=route_method,
        route_path=route_path,
        started_at=datetime.now(),
        app_session_id=app_session_id,
    )
    return _CURRENT_RUN.set(run)


def reset_run(token: Token[_Run | None]) -> None:
    _CURRENT_RUN.reset(token)


def _current_run() -> _Run | None:
    return _CURRENT_RUN.get()


def record_success(
    *,
    prompt_id: str,
    model: str,
    provider: str | None,
    attempt_id: str | None,
    prompt: str,
    llm_result: LlmResult,
    elapsed_ms: int | None,
) -> None:
    run = _current_run()
    if run is None:
        return
    with run.lock:
        run.steps.append(
            _Step(
                index=len(run.steps) + 1,
                kind="success",
                prompt_id=prompt_id,
                model=model,
                provider=provider,
                attempt_id=attempt_id,
                prompt=prompt,
                response_text=llm_result.text,
                elapsed_ms=elapsed_ms,
                input_tokens=llm_result.input_tokens,
                output_tokens=llm_result.output_tokens,
                hidden_thinking_tokens=llm_result.hidden_thinking_tokens,
                estimated_cost_usd=llm_result.estimated_cost_usd,
            )
        )


def record_failure(
    *,
    prompt_id: str,
    model: str,
    provider: str | None,
    attempt_id: str | None,
    prompt: str,
    exc: Exception,
    elapsed_ms: int | None,
) -> None:
    run = _current_run()
    if run is None:
        return
    with run.lock:
        run.steps.append(
            _Step(
                index=len(run.steps) + 1,
                kind="failure",
                prompt_id=prompt_id,
                model=model,
                provider=provider,
                attempt_id=attempt_id,
                prompt=prompt,
                elapsed_ms=elapsed_ms,
                error=str(exc),
                error_kind=getattr(exc, "reason", None) or exc.__class__.__name__,
            )
        )


def record_fallback(
    *,
    prompt_id: str,
    fallback_kind: str,
    attempt_id: str | None,
    model: str | None,
    provider: str | None,
    detail: str | None,
    extra: dict[str, Any] | None = None,
) -> None:
    run = _current_run()
    if run is None:
        return
    with run.lock:
        run.steps.append(
            _Step(
                index=len(run.steps) + 1,
                kind="fallback",
                prompt_id=prompt_id,
                model=model or "",
                provider=provider,
                attempt_id=attempt_id,
                fallback_kind=fallback_kind,
                fallback_detail=detail,
                extra=dict(extra or {}),
            )
        )


_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def _slug(value: str) -> str:
    text = _SLUG_RE.sub("-", value).strip("-").lower()
    return text or "root"


def _fmt_int(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return str(value)


def _fmt_cost(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"${float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def _render_step(step: _Step) -> str:
    header_bits = [
        f"## Step {step.index} — `{step.prompt_id}` ({step.kind})",
    ]
    meta_line = (
        f"- model: `{step.model}` | provider: `{step.provider or '-'}` "
        f"| attempt: `{step.attempt_id or '-'}` "
        f"| elapsed: {_fmt_int(step.elapsed_ms)} ms"
    )
    parts = [*header_bits, meta_line]

    if step.kind == "success":
        parts.append(
            f"- tokens: in={_fmt_int(step.input_tokens)} "
            f"out={_fmt_int(step.output_tokens)} "
            f"hidden_thinking={_fmt_int(step.hidden_thinking_tokens)} "
            f"| cost: {_fmt_cost(step.estimated_cost_usd)}"
        )
    elif step.kind == "failure":
        parts.append(f"- error_kind: `{step.error_kind or '-'}`")
        parts.append(f"- error: {step.error or '-'}")
    elif step.kind == "fallback":
        parts.append(f"- fallback_kind: `{step.fallback_kind or '-'}`")
        if step.fallback_detail:
            parts.append(f"- detail: {step.fallback_detail}")
        if step.extra:
            try:
                parts.append(
                    "- extra:\n\n```json\n"
                    + json.dumps(step.extra, indent=2, ensure_ascii=False, default=str)
                    + "\n```"
                )
            except Exception:
                parts.append(f"- extra: {step.extra}")

    if step.prompt is not None:
        parts.append("\n### Prompt\n\n```\n" + step.prompt + "\n```")
    if step.response_text is not None:
        parts.append("\n### Raw Response\n\n```\n" + step.response_text + "\n```")

    return "\n".join(parts)


def _render_markdown(run: _Run, status_code: int | None) -> str:
    total_steps = len(run.steps)
    successes = sum(1 for s in run.steps if s.kind == "success")
    failures = sum(1 for s in run.steps if s.kind == "failure")
    fallbacks = sum(1 for s in run.steps if s.kind == "fallback")
    total_in = sum(int(s.input_tokens or 0) for s in run.steps if s.kind == "success")
    total_out = sum(int(s.output_tokens or 0) for s in run.steps if s.kind == "success")
    total_cost = sum(
        float(s.estimated_cost_usd or 0.0) for s in run.steps if s.kind == "success"
    )
    duration_ms = int((datetime.now() - run.started_at).total_seconds() * 1000)

    head = [
        f"# LLM Run Trace — {run.route_method} {run.route_path}",
        "",
        f"- request_id: `{run.request_id}`",
        f"- started_at: {run.started_at.isoformat(timespec='seconds')}",
        f"- duration_ms: {duration_ms}",
        f"- status_code: {status_code if status_code is not None else '-'}",
        f"- app_session_id: `{run.app_session_id or '-'}`",
        f"- steps: {total_steps} (success={successes}, failure={failures}, fallback={fallbacks})",
        f"- total_tokens: in={total_in} out={total_out}",
        f"- total_cost: {_fmt_cost(total_cost if successes else None)}",
        "",
        "---",
        "",
    ]
    body = [_render_step(step) for step in run.steps]
    return "\n".join(head) + "\n\n---\n\n".join(body) + "\n"


def flush_run(
    token: Token[_Run | None],
    *,
    status_code: int | None = None,
) -> Path | None:
    run = _current_run()
    try:
        if run is None or not run.steps:
            return None
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = run.started_at.strftime("%Y%m%d-%H%M%S")
        endpoint_slug = _slug(run.route_path.lstrip("/") or "root")
        filename = f"{timestamp}_{endpoint_slug}_{run.request_id[:8]}.md"
        path = TRACE_DIR / filename
        path.write_text(_render_markdown(run, status_code), encoding="utf-8")
        return path
    finally:
        reset_run(token)
