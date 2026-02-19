import sqlite3

import pytest

from backend.core import db
from backend.core.models import Tile


def _tile_payload(tile_id: str, title: str) -> dict:
    return {
        "id": tile_id,
        "title": title,
        "text": "",
        "meta_information": {},
        "column": 0,
        "row": 0,
        "deletable": True,
        "link_from_tile": [],
    }


def test_tiles_are_scoped_by_app_session_id(test_client):
    session_a = "SCOPE-A"
    session_b = "SCOPE-B"

    resp_a = test_client.post(
        "/sessions",
        json={"app_session_id": session_a, "llm_model": "test-model"},
    )
    assert resp_a.status_code == 200
    resp_b = test_client.post(
        "/sessions",
        json={"app_session_id": session_b, "llm_model": "test-model"},
    )
    assert resp_b.status_code == 200

    create_a = test_client.post(
        f"/tiles?app_session_id={session_a}",
        json=_tile_payload("tile_a", "Tile A"),
    )
    assert create_a.status_code == 200
    create_b = test_client.post(
        f"/tiles?app_session_id={session_b}",
        json=_tile_payload("tile_b", "Tile B"),
    )
    assert create_b.status_code == 200

    list_a = test_client.get("/tiles", params={"app_session_id": session_a})
    assert list_a.status_code == 200
    ids_a = {tile["id"] for tile in list_a.json()["tiles"]}
    assert ids_a == {"tile_a"}

    list_b = test_client.get("/tiles", params={"app_session_id": session_b})
    assert list_b.status_code == 200
    ids_b = {tile["id"] for tile in list_b.json()["tiles"]}
    assert ids_b == {"tile_b"}


def test_tile_delete_is_scoped_by_session(test_client):
    session_a = "DEL-A"
    session_b = "DEL-B"
    test_client.post(
        "/sessions",
        json={"app_session_id": session_a, "llm_model": "test-model"},
    )
    test_client.post(
        "/sessions",
        json={"app_session_id": session_b, "llm_model": "test-model"},
    )

    test_client.post(
        f"/tiles?app_session_id={session_a}",
        json=_tile_payload("shared_id", "A"),
    )
    test_client.post(
        f"/tiles?app_session_id={session_b}",
        json=_tile_payload("shared_id", "B"),
    )

    delete_resp = test_client.delete(
        "/tiles/shared_id", params={"app_session_id": session_a}
    )
    assert delete_resp.status_code == 200

    list_a = test_client.get("/tiles", params={"app_session_id": session_a})
    assert list_a.status_code == 200
    assert list_a.json()["tiles"] == []

    list_b = test_client.get("/tiles", params={"app_session_id": session_b})
    assert list_b.status_code == 200
    ids_b = {tile["id"] for tile in list_b.json()["tiles"]}
    assert ids_b == {"shared_id"}


def test_tiles_endpoints_require_app_session_id(test_client):
    tile_payload = _tile_payload("tile_x", "Tile X")

    assert test_client.get("/tiles").status_code == 422
    assert test_client.post("/tiles", json=tile_payload).status_code == 422
    assert test_client.delete("/tiles/tile_x").status_code == 422


def test_rebuild_requires_app_session_id(test_client):
    resp = test_client.post("/tiles/rebuild", json={})
    assert resp.status_code == 422


def test_upsert_tile_without_session_raises(test_client):
    with pytest.raises(TypeError):
        db.upsert_tile(
            Tile(
                id="orphan_tile",
                title="Orphan Tile",
                text="",
                meta_information={},
                column=0,
                row=0,
                deletable=True,
                link_from_tile=[],
            )
        )


def test_tiles_schema_enforces_not_null_and_deletable_check(test_client):
    session_id, _ = db.upsert_session("TILES-CHECK", "test-model")

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(tiles)")
    columns = {str(row[1]): row for row in cur.fetchall()}
    assert int(columns["col"][3]) == 1
    assert int(columns["row"][3]) == 1
    assert int(columns["deletable"][3]) == 1

    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            """
            INSERT INTO tiles (session_id, id, title, text, meta, col, row, deletable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, "bad_deletable", "bad", "", "{}", 0, 0, 2),
        )
    conn.close()
