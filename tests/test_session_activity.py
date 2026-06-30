import asyncio
import logging
import time

import pytest

from backend.core import db
from backend.core.auth import ApiKeys
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.session_activity import WORKFLOW_LEASE_SECONDS, begin_session_activity
from backend.routers import sessions as sessions_router


def _seed_total_cost_ready(app_session_id: str) -> int:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    for addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        db.upsert_session_total_costs_by_addressee(
            session_id=session_id,
            norm_addressee=addressee,
            total_cost=1.0 if addressee != CITIZENS else None,
            bureaucracy_cost=1.0 if addressee == BUSINESS else None,
            total_time_minutes=0.0 if addressee == CITIZENS else None,
            total_expenses=0.0 if addressee == CITIZENS else None,
        )
    return session_id


def _seed_computable_admin_costs(app_session_id: str) -> int:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(
        session_id,
        "Prozess A",
        "Beschreibung Prozess",
        norm_addressee=ADMINISTRATION,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt 1",
        "Beschreibung Schritt 1",
        norm_addressee=ADMINISTRATION,
    )
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_id,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=10,
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_id}",
            title="Schritt 1",
            text="Beschreibung Schritt 1",
            meta_information={"step_id": step_id, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
    )
    return session_id


def _wage_payload(app_session_id: str, activity_id: str | None = None) -> dict:
    return {
        "app_session_id": app_session_id,
        "norm_addressee": ADMINISTRATION,
        "ea_activity_id": activity_id,
        "wage_source_kind": "verwaltungsebene",
        "wage_source_value": "bund",
        "qualification": "einfacher_und_mittlerer_dienst",
        "hourly_rate_edited": 44.5,
    }


def test_ea_activity_owner_can_write_wage_rate(test_client):
    _seed_total_cost_ready("EA-ACT-OWNER")
    activity = test_client.post(
        "/sessions/ea-edit-activity/acquire",
        json={"app_session_id": "EA-ACT-OWNER"},
    )
    assert activity.status_code == 200
    activity_id = activity.json()["activity_id"]

    response = test_client.post(
        "/sessions/wage-rates",
        json=_wage_payload("EA-ACT-OWNER", activity_id),
    )

    assert response.status_code == 200


def test_ea_write_without_owner_activity_is_rejected(test_client):
    _seed_total_cost_ready("EA-ACT-STRICT")

    response = test_client.post(
        "/sessions/wage-rates",
        json=_wage_payload("EA-ACT-STRICT"),
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "session_activity_unavailable"
    assert detail["activity_type"] == "ea_edit"
    assert "EA-Bearbeitung ist nicht mehr aktiv" in detail["message"]


def test_same_session_workflow_rejected_while_ea_activity_active(test_client):
    _seed_total_cost_ready("EA-ACT-BLOCK-RUN")
    activity = test_client.post(
        "/sessions/ea-edit-activity/acquire",
        json={"app_session_id": "EA-ACT-BLOCK-RUN"},
    )
    assert activity.status_code == 200

    response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": "EA-ACT-BLOCK-RUN", "model": "test-model"},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "session_activity_conflict"
    assert detail["active_type"] == "ea_edit"
    assert "EA-Bearbeitung" in detail["message"]


def test_same_session_ea_write_rejected_while_workflow_activity_active(test_client):
    session_id = _seed_total_cost_ready("EA-ACT-BLOCK-WRITE")
    begin_session_activity(
        session_id=session_id,
        activity_type="workflow",
        label="Testlauf",
        ttl_seconds=WORKFLOW_LEASE_SECONDS,
    )

    response = test_client.post(
        "/sessions/wage-rates",
        json=_wage_payload("EA-ACT-BLOCK-WRITE"),
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "session_activity_conflict"
    assert detail["active_type"] == "workflow"
    assert "Ausführung" in detail["message"]


def test_workflow_activity_allows_total_cost_compute_without_ea_owner(test_client):
    session_id = _seed_computable_admin_costs("EA-ACT-WORKFLOW-COSTS")
    begin_session_activity(
        session_id=session_id,
        activity_type="workflow",
        label="Testlauf",
        ttl_seconds=WORKFLOW_LEASE_SECONDS,
    )

    response = test_client.post(
        "/costs/compute",
        json={"app_session_id": "EA-ACT-WORKFLOW-COSTS", "norm_addressee": ADMINISTRATION},
    )

    assert response.status_code == 200
    assert response.json()["total_cost"] == 800


def test_ea_activity_release_does_not_clear_workflow_activity(test_client):
    session_id = _seed_total_cost_ready("EA-ACT-RELEASE-WORKFLOW")
    workflow_activity = begin_session_activity(
        session_id=session_id,
        activity_type="workflow",
        label="Testlauf",
        ttl_seconds=WORKFLOW_LEASE_SECONDS,
    )

    response = test_client.post(
        "/sessions/ea-edit-activity/release",
        json={
            "app_session_id": "EA-ACT-RELEASE-WORKFLOW",
            "activity_id": workflow_activity.activity_id,
        },
    )

    assert response.status_code == 200
    active = db.get_session_activity(session_id)
    assert active is not None
    assert active["activity_id"] == workflow_activity.activity_id
    assert active["activity_type"] == "workflow"


def test_other_session_workflow_allowed_while_ea_activity_active(test_client, monkeypatch):
    async def fake_run_all_background(
        run_id,
        payload,
        api_keys,
        model,
        workflow_activity_id,
    ):
        session_id = db.get_session_id_by_app_id(payload.app_session_id)
        if session_id is not None:
            db.clear_session_activity(session_id, workflow_activity_id)

    monkeypatch.setattr(sessions_router, "_run_all_background", fake_run_all_background)
    _seed_total_cost_ready("EA-ACT-ONE")
    _seed_total_cost_ready("EA-ACT-TWO")
    activity = test_client.post(
        "/sessions/ea-edit-activity/acquire",
        json={"app_session_id": "EA-ACT-ONE"},
    )
    assert activity.status_code == 200

    response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": "EA-ACT-TWO", "model": "test-model"},
    )

    assert response.status_code == 200
    assert response.json()["started"] is True


def test_expired_session_activity_purge_logs_recovery(caplog):
    session_id = _seed_total_cost_ready("EA-ACT-EXPIRED")
    now = time.time()
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO session_activities (
            session_id, activity_id, activity_type, label,
            created_at, updated_at, expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            "workflow:expired-test",
            "workflow",
            "Testlauf",
            now - 2,
            now - 2,
            now - 1,
        ),
    )
    conn.commit()
    conn.close()

    with caplog.at_level(logging.WARNING, logger="backend.core.db"):
        deleted = db.purge_expired_session_activity(session_id)

    assert deleted == 1
    assert db.get_session_activity(session_id) is None
    assert "Purged expired session activity" in caplog.text
    assert "workflow:expired-test" in caplog.text


def test_single_step_workflow_activity_released_when_final_publish_fails(monkeypatch):
    app_session_id = "EA-ACT-FINAL-PUBLISH"
    session_id = _seed_total_cost_ready(app_session_id)
    activity = begin_session_activity(
        session_id=session_id,
        activity_type="workflow",
        label="Testlauf",
        ttl_seconds=WORKFLOW_LEASE_SECONDS,
    )
    run_id = "activity-final-publish"
    sessions_router._RUNS_BY_ID[run_id] = sessions_router._RunRecord(
        run_id=run_id,
        app_session_id=app_session_id,
    )
    sessions_router._ACTIVE_RUN_BY_SESSION[app_session_id] = run_id

    async def fake_execute_single_step(**_kwargs):
        return [], sessions_router._as_session_status_response(app_session_id), True

    publish_calls = 0

    async def flaky_publish_event(*_args, **_kwargs):
        nonlocal publish_calls
        publish_calls += 1
        if publish_calls == 2:
            raise RuntimeError("final publish failed")

    monkeypatch.setattr(sessions_router, "_execute_single_step", fake_execute_single_step)
    monkeypatch.setattr(sessions_router, "_publish_run_event", flaky_publish_event)

    try:
        with pytest.raises(RuntimeError, match="final publish failed"):
            asyncio.run(
                sessions_router._run_single_step_background(
                    run_id,
                    "effort",
                    sessions_router.SessionRunAllRequest(
                        app_session_id=app_session_id,
                        model="test-model",
                    ),
                    ApiKeys(),
                    "test-model",
                    activity.activity_id,
                )
            )

        assert db.get_session_activity(session_id) is None
    finally:
        sessions_router._RUNS_BY_ID.pop(run_id, None)
        sessions_router._ACTIVE_RUN_BY_SESSION.pop(app_session_id, None)
