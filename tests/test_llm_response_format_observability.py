import asyncio

import pytest

from backend.core import db, llm_monitor, llm_service
from backend.core.auth import ApiKeys
from backend.core.llm_attempts import (
    mark_llm_answer_applied,
    mark_llm_answer_apply_failed,
    query_and_stage_llm_answer,
)
from backend.core.llm_service import LlmQueryError, LlmResult, query_llm
from backend.core.prompts import PromptId

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


def _bad_request(model: str, provider: str = "openai") -> LlmQueryError:
    return LlmQueryError(
        provider=provider,
        model=model,
        reason="provider_http_error",
        status_code=400,
        message="unsupported",
    )


# --- Erfolgsfall: kein Downgrade wird auch als solcher gemeldet ---


def test_json_schema_accepted_reports_no_downgrade(monkeypatch):
    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    result = asyncio.run(
        query_llm(
            "p", _keys(), "gpt-4o", provider="openai", response_format=_json_schema_mode()
        )
    )

    assert result.response_format_requested == "json_schema"
    assert result.response_format_used == "json_schema"
    assert result.response_format_downgraded is False


def test_no_response_format_reports_none(monkeypatch):
    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    result = asyncio.run(
        query_llm("p", _keys(), "gpt-4o", provider="openai", response_format=None)
    )

    assert result.response_format_requested == "none"
    assert result.response_format_used == "none"
    assert result.response_format_downgraded is False


# --- Downgrade wird als Daten gemeldet und geloggt ---


def test_downgrade_to_json_object_is_reported(monkeypatch):
    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        if response_format is not None and response_format.get("type") == "json_schema":
            raise _bad_request(model)
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    result = asyncio.run(
        query_llm(
            "p", _keys(), "gpt-4o", provider="openai", response_format=_json_schema_mode()
        )
    )

    assert result.response_format_requested == "json_schema"
    assert result.response_format_used == "json_object"
    assert result.response_format_downgraded is True


def test_downgrade_to_none_is_reported(monkeypatch):
    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        if response_format is not None:
            raise _bad_request(model)
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    result = asyncio.run(
        query_llm(
            "p", _keys(), "gpt-4o", provider="openai", response_format=_json_schema_mode()
        )
    )

    assert result.response_format_used == "none"
    assert result.response_format_downgraded is True


def test_downgrade_emits_warning_log(monkeypatch, caplog):
    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        if response_format is not None and response_format.get("type") == "json_schema":
            raise _bad_request(model)
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    with caplog.at_level("WARNING", logger="uvicorn.error"):
        asyncio.run(
            query_llm(
                "p",
                _keys(),
                "gpt-4o",
                provider="openai",
                response_format=_json_schema_mode(),
            )
        )

    messages = [record.getMessage() for record in caplog.records]
    assert any("response_format downgrade" in message for message in messages)
    assert any("from=json_schema to=json_object" in message for message in messages)


# --- Testluecke geschlossen: Kette galt bisher nur fuer OpenAI ---


def test_gemini_downgrade_is_reported(monkeypatch):
    calls: list = []

    async def fake_query_gemini(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        calls.append(response_format)
        if response_format is not None and response_format.get("type") == "json_schema":
            raise _bad_request(model, provider="gemini")
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_gemini_openai", fake_query_gemini)

    schema = _json_schema_mode()
    result = asyncio.run(
        query_llm("p", _keys(), "gemini-3.5-flash", provider="gemini", response_format=schema)
    )

    assert calls == [schema, JSON_MODE]
    assert result.response_format_used == "json_object"
    assert result.response_format_downgraded is True


def test_deepinfra_downgrade_is_reported(monkeypatch):
    calls: list = []

    async def fake_query_deepinfra(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        calls.append(response_format)
        if response_format is not None:
            raise _bad_request(model, provider="deepinfra")
        return LlmResult(text="{}")

    monkeypatch.setattr(llm_service, "query_deepinfra", fake_query_deepinfra)

    schema = _json_schema_mode()
    result = asyncio.run(
        query_llm(
            "p",
            _keys(),
            "deepseek-ai/DeepSeek-V3.2",
            provider="deepinfra",
            response_format=schema,
        )
    )

    assert calls == [schema, JSON_MODE, None]
    assert result.response_format_used == "none"
    assert result.response_format_downgraded is True


def test_bad_request_on_last_chain_link_raises(monkeypatch):
    calls: list = []

    async def fake_query_openai(
        prompt, api_key, model, *, stream=False, on_event=None, response_format=None
    ):
        calls.append(response_format)
        raise _bad_request(model)

    monkeypatch.setattr(llm_service, "query_openai", fake_query_openai)

    with pytest.raises(LlmQueryError):
        asyncio.run(
            query_llm(
                "p",
                _keys(),
                "gpt-4o",
                provider="openai",
                response_format=_json_schema_mode(),
            )
        )

    assert calls == [_json_schema_mode(), JSON_MODE, None]


# --- Persistenz: das Ergebnis landet in den Answer-Metadaten ---


def test_downgrade_is_persisted_in_answer_metadata(test_client):
    session_id, _ = db.upsert_session("LLM-RESPONSE-FORMAT-OBS", "test-model")

    async def fake_query_fn(prompt, api_keys, model, provider, **kwargs):
        return LlmResult(
            text="Antworttext",
            response_format_requested="json_schema",
            response_format_used="json_object",
            response_format_downgraded=True,
        )

    answer_id, _ = asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id=PromptId.CASES_CALCULATION,
            prompt="p",
            api_keys=_keys(),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
        )
    )

    metadata = db.get_llm_answer_by_id(answer_id)["metadata"]
    assert metadata["response_format_requested"] == "json_schema"
    assert metadata["response_format_used"] == "json_object"
    assert metadata["response_format_downgraded"] is True


# --- Monitor-UI: das Ergebnis erreicht die recent-call API und den Live-Stream ---


def _stage_downgraded_answer(app_session_id: str) -> tuple[int, int]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")

    async def fake_query_fn(prompt, api_keys, model, provider, **kwargs):
        return LlmResult(
            text="Antworttext",
            response_format_requested="json_schema",
            response_format_used="json_object",
            response_format_downgraded=True,
        )

    answer_id, _ = asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id=PromptId.CASES_CALCULATION,
            prompt="p",
            api_keys=_keys(),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
        )
    )
    return session_id, answer_id


def test_downgrade_is_surfaced_in_recent_llm_answers(test_client):
    session_id, answer_id = _stage_downgraded_answer("LLM-RESPONSE-FORMAT-RECENT")

    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["answer_id"] == answer_id
    ]
    assert len(rows) == 1
    assert rows[0]["response_format_requested"] == "json_schema"
    assert rows[0]["response_format_used"] == "json_object"
    assert rows[0]["response_format_downgraded"] is True


async def _run_and_flush_fire_and_forget_tasks(fn) -> None:
    fn()
    pending = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    if pending:
        await asyncio.gather(*pending)


def test_downgrade_is_surfaced_in_apply_succeeded_event(test_client):
    app_session_id = "LLM-RESPONSE-FORMAT-APPLY"
    session_id, answer_id = _stage_downgraded_answer(app_session_id)

    asyncio.run(
        _run_and_flush_fire_and_forget_tasks(
            lambda: mark_llm_answer_applied(
                answer_id=answer_id,
                session_id=session_id,
                prompt_id=PromptId.CASES_CALCULATION,
            )
        )
    )

    events = asyncio.run(llm_monitor.get_recent_events(app_session_id, limit=50))
    apply_events = [
        event
        for event in events
        if event["event_type"] == "llm_apply_succeeded" and event["answer_id"] == answer_id
    ]
    assert len(apply_events) == 1
    assert apply_events[0]["response_format_requested"] == "json_schema"
    assert apply_events[0]["response_format_used"] == "json_object"
    assert apply_events[0]["response_format_downgraded"] is True


def test_downgrade_is_surfaced_in_apply_failed_event(test_client):
    app_session_id = "LLM-RESPONSE-FORMAT-APPLY-FAIL"
    _session_id, answer_id = _stage_downgraded_answer(app_session_id)

    asyncio.run(
        _run_and_flush_fire_and_forget_tasks(
            lambda: mark_llm_answer_apply_failed(answer_id=answer_id, exc=RuntimeError("boom"))
        )
    )

    events = asyncio.run(llm_monitor.get_recent_events(app_session_id, limit=50))
    apply_events = [
        event
        for event in events
        if event["event_type"] == "llm_apply_failed" and event["answer_id"] == answer_id
    ]
    assert len(apply_events) == 1
    assert apply_events[0]["response_format_requested"] == "json_schema"
    assert apply_events[0]["response_format_used"] == "json_object"
    assert apply_events[0]["response_format_downgraded"] is True
