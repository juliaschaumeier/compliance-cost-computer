from backend.core import deep_research_cases_prompt as prompt_builder


def test_build_deep_research_cases_prompt_combines_addressees(monkeypatch):
    session = {
        "session_id": 123,
        "app_session_id": "PROMPT1",
        "law_diff_title": "Testtitel",
        "law_diff_blurb": "Kurzhinweis",
        "law_diff_summary": "Zusammenfassung",
    }
    regulations = [
        {
            "regulation_id": 1,
            "legal_citation": "§ 1 TestG",
            "description": "Testvorgabe",
            "process_id": 10,
            "change_status": "geaendert",
            "applies_to_administration": 1,
            "applies_to_business": 1,
            "applies_to_citizens": 0,
            "is_business_information_obligation": 0,
        }
    ]
    processes_by_addressee = {
        "administration": [
            {
                "process_id": 10,
                "process": "Antraege pruefen",
                "description": "Verwaltung prueft Antraege.",
                "change_status": "geaendert",
            }
        ],
        "business": [
            {
                "process_id": 20,
                "process": "Antrag stellen",
                "description": "Unternehmen stellen Antraege.",
                "change_status": "geaendert",
            }
        ],
        "citizens": [],
    }
    case_groups_by_addressee = {
        "administration": [
            {
                "case_group_id": 100,
                "process_id": 10,
                "case_group": "Standardpruefung",
                "description": "Standardisierte Bearbeitung.",
                "change_status": "geaendert",
            }
        ],
        "business": [
            {
                "case_group_id": 200,
                "process_id": 20,
                "case_group": "Standardantrag",
                "description": "Standardisierte Antragstellung.",
                "change_status": "geaendert",
            }
        ],
        "citizens": [],
    }

    monkeypatch.setattr(
        prompt_builder.db,
        "get_session_by_app_id",
        lambda app_session_id: session if app_session_id == "PROMPT1" else None,
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "get_session_law_texts",
        lambda session_id: ("Geltendes Recht", "Vorgeschlagenes Recht"),
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_regulations_for_session",
        lambda session_id: regulations,
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_regulations_for_session_and_addressee",
        lambda session_id, norm_addressee: regulations,
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_processes_for_session_and_addressee",
        lambda session_id, norm_addressee: processes_by_addressee[norm_addressee],
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_case_groups_for_session_and_addressee",
        lambda session_id, norm_addressee: case_groups_by_addressee[norm_addressee],
    )

    prompt = prompt_builder.build_deep_research_cases_prompt(app_session_id="PROMPT1")

    assert "ein konsistentes Mengenbild ueber alle Normadressaten hinweg" in prompt
    # Recurring-only-Regel analog zu cases_calculation (#13/#25).
    assert (
        "Betrachten Sie ausschliesslich jaehrlich wiederkehrenden Erfuellungsaufwand"
        in prompt
    )
    assert "anzahl_betroffene_gueltig" in prompt
    assert "haeufigkeit_pro_jahr_vorschlag" in prompt
    assert "kurze Begruendung" in prompt
    assert "https://www.destatis.de/DE/Home/_inhalt.html" in prompt
    assert '"normadressat": "administration"' in prompt
    assert '"normadressat": "business"' in prompt
    assert '"normadressat": "citizens"' not in prompt
    assert '"fallgruppen_id": 100' in prompt
    assert '"fallgruppen_id": 200' in prompt
    assert "process_steps" not in prompt
    assert "taetigkeiten_id" not in prompt
    assert '"gesetz_gueltig"' not in prompt
    assert '"gesetz_vorschlag"' not in prompt

    prompt_with_laws = prompt_builder.build_deep_research_cases_prompt(
        app_session_id="PROMPT1",
        include_law_texts=True,
    )

    assert '"gesetz_gueltig": "Geltendes Recht"' in prompt_with_laws
    assert '"gesetz_vorschlag": "Vorgeschlagenes Recht"' in prompt_with_laws
