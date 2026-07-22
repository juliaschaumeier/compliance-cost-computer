"""Auth + per-user ownership tests exercising the real login flow.

The autouse ``isolated_db`` fixture normally overrides ``get_current_user`` so the
rest of the suite runs authenticated. These tests pop that override to drive the
genuine cookie-based login and ownership checks.
"""

import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.core import auth as auth_core
from backend.core import config, db
from backend.main import app
from backend.routers import regulations as regulations_router

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
    assert re.fullmatch(r"[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{6}", app_session_id)

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


def test_bootstrap_admin_does_not_add_second_admin_when_admin_exists(client, monkeypatch):
    monkeypatch.setattr(config.settings, "admin_bootstrap_email", "bootstrap@example.com")
    monkeypatch.setattr(config.settings, "admin_bootstrap_password", "bootstrappass")

    auth_core.ensure_bootstrap_admin()

    assert db.get_user_by_email("bootstrap@example.com") is None
    assert db.count_admins() == 1


def test_regulation_summary_requires_owned_session(client):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    db.insert_law("summary-proposed.txt", "neuer entwurf")

    missing_session = client.post(
        "/regulations/summary",
        json={
            "filename": "summary-proposed.txt",
            "model": "test-model",
        },
    )
    assert missing_session.status_code == 400

    created = client.post("/sessions", json={"llm_model": "test-model"})
    assert created.status_code == 200
    app_session_id = created.json()["app_session_id"]
    client.post(
        "/auth/users",
        json={"email": "summary-other@example.com", "password": "otherpass"},
    )
    client.post("/auth/logout")
    _login(client, "summary-other@example.com", "otherpass")

    cross_user = client.post(
        "/regulations/summary",
        json={
            "filename": "summary-proposed.txt",
            "app_session_id": app_session_id,
            "model": "test-model",
        },
    )
    assert cross_user.status_code == 404


def test_regulation_summary_succeeds_for_owned_session(client, monkeypatch):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    db.insert_law("owned-summary-current.txt", "aktuelles gesetz")
    db.insert_law("owned-summary-proposed.txt", "neuer entwurf")
    created = client.post("/sessions", json={"llm_model": "test-model"})
    assert created.status_code == 200
    app_session_id = created.json()["app_session_id"]

    async def fake_query_llm(*_args, **_kwargs):
        return '{"title": "Kurz", "blurb": "Ein Satz.", "summary": "Zusammenfassung."}'

    monkeypatch.setattr(regulations_router, "query_llm", fake_query_llm)

    response = client.post(
        "/regulations/summary",
        json={
            "filename": "owned-summary-proposed.txt",
            "current_filename": "owned-summary-current.txt",
            "app_session_id": app_session_id,
            "model": "test-model",
        },
    )

    assert response.status_code == 200
    session = db.get_session_by_app_id(app_session_id)
    assert session["proposed_law_id"] is not None


def test_uploaded_laws_are_private_but_builtin_laws_are_shared(client):
    _login(client, TEST_USER_EMAIL, TEST_USER_PASSWORD)
    db.insert_law("builtin-law.txt", "shared fixture", is_builtin=True)

    upload = client.post(
        "/regulations/upload",
        files={"file": ("private-law.txt", b"user a law", "text/plain")},
    )
    assert upload.status_code == 200
    user_a_files = set(client.get("/regulations").json()["files"])
    assert {"builtin-law.txt", "private-law.txt"}.issubset(user_a_files)

    client.post(
        "/auth/users",
        json={"email": "law-other@example.com", "password": "otherpass"},
    )
    client.post("/auth/logout")
    _login(client, "law-other@example.com", "otherpass")

    user_b_files = set(client.get("/regulations").json()["files"])
    assert "builtin-law.txt" in user_b_files
    assert "private-law.txt" not in user_b_files

    own_session = client.post("/sessions", json={"llm_model": "test-model"})
    assert own_session.status_code == 200
    hidden_private_law = client.post(
        "/regulations/summary",
        json={
            "filename": "private-law.txt",
            "app_session_id": own_session.json()["app_session_id"],
            "model": "test-model",
        },
    )
    assert hidden_private_law.status_code == 404

    same_private_name = client.post(
        "/regulations/upload",
        files={"file": ("private-law.txt", b"user b law", "text/plain")},
    )
    assert same_private_name.status_code == 200

    builtin_conflict = client.post(
        "/regulations/upload",
        files={"file": ("builtin-law.txt", b"shadow builtin", "text/plain")},
    )
    assert builtin_conflict.status_code == 409


def test_legacy_ownerless_laws_are_hidden_but_resource_builtins_are_shared(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "legacy-laws.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE laws (
            document_id INTEGER PRIMARY KEY,
            file_name TEXT NOT NULL,
            law_text TEXT NOT NULL,
            text_length INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL DEFAULT current_timestamp,
            owner_user_id INTEGER,
            is_builtin INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        INSERT INTO laws (file_name, law_text, text_length, owner_user_id, is_builtin)
        VALUES ('legacy-upload.txt', 'alter Upload', 12, NULL, 1)
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(config.settings, "db_path", db_path)
    db.init_db()

    visible = set(db.list_law_file_names(owner_user_id=1))
    assert "legacy-upload.txt" not in visible
    assert {
        "arbeitstagepauschale_gueltig.txt",
        "arbeitstagepauschale_vorschlag.txt",
    }.issubset(visible)
