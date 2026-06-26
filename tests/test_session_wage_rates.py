"""Phase C1: row-based session wage-rate overrides API.

Covers listing the used (source, qualification) rows, setting/clearing an
override, validation, and that an override flows into the cost computation.
"""

import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION


def _seed_session_with_rows(app_id="WAGE-C1"):
    session_id, _ = db.upsert_session(app_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung")
    case_group_id = db.insert_case_group(session_id, process_id, "Fallgruppe", "Beschreibung")
    step_id = db.insert_process_step(session_id, case_group_id, "Schritt", "Beschreibung")
    # Dual-write reality: child rows are authoritative; the slot columns mirror
    # them (and currently still satisfy the cost-input validation).
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_id,
        [
            {"period": "proposed", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
             "time_required_in_min": 60, "model_hourly_rate": 40.4},
        ],
    )
    db.update_process_step_effort_split(
        session_id=session_id, step_id=step_id,
        hourly_rates_current={}, time_required_current={}, expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 40.4, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 60, "c": None, "d": None},
        expenses_proposed=None,
    )
    return app_id, session_id, case_group_id, step_id


def test_wage_rates_lists_used_source_with_all_qualifications(test_client):
    app_id, _session_id, _cg, _step = _seed_session_with_rows()
    resp = test_client.get(
        "/sessions/wage-rates",
        params={"app_session_id": app_id, "norm_addressee": ADMINISTRATION},
    )
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    # one used source (bund) x all four admin qualifications
    assert {r["wage_source_value"] for r in rows} == {"bund"}
    assert {r["qualification"] for r in rows} == {
        "einfacher_und_mittlerer_dienst", "gehobener_dienst", "hoeherer_dienst", "durchschnitt",
    }
    gd = next(r for r in rows if r["qualification"] == "gehobener_dienst")
    assert gd["model_hourly_rate"] == 40.4
    assert gd["hourly_rate_edited"] is None


def test_wage_rate_override_set_clear_and_validation(test_client):
    app_id, _session_id, _cg, _step = _seed_session_with_rows("WAGE-C1-SET")

    # set override
    resp = test_client.post(
        "/sessions/wage-rates",
        json={
            "app_session_id": app_id, "norm_addressee": ADMINISTRATION,
            "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
            "qualification": "gehobener_dienst", "hourly_rate_edited": 55.0,
        },
    )
    assert resp.status_code == 200
    gd = next(r for r in resp.json()["rows"] if r["qualification"] == "gehobener_dienst")
    assert gd["hourly_rate_edited"] == 55.0

    # invalid combination is rejected
    bad = test_client.post(
        "/sessions/wage-rates",
        json={
            "app_session_id": app_id, "norm_addressee": ADMINISTRATION,
            "wage_source_kind": "verwaltungsebene", "wage_source_value": "nonexistent",
            "qualification": "gehobener_dienst", "hourly_rate_edited": 55.0,
        },
    )
    assert bad.status_code == 422

    # clear override (None)
    resp = test_client.post(
        "/sessions/wage-rates",
        json={
            "app_session_id": app_id, "norm_addressee": ADMINISTRATION,
            "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
            "qualification": "gehobener_dienst", "hourly_rate_edited": None,
        },
    )
    assert resp.status_code == 200
    gd = next(r for r in resp.json()["rows"] if r["qualification"] == "gehobener_dienst")
    assert gd["hourly_rate_edited"] is None


def test_wage_rate_override_noop_rejection_and_audit(test_client):
    # Row wage overrides join the EA no-op/audit contract: set/clear are real changes
    # (200 + audit row); re-posting an identical value or clearing an absent override
    # is a no-op (422).
    app_id, session_id, _cg, _step = _seed_session_with_rows("WAGE-C1-NOOP")
    body = {
        "app_session_id": app_id,
        "norm_addressee": ADMINISTRATION,
        "wage_source_kind": "verwaltungsebene",
        "wage_source_value": "bund",
        "qualification": "gehobener_dienst",
    }

    def post(rate):
        return test_client.post("/sessions/wage-rates", json={**body, "hourly_rate_edited": rate})

    assert post(55.0).status_code == 200
    # Same value again -> no-op.
    again = post(55.0)
    assert again.status_code == 422
    assert again.json()["detail"] == "No changes in payload"
    # New value -> real change.
    assert post(60.0).status_code == 200
    # Clear -> real change.
    assert post(None).status_code == 200
    # Clear again (no override left) -> no-op.
    assert post(None).status_code == 422

    # Three real changes (set 55, set 60, clear) are audited as wage_rate.
    audit = db.list_edit_audit_for_session(session_id)
    assert len(audit) == 3
    assert all(row["entity_type"] == "wage_rate" for row in audit)


def test_wage_rate_override_flows_into_cost():
    # The override set via the db layer is picked up by the cost engine's override
    # reader and applied by the row-cost helper (the C1 <-> Phase B integration).
    from backend.core.cost_aggregation import _compute_step_personnel_cost_from_rows

    app_id, session_id, _cg, step_id = _seed_session_with_rows("WAGE-C1-COST")
    rows = [
        r for r in db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
        if r["period"] == "proposed"
    ]

    # baseline: model rate 40.4 * 60/60 = 40.4
    base = _compute_step_personnel_cost_from_rows(
        rows, db.get_session_wage_rate_overrides(session_id, ADMINISTRATION)
    )
    assert base == pytest.approx(40.4)

    db.upsert_session_wage_rate_override(
        session_id, ADMINISTRATION, "verwaltungsebene", "bund", "gehobener_dienst", 100.0,
    )
    overridden = _compute_step_personnel_cost_from_rows(
        rows, db.get_session_wage_rate_overrides(session_id, ADMINISTRATION)
    )
    # override 100 * 60/60 = 100 (not the model 40.4)
    assert overridden == pytest.approx(100.0)
