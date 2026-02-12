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


router = APIRouter(prefix="/processes", tags=["processes"])

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_FENCE_RE = re.compile(r"```(?:think|thinking)[\\s\\S]*?```", re.IGNORECASE)


class ProcessCompilationRequest(BaseModel):
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


def _parse_processes(payload: str) -> list[dict]:
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
        name = str(entry.get("prozess_bezeichnung", "")).strip()
        description = str(entry.get("prozess_beschreibung", "")).strip()
        vorgaben = entry.get("vorgaben")
        if not isinstance(vorgaben, list):
            vorgaben = []
        parsed_vorgaben = []
        for vorgabe in vorgaben:
            if not isinstance(vorgabe, dict):
                continue
            vorgaben_id = str(vorgabe.get("vorgaben_id", "")).strip()
            normzitat = str(vorgabe.get("normzitat", "")).strip()
            beschreibung = str(vorgabe.get("beschreibung", "")).strip()
            if vorgaben_id or normzitat or beschreibung:
                parsed_vorgaben.append(
                    {
                        "vorgaben_id": vorgaben_id,
                        "normzitat": normzitat,
                        "beschreibung": beschreibung,
                    }
                )
        if not name and not description:
            continue
        parsed.append(
            {
                "prozess_bezeichnung": name,
                "prozess_beschreibung": description,
                "vorgaben": parsed_vorgaben,
            }
        )
    return parsed


def _add_process_tiles(
    session_id: int,
    processes: list[dict],
    regulation_lookup: dict[int, dict],
) -> list[dict]:
    base_col = 2
    base_row = 0
    tiles = db.fetch_tiles()
    regulation_tiles = [tile for tile in tiles if tile.id.startswith("regulation_")]
    if regulation_tiles:
        base_col = max(tile.column for tile in regulation_tiles) + 1
        base_row = min(tile.row for tile in regulation_tiles)
    else:
        law_tile = next((item for item in tiles if item.id == "law_tile"), None)
        if law_tile:
            base_col = law_tile.column + 2
            base_row = law_tile.row
    row_spacing = 1
    created = []
    for idx, process in enumerate(processes):
        name = process.get("prozess_bezeichnung") or f"Prozess {idx + 1}"
        description = process.get("prozess_beschreibung") or ""
        process_id = db.insert_process(session_id, name, description)
        link_from_tile = []
        for vorgabe in process.get("vorgaben", []):
            raw_id = str(vorgabe.get("vorgaben_id", "")).strip()
            if not raw_id:
                continue
            try:
                regulation_id = int(raw_id)
            except ValueError:
                continue
            regulation = regulation_lookup.get(regulation_id)
            if not regulation:
                continue
            llm_normzitat = str(vorgabe.get("normzitat", "")).strip()
            llm_beschreibung = str(vorgabe.get("beschreibung", "")).strip()
            updated = db.update_regulation_process(
                regulation_id=regulation_id,
                process_id=process_id,
                legal_citation=llm_normzitat,
                description=llm_beschreibung,
            )
            if not updated:
                latest = db.get_regulation_by_id(regulation_id)
                if latest and latest.get("process_id") is not None:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Regulation already linked to a process: "
                            f"{regulation_id}"
                        ),
                    )
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Regulation text mismatch for regulation_id: "
                        f"{regulation_id}"
                    ),
                )
            link_from_tile.append(f"regulation_{regulation_id}")
        tile = Tile(
            id=f"process_{process_id}",
            title=name,
            text=description,
            meta_information={"process_id": process_id},
            column=base_col,
            row=base_row + (idx * row_spacing),
            deletable=True,
            link_from_tile=link_from_tile,
        )
        db.upsert_tile(tile)
        created.append(
            {
                "process_id": process_id,
                "prozess_bezeichnung": name,
                "prozess_beschreibung": description,
            }
        )
    return created


def _validate_vorgaben(
    processes: list[dict],
    regulation_lookup: dict[int, dict],
) -> None:
    seen_ids: set[int] = set()
    mismatches: list[str] = []
    already_linked: list[str] = []
    for process in processes:
        for vorgabe in process.get("vorgaben", []):
            raw_id = str(vorgabe.get("vorgaben_id", "")).strip()
            if not raw_id:
                continue
            try:
                regulation_id = int(raw_id)
            except ValueError:
                mismatches.append(f"Invalid vorgaben_id '{raw_id}'")
                continue
            if regulation_id in seen_ids:
                mismatches.append(
                    f"Vorgabe {regulation_id} linked to multiple processes"
                )
                continue
            seen_ids.add(regulation_id)
            regulation = regulation_lookup.get(regulation_id)
            if not regulation:
                mismatches.append(f"Vorgabe {regulation_id} not found in database")
                continue
            if regulation.get("process_id") is not None:
                already_linked.append(
                    f"{regulation_id} -> {regulation['process_id']}"
                )
                continue
            llm_normzitat = str(vorgabe.get("normzitat", "")).strip()
            llm_beschreibung = str(vorgabe.get("beschreibung", "")).strip()
            if not llm_normzitat or not llm_beschreibung:
                mismatches.append(
                    f"Vorgabe {regulation_id} missing normzitat/beschreibung"
                )
                continue
            if (
                llm_normzitat != str(regulation["legal_citation"]).strip()
                or llm_beschreibung != str(regulation["description"]).strip()
            ):
                mismatches.append(f"Vorgabe {regulation_id} text mismatch")

    if already_linked:
        raise HTTPException(
            status_code=409,
            detail="Regulations already linked: " + ", ".join(already_linked),
        )
    if mismatches:
        raise HTTPException(status_code=422, detail="; ".join(mismatches[:5]))


@router.post("/compile")
async def compile_processes(
    payload: ProcessCompilationRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    model = payload.model or settings.default_model
    session_id, _created = db.upsert_session(payload.app_session_id, model)
    existing = db.list_processes_for_session(session_id)
    if existing:
        return {
            "prozesse": [
                {
                    "process_id": row["process_id"],
                    "prozess_bezeichnung": row["process"],
                    "prozess_beschreibung": row["description"],
                }
                for row in existing
            ],
            "status": "existing",
        }

    regulations = db.list_regulations_for_session(session_id)
    if not regulations:
        raise HTTPException(status_code=400, detail="No regulations for session")
    vorgaben_payload = [
        {
            "vorgaben_id": row["regulation_id"],
            "normzitat": row["legal_citation"],
            "beschreibung": row["description"],
        }
        for row in regulations
    ]

    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        vorgaben_json=json.dumps(vorgaben_payload, ensure_ascii=False),
    )
    response_text = await query_llm(
        prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.PROCESS_COMPILATION,
        model=model,
        answer_text=response_text,
        metadata={"provider": payload.provider},
    )
    processes = _parse_processes(response_text)
    if not processes:
        raise HTTPException(status_code=422, detail="No processes parsed")
    regulation_lookup = {row["regulation_id"]: row for row in regulations}
    _validate_vorgaben(processes, regulation_lookup)
    created = _add_process_tiles(session_id, processes, regulation_lookup)
    return {"prozesse": created}
