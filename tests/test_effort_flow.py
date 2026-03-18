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
        ),
        session_id=session_id,
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
        ),
        session_id=session_id,
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
              "anzahl_betroffene_gueltig": "100",
              "haeufigkeit_pro_jahr_gueltig": "2",
              "anzahl_betroffene_vorschlag": "120",
              "haeufigkeit_pro_jahr_vorschlag": "2"
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
                  "stundenlohn_satz_a_gueltig": "40",
                  "zeitaufwand_in_min_a_gueltig": "1",
                  "sachaufwand_gueltig": "10",
                  "stundenlohn_satz_a_vorschlag": "45",
                  "zeitaufwand_in_min_a_vorschlag": "1.5",
                  "sachaufwand_vorschlag": "12"
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
    assert case_groups[0]["addressees_current"] == 100
    assert case_groups[0]["annual_frequency_current"] == 2
    assert case_groups[0]["addressees_proposed"] == 120
    assert case_groups[0]["annual_frequency_proposed"] == 2

    steps = db.list_process_steps_for_session(session_id)
    assert steps[0]["hourly_rate_a_current"] == 40
    assert steps[0]["time_required_in_min_a_current"] == 1
    assert steps[0]["expenses_current"] == 10
    assert steps[0]["hourly_rate_a_proposed"] == 45
    assert steps[0]["time_required_in_min_a_proposed"] == 1.5
    assert steps[0]["expenses_proposed"] == 12

    tiles = db.fetch_tiles(session_id=session_id)
    case_tile = next(tile for tile in tiles if tile.id == f"case_group_{case_group_id}")
    step_tile = next(tile for tile in tiles if tile.id == f"step_{step_one}")
    assert case_tile.text == "Beschreibung Fallgruppe"
    assert case_tile.meta_information["addressees_current"] == 100
    assert case_tile.meta_information["annual_frequency_current"] == 2
    assert case_tile.meta_information["cases_current"] == 200
    assert case_tile.meta_information["addressees_proposed"] == 120
    assert case_tile.meta_information["annual_frequency_proposed"] == 2
    assert case_tile.meta_information["cases_proposed"] == 240

    assert step_tile.text == "Beschreibung Schritt 1"
    assert step_tile.meta_information["time_required_current"]["a"] == 1
    assert step_tile.meta_information["time_required_proposed"]["a"] == 1.5
    assert step_tile.meta_information["expenses_current"] == 10
    assert step_tile.meta_information["expenses_proposed"] == 12


def test_calculate_effort_preserves_existing_base_values(test_client, monkeypatch):
    """E-B behavior: existing base values are preserved, missing values are filled."""
    session_id, _ = db.upsert_session("EFFORT-PRESERVE", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_one, _step_two = _seed_steps(session_id, case_group_id)

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_current=100,
        annual_frequency_current=None,
        addressees_proposed=None,
        annual_frequency_proposed=None,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_one,
        hourly_rates_current={"a": 50, "b": None, "c": None, "d": None},
        time_required_current={"a": 5, "b": None, "c": None, "d": None},
        expenses_current=7,
        hourly_rates_proposed={"a": None, "b": None, "c": None, "d": None},
        time_required_proposed={"a": None, "b": None, "c": None, "d": None},
        expenses_proposed=None,
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
              "anzahl_betroffene_current": "200",
              "haeufigkeit_pro_jahr_current": "3",
              "anzahl_betroffene_proposed": "220",
              "haeufigkeit_pro_jahr_proposed": "4"
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
              "taetigkeiten": [
                {{
                  "taetigkeiten_id": "{step_one}",
                  "stundenlohn_satz_a_current": "99",
                  "zeitaufwand_in_min_a_current": "9",
                  "sachaufwand_current": "11",
                  "stundenlohn_satz_a_proposed": "44",
                  "zeitaufwand_in_min_a_proposed": "6",
                  "sachaufwand_proposed": "8"
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
    monkeypatch.setattr(effort_router.db, "has_effort_metrics", lambda _sid: False)

    response = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-PRESERVE",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200

    case_group = db.list_case_groups_for_session(session_id)[0]
    assert case_group["addressees_current"] == 100  # preserved existing base value
    assert case_group["annual_frequency_current"] == 3  # filled missing base value
    assert case_group["addressees_proposed"] == 220  # filled missing base value
    assert case_group["annual_frequency_proposed"] == 4  # filled missing base value

    step = db.list_process_steps_for_session(session_id)[0]
    assert step["hourly_rate_a_current"] == 50  # preserved existing base value
    assert step["time_required_in_min_a_current"] == 5  # preserved existing base value
    assert step["expenses_current"] == 7  # preserved existing base value
    assert step["hourly_rate_a_proposed"] == 44  # filled missing base value
    assert step["time_required_in_min_a_proposed"] == 6  # filled missing base value
    assert step["expenses_proposed"] == 8  # filled missing base value


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
        ),
        session_id=session_id,
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
        ),
        session_id=session_id,
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
              "anzahl_betroffene_vorschlag": "120",
              "haeufigkeit_pro_jahr_vorschlag": "2"
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
                  "stundenlohn_satz_a_vorschlag": "45",
                  "zeitaufwand_in_min_a_vorschlag": "1.5",
                  "sachaufwand_vorschlag": "12"
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


def test_calculate_effort_rejects_legacy_keys(test_client, monkeypatch):
    """Rejects unsuffixed legacy keys in effort payloads."""
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
    assert resp.status_code == 422
    assert resp.json()["detail"] == "No case group metrics parsed"


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


def test_calculate_effort_logs_parse_fallback_for_alias_keys(test_client, monkeypatch):
    session_id, _ = db.upsert_session("EFFORT-FALLBACK-LOG", "test-model")
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
              "anzahl_betroffene_gueltig": "10",
              "haeufigkeit_pro_jahr_gueltig": "3",
              "anzahl_betroffene_vorschlag": "12",
              "haeufigkeit_pro_jahr_vorschlag": "4"
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
                  "stundenlohn_satz_a_gueltig": "20",
                  "zeitaufwand_in_min_a_gueltig": "15",
                  "sachaufwand_gueltig": "5",
                  "stundenlohn_satz_a_vorschlag": "25",
                  "zeitaufwand_in_min_a_vorschlag": "10",
                  "sachaufwand_vorschlag": "6"
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

    fallback_kinds: list[str] = []

    def fake_mark_llm_parse_fallback(*, fallback_kind, **_kwargs):
        fallback_kinds.append(str(fallback_kind))

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm)
    monkeypatch.setattr(
        effort_router,
        "mark_llm_parse_fallback",
        fake_mark_llm_parse_fallback,
    )

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-FALLBACK-LOG",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 200
    assert "cases_legacy_key_alias" in fallback_kinds
    assert "effort_legacy_key_alias" in fallback_kinds


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
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "1"
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
                  "stundenlohn_satz_a_vorschlag": "10",
                  "zeitaufwand_in_min_a_vorschlag": "1",
                  "sachaufwand_vorschlag": "1"
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
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "1"
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
                  "stundenlohn_satz_a_vorschlag": "10",
                  "zeitaufwand_in_min_a_vorschlag": "1",
                  "sachaufwand_vorschlag": "1"
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


def test_calculate_effort_partial_query_failure_keeps_audit_rows(
    test_client, monkeypatch
):
    session_id, _ = db.upsert_session("EFFORT-PARTIAL-FAIL", "test-model")
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
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "1"
            }}
          ]
        }}
      ]
    }}
    """

    async def fake_query_llm(prompt, *_args, **_kwargs):
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            return cases_response
        raise RuntimeError("effort query failed upstream")

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-PARTIAL-FAIL",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert resp.status_code == 502
    assert "EFFORT_CALCULATION query failed" in resp.json()["detail"]

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT prompt_id, answer_state, state_reason
        FROM llm_answers
        WHERE session_id = ?
        ORDER BY prompt_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    by_prompt = {row["prompt_id"]: row for row in rows}
    assert by_prompt["cases_calculation"]["answer_state"] == "pending"
    assert by_prompt["cases_calculation"]["state_reason"] == "waiting_for_paired_retry"
    assert by_prompt["effort_calculation"]["answer_state"] == "invalid"
    assert by_prompt["effort_calculation"]["state_reason"] == "query_failed"


def test_calculate_effort_reuses_pending_pair_answer_on_retry(test_client, monkeypatch):
    session_id, _ = db.upsert_session("EFFORT-RETRY-REUSE", "test-model")
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
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "1"
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
                  "stundenlohn_satz_a_vorschlag": "10",
                  "zeitaufwand_in_min_a_vorschlag": "6",
                  "sachaufwand_vorschlag": "2"
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    calls = {"cases": 0, "effort": 0}

    async def fake_query_llm_first(prompt, *_args, **_kwargs):
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            calls["cases"] += 1
            return cases_response
        calls["effort"] += 1
        raise RuntimeError("effort query failed upstream")

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm_first)

    first = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-RETRY-REUSE",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert first.status_code == 502
    assert calls == {"cases": 1, "effort": 1}

    async def fake_query_llm_second(prompt, *_args, **_kwargs):
        if "Fallzahlen" in prompt or "Fallzahl" in prompt:
            calls["cases"] += 1
            return cases_response
        calls["effort"] += 1
        return effort_response

    monkeypatch.setattr(effort_router, "query_llm", fake_query_llm_second)

    second = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": "EFFORT-RETRY-REUSE",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert second.status_code == 200
    assert second.json()["case_groups_updated"] == 1
    assert second.json()["steps_updated"] == 1
    # CASES_CALCULATION was reused from pending, only effort query was re-run.
    assert calls == {"cases": 1, "effort": 2}
