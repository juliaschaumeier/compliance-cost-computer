"""Tests fuer die Validierung des normadressat-Echo-Felds.

Das LLM soll bei allen addressee-spezifischen Prompts den erwarteten
Normadressaten als top-level `normadressat` in der JSON-Antwort wiederholen.
Ein Mismatch (falscher Adressat) bricht den Flow hart mit 422 ab; ein
fehlendes Echo bleibt reine Soft-Telemetrie (parse_fallback) und bricht
den Flow NICHT ab.
"""
import pytest
from fastapi import HTTPException

from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
    NORM_ADDRESSEE_ECHO_MISMATCH,
    NORM_ADDRESSEE_ECHO_MISSING,
    check_norm_addressee_echo,
)
from backend.routers.case_groups import _parse_case_groups
from backend.routers.effort import _parse_cases_payload, _parse_effort_payload
from backend.routers.process_steps import _parse_process_steps
from backend.routers.processes import _parse_processes


# ---------------------------------------------------------------------------
# check_norm_addressee_echo helper
# ---------------------------------------------------------------------------


def test_echo_matches_returns_empty_set():
    assert check_norm_addressee_echo({"normadressat": "business"}, BUSINESS) == set()


def test_echo_mismatch_returns_mismatch_kind():
    assert check_norm_addressee_echo(
        {"normadressat": "administration"}, BUSINESS
    ) == {NORM_ADDRESSEE_ECHO_MISMATCH}


def test_echo_missing_returns_missing_kind():
    assert check_norm_addressee_echo({"prozesse": []}, BUSINESS) == {
        NORM_ADDRESSEE_ECHO_MISSING
    }


def test_echo_empty_string_returns_missing_kind():
    assert check_norm_addressee_echo({"normadressat": "  "}, BUSINESS) == {
        NORM_ADDRESSEE_ECHO_MISSING
    }


def test_echo_is_case_insensitive():
    assert check_norm_addressee_echo({"normadressat": "BUSINESS"}, BUSINESS) == set()


def test_echo_skipped_when_expected_is_none():
    # Rueckwaertskompatibilitaet: alte Aufrufe ohne NA erzeugen keine Fallbacks.
    assert check_norm_addressee_echo({"normadressat": "foo"}, None) == set()


# ---------------------------------------------------------------------------
# _parse_processes (process_compilation)
# ---------------------------------------------------------------------------


def test_parse_processes_rejects_mismatch():
    payload = """
    {
      "normadressat": "administration",
      "prozesse": [
        {"prozess_bezeichnung": "X", "prozess_beschreibung": "Y", "vorgaben": []}
      ]
    }
    """
    with pytest.raises(HTTPException) as exc_info:
        _parse_processes(payload, BUSINESS)
    assert exc_info.value.status_code == 422
    assert "normadressat mismatch" in exc_info.value.detail


def test_parse_processes_flags_missing():
    payload = """
    {
      "prozesse": [
        {"prozess_bezeichnung": "X", "prozess_beschreibung": "Y", "vorgaben": []}
      ]
    }
    """
    parsed, fallbacks = _parse_processes(payload, BUSINESS)
    assert parsed
    assert NORM_ADDRESSEE_ECHO_MISSING in fallbacks


def test_parse_processes_no_fallback_on_match():
    payload = """
    {
      "normadressat": "business",
      "prozesse": [
        {"prozess_bezeichnung": "X", "prozess_beschreibung": "Y", "vorgaben": []}
      ]
    }
    """
    parsed, fallbacks = _parse_processes(payload, BUSINESS)
    assert parsed
    assert NORM_ADDRESSEE_ECHO_MISMATCH not in fallbacks
    assert NORM_ADDRESSEE_ECHO_MISSING not in fallbacks


# ---------------------------------------------------------------------------
# _parse_case_groups (case_group_development)
# ---------------------------------------------------------------------------


def test_parse_case_groups_rejects_mismatch():
    payload = """
    {
      "normadressat": "citizens",
      "prozesse": [
        {
          "prozess_id": 1,
          "prozess_bezeichnung": "P",
          "prozess_beschreibung": "B",
          "fallgruppen": [
            {"fallgruppe_bezeichnung": "F", "fallgruppe_beschreibung": "D"}
          ]
        }
      ]
    }
    """
    with pytest.raises(HTTPException) as exc_info:
        _parse_case_groups(payload, ADMINISTRATION)
    assert exc_info.value.status_code == 422
    assert "normadressat mismatch" in exc_info.value.detail


def test_parse_case_groups_flags_missing():
    payload = """
    {
      "prozesse": [
        {
          "prozess_id": 1,
          "prozess_bezeichnung": "P",
          "prozess_beschreibung": "B",
          "fallgruppen": [
            {"fallgruppe_bezeichnung": "F", "fallgruppe_beschreibung": "D"}
          ]
        }
      ]
    }
    """
    parsed, fallbacks = _parse_case_groups(payload, ADMINISTRATION)
    assert parsed
    assert NORM_ADDRESSEE_ECHO_MISSING in fallbacks


# ---------------------------------------------------------------------------
# _parse_process_steps (process_step_analysis)
# ---------------------------------------------------------------------------


def test_parse_process_steps_rejects_mismatch():
    payload = """
    {
      "normadressat": "business",
      "fallgruppen": [
        {
          "fallgruppen_id": 10,
          "taetigkeiten": [
            {"taetigkeit": "T", "beschreibung": "B"}
          ]
        }
      ]
    }
    """
    with pytest.raises(HTTPException) as exc_info:
        _parse_process_steps(payload, CITIZENS)
    assert exc_info.value.status_code == 422
    assert "normadressat mismatch" in exc_info.value.detail


def test_parse_process_steps_flags_missing():
    payload = """
    {
      "fallgruppen": [
        {
          "fallgruppen_id": 10,
          "taetigkeiten": [
            {"taetigkeit": "T", "beschreibung": "B"}
          ]
        }
      ]
    }
    """
    parsed, fallbacks = _parse_process_steps(payload, CITIZENS)
    assert parsed
    assert NORM_ADDRESSEE_ECHO_MISSING in fallbacks


# ---------------------------------------------------------------------------
# _parse_cases_payload (cases_calculation)
# ---------------------------------------------------------------------------


def test_parse_cases_payload_rejects_mismatch():
    payload = """
    {
      "normadressat": "administration",
      "prozesse": [
        {
          "fallgruppen": [
            {
              "fallgruppen_id": 42,
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "1"
            }
          ]
        }
      ]
    }
    """
    with pytest.raises(HTTPException) as exc_info:
        _parse_cases_payload(payload, BUSINESS)
    assert exc_info.value.status_code == 422
    assert "normadressat mismatch" in exc_info.value.detail


def test_parse_cases_payload_flags_missing():
    payload = """
    {
      "prozesse": [
        {
          "fallgruppen": [
            {
              "fallgruppen_id": 42,
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "1"
            }
          ]
        }
      ]
    }
    """
    parsed, fallbacks = _parse_cases_payload(payload, BUSINESS)
    assert parsed
    assert NORM_ADDRESSEE_ECHO_MISSING in fallbacks


# ---------------------------------------------------------------------------
# _parse_effort_payload (effort_calculation)
# ---------------------------------------------------------------------------


def test_parse_effort_payload_rejects_mismatch():
    payload = """
    {
      "normadressat": "citizens",
      "prozesse": [
        {
          "fallgruppen": [
            {
              "fallgruppen_id": 10,
              "taetigkeiten": [
                {
                  "taetigkeiten_id": 100,
                  "personalaufwand_vorschlag": [
                    {"qualifikation": "einfacher_und_mittlerer_dienst",
                     "lohnquelle": "bund", "zeitaufwand_in_min": "6"}
                  ],
                  "sachaufwand_vorschlag": "2"
                }
              ]
            }
          ]
        }
      ]
    }
    """
    with pytest.raises(HTTPException) as exc_info:
        _parse_effort_payload(payload, ADMINISTRATION)
    assert exc_info.value.status_code == 422
    assert "normadressat mismatch" in exc_info.value.detail


def test_parse_effort_payload_flags_missing():
    payload = """
    {
      "prozesse": [
        {
          "fallgruppen": [
            {
              "fallgruppen_id": 10,
              "taetigkeiten": [
                {
                  "taetigkeiten_id": 100,
                  "zeitaufwand_in_min_vorschlag": "6",
                  "sachaufwand_vorschlag": "2"
                }
              ]
            }
          ]
        }
      ]
    }
    """
    parsed, fallbacks = _parse_effort_payload(payload, CITIZENS)
    assert parsed
    assert NORM_ADDRESSEE_ECHO_MISSING in fallbacks


def test_parse_effort_payload_no_fallback_on_match():
    payload = """
    {
      "normadressat": "citizens",
      "prozesse": [
        {
          "fallgruppen": [
            {
              "fallgruppen_id": 10,
              "taetigkeiten": [
                {
                  "taetigkeiten_id": 100,
                  "zeitaufwand_in_min_vorschlag": "6",
                  "sachaufwand_vorschlag": "2"
                }
              ]
            }
          ]
        }
      ]
    }
    """
    parsed, fallbacks = _parse_effort_payload(payload, CITIZENS)
    assert parsed
    assert NORM_ADDRESSEE_ECHO_MISMATCH not in fallbacks
    assert NORM_ADDRESSEE_ECHO_MISSING not in fallbacks
