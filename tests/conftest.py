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
def enable_mirror_feature(monkeypatch):
    """Aktiviert das Mirror-Feature fuer Tests, die es brauchen.

    Das Feature ist per Default deaktiviert (siehe
    config.mirror_matching_enabled). Tests, die Mirror-Matching,
    deterministischen Sync oder Propagation pruefen, muessen den Schalter
    explizit anfordern.
    """
    monkeypatch.setattr(config.settings, "mirror_matching_enabled", True)
    yield
