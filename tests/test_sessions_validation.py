def test_upsert_session_ignores_client_app_session_id(test_client):
    # app_session_id is now server-generated; any client-supplied value is ignored.
    resp = test_client.post(
        "/sessions",
        json={"app_session_id": "bad id", "llm_model": "gpt-5"},
    )
    assert resp.status_code == 200
    app_session_id = resp.json()["app_session_id"]
    assert app_session_id != "bad id"
    assert app_session_id.isalnum()


def test_upsert_session_rejects_blank_model_name(test_client):
    resp = test_client.post(
        "/sessions",
        json={"app_session_id": "ABC123", "llm_model": "   "},
    )
    assert resp.status_code == 422


def test_status_rejects_invalid_app_session_id_query(test_client):
    # Malformed/unknown id is rejected by the ownership gate (404) or pattern (422).
    resp = test_client.get("/sessions/status", params={"app_session_id": "bad id"})
    assert resp.status_code in (404, 422)


def test_upsert_session_response_shape(test_client):
    resp = test_client.post(
        "/sessions",
        json={"llm_model": "gpt-5"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload.keys()) == {"app_session_id", "created"}
    assert isinstance(payload["app_session_id"], str) and payload["app_session_id"]
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


def test_undo_noop_response_shape(test_client):
    created = test_client.post("/sessions", json={"llm_model": "gpt-5"})
    app_session_id = created.json()["app_session_id"]
    resp = test_client.post("/sessions/undo", json={"app_session_id": app_session_id})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "no-op"
    assert payload.get("message") == "No completed steps"
