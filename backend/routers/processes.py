from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
from backend.core.payload_builders import build_vorgaben_payload, dump_prompt_json
from backend.core.prompts import PromptId, render_prompt


router = APIRouter(prefix="/processes", tags=["processes"])


def format_existing_processes_response(
    existing: list[dict],
    norm_addressee: str,
) -> dict:
    return {
        "prozesse": [
            {
                "process_id": row["process_id"],
                "prozess_bezeichnung": row["process"],
                "prozess_beschreibung": row["description"],
                "aenderungsstatus": row["change_status"],
            }
            for row in existing
        ],
        "status": "existing",
        "norm_addressee": norm_addressee,
    }


def build_process_compilation_prompt(
    *,
    session_id: int,
    norm_addressee: str,
) -> tuple[str | None, dict]:
    regulations = db.list_regulations_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    session_has_any_regulations = bool(db.list_regulations_for_session(session_id))
    if not regulations and session_has_any_regulations:
        return None, {"status": "skipped", "regulations": [], "regulation_lookup": {}}
    if not regulations:
        raise HTTPException(status_code=400, detail="No regulations for session")
    vorgaben_payload = build_vorgaben_payload(regulations, norm_addressee=norm_addressee)
    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        session_id=session_id,
        vorgaben_json=dump_prompt_json(vorgaben_payload),
        norm_addressee=norm_addressee,
    )
    return prompt, {
        "status": "ready",
        "regulations": regulations,
        "regulation_lookup": {row["regulation_id"]: row for row in regulations},
    }


def parse_process_compilation_answer(
    *,
    response_text: str,
    norm_addressee: str,
    context: dict,
) -> tuple[list[dict], set[str]]:
    processes, fallback_kinds = _parse_processes(response_text, norm_addressee)
    if not processes:
        if _is_explicit_empty_process_list(response_text):
            return [], fallback_kinds
        raise HTTPException(status_code=422, detail="No processes parsed")
    _validate_vorgaben(processes, context["regulation_lookup"])
    return processes, fallback_kinds


def _is_explicit_empty_process_list(payload: str) -> bool:
    data, _parse_mode = require_json_object(
        payload,
        error_context="process compilation",
        required_top_level_key="prozesse",
    )
    return data.get("prozesse") == []


def apply_process_compilation(
    *,
    session_id: int,
    norm_addressee: str,
    parsed: list[dict],
    context: dict,
) -> list[dict]:
    return _add_process_tiles(
        session_id,
        parsed,
        context["regulation_lookup"],
        norm_addressee=norm_addressee,
    )


def _parse_processes(
    payload: str,
    norm_addressee: str | None = None,
) -> tuple[list[dict], set[str]]:
    data, _parse_mode = require_json_object(
        payload,
        error_context="process compilation",
        required_top_level_key="prozesse",
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
        name = str(entry.get("prozess_bezeichnung", "")).strip()
        description = str(entry.get("prozess_beschreibung", "")).strip()
        process_status = extract_change_status(entry)
        vorgaben = entry.get("vorgaben")
        if not isinstance(vorgaben, list):
            vorgaben = []
        parsed_vorgaben = []
        for vorgabe in vorgaben:
            if not isinstance(vorgabe, dict):
                continue
            vorgaben_id = parse_first_int(vorgabe, "vorgaben_id")
            normzitat = str(vorgabe.get("normzitat", "")).strip()
            beschreibung = str(vorgabe.get("beschreibung", "")).strip()
            vorgabe_status = extract_change_status(vorgabe)
            if vorgaben_id is not None or normzitat or beschreibung:
                parsed_vorgaben.append(
                    {
                        "vorgaben_id": vorgaben_id,
                        "normzitat": normzitat,
                        "beschreibung": beschreibung,
                        "aenderungsstatus": vorgabe_status,
                    }
                )
        if not name and not description:
            continue
        parsed.append(
            {
                "prozess_bezeichnung": name,
                "prozess_beschreibung": description,
                "aenderungsstatus": process_status,
                "vorgaben": parsed_vorgaben,
            }
        )
    return parsed, fallback_kinds


def _add_process_tiles(
    session_id: int,
    processes: list[dict],
    regulation_lookup: dict[int, dict],
    norm_addressee: str = ADMINISTRATION,
) -> list[dict]:
    base_col = 2
    base_row = 0
    tiles = db.fetch_tiles(session_id=session_id, norm_addressee=norm_addressee)
    regulation_tiles = [tile for tile in tiles if tile.id.startswith("regulation_")]
    if regulation_tiles:
        base_col = max(tile.column for tile in regulation_tiles) + 1
        base_row = min(tile.row for tile in regulation_tiles)
    else:
        law_tile = next((item for item in tiles if item.id == "law_tile"), None)
        if law_tile:
            base_col = law_tile.column + 2
            base_row = law_tile.row
    available_tile_ids = {tile.id for tile in tiles}
    row_spacing = 1
    created = []
    for idx, process in enumerate(processes):
        name = process.get("prozess_bezeichnung") or f"Prozess {idx + 1}"
        description = process.get("prozess_beschreibung") or ""
        process_status = normalize_change_status(process.get("aenderungsstatus"))
        process_id = db.insert_process(
            session_id,
            name,
            description,
            change_status=process_status,
            norm_addressee=norm_addressee,
        )
        link_from_tile = []
        for vorgabe in process.get("vorgaben", []):
            regulation_id = parse_first_int(vorgabe, "vorgaben_id")
            if regulation_id is None:
                continue
            regulation = regulation_lookup.get(regulation_id)
            if not regulation:
                continue
            updated = db.update_regulation_process(
                regulation_id=regulation_id,
                process_id=process_id,
                norm_addressee=norm_addressee,
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
                        "Regulation ID mismatch for regulation_id: "
                        f"{regulation_id}"
                    ),
                )
            regulation_tile_id = f"regulation_{regulation_id}"
            if regulation_tile_id in available_tile_ids:
                link_from_tile.append(regulation_tile_id)
        tile = Tile(
            id=f"process_{process_id}",
            title=name,
            text=description,
            meta_information={
                "process_id": process_id,
                "change_status": process_status,
                "cost": None,
            },
            column=base_col,
            row=base_row + (idx * row_spacing),
            deletable=True,
            link_from_tile=link_from_tile,
        )
        db.upsert_tile(tile, session_id=session_id, norm_addressee=norm_addressee)
        created.append(
            {
                "process_id": process_id,
                "prozess_bezeichnung": name,
                "prozess_beschreibung": description,
                "aenderungsstatus": process_status,
            }
        )
    return created


def _validate_vorgaben(
    processes: list[dict],
    regulation_lookup: dict[int, dict],
) -> None:
    seen_ids: set[int] = set()
    mismatches: list[str] = []
    duplicate_ids: list[int] = []
    already_linked: list[str] = []
    for process in processes:
        for vorgabe in process.get("vorgaben", []):
            raw_id = vorgabe.get("vorgaben_id")
            regulation_id = parse_first_int(vorgabe, "vorgaben_id")
            if regulation_id is None:
                if str(raw_id or "").strip():
                    mismatches.append(f"Invalid vorgaben_id '{raw_id}'")
                continue
            if regulation_id in seen_ids:
                duplicate_ids.append(regulation_id)
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
            # TODO: Add strict/optional text consistency checks later.
            # Current behavior intentionally validates by vorgaben_id only.
            # If one-to-one ID matching fails, we should decide whether to
            # reject, retry with a repair prompt, or perform interactive review.

    if already_linked:
        raise HTTPException(
            status_code=409,
            detail="Regulations already linked: " + ", ".join(already_linked),
        )
    if duplicate_ids:
        unique_duplicate_ids = sorted(set(duplicate_ids))
        mismatches.insert(
            0,
            "Vorgaben mehrfach zu Prozessen zugeordnet: "
            + ", ".join(str(regulation_id) for regulation_id in unique_duplicate_ids),
        )
    if mismatches:
        raise HTTPException(status_code=422, detail="; ".join(mismatches[:5]))
