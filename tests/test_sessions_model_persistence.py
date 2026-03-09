from uuid import uuid4

import pytest

from backend.core import db


@pytest.fixture(autouse=True)
def cleanup_model_session_artifacts():
    _delete_model_test_sessions()
    yield
    _delete_model_test_sessions()


def _delete_model_test_sessions() -> None:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM sessions
        WHERE app_session_id LIKE 'MODEL-KEEP-%'
           OR app_session_id LIKE 'MODEL-UPDATE-%'
           OR app_session_id LIKE 'MODEL-REQUIRED-%'
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def ensure_schema():
    db.init_db()


def test_ensure_session_keeps_existing_model_without_request_model():
    app_session_id = f"MODEL-KEEP-{uuid4().hex[:8]}"
    session_id, _ = db.upsert_session(app_session_id, "gpt-5")

    resolved_id, created_again, resolved_model = db.ensure_session(app_session_id)
    assert resolved_id == session_id
    assert created_again is False
    assert resolved_model == "gpt-5"

    session = db.get_session_by_app_id(app_session_id)
    assert session is not None
    assert session["llm_model"] == "gpt-5"


def test_ensure_session_updates_existing_model_when_request_model_is_set():
    app_session_id = f"MODEL-UPDATE-{uuid4().hex[:8]}"
    session_id, _ = db.upsert_session(app_session_id, "gpt-5")

    resolved_id, created_again, resolved_model = db.ensure_session(
        app_session_id,
        "gemini-2.5-pro",
    )
    assert resolved_id == session_id
    assert created_again is False
    assert resolved_model == "gemini-2.5-pro"

    session = db.get_session_by_app_id(app_session_id)
    assert session is not None
    assert session["llm_model"] == "gemini-2.5-pro"


def test_ensure_session_requires_model_for_new_session():
    app_session_id = f"MODEL-REQUIRED-{uuid4().hex[:8]}"
    with pytest.raises(ValueError, match="Model is required for new session"):
        db.ensure_session(app_session_id, None)
