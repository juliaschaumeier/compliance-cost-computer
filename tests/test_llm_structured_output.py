import asyncio

import pytest

from backend.core import db, llm_service
from backend.core.auth import ApiKeys
from backend.core.llm_attempts import query_and_stage_llm_answer
from backend.core.llm_service import LlmQueryError, LlmResult, query_llm

JSON_MODE = {"type": "json_object"}


def _keys() -> ApiKeys:
    return ApiKeys(
        openai_api_key="sk-test",
        gemini_api_key="g-test",
        deepinfra_api_key="d-test",
    )


# --- Sicherheitsnetz: graceful fallback bei Provider-Ablehnung (Bad Request) ---


def test_query_llm_retries_without_response_format_on_bad_request(monkeypatch):
    calls: list = []

    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        calls.append(response_format)
        if response_format is not None:
            raise LlmQueryError(
                provider="openai",
                model=model,
                reason="provider_http_error",
                status_code=400,
                message="response_format is not supported",
            )
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    result = asyncio.run(
        query_llm("p", _keys(), "gpt-4o", provider="openai", response_format=JSON_MODE)
    )

    assert result.text == "{}"
    # Erst mit Erzwingung (400), dann genau ein Fallback-Retry ohne.
    assert calls == [JSON_MODE, None]


def test_query_llm_does_not_retry_on_non_bad_request(monkeypatch):
    calls: list = []

    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        calls.append(response_format)
        raise LlmQueryError(
            provider="openai",
            model=model,
            reason="rate_limit",
            status_code=429,
            message="slow down",
        )

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    with pytest.raises(LlmQueryError):
        asyncio.run(
            query_llm("p", _keys(), "gpt-4o", provider="openai", response_format=JSON_MODE)
        )
    # Kein Fallback bei Nicht-400 -> nur ein Versuch.
    assert calls == [JSON_MODE]


# --- Parameter-Durchreichung in alle Provider-Varianten ---


def test_query_openai_chat_injects_response_format(monkeypatch):
    captured: dict = {}

    async def fake_once(*, provider, client, payload, model):
        captured["payload"] = payload
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "_query_chat_completions_once", fake_once)

    asyncio.run(
        llm_service.query_openai("p", "sk-test", "gpt-4o", response_format=JSON_MODE)
    )

    assert captured["payload"]["response_format"] == JSON_MODE


def test_query_gemini_chat_injects_response_format(monkeypatch):
    captured: dict = {}

    async def fake_once(*, provider, client, payload, model):
        captured["payload"] = payload
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "_query_chat_completions_once", fake_once)

    asyncio.run(
        llm_service.query_gemini_openai(
            "p", "g-test", "gemini-2.5-flash", response_format=JSON_MODE
        )
    )

    assert captured["payload"]["response_format"] == JSON_MODE


def test_query_openai_responses_path_receives_response_format(monkeypatch):
    # gpt-5 laeuft ueber die Responses-API (anderes Schema-Feld: text.format).
    captured: dict = {}

    async def fake_responses(client, prompt, model, *, response_format=None):
        captured["response_format"] = response_format
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "_query_openai_responses", fake_responses)

    asyncio.run(
        llm_service.query_openai("p", "sk-test", "gpt-5-mini", response_format=JSON_MODE)
    )

    assert captured["response_format"] == JSON_MODE


def test_query_openai_responses_builds_text_format_payload(monkeypatch):
    # Verifiziert die korrekte Responses-API-Form text={"format": ...}.
    captured: dict = {}

    class _FakeResponses:
        async def create(self, **payload):
            captured["payload"] = payload
            raise RuntimeError("stop after payload capture")

    class _FakeClient:
        responses = _FakeResponses()

    with pytest.raises(Exception):
        asyncio.run(
            llm_service._query_openai_responses(
                _FakeClient(), "p", "gpt-5-mini", response_format=JSON_MODE
            )
        )

    assert captured["payload"]["text"] == {"format": JSON_MODE}


def test_query_deepinfra_passes_response_format(monkeypatch):
    captured: dict = {}

    async def fake_non_stream(*, prompt, api_key, model, response_format=None):
        captured["response_format"] = response_format
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "_query_deepinfra_non_stream", fake_non_stream)

    asyncio.run(
        llm_service.query_deepinfra(
            "p", "d-test", "meta-llama/Test", response_format=JSON_MODE
        )
    )

    assert captured["response_format"] == JSON_MODE


# --- Opt-in: nur die Workflow-Prompts aktivieren den JSON-Modus ---


def test_query_and_stage_enables_json_mode_for_workflow_prompt(test_client):
    session_id, _ = db.upsert_session("LLM-JSON-MODE", "test-model")
    captured: dict = {}

    async def fake_query_fn(prompt, api_keys, model, provider, **kwargs):
        captured.update(kwargs)
        return "Antworttext"

    asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id="cases_calculation",
            prompt="Frage",
            api_keys=ApiKeys(openai_api_key="sk-test"),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
        )
    )

    assert captured.get("response_format") == {"type": "json_object"}


def test_query_and_stage_omits_json_mode_for_non_workflow_prompt(test_client):
    session_id, _ = db.upsert_session("LLM-NO-JSON-MODE", "test-model")
    captured: dict = {}

    async def fake_query_fn(prompt, api_keys, model, provider, **kwargs):
        captured.update(kwargs)
        return "Antworttext"

    asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id="regulation_extraction",
            prompt="Frage",
            api_keys=ApiKeys(openai_api_key="sk-test"),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
        )
    )

    assert "response_format" not in captured
