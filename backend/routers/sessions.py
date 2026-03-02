from __future__ import annotations

import asyncio
import inspect
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Annotated, AsyncGenerator, Awaitable, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints

from backend.core.auth import ApiKeys, get_api_keys
from backend.core import db
from backend.core.session_graph import build_session_tiles_snapshot
from backend.core.workflow import get_last_completed_step, undo_step
from backend.routers._llm_router_utils import ensure_session_or_400
from backend.routers import (
    case_groups as case_groups_router,
    costs as costs_router,
    effort as effort_router,
    process_steps as process_steps_router,
    processes as processes_router,
    regulations as regulations_router,
)


router = APIRouter(prefix="/sessions", tags=["sessions"])

AppSessionId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$",
    ),
]
ModelName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
APP_SESSION_ID_QUERY_VALIDATION = Query(
    ...,
    min_length=1,
    max_length=64,
    pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$",
)


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


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class SessionStatusResponse(BaseModel):
    summary_ready: bool
    regulations_ready: bool
    processes_ready: bool
    case_groups_ready: bool
    process_steps_ready: bool
    effort_ready: bool
    total_cost_ready: bool
    last_completed_step: str | None = None
    last_completed_label: str | None = None


class SessionExportResponse(BaseModel):
    filename: str
    markdown: str


class SessionUndoResponse(BaseModel):
    status: Literal["ok", "no-op"]
    undone_step: str | None = None
    undone_label: str | None = None
    message: str | None = None


class SessionRunAllRequest(BaseModel):
    app_session_id: AppSessionId
    current_filename: str | None = None
    proposed_filename: str | None = None
    model: str | None = None
    provider: str | None = None


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


class SessionRunCancelResponse(BaseModel):
    run_id: str
    app_session_id: str
    status: Literal["cancelling", "completed", "failed", "cancelled"]
    accepted: bool
    message: str | None = None


RUN_ALL_STEPS: tuple[tuple[str, str, str], ...] = (
    ("summary", "CCC starten", "summary_ready"),
    ("regulations", "Vorgaben bestimmen", "regulations_ready"),
    ("processes", "Prozesse bündeln", "processes_ready"),
    ("case_groups", "Fallgruppen entwickeln", "case_groups_ready"),
    ("process_steps", "Prozessschritte bestimmen", "process_steps_ready"),
    ("effort", "Aufwand berechnen", "effort_ready"),
    ("total_cost", "Gesamtkosten berechnen", "total_cost_ready"),
)

_RUN_ALL_LOCKS: dict[str, asyncio.Lock] = {}


@dataclass
class _RunRecord:
    run_id: str
    app_session_id: str
    status: Literal["running", "completed", "failed", "cancelled"] = "running"
    ok: bool | None = None
    steps: list[SessionRunStepResult] = field(default_factory=list)
    final_status: SessionStatusResponse | None = None
    events: list[tuple[str, dict]] = field(default_factory=list)
    subscribers: set[asyncio.Queue[tuple[str, dict]]] = field(default_factory=set)
    task: asyncio.Task[None] | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_RUNS_BY_ID: dict[str, _RunRecord] = {}
_ACTIVE_RUN_BY_SESSION: dict[str, str] = {}
_RUN_REGISTRY_LOCK = asyncio.Lock()
_MAX_STORED_RUNS = 200


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
    return SessionStatusResponse(
        **status,
        last_completed_step=step.key if step else None,
        last_completed_label=step.label if step else None,
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


async def _run_single_step(
    step_key: str,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
) -> None:
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
        current_filename, proposed_filename = _resolve_filenames(
            payload.app_session_id,
            payload.current_filename,
            payload.proposed_filename,
        )
        if not current_filename or not proposed_filename:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Missing current_filename/proposed_filename for regulations step"
                ),
            )
        identify_payload = regulations_router.RegulationIdentifyRequest(
            current_filename=current_filename,
            proposed_filename=proposed_filename,
            app_session_id=payload.app_session_id,
            model=model,
            provider=payload.provider,
        )
        await regulations_router.identify_regulations(identify_payload, api_keys)
        return

    if step_key == "processes":
        processes_payload = processes_router.ProcessCompilationRequest(
            app_session_id=payload.app_session_id,
            model=model,
            provider=payload.provider,
        )
        await processes_router.compile_processes(processes_payload, api_keys)
        return

    if step_key == "case_groups":
        case_groups_payload = case_groups_router.CaseGroupDevelopmentRequest(
            app_session_id=payload.app_session_id,
            model=model,
            provider=payload.provider,
        )
        await case_groups_router.develop_case_groups(case_groups_payload, api_keys)
        return

    if step_key == "process_steps":
        steps_payload = process_steps_router.ProcessStepAnalysisRequest(
            app_session_id=payload.app_session_id,
            model=model,
            provider=payload.provider,
        )
        await process_steps_router.analyze_process_steps(steps_payload, api_keys)
        return

    if step_key == "effort":
        effort_payload = effort_router.EffortCalculationRequest(
            app_session_id=payload.app_session_id,
            model=model,
            provider=payload.provider,
        )
        await effort_router.calculate_effort(effort_payload, api_keys)
        return

    if step_key == "total_cost":
        costs_payload = costs_router.CostComputationRequest(
            app_session_id=payload.app_session_id
        )
        await costs_router.compute_costs(costs_payload)
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
            await _run_single_step(step_key, payload, api_keys, model)
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
    status = db.get_session_status(app_session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    step = get_last_completed_step(status)
    return SessionStatusResponse(
        **status,
        last_completed_step=step.key if step else None,
        last_completed_label=step.label if step else None,
    )


@router.get("/export", response_model=SessionExportResponse)
async def export_session(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION
) -> SessionExportResponse:
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


@router.post("/undo", response_model=SessionUndoResponse)
async def undo_last_step(payload: SessionUndoRequest) -> SessionUndoResponse:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    status = db.get_session_status(payload.app_session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])

    step = get_last_completed_step(status)
    if not step:
        return SessionUndoResponse(status="no-op", message="No completed steps")

    with db.transaction():
        undo_step(session_id, step.key)

    return SessionUndoResponse(
        status="ok",
        undone_step=step.key,
        undone_label=step.label,
    )


async def _run_all_background(
    run_id: str,
    payload: SessionRunAllRequest,
    api_keys: ApiKeys,
    model: str,
) -> None:
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
        async with _RUN_REGISTRY_LOCK:
            record = _RUNS_BY_ID.get(run_id)
            if record is not None:
                if _ACTIVE_RUN_BY_SESSION.get(record.app_session_id) == run_id:
                    _ACTIVE_RUN_BY_SESSION.pop(record.app_session_id, None)

        final_status: SessionStatusResponse | None = None
        try:
            final_status = _as_session_status_response(payload.app_session_id)
        except HTTPException:
            final_status = None
        async with _RUN_REGISTRY_LOCK:
            record = _RUNS_BY_ID.get(run_id)
            if record is not None:
                record.status = "cancelled"
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
            "run_cancelled",
            {
                "ok": False,
                "steps": steps,
                "final_status": final_status.model_dump() if final_status else None,
                "message": "Run cancelled by user",
            },
        )
        await _trim_finished_runs()
        return
    except Exception as exc:
        final_status: SessionStatusResponse | None = None
        try:
            final_status = _as_session_status_response(payload.app_session_id)
        except HTTPException:
            final_status = None
        async with _RUN_REGISTRY_LOCK:
            record = _RUNS_BY_ID.get(run_id)
            if record is not None:
                record.status = "failed"
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
            "run_failed",
            {
                "ok": False,
                "steps": steps,
                "final_status": final_status.model_dump() if final_status else None,
                "message": _step_error_message(exc),
            },
        )
        await _trim_finished_runs()
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


@router.post("/run-all/start", response_model=SessionRunAllStartResponse)
async def start_run_all_steps(
    payload: SessionRunAllRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> SessionRunAllStartResponse:
    _session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )

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

        run_id = uuid.uuid4().hex
        record = _RunRecord(
            run_id=run_id,
            app_session_id=payload.app_session_id,
        )
        _RUNS_BY_ID[run_id] = record
        _ACTIVE_RUN_BY_SESSION[payload.app_session_id] = run_id

    task = asyncio.create_task(_run_all_background(run_id, payload, api_keys, model))
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
async def cancel_run_all(run_id: str) -> SessionRunCancelResponse:
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
    )


@router.get("/run-all/{run_id}/events")
async def stream_run_all_events(run_id: str) -> StreamingResponse:
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
                try:
                    event_name, payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield _format_sse_event(event_name, payload)
                    if event_name in {"run_completed", "run_failed", "run_cancelled"}:
                        break
                except asyncio.TimeoutError:
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
