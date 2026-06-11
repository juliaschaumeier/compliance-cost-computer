import asyncio

import pytest

from backend.core import db, llm_monitor
from backend.core.auth import ApiKeys
from backend.core.deep_research_cases import CASE_GROUP_RESEARCH_PURPOSE
from backend.core.deep_research_service import DeepResearchResult
from backend.routers import sessions as sessions_router


def test_parse_pipe_table_accepts_basic_markdown_table():
    table = (
        "| Fallgruppe | Wert | Hinweis |\n"
        "| --- | ---: | :--- |\n"
        "| A | 10 | plausibel |\n"
        "| B | 20 | Quelle \\| Zusatz |"
    )

    assert sessions_router._parse_pipe_table(table) == [
        ["Fallgruppe", "Wert", "Hinweis"],
        ["A", "10", "plausibel"],
        ["B", "20", "Quelle | Zusatz"],
    ]


def test_parse_pipe_table_rejects_pipe_paragraph_and_malformed_table():
    assert sessions_router._parse_pipe_table("Absatz mit A | B im Text.") is None
    malformed = "| A | B |\n| --- | --- |\n| 1 | 2 | 3 |"
    assert sessions_router._parse_pipe_table(malformed) is None


def test_research_pdf_inline_markup_renders_bold_and_escapes_text():
    rendered = sessions_router._research_pdf_inline_markup(
        "**Erstanerkennung** & <Prüfung> https://www.destatis.de/test."
    )

    assert rendered.startswith("<b>Erstanerkennung</b> &amp; &lt;Prüfung&gt;")
    assert '<link href="https://www.destatis.de/test">' in rendered
    assert rendered.endswith("</link>.")


def test_format_research_report_metadata_lines_includes_disclaimer_and_cost():
    lines = sessions_router._format_research_report_metadata_lines(
        {
            "app_session_id": "DR-REPORT",
            "generated_at": "2026-06-01 12:00",
            "agent": "deep-research-preview-04-2026",
            "status": "parsed",
            "input_tokens": 100,
            "output_tokens": 200,
            "thought_tokens": 30,
            "total_tokens": 330,
            "estimated_cost_usd": 0.0042,
        }
    )

    joined = "\n".join(lines)
    assert "KI-gestuetzt" in joined
    assert "DR-REPORT" in joined
    assert "deep-research-preview-04-2026" in joined
    assert "in 100 / out 200 / thinking 30 / total 330" in joined
    assert "$0.0042" in joined


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
        "elapsed_seconds": None,
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
    assert isinstance(locked.json()["elapsed_seconds"], int)

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
        input_tokens=100,
        output_tokens=200,
        thought_tokens=30,
        total_tokens=330,
        estimated_cost_usd=0.0042,
        report_md=(
            "# Bericht\n\n"
            "Eine belegte Zahl mit Quelle https://www.destatis.de/DE/Home/_inhalt.html.\n\n"
            "| Fallgruppe | Wert |\n"
            "| --- | --- |\n"
            "| **A** | 10 |\n"
            "| B | 20 |"
        ),
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


def test_deep_research_publishes_llm_monitor_lifecycle(monkeypatch):
    app_session_id = "DR-MONITOR"
    session_id, _ = db.upsert_session(app_session_id, "test-model")

    monkeypatch.setattr(
        sessions_router,
        "build_deep_research_cases_prompt",
        lambda *, app_session_id: "prompt",
    )
    monkeypatch.setattr(
        sessions_router,
        "apply_deep_research_case_metrics",
        lambda **_kwargs: 1,
    )

    async def fake_run_deep_research(*_args, **kwargs):
        kwargs["on_interaction_started"](
            "deep-research-preview-04-2026",
            "interaction-1",
        )
        running_run = db.get_latest_deep_research_run(
            session_id,
            CASE_GROUP_RESEARCH_PURPOSE,
        )
        assert running_run is not None
        assert running_run["status"] == "running"
        assert running_run["interaction_id"] == "interaction-1"
        return DeepResearchResult(
            agent="deep-research-preview-04-2026",
            interaction_id="interaction-1",
            report_text='{"prozesse": []}',
            response_json={"status": "completed"},
            input_tokens=100,
            output_tokens=200,
            thought_tokens=30,
            total_tokens=330,
            estimated_cost_usd=0.0042,
        )

    monkeypatch.setattr(sessions_router, "run_deep_research", fake_run_deep_research)

    asyncio.run(
        sessions_router._run_case_group_deep_research(
            app_session_id=app_session_id,
            session_id=session_id,
            api_keys=ApiKeys(gemini_api_key="test"),
        )
    )

    events = asyncio.run(llm_monitor.get_recent_events(app_session_id, limit=10))
    event_types = [event["event_type"] for event in events]
    assert "llm_query_started" in event_types
    assert "llm_query_succeeded" in event_types
    assert "llm_apply_succeeded" in event_types

    pending = asyncio.run(llm_monitor.get_pending(app_session_id))
    assert pending == []

    run = db.get_latest_deep_research_run(session_id, CASE_GROUP_RESEARCH_PURPOSE)
    assert run is not None
    attempt_id = f"deep_research:{run['research_run_id']}"
    succeeded = next(event for event in events if event["event_type"] == "llm_query_succeeded")
    assert succeeded["attempt_id"] == attempt_id
    assert succeeded["prompt_id"] == "deep_research_case_group_metrics"
    assert succeeded["provider"] == "gemini"
    assert succeeded["model"] == "deep-research-preview-04-2026"
    assert succeeded["input_tokens"] == 100
    assert succeeded["hidden_thinking_tokens"] == 30
    assert succeeded["estimated_cost_usd"] == 0.0042
