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

    tiles = db.fetch_tiles(session_id=session_id)
    assert any(tile.id == "law_tile" for tile in tiles)
    reg_tiles = [tile for tile in tiles if tile.id.startswith("regulation_")]
    assert len(reg_tiles) == 2
    assert all("law_tile" in tile.link_from_tile for tile in reg_tiles)

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT prompt_id, answer_state, state_reason
        FROM llm_answers
        ORDER BY answer_id
        """
    )
    answer_rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    assert [row["prompt_id"] for row in answer_rows] == [
        "law_summary",
        "regulations_identification",
    ]
    assert all(row["answer_state"] == "active" for row in answer_rows)
    assert all(row["state_reason"] == "session_updated" for row in answer_rows)

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


def test_identify_regulations_normalizes_change_status_variants(test_client, monkeypatch):
    db.insert_law("status-current.txt", "aktuelles gesetz")
    db.insert_law("status-proposed.txt", "neuer entwurf")

    responses = iter(
        [
            '{"title": "Kurz", "blurb": "Ein Satz."}',
            """
    {
      "vorgaben": [
        {"normzitat": "§ 10", "beschreibung": "Neu", "change_status": "new"},
        {"normzitat": "§ 11", "beschreibung": "Geaendert", "status_change": "updated"},
        {"normzitat": "§ 12", "beschreibung": "Entfaellt", "status": "deleted"}
      ]
    }
    """,
        ]
    )

    async def fake_query_llm(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(regulations_router, "query_llm", fake_query_llm)

    summary_resp = test_client.post(
        "/regulations/summary",
        json={
            "filename": "status-proposed.txt",
            "current_filename": "status-current.txt",
            "app_session_id": "REG-STATUS-VARIANTS",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert summary_resp.status_code == 200

    resp = test_client.post(
        "/regulations/identify",
        json={
            "current_filename": "status-current.txt",
            "proposed_filename": "status-proposed.txt",
            "app_session_id": "REG-STATUS-VARIANTS",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert [row["aenderungsstatus"] for row in payload["vorgaben"]] == [
        "eingefuehrt",
        "geaendert",
        "abgeschafft",
    ]

    session_id = db.get_session_id_by_app_id("REG-STATUS-VARIANTS")
    assert session_id is not None
    rows = db.list_regulations_for_session(session_id)
    assert [row["change_status"] for row in rows] == [
        "eingefuehrt",
        "geaendert",
        "abgeschafft",
    ]


def test_summary_supersedes_previous_active_answer(test_client, monkeypatch):
    db.insert_law("summary-current.txt", "aktuelles gesetz")
    db.insert_law("summary-proposed.txt", "neuer entwurf")

    responses = iter(
        [
            '{"title": "Kurz 1", "blurb": "Ein Satz 1."}',
            '{"title": "Kurz 2", "blurb": "Ein Satz 2."}',
        ]
    )

    async def fake_query_llm(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(regulations_router, "query_llm", fake_query_llm)

    first = test_client.post(
        "/regulations/summary",
        json={
            "filename": "summary-proposed.txt",
            "current_filename": "summary-current.txt",
            "app_session_id": "SUMMARY-SUPERSEDE",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert first.status_code == 200

    second = test_client.post(
        "/regulations/summary",
        json={
            "filename": "summary-proposed.txt",
            "current_filename": "summary-current.txt",
            "app_session_id": "SUMMARY-SUPERSEDE",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert second.status_code == 200

    session_id = db.get_session_id_by_app_id("SUMMARY-SUPERSEDE")
    assert session_id is not None
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT answer_state, state_reason
        FROM llm_answers
        WHERE session_id = ? AND prompt_id = 'law_summary'
        ORDER BY answer_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    assert rows == [
        {"answer_state": "invalid", "state_reason": "superseded_by_new_attempt"},
        {"answer_state": "active", "state_reason": "session_updated"},
    ]
