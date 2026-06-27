from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.change_status import extract_change_status, normalize_change_status
from backend.core.llm_json import require_json_object
from backend.core.llm_service import query_llm
from backend.core.models import Tile
from backend.core.norm_addressees import (
    ADMINISTRATION,
    NORM_ADDRESSEE_ECHO_MISMATCH,
    check_norm_addressee_echo,
)
from backend.core.parsing import parse_first_int
from backend.core.payload_builders import (
    build_processes_payload_with_regulations,
    dump_prompt_json,
)
from backend.core.prompts import PromptId, render_prompt
from backend.core.tile_refresh import refresh_case_group_tiles
from backend.routers._edit_schemas import (
    BulkUpdateResponse,
    EditableCaseGroupsResponse,
)
from backend.routers._edit_validation import validate_non_negative_fields
from backend.routers._edit_validation import validate_non_empty_rows
from backend.routers._edit_validation import validate_non_noop_update_count
from backend.routers._edit_validation import validate_unique_ids
from backend.routers._norm_addressee import normalize_norm_addressee_or_422
from backend.routers._session_activity_guard import guarded_session_activity
from backend.routers._session_validation import (
    APP_SESSION_ID_QUERY_VALIDATION,
    AppSessionId,
)


router = APIRouter(prefix="/case-groups", tags=["case-groups"])

class CaseGroupEditRow(BaseModel):
    case_group_id: int
    addressees_current: float | None = None
    annual_frequency_current: float | None = None
    addressees_proposed: float | None = None
    annual_frequency_proposed: float | None = None


class CaseGroupBulkUpdateRequest(BaseModel):
    app_session_id: AppSessionId
    ea_activity_id: str | None = None
    rows: list[CaseGroupEditRow]


def format_existing_case_groups_response(
    *,
    session_id: int,
    existing: list[dict],
    norm_addressee: str,
) -> dict:
    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    grouped: dict[int, list[dict]] = {}
    for row in existing:
        grouped.setdefault(row["process_id"], []).append(
            {
                "case_group_id": row["case_group_id"],
                "fallgruppe_bezeichnung": row["case_group"],
                "fallgruppe_beschreibung": row["description"],
                "aenderungsstatus": row["change_status"],
            }
        )
    return {
        "prozesse": [
            {
                "process_id": process["process_id"],
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "aenderungsstatus": process["change_status"],
                "fallgruppen": grouped.get(process["process_id"], []),
            }
            for process in processes
            if process["process_id"] in grouped
        ],
        "status": "existing",
        "norm_addressee": norm_addressee,
    }


def build_case_group_development_prompt(
    *,
    session_id: int,
    norm_addressee: str,
) -> tuple[str | None, dict]:
    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    session_has_any_regulations = bool(db.list_regulations_for_session(session_id))
    if not processes and session_has_any_regulations and not db.has_applicable_regulations_for_addressee(
        session_id, norm_addressee
    ):
        return None, {"status": "skipped", "processes": []}
    if not processes and db.has_no_process_path_for_addressee(
        session_id, norm_addressee
    ):
        return None, {"status": "skipped", "processes": []}
    if not processes:
        raise HTTPException(status_code=400, detail="No processes for session")
    regulations = db.list_regulations_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    prozesse_payload = build_processes_payload_with_regulations(
        processes, regulations, norm_addressee=norm_addressee
    )

    prompt = render_prompt(
        PromptId.CASE_GROUP_DEVELOPMENT,
        session_id=session_id,
        prozesse_json=dump_prompt_json(prozesse_payload),
        norm_addressee=norm_addressee,
    )
    return prompt, {"status": "ready", "processes": processes}


def parse_case_group_development_answer(
    *,
    response_text: str,
    norm_addressee: str,
    context: dict,
) -> tuple[list[dict], set[str]]:
    parsed, fallback_kinds = _parse_case_groups(response_text, norm_addressee)
    if not parsed:
        raise HTTPException(status_code=422, detail="No case groups parsed")

    process_ids = {row["process_id"] for row in context["processes"]}
    missing_ids = [
        str(entry["prozess_id"])
        for entry in parsed
        if entry["prozess_id"] not in process_ids
    ]
    if missing_ids:
        raise HTTPException(
            status_code=422,
            detail="Unknown process_id values: " + ", ".join(missing_ids),
        )
    return parsed, fallback_kinds


def apply_case_group_development(
    *,
    session_id: int,
    norm_addressee: str,
    parsed: list[dict],
    context: dict,
) -> list[dict]:
    return _add_case_group_tiles(
        session_id,
        parsed,
        norm_addressee=norm_addressee,
    )


def format_case_group_development_response(
    *,
    created: list[dict],
    context: dict,
    norm_addressee: str,
) -> dict:
    grouped: dict[int, list[dict]] = {}
    for entry in created:
        grouped.setdefault(entry["process_id"], []).append(
            {
                "case_group_id": entry["case_group_id"],
                "fallgruppe_bezeichnung": entry["fallgruppe_bezeichnung"],
                "fallgruppe_beschreibung": entry["fallgruppe_beschreibung"],
                "aenderungsstatus": entry["aenderungsstatus"],
            }
        )
    return {
        "prozesse": [
            {
                "process_id": process["process_id"],
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "aenderungsstatus": process["change_status"],
                "fallgruppen": grouped.get(process["process_id"], []),
            }
            for process in context["processes"]
            if process["process_id"] in grouped
        ],
        "norm_addressee": norm_addressee,
    }


@router.get("/editable", response_model=EditableCaseGroupsResponse)
async def list_editable_case_groups(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
) -> EditableCaseGroupsResponse:
    session_id = db.get_session_id_by_app_id(app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = db.list_editable_case_groups(session_id)
    return EditableCaseGroupsResponse(rows=rows)


@router.post("/bulk-update", response_model=BulkUpdateResponse)
async def bulk_update_case_groups(payload: CaseGroupBulkUpdateRequest) -> BulkUpdateResponse:
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    validate_non_empty_rows(payload.rows)
    validate_unique_ids(
        payload.rows,
        id_field="case_group_id",
        entity_label="case_group_id",
    )
    updates: list[dict] = []
    for row in payload.rows:
        validate_non_negative_fields(
            row,
            field_names=(
                "addressees_current",
                "annual_frequency_current",
                "addressees_proposed",
                "annual_frequency_proposed",
            ),
            id_field="case_group_id",
            entity_label="case_group_id",
        )
        updates.append(row.model_dump())
    edited_case_group_ids = {
        int(row.case_group_id) for row in payload.rows if row.case_group_id is not None
    }
    async with guarded_session_activity(
        session_id=session_id,
        activity_type="ea_edit",
        label="EA bearbeiten",
        owner_activity_id=payload.ea_activity_id,
    ):
        with db.transaction():
            updated, missing_ids = db.bulk_update_case_group_edits(session_id, updates)
            if missing_ids:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Unknown case_group_id values for this session: "
                        + ", ".join(str(case_group_id) for case_group_id in missing_ids)
                    ),
                )
            validate_non_noop_update_count(updated)
            refresh_case_group_tiles(session_id, db.list_case_groups_for_session(session_id))
    return BulkUpdateResponse(updated=updated)


def _parse_case_groups(
    payload: str,
    norm_addressee: str | None = None,
) -> tuple[list[dict], set[str]]:
    data, _parse_mode = require_json_object(
        payload,
        error_context="case group development",
    )
    fallback_kinds = check_norm_addressee_echo(data, norm_addressee)
    if NORM_ADDRESSEE_ECHO_MISMATCH in fallback_kinds:
        raise HTTPException(
            status_code=422,
            detail=f"normadressat mismatch (expected {norm_addressee})",
        )
    processes = data.get("prozesse")
    if not isinstance(processes, list):
        return [], fallback_kinds
    parsed = []
    for entry in processes:
        if not isinstance(entry, dict):
            continue
        process_id = parse_first_int(entry, "prozess_id")
        if process_id is None:
            continue
        process_name = str(entry.get("prozess_bezeichnung", "")).strip()
        process_description = str(entry.get("prozess_beschreibung", "")).strip()
        process_status = extract_change_status(entry)
        fallgruppen = entry.get("fallgruppen")
        if not isinstance(fallgruppen, list):
            fallgruppen = []
        parsed_fallgruppen = []
        for fallgruppe in fallgruppen:
            if not isinstance(fallgruppe, dict):
                continue
            name = str(
                fallgruppe.get("fallgruppe_bezeichnung")
                or fallgruppe.get("fallgruppen_id")
                or ""
            ).strip()
            description = str(
                fallgruppe.get("fallgruppe_beschreibung")
                or fallgruppe.get("beschreibung_fallgruppe")
                or ""
            ).strip()
            case_group_status = extract_change_status(fallgruppe)
            if not name and not description:
                continue
            parsed_fallgruppen.append(
                {
                    "fallgruppe_bezeichnung": name,
                    "fallgruppe_beschreibung": description,
                    "aenderungsstatus": case_group_status,
                }
            )
        parsed.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process_name,
                "prozess_beschreibung": process_description,
                "aenderungsstatus": process_status,
                "fallgruppen": parsed_fallgruppen,
            }
        )
    return parsed, fallback_kinds


def _add_case_group_tiles(
    session_id: int,
    processes: list[dict],
    norm_addressee: str = ADMINISTRATION,
) -> list[dict]:
    tiles = db.fetch_tiles(session_id=session_id, norm_addressee=norm_addressee)
    process_tiles = {tile.id: tile for tile in tiles if tile.id.startswith("process_")}
    created = []
    row_spacing = 1

    for process in processes:
        process_id = process["prozess_id"]
        process_tile_id = f"process_{process_id}"
        process_tile = process_tiles.get(process_tile_id)
        if not process_tile:
            raise HTTPException(
                status_code=409,
                detail=f"Process tile missing for process_id {process_id}",
            )
        base_col = process_tile.column + 1
        base_row = process_tile.row
        for idx, fallgruppe in enumerate(process.get("fallgruppen", [])):
            title = fallgruppe.get("fallgruppe_bezeichnung") or f"Fallgruppe {idx + 1}"
            text = fallgruppe.get("fallgruppe_beschreibung") or ""
            case_group_status = normalize_change_status(
                fallgruppe.get("aenderungsstatus")
            )
            case_group_id = db.insert_case_group(
                session_id=session_id,
                process_id=process_id,
                case_group=title,
                description=text,
                change_status=case_group_status,
                norm_addressee=norm_addressee,
            )
            tile = Tile(
                id=f"case_group_{case_group_id}",
                title=title,
                text=text,
                meta_information={
                    "case_group_id": case_group_id,
                    "process_id": process_id,
                    "description": text,
                    "change_status": case_group_status,
                    "addressees_current": None,
                    "annual_frequency_current": None,
                    "cases_current": None,
                    "addressees_proposed": None,
                    "annual_frequency_proposed": None,
                    "cases_proposed": None,
                },
                column=base_col,
                row=base_row + (idx * row_spacing),
                deletable=True,
                link_from_tile=[process_tile_id],
            )
            db.upsert_tile(tile, session_id=session_id, norm_addressee=norm_addressee)
            created.append(
                {
                    "case_group_id": case_group_id,
                    "fallgruppe_bezeichnung": title,
                    "fallgruppe_beschreibung": text,
                    "aenderungsstatus": case_group_status,
                    "process_id": process_id,
                }
            )
    return created
