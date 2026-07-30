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
    # "einmalig" wurde bewusst aus der Diagnose-Frage entfernt (#13/#25).
    assert "periodisch, anlassbezogen oder bestandsbezogen" in prompt
    # Negativ-Guard gegen einmalige Vorgaenge als jaehrliche Fallzahl (#13/#25).
    assert (
        "Keine einmaligen Vorgaenge, die nur bei Einfuehrung der Regelung anfallen"
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
    assert "Prozess-ID" not in prompt
    assert "maschinenlesbare JSON-Block soll davon unabhaengig flach bleiben" in prompt
    assert "keine Prozesse, keine `prozess_id` und keine Prozessstruktur" in prompt
    assert '  "fallgruppen": [' in prompt
    assert '  "prozesse": [' not in prompt
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


def test_deep_research_cases_prompt_requires_exact_part_headings(monkeypatch):
    session = {
        "session_id": 123,
        "app_session_id": "PROMPT-HEADINGS",
        "law_diff_title": "Testtitel",
        "law_diff_blurb": "Kurzhinweis",
        "law_diff_summary": "Zusammenfassung",
    }

    monkeypatch.setattr(
        prompt_builder.db,
        "get_session_by_app_id",
        lambda app_session_id: session if app_session_id == "PROMPT-HEADINGS" else None,
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "get_session_law_texts",
        lambda session_id: ("Geltendes Recht", "Vorgeschlagenes Recht"),
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_regulations_for_session",
        lambda session_id: [],
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_regulations_for_session_and_addressee",
        lambda session_id, norm_addressee: [],
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_processes_for_session_and_addressee",
        lambda session_id, norm_addressee: [],
    )
    monkeypatch.setattr(
        prompt_builder.db,
        "list_case_groups_for_session_and_addressee",
        lambda session_id, norm_addressee: [],
    )

    prompt = prompt_builder.build_deep_research_cases_prompt(
        app_session_id="PROMPT-HEADINGS"
    )

    assert "## Teil 1: Vollstaendiger Forschungsbericht" in prompt
    assert "## Teil 2: Kurze Begruendungszeilen je Fallgruppe und Kennzahl" in prompt
    assert "## Teil 3: Tabellarische Kurzfassung und JSON-Block" in prompt
    assert "Benennen Sie diese Ueberschriften nicht um" in prompt
    assert "nummerierte Alternativen wie `1.` oder `I.`" in prompt
