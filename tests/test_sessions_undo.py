import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS
from backend.core.prompts import PromptId
from backend.core.session_graph import sync_all_norm_addressee_tile_snapshots
from backend.core.workflow import undo_step


def _seed_flow(app_session_id: str) -> dict:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    db.insert_regulation(session_id, "§ 1", "Beschreibung")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt 1", "Beschreibung Schritt 1"
    )
    return {
        "session_id": session_id,
        "process_id": process_id,
        "case_group_id": case_group_id,
        "step_id": step_id,
    }


def _seed_flow_for_addressee(app_session_id: str, norm_addressee: str) -> dict:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    db.insert_regulation(session_id, "§ 1", "Beschreibung")
    process_id = db.insert_process(
        session_id,
        f"Prozess {norm_addressee}",
        "Beschreibung Prozess",
        norm_addressee=norm_addressee,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        f"Fallgruppe {norm_addressee}",
        "Beschreibung Fallgruppe",
        norm_addressee=norm_addressee,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        f"Schritt {norm_addressee}",
        "Beschreibung Schritt 1",
        norm_addressee=norm_addressee,
    )
    return {
        "session_id": session_id,
        "process_id": process_id,
        "case_group_id": case_group_id,
        "step_id": step_id,
    }


def _seed_multi_addressee_process_steps(app_session_id: str) -> dict:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    db.insert_regulation(
        session_id,
        "§ 1",
        "Beschreibung",
        applies_to_administration=True,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    seeded: dict[str, dict] = {"session_id": session_id}
    for addressee in (ADMINISTRATION, BUSINESS):
        process_id = db.insert_process(
            session_id,
            f"Prozess {addressee}",
            "Beschreibung Prozess",
            norm_addressee=addressee,
        )
        case_group_id = db.insert_case_group(
            session_id,
            process_id,
            f"Fallgruppe {addressee}",
            "Beschreibung Fallgruppe",
            norm_addressee=addressee,
        )
        step_id = db.insert_process_step(
            session_id,
            case_group_id,
            f"Schritt {addressee}",
            "Beschreibung Schritt",
            norm_addressee=addressee,
        )
        seeded[addressee] = {
            "process_id": process_id,
            "case_group_id": case_group_id,
            "step_id": step_id,
        }
    session = db.get_session_by_id(session_id)
    assert session is not None
    sync_all_norm_addressee_tile_snapshots(session)
    return seeded


def _tile_ids(session_id: int, norm_addressee: str) -> set[str]:
    return {tile.id for tile in db.fetch_tiles(session_id, norm_addressee)}


def test_undo_regulations_clears_all_downstream_artifacts_and_wage_overrides():
    seeded = _seed_flow("UNDO-REGULATIONS-DOWNSTREAM")
    session_id = seeded["session_id"]
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_id"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 40, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=5,
    )
    db.replace_process_step_personnel_effort(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        step_id=seeded["step_id"],
        rows=[
            {
                "period": "proposed",
                "qualification": "einfacher_und_mittlerer_dienst",
                "wage_source_kind": "verwaltungsebene",
                "wage_source_value": "bund",
                "time_required_in_min": 30,
                "model_hourly_rate": 40,
            }
        ],
    )
    db.upsert_session_wage_rate_override(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        wage_source_kind="verwaltungsebene",
        wage_source_value="bund",
        qualification="einfacher_und_mittlerer_dienst",
        hourly_rate_edited=45,
    )
    db.update_process_step_cost(session_id, seeded["step_id"], None, 25)
    db.update_case_group_cost(session_id, seeded["case_group_id"], 50)
    db.update_process_cost(session_id, seeded["process_id"], 50)
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        total_cost=50,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )
    for prompt_id in (
        PromptId.PROCESS_COMPILATION,
        PromptId.CASE_GROUP_DEVELOPMENT,
        PromptId.PROCESS_STEP_ANALYSIS,
        PromptId.CASES_CALCULATION,
        PromptId.EFFORT_CALCULATION,
    ):
        db.insert_llm_answer(
            session_id=session_id,
            prompt_id=prompt_id,
            model="test-model",
            answer_text="{}",
        )
    session = db.get_session_by_id(session_id)
    assert session is not None
    sync_all_norm_addressee_tile_snapshots(session)
    assert any(tile_id.startswith("process_") for tile_id in _tile_ids(session_id, ADMINISTRATION))

    with db.transaction():
        undo_step(session_id, "regulations")

    assert db.list_regulations_for_session(session_id) == []
    assert db.list_processes_for_session(session_id) == []
    assert db.list_case_groups_for_session(session_id) == []
    assert db.list_process_steps_for_session(session_id) == []
    assert db.list_session_personnel_effort(session_id) == []
    assert db.list_session_wage_rate_rows(session_id, ADMINISTRATION) == []
    assert db.get_session_total_costs_by_addressee(session_id, ADMINISTRATION) is None
    assert _tile_ids(session_id, ADMINISTRATION) == {"law_tile"}

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT answer_state, state_reason
        FROM llm_answers
        WHERE session_id = ? AND prompt_id IN (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            PromptId.PROCESS_COMPILATION,
            PromptId.CASE_GROUP_DEVELOPMENT,
            PromptId.PROCESS_STEP_ANALYSIS,
            PromptId.CASES_CALCULATION,
            PromptId.EFFORT_CALCULATION,
        ),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    assert rows
    assert all(row["answer_state"] == "invalid" for row in rows)
    assert all(row["state_reason"] == "session_reverted" for row in rows)


def test_undo_total_cost_clears_costs_only(test_client):
    """Undoing step 7 clears costs but keeps effort metrics and EA edits intact."""
    seeded = _seed_flow("UNDO-COST")
    session_id = seeded["session_id"]

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_id"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 40, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=5,
    )
    db.update_process_step_cost(session_id, seeded["step_id"], None, 25)
    db.update_case_group_cost(session_id, seeded["case_group_id"], 50)
    db.update_process_cost(session_id, seeded["process_id"], 50)
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        total_cost=50,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )
    db.upsert_session_wage_rate_override(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        wage_source_kind="verwaltungsebene",
        wage_source_value="bund",
        qualification="gehobener_dienst",
        hourly_rate_edited=55.0,
    )

    resp = test_client.post("/sessions/undo", json={"app_session_id": "UNDO-COST"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["undone_step"] == "total_cost"
    assert (
        payload["message"]
        == "Gesamtkosten zurückgesetzt. Manuell bearbeitete EA-Werte bleiben "
        "erhalten und werden beim erneuten Ausführen von Schritt 7 wieder "
        "berücksichtigt."
    )

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT cc_cost FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    assert cur.fetchone()["cc_cost"] is None
    assert db.get_session_total_costs_by_addressee(session_id, ADMINISTRATION) is None
    cur.execute(
        "SELECT cost FROM processes WHERE process_id = ?",
        (seeded["process_id"],),
    )
    assert cur.fetchone()["cost"] is None
    cur.execute(
        "SELECT cost FROM case_groups WHERE case_group_id = ?",
        (seeded["case_group_id"],),
    )
    assert cur.fetchone()["cost"] is None
    cur.execute(
        "SELECT cost_current, cost_proposed FROM process_steps WHERE step_id = ?",
        (seeded["step_id"],),
    )
    step_cost = cur.fetchone()
    assert step_cost["cost_current"] is None
    assert step_cost["cost_proposed"] is None
    cur.execute(
        """
        SELECT addressees_current, annual_frequency_current, addressees_proposed, annual_frequency_proposed
        FROM case_groups
        WHERE case_group_id = ?
        """,
        (seeded["case_group_id"],),
    )
    group = cur.fetchone()
    assert group["addressees_proposed"] == 10
    assert group["annual_frequency_proposed"] == 2
    assert group["addressees_current"] is None
    assert group["annual_frequency_current"] is None
    cur.execute(
        """
        SELECT hourly_rate_a_current, time_required_in_min_a_current, expenses_current,
               hourly_rate_a_proposed, time_required_in_min_a_proposed, expenses_proposed
        FROM process_steps
        WHERE step_id = ?
        """,
        (seeded["step_id"],),
    )
    step = cur.fetchone()
    assert step["hourly_rate_a_proposed"] == 40
    assert step["time_required_in_min_a_proposed"] == 30
    assert step["expenses_proposed"] == 5
    assert step["hourly_rate_a_current"] is None
    assert step["time_required_in_min_a_current"] is None
    assert step["expenses_current"] is None
    assert db.get_session_wage_rate_overrides(session_id, ADMINISTRATION) == {
        ("verwaltungsebene", "bund", "gehobener_dienst"): 55.0
    }
    conn.close()


def test_undo_effort_clears_metrics(test_client):
    """Undoing step 6 clears effort metrics and manual EA edits while keeping steps."""
    seeded = _seed_flow("UNDO-EFFORT")
    session_id = seeded["session_id"]

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_id"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 40, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=5,
    )
    db.upsert_session_wage_rate_override(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        wage_source_kind="verwaltungsebene",
        wage_source_value="bund",
        qualification="gehobener_dienst",
        hourly_rate_edited=55.0,
    )

    resp = test_client.post(
        "/sessions/undo", json={"app_session_id": "UNDO-EFFORT"}
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["undone_step"] == "effort"
    assert (
        payload["message"]
        == "Aufwand quantifizieren zurückgesetzt. Die zugehörigen EA-Werte und "
        "manuellen EA-Bearbeitungen wurden gelöscht."
    )

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT addressees_current, annual_frequency_current, addressees_proposed, annual_frequency_proposed
        FROM case_groups
        WHERE case_group_id = ?
        """,
        (seeded["case_group_id"],),
    )
    group = cur.fetchone()
    assert group["addressees_current"] is None
    assert group["annual_frequency_current"] is None
    assert group["addressees_proposed"] is None
    assert group["annual_frequency_proposed"] is None
    cur.execute(
        """
        SELECT hourly_rate_a_current, time_required_in_min_a_current, expenses_current,
               hourly_rate_a_proposed, time_required_in_min_a_proposed, expenses_proposed
        FROM process_steps
        WHERE step_id = ?
        """,
        (seeded["step_id"],),
    )
    step = cur.fetchone()
    assert step["hourly_rate_a_current"] is None
    assert step["time_required_in_min_a_current"] is None
    assert step["expenses_current"] is None
    assert step["hourly_rate_a_proposed"] is None
    assert step["time_required_in_min_a_proposed"] is None
    assert step["expenses_proposed"] is None
    assert db.get_session_wage_rate_overrides(session_id, ADMINISTRATION) == {}
    conn.close()


def test_undo_rebuilds_tiles_for_all_norm_addressees(test_client):
    seeded = _seed_multi_addressee_process_steps("UNDO-TILES-ALL-NA")
    session_id = int(seeded["session_id"])

    for addressee in (ADMINISTRATION, BUSINESS):
        ids = _tile_ids(session_id, addressee)
        assert any(tile_id.startswith("case_group_") for tile_id in ids)
        assert any(tile_id.startswith("step_") for tile_id in ids)

    resp = test_client.post(
        "/sessions/undo", json={"app_session_id": "UNDO-TILES-ALL-NA"}
    )
    assert resp.status_code == 200
    assert resp.json()["undone_step"] == "process_steps"

    for addressee in (ADMINISTRATION, BUSINESS):
        ids = _tile_ids(session_id, addressee)
        assert any(tile_id.startswith("case_group_") for tile_id in ids)
        assert not any(tile_id.startswith("step_") for tile_id in ids)

    resp = test_client.post(
        "/sessions/undo", json={"app_session_id": "UNDO-TILES-ALL-NA"}
    )
    assert resp.status_code == 200
    assert resp.json()["undone_step"] == "case_groups"

    for addressee in (ADMINISTRATION, BUSINESS):
        ids = _tile_ids(session_id, addressee)
        assert any(tile_id.startswith("process_") for tile_id in ids)
        assert not any(tile_id.startswith("case_group_") for tile_id in ids)
        assert not any(tile_id.startswith("step_") for tile_id in ids)


def test_undo_effort_is_atomic_on_failure(test_client, monkeypatch):
    seeded = _seed_flow("UNDO-ATOMIC")
    session_id = seeded["session_id"]

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_id"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 40, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=5,
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.CASES_CALCULATION,
        model="test-model",
        answer_text="cases",
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.EFFORT_CALCULATION,
        model="test-model",
        answer_text="effort",
    )

    def _raise_invalidate(*_args, **_kwargs):
        raise RuntimeError("forced invalidation failure")

    monkeypatch.setattr(db, "invalidate_llm_answers", _raise_invalidate)

    with pytest.raises(RuntimeError):
        test_client.post("/sessions/undo", json={"app_session_id": "UNDO-ATOMIC"})

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT addressees_current, annual_frequency_current, addressees_proposed, annual_frequency_proposed
        FROM case_groups
        WHERE case_group_id = ?
        """,
        (seeded["case_group_id"],),
    )
    group = cur.fetchone()
    assert group["addressees_proposed"] == 10
    assert group["annual_frequency_proposed"] == 2

    cur.execute(
        """
        SELECT hourly_rate_a_current, time_required_in_min_a_current, expenses_current,
               hourly_rate_a_proposed, time_required_in_min_a_proposed, expenses_proposed
        FROM process_steps
        WHERE step_id = ?
        """,
        (seeded["step_id"],),
    )
    step = cur.fetchone()
    assert step["hourly_rate_a_proposed"] == 40
    assert step["time_required_in_min_a_proposed"] == 30
    assert step["expenses_proposed"] == 5
    conn.close()


def test_undo_effort_invalidates_llm_answers_instead_of_deleting(test_client):
    seeded = _seed_flow("UNDO-LLM-INVALIDATE")
    session_id = seeded["session_id"]

    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=seeded["case_group_id"],
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=seeded["step_id"],
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 40, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=5,
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.CASES_CALCULATION,
        model="test-model",
        answer_text="cases",
    )
    db.insert_llm_answer(
        session_id=session_id,
        prompt_id=PromptId.EFFORT_CALCULATION,
        model="test-model",
        answer_text="effort",
    )

    resp = test_client.post("/sessions/undo", json={"app_session_id": "UNDO-LLM-INVALIDATE"})
    assert resp.status_code == 200
    assert resp.json()["undone_step"] == "effort"

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
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    assert [row["prompt_id"] for row in rows] == [
        PromptId.CASES_CALCULATION,
        PromptId.EFFORT_CALCULATION,
    ]
    assert all(row["answer_state"] == "invalid" for row in rows)
    assert all(row["state_reason"] == "session_reverted" for row in rows)


def test_undo_effort_clears_all_norm_addressees(test_client):
    admin = _seed_flow_for_addressee("UNDO-EFFORT-SCOPED", ADMINISTRATION)
    business = _seed_flow_for_addressee("UNDO-EFFORT-SCOPED", BUSINESS)
    session_id = admin["session_id"]

    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=admin["case_group_id"],
        norm_addressee=ADMINISTRATION,
        addressees_proposed=10,
        annual_frequency_proposed=2,
        case_metric_research_json={
            "confidence": {"anzahl_betroffene_vorschlag": "medium"},
            "erklaerungen": {
                "anzahl_betroffene_vorschlag": "Admin-Evidenz vor Undo."
            },
        },
    )
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=business["case_group_id"],
        norm_addressee=BUSINESS,
        addressees_proposed=20,
        annual_frequency_proposed=3,
        case_metric_research_json={
            "confidence": {"anzahl_betroffene_vorschlag": "high"},
            "erklaerungen": {
                "anzahl_betroffene_vorschlag": "Business-Evidenz vor Undo."
            },
        },
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=admin["step_id"],
        norm_addressee=ADMINISTRATION,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 40, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 30, "b": None, "c": None, "d": None},
        expenses_proposed=5,
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=business["step_id"],
        norm_addressee=BUSINESS,
        hourly_rates_current={},
        time_required_current={},
        expenses_current=None,
        hourly_rates_proposed={"a": 50, "b": None, "c": None, "d": None},
        time_required_proposed={"a": 45, "b": None, "c": None, "d": None},
        expenses_proposed=7,
    )

    resp = test_client.post(
        "/sessions/undo",
        json={"app_session_id": "UNDO-EFFORT-SCOPED"},
    )
    assert resp.status_code == 200
    assert resp.json()["undone_step"] == "effort"

    conn = db.get_conn()
    cur = conn.cursor()
    for seed in (admin, business):
        cur.execute(
            """
            SELECT addressees_proposed, annual_frequency_proposed, case_metric_research_json
            FROM case_groups
            WHERE case_group_id = ?
            """,
            (seed["case_group_id"],),
        )
        row = cur.fetchone()
        assert row["addressees_proposed"] is None
        assert row["annual_frequency_proposed"] is None
        assert row["case_metric_research_json"] is None

        cur.execute(
            """
            SELECT hourly_rate_a_proposed, time_required_in_min_a_proposed, expenses_proposed
            FROM process_steps
            WHERE step_id = ?
            """,
            (seed["step_id"],),
        )
        step = cur.fetchone()
        assert step["hourly_rate_a_proposed"] is None
        assert step["time_required_in_min_a_proposed"] is None
        assert step["expenses_proposed"] is None
    conn.close()


def test_undo_total_cost_clears_all_norm_addressees(test_client):
    admin = _seed_flow_for_addressee("UNDO-COST-SCOPED", ADMINISTRATION)
    business = _seed_flow_for_addressee("UNDO-COST-SCOPED", BUSINESS)
    session_id = admin["session_id"]

    db.update_process_step_cost(session_id, admin["step_id"], None, 25)
    db.update_case_group_cost(session_id, admin["case_group_id"], 50)
    db.update_process_cost(session_id, admin["process_id"], 50)
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        total_cost=50,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )

    db.update_process_step_cost(session_id, business["step_id"], None, 75)
    db.update_case_group_cost(session_id, business["case_group_id"], 120)
    db.update_process_cost(session_id, business["process_id"], 120)
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=BUSINESS,
        total_cost=120,
        bureaucracy_cost=80,
        total_time_minutes=None,
        total_expenses=None,
    )

    resp = test_client.post(
        "/sessions/undo",
        json={"app_session_id": "UNDO-COST-SCOPED"},
    )
    assert resp.status_code == 200
    assert resp.json()["undone_step"] == "total_cost"

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT cc_cost FROM sessions WHERE session_id = ?", (session_id,))
    assert cur.fetchone()["cc_cost"] is None
    assert db.get_session_total_costs_by_addressee(session_id, ADMINISTRATION) is None
    assert db.get_session_total_costs_by_addressee(session_id, BUSINESS) is None

    for seed in (admin, business):
        cur.execute(
            "SELECT cost FROM processes WHERE process_id = ?",
            (seed["process_id"],),
        )
        assert cur.fetchone()["cost"] is None
    conn.close()
