from backend.core import db
from backend.core.models import Tile
from backend.routers import processes as processes_router


def test_compile_processes_success(test_client, monkeypatch):
    """Creates processes and links them to regulations when LLM matches DB data."""
    session_id, _ = db.upsert_session("PROC-OK", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")
    reg_two = db.insert_regulation(session_id, "Section 2", "Beschreibung B")
    db.upsert_tile(Tile(id=f"regulation_{reg_one}", title="Regelung 1"), session_id=session_id)
    db.upsert_tile(Tile(id=f"regulation_{reg_two}", title="Regelung 2"), session_id=session_id)

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess A",
          "vorgaben": [
            {{"vorgaben_id": "{reg_one}", "normzitat": "Section 1", "beschreibung": "Beschreibung A"}}
          ]
        }},
        {{
          "prozess_bezeichnung": "Prozess B",
          "prozess_beschreibung": "Beschreibung Prozess B",
          "vorgaben": [
            {{"vorgaben_id": "{reg_two}", "normzitat": "Section 2", "beschreibung": "Beschreibung B"}}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(processes_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={"app_session_id": "PROC-OK", "model": "test-model", "provider": "deepinfra"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload["prozesse"]) == 2

    processes = db.list_processes_for_session(session_id)
    assert len(processes) == 2
    regulations = db.list_regulations_for_session(session_id)
    assert all(row["process_id"] is not None for row in regulations)

    tiles = db.fetch_tiles(session_id=session_id)
    process_tiles = [tile for tile in tiles if tile.id.startswith("process_")]
    assert len(process_tiles) == 2
    links = {tuple(tile.link_from_tile) for tile in process_tiles}
    assert links == {(f"regulation_{reg_one}",), (f"regulation_{reg_two}",)}


def test_compile_processes_rejects_mismatched_text(test_client, monkeypatch):
    """Rejects LLM output if normzitat/beschreibung doesn't match the DB record."""
    session_id, _ = db.upsert_session("PROC-MISMATCH", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess A",
          "vorgaben": [
            {{"vorgaben_id": "{reg_one}", "normzitat": "Section 1", "beschreibung": "Andere Beschreibung"}}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(processes_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-MISMATCH",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 422
    assert "text mismatch" in resp.json()["detail"]
    assert db.list_processes_for_session(session_id) == []


def test_compile_processes_rejects_duplicate_vorgaben(test_client, monkeypatch):
    """Rejects LLM output when a vorgabe is linked to multiple processes."""
    session_id, _ = db.upsert_session("PROC-DUP", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess A",
          "vorgaben": [
            {{"vorgaben_id": "{reg_one}", "normzitat": "Section 1", "beschreibung": "Beschreibung A"}}
          ]
        }},
        {{
          "prozess_bezeichnung": "Prozess B",
          "prozess_beschreibung": "Beschreibung Prozess B",
          "vorgaben": [
            {{"vorgaben_id": "{reg_one}", "normzitat": "Section 1", "beschreibung": "Beschreibung A"}}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(processes_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={"app_session_id": "PROC-DUP", "model": "test-model", "provider": "deepinfra"},
    )
    assert resp.status_code == 422
    assert "multiple processes" in resp.json()["detail"]
    assert db.list_processes_for_session(session_id) == []


def test_compile_processes_rejects_already_linked_regulation(test_client, monkeypatch):
    """Rejects LLM output when regulations already have a process_id set."""
    session_a, _ = db.upsert_session("PROC-LINKED-A", "test-model")
    session_b, _ = db.upsert_session("PROC-LINKED-B", "test-model")
    existing_process_id = db.insert_process(
        session_b, "Bestehender Prozess", "Bereits verknuepft"
    )
    reg_one = db.insert_regulation(
        session_a, "Section 1", "Beschreibung A", process_id=existing_process_id
    )

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess A",
          "vorgaben": [
            {{"vorgaben_id": "{reg_one}", "normzitat": "Section 1", "beschreibung": "Beschreibung A"}}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(processes_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-LINKED-A",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 409
    assert "already linked" in resp.json()["detail"]
    assert db.list_processes_for_session(session_a) == []


def test_compile_processes_returns_existing(test_client, monkeypatch):
    """Returns existing processes without calling the LLM."""
    session_id, _ = db.upsert_session("PROC-EXISTING", "test-model")
    process_id = db.insert_process(session_id, "Vorhanden", "Schon da")

    async def fail_query_llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called when processes exist")

    monkeypatch.setattr(processes_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-EXISTING",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "existing"
    assert payload["prozesse"] == [
        {
            "process_id": process_id,
            "prozess_bezeichnung": "Vorhanden",
            "prozess_beschreibung": "Schon da",
        }
    ]


def test_compile_processes_requires_regulations(test_client):
    """Returns an error if no regulations exist for the session."""
    db.upsert_session("PROC-NO-REGS", "test-model")

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-NO-REGS",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No regulations for session"
