from backend.core import db
from backend.core.prompts import PromptId, render_prompt
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


def test_identify_requires_session_law_selection(test_client, monkeypatch):
    db.upsert_session("NO-LAW-IDS", "test-model")

    async def fail_query_llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called when laws are missing")

    monkeypatch.setattr(regulations_router, "query_llm", fail_query_llm)

    resp = test_client.post(
        "/regulations/identify",
        json={
            "app_session_id": "NO-LAW-IDS",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Law files not selected for session. Run summary first."


def test_identify_regulations_rejects_invalid_json_payload(test_client, monkeypatch):
    db.insert_law("invalid-current.txt", "aktuelles gesetz")
    db.insert_law("invalid-proposed.txt", "neuer entwurf")

    responses = iter(
        [
            '{"title": "Kurz", "blurb": "Ein Satz."}',
            "kein json vorhanden",
        ]
    )

    async def fake_query_llm(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(regulations_router, "query_llm", fake_query_llm)

    summary_resp = test_client.post(
        "/regulations/summary",
        json={
            "filename": "invalid-proposed.txt",
            "current_filename": "invalid-current.txt",
            "app_session_id": "REG-INVALID-JSON",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert summary_resp.status_code == 200

    resp = test_client.post(
        "/regulations/identify",
        json={
            "app_session_id": "REG-INVALID-JSON",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == (
        "Invalid regulations_identification payload: no JSON object found in LLM response"
    )


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


def test_summary_separates_blurb_and_summary_storage_and_display(test_client, monkeypatch):
    db.insert_law("sep-current.txt", "aktuelles gesetz")
    db.insert_law("sep-proposed.txt", "neuer entwurf")

    async def fake_query_llm(*_args, **_kwargs):
        return (
            '{"title": "Kurz", "blurb": "Kurzer Satz.", '
            '"summary": "Ausfuehrliche Zusammenfassung fuer Prompt-Kontext."}'
        )

    monkeypatch.setattr(regulations_router, "query_llm", fake_query_llm)

    resp = test_client.post(
        "/regulations/summary",
        json={
            "filename": "sep-proposed.txt",
            "current_filename": "sep-current.txt",
            "app_session_id": "SUMMARY-SEPARATION",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["blurb"] == "Kurzer Satz."
    assert payload["summary"] == "Ausfuehrliche Zusammenfassung fuer Prompt-Kontext."

    session = db.get_session_by_app_id("SUMMARY-SEPARATION")
    assert session is not None
    assert session["law_diff_blurb"] == "Kurzer Satz."
    assert session["law_diff_summary"] == "Ausfuehrliche Zusammenfassung fuer Prompt-Kontext."

    session_id = int(session["session_id"])
    law_tile = next(tile for tile in db.fetch_tiles(session_id=session_id) if tile.id == "law_tile")
    assert law_tile.text == "Kurzer Satz."

    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        session_id=session_id,
        vorgaben_json="[]",
    )
    assert "Ausfuehrliche Zusammenfassung fuer Prompt-Kontext." in prompt
    assert "Kurzer Satz." not in prompt


def test_identify_prompt_contains_session_summary_and_law_texts(test_client, monkeypatch):
    current_text = "CURRENT_TEXT_UNIQUE_4711"
    proposed_text = "PROPOSED_TEXT_UNIQUE_815"
    summary_text = "SUMMARY_CONTEXT_UNIQUE_996"
    db.insert_law("prompt-current.txt", current_text)
    db.insert_law("prompt-proposed.txt", proposed_text)

    prompts: list[str] = []

    async def fake_query_llm(prompt: str, **_kwargs):
        prompts.append(prompt)
        if len(prompts) == 1:
            return (
                '{"title": "Kurz", "blurb": "Ein Satz.", "summary": "'
                + summary_text
                + '"}'
            )
        return (
            '{"vorgaben": ['
            '{"normzitat": "§ 1", "beschreibung": "Vorgabe A"}'
            "]}"
        )

    monkeypatch.setattr(regulations_router, "query_llm", fake_query_llm)

    summary_resp = test_client.post(
        "/regulations/summary",
        json={
            "filename": "prompt-proposed.txt",
            "current_filename": "prompt-current.txt",
            "app_session_id": "PROMPT-CONTEXT-CHECK",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert summary_resp.status_code == 200

    identify_resp = test_client.post(
        "/regulations/identify",
        json={
            "app_session_id": "PROMPT-CONTEXT-CHECK",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert identify_resp.status_code == 200
    assert len(prompts) == 2

    identify_prompt = prompts[1]
    assert summary_text in identify_prompt
    assert current_text in identify_prompt
    assert proposed_text in identify_prompt


def test_identify_regulations_parses_norm_addressees_and_business_information_flag(
    test_client, monkeypatch
):
    db.insert_law("addr-current.txt", "aktuelles gesetz")
    db.insert_law("addr-proposed.txt", "neuer entwurf")

    responses = iter(
        [
            '{"title": "Kurz", "blurb": "Ein Satz."}',
            """
            {
              "vorgaben": [
                {
                  "normzitat": "§ 20",
                  "beschreibung": "Mischfall",
                  "normadressaten": ["administration", "business"],
                  "ist_informationspflicht_wirtschaft": true
                },
                {
                  "normzitat": "§ 21",
                  "beschreibung": "Einzelwert",
                  "normadressat": "citizens"
                },
                {
                  "normzitat": "§ 22",
                  "beschreibung": "Default Verwaltung"
                }
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
            "filename": "addr-proposed.txt",
            "current_filename": "addr-current.txt",
            "app_session_id": "REG-ADDRESSEES",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert summary_resp.status_code == 200

    resp = test_client.post(
        "/regulations/identify",
        json={
            "app_session_id": "REG-ADDRESSEES",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200

    session_id = db.get_session_id_by_app_id("REG-ADDRESSEES")
    assert session_id is not None
    rows = db.list_regulations_for_session(session_id)
    assert [
        (
            row["legal_citation"],
            row["applies_to_administration"],
            row["applies_to_business"],
            row["applies_to_citizens"],
            row["is_business_information_obligation"],
        )
        for row in rows
        ] == [
            ("§ 20", 1, 1, 0, 1),
            ("§ 21", 0, 0, 1, 0),
            ("§ 22", 1, 0, 0, 0),
        ]

    admin_tiles = {
        tile.meta_information["regulation_id"]: tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee="administration")
        if tile.id.startswith("regulation_")
    }
    business_tiles = {
        tile.meta_information["regulation_id"]: tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee="business")
        if tile.id.startswith("regulation_")
    }
    citizens_tiles = {
        tile.meta_information["regulation_id"]: tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee="citizens")
        if tile.id.startswith("regulation_")
    }

    assert set(admin_tiles) == {rows[0]["regulation_id"], rows[2]["regulation_id"]}
    assert set(business_tiles) == {rows[0]["regulation_id"]}
    assert set(citizens_tiles) == {rows[1]["regulation_id"]}

    first_tile = admin_tiles[rows[0]["regulation_id"]]
    assert first_tile.meta_information["normadressaten"] == ["administration", "business"]


def test_identify_regulations_business_information_flag_adds_business_addressee(
    test_client, monkeypatch
):
    db.insert_law("business-current.txt", "aktuelles gesetz")
    db.insert_law("business-proposed.txt", "neuer entwurf")

    responses = iter(
        [
            '{"title": "Kurz", "blurb": "Ein Satz."}',
            """
            {
              "vorgaben": [
                {
                  "normzitat": "§ 30",
                  "beschreibung": "Informationspflicht",
                  "normadressat": "administration",
                  "informationspflicht_wirtschaft": "ja"
                }
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
            "filename": "business-proposed.txt",
            "current_filename": "business-current.txt",
            "app_session_id": "REG-BUSINESS-FLAG",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert summary_resp.status_code == 200

    resp = test_client.post(
        "/regulations/identify",
        json={
            "app_session_id": "REG-BUSINESS-FLAG",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200

    session_id = db.get_session_id_by_app_id("REG-BUSINESS-FLAG")
    assert session_id is not None
    row = db.list_regulations_for_session(session_id)[0]
    assert row["applies_to_administration"] == 1
    assert row["applies_to_business"] == 1
    assert row["applies_to_citizens"] == 0
    assert row["is_business_information_obligation"] == 1


def test_identify_regulations_persists_spiegelsituation_metadata(test_client, monkeypatch):
    db.insert_law("mirror-current.txt", "aktuelles gesetz")
    db.insert_law("mirror-proposed.txt", "neuer entwurf")

    responses = iter(
        [
            '{"title": "Kurz", "blurb": "Ein Satz."}',
            """
            {
              "vorgaben": [
                {
                  "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
                  "beschreibung": "E-Sport-Vereine koennen sich auf Sportfoerderung stuetzen.",
                  "aenderungsstatus": "eingefuehrt",
                  "normadressaten": ["business"],
                  "spiegelsituation": {
                    "liegt_vor": "1",
                    "normadressaten": ["administration", "business"],
                    "beschreibung": "Korrespondierender Pruefaufwand bei der Finanzverwaltung.",
                    "mirror_anchor_key": "Gemeinnuetzigkeit E-Sport"
                  }
                }
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
            "filename": "mirror-proposed.txt",
            "current_filename": "mirror-current.txt",
            "app_session_id": "REG-MIRROR",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert summary_resp.status_code == 200

    resp = test_client.post(
        "/regulations/identify",
        json={
            "app_session_id": "REG-MIRROR",
            "model": "test-model",
            "provider": "deepinfra",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["vorgaben"][0]["mirror_anchor_key"] == "gemeinnuetzigkeit-e-sport"

    session_id = db.get_session_id_by_app_id("REG-MIRROR")
    assert session_id is not None
    row = db.list_regulations_for_session(session_id)[0]
    assert row["mirror_applies_to_administration"] == 1
    assert row["mirror_applies_to_business"] == 0
    assert row["mirror_applies_to_citizens"] == 0
    assert row["mirror_description"] == "Korrespondierender Pruefaufwand bei der Finanzverwaltung."
    assert row["mirror_anchor_key"] == "gemeinnuetzigkeit-e-sport"

    tile = next(
        tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee="business")
        if tile.id.startswith("regulation_")
    )
    assert tile.meta_information["mirror_normadressaten"] == ["administration"]
    assert tile.meta_information["mirror_anchor_key"] == "gemeinnuetzigkeit-e-sport"


def test_prompt_opening_falls_back_to_blurb_when_summary_empty(test_client):
    session_id, _ = db.upsert_session("PROMPT-BLURB-FALLBACK", "test-model")
    db.update_session_summary(
        "PROMPT-BLURB-FALLBACK",
        "Titel",
        "",
        law_diff_blurb="Fallback Blurb Text",
    )

    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        session_id=session_id,
        vorgaben_json="[]",
    )
    assert "Fallback Blurb Text" in prompt
