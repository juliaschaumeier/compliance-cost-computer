import pytest
from fastapi import HTTPException

from backend.core.llm_json import (
    clean_llm_payload,
    extract_fallgruppen,
    require_json_object,
)


def test_clean_llm_payload_removes_think_sections():
    raw = "<think>internal</think>\n```thinking\nhidden\n```\n{\"ok\": true}"
    cleaned = clean_llm_payload(raw)
    assert cleaned == "{\"ok\": true}"


def test_extract_fallgruppen_accepts_top_level_or_nested_payload():
    top_level = {"fallgruppen": [{"fallgruppen_id": 1}, "x"]}
    nested = {
        "prozesse": [
            {"fallgruppen": [{"fallgruppen_id": 2}]},
            {"fallgruppen": "bad"},
        ]
    }
    assert extract_fallgruppen(top_level) == [{"fallgruppen_id": 1}]
    assert extract_fallgruppen(nested) == [{"fallgruppen_id": 2}]


def test_require_json_object_rejects_fallback_inner_object_without_envelope():
    # Kaputtes Top-Level-JSON (trailing comma) -> der Fallback extract_last_json_object
    # liefert ein inneres Objekt OHNE prozesse/fallgruppen. Muss hart als 422
    # scheitern, statt still mit dem Fragment weiterzuarbeiten.
    payload = '{"prozesse": [{"fallgruppen_id": 1, "x": {"inner": "v"}},]}'
    with pytest.raises(HTTPException) as exc_info:
        require_json_object(
            payload,
            error_context="Invalid cases_calculation payload",
            required_any_keys=("prozesse", "fallgruppen"),
        )
    assert exc_info.value.status_code == 422
    assert "expected one of" in exc_info.value.detail


def test_require_json_object_accepts_prose_wrapped_envelope():
    # Legitime Wiederherstellung bleibt erhalten: Prosa um ein valides Envelope
    # herum wird weiter ueber den Fallback akzeptiert.
    payload = 'Hier die Antwort:\n{"prozesse": [{"fallgruppen_id": 1}]}\nDanke.'
    data, mode = require_json_object(
        payload,
        error_context="Invalid cases_calculation payload",
        required_any_keys=("prozesse", "fallgruppen"),
    )
    assert "prozesse" in data
    assert mode == "extract_last_json_object"
