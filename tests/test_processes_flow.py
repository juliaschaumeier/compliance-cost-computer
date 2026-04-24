import json

import pytest

from backend.core import db
from backend.core.llm_service import LlmQueryError, LlmResult
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


def test_compile_processes_accepts_mismatched_text_when_id_matches(
    test_client, monkeypatch
):
    """Links regulations by vorgaben_id even if text differs."""
    session_id, _ = db.upsert_session("PROC-MISMATCH", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")
    db.upsert_tile(Tile(id=f"regulation_{reg_one}", title="Regelung 1"), session_id=session_id)

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
    assert resp.status_code == 200
    processes = db.list_processes_for_session(session_id)
    assert len(processes) == 1
    regulations = db.list_regulations_for_session(session_id)
    assert regulations[0]["process_id"] == processes[0]["process_id"]


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
            "aenderungsstatus": "geaendert",
        }
    ]


def test_compile_processes_allows_missing_regulation_tiles(test_client, monkeypatch):
    """Creates processes even when regulations were preseeded without graph tiles."""
    session_id, _ = db.upsert_session("PROC-NO-REG-TILE", "test-model")
    reg_one = db.insert_regulation(
        session_id,
        "§ B",
        "Beschreibung Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
    )

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess Wirtschaft",
          "prozess_beschreibung": "Beschreibung Prozess Wirtschaft",
          "vorgaben": [
            {{"vorgaben_id": "{reg_one}", "normzitat": "§ B", "beschreibung": "Beschreibung Wirtschaft"}}
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
            "app_session_id": "PROC-NO-REG-TILE",
            "model": "test-model",
            "provider": "deepinfra",
            "norm_addressee": "business",
        },
    )
    assert resp.status_code == 200

    processes = db.list_processes_for_session_and_addressee(session_id, "business")
    assert len(processes) == 1

    process_tiles = [
        tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee="business")
        if tile.id.startswith("process_")
    ]
    assert len(process_tiles) == 1
    assert process_tiles[0].link_from_tile == []


def test_compile_processes_normalizes_change_status_variants(test_client, monkeypatch):
    session_id, _ = db.upsert_session("PROC-STATUS-VARIANTS", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")
    reg_two = db.insert_regulation(session_id, "Section 2", "Beschreibung B")
    reg_three = db.insert_regulation(session_id, "Section 3", "Beschreibung C")
    db.upsert_tile(Tile(id=f"regulation_{reg_one}", title="Regelung 1"), session_id=session_id)
    db.upsert_tile(Tile(id=f"regulation_{reg_two}", title="Regelung 2"), session_id=session_id)
    db.upsert_tile(Tile(id=f"regulation_{reg_three}", title="Regelung 3"), session_id=session_id)

    response_text = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung A",
          "change_status": "new",
          "vorgaben": [
            {{"vorgaben_id": "{reg_one}", "normzitat": "Section 1", "beschreibung": "Beschreibung A"}}
          ]
        }},
        {{
          "prozess_bezeichnung": "Prozess B",
          "prozess_beschreibung": "Beschreibung B",
          "status_change": "updated",
          "vorgaben": [
            {{"vorgaben_id": "{reg_two}", "normzitat": "Section 2", "beschreibung": "Beschreibung B"}}
          ]
        }},
        {{
          "prozess_bezeichnung": "Prozess C",
          "prozess_beschreibung": "Beschreibung C",
          "status": "deleted",
          "vorgaben": [
            {{"vorgaben_id": "{reg_three}", "normzitat": "Section 3", "beschreibung": "Beschreibung C"}}
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
            "app_session_id": "PROC-STATUS-VARIANTS",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert [row["aenderungsstatus"] for row in payload["prozesse"]] == [
        "eingefuehrt",
        "geaendert",
        "abgeschafft",
    ]

    rows = db.list_processes_for_session(session_id)
    assert [row["change_status"] for row in rows] == [
        "eingefuehrt",
        "geaendert",
        "abgeschafft",
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


def test_compile_processes_skips_administration_when_only_other_addressee_has_regulations(
    test_client,
):
    session_id, _ = db.upsert_session("PROC-ADMIN-SKIP", "test-model")
    db.insert_regulation(
        session_id,
        "§ 1",
        "Nur Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
    )

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-ADMIN-SKIP",
            "model": "test-model",
            "provider": "deepinfra",
            "norm_addressee": "administration",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"
    assert resp.json()["norm_addressee"] == "administration"


def test_compile_processes_stores_query_failed_attempt(test_client, monkeypatch):
    session_id, _ = db.upsert_session("PROC-QUERY-FAILED", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")
    db.upsert_tile(
        Tile(id=f"regulation_{reg_one}", title="Regelung 1"),
        session_id=session_id,
    )

    async def fail_query_llm(*_args, **_kwargs):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(processes_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-QUERY-FAILED",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 502
    assert "LLM query failed" in resp.json()["detail"]

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT prompt_id, answer_state, state_reason, metadata
        FROM llm_answers
        WHERE session_id = ?
        """,
        (session_id,),
    )
    row = dict(cur.fetchone())
    conn.close()
    assert row["prompt_id"] == "process_compilation"
    assert row["answer_state"] == "invalid"
    assert row["state_reason"] == "query_failed"
    metadata = json.loads(row["metadata"])
    assert "provider exploded" in metadata.get("error", "")


def test_compile_processes_invalidates_on_parse_failure(test_client, monkeypatch):
    session_id, _ = db.upsert_session("PROC-PARSE-FAILED", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")
    db.upsert_tile(
        Tile(id=f"regulation_{reg_one}", title="Regelung 1"),
        session_id=session_id,
    )

    async def fake_query_llm(*_args, **_kwargs):
        return '{"prozesse": []}'

    monkeypatch.setattr(processes_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-PARSE-FAILED",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "No processes parsed"

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT prompt_id, answer_state, state_reason
        FROM llm_answers
        WHERE session_id = ?
        ORDER BY answer_id
        """,
        (session_id,),
    )
    row = dict(cur.fetchone())
    conn.close()
    assert row["prompt_id"] == "process_compilation"
    assert row["answer_state"] == "invalid"
    assert row["state_reason"].startswith("session_update_failed:")


def test_compile_processes_maps_provider_timeout_to_504(test_client, monkeypatch):
    session_id, _ = db.upsert_session("PROC-TIMEOUT", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")
    db.upsert_tile(
        Tile(id=f"regulation_{reg_one}", title="Regelung 1"),
        session_id=session_id,
    )

    async def fail_query_llm(*_args, **_kwargs):
        raise LlmQueryError(
            provider="openai",
            model="gpt-5.2",
            reason="provider_timeout",
            message="upstream timeout",
        )

    monkeypatch.setattr(processes_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-TIMEOUT",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 504
    assert "provider_timeout" in resp.json()["detail"]


def test_compile_processes_persists_usage_and_raw_response(test_client, monkeypatch):
    session_id, _ = db.upsert_session("PROC-USAGE", "test-model")
    reg_one = db.insert_regulation(session_id, "Section 1", "Beschreibung A")
    db.upsert_tile(
        Tile(id=f"regulation_{reg_one}", title="Regelung 1"),
        session_id=session_id,
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
        return LlmResult(
            text=response_text,
            input_tokens=111,
            output_tokens=210,
            hidden_thinking_tokens=45,
            estimated_cost_usd=0.0042,
            provider_response_json={"usage": {"total_tokens": 321}},
        )

    monkeypatch.setattr(processes_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": "PROC-USAGE",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT input_tokens, output_tokens, hidden_thinking_tokens, estimated_cost_usd, provider_response_json
        FROM llm_answers
        WHERE session_id = ?
        ORDER BY answer_id DESC
        LIMIT 1
        """,
        (session_id,),
    )
    row = dict(cur.fetchone())
    conn.close()
    assert row["input_tokens"] == 111
    assert row["output_tokens"] == 210
    assert row["hidden_thinking_tokens"] == 45
    assert row["estimated_cost_usd"] == pytest.approx(0.0042)
    raw = json.loads(row["provider_response_json"])
    assert raw["usage"]["total_tokens"] == 321
