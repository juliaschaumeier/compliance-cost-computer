import httpx

from backend.core import llm_service


def test_resolve_estimated_cost_prefers_provider_reported_cost():
    resolved = llm_service._resolve_estimated_cost_usd(
        provider="openai",
        model="gpt-5.2-pro",
        input_tokens=1000,
        output_tokens=1000,
        provider_reported_cost_usd=0.123456789,
    )
    assert resolved == 0.12345679


def test_extract_hidden_thinking_tokens_openai_reasoning():
    payload = {"usage": {"output_tokens_details": {"reasoning_tokens": 42}}}
    hidden = llm_service._extract_hidden_thinking_tokens(
        provider="openai",
        response_json=payload,
    )
    assert hidden == 42


def test_resolve_billable_output_tokens_gemini_includes_thoughts_without_double_count():
    payload = {"usageMetadata": {"candidatesTokenCount": 90, "thoughtsTokenCount": 30}}
    billable = llm_service._resolve_billable_output_tokens(
        provider="gemini",
        output_tokens=100,
        response_json=payload,
        hidden_thinking_tokens=30,
    )
    assert billable == 120


def test_extract_provider_reported_cost_usd():
    payload = {"usage": {"estimated_cost": "0.00123"}}
    reported = llm_service._extract_provider_reported_cost_usd(payload)
    assert reported == 0.00123


def test_normalize_llm_exception_timeout_reason():
    normalized = llm_service._normalize_llm_exception(
        provider="openai",
        model="gpt-5.2-pro",
        exc=TimeoutError("request timed out"),
    )
    assert normalized.reason == "provider_timeout"
    assert "openai:provider_timeout" in str(normalized)


def test_normalize_llm_exception_connection_reason():
    normalized = llm_service._normalize_llm_exception(
        provider="gemini",
        model="gemini-2.5-flash",
        exc=httpx.ConnectError("connection dropped"),
    )
    assert normalized.reason == "provider_connection_error"
    assert "gemini:provider_connection_error" in str(normalized)
