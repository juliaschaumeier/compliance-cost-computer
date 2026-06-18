"""Phase C2: row-based editable API + personnel-effort time edits."""

import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION


def _seed(app_id="C2-EDIT"):
    session_id, _ = db.upsert_session(app_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung")
    case_group_id = db.insert_case_group(session_id, process_id, "Fallgruppe", "Beschreibung")
    step_id = db.insert_process_step(session_id, case_group_id, "Schritt", "Beschreibung")
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_id,
        [
            {"period": "proposed", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
             "time_required_in_min": 30, "model_hourly_rate": 40.4},
        ],
    )
    return app_id, session_id, step_id


def _edit_payload(app_id, step_id, **overrides):
    payload = {
        "app_session_id": app_id, "norm_addressee": ADMINISTRATION, "step_id": step_id,
        "period": "proposed", "qualification": "gehobener_dienst",
        "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
        "time_required_in_min_edited": 10.0,
    }
    payload.update(overrides)
    return payload


def test_editable_returns_personnel_rows(test_client):
    app_id, _session_id, step_id = _seed()
    resp = test_client.get("/process-steps/editable", params={"app_session_id": app_id})
    assert resp.status_code == 200
    row = next(r for r in resp.json()["rows"] if r["step_id"] == step_id)
    assert row["personnel_effort_proposed"] == [
        {
            "qualification": "gehobener_dienst",
            "wage_source_kind": "verwaltungsebene",
            "wage_source_value": "bund",
            "model_hourly_rate": 40.4,
            "time_required_in_min": 30,
            "time_required_in_min_edited": None,
        }
    ]
    assert row["personnel_effort_current"] == []


def test_personnel_effort_time_edit_sets_and_flows_into_cost(test_client):
    from backend.routers.costs import _compute_step_personnel_cost_from_rows

    app_id, session_id, step_id = _seed("C2-EDIT-COST")
    resp = test_client.post("/process-steps/personnel-effort-edit", json=_edit_payload(app_id, step_id))
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1

    rows = db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
    assert rows[0]["time_required_in_min_edited"] == 10.0

    # edited time (10) wins over the model time (30): 40.4 * 10/60
    cost = _compute_step_personnel_cost_from_rows(rows, {})
    assert cost == pytest.approx(40.4 * 10 / 60)


def test_personnel_effort_time_edit_clear(test_client):
    app_id, session_id, step_id = _seed("C2-EDIT-CLEAR")
    test_client.post("/process-steps/personnel-effort-edit", json=_edit_payload(app_id, step_id))
    resp = test_client.post(
        "/process-steps/personnel-effort-edit",
        json=_edit_payload(app_id, step_id, time_required_in_min_edited=None),
    )
    assert resp.status_code == 200
    rows = db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
    assert rows[0]["time_required_in_min_edited"] is None


def test_personnel_effort_invalid_combination_rejected(test_client):
    # An unknown wage source has no model rate -> the row cannot be created (422).
    app_id, _session_id, step_id = _seed("C2-EDIT-NOMATCH")
    resp = test_client.post(
        "/process-steps/personnel-effort-edit",
        json=_edit_payload(app_id, step_id, wage_source_value="voellig_ungueltig"),
    )
    assert resp.status_code == 422


def test_personnel_effort_upsert_creates_row_for_unassigned_qualification(test_client):
    # The LLM only assigned gehobener_dienst; the user adds time for hoeherer_dienst
    # under the step's source (laender) -> a new row is created (model rate from the
    # wage table, no model time, the entry stored as the edited time).
    app_id, session_id, step_id = _seed("C2-EDIT-UPSERT")
    resp = test_client.post(
        "/process-steps/personnel-effort-edit",
        json=_edit_payload(
            app_id, step_id, qualification="hoeherer_dienst",
            wage_source_value="bund", time_required_in_min_edited=15.0,
        ),
    )
    assert resp.status_code == 200
    rows = db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
    created = next(r for r in rows if r["qualification"] == "hoeherer_dienst")
    assert created["time_required_in_min"] is None
    assert created["time_required_in_min_edited"] == 15.0
    assert created["model_hourly_rate"] == 67.6  # bund, slot c


def test_personnel_effort_clear_removes_user_created_row(test_client):
    app_id, session_id, step_id = _seed("C2-EDIT-UPSERT-CLEAR")
    payload = _edit_payload(
        app_id, step_id, qualification="hoeherer_dienst",
        wage_source_value="bund", time_required_in_min_edited=15.0,
    )
    test_client.post("/process-steps/personnel-effort-edit", json=payload)
    # Clearing a user-created row removes it entirely.
    test_client.post(
        "/process-steps/personnel-effort-edit",
        json={**payload, "time_required_in_min_edited": None},
    )
    rows = db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
    assert all(r["qualification"] != "hoeherer_dienst" for r in rows)
