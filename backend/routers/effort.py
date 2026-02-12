from __future__ import annotations

import asyncio
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


router = APIRouter(prefix="/effort", tags=["effort"])

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_FENCE_RE = re.compile(r"```(?:think|thinking)[\\s\\S]*?```", re.IGNORECASE)


class EffortCalculationRequest(BaseModel):
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


def _parse_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace("\u00a0", "").replace(" ", "")
        cleaned = cleaned.replace(",", ".")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if cleaned.count(".") > 1:
            parts = cleaned.split(".")
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_cases_payload(payload: str) -> list[dict]:
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
        if not isinstance(fallgruppe, dict):
            continue
        raw_id = str(
            fallgruppe.get("fallgruppen_id")
            or fallgruppe.get("fallgruppe_id")
            or fallgruppe.get("case_group_id")
            or ""
        ).strip()
        if not raw_id:
            continue
        try:
            case_group_id = int(raw_id)
        except ValueError:
            continue
        addressees = _parse_number(fallgruppe.get("anzahl_betroffene"))
        annual_frequency = _parse_number(fallgruppe.get("haeufigkeit_pro_jahr"))
        if addressees is None and annual_frequency is None:
            continue
        parsed.append(
            {
                "case_group_id": case_group_id,
                "addressees": addressees,
                "annual_frequency": annual_frequency,
            }
        )
    return parsed


def _parse_effort_payload(payload: str) -> list[dict]:
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
        if not isinstance(fallgruppe, dict):
            continue
        taetigkeiten = fallgruppe.get("taetigkeiten") or fallgruppe.get("tätigkeiten")
        if not isinstance(taetigkeiten, list):
            continue
        for entry in taetigkeiten:
            if not isinstance(entry, dict):
                continue
            raw_id = str(
                entry.get("taetigkeiten_id")
                or entry.get("tätigkeiten_id")
                or entry.get("taetigkeit_id")
                or entry.get("step_id")
                or ""
            ).strip()
            if not raw_id:
                continue
            try:
                step_id = int(raw_id)
            except ValueError:
                continue
            hourly_rates = {}
            time_required = {}
            for key in ["a", "b", "c", "d", "e"]:
                hourly_rates[key] = _parse_number(
                    entry.get(f"stundenlohn_satz_{key}")
                    or entry.get(f"stundenlohn_satz_{key.upper()}")
                    or entry.get(f"studenlohn_satz_{key}")
                    or entry.get(f"studenlohn_satz_{key.upper()}")
                    or entry.get(f"lohnsatz_{key}")
                    or entry.get(f"lohnsatz_{key.upper()}")
                )
                time_required[key] = _parse_number(
                    entry.get(f"zeitaufwand_in_min_{key}")
                    or entry.get(f"zeitaufwand_in_min_{key.upper()}")
                    or entry.get(f"zeitaufwand_{key}")
                    or entry.get(f"zeitaufwand_{key.upper()}")
                )
            expenses = _parse_number(entry.get("sachaufwand"))
            raw_execution = entry.get("execution_per_case")
            if raw_execution is None:
                raw_execution = entry.get("ausfuehrung_pro_einzelfall")
            if isinstance(raw_execution, bool):
                execution_per_case = raw_execution
            elif isinstance(raw_execution, (int, float)):
                execution_per_case = bool(raw_execution)
            elif isinstance(raw_execution, str):
                normalized = raw_execution.strip().lower()
                if normalized in {"1", "true", "ja", "yes", "y"}:
                    execution_per_case = True
                elif normalized in {"0", "false", "nein", "no", "n"}:
                    execution_per_case = False
                else:
                    execution_per_case = None
            else:
                execution_per_case = None
            if (
                all(value is None for value in hourly_rates.values())
                and all(value is None for value in time_required.values())
                and expenses is None
            ):
                continue
            parsed.append(
                {
                    "step_id": step_id,
                    "hourly_rates": hourly_rates,
                    "time_required": time_required,
                    "expenses": expenses,
                    "execution_per_case": execution_per_case,
                }
            )
    return parsed


def _order_steps(steps: list[dict]) -> list[dict]:
    step_map = {int(step["step_id"]): step for step in steps}
    steps_by_prev: dict[int | None, list[int]] = {}
    for step_id, step in step_map.items():
        steps_by_prev.setdefault(step.get("previous_id"), []).append(step_id)
    ordered: list[int] = []
    start_ids = steps_by_prev.get(None, [])
    if start_ids:
        current_id = start_ids[0]
        seen = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            ordered.append(current_id)
            next_id = step_map[current_id].get("next_id")
            current_id = int(next_id) if next_id is not None else None
    if not ordered:
        ordered = sorted(step_map.keys())
    return [step_map[step_id] for step_id in ordered]


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


def _build_step_analysis_payload(
    processes: list[dict],
    case_groups: list[dict],
    steps: list[dict],
) -> list[dict]:
    groups_by_process: dict[int, list[dict]] = {}
    for group in case_groups:
        process_id = int(group["process_id"])
        groups_by_process.setdefault(process_id, []).append(group)

    steps_by_group: dict[int, list[dict]] = {}
    for step in steps:
        steps_by_group.setdefault(int(step["case_group_id"]), []).append(step)

    payload = []
    for process in processes:
        process_id = int(process["process_id"])
        fallgruppen_payload = []
        for group in groups_by_process.get(process_id, []):
            case_group_id = int(group["case_group_id"])
            ordered_steps = _order_steps(steps_by_group.get(case_group_id, []))
            taetigkeiten = [
                {
                    "taetigkeiten_id": step["step_id"],
                    "taetigkeit": step["step"],
                    "beschreibung": step["description"],
                }
                for step in ordered_steps
            ]
            fallgruppen_payload.append(
                {
                    "fallgruppen_id": case_group_id,
                    "fallgruppe_bezeichnung": group["case_group"],
                    "fallgruppe_beschreibung": group["description"],
                    "taetigkeiten": taetigkeiten,
                }
            )
        payload.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "fallgruppen": fallgruppen_payload,
            }
        )
    return payload


def _refresh_case_group_tiles(case_groups: list[dict]) -> None:
    tiles = {tile.id: tile for tile in db.fetch_tiles()}
    for group in case_groups:
        tile_id = f"case_group_{group['case_group_id']}"
        tile = tiles.get(tile_id)
        if not tile:
            continue
        new_text = db.build_case_group_tile_text(
            description=group["description"],
            addressees=group.get("addressees"),
            annual_frequency=group.get("annual_frequency"),
        )
        updated = Tile(
            id=tile.id,
            title=tile.title,
            text=new_text,
            meta_information=tile.meta_information,
            column=tile.column,
            row=tile.row,
            deletable=tile.deletable,
            link_from_tile=tile.link_from_tile,
        )
        db.upsert_tile(updated)


def _refresh_step_tiles(steps: list[dict]) -> None:
    tiles = {tile.id: tile for tile in db.fetch_tiles()}
    for step in steps:
        tile_id = f"step_{step['step_id']}"
        tile = tiles.get(tile_id)
        if not tile:
            continue
        hourly_rates = {
            "a": step.get("hourly_rate_a"),
            "b": step.get("hourly_rate_b"),
            "c": step.get("hourly_rate_c"),
            "d": step.get("hourly_rate_d"),
            "e": step.get("hourly_rate_e"),
        }
        time_required = {
            "a": step.get("time_required_in_min_a"),
            "b": step.get("time_required_in_min_b"),
            "c": step.get("time_required_in_min_c"),
            "d": step.get("time_required_in_min_d"),
            "e": step.get("time_required_in_min_e"),
        }
        new_text = db.build_process_step_tile_text(
            description=step["description"],
            hourly_rates=hourly_rates,
            time_required=time_required,
            expenses=step.get("expenses"),
            cost=step.get("cost"),
            execution_per_case=step.get("execution_per_case"),
        )
        updated = Tile(
            id=tile.id,
            title=tile.title,
            text=new_text,
            meta_information=tile.meta_information,
            column=tile.column,
            row=tile.row,
            deletable=tile.deletable,
            link_from_tile=tile.link_from_tile,
        )
        db.upsert_tile(updated)


@router.post("/calculate")
async def calculate_effort(
    payload: EffortCalculationRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    model = payload.model or settings.default_model
    session_id, _created = db.upsert_session(payload.app_session_id, model)

    processes = db.list_processes_for_session(session_id)
    case_groups = db.list_case_groups_for_session(session_id)
    steps = db.list_process_steps_for_session(session_id)
    if not case_groups:
        raise HTTPException(status_code=400, detail="No case groups for session")
    if not steps:
        raise HTTPException(status_code=400, detail="No process steps for session")
    if db.has_effort_metrics(session_id):
        return {
            "status": "existing",
            "case_groups_updated": 0,
            "steps_updated": 0,
        }

    case_groups_payload = _build_case_groups_payload(processes, case_groups)
    steps_payload = _build_step_analysis_payload(processes, case_groups, steps)

    cases_prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        case_groups_json=json.dumps(case_groups_payload, ensure_ascii=False),
    )
    effort_prompt = render_prompt(
        PromptId.EFFORT_CALCULATION,
        step_analysis_json=json.dumps(steps_payload, ensure_ascii=False),
    )

    cases_response, effort_response = await asyncio.gather(
        query_llm(
            cases_prompt,
            api_keys=api_keys,
            model=model,
            provider=payload.provider,
        ),
        query_llm(
            effort_prompt,
            api_keys=api_keys,
            model=model,
            provider=payload.provider,
        ),
    )

    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.CASES_CALCULATION,
        model=model,
        answer_text=cases_response,
        metadata={"provider": payload.provider},
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.EFFORT_CALCULATION,
        model=model,
        answer_text=effort_response,
        metadata={"provider": payload.provider},
    )

    parsed_cases = _parse_cases_payload(cases_response)
    if not parsed_cases:
        raise HTTPException(status_code=422, detail="No case group metrics parsed")
    parsed_effort = _parse_effort_payload(effort_response)
    if not parsed_effort:
        raise HTTPException(status_code=422, detail="No effort metrics parsed")

    case_group_ids = {int(group["case_group_id"]) for group in case_groups}
    step_ids = {int(step["step_id"]) for step in steps}

    missing_case_groups = [
        str(entry["case_group_id"])
        for entry in parsed_cases
        if entry["case_group_id"] not in case_group_ids
    ]
    if missing_case_groups:
        raise HTTPException(
            status_code=422,
            detail="Unknown fallgruppen_id values: " + ", ".join(missing_case_groups),
        )

    missing_steps = [
        str(entry["step_id"])
        for entry in parsed_effort
        if entry["step_id"] not in step_ids
    ]
    if missing_steps:
        raise HTTPException(
            status_code=422,
            detail="Unknown taetigkeiten_id values: " + ", ".join(missing_steps),
        )

    for entry in parsed_cases:
        db.update_case_group_metrics(
            session_id=session_id,
            case_group_id=entry["case_group_id"],
            addressees=entry.get("addressees"),
            annual_frequency=entry.get("annual_frequency"),
        )

    for entry in parsed_effort:
        db.update_process_step_effort(
            session_id=session_id,
            step_id=entry["step_id"],
            hourly_rates=entry["hourly_rates"],
            time_required=entry["time_required"],
            expenses=entry.get("expenses"),
        )
        execution_per_case = entry.get("execution_per_case")
        if execution_per_case is not None:
            db.update_process_step_execution(
                session_id=session_id,
                step_id=entry["step_id"],
                execution_per_case=execution_per_case,
            )

    refreshed_case_groups = db.list_case_groups_for_session(session_id)
    refreshed_steps = db.list_process_steps_for_session(session_id)
    _refresh_case_group_tiles(refreshed_case_groups)
    _refresh_step_tiles(refreshed_steps)

    return {
        "case_groups_updated": len(parsed_cases),
        "steps_updated": len(parsed_effort),
    }
