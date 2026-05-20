from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from backend.core import db
from backend.core.llm_json import require_json_object
from backend.core.norm_addressees import normalize_norm_addressee
from backend.core.parsing import parse_first_int, parse_optional_number


CASE_GROUP_RESEARCH_PURPOSE = "case_group_metrics"


@dataclass(frozen=True)
class ParsedResearchCaseGroup:
    norm_addressee: str
    process_id: int
    case_group_id: int
    addressees_current: float | None
    annual_frequency_current: float | None
    addressees_proposed: float | None
    annual_frequency_proposed: float | None
    metadata: dict[str, Any]


def _extract_process_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    processes = data.get("prozesse")
    if not isinstance(processes, list):
        raise HTTPException(
            status_code=422,
            detail="Invalid Deep Research payload: expected top-level 'prozesse' list",
        )
    return [process for process in processes if isinstance(process, dict)]


def parse_deep_research_case_metrics(report_text: str) -> tuple[dict[str, Any], list[ParsedResearchCaseGroup]]:
    data, _parse_mode = require_json_object(
        report_text,
        error_context="Invalid Deep Research case metrics payload",
        required_top_level_key="prozesse",
    )
    parsed: list[ParsedResearchCaseGroup] = []
    for process in _extract_process_entries(data):
        try:
            norm_addressee = normalize_norm_addressee(str(process.get("normadressat") or ""))
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid Deep Research payload: {exc}",
            ) from exc
        process_id = parse_first_int(process, "prozess_id", "process_id")
        if process_id is None:
            raise HTTPException(
                status_code=422,
                detail="Invalid Deep Research payload: process is missing prozess_id",
            )
        fallgruppen = process.get("fallgruppen")
        if not isinstance(fallgruppen, list):
            continue
        for group in fallgruppen:
            if not isinstance(group, dict):
                continue
            case_group_id = parse_first_int(
                group,
                "fallgruppen_id",
                "fallgruppe_id",
                "case_group_id",
            )
            if case_group_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="Invalid Deep Research payload: fallgruppe is missing fallgruppen_id",
                )
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
                    process_id=int(process_id),
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
    data, parsed = parse_deep_research_case_metrics(report_text)
    if not parsed:
        raise HTTPException(
            status_code=422,
            detail="Invalid Deep Research payload: no case-group metrics parsed",
        )

    expected: dict[tuple[str, int], dict] = {}
    for group in db.list_case_groups_for_session(session_id):
        expected[(str(group["norm_addressee"]), int(group["case_group_id"]))] = group

    missing: list[str] = []
    process_mismatches: list[str] = []
    seen: set[tuple[str, int]] = set()
    for entry in parsed:
        key = (entry.norm_addressee, entry.case_group_id)
        seen.add(key)
        existing = expected.get(key)
        if existing is None:
            missing.append(f"{entry.norm_addressee}:{entry.case_group_id}")
            continue
        if int(existing["process_id"]) != int(entry.process_id):
            process_mismatches.append(
                f"{entry.norm_addressee}:{entry.case_group_id} "
                f"(expected process {existing['process_id']}, got {entry.process_id})"
            )
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Unknown Deep Research fallgruppen_id values: " + ", ".join(missing),
        )
    if process_mismatches:
        raise HTTPException(
            status_code=422,
            detail="Deep Research process_id mismatch: " + "; ".join(process_mismatches),
        )
    omitted = sorted(
        f"{norm_addressee}:{case_group_id}"
        for norm_addressee, case_group_id in expected
        if (norm_addressee, case_group_id) not in seen
    )
    if omitted:
        raise HTTPException(
            status_code=422,
            detail="Deep Research omitted fallgruppen_id values: " + ", ".join(omitted),
        )

    with db.transaction():
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
