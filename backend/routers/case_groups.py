from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.auth import ApiKeys, get_api_keys
from backend.core.change_status import extract_change_status, normalize_change_status
from backend.core.llm_attempts import (
    mark_llm_answer_applied,
)
from backend.core.llm_json import require_json_object
from backend.core.llm_service import query_llm
from backend.core.models import Tile
from backend.core.norm_addressees import (
    ADMINISTRATION,
)
from backend.core.parsing import parse_first_int
from backend.core.payload_builders import (
    build_processes_payload_with_regulations,
    dump_prompt_json,
)
from backend.core.mirror_context import propagate_case_group_edits_to_mirror_targets
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


router = APIRouter(prefix="/case-groups", tags=["case-groups"])

class CaseGroupDevelopmentRequest(BaseModel):
    app_session_id: AppSessionId
    model: str | None = None
    provider: str | None = None
    norm_addressee: str | None = None


class CaseGroupEditRow(BaseModel):
    case_group_id: int
    addressees_current: float | None = None
    annual_frequency_current: float | None = None
    addressees_proposed: float | None = None
    annual_frequency_proposed: float | None = None


class CaseGroupBulkUpdateRequest(BaseModel):
    app_session_id: AppSessionId
    rows: list[CaseGroupEditRow]


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
        # Leitfaden-Invariante: Spiegelsituationen muessen dieselben
        # Fallzahlen und Adressatenzahlen tragen. Nach dem manuellen Edit
        # propagieren wir die neuen Effektivwerte der Quelle auf alle
        # Mirror-Ziele mit sync_cases=True, damit Quelle und Ziel nicht
        # auseinanderdriften und die Kostenberechnung des Spiegel-
        # Normadressaten konsistent bleibt.
        propagate_case_group_edits_to_mirror_targets(
            session_id=session_id,
            edited_case_group_ids=edited_case_group_ids,
        )
        refresh_case_group_tiles(session_id, db.list_case_groups_for_session(session_id))
    return BulkUpdateResponse(updated=updated)


def _parse_case_groups(payload: str) -> list[dict]:
    data, _parse_mode = require_json_object(
        payload,
        error_context="case group development",
    )
    processes = data.get("prozesse")
    if not isinstance(processes, list):
        return []
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
    return parsed


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


@router.post("/develop")
async def develop_case_groups(
    payload: CaseGroupDevelopmentRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )
    norm_addressee = normalize_norm_addressee_or_422(payload.norm_addressee)
    existing = db.list_case_groups_for_session_and_addressee(session_id, norm_addressee)
    if existing:
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

    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    session_has_any_regulations = bool(db.list_regulations_for_session(session_id))
    if not processes and session_has_any_regulations and not db.has_applicable_regulations_for_addressee(
        session_id, norm_addressee
    ):
        return {"prozesse": [], "status": "skipped", "norm_addressee": norm_addressee}
    if not processes:
        raise HTTPException(status_code=400, detail="No processes for session")
    regulations = db.list_regulations_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    prozesse_payload = build_processes_payload_with_regulations(processes, regulations)

    prompt = render_prompt(
        PromptId.CASE_GROUP_DEVELOPMENT,
        session_id=session_id,
        prozesse_json=dump_prompt_json(prozesse_payload),
        norm_addressee=norm_addressee,
    )
    answer_id, llm_result = await query_and_stage_or_http(
        session_id=session_id,
        prompt_id=PromptId.CASE_GROUP_DEVELOPMENT,
        prompt=prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
        query_fn=query_llm,
        norm_addressee=norm_addressee,
    )
    response_text = llm_result.text

    def _apply() -> list[dict]:
        parsed = _parse_case_groups(response_text)
        if not parsed:
            raise HTTPException(status_code=422, detail="No case groups parsed")

        process_ids = {row["process_id"] for row in processes}
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

        with db.transaction():
            created_local = _add_case_group_tiles(
                session_id,
                parsed,
                norm_addressee=norm_addressee,
            )
            mark_llm_answer_applied(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.CASE_GROUP_DEVELOPMENT,
            )
        return created_local

    created = run_with_answer_apply_guard(answer_id=answer_id, apply_fn=_apply)
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
            for process in processes
            if process["process_id"] in grouped
        ],
        "norm_addressee": norm_addressee,
    }
