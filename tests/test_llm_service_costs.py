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


def test_estimate_cost_supports_deep_research_agent_alias():
    resolved = llm_service._resolve_estimated_cost_usd(
        provider="gemini",
        model="deep-research-preview-04-2026",
        input_tokens=1_000_000,
        output_tokens=2_000_000,
    )

    assert resolved == 26.0


def test_estimate_cost_supports_current_recommended_openai_models():
    assert (
        llm_service._resolve_estimated_cost_usd(
            provider="openai",
            model="gpt-5.5",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        == 35.0
    )
    assert (
        llm_service._resolve_estimated_cost_usd(
            provider="openai",
            model="gpt-5.4-mini",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        == 5.25
    )
    assert (
        llm_service._resolve_estimated_cost_usd(
            provider="openai",
            model="gpt-5.4-nano",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        == 1.45
    )


def test_estimate_cost_supports_current_recommended_gemini_models():
    assert (
        llm_service._resolve_estimated_cost_usd(
            provider="gemini",
            model="gemini-3.5-flash",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        == 10.5
    )
    assert (
        llm_service._resolve_estimated_cost_usd(
            provider="gemini",
            model="gemini-3-flash-preview",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        == 3.5
    )


def test_estimate_cost_returns_none_for_deepinfra_without_provider_reported_cost():
    assert (
        llm_service._resolve_estimated_cost_usd(
            provider="deepinfra",
            model="anthropic/claude-sonnet-4-6",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        is None
    )


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


def test_extract_openai_responses_stream_delta_text():
    event_json = {
        "type": "response.output_text.delta",
        "delta": "Teil ",
    }
    assert llm_service._extract_openai_responses_stream_delta_text(None, event_json) == "Teil "


def test_extract_openai_responses_stream_delta_text_ignores_other_events():
    event_json = {
        "type": "response.completed",
        "delta": "ignored",
    }
    assert llm_service._extract_openai_responses_stream_delta_text(None, event_json) == ""


def test_extract_openai_responses_stream_error_from_response_failed():
    event_json = {
        "type": "response.failed",
        "response": {"error": {"message": "tool failed"}},
    }
    message = llm_service._extract_openai_responses_stream_error(None, event_json)
    assert message is not None
    assert "tool failed" in message
