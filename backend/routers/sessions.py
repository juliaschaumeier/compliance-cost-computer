from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.core import db
from backend.core.prompts import PromptId


router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionUpsertRequest(BaseModel):
    app_session_id: str
    llm_model: str


class SessionUndoRequest(BaseModel):
    app_session_id: str


@router.post("")
async def upsert_session(payload: SessionUpsertRequest) -> dict:
    session_id, created = db.upsert_session(payload.app_session_id, payload.llm_model)
    return {"session_id": session_id, "created": created}


@router.get("")
async def list_sessions(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    sessions = db.list_sessions(limit=limit)
    return {"sessions": sessions}


@router.get("/status")
async def session_status(app_session_id: str) -> dict:
    status = db.get_session_status(app_session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    return status


@router.post("/undo")
async def undo_last_step(payload: SessionUndoRequest) -> dict:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    status = db.get_session_status(payload.app_session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])

    def step_info() -> tuple[str, str] | None:
        if status.get("total_cost_ready"):
            return ("total_cost", "Gesamtkosten berechnen")
        if status.get("effort_ready"):
            return ("effort", "Aufwand berechnen")
        if status.get("process_steps_ready"):
            return ("process_steps", "Prozessschritte bestimmen")
        if status.get("case_groups_ready"):
            return ("case_groups", "Fallgruppen entwickeln")
        if status.get("processes_ready"):
            return ("processes", "Prozesse bündeln")
        if status.get("regulations_ready"):
            return ("regulations", "Vorgaben bestimmen")
        if status.get("summary_ready"):
            return ("summary", "CCC starten")
        return None

    info = step_info()
    if not info:
        return {"status": "no-op", "message": "No completed steps"}

    step_key, label = info

    if step_key == "total_cost":
        db.clear_costs(session_id)
    elif step_key == "effort":
        db.clear_effort_metrics(session_id)
        db.delete_llm_answers(
            session_id,
            [PromptId.CASES_CALCULATION, PromptId.EFFORT_CALCULATION],
        )
    elif step_key == "process_steps":
        db.delete_process_steps_for_session(session_id)
        db.delete_llm_answers(session_id, [PromptId.PROCESS_STEP_ANALYSIS])
    elif step_key == "case_groups":
        db.delete_case_groups_for_session(session_id)
        db.delete_llm_answers(session_id, [PromptId.CASE_GROUP_DEVELOPMENT])
    elif step_key == "processes":
        db.delete_processes_for_session(session_id)
        db.delete_llm_answers(session_id, [PromptId.PROCESS_COMPILATION])
    elif step_key == "regulations":
        db.delete_regulations_for_session(session_id)
        db.delete_llm_answers(session_id, [PromptId.REGULATIONS_IDENTIFICATION])
    elif step_key == "summary":
        db.clear_session_summary(session_id)
        db.delete_llm_answers(session_id, [PromptId.LAW_SUMMARY])

    return {"status": "ok", "undone_step": step_key, "undone_label": label}
