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


class FallgruppePayload(_PromptPayloadModel):
    fallgruppen_id: int
    fallgruppe_bezeichnung: str
    fallgruppe_beschreibung: str
    aenderungsstatus: str | None = None


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


def _project_normadressaten(
    row: dict,
    norm_addressee: str | None,
) -> list[str]:
    """Listet die Normadressaten, auf die eine Vorgabe zutrifft.

    Ist `norm_addressee` gesetzt (Run-Kontext), wird das Ergebnis auf genau
    diesen Adressaten projiziert - das LLM sieht dann nur die fuer den
    aktuellen Run relevante Angabe, keine Fremdadressaten aus anderen Laeufen.
    """
    all_addressees = [
        name
        for name, enabled in (
            (ADMINISTRATION, row.get("applies_to_administration")),
            (BUSINESS, row.get("applies_to_business")),
            (CITIZENS, row.get("applies_to_citizens")),
        )
        if enabled
    ]
    if norm_addressee is None:
        return all_addressees
    projected = [name for name in all_addressees if name == norm_addressee]
    # Falls upstream die Filterung bereits alle passenden Vorgaben geladen
    # hat, ist der Run-NA immer enthalten. Defensiv: wenn die Vorgabe doch
    # keinen Overlap hat (z.B. Daten-Inkonsistenz), behalten wir die
    # Originalliste, damit nicht stumm ein leeres Array ans LLM geht.
    return projected or all_addressees


def build_vorgaben_payload(
    regulations: list[dict],
    *,
    norm_addressee: str | None = None,
) -> list[dict]:
    payload: list[dict] = []
    for row in regulations:
        payload.append(
            VorgabePayload(
                vorgaben_id=int(row["regulation_id"]),
                normzitat=str(row.get("legal_citation") or ""),
                beschreibung=str(row.get("description") or ""),
                aenderungsstatus=row.get("change_status"),
                normadressaten=_project_normadressaten(row, norm_addressee),
                ist_informationspflicht_wirtschaft=bool(
                    row.get("is_business_information_obligation")
                ),
            ).model_dump()
        )
    return payload


def _serialize_process_regulations(
    regs_by_process: dict[int, list[dict]],
    process_id: int,
    norm_addressee: str | None = None,
) -> list[VorgabePayload]:
    return [
        VorgabePayload(
            vorgaben_id=int(row["regulation_id"]),
            normzitat=str(row.get("legal_citation") or ""),
            beschreibung=str(row.get("description") or ""),
            aenderungsstatus=row.get("change_status"),
            normadressaten=_project_normadressaten(row, norm_addressee),
            ist_informationspflicht_wirtschaft=bool(
                row.get("is_business_information_obligation")
            ),
        )
        for row in regs_by_process.get(process_id, [])
    ]


def build_case_groups_payload(
    processes: list[dict],
    case_groups: list[dict],
    regulations: list[dict] | None = None,
    *,
    norm_addressee: str | None = None,
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
            vorgaben=_serialize_process_regulations(
                regs_by_process, process_id, norm_addressee
            ),
            fallgruppen=groups_by_process.get(process_id, []),
        )
        payload.append(process_payload.model_dump())
    return payload


def build_processes_payload_with_regulations(
    processes: list[dict],
    regulations: list[dict],
    *,
    norm_addressee: str | None = None,
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
            vorgaben=_serialize_process_regulations(
                regs_by_process, process_id, norm_addressee
            ),
        )
        payload.append(process_payload.model_dump())
    return payload


def _order_steps(steps: list[dict]) -> list[dict]:
    step_map = {int(step["step_id"]): step for step in steps}
    steps_by_prev: dict[int | None, list[int]] = {}
    for step_id, step in step_map.items():
        steps_by_prev.setdefault(step.get("previous_id"), []).append(step_id)

    ordered: list[int] = []
    seen: set[int] = set()
    for start_id in steps_by_prev.get(None, []):
        current_id: int | None = start_id
        while current_id is not None and current_id not in seen:
            seen.add(current_id)
            ordered.append(current_id)
            next_id = step_map[current_id].get("next_id")
            current_id = int(next_id) if next_id is not None else None
    for step_id in sorted(step_map):
        if step_id not in seen:
            ordered.append(step_id)
    return [step_map[step_id] for step_id in ordered]


def build_step_analysis_payload(
    processes: list[dict],
    case_groups: list[dict],
    steps: list[dict],
    regulations: list[dict] | None = None,
    *,
    norm_addressee: str | None = None,
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
                    taetigkeiten=taetigkeiten,
                )
            )
        process_payload = ProzessStepAnalysisPayload(
            prozess_id=process_id,
            prozess_bezeichnung=str(process.get("process") or ""),
            prozess_beschreibung=str(process.get("description") or ""),
            aenderungsstatus=process.get("change_status"),
            vorgaben=_serialize_process_regulations(
                regs_by_process, process_id, norm_addressee
            ),
            fallgruppen=fallgruppen_payload,
        )
        payload.append(process_payload.model_dump())
    return payload


def build_step_analysis_output_skeleton(
    case_groups_payload: list[dict],
    *,
    norm_addressee: str,
) -> dict:
    fallgruppen = [
        {
            "fallgruppen_id": group["fallgruppen_id"],
            "taetigkeiten": [],
        }
        for process in case_groups_payload
        for group in process.get("fallgruppen", [])
    ]
    return {"normadressat": norm_addressee, "fallgruppen": fallgruppen}


_CASES_METRIC_KEYS = (
    "anzahl_betroffene_gueltig",
    "haeufigkeit_pro_jahr_gueltig",
    "anzahl_betroffene_vorschlag",
    "haeufigkeit_pro_jahr_vorschlag",
)


def build_cases_calculation_output_skeleton(
    case_groups_payload: list[dict],
    *,
    norm_addressee: str,
) -> dict:
    fallgruppen = [
        {
            "fallgruppen_id": group["fallgruppen_id"],
            "anzahl_betroffene_gueltig": "",
            "haeufigkeit_pro_jahr_gueltig": "",
            "anzahl_betroffene_vorschlag": "",
            "haeufigkeit_pro_jahr_vorschlag": "",
            "erklaerungen": {key: "" for key in _CASES_METRIC_KEYS},
            "confidence": {key: "" for key in _CASES_METRIC_KEYS},
        }
        for process in case_groups_payload
        for group in process.get("fallgruppen", [])
    ]
    return {"normadressat": norm_addressee, "fallgruppen": fallgruppen}


def _effort_taetigkeit_slots(norm_addressee: str) -> dict:
    if norm_addressee == CITIZENS:
        return {
            "zeitaufwand_in_min_gueltig": "",
            "sachaufwand_gueltig": "",
            "zeitaufwand_in_min_vorschlag": "",
            "sachaufwand_vorschlag": "",
        }
    return {
        "personalaufwand_gueltig": [
            {"qualifikation": "", "lohnquelle": "", "zeitaufwand_in_min": ""}
        ],
        "sachaufwand_gueltig": "",
        "personalaufwand_vorschlag": [
            {"qualifikation": "", "lohnquelle": "", "zeitaufwand_in_min": ""}
        ],
        "sachaufwand_vorschlag": "",
    }


def build_effort_calculation_output_skeleton(
    step_analysis_payload: list[dict],
    *,
    norm_addressee: str,
) -> dict:
    fallgruppen: list[dict] = []
    for process in step_analysis_payload:
        for group in process.get("fallgruppen", []):
            taetigkeiten = [
                {
                    "taetigkeiten_id": step["taetigkeiten_id"],
                    **_effort_taetigkeit_slots(norm_addressee),
                }
                for step in group.get("taetigkeiten", [])
            ]
            fallgruppen.append(
                {
                    "fallgruppen_id": group["fallgruppen_id"],
                    "taetigkeiten": taetigkeiten,
                }
            )
    return {"normadressat": norm_addressee, "fallgruppen": fallgruppen}


_CONFIDENCE_ENUM = ("high", "medium", "low")

_NULLABLE_NUMBER = {"type": ["number", "null"]}


def _strict_object(properties: dict[str, Any]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


def build_cases_calculation_output_schema(norm_addressee: str) -> dict:
    fallgruppe = _strict_object(
        {
            "fallgruppen_id": {"type": "integer"},
            "anzahl_betroffene_gueltig": _NULLABLE_NUMBER,
            "haeufigkeit_pro_jahr_gueltig": _NULLABLE_NUMBER,
            "anzahl_betroffene_vorschlag": _NULLABLE_NUMBER,
            "haeufigkeit_pro_jahr_vorschlag": _NULLABLE_NUMBER,
            "erklaerungen": _strict_object(
                {key: {"type": "string"} for key in _CASES_METRIC_KEYS}
            ),
            "confidence": _strict_object(
                {
                    key: {"type": "string", "enum": list(_CONFIDENCE_ENUM)}
                    for key in _CASES_METRIC_KEYS
                }
            ),
        }
    )
    return _strict_object(
        {
            "normadressat": {"type": "string", "enum": [norm_addressee]},
            "fallgruppen": {"type": "array", "items": fallgruppe},
        }
    )


def _effort_taetigkeit_schema(norm_addressee: str) -> dict:
    if norm_addressee == CITIZENS:
        return _strict_object(
            {
                "taetigkeiten_id": {"type": "integer"},
                "zeitaufwand_in_min_gueltig": _NULLABLE_NUMBER,
                "sachaufwand_gueltig": _NULLABLE_NUMBER,
                "zeitaufwand_in_min_vorschlag": _NULLABLE_NUMBER,
                "sachaufwand_vorschlag": _NULLABLE_NUMBER,
            }
        )
    personalaufwand_item = _strict_object(
        {
            "qualifikation": {"type": "string"},
            "lohnquelle": {"type": "string"},
            "zeitaufwand_in_min": _NULLABLE_NUMBER,
        }
    )
    return _strict_object(
        {
            "taetigkeiten_id": {"type": "integer"},
            "personalaufwand_gueltig": {"type": "array", "items": personalaufwand_item},
            "sachaufwand_gueltig": _NULLABLE_NUMBER,
            "personalaufwand_vorschlag": {
                "type": "array",
                "items": personalaufwand_item,
            },
            "sachaufwand_vorschlag": _NULLABLE_NUMBER,
        }
    )


def build_effort_calculation_output_schema(norm_addressee: str) -> dict:
    fallgruppe = _strict_object(
        {
            "fallgruppen_id": {"type": "integer"},
            "taetigkeiten": {
                "type": "array",
                "items": _effort_taetigkeit_schema(norm_addressee),
            },
        }
    )
    return _strict_object(
        {
            "normadressat": {"type": "string", "enum": [norm_addressee]},
            "fallgruppen": {"type": "array", "items": fallgruppe},
        }
    )
