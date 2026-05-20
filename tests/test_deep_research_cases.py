from backend.core.deep_research_cases import parse_deep_research_case_metrics


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
