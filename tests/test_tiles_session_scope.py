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
