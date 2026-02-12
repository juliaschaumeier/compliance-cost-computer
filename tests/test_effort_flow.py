from backend.core import db
from backend.core.models import Tile
from backend.routers import effort as effort_router


def _seed_case_group(session_id: int) -> tuple[int, int]:
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    return process_id, case_group_id


def _seed_steps(session_id: int, case_group_id: int) -> tuple[int, int]:
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
    db.update_process_step_next(step_one, step_two)
    return step_one, step_two


def test_calculate_effort_updates_db_and_tiles(test_client, monkeypatch):
    """Updates case-group metrics and process-step effort values plus tile text."""
    session_id, _ = db.upsert_session("EFFORT-OK", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_one, _step_two = _seed_steps(session_id, case_group_id)

    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={"case_group_id": case_group_id},
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[],
        )
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_one}",
            title="Schritt 1",
            text="Beschreibung Schritt 1",
            meta_information={"step_id": step_one, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[f"case_group_{case_group_id}"],
        )
    )

    cases_response = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "1",
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung Fallgruppe",
              "anzahl_betroffene": "120",
              "haeufigkeit_pro_jahr": "2"
            }}
          ]
        }}
      ]
    }}
    """
    effort_response = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "1",
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung Fallgruppe",
              "taetigkeiten": [
                {{
                  "taetigkeiten_id": "{step_one}",
                  "taetigkeit": "Schritt 1",
                  "beschreibung": "Beschreibung Schritt 1",
                  "stundenlohn_satz_a": "45",
                  "zeitaufwand_in_min_a": "1.5",
                  "sachaufwand": "12",
                  "ausfuehrung_pro_einzelfall": "0"
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    calls = []

    async def fake_query_llm(prompt, *_args, **_kwargs):
        calls.append(prompt)
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            return cases_response
        return effort_response

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-OK",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["case_groups_updated"] == 1
    assert payload["steps_updated"] == 1
    assert len(calls) == 2

    case_groups = db.list_case_groups_for_session(session_id)
    assert case_groups[0]["addressees"] == 120
    assert case_groups[0]["annual_frequency"] == 2

    steps = db.list_process_steps_for_session(session_id)
    assert steps[0]["hourly_rate_a"] == 45
    assert steps[0]["time_required_in_min_a"] == 1.5
    assert steps[0]["expenses"] == 12
    assert steps[0]["execution_per_case"] in (0, False)

    tiles = db.fetch_tiles()
    case_tile = next(tile for tile in tiles if tile.id == f"case_group_{case_group_id}")
    step_tile = next(tile for tile in tiles if tile.id == f"step_{step_one}")
    assert "Betroffene: 120" in case_tile.text
    assert "Häufigkeit: 2" in case_tile.text
    assert "Lohnsatz A: 45" in step_tile.text
    assert "Zeitaufwand A: 1.5" in step_tile.text
    assert "Sachaufwand: 12" in step_tile.text


def test_calculate_effort_returns_existing_without_llm_call(test_client, monkeypatch):
    """Skips the LLM when effort metrics already exist for the session."""
    session_id, _ = db.upsert_session("EFFORT-EXISTING", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_one, _step_two = _seed_steps(session_id, case_group_id)

    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title="Fallgruppe A",
            text="Beschreibung Fallgruppe",
            meta_information={"case_group_id": case_group_id},
            column=3,
            row=0,
            deletable=True,
            link_from_tile=[],
        )
    )
    db.upsert_tile(
        Tile(
            id=f"step_{step_one}",
            title="Schritt 1",
            text="Beschreibung Schritt 1",
            meta_information={"step_id": step_one, "case_group_id": case_group_id},
            column=4,
            row=0,
            deletable=True,
            link_from_tile=[f"case_group_{case_group_id}"],
        )
    )

    cases_response = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "1",
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung Fallgruppe",
              "anzahl_betroffene": "120",
              "haeufigkeit_pro_jahr": "2"
            }}
          ]
        }}
      ]
    }}
    """
    effort_response = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "1",
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung Prozess",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "fallgruppe_bezeichnung": "Fallgruppe A",
              "fallgruppe_beschreibung": "Beschreibung Fallgruppe",
              "taetigkeiten": [
                {{
                  "taetigkeiten_id": "{step_one}",
                  "taetigkeit": "Schritt 1",
                  "beschreibung": "Beschreibung Schritt 1",
                  "stundenlohn_satz_a": "45",
                  "zeitaufwand_in_min_a": "1.5",
                  "sachaufwand": "12"
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(prompt, *_args, **_kwargs):
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            return cases_response
        return effort_response

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm)

    first = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-EXISTING",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert first.status_code == 200

    async def fail_query_llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called on existing metrics")

    monkeypatch.setattr(effort_router, "query_llm", fail_query_llm)

    second = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-EXISTING",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "existing"
    assert payload["case_groups_updated"] == 0
    assert payload["steps_updated"] == 0


def test_calculate_effort_parses_legacy_keys(test_client, monkeypatch):
    """Accepts legacy lohnsatz/zeitaufwand keys and stores metrics."""
    session_id, _ = db.upsert_session("EFFORT-LEGACY", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_one, _step_two = _seed_steps(session_id, case_group_id)

    cases_response = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "1",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene": "10",
              "haeufigkeit_pro_jahr": "3"
            }}
          ]
        }}
      ]
    }}
    """
    effort_response = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "1",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "taetigkeiten": [
                {{
                  "taetigkeiten_id": "{step_one}",
                  "lohnsatz_a": "22",
                  "zeitaufwand_a": "15",
                  "sachaufwand": "7"
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(prompt, *_args, **_kwargs):
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            return cases_response
        return effort_response

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-LEGACY",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200

    steps = db.list_process_steps_for_session(session_id)
    assert steps[0]["hourly_rate_a"] == 22
    assert steps[0]["time_required_in_min_a"] == 15
    assert steps[0]["expenses"] == 7


def test_calculate_effort_requires_case_groups(test_client):
    """Requires case groups before calculating effort metrics."""
    db.upsert_session("EFFORT-NO-GROUPS", "test-model")

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-NO-GROUPS",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No case groups for session"


def test_calculate_effort_requires_steps(test_client):
    """Requires process steps before calculating effort metrics."""
    session_id, _ = db.upsert_session("EFFORT-NO-STEPS", "test-model")
    _process_id, _case_group_id = _seed_case_group(session_id)

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-NO-STEPS",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No process steps for session"


def test_calculate_effort_rejects_unknown_case_group(test_client, monkeypatch):
    """Rejects cases output when fallgruppen_id doesn't exist in DB."""
    session_id, _ = db.upsert_session("EFFORT-UNKNOWN-GROUP", "test-model")
    _process_id, _case_group_id = _seed_case_group(session_id)
    _step_one, _step_two = _seed_steps(session_id, _case_group_id)

    cases_response = """
    {
      "prozesse": [
        {
          "prozess_id": "1",
          "fallgruppen": [
            {
              "fallgruppen_id": "999",
              "anzahl_betroffene": "10",
              "haeufigkeit_pro_jahr": "1"
            }
          ]
        }
      ]
    }
    """
    effort_response = """
    {
      "prozesse": [
        {
          "prozess_id": "1",
          "fallgruppen": [
            {
              "fallgruppen_id": "1",
              "taetigkeiten": [
                {
                  "taetigkeiten_id": "1",
                  "stundenlohn_satz_a": "10",
                  "zeitaufwand_in_min_a": "1",
                  "sachaufwand": "1"
                }
              ]
            }
          ]
        }
      ]
    }
    """

    async def fake_query_llm(prompt, *_args, **_kwargs):
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            return cases_response
        return effort_response

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-UNKNOWN-GROUP",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 422
    assert "Unknown fallgruppen_id values" in resp.json()["detail"]


def test_calculate_effort_rejects_unknown_step(test_client, monkeypatch):
    """Rejects effort output when taetigkeiten_id doesn't exist in DB."""
    session_id, _ = db.upsert_session("EFFORT-UNKNOWN-STEP", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    _step_one, _step_two = _seed_steps(session_id, case_group_id)

    cases_response = f"""
    {{
      "prozesse": [
        {{
          "prozess_id": "1",
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene": "10",
              "haeufigkeit_pro_jahr": "1"
            }}
          ]
        }}
      ]
    }}
    """
    effort_response = """
    {
      "prozesse": [
        {
          "prozess_id": "1",
          "fallgruppen": [
            {
              "fallgruppen_id": "1",
              "taetigkeiten": [
                {
                  "taetigkeiten_id": "999",
                  "stundenlohn_satz_a": "10",
                  "zeitaufwand_in_min_a": "1",
                  "sachaufwand": "1"
                }
              ]
            }
          ]
        }
      ]
    }
    """

    async def fake_query_llm(prompt, *_args, **_kwargs):
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            return cases_response
        return effort_response

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-UNKNOWN-STEP",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 422
    assert "Unknown taetigkeiten_id values" in resp.json()["detail"]
