import pytest
from fastapi.testclient import TestClient

from backend.core import config, db
from backend.main import app


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    with TestClient(app) as client:
        yield client
