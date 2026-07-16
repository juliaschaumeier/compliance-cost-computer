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


def test_research_pdf_inline_markup_deemphasizes_long_fallgruppe_bold_text():
    rendered = sessions_router._research_pdf_inline_markup(
        "**Fallgruppe 1 Unternehmen mit besonders langen Melde- und Nachweispflichten**"
    )

    assert "<b>" not in rendered
    assert "Fallgruppe 1 Unternehmen" in rendered


def test_research_pdf_inline_markup_renders_italic_and_keeps_unbalanced_stars():
    rendered = sessions_router._research_pdf_inline_markup(
        "*Fallzahl:* Jährlich sind 2 800 000 Fälle * pro Betrieb zu erwarten."
    )

    assert rendered.startswith("<i>Fallzahl:</i> Jährlich")
    assert "Fälle * pro Betrieb" in rendered


def test_research_pdf_inline_markup_combines_bold_and_italic():
    rendered = sessions_router._research_pdf_inline_markup(
        "**Zu lfd. Nr. 4.1.1:** *Fallzahl:* 2 800 000"
    )

    assert rendered == "<b>Zu lfd. Nr. 4.1.1:</b> <i>Fallzahl:</i> 2 800 000"


def test_research_pdf_inline_markup_renders_html_line_breaks_in_table_cells():
    rendered = sessions_router._research_pdf_inline_markup(
        "Digital: 11 Min.<br>Stationär: 14 Min.<br />Papier: 20 Min."
    )

    assert rendered == (
        "Digital: 11 Min.<br/>Stationär: 14 Min.<br/>Papier: 20 Min."
    )


def test_research_pdf_inline_markup_still_escapes_other_html_tags():
    rendered = sessions_router._research_pdf_inline_markup("Prüfung <script> und <b>")

    assert rendered == "Prüfung &lt;script&gt; und &lt;b&gt;"


def test_parse_markdown_list_reads_bullets_and_continuation_lines():
    block = "- Erster Punkt\n  mit Fortsetzung\n* Zweiter Punkt\n  - Unterpunkt"

    assert sessions_router._parse_markdown_list(block) == (
        "",
        [
            (0, "Erster Punkt mit Fortsetzung"),
            (0, "Zweiter Punkt"),
            (1, "Unterpunkt"),
        ],
    )


def test_parse_markdown_list_keeps_paragraph_that_precedes_the_bullets():
    block = "**Zu lfd. Nr. 4.1.1:** Einhaltung\n* *Fallzahl:* 2 800 000 Fälle"

    assert sessions_router._parse_markdown_list(block) == (
        "**Zu lfd. Nr. 4.1.1:** Einhaltung",
        [(0, "*Fallzahl:* 2 800 000 Fälle")],
    )


def test_parse_markdown_list_rejects_plain_paragraph():
    assert sessions_router._parse_markdown_list("Ein Absatz ohne Aufzählung.") is None


def test_markdown_lists_render_as_bullets_in_pdf(monkeypatch):
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    captured: dict[str, list] = {}

    def fake_build(self, story, *args, **kwargs):
        captured["story"] = story

    monkeypatch.setattr(SimpleDocTemplate, "build", fake_build)

    report_md = (
        "**Zu lfd. Nr. 4.1.1:** Einhaltung verbraucherschützender Vorgaben\n"
        "* *Fallzahl:* Jährlich 2 800 000 Fälle\n"
        "* *Digitaler Abschluss:* 1 200 000 Fälle"
    )
    sessions_router._render_research_report_pdf(report_md, "Titel")

    paragraphs = [item for item in captured["story"] if isinstance(item, Paragraph)]
    lead = next(
        item
        for item in paragraphs
        if item.style.name == "BodyText" and "lfd. Nr." in item.text
    )
    bullets = [item for item in paragraphs if item.style.name == "ResearchListItem0"]

    assert lead.text.startswith("<b>Zu lfd. Nr. 4.1.1:</b> Einhaltung")
    assert len(bullets) == 2
    assert bullets[0].text.startswith("<i>Fallzahl:</i> Jährlich")
    assert all("*" not in bullet.text for bullet in bullets)


def test_render_research_report_pdf_builds_document_with_lists_and_markup():
    report_md = "\n\n".join(
        [
            "# 4. Erfüllungsaufwand",
            "### Davon Bürokratiekosten aus Informationspflichten",
            "**Zu lfd. Nr. 4.1.1:** *Fallzahl:* 2 800 000 Fälle",
            "- Erster Punkt\n  - Unterpunkt",
        ]
    )

    pdf = sessions_router._render_research_report_pdf(report_md, "Titel")

    assert pdf.startswith(b"%PDF")


def test_research_pdf_heading_detection_rejects_long_heading_like_paragraphs():
    assert sessions_router._is_research_pdf_heading("# E. Erfüllungsaufwand") is True
    assert sessions_router._is_research_pdf_heading("# 4. Erfüllungsaufwand") is True
    assert (
        sessions_router._is_research_pdf_heading(
            "### 1. Erstanerkennungsverfahren (Fallgruppe 1)"
        )
        is False
    )
    assert (
        sessions_router._is_research_pdf_heading(
            "### Vorgabe 1: Sehr lange Beschreibung der Fallgruppe mit mehreren "
            "Detailangaben zu Antragsverfahren, Nachweisen, Prüfungen und "
            "organisatorischen Sonderfällen"
        )
        is False
    )


def test_section_4_headings_render_as_headings_in_pdf(monkeypatch):
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    captured: dict[str, list] = {}

    def fake_build(self, story, *args, **kwargs):
        captured["story"] = story

    monkeypatch.setattr(SimpleDocTemplate, "build", fake_build)

    report_md = "\n\n".join(
        [
            "# E. Erfüllungsaufwand",
            "# 4. Erfüllungsaufwand",
            "## 4.1 Erfüllungsaufwand für Bürgerinnen und Bürger",
            "## 4.2 Erfüllungsaufwand für die Wirtschaft",
            "## 4.3 Erfüllungsaufwand der Verwaltung",
            "### 1. Erstanerkennungsverfahren (Fallgruppe 1)",
        ]
    )
    sessions_router._render_research_report_pdf(report_md, "Titel")

    style_by_text = {
        getattr(item, "text", ""): item.style.name
        for item in captured["story"]
        if isinstance(item, Paragraph)
    }
    for heading in (
        "E. Erfüllungsaufwand",
        "4. Erfüllungsaufwand",
        "4.1 Erfüllungsaufwand für Bürgerinnen und Bürger",
        "4.2 Erfüllungsaufwand für die Wirtschaft",
        "4.3 Erfüllungsaufwand der Verwaltung",
    ):
        assert style_by_text.get(heading) == "Heading2"
    assert (
        style_by_text.get("1. Erstanerkennungsverfahren (Fallgruppe 1)") == "BodyText"
    )


def test_sub_headings_render_smaller_than_section_headings(monkeypatch):
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    captured: dict[str, list] = {}

    def fake_build(self, story, *args, **kwargs):
        captured["story"] = story

    monkeypatch.setattr(SimpleDocTemplate, "build", fake_build)

    report_md = "\n\n".join(
        [
            "## E.2 Erfüllungsaufwand für die Wirtschaft",
            "### Davon Bürokratiekosten aus Informationspflichten",
        ]
    )
    sessions_router._render_research_report_pdf(report_md, "Titel")

    style_by_text = {
        getattr(item, "text", ""): item.style
        for item in captured["story"]
        if isinstance(item, Paragraph)
    }
    section = style_by_text["E.2 Erfüllungsaufwand für die Wirtschaft"]
    sub_section = style_by_text["Davon Bürokratiekosten aus Informationspflichten"]

    assert section.name == "Heading2"
    assert sub_section.name == "ResearchSubHeading"
    assert sub_section.fontSize < section.fontSize
    assert sub_section.fontName == section.fontName


def test_strip_markdown_heading_prefix_for_demoted_body_text():
    assert (
        sessions_router._strip_markdown_heading_prefix(
            "### 1. Erstanerkennungsverfahren (Fallgruppe 1) Die erstmalige Prüfung"
        )
        == "1. Erstanerkennungsverfahren (Fallgruppe 1) Die erstmalige Prüfung"
    )


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


def test_format_compliance_export_metadata_lines_includes_scope_disclaimer():
    lines = sessions_router._format_compliance_export_metadata_lines(
        {
            "app_session_id": "COMP-REPORT",
            "generated_at": "2026-06-01 12:00",
            "model": "test-model",
            "provider": "openai",
            "reuse_status": "neu generiert",
            "deep_research_status": "Nicht verwendet",
            "user_edit_status": "Keine bearbeiteten EA-Werte im Quellstand.",
            "source_snapshot_sha256": "abcdef123456",
        }
    )

    joined = "\n".join(lines)
    assert "jaehrlichen Erfuellungsaufwand" in joined
    assert "Einmaliger Erfuellungsaufwand ist nicht Gegenstand" in joined
    assert "Bundesebene und Landesebene" in joined


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


def test_cancelled_deep_research_harvest_stores_audit_report(monkeypatch):
    app_session_id = "DR-CANCEL-HARVEST"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    run_id = db.create_deep_research_run(
        session_id=session_id,
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="deep-research-test",
        status="running",
        prompt_text="prompt",
    )
    db.update_deep_research_run(
        run_id,
        status="cancelled",
        interaction_id="interaction-1",
        error="cancelled locally",
    )

    async def fake_harvest(*_args, **_kwargs):
        return DeepResearchResult(
            agent="deep-research-test",
            interaction_id="interaction-1",
            report_text="late report",
            response_json={"status": "completed"},
            input_tokens=10,
            output_tokens=20,
            thought_tokens=5,
            total_tokens=35,
            estimated_cost_usd=0.12,
        )

    monkeypatch.setattr(
        sessions_router,
        "harvest_deep_research_interaction",
        fake_harvest,
    )

    asyncio.run(
        sessions_router._harvest_cancelled_deep_research_run(
            app_session_id=app_session_id,
            session_id=session_id,
            research_run_id=run_id,
            api_keys=ApiKeys(gemini_api_key="test"),
        )
    )

    run = db.get_deep_research_run(run_id)
    assert run is not None
    assert run["status"] == "cancelled_harvested"
    assert run["report_md"] == "late report"
    assert run["parsed_at"] is None
    assert "audit only" in run["error"]


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
