from backend.core import db


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
