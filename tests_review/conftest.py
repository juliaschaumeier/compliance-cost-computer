import pytest
from fastapi.testclient import TestClient

from backend.core import config, db
from backend.main import app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    yield


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def session_id() -> int:
    sid, _created, _model = db.ensure_session("test-app-session", llm_model="gpt-4o-mini")
    return sid
