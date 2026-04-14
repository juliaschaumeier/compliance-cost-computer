from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


class _PromptPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VorgabePayload(_PromptPayloadModel):
    vorgaben_id: int
    normzitat: str
    beschreibung: str
    aenderungsstatus: str | None = None
    normadressaten: list[str] = Field(default_factory=list)
    ist_informationspflicht_wirtschaft: bool = False
    spiegelsituation: dict[str, Any] | None = None


class FallgruppePayload(_PromptPayloadModel):
    fallgruppen_id: int
    fallgruppe_bezeichnung: str
    fallgruppe_beschreibung: str
    aenderungsstatus: str | None = None
    spiegelsituationen: list[dict[str, Any]] = Field(default_factory=list)


class TaetigkeitPayload(_PromptPayloadModel):
    taetigkeiten_id: int
    taetigkeit: str
    beschreibung: str
    aenderungsstatus: str | None = None
    vorgaben_ids: list[int] = Field(default_factory=list)


class ProzessWithVorgabenPayload(_PromptPayloadModel):
    prozess_id: int
    prozess_bezeichnung: str
    prozess_beschreibung: str
    aenderungsstatus: str | None = None
    vorgaben: list[VorgabePayload] = Field(default_factory=list)


class ProzessWithFallgruppenPayload(ProzessWithVorgabenPayload):
    fallgruppen: list[FallgruppePayload] = Field(default_factory=list)


class FallgruppeWithTaetigkeitenPayload(FallgruppePayload):
    taetigkeiten: list[TaetigkeitPayload] = Field(default_factory=list)


class ProzessStepAnalysisPayload(ProzessWithVorgabenPayload):
    fallgruppen: list[FallgruppeWithTaetigkeitenPayload] = Field(default_factory=list)


def dump_prompt_json(payload: Any) -> str:
    """Serialize prompt input payloads with stable unicode handling."""
    return json.dumps(payload, ensure_ascii=False)


def _build_regulations_by_process(
    regulations: list[dict] | None,
) -> dict[int, list[dict]]:
    regs_by_process: dict[int, list[dict]] = {}
    for regulation in regulations or []:
        process_id = regulation.get("process_id")
        if process_id is None:
            continue
        regs_by_process.setdefault(int(process_id), []).append(regulation)
    return regs_by_process


def build_vorgaben_payload(regulations: list[dict]) -> list[dict]:
    payload: list[dict] = []
    for row in regulations:
        payload.append(
            VorgabePayload(
                vorgaben_id=int(row["regulation_id"]),
                normzitat=str(row.get("legal_citation") or ""),
                beschreibung=str(row.get("description") or ""),
                aenderungsstatus=row.get("change_status"),
                normadressaten=[
                    name
                    for name, enabled in (
                        (ADMINISTRATION, row.get("applies_to_administration")),
                        (BUSINESS, row.get("applies_to_business")),
                        (CITIZENS, row.get("applies_to_citizens")),
                    )
                    if enabled
                ],
                ist_informationspflicht_wirtschaft=bool(
                    row.get("is_business_information_obligation")
                ),
                spiegelsituation=_build_spiegelsituation_payload(row),
            ).model_dump()
        )
    return payload


def _serialize_process_regulations(
    regs_by_process: dict[int, list[dict]],
    process_id: int,
) -> list[VorgabePayload]:
    return [
        VorgabePayload(
            vorgaben_id=int(row["regulation_id"]),
            normzitat=str(row.get("legal_citation") or ""),
            beschreibung=str(row.get("description") or ""),
            aenderungsstatus=row.get("change_status"),
            normadressaten=[
                name
                for name, enabled in (
                    (ADMINISTRATION, row.get("applies_to_administration")),
                    (BUSINESS, row.get("applies_to_business")),
                    (CITIZENS, row.get("applies_to_citizens")),
                )
                if enabled
            ],
            ist_informationspflicht_wirtschaft=bool(
                row.get("is_business_information_obligation")
            ),
            spiegelsituation=_build_spiegelsituation_payload(row),
        )
        for row in regs_by_process.get(process_id, [])
    ]


def _build_spiegelsituation_payload(row: dict) -> dict[str, Any] | None:
    mirror_addressees = [
        name
        for name, enabled in (
            (ADMINISTRATION, row.get("mirror_applies_to_administration")),
            (BUSINESS, row.get("mirror_applies_to_business")),
            (CITIZENS, row.get("mirror_applies_to_citizens")),
        )
        if enabled
    ]
    mirror_description = str(row.get("mirror_description") or "")
    mirror_anchor_key = str(row.get("mirror_anchor_key") or "")
    if not (mirror_addressees or mirror_description or mirror_anchor_key):
        return None
    return {
        "liegt_vor": True,
        "normadressaten": mirror_addressees,
        "beschreibung": mirror_description,
        "mirror_anchor_key": mirror_anchor_key,
    }


def _build_process_spiegelsituationen(
    regs_by_process: dict[int, list[dict]],
    process_id: int,
) -> list[dict[str, Any]]:
    situations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in regs_by_process.get(process_id, []):
        payload = _build_spiegelsituation_payload(row)
        if payload is None:
            continue
        dedupe_key = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        situations.append(payload)
    return situations


def build_case_groups_payload(
    processes: list[dict],
    case_groups: list[dict],
    regulations: list[dict] | None = None,
) -> list[dict]:
    groups_by_process: dict[int, list[FallgruppePayload]] = {}
    regs_by_process = _build_regulations_by_process(regulations)
    for group in case_groups:
        process_id = int(group["process_id"])
        group_payload = FallgruppePayload(
            fallgruppen_id=int(group["case_group_id"]),
            fallgruppe_bezeichnung=str(group.get("case_group") or ""),
            fallgruppe_beschreibung=str(group.get("description") or ""),
            aenderungsstatus=group.get("change_status"),
            spiegelsituationen=_build_process_spiegelsituationen(regs_by_process, process_id),
        )
        groups_by_process.setdefault(process_id, []).append(group_payload)

    payload: list[dict] = []
    for process in processes:
        process_id = int(process["process_id"])
        process_payload = ProzessWithFallgruppenPayload(
            prozess_id=process_id,
            prozess_bezeichnung=str(process.get("process") or ""),
            prozess_beschreibung=str(process.get("description") or ""),
            aenderungsstatus=process.get("change_status"),
            vorgaben=_serialize_process_regulations(regs_by_process, process_id),
            fallgruppen=groups_by_process.get(process_id, []),
        )
        payload.append(process_payload.model_dump())
    return payload


def build_processes_payload_with_regulations(
    processes: list[dict],
    regulations: list[dict],
) -> list[dict]:
    regs_by_process = _build_regulations_by_process(regulations)

    payload: list[dict] = []
    for process in processes:
        process_id = int(process["process_id"])
        process_payload = ProzessWithVorgabenPayload(
            prozess_id=process_id,
            prozess_bezeichnung=str(process.get("process") or ""),
            prozess_beschreibung=str(process.get("description") or ""),
            aenderungsstatus=process.get("change_status"),
            vorgaben=_serialize_process_regulations(regs_by_process, process_id),
        )
        payload.append(process_payload.model_dump())
    return payload


def _order_steps(steps: list[dict]) -> list[dict]:
    step_map = {int(step["step_id"]): step for step in steps}
    steps_by_prev: dict[int | None, list[int]] = {}
    for step_id, step in step_map.items():
        steps_by_prev.setdefault(step.get("previous_id"), []).append(step_id)

    ordered: list[int] = []
    start_ids = steps_by_prev.get(None, [])
    if start_ids:
        current_id = start_ids[0]
        seen: set[int] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            ordered.append(current_id)
            next_id = step_map[current_id].get("next_id")
            current_id = int(next_id) if next_id is not None else None
    if not ordered:
        ordered = sorted(step_map.keys())
    return [step_map[step_id] for step_id in ordered]


def build_step_analysis_payload(
    processes: list[dict],
    case_groups: list[dict],
    steps: list[dict],
    regulations: list[dict] | None = None,
) -> list[dict]:
    groups_by_process: dict[int, list[dict]] = {}
    regs_by_process = _build_regulations_by_process(regulations)
    for group in case_groups:
        process_id = int(group["process_id"])
        groups_by_process.setdefault(process_id, []).append(group)

    steps_by_group: dict[int, list[dict]] = {}
    for step in steps:
        steps_by_group.setdefault(int(step["case_group_id"]), []).append(step)

    payload: list[dict] = []
    for process in processes:
        process_id = int(process["process_id"])
        fallgruppen_payload: list[FallgruppeWithTaetigkeitenPayload] = []
        for group in groups_by_process.get(process_id, []):
            case_group_id = int(group["case_group_id"])
            ordered_steps = _order_steps(steps_by_group.get(case_group_id, []))
            taetigkeiten = [
                TaetigkeitPayload(
                    taetigkeiten_id=int(step["step_id"]),
                    taetigkeit=str(step.get("step") or ""),
                    beschreibung=str(step.get("description") or ""),
                    aenderungsstatus=step.get("change_status"),
                    vorgaben_ids=[
                        int(regulation_id)
                        for regulation_id in (step.get("regulation_ids") or [])
                    ],
                )
                for step in ordered_steps
            ]
            fallgruppen_payload.append(
                FallgruppeWithTaetigkeitenPayload(
                    fallgruppen_id=case_group_id,
                    fallgruppe_bezeichnung=str(group.get("case_group") or ""),
                    fallgruppe_beschreibung=str(group.get("description") or ""),
                    aenderungsstatus=group.get("change_status"),
                    spiegelsituationen=_build_process_spiegelsituationen(
                        regs_by_process, process_id
                    ),
                    taetigkeiten=taetigkeiten,
                )
            )
        process_payload = ProzessStepAnalysisPayload(
            prozess_id=process_id,
            prozess_bezeichnung=str(process.get("process") or ""),
            prozess_beschreibung=str(process.get("description") or ""),
            aenderungsstatus=process.get("change_status"),
            vorgaben=_serialize_process_regulations(regs_by_process, process_id),
            fallgruppen=fallgruppen_payload,
        )
        payload.append(process_payload.model_dump())
    return payload
