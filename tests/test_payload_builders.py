from backend.core.payload_builders import (
    build_case_groups_payload,
    build_cases_calculation_output_skeleton,
    build_effort_calculation_output_skeleton,
    build_processes_payload_with_regulations,
    build_step_analysis_output_skeleton,
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
            "normadressaten": [],
            "ist_informationspflicht_wirtschaft": False,
        }
    ]
    assert set(payload[0].keys()) == {
        "vorgaben_id",
        "normzitat",
        "beschreibung",
        "aenderungsstatus",
        "normadressaten",
        "ist_informationspflicht_wirtschaft",
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
        "normadressaten",
        "ist_informationspflicht_wirtschaft",
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
            "normadressaten": [],
            "ist_informationspflicht_wirtschaft": False,
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
            "normadressaten": [],
            "ist_informationspflicht_wirtschaft": False,
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
        "vorgaben_ids",
    }
    assert taetigkeit["vorgaben_ids"] == []


def test_build_case_groups_payload_omits_metrics():
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


def test_build_vorgaben_payload_includes_norm_addressees_and_business_flag():
    regulations = [
        {
            "regulation_id": 31,
            "process_id": 10,
            "legal_citation": "§ 2",
            "description": "Vorgabe B",
            "change_status": "neu",
            "applies_to_administration": 1,
            "applies_to_business": 1,
            "applies_to_citizens": 0,
            "is_business_information_obligation": 1,
        }
    ]

    payload = build_vorgaben_payload(regulations)

    assert payload == [
        {
            "vorgaben_id": 31,
            "normzitat": "§ 2",
            "beschreibung": "Vorgabe B",
            "aenderungsstatus": "neu",
            "normadressaten": ["administration", "business"],
            "ist_informationspflicht_wirtschaft": True,
        }
    ]


def test_build_processes_payload_with_regulations_includes_norm_addressees_and_business_flag():
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
            "regulation_id": 31,
            "process_id": 10,
            "legal_citation": "§ 2",
            "description": "Vorgabe B",
            "change_status": "neu",
            "applies_to_administration": 1,
            "applies_to_business": 1,
            "applies_to_citizens": 0,
            "is_business_information_obligation": 1,
        }
    ]

    payload = build_processes_payload_with_regulations(processes, regulations)

    assert payload[0]["vorgaben"] == [
        {
            "vorgaben_id": 31,
            "normzitat": "§ 2",
            "beschreibung": "Vorgabe B",
            "aenderungsstatus": "neu",
            "normadressaten": ["administration", "business"],
            "ist_informationspflicht_wirtschaft": True,
        }
    ]


def test_build_case_groups_payload_preserves_norm_addressees_and_business_flag():
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
    regulations = [
        {
            "regulation_id": 31,
            "process_id": 10,
            "legal_citation": "§ 2",
            "description": "Vorgabe B",
            "change_status": "neu",
            "applies_to_administration": 1,
            "applies_to_business": 0,
            "applies_to_citizens": 1,
            "is_business_information_obligation": 0,
        }
    ]

    payload = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        regulations=regulations,
    )

    assert payload[0]["vorgaben"] == [
        {
            "vorgaben_id": 31,
            "normzitat": "§ 2",
            "beschreibung": "Vorgabe B",
            "aenderungsstatus": "neu",
            "normadressaten": ["administration", "citizens"],
            "ist_informationspflicht_wirtschaft": False,
        }
    ]


def test_build_step_analysis_payload_preserves_norm_addressees_and_business_flag():
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
            "regulation_id": 31,
            "process_id": 10,
            "legal_citation": "§ 2",
            "description": "Vorgabe B",
            "change_status": "neu",
            "applies_to_administration": 0,
            "applies_to_business": 1,
            "applies_to_citizens": 1,
            "is_business_information_obligation": 1,
        }
    ]

    payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=regulations,
    )

    assert payload[0]["vorgaben"] == [
        {
            "vorgaben_id": 31,
            "normzitat": "§ 2",
            "beschreibung": "Vorgabe B",
            "aenderungsstatus": "neu",
            "normadressaten": ["business", "citizens"],
            "ist_informationspflicht_wirtschaft": True,
        }
    ]


def test_build_vorgaben_payload_suppresses_business_flag_outside_business_run():
    regulations = [
        {
            "regulation_id": 31,
            "process_id": 10,
            "legal_citation": "§ 2",
            "description": "Vorgabe B",
            "change_status": "neu",
            "applies_to_administration": 0,
            "applies_to_business": 1,
            "applies_to_citizens": 1,
            "is_business_information_obligation": 1,
        }
    ]

    citizens_payload = build_vorgaben_payload(regulations, norm_addressee="citizens")
    business_payload = build_vorgaben_payload(regulations, norm_addressee="business")

    assert citizens_payload[0]["normadressaten"] == ["citizens"]
    assert citizens_payload[0]["ist_informationspflicht_wirtschaft"] is False
    assert business_payload[0]["normadressaten"] == ["business"]
    assert business_payload[0]["ist_informationspflicht_wirtschaft"] is True


def test_build_step_analysis_payload_suppresses_business_flag_outside_business_run():
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
            "regulation_id": 31,
            "process_id": 10,
            "legal_citation": "§ 2",
            "description": "Vorgabe B",
            "change_status": "neu",
            "applies_to_administration": 0,
            "applies_to_business": 1,
            "applies_to_citizens": 1,
            "is_business_information_obligation": 1,
        }
    ]

    payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=regulations,
        norm_addressee="citizens",
    )

    assert payload[0]["vorgaben"] == [
        {
            "vorgaben_id": 31,
            "normzitat": "§ 2",
            "beschreibung": "Vorgabe B",
            "aenderungsstatus": "neu",
            "normadressaten": ["citizens"],
            "ist_informationspflicht_wirtschaft": False,
        }
    ]


def test_build_step_analysis_payload_omits_effort_fields_when_present():
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
    assert taetigkeit["vorgaben_ids"] == []
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


def test_build_step_analysis_payload_keeps_all_steps_with_multiple_roots():
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
            "description": "",
            "change_status": "geaendert",
            "previous_id": None,
            "next_id": 41,
        },
        {
            "step_id": 41,
            "case_group_id": 20,
            "step": "Schritt 2",
            "description": "",
            "change_status": "geaendert",
            "previous_id": 40,
            "next_id": None,
        },
        {
            "step_id": 42,
            "case_group_id": 20,
            "step": "Schritt 3",
            "description": "",
            "change_status": "geaendert",
            "previous_id": None,
            "next_id": None,
        },
    ]

    payload = build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=[],
    )

    taetigkeiten = payload[0]["fallgruppen"][0]["taetigkeiten"]
    step_ids = [taetigkeit["taetigkeiten_id"] for taetigkeit in taetigkeiten]
    assert step_ids == [40, 41, 42]


def test_build_step_analysis_output_skeleton_is_flat_ids_only():
    # #64 (Option 4): flaches Skelett - alle Fallgruppen zweier Prozesse liegen
    # ohne Prozess-Ebene flach nebeneinander; vorbefuellt nur die IDs, laesst
    # `taetigkeiten` leer; kein deskriptives Feld darf durchsickern.
    processes = [
        {"process_id": 312, "process": "Prozess 312", "description": "d", "change_status": "geaendert"},
        {"process_id": 313, "process": "Prozess 313", "description": "d", "change_status": "geaendert"},
    ]
    case_groups = [
        {"case_group_id": 491, "process_id": 312, "case_group": "F491", "description": "d", "change_status": "geaendert"},
        {"case_group_id": 492, "process_id": 313, "case_group": "F492", "description": "d", "change_status": "geaendert"},
    ]
    payload_groups = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        norm_addressee="business",
    )

    skeleton = build_step_analysis_output_skeleton(payload_groups, norm_addressee="business")

    assert skeleton == {
        "normadressat": "business",
        "fallgruppen": [
            {"fallgruppen_id": 491, "taetigkeiten": []},
            {"fallgruppen_id": 492, "taetigkeiten": []},
        ],
    }
    assert set(skeleton.keys()) == {"normadressat", "fallgruppen"}
    fallgruppen_ids = [group["fallgruppen_id"] for group in skeleton["fallgruppen"]]
    assert fallgruppen_ids == [491, 492]
    assert len(fallgruppen_ids) == len(set(fallgruppen_ids))
    for group in skeleton["fallgruppen"]:
        assert set(group.keys()) == {"fallgruppen_id", "taetigkeiten"}


def test_build_cases_calculation_output_skeleton_is_flat_prefilled():
    # #64 (Option 4, Schritt 6): flaches Skelett - alle Fallgruppen zweier Prozesse
    # flach nebeneinander, vorbefuellt mit `fallgruppen_id` + leeren Kennzahlen-Slots
    # (inkl. erklaerungen/confidence); das Modell fuellt nur Werte.
    processes = [
        {"process_id": 312, "process": "Prozess 312", "description": "d", "change_status": "geaendert"},
        {"process_id": 313, "process": "Prozess 313", "description": "d", "change_status": "geaendert"},
    ]
    case_groups = [
        {"case_group_id": 491, "process_id": 312, "case_group": "F491", "description": "d", "change_status": "geaendert"},
        {"case_group_id": 492, "process_id": 313, "case_group": "F492", "description": "d", "change_status": "geaendert"},
    ]
    payload_groups = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        norm_addressee="business",
    )

    skeleton = build_cases_calculation_output_skeleton(payload_groups, norm_addressee="business")

    assert set(skeleton.keys()) == {"normadressat", "fallgruppen"}
    assert skeleton["normadressat"] == "business"
    fallgruppen_ids = [group["fallgruppen_id"] for group in skeleton["fallgruppen"]]
    assert fallgruppen_ids == [491, 492]
    metric_keys = (
        "anzahl_betroffene_gueltig",
        "haeufigkeit_pro_jahr_gueltig",
        "anzahl_betroffene_vorschlag",
        "haeufigkeit_pro_jahr_vorschlag",
    )
    for group in skeleton["fallgruppen"]:
        assert set(group.keys()) == {
            "fallgruppen_id",
            *metric_keys,
            "erklaerungen",
            "confidence",
        }
        for key in metric_keys:
            assert group[key] == ""
        assert set(group["erklaerungen"].keys()) == set(metric_keys)
        assert set(group["confidence"].keys()) == set(metric_keys)


def _effort_skeleton_input():
    processes = [
        {"process_id": 10, "process": "Prozess 10", "description": "d", "change_status": "geaendert"},
    ]
    case_groups = [
        {"case_group_id": 20, "process_id": 10, "case_group": "F20", "description": "d", "change_status": "geaendert"},
    ]
    steps = [
        {"step_id": 40, "case_group_id": 20, "step": "Schritt 1", "description": "", "change_status": "geaendert", "previous_id": None, "next_id": 41},
        {"step_id": 41, "case_group_id": 20, "step": "Schritt 2", "description": "", "change_status": "geaendert", "previous_id": 40, "next_id": None},
    ]
    return build_step_analysis_payload(
        processes=processes,
        case_groups=case_groups,
        steps=steps,
        regulations=[],
    )


def test_build_effort_calculation_output_skeleton_org_is_flat_prefilled():
    payload = _effort_skeleton_input()

    skeleton = build_effort_calculation_output_skeleton(payload, norm_addressee="administration")

    assert set(skeleton.keys()) == {"normadressat", "fallgruppen"}
    assert skeleton["normadressat"] == "administration"
    assert [group["fallgruppen_id"] for group in skeleton["fallgruppen"]] == [20]
    taetigkeiten = skeleton["fallgruppen"][0]["taetigkeiten"]
    assert [t["taetigkeiten_id"] for t in taetigkeiten] == [40, 41]
    for taetigkeit in taetigkeiten:
        assert set(taetigkeit.keys()) == {
            "taetigkeiten_id",
            "personalaufwand_gueltig",
            "sachaufwand_gueltig",
            "personalaufwand_vorschlag",
            "sachaufwand_vorschlag",
        }
        assert taetigkeit["personalaufwand_gueltig"] == [
            {"qualifikation": "", "lohnquelle": "", "zeitaufwand_in_min": ""}
        ]
        assert taetigkeit["personalaufwand_vorschlag"] == [
            {"qualifikation": "", "lohnquelle": "", "zeitaufwand_in_min": ""}
        ]


def test_build_effort_calculation_output_skeleton_citizens_omits_wages():
    payload = _effort_skeleton_input()

    skeleton = build_effort_calculation_output_skeleton(payload, norm_addressee="citizens")

    taetigkeiten = skeleton["fallgruppen"][0]["taetigkeiten"]
    assert [t["taetigkeiten_id"] for t in taetigkeiten] == [40, 41]
    for taetigkeit in taetigkeiten:
        assert set(taetigkeit.keys()) == {
            "taetigkeiten_id",
            "zeitaufwand_in_min_gueltig",
            "sachaufwand_gueltig",
            "zeitaufwand_in_min_vorschlag",
            "sachaufwand_vorschlag",
        }
        assert "personalaufwand_gueltig" not in taetigkeit
