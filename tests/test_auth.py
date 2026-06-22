"""Auth + per-user ownership tests exercising the real login flow.

The autouse ``isolated_db`` fixture normally overrides ``get_current_user`` so the
rest of the suite runs authenticated. These tests pop that override to drive the
genuine cookie-based login and ownership checks.
"""

import pytest
from fastapi.testclient import TestClient

from backend.core import auth as auth_core
from backend.core import config, db
from backend.main import app

from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use real authentication (no dependency override) on the seeded DB.
    app.dependency_overrides.pop(auth_core.get_current_user, None)
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    monkeypatch.setattr(config.settings, "auth_secret_key", "test-secret-key")
    db.init_db()
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_sets_cookie_and_me_returns_user(client):
    resp = _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    assert resp.status_code == 200
    assert resp.json()["email"] == TEST_USER_EMAIL

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == TEST_USER_EMAIL
    assert me.json()["is_admin"] is True


def test_login_with_wrong_password_is_rejected(client):
    assert _login(client, TEST_USER_EMAIL, "wrong-password").status_code == 401


def test_unauthenticated_request_is_rejected(client):
    assert client.get("/sessions").status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_logout_clears_session(client):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_admin_can_provision_user_who_can_then_login(client):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    created = client.post(
        "/auth/users",
        json={"email": "member@example.com", "password": "memberpass"},
    )
    assert created.status_code == 201
    assert created.json()["is_admin"] is False

    client.post("/auth/logout")
    assert _login(client, "member@example.com", "memberpass").status_code == 200


def test_duplicate_email_is_rejected(client):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    assert client.post(
        "/auth/users",
        json={"email": TEST_USER_EMAIL, "password": "anotherpass"},
    ).status_code == 409


def test_non_admin_cannot_provision_users(client):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    client.post(
        "/auth/users",
        json={"email": "plain@example.com", "password": "plainpass"},
    )
    client.post("/auth/logout")
    _login(client, "plain@example.com", "plainpass")

    resp = client.post(
        "/auth/users",
        json={"email": "blocked@example.com", "password": "blockedpass"},
    )
    assert resp.status_code == 403


def test_sessions_are_private_per_user(client):
    # User A creates a session.
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    created = client.post("/sessions", json={"llm_model": "gpt-5"})
    assert created.status_code == 200
    app_session_id = created.json()["app_session_id"]

    # Provision and switch to user B.
    client.post(
        "/auth/users",
        json={"email": "userb@example.com", "password": "userbpass"},
    )
    client.post("/auth/logout")
    _login(client, "userb@example.com", "userbpass")

    # B cannot see A's session, and B's own list is empty.
    status = client.get("/sessions/status", params={"app_session_id": app_session_id})
    assert status.status_code == 404
    assert client.get("/sessions").json()["sessions"] == []


def test_cannot_remove_last_admin(client):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    admin = db.get_user_by_email(TEST_USER_EMAIL)
    resp = client.patch(f"/auth/users/{admin['user_id']}", json={"is_active": False})
    assert resp.status_code == 400
