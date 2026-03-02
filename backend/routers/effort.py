from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.auth import ApiKeys, get_api_keys
from backend.core.change_status import extract_change_status
from backend.core.llm_attempts import (
    LlmPromptSpec,
    mark_llm_answer_applied,
    mark_llm_answers_apply_failed,
    prompt_sha256,
    query_and_stage_llm_answers_parallel,
)
from backend.core.llm_json import extract_fallgruppen, parse_json_object
from backend.core.llm_service import LlmResult, query_llm
from backend.core.parsing import parse_first_int, parse_optional_number
from backend.core.payload_builders import (
    build_case_groups_payload,
    build_step_analysis_payload,
)
from backend.core.prompts import PromptId, render_prompt
from backend.core.tile_refresh import refresh_case_group_tiles, refresh_step_tiles
from backend.routers._llm_router_utils import ensure_session_or_400


router = APIRouter(prefix="/effort", tags=["effort"])


class EffortCalculationRequest(BaseModel):
    app_session_id: str
    model: str | None = None
    provider: str | None = None


def _parse_cases_payload(payload: str) -> list[dict]:
    data = parse_json_object(payload)
    if not isinstance(data, dict):
        return []
    fallgruppen = extract_fallgruppen(data)
    parsed: list[dict] = []
    for fallgruppe in fallgruppen:
        if not isinstance(fallgruppe, dict):
            continue
        case_group_id = parse_first_int(
            fallgruppe,
            "fallgruppen_id",
            "fallgruppe_id",
            "case_group_id",
        )
        if case_group_id is None:
            continue
        addressees_current = parse_optional_number(
            fallgruppe.get("anzahl_betroffene_current")
            or fallgruppe.get("anzahl_betroffene_gueltig")
        )
        annual_frequency_current = parse_optional_number(
            fallgruppe.get("haeufigkeit_pro_jahr_current")
            or fallgruppe.get("haeufigkeit_pro_jahr_gueltig")
        )
        addressees_proposed = parse_optional_number(
            fallgruppe.get("anzahl_betroffene_proposed")
            or fallgruppe.get("anzahl_betroffene_vorschlag")
        )
        annual_frequency_proposed = parse_optional_number(
            fallgruppe.get("haeufigkeit_pro_jahr_proposed")
            or fallgruppe.get("haeufigkeit_pro_jahr_vorschlag")
        )
        if (
            addressees_current is None
            and annual_frequency_current is None
            and addressees_proposed is None
            and annual_frequency_proposed is None
        ):
            continue
        parsed.append(
            {
                "case_group_id": case_group_id,
                "addressees_current": addressees_current,
                "annual_frequency_current": annual_frequency_current,
                "addressees_proposed": addressees_proposed,
                "annual_frequency_proposed": annual_frequency_proposed,
                "aenderungsstatus": extract_change_status(fallgruppe),
            }
        )
    return parsed


def _parse_effort_payload(payload: str) -> list[dict]:
    data = parse_json_object(payload)
    if not isinstance(data, dict):
        return []
    fallgruppen = extract_fallgruppen(data)
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
            step_id = parse_first_int(
                entry,
                "taetigkeiten_id",
                "tätigkeiten_id",
                "taetigkeit_id",
                "step_id",
            )
            if step_id is None:
                continue
            hourly_rates_current = {}
            hourly_rates_proposed = {}
            time_required_current = {}
            time_required_proposed = {}
            for key in ["a", "b", "c", "d"]:
                hourly_rates_current[key] = parse_optional_number(
                    entry.get(f"stundenlohn_satz_{key}_current")
                    or entry.get(f"stundenlohn_satz_{key}_gueltig")
                    or entry.get(f"stundenlohn_satz_{key.upper()}_current")
                    or entry.get(f"stundenlohn_satz_{key.upper()}_gueltig")
                )
                hourly_rates_proposed[key] = parse_optional_number(
                    entry.get(f"stundenlohn_satz_{key}_proposed")
                    or entry.get(f"stundenlohn_satz_{key}_vorschlag")
                    or entry.get(f"stundenlohn_satz_{key.upper()}_proposed")
                    or entry.get(f"stundenlohn_satz_{key.upper()}_vorschlag")
                )
                time_required_current[key] = parse_optional_number(
                    entry.get(f"zeitaufwand_in_min_{key}_current")
                    or entry.get(f"zeitaufwand_in_min_{key}_gueltig")
                    or entry.get(f"zeitaufwand_in_min_{key.upper()}_current")
                    or entry.get(f"zeitaufwand_in_min_{key.upper()}_gueltig")
                )
                time_required_proposed[key] = parse_optional_number(
                    entry.get(f"zeitaufwand_in_min_{key}_proposed")
                    or entry.get(f"zeitaufwand_in_min_{key}_vorschlag")
                    or entry.get(f"zeitaufwand_in_min_{key.upper()}_proposed")
                    or entry.get(f"zeitaufwand_in_min_{key.upper()}_vorschlag")
                )
            expenses_current = parse_optional_number(
                entry.get("sachaufwand_current")
                or entry.get("sachaufwand_gueltig")
            )
            expenses_proposed = parse_optional_number(
                entry.get("sachaufwand_proposed")
                or entry.get("sachaufwand_vorschlag")
            )
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
                all(value is None for value in hourly_rates_current.values())
                and all(value is None for value in hourly_rates_proposed.values())
                and all(value is None for value in time_required_current.values())
                and all(value is None for value in time_required_proposed.values())
                and expenses_current is None
                and expenses_proposed is None
            ):
                continue
            parsed.append(
                {
                    "step_id": step_id,
                    "hourly_rates_current": hourly_rates_current,
                    "hourly_rates_proposed": hourly_rates_proposed,
                    "time_required_current": time_required_current,
                    "time_required_proposed": time_required_proposed,
                    "expenses_current": expenses_current,
                    "expenses_proposed": expenses_proposed,
                    "execution_per_case": execution_per_case,
                    "aenderungsstatus": extract_change_status(entry),
                }
            )
    return parsed


@router.post("/calculate")
async def calculate_effort(
    payload: EffortCalculationRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )

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

    case_groups_payload = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        include_metrics=True,
    )
    steps_payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
    )
    current_law_text, proposed_law_text = db.get_session_law_texts(session_id)

    cases_prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        gesetz_gueltig=current_law_text,
        gesetz_vorschlag=proposed_law_text,
        case_groups_json=json.dumps(case_groups_payload, ensure_ascii=False),
    )
    effort_prompt = render_prompt(
        PromptId.EFFORT_CALCULATION,
        gesetz_gueltig=current_law_text,
        gesetz_vorschlag=proposed_law_text,
        step_analysis_json=json.dumps(steps_payload, ensure_ascii=False),
    )

    all_specs = [
        LlmPromptSpec(
            prompt_id=PromptId.CASES_CALCULATION,
            query_label="CASES_CALCULATION",
            prompt=cases_prompt,
        ),
        LlmPromptSpec(
            prompt_id=PromptId.EFFORT_CALCULATION,
            query_label="EFFORT_CALCULATION",
            prompt=effort_prompt,
        ),
    ]
    pending_answer_ids = {}
    query_results = {}
    query_errors: list[str] = []

    missing_specs: list[LlmPromptSpec] = []
    for spec in all_specs:
        reusable = db.get_reusable_pending_llm_answer(
            session_id=session_id,
            prompt_id=spec.prompt_id,
            model=model,
            provider=payload.provider,
            prompt_sha256=prompt_sha256(spec.prompt),
        )
        if reusable:
            pending_answer_ids[spec.prompt_id] = int(reusable["answer_id"])
            query_results[spec.prompt_id] = LlmResult(text=str(reusable["answer_text"]))
            continue
        missing_specs.append(spec)

    if missing_specs:
        staged_ids, staged_results, query_errors = await query_and_stage_llm_answers_parallel(
            session_id=session_id,
            specs=missing_specs,
            api_keys=api_keys,
            model=model,
            provider=payload.provider,
            query_fn=query_llm,
        )
        pending_answer_ids.update(staged_ids)
        query_results.update(staged_results)

    if query_errors:
        for answer_id in pending_answer_ids.values():
            db.update_llm_answer_state_reason(
                answer_id,
                "waiting_for_paired_retry",
                state=db.LLM_ANSWER_STATE_PENDING,
            )
        raise HTTPException(status_code=502, detail="; ".join(query_errors))

    cases_result = query_results[PromptId.CASES_CALCULATION]
    effort_result = query_results[PromptId.EFFORT_CALCULATION]

    try:
        parsed_cases = _parse_cases_payload(cases_result.text)
        if not parsed_cases:
            raise HTTPException(status_code=422, detail="No case group metrics parsed")
        parsed_effort = _parse_effort_payload(effort_result.text)
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

        with db.transaction():
            for entry in parsed_cases:
                addressees_current = entry.get("addressees_current")
                annual_frequency_current = entry.get("annual_frequency_current")
                addressees_proposed = entry.get("addressees_proposed")
                annual_frequency_proposed = entry.get("annual_frequency_proposed")
                cases_current = (
                    addressees_current * annual_frequency_current
                    if addressees_current is not None
                    and annual_frequency_current is not None
                    else None
                )
                cases_proposed = (
                    addressees_proposed * annual_frequency_proposed
                    if addressees_proposed is not None
                    and annual_frequency_proposed is not None
                    else None
                )
                db.update_case_group_metrics(
                    session_id=session_id,
                    case_group_id=entry["case_group_id"],
                    addressees_current=addressees_current,
                    annual_frequency_current=annual_frequency_current,
                    addressees_proposed=addressees_proposed,
                    annual_frequency_proposed=annual_frequency_proposed,
                    cases_current=cases_current,
                    cases_proposed=cases_proposed,
                )

            for entry in parsed_effort:
                db.update_process_step_effort_split(
                    session_id=session_id,
                    step_id=entry["step_id"],
                    hourly_rates_current=entry["hourly_rates_current"],
                    time_required_current=entry["time_required_current"],
                    expenses_current=entry.get("expenses_current"),
                    hourly_rates_proposed=entry["hourly_rates_proposed"],
                    time_required_proposed=entry["time_required_proposed"],
                    expenses_proposed=entry.get("expenses_proposed"),
                    execution_per_case=entry.get("execution_per_case"),
                )

            mark_llm_answer_applied(
                answer_id=pending_answer_ids[PromptId.CASES_CALCULATION],
                session_id=session_id,
                prompt_id=PromptId.CASES_CALCULATION,
            )
            mark_llm_answer_applied(
                answer_id=pending_answer_ids[PromptId.EFFORT_CALCULATION],
                session_id=session_id,
                prompt_id=PromptId.EFFORT_CALCULATION,
            )
    except Exception as exc:
        mark_llm_answers_apply_failed(answer_ids=pending_answer_ids.values(), exc=exc)
        raise

    refreshed_case_groups = db.list_case_groups_for_session(session_id)
    refreshed_steps = db.list_process_steps_for_session(session_id)
    refresh_case_group_tiles(session_id, refreshed_case_groups)
    refresh_step_tiles(session_id, refreshed_steps)

    return {
        "case_groups_updated": len(parsed_cases),
        "steps_updated": len(parsed_effort),
    }
