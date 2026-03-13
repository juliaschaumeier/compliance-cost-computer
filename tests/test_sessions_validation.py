def test_upsert_session_rejects_invalid_app_session_id(test_client):
    resp = test_client.post(
        "/sessions",
        json={"app_session_id": "bad id", "llm_model": "gpt-5"},
    )
    assert resp.status_code == 422


def test_upsert_session_rejects_blank_model_name(test_client):
    resp = test_client.post(
        "/sessions",
        json={"app_session_id": "ABC123", "llm_model": "   "},
    )
    assert resp.status_code == 422


def test_status_rejects_invalid_app_session_id_query(test_client):
    resp = test_client.get("/sessions/status", params={"app_session_id": "bad id"})
    assert resp.status_code == 422


def test_upsert_session_response_shape(test_client):
    resp = test_client.post(
        "/sessions",
        json={"app_session_id": "ABC123", "llm_model": "gpt-5"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload.keys()) == {"app_session_id", "created"}
    assert payload["app_session_id"] == "ABC123"
    assert isinstance(payload["created"], bool)


def test_list_sessions_response_shape(test_client):
    test_client.post("/sessions", json={"app_session_id": "LIST01", "llm_model": "gpt-5"})
    resp = test_client.get("/sessions")
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload.keys()) == {"sessions"}
    assert isinstance(payload["sessions"], list)
    assert payload["sessions"]
    first = payload["sessions"][0]
    assert {"app_session_id", "created_at", "llm_model", "used_llm_models"}.issubset(
        first.keys()
    )


def test_export_rejects_invalid_app_session_id_query(test_client):
    resp = test_client.get("/sessions/export", params={"app_session_id": "bad id"})
    assert resp.status_code == 422


def test_export_requires_app_session_id_query(test_client):
    resp = test_client.get("/sessions/export")
    assert resp.status_code == 422


def test_undo_noop_response_shape(test_client):
    test_client.post("/sessions", json={"app_session_id": "UNDO00", "llm_model": "gpt-5"})
    resp = test_client.post("/sessions/undo", json={"app_session_id": "UNDO00"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "no-op"
    assert payload.get("message") == "No completed steps"
