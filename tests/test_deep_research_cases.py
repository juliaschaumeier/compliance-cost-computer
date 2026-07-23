import pytest
from fastapi import HTTPException

from backend.core import db
from backend.core.deep_research_cases import (
    apply_deep_research_case_metrics,
    parse_deep_research_case_metrics,
)


def test_parse_deep_research_case_metrics_preserves_field_evidence():
    payload = """
    Berichtstext.

    {
      "session": {"session_id": 1, "app_session_id": "DRTEST"},
      "fallgruppen": [
        {
          "normadressat": "business",
          "fallgruppen_id": 81,
          "anzahl_betroffene_gueltig": 500,
          "haeufigkeit_pro_jahr_gueltig": 1,
          "fallzahl_gueltig": 500,
          "anzahl_betroffene_vorschlag": 520,
          "haeufigkeit_pro_jahr_vorschlag": 2,
          "fallzahl_vorschlag": 1040,
          "erklaerungen": {
            "anzahl_betroffene_gueltig": "500 Unternehmen laut Quelle https://destatis.de/.",
            "haeufigkeit_pro_jahr_gueltig": "Ein Antrag pro Jahr.",
            "anzahl_betroffene_vorschlag": "520 Unternehmen wegen erweitertem Kreis.",
            "haeufigkeit_pro_jahr_vorschlag": "Zwei Meldungen pro Jahr."
          },
          "confidence": {
            "anzahl_betroffene_gueltig": "high",
            "haeufigkeit_pro_jahr_gueltig": "medium",
            "anzahl_betroffene_vorschlag": "medium",
            "haeufigkeit_pro_jahr_vorschlag": "low"
          },
          "quellen": ["https://www.destatis.de/DE/Home/_inhalt.html"]
        }
      ]
    }
    """

    data, parsed = parse_deep_research_case_metrics(payload)

    assert data["fallgruppen"][0]["fallgruppen_id"] == 81
    assert len(parsed) == 1
    entry = parsed[0]
    assert entry.norm_addressee == "business"
    assert entry.process_id is None
    assert entry.case_group_id == 81
    assert entry.addressees_current == 500
    assert entry.annual_frequency_proposed == 2
    assert entry.metadata["fallzahl_vorschlag"] == 1040
    assert entry.metadata["confidence"]["haeufigkeit_pro_jahr_vorschlag"] == "low"
    assert "destatis.de" in entry.metadata["erklaerungen"]["anzahl_betroffene_gueltig"]


def test_parse_deep_research_case_metrics_keeps_legacy_nested_payload():
    payload = """
    {
      "prozesse": [
        {
          "normadressat": "business",
          "prozess_id": 10,
          "fallgruppen": [
            {
              "fallgruppen_id": 81,
              "anzahl_betroffene_gueltig": 500,
              "haeufigkeit_pro_jahr_gueltig": 1
            }
          ]
        }
      ]
    }
    """

    data, parsed = parse_deep_research_case_metrics(payload)

    assert data["prozesse"][0]["prozess_id"] == 10
    assert len(parsed) == 1
    assert parsed[0].norm_addressee == "business"
    assert parsed[0].process_id == 10
    assert parsed[0].case_group_id == 81


def test_apply_deep_research_flat_payload_uses_db_process_assignment(test_client):
    session_id, _ = db.upsert_session("DR-FLAT", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung")
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung",
        norm_addressee="administration",
    )
    report_text = f"""
    {{
      "fallgruppen": [
        {{
          "normadressat": "administration",
          "fallgruppen_id": {case_group_id},
          "anzahl_betroffene_gueltig": 100,
          "haeufigkeit_pro_jahr_gueltig": 1,
          "anzahl_betroffene_vorschlag": 120,
          "haeufigkeit_pro_jahr_vorschlag": 1
        }}
      ]
    }}
    """

    assert apply_deep_research_case_metrics(
        session_id=session_id,
        report_text=report_text,
    ) == 1

    metrics = next(
        group
        for group in db.list_case_groups_for_session_and_addressee(
            session_id,
            "administration",
        )
        if int(group["case_group_id"]) == case_group_id
    )
    assert metrics["addressees_current"] == 100
    assert metrics["addressees_proposed"] == 120


def test_apply_deep_research_rejects_duplicate_fallgruppen_id(test_client):
    # Symmetrisch zum Hauptpfad (effort.py): dieselbe fallgruppen_id zweimal in der
    # Deep-Research-Antwort -> 422 statt stillem last-write-wins-Ueberschreiben.
    session_id, _ = db.upsert_session("DR-DUP", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung"
    )

    report_text = f"""
    {{
      "prozesse": [
        {{
          "normadressat": "administration",
          "prozess_id": {process_id},
          "fallgruppen": [
            {{
              "fallgruppen_id": {case_group_id},
              "anzahl_betroffene_gueltig": 100,
              "haeufigkeit_pro_jahr_gueltig": 1
            }},
            {{
              "fallgruppen_id": {case_group_id},
              "anzahl_betroffene_gueltig": 120,
              "haeufigkeit_pro_jahr_gueltig": 1
            }}
          ]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        apply_deep_research_case_metrics(session_id=session_id, report_text=report_text)
    assert exc_info.value.status_code == 422
    assert "doppelte fallgruppen_id-Werte" in exc_info.value.detail
    assert str(case_group_id) in exc_info.value.detail


def test_apply_deep_research_rejects_omitted_flat_fallgruppe(test_client):
    session_id, _ = db.upsert_session("DR-OMIT", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung")
    first_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung",
        norm_addressee="business",
    )
    second_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe B",
        "Beschreibung",
        norm_addressee="business",
    )
    report_text = f"""
    {{
      "fallgruppen": [
        {{
          "normadressat": "business",
          "fallgruppen_id": {first_id},
          "anzahl_betroffene_gueltig": 100,
          "haeufigkeit_pro_jahr_gueltig": 1
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        apply_deep_research_case_metrics(session_id=session_id, report_text=report_text)

    assert exc_info.value.status_code == 422
    assert "lassen fallgruppen_id-Werte aus" in exc_info.value.detail
    assert f"business:{second_id}" in exc_info.value.detail


def test_apply_deep_research_rejects_unknown_flat_fallgruppe(test_client):
    session_id, _ = db.upsert_session("DR-UNKNOWN", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung")
    db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung",
        norm_addressee="business",
    )
    report_text = """
    {
      "fallgruppen": [
        {
          "normadressat": "business",
          "fallgruppen_id": 999999,
          "anzahl_betroffene_gueltig": 100,
          "haeufigkeit_pro_jahr_gueltig": 1
        }
      ]
    }
    """

    with pytest.raises(HTTPException) as exc_info:
        apply_deep_research_case_metrics(session_id=session_id, report_text=report_text)

    assert exc_info.value.status_code == 422
    assert "unbekannte fallgruppen_id-Werte" in exc_info.value.detail
    assert "business:999999" in exc_info.value.detail


def test_parse_deep_research_rejects_malformed_envelope_with_dr_wording():
    with pytest.raises(HTTPException) as exc_info:
        parse_deep_research_case_metrics('{"session": {"session_id": 1}}')

    assert exc_info.value.status_code == 422
    assert "Deep-Research-Fallzahlen" in exc_info.value.detail
    assert "erwartet wurde ein JSON-Objekt mit Array `fallgruppen`" in exc_info.value.detail
