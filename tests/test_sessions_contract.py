import asyncio
import time

from backend.core import db, llm_monitor
from backend.core.config import settings
from backend.routers import sessions as sessions_router


def _parse_contract(model_cls, payload):
    parsed = model_cls.model_validate(payload)
    assert set(payload.keys()) == set(parsed.model_dump().keys())
    return parsed


def _seed_exportable_session(app_session_id: str) -> None:
    current_name = f"{app_session_id}_current.txt"
    proposed_name = f"{app_session_id}_proposed.txt"
    db.insert_law(current_name, f"{app_session_id} current text")
    db.insert_law(proposed_name, f"{app_session_id} proposed text")
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_documents(app_session_id, current_name, proposed_name)
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    db.insert_regulation(session_id, "§ 1", "Beschreibung")


def test_sessions_upsert_and_list_contract(test_client):
    upsert_resp = test_client.post(
        "/sessions",
        json={"app_session_id": "CONTRACT-UPSERT", "llm_model": "gpt-5"},
    )
    assert upsert_resp.status_code == 200
    upsert_payload = upsert_resp.json()
    upsert = _parse_contract(sessions_router.SessionUpsertResponse, upsert_payload)
    assert upsert.app_session_id == "CONTRACT-UPSERT"

    list_resp = test_client.get("/sessions", params={"limit": 1})
    assert list_resp.status_code == 200
    listed = _parse_contract(sessions_router.SessionListResponse, list_resp.json())
    assert len(listed.sessions) == 1
    assert listed.sessions[0].app_session_id == "CONTRACT-UPSERT"


def test_sessions_list_includes_used_llm_models(test_client):
    app_session_id = "CONTRACT-USED-MODELS"
    upsert_resp = test_client.post(
        "/sessions",
        json={"app_session_id": app_session_id, "llm_model": "gpt-5"},
    )
    assert upsert_resp.status_code == 200

    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    db.insert_llm_answer(session_id, "law_summary", "gpt-5-mini", "{}")
    db.insert_llm_answer(session_id, "regulations_identification", "gpt-5", "{}")
    db.insert_llm_answer(
        session_id,
        "process_compilation",
        "gpt-5-mini",
        "{}",
        answer_state=db.LLM_ANSWER_STATE_INVALID,
        state_reason="query_failed",
    )

    list_resp = test_client.get("/sessions", params={"limit": 10})
    assert list_resp.status_code == 200
    payload = list_resp.json()
    sessions = payload.get("sessions", [])
    session = next(s for s in sessions if s["app_session_id"] == app_session_id)
    label = str(session.get("used_llm_models") or "")
    used_models = {part.strip() for part in label.split(",") if part.strip()}
    assert used_models == {"gpt-5-mini", "gpt-5"}


def test_sessions_used_llm_models_triggers_update_and_delete(test_client):
    app_session_id = "CONTRACT-USED-MODELS-TRIGGERS"
    upsert_resp = test_client.post(
        "/sessions",
        json={"app_session_id": app_session_id, "llm_model": "gpt-5"},
    )
    assert upsert_resp.status_code == 200

    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    answer_id_a = db.insert_llm_answer(session_id, "law_summary", "gpt-5", "{}")
    answer_id_b = db.insert_llm_answer(session_id, "process_compilation", "gpt-5-mini", "{}")
    assert answer_id_a > 0
    assert answer_id_b > 0

    with db.transaction() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE llm_answers SET model = ? WHERE answer_id = ?",
            ("gemini-2.5-pro", answer_id_b),
        )

    session = db.get_session_by_app_id(app_session_id)
    assert session is not None
    used_after_update = str(session.get("used_llm_models") or "")
    assert {part.strip() for part in used_after_update.split(",") if part.strip()} == {
        "gpt-5",
        "gemini-2.5-pro",
    }

    with db.transaction() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM llm_answers WHERE answer_id = ?", (answer_id_a,))

    session = db.get_session_by_app_id(app_session_id)
    assert session is not None
    used_after_delete = str(session.get("used_llm_models") or "")
    assert {part.strip() for part in used_after_delete.split(",") if part.strip()} == {
        "gemini-2.5-pro",
    }


def test_sessions_status_contract(test_client):
    test_client.post(
        "/sessions",
        json={"app_session_id": "CONTRACT-STATUS", "llm_model": "gpt-5"},
    )

    resp = test_client.get(
        "/sessions/status", params={"app_session_id": "CONTRACT-STATUS"}
    )
    assert resp.status_code == 200
    status_payload = resp.json()
    status = _parse_contract(sessions_router.SessionStatusResponse, status_payload)
    assert status.last_completed_step is None
    assert status.last_completed_label is None


def test_sessions_export_contract(test_client):
    _seed_exportable_session("CONTRACT-EXPORT")

    resp = test_client.get(
        "/sessions/export", params={"app_session_id": "CONTRACT-EXPORT"}
    )
    assert resp.status_code == 200
    payload = resp.json()
    exported = _parse_contract(sessions_router.SessionExportResponse, payload)
    assert exported.filename == "ccc_session_CONTRACT-EXPORT.md"
    assert "Titel" in exported.markdown


def test_sessions_undo_contract(test_client):
    test_client.post(
        "/sessions",
        json={"app_session_id": "CONTRACT-UNDO", "llm_model": "gpt-5"},
    )

    noop_resp = test_client.post(
        "/sessions/undo", json={"app_session_id": "CONTRACT-UNDO"}
    )
    assert noop_resp.status_code == 200
    noop = _parse_contract(sessions_router.SessionUndoResponse, noop_resp.json())
    assert noop.status == "no-op"
    assert noop.message == "No completed steps"

    db.update_session_summary("CONTRACT-UNDO", "Titel", "Zusammenfassung")
    ok_resp = test_client.post(
        "/sessions/undo", json={"app_session_id": "CONTRACT-UNDO"}
    )
    assert ok_resp.status_code == 200
    undone = _parse_contract(sessions_router.SessionUndoResponse, ok_resp.json())
    assert undone.status == "ok"
    assert undone.undone_step == "summary"


def test_sessions_run_all_async_contract(test_client, monkeypatch):
    async def _slow_step(*_args, **_kwargs):
        await asyncio.sleep(0.3)

    monkeypatch.setattr(sessions_router, "_run_single_step", _slow_step)

    start_resp = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": "CONTRACT-RUN-ASYNC", "model": "test-model"},
    )
    assert start_resp.status_code == 200
    started = _parse_contract(
        sessions_router.SessionRunAllStartResponse, start_resp.json()
    )
    assert started.started is True

    status_resp = test_client.get(f"/sessions/run-all/{started.run_id}")
    assert status_resp.status_code == 200
    _parse_contract(sessions_router.SessionRunStatusResponse, status_resp.json())

    cancel_resp = test_client.post(f"/sessions/run-all/{started.run_id}/cancel")
    assert cancel_resp.status_code == 200
    cancelled = _parse_contract(
        sessions_router.SessionRunCancelResponse, cancel_resp.json()
    )
    assert cancelled.accepted is True
    assert cancelled.status == "cancelling"

    deadline = time.time() + 3.0
    final_payload = None
    while time.time() < deadline:
        poll = test_client.get(f"/sessions/run-all/{started.run_id}")
        assert poll.status_code == 200
        final_payload = poll.json()
        if final_payload["status"] != "running":
            break
        time.sleep(0.05)

    assert final_payload is not None
    final_status = _parse_contract(sessions_router.SessionRunStatusResponse, final_payload)
    assert final_status.status == "cancelled"


def test_sessions_run_all_events_contract(test_client):
    start_resp = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": "CONTRACT-RUN-EVENTS", "model": "test-model"},
    )
    assert start_resp.status_code == 200
    run_id = start_resp.json()["run_id"]

    with test_client.stream("GET", f"/sessions/run-all/{run_id}/events") as stream_resp:
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"].startswith("text/event-stream")
        first_chunk = next(stream_resp.iter_text())
        assert "event: snapshot" in first_chunk


def test_sessions_llm_monitor_snapshot_contract(test_client):
    app_session_id = "CONTRACT-LLM-MONITOR"
    session_id, _ = db.upsert_session(app_session_id, "gpt-5")
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id="regulations_identification",
        model="gpt-5",
        answer_text='{"ok": true}',
        metadata={
            "provider": "openai",
            "attempt_id": "attempt-contract-1",
            "request_id": "request-contract-1",
            "route_method": "POST",
            "route_path": "/regulations/identify",
            "elapsed_ms": 1234,
        },
        answer_state=db.LLM_ANSWER_STATE_ACTIVE,
        state_reason="session_updated",
    )

    resp = test_client.get(
        "/sessions/llm-monitor",
        params={"app_session_id": app_session_id},
    )
    assert resp.status_code == 200
    payload = resp.json()
    parsed = _parse_contract(sessions_router.SessionLlmMonitorSnapshotResponse, payload)
    assert parsed.app_session_id == app_session_id
    assert isinstance(parsed.pending, list)
    assert isinstance(parsed.recent, list)
    assert len(parsed.recent) >= 1
    first = parsed.recent[0]
    assert first["prompt_id"] == "regulations_identification"
    assert first["provider"] == "openai"


def test_sessions_llm_monitor_events_contract(test_client):
    app_session_id = "CONTRACT-LLM-MONITOR-EVENTS"
    db.upsert_session(app_session_id, "gpt-5")

    with test_client.stream(
        "GET",
        "/sessions/llm-monitor/events",
        params={"app_session_id": app_session_id, "once": "true"},
    ) as stream_resp:
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"].startswith("text/event-stream")
        first_chunk = next(stream_resp.iter_text())
        assert "event: snapshot" in first_chunk


def test_sessions_llm_monitor_stream_attempt_contract(test_client):
    app_session_id = "CONTRACT-LLM-MONITOR-STREAM-DETAIL"
    db.upsert_session(app_session_id, "gpt-5")
    asyncio.run(
        llm_monitor.publish_llm_event(
            app_session_id=app_session_id,
            event={
                "event_type": "llm_stream_delta",
                "attempt_id": "attempt-stream-contract-1",
                "session_id": db.get_session_id_by_app_id(app_session_id),
                "prompt_id": "law_summary",
                "model": "gpt-5",
                "provider": "openai",
                "request_id": "request-contract-stream-1",
                "route_method": "POST",
                "route_path": "/regulations/summary",
                "delta_text": "chunk-a",
                "chunk_index": 1,
                "cumulative_chars": 7,
            },
        )
    )

    stream_resp = test_client.get(
        "/sessions/llm-monitor/stream/attempt-stream-contract-1",
        params={"app_session_id": app_session_id},
    )
    assert stream_resp.status_code == 200
    parsed = _parse_contract(
        sessions_router.SessionLlmMonitorStreamAttemptResponse,
        stream_resp.json(),
    )
    assert parsed.app_session_id == app_session_id
    assert parsed.attempt["attempt_id"] == "attempt-stream-contract-1"


def test_sessions_llm_monitor_endpoints_disabled(test_client, monkeypatch):
    app_session_id = "CONTRACT-LLM-MONITOR-DISABLED"
    db.upsert_session(app_session_id, "gpt-5")
    monkeypatch.setattr(settings, "llm_console_enabled", False)

    snapshot_resp = test_client.get(
        "/sessions/llm-monitor",
        params={"app_session_id": app_session_id},
    )
    assert snapshot_resp.status_code == 404

    events_resp = test_client.get(
        "/sessions/llm-monitor/events",
        params={"app_session_id": app_session_id, "once": "true"},
    )
    assert events_resp.status_code == 404

    stream_resp = test_client.get(
        "/sessions/llm-monitor/stream/attempt-does-not-matter",
        params={"app_session_id": app_session_id},
    )
    assert stream_resp.status_code == 404
