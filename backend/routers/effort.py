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
from backend.core.llm_json import extract_fallgruppen, require_json_object
from backend.core.llm_service import LlmResult, query_llm
from backend.core.mirror_context import apply_deterministic_mirror_case_group_sync
from backend.core.mirror_context import ensure_mirror_matching
from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
)
from backend.core.parsing import parse_first_int, parse_optional_number
from backend.core.payload_builders import (
    build_case_groups_payload,
    build_step_analysis_payload,
    dump_prompt_json,
)
from backend.core.prompts import PromptId, render_prompt
from backend.core.tile_refresh import refresh_case_group_tiles, refresh_step_tiles
from backend.routers._llm_router_utils import ensure_session_or_400
from backend.routers._norm_addressee import normalize_norm_addressee_or_422


router = APIRouter(prefix="/effort", tags=["effort"])


class EffortCalculationRequest(BaseModel):
    app_session_id: str
    model: str | None = None
    provider: str | None = None
    norm_addressee: str | None = None

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
    data, parse_mode = require_json_object(
        payload,
        error_context="Invalid cases_calculation payload",
    )
    fallback_kinds: set[str] = set()
    if parse_mode == "extract_last_json_object":
        fallback_kinds.add("json_extract_last_object")
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


def _empty_role_values() -> dict[str, None]:
    return {"a": None, "b": None, "c": None, "d": None}


def _parse_execution_per_case(entry: dict) -> bool | None:
    raw_execution = entry.get("execution_per_case")
    if raw_execution is None:
        raw_execution = entry.get("ausfuehrung_pro_einzelfall")
    if isinstance(raw_execution, bool):
        return raw_execution
    if isinstance(raw_execution, (int, float)):
        return bool(raw_execution)
    if isinstance(raw_execution, str):
        normalized = raw_execution.strip().lower()
        if normalized in {"1", "true", "ja", "yes", "y"}:
            return True
        if normalized in {"0", "false", "nein", "no", "n"}:
            return False
    return None


def _resolve_effort_group(
    raw_role: dict,
    norm_addressee: str,
) -> str | None:
    raw_group = str(
        raw_role.get("lohngruppe")
        or raw_role.get("gruppe")
        or raw_role.get("group")
        or ""
    ).strip().lower()
    if raw_group in {"a", "b", "c", "d"}:
        return raw_group

    raw_level = str(
        raw_role.get("schwierigkeitsgrad")
        or raw_role.get("niveau")
        or raw_role.get("level")
        or raw_role.get("rolle")
        or ""
    ).strip().lower()
    if norm_addressee == ADMINISTRATION:
        if raw_level in {"einfach", "mittlerer dienst", "einfacher und mittlerer dienst", "mittel"}:
            return "a"
        if raw_level in {"gehoben", "gehobener dienst"}:
            return "b"
        if raw_level in {"hoeher", "höher", "hoeherer dienst", "höherer dienst"}:
            return "c"
        if raw_level in {"durchschnitt", "average", "avg"}:
            return "d"
        return None

    if raw_level in {"niedrig", "low"}:
        return "a"
    if raw_level in {"mittel", "medium"}:
        return "b"
    if raw_level in {"hoch", "high"}:
        return "c"
    if raw_level in {"durchschnitt", "average", "avg"}:
        return "d"
    return None


def _parse_role_entries(
    entry: dict,
    period_suffix: str,
    norm_addressee: str,
) -> tuple[dict[str, float | None], dict[str, float | None], bool]:
    slot_keys = ["a", "b", "c", "d"]
    hourly_rates = {key: None for key in slot_keys}
    time_required = {key: None for key in slot_keys}
    raw_roles = entry.get(f"rollen_{period_suffix}")
    used_new_format = isinstance(raw_roles, list)
    if not used_new_format:
        return hourly_rates, time_required, False

    parsed_roles: list[tuple[str, float | None, float | None]] = []
    for raw_role in raw_roles:
        if not isinstance(raw_role, dict):
            continue
        slot = _resolve_effort_group(raw_role, norm_addressee)
        if slot is None:
            continue
        hourly_rate = parse_optional_number(
            raw_role.get("stundenlohn")
            or raw_role.get("stundenlohn_satz")
            or raw_role.get("hourly_rate")
        )
        duration = parse_optional_number(
            raw_role.get("zeitaufwand_in_min")
            or raw_role.get("zeitaufwand")
            or raw_role.get("time_required_in_min")
        )
        if hourly_rate is None and duration is None:
            continue
        parsed_roles.append((slot, hourly_rate, duration))

    for slot, hourly_rate, duration in parsed_roles:
        hourly_rates[slot] = hourly_rate
        time_required[slot] = duration
    return hourly_rates, time_required, True


def _parse_citizens_effort_entry(entry: dict, step_id: int) -> dict | None:
    for key in ("rollen_current", "rollen_gueltig", "rollen_proposed", "rollen_vorschlag"):
        if isinstance(entry.get(key), list):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Invalid effort_calculation payload for citizens: "
                    f"unexpected roles array '{key}' for step_id {step_id}"
                ),
            )
    time_current = parse_optional_number(
        entry.get("zeitaufwand_in_min_current")
        or entry.get("zeitaufwand_in_min_gueltig")
        or entry.get("time_required_in_min_current")
        or entry.get("time_required_in_min_gueltig")
    )
    time_proposed = parse_optional_number(
        entry.get("zeitaufwand_in_min_proposed")
        or entry.get("zeitaufwand_in_min_vorschlag")
        or entry.get("time_required_in_min_proposed")
        or entry.get("time_required_in_min_vorschlag")
    )
    expenses_current = parse_optional_number(
        entry.get("sachaufwand_current")
        or entry.get("sachaufwand_gueltig")
    )
    expenses_proposed = parse_optional_number(
        entry.get("sachaufwand_proposed")
        or entry.get("sachaufwand_vorschlag")
    )

    if (
        time_current is None
        and time_proposed is None
        and expenses_current is None
        and expenses_proposed is None
    ):
        return None

    return {
        "step_id": step_id,
        "hourly_rates_current": _empty_role_values(),
        "hourly_rates_proposed": _empty_role_values(),
        "time_required_current": {"a": time_current, "b": None, "c": None, "d": None},
        "time_required_proposed": {"a": time_proposed, "b": None, "c": None, "d": None},
        "expenses_current": expenses_current,
        "expenses_proposed": expenses_proposed,
        "execution_per_case": _parse_execution_per_case(entry),
        "aenderungsstatus": extract_change_status(entry),
    }


def _parse_org_effort_entry(
    entry: dict,
    step_id: int,
    norm_addressee: str,
) -> tuple[dict | None, set[str]]:
    fallback_kinds: set[str] = set()
    hourly_rates_current, time_required_current, uses_role_format_current = _parse_role_entries(
        entry,
        "gueltig",
        norm_addressee,
    )
    hourly_rates_proposed, time_required_proposed, uses_role_format_proposed = _parse_role_entries(
        entry,
        "vorschlag",
        norm_addressee,
    )
    business_aliases = {
        "a": ["niedrig", "low"],
        "b": ["mittel", "medium"],
        "c": ["hoch", "high"],
        "d": ["durchschnitt", "average", "avg"],
    }
    for key in ["a", "b", "c", "d"]:
        if not uses_role_format_current:
            hourly_rates_current_raw, current_rate_alias = _value_from_keys(
                entry,
                f"stundenlohn_satz_{key}_current",
                (
                    f"stundenlohn_satz_{key}_gueltig",
                    f"stundenlohn_satz_{key.upper()}_current",
                    f"stundenlohn_satz_{key.upper()}_gueltig",
                    *(f"stundenlohn_satz_{alias}_current" for alias in business_aliases[key]),
                    *(f"stundenlohn_satz_{alias}_gueltig" for alias in business_aliases[key]),
                    *(f"stundenlohn_satz_{alias.upper()}_current" for alias in business_aliases[key]),
                    *(f"stundenlohn_satz_{alias.upper()}_gueltig" for alias in business_aliases[key]),
                ),
            )
            time_required_current_raw, current_time_alias = _value_from_keys(
                entry,
                f"zeitaufwand_in_min_{key}_current",
                (
                    f"zeitaufwand_in_min_{key}_gueltig",
                    f"zeitaufwand_in_min_{key.upper()}_current",
                    f"zeitaufwand_in_min_{key.upper()}_gueltig",
                    *(f"zeitaufwand_in_min_{alias}_current" for alias in business_aliases[key]),
                    *(f"zeitaufwand_in_min_{alias}_gueltig" for alias in business_aliases[key]),
                    *(f"zeitaufwand_in_min_{alias.upper()}_current" for alias in business_aliases[key]),
                    *(f"zeitaufwand_in_min_{alias.upper()}_gueltig" for alias in business_aliases[key]),
                ),
            )
            if current_rate_alias is not None or current_time_alias is not None:
                fallback_kinds.add("effort_legacy_key_alias")
            hourly_rates_current[key] = parse_optional_number(hourly_rates_current_raw)
            time_required_current[key] = parse_optional_number(time_required_current_raw)

        if not uses_role_format_proposed:
            hourly_rates_proposed_raw, proposed_rate_alias = _value_from_keys(
                entry,
                f"stundenlohn_satz_{key}_proposed",
                (
                    f"stundenlohn_satz_{key}_vorschlag",
                    f"stundenlohn_satz_{key.upper()}_proposed",
                    f"stundenlohn_satz_{key.upper()}_vorschlag",
                    *(f"stundenlohn_satz_{alias}_proposed" for alias in business_aliases[key]),
                    *(f"stundenlohn_satz_{alias}_vorschlag" for alias in business_aliases[key]),
                    *(f"stundenlohn_satz_{alias.upper()}_proposed" for alias in business_aliases[key]),
                    *(f"stundenlohn_satz_{alias.upper()}_vorschlag" for alias in business_aliases[key]),
                ),
            )
            time_required_proposed_raw, proposed_time_alias = _value_from_keys(
                entry,
                f"zeitaufwand_in_min_{key}_proposed",
                (
                    f"zeitaufwand_in_min_{key}_vorschlag",
                    f"zeitaufwand_in_min_{key.upper()}_proposed",
                    f"zeitaufwand_in_min_{key.upper()}_vorschlag",
                    *(f"zeitaufwand_in_min_{alias}_proposed" for alias in business_aliases[key]),
                    *(f"zeitaufwand_in_min_{alias}_vorschlag" for alias in business_aliases[key]),
                    *(f"zeitaufwand_in_min_{alias.upper()}_proposed" for alias in business_aliases[key]),
                    *(f"zeitaufwand_in_min_{alias.upper()}_vorschlag" for alias in business_aliases[key]),
                ),
            )
            if proposed_rate_alias is not None or proposed_time_alias is not None:
                fallback_kinds.add("effort_legacy_key_alias")
            hourly_rates_proposed[key] = parse_optional_number(hourly_rates_proposed_raw)
            time_required_proposed[key] = parse_optional_number(time_required_proposed_raw)

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
    expenses_current = parse_optional_number(expenses_current_raw)
    expenses_proposed = parse_optional_number(expenses_proposed_raw)

    if (
        all(value is None for value in hourly_rates_current.values())
        and all(value is None for value in hourly_rates_proposed.values())
        and all(value is None for value in time_required_current.values())
        and all(value is None for value in time_required_proposed.values())
        and expenses_current is None
        and expenses_proposed is None
    ):
        return None, fallback_kinds

    return {
        "step_id": step_id,
        "hourly_rates_current": hourly_rates_current,
        "hourly_rates_proposed": hourly_rates_proposed,
        "time_required_current": time_required_current,
        "time_required_proposed": time_required_proposed,
        "expenses_current": expenses_current,
        "expenses_proposed": expenses_proposed,
        "execution_per_case": _parse_execution_per_case(entry),
        "aenderungsstatus": extract_change_status(entry),
    }, fallback_kinds


def _parse_effort_payload(payload: str, norm_addressee: str) -> tuple[list[dict], set[str]]:
    data, parse_mode = require_json_object(
        payload,
        error_context=f"Invalid effort_calculation payload for {norm_addressee}",
    )
    fallback_kinds: set[str] = set()
    if parse_mode == "extract_last_json_object":
        fallback_kinds.add("json_extract_last_object")
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
            if norm_addressee == CITIZENS:
                parsed_entry = _parse_citizens_effort_entry(entry, step_id)
            else:
                parsed_entry, entry_fallbacks = _parse_org_effort_entry(
                    entry,
                    step_id,
                    norm_addressee,
                )
                fallback_kinds.update(entry_fallbacks)
            if parsed_entry is not None:
                parsed.append(parsed_entry)
    return parsed, fallback_kinds


def _requires_mirror_matching_for_addressee(
    regulations: list[dict],
    norm_addressee: str,
) -> bool:
    for row in regulations:
        if str(row.get("mirror_anchor_key") or "").strip():
            return True
    return False


@router.post("/calculate")
async def calculate_effort(
    payload: EffortCalculationRequest,
    api_keys: ApiKeys = Depends(get_api_keys),
) -> dict:
    session_id, _created, model = ensure_session_or_400(
        payload.app_session_id,
        payload.model,
    )

    norm_addressee = normalize_norm_addressee_or_422(payload.norm_addressee)
    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    regulations = db.list_regulations_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    case_groups = db.list_case_groups_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    steps = db.list_process_steps_for_session_and_addressee(session_id, norm_addressee)
    session_has_any_regulations = bool(db.list_regulations_for_session(session_id))
    if not case_groups and session_has_any_regulations and not db.has_applicable_regulations_for_addressee(
        session_id, norm_addressee
    ):
        return {
            "status": "skipped",
            "case_groups_updated": 0,
            "steps_updated": 0,
            "norm_addressee": norm_addressee,
        }
    if not case_groups:
        raise HTTPException(
            status_code=400,
            detail=(
                "No case groups for session"
                if norm_addressee == ADMINISTRATION
                else "No case groups for selected norm addressee"
            ),
        )
    if not steps:
        raise HTTPException(status_code=400, detail="No process steps for session")
    has_existing_metrics = db.has_effort_metrics(session_id, norm_addressee)
    if has_existing_metrics:
        return {
            "status": "existing",
            "case_groups_updated": 0,
            "steps_updated": 0,
            "norm_addressee": norm_addressee,
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

    mirror_matches = await ensure_mirror_matching(
        session_id=session_id,
        model=model,
        provider=payload.provider,
        api_keys=api_keys,
        query_fn=query_llm,
    )
    if _requires_mirror_matching_for_addressee(regulations, norm_addressee) and not mirror_matches:
        raise HTTPException(
            status_code=422,
            detail=(
                "Mirror matching required for selected norm addressee, "
                "but no mirror matches could be determined"
            ),
        )

    cases_prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        session_id=session_id,
        case_groups_json=dump_prompt_json(case_groups_payload),
        norm_addressee=norm_addressee,
    )
    effort_prompt = render_prompt(
        PromptId.EFFORT_CALCULATION,
        session_id=session_id,
        step_analysis_json=dump_prompt_json(steps_payload),
        norm_addressee=norm_addressee,
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
        parsed_cases = apply_deterministic_mirror_case_group_sync(
            session_id=session_id,
            norm_addressee=norm_addressee,
            parsed_cases=parsed_cases,
        )
        parsed_effort, effort_fallback_kinds = _parse_effort_payload(
            effort_result.text,
            norm_addressee,
        )
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
                db.upsert_case_group_metrics_by_addressee(
                    session_id=session_id,
                    case_group_id=entry["case_group_id"],
                    norm_addressee=norm_addressee,
                    addressees_current=addressees_current,
                    annual_frequency_current=annual_frequency_current,
                    addressees_proposed=addressees_proposed,
                    annual_frequency_proposed=annual_frequency_proposed,
                    cases_current=cases_current,
                    cases_proposed=cases_proposed,
                )

            for entry in parsed_effort:
                db.upsert_process_step_effort_split_by_addressee(
                    session_id=session_id,
                    step_id=entry["step_id"],
                    norm_addressee=norm_addressee,
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

    refreshed_case_groups = db.list_case_groups_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    refreshed_steps = db.list_process_steps_for_session_and_addressee(
        session_id,
        norm_addressee,
    )
    refresh_case_group_tiles(session_id, refreshed_case_groups, norm_addressee=norm_addressee)
    refresh_step_tiles(session_id, refreshed_steps, norm_addressee=norm_addressee)

    return {
        "case_groups_updated": len(parsed_cases),
        "steps_updated": len(parsed_effort),
        "norm_addressee": norm_addressee,
    }
