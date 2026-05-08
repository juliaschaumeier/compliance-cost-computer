import pytest
from fastapi import HTTPException

from backend.core.llm_json import (
    clean_llm_payload,
    extract_fallgruppen,
    extract_last_json_object,
    parse_json_object,
    parse_json_object_with_mode,
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


def test_direct_json_loads_happy_path():
    data, mode = parse_json_object_with_mode('{"k": 1}')
    assert data == {"k": 1}
    assert mode == "direct_json_loads"


def test_extracts_json_from_markdown_codefence():
    payload = "Hier ist das Ergebnis:\n```json\n{\"k\": 2}\n```\n"
    data, mode = parse_json_object_with_mode(payload)
    assert data == {"k": 2}
    assert mode in {"direct_json_loads", "extract_last_json_object"}


def test_picks_last_json_block_when_multiple_present():
    payload = '{"k": 1}\n\nKorrektur:\n{"k": 99}'
    data, _mode = parse_json_object_with_mode(payload)
    assert data == {"k": 99}


def test_strips_think_block_before_parsing():
    payload = "<think>Ueberlegung...</think>{\"k\": 3}"
    cleaned = clean_llm_payload(payload)
    assert "<think>" not in cleaned
    data = parse_json_object(payload)
    assert data == {"k": 3}


def test_strips_thinking_codefence_before_parsing():
    payload = "```thinking\nplanung\n```\n{\"k\": 4}"
    data = parse_json_object(payload)
    assert data == {"k": 4}


@pytest.mark.parametrize(
    "garbage",
    ["", "   ", "kein json hier", "{ unbalanced", "[1, 2, 3]"],
)
def test_require_json_object_raises_on_garbage(garbage):
    with pytest.raises(HTTPException) as excinfo:
        require_json_object(garbage, error_context="test")
    assert excinfo.value.status_code == 422


def test_require_json_object_validates_top_level_key():
    with pytest.raises(HTTPException) as excinfo:
        require_json_object('{"foo": 1}', error_context="test", required_top_level_key="bar")
    assert excinfo.value.status_code == 422


def test_extract_last_json_object_returns_none_for_empty_input():
    assert extract_last_json_object("") is None
    assert extract_last_json_object("nichts hier") is None


def test_parse_json_object_raises_on_garbage():
    with pytest.raises(ValueError):
        parse_json_object("kein json hier")
