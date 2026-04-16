from __future__ import annotations

import logging
import re
from pathlib import Path

import json

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.core.auth import ApiKeys, get_api_keys
from backend.core.change_status import extract_change_status, normalize_change_status
from backend.core.config import settings
from backend.core import db
from backend.core.llm_attempts import (
    mark_llm_answer_applied,
)
from backend.core.llm_json import clean_llm_payload, parse_json_object, require_json_object
from backend.core.llm_service import query_llm
from backend.core.prompts import PromptId, render_prompt
from backend.core.session_graph import sync_all_norm_addressee_tile_snapshots
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.routers._llm_router_utils import (
    ensure_session_or_400,
    query_and_stage_or_http,
    run_with_answer_apply_guard,
)


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


def _parse_summary(payload: str) -> tuple[str, str, str]:
    payload = payload.strip()
    if not payload:
        return "", "", ""

    cleaned = clean_llm_payload(payload)
    data = parse_json_object(payload)
    if data:
        title = str(data.get("title", "")).strip()
        blurb = str(data.get("blurb", "")).strip()
        summary = str(data.get("summary", "")).strip()
        if not summary:
            summary = blurb
        if not blurb:
            blurb = summary
        if title or blurb or summary:
            return title, blurb, summary

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return "", "", ""
    title = lines[0][:120]
    body = " ".join(lines[1:]).strip()
    return title, body, body


def _parse_vorgaben(payload: str) -> list[dict]:
    data, _parse_mode = require_json_object(
        payload,
        error_context="Invalid regulations_identification payload",
        required_top_level_key="vorgaben",
    )
    vorgaben = data.get("vorgaben")
    if not isinstance(vorgaben, list):
        raise HTTPException(
            status_code=422,
            detail="Invalid regulations_identification payload: 'vorgaben' must be a list",
        )
    parsed = []
    for entry in vorgaben:
        if not isinstance(entry, dict):
            continue
        normzitat = str(entry.get("normzitat", "")).strip()
        beschreibung = str(entry.get("beschreibung", "")).strip()
        aenderungsstatus = extract_change_status(entry)
        normadressaten = _parse_addressee_list(
            entry.get("normadressaten")
            or entry.get("normadressat")
        )
        if not normadressaten:
            normadressaten = [ADMINISTRATION]
        is_business_information_obligation = bool(
            _parse_bool_like(
                entry.get("ist_informationspflicht_wirtschaft")
                or entry.get("informationspflicht_wirtschaft")
            )
        )
        # Per Leitfaden (StBA): Die Unterscheidung zwischen Informationspflichten
        # und uebrigen Vorgaben ist nur fuer Wirtschaft gefordert. Setzt das LLM
        # das Flag ohne BUSINESS im Normadressaten-Set, ergaenzen wir BUSINESS
        # (robust gegen unvollstaendige LLM-Ausgaben) UND loggen den Vorfall,
        # damit Folge-Korrekturen auffindbar sind.
        if is_business_information_obligation and BUSINESS not in normadressaten:
            logger.warning(
                "regulations_identification: informationspflicht-Flag ohne "
                "BUSINESS-Normadressat; BUSINESS wird ergaenzt. normzitat=%r "
                "normadressaten=%r",
                normzitat[:120],
                list(normadressaten),
            )
            normadressaten.append(BUSINESS)
        if not normzitat and not beschreibung:
            continue
        parsed.append(
            {
                "normzitat": normzitat,
                "beschreibung": beschreibung,
                "aenderungsstatus": aenderungsstatus,
                "applies_to_administration": ADMINISTRATION in normadressaten,
                "applies_to_business": BUSINESS in normadressaten,
                "applies_to_citizens": CITIZENS in normadressaten,
                "normadressaten": normadressaten,
                "is_business_information_obligation": is_business_information_obligation,
            }
        )
    return parsed


def _parse_bool_like(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "ja", "yes", "y"}:
            return True
        if normalized in {"0", "false", "nein", "no", "n"}:
            return False
    return None


def _parse_addressee_list(value: object) -> list[str]:
    raw_values: list[object]
    if isinstance(value, list):
        raw_values = value
    elif value is None:
        raw_values = []
    else:
        raw_values = [value]
    parsed: list[str] = []
    for item in raw_values:
        raw_item = str(item or "").strip().lower()
        if not raw_item:
            continue
        fragments = [
            fragment.strip()
            for fragment in re.split(r"[,;/]|\bund\b|\band\b", raw_item)
            if fragment.strip()
        ]
        if not fragments:
            fragments = [raw_item]
        for normalized in fragments:
            if normalized == ADMINISTRATION and ADMINISTRATION not in parsed:
                parsed.append(ADMINISTRATION)
            elif normalized == BUSINESS and BUSINESS not in parsed:
                parsed.append(BUSINESS)
            elif normalized == CITIZENS and CITIZENS not in parsed:
                parsed.append(CITIZENS)
    return parsed


def _update_law_tile(
    session_id: int,
    title: str,
    blurb: str,
    filename: str,
    model: str,
    current_filename: str | None = None,
) -> Tile:
    tiles = db.fetch_tiles(session_id=session_id)
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

    db.upsert_tile(tile, session_id=session_id)
    return tile


def _add_vorgaben_tiles(session_id: int, vorgaben: list[dict]) -> list[dict]:
    base_col = 0
    base_row = 0
    law_tile = next(
        (item for item in db.fetch_tiles(session_id=session_id) if item.id == "law_tile"),
        None,
    )
    if law_tile:
        base_col = law_tile.column
        base_row = law_tile.row
    row_spacing = 1
    created = []
    for idx, vorgabe in enumerate(vorgaben):
        title = vorgabe.get("normzitat") or f"Vorgabe {idx + 1}"
        text = vorgabe.get("beschreibung") or ""
        aenderungsstatus = normalize_change_status(vorgabe.get("aenderungsstatus"))
        regulation_id = db.insert_regulation(
            session_id=session_id,
            legal_citation=title,
            description=text,
            change_status=aenderungsstatus,
            applies_to_administration=bool(vorgabe.get("applies_to_administration", True)),
            applies_to_business=bool(vorgabe.get("applies_to_business")),
            applies_to_citizens=bool(vorgabe.get("applies_to_citizens")),
            is_business_information_obligation=bool(
                vorgabe.get("is_business_information_obligation")
            ),
        )
        tile = Tile(
            id=f"regulation_{regulation_id}",
            title=title,
            text=text,
            meta_information={
                "regulation_id": regulation_id,
                "change_status": aenderungsstatus,
                "normadressaten": list(vorgabe.get("normadressaten") or []),
                "is_business_information_obligation": bool(
                    vorgabe.get("is_business_information_obligation")
                ),
            },
            column=base_col + 1,
            row=base_row + (idx * row_spacing),
            deletable=True,
            link_from_tile=["law_tile"],
        )
        db.upsert_tile(tile, session_id=session_id)
        created.append(
            {
                "regulation_id": regulation_id,
                "normzitat": title,
                "beschreibung": text,
                "aenderungsstatus": aenderungsstatus,
            }
        )
    return created


def _clear_existing_tiles(session_id: int) -> None:
    for tile in db.fetch_tiles(session_id=session_id):
        db.delete_tile(tile.id, session_id=session_id)


@router.post("/identify")
async def identify_regulations(
    payload: RegulationIdentifyRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )
    current_text, proposed_text = db.get_session_law_texts(session_id)
    if not current_text or not proposed_text:
        raise HTTPException(
            status_code=422,
            detail="Law files not selected for session. Run summary first.",
        )
    existing = db.list_regulations_for_session(session_id)
    if existing:
        return {
            "vorgaben": [
                {
                    "regulation_id": row["regulation_id"],
                    "normzitat": row["legal_citation"],
                    "beschreibung": row["description"],
                    "aenderungsstatus": row["change_status"],
                }
                for row in existing
            ],
            "status": "existing",
        }

    prompt = render_prompt(
        PromptId.REGULATIONS_IDENTIFICATION,
        session_id=session_id,
        gesetz_gueltig=current_text,
        gesetz_vorschlag=proposed_text,
    )
    answer_id, llm_result = await query_and_stage_or_http(
        session_id=session_id,
        prompt_id=PromptId.REGULATIONS_IDENTIFICATION,
        prompt=prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
        query_fn=query_llm,
    )
    response_text = llm_result.text

    def _apply() -> list[dict]:
        vorgaben = _parse_vorgaben(response_text)
        if not vorgaben:
            raise HTTPException(status_code=422, detail="No vorgaben parsed")
        with db.transaction():
            created_local = _add_vorgaben_tiles(session_id, vorgaben)
            session = db.get_session_by_id(session_id)
            if session:
                sync_all_norm_addressee_tile_snapshots(session)
            mark_llm_answer_applied(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.REGULATIONS_IDENTIFICATION,
            )
        return created_local

    created = run_with_answer_apply_guard(answer_id=answer_id, apply_fn=_apply)
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

    if payload.app_session_id:
        session_id, _created, model = ensure_session_or_400(
            payload.app_session_id,
            payload.model,
        )
    else:
        model = str(payload.model or "").strip()
        if not model:
            raise HTTPException(status_code=400, detail="Model is required")
        latest = db.get_latest_session()
        if latest:
            session_id = int(latest["session_id"])
        else:
            session_id, _created = db.upsert_session("SUMMARY-AUTO", model)
    answer_id, llm_result = await query_and_stage_or_http(
        session_id=session_id,
        prompt_id=PromptId.LAW_SUMMARY,
        prompt=prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
        query_fn=query_llm,
    )
    response_text = llm_result.text
    title, blurb, summary = _parse_summary(response_text)
    if not title:
        title = filename

    def _apply() -> None:
        with db.transaction():
            if payload.app_session_id:
                try:
                    db.update_session_documents(
                        payload.app_session_id,
                        current_filename,
                        filename,
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=404, detail=str(exc)) from exc
            _clear_existing_tiles(session_id)
            _update_law_tile(
                session_id,
                title,
                blurb,
                filename,
                model,
                current_filename=current_filename,
            )
            if payload.app_session_id:
                db.update_session_summary(
                    payload.app_session_id,
                    title,
                    summary,
                    law_diff_blurb=blurb,
                )
                session = db.get_session_by_app_id(payload.app_session_id)
                if session:
                    sync_all_norm_addressee_tile_snapshots(session)
            mark_llm_answer_applied(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.LAW_SUMMARY,
            )

    run_with_answer_apply_guard(answer_id=answer_id, apply_fn=_apply)
    return {
        "title": title,
        "summary": summary,
        "blurb": blurb,
        "filename": filename,
    }
