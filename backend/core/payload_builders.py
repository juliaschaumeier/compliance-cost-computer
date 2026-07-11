from __future__ import annotations

from dataclasses import dataclass
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
            **_CASES_FALLGRUPPE.to_slots(),
            "fallgruppen_id": group["fallgruppen_id"],
        }
        for process in case_groups_payload
        for group in process.get("fallgruppen", [])
    ]
    return {"normadressat": norm_addressee, "fallgruppen": fallgruppen}


def build_effort_calculation_output_skeleton(
    step_analysis_payload: list[dict],
    *,
    norm_addressee: str,
) -> dict:
    taetigkeit = _effort_taetigkeit(norm_addressee)
    fallgruppen: list[dict] = []
    for process in step_analysis_payload:
        for group in process.get("fallgruppen", []):
            taetigkeiten = [
                {
                    **taetigkeit.to_slots(),
                    "taetigkeiten_id": step["taetigkeiten_id"],
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


def _strict_object(properties: dict[str, Any]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


_EMPTY_SLOT = ""


class _Node:
    def to_schema(self) -> dict:
        raise NotImplementedError

    def to_slots(self) -> Any:
        return _EMPTY_SLOT


@dataclass(frozen=True)
class _Str(_Node):
    def to_schema(self) -> dict:
        return {"type": "string"}


@dataclass(frozen=True)
class _Int(_Node):
    def to_schema(self) -> dict:
        return {"type": "integer"}


@dataclass(frozen=True)
class _Num(_Node):
    def to_schema(self) -> dict:
        return {"type": ["number", "null"]}


@dataclass(frozen=True)
class _Enum(_Node):
    values: tuple[str, ...]

    def to_schema(self) -> dict:
        return {"type": "string", "enum": list(self.values)}


@dataclass(frozen=True)
class _Arr(_Node):
    item: _Node

    def to_schema(self) -> dict:
        return {"type": "array", "items": self.item.to_schema()}

    def to_slots(self) -> Any:
        return [self.item.to_slots()]


@dataclass(frozen=True)
class _Obj(_Node):
    properties: dict[str, _Node]

    def to_schema(self) -> dict:
        return _strict_object(
            {key: node.to_schema() for key, node in self.properties.items()}
        )

    def to_slots(self) -> Any:
        return {key: node.to_slots() for key, node in self.properties.items()}


_CHANGE_STATUS = _Enum(("eingefuehrt", "geaendert", "abgeschafft"))

_CHANGE_STATUS_WITH_UNCHANGED = _Enum(
    ("eingefuehrt", "geaendert", "abgeschafft", "unveraendert")
)


_STEP_ANALYSIS_TAETIGKEIT = _Obj(
    {
        "taetigkeit": _Str(),
        "beschreibung": _Str(),
        "aenderungsstatus": _CHANGE_STATUS_WITH_UNCHANGED,
    }
)


def _fallgruppen_envelope(norm_addressee: str, fallgruppe: _Node) -> _Obj:
    return _Obj(
        {
            "normadressat": _Enum((norm_addressee,)),
            "fallgruppen": _Arr(fallgruppe),
        }
    )


def _prozesse_envelope(norm_addressee: str, prozess: _Node) -> _Obj:
    return _Obj(
        {
            "normadressat": _Enum((norm_addressee,)),
            "prozesse": _Arr(prozess),
        }
    )


def build_step_analysis_output_schema(norm_addressee: str) -> dict:
    fallgruppe = _Obj(
        {
            "fallgruppen_id": _Int(),
            "taetigkeiten": _Arr(_STEP_ANALYSIS_TAETIGKEIT),
        }
    )
    return _fallgruppen_envelope(norm_addressee, fallgruppe).to_schema()


_VORGABE = _Obj(
    {
        "vorgaben_id": _Int(),
        "normzitat": _Str(),
        "beschreibung": _Str(),
        "aenderungsstatus": _CHANGE_STATUS,
    }
)

_CASE_GROUP_FALLGRUPPE = _Obj(
    {
        "fallgruppe_bezeichnung": _Str(),
        "fallgruppe_beschreibung": _Str(),
        "aenderungsstatus": _CHANGE_STATUS,
    }
)


def build_case_group_development_output_schema(norm_addressee: str) -> dict:
    prozess = _Obj(
        {
            "prozess_id": _Int(),
            "prozess_bezeichnung": _Str(),
            "prozess_beschreibung": _Str(),
            "aenderungsstatus": _CHANGE_STATUS,
            "vorgaben": _Arr(_VORGABE),
            "fallgruppen": _Arr(_CASE_GROUP_FALLGRUPPE),
        }
    )
    return _prozesse_envelope(norm_addressee, prozess).to_schema()


def build_process_compilation_output_schema(norm_addressee: str) -> dict:
    prozess = _Obj(
        {
            "prozess_bezeichnung": _Str(),
            "prozess_beschreibung": _Str(),
            "aenderungsstatus": _CHANGE_STATUS,
            "vorgaben": _Arr(_VORGABE),
        }
    )
    return _prozesse_envelope(norm_addressee, prozess).to_schema()


_CASES_FALLGRUPPE = _Obj(
    {
        "fallgruppen_id": _Int(),
        **{key: _Num() for key in _CASES_METRIC_KEYS},
        "erklaerungen": _Obj({key: _Str() for key in _CASES_METRIC_KEYS}),
        "confidence": _Obj({key: _Enum(_CONFIDENCE_ENUM) for key in _CASES_METRIC_KEYS}),
    }
)


def build_cases_calculation_output_schema(norm_addressee: str) -> dict:
    return _fallgruppen_envelope(norm_addressee, _CASES_FALLGRUPPE).to_schema()


def _effort_taetigkeit(norm_addressee: str) -> _Obj:
    if norm_addressee == CITIZENS:
        return _Obj(
            {
                "taetigkeiten_id": _Int(),
                "zeitaufwand_in_min_gueltig": _Num(),
                "sachaufwand_gueltig": _Num(),
                "zeitaufwand_in_min_vorschlag": _Num(),
                "sachaufwand_vorschlag": _Num(),
            }
        )
    personalaufwand = _Arr(
        _Obj(
            {
                "qualifikation": _Str(),
                "lohnquelle": _Str(),
                "zeitaufwand_in_min": _Num(),
            }
        )
    )
    return _Obj(
        {
            "taetigkeiten_id": _Int(),
            "personalaufwand_gueltig": personalaufwand,
            "sachaufwand_gueltig": _Num(),
            "personalaufwand_vorschlag": personalaufwand,
            "sachaufwand_vorschlag": _Num(),
        }
    )


def build_effort_calculation_output_schema(norm_addressee: str) -> dict:
    fallgruppe = _Obj(
        {
            "fallgruppen_id": _Int(),
            "taetigkeiten": _Arr(_effort_taetigkeit(norm_addressee)),
        }
    )
    return _fallgruppen_envelope(norm_addressee, fallgruppe).to_schema()
