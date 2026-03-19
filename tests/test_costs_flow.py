import pytest

from backend.core import db
from backend.core.models import Tile


def _seed_flow(session_id: int) -> dict:
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_one = db.insert_process_step(
        session_id, case_group_id, "Schritt 1", "Beschreibung Schritt 1"
    )
    step_two = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt 2",
        "Beschreibung Schritt 2",
        previous_id=step_one,
    )
    db.update_process_step_next(step_one, step_two)
    db.upsert_tile(
        Tile(
            id=f"process_{process_id}",
            title="Prozess A",
            text="Beschreibung Prozess",
            meta_information={"process_id": process_id},
            column=2,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={"case_group_id": case_group_id, "process_id": process_id},
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[f"process_{process_id}"],
        ),
        session_id=session_id,
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_one}",
            title="Schritt 1",
            text="Beschreibung Schritt 1",
            meta_information={"step_id": step_one, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[f"case_group_{case_group_id}"],
        ),
        session_id=session_id,
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_two}",
            title="Schritt 2",
            text="Beschreibung Schritt 2",
            meta_information={"step_id": step_two, "case_group_id": case_group_id},
            column=5,
            row=0,
            deletable=True,
            link_from_tile=[f"step_{step_one}"],
        ),
        session_id=session_id,
    )
    return {
        "process_id": process_id,
        "case_group_id": case_group_id,
        "step_one": step_one,
        "step_two": step_two,
    }


def test_compute_costs_requires_steps(test_client):
    """Rejects cost computation without process steps."""
    session_id, _ = db.upsert_session("COST-NO-STEPS", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )

    resp = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-NO-STEPS"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No process steps for session"


def test_compute_costs_requires_case_group_metrics(test_client):
    """Rejects cost computation when case group metrics are missing."""
    session_id, _ = db.upsert_session("COST-NO-METRICS", "test-model")
    _seed_flow(session_id)

    resp = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-NO-METRICS"}
    )
    assert resp.status_code == 422
    assert "Missing case group metrics" in resp.json()["detail"]


def test_compute_costs_updates_db_and_tiles(test_client):
    """Computes step, case-group, process and session costs plus total tile."""
    session_id, _ = db.upsert_session("COST-OK", "test-model")
    seeded = _seed_flow(session_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_one"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=10,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.post("/costs/compute", json={"app_session_id": "COST-OK"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_cost"] == 1214

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT cost_current, cost_proposed FROM process_steps WHERE step_id = ?",
        (seeded["step_one"],),
    )
    step_one_cost = cur.fetchone()
    assert step_one_cost["cost_current"] == 0
    assert step_one_cost["cost_proposed"] == 26.9
    cur.execute(
        "SELECT cost_current, cost_proposed FROM process_steps WHERE step_id = ?",
        (seeded["step_two"],),
    )
    step_two_cost = cur.fetchone()
    assert step_two_cost["cost_current"] == 0
    assert step_two_cost["cost_proposed"] == 33.8
    cur.execute(
        "SELECT cost FROM case_groups WHERE case_group_id = ?",
        (seeded["case_group_id"],),
    )
    assert cur.fetchone()["cost"] == 1214
    cur.execute(
        "SELECT cost FROM processes WHERE process_id = ?",
        (seeded["process_id"],),
    )
    assert cur.fetchone()["cost"] == 1214
    cur.execute(
        "SELECT cc_cost FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    assert cur.fetchone()["cc_cost"] == 1214
    conn.close()

    tiles = db.fetch_tiles(session_id=session_id)
    process_tile = next(tile for tile in tiles if tile.id == f"process_{seeded['process_id']}")
    case_group_tile = next(
        tile for tile in tiles if tile.id == f"case_group_{seeded['case_group_id']}"
    )
    step_tile_one = next(tile for tile in tiles if tile.id == f"step_{seeded['step_one']}")
    step_tile_two = next(tile for tile in tiles if tile.id == f"step_{seeded['step_two']}")
    total_tile = next(tile for tile in tiles if tile.id == "total_cost")

    assert "Kosten:" not in process_tile.text
    assert process_tile.meta_information.get("cost") == 1214
    assert case_group_tile.meta_information.get("cases_proposed") == 20
    assert case_group_tile.meta_information.get("cases_current") is None
    assert "Kosten:" not in step_tile_one.text
    assert "Kosten:" not in step_tile_two.text
    assert step_tile_one.meta_information.get("cost_current") == 0
    assert step_tile_one.meta_information.get("cost_proposed") == 26.9
    assert step_tile_two.meta_information.get("cost_current") == 0
    assert step_tile_two.meta_information.get("cost_proposed") == 33.8

    assert "€" in total_tile.text
    assert "Fälle pro Jahr (Δ)" not in total_tile.text
    assert f"step_{seeded['step_two']}" in total_tile.link_from_tile


def test_compute_costs_multiplies_all_steps_by_case_counts(test_client):
    """All step costs are multiplied by per-group yearly case counts."""
    session_id, _ = db.upsert_session("COST-PER-GROUP", "test-model")
    seeded = _seed_flow(session_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=3,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_one"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=10,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.post("/costs/compute", json={"app_session_id": "COST-PER-GROUP"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_cost"] == pytest.approx(364.2)


def test_compute_costs_uses_edited_case_and_step_values(test_client):
    session_id, _ = db.upsert_session("COST-USES-EDITS", "test-model")
    seeded = _seed_flow(session_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_one"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=0,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=0,
    )

    updated_case_groups, missing_case_groups = db.bulk_update_case_group_edits(
        session_id,
        [
            {
                "case_group_id": seeded["case_group_id"],
                "addressees_proposed": 5,
                "annual_frequency_proposed": 1,
            }
        ],
    )
    assert updated_case_groups == 1
    assert missing_case_groups == []

    updated_steps, missing_steps = db.bulk_update_process_step_edits(
        session_id,
        [
            {
                "step_id": seeded["step_one"],
                "time_required_in_min_a_proposed": 30,
                "expenses_proposed": 0,
            },
            {
                "step_id": seeded["step_two"],
                "time_required_in_min_a_proposed": 30,
                "expenses_proposed": 0,
            },
        ],
    )
    assert updated_steps == 2
    assert missing_steps == []

    resp = test_client.post("/costs/compute", json={"app_session_id": "COST-USES-EDITS"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_cost"] == pytest.approx(169.0)
