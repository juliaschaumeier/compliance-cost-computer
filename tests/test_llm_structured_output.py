import asyncio

import pytest

from backend.core import db, llm_service
from backend.core.auth import ApiKeys
from backend.core.llm_attempts import query_and_stage_llm_answer
from backend.core.llm_service import LlmQueryError, LlmResult, query_llm
from backend.core.norm_addressees import BUSINESS, CITIZENS

JSON_MODE = {"type": "json_object"}


def _json_schema_mode() -> dict:
    return {
        "type": "json_schema",
        "name": "cases_calculation",
        "schema": {
            "type": "object",
            "properties": {"normadressat": {"type": "string"}},
            "required": ["normadressat"],
            "additionalProperties": False,
        },
        "strict": True,
    }


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


# --- API-spezifisches Wrapping des json_schema-Formats ---


def test_query_openai_chat_wraps_json_schema(monkeypatch):
    captured: dict = {}

    async def fake_once(*, provider, client, payload, model):
        captured["payload"] = payload
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "_query_chat_completions_once", fake_once)

    schema = _json_schema_mode()
    asyncio.run(
        llm_service.query_openai("p", "sk-test", "gpt-4o", response_format=schema)
    )

    assert captured["payload"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "cases_calculation",
            "strict": True,
            "schema": schema["schema"],
        },
    }


def test_query_gemini_chat_wraps_json_schema(monkeypatch):
    captured: dict = {}

    async def fake_once(*, provider, client, payload, model):
        captured["payload"] = payload
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "_query_chat_completions_once", fake_once)

    schema = _json_schema_mode()
    asyncio.run(
        llm_service.query_gemini_openai(
            "p", "g-test", "gemini-2.5-flash", response_format=schema
        )
    )

    assert captured["payload"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "cases_calculation",
            "strict": True,
            "schema": schema["schema"],
        },
    }


def test_query_openai_responses_wraps_json_schema(monkeypatch):
    captured: dict = {}

    class _FakeResponses:
        async def create(self, **payload):
            captured["payload"] = payload
            raise RuntimeError("stop after payload capture")

    class _FakeClient:
        responses = _FakeResponses()

    schema = _json_schema_mode()
    with pytest.raises(Exception):
        asyncio.run(
            llm_service._query_openai_responses(
                _FakeClient(), "p", "gpt-5-mini", response_format=schema
            )
        )

    assert captured["payload"]["text"] == {
        "format": {
            "type": "json_schema",
            "name": "cases_calculation",
            "schema": schema["schema"],
            "strict": True,
        }
    }


def test_response_format_wrappers_pass_json_object_through():
    assert llm_service._response_format_for_chat(JSON_MODE) == JSON_MODE
    assert llm_service._response_format_for_responses(JSON_MODE) == JSON_MODE
    assert llm_service._response_format_for_chat(None) is None
    assert llm_service._response_format_for_responses(None) is None


# --- Gestaffelte Fallback-Kette json_schema -> json_object -> None ---


def test_query_llm_staged_fallback_json_schema_to_json_object_to_none(monkeypatch):
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
                message="unsupported",
            )
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    schema = _json_schema_mode()
    result = asyncio.run(
        query_llm("p", _keys(), "gpt-4o", provider="openai", response_format=schema)
    )

    assert result.text == "{}"
    assert calls == [schema, JSON_MODE, None]


def test_query_llm_json_schema_falls_back_to_json_object(monkeypatch):
    calls: list = []

    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        calls.append(response_format)
        if response_format is not None and response_format.get("type") == "json_schema":
            raise LlmQueryError(
                provider="openai",
                model=model,
                reason="provider_http_error",
                status_code=400,
                message="strict schema unsupported",
            )
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    schema = _json_schema_mode()
    result = asyncio.run(
        query_llm("p", _keys(), "gpt-4o", provider="openai", response_format=schema)
    )

    assert result.text == "{}"
    assert calls == [schema, JSON_MODE]


# --- Alle strukturierten Workflow-Prompts erzwingen json_schema ---


def test_query_and_stage_uses_effort_citizens_schema_variant(test_client):
    session_id, _ = db.upsert_session("LLM-JSON-SCHEMA-EFFORT", "test-model")
    captured: dict = {}

    async def fake_query_fn(prompt, api_keys, model, provider, **kwargs):
        captured.update(kwargs)
        return "Antworttext"

    asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id="effort_calculation",
            prompt="Frage",
            api_keys=ApiKeys(openai_api_key="sk-test"),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
            norm_addressee=CITIZENS,
        )
    )

    response_format = captured.get("response_format")
    assert response_format["type"] == "json_schema"
    assert response_format["name"] == "effort_calculation"
    taetigkeit = response_format["schema"]["properties"]["fallgruppen"]["items"][
        "properties"
    ]["taetigkeiten"]["items"]
    assert set(taetigkeit["properties"].keys()) == {
        "taetigkeiten_id",
        "zeitaufwand_in_min_gueltig",
        "sachaufwand_gueltig",
        "zeitaufwand_in_min_vorschlag",
        "sachaufwand_vorschlag",
    }


@pytest.mark.parametrize(
    "prompt_id",
    [
        "process_compilation",
        "case_group_development",
        "process_step_analysis",
        "cases_calculation",
        "effort_calculation",
    ],
)
def test_query_and_stage_uses_json_schema_for_every_structured_prompt(
    test_client, prompt_id
):
    session_id, _ = db.upsert_session(f"LLM-JSON-SCHEMA-{prompt_id}", "test-model")
    captured: dict = {}

    async def fake_query_fn(prompt, api_keys, model, provider, **kwargs):
        captured.update(kwargs)
        return "Antworttext"

    asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id=prompt_id,
            prompt="Frage",
            api_keys=ApiKeys(openai_api_key="sk-test"),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
            norm_addressee=BUSINESS,
        )
    )

    response_format = captured.get("response_format")
    assert response_format["type"] == "json_schema"
    assert response_format["name"] == prompt_id
    assert response_format["strict"] is True
    assert response_format["schema"]["properties"]["normadressat"]["enum"] == [BUSINESS]


def test_query_and_stage_cases_degrades_to_json_object_without_addressee(test_client):
    session_id, _ = db.upsert_session("LLM-JSON-DEGRADE", "test-model")
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
