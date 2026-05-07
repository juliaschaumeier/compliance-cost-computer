from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.auth import ApiKeys, get_api_keys
from backend.core.change_status import extract_change_status, normalize_change_status
from backend.core.llm_attempts import (
    mark_llm_parse_fallback,
    mark_llm_answer_applied,
)
from backend.core.llm_json import extract_fallgruppen, require_json_object
from backend.core.llm_service import query_llm
from backend.core.parsing import parse_first_int
from backend.core.models import Tile
from backend.core.norm_addressees import (
    ADMINISTRATION,
    check_norm_addressee_echo,
)
from backend.core.payload_builders import build_case_groups_payload, dump_prompt_json
from backend.core.prompts import PromptId, render_prompt
from backend.core.tile_refresh import refresh_step_tiles
from backend.routers._edit_schemas import (
    BulkUpdateResponse,
    EditableProcessStepsResponse,
)
from backend.routers._edit_validation import validate_non_negative_fields
from backend.routers._edit_validation import validate_non_empty_rows
from backend.routers._edit_validation import validate_non_noop_update_count
from backend.routers._edit_validation import validate_unique_ids
from backend.routers._llm_router_utils import (
    ensure_session_or_400,
    query_and_stage_or_http,
    run_with_answer_apply_guard,
)
from backend.routers._norm_addressee import normalize_norm_addressee_or_422
from backend.routers._session_validation import (
    APP_SESSION_ID_QUERY_VALIDATION,
    AppSessionId,
)


router = APIRouter(prefix="/process-steps", tags=["process-steps"])

class ProcessStepAnalysisRequest(BaseModel):
    app_session_id: AppSessionId
    model: str | None = None
    provider: str | None = None
    norm_addressee: str | None = None


class ProcessStepEditRow(BaseModel):
    step_id: int
    time_required_in_min_a_current: float | None = None
    time_required_in_min_b_current: float | None = None
    time_required_in_min_c_current: float | None = None
    time_required_in_min_d_current: float | None = None
    expenses_current: float | None = None
    time_required_in_min_a_proposed: float | None = None
    time_required_in_min_b_proposed: float | None = None
    time_required_in_min_c_proposed: float | None = None
    time_required_in_min_d_proposed: float | None = None
    expenses_proposed: float | None = None


class ProcessStepBulkUpdateRequest(BaseModel):
    app_session_id: AppSessionId
    rows: list[ProcessStepEditRow]


@router.get("/editable", response_model=EditableProcessStepsResponse)
async def list_editable_process_steps(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    case_group_id: int | None = None,
) -> EditableProcessStepsResponse:
    session_id = db.get_session_id_by_app_id(app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = db.list_editable_process_steps(session_id, case_group_id=case_group_id)
    return EditableProcessStepsResponse(rows=rows)


@router.post("/bulk-update", response_model=BulkUpdateResponse)
async def bulk_update_process_steps(
    payload: ProcessStepBulkUpdateRequest,
) -> BulkUpdateResponse:
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    validate_non_empty_rows(payload.rows)
    validate_unique_ids(
        payload.rows,
        id_field="step_id",
        entity_label="step_id",
    )
    updates: list[dict] = []
    for row in payload.rows:
        validate_non_negative_fields(
            row,
            field_names=(
                "time_required_in_min_a_current",
                "time_required_in_min_b_current",
                "time_required_in_min_c_current",
                "time_required_in_min_d_current",
                "expenses_current",
                "time_required_in_min_a_proposed",
                "time_required_in_min_b_proposed",
                "time_required_in_min_c_proposed",
                "time_required_in_min_d_proposed",
                "expenses_proposed",
            ),
            id_field="step_id",
            entity_label="step_id",
        )
        updates.append(row.model_dump())
    with db.transaction():
        updated, missing_ids = db.bulk_update_process_step_edits(session_id, updates)
        if missing_ids:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Unknown step_id values for this session: "
                    + ", ".join(str(step_id) for step_id in missing_ids)
                ),
            )
        validate_non_noop_update_count(updated)
        refresh_step_tiles(session_id, db.list_process_steps_for_session(session_id))
    return BulkUpdateResponse(updated=updated)


def _parse_process_steps(
    payload: str,
    norm_addressee: str | None = None,
) -> tuple[list[dict], set[str]]:
    data, parse_mode = require_json_object(
        payload,
        error_context="Invalid process_step_analysis payload",
    )
    fallback_kinds: set[str] = set()
    if parse_mode == "extract_last_json_object":
        fallback_kinds.add("json_extract_last_object")
    fallback_kinds.update(check_norm_addressee_echo(data, norm_addressee))

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
                        "regulation_ids": _parse_regulation_ids(
                            entry.get("vorgaben_ids") or entry.get("vorgaben")
                        ),
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
        return parsed, fallback_kinds

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
                    "regulation_ids": _parse_regulation_ids(
                        entry.get("vorgaben_ids") or entry.get("vorgaben")
                    ),
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
    if parsed:
        fallback_kinds.add("process_steps_flattened_fallgruppen")
    return parsed, fallback_kinds


def _add_step_tiles(
    session_id: int,
    parsed: list[dict],
    case_group_lookup: dict[int, dict],
    process_regulation_ids_by_process: dict[int, list[int]],
    norm_addressee: str = ADMINISTRATION,
) -> list[dict]:
    tiles = db.fetch_tiles(session_id=session_id, norm_addressee=norm_addressee)
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
            process_id = int(case_group_lookup[case_group_id]["process_id"])
            linked_regulation_ids = _resolve_step_regulation_ids(
                step.get("regulation_ids") or [],
                process_regulation_ids_by_process.get(process_id, []),
            )
            step_id = db.insert_process_step(
                session_id=session_id,
                case_group_id=case_group_id,
                step=title,
                description=description,
                change_status=step_status,
                previous_id=prev_step_id,
                norm_addressee=norm_addressee,
            )
            if prev_step_id is not None:
                db.update_process_step_next(prev_step_id, step_id)
            db.replace_process_step_regulation_links(
                session_id=session_id,
                step_id=step_id,
                norm_addressee=norm_addressee,
                regulation_ids=linked_regulation_ids,
            )
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
                    "process_id": process_id,
                    "regulation_ids": linked_regulation_ids,
                    "description": description,
                    "change_status": step_status,
                    "time_required_current": {"a": None, "b": None, "c": None, "d": None},
                    "time_required_proposed": {"a": None, "b": None, "c": None, "d": None},
                    "expenses_current": None,
                    "expenses_proposed": None,
                    "cost_current": None,
                    "cost_proposed": None,
                },
                column=case_group_tile.column + 1 + idx,
                row=case_group_tile.row,
                deletable=True,
                link_from_tile=link_from,
            )
            db.upsert_tile(tile, session_id=session_id, norm_addressee=norm_addressee)
            created.append(
                {
                    "step_id": step_id,
                    "case_group_id": case_group_id,
                    "taetigkeit": title,
                    "beschreibung": description,
                    "aenderungsstatus": step_status,
                    "regulation_ids": linked_regulation_ids,
                }
            )
            prev_step_id = step_id
    return created


def _parse_regulation_ids(raw_value: object) -> list[int]:
    if isinstance(raw_value, list):
        parsed: list[int] = []
        for entry in raw_value:
            regulation_id = None
            if isinstance(entry, dict):
                regulation_id = parse_first_int(entry, "vorgaben_id", "regulation_id")
            elif entry is not None:
                regulation_id = parse_first_int({"value": entry}, "value")
            if regulation_id is not None:
                parsed.append(regulation_id)
        return sorted(set(parsed))
    return []


def _resolve_step_regulation_ids(
    parsed_regulation_ids: list[int],
    process_regulation_ids: list[int],
) -> list[int]:
    valid_ids = sorted(
        {
            int(regulation_id)
            for regulation_id in parsed_regulation_ids
            if int(regulation_id) in set(process_regulation_ids)
        }
    )
    if valid_ids:
        return valid_ids
    if len(process_regulation_ids) == 1:
        return list(process_regulation_ids)
    return []


@router.post("/analyze")
async def analyze_process_steps(
    payload: ProcessStepAnalysisRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )
    norm_addressee = normalize_norm_addressee_or_422(payload.norm_addressee)
    existing = db.list_process_steps_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    if existing:
        return {"steps": existing, "status": "existing", "norm_addressee": norm_addressee}

    case_groups = db.list_case_groups_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    session_has_any_regulations = bool(db.list_regulations_for_session(session_id))
    if not case_groups and session_has_any_regulations and not db.has_applicable_regulations_for_addressee(
        session_id, norm_addressee
    ):
        return {"steps": [], "status": "skipped", "norm_addressee": norm_addressee}
    if not case_groups:
        raise HTTPException(status_code=400, detail="No case groups for session")

    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    regulations = db.list_regulations_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    payload_groups = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        regulations=regulations,
        norm_addressee=norm_addressee,
    )

    prompt = render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        session_id=session_id,
        case_groups_json=dump_prompt_json(payload_groups),
        norm_addressee=norm_addressee,
    )
    answer_id, llm_result = await query_and_stage_or_http(
        session_id=session_id,
        prompt_id=PromptId.PROCESS_STEP_ANALYSIS,
        prompt=prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
        query_fn=query_llm,
        norm_addressee=norm_addressee,
    )
    response_text = llm_result.text

    def _apply() -> list[dict]:
        parsed, fallback_kinds = _parse_process_steps(response_text, norm_addressee)
        for fallback_kind in sorted(fallback_kinds):
            mark_llm_parse_fallback(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.PROCESS_STEP_ANALYSIS,
                fallback_kind=fallback_kind,
            )
        if not parsed:
            raise HTTPException(status_code=422, detail="No process steps parsed")

        case_group_lookup = {row["case_group_id"]: row for row in case_groups}
        process_regulation_ids_by_process: dict[int, list[int]] = {}
        for row in regulations:
            process_id = row.get("process_id")
            regulation_id = row.get("regulation_id")
            if process_id is None or regulation_id is None:
                continue
            process_regulation_ids_by_process.setdefault(int(process_id), []).append(
                int(regulation_id)
            )
        for process_id, regulation_ids in list(process_regulation_ids_by_process.items()):
            process_regulation_ids_by_process[process_id] = sorted(set(regulation_ids))
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

        invalid_regulation_links: list[str] = []
        for entry in parsed:
            process_id = int(case_group_lookup[entry["case_group_id"]]["process_id"])
            valid_regulation_ids = set(process_regulation_ids_by_process.get(process_id, []))
            for step in entry["taetigkeiten"]:
                unknown_ids = sorted(
                    {
                        int(regulation_id)
                        for regulation_id in (step.get("regulation_ids") or [])
                        if int(regulation_id) not in valid_regulation_ids
                    }
                )
                if not unknown_ids:
                    continue
                invalid_regulation_links.append(
                    f"{step.get('taetigkeit') or 'Unbenannte Taetigkeit'} -> "
                    + ", ".join(str(regulation_id) for regulation_id in unknown_ids)
                )
        if invalid_regulation_links:
            raise HTTPException(
                status_code=422,
                detail="Unknown vorgaben_ids in process steps: " + "; ".join(invalid_regulation_links),
            )

        with db.transaction():
            created_local = _add_step_tiles(
                session_id,
                parsed,
                case_group_lookup,
                process_regulation_ids_by_process,
                norm_addressee=norm_addressee,
            )
            mark_llm_answer_applied(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.PROCESS_STEP_ANALYSIS,
            )
        return created_local

    created = run_with_answer_apply_guard(answer_id=answer_id, apply_fn=_apply)
    return {"steps": created, "norm_addressee": norm_addressee}
