"""Phase D2d: wage provenance in step tiles (Julia Comment 2).

Step tiles for the row-based model show the wage source + qualification per
personnel row (e.g. "Bund - gD", "R - Mittel") and use the
effective rate/time, so a row edit is reflected instead of stale slot data.
"""

from backend.core import db
from backend.core.db_formatting import build_process_step_tile_text_from_rows
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS, personnel_provenance_label
from backend.core.tile_refresh import build_step_tile_text


def _row(period, qualification, kind, value, *, base=None, edited=None, rate=0.0):
    return {
        "period": period,
        "qualification": qualification,
        "wage_source_kind": kind,
        "wage_source_value": value,
        "time_required_in_min": base,
        "time_required_in_min_edited": edited,
        "model_hourly_rate": rate,
    }


def test_provenance_label_admin_and_business():
    assert personnel_provenance_label(ADMINISTRATION, "bund", "gehobener_dienst") == "Bund - gD"
    assert personnel_provenance_label(BUSINESS, "R", "mittel") == "R - Mittel"
    # Unknown source falls back to the bare value (business WZ letters).
    assert personnel_provenance_label(BUSINESS, "K", "hoch") == "K - Hoch"


def test_tile_text_from_rows_shows_provenance():
    text = build_process_step_tile_text_from_rows(
        description="Schritt",
        norm_addressee=ADMINISTRATION,
        current_rows=[_row("current", "gehobener_dienst", "verwaltungsebene", "bund", base=30, rate=40.4)],
        proposed_rows=[],
        expenses_current=None,
        cost_current=None,
        expenses_proposed=None,
        cost_proposed=None,
        execution_per_case=None,
    )
    assert "Aktuell: Bund - gD: 30 Min." in text
    assert "Std." in text


def test_tile_text_from_rows_override_wins_over_model_rate():
    overrides = {("verwaltungsebene", "bund", "gehobener_dienst"): 50.0}
    text = build_process_step_tile_text_from_rows(
        description="",
        norm_addressee=ADMINISTRATION,
        current_rows=[_row("current", "gehobener_dienst", "verwaltungsebene", "bund", base=60, rate=40.4)],
        proposed_rows=[],
        expenses_current=None,
        cost_current=None,
        expenses_proposed=None,
        cost_proposed=None,
        execution_per_case=None,
        wage_overrides=overrides,
    )
    assert "50" in text
    assert "40,4" not in text and "40.4" not in text


def test_tile_text_from_rows_edited_time_wins_over_base():
    text = build_process_step_tile_text_from_rows(
        description="",
        norm_addressee=BUSINESS,
        current_rows=[_row("current", "mittel", "wirtschaftsabschnitt", "R", base=30, edited=12, rate=32.2)],
        proposed_rows=[],
        expenses_current=None,
        cost_current=None,
        expenses_proposed=None,
        cost_proposed=None,
        execution_per_case=None,
    )
    assert "R - Mittel: 12 Min." in text
    assert "30 Min." not in text


def test_build_step_tile_text_uses_rows_when_present(test_client):
    session_id, _ = db.upsert_session("TILE-ROWS", "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung", norm_addressee=ADMINISTRATION)
    case_group_id = db.insert_case_group(session_id, process_id, "FG", "Beschreibung", norm_addressee=ADMINISTRATION)
    step_id = db.insert_process_step(session_id, case_group_id, "Schritt", "Beschreibung Schritt", norm_addressee=ADMINISTRATION)
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_id,
        [
            {"period": "current", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
             "time_required_in_min": 30, "model_hourly_rate": 40.4},
        ],
    )
    step = next(s for s in db.list_process_steps_for_session_and_addressee(session_id, ADMINISTRATION) if s["step_id"] == step_id)
    text = build_step_tile_text(session_id, step, ADMINISTRATION)
    assert "Bund - gD" in text


def test_build_step_tile_text_citizens_falls_back_to_slots(test_client):
    # Citizens have no monetised personnel rows; the tile keeps the slot path
    # (time only, no wage provenance).
    session_id, _ = db.upsert_session("TILE-CITIZENS", "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung", norm_addressee=CITIZENS)
    case_group_id = db.insert_case_group(session_id, process_id, "FG", "Beschreibung", norm_addressee=CITIZENS)
    step_id = db.insert_process_step(session_id, case_group_id, "Schritt", "Beschreibung Buerger", norm_addressee=CITIZENS)
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=CITIZENS,
        hourly_rates_current={"a": None, "b": None, "c": None, "d": None},
        time_required_current={"a": 20, "b": None, "c": None, "d": None},
        expenses_current=None,
        hourly_rates_proposed={"a": None, "b": None, "c": None, "d": None},
        time_required_proposed={"a": None, "b": None, "c": None, "d": None},
        expenses_proposed=None,
        role_sources_current=None,
        role_sources_proposed=None,
    )
    step = next(s for s in db.list_process_steps_for_session_and_addressee(session_id, CITIZENS) if s["step_id"] == step_id)
    text = build_step_tile_text(session_id, step, CITIZENS)
    assert "20 Min." in text
    assert " - " not in text  # no provenance label for citizens


def test_get_tiles_self_heals_pre_provenance_step_tiles(test_client):
    # A step tile persisted before the personnel_rows field (no provenance) is
    # refreshed in place on the next GET, so old sessions show provenance without
    # a manual recompute.
    app_id = "TILE-SELFHEAL"
    session_id, _ = db.upsert_session(app_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung", norm_addressee=ADMINISTRATION)
    case_group_id = db.insert_case_group(session_id, process_id, "FG", "Beschreibung", norm_addressee=ADMINISTRATION)
    step_id = db.insert_process_step(session_id, case_group_id, "Schritt", "Beschreibung Schritt", norm_addressee=ADMINISTRATION)
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_id,
        [
            {"period": "current", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "laender",
             "time_required_in_min": 12, "model_hourly_rate": 43.2},
        ],
    )
    # Old-format tile: meta WITHOUT personnel_rows, qualification-only text.
    db.upsert_tile(
        Tile(
            id=f"step_{step_id}",
            title="Schritt",
            text="Beschreibung Schritt\nAktuell: Gehobener Dienst: 12 Min., 43.20 €/Std.",
            meta_information={"step_id": step_id, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )

    resp = test_client.get("/tiles", params={"app_session_id": app_id, "norm_addressee": ADMINISTRATION})
    assert resp.status_code == 200
    step_tile = next(t for t in resp.json()["tiles"] if t["id"] == f"step_{step_id}")
    assert step_tile["meta_information"].get("personnel_rows") == [
        {"label": "Länder - gD", "current_min": 12.0, "proposed_min": None}
    ]
    assert "Länder - gD" in step_tile["text"]
