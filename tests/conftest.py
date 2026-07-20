import pytest
from fastapi.testclient import TestClient

from backend.core import auth as auth_core
from backend.core import config, db
from backend.main import app


# Identity that the auth dependency is overridden to represent in tests. Sessions
# created during tests are owned by this user so ownership checks line up without
# every test having to perform a real login.
TEST_USER_ID = 1
TEST_USER_EMAIL = "tester@example.com"
TEST_USER_PASSWORD = "password123"


def override_current_user() -> auth_core.AuthUser:
    return auth_core.AuthUser(
        user_id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        is_admin=True,
    )


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    monkeypatch.setattr(config.settings, "auth_secret_key", "test-secret-key")
    db.init_db()
    # Seed the user the overridden auth dependency represents.
    if db.get_user_by_email(TEST_USER_EMAIL) is None:
        db.create_user(
            TEST_USER_EMAIL,
            auth_core.hash_password(TEST_USER_PASSWORD),
            is_admin=True,
        )

    # Default the owner of any test-created session (the ~140 direct
    # upsert_session/ensure_session calls) to the test user so ownership-gated
    # endpoints resolve. Explicit owners (e.g. create_owned_session) are honored.
    real_upsert_session = db.upsert_session

    def _upsert_session_with_owner(app_session_id, llm_model, owner_user_id=None):
        # Only default the owner when the seeded test user exists in the active DB.
        # Some pure-DB tests repoint db_path to a fresh database without the user;
        # stamping a non-existent owner there would violate the FK.
        if owner_user_id is None and db.get_user_by_id(TEST_USER_ID) is not None:
            owner_user_id = TEST_USER_ID
        return real_upsert_session(app_session_id, llm_model, owner_user_id=owner_user_id)

    monkeypatch.setattr(db, "upsert_session", _upsert_session_with_owner)

    # Authenticate every request as the seeded test user by default.
    app.dependency_overrides[auth_core.get_current_user] = override_current_user
    yield
    app.dependency_overrides.pop(auth_core.get_current_user, None)


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    with TestClient(app) as client:
        yield client
