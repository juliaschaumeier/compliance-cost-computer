import pytest
from fastapi import HTTPException

from backend.core.llm_json import (
    clean_llm_payload,
    extract_fallgruppen,
    parse_json_object,
    require_json_object,
)


def test_clean_llm_payload_removes_think_sections():
    raw = "<think>internal</think>\n```thinking\nhidden\n```\n{\"ok\": true}"
    cleaned = clean_llm_payload(raw)
    assert cleaned == "{\"ok\": true}"


def test_parse_json_object_reads_trailing_json_object():
    raw = "preface text\n{\"a\": 1}\nmore text\n{\"b\": 2}"
    parsed = parse_json_object(raw)
    assert parsed == {"b": 2}


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


def test_require_json_object_raises_for_missing_json_object():
    with pytest.raises(HTTPException) as exc_info:
        require_json_object("not json", error_context="Invalid payload")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Invalid payload: no JSON object found in LLM response"


def test_require_json_object_raises_for_missing_top_level_key():
    with pytest.raises(HTTPException) as exc_info:
        require_json_object(
            '{"other": []}',
            error_context="Invalid payload",
            required_top_level_key="vorgaben",
        )

    assert exc_info.value.status_code == 422
    assert "expected top-level key 'vorgaben'" in exc_info.value.detail
