from backend.core import db


def test_session_status_formats_persisted_cancelled_query_as_user_message(test_client):
    session_id, _ = db.upsert_session("STATUS-CANCELLED-STEP", "test-model")
    db.update_session_summary("STATUS-CANCELLED-STEP", "Titel", "Zusammenfassung")
    db.insert_regulation(session_id, "§ 1", "Beschreibung")
    process_id = db.insert_process(
        session_id,
        "Prozess A",
        "Beschreibung Prozess",
        norm_addressee="administration",
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung Fallgruppe",
        norm_addressee="administration",
    )
    db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt 1",
        "Beschreibung Schritt 1",
        norm_addressee="administration",
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id="effort_calculation",
        model="test-model",
        answer_text="",
        metadata={
            "error": "gemini:cancelled - LLM query was cancelled before completion",
            "error_kind": "cancelled",
        },
        answer_state=db.LLM_ANSWER_STATE_INVALID,
        state_reason="query_failed",
        norm_addressee="administration",
    )

    resp = test_client.get(
        "/sessions/status", params={"app_session_id": "STATUS-CANCELLED-STEP"}
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["effort_ready"] is False
    assert payload["last_failed_step"] == "effort"
    assert payload["last_failed_label"] == "Aufwand berechnen"
    assert (
        payload["last_failed_message"]
        == "Der Schritt wurde abgebrochen. Bitte führen Sie ihn erneut aus."
    )
    assert "gemini:cancelled" not in payload["last_failed_message"]


def test_session_status_exposes_latest_failed_step_message(test_client):
    session_id, _ = db.upsert_session("STATUS-FAILED-STEP", "test-model")
    db.update_session_summary("STATUS-FAILED-STEP", "Titel", "Zusammenfassung")
    db.insert_regulation(session_id, "§ 1", "Beschreibung")
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id="process_compilation",
        model="test-model",
        answer_text="{}",
        answer_state=db.LLM_ANSWER_STATE_INVALID,
        state_reason="session_update_failed: Vorgabe 295 linked to multiple processes",
        norm_addressee="administration",
    )

    resp = test_client.get(
        "/sessions/status", params={"app_session_id": "STATUS-FAILED-STEP"}
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["processes_ready"] is False
    assert payload["last_failed_step"] == "processes"
    assert payload["last_failed_label"] == "Prozesse bündeln"
    assert "Die Antwort für Verwaltung konnte nicht verarbeitet werden" in payload["last_failed_message"]
    assert "Schritt erneut aus.\nTechnische Details:" in payload["last_failed_message"]
    assert (
        "Technische Details: Prozesse bündeln / processes / Verwaltung / process_compilation"
        in payload["last_failed_message"]
    )
    assert "Vorgabe 295 linked to multiple processes" in payload["last_failed_message"]

    process_id = db.insert_process(
        session_id,
        "Prozess A",
        "Beschreibung Prozess",
        norm_addressee="administration",
    )
    assert process_id is not None

    resp = test_client.get(
        "/sessions/status", params={"app_session_id": "STATUS-FAILED-STEP"}
    )
    payload = resp.json()
    assert payload["last_failed_step"] is None
    assert payload["last_failed_message"] is None


def test_session_status_treats_empty_process_answer_as_completed_no_op(test_client):
    session_id, _ = db.upsert_session("STATUS-EMPTY-PROCESSES", "test-model")
    db.update_session_summary("STATUS-EMPTY-PROCESSES", "Titel", "Zusammenfassung")
    db.insert_regulation(
        session_id,
        "§ 1",
        "Beschreibung",
        applies_to_administration=True,
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id="process_compilation",
        model="test-model",
        answer_text='{"prozesse": []}',
        answer_state=db.LLM_ANSWER_STATE_ACTIVE,
        state_reason="session_updated",
        norm_addressee="administration",
    )

    resp = test_client.get(
        "/sessions/status", params={"app_session_id": "STATUS-EMPTY-PROCESSES"}
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["processes_ready"] is True
    assert payload["case_groups_ready"] is True
    assert payload["process_steps_ready"] is True
    assert payload["effort_ready"] is True
    assert payload["total_cost_ready"] is True
    assert payload["processes_ready_by_addressee"]["administration"] is True
    assert db.list_processes_for_session_and_addressee(session_id, "administration") == []


def test_session_status_progression(test_client):
    """Reflects readiness flags as session data accumulates."""
    session_id, _ = db.upsert_session("STATUS-OK", "test-model")

    resp = test_client.get("/sessions/status", params={"app_session_id": "STATUS-OK"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["summary_ready"] is False
    assert payload["regulations_ready"] is False
    assert payload["processes_ready"] is False
    assert payload["case_groups_ready"] is False
    assert payload["process_steps_ready"] is False
    assert payload["effort_ready"] is False
    assert payload["total_cost_ready"] is False
    assert payload["last_completed_step"] is None
    assert payload["last_completed_label"] is None

    db.update_session_summary("STATUS-OK", "Titel", "Zusammenfassung")
    reg_id = db.insert_regulation(session_id, "§ 1", "Beschreibung")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt 1", "Beschreibung Schritt 1"
    )

    resp = test_client.get("/sessions/status", params={"app_session_id": "STATUS-OK"})
    payload = resp.json()
    assert payload["summary_ready"] is True
    assert payload["regulations_ready"] is True
    assert payload["processes_ready"] is True
    assert payload["case_groups_ready"] is True
    assert payload["process_steps_ready"] is True
    assert payload["effort_ready"] is False
    assert payload["total_cost_ready"] is False
    assert payload["last_completed_step"] == "process_steps"
    assert payload["last_completed_label"] == "Prozessschritte bestimmen"

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_proposed=5,
        annual_frequency_proposed=1,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_id,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 10, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 5, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.get("/sessions/status", params={"app_session_id": "STATUS-OK"})
    payload = resp.json()
    assert payload["effort_ready"] is True
    assert payload["total_cost_ready"] is False
    assert payload["last_completed_step"] == "effort"
    assert payload["last_completed_label"] == "Aufwand berechnen"
    assert reg_id is not None

    db.update_process_cost(session_id, process_id, 123.0)
    resp = test_client.get("/sessions/status", params={"app_session_id": "STATUS-OK"})
    payload = resp.json()
    assert payload["total_cost_ready"] is True
    assert payload["last_completed_step"] == "total_cost"
    assert payload["last_completed_label"] == "Gesamtkosten berechnen"
