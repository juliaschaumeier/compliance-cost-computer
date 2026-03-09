from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.auth import ApiKeys, get_api_keys
from backend.core.change_status import extract_change_status, normalize_change_status
from backend.core.llm_attempts import (
    mark_llm_answer_applied,
)
from backend.core.llm_json import extract_fallgruppen, parse_json_object
from backend.core.llm_service import query_llm
from backend.core.parsing import parse_first_int
from backend.core.models import Tile
from backend.core.payload_builders import build_case_groups_payload, dump_prompt_json
from backend.core.prompts import PromptId, render_prompt
from backend.routers._llm_router_utils import (
    ensure_session_or_400,
    query_and_stage_or_http,
    run_with_answer_apply_guard,
)


router = APIRouter(prefix="/process-steps", tags=["process-steps"])

class ProcessStepAnalysisRequest(BaseModel):
    app_session_id: str
    model: str | None = None
    provider: str | None = None


def _parse_process_steps(payload: str) -> list[dict]:
    data = parse_json_object(payload)
    if not isinstance(data, dict):
        return []

    parsed: list[dict] = []
    processes = data.get("prozesse")
    if not isinstance(processes, list):
        processes = []

    for process in processes:
        if not isinstance(process, dict):
            continue
        process_status = extract_change_status(process)
        fallgruppen = process.get("fallgruppen")
        if not isinstance(fallgruppen, list):
            continue
        for fallgruppe in fallgruppen:
            if not isinstance(fallgruppe, dict):
                continue
            case_group_id = parse_first_int(
                fallgruppe,
                "fallgruppen_id",
                "fallgruppe_id",
                "case_group_id",
            )
            if case_group_id is None:
                continue
            case_group_status = extract_change_status(fallgruppe)
            taetigkeiten = fallgruppe.get("taetigkeiten") or fallgruppe.get("tätigkeiten")
            if not isinstance(taetigkeiten, list):
                taetigkeiten = []
            steps: list[dict] = []
            for entry in taetigkeiten:
                if not isinstance(entry, dict):
                    continue
                step = str(
                    entry.get("taetigkeit")
                    or entry.get("tätigkeit")
                    or entry.get("step")
                    or ""
                ).strip()
                description = str(
                    entry.get("beschreibung")
                    or entry.get("description")
                    or ""
                ).strip()
                step_status = extract_change_status(entry)
                if not step and not description:
                    continue
                steps.append(
                    {
                        "taetigkeit": step,
                        "beschreibung": description,
                        "aenderungsstatus": step_status,
                    }
                )
            if steps:
                parsed.append(
                    {
                        "case_group_id": case_group_id,
                        "aenderungsstatus": case_group_status or process_status,
                        "taetigkeiten": steps,
                    }
                )

    if parsed:
        return parsed

    fallgruppen = extract_fallgruppen(data)
    for fallgruppe in fallgruppen:
        case_group_id = parse_first_int(
            fallgruppe,
            "fallgruppen_id",
            "fallgruppe_id",
            "case_group_id",
        )
        if case_group_id is None:
            continue
        case_group_status = extract_change_status(fallgruppe)
        taetigkeiten = fallgruppe.get("taetigkeiten") or fallgruppe.get("tätigkeiten")
        if not isinstance(taetigkeiten, list):
            taetigkeiten = []
        steps: list[dict] = []
        for entry in taetigkeiten:
            if not isinstance(entry, dict):
                continue
            step = str(
                entry.get("taetigkeit")
                or entry.get("tätigkeit")
                or entry.get("step")
                or ""
            ).strip()
            description = str(
                entry.get("beschreibung")
                or entry.get("description")
                or ""
            ).strip()
            step_status = extract_change_status(entry)
            if not step and not description:
                continue
            steps.append(
                {
                    "taetigkeit": step,
                    "beschreibung": description,
                    "aenderungsstatus": step_status,
                }
            )
        if steps:
            parsed.append(
                {
                    "case_group_id": case_group_id,
                    "aenderungsstatus": case_group_status,
                    "taetigkeiten": steps,
                }
            )
    return parsed


def _add_step_tiles(
    session_id: int,
    parsed: list[dict],
    case_group_lookup: dict[int, dict],
) -> list[dict]:
    tiles = db.fetch_tiles(session_id=session_id)
    case_group_tiles = {
        tile.id: tile for tile in tiles if tile.id.startswith("case_group_")
    }
    created: list[dict] = []

    for entry in parsed:
        case_group_id = entry["case_group_id"]
        case_group_tile_id = f"case_group_{case_group_id}"
        case_group_tile = case_group_tiles.get(case_group_tile_id)
        if not case_group_tile:
            raise HTTPException(
                status_code=409,
                detail=f"Case group tile missing for case_group_id {case_group_id}",
            )
        prev_step_id: int | None = None
        for idx, step in enumerate(entry["taetigkeiten"]):
            title = step.get("taetigkeit") or f"Schritt {idx + 1}"
            description = step.get("beschreibung") or ""
            step_status = normalize_change_status(step.get("aenderungsstatus"))
            step_id = db.insert_process_step(
                session_id=session_id,
                case_group_id=case_group_id,
                step=title,
                description=description,
                change_status=step_status,
                previous_id=prev_step_id,
            )
            if prev_step_id is not None:
                db.update_process_step_next(prev_step_id, step_id)
            link_from = (
                [f"step_{prev_step_id}"]
                if prev_step_id is not None
                else [case_group_tile_id]
            )
            tile = Tile(
                id=f"step_{step_id}",
                title=title,
                text=description,
                meta_information={
                    "step_id": step_id,
                    "case_group_id": case_group_id,
                    "process_id": case_group_lookup[case_group_id]["process_id"],
                    "change_status": step_status,
                },
                column=case_group_tile.column + 1 + idx,
                row=case_group_tile.row,
                deletable=True,
                link_from_tile=link_from,
            )
            db.upsert_tile(tile, session_id=session_id)
            created.append(
                {
                    "step_id": step_id,
                    "case_group_id": case_group_id,
                    "taetigkeit": title,
                    "beschreibung": description,
                    "aenderungsstatus": step_status,
                }
            )
            prev_step_id = step_id
    return created


@router.post("/analyze")
async def analyze_process_steps(
    payload: ProcessStepAnalysisRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )
    existing = db.list_process_steps_for_session(session_id)
    if existing:
        return {"steps": existing, "status": "existing"}

    case_groups = db.list_case_groups_for_session(session_id)
    if not case_groups:
        raise HTTPException(status_code=400, detail="No case groups for session")

    processes = db.list_processes_for_session(session_id)
    regulations = db.list_regulations_for_session(session_id)
    payload_groups = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        regulations=regulations,
    )

    prompt = render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        session_id=session_id,
        case_groups_json=dump_prompt_json(payload_groups),
    )
    answer_id, llm_result = await query_and_stage_or_http(
        session_id=session_id,
        prompt_id=PromptId.PROCESS_STEP_ANALYSIS,
        prompt=prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
        query_fn=query_llm,
    )
    response_text = llm_result.text

    def _apply() -> list[dict]:
        parsed = _parse_process_steps(response_text)
        if not parsed:
            raise HTTPException(status_code=422, detail="No process steps parsed")

        case_group_lookup = {row["case_group_id"]: row for row in case_groups}
        missing = [
            str(entry["case_group_id"])
            for entry in parsed
            if entry["case_group_id"] not in case_group_lookup
        ]
        if missing:
            raise HTTPException(
                status_code=422,
                detail="Unknown fallgruppen_id values: " + ", ".join(missing),
            )

        with db.transaction():
            created_local = _add_step_tiles(session_id, parsed, case_group_lookup)
            mark_llm_answer_applied(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.PROCESS_STEP_ANALYSIS,
            )
        return created_local

    created = run_with_answer_apply_guard(answer_id=answer_id, apply_fn=_apply)
    return {"steps": created}
