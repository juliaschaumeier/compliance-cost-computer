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


def test_case_group_metrics_require_matching_session_and_addressee(seeded_db):
    conn = seeded_db["conn"]
    with pytest.raises(sqlite3.IntegrityError):
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
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                seeded_db["session_id"],
                seeded_db["case_group_id"],
                "business",
                10,
                2,
                20,
            ),
        )


@pytest.mark.parametrize(
    ("table_name", "value_columns", "value_params"),
    [
        (
            "process_step_effort_metrics_by_addressee",
            "hourly_rate_a_proposed, time_required_in_min_a_proposed, expenses_proposed",
            (40, 15, 5),
        ),
        (
            "process_step_costs_by_addressee",
            "cost_proposed, bureaucracy_cost_proposed, other_cost_proposed",
            (25, 10, 15),
        ),
    ],
)
def test_process_step_addressee_tables_require_matching_session_and_addressee(
    seeded_db,
    table_name,
    value_columns,
    value_params,
):
    conn = seeded_db["conn"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            f"""
            INSERT INTO {table_name} (
                session_id,
                step_id,
                norm_addressee,
                {value_columns}
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                seeded_db["session_id"],
                seeded_db["step_id"],
                "business",
                *value_params,
            ),
        )


def test_init_db_rebuilds_legacy_addressee_child_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "legacy_fk.db")
    db.init_db()

    conn = sqlite3.connect(config.settings.db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("DROP TABLE regulation_process_links_by_addressee")
        conn.execute(
            """
            CREATE TABLE regulation_process_links_by_addressee (
                session_id INTEGER NOT NULL,
                norm_addressee TEXT NOT NULL,
                regulation_id INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                PRIMARY KEY (session_id, norm_addressee, regulation_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (regulation_id) REFERENCES regulations(regulation_id),
                FOREIGN KEY (process_id) REFERENCES processes(process_id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    db.init_db()
    session_id, _ = db.upsert_session("LEGACY-FK", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    regulation_id = db.insert_regulation(session_id, "§ 1", "Beschreibung Vorgabe")
    conn = db.get_conn()
    try:
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
                (session_id, "business", regulation_id, process_id),
            )
    finally:
        conn.close()
