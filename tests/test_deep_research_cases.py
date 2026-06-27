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
      "prozesse": [
        {
          "normadressat": "business",
          "prozess_id": 10,
          "fallgruppen": [
            {
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
      ]
    }
    """

    data, parsed = parse_deep_research_case_metrics(payload)

    assert data["prozesse"][0]["prozess_id"] == 10
    assert len(parsed) == 1
    entry = parsed[0]
    assert entry.norm_addressee == "business"
    assert entry.process_id == 10
    assert entry.case_group_id == 81
    assert entry.addressees_current == 500
    assert entry.annual_frequency_proposed == 2
    assert entry.metadata["fallzahl_vorschlag"] == 1040
    assert entry.metadata["confidence"]["haeufigkeit_pro_jahr_vorschlag"] == "low"
    assert "destatis.de" in entry.metadata["erklaerungen"]["anzahl_betroffene_gueltig"]


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
    assert "Duplicate Deep Research fallgruppen_id values" in exc_info.value.detail
    assert str(case_group_id) in exc_info.value.detail
