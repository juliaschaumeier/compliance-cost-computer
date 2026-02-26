from backend.core import db
from backend.core.models import Tile
from backend.routers import case_groups as case_groups_router


def test_develop_case_groups_success(test_client, monkeypatch):
    """Creates case groups from LLM output and links them to process tiles."""
    session_id, _ = db.upsert_session("CASE-OK", "test-model")
    process_one = db.insert_process(session_id, "Process 1", "Desc 1")
    process_two = db.insert_process(session_id, "Process 2", "Desc 2")
    db.insert_regulation(session_id, "Section 1", "Reg 1", process_id=process_one)
    db.insert_regulation(session_id, "Section 2", "Reg 2", process_id=process_two)
    db.upsert_tile(
        Tile(
            id=f"process_{process_one}",
            title="Process 1",
            text="",
            meta_information={"process_id": process_one},
            column=0,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )
    db.upsert_tile(
        Tile(
            id=f"process_{process_two}",
            title="Process 2",
            text="",
            meta_information={"process_id": process_two},
            column=0,
            row=1,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "{process_one}",
          "prozess_bezeichnung": "Process 1",
          "prozess_beschreibung": "Desc 1",
          "fallgruppen": [
            {{
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung A"
            }}
          ]
        }},
        {{
          "prozess_id": "{process_two}",
          "prozess_bezeichnung": "Process 2",
          "prozess_beschreibung": "Desc 2",
          "fallgruppen": [
            {{
              "fallgruppe_bezeichnung": "Fallgruppe B",
              "fallgruppe_beschreibung": "Beschreibung B"
            }},
            {{
              "fallgruppe_bezeichnung": "Fallgruppe C",
              "fallgruppe_beschreibung": "Beschreibung C"
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(case_groups_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/case-groups/develop",
        json={
            "app_session_id": "CASE-OK",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload["prozesse"]) == 2

    case_groups = db.list_case_groups_for_session(session_id)
    assert len(case_groups) == 3

    tiles = db.fetch_tiles(session_id=session_id)
    case_tiles = [tile for tile in tiles if tile.id.startswith("case_group_")]
    assert len(case_tiles) == 3
    assert all(tile.link_from_tile for tile in case_tiles)


def test_develop_case_groups_returns_existing(test_client, monkeypatch):
    """Returns existing case groups without calling the LLM."""
    session_id, _ = db.upsert_session("CASE-EXISTING", "test-model")
    process_id = db.insert_process(session_id, "Process 1", "Desc 1")
    db.insert_case_group(session_id, process_id, "Fallgruppe A", "Beschreibung A")

    async def fail_query_llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called when case groups exist")

    monkeypatch.setattr(case_groups_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/case-groups/develop",
        json={
            "app_session_id": "CASE-EXISTING",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "existing"
    assert payload["prozesse"][0]["fallgruppen"][0]["fallgruppe_bezeichnung"] == "Fallgruppe A"


def test_develop_case_groups_requires_processes(test_client):
    """Returns an error if no processes exist for the session."""
    db.upsert_session("CASE-NO-PROC", "test-model")

    resp = test_client.post(
        "/case-groups/develop",
        json={
            "app_session_id": "CASE-NO-PROC",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No processes for session"


def test_develop_case_groups_rejects_unknown_process_id(test_client, monkeypatch):
    """Rejects LLM output that references missing process ids."""
    session_id, _ = db.upsert_session("CASE-UNKNOWN-PROC", "test-model")
    db.insert_process(session_id, "Process 1", "Desc 1")

    response_text = """
    {
      "prozesse": [
        {
          "prozess_id": "999",
          "prozess_bezeichnung": "Ghost",
          "prozess_beschreibung": "Desc",
          "fallgruppen": [
            {
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung A"
            }
          ]
        }
      ]
    }
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(case_groups_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/case-groups/develop",
        json={
            "app_session_id": "CASE-UNKNOWN-PROC",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 422
    assert "Unknown process_id values" in resp.json()["detail"]


def test_develop_case_groups_rejects_missing_process_tile(test_client, monkeypatch):
    """Rejects when process tiles are missing for the referenced process ids."""
    session_id, _ = db.upsert_session("CASE-NO-TILE", "test-model")
    process_id = db.insert_process(session_id, "Process 1", "Desc 1")
    db.insert_regulation(session_id, "Section 1", "Reg 1", process_id=process_id)

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "{process_id}",
          "prozess_bezeichnung": "Process 1",
          "prozess_beschreibung": "Desc 1",
          "fallgruppen": [
            {{
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung A"
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(case_groups_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/case-groups/develop",
        json={
            "app_session_id": "CASE-NO-TILE",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 409
    assert "Process tile missing" in resp.json()["detail"]


def test_develop_case_groups_normalizes_change_status_variants(test_client, monkeypatch):
    session_id, _ = db.upsert_session("CASE-STATUS-VARIANTS", "test-model")
    process_id = db.insert_process(session_id, "Process 1", "Desc 1")
    db.insert_regulation(session_id, "Section 1", "Reg 1", process_id=process_id)
    db.upsert_tile(
        Tile(
            id=f"process_{process_id}",
            title="Process 1",
            text="",
            meta_information={"process_id": process_id},
            column=0,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "{process_id}",
          "fallgruppen": [
            {{
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung A",
              "change_status": "new"
            }},
            {{
              "fallgruppe_bezeichnung": "Fallgruppe B",
              "fallgruppe_beschreibung": "Beschreibung B",
              "status_change": "updated"
            }},
            {{
              "fallgruppe_bezeichnung": "Fallgruppe C",
              "fallgruppe_beschreibung": "Beschreibung C",
              "status": "deleted"
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(case_groups_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/case-groups/develop",
        json={
            "app_session_id": "CASE-STATUS-VARIANTS",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert [row["aenderungsstatus"] for row in payload["prozesse"][0]["fallgruppen"]] == [
        "eingefuehrt",
        "geaendert",
        "abgeschafft",
    ]

    rows = db.list_case_groups_for_session(session_id)
    assert [row["change_status"] for row in rows] == [
        "eingefuehrt",
        "geaendert",
        "abgeschafft",
    ]
