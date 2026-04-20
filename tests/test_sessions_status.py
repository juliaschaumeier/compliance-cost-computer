from backend.core import db


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
