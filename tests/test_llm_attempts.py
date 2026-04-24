import asyncio
import json
from pathlib import Path

from backend.core import db
from backend.core.auth import ApiKeys
from backend.core import config
from backend.core.llm_attempts import (
    llm_query_error_to_status_detail,
    mark_llm_answer_applied,
    query_and_stage_llm_answer,
)
from backend.core.llm_service import LlmQueryError


def test_query_and_stage_uses_injected_query_fn_and_stages_pending(test_client):
    session_id, _ = db.upsert_session("LLM-ATTEMPT", "test-model")

    async def fake_query_fn(prompt, api_keys, model, provider):
        assert "Hallo" in prompt
        assert isinstance(api_keys, ApiKeys)
        assert model == "test-model"
        assert provider == "openai"
        return "Antworttext"

    answer_id, llm_result = asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id="test_prompt",
            prompt="Hallo Welt",
            api_keys=ApiKeys(openai_api_key="sk-test"),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
        )
    )
    assert answer_id > 0
    assert llm_result.text == "Antworttext"

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT answer_state, state_reason, answer_text
        FROM llm_answers
        WHERE answer_id = ?
        """,
        (answer_id,),
    )
    pending = dict(cur.fetchone())
    assert pending == {
        "answer_state": "pending",
        "state_reason": "waiting_for_session_update",
        "answer_text": "Antworttext",
    }

    mark_llm_answer_applied(
        answer_id=answer_id,
        session_id=session_id,
        prompt_id="test_prompt",
    )

    cur.execute(
        """
        SELECT answer_state, state_reason
        FROM llm_answers
        WHERE answer_id = ?
        """,
        (answer_id,),
    )
    active = dict(cur.fetchone())
    conn.close()
    assert active == {
        "answer_state": "active",
        "state_reason": "session_updated",
    }


def test_llm_query_error_to_status_detail_maps_known_reasons():
    status, detail = llm_query_error_to_status_detail(
        LlmQueryError(
            provider="openai",
            model="gpt-5.2",
            reason="provider_timeout",
            message="timed out",
        )
    )
    assert status == 504
    assert "provider_timeout" in detail

    status, detail = llm_query_error_to_status_detail(
        LlmQueryError(
            provider="openai",
            model="gpt-5.2",
            reason="rate_limit",
            message="quota",
            status_code=429,
        )
    )
    assert status == 429
    assert "rate_limit" in detail


def test_query_failure_persists_extended_error_metadata(test_client):
    session_id, _ = db.upsert_session("LLM-ATTEMPT-ERR", "test-model")

    async def fail_query_fn(*_args, **_kwargs):
        raise RuntimeError("synthetic timeout-like failure")

    try:
        asyncio.run(
            query_and_stage_llm_answer(
                session_id=session_id,
                prompt_id="test_prompt_error",
                prompt="Bitte berechnen",
                api_keys=ApiKeys(openai_api_key="sk-test"),
                model="test-model",
                provider="openai",
                query_fn=fail_query_fn,
            )
        )
    except RuntimeError:
        pass

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT answer_state, state_reason, metadata
        FROM llm_answers
        WHERE session_id = ? AND prompt_id = 'test_prompt_error'
        ORDER BY answer_id DESC
        LIMIT 1
        """,
        (session_id,),
    )
    row = dict(cur.fetchone())
    conn.close()
    assert row["answer_state"] == "invalid"
    assert row["state_reason"] == "query_failed"
    metadata = json.loads(row["metadata"])
    assert metadata.get("error_type") == "RuntimeError"
    assert metadata.get("provider") == "openai"
    assert metadata.get("prompt_sha256")
    assert isinstance(metadata.get("elapsed_ms"), int)


def test_query_and_stage_writes_prompt_audit_markdown_when_enabled(test_client, tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "prompt_audit_enabled", True)
    monkeypatch.setattr(config.settings, "prompt_audit_output_dir", tmp_path / "prompt_audits")
    monkeypatch.setattr(config.settings, "prompt_audit_session_ids", "LLM-AUDIT")

    session_id, _ = db.upsert_session("LLM-AUDIT", "test-model")

    async def fake_query_fn(prompt, api_keys, model, provider):
        assert prompt == "Hallo Audit"
        return "Antworttext"

    answer_id, _llm_result = asyncio.run(
        query_and_stage_llm_answer(
            session_id=session_id,
            prompt_id="test_prompt_audit",
            prompt="Hallo Audit",
            api_keys=ApiKeys(openai_api_key="sk-test"),
            model="test-model",
            provider="openai",
            query_fn=fake_query_fn,
        )
    )

    assert answer_id > 0
    audit_path = Path(tmp_path / "prompt_audits" / "LLM-AUDIT_prompt_audit.md")
    assert audit_path.exists()
    content = audit_path.read_text(encoding="utf-8")
    assert "# Prompt-Audit fuer Session `LLM-AUDIT`" in content
    assert "## test_prompt_audit" in content
    assert "Hallo Audit" in content
    assert "test-model" in content
    assert "openai" in content
