from backend.core import db
from backend.routers import process_steps as process_steps_router


def _seed_steps(app_session_id: str) -> tuple[int, int, int, int]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt 1", "Beschreibung Schritt 1"
    )
    return session_id, process_id, case_group_id, step_id


def test_analyze_process_steps_returns_existing(test_client, monkeypatch):
    """Returns existing steps without calling the LLM."""
    _session_id, _process_id, _case_group_id, step_id = _seed_steps("STEPS-EXISTING")

    async def fail_query_llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called when steps already exist")

    monkeypatch.setattr(process_steps_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-EXISTING",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "existing"
    assert [row["step_id"] for row in payload["steps"]] == [step_id]


def test_analyze_process_steps_requires_case_groups(test_client):
    """Rejects analysis when no case groups exist for the session."""
    db.upsert_session("STEPS-NO-GROUPS", "test-model")

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-NO-GROUPS",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No case groups for session"

