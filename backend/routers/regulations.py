from __future__ import annotations

from pathlib import Path
import re

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.core.auth import ApiKeys, get_api_keys
from backend.core.config import settings
from backend.core import db
from backend.core.llm_service import query_llm
from backend.core.prompts import PromptId, render_prompt
from backend.core.models import Tile


router = APIRouter(prefix="/regulations", tags=["regulations"])


def _ensure_regulations_dir() -> Path:
    path = settings.regulations_path
    path.mkdir(parents=True, exist_ok=True)
    return path


class RegulationSummaryRequest(BaseModel):
    filename: str
    current_filename: str | None = None
    app_session_id: str | None = None
    model: str | None = None
    provider: str | None = None


class RegulationIdentifyRequest(BaseModel):
    current_filename: str
    proposed_filename: str
    app_session_id: str
    model: str | None = None
    provider: str | None = None


@router.get("")
async def list_regulations() -> dict:
    files = db.list_law_file_names()
    return {"files": files}


@router.post("/upload")
async def upload_regulation(
    file: UploadFile = File(...),
    filename: str | None = Form(default=None),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    desired_name = Path(filename or file.filename).name
    if not desired_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if db.get_law_by_filename(desired_name):
        raise HTTPException(
            status_code=409,
            detail={"error": "exists", "filename": desired_name},
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    law_text = content.decode("utf-8", errors="ignore").strip()
    if not law_text:
        raise HTTPException(status_code=400, detail="Empty file")
    document_id = db.insert_law(desired_name, law_text)
    return {"ok": True, "filename": desired_name, "document_id": document_id}


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_FENCE_RE = re.compile(r"```(?:think|thinking)[\\s\\S]*?```", re.IGNORECASE)


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


def _parse_summary(payload: str) -> tuple[str, str]:
    payload = payload.strip()
    if not payload:
        return "", ""

    cleaned = _clean_llm_payload(payload)

    try:
        data = json.loads(cleaned)
        title = str(data.get("title", "")).strip()
        blurb = str(data.get("blurb", "")).strip()
        if title or blurb:
            return title, blurb
    except Exception:
        pass

    data = _extract_last_json(cleaned)
    if data:
        title = str(data.get("title", "")).strip()
        blurb = str(data.get("blurb", "")).strip()
        if title or blurb:
            return title, blurb

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return "", ""
    title = lines[0][:120]
    blurb = " ".join(lines[1:]).strip()
    return title, blurb


def _parse_vorgaben(payload: str) -> list[dict]:
    cleaned = _clean_llm_payload(payload)
    data = None
    try:
        data = json.loads(cleaned)
    except Exception:
        data = _extract_last_json(cleaned)
    if not isinstance(data, dict):
        return []
    vorgaben = data.get("vorgaben")
    if not isinstance(vorgaben, list):
        return []
    parsed = []
    for entry in vorgaben:
        if not isinstance(entry, dict):
            continue
        normzitat = str(entry.get("normzitat", "")).strip()
        beschreibung = str(entry.get("beschreibung", "")).strip()
        if not normzitat and not beschreibung:
            continue
        parsed.append(
            {
                "normzitat": normzitat,
                "beschreibung": beschreibung,
            }
        )
    return parsed


def _update_law_tile(
    title: str,
    blurb: str,
    filename: str,
    model: str,
    current_filename: str | None = None,
) -> Tile:
    tiles = db.fetch_tiles()
    tile = next((item for item in tiles if item.id == "law_tile"), None)
    if tile is None:
        tile = Tile(
            id="law_tile",
            title=title or filename,
            text=blurb,
            meta_information={},
            column=0,
            row=0,
            deletable=False,
            link_from_tile=[],
        )
    else:
        tile.title = title or tile.title
        tile.text = blurb or tile.text

    meta = dict(tile.meta_information or {})
    meta["source_file"] = filename
    if current_filename:
        meta["source_current_file"] = current_filename
    if model:
        meta["summary_model"] = model
    tile.meta_information = meta

    db.upsert_tile(tile)
    return tile


def _add_vorgaben_tiles(session_id: int, vorgaben: list[dict]) -> list[dict]:
    base_col = 0
    base_row = 0
    law_tile = next((item for item in db.fetch_tiles() if item.id == "law_tile"), None)
    if law_tile:
        base_col = law_tile.column
        base_row = law_tile.row
    row_spacing = 1
    created = []
    for idx, vorgabe in enumerate(vorgaben):
        title = vorgabe.get("normzitat") or f"Vorgabe {idx + 1}"
        text = vorgabe.get("beschreibung") or ""
        regulation_id = db.insert_regulation(
            session_id=session_id,
            legal_citation=title,
            description=text,
        )
        tile = Tile(
            id=f"regulation_{regulation_id}",
            title=title,
            text=text,
            meta_information={"regulation_id": regulation_id},
            column=base_col + 1,
            row=base_row + (idx * row_spacing),
            deletable=True,
            link_from_tile=["law_tile"],
        )
        db.upsert_tile(tile)
        created.append(
            {
                "regulation_id": regulation_id,
                "normzitat": title,
                "beschreibung": text,
            }
        )
    return created


def _clear_existing_tiles() -> None:
    for tile in db.fetch_tiles():
        db.delete_tile(tile.id)


@router.post("/identify")
async def identify_regulations(
    payload: RegulationIdentifyRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    current_filename = Path(payload.current_filename).name
    proposed_filename = Path(payload.proposed_filename).name
    if not current_filename or not proposed_filename:
        raise HTTPException(status_code=400, detail="Invalid filenames")

    current_law = db.get_law_by_filename(current_filename)
    if not current_law:
        raise HTTPException(status_code=404, detail="Current file not found")
    proposed_law = db.get_law_by_filename(proposed_filename)
    if not proposed_law:
        raise HTTPException(status_code=404, detail="Proposed file not found")

    current_text = str(current_law.get("law_text", "")).strip()
    proposed_text = str(proposed_law.get("law_text", "")).strip()
    if not current_text or not proposed_text:
        raise HTTPException(status_code=400, detail="Empty file")

    model = payload.model or settings.default_model
    session_id, _created = db.upsert_session(payload.app_session_id, model)
    existing = db.list_regulations_for_session(session_id)
    if existing:
        return {
            "vorgaben": [
                {
                    "regulation_id": row["regulation_id"],
                    "normzitat": row["legal_citation"],
                    "beschreibung": row["description"],
                }
                for row in existing
            ],
            "status": "existing",
        }

    prompt = render_prompt(
        PromptId.REGULATIONS_IDENTIFICATION,
        gesetz_gueltig=current_text,
        gesetz_vorschlag=proposed_text,
    )
    response_text = await query_llm(
        prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.REGULATIONS_IDENTIFICATION,
        model=model,
        answer_text=response_text,
        metadata={
            "provider": payload.provider,
        },
    )
    vorgaben = _parse_vorgaben(response_text)
    if not vorgaben:
        raise HTTPException(status_code=422, detail="No vorgaben parsed")
    created = _add_vorgaben_tiles(session_id, vorgaben)
    return {"vorgaben": created}


@router.post("/summary")
async def summarize_regulation(
    payload: RegulationSummaryRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    filename = Path(payload.filename).name
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    proposed_law = db.get_law_by_filename(filename)
    if not proposed_law:
        raise HTTPException(status_code=404, detail="File not found")
    content = str(proposed_law.get("law_text", "")).strip()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    current_filename = None
    current_content = ""
    if payload.current_filename:
        current_filename = Path(payload.current_filename).name
        if not current_filename:
            raise HTTPException(status_code=400, detail="Invalid current filename")
        current_law = db.get_law_by_filename(current_filename)
        if not current_law:
            raise HTTPException(status_code=404, detail="Current file not found")
        current_content = str(current_law.get("law_text", "")).strip()
        if not current_content:
            raise HTTPException(status_code=400, detail="Current file is empty")

    prompt = render_prompt(
        PromptId.LAW_SUMMARY,
        gesetz_gueltig=current_content or content,
        gesetz_vorschlag=content,
    )

    model = payload.model or settings.default_model
    session_id = None
    if payload.app_session_id:
        session_id, _created = db.upsert_session(payload.app_session_id, model)
        try:
            db.update_session_documents(
                payload.app_session_id,
                current_filename,
                filename,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    _clear_existing_tiles()
    response_text = await query_llm(
        prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
    )
    if session_id is not None:
        db.insert_llm_answer(
            session_id=session_id,
            prompt_id=PromptId.LAW_SUMMARY,
            model=model,
            answer_text=response_text,
            metadata={
                "provider": payload.provider,
            },
        )
    title, blurb = _parse_summary(response_text)
    if not title:
        title = filename
    _update_law_tile(title, blurb, filename, model, current_filename=current_filename)
    if payload.app_session_id:
        db.update_session_summary(payload.app_session_id, title, blurb)

    return {"title": title, "blurb": blurb, "filename": filename}
