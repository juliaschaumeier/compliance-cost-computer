from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.auth import ApiKeys, get_api_keys
from backend.core.change_status import extract_change_status
from backend.core.llm_attempts import (
    LlmPromptSpec,
    mark_llm_answer_applied,
    mark_llm_answers_apply_failed,
    mark_llm_parse_fallback,
    prompt_sha256,
    query_and_stage_llm_answers_parallel,
)
from backend.core.llm_json import extract_fallgruppen, parse_json_object_with_mode
from backend.core.llm_service import LlmResult, query_llm
from backend.core.parsing import parse_first_int, parse_optional_number
from backend.core.payload_builders import (
    build_case_groups_payload,
    build_step_analysis_payload,
    dump_prompt_json,
)
from backend.core.prompts import PromptId, render_prompt
from backend.core.tile_refresh import refresh_case_group_tiles, refresh_step_tiles
from backend.routers._llm_router_utils import ensure_session_or_400


router = APIRouter(prefix="/effort", tags=["effort"])


class EffortCalculationRequest(BaseModel):
    app_session_id: str
    model: str | None = None
    provider: str | None = None


def _has_meaningful_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _value_from_keys(
    payload: dict[str, object],
    primary_key: str,
    fallback_keys: tuple[str, ...],
) -> tuple[object | None, str | None]:
    primary = payload.get(primary_key)
    if _has_meaningful_value(primary):
        return primary, None
    for key in fallback_keys:
        candidate = payload.get(key)
        if _has_meaningful_value(candidate):
            return candidate, key
    return None, None


def _parse_cases_payload(payload: str) -> tuple[list[dict], set[str]]:
    data, parse_mode = parse_json_object_with_mode(payload)
    fallback_kinds: set[str] = set()
    if parse_mode == "extract_last_json_object":
        fallback_kinds.add("json_extract_last_object")
    if not isinstance(data, dict):
        return [], fallback_kinds
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
        addressees_current_raw, current_alias = _value_from_keys(
            fallgruppe,
            "anzahl_betroffene_current",
            ("anzahl_betroffene_gueltig",),
        )
        annual_frequency_current_raw, frequency_current_alias = _value_from_keys(
            fallgruppe,
            "haeufigkeit_pro_jahr_current",
            ("haeufigkeit_pro_jahr_gueltig",),
        )
        addressees_proposed_raw, proposed_alias = _value_from_keys(
            fallgruppe,
            "anzahl_betroffene_proposed",
            ("anzahl_betroffene_vorschlag",),
        )
        annual_frequency_proposed_raw, frequency_proposed_alias = _value_from_keys(
            fallgruppe,
            "haeufigkeit_pro_jahr_proposed",
            ("haeufigkeit_pro_jahr_vorschlag",),
        )
        if any(
            alias is not None
            for alias in (
                current_alias,
                frequency_current_alias,
                proposed_alias,
                frequency_proposed_alias,
            )
        ):
            fallback_kinds.add("cases_legacy_key_alias")
        addressees_current = parse_optional_number(
            addressees_current_raw
        )
        annual_frequency_current = parse_optional_number(
            annual_frequency_current_raw
        )
        addressees_proposed = parse_optional_number(
            addressees_proposed_raw
        )
        annual_frequency_proposed = parse_optional_number(
            annual_frequency_proposed_raw
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
    return parsed, fallback_kinds


def _parse_effort_payload(payload: str) -> tuple[list[dict], set[str]]:
    data, parse_mode = parse_json_object_with_mode(payload)
    fallback_kinds: set[str] = set()
    if parse_mode == "extract_last_json_object":
        fallback_kinds.add("json_extract_last_object")
    if not isinstance(data, dict):
        return [], fallback_kinds
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
                hourly_rates_current_raw, current_rate_alias = _value_from_keys(
                    entry,
                    f"stundenlohn_satz_{key}_current",
                    (
                        f"stundenlohn_satz_{key}_gueltig",
                        f"stundenlohn_satz_{key.upper()}_current",
                        f"stundenlohn_satz_{key.upper()}_gueltig",
                    ),
                )
                hourly_rates_proposed_raw, proposed_rate_alias = _value_from_keys(
                    entry,
                    f"stundenlohn_satz_{key}_proposed",
                    (
                        f"stundenlohn_satz_{key}_vorschlag",
                        f"stundenlohn_satz_{key.upper()}_proposed",
                        f"stundenlohn_satz_{key.upper()}_vorschlag",
                    ),
                )
                time_required_current_raw, current_time_alias = _value_from_keys(
                    entry,
                    f"zeitaufwand_in_min_{key}_current",
                    (
                        f"zeitaufwand_in_min_{key}_gueltig",
                        f"zeitaufwand_in_min_{key.upper()}_current",
                        f"zeitaufwand_in_min_{key.upper()}_gueltig",
                    ),
                )
                time_required_proposed_raw, proposed_time_alias = _value_from_keys(
                    entry,
                    f"zeitaufwand_in_min_{key}_proposed",
                    (
                        f"zeitaufwand_in_min_{key}_vorschlag",
                        f"zeitaufwand_in_min_{key.upper()}_proposed",
                        f"zeitaufwand_in_min_{key.upper()}_vorschlag",
                    ),
                )
                if any(
                    alias is not None
                    for alias in (
                        current_rate_alias,
                        proposed_rate_alias,
                        current_time_alias,
                        proposed_time_alias,
                    )
                ):
                    fallback_kinds.add("effort_legacy_key_alias")
                hourly_rates_current[key] = parse_optional_number(
                    hourly_rates_current_raw
                )
                hourly_rates_proposed[key] = parse_optional_number(
                    hourly_rates_proposed_raw
                )
                time_required_current[key] = parse_optional_number(
                    time_required_current_raw
                )
                time_required_proposed[key] = parse_optional_number(
                    time_required_proposed_raw
                )
            expenses_current_raw, expenses_current_alias = _value_from_keys(
                entry,
                "sachaufwand_current",
                ("sachaufwand_gueltig",),
            )
            expenses_proposed_raw, expenses_proposed_alias = _value_from_keys(
                entry,
                "sachaufwand_proposed",
                ("sachaufwand_vorschlag",),
            )
            if expenses_current_alias is not None or expenses_proposed_alias is not None:
                fallback_kinds.add("effort_legacy_key_alias")
            expenses_current = parse_optional_number(
                expenses_current_raw
            )
            expenses_proposed = parse_optional_number(
                expenses_proposed_raw
            )
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
                    "aenderungsstatus": extract_change_status(entry),
                }
            )
    return parsed, fallback_kinds


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
    regulations = db.list_regulations_for_session(session_id)
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
        regulations=regulations,
    )
    steps_payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=regulations,
    )

    cases_prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        session_id=session_id,
        case_groups_json=dump_prompt_json(case_groups_payload),
    )
    effort_prompt = render_prompt(
        PromptId.EFFORT_CALCULATION,
        session_id=session_id,
        step_analysis_json=dump_prompt_json(steps_payload),
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
        parsed_cases, cases_fallback_kinds = _parse_cases_payload(cases_result.text)
        for fallback_kind in sorted(cases_fallback_kinds):
            mark_llm_parse_fallback(
                answer_id=pending_answer_ids[PromptId.CASES_CALCULATION],
                session_id=session_id,
                prompt_id=PromptId.CASES_CALCULATION,
                fallback_kind=fallback_kind,
            )
        if not parsed_cases:
            raise HTTPException(status_code=422, detail="No case group metrics parsed")
        parsed_effort, effort_fallback_kinds = _parse_effort_payload(effort_result.text)
        for fallback_kind in sorted(effort_fallback_kinds):
            mark_llm_parse_fallback(
                answer_id=pending_answer_ids[PromptId.EFFORT_CALCULATION],
                session_id=session_id,
                prompt_id=PromptId.EFFORT_CALCULATION,
                fallback_kind=fallback_kind,
            )
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
            case_groups_by_id = {
                int(group["case_group_id"]): group for group in case_groups
            }
            for entry in parsed_cases:
                existing_group = case_groups_by_id[int(entry["case_group_id"])]
                addressees_current = (
                    existing_group.get("addressees_current")
                    if existing_group.get("addressees_current") is not None
                    else entry.get("addressees_current")
                )
                annual_frequency_current = (
                    existing_group.get("annual_frequency_current")
                    if existing_group.get("annual_frequency_current") is not None
                    else entry.get("annual_frequency_current")
                )
                addressees_proposed = (
                    existing_group.get("addressees_proposed")
                    if existing_group.get("addressees_proposed") is not None
                    else entry.get("addressees_proposed")
                )
                annual_frequency_proposed = (
                    existing_group.get("annual_frequency_proposed")
                    if existing_group.get("annual_frequency_proposed") is not None
                    else entry.get("annual_frequency_proposed")
                )
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

            steps_by_id = {int(step["step_id"]): step for step in steps}
            for entry in parsed_effort:
                existing_step = steps_by_id[int(entry["step_id"])]
                hourly_rates_current = {
                    key: (
                        existing_step.get(f"hourly_rate_{key}_current")
                        if existing_step.get(f"hourly_rate_{key}_current") is not None
                        else entry["hourly_rates_current"].get(key)
                    )
                    for key in ["a", "b", "c", "d"]
                }
                hourly_rates_proposed = {
                    key: (
                        existing_step.get(f"hourly_rate_{key}_proposed")
                        if existing_step.get(f"hourly_rate_{key}_proposed") is not None
                        else entry["hourly_rates_proposed"].get(key)
                    )
                    for key in ["a", "b", "c", "d"]
                }
                time_required_current = {
                    key: (
                        existing_step.get(f"time_required_in_min_{key}_current")
                        if existing_step.get(f"time_required_in_min_{key}_current") is not None
                        else entry["time_required_current"].get(key)
                    )
                    for key in ["a", "b", "c", "d"]
                }
                time_required_proposed = {
                    key: (
                        existing_step.get(f"time_required_in_min_{key}_proposed")
                        if existing_step.get(f"time_required_in_min_{key}_proposed") is not None
                        else entry["time_required_proposed"].get(key)
                    )
                    for key in ["a", "b", "c", "d"]
                }
                expenses_current = (
                    existing_step.get("expenses_current")
                    if existing_step.get("expenses_current") is not None
                    else entry.get("expenses_current")
                )
                expenses_proposed = (
                    existing_step.get("expenses_proposed")
                    if existing_step.get("expenses_proposed") is not None
                    else entry.get("expenses_proposed")
                )
                db.update_process_step_effort_split(
                    session_id=session_id,
                    step_id=entry["step_id"],
                    hourly_rates_current=hourly_rates_current,
                    time_required_current=time_required_current,
                    expenses_current=expenses_current,
                    hourly_rates_proposed=hourly_rates_proposed,
                    time_required_proposed=time_required_proposed,
                    expenses_proposed=expenses_proposed,
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
