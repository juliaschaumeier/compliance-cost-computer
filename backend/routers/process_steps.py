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


router = APIRouter(prefix="/process-steps", tags=["process-steps"])

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_FENCE_RE = re.compile(r"```(?:think|thinking)[\\s\\S]*?```", re.IGNORECASE)


class ProcessStepAnalysisRequest(BaseModel):
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


def _extract_fallgruppen(data: dict) -> list[dict]:
    if "fallgruppen" in data and isinstance(data["fallgruppen"], list):
        return data["fallgruppen"]
    processes = data.get("prozesse")
    if not isinstance(processes, list):
        return []
    fallgruppen: list[dict] = []
    for process in processes:
        if not isinstance(process, dict):
            continue
        process_groups = process.get("fallgruppen")
        if isinstance(process_groups, list):
            fallgruppen.extend([item for item in process_groups if isinstance(item, dict)])
    return fallgruppen


def _parse_process_steps(payload: str) -> list[dict]:
    cleaned = _clean_llm_payload(payload)
    data = None
    try:
        data = json.loads(cleaned)
    except Exception:
        data = _extract_last_json(cleaned)
    if not isinstance(data, dict):
        return []

    fallgruppen = _extract_fallgruppen(data)
    parsed: list[dict] = []
    for fallgruppe in fallgruppen:
        fallgruppen_id = str(
            fallgruppe.get("fallgruppen_id")
            or fallgruppe.get("fallgruppe_id")
            or fallgruppe.get("case_group_id")
            or ""
        ).strip()
        if not fallgruppen_id:
            continue
        try:
            case_group_id = int(fallgruppen_id)
        except ValueError:
            continue
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
            if not step and not description:
                continue
            steps.append(
                {
                    "taetigkeit": step,
                    "beschreibung": description,
                }
            )
        if steps:
            parsed.append(
                {
                    "case_group_id": case_group_id,
                    "taetigkeiten": steps,
                }
            )
    return parsed


def _build_case_groups_payload(
    processes: list[dict],
    case_groups: list[dict],
) -> list[dict]:
    groups_by_process: dict[int, list[dict]] = {}
    for group in case_groups:
        process_id = int(group["process_id"])
        groups_by_process.setdefault(process_id, []).append(
            {
                "fallgruppen_id": group["case_group_id"],
                "fallgruppe_bezeichnung": group["case_group"],
                "fallgruppe_beschreibung": group["description"],
            }
        )

    payload = []
    for process in processes:
        process_id = int(process["process_id"])
        payload.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "fallgruppen": groups_by_process.get(process_id, []),
            }
        )
    return payload


def _add_step_tiles(
    session_id: int,
    parsed: list[dict],
    case_group_lookup: dict[int, dict],
) -> list[dict]:
    tiles = db.fetch_tiles()
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
            step_id = db.insert_process_step(
                session_id=session_id,
                case_group_id=case_group_id,
                step=title,
                description=description,
                previous_id=prev_step_id,
                execution_per_case=None,
            )
            if prev_step_id is not None:
                db.update_process_step_next(prev_step_id, step_id)
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
                    "process_id": case_group_lookup[case_group_id]["process_id"],
                },
                column=case_group_tile.column + 1 + idx,
                row=case_group_tile.row,
                deletable=True,
                link_from_tile=link_from,
            )
            db.upsert_tile(tile)
            created.append(
                {
                    "step_id": step_id,
                    "case_group_id": case_group_id,
                    "taetigkeit": title,
                    "beschreibung": description,
                }
            )
            prev_step_id = step_id
    return created


@router.post("/analyze")
async def analyze_process_steps(
    payload: ProcessStepAnalysisRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    model = payload.model or settings.default_model
    session_id, _created = db.upsert_session(payload.app_session_id, model)
    existing = db.list_process_steps_for_session(session_id)
    if existing:
        return {"steps": existing, "status": "existing"}

    case_groups = db.list_case_groups_for_session(session_id)
    if not case_groups:
        raise HTTPException(status_code=400, detail="No case groups for session")

    processes = db.list_processes_for_session(session_id)
    payload_groups = _build_case_groups_payload(processes, case_groups)

    prompt = render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        case_groups_json=json.dumps(payload_groups, ensure_ascii=False),
    )
    response_text = await query_llm(
        prompt,
        api_keys=api_keys,
        model=model,
        provider=payload.provider,
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.PROCESS_STEP_ANALYSIS,
        model=model,
        answer_text=response_text,
        metadata={"provider": payload.provider},
    )
    parsed = _parse_process_steps(response_text)
    if not parsed:
        raise HTTPException(status_code=422, detail="No process steps parsed")

    case_group_lookup = {row["case_group_id"]: row for row in case_groups}
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

    created = _add_step_tiles(session_id, parsed, case_group_lookup)
    return {"steps": created}
