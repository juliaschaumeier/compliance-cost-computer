import sqlite3

import pytest

from backend.core import config, db


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    session_id, _ = db.upsert_session("FK-CHECK", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt A", "Beschreibung Schritt A"
    )
    regulation_id = db.insert_regulation(session_id, "§ 1", "Beschreibung Vorgabe")
    conn = db.get_conn()
    try:
        yield {
            "conn": conn,
            "session_id": session_id,
            "process_id": process_id,
            "case_group_id": case_group_id,
            "step_id": step_id,
            "regulation_id": regulation_id,
        }
    finally:
        conn.close()


def test_processes_reject_invalid_norm_addressee(seeded_db):
    conn = seeded_db["conn"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO processes (
                session_id,
                norm_addressee,
                process,
                description,
                change_status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                seeded_db["session_id"],
                "invalid",
                "Fehlerprozess",
                "Beschreibung",
                "neu",
            ),
        )


def test_regulation_process_links_require_matching_session_and_addressee(seeded_db):
    conn = seeded_db["conn"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO regulation_process_links_by_addressee (
                session_id,
                norm_addressee,
                regulation_id,
                process_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                seeded_db["session_id"],
                "business",
                seeded_db["regulation_id"],
                seeded_db["process_id"],
            ),
        )


def test_update_regulation_process_links_and_lists_by_addressee(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "addressee_links.db")
    db.init_db()

    session_id, _ = db.upsert_session("ADDRESSEE-LINKS", "test-model")
    regulation_id = db.insert_regulation(
        session_id,
        "§ 2",
        "Beschreibung Vorgabe B",
        applies_to_administration=True,
        applies_to_business=True,
        applies_to_citizens=False,
    )
    admin_process_id = db.insert_process(
        session_id,
        "Verwaltungsprozess",
        "Beschreibung Verwaltung",
        norm_addressee="administration",
    )
    business_process_id = db.insert_process(
        session_id,
        "Wirtschaftsprozess",
        "Beschreibung Wirtschaft",
        norm_addressee="business",
    )

    assert db.update_regulation_process(regulation_id, business_process_id, "business") is True
    assert db.update_regulation_process(regulation_id, business_process_id, "business") is False
    assert db.update_regulation_process(regulation_id, admin_process_id, "administration") is True

    admin_rows = db.list_regulations_for_session_and_addressee(session_id, "administration")
    business_rows = db.list_regulations_for_session_and_addressee(session_id, "business")
    citizens_rows = db.list_regulations_for_session_and_addressee(session_id, "citizens")

    assert len(admin_rows) == 1
    assert admin_rows[0]["regulation_id"] == regulation_id
    assert admin_rows[0]["process_id"] == admin_process_id

    assert len(business_rows) == 1
    assert business_rows[0]["regulation_id"] == regulation_id
    assert business_rows[0]["process_id"] == business_process_id

    assert citizens_rows == []

    conn = db.get_conn()
    try:
        stored_links = conn.execute(
            """
            SELECT session_id, norm_addressee, regulation_id, process_id
            FROM regulation_process_links_by_addressee
            ORDER BY norm_addressee, regulation_id
            """
        ).fetchall()
    finally:
        conn.close()

    assert [tuple(row) for row in stored_links] == [
        (session_id, "business", regulation_id, business_process_id)
    ]


def test_init_db_migrates_addressee_metrics_into_parent_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "legacy_addressee_metrics.db")
    db.init_db()

    session_id, _ = db.upsert_session("LEGACY-METRICS", "test-model")
    process_id = db.insert_process(
        session_id,
        "Prozess B",
        "Beschreibung Prozess B",
        norm_addressee="business",
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe B",
        "Beschreibung Fallgruppe B",
        norm_addressee="business",
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt B",
        "Beschreibung Schritt B",
        norm_addressee="business",
    )

    conn = db.get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE case_group_metrics_by_addressee (
                session_id INTEGER NOT NULL,
                case_group_id INTEGER NOT NULL,
                norm_addressee TEXT NOT NULL,
                addressees_current REAL,
                annual_frequency_current REAL,
                cases_current REAL,
                addressees_proposed REAL,
                annual_frequency_proposed REAL,
                cases_proposed REAL,
                PRIMARY KEY (session_id, case_group_id, norm_addressee)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE process_step_effort_metrics_by_addressee (
                session_id INTEGER NOT NULL,
                step_id INTEGER NOT NULL,
                norm_addressee TEXT NOT NULL,
                hourly_rate_a_current REAL,
                hourly_rate_b_current REAL,
                hourly_rate_c_current REAL,
                hourly_rate_d_current REAL,
                time_required_in_min_a_current REAL,
                time_required_in_min_b_current REAL,
                time_required_in_min_c_current REAL,
                time_required_in_min_d_current REAL,
                expenses_current REAL,
                hourly_rate_a_proposed REAL,
                hourly_rate_b_proposed REAL,
                hourly_rate_c_proposed REAL,
                hourly_rate_d_proposed REAL,
                time_required_in_min_a_proposed REAL,
                time_required_in_min_b_proposed REAL,
                time_required_in_min_c_proposed REAL,
                time_required_in_min_d_proposed REAL,
                expenses_proposed REAL,
                execution_per_case INTEGER,
                PRIMARY KEY (session_id, step_id, norm_addressee)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE process_step_costs_by_addressee (
                session_id INTEGER NOT NULL,
                step_id INTEGER NOT NULL,
                norm_addressee TEXT NOT NULL,
                cost_current REAL,
                cost_proposed REAL,
                bureaucracy_cost_current REAL,
                bureaucracy_cost_proposed REAL,
                other_cost_current REAL,
                other_cost_proposed REAL,
                PRIMARY KEY (session_id, step_id, norm_addressee)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO case_group_metrics_by_addressee (
                session_id,
                case_group_id,
                norm_addressee,
                addressees_proposed,
                annual_frequency_proposed,
                cases_proposed
            )
            VALUES (?, ?, 'business', 10, 2, 20)
            """,
            (session_id, case_group_id),
        )
        conn.execute(
            """
            INSERT INTO process_step_effort_metrics_by_addressee (
                session_id,
                step_id,
                norm_addressee,
                hourly_rate_a_proposed,
                time_required_in_min_a_proposed,
                expenses_proposed,
                execution_per_case
            )
            VALUES (?, ?, 'business', 55, 30, 5, 0)
            """,
            (session_id, step_id),
        )
        conn.execute(
            """
            INSERT INTO process_step_costs_by_addressee (
                session_id,
                step_id,
                norm_addressee,
                cost_current,
                cost_proposed,
                bureaucracy_cost_proposed,
                other_cost_proposed
            )
            VALUES (?, ?, 'business', 11, 25, 10, 15)
            """,
            (session_id, step_id),
        )
        conn.commit()
    finally:
        conn.close()

    db.init_db()

    check = sqlite3.connect(config.settings.db_path)
    check.row_factory = sqlite3.Row
    try:
        tables = {
            row["name"]
            for row in check.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "case_group_metrics_by_addressee" not in tables
        assert "process_step_effort_metrics_by_addressee" not in tables
        assert "process_step_costs_by_addressee" not in tables

        case_group = check.execute(
            """
            SELECT addressees_proposed, annual_frequency_proposed, cases_proposed
            FROM case_groups
            WHERE session_id = ? AND case_group_id = ? AND norm_addressee = 'business'
            """,
            (session_id, case_group_id),
        ).fetchone()
        assert case_group["addressees_proposed"] == 10
        assert case_group["annual_frequency_proposed"] == 2
        assert case_group["cases_proposed"] == 20

        step = check.execute(
            """
            SELECT
                hourly_rate_a_proposed,
                time_required_in_min_a_proposed,
                expenses_proposed,
                execution_per_case,
                cost_current,
                cost_proposed
            FROM process_steps
            WHERE session_id = ? AND step_id = ? AND norm_addressee = 'business'
            """,
            (session_id, step_id),
        ).fetchone()
        assert step["hourly_rate_a_proposed"] == 55
        assert step["time_required_in_min_a_proposed"] == 30
        assert step["expenses_proposed"] == 5
        assert step["execution_per_case"] == 0
        assert step["cost_current"] == 11
        assert step["cost_proposed"] == 25
    finally:
        check.close()
