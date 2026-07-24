from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from backend.core import db
from backend.core.llm_json import extract_fallgruppen, require_fallgruppen_envelope
from backend.core.norm_addressees import normalize_norm_addressee
from backend.core.parsing import parse_first_int, parse_optional_number


CASE_GROUP_RESEARCH_PURPOSE = "case_group_metrics"


@dataclass(frozen=True)
class ParsedResearchCaseGroup:
    norm_addressee: str
    process_id: int | None
    case_group_id: int
    addressees_current: float | None
    annual_frequency_current: float | None
    addressees_proposed: float | None
    annual_frequency_proposed: float | None
    metadata: dict[str, Any]


def _deep_research_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail=f"Deep-Research-Fallzahlen konnten nicht verarbeitet werden: {detail}",
    )


def _format_deep_research_envelope_error(detail: str) -> str:
    if "no JSON object found" in detail:
        return "kein JSON-Objekt gefunden"
    if "top-level key 'fallgruppen' to contain an array" in detail:
        return "das Feld `fallgruppen` muss ein Array enthalten"
    if "expected top-level key 'fallgruppen' or legacy 'prozesse' array" in detail:
        return "erwartet wurde ein JSON-Objekt mit Array `fallgruppen`"
    return detail


def _normalize_deep_research_norm_addressee(raw: Any) -> str:
    try:
        return normalize_norm_addressee(str(raw or ""))
    except ValueError as exc:
        raise _deep_research_error(str(exc)) from exc


def _iter_research_case_groups(
    data: dict[str, Any],
    *,
    envelope_mode: str,
) -> list[tuple[dict[str, Any], str | None, int | None]]:
    if envelope_mode == "flat_fallgruppen":
        return [
            (group, None, None)
            for group in extract_fallgruppen(data)
            if isinstance(group, dict)
        ]

    processes = data.get("prozesse")
    if not isinstance(processes, list):
        raise _deep_research_error("erwartet wurde ein Array `fallgruppen`")

    entries: list[tuple[dict[str, Any], str | None, int | None]] = []
    for process in processes:
        if not isinstance(process, dict):
            continue
        process_norm_addressee = process.get("normadressat")
        process_id = parse_first_int(process, "prozess_id", "process_id")
        fallgruppen = process.get("fallgruppen")
        if not isinstance(fallgruppen, list):
            continue
        for group in fallgruppen:
            if isinstance(group, dict):
                entries.append((group, process_norm_addressee, process_id))
    return entries


def parse_deep_research_case_metrics(report_text: str) -> tuple[dict[str, Any], list[ParsedResearchCaseGroup]]:
    try:
        data, _parse_mode, envelope_mode = require_fallgruppen_envelope(
            report_text,
            error_context="Invalid Deep Research case metrics payload",
        )
    except HTTPException as exc:
        raise _deep_research_error(
            _format_deep_research_envelope_error(str(exc.detail))
        ) from exc

    parsed: list[ParsedResearchCaseGroup] = []
    for group, inherited_norm_addressee, inherited_process_id in _iter_research_case_groups(
        data,
        envelope_mode=envelope_mode,
    ):
        norm_addressee = _normalize_deep_research_norm_addressee(
            group.get("normadressat") or inherited_norm_addressee
        )
        case_group_id = parse_first_int(
            group,
            "fallgruppen_id",
            "fallgruppe_id",
            "case_group_id",
        )
        if case_group_id is None:
            raise _deep_research_error("Fallgruppe ohne `fallgruppen_id`")
        addressees_current = parse_optional_number(
            group.get("anzahl_betroffene_gueltig")
        )
        annual_frequency_current = parse_optional_number(
            group.get("haeufigkeit_pro_jahr_gueltig")
        )
        addressees_proposed = parse_optional_number(
            group.get("anzahl_betroffene_vorschlag")
        )
        annual_frequency_proposed = parse_optional_number(
            group.get("haeufigkeit_pro_jahr_vorschlag")
        )
        if (
            addressees_current is None
            and annual_frequency_current is None
            and addressees_proposed is None
            and annual_frequency_proposed is None
        ):
            continue
        metadata = {
            "confidence": group.get("confidence"),
            "erklaerungen": group.get("erklaerungen"),
            "quellen": group.get("quellen"),
            "fallzahl_gueltig": parse_optional_number(group.get("fallzahl_gueltig")),
            "fallzahl_vorschlag": parse_optional_number(group.get("fallzahl_vorschlag")),
            "raw": group,
        }
        parsed.append(
            ParsedResearchCaseGroup(
                norm_addressee=norm_addressee,
                process_id=inherited_process_id,
                case_group_id=int(case_group_id),
                addressees_current=addressees_current,
                annual_frequency_current=annual_frequency_current,
                addressees_proposed=addressees_proposed,
                annual_frequency_proposed=annual_frequency_proposed,
                metadata=metadata,
            )
        )
    return data, parsed


def apply_deep_research_case_metrics(
    *,
    session_id: int,
    report_text: str,
    research_run_id: int | None = None,
) -> int:
    data, parsed = validate_deep_research_case_metrics(
        session_id=session_id,
        report_text=report_text,
    )
    with db.transaction():
        apply_validated_deep_research_case_metrics(
            session_id=session_id,
            data=data,
            parsed=parsed,
            report_text=report_text,
            research_run_id=research_run_id,
        )
    return len(parsed)


def validate_deep_research_case_metrics(
    *,
    session_id: int,
    report_text: str,
) -> tuple[dict[str, Any], list[ParsedResearchCaseGroup]]:
    data, parsed = parse_deep_research_case_metrics(report_text)
    if not parsed:
        raise _deep_research_error("keine Fallgruppen-Kennzahlen gefunden")

    expected: dict[tuple[str, int], dict] = {}
    for group in db.list_case_groups_for_session(session_id):
        expected[(str(group["norm_addressee"]), int(group["case_group_id"]))] = group

    missing: list[str] = []
    process_mismatches: list[str] = []
    duplicates: list[str] = []
    seen: set[tuple[str, int]] = set()
    for entry in parsed:
        key = (entry.norm_addressee, entry.case_group_id)
        if key in seen:
            duplicates.append(f"{entry.norm_addressee}:{entry.case_group_id}")
        seen.add(key)
        existing = expected.get(key)
        if existing is None:
            missing.append(f"{entry.norm_addressee}:{entry.case_group_id}")
            continue
        if entry.process_id is not None and int(existing["process_id"]) != int(entry.process_id):
            process_mismatches.append(
                f"{entry.norm_addressee}:{entry.case_group_id} "
                f"(expected process {existing['process_id']}, got {entry.process_id})"
            )
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Deep-Research-Fallzahlen enthalten unbekannte fallgruppen_id-Werte: "
            + ", ".join(missing),
        )
    if duplicates:
        raise HTTPException(
            status_code=422,
            detail="Deep-Research-Fallzahlen enthalten doppelte fallgruppen_id-Werte: "
            + ", ".join(sorted(set(duplicates))),
        )
    if process_mismatches:
        raise HTTPException(
            status_code=422,
            detail="Deep-Research-Fallzahlen enthalten widerspruechliche Prozesszuordnungen: "
            + "; ".join(process_mismatches),
        )
    omitted = sorted(
        f"{norm_addressee}:{case_group_id}"
        for norm_addressee, case_group_id in expected
        if (norm_addressee, case_group_id) not in seen
    )
    if omitted:
        raise HTTPException(
            status_code=422,
            detail="Deep-Research-Fallzahlen lassen fallgruppen_id-Werte aus: "
            + ", ".join(omitted),
        )
    return data, parsed


def apply_validated_deep_research_case_metrics(
    *,
    session_id: int,
    data: dict[str, Any],
    parsed: list[ParsedResearchCaseGroup],
    report_text: str,
    research_run_id: int | None = None,
) -> int:
    for entry in parsed:
        db.upsert_case_group_metrics_by_addressee(
            session_id=session_id,
            case_group_id=entry.case_group_id,
            norm_addressee=entry.norm_addressee,
            addressees_current=entry.addressees_current,
            annual_frequency_current=entry.annual_frequency_current,
            addressees_proposed=entry.addressees_proposed,
            annual_frequency_proposed=entry.annual_frequency_proposed,
            case_metric_research_json=entry.metadata,
        )
    if research_run_id is not None:
        db.update_deep_research_run(
            research_run_id,
            status="parsed",
            report_md=report_text,
            result_json=data,
        )
    return len(parsed)
