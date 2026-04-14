import pytest

from backend.core import db
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


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
    assert payload["total_cost"] == 2000

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT cost_current, cost_proposed FROM process_steps WHERE step_id = ?",
        (seeded["step_one"],),
    )
    step_one_cost = cur.fetchone()
    assert step_one_cost["cost_current"] == 0
    assert step_one_cost["cost_proposed"] == 40.0
    cur.execute(
        "SELECT cost_current, cost_proposed FROM process_steps WHERE step_id = ?",
        (seeded["step_two"],),
    )
    step_two_cost = cur.fetchone()
    assert step_two_cost["cost_current"] == 0
    assert step_two_cost["cost_proposed"] == 60.0
    cur.execute(
        "SELECT cost FROM case_groups WHERE case_group_id = ?",
        (seeded["case_group_id"],),
    )
    assert cur.fetchone()["cost"] == 2000
    cur.execute(
        "SELECT cost FROM processes WHERE process_id = ?",
        (seeded["process_id"],),
    )
    assert cur.fetchone()["cost"] == 2000
    cur.execute(
        "SELECT cc_cost FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    assert cur.fetchone()["cc_cost"] == 2000
    conn.close()
    totals = db.get_session_total_costs_by_addressee(session_id, ADMINISTRATION)
    assert totals is not None
    assert totals["total_cost"] == 2000
    assert totals["bureaucracy_cost"] is None
    assert totals["total_time_minutes"] is None
    assert totals["total_expenses"] is None

    tiles = db.fetch_tiles(session_id=session_id)
    process_tile = next(tile for tile in tiles if tile.id == f"process_{seeded['process_id']}")
    case_group_tile = next(
        tile for tile in tiles if tile.id == f"case_group_{seeded['case_group_id']}"
    )
    step_tile_one = next(tile for tile in tiles if tile.id == f"step_{seeded['step_one']}")
    step_tile_two = next(tile for tile in tiles if tile.id == f"step_{seeded['step_two']}")
    total_tile = next(tile for tile in tiles if tile.id == "total_cost")

    assert "Kosten:" not in process_tile.text
    assert process_tile.meta_information.get("cost") == 2000
    assert case_group_tile.meta_information.get("cases_proposed") == 20
    assert case_group_tile.meta_information.get("cases_current") is None
    assert "Kosten:" in step_tile_one.text
    assert "Kosten:" in step_tile_two.text
    assert step_tile_one.meta_information.get("cost_current") == 0
    assert step_tile_one.meta_information.get("cost_proposed") == 40.0
    assert step_tile_two.meta_information.get("cost_current") == 0
    assert step_tile_two.meta_information.get("cost_proposed") == 60.0

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
    assert payload["total_cost"] == pytest.approx(600.0)


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
    assert payload["total_cost"] == pytest.approx(300.0)


def test_compute_costs_allows_admin_time_only_inputs_with_active_rates(test_client):
    session_id, _ = db.upsert_session("COST-ADMIN-TIME-ONLY", "test-model")
    seeded = _seed_flow(session_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_one"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={},
        time_required_proposed={"a": 0, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-ADMIN-TIME-ONLY"}
    )
    assert resp.status_code == 200
    assert resp.json()["total_cost"] == pytest.approx(33.8)


def test_compute_costs_allows_business_time_only_inputs_with_active_rates(test_client):
    session_id, _ = db.upsert_session("COST-BUSINESS-TIME-ONLY", "test-model")
    process_id = db.insert_process(
        session_id,
        "Business Process",
        "Beschreibung Prozess",
        norm_addressee=BUSINESS,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Business Case Group",
        "Beschreibung Fallgruppe",
        norm_addressee=BUSINESS,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Business Step",
        "Beschreibung Schritt",
        norm_addressee=BUSINESS,
    )
    db.upsert_tile(
        Tile(
            id=f"process_{process_id}",
            title="Business Process",
            text="Beschreibung Prozess",
            meta_information={"process_id": process_id},
            column=2,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
        norm_addressee=BUSINESS,
    )
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Business Case Group",
            text="Beschreibung Fallgruppe",
            meta_information={"case_group_id": case_group_id, "process_id": process_id},
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[f"process_{process_id}"],
        ),
        session_id=session_id,
        norm_addressee=BUSINESS,
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_id}",
            title="Business Step",
            text="Beschreibung Schritt",
            meta_information={"step_id": step_id, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[f"case_group_{case_group_id}"],
        ),
        session_id=session_id,
        norm_addressee=BUSINESS,
    )
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=case_group_id,
        norm_addressee=BUSINESS,
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=BUSINESS,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-BUSINESS-TIME-ONLY", "norm_addressee": BUSINESS},
    )
    assert resp.status_code == 200
    assert resp.json()["total_cost"] == pytest.approx(26.1)


def test_compute_costs_business_counts_mixed_information_obligation_steps_as_bureaucracy(
    test_client,
):
    session_id, _ = db.upsert_session("COST-BUSINESS-MIXED", "test-model")
    process_id = db.insert_process(
        session_id,
        "Business Process",
        "Beschreibung Prozess",
        norm_addressee=BUSINESS,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Business Case Group",
        "Beschreibung Fallgruppe",
        norm_addressee=BUSINESS,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Business Step",
        "Beschreibung Schritt",
        norm_addressee=BUSINESS,
    )

    regulation_info = db.insert_regulation(
        session_id,
        "§ 1",
        "Informationspflicht",
        applies_to_administration=False,
        applies_to_business=True,
        is_business_information_obligation=True,
    )
    regulation_other = db.insert_regulation(
        session_id,
        "§ 2",
        "Sonstige Vorgabe",
        applies_to_administration=False,
        applies_to_business=True,
        is_business_information_obligation=False,
    )
    assert db.update_regulation_process(
        regulation_id=regulation_info,
        process_id=process_id,
        norm_addressee=BUSINESS,
    )
    assert db.update_regulation_process(
        regulation_id=regulation_other,
        process_id=process_id,
        norm_addressee=BUSINESS,
    )

    db.upsert_tile(
        Tile(
            id=f"process_{process_id}",
            title="Business Process",
            text="Beschreibung Prozess",
            meta_information={"process_id": process_id},
            column=2,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
        norm_addressee=BUSINESS,
    )
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Business Case Group",
            text="Beschreibung Fallgruppe",
            meta_information={"case_group_id": case_group_id, "process_id": process_id},
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[f"process_{process_id}"],
        ),
        session_id=session_id,
        norm_addressee=BUSINESS,
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_id}",
            title="Business Step",
            text="Beschreibung Schritt",
            meta_information={"step_id": step_id, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[f"case_group_{case_group_id}"],
        ),
        session_id=session_id,
        norm_addressee=BUSINESS,
    )

    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=case_group_id,
        norm_addressee=BUSINESS,
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=BUSINESS,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=40,
    )

    resp = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-BUSINESS-MIXED", "norm_addressee": BUSINESS},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_cost"] == pytest.approx(100.0)
    assert payload["bureaucracy_cost"] == pytest.approx(100.0)
    assert payload["other_cost"] == pytest.approx(0.0)
    totals = db.get_session_total_costs_by_addressee(session_id, BUSINESS)
    assert totals is not None
    assert totals["total_cost"] == pytest.approx(100.0)
    assert totals["bureaucracy_cost"] == pytest.approx(100.0)
    assert totals["total_time_minutes"] is None
    assert totals["total_expenses"] is None


def test_compute_costs_rejects_invalid_norm_addressee(test_client):
    session_id, _ = db.upsert_session("COST-INVALID-ADDRESSEE", "test-model")
    _seed_flow(session_id)

    resp = test_client.post(
        "/costs/compute",
        json={
            "app_session_id": "COST-INVALID-ADDRESSEE",
            "norm_addressee": "verwaltung",
        },
    )
    assert resp.status_code == 422
    assert "Unsupported norm_addressee" in resp.json()["detail"]


def test_compute_costs_business_uses_explicit_step_regulation_links_for_bureaucracy(
    test_client,
):
    session_id, _ = db.upsert_session("COST-BUSINESS-STEP-LINKS", "test-model")
    process_id = db.insert_process(
        session_id,
        "Business Process",
        "Beschreibung Prozess",
        norm_addressee=BUSINESS,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Business Case Group",
        "Beschreibung Fallgruppe",
        norm_addressee=BUSINESS,
    )
    step_info = db.insert_process_step(
        session_id,
        case_group_id,
        "Info Step",
        "Beschreibung Info",
        norm_addressee=BUSINESS,
    )
    step_other = db.insert_process_step(
        session_id,
        case_group_id,
        "Other Step",
        "Beschreibung Other",
        previous_id=step_info,
        norm_addressee=BUSINESS,
    )
    db.update_process_step_next(step_info, step_other)

    regulation_info = db.insert_regulation(
        session_id,
        "§ 1",
        "Informationspflicht",
        applies_to_administration=False,
        applies_to_business=True,
        is_business_information_obligation=True,
    )
    regulation_other = db.insert_regulation(
        session_id,
        "§ 2",
        "Materielle Pflicht",
        applies_to_administration=False,
        applies_to_business=True,
        is_business_information_obligation=False,
    )
    assert db.update_regulation_process(
        regulation_id=regulation_info,
        process_id=process_id,
        norm_addressee=BUSINESS,
    )
    assert db.update_regulation_process(
        regulation_id=regulation_other,
        process_id=process_id,
        norm_addressee=BUSINESS,
    )

    for tile_id, title, link_from, column, meta in (
        (
            f"process_{process_id}",
            "Business Process",
            [],
            2,
            {"process_id": process_id},
        ),
        (
            f"case_group_{case_group_id}",
            "Business Case Group",
            [f"process_{process_id}"],
            3,
            {"case_group_id": case_group_id, "process_id": process_id},
        ),
        (
            f"step_{step_info}",
            "Info Step",
            [f"case_group_{case_group_id}"],
            4,
            {"step_id": step_info, "case_group_id": case_group_id},
        ),
        (
            f"step_{step_other}",
            "Other Step",
            [f"step_{step_info}"],
            5,
            {"step_id": step_other, "case_group_id": case_group_id},
        ),
    ):
        db.upsert_tile(
            Tile(
                id=tile_id,
                title=title,
                text=title,
                meta_information=meta,
                column=column,
                row=0,
                deletable=True,
                link_from_tile=link_from,
            ),
            session_id=session_id,
            norm_addressee=BUSINESS,
        )

    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=case_group_id,
        norm_addressee=BUSINESS,
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_info,
        norm_addressee=BUSINESS,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=40,
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_other,
        norm_addressee=BUSINESS,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 60, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=10,
    )
    db.replace_process_step_regulation_links(
        session_id,
        step_info,
        BUSINESS,
        [regulation_info],
    )
    db.replace_process_step_regulation_links(
        session_id,
        step_other,
        BUSINESS,
        [regulation_other],
    )

    resp = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-BUSINESS-STEP-LINKS", "norm_addressee": BUSINESS},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_cost"] == pytest.approx(140.0)
    assert payload["bureaucracy_cost"] == pytest.approx(100.0)
    assert payload["other_cost"] == pytest.approx(40.0)


def test_compute_costs_citizens_ignores_persisted_hourly_rates(test_client):
    session_id, _ = db.upsert_session("COST-CITIZENS-IGNORE-RATES", "test-model")
    process_id = db.insert_process(
        session_id,
        "Citizens Process",
        "Beschreibung Prozess",
        norm_addressee="citizens",
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Citizens Case Group",
        "Beschreibung Fallgruppe",
        norm_addressee="citizens",
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Citizens Step",
        "Beschreibung Schritt",
        norm_addressee="citizens",
    )

    db.upsert_tile(
        Tile(
            id=f"process_{process_id}",
            title="Citizens Process",
            text="Beschreibung Prozess",
            meta_information={"process_id": process_id},
            column=2,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
        norm_addressee="citizens",
    )
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Citizens Case Group",
            text="Beschreibung Fallgruppe",
            meta_information={"case_group_id": case_group_id, "process_id": process_id},
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[f"process_{process_id}"],
        ),
        session_id=session_id,
        norm_addressee="citizens",
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_id}",
            title="Citizens Step",
            text="Beschreibung Schritt",
            meta_information={"step_id": step_id, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[f"case_group_{case_group_id}"],
        ),
        session_id=session_id,
        norm_addressee="citizens",
    )

    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=case_group_id,
        norm_addressee="citizens",
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )

    conn = db.get_conn()
    try:
        conn.execute("DROP TRIGGER IF EXISTS trg_process_steps_citizens_no_hourly_rates_ai")
        conn.execute("DROP TRIGGER IF EXISTS trg_process_steps_citizens_no_hourly_rates_au")
        conn.execute(
            """
            UPDATE process_steps
            SET hourly_rate_a_proposed = ?, time_required_in_min_a_proposed = ?, expenses_proposed = ?
            WHERE session_id = ? AND step_id = ? AND norm_addressee = 'citizens'
            """,
            (999.0, 60.0, 10.0, session_id, step_id),
        )
        conn.commit()
    finally:
        conn.close()

    resp = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-CITIZENS-IGNORE-RATES", "norm_addressee": "citizens"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_cost"] is None
    assert payload["total_time_minutes"] == pytest.approx(60.0)
    assert payload["total_expenses"] == pytest.approx(10.0)
    totals = db.get_session_total_costs_by_addressee(session_id, CITIZENS)
    assert totals is not None
    assert totals["total_cost"] is None
    assert totals["bureaucracy_cost"] is None
    assert totals["total_time_minutes"] == pytest.approx(60.0)
    assert totals["total_expenses"] == pytest.approx(10.0)
