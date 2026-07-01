import inspect

import pytest

from backend.core import db
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from tests.activity_helpers import ea_payload_for_session
from backend.core.session_graph import build_session_tiles_snapshot


def test_upsert_process_step_cost_by_addressee_has_no_dead_breakdown_params():
    """Regression: Die Funktion hatte tote Parameter bureaucracy_cost_* /
    other_cost_*, die vom UPDATE ignoriert wurden (entsprechende Spalten
    existieren nicht im process_steps-Schema). Die Bürokratiekosten-
    Aggregation läuft ausschließlich auf Session-Ebene
    (session_total_costs_by_addressee.bureaucracy_cost). Signatur darf
    keine versteckten Kostenaufteilungs-Parameter zurückbringen, bevor
    ein konkreter Step-Level-Consumer existiert."""
    params = set(inspect.signature(db.upsert_process_step_cost_by_addressee).parameters)
    assert params == {
        "session_id",
        "step_id",
        "norm_addressee",
        "cost_current",
        "cost_proposed",
    }


def test_get_cost_totals_returns_persisted_addressee_totals(test_client):
    session_id, _ = db.upsert_session("COST-TOTALS", "test-model")
    db.upsert_session_total_costs_by_addressee(
        session_id,
        ADMINISTRATION,
        total_cost=35305.2,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )
    db.upsert_session_total_costs_by_addressee(
        session_id,
        BUSINESS,
        total_cost=78202.0,
        bureaucracy_cost=78202.0,
        total_time_minutes=None,
        total_expenses=None,
    )

    resp = test_client.get("/costs/totals", params={"app_session_id": "COST-TOTALS"})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["administration"]["total_cost"] == pytest.approx(35305.2)
    assert payload["business"]["total_cost"] == pytest.approx(78202.0)
    assert payload["business"]["bureaucracy_cost"] == pytest.approx(78202.0)
    assert payload["citizens"] is None


def test_total_cost_readiness_requires_explicit_total_row():
    session_id, _ = db.upsert_session("COST-READY-EXPLICIT", "test-model")
    db.update_session_summary(
        "COST-READY-EXPLICIT",
        "Titel",
        "Zusammenfassung",
    )
    db.insert_regulation(
        session_id,
        "§ 1",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    db.insert_process(
        session_id,
        "Prozess Verwaltung",
        "Beschreibung",
        cost=123.0,
        norm_addressee=ADMINISTRATION,
    )

    status = db.get_session_status("COST-READY-EXPLICIT")

    assert status is not None
    assert status["total_cost_ready_by_addressee"][ADMINISTRATION] is False
    assert status["total_cost_ready_by_addressee"][BUSINESS] is True
    assert status["total_cost_ready_by_addressee"][CITIZENS] is True
    assert status["total_cost_ready"] is False


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


def test_compute_costs_business_time_only_uses_baseline_row_not_gesamtwirtschaft(
    test_client,
):
    """Regression (M-2): Ein Schritt mit Zeit, aber OHNE per-Schritt-Modell-Satz und
    OHNE Override faellt auf die tatsaechlich genutzte Baseline-Zeile zurueck
    (role_sources -> "K"), nicht mehr auf den Gesamtwirtschaft-Snapshot.
    K.a = 29.0, Gesamtwirtschaft.a = 26.1; 1 h -> 29.0 belegt die genutzte Zeile."""
    session_id, _ = db.upsert_session("COST-BUSINESS-BASELINE-ROW", "test-model")
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
    for tile_id, title, link_from, column, meta in (
        (f"process_{process_id}", "Business Process", [], 2, {"process_id": process_id}),
        (
            f"case_group_{case_group_id}",
            "Business Case Group",
            [f"process_{process_id}"],
            3,
            {"case_group_id": case_group_id, "process_id": process_id},
        ),
        (
            f"step_{step_id}",
            "Business Step",
            [f"case_group_{case_group_id}"],
            4,
            {"step_id": step_id, "case_group_id": case_group_id},
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
    # Time on slot a but no per-step model rate; used row via role_sources = "K".
    role_sources = [
        {
            "slot": "a",
            "role": "",
            "source_kind": "wirtschaftsabschnitt",
            "source_value": "K",
        }
    ]
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
        role_sources_current=role_sources,
        role_sources_proposed=role_sources,
    )

    # Make sure the used baseline row is actually "K".
    assert db.get_used_wage_baseline(session_id, BUSINESS) == "K"

    resp = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-BUSINESS-BASELINE-ROW", "norm_addressee": BUSINESS},
    )
    assert resp.status_code == 200
    # K.a = 29.0 (nicht Gesamtwirtschaft 26.1).
    assert resp.json()["total_cost"] == pytest.approx(29.0)


def test_compute_costs_business_allocates_bureaucracy_proportionally_for_mixed_steps(
    test_client,
):
    """Leitfaden-konform: wenn ein Schritt an 2 Vorgaben gekoppelt ist, von denen
    nur eine Informationspflicht ist, werden 50 % der Schrittkosten als
    Buerokratiekosten verbucht - nicht der volle Schritt."""
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
    assert payload["bureaucracy_cost"] == pytest.approx(50.0)
    assert payload["other_cost"] == pytest.approx(50.0)
    totals = db.get_session_total_costs_by_addressee(session_id, BUSINESS)
    assert totals is not None
    assert totals["total_cost"] == pytest.approx(100.0)
    assert totals["bureaucracy_cost"] == pytest.approx(50.0)
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

    session = db.get_session_by_id(session_id)
    assert session is not None
    rebuilt_tiles = build_session_tiles_snapshot(session, CITIZENS)
    total_tile = next(tile for tile in rebuilt_tiles if tile.id == "total_cost")
    assert total_tile.title == "Jährlicher Aufwand"
    assert total_tile.text == "Zeit: 1 Std.\nSachaufwand: 10 €"
    assert total_tile.meta_information["total_time_minutes"] == pytest.approx(60.0)
    assert total_tile.meta_information["total_time_hours"] == pytest.approx(1.0)
    assert total_tile.meta_information["total_expenses"] == pytest.approx(10.0)


def test_rebuild_non_citizen_tiles_omits_total_without_stored_total_row():
    session_id, _ = db.upsert_session("COST-REBUILD-TOTAL-META", "test-model")
    db.update_session_summary(
        "COST-REBUILD-TOTAL-META",
        "Titel",
        "Zusammenfassung",
    )
    process_id = db.insert_process(
        session_id,
        "Administration Process",
        "Beschreibung Prozess",
        cost=-1655330000.0,
        norm_addressee=ADMINISTRATION,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Administration Case Group",
        "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    db.insert_process_step(
        session_id,
        case_group_id,
        "Administration Step",
        "Beschreibung Schritt",
        norm_addressee=ADMINISTRATION,
    )

    session = db.get_session_by_id(session_id)
    assert session is not None
    rebuilt_tiles = build_session_tiles_snapshot(session, ADMINISTRATION)

    assert not any(tile.id == "total_cost" for tile in rebuilt_tiles)


def test_rebuild_non_citizen_total_tile_includes_numeric_metadata():
    session_id, _ = db.upsert_session("COST-REBUILD-TOTAL-META-READY", "test-model")
    db.update_session_summary(
        "COST-REBUILD-TOTAL-META-READY",
        "Titel",
        "Zusammenfassung",
    )
    process_id = db.insert_process(
        session_id,
        "Administration Process",
        "Beschreibung Prozess",
        cost=-1655330000.0,
        norm_addressee=ADMINISTRATION,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Administration Case Group",
        "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    db.insert_process_step(
        session_id,
        case_group_id,
        "Administration Step",
        "Beschreibung Schritt",
        norm_addressee=ADMINISTRATION,
    )
    db.upsert_session_total_costs_by_addressee(
        session_id,
        ADMINISTRATION,
        total_cost=-1655330000.0,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )

    session = db.get_session_by_id(session_id)
    assert session is not None
    rebuilt_tiles = build_session_tiles_snapshot(session, ADMINISTRATION)

    total_tile = next(tile for tile in rebuilt_tiles if tile.id == "total_cost")
    assert total_tile.meta_information["norm_addressee"] == ADMINISTRATION
    assert total_tile.meta_information["total_cost"] == pytest.approx(-1655330000.0)
    assert total_tile.meta_information["total_time_minutes"] is None
    assert total_tile.meta_information["total_expenses"] is None


def _set_admin_pay_rate_override(test_client, app_session_id: str, **edited: float | None):
    """Setzt einen manuellen Lohnsatz-Override realistisch ueber den oeffentlichen
    Endpoint POST /sessions/pay-rates (nicht per direktem SQL)."""
    payload = {
        "app_session_id": app_session_id,
        "norm_addressee": ADMINISTRATION,
        "edited_a": edited.get("a"),
        "edited_b": edited.get("b"),
        "edited_c": edited.get("c"),
        "edited_d": edited.get("d"),
    }
    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    payload = ea_payload_for_session(session_id, payload)
    resp = test_client.post("/sessions/pay-rates", json=payload)
    assert resp.status_code == 200, resp.text
    db.clear_session_activity(session_id, payload["ea_activity_id"])
    return resp.json()


def test_manual_pay_rate_override_beats_per_step_rate(test_client):
    """B1: Ein manuell gesetzter Override (Stufe b) schlaegt den pro Schritt vom
    Modell zugewiesenen hourly_rate_b; die Gesamtsumme entspricht dem Override."""
    session_id, _ = db.upsert_session("COST-OVERRIDE-B1", "test-model")
    seeded = _seed_flow(session_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )
    # Step 1 carries the per-step model rate b = 50; step 2 has no effort.
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_one"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 50, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 60, "c": None, "d": None},
        expenses_proposed=None,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 50, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 0, "c": None, "d": None},
        expenses_proposed=None,
    )

    # Without override: model rate 50 EUR/h * 1 h = 50.
    resp_no_override = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-OVERRIDE-B1"}
    )
    assert resp_no_override.status_code == 200
    assert resp_no_override.json()["total_cost"] == pytest.approx(50.0)

    # With override b = 80: override beats the model rate -> 80 EUR/h * 1 h = 80.
    _set_admin_pay_rate_override(test_client, "COST-OVERRIDE-B1", b=80)
    resp_override = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-OVERRIDE-B1"}
    )
    assert resp_override.status_code == 200
    assert resp_override.json()["total_cost"] == pytest.approx(80.0)


def test_no_override_uses_per_step_model_rate(test_client):
    """B2: Ohne Override wird der pro Schritt zugewiesene Modell-Satz genutzt;
    Kosten bleiben unveraendert (Regression)."""
    session_id, _ = db.upsert_session("COST-OVERRIDE-B2", "test-model")
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
        hourly_rates_proposed={"a": 70, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 70, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 0, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-OVERRIDE-B2"}
    )
    assert resp.status_code == 200
    assert resp.json()["total_cost"] == pytest.approx(70.0)


def test_override_only_b_keeps_other_slots_on_model_rate(test_client):
    """B3: Override nur fuer Stufe b -> a/c/d behalten ihre Modell-Schritt-Saetze."""
    session_id, _ = db.upsert_session("COST-OVERRIDE-B3", "test-model")
    seeded = _seed_flow(session_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )
    # 60 min (1 h) per slot with a model rate; sum without override = 10+20+30+40 = 100.
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_one"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 10, "b": 20, "c": 30, "d": 40},
        time_required_proposed={"a": 60, "b": 60, "c": 60, "d": 60},
        expenses_proposed=None,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 10, "b": 20, "c": 30, "d": 40},
        time_required_proposed={"a": 0, "b": 0, "c": 0, "d": 0},
        expenses_proposed=None,
    )

    _set_admin_pay_rate_override(test_client, "COST-OVERRIDE-B3", b=80)
    resp = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-OVERRIDE-B3"}
    )
    assert resp.status_code == 200
    # Nur b durch 80 ersetzt: 10 + 80 + 30 + 40 = 160.
    assert resp.json()["total_cost"] == pytest.approx(160.0)


def test_override_applies_to_current_and_proposed(test_client):
    """B4: Der Override wirkt in current UND proposed."""
    session_id, _ = db.upsert_session("COST-OVERRIDE-B4", "test-model")
    seeded = _seed_flow(session_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_current=1,
        annual_frequency_current=1,
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )
    # current and proposed each 1 h of effort on slot b with model rate 50.
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_one"],
        hourly_rates_current={"a": None, "b": 50, "c": None, "d": None},
        time_required_current={"a": None, "b": 60, "c": None, "d": None},
        expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 50, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 60, "c": None, "d": None},
        expenses_proposed=None,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_two"],
        hourly_rates_current={"a": None, "b": 50, "c": None, "d": None},
        time_required_current={"a": None, "b": 0, "c": None, "d": None},
        expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 50, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 0, "c": None, "d": None},
        expenses_proposed=None,
    )

    _set_admin_pay_rate_override(test_client, "COST-OVERRIDE-B4", b=80)
    resp = test_client.post(
        "/costs/compute", json={"app_session_id": "COST-OVERRIDE-B4"}
    )
    assert resp.status_code == 200

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT cost_current, cost_proposed FROM process_steps WHERE step_id = ?",
        (seeded["step_one"],),
    )
    row = cur.fetchone()
    conn.close()
    # current AND proposed use the override 80 instead of the model rate 50.
    assert row["cost_current"] == pytest.approx(80.0)
    assert row["cost_proposed"] == pytest.approx(80.0)


def test_override_does_not_affect_citizens(test_client):
    """B5: Buerger haben keine Lohnsaetze; ein Lohnsatz hat keinen Kosteneffekt (0)."""
    session_id, _ = db.upsert_session("COST-OVERRIDE-B5", "test-model")
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
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee="citizens",
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=10.0,
    )

    resp = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-OVERRIDE-B5", "norm_addressee": "citizens"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    # Citizens carry no wage costs; only the expenses (10) count.
    assert payload["total_cost"] is None
    assert payload["total_time_minutes"] == pytest.approx(60.0)
    assert payload["total_expenses"] == pytest.approx(10.0)


def _set_business_pay_rate_override(test_client, app_session_id: str, **edited: float | None):
    """Like _set_admin_pay_rate_override but for business: no administration_level
    (which would raise 422 for business)."""
    payload = {
        "app_session_id": app_session_id,
        "norm_addressee": BUSINESS,
        "edited_a": edited.get("a"),
        "edited_b": edited.get("b"),
        "edited_c": edited.get("c"),
        "edited_d": edited.get("d"),
    }
    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    payload = ea_payload_for_session(session_id, payload)
    resp = test_client.post("/sessions/pay-rates", json=payload)
    assert resp.status_code == 200, resp.text
    db.clear_session_activity(session_id, payload["ea_activity_id"])
    return resp.json()


def _seed_business_single_step(session_id: int, *, model_rate_a: float) -> None:
    process_id = db.insert_process(session_id, "Business Process", "d", norm_addressee=BUSINESS)
    case_group_id = db.insert_case_group(
        session_id, process_id, "Business Case Group", "d", norm_addressee=BUSINESS
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Business Step", "d", norm_addressee=BUSINESS
    )
    for tile_id, column, link in (
        (f"process_{process_id}", 2, []),
        (f"case_group_{case_group_id}", 3, [f"process_{process_id}"]),
        (f"step_{step_id}", 4, [f"case_group_{case_group_id}"]),
    ):
        db.upsert_tile(
            Tile(
                id=tile_id,
                title="t",
                text="d",
                meta_information={},
                column=column,
                row=0,
                deletable=True,
                link_from_tile=link,
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
        hourly_rates_proposed={"a": model_rate_a, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 60, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )


def test_manual_business_pay_rate_override_beats_per_step_rate(test_client):
    """B6: like B1 but for business. A business override set via the pay-rates tab
    beats the per-step model rate and flows into the computed total (the path that was
    untested and hid the earlier business recompute bug)."""
    session_id, _ = db.upsert_session("COST-OVERRIDE-B6", "test-model")
    _seed_business_single_step(session_id, model_rate_a=50)

    # Without override: model rate 50 EUR/h * 1 h = 50.
    resp_no_override = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-OVERRIDE-B6", "norm_addressee": BUSINESS},
    )
    assert resp_no_override.status_code == 200
    assert resp_no_override.json()["total_cost"] == pytest.approx(50.0)

    # With override a = 80: override beats the model rate -> 80 EUR/h * 1 h = 80.
    _set_business_pay_rate_override(test_client, "COST-OVERRIDE-B6", a=80)
    resp_override = test_client.post(
        "/costs/compute",
        json={"app_session_id": "COST-OVERRIDE-B6", "norm_addressee": BUSINESS},
    )
    assert resp_override.status_code == 200
    assert resp_override.json()["total_cost"] == pytest.approx(80.0)


def _seed_proposed_cases(session_id, case_group_id):
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_proposed=1,
        annual_frequency_proposed=1,
    )


def test_compute_costs_row_model_sums_mixed_sources(test_client):
    # Bund and Laender (same qualification) in one step are summed per row -- the
    # legacy slot model could only keep one rate for that qualification.
    session_id, _ = db.upsert_session("COST-ROWS-MIXED", "test-model")
    seeded = _seed_flow(session_id)
    _seed_proposed_cases(session_id, seeded["case_group_id"])
    step_one, step_two = seeded["step_one"], seeded["step_two"]

    # Dual-write reality: slot carries the aggregated time (passes cost-input
    # validation); child rows carry the per-source detail and drive the cost.
    db.update_process_step_effort_split(
        session_id=session_id, step_id=step_one,
        hourly_rates_current={}, time_required_current={}, expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 42.0, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 60, "c": None, "d": None},
        expenses_proposed=None,
    )
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_one,
        [
            {"period": "proposed", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
             "time_required_in_min": 30, "model_hourly_rate": 40.4},
            {"period": "proposed", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "laender",
             "time_required_in_min": 30, "model_hourly_rate": 43.2},
        ],
    )
    # step_two stays on the legacy slot fallback (no child rows) in the same run.
    db.update_process_step_effort_split(
        session_id=session_id, step_id=step_two,
        hourly_rates_current={}, time_required_current={}, expenses_current=None,
        hourly_rates_proposed={"a": 60.0, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.post("/costs/compute", json={"app_session_id": "COST-ROWS-MIXED"})
    assert resp.status_code == 200

    conn = db.get_conn()
    c1 = conn.execute("SELECT cost_proposed FROM process_steps WHERE step_id=?", (step_one,)).fetchone()["cost_proposed"]
    c2 = conn.execute("SELECT cost_proposed FROM process_steps WHERE step_id=?", (step_two,)).fetchone()["cost_proposed"]
    # Row model: 40.4*30/60 + 43.2*30/60 = 20.2 + 21.6 = 41.8 (not 42*60/60=42)
    assert c1 == pytest.approx(41.8)
    # Legacy fallback still works in the same session: 60*30/60 = 30
    assert c2 == pytest.approx(30.0)


def test_compute_costs_row_model_override_wins_and_expenses_once(test_client):
    # A session wage override beats the model rate; step expenses are added once
    # per step, not per personnel row.
    session_id, _ = db.upsert_session("COST-ROWS-OVR", "test-model")
    seeded = _seed_flow(session_id)
    _seed_proposed_cases(session_id, seeded["case_group_id"])
    step_one, step_two = seeded["step_one"], seeded["step_two"]

    db.update_process_step_effort_split(
        session_id=session_id, step_id=step_one,
        hourly_rates_current={}, time_required_current={}, expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 40.4, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 60, "c": None, "d": None},
        expenses_proposed=10,
    )
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_one,
        [
            {"period": "proposed", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
             "time_required_in_min": 60, "model_hourly_rate": 40.4},
        ],
    )
    # Override for (verwaltungsebene, bund, gehobener_dienst) -> 50.0
    conn = db.get_conn()
    conn.execute(
        """
        INSERT INTO session_wage_rate_overrides (
            session_id, norm_addressee, wage_source_kind, wage_source_value,
            qualification, hourly_rate_edited, last_edited_at
        ) VALUES (?, 'administration', 'verwaltungsebene', 'bund',
                  'gehobener_dienst', 50.0, current_timestamp)
        """,
        (session_id,),
    )
    conn.commit()
    db.update_process_step_effort_split(
        session_id=session_id, step_id=step_two,
        hourly_rates_current={}, time_required_current={}, expenses_current=None,
        hourly_rates_proposed={"a": 60.0, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 10, "b": None, "c": None, "d": None},
        expenses_proposed=None,
    )

    resp = test_client.post("/costs/compute", json={"app_session_id": "COST-ROWS-OVR"})
    assert resp.status_code == 200

    cost = db.get_conn().execute(
        "SELECT cost_proposed FROM process_steps WHERE step_id=?", (step_one,)
    ).fetchone()["cost_proposed"]
    # Override 50.0 * 60/60 + expenses 10 (once) = 60.0  (model 40.4 would give 50.4)
    assert cost == pytest.approx(60.0)
