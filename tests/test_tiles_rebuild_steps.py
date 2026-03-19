from backend.core import db
from backend.core.models import Tile


def test_rebuild_tiles_keeps_step_order(test_client):
    """Rebuild keeps step tiles on the case-group row and ordered by linked list."""
    session_id, _ = db.upsert_session("TILES-REBUILD", "test-model")
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
    step_three = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt 3",
        "Beschreibung Schritt 3",
        previous_id=step_two,
    )
    db.update_process_step_next(step_one, step_two)
    db.update_process_step_next(step_two, step_three)

    resp = test_client.post("/tiles/rebuild", json={"app_session_id": "TILES-REBUILD"})
    assert resp.status_code == 200

    tiles = db.fetch_tiles(session_id=session_id)
    case_tile = next(tile for tile in tiles if tile.id == f"case_group_{case_group_id}")
    step_tiles = [
        tile
        for tile in tiles
        if tile.id in {f"step_{step_one}", f"step_{step_two}", f"step_{step_three}"}
    ]
    assert len(step_tiles) == 3
    assert all(tile.row == case_tile.row for tile in step_tiles)
    by_id = {tile.id: tile for tile in step_tiles}
    assert by_id[f"step_{step_one}"].column < by_id[f"step_{step_two}"].column
    assert by_id[f"step_{step_two}"].column < by_id[f"step_{step_three}"].column


def test_rebuild_uses_blurb_for_law_tile_text(test_client):
    app_session_id = "TILES-REBUILD-BLURB"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_law("rebuild-current.txt", "current law")
    db.insert_law("rebuild-proposed.txt", "proposed law")
    db.update_session_documents(app_session_id, "rebuild-current.txt", "rebuild-proposed.txt")
    db.update_session_summary(
        app_session_id,
        "Titel",
        "Lange Zusammenfassung fuer Prompt-Kontext",
        law_diff_blurb="Kurzer Blurb fuer Anzeige",
    )

    resp = test_client.post("/tiles/rebuild", json={"app_session_id": app_session_id})
    assert resp.status_code == 200

    law_tile = next(tile for tile in db.fetch_tiles(session_id=session_id) if tile.id == "law_tile")
    assert law_tile.text == "Kurzer Blurb fuer Anzeige"


def test_rebuild_tiles_populates_structured_metrics_meta(test_client):
    app_session_id = "TILES-STRUCTURED"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Prozessbeschreibung")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Fallgruppenbeschreibung"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt A", "Schrittbeschreibung"
    )
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_current=10,
        annual_frequency_current=2,
        addressees_proposed=12,
        annual_frequency_proposed=3,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_id,
        hourly_rates_current={"a": 33.8, "b": None, "c": None, "d": None},
        time_required_current={"a": 5, "b": None, "c": None, "d": None},
        expenses_current=1,
        hourly_rates_proposed={"a": 33.8, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 7, "b": None, "c": None, "d": None},
        expenses_proposed=2,
    )
    db.update_process_step_cost(
        session_id=session_id, step_id=step_id, cost_current=100, cost_proposed=120
    )

    resp = test_client.post("/tiles/rebuild", json={"app_session_id": app_session_id})
    assert resp.status_code == 200

    tiles = db.fetch_tiles(session_id=session_id)
    case_tile = next(tile for tile in tiles if tile.id == f"case_group_{case_group_id}")
    step_tile = next(tile for tile in tiles if tile.id == f"step_{step_id}")

    assert case_tile.text == "Fallgruppenbeschreibung"
    assert case_tile.meta_information["description"] == "Fallgruppenbeschreibung"
    assert case_tile.meta_information["addressees_current"] == 10
    assert case_tile.meta_information["annual_frequency_current"] == 2
    assert case_tile.meta_information["cases_current"] == 20
    assert case_tile.meta_information["addressees_proposed"] == 12
    assert case_tile.meta_information["annual_frequency_proposed"] == 3
    assert case_tile.meta_information["cases_proposed"] == 36

    assert step_tile.text == "Schrittbeschreibung"
    assert step_tile.meta_information["description"] == "Schrittbeschreibung"
    assert step_tile.meta_information["time_required_current"]["a"] == 5
    assert step_tile.meta_information["time_required_proposed"]["a"] == 7
    assert step_tile.meta_information["expenses_current"] == 1
    assert step_tile.meta_information["expenses_proposed"] == 2
    assert step_tile.meta_information["cost_current"] == 100
    assert step_tile.meta_information["cost_proposed"] == 120


def test_list_tiles_auto_rebuilds_stale_metrics_tiles(test_client):
    app_session_id = "TILES-AUTO-REBUILD"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Prozessbeschreibung")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Fallgruppenbeschreibung"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt A", "Schrittbeschreibung"
    )
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_current=2,
        annual_frequency_current=3,
        addressees_proposed=4,
        annual_frequency_proposed=5,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_id,
        hourly_rates_current={"a": 33.8, "b": None, "c": None, "d": None},
        time_required_current={"a": 1, "b": None, "c": None, "d": None},
        expenses_current=0.5,
        hourly_rates_proposed={"a": 33.8, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 2, "b": None, "c": None, "d": None},
        expenses_proposed=0.75,
    )

    rebuild = test_client.post("/tiles/rebuild", json={"app_session_id": app_session_id})
    assert rebuild.status_code == 200

    tiles = db.fetch_tiles(session_id=session_id)
    case_tile = next(tile for tile in tiles if tile.id == f"case_group_{case_group_id}")
    step_tile = next(tile for tile in tiles if tile.id == f"step_{step_id}")

    # Simulate stale persisted tiles from previous schema generation.
    db.upsert_tile(
        Tile(
            id=case_tile.id,
            title=case_tile.title,
            text=case_tile.text,
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
                "change_status": "geaendert",
            },
            column=case_tile.column,
            row=case_tile.row,
            deletable=case_tile.deletable,
            link_from_tile=case_tile.link_from_tile,
        ),
        session_id=session_id,
    )
    db.upsert_tile(
        Tile(
            id=step_tile.id,
            title=step_tile.title,
            text=step_tile.text,
            meta_information={
                "step_id": step_id,
                "case_group_id": case_group_id,
                "process_id": process_id,
                "change_status": "geaendert",
            },
            column=step_tile.column,
            row=step_tile.row,
            deletable=step_tile.deletable,
            link_from_tile=step_tile.link_from_tile,
        ),
        session_id=session_id,
    )

    listed = test_client.get("/tiles", params={"app_session_id": app_session_id})
    assert listed.status_code == 200
    listed_tiles = listed.json()["tiles"]
    listed_case = next(tile for tile in listed_tiles if tile["id"] == f"case_group_{case_group_id}")
    listed_step = next(tile for tile in listed_tiles if tile["id"] == f"step_{step_id}")

    assert "addressees_current" in listed_case["meta_information"]
    assert "annual_frequency_current" in listed_case["meta_information"]
    assert "time_required_current" in listed_step["meta_information"]
    assert "time_required_proposed" in listed_step["meta_information"]


def test_list_tiles_auto_rebuilds_when_text_does_not_match_description(test_client):
    app_session_id = "TILES-AUTO-REBUILD-TEXT"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Prozessbeschreibung")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Fallgruppenbeschreibung"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt A", "Schrittbeschreibung"
    )
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_current=2,
        annual_frequency_current=3,
        addressees_proposed=4,
        annual_frequency_proposed=5,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_id,
        hourly_rates_current={"a": 33.8, "b": None, "c": None, "d": None},
        time_required_current={"a": 1, "b": None, "c": None, "d": None},
        expenses_current=0.5,
        hourly_rates_proposed={"a": 33.8, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 2, "b": None, "c": None, "d": None},
        expenses_proposed=0.75,
    )

    rebuild = test_client.post("/tiles/rebuild", json={"app_session_id": app_session_id})
    assert rebuild.status_code == 200

    tiles = db.fetch_tiles(session_id=session_id)
    step_tile = next(tile for tile in tiles if tile.id == f"step_{step_id}")
    stale_meta = dict(step_tile.meta_information)
    db.upsert_tile(
        Tile(
            id=step_tile.id,
            title=step_tile.title,
            text="Schrittbeschreibung\neD/mD: 1 min | 2 min",
            meta_information=stale_meta,
            column=step_tile.column,
            row=step_tile.row,
            deletable=step_tile.deletable,
            link_from_tile=step_tile.link_from_tile,
        ),
        session_id=session_id,
    )

    listed = test_client.get("/tiles", params={"app_session_id": app_session_id})
    assert listed.status_code == 200
    listed_tiles = listed.json()["tiles"]
    listed_step = next(tile for tile in listed_tiles if tile["id"] == f"step_{step_id}")
    assert listed_step["text"] == "Schrittbeschreibung"
