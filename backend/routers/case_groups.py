from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.auth import ApiKeys, get_api_keys
from backend.core.change_status import extract_change_status, normalize_change_status
from backend.core.llm_json import parse_json_object
from backend.core.llm_service import query_llm
from backend.core.models import Tile
from backend.core.parsing import parse_first_int
from backend.core.payload_builders import build_processes_payload_with_regulations
from backend.core.prompts import PromptId, render_prompt


router = APIRouter(prefix="/case-groups", tags=["case-groups"])

class CaseGroupDevelopmentRequest(BaseModel):
    app_session_id: str
    model: str | None = None
    provider: str | None = None


def _parse_case_groups(payload: str) -> list[dict]:
    data = parse_json_object(payload)
    if not isinstance(data, dict):
        return []
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
) -> list[dict]:
    tiles = db.fetch_tiles(session_id=session_id)
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
            )
            tile = Tile(
                id=f"case_group_{case_group_id}",
                title=title,
                text=text,
                meta_information={
                    "case_group_id": case_group_id,
                    "process_id": process_id,
                    "change_status": case_group_status,
                },
                column=base_col,
                row=base_row + (idx * row_spacing),
                deletable=True,
                link_from_tile=[process_tile_id],
            )
            db.upsert_tile(tile, session_id=session_id)
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
    try:
        session_id, _created, model = db.ensure_session(
            payload.app_session_id,
            payload.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    existing = db.list_case_groups_for_session(session_id)
    if existing:
        processes = db.list_processes_for_session(session_id)
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
        }

    processes = db.list_processes_for_session(session_id)
    if not processes:
        raise HTTPException(status_code=400, detail="No processes for session")
    current_law_text, proposed_law_text = db.get_session_law_texts(session_id)
    regulations = db.list_regulations_for_session(session_id)
    prozesse_payload = build_processes_payload_with_regulations(processes, regulations)

    prompt = render_prompt(
        PromptId.CASE_GROUP_DEVELOPMENT,
        gesetz_gueltig=current_law_text,
        gesetz_vorschlag=proposed_law_text,
        prozesse_json=json.dumps(prozesse_payload, ensure_ascii=False),
    )
    response_text = await query_llm(
        prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
    )
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
        db.insert_llm_answer(
            session_id=session_id,
            prompt_id=PromptId.CASE_GROUP_DEVELOPMENT,
            model=model,
            answer_text=response_text,
            metadata={"provider": payload.provider},
        )
        created = _add_case_group_tiles(session_id, parsed)
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
        ]
    }
