import asyncio
from types import SimpleNamespace

import httpx

from backend.core import llm_service
from backend.core import config


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


def test_openai_chat_token_limit_key_uses_completion_tokens_for_o_models():
    assert llm_service._openai_chat_token_limit_key("o4-mini") == "max_completion_tokens"
    assert llm_service._openai_chat_token_limit_key("openai/o4-mini") == "max_completion_tokens"
    assert llm_service._openai_chat_token_limit_key("O4 mini") == "max_completion_tokens"
    assert llm_service._openai_chat_token_limit_key("o4_mini") == "max_completion_tokens"
    assert llm_service._openai_chat_token_limit_key("o4-mini-2025-04-16") == "max_completion_tokens"
    assert llm_service._openai_chat_token_limit_key("o3-mini") == "max_completion_tokens"
    assert llm_service._openai_chat_token_limit_key("o1") == "max_completion_tokens"


def test_openai_chat_token_limit_key_keeps_max_tokens_for_gpt_4o_models():
    assert llm_service._openai_chat_token_limit_key("gpt-4o-mini") == "max_tokens"


def test_openai_chat_max_tokens_caps_o4_mini_to_provider_limit():
    assert llm_service._openai_chat_max_tokens("o4-mini", 125_000) == 100_000
    assert llm_service._openai_chat_max_tokens("openai/o4-mini", 125_000) == 100_000
    assert llm_service._openai_chat_max_tokens("O4 mini", 125_000) == 100_000
    assert llm_service._openai_chat_max_tokens("o4_mini", 125_000) == 100_000
    assert llm_service._openai_chat_max_tokens("o4-mini-2025-04-16", 125_000) == 100_000
    assert llm_service._openai_chat_max_tokens("o4-mini", 50_000) == 50_000


def test_openai_chat_max_tokens_leaves_other_models_unchanged():
    assert llm_service._openai_chat_max_tokens("gpt-4o-mini", 125_000) == 125_000


def test_openai_safe_max_tokens_caps_openai_default():
    assert llm_service._openai_safe_max_tokens(125_000) == 100_000
    assert llm_service._openai_safe_max_tokens(50_000) == 50_000
    assert llm_service._openai_safe_max_tokens(0) == 0


def test_openai_chat_retry_payload_swaps_unsupported_max_tokens_parameter():
    payload = {"model": "unknown", "max_tokens": 125_000}
    retry = llm_service._openai_chat_retry_payload_for_token_error(
        payload,
        RuntimeError("Unsupported parameter: 'max_tokens' is not supported with this model."),
    )

    assert retry == {"model": "unknown", "max_completion_tokens": 125_000}
    assert payload == {"model": "unknown", "max_tokens": 125_000}


def test_openai_chat_retry_payload_caps_provider_reported_completion_limit():
    payload = {"model": "unknown", "max_completion_tokens": 125_000}
    retry = llm_service._openai_chat_retry_payload_for_token_error(
        payload,
        RuntimeError(
            "max_tokens is too large: 125000. This model supports at most "
            "100003 completion tokens, whereas you provided 125000."
        ),
    )

    assert retry == {"model": "unknown", "max_completion_tokens": 100_003}


def test_openai_chat_retry_payload_returns_none_for_unrelated_error():
    payload = {"model": "unknown", "max_tokens": 125_000}
    assert (
        llm_service._openai_chat_retry_payload_for_token_error(
            payload,
            RuntimeError("rate limit"),
        )
        is None
    )


def test_query_openai_chat_retries_token_key_then_provider_limit(monkeypatch):
    calls = []

    class FakeCompletions:
        async def create(self, **payload):
            calls.append(payload)
            if len(calls) == 1:
                raise RuntimeError(
                    "Unsupported parameter: 'max_tokens' is not supported with this model."
                )
            if len(calls) == 2:
                raise RuntimeError(
                    "max_tokens is too large: 125000. This model supports at most "
                    "100003 completion tokens, whereas you provided 125000."
                )
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content="Antwort"))
                ],
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30,
                ),
            )

    class FakeOpenAI:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(
                completions=FakeCompletions(),
            )

    monkeypatch.setattr(llm_service, "AsyncOpenAI", FakeOpenAI)
    monkeypatch.setattr(config.settings, "openai_max_tokens", 125_000)
    monkeypatch.setattr(config.settings, "enable_web_search", False)

    result = asyncio.run(
        llm_service.query_openai(
            "Prompt",
            "sk-test",
            "model:o4-mini",
        )
    )

    assert result.text == "Antwort"
    assert calls[0]["max_tokens"] == 125_000
    assert "max_completion_tokens" not in calls[0]
    assert calls[1]["max_completion_tokens"] == 125_000
    assert "max_tokens" not in calls[1]
    assert calls[2]["max_completion_tokens"] == 100_003


def test_query_openai_chat_caps_canonical_o4_mini_before_first_request(monkeypatch):
    calls = []

    class FakeCompletions:
        async def create(self, **payload):
            calls.append(payload)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content="Antwort"))
                ],
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30,
                ),
            )

    class FakeOpenAI:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(
                completions=FakeCompletions(),
            )

    monkeypatch.setattr(llm_service, "AsyncOpenAI", FakeOpenAI)
    monkeypatch.setattr(config.settings, "openai_max_tokens", 125_000)
    monkeypatch.setattr(config.settings, "enable_web_search", False)

    result = asyncio.run(
        llm_service.query_openai(
            "Prompt",
            "sk-test",
            "o4-mini",
        )
    )

    assert result.text == "Antwort"
    assert calls == [
        {
            "model": "o4-mini",
            "messages": [{"role": "user", "content": "Prompt"}],
            "max_completion_tokens": 100_000,
        }
    ]


def test_query_openai_chat_stream_unsupported_falls_back_to_non_stream(monkeypatch):
    calls = []
    events = []

    class FakeCompletions:
        async def create(self, **payload):
            calls.append(payload)
            if payload.get("stream"):
                raise RuntimeError("stream unsupported for this model")
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content="Fallback Antwort"))
                ],
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30,
                ),
            )

    class FakeOpenAI:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(
                completions=FakeCompletions(),
            )

    async def on_event(payload):
        events.append(payload)

    monkeypatch.setattr(llm_service, "AsyncOpenAI", FakeOpenAI)
    monkeypatch.setattr(config.settings, "openai_max_tokens", 50_000)
    monkeypatch.setattr(config.settings, "enable_web_search", False)

    result = asyncio.run(
        llm_service.query_openai(
            "Prompt",
            "sk-test",
            "gpt-4o-mini",
            stream=True,
            on_event=on_event,
        )
    )

    assert result.text == "Fallback Antwort"
    assert len(calls) == 2
    assert calls[0]["stream"] is True
    assert "stream" not in calls[1]
    assert any(
        event.get("event_type") == "llm_stream_fallback"
        and event.get("stream_mode") == "fallback_non_stream"
        for event in events
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
