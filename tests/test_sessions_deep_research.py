import asyncio

import pytest

from backend.core import db
from backend.core.auth import ApiKeys
from backend.core.deep_research_cases import CASE_GROUP_RESEARCH_PURPOSE
from backend.routers import sessions as sessions_router


def test_case_group_research_toggle_locks_after_run_started(test_client):
    app_session_id = "DR-TOGGLE"
    session_id, _ = db.upsert_session(app_session_id, "test-model")

    initial = test_client.get(
        "/sessions/case-group-research",
        params={"app_session_id": app_session_id},
    )
    assert initial.status_code == 200
    assert initial.json() == {
        "app_session_id": app_session_id,
        "enabled": False,
        "status": "idle",
        "locked": False,
    }

    enabled = test_client.post(
        "/sessions/case-group-research",
        json={"app_session_id": app_session_id, "enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    db.create_deep_research_run(
        session_id=session_id,
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="running",
    )
    locked = test_client.get(
        "/sessions/case-group-research",
        params={"app_session_id": app_session_id},
    )
    assert locked.status_code == 200
    assert locked.json()["status"] == "running"
    assert locked.json()["locked"] is True

    blocked = test_client.post(
        "/sessions/case-group-research",
        json={"app_session_id": app_session_id, "enabled": False},
    )
    assert blocked.status_code == 409


def test_deep_research_report_downloads_markdown_and_pdf(test_client):
    app_session_id = "DR-REPORT"
    session_id, _ = db.upsert_session(app_session_id, "test-model")

    missing = test_client.get(
        "/sessions/deep-research-report",
        params={"app_session_id": app_session_id},
    )
    assert missing.status_code == 404

    running_id = db.create_deep_research_run(
        session_id=session_id,
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="running",
    )
    not_ready = test_client.get(
        "/sessions/deep-research-report",
        params={"app_session_id": app_session_id},
    )
    assert not_ready.status_code == 409

    db.update_deep_research_run(
        running_id,
        status="completed",
        report_md="# Bericht\n\nEine belegte Zahl.",
    )
    markdown = test_client.get(
        "/sessions/deep-research-report",
        params={"app_session_id": app_session_id, "format": "md"},
    )
    assert markdown.status_code == 200
    assert markdown.text.startswith("# Bericht")
    assert markdown.headers["content-type"].startswith("text/markdown")

    pdf = test_client.get(
        "/sessions/deep-research-report",
        params={"app_session_id": app_session_id, "format": "pdf"},
    )
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"


def test_deep_research_cancellation_marks_run_terminal(monkeypatch):
    app_session_id = "DR-CANCEL"
    session_id, _ = db.upsert_session(app_session_id, "test-model")

    monkeypatch.setattr(
        sessions_router,
        "build_deep_research_cases_prompt",
        lambda *, app_session_id: "prompt",
    )

    async def fake_run_deep_research(*_args, **_kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(sessions_router, "run_deep_research", fake_run_deep_research)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            sessions_router._run_case_group_deep_research(
                app_session_id=app_session_id,
                session_id=session_id,
                api_keys=ApiKeys(gemini_api_key="test"),
            )
        )

    run = db.get_latest_deep_research_run(session_id, CASE_GROUP_RESEARCH_PURPOSE)
    assert run is not None
    assert run["status"] == "cancelled"
    assert "cancelled" in run["error"]
