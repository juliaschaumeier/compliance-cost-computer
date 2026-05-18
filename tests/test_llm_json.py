from backend.core.llm_json import (
    clean_llm_payload,
    extract_fallgruppen,
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
