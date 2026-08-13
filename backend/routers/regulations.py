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
from backend.core.legisllm_import import LegisLlmImportError, build_legisllm_law_texts
from backend.core.llm_attempts import (
    mark_llm_answer_applied,
)
from backend.core.llm_json import clean_llm_payload, parse_json_object, require_json_object
from backend.core.llm_service import query_llm
from backend.core.prompts import PromptId, render_prompt
from backend.core.session_graph import sync_all_norm_addressee_tile_snapshots
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.auth import AuthUser, get_current_user
from backend.routers._llm_router_utils import (
    ensure_session_or_400,
    query_and_stage_or_http,
    run_with_answer_apply_guard,
)


router = APIRouter(prefix="/regulations", tags=["regulations"])

_NEW_LAW_BASELINE_TEXT = (
    "Es gibt kein aktuell geltendes Gegenstueck. "
    "Der Gesetzesvorschlag ist als neue Regelung ohne bestehenden Ausgangstext "
    "zu behandeln."
)

_LAW_MODE_CONTEXTS: dict[tuple[str, str], str] = {
    (
        PromptId.LAW_SUMMARY,
        "comparison",
    ): (
        "Arbeitsmodus: Vergleich. Vergleichen Sie geltenden Text und "
        "Gesetzesvorschlag direkt miteinander.\n\n"
    ),
    (
        PromptId.REGULATIONS_IDENTIFICATION,
        "comparison",
    ): (
        "Arbeitsmodus: Vergleich. Identifizieren Sie die Unterschiede zwischen "
        "geltendem Text und Gesetzesvorschlag.\n\n"
    ),
    (
        PromptId.LAW_SUMMARY,
        "new_law",
    ): (
        "Arbeitsmodus: Neuregelung. Es gibt kein aktuell geltendes "
        "Vergleichsgesetz. Behandeln Sie den Gesetzesvorschlag als vollstaendig "
        "neue Regelung und stellen Sie keinen Selbstvergleich an.\n\n"
    ),
    (
        PromptId.REGULATIONS_IDENTIFICATION,
        "new_law",
    ): (
        "Arbeitsmodus: Neuregelung. Es gibt kein aktuell geltendes "
        "Vergleichsgesetz. Identifizieren Sie die im Gesetzesvorschlag enthaltenen "
        "Vorgaben als Einfuehrungen, soweit nicht aus dem Text selbst etwas anderes "
        "hervorgeht, und stellen Sie keinen Selbstvergleich an.\n\n"
    ),
}


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
async def list_regulations(
    user: AuthUser = Depends(get_current_user),
) -> dict:
    files = db.list_law_file_names(owner_user_id=user.user_id)
    return {"files": files}


@router.post("/upload")
async def upload_regulation(
    file: UploadFile = File(...),
    filename: str | None = Form(default=None),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    desired_name = Path(filename or file.filename).name
    if not desired_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if db.get_law_by_filename(desired_name, owner_user_id=user.user_id):
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
    document_id = db.insert_law(
        desired_name,
        law_text,
        owner_user_id=user.user_id,
        is_builtin=False,
    )
    return {"ok": True, "filename": desired_name, "document_id": document_id}


@router.post("/import/legisllm")
async def import_legisllm_export(
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read()
    try:
        law_texts = build_legisllm_law_texts(content)
    except LegisLlmImportError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"LegisLLM-Export konnte nicht gelesen werden: {exc}",
        ) from exc

    try:
        with db.transaction():
            current_id, current_created = db.insert_or_reuse_law(
                law_texts.current_filename,
                law_texts.current_text,
                owner_user_id=user.user_id,
            )
            proposed_id, proposed_created = db.insert_or_reuse_law(
                law_texts.proposed_filename,
                law_texts.proposed_text,
                owner_user_id=user.user_id,
            )
    except ValueError as exc:
        logger.warning("LegisLLM import conflict for user=%s: %s", user.user_id, exc)
        raise HTTPException(
            status_code=409,
            detail=(
                "LegisLLM-Export konnte nicht wiederverwendet werden, weil bereits "
                "ein Eintrag mit gleichem Namen, aber anderem Inhalt existiert."
            ),
        ) from exc

    created = current_created or proposed_created
    return {
        "ok": True,
        "created": created,
        "current_filename": law_texts.current_filename,
        "proposed_filename": law_texts.proposed_filename,
        "current_document_id": current_id,
        "proposed_document_id": proposed_id,
        "message": (
            "LegisLLM-Export importiert. Gültige Fassung und Vorschlag sind ausgewählt."
            if created
            else "LegisLLM-Export war bereits vorhanden. Die Fassungen wurden ausgewählt."
        ),
    }


def _parse_summary(payload: str) -> tuple[str, str, str]:
    payload = payload.strip()
    if not payload:
        return "", "", ""

    cleaned = clean_llm_payload(payload)
    try:
        data = parse_json_object(payload)
    except ValueError:
        data = None
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
        if is_business_information_obligation and BUSINESS not in normadressaten:
            logger.warning(
                "event=ip_flag_cleared reason=missing_business_in_addressees "
                "normzitat=%r addressees=%r",
                normzitat[:120],
                list(normadressaten),
            )
            is_business_information_obligation = False
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


def _resolve_law_mode(
    current_text: str,
    proposed_text: str,
) -> tuple[str, str]:
    if not proposed_text:
        raise HTTPException(
            status_code=422,
            detail=(
                "Proposed law not selected for session. "
                "Select a proposed law and run summary first."
            ),
        )
    if current_text:
        return "comparison", current_text
    return "new_law", _NEW_LAW_BASELINE_TEXT


def _render_law_mode_context(prompt_id: str, law_mode: str) -> str:
    """Render mode-specific prompt guidance for summary vs. regulations tasks.
    Distinguishes comparison runs from proposed-only new-law runs."""
    try:
        return _LAW_MODE_CONTEXTS[(prompt_id, law_mode)]
    except KeyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
            f"Unsupported law mode context combination: prompt_id={prompt_id!r}, "
            f"law_mode={law_mode!r}"
            ),
        ) from exc


@router.post("/identify")
async def identify_regulations(
    payload: RegulationIdentifyRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
        user,
    )
    current_text, proposed_text = db.get_session_law_texts(session_id)
    law_mode, current_prompt_text = _resolve_law_mode(current_text, proposed_text)
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
        gesetz_gueltig=current_prompt_text,
        gesetz_vorschlag=proposed_text,
        law_mode_context=_render_law_mode_context(
            PromptId.REGULATIONS_IDENTIFICATION, law_mode
        ),
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
    user: AuthUser = Depends(get_current_user),
) -> dict:
    if not payload.app_session_id:
        raise HTTPException(status_code=400, detail="app_session_id is required")
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
        user,
    )

    filename = Path(payload.filename).name
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    proposed_law = db.get_law_by_filename(filename, owner_user_id=user.user_id)
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
        current_law = db.get_law_by_filename(current_filename, owner_user_id=user.user_id)
        if not current_law:
            raise HTTPException(status_code=404, detail="Current file not found")
        current_content = str(current_law.get("law_text", "")).strip()
        if not current_content:
            raise HTTPException(status_code=400, detail="Current file is empty")

    law_mode, current_prompt_text = _resolve_law_mode(current_content, content)
    prompt = render_prompt(
        PromptId.LAW_SUMMARY,
        gesetz_gueltig=current_prompt_text,
        gesetz_vorschlag=content,
        law_mode_context=_render_law_mode_context(PromptId.LAW_SUMMARY, law_mode),
    )

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
            try:
                db.update_session_documents(
                    payload.app_session_id,
                    current_filename,
                    filename,
                    owner_user_id=user.user_id,
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
