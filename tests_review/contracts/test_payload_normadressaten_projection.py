"""
Regression-Guard fuer Review-Befund "VorgabePayload.normadressaten ungefiltert".

Bisher sah der LLM-Prompt einer Vorgabe immer alle Normadressaten, auf die
die Vorgabe zutrifft - auch Fremdadressaten aus anderen Laeufen. Z.B. bei
einem Business-Run wurden 'administration' und 'citizens' ebenfalls im
normadressaten-Array mitgegeben, obwohl das fuer die Prozess-Buendelung
irrelevant ist.

Jetzt: build_*-Funktionen akzeptieren optional `norm_addressee=...` und
projizieren die Liste auf genau diesen Adressaten. Ohne Parameter bleibt
das Verhalten identisch (Abwaertskompatibilitaet).
"""
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.payload_builders import (
    build_case_groups_payload,
    build_processes_payload_with_regulations,
    build_step_analysis_payload,
    build_vorgaben_payload,
)


def _multi_na_regulation():
    return {
        "regulation_id": 1,
        "legal_citation": "§1",
        "description": "Multi-NA",
        "change_status": "eingefuehrt",
        "applies_to_administration": 1,
        "applies_to_business": 1,
        "applies_to_citizens": 0,
        "is_business_information_obligation": 0,
        "process_id": 10,
    }


def test_build_vorgaben_payload_without_filter_keeps_all_addressees():
    payload = build_vorgaben_payload([_multi_na_regulation()])
    assert sorted(payload[0]["normadressaten"]) == sorted([ADMINISTRATION, BUSINESS])


def test_build_vorgaben_payload_projects_onto_business():
    payload = build_vorgaben_payload([_multi_na_regulation()], norm_addressee=BUSINESS)
    assert payload[0]["normadressaten"] == [BUSINESS]


def test_build_vorgaben_payload_projects_onto_administration():
    payload = build_vorgaben_payload(
        [_multi_na_regulation()], norm_addressee=ADMINISTRATION
    )
    assert payload[0]["normadressaten"] == [ADMINISTRATION]


def test_build_processes_payload_projects_regulations():
    processes = [{"process_id": 10, "process": "P", "description": "d"}]
    payload = build_processes_payload_with_regulations(
        processes, [_multi_na_regulation()], norm_addressee=BUSINESS
    )
    assert payload[0]["vorgaben"][0]["normadressaten"] == [BUSINESS]


def test_build_case_groups_payload_projects_regulations():
    processes = [{"process_id": 10, "process": "P", "description": "d"}]
    payload = build_case_groups_payload(
        processes=processes,
        case_groups=[],
        regulations=[_multi_na_regulation()],
        norm_addressee=BUSINESS,
    )
    assert payload[0]["vorgaben"][0]["normadressaten"] == [BUSINESS]


def test_build_step_analysis_payload_projects_regulations():
    processes = [{"process_id": 10, "process": "P", "description": "d"}]
    payload = build_step_analysis_payload(
        processes=processes,
        case_groups=[],
        steps=[],
        regulations=[_multi_na_regulation()],
        norm_addressee=BUSINESS,
    )
    assert payload[0]["vorgaben"][0]["normadressaten"] == [BUSINESS]


def test_projection_fallback_when_no_overlap():
    # Defensive Edge-Case: Vorgabe gehoert nicht zum Run-NA. Upstream haette
    # das filtern sollen; Builder faengt es trotzdem ab, damit nicht stumm
    # ein leeres Array ans LLM geht.
    reg = _multi_na_regulation()
    reg["applies_to_business"] = 0  # Nur Admin
    payload = build_vorgaben_payload([reg], norm_addressee=CITIZENS)
    # Kein Overlap -> faellt auf Originalliste zurueck
    assert payload[0]["normadressaten"] == [ADMINISTRATION]
