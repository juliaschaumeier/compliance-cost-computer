from __future__ import annotations
import re

from fastapi import APIRouter, HTTPException

from backend.core import db
from backend.core.change_status import extract_change_status
from backend.core.llm_attempts import (
    mark_llm_parse_fallback,
)
from backend.core.llm_json import extract_fallgruppen, require_fallgruppen_envelope
from backend.core.llm_service import query_llm
from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
    NORM_ADDRESSEE_ECHO_MISMATCH,
    check_norm_addressee_echo,
)
from backend.core.parsing import parse_first_int, parse_optional_number
from backend.core.payload_builders import (
    build_case_groups_payload,
    build_step_analysis_payload,
    dump_prompt_json,
)
from backend.core.prompts import PromptId, render_prompt
from backend.core.tile_refresh import refresh_case_group_tiles, refresh_step_tiles
from backend.routers._norm_addressee import normalize_norm_addressee_or_422


router = APIRouter(prefix="/effort", tags=["effort"])

def _has_meaningful_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
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


def _parse_cases_payload(
    payload: str,
    norm_addressee: str | None = None,
) -> tuple[list[dict], set[str]]:
    data, parse_mode, envelope_mode = require_fallgruppen_envelope(
        payload,
        error_context="Invalid cases_calculation payload",
    )
    fallback_kinds: set[str] = set()
    if envelope_mode == "nested_prozesse":
        fallback_kinds.add("cases_nested_prozesse")
    if parse_mode == "extract_last_json_object":
        fallback_kinds.add("json_extract_last_object")
    echo_kinds = check_norm_addressee_echo(data, norm_addressee)
    if NORM_ADDRESSEE_ECHO_MISMATCH in echo_kinds:
        raise HTTPException(
            status_code=422,
            detail=f"normadressat mismatch (expected {norm_addressee})",
        )
    fallback_kinds.update(echo_kinds)
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
            "anzahl_betroffene_gueltig",
            ("anzahl_betroffene_current",),
        )
        annual_frequency_current_raw, frequency_current_alias = _value_from_keys(
            fallgruppe,
            "haeufigkeit_pro_jahr_gueltig",
            ("haeufigkeit_pro_jahr_current",),
        )
        addressees_proposed_raw, proposed_alias = _value_from_keys(
            fallgruppe,
            "anzahl_betroffene_vorschlag",
            ("anzahl_betroffene_proposed",),
        )
        annual_frequency_proposed_raw, frequency_proposed_alias = _value_from_keys(
            fallgruppe,
            "haeufigkeit_pro_jahr_vorschlag",
            ("haeufigkeit_pro_jahr_proposed",),
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
            fallback_kinds.add("cases_legacy_english_alias")
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
        metadata: dict[str, object] = {}
        confidence = fallgruppe.get("confidence")
        if isinstance(confidence, dict):
            metadata["confidence"] = confidence
        explanations = fallgruppe.get("erklaerungen")
        if isinstance(explanations, dict):
            metadata["erklaerungen"] = explanations
        parsed.append(
            {
                "case_group_id": case_group_id,
                "addressees_current": addressees_current,
                "annual_frequency_current": annual_frequency_current,
                "addressees_proposed": addressees_proposed,
                "annual_frequency_proposed": annual_frequency_proposed,
                "aenderungsstatus": extract_change_status(fallgruppe),
                "case_metric_research_json": metadata or None,
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


_ADMIN_LAUFBAHN_ALIASES: dict[str, str] = {
    "einfach": "a",
    "einfacher dienst": "a",
    "mittlerer dienst": "a",
    "einfacher und mittlerer dienst": "a",
    "mittel": "a",
    "m.d.": "a",
    "m. d.": "a",
    "md": "a",
    "gehoben": "b",
    "gehobener dienst": "b",
    "g.d.": "b",
    "g. d.": "b",
    "gd": "b",
    "hoeher": "c",
    "höher": "c",
    "hoeherer dienst": "c",
    "höherer dienst": "c",
    "h.d.": "c",
    "h. d.": "c",
    "hd": "c",
    "durchschnitt": "d",
    "average": "d",
    "avg": "d",
}

_BUSINESS_LEVEL_ALIASES: dict[str, str] = {
    "niedrig": "a",
    "low": "a",
    "einfach": "a",
    "mittel": "b",
    "medium": "b",
    "hoch": "c",
    "high": "c",
    "durchschnitt": "d",
    "average": "d",
    "avg": "d",
}


_WZ_VALID_LETTERS: frozenset[str] = frozenset("ABCDEFGHIJKLMNPQRS")
_WZ_PREFIX_RE = re.compile(
    r"^(?:wirtschaftsabschnitt|wz[ -]?abschnitt|wz)?\s*[-–—]?\s*([a-s])\b",
    re.IGNORECASE,
)
_WZ_GESAMTWIRTSCHAFT_VALUES = frozenset([
    "gesamtwirtschaft",
    "gesamtwirtschaft (a-s ohne o)",
])
_ADMIN_LEVEL_ALIASES: dict[str, str] = {
    "bund": "bund",
    "laender": "laender",
    "länder": "laender",
    "lander": "laender",
    "land": "laender",
    "kommunen": "kommunen",
    "kommune": "kommunen",
    "sozialversicherung": "sozialversicherung",
    "durchschnitt": "durchschnitt",
    "öffentliche verwaltung": "durchschnitt",
    "oeffentliche verwaltung": "durchschnitt",
    "durchschnitt öffentliche verwaltung, verteidigung, sozialversicherung": "durchschnitt",
    "durchschnitt oeffentliche verwaltung, verteidigung, sozialversicherung": "durchschnitt",
}


def _normalize_role_wage_source(raw_role: dict, norm_addressee: str) -> str | None:
    raw = str(raw_role.get("lohnquelle") or "").strip()
    if not raw:
        return None
    if norm_addressee == BUSINESS:
        normalized = raw.lower()
        if normalized in _WZ_GESAMTWIRTSCHAFT_VALUES:
            return "gesamtwirtschaft"
        match = _WZ_PREFIX_RE.match(normalized)
        if match:
            letter = match.group(1).upper()
            if letter in _WZ_VALID_LETTERS:
                return letter
        return None
    if norm_addressee == ADMINISTRATION:
        return _ADMIN_LEVEL_ALIASES.get(raw.lower())
    return None


def _resolve_qualification_slot(item: dict, norm_addressee: str) -> str | None:
    """Map a `qualifikation` value (row-based model) to the a/b/c/d slot.

    Maps via the laufbahn/level aliases only (underscores in canonical machine
    names like ``gehobener_dienst`` are normalised to spaces first). The bare
    slot letters a/b/c/d are intentionally NOT accepted: the prompt never emits
    them, so they would be old-slot-model leakage. The semantic aliases
    (``gehobener dienst``, ``gd``, ``niedrig``/``low`` …) are kept on purpose as
    LLM robustness. Raises 422 on an unrecognised qualification.
    """
    raw = str(item.get("qualifikation") or item.get("qualification") or "").strip()
    if not raw:
        return None
    normalized = raw.lower().replace("_", " ")
    aliases = (
        _ADMIN_LAUFBAHN_ALIASES
        if norm_addressee == ADMINISTRATION
        else _BUSINESS_LEVEL_ALIASES
    )
    resolved = aliases.get(normalized)
    if resolved is not None:
        return resolved
    raise HTTPException(
        status_code=422,
        detail=(
            f"effort_calculation: Unbekannte `qualifikation` {raw!r} fuer "
            f"Normadressat {norm_addressee!r}. Bitte Prompt- oder LLM-Antwort pruefen."
        ),
    )


def _parse_personnel_effort_entries(
    entry: dict,
    period_suffix: str,
    norm_addressee: str,
) -> tuple[dict[str, float | None], dict[str, float | None], list[dict], list[dict], bool]:
    """Parse the row-based ``personalaufwand_{period}`` list.

    Returns ``(hourly_rates, time_required, role_sources, rows, used_format)``.
    The first three are the legacy slot-based aggregation used for the Phase A
    dual-write into the old process_steps columns; ``rows`` are the authoritative
    child-table rows. Rejects the legacy ``rollen_{period}`` format (K4).
    """
    slot_keys = ["a", "b", "c", "d"]
    hourly_rates: dict[str, float | None] = {key: None for key in slot_keys}
    time_required: dict[str, float | None] = {key: None for key in slot_keys}

    raw_items = entry.get(f"personalaufwand_{period_suffix}")
    if not isinstance(raw_items, list):
        if isinstance(entry.get(f"rollen_{period_suffix}"), list):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"effort_calculation: Veraltetes `rollen_{period_suffix}`-Format "
                    f"wird nicht mehr akzeptiert. Erwartet: "
                    f"`personalaufwand_{period_suffix}`."
                ),
            )
        return hourly_rates, time_required, [], [], False

    period = "current" if period_suffix == "gueltig" else "proposed"
    source_kind = db.WAGE_SOURCE_KIND_BY_ADDRESSEE.get(norm_addressee)
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    slot_minutes: dict[str, float] = {}
    # slot -> (minutes, model_rate, source_value) of the dominant (max-minutes) row
    slot_dominant: dict[str, tuple[float, float, str]] = {}

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        raw_qualification = str(
            raw_item.get("qualifikation") or raw_item.get("qualification") or ""
        ).strip()
        raw_source = str(raw_item.get("lohnquelle") or "").strip()
        duration_raw, _duration_alias = _value_from_keys(
            raw_item,
            "zeitaufwand_in_min",
            ("zeitaufwand", "time_required_in_min"),
        )
        duration = parse_optional_number(duration_raw)
        if not raw_qualification:
            # Fully empty placeholder rows (prompt template) are skipped; a row that
            # carries a `lohnquelle` or a time but no `qualifikation` is rejected, so
            # a partially-filled entry is never silently dropped (symmetric with the
            # missing-`lohnquelle` rule below).
            if raw_source or duration is not None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "effort_calculation: Personalaufwand-Eintrag ohne "
                        "`qualifikation`, aber mit `lohnquelle`/`zeitaufwand`. Jeder "
                        "Eintrag mit Daten muss eine `qualifikation` angeben."
                    ),
                )
            continue
        slot = _resolve_qualification_slot(raw_item, norm_addressee)
        qualification = db.PERSONNEL_QUALIFICATION_BY_SLOT[norm_addressee][slot]

        source_value = _normalize_role_wage_source(raw_item, norm_addressee)
        if source_value is None:
            if raw_source:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"effort_calculation: Ungueltige `lohnquelle` "
                        f"{raw_item.get('lohnquelle')!r} fuer Normadressat "
                        f"{norm_addressee!r}. Erwartet: {source_kind}."
                    ),
                )
            # Missing source is rejected (not silently defaulted): every row must
            # name its lohnquelle, otherwise the wage row is not verifiable (#23)
            # and "forgot" would be indistinguishable from an explicit durchschnitt/
            # gesamtwirtschaft choice.
            raise HTTPException(
                status_code=422,
                detail=(
                    f"effort_calculation: Fehlende `lohnquelle` fuer Normadressat "
                    f"{norm_addressee!r}. Jeder Personalaufwand-Eintrag muss eine "
                    f"`lohnquelle` angeben ({source_kind})."
                ),
            )

        if duration is None:
            continue

        dedup_key = (qualification, source_value)
        if dedup_key in seen:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"effort_calculation: Doppelte Kombination aus `qualifikation` "
                    f"{qualification!r} und `lohnquelle` {source_value!r} in "
                    f"`personalaufwand_{period_suffix}`. Jede Kombination darf nur "
                    "einmal vorkommen."
                ),
            )
        seen.add(dedup_key)

        model_rate = db.get_model_hourly_rate(norm_addressee, source_value, qualification)
        if model_rate is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"effort_calculation: Kein Modell-Stundenlohn fuer "
                    f"{norm_addressee!r}/{source_value!r}/{qualification!r}."
                ),
            )

        rows.append(
            {
                "period": period,
                "qualification": qualification,
                "wage_source_kind": source_kind,
                "wage_source_value": source_value,
                "time_required_in_min": duration,
                "model_hourly_rate": model_rate,
            }
        )

        # Dual-write aggregation: sum minutes per slot, keep the dominant row's
        # rate/source so the legacy single-rate columns stay consistent.
        slot_minutes[slot] = slot_minutes.get(slot, 0.0) + duration
        prev = slot_dominant.get(slot)
        if prev is None or duration > prev[0]:
            slot_dominant[slot] = (duration, model_rate, source_value)

    role_sources: dict[str, dict] = {}
    for slot, total_minutes in slot_minutes.items():
        time_required[slot] = total_minutes
    for slot, (_mins, rate, source_value) in slot_dominant.items():
        hourly_rates[slot] = rate
        role_sources[slot] = {
            "slot": slot,
            "role": "",
            "source_kind": source_kind,
            "source_value": source_value,
        }

    return hourly_rates, time_required, list(role_sources.values()), rows, True


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
    time_current_raw, _time_current_alias = _value_from_keys(
        entry,
        "zeitaufwand_in_min_gueltig",
        (
            "zeitaufwand_in_min_current",
            "time_required_in_min_gueltig",
            "time_required_in_min_current",
        ),
    )
    time_proposed_raw, _time_proposed_alias = _value_from_keys(
        entry,
        "zeitaufwand_in_min_vorschlag",
        (
            "zeitaufwand_in_min_proposed",
            "time_required_in_min_vorschlag",
            "time_required_in_min_proposed",
        ),
    )
    expenses_current_raw, _expenses_current_alias = _value_from_keys(
        entry,
        "sachaufwand_gueltig",
        ("sachaufwand_current",),
    )
    expenses_proposed_raw, _expenses_proposed_alias = _value_from_keys(
        entry,
        "sachaufwand_vorschlag",
        ("sachaufwand_proposed",),
    )
    time_current = parse_optional_number(time_current_raw)
    time_proposed = parse_optional_number(time_proposed_raw)
    expenses_current = parse_optional_number(expenses_current_raw)
    expenses_proposed = parse_optional_number(expenses_proposed_raw)

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
    (
        hourly_rates_current,
        time_required_current,
        role_sources_current,
        rows_current,
        _uses_personnel_current,
    ) = _parse_personnel_effort_entries(entry, "gueltig", norm_addressee)
    (
        hourly_rates_proposed,
        time_required_proposed,
        role_sources_proposed,
        rows_proposed,
        _uses_personnel_proposed,
    ) = _parse_personnel_effort_entries(entry, "vorschlag", norm_addressee)
    # The LLM contract is row-only (`personalaufwand_*`); it must never return
    # wages. Any `stundenlohn_satz_*` (the old AI-wage slot format) is rejected
    # outright (Julia: "stop accepting stundenlohn"). The backend resolves the
    # hourly rate from the wage table. The slot columns are still written, but
    # only as a dual-write aggregation of the row model (see
    # `_parse_personnel_effort_entries`), not from flat LLM keys.
    if any(
        isinstance(key, str) and key.lower().startswith("stundenlohn_satz")
        for key in entry
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "effort_calculation: `stundenlohn_satz_*` (KI-Loehne) werden nicht "
                "mehr akzeptiert. Der Backend-Dienst ermittelt den Stundenlohn aus "
                "der Lohnkostentabelle; geben Sie nur `personalaufwand_*` aus."
            ),
        )

    expenses_current_raw, expenses_current_alias = _value_from_keys(
        entry,
        "sachaufwand_gueltig",
        ("sachaufwand_current",),
    )
    expenses_proposed_raw, expenses_proposed_alias = _value_from_keys(
        entry,
        "sachaufwand_vorschlag",
        ("sachaufwand_proposed",),
    )
    if expenses_current_alias is not None or expenses_proposed_alias is not None:
        fallback_kinds.add("effort_legacy_english_alias")
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
        "role_sources_current": role_sources_current,
        "role_sources_proposed": role_sources_proposed,
        "personnel_effort_rows": rows_current + rows_proposed,
    }, fallback_kinds


def _parse_effort_payload(payload: str, norm_addressee: str) -> tuple[list[dict], set[str]]:
    data, parse_mode, envelope_mode = require_fallgruppen_envelope(
        payload,
        error_context=f"Invalid effort_calculation payload for {norm_addressee}",
    )
    fallback_kinds: set[str] = set()
    if envelope_mode == "nested_prozesse":
        fallback_kinds.add("effort_nested_prozesse")
    if parse_mode == "extract_last_json_object":
        fallback_kinds.add("json_extract_last_object")
    echo_kinds = check_norm_addressee_echo(data, norm_addressee)
    if NORM_ADDRESSEE_ECHO_MISMATCH in echo_kinds:
        raise HTTPException(
            status_code=422,
            detail=f"normadressat mismatch (expected {norm_addressee})",
        )
    fallback_kinds.update(echo_kinds)
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


def _expected_case_group_ids(context: dict) -> set[int]:
    return {int(group["case_group_id"]) for group in context["case_groups"]}


def _expected_step_ids(context: dict) -> set[int]:
    return {int(step["step_id"]) for step in context["steps"]}


def _validate_parsed_cases(parsed_cases: list[dict], context: dict) -> None:
    if not parsed_cases:
        raise HTTPException(status_code=422, detail="No case group metrics parsed")

    case_group_ids = _expected_case_group_ids(context)
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

    # #13/#25: Jede fallgruppen_id genau einmal (kein stilles last-write-wins)
    # und jede Fallgruppe des Normadressaten muss Kennzahlen erhalten.
    seen_case_group_ids: set[int] = set()
    duplicate_case_groups: list[str] = []
    for entry in parsed_cases:
        case_group_id = int(entry["case_group_id"])
        if case_group_id in seen_case_group_ids:
            duplicate_case_groups.append(str(case_group_id))
        else:
            seen_case_group_ids.add(case_group_id)
    if duplicate_case_groups:
        raise HTTPException(
            status_code=422,
            detail="Duplicate fallgruppen_id values: "
            + ", ".join(sorted(set(duplicate_case_groups))),
        )

    uncovered_case_groups = sorted(
        str(case_group_id) for case_group_id in case_group_ids - seen_case_group_ids
    )
    if uncovered_case_groups:
        raise HTTPException(
            status_code=422,
            detail="Missing metrics for fallgruppen_id values: "
            + ", ".join(uncovered_case_groups),
        )


def _validate_parsed_effort(parsed_effort: list[dict], context: dict) -> None:
    if not parsed_effort:
        raise HTTPException(status_code=422, detail="No effort metrics parsed")

    step_ids = _expected_step_ids(context)
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

    # #13/#25: Jede taetigkeiten_id genau einmal und jeder Schritt des
    # Normadressaten muss einen Aufwandswert erhalten (symmetrisch zu den
    # Fallgruppen oben).
    seen_step_ids: set[int] = set()
    duplicate_steps: list[str] = []
    for entry in parsed_effort:
        step_id = int(entry["step_id"])
        if step_id in seen_step_ids:
            duplicate_steps.append(str(step_id))
        else:
            seen_step_ids.add(step_id)
    if duplicate_steps:
        raise HTTPException(
            status_code=422,
            detail="Duplicate taetigkeiten_id values: "
            + ", ".join(sorted(set(duplicate_steps))),
        )

    uncovered_steps = sorted(str(step_id) for step_id in step_ids - seen_step_ids)
    if uncovered_steps:
        raise HTTPException(
            status_code=422,
            detail="Missing effort for taetigkeiten_id values: "
            + ", ".join(uncovered_steps),
        )


def parse_cases_calculation_output(
    *,
    session_id: int,
    norm_addressee: str,
    context: dict,
    cases_text: str,
    cases_answer_id: int | None,
) -> list[dict]:
    parsed_cases, fallback_kinds = _parse_cases_payload(cases_text, norm_addressee)
    for fallback_kind in sorted(fallback_kinds):
        mark_llm_parse_fallback(
            answer_id=cases_answer_id,
            session_id=session_id,
            prompt_id=PromptId.CASES_CALCULATION,
            fallback_kind=fallback_kind,
        )
    _validate_parsed_cases(parsed_cases, context)
    return parsed_cases


def parse_effort_calculation_output(
    *,
    session_id: int,
    norm_addressee: str,
    context: dict,
    effort_text: str,
    effort_answer_id: int | None,
) -> list[dict]:
    parsed_effort, fallback_kinds = _parse_effort_payload(effort_text, norm_addressee)
    for fallback_kind in sorted(fallback_kinds):
        mark_llm_parse_fallback(
            answer_id=effort_answer_id,
            session_id=session_id,
            prompt_id=PromptId.EFFORT_CALCULATION,
            fallback_kind=fallback_kind,
        )
    _validate_parsed_effort(parsed_effort, context)
    return parsed_effort


def prepare_effort_calculation(
    *,
    session_id: int,
    norm_addressee: str,
    skip_cases_calculation: bool,
) -> dict:
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
        return {"status": "skipped", "case_groups": [], "steps": []}
    if not case_groups and db.has_no_process_path_for_addressee(
        session_id, norm_addressee
    ):
        return {"status": "skipped", "case_groups": [], "steps": []}
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
    has_existing_metrics = (
        db.has_process_step_effort_metrics(session_id, norm_addressee)
        if skip_cases_calculation
        else db.has_effort_metrics(session_id, norm_addressee)
    )
    if has_existing_metrics:
        return {"status": "existing", "case_groups": case_groups, "steps": steps}

    steps_payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=regulations,
        norm_addressee=norm_addressee,
    )

    effort_prompt = render_prompt(
        PromptId.EFFORT_CALCULATION,
        session_id=session_id,
        step_analysis_json=dump_prompt_json(steps_payload),
        norm_addressee=norm_addressee,
    )

    cases_prompt = None
    if not skip_cases_calculation:
        case_groups_payload = build_case_groups_payload(
            processes=processes,
            case_groups=case_groups,
            regulations=regulations,
            norm_addressee=norm_addressee,
        )
        cases_prompt = render_prompt(
            PromptId.CASES_CALCULATION,
            session_id=session_id,
            case_groups_json=dump_prompt_json(case_groups_payload),
            norm_addressee=norm_addressee,
        )

    return {
        "status": "ready",
        "processes": processes,
        "regulations": regulations,
        "case_groups": case_groups,
        "steps": steps,
        "cases_prompt": cases_prompt,
        "effort_prompt": effort_prompt,
        "skip_cases_calculation": skip_cases_calculation,
    }


def parse_effort_calculation_outputs(
    *,
    session_id: int,
    norm_addressee: str,
    context: dict,
    cases_text: str | None,
    effort_text: str,
    cases_answer_id: int | None,
    effort_answer_id: int,
) -> tuple[list[dict], list[dict]]:
    parsed_cases: list[dict] = []
    skip_cases_calculation = bool(context.get("skip_cases_calculation"))
    if not skip_cases_calculation:
        if cases_text is None:
            raise HTTPException(status_code=500, detail="Missing cases_calculation answer")
        parsed_cases = parse_cases_calculation_output(
            session_id=session_id,
            norm_addressee=norm_addressee,
            context=context,
            cases_text=cases_text,
            cases_answer_id=cases_answer_id,
        )
    parsed_effort = parse_effort_calculation_output(
        session_id=session_id,
        norm_addressee=norm_addressee,
        context=context,
        effort_text=effort_text,
        effort_answer_id=effort_answer_id,
    )

    return parsed_cases, parsed_effort


def apply_effort_calculation_outputs(
    *,
    session_id: int,
    norm_addressee: str,
    parsed_cases: list[dict],
    parsed_effort: list[dict],
    skip_cases_calculation: bool,
) -> None:
    if not skip_cases_calculation:
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
                case_metric_research_json=entry.get("case_metric_research_json"),
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
            role_sources_current=entry.get("role_sources_current"),
            role_sources_proposed=entry.get("role_sources_proposed"),
        )
        db.replace_process_step_personnel_effort(
            session_id=session_id,
            norm_addressee=norm_addressee,
            step_id=entry["step_id"],
            rows=entry.get("personnel_effort_rows", []),
        )


def refresh_effort_tiles(
    *,
    session_id: int,
    norm_addressee: str,
) -> None:
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
