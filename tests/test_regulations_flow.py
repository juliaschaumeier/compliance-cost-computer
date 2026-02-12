from pathlib import Path

from backend.core import db
from backend.routers import regulations as regulations_router


def test_identify_regulations_flow(test_client, monkeypatch):
    """Runs summary + identify flow and verifies tiles/regulations/answers are stored."""
    db.insert_law("current.txt", "aktuelles gesetz")
    db.insert_law("proposed.txt", "neuer entwurf")

    responses = iter(
        [
            '{"title": "Kurz", "blurb": "Ein Satz."}',
            """<think>plan</think>
            {
              "vorgaben": [
                {"normzitat": "§ 1", "beschreibung": "Vorgabe A"},
                {"normzitat": "§ 2", "beschreibung": "Vorgabe B"}
              ]
            }""",
        ]
    )

    async def fake_query_llm(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(regulations_router, "query_llm", fake_query_llm)

    summary_resp = test_client.post(
        "/regulations/summary",
        json={
            "filename": "proposed.txt",
            "current_filename": "current.txt",
            "app_session_id": "ABC123",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert summary_resp.status_code == 200

    identify_resp = test_client.post(
        "/regulations/identify",
        json={
            "current_filename": "current.txt",
            "proposed_filename": "proposed.txt",
            "app_session_id": "ABC123",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert identify_resp.status_code == 200
    payload = identify_resp.json()
    assert len(payload["vorgaben"]) == 2

    session_id = db.get_session_id_by_app_id("ABC123")
    assert session_id is not None
    regs = db.list_regulations_for_session(session_id)
    assert [r["legal_citation"] for r in regs] == ["§ 1", "§ 2"]

    tiles = db.fetch_tiles()
    assert any(tile.id == "law_tile" for tile in tiles)
    reg_tiles = [tile for tile in tiles if tile.id.startswith("regulation_")]
    assert len(reg_tiles) == 2
    assert all("law_tile" in tile.link_from_tile for tile in reg_tiles)

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT prompt_id FROM llm_answers ORDER BY answer_id")
    prompt_ids = [row["prompt_id"] for row in cur.fetchall()]
    conn.close()
    assert prompt_ids == ["law_summary", "regulations_identification"]

    async def fail_query_llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called on repeat identify")

    monkeypatch.setattr(regulations_router, "query_llm", fail_query_llm)

    repeat_resp = test_client.post(
        "/regulations/identify",
        json={
            "current_filename": "current.txt",
            "proposed_filename": "proposed.txt",
            "app_session_id": "ABC123",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert repeat_resp.status_code == 200
    repeat_payload = repeat_resp.json()
    assert repeat_payload["status"] == "existing"
