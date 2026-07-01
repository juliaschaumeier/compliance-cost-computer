from __future__ import annotations

import asyncio
from datetime import datetime
import html
import inspect
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from io import BytesIO
from typing import Annotated, AsyncGenerator, Awaitable, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, StringConstraints

from backend.core.auth import ApiKeys, get_api_keys
from backend.core.compliance_text_export import (
    USER_EDIT_REJECT,
    USER_EDIT_USE,
    build_compliance_export_context,
    normalize_user_edit_policy,
)
from backend.core import db, llm_monitor, llm_trace
from backend.core.config import settings
from backend.core.deep_research_cases import (
    CASE_GROUP_RESEARCH_PURPOSE,
    apply_deep_research_case_metrics,
    apply_validated_deep_research_case_metrics,
    validate_deep_research_case_metrics,
)
from backend.core.deep_research_cases_prompt import build_deep_research_cases_prompt
from backend.core.deep_research_service import (
    DeepResearchError,
    harvest_deep_research_interaction,
    run_deep_research,
)
from backend.core.llm_attempts import (
    LlmPromptSpec,
    mark_llm_answer_applied,
    mark_llm_answer_apply_failed,
    mark_llm_parse_fallback,
    prompt_sha256,
    publish_llm_answer_applied,
    query_and_stage_llm_answers_parallel,
)
from backend.core.llm_service import LlmResult, query_llm
from backend.core.norm_addressees import SUPPORTED_NORM_ADDRESSEES
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.prompts import PromptId, render_prompt
from backend.core.request_context import get_request_context
from backend.core.session_activity import (
    EA_EDIT_LEASE_SECONDS,
    SessionActivityConflict,
    SessionActivityUnavailable,
    WORKFLOW_LEASE_SECONDS,
    begin_session_activity,
    refresh_session_activity,
    release_session_activity,
)
from backend.core.session_graph import build_session_tiles_snapshot
from backend.core.workflow import (
    get_last_completed_step,
    undo_step,
)
from backend.routers._llm_router_utils import (
    ensure_session_or_400,
    query_and_stage_or_http,
    run_with_answer_apply_guard,
)
from backend.routers._edit_validation import validate_wage_source_kind
from backend.routers._norm_addressee import normalize_norm_addressee_or_422
from backend.routers._session_activity_guard import (
    guarded_session_activity,
    raise_session_activity_conflict,
    raise_session_activity_unavailable,
)
from backend.routers._session_validation import (
    APP_SESSION_ID_QUERY_VALIDATION,
    AppSessionId,
)
from backend.routers import (
    case_groups as case_groups_router,
    costs as costs_router,
    effort as effort_router,
    process_steps as process_steps_router,
    processes as processes_router,
    regulations as regulations_router,
)


router = APIRouter(prefix="/sessions", tags=["sessions"])

DEEP_RESEARCH_MONITOR_PROMPT_ID = "deep_research_case_group_metrics"
_CANCELLED_DEEP_RESEARCH_HARVEST_TASKS: set[asyncio.Task] = set()

ModelName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]


class SessionUpsertRequest(BaseModel):
    app_session_id: AppSessionId
    llm_model: ModelName


class SessionUndoRequest(BaseModel):
    app_session_id: AppSessionId


class SessionUpsertResponse(BaseModel):
    app_session_id: str
    created: bool


class SessionSummary(BaseModel):
    app_session_id: str
    created_at: str
    llm_model: str
    used_llm_models: str | None = None
    case_group_research_enabled: bool = False


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class SessionStatusResponse(BaseModel):
    summary_ready: bool
    regulations_ready: bool
    processes_ready: bool
    processes_ready_by_addressee: dict[str, bool] = {}
    case_groups_ready: bool
    case_groups_ready_by_addressee: dict[str, bool] = {}
    process_steps_ready: bool
    process_steps_ready_by_addressee: dict[str, bool] = {}
    effort_ready: bool
    effort_ready_by_addressee: dict[str, bool] = {}
    total_cost_ready: bool
    total_cost_ready_by_addressee: dict[str, bool] = {}
    case_group_research_enabled: bool = False
    case_group_research_status: str = "idle"
    case_group_research_elapsed_seconds: int | None = None
    last_completed_step: str | None = None
    last_completed_label: str | None = None
    last_failed_step: str | None = None
    last_failed_label: str | None = None
    last_failed_message: str | None = None


class SessionPayRatesUpdateRequest(BaseModel):
    app_session_id: AppSessionId
    norm_addressee: str | None = None
    ea_activity_id: str | None = None
    administration_level: str | None = None
    edited_a: float | None
    edited_b: float | None
    edited_c: float | None
    edited_d: float | None


class SessionPayRatesResponse(BaseModel):
    app_session_id: str
    norm_addressee: str = ADMINISTRATION
    editable: bool = True
    administration_level: str | None = None
    wage_source_label: str | None = None
    defaults: dict[str, float]
    edited: dict[str, float | None]
    active: dict[str, float]


class SessionWageRateRow(BaseModel):
    wage_source_kind: str
    wage_source_value: str
    qualification: str
    model_hourly_rate: float
    hourly_rate_edited: float | None = None


class SessionWageRatesResponse(BaseModel):
    app_session_id: str
    norm_addressee: str = ADMINISTRATION
    rows: list[SessionWageRateRow]


class SessionWageRateUpdateRequest(BaseModel):
    app_session_id: AppSessionId
    norm_addressee: str | None = None
    ea_activity_id: str | None = None
    wage_source_kind: str
    wage_source_value: str
    qualification: str
    hourly_rate_edited: float | None = None


class SessionEditAuditRow(BaseModel):
    audit_id: int
    session_id: int
    entity_type: str
    entity_id: int | None = None
    field_name: str
    old_value: str | None = None
    new_value: str | None = None
    edited_at: str


class SessionEditAuditResponse(BaseModel):
    app_session_id: str
    rows: list[SessionEditAuditRow]


class SessionEaEditResetRequest(BaseModel):
    app_session_id: AppSessionId
    ea_activity_id: str | None = None


class SessionEaEditResetResponse(BaseModel):
    app_session_id: str
    reset_counts: dict[str, int]
    recomputed_norm_addressees: list[str]


class SessionEaEditActivityRequest(BaseModel):
    app_session_id: AppSessionId
    activity_id: str | None = None


class SessionEaEditActivityResponse(BaseModel):
    app_session_id: str
    activity_id: str
    lease_seconds: float
    expires_at: float | None = None


class CaseGroupResearchSettingsRequest(BaseModel):
    app_session_id: AppSessionId
    enabled: bool


class CaseGroupResearchSettingsResponse(BaseModel):
    app_session_id: str
    enabled: bool
    status: str = "idle"
    locked: bool = False
    elapsed_seconds: int | None = None


class SessionExportResponse(BaseModel):
    filename: str
    markdown: str


class ComplianceTextExportRequest(BaseModel):
    app_session_id: AppSessionId
    model: str | None = None
    provider: str | None = None
    user_edit_policy: Literal[
        "reject_if_user_edits",
        "use_user_edits",
    ] = USER_EDIT_REJECT


class SessionUndoResponse(BaseModel):
    status: Literal["ok", "no-op"]
    undone_step: str | None = None
    undone_label: str | None = None
    message: str | None = None


UNDO_MESSAGES: dict[str, str] = {
    "total_cost": (
        "Gesamtkosten zurückgesetzt. Manuell bearbeitete EA-Werte bleiben "
        "erhalten und werden beim erneuten Ausführen von Schritt 7 wieder "
        "berücksichtigt."
    ),
    "effort": (
        "Aufwand quantifizieren zurückgesetzt. Die zugehörigen EA-Werte und "
        "manuellen EA-Bearbeitungen wurden gelöscht."
    ),
}


class SessionRunAllRequest(BaseModel):
    app_session_id: AppSessionId
    current_filename: str | None = None
    proposed_filename: str | None = None
    model: str | None = None
    provider: str | None = None


class SessionStepRunRequest(SessionRunAllRequest):
    step_key: str


class SessionRunStepResult(BaseModel):
    key: str
    label: str
    status: Literal["completed", "skipped", "failed"]
    message: str | None = None


class SessionRunAllStartResponse(BaseModel):
    app_session_id: str
    run_id: str
    started: bool
    status: Literal["running", "completed", "failed", "cancelled"]


class SessionRunStatusResponse(BaseModel):
    run_id: str
    app_session_id: str
    status: Literal["running", "completed", "failed", "cancelled"]
    ok: bool | None = None
    steps: list[SessionRunStepResult]
    final_status: SessionStatusResponse | None = None
    current_step: str | None = None
    current_label: str | None = None
    current_norm_addressee: str | None = None
    last_error: str | None = None


class SessionRunCancelResponse(BaseModel):
    run_id: str
    app_session_id: str
    status: Literal["cancelling", "completed", "failed", "cancelled"]
    accepted: bool
    message: str | None = None


class SessionLlmMonitorSnapshotResponse(BaseModel):
    app_session_id: str
    pending: list[dict]
    recent: list[dict]
    events: list[dict] | None = None
    stream_attempts: list[dict] | None = None


class SessionLlmMonitorStreamAttemptResponse(BaseModel):
    app_session_id: str
    attempt: dict


RUN_ALL_STEPS: tuple[tuple[str, str, str], ...] = (
    ("summary", "CCC starten", "summary_ready"),
    ("regulations", "Vorgaben identifizieren", "regulations_ready"),
    ("processes", "Prozesse bündeln", "processes_ready"),
    ("case_groups", "Fallgruppen entwickeln", "case_groups_ready"),
    ("process_steps", "Prozessschritte bestimmen", "process_steps_ready"),
    ("effort", "Aufwand quantifizieren", "effort_ready"),
    ("total_cost", "Gesamtkosten berechnen", "total_cost_ready"),
)
RUN_ALL_STEP_BY_KEY = {key: (label, status_flag) for key, label, status_flag in RUN_ALL_STEPS}


@dataclass(frozen=True)
class _AtomicSinglePromptStep:
    step_key: str
    step_label: str
    prompt_id: str
    query_label: str
    existing_fn: Callable[[int, str], list[dict]]
    build_prompt_fn: Callable[..., tuple[str | None, dict]]
    parse_fn: Callable[..., tuple[list[dict], set[str]]]
    apply_fn: Callable[..., list[dict]]
    query_fn: Callable[..., Awaitable[str | LlmResult]]


_RUN_ALL_LOCKS: dict[str, asyncio.Lock] = {}


@dataclass
class _RunRecord:
    run_id: str
    app_session_id: str
    status: Literal["running", "completed", "failed", "cancelled"] = "running"
    ok: bool | None = None
    steps: list[SessionRunStepResult] = field(default_factory=list)
    final_status: SessionStatusResponse | None = None
    current_step: str | None = None
    current_label: str | None = None
    current_norm_addressee: str | None = None
    last_error: str | None = None
    events: list[tuple[str, dict]] = field(default_factory=list)
    subscribers: set[asyncio.Queue[tuple[str, dict]]] = field(default_factory=set)
    task: asyncio.Task[None] | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_RUNS_BY_ID: dict[str, _RunRecord] = {}
_ACTIVE_RUN_BY_SESSION: dict[str, str] = {}
_RUN_REGISTRY_LOCK = asyncio.Lock()
_MAX_STORED_RUNS = 200


def _ensure_llm_console_enabled() -> None:
    if settings.llm_console_enabled:
        return
    raise HTTPException(status_code=404, detail="Not found")


def _get_run_all_lock(app_session_id: str) -> asyncio.Lock:
    lock = _RUN_ALL_LOCKS.get(app_session_id)
    if lock is None:
        lock = asyncio.Lock()
        _RUN_ALL_LOCKS[app_session_id] = lock
    return lock


def _format_sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _run_snapshot_payload(record: _RunRecord) -> dict:
    return {
        "run_id": record.run_id,
        "app_session_id": record.app_session_id,
        "status": record.status,
        "ok": record.ok,
        "current_step": record.current_step,
        "current_label": record.current_label,
        "current_norm_addressee": record.current_norm_addressee,
        "last_error": record.last_error,
        "steps": [step.model_dump() for step in record.steps],
        "final_status": (
            record.final_status.model_dump() if record.final_status is not None else None
        ),
    }


async def _publish_run_event(run_id: str, event: str, payload: dict) -> None:
    async with _RUN_REGISTRY_LOCK:
        record = _RUNS_BY_ID.get(run_id)
        if record is None:
            return
        record.updated_at = time.time()
        if event == "step_started":
            record.current_step = str(payload.get("key") or "")
            record.current_label = str(payload.get("label") or "")
            record.current_norm_addressee = None
            record.last_error = None
        elif event == "addressee_started":
            norm_addressee = payload.get("norm_addressee")
            record.current_norm_addressee = None if norm_addressee is None else str(norm_addressee)
        elif event == "step_failed":
            step = payload.get("step")
            if isinstance(step, dict):
                message = step.get("message")
                record.last_error = None if message is None else str(message)
        elif event == "run_failed":
            message = payload.get("message")
            if message is not None:
                record.last_error = str(message)
        elif event in {
            "step_completed",
            "step_skipped",
            "run_completed",
            "run_cancelled",
        }:
            if event.startswith("run_"):
                record.current_step = None
                record.current_label = None
                if event in {"run_completed", "run_cancelled"}:
                    record.last_error = None
            record.current_norm_addressee = None
        record.events.append((event, payload))
        subscribers = list(record.subscribers)
    for queue in subscribers:
        try:
            queue.put_nowait((event, payload))
        except asyncio.QueueFull:
            continue


async def _emit_event(
    event_hook: Callable[[str, dict], Awaitable[None] | None] | None,
    event: str,
    payload: dict,
) -> None:
    if event_hook is None:
        return
    maybe_awaitable = event_hook(event, payload)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable


async def _get_run_record(run_id: str) -> _RunRecord:
    async with _RUN_REGISTRY_LOCK:
        record = _RUNS_BY_ID.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record


async def _trim_finished_runs() -> None:
    async with _RUN_REGISTRY_LOCK:
        if len(_RUNS_BY_ID) <= _MAX_STORED_RUNS:
            return
        finished = [
            record
            for record in _RUNS_BY_ID.values()
            if record.status in {"completed", "failed", "cancelled"}
        ]
        finished.sort(key=lambda r: r.updated_at)
        overflow = len(_RUNS_BY_ID) - _MAX_STORED_RUNS
        for record in finished[:overflow]:
            _RUNS_BY_ID.pop(record.run_id, None)


def _as_session_status_response(app_session_id: str) -> SessionStatusResponse:
    status = db.get_session_status(app_session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    step = get_last_completed_step(status)
    failed = _get_latest_failed_step_status(app_session_id, status)
    return SessionStatusResponse(
        **status,
        last_completed_step=step.key if step else None,
        last_completed_label=step.label if step else None,
        last_failed_step=failed["step"] if failed else None,
        last_failed_label=failed["label"] if failed else None,
        last_failed_message=failed["message"] if failed else None,
    )


_FAILED_PROMPT_STEP: dict[str, tuple[str, str, str]] = {
    "law_summary": ("summary", "CCC starten", "summary_ready"),
    "regulations_identification": (
        "regulations",
        "Vorgaben identifizieren",
        "regulations_ready",
    ),
    "process_compilation": ("processes", "Prozesse bündeln", "processes_ready"),
    "case_group_development": (
        "case_groups",
        "Fallgruppen entwickeln",
        "case_groups_ready",
    ),
    "process_step_analysis": (
        "process_steps",
        "Prozessschritte bestimmen",
        "process_steps_ready",
    ),
    "cases_calculation": ("effort", "Aufwand quantifizieren", "effort_ready"),
    "effort_calculation": ("effort", "Aufwand quantifizieren", "effort_ready"),
}


def _format_persisted_atomic_failure(row: dict, detail: str) -> str | None:
    prompt_id = str(row.get("prompt_id") or "")
    mapping = _FAILED_PROMPT_STEP.get(prompt_id)
    norm_addressee = str(row.get("norm_addressee") or "").strip()
    if mapping is None or not norm_addressee:
        return None
    step_key, label, _ready_flag = mapping
    return _format_atomic_step_error(
        step_label=label,
        step_key=step_key,
        norm_addressee=norm_addressee,
        prompt_label=prompt_id,
        detail=detail,
    )


def _format_failed_answer_message(row: dict) -> str | None:
    reason = str(row.get("state_reason") or "").strip()
    error = str(row.get("error") or "").strip()
    error_kind = str(row.get("error_kind") or "").strip()
    if reason.startswith("session_update_failed:"):
        detail = reason.split(":", 1)[1].strip()
        if not detail:
            return None
        return _format_persisted_atomic_failure(row, detail) or detail
    if reason == "query_failed" and error_kind == "cancelled":
        return "Der Schritt wurde abgebrochen. Bitte führen Sie ihn erneut aus."
    if reason == "query_failed" and error:
        return error
    if reason and reason not in {
        "session_reverted",
        "superseded_by_new_attempt",
        "superseded_by_reuse",
        "session_updated",
        "waiting_for_session_update",
        "querying",
    }:
        return reason
    return None


def _get_latest_failed_step_status(
    app_session_id: str,
    status: dict,
) -> dict[str, str] | None:
    session_id = db.get_session_id_by_app_id(app_session_id)
    if session_id is None:
        return None
    seen_prompts: set[str] = set()
    for row in db.list_recent_llm_answers_for_session(session_id, limit=50):
        prompt_id = str(row.get("prompt_id") or "")
        mapping = _FAILED_PROMPT_STEP.get(prompt_id)
        if mapping is None:
            continue
        if prompt_id in seen_prompts:
            continue
        seen_prompts.add(prompt_id)
        if row.get("answer_state") != "invalid":
            continue
        step_key, label, ready_flag = mapping
        if bool(status.get(ready_flag)):
            continue
        message = _format_failed_answer_message(row)
        if not message:
            continue
        return {"step": step_key, "label": label, "message": message}
    return None


def _as_session_pay_rates_response(
    app_session_id: str,
    norm_addressee: str | None = None,
) -> SessionPayRatesResponse:
    session_id = db.get_session_id_by_app_id(app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    resolved = normalize_norm_addressee_or_422(norm_addressee)
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, resolved)
    if pay_rates is None:
        raise HTTPException(status_code=404, detail="Session pay rates not found")
    return SessionPayRatesResponse(
        app_session_id=app_session_id,
        norm_addressee=str(pay_rates["norm_addressee"]),
        editable=bool(pay_rates["editable"]),
        administration_level=(
            None
            if pay_rates["administration_level"] is None
            else str(pay_rates["administration_level"])
        ),
        wage_source_label=(
            None
            if pay_rates.get("wage_source_label") is None
            else str(pay_rates["wage_source_label"])
        ),
        defaults={key: float(value) for key, value in pay_rates["defaults"].items()},
        edited={
            key: (None if value is None else float(value))
            for key, value in pay_rates["edited"].items()
        },
        active={key: float(value) for key, value in pay_rates["active"].items()},
    )


def _validate_pay_rates_update_payload(payload: SessionPayRatesUpdateRequest) -> None:
    resolved = normalize_norm_addressee_or_422(payload.norm_addressee)
    if resolved == CITIZENS:
        raise HTTPException(
            status_code=422,
            detail="Citizens pay rates are not editable",
        )
    if payload.administration_level is not None and resolved != ADMINISTRATION:
        raise HTTPException(
            status_code=422,
            detail="administration_level is only supported for administration",
        )
    if payload.administration_level is not None:
        requested_level = payload.administration_level.strip().lower()
        allowed_levels = {
            str(row.get("administration_level") or "").strip().lower()
            for row in db.list_pay_rate_defaults()
        }
        if requested_level not in allowed_levels:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Unknown administration_level. Allowed values: "
                    + ", ".join(sorted(level for level in allowed_levels if level))
                ),
            )

    edited = {
        "edited_a": payload.edited_a,
        "edited_b": payload.edited_b,
        "edited_c": payload.edited_c,
        "edited_d": payload.edited_d,
    }
    invalid = [field for field, value in edited.items() if value is not None and value < 0]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail="Edited values must be non-negative: " + ", ".join(invalid),
        )


def _resolve_filenames(
    app_session_id: str,
    current_filename: str | None,
    proposed_filename: str | None,
) -> tuple[str | None, str | None]:
    current = current_filename
    proposed = proposed_filename
    session = db.get_session_by_app_id(app_session_id)
    if session:
        if not current and session.get("current_law_id") is not None:
            current_law = db.get_law_by_id(int(session["current_law_id"]))
            if current_law:
                current = str(current_law["file_name"])
        if not proposed and session.get("proposed_law_id") is not None:
            proposed_law = db.get_law_by_id(int(session["proposed_law_id"]))
            if proposed_law:
                proposed = str(proposed_law["file_name"])
    return current, proposed


def _step_error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            if "error" in detail:
                return str(detail["error"])
            return str(detail)
        if detail is None:
            return f"HTTP {exc.status_code}"
        return str(detail)
    message = str(exc).strip()
    return message or exc.__class__.__name__


def _deep_research_attempt_id(research_run_id: int) -> str:
    return f"deep_research:{research_run_id}"


async def _publish_deep_research_monitor_event(
    *,
    app_session_id: str,
    session_id: int,
    research_run_id: int,
    event_type: str,
    agent: str,
    request_context: dict[str, str | None],
    elapsed_ms: int | None = None,
    prompt_chars: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    thought_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
    error: str | None = None,
    error_kind: str | None = None,
    answer_state: str | None = None,
    state_reason: str | None = None,
) -> None:
    event: dict[str, object] = {
        "event_type": event_type,
        "attempt_id": _deep_research_attempt_id(research_run_id),
        "session_id": session_id,
        "prompt_id": DEEP_RESEARCH_MONITOR_PROMPT_ID,
        "model": agent,
        "provider": "gemini",
        "request_id": request_context.get("request_id"),
        "route_method": request_context.get("route_method"),
        "route_path": request_context.get("route_path"),
        "stream_mode": "non_stream",
    }
    for key, value in (
        ("elapsed_ms", elapsed_ms),
        ("prompt_chars", prompt_chars),
        ("input_tokens", input_tokens),
        ("output_tokens", output_tokens),
        ("hidden_thinking_tokens", thought_tokens),
        ("estimated_cost_usd", estimated_cost_usd),
        ("error", error),
        ("error_kind", error_kind),
        ("answer_state", answer_state),
        ("state_reason", state_reason),
    ):
        if value is not None:
            event[key] = value
    await llm_monitor.publish_llm_event(app_session_id=app_session_id, event=event)


def _recent_monitor_rows(session_id: int, limit: int) -> list[dict]:
    rows = [
        *db.list_recent_llm_answers_for_session(session_id, limit=limit),
        *db.list_recent_deep_research_monitor_rows_for_session(session_id, limit=limit),
    ]
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows[: max(1, min(limit, 500))]


async def _harvest_cancelled_deep_research_run(
    *,
    app_session_id: str,
    session_id: int,
    research_run_id: int,
    api_keys: ApiKeys,
) -> None:
    run = db.get_deep_research_run(research_run_id)
    if not run or str(run.get("status") or "") != "cancelled":
        return
    interaction_id = str(run.get("interaction_id") or "").strip()
    if not interaction_id:
        return
    agent = str(run.get("agent") or settings.deep_research_primary_agent)
    try:
        result = await harvest_deep_research_interaction(
            interaction_id=interaction_id,
            api_keys=api_keys,
            agent=agent,
        )
    except Exception as exc:
        current = db.get_deep_research_run(research_run_id)
        if current and str(current.get("status") or "") == "cancelled":
            db.update_deep_research_run(
                research_run_id,
                error=(
                    "Deep Research was cancelled locally; remote harvest failed: "
                    f"{_step_error_message(exc)}"
                ),
            )
        return

    current = db.get_deep_research_run(research_run_id)
    if not current or str(current.get("status") or "") != "cancelled":
        return
    db.update_deep_research_run(
        research_run_id,
        status="cancelled_harvested",
        agent=result.agent,
        interaction_id=result.interaction_id,
        report_md=result.report_text,
        response_json=result.response_json,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        thought_tokens=result.thought_tokens,
        total_tokens=result.total_tokens,
        estimated_cost_usd=result.estimated_cost_usd,
        error="Deep Research was cancelled locally; remote result harvested for audit only.",
    )
    await _publish_deep_research_monitor_event(
        app_session_id=app_session_id,
        session_id=session_id,
        research_run_id=research_run_id,
        event_type="llm_query_failed",
        agent=result.agent,
        request_context={},
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        thought_tokens=result.thought_tokens,
        estimated_cost_usd=result.estimated_cost_usd,
        answer_state="invalid",
        state_reason="cancelled_harvested",
        error="Deep Research was cancelled locally; remote result harvested for audit only.",
        error_kind="cancelled_harvested",
    )


def _start_cancelled_deep_research_harvest(
    *,
    app_session_id: str,
    session_id: int,
    research_run_id: int,
    api_keys: ApiKeys,
) -> None:
    task = asyncio.create_task(
        _harvest_cancelled_deep_research_run(
            app_session_id=app_session_id,
            session_id=session_id,
            research_run_id=research_run_id,
            api_keys=api_keys,
        )
    )
    _CANCELLED_DEEP_RESEARCH_HARVEST_TASKS.add(task)
    task.add_done_callback(_CANCELLED_DEEP_RESEARCH_HARVEST_TASKS.discard)


def _promote_effort_answers_for_retry(app_session_id: str) -> None:
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        return
    db.promote_waiting_session_update_answers_by_prompt(
        int(session["session_id"]),
        [PromptId.CASES_CALCULATION, PromptId.EFFORT_CALCULATION],
    )


def _cancel_running_deep_research_for_session(
    *,
    app_session_id: str,
    api_keys: ApiKeys,
) -> None:
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        return
    session_id = int(session["session_id"])
    run = db.get_latest_deep_research_run(session_id, CASE_GROUP_RESEARCH_PURPOSE)
    if not run or str(run.get("status") or "") != "running":
        return
    research_run_id = int(run["research_run_id"])
    db.update_deep_research_run(
        research_run_id,
        status="cancelled",
        error="Deep Research was cancelled by the user.",
    )
    _start_cancelled_deep_research_harvest(
        app_session_id=app_session_id,
        session_id=session_id,
        research_run_id=research_run_id,
        api_keys=api_keys,
    )


async def _run_case_group_deep_research(
    *,
    app_session_id: str,
    session_id: int,
    api_keys: ApiKeys,
    apply_result: bool = True,
) -> dict | None:
    latest = db.get_latest_deep_research_run(session_id, CASE_GROUP_RESEARCH_PURPOSE)
    latest_status = str(latest.get("status") or "") if latest else "idle"
    if latest_status == "parsed":
        return latest
    if latest_status == "completed" and latest and latest.get("report_md"):
        if not apply_result:
            return latest
        apply_deep_research_case_metrics(
            session_id=session_id,
            report_text=str(latest["report_md"]),
            research_run_id=int(latest["research_run_id"]),
        )
        return db.get_latest_deep_research_run(session_id, CASE_GROUP_RESEARCH_PURPOSE)
    if latest_status == "running":
        raise HTTPException(
            status_code=409,
            detail="Deep Research for case groups is already running.",
        )

    prompt = build_deep_research_cases_prompt(app_session_id=app_session_id)
    research_run_id = db.create_deep_research_run(
        session_id=session_id,
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent=settings.deep_research_primary_agent,
        status="running",
        prompt_text=prompt,
    )
    request_context = get_request_context()
    started = time.perf_counter()
    await _publish_deep_research_monitor_event(
        app_session_id=app_session_id,
        session_id=session_id,
        research_run_id=research_run_id,
        event_type="llm_query_started",
        agent=settings.deep_research_primary_agent,
        request_context=request_context,
        prompt_chars=len(prompt),
    )
    query_succeeded = False
    try:
        result = await run_deep_research(
            prompt=prompt,
            api_keys=api_keys,
            on_interaction_started=lambda agent, interaction_id: db.update_deep_research_run(
                research_run_id,
                agent=agent,
                interaction_id=interaction_id,
            ),
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        db.update_deep_research_run(
            research_run_id,
            status="completed",
            agent=result.agent,
            interaction_id=result.interaction_id,
            report_md=result.report_text,
            response_json=result.response_json,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            thought_tokens=result.thought_tokens,
            total_tokens=result.total_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
        )
        await _publish_deep_research_monitor_event(
            app_session_id=app_session_id,
            session_id=session_id,
            research_run_id=research_run_id,
            event_type="llm_query_succeeded",
            agent=result.agent,
            request_context=request_context,
            elapsed_ms=elapsed_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            thought_tokens=result.thought_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
        )
        query_succeeded = True
        try:
            if apply_result:
                apply_deep_research_case_metrics(
                    session_id=session_id,
                    report_text=result.report_text,
                    research_run_id=research_run_id,
                )
        except Exception as exc:
            await _publish_deep_research_monitor_event(
                app_session_id=app_session_id,
                session_id=session_id,
                research_run_id=research_run_id,
                event_type="llm_apply_failed",
                agent=result.agent,
                request_context=request_context,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                error=_step_error_message(exc),
                error_kind="deep_research_apply_failed",
                answer_state="invalid",
                state_reason="session_update_failed",
            )
            raise
        if apply_result:
            await _publish_deep_research_monitor_event(
                app_session_id=app_session_id,
                session_id=session_id,
                research_run_id=research_run_id,
                event_type="llm_apply_succeeded",
                agent=result.agent,
                request_context=request_context,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                thought_tokens=result.thought_tokens,
                estimated_cost_usd=result.estimated_cost_usd,
                answer_state="active",
                state_reason="session_updated",
            )
        return db.get_latest_deep_research_run(session_id, CASE_GROUP_RESEARCH_PURPOSE)
    except asyncio.CancelledError:
        db.update_deep_research_run(
            research_run_id,
            status="cancelled",
            error="Deep Research was cancelled by the run-all task.",
        )
        _start_cancelled_deep_research_harvest(
            app_session_id=app_session_id,
            session_id=session_id,
            research_run_id=research_run_id,
            api_keys=api_keys,
        )
        await _publish_deep_research_monitor_event(
            app_session_id=app_session_id,
            session_id=session_id,
            research_run_id=research_run_id,
            event_type="llm_query_failed",
            agent=settings.deep_research_primary_agent,
            request_context=request_context,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            error="Deep Research was cancelled by the run-all task.",
            error_kind="cancelled",
        )
        raise
    except DeepResearchError as exc:
        db.update_deep_research_run(
            research_run_id,
            status="failed",
            error=str(exc),
        )
        await _publish_deep_research_monitor_event(
            app_session_id=app_session_id,
            session_id=session_id,
            research_run_id=research_run_id,
            event_type="llm_query_failed",
            agent=settings.deep_research_primary_agent,
            request_context=request_context,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            error=str(exc),
            error_kind="deep_research_query_failed",
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        db.update_deep_research_run(
            research_run_id,
            status="failed",
            error=_step_error_message(exc),
        )
        if not query_succeeded:
            await _publish_deep_research_monitor_event(
                app_session_id=app_session_id,
                session_id=session_id,
                research_run_id=research_run_id,
                event_type="llm_query_failed",
                agent=settings.deep_research_primary_agent,
                request_context=request_context,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                error=_step_error_message(exc),
                error_kind="deep_research_failed",
            )
        raise


def _result_key(prompt_id: str, norm_addressee: str) -> str:
    return f"{prompt_id}:{norm_addressee}"


def _format_atomic_step_error(
    *,
    step_label: str,
    step_key: str,
    norm_addressee: str,
    prompt_label: str,
    detail: str,
) -> str:
    display_addressee = {
        ADMINISTRATION: "Verwaltung",
        BUSINESS: "Wirtschaft",
        CITIZENS: "Bürgerinnen und Bürger",
    }.get(norm_addressee, norm_addressee)
    return (
        f"Die Antwort für {display_addressee} konnte nicht verarbeitet werden. "
        "Bitte führen Sie den Schritt erneut aus.\n"
        f"Technische Details: {step_label} / {step_key} / {display_addressee} / "
        f"{prompt_label}: {detail}"
    )


def _promote_pending_retry(answer_ids: list[int]) -> None:
    for answer_id in answer_ids:
        db.update_llm_answer_state_reason(
            answer_id,
            "waiting_for_paired_retry",
            state=db.LLM_ANSWER_STATE_PENDING,
        )


async def _run_atomic_single_prompt_step(
    *,
    step: _AtomicSinglePromptStep,
    session_id: int,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
    event_hook: Callable[[str, dict], Awaitable[None] | None] | None = None,
) -> dict[str, dict]:
    prepared: dict[str, dict] = {}
    specs: list[LlmPromptSpec] = []
    pending_answer_ids: dict[str, int] = {}
    query_results: dict[str, LlmResult] = {}

    for norm_addressee in SUPPORTED_NORM_ADDRESSEES:
        existing = step.existing_fn(session_id, norm_addressee)
        if existing:
            prepared[norm_addressee] = {
                "status": "existing",
                "existing": existing,
            }
            continue

        prompt, context = step.build_prompt_fn(
            session_id=session_id,
            norm_addressee=norm_addressee,
        )
        if context.get("status") == "skipped":
            prepared[norm_addressee] = {"status": "skipped", "context": context}
            continue
        if not prompt:
            raise HTTPException(
                status_code=500,
                detail=f"No prompt built for {step.step_key}/{norm_addressee}",
            )
        await _emit_event(
            event_hook,
            "addressee_started",
            {"key": step.step_key, "norm_addressee": norm_addressee},
        )

        key = _result_key(step.prompt_id, norm_addressee)
        reusable = db.get_reusable_pending_llm_answer(
            session_id=session_id,
            prompt_id=step.prompt_id,
            model=model,
            provider=payload.provider,
            prompt_sha256=prompt_sha256(prompt),
            norm_addressee=norm_addressee,
        )
        if reusable:
            pending_answer_ids[key] = int(reusable["answer_id"])
            query_results[key] = LlmResult(text=str(reusable["answer_text"]))
        else:
            specs.append(
                LlmPromptSpec(
                    prompt_id=step.prompt_id,
                    query_label=f"{step.query_label}/{norm_addressee}",
                    prompt=prompt,
                    norm_addressee=norm_addressee,
                    result_key=key,
                )
            )
        prepared[norm_addressee] = {"status": "ready", "context": context, "key": key}

    if specs:
        staged_ids, staged_results, query_errors = await query_and_stage_llm_answers_parallel(
            session_id=session_id,
            specs=specs,
            api_keys=api_keys,
            model=model,
            provider=payload.provider,
            query_fn=step.query_fn,
        )
        pending_answer_ids.update(staged_ids)
        query_results.update(staged_results)
        if query_errors:
            _promote_pending_retry(list(pending_answer_ids.values()))
            detail = "; ".join(query_errors)
            await _emit_event(
                event_hook,
                "addressee_failed",
                {
                    "key": step.step_key,
                    "norm_addressee": "unknown",
                    "message": detail,
                },
            )
            raise HTTPException(status_code=502, detail=detail)

    parsed_by_addressee: dict[str, list[dict]] = {}
    try:
        for norm_addressee, info in prepared.items():
            if info["status"] != "ready":
                continue
            key = info["key"]
            answer_id = pending_answer_ids[key]
            result = query_results[key]
            parsed, fallback_kinds = step.parse_fn(
                response_text=result.text,
                norm_addressee=norm_addressee,
                context=info["context"],
            )
            for fallback_kind in sorted(fallback_kinds):
                mark_llm_parse_fallback(
                    answer_id=answer_id,
                    session_id=session_id,
                    prompt_id=step.prompt_id,
                    fallback_kind=fallback_kind,
                )
            parsed_by_addressee[norm_addressee] = parsed
    except Exception as exc:
        failed_addressee = norm_addressee
        failed_key = prepared[failed_addressee]["key"]
        failed_answer_id = pending_answer_ids.get(failed_key)
        if failed_answer_id is not None:
            mark_llm_answer_apply_failed(answer_id=failed_answer_id, exc=exc)
        sibling_ids = [
            answer_id
            for key, answer_id in pending_answer_ids.items()
            if key != failed_key
        ]
        _promote_pending_retry(sibling_ids)
        detail = _format_atomic_step_error(
            step_label=step.step_label,
            step_key=step.step_key,
            norm_addressee=failed_addressee,
            prompt_label=step.prompt_id,
            detail=_step_error_message(exc),
        )
        await _emit_event(
            event_hook,
            "addressee_failed",
            {
                "key": step.step_key,
                "norm_addressee": failed_addressee,
                "prompt_id": step.prompt_id,
                "message": detail,
            },
        )
        raise HTTPException(
            status_code=getattr(exc, "status_code", 422),
            detail=detail,
        ) from exc

    created_by_addressee: dict[str, dict] = {}
    applied_answer_ids: list[tuple[int, str]] = []
    try:
        with db.transaction():
            for norm_addressee, info in prepared.items():
                if info["status"] == "ready":
                    created = step.apply_fn(
                        session_id=session_id,
                        norm_addressee=norm_addressee,
                        parsed=parsed_by_addressee[norm_addressee],
                        context=info["context"],
                    )
                    created_by_addressee[norm_addressee] = {
                        "status": "applied",
                        "created": created,
                    }
                    mark_llm_answer_applied(
                        answer_id=pending_answer_ids[info["key"]],
                        session_id=session_id,
                        prompt_id=step.prompt_id,
                        publish=False,
                    )
                    applied_answer_ids.append(
                        (pending_answer_ids[info["key"]], step.prompt_id)
                    )
                else:
                    created_by_addressee[norm_addressee] = info
    except Exception as exc:
        for answer_id in pending_answer_ids.values():
            mark_llm_answer_apply_failed(answer_id=answer_id, exc=exc)
        raise

    for answer_id, prompt_id in applied_answer_ids:
        publish_llm_answer_applied(answer_id=answer_id, prompt_id=prompt_id)

    for norm_addressee in SUPPORTED_NORM_ADDRESSEES:
        if prepared.get(norm_addressee, {}).get("status") == "ready":
            await _emit_event(
                event_hook,
                "addressee_completed",
                {"key": step.step_key, "norm_addressee": norm_addressee},
            )
    return created_by_addressee


async def _run_atomic_effort_step(
    *,
    app_session_id: str,
    session_id: int,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
    event_hook: Callable[[str, dict], Awaitable[None] | None] | None = None,
) -> None:
    use_deep_research = db.get_case_group_research_enabled(session_id)
    contexts: dict[str, dict] = {}
    specs: list[LlmPromptSpec] = []
    pending_answer_ids: dict[str, int] = {}
    query_results: dict[str, LlmResult] = {}

    for norm_addressee in SUPPORTED_NORM_ADDRESSEES:
        context = effort_router.prepare_effort_calculation(
            session_id=session_id,
            norm_addressee=norm_addressee,
            skip_cases_calculation=use_deep_research,
        )
        contexts[norm_addressee] = context
        if context["status"] in {"skipped", "existing"}:
            continue
        await _emit_event(
            event_hook,
            "addressee_started",
            {"key": "effort", "norm_addressee": norm_addressee},
        )

        prompt_pairs = [
            (PromptId.EFFORT_CALCULATION, "EFFORT_CALCULATION", context["effort_prompt"])
        ]
        if not use_deep_research:
            prompt_pairs.insert(
                0,
                (PromptId.CASES_CALCULATION, "CASES_CALCULATION", context["cases_prompt"]),
            )
        for prompt_id, query_label, prompt in prompt_pairs:
            key = _result_key(prompt_id, norm_addressee)
            prompt_hash = prompt_sha256(prompt)
            db.promote_waiting_session_update_llm_answers_to_paired_retry(
                session_id=session_id,
                prompts=[
                    (
                        prompt_id,
                        norm_addressee,
                        prompt_hash,
                        model,
                        payload.provider,
                    )
                ],
            )
            reusable = db.get_reusable_pending_llm_answer(
                session_id=session_id,
                prompt_id=prompt_id,
                model=model,
                provider=payload.provider,
                prompt_sha256=prompt_hash,
                norm_addressee=norm_addressee,
            )
            if reusable:
                pending_answer_ids[key] = int(reusable["answer_id"])
                query_results[key] = LlmResult(text=str(reusable["answer_text"]))
                continue
            specs.append(
                LlmPromptSpec(
                    prompt_id=prompt_id,
                    query_label=f"{query_label}/{norm_addressee}",
                    prompt=prompt,
                    norm_addressee=norm_addressee,
                    result_key=key,
                )
            )

    async def _stage_missing_answers() -> tuple[dict[str, int], dict[str, LlmResult], list[str]]:
        if not specs:
            return {}, {}, []
        return await query_and_stage_llm_answers_parallel(
            session_id=session_id,
            specs=specs,
            api_keys=api_keys,
            model=model,
            provider=payload.provider,
            query_fn=effort_router.query_llm,
        )

    deep_research_run: dict | None = None
    if use_deep_research:
        latest_research = db.get_latest_deep_research_run(
            session_id,
            CASE_GROUP_RESEARCH_PURPOSE,
        )
        if str((latest_research or {}).get("status") or "") == "running":
            db.promote_waiting_session_update_answers_by_prompt(
                session_id,
                [PromptId.EFFORT_CALCULATION],
            )
            raise HTTPException(
                status_code=409,
                detail="Deep Research for case groups is already running.",
            )
        staged_task = asyncio.create_task(_stage_missing_answers())
        research_task = asyncio.create_task(
            _run_case_group_deep_research(
                app_session_id=app_session_id,
                session_id=session_id,
                api_keys=api_keys,
                apply_result=False,
            )
        )
        done, pending = await asyncio.wait(
            {staged_task, research_task},
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in done:
            exc = task.exception()
            if exc is None:
                continue
            for pending_task in pending:
                pending_task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            _promote_pending_retry(list(pending_answer_ids.values()))
            raise exc
        if pending:
            more_done = await asyncio.gather(*pending, return_exceptions=True)
            for result in more_done:
                if isinstance(result, Exception):
                    _promote_pending_retry(list(pending_answer_ids.values()))
                    raise result
        staged_ids, staged_results, query_errors = staged_task.result()
        deep_research_run = research_task.result()
    else:
        staged_ids, staged_results, query_errors = await _stage_missing_answers()

    pending_answer_ids.update(staged_ids)
    query_results.update(staged_results)
    if query_errors:
        _promote_pending_retry(list(pending_answer_ids.values()))
        raise HTTPException(status_code=502, detail="; ".join(query_errors))

    deep_research_payload: tuple[dict, list] | None = None
    if use_deep_research:
        if not deep_research_run or not deep_research_run.get("report_md"):
            raise HTTPException(status_code=422, detail="No Deep Research report parsed")
        if str(deep_research_run.get("status") or "") == "completed":
            deep_research_payload = validate_deep_research_case_metrics(
                session_id=session_id,
                report_text=str(deep_research_run["report_md"]),
            )

    parsed_by_addressee: dict[str, tuple[list[dict], list[dict]]] = {}
    try:
        for norm_addressee, context in contexts.items():
            if context["status"] != "ready":
                continue
            effort_key = _result_key(PromptId.EFFORT_CALCULATION, norm_addressee)
            cases_key = _result_key(PromptId.CASES_CALCULATION, norm_addressee)
            parsed_by_addressee[norm_addressee] = effort_router.parse_effort_calculation_outputs(
                session_id=session_id,
                norm_addressee=norm_addressee,
                context=context,
                cases_text=(
                    None
                    if use_deep_research
                    else query_results[cases_key].text
                ),
                effort_text=query_results[effort_key].text,
                cases_answer_id=(
                    None
                    if use_deep_research
                    else pending_answer_ids[cases_key]
                ),
                effort_answer_id=pending_answer_ids[effort_key],
            )
    except Exception as exc:
        failed_addressee = norm_addressee
        failed_ids = [
            pending_answer_ids[key]
            for key in (
                _result_key(PromptId.CASES_CALCULATION, failed_addressee),
                _result_key(PromptId.EFFORT_CALCULATION, failed_addressee),
            )
            if key in pending_answer_ids
        ]
        for answer_id in failed_ids:
            mark_llm_answer_apply_failed(answer_id=answer_id, exc=exc)
        sibling_ids = [
            answer_id
            for answer_id in pending_answer_ids.values()
            if answer_id not in set(failed_ids)
        ]
        _promote_pending_retry(sibling_ids)
        detail = _format_atomic_step_error(
            step_label=RUN_ALL_STEP_BY_KEY["effort"][0],
            step_key="effort",
            norm_addressee=failed_addressee,
            prompt_label=PromptId.EFFORT_CALCULATION,
            detail=_step_error_message(exc),
        )
        await _emit_event(
            event_hook,
            "addressee_failed",
            {
                "key": "effort",
                "norm_addressee": failed_addressee,
                "prompt_id": PromptId.EFFORT_CALCULATION,
                "message": detail,
            },
        )
        raise HTTPException(
            status_code=getattr(exc, "status_code", 422),
            detail=detail,
        ) from exc

    applied_answer_ids: list[tuple[int, str]] = []
    try:
        with db.transaction():
            if deep_research_payload is not None and deep_research_run is not None:
                data, parsed_research = deep_research_payload
                apply_validated_deep_research_case_metrics(
                    session_id=session_id,
                    data=data,
                    parsed=parsed_research,
                    report_text=str(deep_research_run["report_md"]),
                    research_run_id=int(deep_research_run["research_run_id"]),
                )
            for norm_addressee, (parsed_cases, parsed_effort) in parsed_by_addressee.items():
                effort_router.apply_effort_calculation_outputs(
                    session_id=session_id,
                    norm_addressee=norm_addressee,
                    parsed_cases=parsed_cases,
                    parsed_effort=parsed_effort,
                    skip_cases_calculation=use_deep_research,
                )
                if not use_deep_research:
                    mark_llm_answer_applied(
                        answer_id=pending_answer_ids[
                            _result_key(PromptId.CASES_CALCULATION, norm_addressee)
                        ],
                        session_id=session_id,
                        prompt_id=PromptId.CASES_CALCULATION,
                        publish=False,
                    )
                    applied_answer_ids.append(
                        (
                            pending_answer_ids[
                                _result_key(PromptId.CASES_CALCULATION, norm_addressee)
                            ],
                            PromptId.CASES_CALCULATION,
                        )
                    )
                mark_llm_answer_applied(
                    answer_id=pending_answer_ids[
                        _result_key(PromptId.EFFORT_CALCULATION, norm_addressee)
                    ],
                    session_id=session_id,
                    prompt_id=PromptId.EFFORT_CALCULATION,
                    publish=False,
                )
                applied_answer_ids.append(
                    (
                        pending_answer_ids[
                            _result_key(PromptId.EFFORT_CALCULATION, norm_addressee)
                        ],
                        PromptId.EFFORT_CALCULATION,
                    )
                )
            for norm_addressee, context in contexts.items():
                if context["status"] == "ready":
                    effort_router.refresh_effort_tiles(
                        session_id=session_id,
                        norm_addressee=norm_addressee,
                    )
    except Exception as exc:
        for answer_id in pending_answer_ids.values():
            mark_llm_answer_apply_failed(answer_id=answer_id, exc=exc)
        raise

    for answer_id, prompt_id in applied_answer_ids:
        publish_llm_answer_applied(answer_id=answer_id, prompt_id=prompt_id)

    for norm_addressee, context in contexts.items():
        if context["status"] == "ready":
            await _emit_event(
                event_hook,
                "addressee_completed",
                {"key": "effort", "norm_addressee": norm_addressee},
            )


async def _run_single_step(
    step_key: str,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
    event_hook: Callable[[str, dict], Awaitable[None] | None] | None = None,
) -> None:
    addressee_labels = {
        ADMINISTRATION: "administration",
        BUSINESS: "business",
        CITIZENS: "citizens",
    }

    async def _run_for_supported_addressees(
        runner: Callable[[str], Awaitable[None]],
    ) -> None:
        for norm_addressee in SUPPORTED_NORM_ADDRESSEES:
            await _emit_event(
                event_hook,
                "addressee_started",
                {
                    "key": step_key,
                    "norm_addressee": norm_addressee,
                },
            )
            try:
                await runner(norm_addressee)
                await _emit_event(
                    event_hook,
                    "addressee_completed",
                    {
                        "key": step_key,
                        "norm_addressee": norm_addressee,
                    },
                )
            except HTTPException as exc:
                detail = _step_error_message(exc)
                await _emit_event(
                    event_hook,
                    "addressee_failed",
                    {
                        "key": step_key,
                        "norm_addressee": norm_addressee,
                        "message": detail,
                    },
                )
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=(
                        f"{addressee_labels.get(norm_addressee, norm_addressee)}: {detail}"
                    ),
                ) from exc
            except Exception as exc:
                detail = _step_error_message(exc)
                await _emit_event(
                    event_hook,
                    "addressee_failed",
                    {
                        "key": step_key,
                        "norm_addressee": norm_addressee,
                        "message": detail,
                    },
                )
                raise RuntimeError(
                    f"{addressee_labels.get(norm_addressee, norm_addressee)}: {detail}"
                ) from exc

    if step_key == "summary":
        current_filename, proposed_filename = _resolve_filenames(
            payload.app_session_id,
            payload.current_filename,
            payload.proposed_filename,
        )
        if not proposed_filename:
            raise HTTPException(
                status_code=422,
                detail="Missing proposed_filename for summary step",
            )
        summary_payload = regulations_router.RegulationSummaryRequest(
            filename=proposed_filename,
            current_filename=current_filename,
            app_session_id=payload.app_session_id,
            model=model,
            provider=payload.provider,
        )
        await regulations_router.summarize_regulation(summary_payload, api_keys)
        return

    if step_key == "regulations":
        identify_payload = regulations_router.RegulationIdentifyRequest(
            app_session_id=payload.app_session_id,
            model=model,
            provider=payload.provider,
        )
        await regulations_router.identify_regulations(identify_payload, api_keys)
        return

    if step_key == "processes":
        session_id = db.get_session_id_by_app_id(payload.app_session_id)
        if session_id is None:
            raise HTTPException(status_code=404, detail="Session not found")
        await _run_atomic_single_prompt_step(
            step=_AtomicSinglePromptStep(
                step_key="processes",
                step_label=RUN_ALL_STEP_BY_KEY["processes"][0],
                prompt_id=PromptId.PROCESS_COMPILATION,
                query_label="PROCESS_COMPILATION",
                existing_fn=db.list_processes_for_session_and_addressee,
                build_prompt_fn=processes_router.build_process_compilation_prompt,
                parse_fn=processes_router.parse_process_compilation_answer,
                apply_fn=processes_router.apply_process_compilation,
                query_fn=processes_router.query_llm,
            ),
            session_id=session_id,
            payload=payload,
            api_keys=api_keys,
            model=model,
            event_hook=event_hook,
        )
        return

    if step_key == "case_groups":
        session_id = db.get_session_id_by_app_id(payload.app_session_id)
        if session_id is None:
            raise HTTPException(status_code=404, detail="Session not found")
        await _run_atomic_single_prompt_step(
            step=_AtomicSinglePromptStep(
                step_key="case_groups",
                step_label=RUN_ALL_STEP_BY_KEY["case_groups"][0],
                prompt_id=PromptId.CASE_GROUP_DEVELOPMENT,
                query_label="CASE_GROUP_DEVELOPMENT",
                existing_fn=db.list_case_groups_for_session_and_addressee,
                build_prompt_fn=case_groups_router.build_case_group_development_prompt,
                parse_fn=case_groups_router.parse_case_group_development_answer,
                apply_fn=case_groups_router.apply_case_group_development,
                query_fn=case_groups_router.query_llm,
            ),
            session_id=session_id,
            payload=payload,
            api_keys=api_keys,
            model=model,
            event_hook=event_hook,
        )
        return

    if step_key == "process_steps":
        session_id = db.get_session_id_by_app_id(payload.app_session_id)
        if session_id is None:
            raise HTTPException(status_code=404, detail="Session not found")
        await _run_atomic_single_prompt_step(
            step=_AtomicSinglePromptStep(
                step_key="process_steps",
                step_label=RUN_ALL_STEP_BY_KEY["process_steps"][0],
                prompt_id=PromptId.PROCESS_STEP_ANALYSIS,
                query_label="PROCESS_STEP_ANALYSIS",
                existing_fn=db.list_process_steps_for_session_and_addressee,
                build_prompt_fn=process_steps_router.build_process_step_analysis_prompt,
                parse_fn=process_steps_router.parse_process_step_analysis_answer,
                apply_fn=process_steps_router.apply_process_step_analysis,
                query_fn=process_steps_router.query_llm,
            ),
            session_id=session_id,
            payload=payload,
            api_keys=api_keys,
            model=model,
            event_hook=event_hook,
        )
        return

    if step_key == "effort":
        session_id = db.get_session_id_by_app_id(payload.app_session_id)
        if session_id is None:
            raise HTTPException(status_code=404, detail="Session not found")
        await _run_atomic_effort_step(
            app_session_id=payload.app_session_id,
            session_id=session_id,
            payload=payload,
            api_keys=api_keys,
            model=model,
            event_hook=event_hook,
        )
        return

    if step_key == "total_cost":
        async def _run_costs(norm_addressee: str) -> None:
            costs_payload = costs_router.CostComputationRequest(
                app_session_id=payload.app_session_id,
                norm_addressee=norm_addressee,
            )
            await costs_router.compute_costs(costs_payload)

        await _run_for_supported_addressees(_run_costs)
        return

    raise HTTPException(status_code=400, detail=f"Unknown step: {step_key}")


async def _execute_run_all_steps(
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
    event_hook: Callable[[str, dict], Awaitable[None] | None] | None = None,
) -> tuple[list[SessionRunStepResult], SessionStatusResponse, bool]:
    step_results: list[SessionRunStepResult] = []
    for step_key, step_label, status_flag in RUN_ALL_STEPS:
        if asyncio.current_task() and asyncio.current_task().cancelled():
            raise asyncio.CancelledError
        current_status = db.get_session_status(payload.app_session_id)
        if not current_status:
            raise HTTPException(status_code=404, detail="Session not found")
        if bool(current_status.get(status_flag)):
            step_result = SessionRunStepResult(
                key=step_key,
                label=step_label,
                status="skipped",
                message="Step already complete",
            )
            step_results.append(step_result)
            await _emit_event(
                event_hook,
                "step_skipped",
                {
                    "key": step_key,
                    "label": step_label,
                    "step": step_result.model_dump(),
                    "session_status": _as_session_status_response(
                        payload.app_session_id
                    ).model_dump(),
                },
            )
            continue

        await _emit_event(
            event_hook,
            "step_started",
            {"key": step_key, "label": step_label},
        )

        try:
            await _run_single_step(
                step_key,
                payload,
                api_keys,
                model,
                event_hook=event_hook,
            )
        except Exception as exc:
            step_result = SessionRunStepResult(
                key=step_key,
                label=step_label,
                status="failed",
                message=_step_error_message(exc),
            )
            step_results.append(step_result)
            await _emit_event(
                event_hook,
                "step_failed",
                {
                    "key": step_key,
                    "label": step_label,
                    "step": step_result.model_dump(),
                    "session_status": _as_session_status_response(
                        payload.app_session_id
                    ).model_dump(),
                },
            )
            break

        updated_status = db.get_session_status(payload.app_session_id)
        if updated_status and bool(updated_status.get(status_flag)):
            step_result = SessionRunStepResult(
                key=step_key,
                label=step_label,
                status="completed",
            )
            step_results.append(step_result)
            await _emit_event(
                event_hook,
                "step_completed",
                {
                    "key": step_key,
                    "label": step_label,
                    "step": step_result.model_dump(),
                    "session_status": _as_session_status_response(
                        payload.app_session_id
                    ).model_dump(),
                },
            )
        else:
            step_result = SessionRunStepResult(
                key=step_key,
                label=step_label,
                status="failed",
                message="Step did not update session state as expected",
            )
            step_results.append(step_result)
            await _emit_event(
                event_hook,
                "step_failed",
                {
                    "key": step_key,
                    "label": step_label,
                    "step": step_result.model_dump(),
                    "session_status": _as_session_status_response(
                        payload.app_session_id
                    ).model_dump(),
                },
            )
            break

    final_status = _as_session_status_response(payload.app_session_id)
    ok = all(step.status != "failed" for step in step_results)
    await _emit_event(
        event_hook,
        "run_completed" if ok else "run_failed",
        {
            "ok": ok,
            "steps": [step.model_dump() for step in step_results],
            "final_status": final_status.model_dump(),
        },
    )
    return step_results, final_status, ok


async def _execute_single_step(
    *,
    step_key: str,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
    event_hook: Callable[[str, dict], Awaitable[None] | None] | None = None,
) -> tuple[list[SessionRunStepResult], SessionStatusResponse, bool]:
    step_definition = RUN_ALL_STEP_BY_KEY.get(step_key)
    if step_definition is None:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_key}")
    step_label, status_flag = step_definition
    current_status = db.get_session_status(payload.app_session_id)
    if not current_status:
        raise HTTPException(status_code=404, detail="Session not found")
    if bool(current_status.get(status_flag)):
        step_result = SessionRunStepResult(
            key=step_key,
            label=step_label,
            status="skipped",
            message="Step already complete",
        )
        final_status = _as_session_status_response(payload.app_session_id)
        await _emit_event(
            event_hook,
            "step_skipped",
            {
                "key": step_key,
                "label": step_label,
                "step": step_result.model_dump(),
                "session_status": final_status.model_dump(),
            },
        )
        await _emit_event(
            event_hook,
            "run_completed",
            {
                "ok": True,
                "steps": [step_result.model_dump()],
                "final_status": final_status.model_dump(),
            },
        )
        return [step_result], final_status, True

    await _emit_event(event_hook, "step_started", {"key": step_key, "label": step_label})
    try:
        await _run_single_step(
            step_key,
            payload,
            api_keys,
            model,
            event_hook=event_hook,
        )
    except Exception as exc:
        step_result = SessionRunStepResult(
            key=step_key,
            label=step_label,
            status="failed",
            message=_step_error_message(exc),
        )
        final_status = _as_session_status_response(payload.app_session_id)
        await _emit_event(
            event_hook,
            "step_failed",
            {
                "key": step_key,
                "label": step_label,
                "step": step_result.model_dump(),
                "session_status": final_status.model_dump(),
            },
        )
        await _emit_event(
            event_hook,
            "run_failed",
            {
                "ok": False,
                "steps": [step_result.model_dump()],
                "final_status": final_status.model_dump(),
                "message": step_result.message,
            },
        )
        return [step_result], final_status, False

    updated_status = db.get_session_status(payload.app_session_id)
    if updated_status and bool(updated_status.get(status_flag)):
        step_result = SessionRunStepResult(
            key=step_key,
            label=step_label,
            status="completed",
        )
        final_status = _as_session_status_response(payload.app_session_id)
        await _emit_event(
            event_hook,
            "step_completed",
            {
                "key": step_key,
                "label": step_label,
                "step": step_result.model_dump(),
                "session_status": final_status.model_dump(),
            },
        )
        await _emit_event(
            event_hook,
            "run_completed",
            {
                "ok": True,
                "steps": [step_result.model_dump()],
                "final_status": final_status.model_dump(),
            },
        )
        return [step_result], final_status, True

    step_result = SessionRunStepResult(
        key=step_key,
        label=step_label,
        status="failed",
        message="Step did not update session state as expected",
    )
    final_status = _as_session_status_response(payload.app_session_id)
    await _emit_event(
        event_hook,
        "step_failed",
        {
            "key": step_key,
            "label": step_label,
            "step": step_result.model_dump(),
            "session_status": final_status.model_dump(),
        },
    )
    await _emit_event(
        event_hook,
        "run_failed",
        {
            "ok": False,
            "steps": [step_result.model_dump()],
            "final_status": final_status.model_dump(),
            "message": step_result.message,
        },
    )
    return [step_result], final_status, False


@router.post("", response_model=SessionUpsertResponse)
async def upsert_session(payload: SessionUpsertRequest) -> SessionUpsertResponse:
    _, created = db.upsert_session(payload.app_session_id, payload.llm_model)
    return SessionUpsertResponse(
        app_session_id=payload.app_session_id,
        created=created,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(limit: int = Query(default=50, ge=1, le=200)) -> SessionListResponse:
    sessions = db.list_sessions(limit=limit)
    return SessionListResponse(sessions=sessions)


@router.get("/status", response_model=SessionStatusResponse)
async def session_status(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION
) -> SessionStatusResponse:
    return _as_session_status_response(app_session_id)


def _session_id_or_404(app_session_id: str) -> int:
    session_id = db.get_session_id_by_app_id(app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_id


def _ensure_ea_edit_allowed(app_session_id: str) -> None:
    status = db.get_session_status(app_session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    if not bool(status.get("total_cost_ready")):
        raise HTTPException(
            status_code=409,
            detail="EA-Bearbeitung ist erst nach berechneten Gesamtkosten möglich.",
        )


@router.post("/ea-edit-activity/acquire", response_model=SessionEaEditActivityResponse)
async def acquire_ea_edit_activity(
    payload: SessionEaEditActivityRequest,
) -> SessionEaEditActivityResponse:
    session_id = _session_id_or_404(payload.app_session_id)
    _ensure_ea_edit_allowed(payload.app_session_id)
    try:
        activity = begin_session_activity(
            session_id=session_id,
            activity_type="ea_edit",
            label="EA bearbeiten",
            ttl_seconds=EA_EDIT_LEASE_SECONDS,
        )
    except SessionActivityConflict as exc:
        raise_session_activity_conflict(exc)
    except SessionActivityUnavailable as exc:
        raise_session_activity_unavailable(exc)
    return SessionEaEditActivityResponse(
        app_session_id=payload.app_session_id,
        activity_id=activity.activity_id,
        lease_seconds=EA_EDIT_LEASE_SECONDS,
        expires_at=activity.expires_at,
    )


@router.post("/ea-edit-activity/heartbeat", response_model=SessionEaEditActivityResponse)
async def heartbeat_ea_edit_activity(
    payload: SessionEaEditActivityRequest,
) -> SessionEaEditActivityResponse:
    session_id = _session_id_or_404(payload.app_session_id)
    try:
        activity = refresh_session_activity(
            session_id=session_id,
            activity_id=payload.activity_id or "",
            activity_type="ea_edit",
            ttl_seconds=EA_EDIT_LEASE_SECONDS,
        )
    except SessionActivityConflict as exc:
        raise_session_activity_conflict(exc)
    except SessionActivityUnavailable as exc:
        raise_session_activity_unavailable(exc)
    return SessionEaEditActivityResponse(
        app_session_id=payload.app_session_id,
        activity_id=activity.activity_id,
        lease_seconds=EA_EDIT_LEASE_SECONDS,
        expires_at=activity.expires_at,
    )


@router.post("/ea-edit-activity/release")
async def release_ea_edit_activity(payload: SessionEaEditActivityRequest) -> dict:
    session_id = _session_id_or_404(payload.app_session_id)
    if payload.activity_id:
        release_session_activity(
            session_id=session_id,
            activity_id=payload.activity_id,
            activity_type="ea_edit",
        )
    return {"ok": True}


@router.get("/pay-rates", response_model=SessionPayRatesResponse)
async def session_pay_rates(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    norm_addressee: str | None = None,
) -> SessionPayRatesResponse:
    return _as_session_pay_rates_response(app_session_id, norm_addressee=norm_addressee)


@router.post("/pay-rates", response_model=SessionPayRatesResponse)
async def session_pay_rates_update(
    payload: SessionPayRatesUpdateRequest,
) -> SessionPayRatesResponse:
    _validate_pay_rates_update_payload(payload)
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    async with guarded_session_activity(
        session_id=session_id,
        activity_type="ea_edit",
        label="EA bearbeiten",
        owner_activity_id=payload.ea_activity_id,
    ):
        try:
            changed = db.update_session_pay_rate_edits_for_addressee(
                session_id=session_id,
                norm_addressee=normalize_norm_addressee_or_422(payload.norm_addressee),
                administration_level=payload.administration_level,
                edited={
                    "a": payload.edited_a,
                    "b": payload.edited_b,
                    "c": payload.edited_c,
                    "d": payload.edited_d,
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not changed:
        raise HTTPException(status_code=422, detail="No changes in payload")
    return _as_session_pay_rates_response(
        payload.app_session_id,
        norm_addressee=payload.norm_addressee,
    )


def _as_session_wage_rates_response(
    app_session_id: str, session_id: int, resolved: str
) -> SessionWageRatesResponse:
    rows = db.list_session_wage_rate_rows(session_id, resolved)
    return SessionWageRatesResponse(
        app_session_id=app_session_id,
        norm_addressee=resolved,
        rows=[SessionWageRateRow(**row) for row in rows],
    )


@router.get("/wage-rates", response_model=SessionWageRatesResponse)
async def session_wage_rates(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    norm_addressee: str | None = None,
) -> SessionWageRatesResponse:
    session_id = db.get_session_id_by_app_id(app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    resolved = normalize_norm_addressee_or_422(norm_addressee)
    return _as_session_wage_rates_response(app_session_id, session_id, resolved)


@router.post("/wage-rates", response_model=SessionWageRatesResponse)
async def session_wage_rates_update(
    payload: SessionWageRateUpdateRequest,
) -> SessionWageRatesResponse:
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    resolved = normalize_norm_addressee_or_422(payload.norm_addressee)
    if resolved == CITIZENS:
        raise HTTPException(status_code=422, detail="Citizens wage rates are not editable")
    validate_wage_source_kind(payload.wage_source_kind, resolved)
    if payload.hourly_rate_edited is not None:
        if payload.hourly_rate_edited < 0:
            raise HTTPException(status_code=422, detail="hourly_rate_edited must not be negative")
        if db.get_model_hourly_rate(
            resolved, payload.wage_source_value, payload.qualification
        ) is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Unknown wage combination: {payload.wage_source_value!r} / "
                    f"{payload.qualification!r} for {resolved!r}"
                ),
            )
    async with guarded_session_activity(
        session_id=session_id,
        activity_type="ea_edit",
        label="EA bearbeiten",
        owner_activity_id=payload.ea_activity_id,
    ):
        changed = db.upsert_session_wage_rate_override(
            session_id=session_id,
            norm_addressee=resolved,
            wage_source_kind=payload.wage_source_kind,
            wage_source_value=payload.wage_source_value,
            qualification=payload.qualification,
            hourly_rate_edited=payload.hourly_rate_edited,
        )
    if not changed:
        raise HTTPException(status_code=422, detail="No changes in payload")
    return _as_session_wage_rates_response(payload.app_session_id, session_id, resolved)


@router.get("/edit-audit", response_model=SessionEditAuditResponse)
async def session_edit_audit(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    limit: int = Query(default=200, ge=1, le=1000),
) -> SessionEditAuditResponse:
    session_id = db.get_session_id_by_app_id(app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = db.list_edit_audit_for_session(session_id=session_id, limit=limit)
    return SessionEditAuditResponse(app_session_id=app_session_id, rows=rows)


@router.post("/ea-edits/reset", response_model=SessionEaEditResetResponse)
async def reset_session_ea_edits(
    payload: SessionEaEditResetRequest,
) -> SessionEaEditResetResponse:
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    async with guarded_session_activity(
        session_id=session_id,
        activity_type="ea_edit",
        label="EA bearbeiten",
        owner_activity_id=payload.ea_activity_id,
    ):
        status = db.get_session_status(payload.app_session_id) or {}
        ready_by_addressee = status.get("total_cost_ready_by_addressee")
        if not isinstance(ready_by_addressee, dict):
            ready_by_addressee = {}
        reset_counts = db.reset_all_ea_edit_overrides(session_id)
        recomputed: list[str] = []
        for norm_addressee in SUPPORTED_NORM_ADDRESSEES:
            if not bool(ready_by_addressee.get(norm_addressee)):
                continue
            costs_router.compute_total_cost_for_session(
                app_session_id=payload.app_session_id,
                norm_addressee=norm_addressee,
            )
            recomputed.append(norm_addressee)
    return SessionEaEditResetResponse(
        app_session_id=payload.app_session_id,
        reset_counts=reset_counts,
        recomputed_norm_addressees=recomputed,
    )


def _research_settings_response(app_session_id: str) -> CaseGroupResearchSettingsResponse:
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])
    status = db.get_latest_deep_research_run_status(session_id, "case_group_metrics")
    session_status = db.get_session_status(app_session_id) or {}
    return CaseGroupResearchSettingsResponse(
        app_session_id=app_session_id,
        enabled=bool(session.get("case_group_research_enabled")),
        status=status,
        locked=(
            status not in {"idle", "failed", "cancelled", "cancelled_harvested"}
            or bool(session_status.get("effort_ready"))
            or bool(session_status.get("total_cost_ready"))
        ),
        elapsed_seconds=db.get_latest_deep_research_run_elapsed_seconds(
            session_id,
            CASE_GROUP_RESEARCH_PURPOSE,
        ),
    )


@router.get("/case-group-research", response_model=CaseGroupResearchSettingsResponse)
async def case_group_research_settings(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
) -> CaseGroupResearchSettingsResponse:
    return _research_settings_response(app_session_id)


@router.post("/case-group-research", response_model=CaseGroupResearchSettingsResponse)
async def case_group_research_settings_update(
    payload: CaseGroupResearchSettingsRequest,
) -> CaseGroupResearchSettingsResponse:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])
    current_enabled = bool(session.get("case_group_research_enabled"))
    if current_enabled == payload.enabled:
        return _research_settings_response(payload.app_session_id)
    session_status = db.get_session_status(payload.app_session_id) or {}
    if bool(session_status.get("effort_ready")) or bool(session_status.get("total_cost_ready")):
        raise HTTPException(
            status_code=409,
            detail="Deep Research mode is locked after effort has been calculated. Revert effort to change it.",
        )
    status = db.get_latest_deep_research_run_status(session_id, "case_group_metrics")
    if status not in {"idle", "failed", "cancelled", "cancelled_harvested"}:
        raise HTTPException(
            status_code=409,
            detail="Deep Research mode is locked after a research run has started. Revert effort to change it.",
        )
    db.update_case_group_research_enabled(session_id, payload.enabled)
    return _research_settings_response(payload.app_session_id)


@router.get("/export", response_model=SessionExportResponse)
async def export_session(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION
) -> SessionExportResponse:
    # Currently not exposed in the frontend. The Mermaid/Markdown export needs
    # rework before becoming user-facing again: it renders only the Verwaltung
    # view and the Markdown output is not polished enough for users.
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    info = db.get_session_export_info(app_session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")

    tiles = build_session_tiles_snapshot(session)

    def escape_label(value: str) -> str:
        escaped = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("[", "&#91;")
            .replace("]", "&#93;")
        )
        return escaped.replace("\n", "<br/>")

    tiles_by_column: dict[int, list] = {}
    for tile in tiles:
        tiles_by_column.setdefault(tile.column, []).append(tile)
    for column_tiles in tiles_by_column.values():
        column_tiles.sort(key=lambda t: (t.row, t.id))

    column_labels = {
        0: "Gesetz",
        1: "Vorgaben",
        2: "Prozesse",
        3: "Fallgruppen",
    }

    mermaid_lines = ["```mermaid", "flowchart LR"]
    for column in sorted(tiles_by_column.keys()):
        column_tiles = tiles_by_column[column]
        if not column_tiles:
            continue
        if any(tile.id == "total_cost" for tile in column_tiles):
            label = "Kosten"
        else:
            label = column_labels.get(column, "Prozessschritte")
        mermaid_lines.append(f'  subgraph col_{column}["{label}"]')
        mermaid_lines.append("    direction TB")
        for tile in column_tiles:
            title = escape_label(tile.title)
            text = escape_label(tile.text or "")
            label_text = f"<b>{title}</b>"
            if text:
                label_text = f"{label_text}<br/>{text}"
            mermaid_lines.append(f'    {tile.id}["{label_text}"]')
        mermaid_lines.append("  end")

    edges = set()
    for tile in tiles:
        for source in tile.link_from_tile:
            edges.add((source, tile.id))
    for source, target in sorted(edges):
        mermaid_lines.append(f"  {source} --> {target}")
    mermaid_lines.append("```")

    export_title = f"Session {info['app_session_id']} Export"
    model_name = info.get("llm_model") or "-"
    markdown = "\n\n".join(
        [
            f"## {export_title}",
            f"**LLM-Modell:** {model_name}",
            f"**Aktuelles Gesetz:** {info.get('current_file_name') or '-'}",
            f"**Gesetzesvorschlag:** {info.get('proposed_file_name') or '-'}",
            "\n".join(mermaid_lines),
        ]
    ).strip()

    filename = f"ccc_session_{info['app_session_id']}.md"
    return SessionExportResponse(filename=filename, markdown=markdown)


def _compliance_export_filename(app_session_id: str, user_edit_policy: str) -> str:
    suffix = ""
    if user_edit_policy == USER_EDIT_USE:
        suffix = "_ea_bearbeitet"
    return f"ccc_vorblatt_begruendung_{app_session_id}{suffix}.pdf"


def _compliance_metadata_for_pdf(
    *,
    app_session_id: str,
    model: str | None,
    provider: str | None,
    source_snapshot_sha256: str,
    used_deep_research: bool,
    deep_research_excerpt_status: str | None,
    has_user_edits: bool,
    used_user_edits: bool,
    reused: bool,
    created_at: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    hidden_thinking_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
) -> dict[str, object]:
    if not has_user_edits:
        user_edit_status = "Keine bearbeiteten EA-Werte im Quellstand."
    elif used_user_edits:
        user_edit_status = "Beteiligte EA-Werte wurden mit Anwenderbearbeitungen exportiert."
    else:
        user_edit_status = "Anwenderbearbeitungen waren vorhanden."
    if used_deep_research:
        dr_status = (
            "Verwendet"
            if deep_research_excerpt_status == "extracted"
            else "Verwendet; Berichtsteile 1/2 konnten nicht extrahiert werden"
        )
    else:
        dr_status = "Nicht verwendet"
    return {
        "app_session_id": app_session_id,
        "generated_at": created_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": model,
        "provider": provider,
        "reuse_status": "gespeicherter Export wiederverwendet" if reused else "neu generiert",
        "deep_research_status": dr_status,
        "user_edit_status": user_edit_status,
        "source_snapshot_sha256": source_snapshot_sha256[:12],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "hidden_thinking_tokens": hidden_thinking_tokens,
        "estimated_cost_usd": estimated_cost_usd,
    }


@router.post("/compliance-text-export")
async def export_compliance_text(
    payload: ComplianceTextExportRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> Response:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )
    status = db.get_session_status(payload.app_session_id)
    if not status or not bool(status.get("total_cost_ready")):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "session_not_complete",
                "message": "Vorblatt und Begründung export requires a completed session.",
            },
        )
    user_edit_policy = normalize_user_edit_policy(payload.user_edit_policy)
    context = build_compliance_export_context(
        app_session_id=payload.app_session_id,
        session_id=session_id,
        user_edit_policy=user_edit_policy,
    )
    if context.has_user_edits and user_edit_policy == USER_EDIT_REJECT:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "user_edits_present",
                "message": "EA values have been edited by the user.",
                "options": [USER_EDIT_USE],
            },
        )
    cached = db.get_latest_compliance_text_export(
        session_id,
        context.snapshot_sha256,
        user_edit_policy,
    )
    if cached:
        metadata_raw = cached.get("metadata_json")
        try:
            stored_metadata = json.loads(metadata_raw) if metadata_raw else {}
        except (TypeError, json.JSONDecodeError):
            stored_metadata = {}
        if not isinstance(stored_metadata, dict):
            stored_metadata = {}
        pdf_metadata = _compliance_metadata_for_pdf(
            app_session_id=payload.app_session_id,
            model=cached.get("model"),
            provider=cached.get("provider"),
            source_snapshot_sha256=str(cached["source_snapshot_sha256"]),
            used_deep_research=bool(cached.get("used_deep_research")),
            deep_research_excerpt_status=stored_metadata.get(
                "deep_research_report_excerpt_status"
            ),
            has_user_edits=bool(stored_metadata.get("has_user_edits")),
            used_user_edits=bool(cached.get("used_user_edits")),
            reused=True,
            created_at=cached.get("created_at"),
            input_tokens=cached.get("input_tokens"),
            output_tokens=cached.get("output_tokens"),
            hidden_thinking_tokens=cached.get("hidden_thinking_tokens"),
            estimated_cost_usd=cached.get("estimated_cost_usd"),
        )
        pdf = _render_research_report_pdf(
            str(cached["generated_markdown"]),
            f"Vorblatt und Begründung {payload.app_session_id}",
            metadata_lines=_format_compliance_export_metadata_lines(pdf_metadata),
        )
        filename = _compliance_export_filename(payload.app_session_id, user_edit_policy)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    example_values = {
        f"beispiel_{index}": str(example.get("body_md") or "")
        for index, example in enumerate(context.examples, start=1)
    }
    for index in range(len(context.examples) + 1, 4):
        example_values[f"beispiel_{index}"] = ""
    prompt = render_prompt(
        PromptId.COMPLIANCE_TEXT_EXTRACTION,
        session_id=session_id,
        consolidated_session_json=json.dumps(
            context.snapshot,
            ensure_ascii=False,
            indent=2,
        ),
        optional_deep_research_part_1_2=context.optional_deep_research_part_1_2,
        **example_values,
    )
    answer_id, llm_result = await query_and_stage_or_http(
        session_id=session_id,
        prompt_id=PromptId.COMPLIANCE_TEXT_EXTRACTION,
        prompt=prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
        query_fn=query_llm,
    )
    metadata = {
        **context.metadata,
        "model": model,
        "provider": payload.provider,
    }

    def _apply_compliance_export() -> None:
        with db.transaction():
            db.insert_compliance_text_export(
                session_id=session_id,
                llm_answer_id=answer_id,
                status="succeeded",
                model=model,
                provider=payload.provider,
                prompt_text=prompt,
                generated_markdown=llm_result.text,
                source_snapshot_json=context.snapshot,
                source_snapshot_sha256=context.snapshot_sha256,
                used_deep_research=context.used_deep_research,
                deep_research_run_id=context.deep_research_run_id,
                used_user_edits=context.used_user_edits,
                user_edit_policy=user_edit_policy,
                metadata_json=metadata,
                input_tokens=llm_result.input_tokens,
                output_tokens=llm_result.output_tokens,
                hidden_thinking_tokens=llm_result.hidden_thinking_tokens,
                estimated_cost_usd=llm_result.estimated_cost_usd,
            )
            mark_llm_answer_applied(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.COMPLIANCE_TEXT_EXTRACTION,
            )

    run_with_answer_apply_guard(answer_id=answer_id, apply_fn=_apply_compliance_export)
    pdf_metadata = _compliance_metadata_for_pdf(
        app_session_id=payload.app_session_id,
        model=model,
        provider=payload.provider,
        source_snapshot_sha256=context.snapshot_sha256,
        used_deep_research=context.used_deep_research,
        deep_research_excerpt_status=context.deep_research_excerpt_status,
        has_user_edits=context.has_user_edits,
        used_user_edits=context.used_user_edits,
        reused=False,
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        hidden_thinking_tokens=llm_result.hidden_thinking_tokens,
        estimated_cost_usd=llm_result.estimated_cost_usd,
    )
    pdf = _render_research_report_pdf(
        llm_result.text,
        f"Vorblatt und Begründung {payload.app_session_id}",
        metadata_lines=_format_compliance_export_metadata_lines(pdf_metadata),
    )
    filename = _compliance_export_filename(payload.app_session_id, user_edit_policy)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _split_pipe_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in stripped:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _is_pipe_table_separator(line: str) -> bool:
    cells = _split_pipe_table_row(line)
    if len(cells) < 2:
        return False
    for cell in cells:
        marker = cell.strip()
        if len(marker) < 3:
            return False
        marker = marker.strip(":")
        if not marker or any(char != "-" for char in marker):
            return False
    return True


def _parse_pipe_table(block: str) -> list[list[str]] | None:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) < 3 or "|" not in lines[0] or not _is_pipe_table_separator(lines[1]):
        return None
    rows = [_split_pipe_table_row(lines[0])]
    expected_columns = len(rows[0])
    if expected_columns < 2:
        return None
    body_rows = [_split_pipe_table_row(line) for line in lines[2:]]
    if not body_rows:
        return None
    for row in body_rows:
        if len(row) != expected_columns:
            return None
    rows.extend(body_rows)
    return rows


def _should_render_research_pdf_bold(escaped_text: str) -> bool:
    plain_text = html.unescape(escaped_text).strip()
    if not plain_text:
        return False
    if len(plain_text) > 70:
        return False
    if plain_text.lower().startswith("fallgruppe") and len(plain_text) > 40:
        return False
    return True


def _research_pdf_inline_markup(text: str) -> str:
    escaped = html.escape(text).replace("\n", "<br/>")
    parts = escaped.split("**")
    if len(parts) == 1:
        return _linkify_research_pdf_urls(escaped)
    rendered: list[str] = []
    for index, part in enumerate(parts):
        linked_part = _linkify_research_pdf_urls(part)
        if index % 2 == 1 and _should_render_research_pdf_bold(part):
            rendered.append(f"<b>{linked_part}</b>")
        else:
            rendered.append(linked_part)
    return "".join(rendered)


def _is_research_pdf_heading(text: str) -> bool:
    heading = text.lstrip("#").strip()
    if not heading:
        return False
    if "\n" in heading:
        return False
    if re.match(r"^\d+\.\s+", heading):
        return False
    if len(heading) > 85:
        return False
    if heading.count(".") > 1 and len(heading) > 60:
        return False
    return True


def _strip_markdown_heading_prefix(text: str) -> str:
    return re.sub(r"^#{1,6}\s*", "", text, count=1).strip()


def _linkify_research_pdf_urls(escaped_text: str) -> str:
    url_pattern = re.compile(r"https?://[^\s<]+")

    def replace(match: re.Match[str]) -> str:
        url = match.group(0)
        trailing = ""
        while url and url[-1] in ".,;:)]]":
            trailing = f"{url[-1]}{trailing}"
            url = url[:-1]
        if not url:
            return match.group(0)
        return f'<link href="{url}"><font color="blue">{url}</font></link>{trailing}'

    return url_pattern.sub(replace, escaped_text)


def _format_research_report_metadata_lines(metadata: dict[str, object]) -> list[str]:
    lines = [
        "<b>Hinweis:</b> Dieser Deep-Research-Bericht wurde KI-gestuetzt erzeugt. "
        "Die genannten Zahlen, Quellen und Schlussfolgerungen sollten vor einer offiziellen "
        "Verwendung fachlich geprueft werden.",
    ]
    for label, value in (
        ("Session", metadata.get("app_session_id")),
        ("Erstellt", metadata.get("generated_at")),
        ("Agent", metadata.get("agent")),
        ("Status", metadata.get("status")),
    ):
        if value:
            lines.append(f"<b>{label}:</b> {html.escape(str(value))}")
    token_parts = [
        f"in {metadata.get('input_tokens')}" if metadata.get("input_tokens") is not None else None,
        f"out {metadata.get('output_tokens')}" if metadata.get("output_tokens") is not None else None,
        (
            f"thinking {metadata.get('thought_tokens')}"
            if metadata.get("thought_tokens") is not None
            else None
        ),
        f"total {metadata.get('total_tokens')}" if metadata.get("total_tokens") is not None else None,
    ]
    tokens = " / ".join(part for part in token_parts if part)
    if tokens:
        lines.append(f"<b>Token:</b> {html.escape(tokens)}")
    cost = metadata.get("estimated_cost_usd")
    if cost is not None:
        try:
            lines.append(f"<b>Geschaetzte API-Kosten:</b> ${float(cost):.4f}")
        except (TypeError, ValueError):
            lines.append(f"<b>Geschaetzte API-Kosten:</b> {html.escape(str(cost))}")
    return lines


def _format_compliance_export_metadata_lines(metadata: dict[str, object]) -> list[str]:
    lines = [
        "<b>Hinweis:</b> Dieser Vorblatt-/Begruendungsentwurf wurde KI-gestuetzt "
        "erzeugt und muss vor einer offiziellen Verwendung fachlich und rechtlich "
        "geprueft werden.",
        "<b>Analyseumfang:</b> Die Darstellung umfasst ausschliesslich jaehrlichen "
        "Erfuellungsaufwand. Einmaliger Erfuellungsaufwand ist nicht Gegenstand "
        "dieser Analyse.",
        "<b>Verwaltung:</b> Fuer die Verwaltung werden ausschliesslich Effekte auf "
        "die Bundesverwaltung dargestellt; Laender und Kommunen sind nicht "
        "Gegenstand dieser Analyse.",
    ]
    for label, value in (
        ("Session", metadata.get("app_session_id")),
        ("Erstellt", metadata.get("generated_at")),
        ("Modell", metadata.get("model")),
        ("Provider", metadata.get("provider")),
        ("Export", metadata.get("reuse_status")),
        ("Deep Research", metadata.get("deep_research_status")),
        ("EA-Werte", metadata.get("user_edit_status")),
        ("Quellstand", metadata.get("source_snapshot_sha256")),
    ):
        if value:
            lines.append(f"<b>{label}:</b> {html.escape(str(value))}")
    token_parts = [
        f"in {metadata.get('input_tokens')}" if metadata.get("input_tokens") is not None else None,
        f"out {metadata.get('output_tokens')}" if metadata.get("output_tokens") is not None else None,
        (
            f"thinking {metadata.get('hidden_thinking_tokens')}"
            if metadata.get("hidden_thinking_tokens") is not None
            else None
        ),
    ]
    tokens = " / ".join(part for part in token_parts if part)
    if tokens:
        lines.append(f"<b>Token:</b> {html.escape(tokens)}")
    cost = metadata.get("estimated_cost_usd")
    if cost is not None:
        try:
            lines.append(f"<b>Geschaetzte API-Kosten:</b> ${float(cost):.4f}")
        except (TypeError, ValueError):
            lines.append(f"<b>Geschaetzte API-Kosten:</b> {html.escape(str(cost))}")
    return lines


def _render_research_report_pdf(
    report_md: str,
    title: str,
    metadata: dict[str, object] | None = None,
    metadata_lines: list[str] | None = None,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:  # pragma: no cover - exercised only without optional dep.
        raise HTTPException(
            status_code=500,
            detail={
                "error": "render_failed",
                "message": "PDF rendering requires reportlab. Please install project requirements.",
            },
        ) from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title=title,
    )
    styles = getSampleStyleSheet()
    table_cell_style = ParagraphStyle(
        "ResearchTableCell",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )
    available_width = A4[0] - doc.leftMargin - doc.rightMargin
    story = [Paragraph(html.escape(title), styles["Title"]), Spacer(1, 12)]
    if metadata or metadata_lines:
        rendered_metadata_lines = (
            metadata_lines
            if metadata_lines is not None
            else _format_research_report_metadata_lines(metadata or {})
        )
        metadata_box = Table(
            [[Paragraph("<br/>".join(rendered_metadata_lines), styles["BodyText"])]],
            colWidths=[available_width],
        )
        metadata_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([metadata_box, Spacer(1, 12)])
    for block in report_md.split("\n\n"):
        text = block.strip()
        if not text:
            continue
        if text.startswith("#") and _is_research_pdf_heading(text):
            heading = text.lstrip("#").strip()
            story.append(Paragraph(html.escape(heading), styles["Heading2"]))
        elif table_rows := _parse_pipe_table(text):
            column_count = len(table_rows[0])
            table_data = [
                [
                    Paragraph(_research_pdf_inline_markup(cell), table_cell_style)
                    for cell in row
                ]
                for row in table_rows
            ]
            table = Table(
                table_data,
                colWidths=[available_width / column_count] * column_count,
                repeatRows=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(table)
        else:
            story.append(
                Paragraph(
                    _research_pdf_inline_markup(_strip_markdown_heading_prefix(text)),
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 8))
    try:
        def add_page_number(canvas, document) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.drawRightString(
                document.pagesize[0] - document.rightMargin,
                18,
                f"Seite {document.page}",
            )
            canvas.restoreState()

        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    except Exception as exc:  # pragma: no cover - reportlab internals.
        raise HTTPException(
            status_code=500,
            detail={"error": "render_failed", "message": str(exc)},
        ) from exc
    return buffer.getvalue()


@router.get("/deep-research-report")
async def download_deep_research_report(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    format: Literal["pdf", "md"] = "pdf",
) -> Response:
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    run = db.get_latest_deep_research_run(
        int(session["session_id"]),
        CASE_GROUP_RESEARCH_PURPOSE,
    )
    if not run:
        raise HTTPException(status_code=404, detail="No Deep Research report for session")
    status = str(run.get("status") or "")
    if status not in {"completed", "parsed"}:
        raise HTTPException(
            status_code=409,
            detail=f"Deep Research report is not ready yet (status: {status or 'idle'}).",
        )
    report_md = str(run.get("report_md") or "").strip()
    if not report_md:
        raise HTTPException(status_code=404, detail="Deep Research report is empty")

    base_filename = f"ccc_deep_research_{app_session_id}"
    if format == "md":
        return Response(
            content=report_md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_filename}.md"'},
        )
    pdf = _render_research_report_pdf(
        report_md,
        f"Deep Research Report {app_session_id}",
        metadata={
            "app_session_id": app_session_id,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "agent": run.get("agent"),
            "status": status,
            "input_tokens": run.get("input_tokens"),
            "output_tokens": run.get("output_tokens"),
            "thought_tokens": run.get("thought_tokens"),
            "total_tokens": run.get("total_tokens"),
            "estimated_cost_usd": run.get("estimated_cost_usd"),
        },
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{base_filename}.pdf"'},
    )


@router.post("/undo", response_model=SessionUndoResponse)
async def undo_last_step(payload: SessionUndoRequest) -> SessionUndoResponse:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    status = db.get_session_status(payload.app_session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])

    async with _RUN_REGISTRY_LOCK:
        active_run_id = _ACTIVE_RUN_BY_SESSION.get(payload.app_session_id)
        if active_run_id:
            active = _RUNS_BY_ID.get(active_run_id)
            if active and active.status == "running":
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Zurücksetzen ist während einer laufenden Ausführung nicht "
                        "möglich. Bitte den Lauf zuerst abbrechen."
                    ),
                )
            _ACTIVE_RUN_BY_SESSION.pop(payload.app_session_id, None)

    step = get_last_completed_step(status)
    if not step:
        return SessionUndoResponse(status="no-op", message="No completed steps")

    async with guarded_session_activity(
        session_id=session_id,
        activity_type="workflow",
        label=f"{step.label} zurücksetzen",
        ttl_seconds=WORKFLOW_LEASE_SECONDS,
    ):
        with db.transaction():
            undo_step(session_id, step.key)

    return SessionUndoResponse(
        status="ok",
        undone_step=step.key,
        undone_label=step.label,
        message=UNDO_MESSAGES.get(step.key),
    )


async def _mark_background_run_terminal(
    *,
    run_id: str,
    app_session_id: str,
    status: Literal["failed", "cancelled"],
    event_name: Literal["run_failed", "run_cancelled"],
    message: str,
) -> None:
    final_status: SessionStatusResponse | None = None
    try:
        final_status = _as_session_status_response(app_session_id)
    except HTTPException:
        final_status = None

    async with _RUN_REGISTRY_LOCK:
        record = _RUNS_BY_ID.get(run_id)
        if record is not None:
            record.status = status
            record.ok = False
            record.updated_at = time.time()
            record.final_status = final_status
            if _ACTIVE_RUN_BY_SESSION.get(record.app_session_id) == run_id:
                _ACTIVE_RUN_BY_SESSION.pop(record.app_session_id, None)
            steps = [step.model_dump() for step in record.steps]
        else:
            steps = []

    await _publish_run_event(
        run_id,
        event_name,
        {
            "ok": False,
            "steps": steps,
            "final_status": final_status.model_dump() if final_status else None,
            "message": message,
        },
    )
    await _trim_finished_runs()


def _release_workflow_activity(session_id: int | None, activity_id: str) -> None:
    if session_id is not None:
        db.clear_session_activity(session_id, activity_id)


async def _run_all_background(
    run_id: str,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
    workflow_activity_id: str,
) -> None:
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    try:
        trace_token = None
        if llm_trace.trace_enabled_by_env():
            trace_token = llm_trace.start_run(
                request_id=run_id,
                route_method="BACKGROUND",
                route_path=f"/sessions/{payload.app_session_id}/run-all",
                app_session_id=payload.app_session_id,
            )
        lock = _get_run_all_lock(payload.app_session_id)
        try:
            start_record = await _get_run_record(run_id)
            await _publish_run_event(
                run_id,
                "snapshot",
                _run_snapshot_payload(start_record),
            )
            async with lock:
                steps, final_status, ok = await _execute_run_all_steps(
                    payload=payload,
                    api_keys=api_keys,
                    model=model,
                    event_hook=lambda event, data: _publish_run_event(run_id, event, data),
                )
        except asyncio.CancelledError:
            _promote_effort_answers_for_retry(payload.app_session_id)
            await _mark_background_run_terminal(
                run_id=run_id,
                app_session_id=payload.app_session_id,
                status="cancelled",
                event_name="run_cancelled",
                message="Run cancelled by user",
            )
            if trace_token is not None:
                try:
                    llm_trace.flush_run(trace_token, status_code=499)
                except Exception:
                    pass
            return
        except Exception as exc:
            await _mark_background_run_terminal(
                run_id=run_id,
                app_session_id=payload.app_session_id,
                status="failed",
                event_name="run_failed",
                message=_step_error_message(exc),
            )
            if trace_token is not None:
                try:
                    llm_trace.flush_run(trace_token, status_code=500)
                except Exception:
                    pass
            return

        async with _RUN_REGISTRY_LOCK:
            record = _RUNS_BY_ID.get(run_id)
            if record is not None:
                record.steps = steps
                record.final_status = final_status
                record.ok = ok
                record.status = "completed" if ok else "failed"
                record.updated_at = time.time()
                if _ACTIVE_RUN_BY_SESSION.get(record.app_session_id) == run_id:
                    _ACTIVE_RUN_BY_SESSION.pop(record.app_session_id, None)

        record_after = await _get_run_record(run_id)
        await _publish_run_event(
            run_id,
            "snapshot",
            _run_snapshot_payload(record_after),
        )
        await _trim_finished_runs()
        if trace_token is not None:
            try:
                llm_trace.flush_run(trace_token, status_code=200 if ok else 500)
            except Exception:
                pass
    finally:
        _release_workflow_activity(session_id, workflow_activity_id)


async def _run_single_step_background(
    run_id: str,
    step_key: str,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
    workflow_activity_id: str,
) -> None:
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    try:
        lock = _get_run_all_lock(payload.app_session_id)
        try:
            start_record = await _get_run_record(run_id)
            await _publish_run_event(
                run_id,
                "snapshot",
                _run_snapshot_payload(start_record),
            )
            async with lock:
                steps, final_status, ok = await _execute_single_step(
                    step_key=step_key,
                    payload=payload,
                    api_keys=api_keys,
                    model=model,
                    event_hook=lambda event, data: _publish_run_event(run_id, event, data),
                )
        except asyncio.CancelledError:
            _promote_effort_answers_for_retry(payload.app_session_id)
            await _mark_background_run_terminal(
                run_id=run_id,
                app_session_id=payload.app_session_id,
                status="cancelled",
                event_name="run_cancelled",
                message="Run cancelled by user",
            )
            return
        except Exception as exc:
            await _mark_background_run_terminal(
                run_id=run_id,
                app_session_id=payload.app_session_id,
                status="failed",
                event_name="run_failed",
                message=_step_error_message(exc),
            )
            return

        async with _RUN_REGISTRY_LOCK:
            record = _RUNS_BY_ID.get(run_id)
            if record is not None:
                record.steps = steps
                record.final_status = final_status
                record.ok = ok
                record.status = "completed" if ok else "failed"
                record.updated_at = time.time()
                if _ACTIVE_RUN_BY_SESSION.get(record.app_session_id) == run_id:
                    _ACTIVE_RUN_BY_SESSION.pop(record.app_session_id, None)

        record_after = await _get_run_record(run_id)
        await _publish_run_event(
            run_id,
            "snapshot",
            _run_snapshot_payload(record_after),
        )
        await _trim_finished_runs()
    finally:
        _release_workflow_activity(session_id, workflow_activity_id)


@router.post("/step-runs/start", response_model=SessionRunAllStartResponse)
async def start_step_run(
    payload: SessionStepRunRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> SessionRunAllStartResponse:
    if payload.step_key not in RUN_ALL_STEP_BY_KEY:
        raise HTTPException(status_code=400, detail=f"Unknown step: {payload.step_key}")
    _session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )
    workflow_activity_id: str | None = None

    async with _RUN_REGISTRY_LOCK:
        active_run_id = _ACTIVE_RUN_BY_SESSION.get(payload.app_session_id)
        if active_run_id:
            active = _RUNS_BY_ID.get(active_run_id)
            if active and active.status == "running":
                return SessionRunAllStartResponse(
                    app_session_id=payload.app_session_id,
                    run_id=active_run_id,
                    started=False,
                    status="running",
                )
            _ACTIVE_RUN_BY_SESSION.pop(payload.app_session_id, None)

        try:
            workflow_activity = begin_session_activity(
                session_id=_session_id,
                activity_type="workflow",
                label=RUN_ALL_STEP_BY_KEY[payload.step_key][0],
                ttl_seconds=WORKFLOW_LEASE_SECONDS,
            )
            workflow_activity_id = workflow_activity.activity_id
        except SessionActivityConflict as exc:
            raise_session_activity_conflict(exc)
        except SessionActivityUnavailable as exc:
            raise_session_activity_unavailable(exc)

        run_id = uuid.uuid4().hex
        record = _RunRecord(
            run_id=run_id,
            app_session_id=payload.app_session_id,
        )
        _RUNS_BY_ID[run_id] = record
        _ACTIVE_RUN_BY_SESSION[payload.app_session_id] = run_id

    run_payload = SessionRunAllRequest(
        app_session_id=payload.app_session_id,
        current_filename=payload.current_filename,
        proposed_filename=payload.proposed_filename,
        model=payload.model,
        provider=payload.provider,
    )
    task = asyncio.create_task(
        _run_single_step_background(
            run_id,
            payload.step_key,
            run_payload,
            api_keys,
            model,
            workflow_activity_id,
        )
    )
    async with _RUN_REGISTRY_LOCK:
        active = _RUNS_BY_ID.get(run_id)
        if active is not None:
            active.task = task
    return SessionRunAllStartResponse(
        app_session_id=payload.app_session_id,
        run_id=run_id,
        started=True,
        status="running",
    )


@router.get("/step-runs/{run_id}", response_model=SessionRunStatusResponse)
async def get_step_run_status(run_id: str) -> SessionRunStatusResponse:
    return await get_run_all_status(run_id)


@router.post("/step-runs/{run_id}/cancel", response_model=SessionRunCancelResponse)
async def cancel_step_run(
    run_id: str,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> SessionRunCancelResponse:
    return await cancel_run_all(run_id, api_keys)


@router.get("/step-runs/{run_id}/events")
async def stream_step_run_events(run_id: str, request: Request) -> StreamingResponse:
    return await stream_run_all_events(run_id, request)


@router.post("/run-all/start", response_model=SessionRunAllStartResponse)
async def start_run_all_steps(
    payload: SessionRunAllRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> SessionRunAllStartResponse:
    _session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )
    workflow_activity_id: str | None = None

    async with _RUN_REGISTRY_LOCK:
        active_run_id = _ACTIVE_RUN_BY_SESSION.get(payload.app_session_id)
        if active_run_id:
            active = _RUNS_BY_ID.get(active_run_id)
            if active and active.status == "running":
                return SessionRunAllStartResponse(
                    app_session_id=payload.app_session_id,
                    run_id=active_run_id,
                    started=False,
                    status="running",
                )
            _ACTIVE_RUN_BY_SESSION.pop(payload.app_session_id, None)

        try:
            workflow_activity = begin_session_activity(
                session_id=_session_id,
                activity_type="workflow",
                label="Alle Schritte ausführen",
                ttl_seconds=WORKFLOW_LEASE_SECONDS,
            )
            workflow_activity_id = workflow_activity.activity_id
        except SessionActivityConflict as exc:
            raise_session_activity_conflict(exc)
        except SessionActivityUnavailable as exc:
            raise_session_activity_unavailable(exc)

        run_id = uuid.uuid4().hex
        record = _RunRecord(
            run_id=run_id,
            app_session_id=payload.app_session_id,
        )
        _RUNS_BY_ID[run_id] = record
        _ACTIVE_RUN_BY_SESSION[payload.app_session_id] = run_id

    task = asyncio.create_task(
        _run_all_background(run_id, payload, api_keys, model, workflow_activity_id)
    )
    async with _RUN_REGISTRY_LOCK:
        active = _RUNS_BY_ID.get(run_id)
        if active is not None:
            active.task = task
    return SessionRunAllStartResponse(
        app_session_id=payload.app_session_id,
        run_id=run_id,
        started=True,
        status="running",
    )


@router.post("/run-all/{run_id}/cancel", response_model=SessionRunCancelResponse)
async def cancel_run_all(
    run_id: str,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> SessionRunCancelResponse:
    async with _RUN_REGISTRY_LOCK:
        record = _RUNS_BY_ID.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if record.status != "running":
            return SessionRunCancelResponse(
                run_id=record.run_id,
                app_session_id=record.app_session_id,
                status=record.status,
                accepted=False,
                message="Run is not running",
            )
        record.updated_at = time.time()
        task = record.task

    await _publish_run_event(
        run_id,
        "run_cancelling",
        {"message": "Cancellation requested"},
    )

    if task is not None and not task.done():
        _cancel_running_deep_research_for_session(
            app_session_id=record.app_session_id,
            api_keys=api_keys,
        )
        task.cancel("Run cancelled by user")
    return SessionRunCancelResponse(
        run_id=run_id,
        app_session_id=record.app_session_id,
        status="cancelling",
        accepted=True,
        message="Cancellation requested",
    )


@router.get("/run-all/{run_id}", response_model=SessionRunStatusResponse)
async def get_run_all_status(run_id: str) -> SessionRunStatusResponse:
    record = await _get_run_record(run_id)
    return SessionRunStatusResponse(
        run_id=record.run_id,
        app_session_id=record.app_session_id,
        status=record.status,
        ok=record.ok,
        steps=record.steps,
        final_status=record.final_status,
        current_step=record.current_step,
        current_label=record.current_label,
        current_norm_addressee=record.current_norm_addressee,
        last_error=record.last_error,
    )


@router.get("/run-all/{run_id}/events")
async def stream_run_all_events(run_id: str, request: Request) -> StreamingResponse:
    await _get_run_record(run_id)

    async def _event_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue(maxsize=128)
        async with _RUN_REGISTRY_LOCK:
            current = _RUNS_BY_ID.get(run_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Run not found")
            backlog = list(current.events)
            snapshot_payload = _run_snapshot_payload(current)
            current.subscribers.add(queue)

        try:
            yield _format_sse_event("snapshot", snapshot_payload)
            for event_name, payload in backlog:
                yield _format_sse_event(event_name, payload)

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_name, payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield _format_sse_event(event_name, payload)
                    if event_name in {"run_completed", "run_failed", "run_cancelled"}:
                        break
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    async with _RUN_REGISTRY_LOCK:
                        latest = _RUNS_BY_ID.get(run_id)
                        if latest is None:
                            break
                        if latest.status in {"completed", "failed", "cancelled"}:
                            break
                    yield ": keep-alive\n\n"
        finally:
            async with _RUN_REGISTRY_LOCK:
                current = _RUNS_BY_ID.get(run_id)
                if current is not None:
                    current.subscribers.discard(queue)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/llm-monitor", response_model=SessionLlmMonitorSnapshotResponse)
async def get_llm_monitor_snapshot(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    limit: int = Query(default=80, ge=1, le=500),
) -> SessionLlmMonitorSnapshotResponse:
    _ensure_llm_console_enabled()
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])
    pending = await llm_monitor.get_pending(app_session_id)
    recent = _recent_monitor_rows(session_id, limit)
    events = await llm_monitor.get_recent_events(app_session_id, limit=limit)
    stream_attempts = await llm_monitor.get_stream_attempts(
        app_session_id,
        limit=limit,
    )
    return SessionLlmMonitorSnapshotResponse(
        app_session_id=app_session_id,
        pending=pending,
        recent=recent,
        events=events,
        stream_attempts=stream_attempts,
    )


@router.get("/llm-monitor/events")
async def stream_llm_monitor_events(
    request: Request,
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    limit: int = Query(default=80, ge=1, le=500),
    once: bool = Query(default=False),
) -> StreamingResponse:
    _ensure_llm_console_enabled()
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])

    async def _event_generator() -> AsyncGenerator[str, None]:
        queue, monitor_snapshot = await llm_monitor.subscribe(app_session_id)
        try:
            yield _format_sse_event(
                "snapshot",
                {
                    "app_session_id": app_session_id,
                    "pending": monitor_snapshot["pending"],
                    "events": monitor_snapshot["events"],
                    "stream_attempts": monitor_snapshot["stream_attempts"],
                    "recent": _recent_monitor_rows(session_id, limit),
                },
            )
            if once:
                return
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield _format_sse_event("llm_event", payload)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield ": keep-alive\n\n"
        finally:
            await llm_monitor.unsubscribe(app_session_id, queue)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/llm-monitor/stream/{attempt_id}",
    response_model=SessionLlmMonitorStreamAttemptResponse,
)
async def get_llm_monitor_stream_attempt(
    attempt_id: str,
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
) -> SessionLlmMonitorStreamAttemptResponse:
    _ensure_llm_console_enabled()
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    attempt = await llm_monitor.get_stream_attempt(app_session_id, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Stream attempt not found")
    return SessionLlmMonitorStreamAttemptResponse(
        app_session_id=app_session_id,
        attempt=attempt,
    )
