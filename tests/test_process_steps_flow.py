from backend.core import db
from backend.core.llm_service import LlmQueryError
from backend.core.models import Tile
from backend.routers import process_steps as process_steps_router


def _seed_steps(app_session_id: str) -> tuple[int, int, int, int]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt 1", "Beschreibung Schritt 1"
    )
    return session_id, process_id, case_group_id, step_id


def test_analyze_process_steps_returns_existing(test_client, monkeypatch):
    """Returns existing steps without calling the LLM."""
    _session_id, _process_id, _case_group_id, step_id = _seed_steps("STEPS-EXISTING")

    async def fail_query_llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called when steps already exist")

    monkeypatch.setattr(process_steps_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-EXISTING",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "existing"
    assert [row["step_id"] for row in payload["steps"]] == [step_id]


def test_analyze_process_steps_requires_case_groups(test_client):
    """Rejects analysis when no case groups exist for the session."""
    db.upsert_session("STEPS-NO-GROUPS", "test-model")

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-NO-GROUPS",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No case groups for session"


def test_analyze_process_steps_parses_change_status_and_sets_tile_meta(
    test_client, monkeypatch
):
    session_id, process_id, case_group_id, _step_id = _seed_steps("STEPS-STATUS")
    db.delete_process_steps_for_session(session_id)
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
            },
            column=3,
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
          "aenderungsstatus": "geaendert",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "aenderungsstatus": "geaendert",
              "taetigkeiten": [
                {{
                  "taetigkeit": "Neuer Schritt",
                  "beschreibung": "Beschreibung",
                  "aenderungsstatus": "abgeschafft"
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(process_steps_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-STATUS",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["steps"][0]["aenderungsstatus"] == "abgeschafft"
    steps = db.list_process_steps_for_session(session_id)
    assert steps[0]["change_status"] == "abgeschafft"

    tiles = db.fetch_tiles(session_id=session_id)
    step_tile = next(tile for tile in tiles if tile.id.startswith("step_"))
    assert step_tile.meta_information.get("change_status") == "abgeschafft"


def test_analyze_process_steps_persists_regulation_links(test_client, monkeypatch):
    session_id, process_id, case_group_id, _step_id = _seed_steps("STEPS-REG-LINKS")
    db.delete_process_steps_for_session(session_id)
    regulation_id = db.insert_regulation(
        session_id,
        "§ 10",
        "Informationspflicht",
    )
    assert db.update_regulation_process(regulation_id, process_id, "administration")
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
            },
            column=3,
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
          "vorgaben": [
            {{
              "vorgaben_id": "{regulation_id}",
              "normzitat": "§ 10",
              "beschreibung": "Informationspflicht"
            }}
          ],
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "taetigkeiten": [
                {{
                  "taetigkeit": "Unterlagen pruefen",
                  "beschreibung": "Beschreibung",
                  "aenderungsstatus": "geaendert",
                  "vorgaben_ids": ["{regulation_id}"]
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(process_steps_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-REG-LINKS",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    step_id = resp.json()["steps"][0]["step_id"]
    assert db.get_process_step_regulation_ids_by_step(session_id, "administration") == {
        step_id: [regulation_id]
    }


def test_analyze_process_steps_normalizes_change_status_variants(test_client, monkeypatch):
    session_id, process_id, case_group_id, _step_id = _seed_steps("STEPS-STATUS-VARIANTS")
    db.delete_process_steps_for_session(session_id)
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
            },
            column=3,
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
          "status": "updated",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "change_status": "updated",
                "taetigkeiten": [
                {{
                  "taetigkeit": "Neuer Schritt A",
                  "beschreibung": "Beschreibung A",
                  "status_change": "new"
                }},
                {{
                  "taetigkeit": "Neuer Schritt B",
                  "beschreibung": "Beschreibung B",
                  "status": "deleted"
                }},
                {{
                  "taetigkeit": "Neuer Schritt C",
                  "beschreibung": "Beschreibung C",
                  "aenderungsstatus": "unveraendert"
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    monkeypatch.setattr(process_steps_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-STATUS-VARIANTS",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert [row["aenderungsstatus"] for row in payload["steps"]] == [
        "eingefuehrt",
        "abgeschafft",
        "unveraendert",
    ]

    rows = db.list_process_steps_for_session(session_id)
    assert [row["change_status"] for row in rows] == [
        "eingefuehrt",
        "abgeschafft",
        "unveraendert",
    ]


def test_analyze_process_steps_maps_connection_error_to_503(test_client, monkeypatch):
    session_id, process_id, case_group_id, _step_id = _seed_steps("STEPS-CONN-ERR")
    db.delete_process_steps_for_session(session_id)
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
            },
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )

    async def fail_query_llm(*_args, **_kwargs):
        raise LlmQueryError(
            provider="deepinfra",
            model="model-x",
            reason="provider_connection_error",
            message="connection dropped",
        )

    monkeypatch.setattr(process_steps_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-CONN-ERR",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 503
    assert "provider_connection_error" in resp.json()["detail"]


def test_analyze_process_steps_logs_flattened_fallback(test_client, monkeypatch):
    session_id, process_id, case_group_id, _step_id = _seed_steps("STEPS-FALLBACK-LOG")
    db.delete_process_steps_for_session(session_id)
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
            },
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )

    response_text = f"""
    {{
      "fallgruppen": [
        {{
          "fallgruppen_id": "{case_group_id}",
          "taetigkeiten": [
            {{
              "taetigkeit": "Fallback Schritt",
              "beschreibung": "Aus fallback parser"
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(*_args, **_kwargs):
        return response_text

    fallback_kinds: list[str] = []

    def fake_mark_llm_parse_fallback(*, fallback_kind, **_kwargs):
        fallback_kinds.append(str(fallback_kind))

    monkeypatch.setattr(process_steps_router, "query_llm", fake_query_llm)
    monkeypatch.setattr(
        process_steps_router,
        "mark_llm_parse_fallback",
        fake_mark_llm_parse_fallback,
    )

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-FALLBACK-LOG",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    assert "process_steps_flattened_fallgruppen" in fallback_kinds


def test_analyze_process_steps_rejects_invalid_json_payload(test_client, monkeypatch):
    session_id, process_id, case_group_id, _step_id = _seed_steps("STEPS-BAD-JSON")
    db.delete_process_steps_for_session(session_id)
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
            },
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
    )

    async def fake_query_llm(*_args, **_kwargs):
        return "ungueltiger payload"

    monkeypatch.setattr(process_steps_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": "STEPS-BAD-JSON",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == (
        "Invalid process_step_analysis payload: no JSON object found in LLM response"
    )
