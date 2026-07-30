from backend.core import compliance_text_export, db
from backend.core.compliance_text_export import (
    DEEP_RESEARCH_FULL_REPORT_FALLBACK_MAX_CHARS,
    DEEP_RESEARCH_REPORT_BEFORE_JSON_FALLBACK_MAX_CHARS,
    USER_EDIT_REJECT,
    USER_EDIT_USE,
    build_compliance_export_context,
    extract_deep_research_part_1_2,
    extract_deep_research_report_text_for_export,
)
from backend.core.prompts import PromptId, render_prompt
from backend.core.deep_research_cases import CASE_GROUP_RESEARCH_PURPOSE
from backend.core.llm_service import LlmResult
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION
from tests.activity_helpers import ea_payload_for_session
from backend.routers import sessions as sessions_router


def _seed_completed_session(app_session_id: str) -> dict:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    regulation_id = db.insert_regulation(
        session_id,
        "§ 1",
        "Vorgabe",
        applies_to_administration=True,
    )
    process_id = db.insert_process(
        session_id,
        "Prozess",
        "Beschreibung Prozess",
        norm_addressee=ADMINISTRATION,
    )
    db.update_regulation_process(
        regulation_id=regulation_id,
        process_id=process_id,
        norm_addressee=ADMINISTRATION,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe",
        "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Taetigkeit",
        "Beschreibung Taetigkeit",
        norm_addressee=ADMINISTRATION,
    )
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=case_group_id,
        norm_addressee=ADMINISTRATION,
        addressees_current=10,
        annual_frequency_current=1,
        addressees_proposed=12,
        annual_frequency_proposed=1,
        case_metric_research_json={
            "confidence": {"anzahl_betroffene_vorschlag": "medium"},
            "erklaerungen": {
                "anzahl_betroffene_vorschlag": "12 Faelle laut Schaetzung."
            },
        },
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=ADMINISTRATION,
        hourly_rates_current={"a": 40, "b": None, "c": None, "d": None},
        time_required_current={"a": 20, "b": None, "c": None, "d": None},
        expenses_current=1,
        hourly_rates_proposed={"a": 40, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=2,
        execution_per_case=True,
    )
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        total_cost=100,
        bureaucracy_cost=10,
        total_time_minutes=360,
        total_expenses=20,
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_id}",
            title="Taetigkeit",
            text="Beschreibung Taetigkeit",
            column=5,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
    )
    return {
        "session_id": session_id,
        "case_group_id": case_group_id,
        "step_id": step_id,
    }


def test_export_reflects_row_wage_override_and_warns(test_client):
    # A row-based wage override must appear in the export at the override rate, be
    # flagged as a user edit (so the export warns), and keep the cost consistent
    # with the displayed rate. "reject" falls back to the model rate + model cost.
    seeded = _seed_completed_session("COMP-WAGE-OVR")
    session_id = seeded["session_id"]
    step_id = seeded["step_id"]
    db.replace_process_step_personnel_effort(
        session_id,
        ADMINISTRATION,
        step_id,
        [
            {
                "period": "current",
                "qualification": "gehobener_dienst",
                "wage_source_kind": "verwaltungsebene",
                "wage_source_value": "bund",
                "time_required_in_min": 20,
                "model_hourly_rate": 40.4,
            },
        ],
    )
    # Dual-write reality: slot columns mirror the row so the cost-input gate passes.
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=ADMINISTRATION,
        hourly_rates_current={"a": None, "b": 40.4, "c": None, "d": None},
        time_required_current={"a": None, "b": 20, "c": None, "d": None},
        expenses_current=None,
        hourly_rates_proposed={"a": None, "b": None, "c": None, "d": None},
        time_required_proposed={"a": None, "b": None, "c": None, "d": None},
        expenses_proposed=None,
        execution_per_case=True,
    )
    db.upsert_session_wage_rate_override(
        session_id, ADMINISTRATION, "verwaltungsebene", "bund", "gehobener_dienst", 100.0
    )

    use = build_compliance_export_context(
        app_session_id="COMP-WAGE-OVR",
        session_id=session_id,
        user_edit_policy=USER_EDIT_USE,
    )
    assert use.has_user_edits is True
    adm = next(
        a for a in use.snapshot["normadressaten"] if a["normadressat"] == ADMINISTRATION
    )
    rate = adm["lohnsaetze"]["werte"]["b"]
    assert rate["wert"] == 100.0
    assert rate["value_source"] == "user_edited"
    step = adm["prozesse"][0]["fallgruppen"][0]["taetigkeiten"][0]
    assert step["stundenloehne"]["b_current"] == 100.0
    assert abs(step["kosten"]["gueltig"] - 100.0 * 20 / 60) < 0.01

    reject = build_compliance_export_context(
        app_session_id="COMP-WAGE-OVR",
        session_id=session_id,
        user_edit_policy=USER_EDIT_REJECT,
    )
    adm_r = next(
        a
        for a in reject.snapshot["normadressaten"]
        if a["normadressat"] == ADMINISTRATION
    )
    assert adm_r["lohnsaetze"]["werte"]["b"]["wert"] == 40.4
    step_r = adm_r["prozesse"][0]["fallgruppen"][0]["taetigkeiten"][0]
    assert step_r["stundenloehne"]["b_current"] == 40.4
    assert abs(step_r["kosten"]["gueltig"] - 40.4 * 20 / 60) < 0.01


def test_reject_export_does_not_persist_model_costs(test_client):
    # Regression: aggregate_addressee_costs() must be read-only. Building the
    # compliance export with USER_EDIT_REJECT recomputes model-only costs; it must
    # NOT write those back over the persisted live (user-edited) process/case
    # costs. Before the read-only fix, the reject export re-persisted model costs,
    # silently drifting the live session away from what the user sees.
    seeded = _seed_completed_session("COMP-REJECT-NOPERSIST")
    session_id = seeded["session_id"]
    case_group_id = seeded["case_group_id"]
    step_id = seeded["step_id"]

    # A row wage override (100) that differs from the model rate (40.4), so the
    # edited live cost is distinguishable from the model-only cost.
    db.replace_process_step_personnel_effort(
        session_id,
        ADMINISTRATION,
        step_id,
        [
            {
                "period": "current",
                "qualification": "gehobener_dienst",
                "wage_source_kind": "verwaltungsebene",
                "wage_source_value": "bund",
                "time_required_in_min": 20,
                "model_hourly_rate": 40.4,
            },
        ],
    )
    # Dual-write reality: slot columns mirror the row so the cost-input gate passes.
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=ADMINISTRATION,
        hourly_rates_current={"a": None, "b": 40.4, "c": None, "d": None},
        time_required_current={"a": None, "b": 20, "c": None, "d": None},
        expenses_current=None,
        hourly_rates_proposed={"a": None, "b": None, "c": None, "d": None},
        time_required_proposed={"a": None, "b": None, "c": None, "d": None},
        expenses_proposed=None,
        execution_per_case=True,
    )
    db.upsert_session_wage_rate_override(
        session_id, ADMINISTRATION, "verwaltungsebene", "bund", "gehobener_dienst", 100.0
    )

    # Persist the live (edited) costs.
    resp = test_client.post(
        "/costs/compute", json={"app_session_id": "COMP-REJECT-NOPERSIST"}
    )
    assert resp.status_code == 200

    process_id = db.list_processes_for_session_and_addressee(session_id, ADMINISTRATION)[0][
        "process_id"
    ]

    def _persisted_costs():
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT cost FROM case_groups WHERE case_group_id = ?", (case_group_id,)
        )
        case_group_cost = cur.fetchone()["cost"]
        cur.execute("SELECT cost FROM processes WHERE process_id = ?", (process_id,))
        process_cost = cur.fetchone()["cost"]
        conn.close()
        return case_group_cost, process_cost

    before = _persisted_costs()
    # The override (100) drives the live cost, so it must differ from the model
    # cost (40.4) the reject export would recompute - otherwise the test is blind.
    assert before[0] is not None and before[0] != 0

    build_compliance_export_context(
        app_session_id="COMP-REJECT-NOPERSIST",
        session_id=session_id,
        user_edit_policy=USER_EDIT_REJECT,
    )

    assert _persisted_costs() == before


def test_compliance_text_examples_are_seeded_from_resources(test_client):
    examples = db.list_compliance_text_examples()

    assert len(examples) == 3
    assert all(example["source_path"].endswith(".md") for example in examples)
    assert all(example["body_md"].strip() for example in examples)


def test_compliance_text_examples_are_seeded_once_and_reads_do_not_update_timestamps(
    test_client,
):
    examples = db.list_compliance_text_examples()
    first_updated_at = [example["updated_at"] for example in examples]

    reread = db.list_compliance_text_examples()

    assert [example["updated_at"] for example in reread] == first_updated_at


def test_compliance_text_seed_does_not_overwrite_existing_examples(test_client):
    conn = db.get_conn()
    try:
        conn.execute(
            """
            UPDATE compliance_text_examples
            SET title = ?, body_md = ?
            WHERE example_id = (
                SELECT example_id FROM compliance_text_examples ORDER BY sort_order LIMIT 1
            )
            """,
            ("DB Beispiel", "DB ist Quelle der Wahrheit."),
        )
        conn.commit()
    finally:
        conn.close()

    db.init_db()
    examples = db.list_compliance_text_examples()

    assert examples[0]["title"] == "DB Beispiel"
    assert examples[0]["body_md"] == "DB ist Quelle der Wahrheit."


def test_extract_deep_research_part_1_2_returns_fallback_on_missing_parts():
    excerpt, status = extract_deep_research_part_1_2("Nur Bericht ohne passende Teile")

    assert excerpt == ""
    assert status == "fallback"


def test_extract_deep_research_report_text_infers_rich_report_from_start():
    excerpt, status = extract_deep_research_report_text_for_export(
        "Bericht startet ohne Teil-1-Ueberschrift.\n\n"
        "## Teil 2: Begruendungszeilen\n\n"
        "Zeilen\n\n"
        "## Teil 3: Tabelle\n\n"
        "Nicht mehr Teil des Exzerpts"
    )

    assert status == "inferred_rich_report_from_start"
    assert excerpt.startswith("Bericht startet ohne Teil-1-Ueberschrift.")
    assert "## Teil 2: Begruendungszeilen" not in excerpt
    assert "## Teil 3" not in excerpt


def test_extract_deep_research_report_text_accepts_english_part_headings():
    excerpt, status = extract_deep_research_report_text_for_export(
        "# Part 1: Report\n\nText\n\n## Part 2: Lines\n\nDetails\n\n## Part 3: JSON\n\n{}"
    )

    assert status == "rich_report_extracted"
    assert "Part 1" in excerpt
    assert "Part 2" not in excerpt
    assert "Part 3" not in excerpt


def test_extract_deep_research_part_1_2_rejects_generic_numbered_sections():
    excerpt, status = extract_deep_research_part_1_2(
        "# 1. Vollstaendiger Forschungsbericht\n\nText\n\n"
        "## 2. Kurze Begruendungszeilen\n\nZeilen"
    )

    assert excerpt == ""
    assert status == "fallback"


def test_build_compliance_context_marks_user_edited_case_values(test_client):
    seeded = _seed_completed_session("COMP-EDIT")
    updated, missing = db.bulk_update_case_group_edits(
        seeded["session_id"],
        [{"case_group_id": seeded["case_group_id"], "addressees_proposed": 20}],
    )
    assert updated == 1
    assert missing == []

    context = build_compliance_export_context(
        app_session_id="COMP-EDIT",
        session_id=seeded["session_id"],
        user_edit_policy=USER_EDIT_USE,
    )

    group = context.snapshot["normadressaten"][0]["prozesse"][0]["fallgruppen"][0]
    metric = group["kennzahlen"]["addressees_proposed"]
    assert context.has_user_edits is True
    assert context.used_user_edits is True
    assert metric["wert"] == 20
    assert metric["originalwert"] == 12
    assert metric["value_source"] == "user_edited"
    assert metric["erklaerung"] == "überschrieben durch Anwender"
    assert metric["confidence"] is None
    cases_metric = group["kennzahlen"]["cases_proposed"]
    assert cases_metric["wert"] == 20
    assert cases_metric["value_source"] == "derived_from_user_edited"
    assert cases_metric["confidence"] is None


def test_build_compliance_context_marks_user_edited_pay_rates(test_client):
    seeded = _seed_completed_session("COMP-PAY-EDIT")
    changed = db.update_session_pay_rate_edits_for_addressee(
        session_id=seeded["session_id"],
        norm_addressee=ADMINISTRATION,
        administration_level="bund",
        edited={"a": 99, "b": None, "c": None, "d": None},
    )
    assert changed is True

    context = build_compliance_export_context(
        app_session_id="COMP-PAY-EDIT",
        session_id=seeded["session_id"],
        user_edit_policy=USER_EDIT_USE,
    )

    pay_rate = context.snapshot["normadressaten"][0]["lohnsaetze"]["werte"]["a"]
    assert context.has_user_edits is True
    assert context.used_user_edits is True
    assert pay_rate["wert"] == 99
    assert pay_rate["originalwert"] == 33.8
    assert pay_rate["active_session_value"] == 99
    assert pay_rate["value_source"] == "user_edited"


def test_compliance_context_hash_changes_when_prompt_examples_change(
    test_client,
    monkeypatch,
):
    seeded = _seed_completed_session("COMP-EXAMPLE-HASH")
    example = {
        "slug": "example",
        "title": "Beispiel",
        "body_md": "Erste Fassung",
        "sort_order": 1,
        "source_path": "resources/compliance_text_examples/example.md",
        "updated_at": "2026-01-01 00:00:00",
    }

    monkeypatch.setattr(
        compliance_text_export.db,
        "list_compliance_text_examples",
        lambda limit=3: [dict(example)],
    )
    first = build_compliance_export_context(
        app_session_id="COMP-EXAMPLE-HASH",
        session_id=seeded["session_id"],
    )

    example["body_md"] = "Zweite Fassung"
    second = build_compliance_export_context(
        app_session_id="COMP-EXAMPLE-HASH",
        session_id=seeded["session_id"],
    )

    assert first.snapshot_sha256 != second.snapshot_sha256
    assert first.snapshot["prompt_examples"][0]["body_sha256"] != (
        second.snapshot["prompt_examples"][0]["body_sha256"]
    )


def test_compliance_context_hash_ignores_prompt_example_updated_at(
    test_client,
    monkeypatch,
):
    seeded = _seed_completed_session("COMP-EXAMPLE-TIMESTAMP")
    example = {
        "slug": "example",
        "title": "Beispiel",
        "body_md": "Gleiche Fassung",
        "sort_order": 1,
        "source_path": "resources/compliance_text_examples/example.md",
        "updated_at": "2026-01-01 00:00:00",
    }

    monkeypatch.setattr(
        compliance_text_export.db,
        "list_compliance_text_examples",
        lambda limit=3: [dict(example)],
    )
    first = build_compliance_export_context(
        app_session_id="COMP-EXAMPLE-TIMESTAMP",
        session_id=seeded["session_id"],
    )

    example["updated_at"] = "2026-01-02 00:00:00"
    second = build_compliance_export_context(
        app_session_id="COMP-EXAMPLE-TIMESTAMP",
        session_id=seeded["session_id"],
    )

    assert first.snapshot_sha256 == second.snapshot_sha256


def test_compliance_text_export_returns_pdf_and_reuses_cached_artifact(
    test_client,
    monkeypatch,
):
    _seed_completed_session("COMP-PDF")
    calls = []

    async def fake_query_llm(prompt, *_args, **_kwargs):
        calls.append(prompt)
        assert "BT-Drs" in prompt
        assert "Fallgruppe" in prompt
        return LlmResult(
            text="# E. Erfüllungsaufwand\n\nExporttext",
            input_tokens=10,
            output_tokens=20,
            estimated_cost_usd=0.01,
        )

    monkeypatch.setattr(sessions_router, "query_llm", fake_query_llm)

    for _ in range(2):
        response = test_client.post(
            "/sessions/compliance-text-export",
            json={
                "app_session_id": "COMP-PDF",
                "model": "test-model",
                "provider": "openai",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    assert len(calls) == 1
    conn = db.get_conn()
    try:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM compliance_text_exports"
        ).fetchone()[0]
    finally:
        conn.close()
    assert row_count == 1


def test_compliance_text_export_prompt_uses_deep_research_report_text_conditionally(
    test_client,
    monkeypatch,
):
    seeded = _seed_completed_session("COMP-PDF-DR")
    run_id = db.create_deep_research_run(
        session_id=seeded["session_id"],
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="completed",
    )
    db.update_deep_research_run(
        run_id,
        report_md=(
            "## Teil 1: Vollstaendiger Forschungsbericht\n\n"
            "Konkrete Herleitung aus dem Bericht.\n\n"
            "## Teil 2: Kurze Begruendungszeilen\n\n"
            "Soll nicht in den Exportprompt.\n\n"
            "```json\n{}"
        ),
        result_json={"fallgruppen": []},
    )
    prompts = []

    async def fake_query_llm(prompt, *_args, **_kwargs):
        prompts.append(prompt)
        return LlmResult(text="# E. Erfüllungsaufwand\n\nExporttext")

    monkeypatch.setattr(sessions_router, "query_llm", fake_query_llm)

    response = test_client.post(
        "/sessions/compliance-text-export",
        json={
            "app_session_id": "COMP-PDF-DR",
            "model": "test-model",
            "provider": "openai",
        },
    )

    assert response.status_code == 200
    assert len(prompts) == 1
    prompt = prompts[0]
    assert "| Deep-Research-Bericht |" in prompt
    assert "Nutze den Deep-Research-Bericht aktiv" in prompt
    assert "Konkrete Herleitung aus dem Bericht." in prompt
    assert "Soll nicht in den Exportprompt." not in prompt
    assert "<deep_research_report>" in prompt


def test_compliance_text_export_reuses_visible_state_policy_cache(
    test_client,
    monkeypatch,
):
    seeded = _seed_completed_session("COMP-POLICY")
    db.bulk_update_case_group_edits(
        seeded["session_id"],
        [{"case_group_id": seeded["case_group_id"], "addressees_proposed": 30}],
    )
    calls = []

    async def fake_query_llm(prompt, *_args, **_kwargs):
        calls.append(prompt)
        return "# E. Erfüllungsaufwand\n\nExporttext"

    monkeypatch.setattr(sessions_router, "query_llm", fake_query_llm)

    reject = test_client.post(
        "/sessions/compliance-text-export",
        json={
            "app_session_id": "COMP-POLICY",
            "model": "test-model",
            "user_edit_policy": USER_EDIT_REJECT,
        },
    )
    assert reject.status_code == 409
    assert reject.json()["detail"]["error"] == "user_edits_present"

    for policy in (USER_EDIT_USE, USER_EDIT_USE):
        response = test_client.post(
            "/sessions/compliance-text-export",
            json={
                "app_session_id": "COMP-POLICY",
                "model": "test-model",
                "user_edit_policy": policy,
            },
        )
        assert response.status_code == 200

    assert len(calls) == 1
    conn = db.get_conn()
    try:
        policies = [
            row["user_edit_policy"]
            for row in conn.execute(
                "SELECT user_edit_policy FROM compliance_text_exports ORDER BY export_id"
            ).fetchall()
        ]
    finally:
        conn.close()
    assert policies == [USER_EDIT_USE]


def test_reset_session_ea_edits_clears_overrides_for_export(test_client):
    seeded = _seed_completed_session("COMP-RESET-EA")
    db.update_session_pay_rate_edits_for_addressee(
        session_id=seeded["session_id"],
        norm_addressee=ADMINISTRATION,
        administration_level="bund",
        edited={"a": 99, "b": None, "c": None, "d": None},
    )
    db.bulk_update_case_group_edits(
        seeded["session_id"],
        [{"case_group_id": seeded["case_group_id"], "addressees_proposed": 30}],
    )
    db.bulk_update_process_step_edits(
        seeded["session_id"],
        [{"step_id": seeded["step_id"], "expenses_proposed": 9}],
    )
    before = build_compliance_export_context(
        app_session_id="COMP-RESET-EA",
        session_id=seeded["session_id"],
        user_edit_policy=USER_EDIT_REJECT,
    )
    assert before.has_user_edits is True

    response = test_client.post(
        "/sessions/ea-edits/reset",
        json=ea_payload_for_session(
            seeded["session_id"],
            {"app_session_id": "COMP-RESET-EA"},
        ),
    )

    assert response.status_code == 200
    assert response.json()["reset_counts"] == {
        "pay_rates": 1,
        "case_groups": 1,
        "process_steps": 1,
        # NEU stores: none set in this session, so the global reset clears 0 of each.
        "wage_overrides": 0,
        "effort_time_edits": 0,
    }
    after = build_compliance_export_context(
        app_session_id="COMP-RESET-EA",
        session_id=seeded["session_id"],
        user_edit_policy=USER_EDIT_REJECT,
    )
    assert after.has_user_edits is False


def test_compliance_context_includes_deep_research_json_and_excerpt_status(test_client):
    seeded = _seed_completed_session("COMP-DR")
    run_id = db.create_deep_research_run(
        session_id=seeded["session_id"],
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="completed",
    )
    db.update_deep_research_run(
        run_id,
        report_md="# Teil 1: Bericht\n\nText\n\n## Teil 2: Zeilen\n\nWert\n\n```json\n{}",
        result_json={"prozesse": [{"prozess_id": 1}]},
    )

    context = build_compliance_export_context(
        app_session_id="COMP-DR",
        session_id=seeded["session_id"],
    )

    assert context.deep_research_run_id == run_id
    assert context.used_deep_research is True
    assert context.deep_research_excerpt_status == "rich_report_extracted"
    assert context.deep_research_report_text_included is True
    assert "Teil 1" in context.optional_deep_research_report_text
    assert "Teil 2" not in context.optional_deep_research_report_text
    assert context.snapshot["deep_research"]["result_json"] == {
        "prozesse": [{"prozess_id": 1}]
    }
    assert context.snapshot["deep_research"]["report_text_included"] is True


def test_compliance_context_uses_full_deep_research_report_fallback(test_client):
    seeded = _seed_completed_session("COMP-DR-FALLBACK")
    run_id = db.create_deep_research_run(
        session_id=seeded["session_id"],
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="completed",
    )
    db.update_deep_research_run(
        run_id,
        report_md="# Forschungsbericht\n\nKeine Teil-Ueberschriften, aber nutzbarer Kontext.",
        result_json={"fallgruppen": []},
    )

    context = build_compliance_export_context(
        app_session_id="COMP-DR-FALLBACK",
        session_id=seeded["session_id"],
    )

    assert context.deep_research_excerpt_status == "full_report_fallback"
    assert context.deep_research_report_text_included is True
    assert "vollstaendige Bericht darf nur fuer Kontext" in (
        context.optional_deep_research_report_text
    )
    assert "Keine Teil-Ueberschriften" in context.optional_deep_research_report_text
    assert context.snapshot["deep_research"]["report_excerpt_status"] == (
        "full_report_fallback"
    )


def test_compliance_context_fallback_uses_prose_before_json_without_cap(
    test_client,
    monkeypatch,
):
    assert DEEP_RESEARCH_REPORT_BEFORE_JSON_FALLBACK_MAX_CHARS == 75_000
    seeded = _seed_completed_session("COMP-DR-FALLBACK-JSON")
    run_id = db.create_deep_research_run(
        session_id=seeded["session_id"],
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="completed",
    )
    monkeypatch.setattr(
        compliance_text_export,
        "DEEP_RESEARCH_FULL_REPORT_FALLBACK_MAX_CHARS",
        20,
    )
    monkeypatch.setattr(
        compliance_text_export,
        "DEEP_RESEARCH_REPORT_BEFORE_JSON_FALLBACK_MAX_CHARS",
        200,
    )
    db.update_deep_research_run(
        run_id,
        report_md=(
            "# Forschungsbericht\n\n"
            "Dieser Berichtsteil ist deutlich laenger als die Test-Kappung.\n\n"
            "```json\n"
            '{"fallgruppen": []}\n'
            "```"
        ),
        result_json={"fallgruppen": []},
    )

    context = build_compliance_export_context(
        app_session_id="COMP-DR-FALLBACK-JSON",
        session_id=seeded["session_id"],
    )

    assert context.deep_research_excerpt_status == "full_report_fallback_before_json"
    assert context.deep_research_report_text_included is True
    assert "deutlich laenger als die Test-Kappung" in (
        context.optional_deep_research_report_text
    )
    assert "```json" not in context.optional_deep_research_report_text


def test_compliance_context_truncates_prose_before_json_fallback(
    test_client,
    monkeypatch,
):
    seeded = _seed_completed_session("COMP-DR-FALLBACK-JSON-LONG")
    run_id = db.create_deep_research_run(
        session_id=seeded["session_id"],
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="completed",
    )
    monkeypatch.setattr(
        compliance_text_export,
        "DEEP_RESEARCH_REPORT_BEFORE_JSON_FALLBACK_MAX_CHARS",
        20,
    )
    db.update_deep_research_run(
        run_id,
        report_md=("B" * 30) + "\n\n```json\n{}\n```",
        result_json={},
    )

    context = build_compliance_export_context(
        app_session_id="COMP-DR-FALLBACK-JSON-LONG",
        session_id=seeded["session_id"],
    )

    assert context.deep_research_excerpt_status == (
        "full_report_fallback_before_json_truncated"
    )
    assert context.optional_deep_research_report_text.endswith("B" * 20)
    assert "```json" not in context.optional_deep_research_report_text


def test_compliance_context_truncates_full_deep_research_report_fallback(
    test_client,
    monkeypatch,
):
    assert DEEP_RESEARCH_FULL_REPORT_FALLBACK_MAX_CHARS == 50_000
    seeded = _seed_completed_session("COMP-DR-FALLBACK-LONG")
    run_id = db.create_deep_research_run(
        session_id=seeded["session_id"],
        purpose=CASE_GROUP_RESEARCH_PURPOSE,
        agent="test-agent",
        status="completed",
    )
    monkeypatch.setattr(
        compliance_text_export,
        "DEEP_RESEARCH_FULL_REPORT_FALLBACK_MAX_CHARS",
        20,
    )
    db.update_deep_research_run(
        run_id,
        report_md="A" * 30,
        result_json={},
    )

    context = build_compliance_export_context(
        app_session_id="COMP-DR-FALLBACK-LONG",
        session_id=seeded["session_id"],
    )

    assert context.deep_research_excerpt_status == "full_report_fallback_truncated"
    assert context.optional_deep_research_report_text.endswith("A" * 20)


def test_compliance_pdf_metadata_describes_deep_research_fallback_statuses():
    base_kwargs = {
        "app_session_id": "COMP-META",
        "model": "test-model",
        "provider": "test-provider",
        "source_snapshot_sha256": "abcdef123456",
        "used_deep_research": True,
        "has_user_edits": False,
        "used_user_edits": False,
        "reused": False,
    }

    extracted = sessions_router._compliance_metadata_for_pdf(
        **base_kwargs,
        deep_research_excerpt_status="inferred_rich_report_from_start",
        deep_research_report_text_included=True,
    )
    fallback = sessions_router._compliance_metadata_for_pdf(
        **base_kwargs,
        deep_research_excerpt_status="full_report_fallback",
        deep_research_report_text_included=True,
    )
    truncated = sessions_router._compliance_metadata_for_pdf(
        **base_kwargs,
        deep_research_excerpt_status="full_report_fallback_truncated",
        deep_research_report_text_included=True,
    )
    before_json_truncated = sessions_router._compliance_metadata_for_pdf(
        **base_kwargs,
        deep_research_excerpt_status="full_report_fallback_before_json_truncated",
        deep_research_report_text_included=True,
    )
    no_report_text = sessions_router._compliance_metadata_for_pdf(
        **base_kwargs,
        deep_research_excerpt_status="not_available",
        deep_research_report_text_included=False,
    )

    assert extracted["deep_research_status"] == "DR-Berichtstext verwendet"
    assert fallback["deep_research_status"] == "Vollständiger DR-Bericht verwendet"
    assert truncated["deep_research_status"] == (
        "Gekürzter vollständiger DR-Bericht verwendet"
    )
    assert before_json_truncated["deep_research_status"] == (
        "Gekürzter vollständiger DR-Bericht verwendet"
    )
    assert no_report_text["deep_research_status"] == (
        "DR-Fallzahlen aus Sessiondaten verwendet; kein DR-Berichtstext eingebunden"
    )


def test_compliance_text_prompt_omits_deep_research_fragments_without_report_text():
    prompt = render_prompt(
        PromptId.COMPLIANCE_TEXT_EXTRACTION,
        law_summary="Kurzfassung",
        consolidated_session_json="{}",
        beispiel_1="",
        beispiel_2="",
        beispiel_3="",
    )

    assert "Deep Research" not in prompt
    assert "Deep-Research" not in prompt
    assert "<deep_research_report>" not in prompt
    assert (
        "| JSON-Struktur | Verbindliche Quelle für Berechnung, Vorgabenstruktur "
        "und finale Werte |\n"
        "| Gesetzeszusammenfassung | Kontext zum Regelungsvorhaben; "
        "keine Berechnungsquelle |"
    ) in prompt


def test_compliance_text_prompt_includes_deep_research_guidance_when_report_text_exists():
    prompt = render_prompt(
        PromptId.COMPLIANCE_TEXT_EXTRACTION,
        law_summary="Kurzfassung",
        consolidated_session_json="{}",
        deep_research_source_row=(
            "| Deep-Research-Bericht | Herleitung, Plausibilisierung und Quellen |"
        ),
        deep_research_hierarchy_rules=(
            "Nutze den Deep-Research-Bericht aktiv fuer Herleitungstexte."
        ),
        deep_research_footnote_guidance=(
            "Fussnoten sollen Deep-Research-Begruendungen aufgreifen."
        ),
        deep_research_consistency_check=(
            "1. Wurden vorhandene Deep-Research-Begruendungen aufgegriffen?"
        ),
        deep_research_input_block=(
            "<deep_research_report>\n## Teil 1: Bericht\nText\n</deep_research_report>"
        ),
        deep_research_forbidden_term="`Deep Research Report`, ",
        beispiel_1="",
        beispiel_2="",
        beispiel_3="",
    )

    assert "| Deep-Research-Bericht |" in prompt
    assert "Nutze den Deep-Research-Bericht aktiv" in prompt
    assert "Fussnoten sollen Deep-Research-Begruendungen" in prompt
    assert "<deep_research_report>" in prompt
    assert "`Deep Research Report`, `Prompt`" in prompt


def test_export_attaches_vorgaben_per_process():
    seeded = _seed_completed_session("COMP-VORGABEN-PROC")
    session_id = seeded["session_id"]

    context = build_compliance_export_context(
        app_session_id="COMP-VORGABEN-PROC",
        session_id=session_id,
        user_edit_policy=USER_EDIT_REJECT,
    )
    adm = next(
        a for a in context.snapshot["normadressaten"] if a["normadressat"] == ADMINISTRATION
    )
    prozess = adm["prozesse"][0]
    vorgaben = prozess["vorgaben"]

    assert len(vorgaben) == 1
    vorgabe = vorgaben[0]
    assert vorgabe["normzitat"] == "§ 1"
    assert vorgabe["ist_informationspflicht_wirtschaft"] is False
    assert {v["vorgaben_id"] for v in vorgaben} == {
        v["vorgaben_id"] for v in adm["vorgaben"]
    }
