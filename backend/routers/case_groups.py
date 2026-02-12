from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.auth import ApiKeys, get_api_keys
from backend.core.config import settings
from backend.core.llm_service import query_llm
from backend.core.models import Tile
from backend.core.prompts import PromptId, render_prompt


router = APIRouter(prefix="/case-groups", tags=["case-groups"])

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_FENCE_RE = re.compile(r"```(?:think|thinking)[\\s\\S]*?```", re.IGNORECASE)


class CaseGroupDevelopmentRequest(BaseModel):
    app_session_id: str
    model: str | None = None
    provider: str | None = None


def _clean_llm_payload(payload: str) -> str:
    cleaned = _THINK_BLOCK_RE.sub("", payload)
    cleaned = _THINK_FENCE_RE.sub("", cleaned)
    return cleaned.strip()


def _extract_last_json(payload: str) -> dict | None:
    decoder = json.JSONDecoder()
    index = 0
    last: dict | None = None
    while True:
        start = payload.find("{", index)
        if start == -1:
            break
        try:
            data, end = decoder.raw_decode(payload, start)
            if isinstance(data, dict):
                last = data
            index = end
        except json.JSONDecodeError:
            index = start + 1
    return last


def _parse_case_groups(payload: str) -> list[dict]:
    cleaned = _clean_llm_payload(payload)
    data = None
    try:
        data = json.loads(cleaned)
    except Exception:
        data = _extract_last_json(cleaned)
    if not isinstance(data, dict):
        return []
    processes = data.get("prozesse")
    if not isinstance(processes, list):
        return []
    parsed = []
    for entry in processes:
        if not isinstance(entry, dict):
            continue
        process_id_raw = str(entry.get("prozess_id", "")).strip()
        if not process_id_raw:
            continue
        try:
            process_id = int(process_id_raw)
        except ValueError:
            continue
        process_name = str(entry.get("prozess_bezeichnung", "")).strip()
        process_description = str(entry.get("prozess_beschreibung", "")).strip()
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
            if not name and not description:
                continue
            parsed_fallgruppen.append(
                {
                    "fallgruppe_bezeichnung": name,
                    "fallgruppe_beschreibung": description,
                }
            )
        parsed.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process_name,
                "prozess_beschreibung": process_description,
                "fallgruppen": parsed_fallgruppen,
            }
        )
    return parsed


def _build_prozesse_payload(
    processes: list[dict],
    regulations: list[dict],
) -> list[dict]:
    regs_by_process: dict[int, list[dict]] = {}
    for regulation in regulations:
        process_id = regulation.get("process_id")
        if process_id is None:
            continue
        regs_by_process.setdefault(int(process_id), []).append(regulation)

    payload = []
    for process in processes:
        process_id = int(process["process_id"])
        vorgaben = [
            {
                "vorgaben_id": row["regulation_id"],
                "normzitat": row["legal_citation"],
                "beschreibung": row["description"],
            }
            for row in regs_by_process.get(process_id, [])
        ]
        payload.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "vorgaben": vorgaben,
            }
        )
    return payload


def _add_case_group_tiles(
    session_id: int,
    processes: list[dict],
) -> list[dict]:
    tiles = db.fetch_tiles()
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
            case_group_id = db.insert_case_group(
                session_id=session_id,
                process_id=process_id,
                case_group=title,
                description=text,
            )
            tile = Tile(
                id=f"case_group_{case_group_id}",
                title=title,
                text=text,
                meta_information={
                    "case_group_id": case_group_id,
                    "process_id": process_id,
                },
                column=base_col,
                row=base_row + (idx * row_spacing),
                deletable=True,
                link_from_tile=[process_tile_id],
            )
            db.upsert_tile(tile)
            created.append(
                {
                    "case_group_id": case_group_id,
                    "fallgruppe_bezeichnung": title,
                    "fallgruppe_beschreibung": text,
                    "process_id": process_id,
                }
            )
    return created


@router.post("/develop")
async def develop_case_groups(
    payload: CaseGroupDevelopmentRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    model = payload.model or settings.default_model
    session_id, _created = db.upsert_session(payload.app_session_id, model)
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
                }
            )
        return {
            "prozesse": [
                {
                    "process_id": process["process_id"],
                    "prozess_bezeichnung": process["process"],
                    "prozess_beschreibung": process["description"],
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
    regulations = db.list_regulations_for_session(session_id)
    prozesse_payload = _build_prozesse_payload(processes, regulations)

    prompt = render_prompt(
        PromptId.CASE_GROUP_DEVELOPMENT,
        prozesse_json=json.dumps(prozesse_payload, ensure_ascii=False),
    )
    response_text = await query_llm(
        prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.CASE_GROUP_DEVELOPMENT,
        model=model,
        answer_text=response_text,
        metadata={"provider": payload.provider},
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

    created = _add_case_group_tiles(session_id, parsed)
    grouped: dict[int, list[dict]] = {}
    for entry in created:
        grouped.setdefault(entry["process_id"], []).append(
            {
                "case_group_id": entry["case_group_id"],
                "fallgruppe_bezeichnung": entry["fallgruppe_bezeichnung"],
                "fallgruppe_beschreibung": entry["fallgruppe_beschreibung"],
            }
        )
    return {
        "prozesse": [
            {
                "process_id": process["process_id"],
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "fallgruppen": grouped.get(process["process_id"], []),
            }
            for process in processes
            if process["process_id"] in grouped
        ]
    }
