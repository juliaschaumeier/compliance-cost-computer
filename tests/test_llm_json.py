import pytest
from fastapi import HTTPException

from backend.core.llm_json import (
    clean_llm_payload,
    extract_fallgruppen,
    require_fallgruppen_envelope,
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


@pytest.mark.parametrize(
    ("payload", "expected_mode"),
    [
        ('{"fallgruppen": []}', "flat_fallgruppen"),
        ('{"prozesse": [{"fallgruppen": []}]}', "nested_prozesse"),
    ],
)
def test_require_fallgruppen_envelope_accepts_flat_or_nested(payload, expected_mode):
    data, parse_mode, envelope_mode = require_fallgruppen_envelope(
        payload,
        error_context="Invalid structured payload",
    )

    assert isinstance(data, dict)
    assert parse_mode == "direct_json_loads"
    assert envelope_mode == expected_mode


def test_require_fallgruppen_envelope_rejects_malformed_flat_even_with_nested_data():
    payload = '{"fallgruppen": {}, "prozesse": [{"fallgruppen": []}]}'

    with pytest.raises(HTTPException) as exc_info:
        require_fallgruppen_envelope(
            payload,
            error_context="Invalid structured payload",
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == (
        "Invalid structured payload: expected top-level key 'fallgruppen' "
        "to contain an array"
    )


def test_require_json_object_rejects_fallback_inner_object_without_envelope():
    # Kaputtes Top-Level-JSON (trailing comma) -> der Fallback extract_last_json_object
    # liefert ein inneres Objekt OHNE prozesse. Muss hart als 422 scheitern,
    # statt still mit dem Fragment weiterzuarbeiten.
    payload = '{"prozesse": [{"fallgruppen_id": 1, "x": {"inner": "v"}},]}'
    with pytest.raises(HTTPException) as exc_info:
        require_json_object(
            payload,
            error_context="Invalid cases_calculation payload",
            required_top_level_key="prozesse",
        )
    assert exc_info.value.status_code == 422
    assert "expected top-level key 'prozesse'" in exc_info.value.detail


def test_require_json_object_accepts_prose_wrapped_envelope():
    # Legitime Wiederherstellung bleibt erhalten: Prosa um ein valides Envelope
    # herum wird weiter ueber den Fallback akzeptiert.
    payload = 'Hier die Antwort:\n{"prozesse": [{"fallgruppen_id": 1}]}\nDanke.'
    data, mode = require_json_object(
        payload,
        error_context="Invalid cases_calculation payload",
        required_top_level_key="prozesse",
    )
    assert "prozesse" in data
    assert mode == "extract_last_json_object"


def test_require_json_object_rejects_recovered_process_fragment_without_prozesse():
    # Backstop fuer process_compilation / case_group_development: bei einer
    # abgeschnittenen Antwort birgt der Fallback extract_last_json_object ein
    # einzelnes Prozess-Objekt. Es traegt zwar ein Top-Level-`fallgruppen`, aber
    # kein `prozesse`. Mit required_top_level_key="prozesse" muss das hart als
    # 422 scheitern, statt als Teil-Fragment durchzurutschen.
    payload = (
        '{"normadressat": "business", "prozesse": ['
        '{"prozess_id": 1, "prozess_bezeichnung": "A", '
        '"fallgruppen": [{"fallgruppen_id": 7}]},'
        '{"prozess_id": 2, "prozess_bezeichnung": "B"'
    )
    with pytest.raises(HTTPException) as exc_info:
        require_json_object(
            payload,
            error_context="process compilation",
            required_top_level_key="prozesse",
        )
    assert exc_info.value.status_code == 422
    assert "prozesse" in exc_info.value.detail


def test_require_json_object_accepts_prozesse_envelope_with_required_key():
    # Die legitime Form bleibt erhalten: ein Top-Level-`prozesse`-Envelope wird
    # mit der `prozesse`-Pflicht weiterhin akzeptiert.
    payload = '{"prozesse": [{"prozess_id": 1, "fallgruppen": [{"fallgruppen_id": 7}]}]}'
    data, mode = require_json_object(
        payload,
        error_context="process compilation",
        required_top_level_key="prozesse",
    )
    assert "prozesse" in data
    assert mode == "direct_json_loads"
