import sqlite3

from backend.core import db
from backend.core import config


def _create_legacy_schema(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE sessions (
            session_id INTEGER PRIMARY KEY,
            app_session_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT current_timestamp,
            llm_model TEXT NOT NULL,
            current_law_id INTEGER,
            proposed_law_id INTEGER,
            cc_cost REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE processes (
            process_id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            process TEXT NOT NULL,
            description TEXT NOT NULL,
            change_status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT current_timestamp
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE case_groups (
            case_group_id INTEGER PRIMARY KEY,
            process_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            case_group TEXT NOT NULL,
            description TEXT NOT NULL,
            change_status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT current_timestamp
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE process_steps (
            step_id                         INTEGER PRIMARY KEY,
            case_group_id                   INTEGER NOT NULL,
            session_id                      INTEGER NOT NULL,
            step                            TEXT NOT NULL,
            description                     TEXT NOT NULL,
            change_status                   TEXT NOT NULL,
            created_at                      TEXT NOT NULL DEFAULT current_timestamp,
            previous_id                     INTEGER,
            next_id                         INTEGER,
            hourly_rate_a_current           REAL,
            hourly_rate_b_current           REAL,
            hourly_rate_c_current           REAL,
            hourly_rate_d_current           REAL,
            time_required_in_min_a_current  REAL,
            time_required_in_min_b_current  REAL,
            time_required_in_min_c_current  REAL,
            time_required_in_min_d_current  REAL,
            expenses_current                REAL,
            hourly_rate_a_proposed          REAL,
            hourly_rate_b_proposed          REAL,
            hourly_rate_c_proposed          REAL,
            hourly_rate_d_proposed          REAL,
            time_required_in_min_a_proposed REAL,
            time_required_in_min_b_proposed REAL,
            time_required_in_min_c_proposed REAL,
            time_required_in_min_d_proposed REAL,
            expenses_proposed               REAL,
            execution_per_case              BIT,
            cost_current                    REAL,
            cost_proposed                   REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE llm_answers (
            answer_id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            prompt_id TEXT NOT NULL,
            model TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            metadata JSON,
            created_at TEXT NOT NULL DEFAULT current_timestamp
        )
        """
    )


def _seed_legacy_rows(cur: sqlite3.Cursor) -> None:
    cur.execute(
        "INSERT INTO sessions (session_id, app_session_id, llm_model) VALUES (1, 'MIG-1', 'gpt-5-mini')"
    )
    cur.execute(
        """
        INSERT INTO processes (process_id, session_id, process, description, change_status)
        VALUES (1, 1, 'P1', 'Prozess', 'geaendert')
        """
    )
    cur.execute(
        """
        INSERT INTO case_groups (case_group_id, process_id, session_id, case_group, description, change_status)
        VALUES (1, 1, 1, 'FG1', 'Fallgruppe', 'geaendert')
        """
    )
    cur.execute(
        """
        INSERT INTO process_steps (
            step_id, case_group_id, session_id, step, description, change_status,
            execution_per_case, cost_current, cost_proposed
        )
        VALUES (1, 1, 1, 'S1', 'Schritt', 'geaendert', 0, 12.5, 13.5)
        """
    )
    cur.execute(
        """
        INSERT INTO llm_answers (
            answer_id, session_id, prompt_id, model, answer_text, metadata
        )
        VALUES (1, 1, 'prompt-1', 'gpt-5-mini', 'Antwort', '{}')
        """
    )


def test_init_db_preserves_process_steps_execution_per_case(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy_process_steps.db"

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()
    _create_legacy_schema(cur)
    _seed_legacy_rows(cur)
    conn.commit()
    conn.close()

    monkeypatch.setattr(config.settings, "db_path", db_path)
    db.init_db()

    check = sqlite3.connect(db_path)
    check.row_factory = sqlite3.Row
    cur = check.cursor()
    cur.execute("PRAGMA table_info(process_steps)")
    columns = {row["name"] for row in cur.fetchall()}
    assert "execution_per_case" in columns
    assert "expenses_current_edited" in columns
    assert "expenses_proposed_edited" in columns

    cur.execute(
        "SELECT step, description, execution_per_case, cost_current, cost_proposed FROM process_steps WHERE step_id = 1"
    )
    row = cur.fetchone()
    assert row["step"] == "S1"
    assert row["description"] == "Schritt"
    assert row["execution_per_case"] == 0
    assert row["cost_current"] == 12.5
    assert row["cost_proposed"] == 13.5
    check.close()


def test_init_db_migrates_legacy_llm_answers_before_state_indexes(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy_llm_answers.db"

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()
    _create_legacy_schema(cur)
    _seed_legacy_rows(cur)
    conn.commit()
    conn.close()

    monkeypatch.setattr(config.settings, "db_path", db_path)
    db.init_db()

    check = sqlite3.connect(db_path)
    check.row_factory = sqlite3.Row
    cur = check.cursor()
    cur.execute("PRAGMA table_info(llm_answers)")
    columns = {row["name"] for row in cur.fetchall()}
    assert "answer_state" in columns

    cur.execute("PRAGMA index_list(llm_answers)")
    indexes = {row["name"] for row in cur.fetchall()}
    assert "idx_llm_answers_state" in indexes

    cur.execute("SELECT answer_state FROM llm_answers WHERE answer_id = 1")
    assert cur.fetchone()["answer_state"] == "active"
    check.close()
