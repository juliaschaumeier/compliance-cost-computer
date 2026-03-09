from backend.core.payload_builders import (
    build_case_groups_payload,
    build_processes_payload_with_regulations,
    build_step_analysis_payload,
    build_vorgaben_payload,
)


def test_build_vorgaben_payload_contract_keys():
    regulations = [
        {
            "regulation_id": 30,
            "process_id": 10,
            "legal_citation": "§ 1",
            "description": "Vorgabe A",
            "change_status": "geaendert",
        }
    ]

    payload = build_vorgaben_payload(regulations)

    assert payload == [
        {
            "vorgaben_id": 30,
            "normzitat": "§ 1",
            "beschreibung": "Vorgabe A",
            "aenderungsstatus": "geaendert",
        }
    ]
    assert set(payload[0].keys()) == {
        "vorgaben_id",
        "normzitat",
        "beschreibung",
        "aenderungsstatus",
    }


def test_build_processes_payload_with_regulations_contract_keys():
    processes = [
        {
            "process_id": 10,
            "process": "Prozess A",
            "description": "Beschreibung A",
            "change_status": "geaendert",
        }
    ]
    regulations = [
        {
            "regulation_id": 30,
            "process_id": 10,
            "legal_citation": "§ 1",
            "description": "Vorgabe A",
            "change_status": "geaendert",
        }
    ]

    payload = build_processes_payload_with_regulations(processes, regulations)
    process = payload[0]

    assert set(process.keys()) == {
        "prozess_id",
        "prozess_bezeichnung",
        "prozess_beschreibung",
        "aenderungsstatus",
        "vorgaben",
    }
    assert set(process["vorgaben"][0].keys()) == {
        "vorgaben_id",
        "normzitat",
        "beschreibung",
        "aenderungsstatus",
    }


def test_build_case_groups_payload_includes_vorgaben():
    processes = [
        {
            "process_id": 10,
            "process": "Prozess A",
            "description": "Beschreibung A",
            "change_status": "geaendert",
        }
    ]
    case_groups = [
        {
            "case_group_id": 20,
            "process_id": 10,
            "case_group": "Fallgruppe A",
            "description": "Beschreibung Fallgruppe A",
            "change_status": "geaendert",
            "addressees_current": 1,
            "annual_frequency_current": 2,
            "addressees_proposed": 3,
            "annual_frequency_proposed": 4,
        }
    ]
    regulations = [
        {
            "regulation_id": 30,
            "process_id": 10,
            "legal_citation": "§ 1",
            "description": "Vorgabe A",
            "change_status": "geaendert",
        }
    ]

    payload = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        regulations=regulations,
    )

    process = payload[0]
    assert process["prozess_id"] == 10
    assert process["vorgaben"] == [
        {
            "vorgaben_id": 30,
            "normzitat": "§ 1",
            "beschreibung": "Vorgabe A",
            "aenderungsstatus": "geaendert",
        }
    ]
    assert set(process.keys()) == {
        "prozess_id",
        "prozess_bezeichnung",
        "prozess_beschreibung",
        "aenderungsstatus",
        "vorgaben",
        "fallgruppen",
    }
    assert set(process["fallgruppen"][0].keys()) == {
        "fallgruppen_id",
        "fallgruppe_bezeichnung",
        "fallgruppe_beschreibung",
        "aenderungsstatus",
    }


def test_build_step_analysis_payload_includes_vorgaben():
    processes = [
        {
            "process_id": 10,
            "process": "Prozess A",
            "description": "Beschreibung A",
            "change_status": "geaendert",
        }
    ]
    case_groups = [
        {
            "case_group_id": 20,
            "process_id": 10,
            "case_group": "Fallgruppe A",
            "description": "Beschreibung Fallgruppe A",
            "change_status": "geaendert",
        }
    ]
    steps = [
        {
            "step_id": 40,
            "case_group_id": 20,
            "step": "Schritt 1",
            "description": "Beschreibung Schritt 1",
            "change_status": "geaendert",
            "previous_id": None,
            "next_id": None,
        }
    ]
    regulations = [
        {
            "regulation_id": 30,
            "process_id": 10,
            "legal_citation": "§ 1",
            "description": "Vorgabe A",
            "change_status": "geaendert",
        }
    ]

    payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=regulations,
    )

    process = payload[0]
    assert process["prozess_id"] == 10
    assert process["vorgaben"] == [
        {
            "vorgaben_id": 30,
            "normzitat": "§ 1",
            "beschreibung": "Vorgabe A",
            "aenderungsstatus": "geaendert",
        }
    ]
    assert set(process.keys()) == {
        "prozess_id",
        "prozess_bezeichnung",
        "prozess_beschreibung",
        "aenderungsstatus",
        "vorgaben",
        "fallgruppen",
    }
    taetigkeit = process["fallgruppen"][0]["taetigkeiten"][0]
    assert taetigkeit["taetigkeiten_id"] == 40
    assert set(taetigkeit.keys()) == {
        "taetigkeiten_id",
        "taetigkeit",
        "beschreibung",
        "aenderungsstatus",
    }


def test_build_case_groups_payload_omits_null_metrics():
    processes = [
        {
            "process_id": 10,
            "process": "Prozess A",
            "description": "Beschreibung A",
            "change_status": "geaendert",
        }
    ]
    case_groups = [
        {
            "case_group_id": 20,
            "process_id": 10,
            "case_group": "Fallgruppe A",
            "description": "Beschreibung Fallgruppe A",
            "change_status": "geaendert",
            "addressees_current": None,
            "annual_frequency_current": None,
            "addressees_proposed": None,
            "annual_frequency_proposed": None,
        }
    ]

    payload = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        regulations=[],
    )

    fallgruppe = payload[0]["fallgruppen"][0]
    assert "anzahl_betroffene_gueltig" not in fallgruppe
    assert "haeufigkeit_pro_jahr_gueltig" not in fallgruppe
    assert "anzahl_betroffene_vorschlag" not in fallgruppe
    assert "haeufigkeit_pro_jahr_vorschlag" not in fallgruppe


def test_build_case_groups_payload_omits_metrics_even_when_present():
    processes = [
        {
            "process_id": 10,
            "process": "Prozess A",
            "description": "Beschreibung A",
            "change_status": "geaendert",
        }
    ]
    case_groups = [
        {
            "case_group_id": 20,
            "process_id": 10,
            "case_group": "Fallgruppe A",
            "description": "Beschreibung Fallgruppe A",
            "change_status": "geaendert",
            "addressees_current": 100,
            "annual_frequency_current": 2,
            "addressees_proposed": 120,
            "annual_frequency_proposed": 3,
        }
    ]

    payload = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        regulations=[],
    )

    fallgruppe = payload[0]["fallgruppen"][0]
    assert "anzahl_betroffene_gueltig" not in fallgruppe
    assert "haeufigkeit_pro_jahr_gueltig" not in fallgruppe
    assert "anzahl_betroffene_vorschlag" not in fallgruppe
    assert "haeufigkeit_pro_jahr_vorschlag" not in fallgruppe


def test_build_step_analysis_payload_omits_null_effort_fields():
    processes = [
        {
            "process_id": 10,
            "process": "Prozess A",
            "description": "Beschreibung A",
            "change_status": "geaendert",
        }
    ]
    case_groups = [
        {
            "case_group_id": 20,
            "process_id": 10,
            "case_group": "Fallgruppe A",
            "description": "Beschreibung Fallgruppe A",
            "change_status": "geaendert",
        }
    ]
    steps = [
        {
            "step_id": 40,
            "case_group_id": 20,
            "step": "Schritt 1",
            "description": "Beschreibung Schritt 1",
            "change_status": "geaendert",
            "previous_id": None,
            "next_id": None,
            "hourly_rate_a_current": None,
            "hourly_rate_b_current": None,
            "hourly_rate_c_current": None,
            "hourly_rate_d_current": None,
            "time_required_in_min_a_current": None,
            "time_required_in_min_b_current": None,
            "time_required_in_min_c_current": None,
            "time_required_in_min_d_current": None,
            "expenses_current": None,
            "hourly_rate_a_proposed": None,
            "hourly_rate_b_proposed": None,
            "hourly_rate_c_proposed": None,
            "hourly_rate_d_proposed": None,
            "time_required_in_min_a_proposed": None,
            "time_required_in_min_b_proposed": None,
            "time_required_in_min_c_proposed": None,
            "time_required_in_min_d_proposed": None,
            "expenses_proposed": None,
            "execution_per_case": None,
        }
    ]

    payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=[],
    )

    taetigkeit = payload[0]["fallgruppen"][0]["taetigkeiten"][0]
    assert taetigkeit["taetigkeiten_id"] == 40
    assert taetigkeit["taetigkeit"] == "Schritt 1"
    assert "stundenlohn_satz_a_gueltig" not in taetigkeit
    assert "stundenlohn_satz_b_gueltig" not in taetigkeit
    assert "stundenlohn_satz_c_gueltig" not in taetigkeit
    assert "stundenlohn_satz_d_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_a_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_b_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_c_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_d_gueltig" not in taetigkeit
    assert "sachaufwand_gueltig" not in taetigkeit
    assert "stundenlohn_satz_a_vorschlag" not in taetigkeit
    assert "stundenlohn_satz_b_vorschlag" not in taetigkeit
    assert "stundenlohn_satz_c_vorschlag" not in taetigkeit
    assert "stundenlohn_satz_d_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_a_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_b_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_c_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_d_vorschlag" not in taetigkeit
    assert "sachaufwand_vorschlag" not in taetigkeit
    assert "ausfuehrung_pro_einzelfall" not in taetigkeit


def test_build_step_analysis_payload_omits_effort_fields_even_when_present():
    processes = [
        {
            "process_id": 10,
            "process": "Prozess A",
            "description": "Beschreibung A",
            "change_status": "geaendert",
        }
    ]
    case_groups = [
        {
            "case_group_id": 20,
            "process_id": 10,
            "case_group": "Fallgruppe A",
            "description": "Beschreibung Fallgruppe A",
            "change_status": "geaendert",
        }
    ]
    steps = [
        {
            "step_id": 40,
            "case_group_id": 20,
            "step": "Schritt 1",
            "description": "Beschreibung Schritt 1",
            "change_status": "geaendert",
            "previous_id": None,
            "next_id": None,
            "hourly_rate_a_current": 10,
            "hourly_rate_b_current": 11,
            "hourly_rate_c_current": 12,
            "hourly_rate_d_current": 13,
            "time_required_in_min_a_current": 1,
            "time_required_in_min_b_current": 2,
            "time_required_in_min_c_current": 3,
            "time_required_in_min_d_current": 4,
            "expenses_current": 5,
            "hourly_rate_a_proposed": 20,
            "hourly_rate_b_proposed": 21,
            "hourly_rate_c_proposed": 22,
            "hourly_rate_d_proposed": 23,
            "time_required_in_min_a_proposed": 6,
            "time_required_in_min_b_proposed": 7,
            "time_required_in_min_c_proposed": 8,
            "time_required_in_min_d_proposed": 9,
            "expenses_proposed": 10,
            "execution_per_case": 1,
        }
    ]

    payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=[],
    )

    taetigkeit = payload[0]["fallgruppen"][0]["taetigkeiten"][0]
    assert taetigkeit["taetigkeiten_id"] == 40
    assert taetigkeit["taetigkeit"] == "Schritt 1"
    assert "stundenlohn_satz_a_gueltig" not in taetigkeit
    assert "stundenlohn_satz_b_gueltig" not in taetigkeit
    assert "stundenlohn_satz_c_gueltig" not in taetigkeit
    assert "stundenlohn_satz_d_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_a_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_b_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_c_gueltig" not in taetigkeit
    assert "zeitaufwand_in_min_d_gueltig" not in taetigkeit
    assert "sachaufwand_gueltig" not in taetigkeit
    assert "stundenlohn_satz_a_vorschlag" not in taetigkeit
    assert "stundenlohn_satz_b_vorschlag" not in taetigkeit
    assert "stundenlohn_satz_c_vorschlag" not in taetigkeit
    assert "stundenlohn_satz_d_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_a_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_b_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_c_vorschlag" not in taetigkeit
    assert "zeitaufwand_in_min_d_vorschlag" not in taetigkeit
    assert "sachaufwand_vorschlag" not in taetigkeit
    assert "ausfuehrung_pro_einzelfall" not in taetigkeit
