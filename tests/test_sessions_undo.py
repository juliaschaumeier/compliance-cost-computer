from backend.core import db


def _seed_flow(app_session_id: str) -> dict:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt 1", "Beschreibung Schritt 1"
    )
    return {
        "session_id": session_id,
        "process_id": process_id,
        "case_group_id": case_group_id,
        "step_id": step_id,
    }


def test_undo_total_cost_clears_costs_only(test_client):
    """Undoing step 7 clears costs but keeps effort metrics intact."""
    seeded = _seed_flow("UNDO-COST")
    session_id = seeded["session_id"]

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees=10,
        annual_frequency=2,
    )
    db.update_process_step_effort(
        session_id=session_id,
        step_id=seeded["step_id"],
        hourly_rates={"a": 40, "b": None, "c": None, "d": None, "e": None},
        time_required={"a": 30, "b": None, "c": None, "d": None, "e": None},
        expenses=5,
    )
    db.update_process_step_cost(session_id, seeded["step_id"], 25)
    db.update_case_group_cost(session_id, seeded["case_group_id"], 50)
    db.update_process_cost(session_id, seeded["process_id"], 50)
    db.update_session_cost(session_id, 50)

    resp = test_client.post("/sessions/undo", json={"app_session_id": "UNDO-COST"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["undone_step"] == "total_cost"

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT cc_cost FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    assert cur.fetchone()["cc_cost"] is None
    cur.execute(
        "SELECT cost FROM processes WHERE process_id = ?",
        (seeded["process_id"],),
    )
    assert cur.fetchone()["cost"] is None
    cur.execute(
        "SELECT cost FROM case_groups WHERE case_group_id = ?",
        (seeded["case_group_id"],),
    )
    assert cur.fetchone()["cost"] is None
    cur.execute(
        "SELECT cost FROM process_steps WHERE step_id = ?",
        (seeded["step_id"],),
    )
    assert cur.fetchone()["cost"] is None
    cur.execute(
        "SELECT addressees, annual_frequency FROM case_groups WHERE case_group_id = ?",
        (seeded["case_group_id"],),
    )
    group = cur.fetchone()
    assert group["addressees"] == 10
    assert group["annual_frequency"] == 2
    cur.execute(
        "SELECT hourly_rate_a, time_required_in_min_a, expenses FROM process_steps WHERE step_id = ?",
        (seeded["step_id"],),
    )
    step = cur.fetchone()
    assert step["hourly_rate_a"] == 40
    assert step["time_required_in_min_a"] == 30
    assert step["expenses"] == 5
    conn.close()


def test_undo_effort_clears_metrics(test_client):
    """Undoing step 6 clears effort metrics while keeping steps."""
    seeded = _seed_flow("UNDO-EFFORT")
    session_id = seeded["session_id"]

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees=10,
        annual_frequency=2,
    )
    db.update_process_step_effort(
        session_id=session_id,
        step_id=seeded["step_id"],
        hourly_rates={"a": 40, "b": None, "c": None, "d": None, "e": None},
        time_required={"a": 30, "b": None, "c": None, "d": None, "e": None},
        expenses=5,
    )

    resp = test_client.post(
        "/sessions/undo", json={"app_session_id": "UNDO-EFFORT"}
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["undone_step"] == "effort"

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT addressees, annual_frequency FROM case_groups WHERE case_group_id = ?",
        (seeded["case_group_id"],),
    )
    group = cur.fetchone()
    assert group["addressees"] is None
    assert group["annual_frequency"] is None
    cur.execute(
        "SELECT hourly_rate_a, time_required_in_min_a, expenses FROM process_steps WHERE step_id = ?",
        (seeded["step_id"],),
    )
    step = cur.fetchone()
    assert step["hourly_rate_a"] is None
    assert step["time_required_in_min_a"] is None
    assert step["expenses"] is None
    conn.close()
