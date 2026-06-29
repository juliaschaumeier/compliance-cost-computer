"""
Regression-Guards fuer die JSON-Robustheit auf Router-Ebene
(_parse_processes, _parse_case_groups).

Vertrag: Beide Parser verlangen ueber require_json_object den Top-Level-
Schluessel `prozesse`. Damit liefern sowohl kaputte JSON-Outputs als auch
wohlgeformtes JSON ohne `prozesse` (z.B. ein geborgenes inneres Fragment)
einen klar identifizierbaren 422 mit error_context-Message. Nur ein
explizites `{"prozesse": []}` gilt als gueltige Leer-Antwort.
"""
import pytest
from fastapi import HTTPException

from backend.routers.case_groups import _parse_case_groups
from backend.routers.processes import _parse_processes


# ---------------------------------------------------------------------------
# _parse_processes
# ---------------------------------------------------------------------------


def test_parse_processes_raises_422_for_wellformed_json_without_prozesse_key():
    """Wohlgeformtes JSON ohne 'prozesse' -> harter 422 (Envelope-Pflicht)."""
    with pytest.raises(HTTPException) as excinfo:
        _parse_processes('{"foo": "bar"}')
    assert excinfo.value.status_code == 422
    assert "process compilation" in str(excinfo.value.detail).lower()


def test_parse_processes_returns_empty_for_explicit_empty_list():
    parsed, _fallbacks = _parse_processes('{"prozesse": []}')
    assert parsed == []


@pytest.mark.parametrize(
    "garbage",
    ["", "   ", "kein json hier", "{ unbalanced", "[1, 2, 3]"],
)
def test_parse_processes_raises_422_for_garbage(garbage):
    with pytest.raises(HTTPException) as excinfo:
        _parse_processes(garbage)
    assert excinfo.value.status_code == 422
    assert "process compilation" in str(excinfo.value.detail).lower()


def test_parse_processes_extracts_minimal_valid_entry():
    payload = """
    {
      "prozesse": [
        {
          "prozess_bezeichnung": "Antragstellung",
          "prozess_beschreibung": "Buerger stellt Antrag",
          "vorgaben": []
        }
      ]
    }
    """
    parsed, _fallbacks = _parse_processes(payload)
    assert len(parsed) == 1
    assert parsed[0]["prozess_bezeichnung"] == "Antragstellung"


# ---------------------------------------------------------------------------
# _parse_case_groups
# ---------------------------------------------------------------------------


def test_parse_case_groups_raises_422_for_wellformed_json_without_prozesse_key():
    """Wohlgeformtes JSON ohne 'prozesse' -> harter 422 (Envelope-Pflicht)."""
    with pytest.raises(HTTPException) as excinfo:
        _parse_case_groups('{"foo": "bar"}')
    assert excinfo.value.status_code == 422
    assert "case group development" in str(excinfo.value.detail).lower()


@pytest.mark.parametrize(
    "garbage",
    ["", "kein json", "{ unbalanced", "null"],
)
def test_parse_case_groups_raises_422_for_garbage(garbage):
    with pytest.raises(HTTPException) as excinfo:
        _parse_case_groups(garbage)
    assert excinfo.value.status_code == 422
    assert "case group development" in str(excinfo.value.detail).lower()


